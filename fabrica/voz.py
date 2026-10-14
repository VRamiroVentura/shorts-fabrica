"""Voz en off y tiempos de cada palabra.

Motor principal: la voz de Gemini (misma clave gratuita), que se graba de una sola toma con indicaciones
de estilo para que suene a charla y no a lectura. Los tiempos de cada palabra salen de escuchar el audio
con Whisper (faster-whisper). Si algo falla, se usa la voz de Microsoft Edge como antes.

Devuelve siempre lo mismo: un .wav, la lista de palabras [inicio, fin, palabra, escena] y los tiempos de
cada escena, para que la imagen y los subtítulos vayan pegados a la voz."""
import base64
import difflib
import io
import os
import re
import subprocess
import unicodedata
import wave
from pathlib import Path

from . import util

API = "https://generativelanguage.googleapis.com/v1beta/"
VOCES_HOMBRE = ["Puck", "Orus", "Charon", "Fenrir"]
VOCES_MUJER = ["Kore", "Aoede", "Leda", "Zephyr"]
ESTILO = ("Español rioplatense de Buenos Aires, con voseo y acento porteño natural. Tono relajado y cercano, "
          "como un amigo que te cuenta algo útil en una charla: ritmo ágil, con energía, frases que fluyen "
          "una detrás de la otra, sin pausas largas y sin sonar a locutor ni a alguien leyendo.")


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("Falló " + " ".join(cmd[:4]) + ": " + r.stderr[-600:])
    return r.stdout


def duracion(path):
    return float(_run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                       "-of", "default=nw=1:nk=1", str(path)]).strip())


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]", "", t)


# ---------------------------------------------------------------- Gemini
def _elegir_voz(clave, cfg):
    pedida = cfg.get("voz_gemini", "auto")
    if pedida and pedida != "auto":
        return pedida
    genero = cfg.get("voz_genero", "hombre")
    # 1) Biblioteca de voces: si hay alguna argentina, mejor.
    try:
        for params in ({"language_code": "es-AR", "page_size": 100}, {"region_code": "AR", "page_size": 100}):
            r = util.pedir("GET", API + "voices", intentos=2, timeout=40, headers={"x-goog-api-key": clave},
                           params=params)
            if r is None or r.status_code != 200:
                continue
            voces = r.json().get("voices", [])
            g = "female" if genero == "mujer" else "male"
            elegidas = [v for v in voces if g in str(v.get("gender", "")).lower()] or voces
            if elegidas:
                v = elegidas[0]
                util.log("Voz argentina de la biblioteca de Gemini:", v.get("display_name"), v.get("id"))
                return v.get("id") or v.get("name")
    except Exception as e:  # noqa
        util.log("No pude listar voces de Gemini:", util.ocultar(e))
    return (VOCES_MUJER if genero == "mujer" else VOCES_HOMBRE)[0]


def _a_wav(datos, destino):
    """Gemini devuelve WAV (o PCM crudo de 24 kHz). Lo dejamos como WAV."""
    if datos[:4] == b"RIFF":
        destino.write_bytes(datos)
        return
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(datos)


