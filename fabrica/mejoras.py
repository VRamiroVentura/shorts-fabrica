"""Mejora continua de la fábrica.

Todos los días la fábrica mira cómo le fue a cada serie (estilo de video) y te manda UNA sugerencia de cambio por mail.
Respondés con el formulario «Responder sugerencia» (sugerencia.yml): aplicarla, no aplicarla, aplicarla con cambios o
deshacer el último cambio. Si no respondés, se aplica sola a los N días (mejoras_dias_para_aplicar, 2 por defecto).

Los cambios aprobados quedan en data/ajustes.json (util.config los suma encima de config.json y turnos.json), así se
pueden deshacer y nunca se pisa lo que editaste a mano. Solo se permiten estos tipos de cambio, validados por código:
  cambiar_serie_dia · cambiar_horario · ajustar_prompt_serie · nueva_serie · carrusel_siempre
"""
import json
import os
import re

from . import util

PROPUESTAS = "data/propuestas.json"
AJUSTES = "data/ajustes.json"
APRENDIZAJES = "data/aprendizajes.json"
DIAS = {"1": "lunes", "2": "martes", "3": "miércoles", "4": "jueves", "5": "viernes", "6": "sábado", "7": "domingo"}
RESPUESTAS = {"Sí, aplicala": "si", "No, dejala": "no", "Aplicala con cambios": "cambios",
              "Deshacer el último cambio": "deshacer"}
TIPOS = ("cambiar_serie_dia", "cambiar_horario", "ajustar_prompt_serie", "nueva_serie", "carrusel_siempre",
         "deshacer_cambio")


# ------------------------------------------------------------------ datos
def _leer():
    d = util.leer_json(PROPUESTAS, {}) or {}
    d.setdefault("proximo_id", 1)
    d.setdefault("lista", [])
    return d


def _guardar(d):
    d["lista"] = d["lista"][-200:]
    util.guardar_json(PROPUESTAS, d)


def ajustes():
    return util.leer_json(AJUSTES, {}) or {}


def _hoy():
    return util.ahora().strftime("%Y-%m-%d")


def _sumar_dias(fecha, n):
    return (util.datetime.strptime(fecha, "%Y-%m-%d") + util.timedelta(days=n)).strftime("%Y-%m-%d")


def _fecha_linda(fecha):
    f = util.datetime.strptime(fecha, "%Y-%m-%d")
    return f'{DIAS[str(f.isoweekday())]} {f:%d/%m}'


def dias_para_aplicar(cfg):
    return max(1, int(cfg.get("mejoras_dias_para_aplicar", 2)))


def link_formulario():
    repo = os.getenv("GITHUB_REPOSITORY", "")
    return f"https://github.com/{repo}/actions/workflows/sugerencia.yml" if repo else ""


def _plan_key(turno):
    return "plan_semanal" if int(turno) == 1 else "plan_semanal_2"


def _hora_key(turno):
    return "horarios" if int(turno) == 1 else "horarios_2"


def _nombre(cfg, clave):
    return (cfg["series"].get(clave) or {}).get("nombre", clave)


def grilla(cfg):
    lineas = []
    for d in map(str, range(1, 8)):
        partes = []
        for t in (1, 2):
            s, h = (cfg.get(_plan_key(t)) or {}).get(d), (cfg.get(_hora_key(t)) or {}).get(d)
            if s and h and (t == 1 or cfg.get("segundo_turno")):
                partes.append(f"turno {t} {h} «{_nombre(cfg, s)}» ({s})")
        lineas.append(f"- {DIAS[d]} ({d}): " + " · ".join(partes))
    return "\n".join(lineas)


# ------------------------------------------------------------------ validar y aplicar
def _minutos(h):
    hh, mm = (int(x) for x in str(h).split(":")[:2])
    return hh * 60 + mm


def _posts_por_serie(propias):
    cuenta = {}
    for f in propias or []:
        cuenta[f.get("serie")] = cuenta.get(f.get("serie"), 0) + 1
    return cuenta


def _ultimo_cambio(lista, clave_cosa):
    fechas = [p.get("aplicada_el", "") for p in lista if p.get("estado") == "aplicada" and _cosa(p) == clave_cosa]
    return max(fechas) if fechas else ""


