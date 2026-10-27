"""Gráficos animados para la serie "La plata en datos" (y cualquier escena que traiga un `grafico`).

Se dibuja cuadro por cuadro con Pillow y se codifica con ffmpeg: no usa IA de imágenes ni bancos de video,
así que sale siempre igual de prolijo y gratis. Los números NUNCA los pone la IA: vienen de `datos`
(chequeados a mano en temas.json o bajados de una API) y acá solo se dibujan.

Tipos:
  barras   ranking de barras horizontales que crecen de a una (de menor a mayor) y resaltan una
  contador un número grande que cuenta hasta el valor, con texto arriba y abajo

Zona libre para los subtítulos: y ~1430-1600 (montaje usa SUB_Y_GRAFICO).
"""
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from . import marca as mk

W, H, FPS = 1080, 1920, 30
FONDO = (17, 17, 17)
GRILLA = (48, 48, 48)
TEXTO = (235, 235, 235)
APAGADO = (150, 150, 150)
BARRA = (215, 215, 215)
RESALTE = mk.AMARILLO

ZONA_ARRIBA, ZONA_ABAJO = 610, 1350      # dónde van las barras
Y_TITULO, Y_FUENTE = 550, 1395


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _num(v, decimales):
    """31.5 -> '31,5' ; 1234.5 -> '1.234,5' (formato argentino)."""
    s = f"{v:,.{decimales}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _decimales(v):
    s = repr(float(v))
    return 0 if s.endswith(".0") else min(2, len(s.split(".")[1]))


