"""Control de temas repetidos, según cómo rindió el video anterior.

Antes de armar el video, la IA compara el guion nuevo con lo publicado en los últimos `dias` (60 por defecto):
  - Si es la misma idea que algo de los últimos `dias_bloqueo` (30): se frena siempre y se escribe otro tema.
  - Si la idea ya salió `max_veces` en la ventana de `dias`, se frena aunque haya rendido (0 = sin tope:
    lo que rinde puede volver todas las veces que quiera, respetando `dias_bloqueo`).
  - Si es la misma idea que un video más viejo que ANDUVO BIEN (vistas >= la mediana de los últimos videos):
    pasa como relanzamiento.
  - Si es la misma idea que un video más viejo que ANDUVO MAL: se frena y se escribe otro tema.
Si después de `intentos` sigue parecido, sale igual (nunca se pierde el video del día) y queda el aviso en el mail.
Se configura en config.json → control_repetidos. Si algo falla (IA, métricas), el video sigue sin control.
"""
import statistics

from . import util

COMPARAR = """Sos editor de una cuenta de videos cortos sobre plata, economía e impuestos.
Te paso un VIDEO NUEVO y una lista de VIDEOS YA PUBLICADOS.
Decime cuáles de los publicados cuentan LA MISMA IDEA CENTRAL que el nuevo, aunque usen otras palabras,
otro título u otros ejemplos. Ejemplo: "Tu plata vale menos", "Tu sueldo pierde" y "La plata no dura nada"
son la misma idea (la inflación te come la plata). En cambio, dos videos de impuestos sobre trámites distintos
NO son la misma idea. Si dudás, NO lo marques.
Respondé solo con JSON: {"iguales": [números de los videos publicados con la misma idea], "idea": "la idea central
del video nuevo en pocas palabras"}"""


def _cfg():
    c = util.config().get("control_repetidos") or {}
    return c if isinstance(c, dict) else {}


def activo():
    return bool(_cfg().get("activo", True))


def _publicados(historial, dias):
    desde = (util.ahora() - util.timedelta(days=dias)).strftime("%Y-%m-%d")
    return [h for h in historial if h.get("fecha", "") >= desde and not h.get("cancelado")
            and any(r.get("ok") for r in (h.get("resultados") or {}).values() if isinstance(r, dict))]


def _texto(contenido):
    guion = " ".join(e.get("texto_voz", "") for e in contenido.get("escenas", []))
    return f'Título: {contenido.get("titulo", "")}\nGuion: {guion[:900]}'


def iguales(contenido, previos):
    """Índices (de `previos`) que la IA considera la misma idea. Devuelve (lista, idea)."""
    from . import escritor
    lista = "\n".join(f'{i}. [{h.get("fecha")}] {h.get("titulo")}' + (f' — {h["guion"][:220]}' if h.get("guion") else "")
                      for i, h in enumerate(previos, 1))
    r = escritor.gemini(COMPARAR, f"VIDEO NUEVO:\n{_texto(contenido)}\n\nVIDEOS YA PUBLICADOS:\n{lista}",
                        temperatura=0.1)
    idx = []
    for x in (r or {}).get("iguales", []) or []:
        if str(x).isdigit() and 1 <= int(x) <= len(previos):
            idx.append(int(x) - 1)
    return idx, str((r or {}).get("idea", ""))[:120]


def _vistas(entradas, medir):
    """{(fecha, turno, titulo): vistas} usando la función de métricas de la fábrica."""
    filas, _ = medir(entradas)
    return {(f["fecha"], f.get("turno", 1), f["titulo"]): f["vistas"] for f in filas}


