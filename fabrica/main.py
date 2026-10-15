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


def _serie_del_dia(cfg):
    forzada = (os.getenv("SERIE") or "").strip().lower()
    if forzada in cfg["series"]:
        return forzada
    return cfg["plan_semanal"][str(util.ahora().isoweekday())]


def generar(simulado=False):
    cfg = util.config()
    os.environ.setdefault("TTS_VOICE", cfg.get("voz", "es-AR-TomasNeural"))
    os.environ.setdefault("TTS_RATE", str(cfg.get("voz_velocidad", "+15%")))
    os.environ.setdefault("TTS_MAX_PAUSA", str(cfg.get("voz_pausa_maxima", 0.28)))
    from . import carrusel, escritor, investigar, montaje  # importa después de fijar la voz

    if not simulado:
        _sumar_intento()
    clave_serie = _serie_del_dia(cfg)
    serie = cfg["series"][clave_serie]
    fecha = util.ahora().strftime("%Y-%m-%d")
    util.log("Serie de hoy:", serie["nombre"])

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
                fuentes = investigar.fuera_de_serie(serie["canales"], clave_yt, usados,
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

    carpeta = SITIO / fecha
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    carpeta.mkdir(parents=True)
    placas = carrusel.generar(contenido, serie["nombre"], cfg["usuario"], carpeta)
    video_path, thumb_path = montaje.generar(contenido, serie["nombre"], cfg["usuario"], carpeta)
    shutil.rmtree(carpeta / "_trabajo", ignore_errors=True)
    (carpeta / "spec.json").unlink(missing_ok=True)
    meta_video = util.leer_json(str((carpeta / "meta.json").relative_to(util.RAIZ)), {}) or {}
    (carpeta / "meta.json").unlink(missing_ok=True)
    (SITIO / "index.html").write_text("<meta charset='utf-8'><p>Fábrica de Shorts</p>", encoding="utf-8")

    firma = cfg.get("firma", "")
    if serie.get("modo") == "virales" and fuentes:
        firma = ("Inspirado en videos virales de " +
                 ", ".join(f'{f["canal"]} ({f["pais"]})' for f in fuentes) + ".\n" + firma)
    if meta_video.get("clips_stock"):
        firma = firma + f'\nVideos de stock: {meta_video.get("banco")}.'
    tags = " ".join(contenido["hashtags"])
    publicacion = {
        "fecha": fecha,
        "serie": clave_serie,
        "serie_nombre": serie["nombre"],
        "titulo": contenido["titulo"],
        "caption": f'{contenido["titulo"]}\n\n{contenido["descripcion"]}\n\n{firma}\n\n{tags}'.strip(),
        "descripcion_youtube": f'{contenido["descripcion"]}\n\n{firma}\n\n{tags} #shorts'.strip(),
        "tags": [t.lstrip("#") for t in contenido["hashtags"]],
        "guion": " ".join(e["texto_voz"] for e in contenido["escenas"]),
        "fuentes": [f["id"] for f in fuentes],
        "fuentes_detalle": [{"canal": f["canal"], "titulo": f["titulo"], "score": f.get("score") or f.get("pais", "")}
                            for f in fuentes],
        "archivos": {"video": f"{fecha}/video.mp4", "portada": f"{fecha}/thumb.jpg",
                     "placas": [f"{fecha}/{p.name}" for p in placas]},
        "contenido": contenido,
        "video": meta_video,
    }
    util.guardar_json("out/publicacion.json", publicacion)
    util.log("Listo:", contenido["titulo"])


def publicar(base_url):
    from . import publicar as pub
    cfg = util.config()
    p = util.leer_json("out/publicacion.json")
    base = base_url.rstrip("/") + "/"
    url = lambda rel: base + rel  # noqa
    video_local = SITIO / p["archivos"]["video"]
    hoy_carrusel = util.ahora().isoweekday() in cfg.get("carrusel_dias", [])
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
    historial.append({"fecha": p["fecha"], "hora": util.ahora().strftime("%H:%M"), "serie": p["serie"],
                      "titulo": p["titulo"], "fuentes": p["fuentes"], "resultados": resultados})
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
    ruta = util.RAIZ / "publicaciones" / f'{p["fecha"]}.md'
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
              f'<a href="{base}{p["archivos"]["placas"][0]}">Carrusel</a> (los links duran hasta mañana)</p>'
              f'<p><b>Texto:</b><br>{e(p["caption"]).replace(chr(10), "<br>")}</p>'
              f'<hr><p style="color:#666">{e(p["guion"])}</p>')
    try:
        pub.mail(f'Short del día: {p["titulo"]}', cuerpo)
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
VENTANA = (30, 60)  # se arranca entre 60 y 30 minutos antes del horario (el reloj corre cada 30 min)
TARDE_MAX = 180     # si el reloj de GitHub se atrasa, publica igual hasta 3 horas después del horario
INTENTOS_MAX = 2    # si falla, lo reintenta una vez más ese día (no más, para no llenarte de avisos)


