"""Revisión antes de publicar: tus pedidos (cambios, publicar ya, no publicar) llegan por el formulario
"Revisar video" de GitHub Actions, que los anota en data/pedidos.json. La corrida que está esperando la hora
los lee cada minuto y actúa."""
import json
import os
import subprocess

from . import util

ARCHIVO = "data/pedidos.json"
ACCIONES = {"Pedir cambios": "cambios", "Publicar ya": "publicar", "No publicar hoy": "cancelar"}


def ahora_utc():
    return util.datetime.now(util.ZoneInfo("UTC")).isoformat()


def leer_remotos():
    """Los pedidos más nuevos del repo (los de la rama principal, recién bajados)."""
    try:
        subprocess.run(["git", "fetch", "-q", "origin", "main"], capture_output=True, timeout=60)
        r = subprocess.run(["git", "show", f"origin/main:{ARCHIVO}"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception as e:  # noqa
        util.log("No pude leer los pedidos:", util.ocultar(e))
    return util.leer_json(ARCHIVO, []) or []


def nuevos(pedidos, fecha, turno, desde):
    """Pedidos de hoy para este turno (o para "el que está esperando") hechos después de `desde`."""
    out = []
    for x in pedidos:
        if x.get("fecha") != fecha or x.get("creado", "") <= desde:
            continue
        if str(x.get("turno", "auto")) not in ("auto", str(turno)):
            continue
        out.append(x)
    return sorted(out, key=lambda x: x.get("creado", ""))


def cancelado(fecha, turno):
    """¿Pediste explícitamente que este turno no salga hoy?"""
    return any(x.get("fecha") == fecha and str(x.get("turno")) == str(turno) and x.get("accion") == "cancelar"
               for x in util.leer_json(ARCHIVO, []) or [])


def registrar(accion_texto, turno_texto, cambios):
    accion = ACCIONES.get(accion_texto, "")
    if not accion:
        raise ValueError(f"Acción desconocida: {accion_texto}")
    cambios = (cambios or "").strip()
    if accion == "cambios" and not cambios:
        raise ValueError("Elegiste «Pedir cambios» pero no escribiste qué cambiar.")
    turno = turno_texto if turno_texto in ("1", "2") else "auto"
    pedido = {"id": os.getenv("GITHUB_RUN_ID", "local"), "creado": ahora_utc(),
              "fecha": util.ahora().strftime("%Y-%m-%d"), "turno": turno, "accion": accion, "cambios": cambios[:1500]}
    lista = (util.leer_json(ARCHIVO, []) or []) + [pedido]
    util.guardar_json(ARCHIVO, lista[-60:])
    return pedido


def link_formulario():
    repo = os.getenv("GITHUB_REPOSITORY", "")
    return f"https://github.com/{repo}/actions/workflows/revisar.yml" if repo else ""
