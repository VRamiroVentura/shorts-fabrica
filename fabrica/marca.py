"""Identidad visual de la cuenta: colores, tipografías, emojis y texto."""
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTS = RAIZ / "fonts"

AMARILLO = (255, 212, 0)
NEGRO = (17, 17, 17)
BLANCO = (255, 255, 255)
CREMA = (255, 248, 231)
GRIS = (90, 90, 90)

_BUSQUEDA = {
    "titulo": ["Anton-Regular.ttf"],
    "bold": ["Poppins-Bold.ttf", "DejaVuSans-Bold.ttf"],
    "semibold": ["Poppins-SemiBold.ttf", "Poppins-Medium.ttf", "DejaVuSans-Bold.ttf"],
    "regular": ["Poppins-Regular.ttf", "Poppins-Medium.ttf", "DejaVuSans.ttf"],
}
_CARPETAS = [FONTS, Path("/usr/share/fonts/truetype/google-fonts"), Path("/usr/share/fonts/truetype/dejavu")]


@lru_cache(maxsize=None)
def _ruta_fuente(estilo):
    nombres = list(_BUSQUEDA[estilo])
    if estilo == "titulo":
        nombres += _BUSQUEDA["bold"]
    for n in nombres:
        for c in _CARPETAS:
            if (c / n).exists():
                return str(c / n)
    return None


@lru_cache(maxsize=None)
def fuente(estilo, size):
    ruta = _ruta_fuente(estilo)
    return ImageFont.truetype(ruta, size) if ruta else ImageFont.load_default()


def es_anton():
    r = _ruta_fuente("titulo") or ""
    return "Anton" in r


# ------------------------------------------------------------------ texto
def partir(draw, texto, fnt, ancho):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if draw.textlength(prueba, font=fnt) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def ajustar(draw, texto, estilo, ancho, max_lineas, inicio, minimo=28):
    """Busca el tamaño de letra más grande que entra en max_lineas."""
    size = inicio
    while size >= minimo:
        f = fuente(estilo, size)
        lineas = partir(draw, texto, f, ancho)
        if len(lineas) <= max_lineas:
            return f, lineas
        size -= 4
    f = fuente(estilo, minimo)
    return f, partir(draw, texto, f, ancho)[:max_lineas]


def escribir(draw, xy, lineas, fnt, color, interlineado=1.15, anchor="la", **kw):
    x, y = xy
    alto = fnt.size * interlineado
    for ln in lineas:
        draw.text((x, y), ln, font=fnt, fill=color, anchor=anchor, **kw)
        y += alto
    return y


# ------------------------------------------------------------------ emojis
_EMOJI_FONTS = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
]


def _emoji_por_fuente(e):
    for ruta in _EMOJI_FONTS:
        if os.path.exists(ruta):
            try:
                f = ImageFont.truetype(ruta, 109)
                tmp = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
                ImageDraw.Draw(tmp).text((80, 80), e, font=f, embedded_color=True, anchor="mm")
                bbox = tmp.getbbox()
                return tmp.crop(bbox) if bbox else None
            except Exception:  # noqa
                return None
    return None


def _emoji_twemoji(e):
    try:
        import cairosvg, requests, io  # noqa
        cod = "-".join(f"{ord(c):x}" for c in e if ord(c) != 0xFE0F)
        url = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/svg/{cod}.svg"
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        png = cairosvg.svg2png(bytestring=r.content, output_width=512, output_height=512)
        return Image.open(io.BytesIO(png)).convert("RGBA")
    except Exception:  # noqa
        return None


@lru_cache(maxsize=64)
def emoji(e, size):
    """Devuelve el emoji como imagen RGBA del tamaño pedido, o None."""
    e = (e or "").strip()
    if not e:
        return None
    img = _emoji_por_fuente(e) or _emoji_twemoji(e)
    if img is None:
        return None
    return img.resize((size, size), Image.LANCZOS)


def pegar_emoji(img, e, centro, size):
    em = emoji(e, size)
    if em is None:
        return False
    img.paste(em, (int(centro[0] - size / 2), int(centro[1] - size / 2)), em)
    return True
