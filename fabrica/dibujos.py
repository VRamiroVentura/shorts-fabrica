"""Biblioteca de dibujitos para los carteles animados: líneas negras gruesas y relleno de trama amarilla
(estilo 'revista vieja', con los colores de la cuenta). Todos se dibujan con código, gratis.

icono(nombre, size) → imagen RGBA. La lista completa está en NOMBRES, agrupada por tema en GRUPOS.
"""
import math
from functools import lru_cache

from PIL import Image, ImageDraw

NEGRO = (20, 20, 22)
AMA = (255, 205, 0)
ROJO = (200, 40, 45)
AZUL = (110, 170, 225)
VERDE = (70, 170, 100)
CREMA = (245, 238, 222)
ROSA = (240, 140, 150)
MARRON = (175, 115, 65)
GRIS = (175, 175, 175)
# Agrupados por tema, así la IA encuentra rápido el que va (y el prompt los lista igual).
GRUPOS = {
    "plata": ("moneda", "billete", "alcancia", "tarjeta", "billetera", "bolsa", "banco", "porcentaje", "calculadora",
              "documento", "balanza", "candado", "sube", "baja", "grafico"),
    "lugares": ("casa", "edificio", "fabrica", "banco", "pin", "mundo", "bandera", "sol", "palmera", "salud", "educacion"),
    "transporte": ("auto", "colectivo", "tren", "avion", "barco", "camion", "cohete", "valija"),
    "objetos": ("foco", "lapicera", "celular", "tele", "radio", "camara", "libro", "diario", "sobre", "regalo", "caja",
                "llave", "engranaje", "lupa", "reloj", "calendario", "carrito", "trofeo", "pelota", "megafono"),
    "comida": ("pizza", "mate", "empanada", "taza"),
    "personas": ("persona", "familia", "mano", "ojo"),
    "signos": ("pregunta", "exclamacion", "corazon", "estrella", "rayo", "fuego", "gota", "flecha"),
}
NOMBRES = tuple(dict.fromkeys(n for g in GRUPOS.values() for n in g))


@lru_cache(maxsize=8)
def _trama(w, h, paso=14, r=4, color=AMA):
    im = Image.new("RGBA", (w, h), color + (90,))
    d = ImageDraw.Draw(im)
    for y in range(0, h, paso):
        for x in range((y // paso) % 2 * paso // 2, w, paso):
            d.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))
    return im


def _rellenar(im, forma_fn, color=AMA):
    """Pinta con trama de puntitos lo que dibuja forma_fn sobre una máscara."""
    m = Image.new("L", im.size, 0)
    forma_fn(ImageDraw.Draw(m))
    t = _trama(im.size[0], im.size[1], color=color)
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    capa.paste(t, (0, 0), m)
    im.alpha_composite(capa)