def _cosa(p):
    """Qué toca un cambio (para no tocar lo mismo dos veces seguidas)."""
    x = p.get("params") or {}
    if p["tipo"] == "deshacer_cambio":
        return f'deshacer:{x.get("id")}'
    if p["tipo"] in ("cambiar_serie_dia", "nueva_serie", "cambiar_horario"):
        return f'{p["tipo"] != "cambiar_horario" and "serie" or "hora"}:{x.get("turno")}:{x.get("dia")}'
    return f'{p["tipo"]}:{x.get("serie")}'


def validar(cfg, p, posts=None, lista=None):
    """(ok, motivo). Normaliza los parámetros de la propuesta."""
    tipo, x = p.get("tipo"), dict(p.get("params") or {})
    if tipo not in TIPOS:
        return False, f"tipo desconocido: {tipo}"
    if tipo == "deshacer_cambio":
        objetivo = next((q for q in (lista or []) if str(q.get("id")) == str(x.get("id"))), None)
        if not objetivo or objetivo.get("estado") != "aplicada":
            return False, "ese cambio no está aplicado"
        x["id"] = objetivo["id"]
        p["params"] = x
        return True, ""
    protegidas = set(cfg.get("series_protegidas", ["monotributo"]))
    minimo = int(cfg.get("mejoras_min_posts", 3))
    enfriar = int(cfg.get("mejoras_dias_entre_cambios", 7))
    if tipo in ("cambiar_serie_dia", "nueva_serie", "cambiar_horario"):
        x["turno"], x["dia"] = int(x.get("turno", 1)), str(x.get("dia", ""))
        if x["turno"] not in (1, 2) or x["dia"] not in DIAS:
            return False, "turno o día inválido"
        if x["turno"] == 2 and not cfg.get("segundo_turno"):
            return False, "no hay segundo turno"
    if tipo in ("cambiar_serie_dia", "nueva_serie"):
        plan = dict(cfg.get(_plan_key(x["turno"])) or {})
        actual = plan.get(x["dia"])
        if tipo == "nueva_serie":
            x["clave"] = re.sub(r"[^a-z0-9_]", "", str(x.get("clave", "")).lower())[:30]
            x["nombre"] = str(x.get("nombre", "")).strip()[:40]
            x["prompt"] = str(x.get("prompt", "")).strip()
            if not x["clave"] or x["clave"] in cfg["series"]:
                return False, "clave de serie vacía o ya existente"
            if not x["nombre"] or not (300 <= len(x["prompt"]) <= 4000):
                return False, "falta el nombre o el prompt de la serie nueva es muy corto o muy largo"
            nueva = x["clave"]
        else:
            nueva = str(x.get("serie", ""))
            if nueva not in cfg["series"]:
                return False, f"la serie {nueva} no existe"
            if nueva == actual:
                return False, "ya está esa serie"
        if actual and posts is not None and posts.get(actual, 0) < minimo:
            return False, f"«{_nombre(cfg, actual)}» tiene menos de {minimo} videos: todavía no se puede juzgar"
        if actual in protegidas:
            planes = list((cfg.get("plan_semanal") or {}).items()) + list((cfg.get("plan_semanal_2") or {}).items())
            if sum(1 for _, s in planes if s == actual) <= 1:
                return False, f"«{_nombre(cfg, actual)}» es una serie protegida y es su último día"
        x["antes"] = actual
    if tipo == "cambiar_horario":
        h = str(x.get("hora", ""))
        if not re.fullmatch(r"\d{1,2}:\d{2}", h) or not (_minutos("12:10") <= _minutos(h) <= _minutos("22:30")):
            return False, "el horario tiene que estar entre las 12:10 y las 22:30"
        x["hora"] = f'{int(h.split(":")[0]):02d}:{h.split(":")[1]}'
        otro = (cfg.get(_hora_key(3 - x["turno"])) or {}).get(x["dia"])
        if otro and cfg.get("segundo_turno") and abs(_minutos(otro) - _minutos(x["hora"])) < 240:
            return False, "tiene que quedar a 4 horas o más del otro video de ese día"
        x["antes"] = (cfg.get(_hora_key(x["turno"])) or {}).get(x["dia"])
        if x["antes"] == x["hora"]:
            return False, "ya está en ese horario"
    if tipo in ("ajustar_prompt_serie", "carrusel_siempre"):
        if str(x.get("serie", "")) not in cfg["series"]:
            return False, f'la serie {x.get("serie")} no existe'
    if tipo == "ajustar_prompt_serie":
        x["texto"] = " ".join(str(x.get("texto", "")).split())
        if not (20 <= len(x["texto"]) <= 600):
            return False, "el ajuste tiene que tener entre 20 y 600 caracteres"
    if tipo == "carrusel_siempre":
        x["activar"] = bool(x.get("activar", True))
        actuales = list(cfg.get("carrusel_series", ["monotributo"]))
        if (x["serie"] in actuales) == x["activar"]:
            return False, "ya está así"
    if lista is not None:
        ultima = _ultimo_cambio(lista, _cosa({"tipo": tipo, "params": x}))
        if ultima and ultima > _sumar_dias(_hoy(), -enfriar):
            return False, f"eso se cambió hace menos de {enfriar} días: hay que esperar a ver cómo anda"
    p["params"] = x
    return True, ""


