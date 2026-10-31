# Banco de imágenes de La Plata

- `lugares.json`: lugares emblemáticos y mapas que se buscan (y el plano actual de OpenStreetMap).
- `historias.json`: historias raras y curiosas de La Plata, con su estado (verificado, leyenda o chequear), los datos que puede usar el guion, las fuentes y las fotos de cada una.
- `prompts-maquetas.md`: cómo hacer gratis las maquetas 3D de cada edificio con la app de Gemini.
- `descartar.txt` (opcional): nombres de archivos de Commons que no sirven (por ejemplo `File:Catedral de La Plata 3.jpg`), uno por línea. La próxima corrida los borra y busca otros.

Las imágenes quedan en `assets/laplata/`, con `catalogo.json` (qué hay de cada tema) y `CREDITOS.md` (autor y licencia de cada foto).

## Cómo correrlo
Actions → **Banco de imágenes de La Plata** → Run workflow:
- **muestra**: 4 temas y el plano actual, sin guardar nada. Bajá el artefacto `banco-laplata` y mirá la hoja de contacto.
- **completo**: todo, y lo guarda en el repo. Se puede repetir: no vuelve a bajar lo que ya está.
- **solo**: para rehacer algunos temas, por ejemplo `catedral,plano_actual`.

## Licencias
Solo se bajan fotos con licencia libre (dominio público, CC0, CC BY o CC BY-SA). Nada con "NC" (no comercial) ni "ND".
CC BY y CC BY-SA piden nombrar al autor: por eso queda todo en CREDITOS.md, y cuando un video use una foto, el crédito va en la descripción.
El plano actual usa datos de OpenStreetMap: lleva escrito "© OpenStreetMap contributors".
