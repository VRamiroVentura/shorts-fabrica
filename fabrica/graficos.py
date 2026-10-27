"""Escenas gráficas animadas: carteles, números, sellos, tickets y listas con tildes, en vez de un clip de stock.

Se usan en algunas escenas de cualquier video (las elige la IA con el campo "grafico" de la escena) para explicar
mejor un número, una lista, una comparación o una palabra clave. Dos fondos:
  - "cuaderno": hoja de libro contable (impuestos y temas de contador).
  - "oscuro": fondo carbón con puntitos y un brillo amarillo que se mueve (historias y todo lo demás).
Los subtítulos y la marca los pone el montaje después, así que acá se deja libre la zona de abajo (y > 1040).

Tipos (campos):
  resaltado   {"texto", "sello"?, "sello_color": "rojo"|"verde"?}
  numero      {"rotulo", "valor", "nota"?}
  ticket      {"lineas": [["texto", "+"|"−"|"" ], ...], "sello"?, "sello_color"?}
  lista       {"titulo", "items": [...]}
  comparacion {"arriba", "abajo", "rotulo"?}       (una cosa → la otra, con flecha)
"""
import math
import random
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import util

W, H, FPS = 1080, 1920, 30
AMA = (255, 212, 0)
NEGRO = (20, 20, 22)
PAPEL = (250, 245, 232)
RENGLON = (170, 200, 225)
ROJO = (190, 35, 45)
VERDE = (30, 140, 80)
TIPOS = ("resaltado", "numero", "ticket", "lista", "comparacion")
ZONA = (360, 1010)  # de dónde a dónde puede ir lo gráfico (arriba va la serie, abajo los subtítulos)

_CARPETAS = [util.RAIZ / "fonts", Path("/usr/share/fonts/truetype/google-fonts"),
             Path("/usr/share/fonts/truetype/dejavu")]
_FUENTES = {"bold": ["Poppins-Bold.ttf", "DejaVuSans-Bold.ttf"],
            "medium": ["Poppins-SemiBold.ttf", "Poppins-Medium.ttf", "DejaVuSans-Bold.ttf"],
            "cond": ["Anton-Regular.ttf", "Poppins-Black.ttf", "Poppins-ExtraBold.ttf", "DejaVuSans-Bold.ttf"],
            "mono": ["SpaceMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"]}


@lru_cache(maxsize=None)
def _ruta(estilo):
    for n in _FUENTES[estilo]:
        for c in _CARPETAS:
            if (c / n).exists():
                return str(c / n)
    return None


@lru_cache(maxsize=None)
def F(estilo, size):
    r = _ruta(estilo)
    return ImageFont.truetype(r, size) if r else ImageFont.load_default()