def decidir(contenido, historial, medir):
    """Devuelve (frenar: bool, motivo: str, titulos_a_evitar: list).
    `medir(entradas)` devuelve (filas, por_serie) como main._rendimiento."""
    c = _cfg()
    previos = _publicados(historial, int(c.get("dias", 60)))[-80:]
    if not previos:
        return False, "", []
    idx, idea = iguales(contenido, previos)
    if not idx:
        return False, "", []
    parecidos = [previos[i] for i in idx]
    bloqueo = (util.ahora() - util.timedelta(days=int(c.get("dias_bloqueo", 7)))).strftime("%Y-%m-%d")
    titulos = [h["titulo"] for h in parecidos]
    recientes = [h for h in parecidos if h.get("fecha", "") >= bloqueo]
    if recientes:
        return True, (f'"{contenido.get("titulo")}" es la misma idea que "{recientes[-1]["titulo"]}" '
                      f'({recientes[-1]["fecha"]}), de hace menos de {c.get("dias_bloqueo", 7)} días'), titulos
    # Ya se relanzó: la misma idea no sale más de `max_veces` en la ventana de `dias`, aunque rinda
    max_veces = int(c.get("max_veces", 0) or 0)
    if max_veces > 0 and len(parecidos) + 1 > max_veces:
        return True, (f'"{contenido.get("titulo")}" sería la vez número {len(parecidos) + 1} de la misma idea en '
                      f'{c.get("dias", 60)} días (ya salió como "{parecidos[-1]["titulo"]}", {parecidos[-1]["fecha"]}); '
                      f'el tope es {max_veces}'), titulos
    # Más viejos: depende de cómo rindieron, comparado con la mediana de los últimos videos
    muestra = previos[-int(c.get("muestra_mediana", 12)):]
    vistas = _vistas(list({id(h): h for h in muestra + parecidos}.values()), medir)
    clave = lambda h: (h["fecha"], h.get("turno", 1), h["titulo"])  # noqa
    mediana = statistics.median([vistas.get(clave(h), 0) for h in muestra]) if muestra else 0
    mejor = max(parecidos, key=lambda h: vistas.get(clave(h), 0))
    v = vistas.get(clave(mejor), 0)
    if v >= mediana and v > 0:
        util.log(f'Relanzamiento: "{contenido.get("titulo")}" repite la idea de "{mejor["titulo"]}" '
                 f'({v} vistas, mediana {mediana:.0f}), que anduvo bien: lo dejo pasar')
        return False, f'relanzamiento de "{mejor["titulo"]}" ({v} vistas), que anduvo bien', []
    return True, (f'"{contenido.get("titulo")}" repite la idea de "{mejor["titulo"]}" ({mejor["fecha"]}, {v} vistas, '
                  f'por debajo de la mediana de {mediana:.0f})' + (f' · idea: {idea}' if idea else "")), titulos


def controlar(contenido, historial, medir, reescribir):
    """Aplica el control. `reescribir(titulos_a_evitar)` devuelve un contenido nuevo.
    Devuelve (contenido, nota para el mail o "")."""
    if not activo():
        return contenido, ""
    notas = []
    evitar = []
    for intento in range(int(_cfg().get("intentos", 2)) + 1):
        try:
            frenar, motivo, titulos = decidir(contenido, historial, medir)
        except Exception as e:  # noqa
            util.log("Control de repetidos: no pude revisarlo, sigo:", util.ocultar(e))
            break
        if not frenar:
            if motivo:
                notas.append("🔁 " + motivo)
            break
        notas.append("🚫 Frené: " + motivo)
        util.log("Control de repetidos:", motivo)
        if intento >= int(_cfg().get("intentos", 2)):
            notas.append("Salió igual porque no encontré otro tema distinto después de varios intentos.")
            util.avisar("Tema parecido a uno anterior", motivo)
            break
        evitar = list(dict.fromkeys(titulos + [contenido.get("titulo", "")] + evitar))
        try:
            contenido = reescribir(evitar)
        except Exception as e:  # noqa
            util.log("Control de repetidos: no pude reescribir, sigo con el que había:", util.ocultar(e))
            break
    return contenido, " ".join(notas)
