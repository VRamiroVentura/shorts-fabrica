"""Videos de fondo: clips de stock gratis (Pixabay o Pexels; uso comercial permitido, sin atribución obligatoria).
Si no hay clave o no aparece nada que sirva, se arma un clip con una imagen (IA o placa con emoji)."""
import random
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageFilter

from . import util

PEXELS = "https://api.pexels.com/videos/search"
PIXABAY = "https://pixabay.com/api/videos/"
CACHE_PIXABAY = "data/pixabay_cache.json"   # Pixabay pide guardar las búsquedas 24 horas
W, H, FPS = 1080, 1920, 30


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("Falló " + " ".join(cmd[:4]) + ": " + r.stderr[-600:])
    return r.stdout


def _archivo(video):
    """Elige el archivo más liviano que alcance para 1080x1920 (o lo más parecido)."""
    archivos = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("link")]
    if not archivos:
        return None
    vertical = [f for f in archivos if (f.get("height") or 0) >= (f.get("width") or 0)]
    pool = vertical or archivos

    def costo(f):
        alto = max(f.get("height") or 0, f.get("width") or 0)
        return (0 if 1200 <= alto <= 2200 else 1, abs(alto - 1920))
    return sorted(pool, key=costo)[0]


def proveedor():
    """Qué banco de videos usar según las claves cargadas. Devuelve (nombre, función de búsqueda, clave)."""
    if util.secreto("PIXABAY_API_KEY"):
        return "Pixabay", buscar_pixabay, util.secreto("PIXABAY_API_KEY")
    if util.secreto("PEXELS_API_KEY"):
        return "Pexels", buscar, util.secreto("PEXELS_API_KEY")
    return None, None, None


def _rendicion_pixabay(videos):
    """De las versiones que da Pixabay, la más chica que alcance para 1080x1920 al recortar."""
    opciones = [v for v in (videos or {}).values() if v.get("url")]
    if not opciones:
        return None

    def costo(v):
        alto = min(v.get("width") or 0, v.get("height") or 0)  # el lado corto es el que limita al recortar
        return (0 if alto >= 1000 else 1, -(1 if (v.get("height") or 0) > (v.get("width") or 0) else 0),
                v.get("size") or 0)
    return sorted(opciones, key=costo)[0]


def buscar_pixabay(consulta, clave, usados, cantidad=3, minimo=2.0):
    """Devuelve hasta `cantidad` videos de Pixabay para la consulta, sin repetir ids."""
    cache = util.leer_json(CACHE_PIXABAY, {}) or {}
    ahora = time.time()
    cache = {k: v for k, v in cache.items() if ahora - v.get("t", 0) < 86400}
    if consulta in cache and cache[consulta].get("v") == 2:
        hits = cache[consulta]["hits"]
    else:
        r = util.pedir("GET", PIXABAY, intentos=2, timeout=40,
                       params={"key": clave, "q": consulta[:100], "per_page": 20, "safesearch": "true",
                               "video_type": "film"})
        if r is None or r.status_code != 200:
            util.log("Pixabay", consulta, getattr(r, "status_code", "?"))
            return []
        hits = []
        for h in r.json().get("hits", []):
            v = _rendicion_pixabay(h.get("videos"))
            if v:
                hits.append({"id": f'pixabay-{h["id"]}', "link": v["url"], "dur": h.get("duration") or 0,
                             "url": h.get("pageURL", ""), "vertical": (v.get("height") or 0) > (v.get("width") or 0),
                             "tags": h.get("tags", ""), "thumb": v.get("thumbnail") or ""})
        cache[consulta] = {"t": ahora, "hits": hits, "v": 2}
        util.guardar_json(CACHE_PIXABAY, cache)
    elegibles = [h for h in hits if h["id"] not in usados and h["dur"] >= minimo]
    elegibles.sort(key=lambda h: not h.get("vertical"))  # primero los verticales
    return elegibles[:cantidad]


