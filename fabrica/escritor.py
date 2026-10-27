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
_DESCARTAR = ("image", "tts", "audio", "live", "embed", "native", "exp", "computer", "robotics", "vision", "omni")
# Motivos por los que Google bloquea el pedido por su contenido (no tiene sentido probar otro modelo)
BLOQUEOS = ("PROHIBITED_CONTENT", "SAFETY", "BLOCKLIST", "SPII", "OTHER", "IMAGE_SAFETY", "RECITATION")
_SEGURIDAD = [{"category": c, "threshold": "BLOCK_ONLY_HIGH"} for c in
              ("HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT",
               "HARM_CATEGORY_DANGEROUS_CONTENT")]


class Bloqueado(RuntimeError):
    """Google rechazó el pedido por su contenido (pasa con el pedido, no con el modelo)."""
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


def _cuerpo(sistema, usuario, temperatura, modelo, con_pensamiento, con_seguridad=True):
    gen = {"responseMimeType": "application/json", "maxOutputTokens": 32768}
    moderno = "latest" in modelo or _version(modelo) >= 3
    if moderno:
        # Gemini 3+: Google recomienda temperatura 1.0 y, si no se aclara, piensa "a fondo" y gasta
        # todo el cupo de salida pensando. Con nivel bajo alcanza para guiones cortos.
        if con_pensamiento:
            gen["thinkingConfig"] = {"thinkingLevel": util.config().get("gemini_pensamiento", "low")}
    else:
        gen["temperature"] = temperatura
    cuerpo = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        # usuario puede ser texto o una lista de partes (texto + imágenes)
        "contents": [{"role": "user", "parts": usuario if isinstance(usuario, list) else [{"text": usuario}]}],
        "generationConfig": gen,
    }
    if con_seguridad:
        cuerpo["safetySettings"] = _SEGURIDAD
    return cuerpo


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
    probados, errores, descubiertos, bloqueos = set(), [], False, 0
    cola = list(preferidos)
    while cola or not descubiertos:
        if not cola:
            descubiertos = True
            cola = [m for m in _descubrir(clave) if m not in probados][:5]
            if cola:
                util.log("Busco modelos vigentes de Gemini:", ", ".join(cola))
            continue
        modelo = cola.pop(0)
        if modelo in probados:
            continue
        probados.add(modelo)
        texto, fin = "", ""
        # Si el modelo no acepta algún ajuste (pensamiento o filtros), pruebo sin él.
        for ajustes in ((True, True), (False, True), (False, False)):
            try:
                r = util.pedir("POST", API.format(modelo=modelo), headers={"x-goog-api-key": clave},
                               json=_cuerpo(sistema, usuario, temperatura, modelo, *ajustes),
                               intentos=1 if descubiertos else 2, espera=15, timeout=150)
            except Exception as e:  # noqa  (Google no contestó a tiempo: paso al modelo siguiente)
                r = None
                errores.append(f"{modelo}: no respondió ({type(e).__name__})")
                break
            if r is not None and r.status_code == 400 and any(x in _mensaje(r).lower() for x in ("think", "safety")):
                continue
            break
        if r is None:
            continue
        if r.status_code != 200:
            errores.append(f"{modelo}: {getattr(r, 'status_code', '?')} {_mensaje(r)}")
            continue
        datos = r.json()
        cand = (datos.get("candidates") or [{}])[0]
        en_pedido = (datos.get("promptFeedback") or {}).get("blockReason", "")
        fin = cand.get("finishReason", "") or en_pedido
        donde = "en lo que le mandamos" if en_pedido and not datos.get("candidates") else "en lo que la IA escribió"
        partes = (cand.get("content") or {}).get("parts", [])
        texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
        try:
            resultado = _json_de(texto)
            if _modelo_ok != modelo:
                util.log("Modelo de Gemini usado:", modelo)
            _modelo_ok = modelo
            return resultado
        except Exception as e:  # noqa
            errores.append(f"{modelo}: respuesta sin JSON (motivo: {fin or 'desconocido'}) {str(e)[:80]}")
            if fin in BLOQUEOS:
                bloqueos += 1
                if bloqueos >= 2:  # dos modelos distintos lo rechazan: es el contenido del pedido
                    raise Bloqueado(f"Google bloqueó el pedido por su contenido ({fin}, {donde})")
    raise RuntimeError("Gemini falló con todos los modelos: " + " | ".join(errores))


