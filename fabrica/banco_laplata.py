"""Banco de imágenes de La Plata.

Baja fotos libres de Wikimedia Commons (lugares emblemáticos, fotos históricas y
mapas), dibuja el plano actual con datos de OpenStreetMap y deja todo en
assets/laplata/ con un catálogo (catalogo.json) y los créditos (CREDITOS.md).

Uso (lo corre el workflow "Banco de imágenes de La Plata"):
    python fabrica/banco_laplata.py --modo muestra
    python fabrica/banco_laplata.py --modo completo
    python fabrica/banco_laplata.py --modo completo --solo catedral,plano_actual

Muestra: 4 temas y el plano, sin guardar nada en el repo (solo la hoja de contacto).
Completo: todos los temas; el workflow guarda las imágenes en el repo.
Para sacar una foto que no sirve: agregá su nombre de Commons en
datos/laplata/descartar.txt y volvé a correrlo.
"""
import argparse
import io
import json
import math
import os
import re
import sys
import time
import unicodedata

import requests
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.getcwd()
DATOS = os.path.join(RAIZ, "datos", "laplata")
DESTINO = os.path.join(RAIZ, "assets", "laplata")
SALIDA = os.path.join(RAIZ, "out", "banco_laplata")
COMMONS = "https://commons.wikimedia.org/w/api.php"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = {"User-Agent": "shorts-fabrica/1.0 (https://github.com/VRamiroVentura/shorts-fabrica)"}
LICENCIAS_OK = ("cc0", "public domain", "dominio publico", "pd", "cc by", "cc-by")
LICENCIAS_NO = ("nc", "nd", "fair use", "non-free")
MUESTRA = ["catedral", "plaza_moreno", "teatro_argentino_antiguo", "plano_1882", "plano_actual"]
LADO_MAX = 1600


# ---------------------------------------------------------------- utilidades
def normal(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    texto = re.sub(r"<[^>]+>", " ", texto)
    return re.sub(r"[_\s]+", " ", texto).lower()


def leer_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def guardar_json(ruta, dato):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(dato, f, ensure_ascii=False, indent=2)


def fuente(tam, negrita=False):
    nombres = ["DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"]
    carpetas = ["/usr/share/fonts/truetype/dejavu/", ""]
    for c in carpetas:
        for n in nombres:
            try:
                return ImageFont.truetype(c + n, tam)
            except OSError:
                pass
    return ImageFont.load_default()


def pedir(metodo, url, intentos=3, **kw):
    kw.setdefault("timeout", 60)
    headers = dict(UA)
    headers.update(kw.pop("headers", {}))
    ultimo = None
    for i in range(intentos):
        try:
            r = requests.request(metodo, url, headers=headers, **kw)
            if r.status_code == 200:
                return r
            ultimo = f"HTTP {r.status_code}"
            if r.status_code in (429, 503, 504):
                time.sleep(5 * (i + 1))
                continue
            return None
        except requests.RequestException as e:
            ultimo = str(e)
            time.sleep(3 * (i + 1))
    print(f"  aviso: no pude bajar {url[:80]} ({ultimo})")
    return None


# ---------------------------------------------------------------- Commons
def licencia_ok(nombre):
    n = normal(nombre)
    if not n or any(re.search(rf"\b{x}\b", n) for x in LICENCIAS_NO):
        return False
    return any(x in n for x in LICENCIAS_OK)


def buscar_commons(consulta, limite=40):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{consulta} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": limite,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": LADO_MAX,
    }
    r = pedir("GET", COMMONS, params=params)
    if not r:
        return []
    paginas = (r.json().get("query") or {}).get("pages") or {}
    salida = []
    for p in paginas.values():
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        val = lambda k: (meta.get(k) or {}).get("value", "")
        salida.append({
            "titulo": p.get("title", ""),
            "orden": p.get("index", 999),
            "ancho": info.get("width", 0), "alto": info.get("height", 0),
            "mime": info.get("mime", ""),
            "url": info.get("thumburl") or info.get("url", ""),
            "pagina": info.get("descriptionurl", ""),
            "licencia": val("LicenseShortName"),
            "autor": re.sub(r"<[^>]+>", "", val("Artist")).strip()[:120],
            "texto": " ".join([p.get("title", ""), val("ImageDescription"), val("Categories"), val("ObjectName")]),
            "fecha": re.sub(r"<[^>]+>", "", val("DateTimeOriginal")).strip()[:40],
        })
    return salida


