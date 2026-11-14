"""Piezas animadas (Remotion) para los videos comunes.

Tres usos:
  1. Escenas flojas: cuando para una escena no aparece ningún video que muestre lo que se dice, en vez de un clip
     "aproximado" o una postal que no tiene nada que ver, va una pieza animada con el texto de la escena.
  2. Gancho: si el texto en pantalla de la primera escena trae una cifra ("COBRÓ 750 MILLONES"), los primeros
     segundos son la cifra grande contando hasta el número.
  3. Series animadas enteras (config: "animada": true en la serie), como Impuestos sin vueltas.
Todo se arma con una sola llamada a Remotion por video. Si Remotion no está o falla, sale como siempre.
"""
import json
import re
import subprocess
from pathlib import Path

from . import util

CARPETA = util.RAIZ / "animaciones"
FPS = 30

MONEDAS = r"(?:US\$|U\$S|USD|u\$s|\$)"
UNIDADES = (r"(?:MILLONES|MILLÓN|MILLON|MIL MILLONES|MIL|BILLONES|%|POR CIENTO|AÑOS|VECES|DÍAS|DIAS|PESOS|"
            r"DÓLARES|DOLARES|KILOS|HORAS|MESES|CUOTAS|PERSONAS|LOCALES|SUCURSALES)")
NUMERO = re.compile(r"(?P<pre>" + MONEDAS + r")?\s*(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*"
                    r"(?P<suf>" + UNIDADES + r")?(?![\w])", re.IGNORECASE)


def disponible():
    return (CARPETA / "node_modules").exists()


def _corto(t, n):
    from .capitulos import _corto as c
    return c(t, n)


# ---------------------------------------------------------------- gancho con cifra
def numero_del_gancho(texto):
    """Busca la cifra principal del texto en pantalla. Devuelve la pieza "gancho" o None."""
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    if not texto or re.search(r"\d+\s+de\s+cada\s+\d+", texto, re.IGNORECASE):
        return None  # "3 de cada 10" no se lee bien como una cifra que cuenta
    m = None
    for x in NUMERO.finditer(texto):
        if x.group("pre") or x.group("suf") or len(re.sub(r"\D", "", x.group("num"))) >= 2:
            m = x
            break
    if not m:
        return None
    crudo = m.group("num")
    decimales = len(crudo.split(",")[1]) if "," in crudo else 0
    try:
        numero = float(crudo.replace(".", "").replace(",", "."))
    except ValueError:
        return None
    if numero <= 0:
        return None
    anio = decimales == 0 and "." not in crudo and 1800 <= numero <= 2100 and not m.group("pre") and not m.group("suf")
    suf = (m.group("suf") or "").upper().replace("POR CIENTO", "%")
    pre = (m.group("pre") or "").upper().replace("U$S", "US$").replace("USD", "US$")
    arriba = texto[:m.start()].strip(" -–:,.¿?¡!").strip()
    abajo = texto[m.end():].strip(" -–:,.¿?¡!").strip()
    if len(arriba) <= 3:
        arriba = ""  # "EL 30%": el artículo solo no aporta
    pieza = {"tipo": "gancho", "numero": round(numero, decimales) if decimales else int(numero), "decimales": decimales,
             "contar": not anio}
    if pre:
        pieza["prefijo"] = pre
    if suf == "%":
        pieza["sufijo"] = "%"
    elif suf:
        pieza["sufijo"] = suf
    if arriba:
        pieza["arriba"] = _corto(arriba.upper(), 26)
    if abajo:
        pieza["abajo"] = _corto(abajo.upper(), 28)
    return pieza


# ---------------------------------------------------------------- piezas para escenas sueltas
def piezas_para(escenas):
    """Una pieza animada por escena ({"texto", "pantalla"}). La IA elige el tipo; si falla, título con ícono."""
    from .capitulos import ICONOS, _pieza_valida, _de_respaldo
    elegidas = {}
    if escenas:
        try:
            from . import escritor
            pedido = (
                "Estas escenas son de un video corto de plata, impuestos o historias. Para cada una elegí UNA pieza "
                'visual animada. Devolvé solo un JSON: {"piezas": [{"escena": n, "tipo": "...", ...}]}. Tipos y campos:\n'
                '- titulo: {"texto": "frase corta en pantalla (máx 6 palabras)", "icono": "...", "cinta": "opcional"}\n'
                '- checklist: {"titulo": "...", "items": ["2 a 4 ítems cortos"], "activo": 0}\n'
                '- etiquetas: {"palabra": "UNA palabra clave", "cintas": ["1 o 2 frases cortas"], "icono_orbita": "moneda"}\n'
                '- banda: {"numero": 1, "texto": "título corto", "icono": "...", "detalle": "frase corta opcional"}\n'
                "Íconos posibles: " + ", ".join(ICONOS) + ".\n"
                "No repitas el mismo tipo dos veces seguidas. Los textos salen de lo que dice la escena, sin datos "
                "nuevos; si dice un monto o una fecha, ponelo tal cual.\n\nESCENAS:\n" +
                "\n".join(f"{k}. {e.get('texto')}" + (f" (en pantalla: {e['pantalla']})" if e.get("pantalla") else "")
                          for k, e in enumerate(escenas, start=1)))
            d = escritor._json_de(escritor.gemini("Sos diseñador de videos animados explicativos. Respondés solo JSON.",
                                                  pedido, 0.4)) or {}
            for p in d.get("piezas") or []:
                try:
                    n = int(p.get("escena"))
                except (TypeError, ValueError):
                    continue
                if 1 <= n <= len(escenas):
                    v = _pieza_valida(p, {"texto_pantalla": escenas[n - 1].get("pantalla"),
                                          "texto_voz": escenas[n - 1].get("texto")})
                    if v:
                        elegidas[n] = v
        except Exception as e:  # noqa
            util.log("Piezas animadas: la IA no respondió, uso las de respaldo:", util.ocultar(e))
    salida = []
    for k, e in enumerate(escenas, start=1):
        salida.append(elegidas.get(k) or _de_respaldo({"texto_pantalla": e.get("pantalla"),
                                                       "texto_voz": e.get("texto")}, k))
    return salida