def describir(cfg, p):
    x = p.get("params") or {}
    t = p["tipo"]
    if t == "cambiar_serie_dia":
        return (f'Los {DIAS[x["dia"]]} (turno {x["turno"]}): «{_nombre(cfg, x.get("antes"))}» → '
                f'«{_nombre(cfg, x["serie"])}».')
    if t == "nueva_serie":
        return (f'Serie nueva «{x["nombre"]}», los {DIAS[x["dia"]]} (turno {x["turno"]}) en lugar de '
                f'«{_nombre(cfg, x.get("antes"))}».')
    if t == "cambiar_horario":
        return f'Los {DIAS[x["dia"]]}, el turno {x["turno"]} pasa de las {x.get("antes")} a las {x["hora"]}.'
    if t == "ajustar_prompt_serie":
        return f'En «{_nombre(cfg, x["serie"])}» se suma esta instrucción: «{x["texto"]}»'
    if t == "deshacer_cambio":
        return f'Volver atrás el cambio #{x["id"]}, porque no está funcionando.'
    if t == "carrusel_siempre":
        return (f'«{_nombre(cfg, x["serie"])}» ' + ("sale siempre también como carrusel en Instagram."
                                                   if x["activar"] else "deja de salir siempre como carrusel."))
    return t


def aplicar(cfg, p, lista=None):
    if p["tipo"] == "deshacer_cambio":
        objetivo = next(q for q in (lista or []) if q.get("id") == p["params"]["id"])
        deshacer(objetivo)
        objetivo.update({"estado": "deshecha", "deshecha_el": _hoy(), "por": f'#{p["id"]}'})
        return
    aj = ajustes()
    x = p["params"]
    t = p["tipo"]
    if t in ("cambiar_serie_dia", "nueva_serie"):
        if t == "nueva_serie":
            aj.setdefault("series_nuevas", {})[x["clave"]] = {"nombre": x["nombre"], "prompt": x["prompt"],
                                                              "palabras_max": 160, "canales": []}
            aj.setdefault(_plan_key(x["turno"]), {})[x["dia"]] = x["clave"]
        else:
            aj.setdefault(_plan_key(x["turno"]), {})[x["dia"]] = x["serie"]
    elif t == "cambiar_horario":
        aj.setdefault(_hora_key(x["turno"]), {})[x["dia"]] = x["hora"]
    elif t == "ajustar_prompt_serie":
        extra = aj.setdefault("prompts_extra", {}).setdefault(x["serie"], [])
        extra.append(x["texto"])
        aj["prompts_extra"][x["serie"]] = extra[-5:]
    elif t == "carrusel_siempre":
        actuales = list(cfg.get("carrusel_series", ["monotributo"]))
        x["antes_lista"] = actuales
        aj["carrusel_series"] = (actuales + [x["serie"]]) if x["activar"] else [s for s in actuales if s != x["serie"]]
    util.guardar_json(AJUSTES, aj)


def deshacer(p):
    aj = ajustes()
    x = p["params"]
    t = p["tipo"]
    if t in ("cambiar_serie_dia", "nueva_serie"):
        aj.setdefault(_plan_key(x["turno"]), {})[x["dia"]] = x.get("antes")
    elif t == "cambiar_horario":
        aj.setdefault(_hora_key(x["turno"]), {})[x["dia"]] = x.get("antes")
    elif t == "ajustar_prompt_serie":
        extra = (aj.get("prompts_extra") or {}).get(x["serie"], [])
        if x["texto"] in extra:
            extra.remove(x["texto"])
    elif t == "carrusel_siempre":
        aj["carrusel_series"] = x.get("antes_lista", ["monotributo"])
    util.guardar_json(AJUSTES, aj)


# ------------------------------------------------------------------ ¿los cambios funcionaron?
def _dia_semana(fecha):
    return str(util.datetime.strptime(fecha, "%Y-%m-%d").isoweekday())


