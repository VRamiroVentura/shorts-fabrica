"""Puente con el portal ramacontable.com.ar.

El portal publica en datos/para-shorts.json sus notas ya verificadas (las que están publicadas, nunca las que
quedaron en revisión). Los videos contables salen de ahí: usan solo esos datos y mandan a la nota.
Si el portal no responde o no hay nota nueva, la fábrica sigue como siempre (referentes de YouTube y portales).
"""
import re
from datetime import date, timedelta

from . import util

URL = "https://ramacontable.com.ar/datos/para-shorts.json"
WEB = "https://ramacontable.com.ar/"
LINEA_BLOG = "Más info en ramacontable.com.ar, nuestro blog para contadores (link en la bio)."
# Lo que más le toca el bolsillo a la gente común va primero
PRIORIDAD_SECCION = {"impuestos": 0, "monotributo": 0, "sueldos": 1, "trabajo": 1, "previsional": 2}


def traer(cfg=None):
    """Lee el json del portal. Devuelve {} si no está o falla (nunca corta el video del día)."""
    url = (cfg or {}).get("portal_datos_url") or URL
    try:
        r = util.pedir("GET", url, intentos=2, espera=3, timeout=30)
        if r is not None and getattr(r, "status_code", 0) == 200:
            return r.json() or {}
        util.log("El portal no respondió bien:", getattr(r, "status_code", r))
    except Exception as e:  # noqa
        util.log("No pude leer el portal:", util.ocultar(e))
    return {}


def enlace(nota_url, red):
    """URL de la nota marcada con la red de donde viene la visita (para medirlo en Search Console / Analytics)."""
    if not nota_url:
        return ""
    sep = "&" if "?" in nota_url else "?"
    return f"{nota_url}{sep}utm_source={red}&utm_medium=shorts&utm_campaign=fabrica"


def _texto(cuerpo, tope=3000):
    """El cuerpo de la nota ([{"h": ...}, {"p": ...}, {"ul": [...]}]) en texto corrido."""
    partes = []

    def sumar(x):
        if isinstance(x, str):
            partes.append(x.strip())
        elif isinstance(x, list):
            for y in x:
                sumar(y)
        elif isinstance(x, dict):
            for v in x.values():
                sumar(v)

    sumar(cuerpo or [])
    return " ".join(p for p in partes if p)[:tope]


def _material(n):
    preguntas = "\n".join(f'- {q.get("p", "")} {q.get("r", "")}' for q in (n.get("preguntas") or [])[:4]
                          if isinstance(q, dict))
    return (
        "ESTA ES UNA NOTA NUESTRA (ramacontable.com.ar), YA VERIFICADA. El video cuenta ESTE tema y nada más.\n"
        "- Montos, fechas, porcentajes y normas: usá solo los que están acá, tal cual. Nada de memoria.\n"
        "- Arrancá por lo que le cambia a quien mira (plata, fecha, trámite), no por la norma.\n"
        f'- El cierre manda a la nota con algo concreto, por ejemplo: "La nota completa está en ramacontable.com.ar". '
        "En la voz: \"rama contable punto com punto ar\".\n\n"
        f'Título: {n.get("titulo", "")}\n'
        f'En corto: {n.get("encorto", "")}\n'
        + (f'Dato clave: {n.get("clave")}\n' if n.get("clave") else "")
        + (f'Fuente: {n.get("fuente")}\n' if n.get("fuente") else "")
        + f'\nNota:\n{n.get("texto") or ""}\n'
        + (f"\nPreguntas frecuentes:\n{preguntas}\n" if preguntas else "")
    )


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def ultima_fecha(n):
    """La fecha más lejana que nombra la nota en el título o el dato clave («hasta el 16 de noviembre»).
    Sirve para no hacer un video de algo que ya pasó (bancos cerrados la semana pasada, un plazo vencido)."""
    texto = f'{n.get("titulo", "")} {n.get("clave", "")} {n.get("antetitulo", "")}'.lower()
    try:
        base = date.fromisoformat(str(n.get("fecha", ""))[:10])
    except ValueError:
        base = None
    fechas = []
    for dia, mes, anio in re.findall(r"\b(\d{1,2}) de (" + "|".join(MESES) + r")(?: de (\d{4}))?", texto):
        y = int(anio) if anio else (base.year if base else date.today().year)
        try:
            f = date(y, MESES.index(mes) + 1, int(dia))
        except ValueError:
            continue
        if not anio and base and f < base - timedelta(days=60):  # «enero» en una nota de diciembre
            f = date(y + 1, f.month, f.day)
        fechas.append(f)
    return max(fechas) if fechas else None