def _intentos(fecha):
    return int((util.leer_json("data/estado.json", {}).get("intentos") or {}).get(fecha, 0))


def _sumar_intento():
    """Anota que el reloj arrancó a fabricar hoy (se guarda aunque la corrida falle)."""
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return
    estado = util.leer_json("data/estado.json", {})
    hoy = util.ahora().strftime("%Y-%m-%d")
    intentos = {k: v for k, v in (estado.get("intentos") or {}).items() if k >= hoy}  # solo el de hoy
    intentos[hoy] = intentos.get(hoy, 0) + 1
    estado["intentos"] = intentos
    util.guardar_json("data/estado.json", estado)


def _objetivo(cfg, momento=None):
    momento = momento or util.ahora()
    h = (cfg.get("horarios") or {}).get(str(momento.isoweekday()))
    if not h:
        return None
    hh, mm = (int(x) for x in str(h).split(":")[:2])
    return momento.replace(hour=hh, minute=mm, second=0, microsecond=0)


def toca():
    """Lo usa el reloj de GitHub cada 30 minutos: ¿hay que fabricar y publicar ahora?"""
    cfg = util.config()
    si, motivo = True, "ejecución manual"
    if os.getenv("GITHUB_EVENT_NAME") == "schedule":
        ahora = util.ahora()
        objetivo = _objetivo(cfg, ahora)
        hoy = ahora.strftime("%Y-%m-%d")
        if objetivo is None:
            si, motivo = False, "hoy no tiene horario"
        elif any(h.get("fecha") == hoy for h in util.leer_json("data/historial.json", [])):
            si, motivo = False, "hoy ya se publicó"
        elif _intentos(hoy) >= INTENTOS_MAX:
            si, motivo = False, f"hoy ya se intentó {INTENTOS_MAX} veces y falló; mañana sigue normal"
        else:
            faltan = (objetivo - ahora).total_seconds() / 60
            if VENTANA[0] <= faltan < VENTANA[1]:
                si, motivo = True, f"faltan {faltan:.0f} minutos para las {objetivo:%H:%M}"
            elif -TARDE_MAX <= faltan <= 0:
                si = True
                motivo = (f"ya pasaron {-faltan:.0f} minutos de las {objetivo:%H:%M} y hoy no salió nada "
                          f"(el reloj se atrasó o falló): publico apenas esté listo")
            else:
                si, motivo = False, f"faltan {faltan:.0f} minutos para las {objetivo:%H:%M}"
    util.log("¿Toca publicar?", "sí" if si else "no", "·", motivo)
    salida = os.getenv("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"si={'true' if si else 'false'}\n")


def esperar():
    """Con el video listo, espera al minuto exacto del horario antes de publicar."""
    import time
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return
    objetivo = _objetivo(util.config())
    if not objetivo:
        return
    segundos = (objetivo - util.ahora()).total_seconds()
    if 0 < segundos < 70 * 60:
        util.log(f"Video listo. Espero {segundos / 60:.0f} minutos para publicar a las {objetivo:%H:%M}.")
        time.sleep(segundos)


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
    ap.add_argument("accion", choices=["generar", "publicar", "resumen", "reporte", "toca", "esperar"])
    ap.add_argument("--base-url", default="")
    ap.add_argument("--simulado", action="store_true")
    a = ap.parse_args()
    try:
        if a.accion == "toca":
            toca()
        elif a.accion == "esperar":
            esperar()
        elif a.accion == "generar":
            generar(a.simulado)
        elif a.accion == "publicar":
            publicar(a.base_url)
        elif a.accion == "resumen":
            resumen(a.base_url)
        else:
            reporte()
    except Exception as error:  # noqa
        import traceback
        print(util.ocultar(traceback.format_exc()), flush=True)
        util.avisar_error(a.accion, error)
        sys.exit(1)