def _codificar(cuadros, total, destino):
    """Recibe un generador de imágenes RGB y arma el mp4 sin pasar por disco."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-frames:v", str(total), "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "18", "-pix_fmt", "yuv420p", str(destino)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for im in cuadros:
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg (gráfico): " + p.stderr.read().decode()[-600:])
    return destino


def _base(titulo, fuente):
    im = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(im)
    if titulo:
        d.text((W // 2, Y_TITULO), titulo, font=mk.fuente("semibold", 40), fill=APAGADO, anchor="mm")
    if fuente:
        d.text((W // 2, Y_FUENTE), "Fuente: " + fuente, font=mk.fuente("regular", 28), fill=(120, 120, 120),
               anchor="mm")
    return im


# ---------------------------------------------------------------- barras
def barras(g, dur, destino, arranque=0.6, paso=None, crecer=0.6, completo=False):
    """g = {"titulo", "fuente", "unidad": "%", "resaltar": "Argentina",
            "items": [{"nombre", "valor", "emoji"}], "nota": "texto que aparece al final (opcional)"}
    completo=True: arranca con las barras ya armadas y la nota puesta (para el cierre)."""
    items = sorted(g["items"], key=lambda x: -float(x["valor"]))
    n = len(items)
    maximo = max(float(x["valor"]) for x in items) or 1
    unidad = g.get("unidad", "")
    resaltar = (g.get("resaltar") or "").lower()
    alto = (ZONA_ABAJO - ZONA_ARRIBA) / n
    grosor = min(70, alto * 0.70)
    hay_emoji = any(it.get("emoji") for it in items)
    x_nombre = 108 if hay_emoji else 60
    medir = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    tam = int(min(44, grosor * 0.66))                         # los nombres largos achican la letra
    while tam > 26 and max(medir.textlength(it["nombre"], font=mk.fuente("bold", tam)) for it in items) > 300:
        tam -= 2
    f_nom = mk.fuente("bold", tam)
    x0 = x_nombre + max(medir.textlength(it["nombre"], font=f_nom) for it in items) + 26
    f_val = mk.fuente("bold", int(min(50, grosor * 0.76)))
    ancho_val = max(medir.textlength(_num(float(it["valor"]), _decimales(it["valor"])) + unidad, font=f_val)
                    for it in items)
    ancho_max = W - x0 - ancho_val - 70
    paso = paso or max(0.25, min(1.0, (dur - arranque - crecer - 1.5) / max(1, n - 1)))
    f_nota = mk.fuente("bold", 46)
    base = _base("", g.get("fuente", ""))
    d0 = ImageDraw.Draw(base)
    for k in range(1, 5):                                     # grilla suave
        x = x0 + ancho_max * k / 4
        d0.line([(x, ZONA_ARRIBA - 10), (x, ZONA_ABAJO)], fill=GRILLA, width=2)
    fin_barras = arranque + paso * (n - 1) + crecer
    corrimiento = fin_barras + 1.0 if completo else 0.0
    total = max(1, round(dur * FPS))
    nota = g.get("nota")

    def cuadro(t):
        t += corrimiento
        im = base.copy()
        d = ImageDraw.Draw(im)
        a = _ease((t - fin_barras - 0.4) / 0.4) if nota else 0.0
        if g.get("titulo") and a < 1:                         # el título se va cuando entra la nota
            c = tuple(int(FONDO[j] + (APAGADO[j] - FONDO[j]) * (1 - a)) for j in range(3))
            d.text((W // 2, Y_TITULO), g["titulo"], font=mk.fuente("semibold", 42), fill=c, anchor="mm")
        for i, it in enumerate(items):
            orden = n - 1 - i                                 # aparecen de abajo (menor) hacia arriba
            p = _ease((t - arranque - orden * paso) / crecer)
            cy = ZONA_ARRIBA + alto * (i + 0.5)
            es = resaltar and it["nombre"].lower() == resaltar
            if p <= 0:
                continue
            col_txt = RESALTE if es else TEXTO
            if it.get("emoji"):
                mk.pegar_emoji(im, it["emoji"], (58, cy), int(grosor * 0.78))
            d.text((x_nombre, cy), it["nombre"], font=f_nom, fill=col_txt, anchor="lm")
            largo = max(8, ancho_max * float(it["valor"]) / maximo * p)
            color = RESALTE if es else BARRA
            if es and t > fin_barras:                         # latido de la barra resaltada
                pulso = 0.5 + 0.5 * math.sin((t - fin_barras) * 6)
                d.rounded_rectangle([x0 - 6, cy - grosor / 2 - 6, x0 + largo + 6, cy + grosor / 2 + 6],
                                    radius=14, outline=RESALTE, width=int(2 + 3 * pulso))
            d.rounded_rectangle([x0, cy - grosor / 2, x0 + largo, cy + grosor / 2], radius=10, fill=color)
            v = float(it["valor"]) * p
            d.text((x0 + largo + 16, cy), _num(v, _decimales(it["valor"])) + unidad, font=f_val,
                   fill=col_txt, anchor="lm")
        if a > 0:
            caja = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(caja)
            fn = f_nota
            while dc.textlength(nota.upper(), font=fn) > W - 140 and fn.size > 30:
                fn = mk.fuente("bold", fn.size - 2)
            tw = dc.textlength(nota.upper(), font=fn)
            y = Y_TITULO - 10 + (1 - a) * 30
            dc.rounded_rectangle([W / 2 - tw / 2 - 30, y - 42, W / 2 + tw / 2 + 30, y + 42], 22,
                                 fill=RESALTE + (int(255 * a),))
            dc.text((W / 2, y), nota.upper(), font=fn, fill=FONDO + (int(255 * a),), anchor="mm")
            im.paste(caja, (0, 0), caja)
        return im

    return _codificar((cuadro(k / FPS) for k in range(total)), total, destino)


# ---------------------------------------------------------------- contador
def contador(g, dur, destino):
    """g = {"arriba": "texto chico", "valor": 31.5, "unidad": "%", "abajo": "texto", "emoji": "📈", "fuente"}"""
    base = _base("", g.get("fuente", ""))
    total = max(1, round(dur * FPS))
    dec = _decimales(g["valor"])
    f_num, f_txt = mk.fuente("bold", 220), mk.fuente("bold", 52)

    def cuadro(t):
        im = base.copy()
        d = ImageDraw.Draw(im)
        p = _ease(t / max(0.8, min(1.6, dur * 0.5)))
        if g.get("emoji"):
            mk.pegar_emoji(im, g["emoji"], (W // 2, 680), 170)
        if g.get("arriba"):
            d.text((W // 2, 840), g["arriba"].upper(), font=f_txt, fill=APAGADO, anchor="mm")
        d.text((W // 2, 1010), _num(float(g["valor"]) * p, dec) + g.get("unidad", ""), font=f_num,
               fill=RESALTE, anchor="mm")
        if g.get("abajo") and p > 0.95:
            d.text((W // 2, 1200), g["abajo"].upper(), font=f_txt, fill=TEXTO, anchor="mm")
        return im

    return _codificar((cuadro(k / FPS) for k in range(total)), total, destino)


TIPOS = {"barras": barras, "contador": contador}


def clip(g, dur, destino, completo=False):
    """Punto de entrada para montaje: arma el clip de un gráfico."""
    if g.get("tipo", "barras") == "barras":
        return barras(g, dur, Path(destino), completo=completo)
    return TIPOS[g["tipo"]](g, dur, Path(destino))


def validar(g):
    """Revisa que el gráfico se pueda dibujar. Devuelve el motivo si no sirve, o "" si está bien."""
    if not isinstance(g, dict) or g.get("tipo", "barras") not in TIPOS:
        return "tipo de gráfico desconocido"
    if g.get("tipo", "barras") == "barras":
        items = g.get("items") or []
        if not 3 <= len(items) <= 12:
            return "las barras tienen que ser entre 3 y 12"
        try:
            if any(float(x["valor"]) < 0 for x in items) or not all(str(x["nombre"]).strip() for x in items):
                return "valores negativos o nombres vacíos"
        except (KeyError, TypeError, ValueError):
            return "a algún ítem le falta nombre o valor"
    elif "valor" not in g:
        return "al contador le falta el valor"
    return ""