def _limpiar(s, voz=False):
    s = str(s or "").replace("—", ", ").replace("–", ", ")
    if voz:  # la voz dice "por ciento"; en pantalla y en las placas queda el %
        s = re.sub(r"(\d)\s?%", r"\1 por ciento", s)
    s = EMOJI_RE.sub("", s)
    return re.sub(r"\s+", " ", s).replace(" ,", ",").strip()


_SIGLAS = ["ARCA", "AFIP", "IVA", "CUIT", "CUIL", "CBU", "CVU", "ANSES", "AUH", "DNI", "IIBB", "ARBA", "AGIP",
           "AFJP", "PBI", "FMI", "BCRA", "CEDEAR", "CEDEARs", "FCI", "UVA", "SAC"]
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


_EMOJI_REEMPLAZO = {"📅": "🗓️", "📆": "🗓️"}  # los calendarios muestran una fecha fija ("JULY 17") que confunde


def _emoji(e, defecto):
    e = str(e or "").strip()
    for viejo, nuevo in _EMOJI_REEMPLAZO.items():
        e = e.replace(viejo, nuevo)
    return e[:4] if e else defecto


def _broll(b):
    """Búsquedas en inglés para los videos de stock de la escena (una o dos)."""
    lista = b if isinstance(b, list) else [b]
    limpias = [re.sub(r"[^A-Za-z0-9 \-]", "", str(x or "")).strip()[:60] for x in lista]
    return [x for x in limpias if len(x) > 2][:2]


def _titulo_corto(t, maximo=60):
    """Red de seguridad: si la IA se pasa de largo, corta en la última palabra entera (sin dejar puntuación colgando)."""
    if len(t) <= maximo:
        return t
    corto = t[:maximo].rsplit(" ", 1)[0].rstrip(" ,;:.-—")
    sueltas = {"y", "o", "de", "del", "que", "para", "en", "a", "al", "con", "el", "la", "los", "las", "un", "una",
               "por", "sin", "tu", "tus", "su", "sus", "es", "se", "lo", "le", "mi", "mis"}
    while " " in corto and corto.rsplit(" ", 1)[1].lower() in sueltas:
        corto = corto.rsplit(" ", 1)[0].rstrip(" ,;:.-—")
    if corto.startswith("¿") and not corto.endswith("?"):
        corto += "?"
    return corto


GRAFICOS_MAX = 3


def _grafico(g):
    """Escena gráfica (cartel animado) que propone la IA, revisada; None si no sirve."""
    if not isinstance(g, dict):
        return None
    from . import graficos
    g = graficos.valido({k: v for k, v in g.items()})
    if not g:
        return None
    for k in ("texto", "sello", "rotulo", "valor", "nota", "titulo", "arriba", "abajo"):
        if g.get(k):
            g[k] = _siglas(_limpiar(g[k]))
    if g.get("items"):
        g["items"] = [_siglas(_limpiar(x)) for x in g["items"] if str(x).strip()]
    return g


def validar(d):
    escenas = []
    for e in d.get("escenas", []):
        voz = _limpiar(e.get("texto_voz") or e.get("texto"), voz=True)
        if voz:
            escenas.append({"texto_voz": voz,
                            "texto_pantalla": _siglas(_limpiar(e.get("texto_pantalla")) or voz[:40]),
                            "emoji": _emoji(e.get("emoji"), "💡"),
                            "prompt": str(e.get("prompt") or "").strip(),
                            "broll": _broll(e.get("broll"))})
            g = _grafico(e.get("grafico"))
            if g and len(escenas) > 1 and sum(1 for x in escenas if x.get("grafico")) < GRAFICOS_MAX:
                escenas[-1]["grafico"] = g  # nunca en la escena 1 (ahí va el gancho escrito)
    carrusel = []
    for p in d.get("carrusel", []):
        if p.get("titulo"):
            carrusel.append({"titulo": _siglas(_limpiar(p["titulo"]), True), "cuerpo": _siglas(_limpiar(p.get("cuerpo") or p.get("texto")), True),
                             "emoji": _emoji(p.get("emoji"), "💡")})
    palabras = sum(len(e["texto_voz"].split()) for e in escenas)
    if len(escenas) < 4:
        raise ValueError(f"Guion corto: {len(escenas)} escenas")
    if palabras > 320:  # si se pasa un poco, después lo recorta _ajustar_largo (y la voz se acelera un poco)
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
        "titulo": _titulo_corto(_siglas(_limpiar(d.get("titulo")), True)),
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