def candidatas(datos, usados=(), dias=7, hoy=None):
    """Notas publicadas en los últimos `dias`, no usadas todavía y que no hablen de algo que ya pasó."""
    hoy = hoy or util.ahora().date()
    desde = (hoy - timedelta(days=dias)).isoformat()
    usados = set(usados or ())
    lista = []
    for n in (datos or {}).get("notas") or []:
        slug = n.get("slug")
        if not slug or f"portal:{slug}" in usados or str(n.get("fecha", ""))[:10] < desde:
            continue
        if not (n.get("encorto") or n.get("texto")):
            continue
        fin = ultima_fecha(n)
        if fin and fin < hoy:  # lo que cuenta ya pasó
            continue
        lista.append(n)
    lista.sort(key=lambda n: str(n.get("fecha", ""))[:10], reverse=True)
    lista.sort(key=lambda n: PRIORIDAD_SECCION.get(str(n.get("seccion", "")).lower(), 3))
    return lista[:10]


PUNTAJE_SISTEMA = ("Sos editor de videos cortos de una cuenta argentina de plata e impuestos para gente común "
                   "(no contadores). Elegís qué noticia puede tener muchas vistas y que la gente la comparta. "
                   "Sos exigente: un tema que solo le importa a contadores o empresas tiene puntaje bajo.")


def _pedido_puntaje(lista, referentes):
    notas = "\n".join(f'{i}. [{n.get("seccion", "")}] {n.get("titulo", "")} — {str(n.get("encorto", ""))[:280]}'
                      for i, n in enumerate(lista, 1))
    refs = "\n".join(f'R{i}. "{str(f.get("titulo", ""))[:140]}" ({f.get("canal", "")}, {f.get("score", "")})'
                     for i, f in enumerate(referentes or [], 1)) or "(hoy no hay)"
    return (
        "Puntuá cada NOTA del 1 al 10 según cuánto le interesa al público argentino en general, pensando en:\n"
        "- Bolsillo: le cambia plata, un descuento, un cobro o una fecha a la persona común.\n"
        "- Alcance: a cuánta gente toca (empleados, monotributistas, jubilados, inquilinos, quien cobra por "
        "transferencia o compra afuera). Si solo les importa a contadores o empresas: 3 o menos.\n"
        "- Urgencia: hay que hacer algo pronto o cambia algo ya.\n"
        "- Sorpresa: tiene algo que la mayoría no sabe y da ganas de mandárselo a alguien.\n"
        "Además, fijate si alguna nota trata el MISMO tema que algún REFERENTE (videos o posts de contadores "
        "que pegaron fuerte hoy). Solo si es el mismo tema de verdad, no parecido.\n\n"
        f"NOTAS:\n{notas}\n\nREFERENTES:\n{refs}\n\n"
        'Respondé SOLO con JSON: {"notas": [{"n": 1, "puntaje": 7, "angulo": "en una frase, qué le cambia a '
        'quien mira, para el gancho", "referente": "R2" o null}]}'
    )