def icono(nombre, size=420):
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    L = max(6, s // 40)  # grosor de línea

    def P(*xy):
        return [(x * s, y * s) for x, y in zip(xy[::2], xy[1::2])]

    def R(x0, y0, x1, y1):
        return [x0 * s, y0 * s, x1 * s, y1 * s]

    # Atajos: forma con relleno de trama (c) o liso (liso) + contorno negro.
    def poli(pts, c=None, liso=None, w=L):
        if c:
            _rellenar(im, lambda d: d.polygon(pts, fill=255), c)
        ImageDraw.Draw(im).polygon(pts, fill=liso, outline=NEGRO, width=w)

    def rect(box, c=None, liso=None, w=L, radio=0):
        if c:
            _rellenar(im, lambda d: d.rounded_rectangle(box, radio, fill=255), c)
        ImageDraw.Draw(im).rounded_rectangle(box, radio, fill=liso, outline=NEGRO, width=w)

    def elip(box, c=None, liso=None, w=L):
        if c:
            _rellenar(im, lambda d: d.ellipse(box, fill=255), c)
        ImageDraw.Draw(im).ellipse(box, fill=liso, outline=NEGRO, width=w)

    def linea(pts, w=L, color=NEGRO):
        ImageDraw.Draw(im).line(pts, fill=color, width=w, joint="curve")

    def radial(cx, cy, radios, n, giro=0.0):
        return [(s * (cx + radios[i % len(radios)] * math.cos(giro + 2 * math.pi * i / n)),
                 s * (cy + radios[i % len(radios)] * math.sin(giro + 2 * math.pi * i / n))) for i in range(n)]

    def signo(txt, color):
        from . import graficos
        f = graficos.F("cond", int(s * .8))
        elip(R(.12, .12, .88, .88), color)
        d = ImageDraw.Draw(im)
        d.text((s / 2, s / 2), txt, font=f, fill=NEGRO, anchor="mm", stroke_width=max(2, L // 2), stroke_fill=CREMA)

    if nombre == "casa":
        _rellenar(im, lambda d: (d.polygon(P(.15, .48, .5, .18, .85, .48), fill=255), d.rectangle(R(.22, .46, .78, .86), fill=255)))
        d = ImageDraw.Draw(im)
        d.line(P(.1, .5, .5, .16, .9, .5), fill=NEGRO, width=L, joint="curve")
        d.rectangle(R(.22, .46, .78, .86), outline=NEGRO, width=L)
        d.rectangle(R(.43, .62, .57, .86), fill=ROJO, outline=NEGRO, width=L)
        d.rectangle(R(.28, .54, .38, .64), outline=NEGRO, width=L // 2)
    elif nombre == "edificio":
        _rellenar(im, lambda d: d.rectangle(R(.28, .12, .72, .9), fill=255))
        d = ImageDraw.Draw(im)
        d.rectangle(R(.28, .12, .72, .9), outline=NEGRO, width=L)
        for fila in range(5):
            for col in range(3):
                x, y = .34 + col * .12, .18 + fila * .13
                d.rectangle(R(x, y, x + .07, y + .07), fill=NEGRO)
        d.rectangle(R(.44, .78, .56, .9), fill=ROJO, outline=NEGRO, width=L // 2)
    elif nombre == "auto":
        _rellenar(im, lambda d: d.rounded_rectangle(R(.12, .45, .88, .72), int(.06 * s), fill=255), color=ROJO)
        d = ImageDraw.Draw(im)
        d.polygon(P(.28, .45, .36, .3, .64, .3, .74, .45), fill=None, outline=NEGRO, width=L)
        d.rounded_rectangle(R(.12, .45, .88, .72), int(.06 * s), outline=NEGRO, width=L)
        for cx in (.3, .7):
            d.ellipse(R(cx - .09, .64, cx + .09, .82), fill=NEGRO)
            d.ellipse(R(cx - .04, .69, cx + .04, .77), fill=(240, 235, 220))
    elif nombre == "persona":
        _rellenar(im, lambda d: d.rounded_rectangle(R(.25, .5, .75, .9), int(.12 * s), fill=255))
        d = ImageDraw.Draw(im)
        d.ellipse(R(.35, .12, .65, .42), outline=NEGRO, width=L, fill=(245, 235, 215))
        d.rounded_rectangle(R(.25, .5, .75, .9), int(.12 * s), outline=NEGRO, width=L)
    elif nombre == "moneda":
        _rellenar(im, lambda d: d.ellipse(R(.15, .15, .85, .85), fill=255))
        d = ImageDraw.Draw(im)
        d.ellipse(R(.15, .15, .85, .85), outline=NEGRO, width=L)
        d.ellipse(R(.25, .25, .75, .75), outline=NEGRO, width=L // 2)
        d.line(P(.5, .32, .5, .68), fill=NEGRO, width=L)
        d.arc(R(.38, .34, .62, .5), 90, 360, fill=NEGRO, width=L)
        d.arc(R(.38, .5, .62, .66), 270, 180, fill=NEGRO, width=L)
    elif nombre == "billete":
        _rellenar(im, lambda d: d.rectangle(R(.1, .3, .9, .7), fill=255), color=(70, 170, 100))
        d = ImageDraw.Draw(im)
        d.rectangle(R(.1, .3, .9, .7), outline=NEGRO, width=L)
        d.ellipse(R(.4, .38, .6, .62), outline=NEGRO, width=L)
        d.line(P(.5, .4, .5, .6), fill=NEGRO, width=L // 2)
        d.arc(R(.45, .41, .55, .5), 90, 360, fill=NEGRO, width=L // 2)
        d.arc(R(.45, .5, .55, .59), 270, 180, fill=NEGRO, width=L // 2)
        for x in (.18, .78):
            d.ellipse(R(x, .46, x + .05, .51), fill=NEGRO)
    elif nombre == "calendario":
        _rellenar(im, lambda d: d.rectangle(R(.15, .2, .85, .38), fill=255), color=ROJO)
        d = ImageDraw.Draw(im)
        d.rectangle(R(.15, .2, .85, .85), outline=NEGRO, width=L)
        d.line(P(.15, .38, .85, .38), fill=NEGRO, width=L)
        for x in (.32, .68):
            d.line(P(x, .12, x, .27), fill=NEGRO, width=L)
        for fila in range(3):
            for col in range(4):
                x, y = .22 + col * .15, .45 + fila * .12
                d.rectangle(R(x, y, x + .07, y + .06), fill=NEGRO)
    elif nombre == "fabrica":
        _rellenar(im, lambda d: d.polygon(P(.1, .88, .1, .5, .3, .38, .3, .5, .5, .38, .5, .5, .7, .38, .7, .2, .85, .2, .85, .88), fill=255))
        d = ImageDraw.Draw(im)
        d.line(P(.1, .88, .1, .5, .3, .38, .3, .5, .5, .38, .5, .5, .7, .38, .7, .2, .85, .2, .85, .88, .1, .88),
               fill=NEGRO, width=L, joint="curve")
        for x in (.18, .38, .58):
            d.rectangle(R(x, .62, x + .08, .72), fill=NEGRO)
    elif nombre == "lupa":
        _rellenar(im, lambda d: d.ellipse(R(.15, .15, .62, .62), fill=255))
        d = ImageDraw.Draw(im)
        d.ellipse(R(.15, .15, .62, .62), outline=NEGRO, width=L)
        d.line(P(.56, .56, .85, .85), fill=NEGRO, width=L * 2)
    elif nombre == "mano":
        _rellenar(im, lambda d: (d.rounded_rectangle(R(.42, .38, .82, .7), int(.08 * s), fill=255),
                                 d.rounded_rectangle(R(.1, .38, .5, .48), int(.05 * s), fill=255)))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(R(.1, .38, .5, .48), int(.05 * s), outline=NEGRO, width=L)
        d.rounded_rectangle(R(.42, .38, .82, .7), int(.08 * s), outline=NEGRO, width=L)
        d.rectangle(R(.8, .4, .92, .68), fill=ROJO, outline=NEGRO, width=L)
    elif nombre == "pin":
        _rellenar(im, lambda d: (d.ellipse(R(.25, .1, .75, .6), fill=255), d.polygon(P(.29, .45, .5, .9, .71, .45), fill=255)), color=ROJO)
        d = ImageDraw.Draw(im)
        d.arc(R(.25, .1, .75, .6), 140, 40, fill=NEGRO, width=L)
        d.line(P(.29, .45, .5, .9, .71, .45), fill=NEGRO, width=L, joint="curve")
        d.ellipse(R(.42, .27, .58, .43), fill=(245, 235, 215), outline=NEGRO, width=L // 2)
    elif nombre == "grafico":
        d = ImageDraw.Draw(im)
        for i, h in enumerate((.3, .45, .6, .75)):
            x = .15 + i * .18
            _rellenar(im, lambda dd, x=x, h=h: dd.rectangle(R(x, .88 - h, x + .12, .88), fill=255))
            d.rectangle(R(x, .88 - h, x + .12, .88), outline=NEGRO, width=L)
        d.line(P(.1, .88, .9, .88), fill=NEGRO, width=L)
    elif nombre == "reloj":
        _rellenar(im, lambda d: d.ellipse(R(.15, .15, .85, .85), fill=255))
        d = ImageDraw.Draw(im)
        d.ellipse(R(.15, .15, .85, .85), outline=NEGRO, width=L)
        d.line(P(.5, .5, .5, .26), fill=NEGRO, width=L)
        d.line(P(.5, .5, .68, .6), fill=ROJO, width=L)
    elif nombre == "bandera":
        _rellenar(im, lambda d: d.rectangle(R(.25, .2, .85, .55), fill=255), color=(110, 170, 225))
        d = ImageDraw.Draw(im)
        d.rectangle(R(.25, .32, .85, .43), fill=(245, 240, 230))
        d.ellipse(R(.51, .33, .59, .42), fill=AMA)
        d.rectangle(R(.25, .2, .85, .55), outline=NEGRO, width=L)
        d.line(P(.22, .14, .22, .92), fill=NEGRO, width=L)
    elif nombre == "alcancia":
        elip(R(.14, .3, .8, .78), ROSA)
        rect(R(.76, .45, .9, .6), liso=ROSA, radio=int(.03 * s))
        for x in (.26, .58):
            rect(R(x, .72, x + .1, .86), liso=ROSA)
        poli(P(.3, .36, .36, .2, .44, .33), liso=ROSA)
        linea(P(.4, .3, .56, .3))
        ImageDraw.Draw(im).ellipse(R(.62, .42, .67, .47), fill=NEGRO)
    elif nombre == "tarjeta":
        rect(R(.1, .26, .9, .74), AZUL, radio=int(.05 * s))
        ImageDraw.Draw(im).rectangle(R(.1, .34, .9, .44), fill=NEGRO)
        rect(R(.18, .52, .34, .64), liso=AMA, w=L // 2, radio=int(.015 * s))
        for x in (.5, .6, .7):
            ImageDraw.Draw(im).rectangle(R(x, .6, x + .07, .64), fill=NEGRO)
    elif nombre == "billetera":
        rect(R(.12, .3, .86, .8), ROJO, radio=int(.06 * s))
        rect(R(.58, .45, .92, .65), liso=CREMA, radio=int(.04 * s))
        ImageDraw.Draw(im).ellipse(R(.66, .52, .72, .58), fill=NEGRO)
        poli(P(.2, .3, .3, .18, .62, .18, .7, .3), liso=(110, 200, 130))
    elif nombre == "bolsa":
        elip(R(.18, .34, .82, .9), AMA)
        poli(P(.36, .38, .3, .2, .7, .2, .64, .38), AMA)
        linea(P(.34, .36, .66, .36), w=L + 2)
        linea(P(.5, .5, .5, .8))
        d = ImageDraw.Draw(im)
        d.arc(R(.4, .51, .6, .65), 90, 360, fill=NEGRO, width=L)
        d.arc(R(.4, .65, .6, .79), 270, 180, fill=NEGRO, width=L)
    elif nombre == "banco":
        poli(P(.1, .34, .5, .1, .9, .34), AMA)
        for x in (.2, .4, .6, .76):
            rect(R(x, .4, x + .08, .76), liso=CREMA)
        rect(R(.12, .76, .88, .86), liso=CREMA)
        rect(R(.14, .34, .86, .4), liso=CREMA)
    elif nombre == "porcentaje":
        elip(R(.16, .14, .42, .4), AMA)
        elip(R(.58, .6, .84, .86), AMA)
        linea(P(.78, .14, .22, .86), w=L * 2)
    elif nombre == "calculadora":
        rect(R(.24, .08, .76, .92), AMA, radio=int(.05 * s))
        rect(R(.31, .15, .69, .32), liso=CREMA)
        for fila in range(4):
            for col in range(3):
                x, y = .31 + col * .14, .4 + fila * .12
                rect(R(x, y, x + .1, y + .08), liso=ROJO if (fila, col) == (3, 2) else CREMA, w=L // 2)
    elif nombre == "documento":
        poli(P(.22, .08, .64, .08, .78, .22, .78, .92, .22, .92), liso=CREMA)
        linea(P(.64, .08, .64, .22, .78, .22))
        ImageDraw.Draw(im).rectangle(R(.3, .3, .6, .36), fill=NEGRO)
        _rellenar(im, lambda d: d.rectangle(R(.29, .64, .71, .74), fill=255))
        for y in (.44, .54, .68, .8):
            linea(P(.3, y, .7, y), w=L // 2)
    elif nombre == "balanza":
        linea(P(.5, .14, .5, .84))
        rect(R(.3, .82, .7, .9), liso=CREMA)
        linea(P(.14, .24, .86, .24))
        for cx in (.22, .78):
            linea(P(cx, .24, cx - .1, .5), w=L // 2)
            linea(P(cx, .24, cx + .1, .5), w=L // 2)
            _rellenar(im, lambda d, cx=cx: d.chord(R(cx - .14, .38, cx + .14, .62), 0, 180, fill=255))
            ImageDraw.Draw(im).chord(R(cx - .14, .38, cx + .14, .62), 0, 180, outline=NEGRO, width=L)
        elip(R(.45, .1, .55, .2), liso=AMA)
    elif nombre == "candado":
        ImageDraw.Draw(im).arc(R(.3, .12, .7, .56), 180, 360, fill=NEGRO, width=L * 2)
        linea(P(.3 + L / s, .34, .3 + L / s, .46), w=L * 2)
        linea(P(.7 - L / s, .34, .7 - L / s, .46), w=L * 2)
        rect(R(.2, .44, .8, .9), AMA, radio=int(.05 * s))
        elip(R(.45, .56, .55, .66), liso=NEGRO)
        linea(P(.5, .64, .5, .78), w=L)
    elif nombre in ("sube", "baja"):
        linea(P(.12, .1, .12, .88, .9, .88))
        pts = P(.18, .74, .38, .56, .54, .66, .82, .26) if nombre == "sube" else P(.18, .26, .38, .44, .54, .34, .82, .74)
        linea(pts, w=L * 2, color=VERDE if nombre == "sube" else ROJO)
        x, y = pts[-1]
        dy = 1 if nombre == "sube" else -1
        poli([(x + .08 * s, y - .06 * s * dy), (x - .1 * s, y - .04 * s * dy), (x + .02 * s, y + .12 * s * dy)],
             liso=VERDE if nombre == "sube" else ROJO)
    elif nombre == "foco":
        for a in range(-160, 0, 32):
            r0, r1 = .27, .34
            ang = math.radians(a)
            linea([(s * (.5 + r0 * math.cos(ang)), s * (.35 + r0 * math.sin(ang))),
                   (s * (.5 + r1 * math.cos(ang)), s * (.35 + r1 * math.sin(ang)))], w=L)
        elip(R(.27, .12, .73, .58), AMA)
        poli(P(.38, .54, .62, .54, .6, .7, .4, .7), liso=CREMA)
        rect(R(.38, .7, .62, .84), liso=GRIS)
        linea(P(.38, .75, .62, .75), w=L // 2)
        linea(P(.38, .79, .62, .79), w=L // 2)
    elif nombre == "lapicera":
        poli(P(.42, .2, .58, .2, .58, .7, .42, .7), AMA)
        poli(P(.42, .7, .58, .7, .5, .9), liso=CREMA)
        ImageDraw.Draw(im).ellipse(R(.48, .86, .52, .9), fill=NEGRO)
        rect(R(.4, .08, .6, .3), liso=AZUL, radio=int(.04 * s))
        linea(P(.6, .12, .66, .12, .66, .36))
    elif nombre == "pizza":
        poli(P(.14, .2, .86, .2, .5, .92), AMA)
        rect(R(.1, .1, .9, .24), liso=MARRON, radio=int(.06 * s))
        for x, y in ((.36, .36), (.6, .38), (.48, .56), (.5, .74)):
            elip(R(x - .06, y - .06, x + .06, y + .06), liso=ROJO, w=L // 2)
    elif nombre == "mate":
        linea(P(.56, .3, .74, .04), w=L * 2, color=GRIS)
        linea(P(.56, .3, .74, .04), w=L // 2)
        elip(R(.22, .28, .78, .9), VERDE)
        rect(R(.3, .24, .7, .34), liso=GRIS, radio=int(.03 * s))
    elif nombre == "empanada":
        _rellenar(im, lambda d: d.chord(R(.08, .2, .92, 1.0), 180, 360, fill=255))
        ImageDraw.Draw(im).chord(R(.08, .2, .92, 1.0), 180, 360, outline=NEGRO, width=L)
        for i in range(7):
            cx = .16 + i * .113
            y = .6 - .36 * math.sqrt(max(0, 1 - ((cx - .5) / .42) ** 2))
            elip(R(cx - .05, y - .05, cx + .05, y + .05), liso=MARRON, w=L // 2)
    elif nombre == "taza":
        ImageDraw.Draw(im).arc(R(.62, .42, .86, .7), 270, 90, fill=NEGRO, width=L)
        poli(P(.18, .36, .7, .36, .64, .84, .24, .84), ROJO)
        rect(R(.12, .84, .76, .9), liso=CREMA)
        for x in (.32, .46, .58):
            ImageDraw.Draw(im).arc(R(x - .04, .1, x + .04, .3), 90, 270, fill=NEGRO, width=L // 2)
    elif nombre == "avion":
        poli(P(.4, .46, .7, .14, .78, .18, .6, .48), liso=CREMA)
        poli(P(.4, .54, .7, .86, .78, .82, .6, .52), liso=CREMA)
        rect(R(.08, .42, .92, .58), AZUL, radio=int(.08 * s))
        poli(P(.1, .44, .1, .26, .2, .26, .26, .44), liso=CREMA)
        for x in (.62, .7, .78):
            ImageDraw.Draw(im).ellipse(R(x, .47, x + .04, .51), fill=NEGRO)
    elif nombre == "barco":
        linea(P(.5, .1, .5, .62))
        poli(P(.52, .14, .52, .58, .82, .58), AMA)
        poli(P(.48, .2, .48, .58, .22, .58), liso=CREMA)
        poli(P(.08, .64, .92, .64, .78, .84, .22, .84), ROJO)
        for x in (.08, .36, .64):
            ImageDraw.Draw(im).arc(R(x, .86, x + .28, .96), 180, 360, fill=AZUL, width=L)
    elif nombre == "tren":
        rect(R(.14, .22, .86, .76), ROJO, radio=int(.05 * s))
        rect(R(.2, .1, .3, .22), liso=GRIS)
        for x in (.22, .42, .62):
            rect(R(x, .32, x + .14, .46), liso=CREMA, w=L // 2)
        linea(P(.08, .9, .92, .9))
        for cx in (.28, .5, .72):
            elip(R(cx - .08, .7, cx + .08, .86), liso=NEGRO)
    elif nombre == "colectivo":
        rect(R(.06, .26, .94, .74), AMA, radio=int(.06 * s))
        for x in (.12, .3, .48, .66):
            rect(R(x, .34, x + .14, .48), liso=CREMA, w=L // 2)
        rect(R(.82, .34, .9, .66), liso=CREMA, w=L // 2)
        for cx in (.26, .72):
            elip(R(cx - .09, .66, cx + .09, .84), liso=NEGRO)
            ImageDraw.Draw(im).ellipse(R(cx - .04, .71, cx + .04, .79), fill=CREMA)
    elif nombre == "camion":
        rect(R(.06, .22, .62, .72), liso=CREMA)
        poli(P(.62, .36, .82, .36, .94, .52, .94, .72, .62, .72), ROJO)
        rect(R(.68, .42, .82, .54), liso=AZUL, w=L // 2)
        for cx in (.2, .44, .8):
            elip(R(cx - .08, .66, cx + .08, .82), liso=NEGRO)
    elif nombre == "cohete":
        poli(P(.5, .06, .66, .28, .66, .7, .34, .7, .34, .28), liso=CREMA)
        poli(P(.34, .5, .2, .76, .34, .7), liso=ROJO)
        poli(P(.66, .5, .8, .76, .66, .7), liso=ROJO)
        elip(R(.42, .3, .58, .46), AZUL)
        poli(P(.4, .72, .6, .72, .5, .94), AMA)
    elif nombre == "valija":
        rect(R(.38, .14, .62, .28), radio=int(.04 * s))
        rect(R(.14, .26, .86, .84), MARRON, radio=int(.05 * s))
        for x in (.32, .68):
            linea(P(x, .26, x, .84), w=L)
    elif nombre == "celular":
        rect(R(.3, .06, .7, .94), liso=NEGRO, radio=int(.07 * s))
        _rellenar(im, lambda d: d.rectangle(R(.34, .14, .66, .82), fill=255), AZUL)
        ImageDraw.Draw(im).ellipse(R(.47, .85, .53, .91), fill=CREMA)
    elif nombre == "tele":
        linea(P(.36, .06, .5, .22, .64, .06))
        rect(R(.1, .22, .9, .8), liso=MARRON, radio=int(.05 * s))
        rect(R(.16, .28, .7, .74), AZUL, radio=int(.05 * s))
        for y in (.36, .5):
            elip(R(.74, y, .84, y + .1), liso=CREMA, w=L // 2)
        linea(P(.24, .8, .2, .9))
        linea(P(.76, .8, .8, .9))
    elif nombre == "radio":
        linea(P(.3, .3, .2, .06))
        rect(R(.08, .3, .92, .82), ROJO, radio=int(.06 * s))
        elip(R(.16, .4, .5, .74), liso=CREMA)
        for r in (.12, .06):
            ImageDraw.Draw(im).ellipse(R(.33 - r, .57 - r, .33 + r, .57 + r), outline=NEGRO, width=L // 2)
        rect(R(.58, .42, .84, .54), liso=AMA, w=L // 2)
        elip(R(.64, .6, .78, .74), liso=CREMA)
    elif nombre == "camara":
        rect(R(.3, .2, .5, .3), liso=CREMA)
        rect(R(.08, .28, .92, .8), liso=GRIS, radio=int(.05 * s))
        elip(R(.32, .34, .68, .76), liso=NEGRO)
        elip(R(.38, .4, .62, .7), AZUL)
        rect(R(.74, .34, .86, .42), liso=AMA, w=L // 2)
    elif nombre == "libro":
        poli(P(.5, .24, .08, .16, .08, .8, .5, .88), liso=CREMA)
        poli(P(.5, .24, .92, .16, .92, .8, .5, .88), AMA)
        for y in (.32, .44, .56):
            linea(P(.16, y, .42, y + .04), w=L // 2)
    elif nombre == "diario":
        rect(R(.14, .1, .86, .9), liso=CREMA)
        ImageDraw.Draw(im).rectangle(R(.22, .18, .78, .28), fill=NEGRO)
        rect(R(.22, .36, .48, .6), AMA, w=L // 2)
        for y in (.38, .46, .54, .68, .76):
            linea(P(.54 if y < .6 else .22, y, .78, y), w=L // 2)
    elif nombre == "sobre":
        rect(R(.1, .24, .9, .78), liso=CREMA)
        _rellenar(im, lambda d: d.polygon(P(.1, .24, .9, .24, .5, .54), fill=255))
        linea(P(.1, .24, .5, .54, .9, .24))
        elip(R(.44, .48, .56, .6), liso=ROJO, w=L // 2)
    elif nombre == "regalo":
        rect(R(.16, .4, .84, .88), ROJO)
        rect(R(.1, .3, .9, .42), ROJO)
        ImageDraw.Draw(im).rectangle(R(.45, .3, .55, .88), fill=AMA, outline=NEGRO, width=L // 2)
        for box in (R(.26, .12, .5, .32), R(.5, .12, .74, .32)):
            ImageDraw.Draw(im).ellipse(box, fill=AMA, outline=NEGRO, width=L)
    elif nombre == "caja":
        poli(P(.5, .14, .88, .3, .5, .46, .12, .3), liso=(215, 170, 110))
        poli(P(.12, .3, .5, .46, .5, .9, .12, .74), MARRON)
        poli(P(.88, .3, .5, .46, .5, .9, .88, .74), liso=(200, 145, 85))
        linea(P(.31, .22, .69, .38), w=L // 2)
    elif nombre == "llave":
        elip(R(.08, .3, .44, .66), AMA)
        elip(R(.18, .42, .3, .54), liso=CREMA, w=L // 2)
        rect(R(.42, .44, .9, .54), AMA)
        for x in (.66, .78):
            rect(R(x, .54, x + .06, .68), liso=AMA, w=L // 2)
    elif nombre == "engranaje":
        pts = []
        for k in range(8):
            a = 2 * math.pi * k / 8
            for da, r in ((0, .3), (.1, .42), (.4, .42), (.5, .3)):
                ang = a + da * 2 * math.pi / 8
                pts.append((s * (.5 + r * math.cos(ang)), s * (.5 + r * math.sin(ang))))
        poli(pts, AMA)
        elip(R(.38, .38, .62, .62), liso=CREMA)
    elif nombre == "carrito":
        linea(P(.06, .18, .2, .18, .3, .66, .8, .66))
        poli(P(.22, .28, .9, .28, .82, .56, .28, .56), AMA)
        for cx in (.36, .74):
            elip(R(cx - .06, .72, cx + .06, .84), liso=NEGRO)
    elif nombre == "trofeo":
        for box in (R(.12, .2, .36, .46), R(.64, .2, .88, .46)):
            ImageDraw.Draw(im).arc(box, 90, 270 if box[0] < s / 2 else 90, fill=NEGRO, width=L)
        ImageDraw.Draw(im).arc(R(.12, .2, .36, .46), 90, 270, fill=NEGRO, width=L)
        ImageDraw.Draw(im).arc(R(.64, .2, .88, .46), 270, 90, fill=NEGRO, width=L)
        poli(P(.24, .14, .76, .14, .7, .44, .58, .58, .42, .58, .3, .44), AMA)
        rect(R(.44, .58, .56, .74), liso=AMA)
        rect(R(.28, .74, .72, .86), liso=MARRON)
    elif nombre == "pelota":
        elip(R(.12, .12, .88, .88), liso=CREMA)
        cen = radial(.5, .5, (.14,), 5, -math.pi / 2)
        ImageDraw.Draw(im).polygon(cen, fill=NEGRO)
        for (x, y) in cen:
            dx, dy = x - s / 2, y - s / 2
            linea([(x, y), (s / 2 + dx * 2.6, s / 2 + dy * 2.6)], w=L // 2)
    elif nombre == "megafono":
        poli(P(.16, .4, .56, .2, .56, .8, .16, .6), ROJO)
        rect(R(.08, .4, .18, .6), liso=CREMA)
        rect(R(.26, .58, .36, .78), liso=GRIS, w=L // 2)
        for r in (.1, .2):
            ImageDraw.Draw(im).arc(R(.56 - r + .08, .5 - r - .1, .56 + r + .1, .5 + r + .1), -45, 45, fill=NEGRO,
                                   width=L // 2)
    elif nombre == "mundo":
        elip(R(.12, .12, .88, .88), AZUL)
        _rellenar(im, lambda d: (d.ellipse(R(.24, .24, .5, .54), fill=255), d.ellipse(R(.52, .5, .74, .78), fill=255)),
                  VERDE)
        d = ImageDraw.Draw(im)
        d.ellipse(R(.3, .12, .7, .88), outline=NEGRO, width=L // 2)
        d.line(P(.12, .5, .88, .5), fill=NEGRO, width=L // 2)
        d.ellipse(R(.12, .12, .88, .88), outline=NEGRO, width=L)
    elif nombre == "sol":
        for k in range(12):
            a = 2 * math.pi * k / 12
            linea([(s * (.5 + .32 * math.cos(a)), s * (.5 + .32 * math.sin(a))),
                   (s * (.5 + .46 * math.cos(a)), s * (.5 + .46 * math.sin(a)))])
        elip(R(.24, .24, .76, .76), AMA)
    elif nombre == "palmera":
        ImageDraw.Draw(im).arc(R(.3, .3, 1.1, 1.5), 180, 245, fill=MARRON, width=L * 3)
        ImageDraw.Draw(im).arc(R(.3, .3, 1.1, 1.5), 180, 245, fill=NEGRO, width=L // 2)
        for pts in (P(.38, .3, .08, .34, .2, .22), P(.38, .3, .14, .54, .1, .4), P(.38, .3, .7, .38, .6, .24),
                    P(.38, .3, .62, .56, .7, .48), P(.38, .3, .36, .06, .5, .12)):
            poli(pts, VERDE)
        ImageDraw.Draw(im).chord(R(.0, .86, 1.0, 1.1), 180, 360, fill=(240, 215, 150), outline=NEGRO, width=L)
    elif nombre == "salud":
        rect(R(.12, .12, .88, .88), liso=CREMA, radio=int(.1 * s))
        poli(P(.4, .22, .6, .22, .6, .4, .78, .4, .78, .6, .6, .6, .6, .78, .4, .78, .4, .6, .22, .6, .22, .4, .4, .4),
             liso=ROJO)
    elif nombre == "educacion":
        poli(P(.5, .2, .94, .38, .5, .56, .06, .38), liso=(50, 50, 55))
        poli(P(.26, .48, .26, .7, .5, .8, .74, .7, .74, .48, .5, .58), AZUL)
        linea(P(.5, .38, .86, .44, .86, .66))
        elip(R(.82, .64, .9, .72), liso=AMA, w=L // 2)
    elif nombre == "familia":
        for (x, y, k, c) in ((.08, .22, 1.0, AMA), (.48, .26, .92, ROJO), (.66, .52, .55, VERDE)):
            elip(R(x + .07 * k, y, x + .27 * k, y + .2 * k), liso=CREMA)
            rect(R(x, y + .24 * k, x + .34 * k, y + .62 * k), c, radio=int(.08 * s * k))
    elif nombre == "ojo":
        _rellenar(im, lambda d: d.ellipse(R(.08, .26, .92, .74), fill=255), CREMA)
        ImageDraw.Draw(im).ellipse(R(.08, .26, .92, .74), fill=CREMA, outline=NEGRO, width=L)
        elip(R(.34, .3, .66, .7), AZUL)
        ImageDraw.Draw(im).ellipse(R(.44, .42, .56, .58), fill=NEGRO)
    elif nombre == "pregunta":
        signo("?", AMA)
    elif nombre == "exclamacion":
        signo("!", ROJO)
    elif nombre == "corazon":
        poli([(s * (.5 + .38 * (16 * math.sin(a) ** 3) / 16),
               s * (.52 - .36 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) / 16))
              for a in [2 * math.pi * i / 60 for i in range(60)]], ROJO)
    elif nombre == "estrella":
        poli(radial(.5, .53, (.44, .18), 10, -math.pi / 2), AMA)
    elif nombre == "rayo":
        poli(P(.56, .04, .2, .56, .46, .56, .38, .96, .8, .4, .54, .4, .66, .04), AMA)
    elif nombre == "fuego":
        poli(P(.5, .06, .74, .38, .8, .62, .7, .84, .5, .92, .3, .84, .2, .62, .3, .4, .4, .52), ROJO)
        poli(P(.5, .44, .64, .64, .6, .82, .5, .86, .4, .82, .36, .66), liso=AMA)
    elif nombre == "gota":
        poli([(s * .5, s * .08)] + [(s * (.5 + .3 * math.cos(a)), s * (.62 + .3 * math.sin(a)))
                                    for a in [math.radians(d) for d in range(-35, 216, 10)]], AZUL)
    else:  # flecha
        _rellenar(im, lambda d: d.polygon(P(.1, .4, .6, .4, .6, .25, .9, .5, .6, .75, .6, .6, .1, .6), fill=255), color=ROJO)
        d = ImageDraw.Draw(im)
        d.line(P(.1, .4, .6, .4, .6, .25, .9, .5, .6, .75, .6, .6, .1, .6, .1, .4), fill=NEGRO, width=L, joint="curve")
    return im