def _material(fuentes, nivel):
    """nivel 0: todo el material; 1: solo los títulos; 2: sin material."""
    if nivel >= 2 or not fuentes:
        return "", []
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
        bloques.append(cab + ("\n" + texto[:3500] if nivel == 0 and texto else ""))
    return "\n\n".join(bloques), bloques


def _pedido(serie, titulos_previos, material):
    material = material or ("(Hoy no hay material de referencia: elegí vos un tema que sepas que interesa mucho, "
                            "dentro de la serie.)")
    return (
        serie["prompt"] + "\n\n" + _prompt("formato.md") + "\n\n"
        "Temas ya publicados (NO repetir ni hacer variantes muy parecidas):\n"
        + ("\n".join("- " + t for t in titulos_previos[:40]) or "- (ninguno todavía)") + "\n\n"
        "MATERIAL DE REFERENCIA (videos y posts que funcionaron muy por encima de lo normal, o noticias recientes; "
        "pueden estar en otro idioma). Usalo para entender qué tema y qué gancho funciona. El texto tiene que ser "
        "nuestro, nunca traducido ni parafraseado frase por frase:\n\n" + material
    )


_NIVELES = ["material completo", "solo los títulos del material", "sin material"]

_SISTEMA_MINIMO = ("Sos un contador argentino de La Plata que explica plata e impuestos para gente común. "
                   "Escribís guiones de videos cortos en español rioplatense, con voseo, claro y sin tecnicismos. "
                   "Nunca inventás datos ni números.")


def _diagnostico(sistema, serie):
    """Cuando Google bloquea hasta el pedido sin material, prueba cada pieza por separado (pedidos chiquitos)
    para saber cuál dispara el bloqueo. El resultado queda como aviso en la ejecución."""
    prueba = 'Respondé solo con este JSON: {"ok": true}'
    piezas = [("maestro.md", sistema, prueba),
              ("prompt de la serie", _SISTEMA_MINIMO, serie["prompt"] + "\n\n" + prueba),
              ("formato.md", _SISTEMA_MINIMO, _prompt("formato.md") + "\n\n" + prueba)]
    resultado = []
    for nombre, sis, usu in piezas:
        try:
            gemini(sis, usu)
            resultado.append(f"{nombre}: pasa")
        except Bloqueado as e:
            resultado.append(f"{nombre}: BLOQUEADO ({e})")
        except Exception as e:  # noqa
            resultado.append(f"{nombre}: error {str(e)[:80]}")
    util.avisar("Diagnóstico del bloqueo de Google", " | ".join(resultado))


LARGO_MAX = 160  # palabras (casi un minuto): tope de cualquier serie; cada serie puede tener su propio "palabras_max"


def _para_ia(d):
    """El JSON del guion como lo espera la IA (sin campos internos)."""
    x = {k: v for k, v in d.items() if k != "palabras"}
    x["carrusel"] = [{"titulo": c["titulo"], "texto": c["cuerpo"], "emoji": c["emoji"]} for c in d["carrusel"]]
    return x


