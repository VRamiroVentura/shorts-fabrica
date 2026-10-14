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
def _fondos(escenas, tiempos, trabajo, seed):
    """Un clip cada ~2.3 s. Devuelve (lista de segmentos, cuántos son de stock, nombre del banco)."""
    from . import video
    banco, buscar, clave = broll.proveedor()
    usados, segmentos, de_pexels = set(), [], 0
    n = 0
    for i, (esc, (ini, fin)) in enumerate(zip(escenas, tiempos)):
        dur = fin - ini
        cortes = max(1, round(dur / CORTE))
        largos = [dur / cortes] * cortes
        candidatos = []
        if clave:
            consultas = esc.get("broll") or []
            if isinstance(consultas, str):
                consultas = [consultas]
            consultas = [x for x in consultas if x][:2]
            consultas += [" ".join(x.split()[:2]) for x in consultas if len(x.split()) > 2]  # más general
            for c in consultas:
                try:
                    candidatos += buscar(c, clave, usados, cantidad=cortes + 1, minimo=min(dur, 3))
                except Exception as e:  # noqa
                    util.log(f"{banco} falló:", util.ocultar(e))
                if len(candidatos) >= cortes:
                    break
        for k, largo in enumerate(largos):
            destino = trabajo / f"fondo{n:03d}.mp4"
            hecho = False
            while candidatos and not hecho:
                c = candidatos.pop(0)
                try:
                    crudo = broll.bajar(c["link"], trabajo / f"stock_{c['id']}.mp4")
                    broll.recortar(crudo, largo, destino)
                    usados.add(c["id"])
                    hecho, de_pexels = True, de_pexels + 1
                except Exception as e:  # noqa
                    util.log("Clip descartado:", util.ocultar(e))
            if not hecho:
                img = trabajo / f"img{i}.png"
                if not img.exists():
                    # sin texto: los subtítulos ya cuentan lo que se dice
                    video.make_image(esc.get("prompt") or "", "", img, seed + i, esc.get("emoji") or "💡")
                broll.clip_de_imagen(img, largo, destino, acercar=(n % 2 == 0))
            segmentos.append(destino)
            n += 1
    return segmentos, de_pexels, banco


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
    segmentos, de_pexels, banco = _fondos(escenas, tiempos, trabajo, seed)
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
            "clips_stock": de_pexels, "banco": banco, "musica": musica.name if musica else None, "voz_seg": round(dur_voz, 2)}
    (salida / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    util.log("Video:", json.dumps(meta, ensure_ascii=False))
    shutil.rmtree(trabajo, ignore_errors=True)
    return salida / "video.mp4", salida / "thumb.jpg"
