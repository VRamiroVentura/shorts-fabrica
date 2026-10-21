"""Punto de entrada: python -m fabrica.main generar | publicar --base-url URL | reporte"""
import argparse
import html
import json
import os
import shutil
import sys

from . import util

SALIDA = util.RAIZ / "out"
SITIO = SALIDA / "sitio"


def _turno():
    """1 = el video de siempre; 2 = el segundo video del día (turnos.json)."""
    try:
        return 2 if int(os.getenv("TURNO") or 1) == 2 else 1
    except ValueError:
        return 1


def _turnos(cfg):
    """Turnos activos: el 1 siempre; el 2 si turnos.json tiene segundo_turno en true."""
    lista = [1]
    if cfg.get("segundo_turno") and cfg.get("plan_semanal_2") and cfg.get("horarios_2"):
        lista.append(2)
    return lista


def _horarios(cfg, turno):
    return (cfg.get("horarios_2") if turno == 2 else cfg.get("horarios")) or {}


def _carpeta(fecha, turno):
    return fecha if turno == 1 else f"{fecha}-t{turno}"


def _serie_del_dia(cfg, turno=None):
    forzada = (os.getenv("SERIE") or "").strip().lower()
    if forzada in cfg["series"]:
        return forzada
    dia = str(util.ahora().isoweekday())
    if (turno or _turno()) == 2:
        clave = (cfg.get("plan_semanal_2") or {}).get(dia)
        if clave in cfg["series"]:
            return clave
    return cfg["plan_semanal"][dia]


def _base_paginas():
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return None
    duenio, nombre = repo.split("/", 1)
    return f"https://{duenio.lower()}.github.io/{nombre}/"


def _traer_anteriores(actual):
    """La página de GitHub se reemplaza entera en cada corrida. Traigo los videos de los últimos 2 días
    para que los links de los mails (y el video para TikTok) sigan andando."""
    base = _base_paginas()
    desde = (util.ahora() - util.timedelta(days=2)).strftime("%Y-%m-%d")
    quedan = [x for x in util.leer_json("data/sitio.json", []) or []
              if x.get("fecha", "") >= desde and x.get("carpeta") != actual]
    if not base:
        return quedan
    for x in quedan:
        for rel in x.get("archivos", []):
            try:
                r = util.pedir("GET", base + rel, intentos=2, timeout=120)
                if r is not None and r.status_code == 200:
                    destino = SITIO / rel
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    destino.write_bytes(r.content)
            except Exception as e:  # noqa
                util.log("No pude traer", rel, util.ocultar(e))
    return quedan


def _serie(cfg, clave_serie):
    serie = dict(cfg["series"][clave_serie])
    propio = util.RAIZ / "prompts" / "series" / f"{clave_serie}.md"
    if propio.exists():  # instrucciones de la serie mejoradas, sin tocar config.json
        serie["prompt"] = propio.read_text(encoding="utf-8").strip()
    return serie


def _producir(cfg, clave_serie, serie, contenido, fuentes, fuentes_detalle, firma_base, fecha, turno, nombre_carpeta,
              evitar=(), version=1):
    """Arma placas, video y portada en out/sitio/<nombre_carpeta> y devuelve la publicación."""
    from . import carrusel, montaje
    carpeta = SITIO / nombre_carpeta
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    placas = carrusel.generar(contenido, serie["nombre"], cfg["usuario"], carpeta)
    montaje.generar(contenido, serie["nombre"], cfg["usuario"], carpeta, evitar=evitar)
    shutil.rmtree(carpeta / "_trabajo", ignore_errors=True)
    (carpeta / "spec.json").unlink(missing_ok=True)
    meta_video = util.leer_json(str((carpeta / "meta.json").relative_to(util.RAIZ)), {}) or {}
    (carpeta / "meta.json").unlink(missing_ok=True)
    (SITIO / "index.html").write_text("<meta charset='utf-8'><p>Fábrica de Shorts</p>", encoding="utf-8")
    firma = firma_base
    if meta_video.get("clips_stock"):
        firma = firma + f'\nVideos de stock: {meta_video.get("banco")}.'
    tags = " ".join(contenido["hashtags"])
    return {
        "fecha": fecha,
        "serie": clave_serie,
        "serie_nombre": serie["nombre"],
        "titulo": contenido["titulo"],
        "caption": f'{contenido["titulo"]}\n\n{contenido["descripcion"]}\n\n{firma}\n\n{tags}'.strip(),
        "descripcion_youtube": f'{contenido["descripcion"]}\n\n{firma}\n\n{tags} #shorts'.strip(),
        "tags": [t.lstrip("#") for t in contenido["hashtags"]],
        "guion": " ".join(e["texto_voz"] for e in contenido["escenas"]),
        "fuentes": fuentes,
        "fuentes_detalle": fuentes_detalle,
        "archivos": {"video": f"{nombre_carpeta}/video.mp4", "portada": f"{nombre_carpeta}/thumb.jpg",
                     "placas": [f"{nombre_carpeta}/{x.name}" for x in placas]},
        "contenido": contenido,
        "video": meta_video,
        "turno": turno,
        "carpeta": nombre_carpeta,
        "base": _carpeta(fecha, turno),
        "firma_base": firma_base,
        "version": version,
    }