def elegir(datos, usados=(), referentes=(), dias=7, minimo=7, hoy=None, puntuar=None):
    """La nota del portal que vale la pena convertir en video, o None si ninguna llega al `minimo`.

    Gemini puntúa las candidatas (1 consulta). Gana la que coincide con un tema que está pegando en los
    referentes; después, la de mayor puntaje. Devuelve (fuente_nota, referente_que_coincide_o_None)."""
    lista = candidatas(datos, usados, dias, hoy)
    if not lista:
        return None, None
    if puntuar is None:
        from . import escritor
        puntuar = escritor.gemini
    try:
        r = puntuar(PUNTAJE_SISTEMA, _pedido_puntaje(lista, referentes), 0.2) or {}
    except Exception as e:  # noqa  (si no se puede puntuar, no arriesgamos una nota aburrida)
        util.log("No pude puntuar las notas del portal, sigo con los referentes:", util.ocultar(e))
        return None, None
    puntajes = []
    for x in r.get("notas") or []:
        try:
            i, pts = int(x.get("n")) - 1, float(x.get("puntaje"))
        except (TypeError, ValueError):
            continue
        if not 0 <= i < len(lista):
            continue
        ref = None
        m = re.match(r"R(\d+)", str(x.get("referente") or ""))
        if m and 0 < int(m.group(1)) <= len(referentes or []):
            ref = list(referentes)[int(m.group(1)) - 1]
        puntajes.append((pts, ref, str(x.get("angulo") or "").strip(), i))
    util.log("Puntaje de las notas del portal:",
             [f'{p:g} {lista[i].get("titulo", "")[:60]}' + (" (pega en referentes)" if ref else "")
              for p, ref, _, i in puntajes] or "sin respuesta")
    buenas = [x for x in puntajes if x[0] >= minimo]
    if not buenas:
        return None, None
    buenas.sort(key=lambda x: (x[1] is not None, x[0], -x[3]), reverse=True)
    pts, ref, angulo, i = buenas[0]
    return _fuente(lista[i], angulo, ref, pts), ref


def _fuente(n, angulo="", ref=None, pts=None):
    url = n.get("url") or f'{WEB}nota-{n["slug"]}.html'
    extra = ""
    if angulo:
        extra += f"\nÁngulo sugerido para el gancho (lo que le cambia a quien mira): {angulo}\n"
    if ref:
        extra += (f'\nEste tema está pegando fuerte en otros contadores ("{str(ref.get("titulo", ""))[:140]}"). '
                  "Tomá de ahí qué engancha o el formato, nunca el texto ni sus números: los datos son los de la nota.\n")
    return {
        "id": f'portal:{n["slug"]}',
        "tipo": "noticia",
        "portal": True,
        "canal": "Ramacontable (nuestro portal)",
        "titulo": n.get("titulo", ""),
        "publicado": str(n.get("fecha", ""))[:10],
        "transcripcion": _material(n) + extra,
        "url": url,
        "score": f"nota del portal ({pts:g}/10)" if pts is not None else "nota del portal",
    }


def nota_para_video(datos, usados=(), dias=7, hoy=None):
    """Sin puntaje: la primera candidata (se usa solo si se apaga el puntaje con portal_puntaje_minimo = 0)."""
    lista = candidatas(datos, usados, dias, hoy)
    return _fuente(lista[0]) if lista else None


def vencimientos_semana(datos, hoy=None, dias=7):
    """Vencimientos de los próximos `dias` (para la futura serie «Vence esta semana»)."""
    hoy = hoy or util.ahora().date()
    hasta = (hoy + timedelta(days=dias)).isoformat()
    return [v for v in (datos or {}).get("vencimientos") or []
            if hoy.isoformat() <= str(v.get("fecha", "")) <= hasta]


def con_linea_blog(descripcion):
    """La descripción de un video contable arranca siempre con la línea del blog (una sola vez)."""
    d = (descripcion or "").replace(LINEA_BLOG, "").strip()
    return f"{LINEA_BLOG}\n\n{d}".strip()

