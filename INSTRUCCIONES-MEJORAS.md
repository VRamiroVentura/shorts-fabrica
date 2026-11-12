# Mejoras: más bancos de clips + música de Instagram

## 0. Backup (antes de todo)
En el repo, tocá el botón de la rama (**main**) → escribí `backup-nov-2026` → **Create branch: backup-nov-2026 from main**.
Si algo sale mal, se vuelve a esa versión.

## 1. Subir los archivos
1. Descomprimí este zip.
2. En el repo (rama **main**): **Add file → Upload files**.
3. Arrastrá **todo el contenido** de la carpeta (incluida `.github`). Reemplaza solo estos archivos:
   - `fabrica/broll.py`, `fabrica/montaje.py`, `fabrica/publicar.py`, `fabrica/main.py`, `fabrica/util.py`
   - `config.json`, `.github/workflows/diario.yml`, `README.md`
   - nuevo: `assets/musica/LEEME.md`
4. **Commit changes**.

Ojo con `config.json`: es el de tu backup de hoy con dos bloques nuevos (`instagram_musica` y `bancos_clips`). Si lo cambiaste después de bajar el zip, avisame y lo combino.

## 2. Clave de Pexels (gratis)
1. Cuenta en https://www.pexels.com → pedí la clave en https://www.pexels.com/api/
2. **Settings → Secrets and variables → Actions → New repository secret** → nombre `PEXELS_API_KEY`.
3. (Opcional) Coverr: https://coverr.co/developers → secreto `COVERR_API_KEY`.

Nunca pegues las claves en el chat.

## 3. Permiso para la música de Instagram
La música se agrega por el camino de Facebook. Hay que regenerar el token con un permiso más:
1. https://developers.facebook.com/tools/explorer → elegí tu app → **Generate Access Token**.
2. Tildá: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` (y `business_management` si ya lo tenías).
3. Extendelo en https://developers.facebook.com/tools/debug/accesstoken → **Extend Access Token**.
4. En el Explorer, con ese token, consultá `me/accounts` y copiá el `access_token` de tu página.
5. Actualizá el secreto `IG_FB_TOKEN` con ese token (y verificá que `IG_FB_ID` esté cargado).

Si este paso no está hecho, no se rompe nada: el Reel sale como siempre, sin música, y te llega el aviso.

## 4. Probar
**Actions → Publicación diaria → Run workflow** con "¿Publicar en las redes?" **destildado**.
En el log buscá la línea `Video:` → `"banco": "Pixabay y Pexels"`.
La música de Instagram solo se ve en una publicación real (Instagram no permite vista previa).
En el log aparece `Reel publicado con música de Instagram: <tema>`.

## Ajustes (config.json)
- `instagram_musica.volumen_musica`: 15 (de 0 a 100). Si la música tapa la voz, bajalo a 10.
- `instagram_musica.busquedas`: estilos a buscar; `""` = temas en tendencia.
- `instagram_musica.activa`: `false` para apagarla.
- `bancos_clips`: qué bancos usar.