def _anotar_sitio(anteriores, p):
    a = p["archivos"]
    util.guardar_json("data/sitio.json", anteriores + [
        {"fecha": p["fecha"], "carpeta": p["carpeta"], "archivos": [a["video"], a["portada"]] + a["placas"]}])


def generar(simulado=False):
    cfg = util.config()
    os.environ.setdefault("TTS_VOICE", cfg.get("voz", "es-AR-TomasNeural"))
    os.environ.setdefault("TTS_RATE", str(cfg.get("voz_velocidad", "+15%")))
    os.environ.setdefault("TTS_MAX_PAUSA", str(cfg.get("voz_pausa_maxima", 0.28)))
    from . import escritor, investigar  # importa después de fijar la voz

    turno = _turno()
    if not simulado:
        _sumar_intento(turno)
    inicio = util.datetime.now(util.ZoneInfo("UTC")).isoformat()
    clave_serie = _serie_del_dia(cfg, turno)
    serie = _serie(cfg, clave_serie)
    fecha = util.ahora().strftime("%Y-%m-%d")
    util.log("Serie de hoy:", serie["nombre"], f"(turno {turno})")

    historial = util.leer_json("data/historial.json", [])
    usados = {f for h in historial for f in h.get("fuentes", [])}
    titulos = [h["titulo"] for h in reversed(historial)]

    fuentes = []
    clave_yt = util.secreto("YT_API_KEY")
    if serie.get("modo") == "contable" and not simulado:
        from . import contable
        fuentes = contable.buscar(cfg.get("referentes_contables", {}), clave_yt, usados,
                                  cfg.get("fuentes_por_video", 2))
        util.log("Fuentes:", [f'{f["canal"]}: {f["titulo"][:90]} ({f.get("tipo")}, {f.get("score")})'
                              for f in fuentes] or "ninguna, la IA elige el tema")
    elif clave_yt and not simulado:
        try:
            if serie.get("modo") == "virales":
                lista = serie["busquedas"]
                semana = util.ahora().isocalendar()[1]
                rotadas = [lista[(semana * 2 + k) % len(lista)] for k in range(len(lista))]
                fuentes = investigar.virales_mundo(rotadas, clave_yt, usados, cfg.get("fuentes_por_video", 2))
            else:
                fuentes = investigar.fuera_de_serie(serie.get("canales", []), clave_yt, usados,
                                                    cfg.get("fuentes_por_video", 2))
            for f in fuentes:
                f["transcripcion"] = investigar.transcripcion(f["id"])
            util.log("Fuentes:", [f'{f["canal"]}: {f["titulo"]} (x{f["score"]})' for f in fuentes])
        except Exception as e:  # noqa
            util.log("La investigación falló, sigo sin fuentes:", e)
    else:
        util.log("Sin YT_API_KEY: la IA elige el tema dentro de la serie")

    if simulado:
        contenido = escritor.validar(json.loads((util.RAIZ / "data" / "ejemplo_contenido.json").read_text(encoding="utf-8")))
    else:
        contenido = escritor.escribir(serie, fuentes, titulos)

    nombre_carpeta = _carpeta(fecha, turno)
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    SITIO.mkdir(parents=True)
    util.guardar_json("out/inicio.json", {"inicio": inicio})
    anteriores = [] if simulado else _traer_anteriores(nombre_carpeta)
    firma = cfg.get("firma", "")
    if serie.get("modo") == "virales" and fuentes:
        firma = ("Inspirado en videos virales de " +
                 ", ".join(f'{f["canal"]} ({f["pais"]})' for f in fuentes) + ".\n" + firma)
    detalle = [{"canal": f["canal"], "titulo": f["titulo"], "score": f.get("score") or f.get("pais", "")}
               for f in fuentes]
    publicacion = _producir(cfg, clave_serie, serie, contenido, [f["id"] for f in fuentes], detalle, firma,
                            fecha, turno, nombre_carpeta)
    util.guardar_json("out/publicacion.json", publicacion)
    if not simulado:
        _anotar_sitio(anteriores, publicacion)
    util.log("Listo:", contenido["titulo"])


