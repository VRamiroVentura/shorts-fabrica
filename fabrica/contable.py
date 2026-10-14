"""Serie contable: novedades de los sitios de contadores de referencia, sus videos de YouTube que rindieron
por encima de lo normal y (si está configurado) sus posts de Instagram que más pegaron.

Nunca se copia el texto de nadie: el material solo sirve para elegir el tema y el formato del día."""
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from . import util

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36",
      "Accept-Language": "es-AR,es;q=0.9"}
GRAPH = "https://graph.facebook.com/v25.0/"

# Temas que le tocan el bolsillo a mucha gente (peso = cuánto suma)
MASIVAS = {
    "monotribut": 3, "recategoriz": 3, "ganancias": 3, "aguinaldo": 3, "sueldo": 3, "salario": 2, "recibo": 2,
    "jubilac": 2, "alquil": 3, "inquilin": 3, "transferencia": 3, "billetera": 3, "mercado pago": 3,
    "mercado libre": 2, "cuenta bancaria": 2, "dolar": 3, "tarjeta": 2, "exterior": 2, "courier": 3, "temu": 3,
    "shein": 3, "control": 2, "embargo": 3, "multa": 2, "deuda": 2, "plan de pago": 2, "moratoria": 3,
    "inocencia fiscal": 3, "ahorro": 2, "colchon": 3, "bienes personales": 2, "factura": 2, "iva": 1,
    "empleada": 3, "casas particulares": 3, "servicio domestico": 3, "autonom": 2, "freelanc": 3,
    "vencimiento": 1, "prorroga": 2, "tope": 2, "deduc": 3, "reintegro": 3, "devolucion": 3, "percepcion": 2,
    "herencia": 2, "inmueble": 1, "auto": 1, "anses": 2, "auh": 2, "cuota": 1, "emprendedor": 2, "vender": 1,
    "compras": 2, "efectivo": 2, "simplificad": 2,
}
# Temas que solo le importan a contadores o a empresas grandes (restan)
NICHO = ["convenio", "cct", "uocra", "uom", "liquidador", "aplicativo", "regimen de informacion", "dashboard",
         "aniversario", "cumple", "inaugur", "evento", "jornada", "curso", "capacitaci", "webinar", "sociedad anonima",
         "directorio", "director", "balance", "resolucion tecnica", "auditor", "consejo profesional", "matricula",
         "obra social", "afiliado", "empleadores online", "presenta un nuevo", "lanza", "alianza"]
_EXCLUIR_URL = ("/tag/", "/tags/", "/categoria", "/category", "/autor", "/author", "/page/", "/seccion", "/buscar",
                "mailto:", "whatsapp", "javascript:", "#", "/contacto", "/suscri", "/login", "/publicidad")


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _hay(clave, texto):
    return re.search(r"\b" + re.escape(clave.strip()), texto) is not None


def _puntaje(titulo, texto=""):
    t, x = _norm(titulo), _norm(texto)[:1500]
    p = sum(w for k, w in MASIVAS.items() if _hay(k, t)) + sum(w for k, w in MASIVAS.items() if _hay(k, x)) * 0.3
    p -= 4 * sum(1 for k in NICHO if _hay(k, t))
    return round(p, 1)


def _limpio(html_texto):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", html_texto or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", unescape(t)).strip()


def _bajar(url):
    r = util.pedir("GET", url, intentos=2, espera=3, headers=UA, timeout=40)
    if r is None or r.status_code != 200:
        util.log("No pude leer", url, getattr(r, "status_code", "?"))
        return None
    if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
        r.encoding = r.apparent_encoding or "utf-8"
    return r


# ---------- Lectura de sitios (RSS o portada HTML) ----------

def _fecha(txt):
    if not txt:
        return None
    try:
        return parsedate_to_datetime(txt)
    except Exception:  # noqa
        pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except Exception:  # noqa
        return None


def _rss(contenido):
    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError:
        return None
    ns_content = "{http://purl.org/rss/1.0/modules/content/}encoded"
    atom = "{http://www.w3.org/2005/Atom}"
    items = []
    for it in raiz.iter("item"):
        items.append({
            "titulo": _limpio(it.findtext("title")),
            "url": (it.findtext("link") or "").strip(),
            "fecha": _fecha(it.findtext("pubDate")),
            "texto": _limpio(it.findtext(ns_content) or it.findtext("description")),
        })
    for it in raiz.iter(atom + "entry"):
        link = it.find(atom + "link")
        items.append({
            "titulo": _limpio(it.findtext(atom + "title")),
            "url": link.get("href", "") if link is not None else "",
            "fecha": _fecha(it.findtext(atom + "updated") or it.findtext(atom + "published")),
            "texto": _limpio(it.findtext(atom + "content") or it.findtext(atom + "summary")),
        })
    return items if (items or raiz.tag in ("rss", atom + "feed")) else None