def buscar(consulta, clave, usados, cantidad=3, minimo=2.0):
    """Devuelve hasta `cantidad` videos de Pexels para la consulta, sin repetir ids."""
    resultados = []
    for orientacion in ("portrait", "landscape"):
        r = util.pedir("GET", PEXELS, intentos=2, timeout=40, headers={"Authorization": clave},
                       params={"query": consulta, "orientation": orientacion, "size": "small", "per_page": 15})
        if r is None or r.status_code != 200:
            util.log("Pexels", consulta, getattr(r, "status_code", "?"))
            continue
        for v in r.json().get("videos", []):
            if v.get("id") in usados or (v.get("duration") or 0) < minimo:
                continue
            f = _archivo(v)
            if f:
                resultados.append({"id": v["id"], "link": f["link"], "dur": v.get("duration") or 0,
                                   "url": v.get("url", ""), "thumb": v.get("image", ""),
                                   "tags": (v.get("url", "").rstrip("/").split("/")[-1]).replace("-", " ")})
        if len(resultados) >= cantidad:
            break
    return resultados[:cantidad]


def bajar(link, destino):
    if not str(link).startswith("http"):  # clip propio del repo
        return Path(link)
    r = util.pedir("GET", link, intentos=3, timeout=120, stream=True)
    if r is None or r.status_code != 200:
        raise RuntimeError(f"No pude bajar el clip ({getattr(r, 'status_code', '?')})")
    with open(destino, "wb") as f:
        for parte in r.iter_content(1 << 20):
            f.write(parte)
    return destino


def recortar(origen, dur, destino, desde=None):
    """Toma `dur` segundos del clip y lo deja vertical 1080x1920, 30 fps, un poco oscurecido."""
    total = 0.0
    try:
        total = float(_run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(origen)]).strip())
    except Exception:  # noqa
        pass
    if desde is None:
        # Muchos clips traen un título al principio o un cartel al final: se toma un tramo del medio.
        ini = min(max(1.5, total * 0.2), max(0.0, total - dur - 1.0))
        fin = total - dur - 1.0
        desde = round(random.uniform(ini, fin), 2) if fin > ini else round(max(0.0, min(ini, total - dur)), 2)
    flt = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
           "eq=brightness=-0.05:saturation=1.08,format=yuv420p")
    entrada = ["-stream_loop", "-1"] if total and total < dur + desde else []
    _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{desde:.2f}", *entrada, "-i", str(origen), "-t", f"{dur:.3f}",
          "-vf", flt, "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(destino)])
    return destino