def clamp(x):
    return max(0.0, min(1.0, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    return 1 + 2.6 * (x - 1) ** 3 + 1.6 * (x - 1) ** 2


# ------------------------------------------------------------------ fondos
@lru_cache(maxsize=2)
def _hoja():
    rnd = random.Random(2)
    im = Image.new("RGB", (W + 200, H + 200), PAPEL)
    d = ImageDraw.Draw(im)
    for _ in range(9000):
        x, y, c = rnd.randint(0, W + 199), rnd.randint(0, H + 199), rnd.randint(-10, 4)
        d.point((x, y), fill=(PAPEL[0] + c, PAPEL[1] + c, PAPEL[2] + c))
    for y in range(40, H + 200, 64):
        d.line([0, y, W + 200, y], fill=RENGLON, width=2)
    for x in (150, 158):
        d.line([x, 0, x, H + 200], fill=(225, 95, 95), width=2)
    for x in (W - 230, W - 60):
        d.line([x, 0, x, H + 200], fill=(150, 195, 160), width=2)
    return im


# Colores del fondo oscuro: mismo dibujo, distinto color según lo que se cuenta.
COLORES = {
    "carbon": (22, 22, 24),    # neutro
    "azul": (14, 28, 52),      # explicar, datos, información
    "verde": (12, 44, 30),     # lo que te conviene: ahorro, beneficio, plata que vuelve
    "bordo": (58, 14, 22),     # lo que te cuesta: alerta, error, multa, estafa
    "violeta": (36, 18, 56),   # historias y curiosidades
}


@lru_cache(maxsize=8)
def _carbon(color="carbon"):
    base = COLORES.get(color, COLORES["carbon"])
    im = Image.new("RGB", (W + 200, H + 200), base)
    d = ImageDraw.Draw(im)
    punto = tuple(min(255, c + 26) for c in base)
    for y in range(0, H + 200, 44):  # puntitos (no grilla)
        for x in range((y // 44) % 2 * 22, W + 200, 44):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=punto)
    return im


def fondo(estilo, t, semilla=0, color="carbon"):
    if estilo == "cuaderno":
        ox, oy = 100 + 30 * math.sin(t * 0.35 + semilla), 68 + 20 * math.sin(t * 0.25 + semilla) + (t * 12) % 64
        return _hoja().crop((int(ox), int(oy), int(ox) + W, int(oy) + H)).convert("RGBA")
    ox, oy = 100 + 25 * math.sin(t * 0.3 + semilla), 100 + (t * 10) % 44
    im = _carbon(color).crop((int(ox), int(oy), int(ox) + W, int(oy) + H)).convert("RGBA")
    # brillo amarillo suave que se pasea (la marca de la cuenta)
    gx = W * (0.5 + 0.35 * math.sin(t * 0.5 + semilla))
    gy = H * (0.35 + 0.1 * math.cos(t * 0.4 + semilla))
    b = _brillo()
    _pegar_recortado(im, b, gx, gy)
    return im


@lru_cache(maxsize=1)
def _brillo():
    b = Image.new("RGBA", (1300, 1300), (0, 0, 0, 0))
    ImageDraw.Draw(b).ellipse([230, 230, 1070, 1070], fill=AMA + (38,))
    return b.filter(ImageFilter.GaussianBlur(160))


def _pegar_recortado(im, b, cx, cy):
    x, y = int(cx - b.width / 2), int(cy - b.height / 2)
    x0, y0 = max(0, -x), max(0, -y)
    x1, y1 = min(b.width, W - x), min(b.height, H - y)
    if x1 > x0 and y1 > y0:
        im.alpha_composite(b.crop((x0, y0, x1, y1)), (x + x0, y + y0))


# ------------------------------------------------------------------ piezas
def _sombra(im, off=10, blur=14, alpha=80, color=(0, 0, 0)):
    w, h = im.size
    c = Image.new("RGBA", (w + 2 * blur + off, h + 2 * blur + off), (0, 0, 0, 0))
    s = Image.new("RGBA", im.size, color + (0,))
    s.putalpha(im.getchannel("A").point(lambda a: a * alpha // 255))
    c.alpha_composite(s, (blur + off, blur + off))
    if blur:
        c = c.filter(ImageFilter.GaussianBlur(blur / 2))
    c.alpha_composite(im, (blur, blur))
    return c


def _texto(txt, estilo, size, color=NEGRO, max_ancho=None):
    f = F(estilo, size)
    while max_ancho and f.getlength(txt) > max_ancho and size > 30:
        size -= 4
        f = F(estilo, size)
    bb = f.getbbox(txt)
    im = Image.new("RGBA", (max(1, bb[2] - bb[0] + 12), max(1, bb[3] - bb[1] + 12)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((6 - bb[0], 6 - bb[1]), txt, font=f, fill=color)
    return im


def _tarjeta(contenido, estilo, pad=40, fondo_color=None):
    """Tarjeta donde va el contenido: papel blanco en el cuaderno; blanco con borde negro y sombra amarilla en el oscuro."""
    w, h = contenido.width + 2 * pad, contenido.height + 2 * pad
    color = fondo_color or ((255, 252, 240) if estilo == "cuaderno" else (250, 248, 240))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if estilo == "cuaderno":
        d.rounded_rectangle([0, 0, w - 1, h - 1], 14, fill=color)
        d.rectangle([0, 0, w, 12], fill=AMA)
        im.alpha_composite(contenido, (pad, pad))
        return _sombra(im, 10, 14, 70)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 16, fill=color, outline=NEGRO, width=6)
    im.alpha_composite(contenido, (pad, pad))
    return _sombra(im, 16, 0, 255, AMA)  # sombra amarilla dura, corrida


def _sello(txt, color, seed=4):
    t = _texto(txt.upper(), "bold", 70, color, max_ancho=760)
    pad = 32
    w, h = t.width + 2 * pad, t.height + 2 * pad - 10
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, w - 5, h - 5], 18, outline=color, width=10)
    d.rounded_rectangle([18, 18, w - 19, h - 19], 10, outline=color, width=3)
    im.alpha_composite(t, (pad, pad - 6))
    rnd = random.Random(seed)
    m = Image.new("L", im.size, 255)
    dm = ImageDraw.Draw(m)
    for _ in range(int(w * h / 500)):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(1, 4)
        dm.ellipse([x - r, y - r, x + r, y + r], fill=rnd.randint(0, 120))
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), m))
    return im


def _color_sello(nombre, estilo="cuaderno"):
    verde = str(nombre or "").lower().startswith("verde")
    if estilo == "oscuro":  # tinta más clara para que se lea sobre fondo oscuro
        return (90, 215, 140) if verde else (255, 95, 95)
    return VERDE if verde else ROJO


def _flecha(color, h=150):
    im = Image.new("RGBA", (90, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([45, 0, 45, h - 40], fill=color, width=14)
    d.polygon([(10, h - 52), (80, h - 52), (45, h - 2)], fill=color)
    return im


def _pegar(im, p, cx, cy, rot=0.0, esc=1.0, alfa=1.0):
    if esc != 1:
        p = p.resize((max(1, int(p.width * esc)), max(1, int(p.height * esc))), Image.BICUBIC)
    if rot:
        p = p.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alfa < 1:
        p = p.copy()
        p.putalpha(p.getchannel("A").point(lambda a: int(a * alfa)))
    im.alpha_composite(p, (int(cx - p.width / 2), int(cy - p.height / 2)))


def _pop(im, p, cx, cy, t, t0, rot=0.0):
    """Aparece creciendo con un mini rebote y después flota apenas."""
    if t < t0:
        return
    k = t - t0
    esc = (0.55 + 0.45 * ease_back(k / 0.3)) * (1 + 0.012 * math.sin(k * 1.1))
    _pegar(im, p, cx, cy, rot + 0.7 * math.sin(k * 0.8), esc, clamp(k / 0.12))


def _sellar(im, p, cx, cy, t, t0, rot):
    if t < t0:
        return False
    k = (t - t0) / 0.14
    if k < 1:
        _pegar(im, p, cx, cy, rot, 1.9 - 0.9 * ease_out(k), clamp(k * 1.5))
        return False
    _pegar(im, p, cx, cy, rot)
    return t - t0 < 0.22


# ------------------------------------------------------------------ cada tipo
def _resaltado(g, estilo, dur):
    palabra = str(g.get("texto", ""))[:22].upper()
    estilo_letra = "cond" if estilo == "oscuro" else "bold"
    claro = _texto(palabra, estilo_letra, 150, NEGRO if estilo == "cuaderno" else (255, 255, 255), max_ancho=900)
    oscuro = _texto(palabra, estilo_letra, 150, NEGRO, max_ancho=900)
    sello = _sello(g["sello"], _color_sello(g.get("sello_color"), estilo), 5) if g.get("sello") else None

    def cuadro(im, t):
        w, h = claro.size
        k = ease_out((t - 0.15) / 0.4)
        capa = Image.new("RGBA", (w + 60, h + 24), (0, 0, 0, 0))
        x2 = 10 + (w + 40) * k
        if estilo == "cuaderno":  # resaltador por la mitad de abajo de la palabra
            if k > 0:
                ImageDraw.Draw(capa).polygon([(10, h * 0.45), (x2, h * 0.38), (x2 + 6, h + 6), (16, h + 12)],
                                             fill=AMA + (215,))
            capa.alpha_composite(claro, (30, 4))
        else:  # en el oscuro: bloque amarillo entero y la letra se vuelve negra donde ya pasó
            capa.alpha_composite(claro, (30, 4))
            if k > 0:
                bloque = Image.new("RGBA", capa.size, (0, 0, 0, 0))
                ImageDraw.Draw(bloque).polygon([(10, 2), (x2, 0), (x2 + 6, h + 20), (16, h + 22)], fill=AMA + (255,))
                negro = Image.new("RGBA", capa.size, (0, 0, 0, 0))
                negro.alpha_composite(oscuro, (30, 4))
                mascara = bloque.getchannel("A")
                capa = Image.composite(bloque, capa, mascara)
                capa.alpha_composite(Image.composite(negro, Image.new("RGBA", capa.size, (0, 0, 0, 0)), mascara))
        _pegar(im, capa, W / 2, 560, -2.0 + 0.6 * math.sin(t * 0.7))
        return _sellar(im, sello, W / 2 + 110, 800, t, min(1.1, dur * 0.4), 8) if sello else False
    return cuadro


def _numero(g, estilo, dur):
    import re
    rot = _texto(str(g.get("rotulo", ""))[:30].upper(), "mono", 44, (90, 90, 90), max_ancho=880)
    valor = str(g.get("valor", ""))[:18]
    nota = (_texto(str(g.get("nota", ""))[:40], "medium", 34, (110, 110, 110) if estilo == "cuaderno" else
                   (200, 200, 200), max_ancho=880) if g.get("nota") else None)
    m = re.match(r"^(\D*)([\d.]+)(.*)$", valor)  # "$126.610.838 / año" → cuenta de 0 hasta el número
    objetivo = int(m.group(2).replace(".", "")) if m and m.group(2).replace(".", "").isdigit() else None

    def cuadro(im, t):
        k = ease_out((t - 0.35) / 0.7)
        mostrar = valor
        if objetivo is not None and k < 1:
            mostrar = m.group(1) + f"{int(objetivo * k):,}".replace(",", ".") + m.group(3)
        num = _texto(mostrar, "cond", 190, NEGRO, max_ancho=860)
        cont = Image.new("RGBA", (max(num.width, rot.width, 600) + 20, rot.height + num.height + 30), (0, 0, 0, 0))
        cont.alpha_composite(rot, ((cont.width - rot.width) // 2, 0))
        cont.alpha_composite(num, ((cont.width - num.width) // 2, rot.height + 20))
        _pop(im, _tarjeta(cont, estilo), W / 2, 600, t, 0.1, -1.2)
        if nota and t > 0.9:
            _pegar(im, nota, W / 2, 860, 0, 1, clamp((t - 0.9) / 0.3))
        return False
    return cuadro


def _ticket(g, estilo, dur):
    lineas = [(str(a)[:16], str(b)[:7]) for a, b in (g.get("lineas") or [])[:5] if a]
    f = F("mono", 52)
    ancho = 760
    alto = 80 + 84 * len(lineas) + 40
    tk = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(tk)
    pts = [(0, 0), (ancho, 0), (ancho, alto - 24)]
    paso = ancho / 12
    for i in range(12, 0, -1):
        pts += [(paso * i - paso / 2, alto), (paso * (i - 1), alto - 24)]
    d.polygon(pts, fill=(255, 255, 255))
    for i, (izq, der) in enumerate(lineas):
        y = 50 + i * 84
        color = ROJO if der in ("-", "−") else NEGRO
        d.text((36, y), izq.upper(), font=f, fill=color)
        if der:
            d.text((ancho - 36 - f.getlength(der), y), der, font=f, fill=color)
    tk = _sombra(tk, 8, 12, 60)
    sello = _sello(g["sello"], _color_sello(g.get("sello_color"), estilo), 8) if g.get("sello") else None

    def cuadro(im, t):
        k = ease_out((t - 0.1) / 0.8)
        alto_v = max(1, int(tk.height * k))
        im.alpha_composite(tk.crop((0, 0, tk.width, alto_v)), (int(W / 2 - tk.width / 2 - 40), 420))
        return _sellar(im, sello, W / 2 + 80, 420 + tk.height + 70, t, min(1.4, dur * 0.5), -7) if sello else False
    return cuadro


def _lista(g, estilo, dur):
    items = [str(x)[:22] for x in (g.get("items") or []) if x][:5]
    titulo = _texto(str(g.get("titulo", ""))[:30], "bold", 54, NEGRO, max_ancho=680)
    ancho, fila = 760, 112
    alto = titulo.height + 60 + fila * len(items)
    cont = Image.new("RGBA", (ancho - 80, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(cont)
    cont.alpha_composite(titulo, (0, 0))
    cajas = []
    for i, it in enumerate(items):
        y = titulo.height + 40 + i * fila
        d.line([0, y - 14, ancho - 80, y - 14], fill=RENGLON, width=2)
        d.rounded_rectangle([6, y, 76, y + 70], 10, outline=NEGRO, width=6)
        cont.alpha_composite(_texto(it, "bold", 58, NEGRO, max_ancho=540), (110, y - 4))
        cajas.append((6, y))
    tarjeta = _tarjeta(cont, estilo)
    # cuándo se tilda cada uno: repartido en el tiempo de la escena
    paso = max(0.35, (dur - 0.6) / max(1, len(items)))

    def cuadro(im, t):
        p = tarjeta.copy()
        dp = ImageDraw.Draw(p)
        base_x = 40 + (14 if estilo == "cuaderno" else 0)
        base_y = 40 + (14 if estilo == "cuaderno" else 0)
        for i, (x, y) in enumerate(cajas):
            k = clamp((t - (0.4 + i * paso)) / 0.28)
            if k <= 0:
                continue
            X, Y = x + base_x, y + base_y
            p1, p2, p3 = (X + 8, Y + 40), (X + 28, Y + 60), (X + 66, Y + 4)
            if k < 0.4:
                q = k / 0.4
                dp.line([p1, (p1[0] + (p2[0] - p1[0]) * q, p1[1] + (p2[1] - p1[1]) * q)], fill=VERDE, width=12)
            else:
                q = (k - 0.4) / 0.6
                dp.line([p1, p2, (p2[0] + (p3[0] - p2[0]) * q, p2[1] + (p3[1] - p2[1]) * q)], fill=VERDE,
                        width=12, joint="curve")
        cy = ZONA[0] + min(tarjeta.height, ZONA[1] - ZONA[0]) / 2
        _pop(im, p, W / 2, cy, t, 0.05, -1.2)
        return False
    return cuadro


def _comparacion(g, estilo, dur):
    arriba = _tarjeta(_texto(str(g.get("arriba", ""))[:22].upper(), "cond", 96, NEGRO, max_ancho=800), estilo, 30)
    abajo_txt = _texto(str(g.get("abajo", ""))[:22].upper(), "cond", 104, NEGRO, max_ancho=860)
    abajo = Image.new("RGBA", (abajo_txt.width + 80, abajo_txt.height + 40), AMA + (255,))
    abajo.alpha_composite(abajo_txt, (40, 20))
    abajo = _sombra(abajo, 10, 14, 90)
    rot = _texto(str(g.get("rotulo", ""))[:24].upper(), "mono", 40, AMA if estilo == "oscuro" else (90, 90, 90),
                 max_ancho=600) if g.get("rotulo") else None
    fl = _flecha(AMA if estilo == "oscuro" else NEGRO)

    def cuadro(im, t):
        _pop(im, arriba, W / 2, 470, t, 0.1, -1.0)
        if t > 0.6:
            _pegar(im, fl, W / 2 - (120 if rot else 0), 660, 0, 1, clamp((t - 0.6) / 0.2))
            if rot:
                _pegar(im, rot, W / 2 + 120, 660, 0, 1, clamp((t - 0.7) / 0.2))
        _pop(im, abajo, W / 2, 840, t, 0.95, 1.2)
        return False
    return cuadro


_ARMAR = {"resaltado": _resaltado, "numero": _numero, "ticket": _ticket, "lista": _lista,
          "comparacion": _comparacion}


def valido(g):
    """Revisa y limpia lo que mandó la IA. Devuelve el gráfico listo o None."""
    if not isinstance(g, dict) or g.get("tipo") not in TIPOS:
        return None
    t = g["tipo"]
    if t == "resaltado" and g.get("texto"):
        return g
    if t == "numero" and g.get("valor") and g.get("rotulo"):
        return g
    if t == "ticket" and isinstance(g.get("lineas"), list) and g["lineas"]:
        g["lineas"] = [x if isinstance(x, (list, tuple)) else [str(x), ""] for x in g["lineas"]]
        g["lineas"] = [(list(x) + [""])[:2] for x in g["lineas"]]
        return g
    if t == "lista" and isinstance(g.get("items"), list) and len(g["items"]) >= 2:
        return g
    if t == "comparacion" and g.get("arriba") and g.get("abajo"):
        return g
    return None


def elegir_color(g, semilla=0):
    """El color que pidió la IA ("fondo"); si no pidió, según el tono: rojo → bordó, verde → verde."""
    if g.get("fondo") in COLORES:
        return g["fondo"]
    if g.get("sello"):
        return "verde" if str(g.get("sello_color", "")).lower().startswith("verde") else "bordo"
    return ("azul", "carbon", "violeta")[semilla % 3]


def render(g, dur, destino, estilo="oscuro", semilla=0):
    """Arma el clip de la escena (dur segundos, 1080x1920, 30 fps, sin audio)."""
    g = valido(dict(g or {}))
    if not g:
        raise ValueError("gráfico inválido")
    cuadro = _ARMAR[g["tipo"]](g, estilo, dur)
    color = elegir_color(g, semilla)
    n = max(1, round(dur * FPS))
    proc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", "-r", str(FPS), str(destino)], stdin=subprocess.PIPE)
    rnd = random.Random(semilla)
    try:
        for i in range(n):
            t = i / FPS
            im = fondo(estilo, t, semilla, color)
            golpe = cuadro(im, t)
            if golpe:
                im = im.transform(im.size, Image.AFFINE, (1, 0, rnd.randint(-6, 6), 0, 1, rnd.randint(-6, 6)))
            if t > dur - 0.2:  # se apaga un poco antes del corte
                velo = Image.new("RGBA", im.size, (0, 0, 0, int(70 * clamp((t - (dur - 0.2)) / 0.2))))
                im.alpha_composite(velo)
            proc.stdin.write(im.convert("RGB").tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg no pudo armar el gráfico")
    return destino
