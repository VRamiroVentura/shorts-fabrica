"""Arma el video final: voz, clips de fondo que cambian cada ~2 segundos, subtítulos grandes palabra por
palabra, el gancho escrito desde el segundo 0, barra de progreso y música suave opcional."""
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from . import broll, util, voz

W, H, FPS = 1080, 1920, 30
AMARILLO_ASS = "&H0000D4FF&"   # (255, 212, 0) en formato BGR de ASS
BLANCO_ASS = "&H00FFFFFF&"
CORTE = 2.3                    # cada cuánto cambia el clip de fondo (segundos, aprox.)
SUB_Y = 1160                   # centro de los subtítulos (zona segura de Reels/TikTok/Shorts)


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("Falló " + " ".join(cmd[:4]) + ": " + r.stderr[-900:])
    return r.stdout


def _t(seg):
    seg = max(0.0, seg)
    h, m = int(seg // 3600), int(seg % 3600 // 60)
    return f"{h}:{m:02d}:{seg % 60:05.2f}"


def _fuente_subs():
    fonts = util.RAIZ / "fonts"
    for archivo, nombre in (("Poppins-ExtraBold.ttf", "Poppins ExtraBold"), ("Poppins-Black.ttf", "Poppins Black"),
                            ("Poppins-Bold.ttf", "Poppins")):
        if (fonts / archivo).exists():
            return nombre
    return "Poppins"


def _esc(t):
    return re.sub(r"[{}\\]", "", str(t))


# ---------------------------------------------------------------- subtítulos
def _bloques(palabras, max_palabras=3, max_letras=15):
    """Agrupa de a 2 o 3 palabras, corta en la puntuación y nunca mezcla dos escenas."""
    bloques, actual = [], []
    for p in palabras:
        if actual and p[3] != actual[-1][3]:
            bloques.append(actual)
            actual = []
        actual.append(p)
        txt = " ".join(x[2] for x in actual)
        if len(actual) >= max_palabras or len(txt) >= max_letras or re.search(r"[.,;:?!…]$", p[2]):
            bloques.append(actual)
            actual = []
    if actual:
        bloques.append(actual)
    return bloques


def subtitulos(palabras, gancho, serie, usuario, dur_gancho, dur_total, destino):
    fuente = _fuente_subs()
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{fuente},112,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,1.5,0,1,9,4,5,70,70,0,1
Style: Gancho,{fuente},84,&H00111111,&H00111111,&H0000D4FF,&H0000D4FF,1,0,0,0,100,100,0.5,0,3,22,0,8,110,110,330,1
Style: Serie,{fuente},42,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,2,0,1,4,2,8,60,60,150,1
Style: Marca,{fuente},36,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,1,0,1,4,2,2,60,60,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    eventos = []
    for bloque in _bloques(palabras):
        for i, w in enumerate(bloque):
            ini = w[0]
            fin = bloque[i + 1][0] if i + 1 < len(bloque) else w[1] + 0.25
            partes = []
            for j, x in enumerate(bloque):
                txt = _esc(x[2]).upper()
                if j == i:
                    partes.append("{\\c" + AMARILLO_ASS + "\\fscx108\\fscy108}" + txt + "{\\c" + BLANCO_ASS +
                                  "\\fscx100\\fscy100}")
                else:
                    partes.append(txt)
            pop = "{\\fscx82\\fscy82\\t(0,90,\\fscx100\\fscy100)}" if i == 0 else ""
            eventos.append([ini, fin, "{\\pos(%d,%d)}" % (W // 2, SUB_Y) + pop + " ".join(partes)])
    eventos.sort(key=lambda e: e[0])
    for k in range(len(eventos) - 1):  # nunca dos a la vez y sin parpadeos
        sig = eventos[k + 1][0]
        if eventos[k][1] > sig or sig - eventos[k][1] < 0.4:
            eventos[k][1] = sig
    lineas = [f"Dialogue: 2,{_t(s)},{_t(e)},Sub,,0,0,0,,{txt}" for s, e, txt in eventos if e - s > 0.02]
    if gancho:
        lineas.append(f"Dialogue: 3,{_t(0)},{_t(dur_gancho)},Gancho,,0,0,0,,"
                      "{\\fad(0,150)}" + _esc(gancho).upper())
    if serie:
        lineas.append(f"Dialogue: 1,{_t(dur_gancho)},{_t(dur_total)},Serie,,0,0,0,,"
                      "{\\fad(200,0)}" + _esc(serie).upper())
    if usuario:
        lineas.append(f"Dialogue: 1,{_t(0)},{_t(dur_total)},Marca,,0,0,0,,{_esc(usuario)}")
    destino.write_text(cab + "\n".join(lineas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- fondo
# Comodines: escenas de plata y trámites que acompañan casi cualquier frase de finanzas sin desentonar.
COMODINES = ["hands counting money", "hand holding smartphone", "typing on laptop keyboard",
             "calculator and paperwork", "card payment terminal", "wallet with cash",
             "signing documents", "us dollar bills"]

PUNTUAR = """Sos editor de videos cortos para una cuenta argentina de finanzas personales e impuestos.
Te paso las escenas (lo que se dice) con opciones de video de fondo, y al final unos COMODINES.
Mirá la imagen de cada opción y poné un puntaje:
3 = muestra justo lo que se dice: la acción, el objeto o el lugar.
2 = muestra plata, pagos, un celular, una compu, papeles, trabajo o compras, y acompaña bien la frase.
1 = neutro: no molesta pero no aporta.
0 = no tiene nada que ver (un cielo, flores, alguien en la cama, paisajes), o no puede pasar por Argentina:
    carteles en otros idiomas o alfabetos, lugares reconocibles de otros países, billetes que no sean pesos
    argentinos o dólares.
Las opciones marcadas PROPIA son videos grabados en Argentina.
Para los COMODINES puntuá en general: ¿sirven para acompañar un video de plata e impuestos en Argentina?
Las POSTALES son tomas de Argentina para enganchar la vista (paisajes, drones, ciudades, cosas típicas):
3 = hermosa y claramente argentina (Buenos Aires, Patagonia, Iguazú, glaciares, cordillera, mar, mate, asado);
2 = linda y puede pasar por Argentina; 0 = fea, borrosa o de otro país.
Respondé solo con JSON: {"escenas": [{"escena": 1, "puntajes": [3, 0, 2]}], "comodines": [2, 0, 3], "postales": [3, 0]}"""


def _imagen(c, ruta):
    import base64
    mini = broll.miniatura(c, ruta)
    if not mini:
        return None
    return {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(Path(mini).read_bytes()).decode()}}


def _puntuar_con_ia(escenas, candidatos, comodines, trabajo, postales=()):
    """La IA mira una imagen de cada opción y la puntúa de 0 a 3.
    Si falla, se usa un puntaje por defecto (2 para lo que pasó el filtro)."""
    from . import escritor
    defecto = ([[2] * len(c) for c in candidatos], [2] * len(comodines), [2] * len(postales))
    partes, hay = [{"text": "ESCENAS Y OPCIONES:"}], False
    for i, (esc, cands) in enumerate(zip(escenas, candidatos), 1):
        partes.append({"text": f'\nESCENA {i}: "{esc["texto"]}"'})
        for k, c in enumerate(cands):
            img = _imagen(c, trabajo / f"mini_{i}_{k}.jpg")
            if img:
                hay = True
                partes += [{"text": f"Opción {k}" + (" (PROPIA)" if c.get("propio") else "") + ":"}, img]
            else:
                partes.append({"text": f"Opción {k}: (sin imagen, poné 1)"})
    partes.append({"text": "\nCOMODINES:"})
    for k, c in enumerate(comodines):
        img = _imagen(c, trabajo / f"mini_comodin_{k}.jpg")
        partes += [{"text": f"Comodín {k}:"}, img] if img else [{"text": f"Comodín {k}: (sin imagen, poné 1)"}]
        hay = hay or bool(img)
    if postales:
        partes.append({"text": "\nPOSTALES:"})
        for k, c in enumerate(postales):
            img = _imagen(c, trabajo / f"mini_postal_{k}.jpg")
            partes += [{"text": f"Postal {k}:"}, img] if img else [{"text": f"Postal {k}: (sin imagen, poné 1)"}]
            hay = hay or bool(img)
    if not hay:
        return defecto
    try:
        r = escritor.gemini(PUNTUAR, partes, temperatura=0.2)
        por_escena = {int(e.get("escena", 0)) - 1: e.get("puntajes", []) for e in r.get("escenas", [])
                      if isinstance(e, dict)}
        puntajes = []
        for i, cands in enumerate(candidatos):
            p = [int(x) if str(x).lstrip("-").isdigit() else 1 for x in por_escena.get(i, [])]
            puntajes.append((p + [1] * len(cands))[:len(cands)])
        pc = [int(x) if str(x).lstrip("-").isdigit() else 1 for x in r.get("comodines", [])]
        pc = (pc + [1] * len(comodines))[:len(comodines)]
        pp = [int(x) if str(x).lstrip("-").isdigit() else 1 for x in r.get("postales", [])]
        pp = (pp + [1] * len(postales))[:len(postales)]
        util.log("Puntajes de los fondos:", puntajes, "comodines:", pc, "postales:", pp)
        return puntajes, pc, pp
    except Exception as e:  # noqa
        util.log("No pude puntuar los fondos con la IA:", util.ocultar(e))
        return defecto


def _fondos(escenas, tiempos, trabajo, seed):
    """Un clip cada ~2.3 s. Siempre video: primero lo que muestra justo lo que se dice, si no un comodín
    de plata y trámites; nunca algo de otro país ni sin relación. Devuelve (segmentos, de stock, banco, propios)."""
    from . import video
    banco, buscar, clave = broll.proveedor()
    propios = broll.propios()
    # 1) opciones por escena: primero los clips propios, después los del banco (sin los que son de afuera)
    candidatos = []
    for esc, (ini, fin) in zip(escenas, tiempos):
        dur = fin - ini
        lista = broll.propios_para(propios, esc)
        consultas = [x for x in (esc.get("broll") or []) if x][:2]
        if clave and consultas:
            consultas += [" ".join(x.split()[:2]) for x in consultas if len(x.split()) > 2]
            for c in consultas:
                try:
                    lista += [x for x in buscar(c, clave, set(), cantidad=3, minimo=min(dur, 3))
                              if not broll.de_afuera(x)]
                except Exception as e:  # noqa
                    util.log(f"{banco} falló:", util.ocultar(e))
                if len(lista) >= 4:
                    break
        vistos, unicos = set(), []
        for x in lista:
            if x["id"] not in vistos:
                vistos.add(x["id"])
                unicos.append(x)
        candidatos.append(unicos[:4])
    # comodines: tus clips propios primero, después algunos del banco
    comodines = [c for c in propios][:6]
    if clave:
        for q in random.sample(COMODINES, len(COMODINES)):
            if len(comodines) >= 12:
                break
            try:
                comodines += [x for x in buscar(q, clave, set(), cantidad=2, minimo=3) if not broll.de_afuera(x)]
            except Exception as e:  # noqa
                util.log(f"{banco} falló:", util.ocultar(e))
    ya = {x["id"] for lst in candidatos for x in lst}
    comodines = [c for c in comodines if c["id"] not in ya]
    cfg = util.config()
    tope_postales = int(cfg.get("postales_por_video", 3))
    lindas = broll.postales(buscar, clave) if (clave and tope_postales > 0) else []
    # 2) la IA puntúa
    puntajes, p_comodin, p_postal = _puntuar_con_ia(escenas, candidatos, comodines, trabajo, lindas)
    # 3) armado
    usados, segmentos, de_video, de_propios, n = set(), [], 0, 0, 0
    con_ia_de_imagen = bool(util.secreto("CF_ACCOUNT_ID") and util.secreto("CF_API_TOKEN"))

    def mejores(lista, pts, minimo):
        orden = sorted([(p, k) for k, p in enumerate(pts) if p >= minimo and lista[k]["id"] not in usados],
                       key=lambda x: (-x[0], not lista[x[1]].get("propio"), x[1]))
        return [lista[k] for _, k in orden]

    postales_usadas, anterior_postal = 0, False
    ultima = len(escenas) - 1
    for i, (esc, (ini, fin)) in enumerate(zip(escenas, tiempos)):
        dur = fin - ini
        buenos = mejores(candidatos[i], puntajes[i], 2)          # pegan con la frase
        exacto = any(p >= 3 for p in puntajes[i])
        # Postal de Argentina: en la intriga (escena 2) y en el cierre siempre que no haya un clip exacto,
        # y en cualquier escena que no tenga nada bueno. Nunca dos seguidas ni más del tope.
        postal = []
        if lindas and postales_usadas < tope_postales and not anterior_postal:
            if (not buenos) or (i in (1, ultima) and not exacto):
                postal = mejores(lindas, p_postal, 2)[:1]
        if postal:
            buenos = postal
        if not buenos:
            buenos = mejores(comodines, p_comodin, 2)[:1]          # comodín de plata y trámites
        if not buenos:
            buenos = (mejores(candidatos[i], puntajes[i], 1) or mejores(comodines, p_comodin, 1))[:1]
        cortes = max(1, min(round(dur / CORTE), len(buenos))) if buenos else 1
        for largo in [dur / cortes] * cortes:
            destino = trabajo / f"fondo{n:03d}.mp4"
            hecho = False
            while buenos and not hecho:
                c = buenos.pop(0)
                try:
                    crudo = broll.bajar(c["link"], trabajo / f"stock_{c['id']}.mp4")
                    broll.recortar(crudo, largo, destino)
                    usados.add(c["id"])
                    hecho = True
                    postales_usadas += 1 if c.get("postal") else 0
                    anterior_postal = bool(c.get("postal"))
                    if c.get("propio"):
                        de_propios += 1
                    else:
                        de_video += 1
                except Exception as e:  # noqa
                    util.log("Clip descartado:", util.ocultar(e))
            if not hecho:  # sin ningún video posible (por ejemplo, sin clave del banco)
                if con_ia_de_imagen:
                    img = trabajo / f"img{i}.png"
                    if not img.exists():
                        video.make_image(esc.get("prompt") or "", "", img, seed + i, esc.get("emoji") or "💡")
                    broll.clip_de_imagen(img, largo, destino, acercar=(n % 2 == 0))
                else:
                    broll.clip_tarjeta(esc.get("emoji") or "💡", largo, destino, acercar=(n % 2 == 0))
            segmentos.append(destino)
            n += 1
    return segmentos, de_video, banco, de_propios, postales_usadas


def _musica(cfg):
    ruta = util.RAIZ / cfg.get("musica", "assets/music.mp3")
    if ruta.exists():
        return ruta
    carpeta = util.RAIZ / "assets"
    temas = sorted(list(carpeta.glob("*.mp3")) + list(carpeta.glob("*.m4a"))) if carpeta.exists() else []
    return random.choice(temas) if temas else None


def _portada(segmentos, contenido, destino, trabajo):
    from . import video
    cuadro = trabajo / "cuadro_portada.jpg"
    try:
        _run(["ffmpeg", "-y", "-v", "error", "-ss", "0.4", "-i", str(segmentos[0]), "-frames:v", "1", str(cuadro)])
        im = Image.open(cuadro).convert("RGB")
        lado = min(im.size)
        x, y = (im.width - lado) // 2, (im.height - lado) // 2
        im.crop((x, y, x + lado, y + lado)).save(cuadro)
    except Exception:  # noqa
        video.fallback_card("", cuadro, contenido.get("miniatura", {}).get("emoji", "💡"))
    mini = contenido.get("miniatura", {})
    video.make_thumbnail(cuadro, mini.get("linea1") or contenido["titulo"], mini.get("linea2", ""), destino)


# ---------------------------------------------------------------- todo junto
def generar(contenido, serie_nombre, usuario, carpeta):
    cfg = util.config()
    salida = Path(carpeta)
    trabajo = salida / "_trabajo"
    trabajo.mkdir(parents=True, exist_ok=True)
    escenas = [{"texto": e["texto_voz"], "pantalla": e.get("texto_pantalla", ""), "emoji": e.get("emoji", ""),
                "prompt": e.get("prompt", ""), "broll": e.get("broll", "")} for e in contenido["escenas"]]
    seed = random.randint(1, 10_000_000)

    # 1) voz y tiempos
    wav, palabras, tiempos, motor = voz.sintetizar([e["texto"] for e in escenas], trabajo, cfg)
    dur_voz = voz.duracion(wav)
    total = round(tiempos[-1][1], 3)

    # 2) fondos
    segmentos, de_pexels, banco, de_propios, de_postales = _fondos(escenas, tiempos, trabajo, seed)
    (trabajo / "lista.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in segmentos))
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(trabajo / "lista.txt"),
          "-c", "copy", str(trabajo / "fondo.mp4")])

    # 3) subtítulos + gancho
    gancho = (contenido["escenas"][0].get("texto_pantalla") or contenido.get("miniatura", {}).get("linea1") or "")
    dur_gancho = min(max(tiempos[0][1], 2.2), 4.0)
    subtitulos(palabras, gancho, serie_nombre, usuario, dur_gancho, total, trabajo / "subs.ass")

    # 4) mezcla final: fondo oscurecido + subtítulos + barra de progreso + voz (+ música)
    musica = _musica(cfg)
    fonts = util.RAIZ / "fonts"
    filtro_v = (f"[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.22:t=fill,"
                f"ass={trabajo / 'subs.ass'}:fontsdir={fonts}[v0];"
                f"color=c=0xFFD400:s={W}x14:r={FPS}[barra];"
                f"[v0][barra]overlay=x='-w+w*t/{total}':y={H - 14}:shortest=1[v]")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(trabajo / "fondo.mp4"), "-i", str(wav)]
    if musica:
        vol = float(cfg.get("musica_volumen", 0.08))
        cmd += ["-stream_loop", "-1", "-i", str(musica)]
        filtro_a = (f"[1:a]aresample=44100,apad=pad_dur=0.6[voz];"
                    f"[2:a]aresample=44100,volume={vol},afade=t=out:st={max(0.0, total - 1.5):.2f}:d=1.5[mus];"
                    f"[voz][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
                    f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    else:
        filtro_a = "[1:a]aresample=44100,apad=pad_dur=0.6,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    cmd += ["-filter_complex", filtro_v + ";" + filtro_a, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", str(salida / "video.mp4")]
    _run(cmd)

    # 5) portada
    _portada(segmentos, contenido, salida / "thumb.jpg", trabajo)

    meta = {"duracion": round(voz.duracion(salida / "video.mp4"), 2), "voz": motor, "clips": len(segmentos),
            "clips_stock": de_pexels, "banco": banco, "clips_propios": de_propios, "postales": de_postales, "musica": musica.name if musica else None, "voz_seg": round(dur_voz, 2)}
    (salida / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    util.log("Video:", json.dumps(meta, ensure_ascii=False))
    shutil.rmtree(trabajo, ignore_errors=True)
    return salida / "video.mp4", salida / "thumb.jpg"
