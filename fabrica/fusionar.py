"""Fusiona los datos que dejó esta corrida con los del repo, si otro workflow los cambió en el medio.

Uso: python -m fabrica.fusionar <carpeta_con_nuestros_cambios> <raíz_del_repo> <commit_base>
Es una fusión de tres partes: solo se aplica lo que ESTA corrida cambió respecto del commit con el que arrancó,
así no se pisan los cambios que hicieron otros (la automejora, el reporte, una corrida manual).
- Listas de publicaciones (con "fecha" y "titulo"): se juntan; si la misma está en las dos, gana la nuestra.
- Otras listas: se juntan sin repetir.
- Diccionarios: clave por clave; en los valores simples gana el nuestro solo si lo cambiamos.
"""
import json
import subprocess
import sys
from pathlib import Path

_NADA = object()


def _clave(x):
    if isinstance(x, dict) and "fecha" in x and "titulo" in x:
        return ("pub", x.get("fecha"), str(x.get("turno", 1)), x.get("titulo"))
    return ("json", json.dumps(x, sort_keys=True, ensure_ascii=False))


def fusionar(nuestro, suyo, base=_NADA):
    if nuestro == base:  # no lo tocamos: queda lo que hay en el repo
        return suyo
    if suyo == base or suyo is _NADA:  # ellos no lo tocaron
        return nuestro
    if isinstance(nuestro, dict) and isinstance(suyo, dict):
        b = base if isinstance(base, dict) else {}
        salida = dict(suyo)
        for k in set(nuestro) | set(b):
            if k in nuestro:
                salida[k] = fusionar(nuestro[k], suyo.get(k, _NADA), b.get(k, _NADA))
            elif k in salida and salida[k] == b.get(k):  # lo borramos nosotros y ellos no lo cambiaron
                del salida[k]
        return salida
    if isinstance(nuestro, list) and isinstance(suyo, list):
        de_base = {_clave(x): x for x in (base if isinstance(base, list) else [])}
        nuestros = {_clave(x): x for x in nuestro}
        salida, vistos = [], set()
        for x in suyo:
            k = _clave(x)
            salida.append(nuestros.get(k, x) if nuestros.get(k, x) != de_base.get(k) else x)
            vistos.add(k)
        for x in nuestro:
            k = _clave(x)
            if k not in vistos and (k not in de_base or de_base[k] != x):  # nuevo nuestro (no algo que ellos borraron)
                salida.append(x)
        return salida
    return nuestro


def _base(raiz, commit, ruta):
    r = subprocess.run(["git", "show", f"{commit}:{ruta}"], cwd=raiz, capture_output=True, text=True)
    if r.returncode != 0:
        return _NADA
    try:
        return json.loads(r.stdout or "null")
    except ValueError:
        return _NADA


def fusionar_carpetas(origen, raiz, commit):
    origen, raiz = Path(origen), Path(raiz)
    for f in sorted(origen.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(origen).as_posix()
        dest = raiz / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if f.suffix == ".json" and dest.exists():
            try:
                a = json.loads(f.read_text(encoding="utf-8") or "null")
                b = json.loads(dest.read_text(encoding="utf-8") or "null")
                dest.write_text(json.dumps(fusionar(a, b, _base(raiz, commit, rel)), ensure_ascii=False, indent=2),
                                encoding="utf-8")
                continue
            except ValueError:
                pass
        dest.write_bytes(f.read_bytes())


if __name__ == "__main__":
    fusionar_carpetas(sys.argv[1], sys.argv[2], sys.argv[3])
