"""Prueba las conexiones con las redes SIN publicar nada: python -m fabrica.main probar

Sirve para revisar en un minuto si las llaves de Instagram, Facebook y YouTube andan,
sin esperar a la publicación del día. Nunca muestra las llaves.
"""
import os
import sys

from . import publicar as pub
from . import util

PERMISOS_FB = {"pages_show_list", "pages_read_engagement", "pages_manage_posts"}


def _instagram(filas):
    token = util.secreto("IG_TOKEN")
    if not token:
        filas.append(("Instagram", False, "Falta el secreto IG_TOKEN."))
        return
    r = util.pedir("GET", pub.IG + "me", intentos=2,
                   params={"fields": "user_id,username,account_type", "access_token": token})
    if r is None or r.status_code != 200:
        filas.append(("Instagram · la llave", False, pub._meta_error(r)))
        return
    d = r.json()
    filas.append(("Instagram · la llave", True, f'Cuenta @{d.get("username")} ({d.get("account_type", "?")})'))
    uid = d.get("user_id") or d.get("id")
    r = util.pedir("GET", pub.IG + f"{uid}/content_publishing_limit", intentos=2,
                   params={"fields": "quota_usage,config", "access_token": token})
    if r is None or r.status_code != 200:
        filas.append(("Instagram · permiso para publicar", False, pub._meta_error(r)))
        return
    datos = (r.json().get("data") or [{}])[0]
    usados = datos.get("quota_usage", 0)
    total = (datos.get("config") or {}).get("quota_total", "?")
    filas.append(("Instagram · permiso para publicar", True, f"Puede publicar (hoy usó {usados} de {total})"))


def _facebook(filas):
    token, pagina = util.secreto("FB_PAGE_TOKEN"), util.secreto("FB_PAGE_ID")
    if not (token and pagina):
        faltan = [n for n, v in (("FB_PAGE_TOKEN", token), ("FB_PAGE_ID", pagina)) if not v]
        filas.append(("Facebook", False, "Falta el secreto " + " y ".join(faltan) + "."))
        return
    r = util.pedir("GET", pub.FB + "me", intentos=2, params={"fields": "id,name", "access_token": token})
    if r is None or r.status_code != 200:
        filas.append(("Facebook · la llave", False, pub._meta_error(r)))
        return
    d = r.json()
    if str(d.get("id")) != str(pagina).strip():
        filas.append(("Facebook · la llave", False,
                      f'La llave guardada es de «{d.get("name")}», no de la página cuyo id está en FB_PAGE_ID. '
                      f'Hay que guardar en FB_PAGE_TOKEN el access_token que aparece en me/accounts junto a tu '
                      f'página (o revisar que FB_PAGE_ID sea el id de la página).'))
    else:
        filas.append(("Facebook · la llave", True, f'Es la llave de la página «{d.get("name")}»'))
    r = util.pedir("GET", pub.FB + "debug_token", intentos=2,
                   params={"input_token": token, "access_token": token})
    if r is None or r.status_code != 200:
        filas.append(("Facebook · permisos", None, "No se pudieron leer los permisos: " + pub._meta_error(r)))
        return
    info = r.json().get("data", {})
    permisos = set(info.get("scopes") or [])
    faltan = sorted(PERMISOS_FB - permisos)
    vence = info.get("expires_at", 0)
    detalle = f'tipo {info.get("type", "?")}, ' + ("no vence" if not vence else "vence (no es la llave permanente)")
    if not info.get("is_valid", True):
        filas.append(("Facebook · permisos", False, "La llave ya no es válida. " + detalle))
    elif faltan:
        filas.append(("Facebook · permisos", False,
                      "A la llave le faltan estos permisos: " + ", ".join(faltan) + f" ({detalle})"))
    else:
        filas.append(("Facebook · permisos", True, "Tiene los 3 permisos para publicar · " + detalle))


def _youtube(filas):
    cid, cs, rt = (util.secreto("YT_CLIENT_ID"), util.secreto("YT_CLIENT_SECRET"), util.secreto("YT_REFRESH_TOKEN"))
    if not (cid and cs and rt):
        filas.append(("YouTube", False, "Faltan secretos (YT_CLIENT_ID, YT_CLIENT_SECRET o YT_REFRESH_TOKEN)."))
        return
    r = util.pedir("POST", "https://oauth2.googleapis.com/token", intentos=2, data={
        "client_id": cid, "client_secret": cs, "refresh_token": rt, "grant_type": "refresh_token"})
    if r is None or r.status_code != 200:
        filas.append(("YouTube · la llave", False, util.ocultar(getattr(r, "text", "sin respuesta"))[:300]))
        return
    acceso = r.json()["access_token"]
    r = util.pedir("GET", "https://www.googleapis.com/youtube/v3/channels", intentos=2,
                   params={"part": "snippet", "mine": "true"}, headers={"Authorization": f"Bearer {acceso}"})
    if r is not None and r.status_code == 200 and r.json().get("items"):
        s = r.json()["items"][0]["snippet"]
        filas.append(("YouTube", True, f'Canal «{s.get("title")}» {s.get("customUrl", "")}'.strip()))
    elif r is not None and r.status_code == 200:
        filas.append(("YouTube", False, "La cuenta conectada no tiene canal de YouTube."))
    elif r is not None and r.status_code == 403 and "insufficient" in r.text.lower():
        # con el permiso de solo subir videos Google no deja leer el canal: no es un error de publicación
        filas.append(("YouTube", True, "La llave funciona (con este permiso Google no muestra el nombre del canal)"))
    else:
        filas.append(("YouTube", False, util.ocultar(getattr(r, "text", "sin respuesta"))[:300]))


def probar():
    filas = []
    for paso in (_instagram, _facebook, _youtube):
        try:
            paso(filas)
        except Exception as e:  # noqa
            filas.append((paso.__name__.strip("_").capitalize(), False, util.ocultar(f"{type(e).__name__}: {e}")))
    icono = {True: "✅", False: "❌", None: "⚠️"}
    md = ["## Prueba de conexiones (no se publicó nada)", "", "| | Qué | Resultado |", "|---|---|---|"]
    for que, ok, detalle in filas:
        util.log(icono[ok], que, "·", detalle)
        md.append(f"| {icono[ok]} | {que} | {detalle.replace('|', '/')} |")
    destino = os.getenv("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
    if any(ok is False for _, ok, _ in filas):
        sys.exit(1)
