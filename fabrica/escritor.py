"""Escribe el guion, el carrusel y los textos con Gemini (clave gratuita de Google AI Studio)."""
import json
import re

from . import util

API = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")


def _prompt(nombre):
    return (util.RAIZ / "prompts" / nombre).read_text(encoding="utf-8")


def _json_de(texto):
    t = re.sub(r"```(?:json)?", "", texto or "").strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("La IA no devolvió JSON: " + t[:200])
    return json.loads(t[a:b + 1])


LISTA = "https://generativelanguage.googleapis.com/v1beta/models"
_DESCARTAR = ("image", "tts", "audio", "live", "embed", "native", "exp", "computer", "robotics", "vision")
_modelo_ok = None  # el primer modelo que anduvo en esta ejecución se reusa


def _version(nombre):
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", nombre)
    return float(m.group(1)) if m else 0.0


def _descubrir(clave):
    """Pide a Google la lista de modelos vigentes y ordena los Flash del más nuevo al más viejo.
    Así, cuando Google retire un modelo, la fábrica encuentra sola el reemplazo."""
    try:
        r = util.pedir("GET", LISTA, headers={"x-goog-api-key": clave}, params={"pageSize": 1000}, timeout=60)
        modelos = r.json().get("models", []) if r is not None and r.status_code == 200 else []
    except Exception as e:  # noqa
        util.log("No pude listar los modelos de Gemini:", util.ocultar(str(e)))
        return []
    nombres = []
    for m in modelos:
        n = m.get("name", "").split("/")[-1]
        if ("generateContent" in m.get("supportedGenerationMethods", []) and "flash" in n
                and not any(x in n for x in _DESCARTAR)):
            nombres.append(n)
    # primero Flash común, después Lite; dentro de cada grupo, estable antes que preview y versión más nueva primero
    nombres.sort(key=lambda n: ("lite" in n, "preview" in n, -_version(n), n))
    return nombres


def _cuerpo(sistema, usuario, temperatura, modelo, con_pensamiento):
    gen = {"responseMimeType": "application/json", "maxOutputTokens": 32768}
    moderno = "latest" in modelo or _version(modelo) >= 3
    if moderno:
        # Gemini 3+: Google recomienda temperatura 1.0 y, si no se aclara, piensa "a fondo" y gasta
        # todo el cupo de salida pensando. Con nivel bajo alcanza para guiones cortos.
        if con_pensamiento:
            gen["thinkingConfig"] = {"thinkingLevel": util.config().get("gemini_pensamiento", "low")}
    else:
        gen["temperature"] = temperatura
    return {
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"role": "user", "parts": [{"text": usuario}]}],
        "generationConfig": gen,
    }


def _mensaje(r):
    try:
        return r.json()["error"]["message"][:220]
    except Exception:  # noqa
        return (getattr(r, "text", "") or "")[:220]


