"""Publica en Instagram, YouTube y TikTok, y manda el mail de resumen."""
import os
import smtplib
import subprocess
import time
from email.mime.text import MIMEText

from . import util

IG = "https://graph.instagram.com/v23.0/"


# ------------------------------------------------------------------ secretos que se renuevan solos
def actualizar_secreto(nombre, valor):
    """Guarda un token renovado como secreto del repo (requiere el secreto GH_PAT)."""
    pat = util.secreto("GH_PAT")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not (pat and repo):
        return False
    r = subprocess.run(["gh", "secret", "set", nombre, "--repo", repo, "--body", valor],
                       env={**os.environ, "GH_TOKEN": pat}, capture_output=True, text=True)
    if r.returncode != 0:
        util.log("No pude actualizar el secreto", nombre, r.stderr[:200])
    return r.returncode == 0


# ------------------------------------------------------------------ Instagram
def _meta_error(r):
    """Mensaje de error de Meta (Instagram o Facebook) con sus códigos, para poder diagnosticarlo."""
    if r is None:
        return "sin respuesta de Meta"
    try:
        e = r.json().get("error") or {}
    except Exception:  # noqa
        return f"HTTP {r.status_code}: {r.text[:300]}"
    if not e:
        return f"HTTP {r.status_code}: {r.text[:300]}"
    msg = e.get("message", "") if isinstance(e, dict) else str(e)
    if isinstance(e, dict):
        if e.get("error_user_msg"):
            msg += " · " + e["error_user_msg"]
        codigos = [f"código {e['code']}" if e.get("code") is not None else "",
                   f"subcódigo {e['error_subcode']}" if e.get("error_subcode") else "",
                   e.get("type", "")]
        codigos = [c for c in codigos if c]
        if codigos:
            msg += " (" + ", ".join(codigos) + ")"
    return util.ocultar(msg)[:500]


def _ig_error(r):
    return _meta_error(r)


def ig_token():
    """Devuelve un token válido de Instagram y lo renueva cada 7 días."""
    token = util.secreto("IG_TOKEN")
    if not token:
        return None, "falta el secreto IG_TOKEN"
    estado = util.leer_json("data/estado.json", {})
    ultima = estado.get("ig_renovado", "")
    hoy = util.ahora()
    if not ultima or (hoy - util.datetime.fromisoformat(ultima)).days >= 7:
        r = util.pedir("GET", "https://graph.instagram.com/refresh_access_token",
                       params={"grant_type": "ig_refresh_token", "access_token": token})
        if r is not None and r.status_code == 200:
            nuevo = r.json().get("access_token", token)
            dias = int(r.json().get("expires_in", 0)) // 86400
            estado["ig_renovado"] = hoy.isoformat()
            estado["ig_vence_en_dias"] = dias
            if nuevo != token:
                if actualizar_secreto("IG_TOKEN", nuevo):
                    token = nuevo
                else:
                    estado["ig_aviso"] = "El token de Instagram cambió y no se pudo guardar (falta GH_PAT)."
            util.guardar_json("data/estado.json", estado)
    return token, None


def _ig_esperar(cid, token, minutos=6):
    fin = time.time() + minutos * 60
    while time.time() < fin:
        r = util.pedir("GET", IG + cid, params={"fields": "status_code,status", "access_token": token})
        st = (r.json() if r is not None and r.status_code == 200 else {}).get("status_code")
        if st == "FINISHED":
            return True
        if st == "ERROR":
            raise RuntimeError("Instagram no pudo procesar el archivo: " + str(r.json()))
        time.sleep(10)
    raise RuntimeError("Instagram tardó demasiado en procesar")


