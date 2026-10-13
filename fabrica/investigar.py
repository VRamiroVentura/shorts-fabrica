"""Busca en los canales de referencia los videos 'fuera de serie' (muchas más vistas que su promedio)."""
import re
from datetime import timedelta

from . import util

YT = "https://www.googleapis.com/youtube/v3/"


def _segundos(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)) if m else 0


def _get(endpoint, clave, **params):
    params["key"] = clave
    r = util.pedir("GET", YT + endpoint, params=params, timeout=60)
    if r.status_code != 200:
        util.log("YouTube API", endpoint, r.status_code, r.text[:200])
        return {}
    return r.json()


def canal_id(busqueda, clave, cache):
    if busqueda in cache:
        return cache[busqueda]
    data = _get("search", clave, part="snippet", type="channel", maxResults=1, q=busqueda)
    items = data.get("items") or []
    if not items:
        return None
    it = items[0]
    info = {"id": it["snippet"]["channelId"], "nombre": it["snippet"]["channelTitle"]}
    cache[busqueda] = info
    return info


def videos_recientes(cid, clave):
    pl = _get("playlistItems", clave, part="contentDetails", playlistId="UU" + cid[2:], maxResults=50)
    ids = [x["contentDetails"]["videoId"] for x in pl.get("items", [])]
    if not ids:
        return []
    data = _get("videos", clave, part="snippet,statistics,contentDetails", id=",".join(ids), maxResults=50)
    out = []
    for v in data.get("items", []):
        sn, st = v.get("snippet", {}), v.get("statistics", {})
        out.append({
            "id": v["id"],
            "titulo": sn.get("title", ""),
            "descripcion": (sn.get("description") or "")[:700],
            "publicado": sn.get("publishedAt", ""),
            "vistas": int(st.get("viewCount", 0) or 0),
            "segundos": _segundos(v.get("contentDetails", {}).get("duration")),
        })
    return out


def _mediana(nums):
    s = sorted(nums)
    return s[len(s) // 2] if s else 1


def fuera_de_serie(busquedas, clave, usados, cantidad=2):
    cache = util.leer_json("data/canales.json", {})
    limite = (util.ahora() - timedelta(days=3 * 365)).isoformat()
    candidatos = []
    for b in busquedas:
        info = canal_id(b, clave, cache)
        if not info:
            continue
        vids = [v for v in videos_recientes(info["id"], clave) if v["vistas"] > 0]
        if len(vids) < 5:
            continue
        med = _mediana([v["vistas"] for v in vids]) or 1
        for v in vids:
            if v["id"] in usados or (v["publicado"] and v["publicado"] < limite):
                continue
            candidatos.append(dict(v, canal=info["nombre"], mediana=med, score=round(v["vistas"] / med, 2)))
    util.guardar_json("data/canales.json", cache)
    candidatos.sort(key=lambda c: c["score"], reverse=True)
    elegidos, por_canal = [], set()
    for c in candidatos:
        if len(elegidos) >= cantidad:
            break
        if c["canal"] in por_canal or c["score"] < 1.3:
            continue
        por_canal.add(c["canal"])
        elegidos.append(c)
    return elegidos


def transcripcion(video_id):
    clave = util.secreto("SUPADATA_KEY")
    if not clave:
        return ""
    r = util.pedir("GET", "https://api.supadata.ai/v1/transcript", intentos=2,
                   headers={"x-api-key": clave},
                   params={"url": f"https://www.youtube.com/watch?v={video_id}", "text": "true", "mode": "native"})
    if r is None or r.status_code != 200:
        return ""
    c = r.json().get("content", "")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c)
    return re.sub(r"\s+", " ", c or "").strip()[:4000]


def metricas_canal(busqueda, clave, cache):
    """Para el reporte semanal."""
    info = canal_id(busqueda, clave, cache)
    if not info:
        return None
    vids = videos_recientes(info["id"], clave)
    if not vids:
        return None
    hoy = util.ahora()
    med = _mediana([v["vistas"] for v in vids]) or 1
    hace30 = (hoy - timedelta(days=30)).isoformat()
    hace365 = (hoy - timedelta(days=365)).isoformat()
    top = sorted([v for v in vids if v["publicado"] >= hace365], key=lambda v: v["vistas"], reverse=True)[:3]
    return {
        "canal": info["nombre"],
        "videos_por_semana": round(len([v for v in vids if v["publicado"] >= hace30]) / 4.3, 1),
        "mediana": med,
        "pct_shorts": round(100 * len([v for v in vids if 0 < v["segundos"] <= 180]) / len(vids)),
        "top": [{"titulo": v["titulo"], "vistas": v["vistas"], "veces": round(v["vistas"] / med, 1),
                 "short": 0 < v["segundos"] <= 180} for v in top],
    }


def _detalles(ids, clave):
    if not ids:
        return []
    data = _get("videos", clave, part="snippet,statistics,contentDetails", id=",".join(ids[:50]), maxResults=50)
    out = []
    for v in data.get("items", []):
        sn, st = v.get("snippet", {}), v.get("statistics", {})
        out.append({
            "id": v["id"], "titulo": sn.get("title", ""), "canal": sn.get("channelTitle", ""),
            "descripcion": (sn.get("description") or "")[:700], "publicado": sn.get("publishedAt", ""),
            "vistas": int(st.get("viewCount", 0) or 0),
            "segundos": _segundos(v.get("contentDetails", {}).get("duration")),
        })
    return out


def virales_mundo(busquedas, clave, usados, cantidad=2):
    """Serie 'Viral en el mundo': el video de plata más visto del último año en cada país elegido."""
    desde = (util.ahora() - timedelta(days=365)).astimezone(util.ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    elegidos = []
    for b in busquedas:
        if len(elegidos) >= cantidad:
            break
        data = _get("search", clave, part="snippet", type="video", q=b["q"], relevanceLanguage=b["idioma"],
                    regionCode=b["region"], order="viewCount", videoDuration="short", maxResults=15,
                    publishedAfter=desde)
        ids = [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]
        vids = sorted([v for v in _detalles(ids, clave) if v["id"] not in usados], key=lambda v: v["vistas"],
                      reverse=True)
        if vids:
            elegidos.append(dict(vids[0], pais=b["pais"], idioma=b["idioma"], score=None))
    return elegidos


def estadisticas_youtube(ids, clave):
    """Vistas, likes y comentarios de nuestros propios videos públicos."""
    out = {}
    for i in range(0, len(ids), 50):
        data = _get("videos", clave, part="statistics", id=",".join(ids[i:i + 50]))
        for v in data.get("items", []):
            st = v.get("statistics", {})
            out[v["id"]] = {"vistas": int(st.get("viewCount", 0) or 0), "likes": int(st.get("likeCount", 0) or 0),
                            "comentarios": int(st.get("commentCount", 0) or 0)}
    return out