def gemini(sistema, usuario, temperatura=0.9):
    global _modelo_ok
    clave = util.secreto("GEMINI_API_KEY")
    if not clave:
        raise RuntimeError("Falta el secreto GEMINI_API_KEY (Settings → Secrets and variables → Actions)")
    preferidos = ([_modelo_ok] if _modelo_ok else []) + util.config().get("gemini_modelos", ["gemini-flash-latest"])
    probados, errores, descubiertos = set(), [], False
    cola = list(preferidos)
    while cola or not descubiertos:
        if not cola:
            descubiertos = True
            cola = [m for m in _descubrir(clave) if m not in probados][:6]
            if cola:
                util.log("Busco modelos vigentes de Gemini:", ", ".join(cola))
            continue
        modelo = cola.pop(0)
        if modelo in probados:
            continue
        probados.add(modelo)
        texto, fin = "", ""
        for con_pensamiento in (True, False):
            r = util.pedir("POST", API.format(modelo=modelo), headers={"x-goog-api-key": clave},
                           json=_cuerpo(sistema, usuario, temperatura, modelo, con_pensamiento),
                           intentos=3, espera=15, timeout=240)
            if r is not None and r.status_code == 400 and "think" in _mensaje(r).lower() and con_pensamiento:
                continue  # el modelo no acepta el ajuste de pensamiento: pruebo sin él
            break
        if r is None or r.status_code != 200:
            errores.append(f"{modelo}: {getattr(r, 'status_code', '?')} {_mensaje(r)}")
            continue
        datos = r.json()
        cand = (datos.get("candidates") or [{}])[0]
        fin = cand.get("finishReason", "") or (datos.get("promptFeedback") or {}).get("blockReason", "")
        partes = (cand.get("content") or {}).get("parts", [])
        texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
        try:
            resultado = _json_de(texto)
            if _modelo_ok != modelo:
                util.log("Modelo de Gemini usado:", modelo)
            _modelo_ok = modelo
            return resultado
        except Exception as e:  # noqa
            errores.append(f"{modelo}: respuesta sin JSON (motivo: {fin or 'desconocido'}) {str(e)[:120]}")
    raise RuntimeError("Gemini falló con todos los modelos: " + " | ".join(errores))


def _limpiar(s, voz=False):
    s = str(s or "").replace("—", ", ").replace("–", ", ")
    s = re.sub(r"(\d)\s?%", r"\1 por ciento", s)
    s = EMOJI_RE.sub("", s)
    return re.sub(r"\s+", " ", s).replace(" ,", ",").strip()


_SIGLAS = ["ARCA", "AFIP", "IVA", "CUIT", "CUIL", "CBU", "CVU", "ANSES", "AUH", "DNI", "IIBB", "ARBA", "AGIP",
           "AFJP", "PBI", "FMI", "BCRA", "CEDEAR", "CEDEARs", "FCI", "UVA", "SAC", "ART"]
_SIGLAS_RE = re.compile(r"\b(" + "|".join(sorted(_SIGLAS, key=len, reverse=True)) + r")\b", re.IGNORECASE)
_SIGLAS_MAP = {s.lower(): s for s in _SIGLAS}


def _siglas(s, oracion=False):
    """Siglas siempre en mayúscula y, si es un título, mayúscula al principio."""
    s = _SIGLAS_RE.sub(lambda m: _SIGLAS_MAP.get(m.group(0).lower(), m.group(0)), s or "")
    if oracion:
        for i, c in enumerate(s):
            if c.isalpha():
                s = s[:i] + c.upper() + s[i + 1:]
                break
    return s


def _emoji(e, defecto):
    e = str(e or "").strip()
    return e[:4] if e else defecto


def validar(d):
    escenas = []
    for e in d.get("escenas", []):
        voz = _limpiar(e.get("texto_voz") or e.get("texto"), voz=True)
        if voz:
            escenas.append({"texto_voz": voz,
                            "texto_pantalla": _siglas(_limpiar(e.get("texto_pantalla")) or voz[:40]),
                            "emoji": _emoji(e.get("emoji"), "💡"),
                            "prompt": str(e.get("prompt") or "").strip()})
    carrusel = []
    for p in d.get("carrusel", []):
        if p.get("titulo"):
            carrusel.append({"titulo": _siglas(_limpiar(p["titulo"]), True), "cuerpo": _siglas(_limpiar(p.get("cuerpo")), True),
                             "emoji": _emoji(p.get("emoji"), "💡")})
    palabras = sum(len(e["texto_voz"].split()) for e in escenas)
    if len(escenas) < 4:
        raise ValueError(f"Guion corto: {len(escenas)} escenas")
    if palabras > 190:
        raise ValueError(f"Guion largo: {palabras} palabras")
    if len(carrusel) < 4:
        raise ValueError(f"Carrusel corto: {len(carrusel)} placas")
    tags = []
    for h in d.get("hashtags", []):
        h = "#" + re.sub(r"[^\wáéíóúñü]", "", str(h).lower().lstrip("#"))
        if len(h) > 2 and h not in tags:
            tags.append(h)
    if "#argentina" not in tags:
        tags.append("#argentina")
    mini = d.get("miniatura") or {}
    return {
        "titulo": _siglas(_limpiar(d.get("titulo")), True)[:95],
        "descripcion": _siglas(_limpiar(d.get("descripcion")), True),
        "hashtags": tags[:8],
        "miniatura": {"linea1": _siglas(_limpiar(mini.get("linea1") or d.get("titulo")), True),
                      "linea2": _siglas(_limpiar(mini.get("linea2"))),
                      "emoji": _emoji(mini.get("emoji"), escenas[0]["emoji"]),
                      "prompt": str(mini.get("prompt") or escenas[0]["prompt"])},
        "escenas": escenas,
        "carrusel": carrusel[:10],
        "palabras": palabras,
    }


