import json
import os
import re
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


_SECRETOS = ["GEMINI_API_KEY", "YT_API_KEY", "SUPADATA_KEY", "CF_ACCOUNT_ID", "CF_API_TOKEN", "IG_TOKEN",
             "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET",
             "TIKTOK_REFRESH_TOKEN", "SMTP_USER", "SMTP_PASS", "GH_PAT"]


def ocultar(texto):
    """Tapa cualquier clave que pudiera colarse en un mensaje de error."""
    texto = str(texto)
    for n in _SECRETOS:
        v = os.getenv(n, "").strip()
        if len(v) >= 6:
            texto = texto.replace(v, "***")
    return re.sub(r"([?&](?:key|access_token|token)=)[^&\s]+", r"\1***", texto)


def avisar_error(accion, e):
    """Deja el motivo del error a la vista en la portada de la ejecución de GitHub (sin claves)."""
    msg = ocultar(f"{type(e).__name__}: {e}")[:1500]
    linea = msg.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    print(f"::error title=Falló «{accion}»::{linea}", flush=True)
    destino = os.getenv("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(f"## ❌ Falló «{accion}»\n\n```\n{msg}\n```\n")


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