def _ajustar_largo(sistema, d, maximo=LARGO_MAX):
    """Si el guion se pasó de largo, le pide a la IA que lo recorte sin tocar el gancho."""
    max_escenas = max(10, maximo // 9)
    if d["palabras"] <= maximo and len(d["escenas"]) <= max_escenas:
        return d
    util.log(f'Guion largo ({d["palabras"]} palabras, {len(d["escenas"])} escenas): lo acorto')
    pedido = (f'Este guion de video corto se pasa de largo: tiene {d["palabras"]} palabras y {len(d["escenas"])} '
              f"escenas. Dejalo en {max_escenas} escenas como mucho y en no más de {maximo - 10} palabras en total. "
              "Mantené la escena 1 (el gancho) "
              "y el dato principal tal cual; sacá primero el relleno y las frases que repiten una idea; no saques ideas importantes ni lo que hace falta para entender; si sacás un dato, sacalo entero (no dejes frases que no se entiendan) y mantené el final concreto. No cambies nada "
              "más (ni título, ni descripción, ni carrusel, ni hashtags). Devolvé el JSON completo con la misma forma."
              "\n\nJSON:\n" + json.dumps(_para_ia(d), ensure_ascii=False))
    try:
        nuevo = validar(gemini(sistema, pedido, temperatura=0.4))
        if nuevo["palabras"] < d["palabras"]:
            util.log(f'Acortado a {nuevo["palabras"]} palabras')
            return nuevo
    except Exception as e:  # noqa
        util.log("No pude acortarlo, sigo con el que tengo:", util.ocultar(e))
    return d


def escribir(serie, fuentes, titulos_previos):
    sistema = _prompt("maestro.md")
    borrador, material = None, ""
    for nivel in ((0, 1, 2) if fuentes else (2,)):
        material, _ = _material(fuentes, nivel)
        try:
            borrador = validar(gemini(sistema, _pedido(serie, titulos_previos, material)))
            if nivel:
                util.log(f"Salió con {_NIVELES[nivel]}")
            break
        except Bloqueado as e:
            lista = "; ".join(f'{f.get("canal")}: {str(f.get("titulo"))[:70]}' for f in fuentes) or "ninguna"
            util.avisar("Google bloqueó el pedido, reintento con menos material",
                        f"Intento con {_NIVELES[nivel]}: {e}. Fuentes del día: {lista}")
            if nivel == 2:
                _diagnostico(sistema, serie)
                # Último recurso: instrucciones mínimas para que el video del día salga igual.
                sistema = _SISTEMA_MINIMO
                pedido = (f'Serie: {serie.get("nombre", "")}. Elegí un tema útil y concreto de esta serie.\n\n'
                          + _prompt("formato.md"))
                borrador = validar(gemini(sistema, pedido))
                util.avisar("Video hecho con instrucciones mínimas",
                            "Salió sin el estilo completo. Revisar el diagnóstico de arriba.")
    util.log("Borrador:", borrador["titulo"], f'({borrador["palabras"]} palabras)')
    try:
        chequeo = ("\n\nMATERIAL DE REFERENCIA (solo para chequear que cada dato del guion exista acá):\n" +
                   material[:9000]) if material else ""
        revisado = gemini(sistema, _prompt("revision.md") + "\n\nJSON A REVISAR:\n" +
                          json.dumps(_para_ia(borrador), ensure_ascii=False) + chequeo, temperatura=0.6)
        final = validar(revisado)
        util.log("Revisado:", final["titulo"], f'({final["palabras"]} palabras)')
    except Exception as e:  # noqa
        util.log("La revisión falló, uso el borrador:", util.ocultar(e))
        final = borrador
    return _ajustar_largo(sistema, final, int(serie.get("palabras_max") or LARGO_MAX))


def aplicar_cambios(serie, contenido, cambios):
    """El dueño de la cuenta vio el video y pidió cambios: se rehace el guion respetando lo que pidió."""
    sistema = _prompt("maestro.md")
    pedido = ("Este es el guion de un video corto (JSON). El dueño de la cuenta lo vio antes de publicarlo y pidió "
              f"estos cambios:\n«{cambios.strip()}»\n\n"
              "Aplicá lo que pidió al pie de la letra: si da un título o una frase, usalos textuales; si pide explicar "
              "mejor algo, agregá lo que haga falta; si pide más largo o más corto, ajustalo; si pide otro gancho o otro "
              "final, cambialos. Todo lo demás dejalo como está, salvo que el cambio lo requiera. Seguí respetando las "
              "reglas de formato y de precisión de siempre (ningún dato inventado). Si el pedido es solo sobre las "
              "imágenes o los clips, devolvé el guion igual. Devolvé el JSON completo, con la misma forma.\n\n"
              + serie.get("prompt", "") + "\n\n" + _prompt("formato.md") + "\n\nJSON:\n"
              + json.dumps(_para_ia(contenido), ensure_ascii=False))
    nuevo = validar(gemini(sistema, pedido, temperatura=0.5))
    util.log("Guion con tus cambios:", nuevo["titulo"], f'({nuevo["palabras"]} palabras)')
    return _ajustar_largo(sistema, nuevo, int(serie.get("palabras_max") or LARGO_MAX))