class _Enlaces(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self._href, self._txt = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._txt = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href is not None:
            self._txt.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, re.sub(r"\s+", " ", "".join(self._txt)).strip()))
            self._href = None


def _portada(html_texto, base):
    p = _Enlaces()
    try:
        p.feed(html_texto)
    except Exception:  # noqa
        pass
    host = urlparse(base).netloc.replace("www.", "")
    vistos, items = set(), []
    for href, txt in p.links:
        if not href or not (35 <= len(txt) <= 220) or txt.count(" ") < 4 or txt.startswith(("http", "/", "www")):
            continue
        url = urljoin(base, href)
        u = urlparse(url)
        if u.netloc.replace("www.", "") != host or u.path.strip("/") == "" or any(x in url.lower() for x in _EXCLUIR_URL):
            continue
        clave = _norm(txt)
        if url in vistos or clave in vistos:
            continue
        vistos.update({url, clave})
        items.append({"titulo": txt, "url": url, "fecha": None, "texto": ""})
    return items


class _Articulo(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.parrafos, self._en_p, self._buf, self._salto = {}, [], 0, [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = (a.get("property") or a.get("name") or "").lower()
            if k in ("og:description", "description", "article:published_time", "og:title"):
                self.meta.setdefault(k, a.get("content") or "")
        elif tag in ("script", "style", "nav", "footer", "aside"):
            self._salto += 1
        elif tag == "p":
            self._en_p, self._buf = 1, []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "aside") and self._salto:
            self._salto -= 1
        elif tag == "p" and self._en_p:
            t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if len(t) > 60:
                self.parrafos.append(t)
            self._en_p = 0

    def handle_data(self, data):
        if self._en_p and not self._salto:
            self._buf.append(data)


def _detalle(url):
    r = _bajar(url)
    if r is None:
        return "", None
    a = _Articulo()
    try:
        a.feed(r.text)
    except Exception:  # noqa
        pass
    texto = " ".join([a.meta.get("og:description", "") or a.meta.get("description", "")] + a.parrafos)
    return texto.strip()[:1800], _fecha(a.meta.get("article:published_time"))


def noticias(sitios, usados, maximo=6, dias=12):
    """Titulares recientes de los sitios de referencia, priorizando lo que le importa a la gente común."""
    limite = util.ahora() - timedelta(days=dias)
    candidatos = []
    for s in sitios:
        r = _bajar(s["url"])
        if r is None:
            continue
        items = _rss(r.content)
        if items is None:
            items = _portada(r.text, s["url"])
        for orden, it in enumerate(items[:25]):
            if not it["titulo"] or not it["url"] or it["url"] in usados:
                continue
            if it["fecha"] and it["fecha"].astimezone(util.ZONA) < limite:
                continue
            candidatos.append(dict(it, sitio=s["nombre"], orden=orden, puntaje=_puntaje(it["titulo"], it["texto"])))
    candidatos = [c for c in candidatos if c["puntaje"] >= 2]
    candidatos.sort(key=lambda c: (-c["puntaje"], c["orden"]))
    elegidos, por_sitio = [], {}
    for c in candidatos:
        if len(elegidos) >= maximo or por_sitio.get(c["sitio"], 0) >= 4:
            continue
        if len(c["texto"]) < 300:
            texto, fecha = _detalle(c["url"])
            c["texto"] = texto or c["texto"]
            c["fecha"] = c["fecha"] or fecha
            if c["fecha"] and c["fecha"].astimezone(util.ZONA) < limite:
                continue
        por_sitio[c["sitio"]] = por_sitio.get(c["sitio"], 0) + 1
        elegidos.append({
            "id": c["url"], "tipo": "noticia", "canal": c["sitio"], "titulo": c["titulo"],
            "descripcion": c["texto"][:1800], "publicado": c["fecha"].date().isoformat() if c["fecha"] else "",
            "vistas": 0, "segundos": 0, "score": f'noticia ({c["puntaje"]})',
        })
    return elegidos


# ---------- Instagram de los contadores de referencia (opcional) ----------

def _media_de(usuario, token, mi_id):
    base = "caption,like_count,comments_count,media_type,media_product_type,permalink,timestamp"
    for campos in (base + ",view_count", base):
        r = util.pedir("GET", GRAPH + mi_id, intentos=2, timeout=60, params={
            "fields": f"business_discovery.username({usuario}){{followers_count,media.limit(40){{{campos}}}}}",
            "access_token": token})
        if r is not None and r.status_code == 200:
            bd = r.json().get("business_discovery", {})
            return bd.get("followers_count", 0), bd.get("media", {}).get("data", [])
    msg = ""
    try:
        msg = r.json()["error"]["message"]
    except Exception:  # noqa
        pass
    util.log(f"Instagram @{usuario}: no pude leerlo ({getattr(r, 'status_code', '?')}) {util.ocultar(msg)[:160]}")
    return 0, []


def _rendimiento(posts):
    """Calcula cuánto pegó cada post comparado con lo normal de esa cuenta."""
    hace = (util.ahora() - timedelta(days=365)).isoformat()
    out = []
    for p in posts:
        if (p.get("timestamp") or "") < hace:
            continue
        eng = int(p.get("like_count") or 0) + 3 * int(p.get("comments_count") or 0)
        out.append(dict(p, eng=eng))
    if len(out) < 6:
        return []
    meds = sorted(x["eng"] for x in out)
    med = max(meds[len(meds) // 2], 1)
    for x in out:
        x["veces"] = round(x["eng"] / med, 1)
    return sorted(out, key=lambda x: -x["veces"])


def instagram(usuarios, usados, maximo=2):
    token, mi_id = (util.secreto("IG_FB_TOKEN") or util.secreto("FB_PAGE_TOKEN")), util.secreto("IG_FB_ID")
    if not (token and mi_id):
        util.log("Instagram de referentes: sin IG_FB_TOKEN/IG_FB_ID, lo salteo")
        return []
    candidatos = []
    for u in usuarios:
        _, posts = _media_de(u, token, mi_id)
        for p in _rendimiento(posts)[:2]:
            if p["veces"] >= 1.8 and p.get("permalink") not in usados:
                candidatos.append(dict(p, usuario=u))
                break
    candidatos.sort(key=lambda p: -p["veces"])
    out = []
    for p in candidatos[:maximo]:
        caption = re.sub(r"\s+", " ", p.get("caption") or "").strip()
        formato = {"REELS": "Reel", "FEED": "foto", "STORY": "historia"}.get(p.get("media_product_type"), "")
        if p.get("media_type") == "CAROUSEL_ALBUM":
            formato = "carrusel"
        out.append({
            "id": p.get("permalink") or p.get("id"), "tipo": "instagram", "canal": "@" + p["usuario"],
            "titulo": caption[:90] or "(sin texto)", "descripcion": caption[:1500], "formato": formato or "post",
            "likes": p.get("like_count"), "comentarios": p.get("comments_count"), "vistas": p.get("view_count") or 0,
            "segundos": 0, "score": p["veces"], "publicado": (p.get("timestamp") or "")[:10],
        })
    return out


def resumen_instagram(usuarios):
    """Para el reporte semanal: qué les funcionó a los contadores de referencia."""
    token, mi_id = (util.secreto("IG_FB_TOKEN") or util.secreto("FB_PAGE_TOKEN")), util.secreto("IG_FB_ID")
    if not (token and mi_id):
        return ""
    bloques = []
    for u in usuarios:
        seguidores, posts = _media_de(u, token, mi_id)
        top = _rendimiento(posts)[:3]
        if not top:
            continue
        bloques.append(f"INSTAGRAM @{u} | {seguidores} seguidores\n" + "\n".join(
            f'  - {("carrusel" if t.get("media_type") == "CAROUSEL_ALBUM" else t.get("media_product_type", "post"))}: '
            f'"{re.sub(chr(10), " ", (t.get("caption") or "")[:110])}" ({t["veces"]} veces lo normal)' for t in top))
    return "\n\n".join(bloques)


# ---------- Todo junto ----------

def buscar(ref, clave_yt, usados, cantidad=2):
    from . import investigar
    fuentes = []
    try:
        fuentes += instagram(ref.get("instagram", []), usados, maximo=2)
    except Exception as e:  # noqa
        util.log("Instagram de referentes falló:", util.ocultar(e))
    if clave_yt and ref.get("youtube"):
        try:
            for f in investigar.fuera_de_serie(ref["youtube"], clave_yt, usados, 1):
                f["tipo"] = "youtube"
                f["transcripcion"] = investigar.transcripcion(f["id"])
                fuentes.append(f)
        except Exception as e:  # noqa
            util.log("YouTube de referentes falló:", util.ocultar(e))
    try:
        fuentes += noticias(ref.get("sitios", []), usados, maximo=6)
    except Exception as e:  # noqa
        util.log("Noticias de referentes fallaron:", util.ocultar(e))
    return fuentes