def rehacer():
    """Rehace el video con los cambios que pediste (el pedido lo dejó «esperar» en out/pedido.json)."""
    from . import escritor
    cfg = util.config()
    os.environ.setdefault("TTS_VOICE", cfg.get("voz", "es-AR-TomasNeural"))
    os.environ.setdefault("TTS_RATE", str(cfg.get("voz_velocidad", "+15%")))
    p = util.leer_json("out/publicacion.json")
    pedido = util.leer_json("out/pedido.json", {}) or {}
    cambios = (pedido.get("cambios") or "").strip()
    serie = _serie(cfg, p["serie"])
    version = int(p.get("version", 1)) + 1
    util.log(f"Rehago el video (versión {version}) con tus cambios:", cambios)
    try:
        contenido = escritor.aplicar_cambios(serie, p["contenido"], cambios) if cambios else p["contenido"]
    except Exception as e:  # noqa
        util.avisar("No pude aplicar los cambios al guion", f"Sigo con el guion anterior. Motivo: {util.ocultar(e)}")
        contenido = p["contenido"]
    otros_clips = any(x in cambios.lower() for x in ("clip", "imagen", "imágen", "fondo", "toma", "visual", "video de fondo"))
    evitar = set((p.get("video") or {}).get("clips_ids") or []) if otros_clips else set()
    nombre = f'{p.get("base") or p["carpeta"]}-v{version}'
    try:
        nueva = _producir(cfg, p["serie"], serie, contenido, p.get("fuentes", []), p.get("fuentes_detalle", []),
                          p.get("firma_base", cfg.get("firma", "")), p["fecha"], p.get("turno", 1), nombre,
                          evitar=evitar, version=version)
    except Exception as e:  # noqa
        # si algo falla, no se pierde el día: sale la versión anterior
        util.avisar("No pude rehacer el video", f"Sale la versión anterior. Motivo: {util.ocultar(e)}")
        return
    nueva["cambios_pedidos"] = (p.get("cambios_pedidos") or []) + [cambios]
    nueva["pedido_creado"] = pedido.get("creado", "")
    util.guardar_json("out/publicacion.json", nueva)
    anteriores = [x for x in (util.leer_json("data/sitio.json", []) or []) if x.get("carpeta") != nombre]
    _anotar_sitio(anteriores, nueva)
    util.log("Versión nueva lista:", nueva["titulo"])


def publicar(base_url):
    from . import publicar as pub
    cfg = util.config()
    p = util.leer_json("out/publicacion.json")
    base = base_url.rstrip("/") + "/"
    decision = (util.leer_json("out/decision.json", {}) or {}).get("decision", "publicar")
    if decision == "cancelar":
        historial = util.leer_json("data/historial.json", []) or []
        historial.append({"fecha": p["fecha"], "turno": p.get("turno", 1), "hora": util.ahora().strftime("%H:%M"),
                          "serie": p["serie"], "titulo": p["titulo"], "fuentes": p["fuentes"], "resultados": {},
                          "cancelado": True})
        util.guardar_json("data/historial.json", historial[-400:])
        util.avisar("No se publicó", "Pediste que este video no salga hoy.")
        try:
            pub.mail(f'No se publicó (lo pediste): {p["titulo"]}',
                     f'<p>Como pediste, <b>{html.escape(p["titulo"])}</b> no se publicó. Si lo querés subir a mano, '
                     f'acá está el <a href="{base}{p["archivos"]["video"]}">video</a> (el link dura 2 días).</p>')
        except Exception as ex:  # noqa
            util.log("No pude mandar el mail:", ex)
        return
    url = lambda rel: base + rel  # noqa
    video_local = SITIO / p["archivos"]["video"]
    hoy_carrusel = util.ahora().isoweekday() in cfg.get("carrusel_dias", []) and p.get("turno", 1) == 1
    quiere = cfg.get("publicar", {})
    resultados = {}

    def intentar(nombre, fn):
        try:
            resultados[nombre] = {"ok": True, "id": fn()}
        except Exception as e:  # noqa
            resultados[nombre] = {"ok": False, "error": str(e)[:300]}
        util.log(nombre, resultados[nombre])

    if quiere.get("instagram_reel"):
        intentar("instagram_reel", lambda: pub.instagram_reel(url(p["archivos"]["video"]),
                                                              url(p["archivos"]["portada"]), p["caption"]))
    if quiere.get("instagram_carrusel") and hoy_carrusel:
        intentar("instagram_carrusel", lambda: pub.instagram_carrusel([url(x) for x in p["archivos"]["placas"]],
                                                                      p["caption"]))
    if quiere.get("youtube"):
        intentar("youtube", lambda: pub.youtube(video_local, p["titulo"], p["descripcion_youtube"], p["tags"],
                                                cfg.get("youtube_privacidad", "public")))
    if quiere.get("tiktok"):
        intentar("tiktok", lambda: pub.tiktok(video_local, p["caption"], cfg.get("tiktok_privacidad", "SELF_ONLY")))
    if quiere.get("facebook"):
        intentar("facebook", lambda: pub.facebook_reel(video_local, p["caption"], p["titulo"]))

    historial = util.leer_json("data/historial.json", [])
    historial.append({"fecha": p["fecha"], "turno": p.get("turno", 1), "hora": util.ahora().strftime("%H:%M"),
                      "serie": p["serie"], "titulo": p["titulo"], "fuentes": p["fuentes"], "resultados": resultados})
    util.guardar_json("data/historial.json", historial[-400:])
    _registro(p, resultados, base)
    _mail_diario(p, resultados, base)
    resumen(base_url, resultados)

    if resultados and not any(r["ok"] for r in resultados.values()):
        util.log("No se pudo publicar en ninguna red")
        sys.exit(1)


