# Control de temas repetidos

## Subir
1. Descomprimí el zip.
2. En **shorts-fabrica**, con la rama **main**: **Add file → Upload files**.
3. Arrastrá todo el contenido (carpeta `fabrica` + `config.json`) → **Commit changes**.

Reemplaza `fabrica/main.py` y `config.json`, y agrega `fabrica/repetidos.py`.
Este `config.json` ya trae todo lo del zip anterior (música de Instagram y bancos) más el bloque nuevo.

No hace falta cargar ninguna clave nueva.

## Qué hace
Antes de armar el video, la IA compara la idea del guion con lo publicado en los últimos 60 días:
- Misma idea que algo de los últimos 7 días → lo frena y escribe otro tema.
- Misma idea que un video viejo que anduvo bien (vistas por encima de la mediana) → lo deja pasar como relanzamiento.
- Misma idea que un video viejo que anduvo mal → lo frena y escribe otro tema.
Si después de 2 intentos sigue parecido, sale igual (nunca se pierde el video del día).
En el mail diario aparece la línea **Temas repetidos** cuando frenó o relanzó algo.
Los temas que pedís vos a mano no se controlan.

## Ajustes (config.json → control_repetidos)
- `activo`: `false` para apagarlo.
- `dias_bloqueo`: 7. Subilo si querés más aire entre temas parecidos.
- `dias`: 60 (cuánto hacia atrás mira).