def _gemini_tts(texto, voz, modelo, clave, estilo):
    cuerpo = {
        "model": modelo,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": texto,
            "annotations": [{"type": "speech_metadata", "style": estilo}]}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voz}]},
    }
    r = util.pedir("POST", API + "interactions", intentos=3, espera=15, timeout=240,
                   headers={"x-goog-api-key": clave, "Content-Type": "application/json"}, json=cuerpo)
    if r is not None and r.status_code == 200:
        for paso in reversed(r.json().get("steps", [])):
            if paso.get("type") == "model_output":
                for c in reversed(paso.get("content", [])):
                    if c.get("type") == "audio" and c.get("data"):
                        return base64.b64decode(c["data"])
    # Respaldo: el formato viejo de generateContent (por si la API nueva no está para este modelo)
    viejo = {"contents": [{"parts": [{"text": f"{estilo}\n\nDecí exactamente esto: {texto}"}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
    r2 = util.pedir("POST", API + f"models/{modelo}:generateContent", intentos=2, espera=15, timeout=240,
                    headers={"x-goog-api-key": clave}, json=viejo)
    if r2 is not None and r2.status_code == 200:
        for p in (r2.json().get("candidates") or [{}])[0].get("content", {}).get("parts", []):
            if p.get("inlineData", {}).get("data"):
                return base64.b64decode(p["inlineData"]["data"])
    msg = ""
    for x in (r, r2):
        try:
            msg += f' {x.status_code}: {x.json()["error"]["message"][:160]}'
        except Exception:  # noqa
            pass
    raise RuntimeError("La voz de Gemini no respondió." + msg)


def _limpiar_audio(origen, destino, tempo=1.0):
    """Saca el silencio del principio y del final, pasa a 44.1 kHz y ajusta la velocidad si se pidió."""
    filtro = ("silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,areverse,"
              "silenceremove=start_periods=1:start_silence=0.20:start_threshold=-45dB,areverse")
    if abs(tempo - 1.0) > 0.01:
        filtro += f",atempo={tempo:.3f}"
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(origen), "-af", filtro, "-ar", "44100", "-ac", "1",
          "-c:a", "pcm_s16le", str(destino)])


# ---------------------------------------------------------------- tiempos de las palabras
def _whisper(wav, texto):
    from faster_whisper import WhisperModel  # se instala en GitHub Actions
    modelo = WhisperModel(os.getenv("WHISPER_MODELO", "base"), device="cpu", compute_type="int8")
    segmentos, _ = modelo.transcribe(str(wav), language="es", word_timestamps=True, beam_size=1,
                                     initial_prompt=texto[:600], condition_on_previous_text=False)
    return [[float(w.start), float(w.end), w.word.strip()] for s in segmentos for w in (s.words or [])]


def alinear(tokens, oidas, dur):
    """Pone tiempo a cada palabra del guion usando lo que Whisper escuchó.
    Las que no se reconocen se interpolan entre sus vecinas."""
    n = len(tokens)
    tiempos = [None] * n
    if oidas:
        a = [_norm(t) for t in tokens]
        b = [_norm(w[2]) for w in oidas]
        for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
            for k in range(blk.size):
                w = oidas[blk.b + k]
                tiempos[blk.a + k] = [w[0], w[1]]
    # interpolación por cantidad de letras entre anclas conocidas
    anclas = [(-1, 0.0)] + [(i, t[0]) for i, t in enumerate(tiempos) if t] + [(n, dur)]
    for (i0, t0), (i1, t1) in zip(anclas, anclas[1:]):
        hueco = list(range(i0 + 1, i1))
        if not hueco:
            continue
        ini = tiempos[i0][1] if i0 >= 0 and tiempos[i0] else t0
        pesos = [max(2, len(tokens[i])) for i in hueco]
        total = sum(pesos) or 1
        paso = max(0.0, t1 - ini) / total
        t = ini
        for i, p in zip(hueco, pesos):
            tiempos[i] = [t, t + p * paso]
            t += p * paso
    # nunca hacia atrás
    ultimo = 0.0
    for t in tiempos:
        t[0] = max(t[0], ultimo)
        t[1] = max(t[1], t[0] + 0.05)
        ultimo = t[0]
    return tiempos


# ---------------------------------------------------------------- motores
def _con_gemini(textos, carpeta, cfg):
    clave = util.secreto("GEMINI_API_KEY")
    if not clave:
        raise RuntimeError("sin GEMINI_API_KEY")
    from . import video
    dichos = [video.texto_voz(t) for t in textos]
    texto = " ".join(dichos)
    voz = _elegir_voz(clave, cfg)
    estilo = cfg.get("voz_estilo") or ESTILO
    ultimo_error = None
    for modelo in cfg.get("voz_gemini_modelos", ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]):
        try:
            datos = _gemini_tts(texto, voz, modelo, clave, estilo)
            break
        except Exception as e:  # noqa
            ultimo_error = e
            util.log(f"Voz de Gemini con {modelo} falló:", util.ocultar(e))
    else:
        raise RuntimeError(f"Ningún modelo de voz de Gemini anduvo ({util.ocultar(ultimo_error)})")
    crudo = carpeta / "voz_gemini.wav"
    _a_wav(datos, crudo)
    wav = carpeta / "voz.wav"
    _limpiar_audio(crudo, wav, float(cfg.get("voz_tempo", 1.0)))
    dur = duracion(wav)
    tokens, escena_de = [], []
    for i, d in enumerate(dichos):
        for t in d.split():
            tokens.append(t)
            escena_de.append(i)
    try:
        oidas = _whisper(wav, texto)
        metodo = "whisper"
    except Exception as e:  # noqa
        util.log("Whisper no anduvo, reparto los tiempos a ojo:", e)
        oidas, metodo = [], "estimado"
    tiempos = alinear(tokens, oidas, dur)
    palabras = [[t[0], t[1], tok, esc] for t, tok, esc in zip(tiempos, tokens, escena_de)]
    return wav, palabras, f"gemini · {voz} · tiempos {metodo}"


def _con_edge(textos, carpeta, cfg):
    from . import video
    palabras, partes, t0 = [], [], 0.0
    for i, t in enumerate(textos):
        mp3 = carpeta / f"voz{i}.mp3"
        dicho = video.texto_voz(t)
        words = video.synth(dicho, mp3)
        words = video.align_words(dicho, words, video.duration(mp3))
        words, d = video.compactar(mp3, words, carpeta / f"voz{i}.wav")
        for w in words:
            palabras.append([w[0] + t0, w[1] + t0, w[2], i])
        partes.append(carpeta / f"voz{i}.wav")
        t0 += d + video.PAD
    ins, flt = [], ""
    for i, p in enumerate(partes):
        ins += ["-i", str(p)]
        flt += f"[{i}:a]aresample=44100,apad=pad_dur={video.PAD}[a{i}];"
    flt += "".join(f"[a{i}]" for i in range(len(partes))) + f"concat=n={len(partes)}:v=0:a=1[out]"
    wav = carpeta / "voz.wav"
    _run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", flt, "-map", "[out]", "-ac", "1",
          "-c:a", "pcm_s16le", str(wav)])
    return wav, palabras, f"edge · {video.VOICE}"


