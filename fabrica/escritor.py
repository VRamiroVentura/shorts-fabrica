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


def gemini(sistema, usuario, temperatura=0.9):
    clave = util.secreto("GEMINI_API_KEY")
    if not clave:
        raise RuntimeError("Falta el secreto GEMINI_API_KEY")
    cuerpo = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"role": "user", "parts": [{"text": usuario}]}],
        "generationConfig": {"temperature": temperatura, "responseMimeType": "application/json",
                             "maxOutputTokens": 8192},
    }
    errores = []
    for modelo in util.config().get("gemini_modelos", ["gemini-2.5-flash"]):
        r = util.pedir("POST", API.format(modelo=modelo), params={"key": clave}, json=cuerpo, espera=20, timeout=180)
        if r is not None and r.status_code == 200:
            partes = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            texto = "".join(p.get("text", "") for p in partes)
            try:
                return _json_de(texto)
            except Exception as e:  # noqa
                errores.append(f"{modelo}: {e}")
                continue
        errores.append(f"{modelo}: {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:200]}")
    raise RuntimeError("Gemini falló con todos los modelos: " + " | ".join(errores))


def _limpiar(s, voz=False):
    s = str(s or "").replace("—", ", ").replace("–", ", ")
    s = re.sub(r"(\d)\s?%", r"\1 por ciento", s)
    s = EMOJI_RE.sub("", s)
    return re.sub(r"\s+", " ", s).replace(" ,", ",").strip()


def _emoji(e, defecto):
    e = str(e or "").strip()
    return e[:4] if e else defecto


def validar(d):
    escenas = []
    for e in d.get("escenas", []):
        voz = _limpiar(e.get("texto_voz") or e.get("texto"), voz=True)
        if voz:
            escenas.append({"texto_voz": voz,
                            "texto_pantalla": _limpiar(e.get("texto_pantalla")) or voz[:40],
                            "emoji": _emoji(e.get("emoji"), "💡"),
                            "prompt": str(e.get("prompt") or "").strip()})
    carrusel = []
    for p in d.get("carrusel", []):
        if p.get("titulo"):
            carrusel.append({"titulo": _limpiar(p["titulo"]), "cuerpo": _limpiar(p.get("cuerpo")),
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
        "titulo": _limpiar(d.get("titulo"))[:95],
        "descripcion": _limpiar(d.get("descripcion")),
        "hashtags": tags[:8],
        "miniatura": {"linea1": _limpiar(mini.get("linea1") or d.get("titulo")),
                      "linea2": _limpiar(mini.get("linea2")),
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
        if f.get("pais"):
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
        "MATERIAL DE REFERENCIA (videos que funcionaron muy por encima de lo normal; pueden estar en otro idioma). "
        "Usalo para entender qué tema y qué gancho funciona. El texto tiene que ser nuestro, nunca traducido ni "
        "parafraseado frase por frase:\n\n" + material
    )
    borrador = validar(gemini(sistema, usuario))
    util.log("Borrador:", borrador["titulo"], f'({borrador["palabras"]} palabras)')
    try:
        revisado = gemini(sistema, _prompt("revision.md") + "\n\nJSON A REVISAR:\n" +
                          json.dumps(borrador, ensure_ascii=False), temperatura=0.6)
        final = validar(revisado)
        util.log("Revisado:", final["titulo"])
        return final
    except Exception as e:  # noqa
        util.log("La revisión falló, uso el borrador:", e)
        return borrador