def _ig_publicar(cid, token):
    r = util.pedir("POST", IG + "me/media_publish", data={"creation_id": cid, "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(_ig_error(r))
    return r.json()["id"]


def instagram_reel(video_url, cover_url, caption):
    token, err = ig_token()
    if err:
        raise RuntimeError(err)
    r = util.pedir("POST", IG + "me/media", data={
        "media_type": "REELS", "video_url": video_url, "cover_url": cover_url,
        "caption": caption, "share_to_feed": "true", "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(_ig_error(r))
    cid = r.json()["id"]
    _ig_esperar(cid, token)
    return _ig_publicar(cid, token)


def instagram_carrusel(urls, caption):
    token, err = ig_token()
    if err:
        raise RuntimeError(err)
    hijos = []
    for u in urls[:10]:
        r = util.pedir("POST", IG + "me/media", data={"image_url": u, "is_carousel_item": "true",
                                                       "access_token": token})
        if r.status_code != 200:
            raise RuntimeError(_ig_error(r))
        hijos.append(r.json()["id"])
    r = util.pedir("POST", IG + "me/media", data={"media_type": "CAROUSEL", "children": ",".join(hijos),
                                                   "caption": caption, "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(_ig_error(r))
    cid = r.json()["id"]
    _ig_esperar(cid, token, minutos=3)
    return _ig_publicar(cid, token)


# ------------------------------------------------------------------ YouTube
def youtube(video_path, titulo, descripcion, tags, privacidad="public"):
    cid, cs, rt = (util.secreto("YT_CLIENT_ID"), util.secreto("YT_CLIENT_SECRET"), util.secreto("YT_REFRESH_TOKEN"))
    if not (cid and cs and rt):
        raise RuntimeError("faltan los secretos de YouTube (YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)")
    r = util.pedir("POST", "https://oauth2.googleapis.com/token", data={
        "client_id": cid, "client_secret": cs, "refresh_token": rt, "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise RuntimeError("YouTube no renovó el acceso: " + r.text[:200])
    acceso = r.json()["access_token"]
    tamano = os.path.getsize(video_path)
    meta = {
        "snippet": {"title": titulo[:100], "description": descripcion[:4900], "tags": tags[:15],
                    "categoryId": "27", "defaultLanguage": "es", "defaultAudioLanguage": "es-419"},
        "status": {"privacyStatus": privacidad, "selfDeclaredMadeForKids": False},
    }
    r = util.pedir("POST", "https://www.googleapis.com/upload/youtube/v3/videos",
                   params={"uploadType": "resumable", "part": "snippet,status"}, json=meta,
                   headers={"Authorization": f"Bearer {acceso}", "X-Upload-Content-Type": "video/mp4",
                            "X-Upload-Content-Length": str(tamano)})
    if r.status_code != 200:
        raise RuntimeError("YouTube rechazó la subida: " + r.text[:300])
    destino = r.headers["Location"]
    with open(video_path, "rb") as f:
        r = util.pedir("PUT", destino, data=f.read(), timeout=600,
                       headers={"Authorization": f"Bearer {acceso}", "Content-Type": "video/mp4"})
    if r.status_code not in (200, 201):
        raise RuntimeError("YouTube falló al subir: " + r.text[:300])
    return r.json()["id"]


# ------------------------------------------------------------------ TikTok
def tiktok(video_path, caption, privacidad="SELF_ONLY"):
    ck, cs, rt = (util.secreto("TIKTOK_CLIENT_KEY"), util.secreto("TIKTOK_CLIENT_SECRET"),
                  util.secreto("TIKTOK_REFRESH_TOKEN"))
    if not (ck and cs and rt):
        raise RuntimeError("faltan los secretos de TikTok")
    r = util.pedir("POST", "https://open.tiktokapis.com/v2/oauth/token/", data={
        "client_key": ck, "client_secret": cs, "grant_type": "refresh_token", "refresh_token": rt})
    datos = r.json() if r is not None else {}
    if r.status_code != 200 or "access_token" not in datos:
        raise RuntimeError("TikTok no renovó el acceso: " + r.text[:200])
    if datos.get("refresh_token") and datos["refresh_token"] != rt:
        actualizar_secreto("TIKTOK_REFRESH_TOKEN", datos["refresh_token"])
    acceso = datos["access_token"]
    tamano = os.path.getsize(video_path)
    r = util.pedir("POST", "https://open.tiktokapis.com/v2/post/publish/video/init/",
                   headers={"Authorization": f"Bearer {acceso}", "Content-Type": "application/json; charset=UTF-8"},
                   json={"post_info": {"title": caption[:2200], "privacy_level": privacidad,
                                       "disable_comment": False, "disable_duet": False, "disable_stitch": False,
                                       "video_cover_timestamp_ms": 100},
                         "source_info": {"source": "FILE_UPLOAD", "video_size": tamano, "chunk_size": tamano,
                                         "total_chunk_count": 1}})
    if r.status_code != 200:
        raise RuntimeError("TikTok rechazó la subida: " + r.text[:300])
    d = r.json()["data"]
    with open(video_path, "rb") as f:
        r2 = util.pedir("PUT", d["upload_url"], data=f.read(), timeout=600,
                        headers={"Content-Type": "video/mp4", "Content-Length": str(tamano),
                                 "Content-Range": f"bytes 0-{tamano - 1}/{tamano}"})
    if r2.status_code not in (200, 201):
        raise RuntimeError("TikTok falló al subir: " + r2.text[:300])
    return d.get("publish_id", "ok")


# ------------------------------------------------------------------ mail
# ------------------------------------------------------------------ Facebook (Reels de la página)
FB = "https://graph.facebook.com/v25.0/"


def _fb_error(r):
    return _meta_error(r)


def facebook_reel(video_path, descripcion, titulo=""):
    """Sube el video como Reel a la página de Facebook (necesita FB_PAGE_TOKEN y FB_PAGE_ID)."""
    token, pagina = util.secreto("FB_PAGE_TOKEN"), util.secreto("FB_PAGE_ID")
    if not (token and pagina):
        raise RuntimeError("faltan los secretos FB_PAGE_TOKEN y FB_PAGE_ID")
    r = util.pedir("POST", FB + f"{pagina}/video_reels", data={"upload_phase": "start", "access_token": token})
    if r is None or r.status_code != 200 or "video_id" not in r.json():
        raise RuntimeError("Facebook no abrió la subida: " + _fb_error(r))
    vid = r.json()["video_id"]
    datos = open(video_path, "rb").read()
    r = util.pedir("POST", f"https://rupload.facebook.com/video-upload/v25.0/{vid}", timeout=600,
                   headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(datos)),
                            "Content-Type": "application/octet-stream"}, data=datos)
    if r is None or r.status_code != 200 or not r.json().get("success"):
        raise RuntimeError("Facebook no recibió el video: " + _fb_error(r))
    r = util.pedir("POST", FB + f"{pagina}/video_reels",
                   data={"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
                         "description": descripcion[:2200], "title": titulo[:100], "access_token": token})
    if r is None or r.status_code != 200 or not r.json().get("success"):
        raise RuntimeError("Facebook no publicó el Reel: " + _fb_error(r))
    fin = time.time() + 6 * 60
    while time.time() < fin:
        r = util.pedir("GET", FB + vid, params={"fields": "status", "access_token": token})
        st = (r.json() if r is not None and r.status_code == 200 else {}).get("status", {})
        fases = [st.get(k, {}) for k in ("uploading_phase", "processing_phase", "publishing_phase")]
        if any(f.get("status") == "error" for f in fases) or st.get("video_status") == "error":
            raise RuntimeError("Facebook rechazó el video: " + str(st)[:300])
        if st.get("publishing_phase", {}).get("status") == "complete":
            break
        time.sleep(10)
    return vid


def mail(asunto, html):
    usuario, clave = util.secreto("SMTP_USER"), util.secreto("SMTP_PASS")
    if not (usuario and clave):
        util.log("Sin SMTP configurado: no mando mail")
        return False
    destino = util.config().get("email_aviso") or usuario
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = asunto, usuario, destino
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(usuario, clave)
        s.send_message(msg)
    return True


def instagram_metricas(media_id):
    """Vistas, alcance, guardados, compartidos, comentarios y likes de una publicación nuestra."""
    token, err = ig_token()
    if err:
        return {}
    for metricas in ("views,reach,saved,shares,comments,likes", "reach,saved,shares,comments,likes"):
        r = util.pedir("GET", IG + f"{media_id}/insights", intentos=2,
                       params={"metric": metricas, "access_token": token})
        if r is not None and r.status_code == 200:
            out = {}
            for d in r.json().get("data", []):
                v = (d.get("values") or [{}])[0].get("value")
                if v is None:
                    v = (d.get("total_value") or {}).get("value", 0)
                out[d["name"]] = int(v or 0)
            return out
    r = util.pedir("GET", IG + media_id, intentos=2,
                   params={"fields": "like_count,comments_count", "access_token": token})
    if r is not None and r.status_code == 200:
        j = r.json()
        return {"likes": j.get("like_count", 0), "comments": j.get("comments_count", 0)}
    return {}
