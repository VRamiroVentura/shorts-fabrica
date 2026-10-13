import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

RAIZ = Path(__file__).resolve().parent.parent
ZONA = ZoneInfo("America/Argentina/Buenos_Aires")


def ahora():
    return datetime.now(ZONA)


def leer_json(ruta, defecto=None):
    p = RAIZ / ruta
    if not p.exists():
        return defecto
    return json.loads(p.read_text(encoding="utf-8") or "null") or defecto


def guardar_json(ruta, datos):
    p = RAIZ / ruta
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def config():
    return leer_json("config.json", {})


def secreto(nombre):
    v = os.getenv(nombre, "").strip()
    return v or None


def log(*a):
    print("[fabrica]", *a, flush=True)


def pedir(metodo, url, intentos=4, espera=5, ok=(200, 201, 202, 204), **kw):
    """requests con reintentos para errores temporales (429 y 5xx)."""
    kw.setdefault("timeout", 120)
    ultimo = None
    for i in range(intentos):
        try:
            r = requests.request(metodo, url, **kw)
            if r.status_code in ok:
                return r
            ultimo = r
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(espera * (i + 1))
                continue
            return r
        except requests.RequestException as e:  # noqa
            ultimo = e
            time.sleep(espera * (i + 1))
    if isinstance(ultimo, Exception):
        raise ultimo
    return ultimo