def resumen(base_url, res=None):
    """Escribe el resumen visible en la pestaña Actions de GitHub (con las placas a la vista)."""
    destino = os.getenv("GITHUB_STEP_SUMMARY")
    p = util.leer_json("out/publicacion.json")
    if not (destino and p):
        return
    base = base_url.rstrip("/") + "/"
    md = [f'## {p["serie_nombre"]}: {p["titulo"]}', ""]
    for red, r in (res or {}).items():
        md.append(f'- **{red}**: ' + ("✅ publicado" if r["ok"] else "❌ " + r["error"]))
    v = p.get("video") or {}
    if v:
        md += [f'Voz: {v.get("voz", "?")} · {v.get("duracion", "?")} s · fondos: {v.get("clips_stock", 0)} de '
               f'{v.get("clips", 0)} clips de {v.get("banco") or "stock"}, {v.get("clips_propios", 0)} propios, '
               f'{v.get("postales", 0)} postales de Argentina · música: {v.get("musica") or "no"}', ""]
    md += ["", f'[▶️ Ver el video]({base}{p["archivos"]["video"]}) · [Portada]({base}{p["archivos"]["portada"]})', ""]
    md += [" ".join(f'<img src="{base}{x}" width="180">' for x in p["archivos"]["placas"]), ""]
    md += ["**Texto para publicar:**", "", "```", p["caption"], "```", "", "**Guion:** " + p["guion"]]
    with open(destino, "a", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


def _registro(p, res, base):
    lineas = [f'# {p["fecha"]} · {p["serie_nombre"]}', "", f'**{p["titulo"]}**', ""]
    for red, r in res.items():
        lineas.append(f'- {red}: ' + ("publicado (" + str(r["id"]) + ")" if r["ok"] else "ERROR: " + r["error"]))
    lineas += ["", "Basado en: " + ("; ".join(f'{f["canal"]} - {f["titulo"]} (x{f["score"]})'
                                              for f in p["fuentes_detalle"]) or "tema propio"),
               "", "## Texto", "", p["caption"], "", "## Guion", "", p["guion"]]
    ruta = util.RAIZ / "publicaciones" / f'{p.get("base") or p.get("carpeta") or p["fecha"]}.md'
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _mail_diario(p, res, base):
    from . import publicar as pub
    e = html.escape
    filas = "".join(
        f'<li><b>{e(red)}</b>: {"✅ publicado" if r["ok"] else "❌ " + e(r["error"])}</li>' for red, r in res.items())
    estado = util.leer_json("data/estado.json", {})
    aviso = f'<p style="color:#b00">⚠️ {e(estado["ig_aviso"])}</p>' if estado.get("ig_aviso") else ""
    cuerpo = (f'<h2>{e(p["serie_nombre"])}: {e(p["titulo"])}</h2><ul>{filas}</ul>{aviso}'
              f'<p><a href="{base}{p["archivos"]["video"]}">Video</a> · '
              f'<a href="{base}{p["archivos"]["portada"]}">Portada</a> · '
              + (f'<a href="{base}{p["archivos"]["placas"][0]}">Carrusel</a>' if p["archivos"].get("placas") else "")
              + ' (los links duran 2 días)</p>'
              f'<p><b>Texto:</b><br>{e(p["caption"]).replace(chr(10), "<br>")}</p>'
              f'<p><b>Para TikTok:</b> bajá el video y, antes de publicar, tocá <b>Más opciones</b> y activá '
              f'<b>«Contenido generado por IA»</b> (la voz es de IA).</p>'
              f'<hr><p style="color:#666">{e(p["guion"])}</p>')
    try:
        segundo = " (2º del día)" if p.get("turno", 1) == 2 else ""
        pub.mail(f'Short del día{segundo}: {p["titulo"]}', cuerpo)
    except Exception as ex:  # noqa
        util.log("No pude mandar el mail:", ex)


def _rendimiento(cfg, clave_yt, dias=30):
    """Cómo le fue a cada serie nuestra en los últimos días (YouTube + Instagram)."""
    from . import investigar
    from . import publicar as pub
    hist = util.leer_json("data/historial.json", [])
    desde = (util.ahora() - util.timedelta(days=dias)).strftime("%Y-%m-%d")
    recientes = [h for h in hist if h.get("fecha", "") >= desde]
    yt_ids = [h["resultados"]["youtube"]["id"] for h in recientes
              if h.get("resultados", {}).get("youtube", {}).get("ok")]
    yt = investigar.estadisticas_youtube(yt_ids, clave_yt) if (clave_yt and yt_ids) else {}
    filas = []
    for h in recientes:
        res = h.get("resultados", {})
        fila = {"fecha": h["fecha"], "hora": h.get("hora", ""), "serie": h["serie"], "titulo": h["titulo"],
                "vistas": 0, "guardados": 0, "compartidos": 0, "comentarios": 0, "likes": 0}
        if res.get("youtube", {}).get("ok"):
            m = yt.get(res["youtube"]["id"], {})
            fila["vistas"] += m.get("vistas", 0)
            fila["likes"] += m.get("likes", 0)
            fila["comentarios"] += m.get("comentarios", 0)
        for red in ("instagram_reel", "instagram_carrusel"):
            if res.get(red, {}).get("ok"):
                m = pub.instagram_metricas(res[red]["id"])
                fila["vistas"] += m.get("views", m.get("reach", 0))
                fila["guardados"] += m.get("saved", 0)
                fila["compartidos"] += m.get("shares", 0)
                fila["comentarios"] += m.get("comments", 0)
                fila["likes"] += m.get("likes", 0)
        filas.append(fila)
    por_serie = {}
    for f in filas:
        nombre = cfg["series"].get(f["serie"], {}).get("nombre", f["serie"])
        a = por_serie.setdefault(nombre, {"posts": 0, "vistas": 0, "guardados": 0, "compartidos": 0,
                                          "comentarios": 0})
        a["posts"] += 1
        for k in ("vistas", "guardados", "compartidos", "comentarios"):
            a[k] += f[k]
    return filas, por_serie


# ---------------------------------------------------------------- horarios
# GitHub no respeta el reloj: en la práctica dispara cada 2 o 3 horas y con atraso. Por eso la fábrica
# arranca con el primer aviso que llega dentro de las 5 horas previas al horario, arma el video y
# espera hasta el minuto exacto para publicar.
ANTICIPO_MAX = 300  # minutos antes del horario en que ya puede arrancar (el trabajo de GitHub dura hasta 6 h)
TARDE_MAX = 180     # si el aviso llega tarde, publica igual hasta 3 horas después del horario
INTENTOS_MAX = 2    # si falla, lo reintenta una vez más ese día (no más, para no llenarte de avisos)


def _clave_intento(fecha, turno):
    return fecha if turno == 1 else f"{fecha}#{turno}"


def _intentos(fecha, turno=1):
    return int((util.leer_json("data/estado.json", {}).get("intentos") or {}).get(_clave_intento(fecha, turno), 0))


def _sumar_intento(turno=1):
    """Anota que el reloj arrancó a fabricar este turno hoy (se guarda aunque la corrida falle)."""
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return
    estado = util.leer_json("data/estado.json", {})
    hoy = util.ahora().strftime("%Y-%m-%d")
    intentos = {k: v for k, v in (estado.get("intentos") or {}).items() if k[:10] >= hoy}  # solo los de hoy
    clave = _clave_intento(hoy, turno)
    intentos[clave] = intentos.get(clave, 0) + 1
    estado["intentos"] = intentos
    util.guardar_json("data/estado.json", estado)


def _objetivo(cfg, momento=None, turno=1):
    momento = momento or util.ahora()
    h = _horarios(cfg, turno).get(str(momento.isoweekday()))
    if not h:
        return None
    hh, mm = (int(x) for x in str(h).split(":")[:2])
    return momento.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _ya_salio(hoy, turno):
    return any(h.get("fecha") == hoy and int(h.get("turno", 1) or 1) == turno
               for h in util.leer_json("data/historial.json", []) or [])


def _toca_turno(cfg, ahora, turno):
    """(sí/no, motivo, horario objetivo) para un turno a esta hora."""
    objetivo = _objetivo(cfg, ahora, turno)
    hoy = ahora.strftime("%Y-%m-%d")
    if objetivo is None:
        return False, "hoy no tiene horario", None
    if _ya_salio(hoy, turno):
        return False, "hoy ya se publicó", objetivo
    from . import revision
    if revision.cancelado(hoy, turno):
        return False, "pediste que hoy no salga", objetivo
    if _intentos(hoy, turno) >= INTENTOS_MAX:
        return False, f"hoy ya se intentó {INTENTOS_MAX} veces y falló; mañana sigue normal", objetivo
    faltan = (objetivo - ahora).total_seconds() / 60
    if 0 < faltan <= ANTICIPO_MAX:
        return True, (f"faltan {faltan:.0f} minutos para las {objetivo:%H:%M}: lo armo ahora y espero "
                      f"hasta esa hora para publicar"), objetivo
    if -TARDE_MAX <= faltan <= 0:
        return True, (f"ya pasaron {-faltan:.0f} minutos de las {objetivo:%H:%M} y no salió "
                      f"(el aviso de GitHub llegó tarde o falló): publico apenas esté listo"), objetivo
    return False, f"faltan {faltan:.0f} minutos para las {objetivo:%H:%M}", objetivo


def toca():
    """Lo usa el reloj de GitHub: ¿hay que fabricar y publicar ahora? ¿Qué turno?
    Si tocan los dos, va primero el de horario más temprano (el otro arranca con el aviso siguiente)."""
    cfg = util.config()
    try:
        turno = 2 if int(os.getenv("TURNO_MANUAL") or 1) == 2 else 1
    except ValueError:
        turno = 1
    si, motivos = True, ["ejecución manual"]
    if os.getenv("GITHUB_EVENT_NAME") == "schedule":
        ahora = util.ahora()
        si, motivos, candidatos = False, [], []
        for t in _turnos(cfg):
            ok, motivo, objetivo = _toca_turno(cfg, ahora, t)
            motivos.append(f"turno {t}: {motivo}")
            if ok:
                candidatos.append((objetivo, t))
        if candidatos:
            si, turno = True, min(candidatos)[1]
            motivos.append(f"→ arranca el turno {turno}")
    util.log("¿Toca publicar?", "sí" if si else "no", "·", " | ".join(motivos))
    salida = os.getenv("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"si={'true' if si else 'false'}\nturno={turno}\n")


def esperar(ultima=False):
    """Espera la hora de publicar mirando cada minuto si mandaste un pedido desde «Revisar video».
    Deja la decisión en out/decision.json y en la salida del paso: publicar, cancelar o cambios."""
    import time
    from . import revision
    cfg = util.config()
    turno = _turno()
    p = util.leer_json("out/publicacion.json", {}) or {}
    desde = max((util.leer_json("out/inicio.json", {}) or {}).get("inicio", ""), p.get("pedido_creado", ""))
    objetivo = _objetivo(cfg, turno=turno)
    decision, pedido = "publicar", {}
    if objetivo and (objetivo - util.ahora()).total_seconds() > 0:
        util.log(f"Video listo. Espero hasta las {objetivo:%H:%M} y mientras miro si pedís cambios.")
        util.avisar("Esperando la hora de publicar",
                    f"El video ya está listo y se mandó por mail para que lo revises. Esta corrida queda en marcha "
                    f"(amarilla) hasta las {objetivo:%H:%M} y ahí publica. Es normal.")
    while True:
        for x in revision.nuevos(revision.leer_remotos(), p.get("fecha", ""), turno, desde):
            desde = x.get("creado", desde)
            if x.get("accion") == "cambios" and ultima:
                util.avisar("Ya no se aceptan más cambios", "Este video ya se rehízo dos veces: sale esta versión.")
                continue
            decision, pedido = x.get("accion", "publicar"), x
            break
        if pedido:
            break
        if not objetivo or (objetivo - util.ahora()).total_seconds() <= 0:
            break
        time.sleep(min(60, max(1, (objetivo - util.ahora()).total_seconds())))
    util.log("Decisión:", decision, pedido.get("cambios", ""))
    util.guardar_json("out/decision.json", {"decision": decision, "pedido": pedido})
    util.guardar_json("out/pedido.json", pedido)
    salida = os.getenv("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"decision={decision}\n")


def online(base_url):
    """Espera a que el video nuevo se pueda ver en la página (Instagram lo baja de ahí)."""
    import time
    p = util.leer_json("out/publicacion.json")
    url = base_url.rstrip("/") + "/" + p["archivos"]["video"]
    for _ in range(36):
        try:
            r = util.pedir("HEAD", url, intentos=1, timeout=30)
            if r is not None and r.status_code == 200:
                util.log("Online:", url)
                return
        except Exception:  # noqa
            pass
        time.sleep(10)
    raise RuntimeError("Los archivos no aparecieron online: " + url)


def listo(base_url):
    """Te manda el video apenas está listo, con la hora a la que sale y cómo pedir cambios."""
    from . import publicar as pub
    from . import revision
    e = html.escape
    cfg = util.config()
    p = util.leer_json("out/publicacion.json")
    base = base_url.rstrip("/") + "/"
    objetivo = _objetivo(cfg, turno=_turno())
    cuando = (f"hoy a las {objetivo:%H:%M}" if objetivo and objetivo > util.ahora()
              else "en unos minutos (ya es la hora)")
    v = p.get("version", 1)
    version = f" · versión {v} con tus cambios" if v > 1 else ""
    link = revision.link_formulario()
    cuerpo = (f'<h2>{e(p["serie_nombre"])}: {e(p["titulo"])}</h2>'
              f'<p><b>Sale {cuando}</b> en Instagram, YouTube y Facebook{version}. '
              f'Si no hacés nada, se publica solo.</p>'
              f'<p><a href="{base}{p["archivos"]["video"]}">▶️ Ver el video</a> · '
              f'<a href="{base}{p["archivos"]["portada"]}">Portada</a></p>'
              f'<p><b>¿Querés cambiar algo?</b> Entrá a <a href="{link}">Revisar video</a> → <b>Run workflow</b>, '
              f'elegí qué hacer (pedir cambios, publicar ya o no publicar hoy), escribí qué cambiar y tocá '
              f'<b>Run workflow</b>. En unos 10 minutos te llega la versión nueva.</p>'
              f'<p><b>Texto:</b><br>{e(p["caption"]).replace(chr(10), "<br>")}</p>'
              f'<hr><p style="color:#666"><b>Guion:</b> {e(p["guion"])}</p>'
              f'<p style="color:#666">Al subirlo a TikTok, activá «Contenido generado por IA» en Más opciones.</p>')
    try:
        segundo = " (2º del día)" if p.get("turno", 1) == 2 else ""
        pub.mail(f'Listo para revisar{segundo}: {p["titulo"]}', cuerpo)
    except Exception as ex:  # noqa
        util.log("No pude mandar el mail:", ex)


def revisar():
    """Lo usa el formulario «Revisar video»: anota tu pedido para la corrida que está esperando."""
    from . import revision
    destino = os.getenv("GITHUB_STEP_SUMMARY")
    try:
        x = revision.registrar(os.getenv("ACCION", ""), os.getenv("TURNO_PEDIDO", ""), os.getenv("CAMBIOS", ""))
        texto = {"cambios": "Listo: la fábrica rehace el video con tus cambios y te manda la versión nueva por mail "
                            "en unos 10 minutos. Si para entonces ya pasó la hora, se publica apenas esté.",
                 "publicar": "Listo: se publica en el próximo minuto.",
                 "cancelar": "Listo: hoy no se publica. Te llega un mail con el link por si lo querés subir a mano."}
        msg = texto[x["accion"]]
    except ValueError as e:
        msg = f"❌ {e}"
        if destino:
            open(destino, "a", encoding="utf-8").write(f"## Revisar video\n\n{msg}\n")
        util.log(msg)
        sys.exit(1)
    util.log(msg)
    if destino:
        open(destino, "a", encoding="utf-8").write(f"## Revisar video\n\n{msg}\n")


def reporte():
    from . import escritor, investigar
    from . import publicar as pub
    cfg = util.config()
    clave = util.secreto("YT_API_KEY")
    if not clave:
        util.log("Sin YT_API_KEY no hay reporte")
        return
    cache = util.leer_json("data/canales.json", {})
    vistos, filas = set(), []
    ref = cfg.get("referentes_contables", {})
    for s in list(cfg["series"].values()) + [{"canales": ref.get("youtube", [])}]:
        for b in s.get("canales", []):
            if b.lower() in vistos:
                continue
            vistos.add(b.lower())
            m = investigar.metricas_canal(b, clave, cache)
            if m:
                filas.append(m)
    util.guardar_json("data/canales.json", cache)
    propias, por_serie = _rendimiento(cfg, clave)
    nuestro = "\n".join(
        f'- {serie}: {a["posts"]} publicaciones, {a["vistas"] // max(a["posts"], 1)} vistas promedio, '
        f'{a["guardados"]} guardados, {a["compartidos"]} compartidos, {a["comentarios"]} comentarios'
        for serie, a in sorted(por_serie.items(), key=lambda x: -x[1]["vistas"] / max(x[1]["posts"], 1)))
    mejores = sorted(propias, key=lambda f: -f["vistas"])[:3]
    peores = sorted(propias, key=lambda f: f["vistas"])[:3]
    resumen = "\n\n".join(
        f'CANAL {f["canal"]} | {f["videos_por_semana"]} videos/semana | vistas típicas {f["mediana"]} | '
        f'{f["pct_shorts"]}% Shorts\n' + "\n".join(
            f'  - "{t["titulo"]}" ({t["vistas"]} vistas, {t["veces"]} veces lo normal)' for t in f["top"])
        for f in filas)
    try:
        from . import contable
        ig = contable.resumen_instagram(ref.get("instagram", []))
        if ig:
            resumen += "\n\n" + ig
    except Exception as ex:  # noqa
        util.log("No pude leer el Instagram de los referentes:", util.ocultar(ex))
    sistema = ("Sos analista de contenido de una cuenta argentina sin cara de Shorts, Reels y TikTok sobre plata, "
               "economía, libros de dinero e impuestos. Respondé en español rioplatense natural.")
    pedido = ("Con estas métricas de canales de referencia, devolvé un JSON con: "
              '{"patrones": ["..."], "formatos_que_rinden": ["..."], "estructuras_virales": ["..."], '
              '"ideas": [{"serie": "...", "titulo": "...", "miniatura": "..."}]} '
              "con 5 patrones, 5 formatos, 5 estructuras y 10 ideas originales adaptadas a Argentina para nuestras "
              "series (" + ", ".join(s["nombre"] for s in cfg["series"].values()) + "). "
              'Además sumá "series_reforzar": ["..."] y "series_cambiar": [{"serie": "...", "por_que": "...", '
              '"propuesta": "..."}] mirando NUESTRO RENDIMIENTO (si todavía hay pocos datos, decilo).\n\n'
              "NUESTRO RENDIMIENTO (últimos 30 días, por serie):\n" + (nuestro or "(todavía sin datos)") +
              "\n\nCOMPETENCIA:\n" + resumen)
    try:
        a = escritor.gemini(sistema, pedido, temperatura=0.7)
    except Exception as ex:  # noqa
        a = {"patrones": [f"No se pudo analizar: {ex}"]}
    fecha = util.ahora().strftime("%Y-%m-%d")
    md = [f"# Reporte de competencia · {fecha}", "", "| Canal | Videos/semana | Vistas típicas | % Shorts |",
          "|---|---|---|---|"]
    md += [f'| {f["canal"]} | {f["videos_por_semana"]} | {f["mediana"]:,} | {f["pct_shorts"]}% |' for f in filas]
    for titulo, clave_a in [("Patrones", "patrones"), ("Formatos que rinden", "formatos_que_rinden"),
                            ("Estructuras virales", "estructuras_virales")]:
        md += ["", f"## {titulo}", ""] + [f"- {x}" for x in a.get(clave_a, [])]
    md += ["", "## Cómo nos fue (últimos 30 días)", ""]
    if por_serie:
        md += ["| Serie | Publicaciones | Vistas promedio | Guardados | Compartidos | Comentarios |",
               "|---|---|---|---|---|---|"]
        md += [f'| {k} | {a["posts"]} | {a["vistas"] // max(a["posts"], 1):,} | {a["guardados"]} | '
               f'{a["compartidos"]} | {a["comentarios"]} |'
               for k, a in sorted(por_serie.items(), key=lambda x: -x[1]["vistas"] / max(x[1]["posts"], 1))]
        md += ["", "Lo que mejor anduvo: " + "; ".join(f'{f["titulo"]} ({f["vistas"]:,})' for f in mejores),
               "", "Lo que peor anduvo: " + "; ".join(f'{f["titulo"]} ({f["vistas"]:,})' for f in peores)]
    else:
        md += ["Todavía no hay publicaciones para medir."]
    horas = {}
    for f in propias:
        if f.get("hora"):
            franja = f["hora"][:2] + " h"
            x = horas.setdefault(franja, {"posts": 0, "vistas": 0})
            x["posts"] += 1
            x["vistas"] += f["vistas"]
    if horas:
        md += ["", "## Por horario de publicación", "", "| Franja | Publicaciones | Vistas promedio |", "|---|---|---|"]
        md += [f'| {k} | {v["posts"]} | {v["vistas"] // max(v["posts"], 1):,} |' for k, v in
               sorted(horas.items(), key=lambda x: -x[1]["vistas"] / max(x[1]["posts"], 1))]
    md += ["", "## Qué reforzar y qué cambiar", ""]
    md += [f"- Reforzar: {x}" for x in a.get("series_reforzar", [])]
    md += [f'- Cambiar **{x.get("serie", "")}**: {x.get("por_que", "")} → {x.get("propuesta", "")}'
           for x in a.get("series_cambiar", []) if isinstance(x, dict)]
    md += ["", "## Ideas para las próximas semanas", ""]
    md += [f'- **{i.get("serie", "")}**: {i.get("titulo", "")} · miniatura: "{i.get("miniatura", "")}"'
           for i in a.get("ideas", [])]
    md += ["", "## Lo que más rindió en cada canal", "", resumen]
    ruta = util.RAIZ / "reportes" / f"{fecha}.md"
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text("\n".join(md) + "\n", encoding="utf-8")
    try:
        pub.mail(f"Reporte semanal de competencia · {fecha}",
                 "<pre style='font-family:Arial;white-space:pre-wrap'>" + html.escape("\n".join(md)) + "</pre>")
    except Exception as ex:  # noqa
        util.log("No pude mandar el mail:", ex)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["generar", "publicar", "resumen", "reporte", "toca", "esperar", "probar",
                                       "rehacer", "listo", "revisar", "online"])
    ap.add_argument("--ultima", action="store_true")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--simulado", action="store_true")
    a = ap.parse_args()
    try:
        if a.accion == "toca":
            toca()
        elif a.accion == "esperar":
            esperar(a.ultima)
        elif a.accion == "rehacer":
            rehacer()
        elif a.accion == "listo":
            listo(a.base_url)
        elif a.accion == "online":
            online(a.base_url)
        elif a.accion == "revisar":
            revisar()
        elif a.accion == "generar":
            generar(a.simulado)
        elif a.accion == "publicar":
            publicar(a.base_url)
        elif a.accion == "resumen":
            resumen(a.base_url)
        elif a.accion == "probar":
            from . import probar
            probar.probar()
        else:
            reporte()
    except Exception as error:  # noqa
        import traceback
        print(util.ocultar(traceback.format_exc()), flush=True)
        util.avisar_error(a.accion, error)
        sys.exit(1)
