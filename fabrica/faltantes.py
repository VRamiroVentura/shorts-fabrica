"""Lo que le faltó a cada video para que lo que se ve pegue con lo que se dice.

Cada video anota: escenas sin un clip que muestre justo lo que se dice (y qué se usó en su lugar), dibujitos que la
IA quiso usar y no existen, y el material que la IA dice que le habría servido. El reporte semanal lo junta y te
pide lo que más falta (clips o fotos para grabar con el celu, dibujitos nuevos), y el mail de cada video lo resume.
"""
from collections import Counter

from . import util

ARCHIVO = "data/faltantes.json"


def anotar(p, meta_video, contenido):
    entrada = {"fecha": p.get("fecha"), "turno": p.get("turno", 1), "serie": p.get("serie"),
               "titulo": p.get("titulo"),
               "escenas": (meta_video or {}).get("faltas", []),
               "dibujitos": (contenido or {}).get("dibujitos_faltantes", []),
               "material": (contenido or {}).get("material_que_faltaria", [])}
    if not (entrada["escenas"] or entrada["dibujitos"] or entrada["material"]):
        return
    lista = [x for x in (util.leer_json(ARCHIVO, []) or [])
             if not (x.get("fecha") == entrada["fecha"] and x.get("turno") == entrada["turno"])]  # rehacer: pisa
    util.guardar_json(ARCHIVO, (lista + [entrada])[-300:])


def ultimos(dias=7):
    desde = (util.ahora() - util.timedelta(days=dias)).strftime("%Y-%m-%d")
    return [x for x in (util.leer_json(ARCHIVO, []) or []) if (x.get("fecha") or "") >= desde]


def para_ia(dias=7):
    """Texto compacto para que la IA del reporte arme los pedidos."""
    ent = ultimos(dias)
    if not ent:
        return ""
    lineas = []
    for x in ent:
        for e in x.get("escenas", []):
            lineas.append(f'- [{x.get("serie")}] "{e.get("escena")}" (busqué: {", ".join(e.get("busqueda", []))}; '
                          f'usé: {e.get("se_uso")})')
    dib = Counter(d for x in ent for d in x.get("dibujitos", []))
    mat = [m for x in ent for m in x.get("material", [])]
    txt = "ESCENAS SIN UN VIDEO QUE PEGUE:\n" + ("\n".join(lineas[:60]) or "(ninguna)")
    if dib:
        txt += "\nDIBUJITOS QUE LA IA QUISO Y NO EXISTEN: " + ", ".join(f"{k} ({v})" for k, v in dib.most_common(15))
    if mat:
        txt += "\nMATERIAL QUE EL GUIONISTA DIJO QUE LE HABRÍA SERVIDO:\n" + "\n".join(f"- {m}" for m in mat[:30])
    return txt


def resumen_simple(dias=7):
    """Por si la IA no responde: lo más repetido, sin interpretar."""
    ent = ultimos(dias)
    busquedas = Counter(f'algo que muestre "{e.get("escena", "")[:70]}"' for x in ent for e in x.get("escenas", []))
    dib = Counter(d for x in ent for d in x.get("dibujitos", []))
    mat = Counter(m for x in ent for m in x.get("material", []))
    out = [f"Clip o foto: {k} (faltó {v} {'vez' if v == 1 else 'veces'})" for k, v in busquedas.most_common(6)]
    out += [f"Dibujito nuevo: {k} (lo pidió {v} {'vez' if v == 1 else 'veces'})" for k, v in dib.most_common(5)]
    out += [f"Material: {k}" for k, _ in mat.most_common(5)]
    return out


def bloque_mail(p):
    """Párrafo corto para el mail de cada video: qué le faltó y cómo ayudar."""
    import html
    faltas = (p.get("video") or {}).get("faltas", [])
    contenido = p.get("contenido") or {}
    dib = contenido.get("dibujitos_faltantes", [])
    mat = contenido.get("material_que_faltaria", [])
    if not (faltas or dib or mat):
        return ""
    e = html.escape
    items = [f'<li>"{e(f["escena"][:90])}" → no encontré un video justo, usé {e(f["se_uso"])}'
             + (f' (busqué: {e(", ".join(f["busqueda"]))})' if f.get("busqueda") else "") + "</li>" for f in faltas[:5]]
    items += [f"<li>Dibujito que no tengo: <b>{e(d)}</b></li>" for d in dib[:3]]
    items += [f"<li>Le habría servido: {e(m)}</li>" for m in mat[:3]]
    return ("<p><b>🧩 Lo que le faltó a este video</b> (para que lo que se ve pegue más con lo que se dice):</p>"
            f"<ul>{''.join(items)}</ul>"
            "<p style='color:#666'>Si tenés o grabás algo de esto con el celu (clip vertical de 5-10 s o foto, sin "
            "caras), subilo al repo en <b>assets/clips/</b> con un nombre que diga qué se ve. Los dibujitos "
            "pedíselos a Claude. Los lunes llega todo junto en el reporte semanal.</p>")