def sintetizar(textos, carpeta, cfg=None):
    """textos: lo que se dice en cada escena. Devuelve (wav, palabras, escenas, motor)."""
    cfg = cfg or util.config()
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    motores = [_con_gemini, _con_edge] if cfg.get("voz_motor", "gemini") == "gemini" else [_con_edge]
    if os.getenv("TTS_ENGINE") == "silent":
        motores = [_con_edge]
    error = None
    for motor in motores:
        try:
            wav, palabras, nombre = motor(textos, carpeta, cfg)
            break
        except Exception as e:  # noqa
            error = e
            util.avisar("La voz principal falló, uso la de respaldo", util.ocultar(e))
    else:
        raise RuntimeError(f"No hubo voz: {error}")
    dur = duracion(wav)
    # tiempos de cada escena: desde su primera palabra hasta la primera de la siguiente
    inicios = []
    for i in range(len(textos)):
        ts = [p[0] for p in palabras if p[3] == i]
        inicios.append(min(ts) if ts else (inicios[-1] if inicios else 0.0))
    inicios[0] = 0.0
    escenas = []
    for i, s in enumerate(inicios):
        e = inicios[i + 1] if i + 1 < len(inicios) else dur + 0.35
        escenas.append([s, max(e, s + 0.4)])
    util.log("Voz:", nombre, f"· {dur:.1f} s")
    return wav, palabras, escenas, nombre
