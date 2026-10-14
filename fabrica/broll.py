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
    if consulta in cache:
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
                             "url": h.get("pageURL", ""), "vertical": (v.get("height") or 0) > (v.get("width") or 0)})
        cache[consulta] = {"t": ahora, "hits": hits}
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
                                   "url": v.get("url", "")})
        if len(resultados) >= cantidad:
            break
    return resultados[:cantidad]


def bajar(link, destino):
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
        margen = max(0.0, total - dur - 0.3)
        desde = round(random.uniform(0.2, margen), 2) if margen > 0.4 else 0.0
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