def clip_de_imagen(img, dur, destino, acercar=True):
    """Imagen cuadrada → fondo vertical desenfocado + imagen al centro con zoom lento."""
    base = Image.open(img).convert("RGB")
    fondo = base.resize((H, H)).crop(((H - W) // 2, 0, (H - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(40))
    fondo = Image.eval(fondo, lambda v: int(v * 0.72))
    lado = 1000
    fondo.paste(base.resize((lado, lado), Image.LANCZOS), ((W - lado) // 2, (H - lado) // 2 - 60))
    compuesto = Path(destino).with_suffix(".png")
    fondo.save(compuesto)
    cuadros = max(1, round(dur * FPS))
    z = f"1+0.08*on/{cuadros}" if acercar else f"1.08-0.08*on/{cuadros}"
    flt = (f"scale={int(W * 1.5)}:{int(H * 1.5)},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
           f":d={cuadros}:s={W}x{H}:fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(compuesto),
          "-vf", flt, "-frames:v", str(cuadros), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "20", str(destino)])
    return destino


# ---------------------------------------------------------------- que se vea de acá
# Lugares y monedas de otros países: si aparecen en las etiquetas del clip, se descarta.
_AFUERA = {
    "euro", "euros", "rupee", "rupees", "rupia", "yen", "yuan", "renminbi", "rmb", "won", "pound", "pounds",
    "sterling", "ruble", "rubles", "lira", "dirham", "riyal", "baht", "rupiah", "dong", "peso mexicano",
    "india", "indian rupee", "china", "japan", "tokyo", "korea", "seoul", "vietnam", "thailand", "bangkok",
    "indonesia", "bali", "philippines", "manila", "dubai", "abu dhabi", "saudi", "qatar", "doha", "morocco",
    "marrakech", "egypt", "cairo", "turkey", "istanbul", "iran", "pakistan", "bangladesh", "nigeria", "kenya",
    "russia", "moscow", "ukraine", "poland", "germany", "berlin", "france", "paris", "italy", "rome", "venice",
    "london", "england", "new york", "manhattan", "times square", "las vegas", "hong kong", "singapore", "taiwan",
    "mexico", "brazil", "rio de janeiro", "sao paulo", "mosque", "pagoda", "eiffel", "big ben", "taj mahal",
}


def de_afuera(clip):
    texto = " " + (str(clip.get("tags", "")) + " " + str(clip.get("url", "")).replace("-", " ")).lower() + " "
    texto = texto.replace(",", " ").replace("/", " ")
    return any(f" {x} " in texto for x in _AFUERA)


# Clips propios: los que subas a assets/clips (grabados con el celu en Argentina) tienen prioridad.
_SINONIMOS = {
    "tarjeta": ["card", "credit", "debit", "posnet"], "celular": ["phone", "smartphone", "mobile"],
    "plata": ["money", "cash", "pesos", "billetes", "dolares"], "pesos": ["money", "cash", "plata", "billetes"],
    "dolar": ["dollar", "dollars", "dolares", "usd"], "dolares": ["dollar", "dollars", "dolar", "usd"],
    "billetes": ["money", "cash", "bills", "plata"], "calle": ["street", "city", "ciudad"],
    "ciudad": ["city", "street", "calle"], "super": ["supermarket", "grocery", "supermercado"],
    "supermercado": ["supermarket", "grocery", "super"], "ticket": ["receipt", "factura"],
    "factura": ["receipt", "invoice", "ticket"], "notebook": ["laptop", "computer", "compu"],
    "compu": ["laptop", "computer", "notebook"], "calculadora": ["calculator"], "trabajo": ["work", "office"],
    "oficina": ["office", "work"], "banco": ["bank"], "kiosco": ["kiosk", "store", "shop"],
    "negocio": ["store", "shop"], "mate": ["mate"], "sueldo": ["salary", "money"], "alquiler": ["rent", "house"],
    "laplata": ["ciudad", "city", "street", "calle"], "caba": ["ciudad", "city", "street", "calle"],
}


def _palabras(t):
    import unicodedata
    t = unicodedata.normalize("NFD", str(t).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {w for w in __import__("re").split(r"[^a-z0-9]+", t) if len(w) > 2}


FOTOS = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG", "*.webp")


def es_foto(ruta):
    return Path(str(ruta)).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")


def clip_de_foto(foto, dur, destino, acercar=True):
    """Foto propia (vertical u horizontal) → clip vertical con zoom lento; si es apaisada, va al centro con el
    mismo fondo desenfocado atrás."""
    im = Image.open(foto)
    try:
        from PIL import ImageOps
        im = ImageOps.exif_transpose(im)  # las fotos del celu vienen giradas en el EXIF
    except Exception:  # noqa
        pass
    im = im.convert("RGB")
    if im.width / im.height <= 0.8:  # vertical: llena la pantalla
        k = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        x, y = (im.width - W) // 2, (im.height - H) // 2
        lienzo = im.crop((x, y, x + W, y + H))
    else:
        k = max(W / im.width, H / im.height)
        lienzo = im.resize((round(im.width * k), round(im.height * k))).filter(ImageFilter.GaussianBlur(40))
        x, y = (lienzo.width - W) // 2, (lienzo.height - H) // 2
        lienzo = Image.eval(lienzo.crop((x, y, x + W, y + H)), lambda v: int(v * 0.7))
        frente = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
        lienzo.paste(frente, (0, (H - frente.height) // 2 - 60))
    compuesto = Path(destino).with_suffix(".png")
    lienzo.save(compuesto)
    cuadros = max(1, round(dur * FPS))
    z = f"1+0.08*on/{cuadros}" if acercar else f"1.08-0.08*on/{cuadros}"
    flt = (f"scale={int(W * 1.5)}:{int(H * 1.5)},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
           f":d={cuadros}:s={W}x{H}:fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(compuesto),
          "-vf", flt, "-frames:v", str(cuadros), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "20", str(destino)])
    return destino


def propios():
    carpeta = util.RAIZ / "assets" / "clips"
    if not carpeta.exists():
        return []
    out = []
    tipos = ("*.mp4", "*.mov", "*.MOV", "*.MP4") + FOTOS
    for f in sorted({x for t in tipos for x in carpeta.rglob(t)}):
        nombre = f.stem.lower().replace("la-plata", "laplata").replace("la_plata", "laplata")
        claves = _palabras(nombre) | _palabras(f.parent.name if f.parent != carpeta else "")
        for k in list(claves):
            claves |= set(_SINONIMOS.get(k, []))
        out.append({"id": f"propio-{f.stem}", "link": str(f), "dur": 99, "tags": " ".join(sorted(claves)),
                    "claves": claves, "thumb": "", "propio": True, "foto": es_foto(f)})
    return out


def propios_para(lista, escena):
    pedido = _palabras(escena.get("texto", "")) | _palabras(" ".join(escena.get("broll") or []))
    puntuados = [(len(c["claves"] & pedido), c) for c in lista]
    return [c for p, c in sorted(puntuados, key=lambda x: -x[0]) if p > 0][:3]


def miniatura(clip, destino):
    """Imagen chica del clip para que la IA juzgue si sirve."""
    try:
        if clip.get("thumb", "").startswith("http"):
            r = util.pedir("GET", clip["thumb"], intentos=2, timeout=30)
            if r is None or r.status_code != 200:
                return None
            Path(destino).write_bytes(r.content)
        elif es_foto(clip["link"]):
            Image.open(clip["link"]).convert("RGB").save(destino, "JPEG")
        else:
            _run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", str(clip["link"]), "-frames:v", "1", str(destino)])
        im = Image.open(destino).convert("RGB")
        im.thumbnail((320, 320))
        im.save(destino, "JPEG", quality=70)
        return destino
    except Exception as e:  # noqa
        util.log("Sin miniatura:", util.ocultar(e))
        return None


def clip_tarjeta(emoji, dur, destino, acercar=True):
    """Para frases abstractas: fondo oscuro de marca con un emoji grande arriba de los subtítulos."""
    from . import marca as mk
    im = Image.new("RGB", (W, H), (18, 18, 18))
    franja = Image.new("RGB", (W, 10), (255, 212, 0))
    im.paste(franja, (0, 0))
    if not mk.pegar_emoji(im, emoji or "💡", (W // 2, 720), 560):
        mk.pegar_emoji(im, "💡", (W // 2, 720), 560)
    compuesto = Path(destino).with_suffix(".png")
    im.save(compuesto)
    cuadros = max(1, round(dur * FPS))
    z = f"1+0.06*on/{cuadros}" if acercar else f"1.06-0.06*on/{cuadros}"
    flt = (f"scale={int(W * 1.5)}:{int(H * 1.5)},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
           f":d={cuadros}:s={W}x{H}:fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(compuesto),
          "-vf", flt, "-frames:v", str(cuadros), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "20", str(destino)])
    return destino


# ---------------------------------------------------------------- postales de Argentina
# Tomas lindas de ver (drones, paisajes, lugares típicos) para enganchar la vista entre frase y frase.
POSTALES = ["Buenos Aires aerial", "Obelisco Buenos Aires", "Puerto Madero Buenos Aires", "Caminito La Boca",
            "Perito Moreno glacier", "Patagonia Argentina", "Iguazu falls", "Bariloche Argentina",
            "Mar del Plata", "Ushuaia", "Aconcagua", "Salta Argentina", "Jujuy Argentina", "Mendoza vineyards",
            "El Calafate", "Tierra del Fuego", "Cordoba Argentina", "mate gourd", "asado grill", "tango Buenos Aires"]
_DE_ACA = ["argentina", "argentine", "buenos aires", "patagonia", "iguazu", "iguazú", "bariloche", "ushuaia",
           "mendoza", "salta", "jujuy", "cordoba", "córdoba", "mar del plata", "perito moreno", "obelisco",
           "la boca", "caminito", "puerto madero", "aconcagua", "tierra del fuego", "calafate", "fitz roy",
           "el chalten", "chaltén", "humahuaca", "purmamarca", "mate", "asado", "tango", "gaucho", "pampa"]


def es_de_aca(clip):
    texto = (str(clip.get("tags", "")) + " " + str(clip.get("url", "")).replace("-", " ")).lower()
    return any(x in texto for x in _DE_ACA)


def postales(buscar_fn, clave, cantidad=8):
    """Busca tomas de Argentina (solo las que en sus etiquetas dicen que son de acá)."""
    out, vistos = [], set()
    for q in random.sample(POSTALES, len(POSTALES)):
        if len(out) >= cantidad:
            break
        try:
            for c in buscar_fn(q, clave, set(), cantidad=3, minimo=4):
                if c["id"] not in vistos and es_de_aca(c) and not de_afuera(c):
                    vistos.add(c["id"])
                    out.append(dict(c, postal=True))
        except Exception as e:  # noqa
            util.log("Postal falló:", util.ocultar(e))
    return out[:cantidad]