# ---------------------------------------------------------------- render
def renderizar(piezas, segundos, trabajo, compacto=True, marca=False):
    """Arma todas las piezas en una sola corrida de Remotion y la corta en un clip por pieza, con el mismo
    formato que los clips de fondo (1080x1920, 30 fps, sin audio). Devuelve la lista de rutas o None."""
    if not piezas or len(piezas) != len(segundos) or not disponible():
        return None
    trabajo = Path(trabajo)
    cuadros = [max(12, round(s * FPS)) for s in segundos]
    escenas = [dict(p, segundos=round(c / FPS, 4)) for p, c in zip(piezas, cuadros)]
    props = trabajo / "piezas_sueltas.json"
    props.write_text(json.dumps({"serie": None, "escenas": escenas, "compacto": compacto, "marca": marca},
                                ensure_ascii=False), encoding="utf-8")
    entero = trabajo / "piezas_sueltas.mp4"
    try:
        subprocess.run(["npx", "remotion", "render", "src/index.ts", "Explicativo", str(entero),
                        f"--props={props}", "--log=error"], cwd=CARPETA, check=True, timeout=1200)
    except Exception as e:  # noqa
        util.log("Piezas animadas: Remotion falló, sigo con clips:", util.ocultar(e))
        return None
    return cortar(entero, cuadros, trabajo)


def cortar(entero, cuadros, trabajo):
    """Corta el video en tramos de `cuadros` (en cuadros exactos) con el formato de los fondos."""
    salida, desde = [], 0
    for k, c in enumerate(cuadros):
        destino = Path(trabajo) / f"pieza_{k:02d}.mp4"
        flt = f"select='between(n\\,{desde}\\,{desde + c - 1})',setpts=N/{FPS}/TB,scale=1080:1920,setsar=1,format=yuv420p"
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(entero), "-vf", flt, "-an", "-r", str(FPS),
                            "-frames:v", str(c), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(destino)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not destino.exists():
            util.log("Piezas animadas: no pude cortar el tramo", k, r.stderr[-300:])
            return None
        salida.append(destino)
        desde += c
    return salida


# ---------------------------------------------------------------- series animadas enteras
def animar_todo(contenido):
    """Le pone a cada escena una pieza animada (como los capítulos): gancho o título al principio y cierre al
    portal al final. Lo usa el montaje para armar todo el fondo con Remotion."""
    escenas = contenido.get("escenas") or []
    if len(escenas) < 3 or not disponible():
        return contenido
    from .capitulos import ICONOS
    primera = escenas[0]
    inicio = numero_del_gancho(primera.get("texto_pantalla")) or {
        "tipo": "titulo", "texto": _corto(primera.get("texto_pantalla") or contenido.get("titulo"), 48),
        "icono": ICONOS[hash(contenido.get("titulo", "")) % len(ICONOS)]}
    medio = piezas_para([{"texto": e.get("texto_voz", ""), "pantalla": e.get("texto_pantalla", "")}
                         for e in escenas[1:-1]])
    ultima = escenas[-1]
    texto = ultima.get("texto_pantalla") or ultima.get("texto_voz") or ""
    texto = re.sub(r"\s*(ramacontable\.com\.ar|rama contable punto com punto ar)\.?\s*$", "", texto,
                   flags=re.IGNORECASE).strip(" ,.:")
    cierre = {"tipo": "cierre", "texto": _corto(texto or "Guardalo y la guía completa está en", 40),
              "web": "ramacontable.com.ar"}
    salida = dict(contenido)
    salida["animacion"] = {"serie": None, "piezas": [inicio] + medio + [cierre]}
    return salida