def pasa_filtro(img, tema, descartadas):
    if img["titulo"] in descartadas:
        return False
    if img["mime"] not in ("image/jpeg", "image/png"):
        return False
    if min(img["ancho"], img["alto"]) < tema.get("min_px", 700):
        return False
    if not licencia_ok(img["licencia"]):
        return False
    texto = normal(img["texto"])
    if any(normal(x) not in texto for x in tema.get("requiere", ["plata"])):
        return False
    if tema.get("palabras") and not any(normal(x) in texto for x in tema["palabras"]):
        return False
    if any(normal(x) in texto for x in tema.get("excluir", [])):
        return False
    return True


def puntaje(img, tema):
    texto = normal(img["titulo"])
    p = -img["orden"]
    if tema.get("palabras") and normal(tema["palabras"][0]) in texto:
        p += 30
    if img["ancho"] >= img["alto"] * 0.9:  # en vertical igual se recorta, pero horizontal da más zoom
        p += 5
    p += min(img["ancho"], 4000) / 400
    return p


def bajar_imagen(url, ruta):
    r = pedir("GET", url)
    if not r:
        return False
    try:
        im = Image.open(io.BytesIO(r.content))
        im = im.convert("RGB")
        im.thumbnail((LADO_MAX, LADO_MAX))
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        im.save(ruta, "JPEG", quality=86)
        return True
    except Exception as e:  # imagen rota
        print(f"  aviso: imagen inválida ({e})")
        return False


def tema_commons(tema, catalogo, descartadas):
    actual = catalogo.get(tema["id"], {})
    ya = {x["titulo_commons"] for x in actual.get("imagenes", [])}
    imagenes = []
    for x in actual.get("imagenes", []):
        ruta = os.path.join(RAIZ, x["archivo"])
        if x["titulo_commons"] in descartadas:
            if os.path.exists(ruta):
                os.remove(ruta)  # la foto descartada se borra del repo
        elif os.path.exists(ruta):
            imagenes.append(x)
    candidatos, vistos = [], set()
    for q in tema["buscar"]:
        for img in buscar_commons(q):
            if img["titulo"] in vistos:
                continue
            vistos.add(img["titulo"])
            if pasa_filtro(img, tema, descartadas):
                candidatos.append(img)
        time.sleep(0.5)
    candidatos.sort(key=lambda x: puntaje(x, tema), reverse=True)
    usados = {x["archivo"] for x in imagenes}
    n = 0
    for img in candidatos:
        if len(imagenes) >= tema.get("max", 3):
            break
        if img["titulo"] in ya:
            continue
        while True:  # primer nombre libre (no pisa fotos que ya están)
            n += 1
            rel = os.path.join("assets", "laplata", tema["grupo"], tema["id"], f"{tema['id']}_{n}.jpg")
            if rel.replace(os.sep, "/") not in usados and not os.path.exists(os.path.join(RAIZ, rel)):
                break
        if bajar_imagen(img["url"], os.path.join(RAIZ, rel)):
            imagenes.append({
                "archivo": rel.replace(os.sep, "/"),
                "titulo_commons": img["titulo"], "autor": img["autor"] or "Desconocido",
                "licencia": img["licencia"], "pagina": img["pagina"], "fecha": img["fecha"],
            })
        time.sleep(0.5)
    return {"nombre": tema["nombre"], "grupo": tema["grupo"], "tipo": "foto",
            "palabras": tema.get("etiquetas", []), "imagenes": imagenes,
            "encontradas": len(candidatos)}


# ---------------------------------------------------------------- plano actual (OSM)
CENTRO_PLAZA_MORENO = (-34.9214, -57.9545)  # aproximado; se corrige con el dato de OSM si aparece