def escribir(serie, fuentes, titulos_previos):
    sistema = _prompt("maestro.md")
    bloques = []
    for i, f in enumerate(fuentes, 1):
        tipo = "Short" if 0 < f.get("segundos", 0) <= 180 else "video largo (tomá UNA sola idea)"
        texto = f.get("transcripcion") or f.get("descripcion") or ""
        if f.get("tipo") == "noticia":
            cab = (f'NOTICIA RECIENTE de {f["canal"]}' + (f' ({f["publicado"]})' if f.get("publicado") else "") +
                   f' · "{f["titulo"]}"')
        elif f.get("tipo") == "instagram":
            cab = (f'POST DE INSTAGRAM QUE PEGÓ FUERTE en {f["canal"]} · formato {f.get("formato", "post")} · '
                   f'{f.get("likes") or "?"} me gusta, {f.get("comentarios") or "?"} comentarios · '
                   f'{f["score"]} veces lo normal de esa cuenta (tomá el tema o el formato, nunca el texto)')
        elif f.get("pais"):
            cab = (f'VIDEO VIRAL EN {f["pais"].upper()} (idioma {f.get("idioma")}) · "{f["titulo"]}" · '
                   f'canal {f["canal"]} · {f["vistas"]} vistas · {tipo}')
        else:
            cab = (f'FUENTE {i} · "{f["titulo"]}" · canal {f["canal"]} · {f["vistas"]} vistas, '
                   f'{f["score"]} veces su promedio · {tipo}')
        bloques.append(cab + "\n" + texto[:3500])
    material = ("\n\n".join(bloques) if bloques else
                "(Hoy no hay material de referencia: elegí vos un tema que sepas que interesa mucho, "
                "dentro de la serie.)")
    usuario = (
        serie["prompt"] + "\n\n" + _prompt("formato.md") + "\n\n"
        "Temas ya publicados (NO repetir ni hacer variantes muy parecidas):\n"
        + ("\n".join("- " + t for t in titulos_previos[:40]) or "- (ninguno todavía)") + "\n\n"
        "MATERIAL DE REFERENCIA (videos y posts que funcionaron muy por encima de lo normal, o noticias recientes; "
        "pueden estar en otro idioma). Usalo para entender qué tema y qué gancho funciona. El texto tiene que ser "
        "nuestro, nunca traducido ni parafraseado frase por frase:\n\n" + material
    )
    borrador = validar(gemini(sistema, usuario))
    util.log("Borrador:", borrador["titulo"], f'({borrador["palabras"]} palabras)')
    try:
        chequeo = ("\n\nMATERIAL DE REFERENCIA (solo para chequear que cada dato del guion exista acá):\n" +
                   material[:9000]) if bloques else ""
        revisado = gemini(sistema, _prompt("revision.md") + "\n\nJSON A REVISAR:\n" +
                          json.dumps(borrador, ensure_ascii=False) + chequeo, temperatura=0.6)
        final = validar(revisado)
        util.log("Revisado:", final["titulo"])
        return final
    except Exception as e:  # noqa
        util.log("La revisión falló, uso el borrador:", e)
        return borrador