def _prom(filas):
    return (sum(f["vistas"] for f in filas) // len(filas)) if filas else 0


def balance(cfg, propias, lista):
    """Para cada cambio aplicado: vistas promedio antes y después (videos con 2 días o más)."""
    salida = []
    for p in lista:
        if p.get("estado") != "aplicada" or p["tipo"] == "deshacer_cambio":
            continue
        x, desde = p["params"], p.get("aplicada_el", "")
        if p["tipo"] in ("cambiar_serie_dia", "nueva_serie"):
            nueva = x.get("serie") or x.get("clave")
            antes = [f for f in propias if f["serie"] == x.get("antes") and f["fecha"] < desde]
            despues = [f for f in propias if f["serie"] == nueva and f["fecha"] >= desde]
        elif p["tipo"] == "cambiar_horario":
            mismo = [f for f in propias
                     if _dia_semana(f["fecha"]) == x["dia"] and int(f.get("turno", 1)) == int(x["turno"])]
            antes = [f for f in mismo if f["fecha"] < desde]
            despues = [f for f in mismo if f["fecha"] >= desde]
        else:
            antes = [f for f in propias if f["serie"] == x["serie"] and f["fecha"] < desde]
            despues = [f for f in propias if f["serie"] == x["serie"] and f["fecha"] >= desde]
        a, d = _prom(antes), _prom(despues)
        if not despues:
            veredicto = "todavía sin videos de 2 días o más para medir"
        elif not antes:
            veredicto = f"después: {d} vistas promedio ({len(despues)} videos), sin datos de antes para comparar"
        else:
            cambio = "mejoró" if d > a * 1.15 else ("empeoró" if d < a * 0.85 else "quedó igual")
            veredicto = (f"antes {a} vistas promedio ({len(antes)} videos) → después {d} ({len(despues)} videos): "
                         f"{cambio}")
        p["balance"] = veredicto
        salida.append(f'#{p["id"]} (aplicado el {p.get("aplicada_el")}) {p["titulo"]}: {veredicto}')
    return salida


# ------------------------------------------------------------------ proponer
def _pedido(cfg, por_serie, propias, horas, analisis, historia, balance_txt=""):
    lineas_serie = "\n".join(
        f'- {k}: {a["posts"]} videos, {a["vistas"] // max(a["posts"], 1)} vistas promedio, {a["guardados"]} guardados, '
        f'{a["compartidos"]} compartidos, {a["comentarios"]} comentarios'
        for k, a in sorted(por_serie.items(), key=lambda kv: -kv[1]["vistas"] / max(kv[1]["posts"], 1)))
    titulos = "\n".join(f'- [{f["serie"]}] {f["fecha"]} {f.get("hora", "")} «{f["titulo"]}»: {f["vistas"]} vistas, '
                        f'{f.get("guardados", 0)} guardados' for f in sorted(propias, key=lambda f: -f["vistas"]))
    franjas = "\n".join(f'- {k}: {v["posts"]} videos, {v["vistas"] // max(v["posts"], 1)} vistas promedio'
                        for k, v in sorted(horas.items()))
    series = "\n".join(f'- {k}: «{v.get("nombre", k)}»' for k, v in cfg["series"].items())
    comp = "\n".join(f"- {x}" for k in ("patrones", "formatos_que_rinden", "estructuras_virales")
                     for x in (analisis or {}).get(k, [])[:5])
    return (
        "Sos el responsable de mejorar una fábrica automática de videos cortos sin cara (Reels, Shorts, TikTok) de una "
        "cuenta argentina de plata, economía, impuestos e historias. Mirá cómo le va a cada serie (cada estilo de video) "
        "y proponé cambios concretos que suban las vistas, los guardados y los compartidos.\n\n"
        "TIPOS DE CAMBIO PERMITIDOS (usá exactamente estos y estos parámetros):\n"
        '- cambiar_serie_dia: {"turno": 1|2, "dia": "1".."7", "serie": "<clave existente>"}\n'
        '- cambiar_horario: {"turno": 1|2, "dia": "1".."7", "hora": "HH:MM"} (entre 12:10 y 22:30, a 4 horas o más '
        "del otro video de ese día)\n"
        '- ajustar_prompt_serie: {"serie": "<clave>", "texto": "<instrucción concreta de 1 a 3 frases>"} (gancho, '
        "enfoque, largo, tipo de tema; basada en lo que funcionó)\n"
        '- nueva_serie: {"clave": "<minúsculas_sin_espacios>", "nombre": "<máx 40>", "turno": 1|2, "dia": "1".."7", '
        '"prompt": "<instrucciones completas de la serie, 600 a 2500 caracteres, con el mismo estilo que una serie '
        'existente: qué es, escena 1, escenas 2 y 3, desarrollo, giro, cierre, reglas de precisión y hashtags>"}\n'
        '- carrusel_siempre: {"serie": "<clave>", "activar": true|false}\n'
        '- deshacer_cambio: {"id": <número de un cambio aplicado>} (solo si el BALANCE dice que empeoró con 2 '
        "videos o más después)\n\n"
        "REGLAS:\n"
        "- Entre 3 y 5 propuestas, ordenadas de mayor a menor impacto esperado. Un solo cambio por propuesta.\n"
        "- Cada «por_que» cita números de NUESTRO RENDIMIENTO. Si hay pocos datos, preferí ajustar_prompt_serie "
        "antes que sacar una serie.\n"
        f'- No saques una serie con menos de {cfg.get("mejoras_min_posts", 3)} videos. Nunca saques del todo '
        f'{", ".join(cfg.get("series_protegidas", ["monotributo"]))} (es el contenido contable que queda para el '
        "estudio): mejorala con ajustes.\n"
        "- No repitas propuestas rechazadas ni toques algo cambiado en los últimos 7 días.\n"
        "- Mirá el BALANCE DE CAMBIOS: si algo mejoró, proponé llevar esa idea a otras series; si empeoró, proponé "
        "deshacerlo.\n"
        "- Los números son de los últimos 10 videos de cada serie con 2 días o más de publicados.\n"
        "- Nada que obligue a inventar datos: la fábrica no puede chequear hechos nuevos por su cuenta.\n"
        "- Español rioplatense, títulos cortos y claros para el dueño de la cuenta.\n\n"
        'Devolvé SOLO este JSON: {"propuestas": [{"tipo": "...", "titulo": "...", "por_que": "...", '
        '"params": {...}}]}\n\n'
        "SERIES DISPONIBLES:\n" + series + "\n\nGRILLA ACTUAL:\n" + grilla(cfg) +
        "\n\nNUESTRO RENDIMIENTO POR SERIE (últimos 30 días):\n" + (lineas_serie or "(sin datos)") +
        "\n\nNUESTROS VIDEOS (de más a menos vistas):\n" + (titulos or "(sin datos)") +
        "\n\nPOR HORARIO:\n" + (franjas or "(sin datos)") +
        "\n\nLO QUE RINDE EN LA COMPETENCIA:\n" + (comp or "(sin datos)") +
        "\n\nCAMBIOS DE LAS ÚLTIMAS SEMANAS (no los repitas):\n" + (historia or "(ninguno)") +
        "\n\nBALANCE DE CAMBIOS (¿funcionaron?):\n" + (balance_txt or "(todavía ninguno aplicado)"))


def proponer(cfg, por_serie, propias, horas, analisis=None):
    """Pide propuestas a Gemini, las valida y deja las válidas como pendientes. Devuelve las nuevas."""
    from . import escritor
    d = _leer()
    historia = "\n".join(f'- {p.get("fecha", "")} [{p["estado"]}] {p["titulo"]}' for p in d["lista"][-20:])
    balance_txt = "\n".join("- " + x for x in balance(cfg, propias, d["lista"]))
    respuesta = escritor.gemini("Respondé solo con JSON válido.", _pedido(cfg, por_serie, propias, horas, analisis,
                                                                           historia, balance_txt), temperatura=0.5)
    posts = _posts_por_serie(propias)
    for p in d["lista"]:
        if p["estado"] == "pendiente":
            p["estado"] = "reemplazada"  # las de la tanda anterior que nunca se mandaron
    nuevas = []
    for crudo in (respuesta or {}).get("propuestas", [])[:5]:
        p = {"tipo": crudo.get("tipo"), "params": crudo.get("params") or {},
             "titulo": str(crudo.get("titulo", ""))[:120], "por_que": str(crudo.get("por_que", ""))[:600]}
        ok, motivo = validar(cfg, p, posts, d["lista"])
        if not ok:
            util.log("Propuesta descartada:", p["titulo"], "·", motivo)
            continue
        p.update({"id": d["proximo_id"], "fecha": _hoy(), "estado": "pendiente"})
        d["proximo_id"] += 1
        d["lista"].append(p)
        nuevas.append(p)
    _guardar(d)
    util.log(f"{len(nuevas)} propuestas nuevas")
    return nuevas


def guardar_aprendizajes(propias, analisis=None):
    orden = sorted(propias or [], key=lambda f: -f["vistas"])
    previo = util.leer_json(APRENDIZAJES, {}) or {}
    if analisis:  # lo de la competencia viene del reporte semanal; entre reportes se mantiene
        analisis = {k: list(analisis.get(k, []))[:5] for k in ("patrones", "formatos_que_rinden", "estructuras_virales")}
    else:
        analisis = previo.get("analisis") or {}
    util.guardar_json(APRENDIZAJES, {
        "fecha": _hoy(),
        "mejores": [f'{f["titulo"]} ({f["vistas"]} vistas)' for f in orden[:3] if f["vistas"] > 0],
        "peores": [f'{f["titulo"]} ({f["vistas"]} vistas)' for f in orden[-3:][::-1]] if len(orden) >= 6 else [],
        "patrones": list(analisis.get("patrones", []))[:3],
        "analisis": analisis})
    return analisis


def bloque_aprendizajes():
    """Lo aprendido para sumarle al pedido de cada guion (guía, no reglas)."""
    ap = util.leer_json(APRENDIZAJES, {}) or {}
    partes = []
    if ap.get("mejores"):
        partes.append("Nuestros videos que mejor anduvieron: " + "; ".join(ap["mejores"]) + ".")
    if ap.get("peores"):
        partes.append("Los que peor anduvieron (evitá ese enfoque): " + "; ".join(ap["peores"]) + ".")
    if ap.get("patrones"):
        partes.append("Lo que rinde en cuentas parecidas: " + " ".join(ap["patrones"]))
    if not partes:
        return ""
    return ("\n\nAPRENDIZAJES (guía para elegir el ángulo y el gancho; nunca copies títulos ni inventes datos):\n- "
            + "\n- ".join(partes))


# ------------------------------------------------------------------ mails
def _mail(asunto, cuerpo):
    from . import publicar as pub
    try:
        pub.mail(asunto, cuerpo)
    except Exception as e:  # noqa
        util.log("No pude mandar el mail:", util.ocultar(e))


def _mail_propuesta(cfg, p, recap, quedan, balances=()):
    import html
    e = html.escape
    link = link_formulario()
    extra = ""
    if p["tipo"] == "nueva_serie":
        extra = (f'<p><b>Instrucciones de la serie nueva:</b></p><p style="color:#444;white-space:pre-wrap">'
                 f'{e(p["params"]["prompt"])}</p>')
    cuerpo = (
        f'<h2>Sugerencia #{p["id"]}: {e(p["titulo"])}</h2>'
        f'<p><b>Qué cambia:</b> {e(describir(cfg, p))}</p>'
        f'<p><b>Por qué:</b> {e(p["por_que"])}</p>{extra}'
        f'<p>⏳ <b>Si no respondés, se aplica sola el {_fecha_linda(p["aplica_el"])}.</b></p>'
        f'<p><b>Para responder:</b> entrá a <a href="{link}">Responder sugerencia</a> → <b>Run workflow</b> → elegí '
        f'«Sí, aplicala», «No, dejala» o «Aplicala con cambios» (y escribí cómo) → <b>Run workflow</b>. Si no ponés número, '
        f'responde a esta, que es la última que te llegó.</p>'
        + (f'<hr><p><b>Ya aplicado:</b></p><ul>' + "".join(f"<li>{e(x)}</li>" for x in recap) +
           '</ul><p style="color:#666">Si algo no te gustó: mismo formulario → «Deshacer el último cambio».</p>'
           if recap else "")
        + ('<hr><p><b>Cómo vienen los cambios:</b></p><ul>' +
           "".join(f'<li>#{q["id"]} {e(q["titulo"])}: {e(q["balance"])}</li>' for q in balances) + '</ul>'
           if balances else "")
        + (f'<p style="color:#666">Quedan {quedan} sugerencias más en la fila: te llega una por día.</p>' if quedan else ""))
    _mail(f'Sugerencia de mejora #{p["id"]}: {p["titulo"]}', cuerpo)


# ------------------------------------------------------------------ todos los días
def diario(regenerar=None, medir=None):
    """1) aplica las que vencieron sin respuesta; 2) si no quedan en la fila, arma propuestas nuevas con los datos de
    hoy (así la mejora es continua y no espera al reporte); 3) manda UNA por mail."""
    cfg = util.config()
    d = _leer()
    hoy = _hoy()
    recap = []
    for p in sorted(d["lista"], key=lambda q: q["id"]):
        if p["estado"] == "enviada" and p.get("aplica_el", "9999") <= hoy:
            ok, motivo = validar(cfg, p, None, [q for q in d["lista"] if q is not p])
            if ok:
                aplicar(cfg, p, d["lista"])
                p.update({"estado": "aplicada", "aplicada_el": hoy, "como": "automática (sin respuesta)"})
                recap.append(f'#{p["id"]} {describir(cfg, p)} (automático, no respondiste)')
                cfg = util.config()
            else:
                p.update({"estado": "descartada", "motivo": motivo})
    if medir and any(p.get("estado") == "aplicada" for p in d["lista"]):
        try:
            balance(cfg, medir(), d["lista"])
        except Exception as e:  # noqa
            util.log("No pude medir los cambios:", util.ocultar(e))
    _guardar(d)
    if util.ahora().isoweekday() == int(cfg.get("tiktok_recordatorio_dia", 7)) and \
            (util.leer_json(TIKTOK, {}) or {}).get("fecha") != hoy:
        recordar_tiktok()
    if any(p.get("enviada_el") == hoy for p in d["lista"]):
        util.log("Hoy ya se mandó una sugerencia")
        return
    pendientes = [p for p in d["lista"] if p["estado"] == "pendiente"]
    if not pendientes and regenerar:
        try:
            regenerar()
        except Exception as e:  # noqa
            util.log("No pude armar propuestas nuevas:", util.ocultar(e))
        d = _leer()
        pendientes = [p for p in d["lista"] if p["estado"] == "pendiente"]
    cfg = util.config()
    for p in pendientes:
        ok, motivo = validar(cfg, p, None, [q for q in d["lista"] if q is not p])
        if not ok:
            p.update({"estado": "descartada", "motivo": motivo})
            continue
        p.update({"estado": "enviada", "enviada_el": hoy, "aplica_el": _sumar_dias(hoy, dias_para_aplicar(cfg))})
        quedan = sum(1 for q in d["lista"] if q["estado"] == "pendiente")
        _guardar(d)
        balances = [q for q in d["lista"] if q.get("estado") == "aplicada" and q.get("balance")]
        _mail_propuesta(cfg, p, recap, quedan, balances[-5:])
        return p
    _guardar(d)
    if recap:
        import html
        _mail("Cambios aplicados en la fábrica",
              "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in recap) + "</ul>"
              f'<p>Para deshacer: <a href="{link_formulario()}">Responder sugerencia</a> → «Deshacer el último cambio».</p>')


# ------------------------------------------------------------------ tu respuesta
def responder(respuesta_texto, comentario="", numero=""):
    accion = RESPUESTAS.get(respuesta_texto)
    if not accion:
        raise ValueError(f"Respuesta desconocida: {respuesta_texto}")
    cfg = util.config()
    d = _leer()
    hoy = _hoy()
    if accion == "deshacer":
        aplicadas = [p for p in d["lista"] if p["estado"] == "aplicada" and p["tipo"] != "deshacer_cambio"]
        if not aplicadas:
            raise ValueError("No hay cambios aplicados para deshacer.")
        p = max(aplicadas, key=lambda q: (q.get("aplicada_el", ""), q["id"]))
        deshacer(p)
        p.update({"estado": "deshecha", "deshecha_el": hoy})
        _guardar(d)
        _mail(f'Deshecho: {p["titulo"]}', f'<p>Volvió a como estaba: {describir(cfg, p)}</p>')
        return p
    numero = str(numero or "").strip().lstrip("#")
    if numero:
        p = next((q for q in d["lista"] if str(q["id"]) == numero), None)
        if not p:
            raise ValueError(f"No encuentro la sugerencia #{numero}.")
    else:
        enviadas = [q for q in d["lista"] if q["estado"] == "enviada"]
        if not enviadas:
            raise ValueError("No hay ninguna sugerencia esperando respuesta.")
        p = max(enviadas, key=lambda q: (q.get("enviada_el", ""), q["id"]))
    if p["estado"] not in ("enviada", "pendiente"):
        raise ValueError(f'La sugerencia #{p["id"]} ya está {p["estado"]}.')
    if accion == "no":
        p.update({"estado": "rechazada", "respondida_el": hoy})
        _guardar(d)
        return p
    if accion == "cambios":
        comentario = (comentario or "").strip()
        if not comentario:
            raise ValueError("Elegiste «Aplicala con cambios» pero no escribiste qué cambiar.")
        from . import escritor
        nueva = escritor.gemini(
            "Respondé solo con JSON válido.",
            "Esta es una propuesta de cambio para una fábrica de videos (JSON). El dueño la quiere aplicar con este "
            f"cambio: «{comentario}». Devolvé la propuesta ajustada, con el mismo «tipo» y la misma forma "
            '({"tipo", "titulo", "por_que", "params"}). Si pide otra serie, otro día u otro horario, cambiá esos '
            "parámetros. Series disponibles: " + ", ".join(cfg["series"]) + ".\n\nGRILLA:\n" + grilla(cfg) +
            "\n\nPROPUESTA:\n" + json.dumps({k: p[k] for k in ("tipo", "titulo", "por_que", "params")},
                                             ensure_ascii=False), temperatura=0.3)
        p["tipo"] = nueva.get("tipo", p["tipo"])
        p["params"] = nueva.get("params") or p["params"]
        p["titulo"] = str(nueva.get("titulo") or p["titulo"])[:120]
        p["comentario"] = comentario
    ok, motivo = validar(cfg, p, None, [q for q in d["lista"] if q is not p])
    if not ok:
        raise ValueError(f"No se puede aplicar: {motivo}")
    aplicar(cfg, p, d["lista"])
    p.update({"estado": "aplicada", "aplicada_el": hoy, "respondida_el": hoy,
              "como": "con tus cambios" if accion == "cambios" else "aprobada"})
    _guardar(d)
    _mail(f'Aplicado: {p["titulo"]}', f'<p>{describir(cfg, p)}</p><p>Corre desde el próximo video.</p>')
    return p


# ------------------------------------------------------------------ TikTok (lo subís a mano, así que las vistas también)
TIKTOK = "data/tiktok_pedido.json"
VISTAS_TIKTOK = "data/tiktok_vistas.json"


def clave_tiktok(h):
    return f'{h.get("fecha")}#{h.get("turno", 1)}'


def vistas_tiktok():
    return util.leer_json(VISTAS_TIKTOK, {}) or {}


def link_tiktok():
    repo = os.getenv("GITHUB_REPOSITORY", "")
    return f"https://github.com/{repo}/actions/workflows/tiktok.yml" if repo else ""


def recordar_tiktok():
    """Los domingos: te pide las vistas de TikTok de los videos de la semana (en el orden del mail)."""
    import html
    hasta = _hoy()
    desde = _sumar_dias(hasta, -7)
    hist = util.leer_json("data/historial.json", []) or []
    cargadas = vistas_tiktok()
    semana = [h for h in hist if desde <= h.get("fecha", "") < hasta and not h.get("cancelado")
              and clave_tiktok(h) not in cargadas]
    if not semana:
        return False
    items = [{"fecha": h["fecha"], "turno": h.get("turno", 1), "titulo": h["titulo"]} for h in semana]
    util.guardar_json(TIKTOK, {"fecha": hasta, "items": items})
    lista = "".join(f'<li>{_fecha_linda(i["fecha"])}: {html.escape(i["titulo"])}</li>' for i in items)
    _mail("Cargá las vistas de TikTok de la semana",
          f'<p>Para que las sugerencias de mejora también miren TikTok, pasame las vistas de estos videos, '
          f'<b>en este orden y separadas por coma</b> (si uno no lo subiste, poné 0):</p><ol>{lista}</ol>'
          f'<p>Entrá a <a href="{link_tiktok()}">Cargar vistas de TikTok</a> → <b>Run workflow</b> → escribí, por '
          f'ejemplo, «1200, 340, 0, 89» → <b>Run workflow</b>.</p>')
    return True


def cargar_tiktok(texto):
    pedido = util.leer_json(TIKTOK, {}) or {}
    items = pedido.get("items") or []
    if not items:
        raise ValueError("No hay ningún pedido de vistas de TikTok pendiente.")
    numeros = [x.strip().replace(".", "") for x in re.split(r"[,;\n]+", texto or "") if x.strip()]
    if len(numeros) != len(items) or not all(n.isdigit() for n in numeros):
        raise ValueError(f"Necesito {len(items)} números separados por coma (en el orden del mail); llegaron "
                         f"{len(numeros)}.")
    cargadas = vistas_tiktok()
    for i, n in zip(items, numeros):
        cargadas[clave_tiktok(i)] = int(n)
    util.guardar_json(VISTAS_TIKTOK, cargadas)  # archivo propio: no choca con el historial que escribe la fábrica
    util.guardar_json(TIKTOK, {})
    return len(items)