def consulta_overpass(caja):
    s, o, n, e = caja
    return f"""
[out:json][timeout:120];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|pedestrian)$"]({s},{o},{n},{e});
  way["leisure"~"^(park|garden|pitch|stadium)$"]({s},{o},{n},{e});
  way["natural"="water"]({s},{o},{n},{e});
  way["building"]["name"]({s},{o},{n},{e});
);
out geom;
"""


def bajar_osm(caja):
    q = consulta_overpass(caja)
    for url in OVERPASS:
        r = pedir("POST", url, data={"data": q}, timeout=180, intentos=2)
        if r:
            try:
                return r.json().get("elements", [])
            except ValueError:
                pass
    return []


def angulo_grilla(elementos, proyectar):
    """Ángulo dominante de las calles (mod 90°), para poner la grilla derecha."""
    hist = [0.0] * 90
    segmentos = []
    for el in elementos:
        if "highway" not in el.get("tags", {}):
            continue
        pts = [proyectar(p["lat"], p["lon"]) for p in el.get("geometry", [])]
        for a, b in zip(pts, pts[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            largo = math.hypot(dx, dy)
            if largo < 1:
                continue
            ang = math.degrees(math.atan2(dy, dx)) % 90
            hist[int(ang) % 90] += largo
            segmentos.append((ang, largo))
    pico = max(range(90), key=lambda i: hist[i])
    suma = peso = 0.0
    for ang, largo in segmentos:  # promedio fino alrededor del pico
        dif = (ang - pico + 45) % 90 - 45
        if abs(dif) <= 2:
            suma += dif * largo
            peso += largo
    return round(pico + (suma / peso if peso else 0), 1)


PALETA = {
    "fondo": (239, 230, 207), "manzana": (232, 220, 190), "calle": (255, 251, 240),
    "avenida": (250, 244, 228), "borde": (196, 184, 152), "verde": (171, 196, 140),
    "agua": (150, 190, 205), "edificio": (196, 120, 90), "texto": (60, 52, 40),
}
ANCHOS = {"motorway": 9, "trunk": 9, "primary": 8, "secondary": 7, "tertiary": 6,
          "pedestrian": 4, "residential": 3, "unclassified": 3, "living_street": 3}


def dibujar_plano(elementos, lado=2400, girar=True):
    lat0 = sum(p["lat"] for el in elementos for p in el.get("geometry", [])[:1]) / max(1, len(elementos))
    k = math.cos(math.radians(lat0))
    puntos = [(p["lon"] * k, -p["lat"]) for el in elementos for p in el.get("geometry", [])]
    xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    esc = lado / max(max(xs) - min(xs), max(ys) - min(ys)) * 0.98

    def proyectar(lat, lon):
        return ((lon * k - cx) * esc + lado / 2, (-lat - cy) * esc + lado / 2)

    centro_pm = None
    for el in elementos:
        if normal(el.get("tags", {}).get("name")) == "plaza moreno" and el.get("geometry"):
            g = el["geometry"]
            centro_pm = (sum(p["lat"] for p in g) / len(g), sum(p["lon"] for p in g) / len(g))
    if not centro_pm:
        centro_pm = CENTRO_PLAZA_MORENO

    sup = 2  # dibujo al doble y achico: bordes suaves
    W = lado * sup
    im = Image.new("RGB", (W, W), PALETA["fondo"])
    d = ImageDraw.Draw(im)

    def P(p):
        x, y = proyectar(p["lat"], p["lon"])
        return (x * sup, y * sup)

    for el in elementos:
        t = el.get("tags", {})
        g = el.get("geometry", [])
        if len(g) < 3:
            continue
        if t.get("leisure") or t.get("natural") == "water":
            color = PALETA["agua"] if t.get("natural") == "water" else PALETA["verde"]
            d.polygon([P(p) for p in g], fill=color)
    calles = [el for el in elementos if "highway" in el.get("tags", {})]
    calles.sort(key=lambda el: ANCHOS.get(el["tags"]["highway"], 3))
    for borde in (True, False):
        for el in calles:
            w = ANCHOS.get(el["tags"]["highway"], 3) * sup
            pts = [P(p) for p in el.get("geometry", [])]
            if len(pts) < 2:
                continue
            if borde:
                d.line(pts, fill=PALETA["borde"], width=w + 2 * sup, joint="curve")
            else:
                color = PALETA["avenida"] if w >= 6 * sup else PALETA["calle"]
                d.line(pts, fill=color, width=w, joint="curve")
    for el in elementos:
        t = el.get("tags", {})
        g = el.get("geometry", [])
        if "building" in t and len(g) >= 3:
            d.polygon([P(p) for p in g], fill=PALETA["edificio"])

    im = im.resize((lado, lado), Image.LANCZOS)
    pm = proyectar(*centro_pm)
    ang = angulo_grilla(elementos, proyectar) if girar else 0
    if girar and ang:
        im = im.rotate(ang, resample=Image.BICUBIC, fillcolor=PALETA["fondo"], center=(lado / 2, lado / 2))
        r = math.radians(-ang)
        dx, dy = pm[0] - lado / 2, pm[1] - lado / 2
        pm = (lado / 2 + dx * math.cos(r) - dy * math.sin(r), lado / 2 + dx * math.sin(r) + dy * math.cos(r))
    return im, pm, ang


def firmar_osm(im):
    d = ImageDraw.Draw(im)
    t = "© OpenStreetMap contributors"
    f = fuente(max(14, im.width // 70))
    w = d.textlength(t, font=f)
    d.rectangle([im.width - w - 24, im.height - f.size - 22, im.width, im.height], fill=(239, 230, 207))
    d.text((im.width - w - 12, im.height - f.size - 14), t, font=f, fill=PALETA["texto"])
    return im


def tema_osm(tema):
    elementos = bajar_osm(tema["caja"])
    if len(elementos) < 50:
        print("  aviso: OpenStreetMap no respondió bien; el plano actual queda para la próxima.")
        return None
    salida = []
    carpeta = os.path.join("assets", "laplata", tema["grupo"], tema["id"])
    for girar, sufijo in ((False, "norte_arriba"), (True, "grilla_derecha")):
        im, pm, ang = dibujar_plano(elementos, girar=girar)
        cuad = firmar_osm(im.copy())
        cuad.thumbnail((LADO_MAX, LADO_MAX))
        rel = os.path.join(carpeta, f"plano_actual_{sufijo}.jpg")
        os.makedirs(os.path.join(RAIZ, carpeta), exist_ok=True)
        cuad.save(os.path.join(RAIZ, rel), "JPEG", quality=88)
        salida.append({"archivo": rel.replace(os.sep, "/"), "titulo_commons": "",
                       "autor": "OpenStreetMap contributors", "licencia": "ODbL",
                       "pagina": "https://www.openstreetmap.org/copyright", "fecha": time.strftime("%Y-%m"),
                       "vista": sufijo, "giro_grados": ang})
        # versión vertical para video, centrada en Plaza Moreno
        alto = int(im.width * 0.62)
        ancho = int(alto * 9 / 16)
        x0 = int(min(max(pm[0] - ancho / 2, 0), im.width - ancho))
        y0 = int(min(max(pm[1] - alto / 2, 0), im.height - alto))
        vert = firmar_osm(im.crop((x0, y0, x0 + ancho, y0 + alto)).resize((1080, 1920), Image.LANCZOS))
        relv = os.path.join(carpeta, f"plano_actual_{sufijo}_vertical.jpg")
        vert.save(os.path.join(RAIZ, relv), "JPEG", quality=88)
        salida.append(dict(salida[-1], archivo=relv.replace(os.sep, "/"), vista=sufijo + "_vertical"))
    return {"nombre": tema["nombre"], "grupo": tema["grupo"], "tipo": "mapa",
            "palabras": tema.get("etiquetas", []), "imagenes": salida, "encontradas": len(salida)}


# ---------------------------------------------------------------- salida
def hoja_contacto(catalogo, ids, ruta):
    fichas = []
    for i in ids:
        for n, img in enumerate(catalogo.get(i, {}).get("imagenes", []), 1):
            fichas.append((f"{i} #{n}", img["licencia"], os.path.join(RAIZ, img["archivo"])))
    if not fichas:
        return None
    col, cel, pie = 4, 300, 46
    filas = math.ceil(len(fichas) / col)
    hoja = Image.new("RGB", (col * cel, filas * (cel + pie)), (30, 30, 30))
    d = ImageDraw.Draw(hoja)
    f1, f2 = fuente(17, True), fuente(13)
    for k, (titulo, lic, ruta_img) in enumerate(fichas):
        x, y = (k % col) * cel, (k // col) * (cel + pie)
        try:
            im = Image.open(ruta_img).convert("RGB")
            im.thumbnail((cel - 8, cel - 8))
            hoja.paste(im, (x + (cel - im.width) // 2, y + (cel - im.height) // 2))
        except OSError:
            d.text((x + 10, y + 10), "sin imagen", font=f2, fill="white")
        d.text((x + 8, y + cel + 4), titulo, font=f1, fill="white")
        d.text((x + 8, y + cel + 25), lic[:40], font=f2, fill=(180, 180, 180))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    hoja.save(ruta, "JPEG", quality=85)
    return ruta


def escribir_creditos(catalogo):
    lineas = ["# Créditos del banco de imágenes de La Plata", "",
              "Fotos de Wikimedia Commons con licencia libre y plano con datos de OpenStreetMap.",
              "Si una imagen se usa en un video, el crédito va en la descripción (lo agrega la fábrica).", ""]
    for i, t in sorted(catalogo.items()):
        for img in t.get("imagenes", []):
            lineas.append(f"- `{img['archivo']}`: {img['autor']} · {img['licencia']} · {img['pagina']}")
    with open(os.path.join(DESTINO, "CREDITOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def cargar_temas():
    temas = []
    for nombre in ("lugares.json", "historias.json"):
        dato = leer_json(os.path.join(DATOS, nombre), {})
        temas += dato.get("imagenes", [])
    return temas


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["muestra", "completo"], default="muestra")
    ap.add_argument("--solo", default="")
    a = ap.parse_args(argv)

    temas = cargar_temas()
    if a.solo.strip():
        pedidos = {x.strip() for x in a.solo.split(",") if x.strip()}
        temas = [t for t in temas if t["id"] in pedidos]
    elif a.modo == "muestra":
        temas = [t for t in temas if t["id"] in MUESTRA]
    if not temas:
        print("No hay temas para bajar. Revisá los ids.")
        return 1

    destino_catalogo = os.path.join(DESTINO, "catalogo.json")
    catalogo = leer_json(destino_catalogo, {})
    descartadas = set()
    ruta_desc = os.path.join(DATOS, "descartar.txt")
    if os.path.exists(ruta_desc):
        with open(ruta_desc, encoding="utf-8") as f:
            descartadas = {l.strip() for l in f if l.strip() and not l.startswith("#")}

    resumen = []
    for t in temas:
        print(f"· {t['id']}")
        try:
            res = tema_osm(t) if t.get("tipo") == "osm" else tema_commons(t, catalogo, descartadas)
        except Exception as e:  # un tema roto no frena el resto
            print(f"  aviso: falló {t['id']} ({e})")
            res = None
        if res:
            catalogo[t["id"]] = res
            resumen.append((t["id"], len(res["imagenes"]), res.get("encontradas", 0)))
        else:
            resumen.append((t["id"], 0, 0))

    ids = [t["id"] for t in temas]
    hoja = hoja_contacto(catalogo, ids, os.path.join(SALIDA, "hoja_de_contacto.jpg"))
    guardar_json(destino_catalogo, catalogo)
    escribir_creditos(catalogo)

    md = ["## Banco de imágenes de La Plata", "", f"Modo: **{a.modo}**", "",
          "| Tema | Guardadas | Candidatas que pasaron el filtro |", "|---|---|---|"]
    md += [f"| {i} | {n} | {c} |" for i, n, c in resumen]
    vacios = [i for i, n, _ in resumen if n == 0]
    if vacios:
        md += ["", "Sin imágenes: " + ", ".join(vacios) + ". Probá con otras búsquedas en datos/laplata/."]
    md += ["", "La hoja de contacto está en los artefactos de esta ejecución (banco-laplata)."]
    texto = "\n".join(md) + "\n"
    print(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto)
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "resumen.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    return 0 if hoja else 2


if __name__ == "__main__":
    sys.exit(main())
