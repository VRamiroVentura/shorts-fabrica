# Fábrica de contenido · plata, economía e impuestos

Todos los días, a la hora que le toca a cada serie (ver **Horarios**), este repositorio hace solo:

1. **Elige la serie del día**: lunes libro, martes plata fácil, miércoles economía, jueves la idea de un autor, viernes **impuestos sin vueltas** (la novedad impositiva que más le toca el bolsillo a la gente, tomada de los sitios y cuentas de contadores de referencia), sábado historias de plata, domingo **viral en el mundo** (un video de plata que explotó en Japón, Alemania, Corea, etc., contado en argentino y con la pregunta "¿acá funcionaría?").
2. **Investiga**: busca en los canales de referencia los videos que funcionaron muy por encima de su promedio.
3. **Escribe** el guion, el carrusel y los textos con voz argentina natural (ver `prompts/`). Después hace una segunda pasada que corrige todo lo que suene a IA.
4. **Diseña** las placas del carrusel y el video vertical: voz de Gemini (o la de Microsoft de respaldo), videos de stock de Pexels que cambian cada ~2 segundos, subtítulos grandes palabra por palabra, el gancho escrito desde el segundo 0, barra de progreso y música suave si hay un tema en `assets/`.
5. **Publica** en Instagram (Reel todos los días y carrusel martes y viernes), en YouTube Shorts y en TikTok, según lo que actives.
6. **Guarda el historial** en `publicaciones/` y te manda un mail con el resumen.

Los lunes además arma un **reporte** en `reportes/`: cómo le fue a cada serie nuestra (vistas, guardados, compartidos y comentarios), qué está funcionando en la competencia, qué series conviene reforzar o cambiar, y 10 ideas nuevas.

**Costo: US$ 0.** Usa GitHub Actions (gratis en repos públicos), la clave gratuita de Gemini, la API gratuita de YouTube y voces gratuitas de Microsoft.

---

## Puesta en marcha

### Paso 1 · Subir los archivos (5 minutos)

1. Descomprimí el zip en tu compu.
2. En el repo, tocá **Add file → Upload files**.
3. Arrastrá **todo el contenido** de la carpeta descomprimida, incluida la carpeta `.github`. En Windows se ve normal. En Mac, si no la ves, apretá `Cmd + Shift + .` en el Finder.
4. Tocá **Commit changes**.

### Paso 2 · Activar la página donde se alojan los archivos (1 minuto)

**Settings → Pages → Build and deployment → Source: GitHub Actions.**

Ahí se suben cada día el video y las placas. Instagram y TikTok necesitan un link público para leerlos.

### Paso 3 · Cargar las claves gratuitas mínimas (10 minutos)

Van en **Settings → Secrets and variables → Actions → New repository secret**. Nunca las pegues en un chat ni en un archivo.

| Secreto | Dónde se saca |
|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey → **Create API key** (gratis, sin tarjeta) |
| `YT_API_KEY` | https://console.cloud.google.com → creá un proyecto → **APIs y servicios → Biblioteca → YouTube Data API v3 → Habilitar** → **Credenciales → Crear credenciales → Clave de API** |
| `PIXABAY_API_KEY` (videos de fondo) | Creá una cuenta gratis en https://pixabay.com y entrá a https://pixabay.com/api/docs/ : tu clave aparece en verde en la sección **Parameters → key**. Sin tarjeta. Sin esto, el video usa ilustraciones o emojis de fondo. (También acepta `PEXELS_API_KEY` si algún día Pexels vuelve a dar claves.) |
| `SMTP_USER` y `SMTP_PASS` (opcional, para recibir el mail diario) | `SMTP_USER` es tu Gmail. `SMTP_PASS` es una **contraseña de aplicación**: https://myaccount.google.com/apppasswords (necesita tener activada la verificación en dos pasos) |

### Paso 4 · Poner tu usuario

Abrí `config.json`, tocá el lápiz y cambiá `"usuario": "@tu_cuenta"` por el @ que vas a usar en las tres redes. Guardá con **Commit changes**.

### Paso 5 · Primera prueba (sin publicar nada)

1. Pestaña **Actions → Publicación diaria → Run workflow**.
2. Destildá **"¿Publicar en las redes?"** y tocá **Run workflow**.
3. Esperá unos 5 minutos y entrá a la ejecución. Abajo de todo vas a ver el **resumen**: las placas, el link al video, el texto y el guion.

Si te gusta cómo queda, seguí con las redes.

---

## Conectar las redes

### Instagram (se publica solo desde el primer día)

Requisito: la cuenta de Instagram tiene que ser **profesional** (creador o empresa). Se cambia desde la app en *Configuración → Tipo de cuenta*.

1. Entrá a https://developers.facebook.com → **Mis apps → Crear app** → tipo **Empresa** (o "Otro").
2. Dentro de la app, agregá el producto **Instagram** → **Configuración de la API con inicio de sesión de Instagram**.
3. En **Generar tokens de acceso**, agregá tu cuenta de Instagram, aceptá los permisos y copiá el token.
4. Guardalo como secreto `IG_TOKEN`.
5. **Para que el token se renueve solo** (vence cada 60 días): creá un token de GitHub en https://github.com/settings/personal-access-tokens/new con **Repository access: solo `shorts-fabrica`** y **Permissions → Secrets: Read and write**. Guardalo como secreto `GH_PAT`.
6. En `config.json` poné `"instagram_reel": true` e `"instagram_carrusel": true`.

### Facebook (Reels en una página, se publica solo desde el primer día)

La API de Meta solo publica en **páginas**, no en perfiles personales.

1. Creá la página desde tu perfil: https://www.facebook.com/pages/create (mismo nombre y foto que en Instagram; categoría "Creador digital" o "Servicio financiero").
2. Vinculá Instagram a la página: en la página, *Configuración → Cuentas vinculadas → Instagram*.
3. En tu app de developers.facebook.com: *Casos de uso → Agregar caso de uso → "Administrar todo en tu página"*. Permisos: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` (y, si querés leer el Instagram de los contadores de referencia, también `instagram_basic` y `business_management`).
4. En https://developers.facebook.com/tools/explorer elegí la app, tocá **Generate Access Token** (token de usuario), tildá esos permisos y elegí tu página.
5. Hacelo durar: https://developers.facebook.com/tools/debug/accesstoken → pegá el token → **Extend Access Token** y copiá el nuevo.
6. En el Explorer, con ese token largo, consultá `me/accounts`. De tu página copiá `access_token` (este no vence) e `id`.
7. Guardá los secretos `FB_PAGE_TOKEN` y `FB_PAGE_ID`, y en `config.json` poné `"facebook": true`.
8. (Opcional) Consultá `{id de la página}?fields=instagram_business_account` y guardá ese id como `IG_FB_ID`: con eso la serie de impuestos también mira qué les funciona en Instagram a los contadores de referencia.

### YouTube (se sube solo, pero queda privado hasta que Google apruebe la app)

1. En el mismo proyecto de Google Cloud, habilitá **YouTube Data API v3** (ya lo hiciste en el paso 3).
2. **Pantalla de consentimiento de OAuth**: elegí tipo **Externo**, completá nombre y mail, y en **Estado de publicación** tocá **Publicar app (En producción)**. Si queda en "Prueba", el permiso vence cada 7 días y se corta todo.
3. **Credenciales → Crear credenciales → ID de cliente de OAuth → Aplicación web**. En *URI de redireccionamiento autorizados* poné `https://developers.google.com/oauthplayground`. Copiá el **ID de cliente** y el **secreto**.
4. Entrá a https://developers.google.com/oauthplayground:
   1. Tocá el engranaje, tildá **Use your own OAuth credentials** y pegá el ID y el secreto.
   2. A la izquierda escribí `https://www.googleapis.com/auth/youtube.upload` y tocá **Authorize APIs**. Entrá con la cuenta del canal; si aparece "app no verificada", tocá **Avanzado → Ir a la app**.
   3. Tocá **Exchange authorization code for tokens** y copiá el **Refresh token**.
5. Guardá los secretos `YT_CLIENT_ID`, `YT_CLIENT_SECRET` y `YT_REFRESH_TOKEN`.
6. En `config.json` poné `"youtube": true`.
7. Pedí la auditoría gratis en el formulario **"YouTube API Services - Audit and Quota Extension Form"** de Google. Hasta que la aprueben, los videos quedan privados y los pasás a público desde YouTube Studio con dos toques.

### TikTok (más adelante)

TikTok exige crear una app en https://developers.tiktok.com con **Content Posting API** y aprobarla. Hasta entonces, los videos subidos por API quedan en privado. Mientras tanto, el mail diario te trae el video y el texto para subirlo desde el celular en 30 segundos. Cuando quieras activarlo, avisame y lo configuramos juntos.

---

## Contadores de referencia (serie de los viernes)

Están en `config.json`, en `referentes_contables`:

- **Sitios** (se leen siempre, sin claves): Blog del Contador e Ignacio Online. La fábrica toma las novedades de los últimos 12 días y prioriza las que le tocan el bolsillo a la gente común (sueldo, monotributo, Ganancias, transferencias, alquileres, compras afuera). Descarta lo que solo le importa a contadores (convenios, aplicativos, eventos).
- **YouTube** (con `YT_API_KEY`): Errepar, Ignacio Online, Blog del Contador y Las Contas. Busca el video que rindió muy por encima de su promedio.
- **Instagram**: blogdelcontador, errepar, contadorasalcuadra2, ignacio.online y contadores_net. Busca el post que más les pegó comparado con lo normal de cada cuenta. Necesita la configuración opcional de abajo.

Nunca se copia el texto: el material solo sirve para elegir el tema y el formato. Los montos, topes y fechas solo se dicen si están textuales en la noticia del día.

### Opcional: leer el Instagram de los contadores de referencia

Instagram solo deja ver datos de otras cuentas con su API de Facebook ("Business Discovery"). Es gratis, pero pide que tu Instagram esté vinculado a una página de Facebook. Lo hacemos juntos cuando conectemos Instagram; estos son los pasos:

1. Creá una página de Facebook (puede llamarse igual que la cuenta) y vinculala desde Instagram: *Editar perfil → Página* o desde el *Centro de cuentas*.
2. En https://developers.facebook.com/tools/explorer elegí tu app, tocá **Generate Access Token** y tildá los permisos `instagram_basic`, `pages_show_list`, `pages_read_engagement` y `business_management`.
3. Hacé que dure: en https://developers.facebook.com/tools/debug/accesstoken pegá el token y tocá **Extend Access Token**.
4. De vuelta en el Explorer, con ese token, consultá `me/accounts` y copiá el `access_token` de tu página (ese no vence). Después consultá `{id de tu página}?fields=instagram_business_account` y copiá el `id`.
5. Guardá los secretos `IG_FB_TOKEN` (el token de la página) e `IG_FB_ID` (el id de Instagram).

Sin esto, la serie igual funciona con los sitios y YouTube.

## Opcionales que mejoran el resultado (también gratis)

| Secreto | Para qué |
|---|---|
| `CF_ACCOUNT_ID` y `CF_API_TOKEN` | Ilustraciones de stickman con IA en el video (Cloudflare Workers AI, cupo gratis diario). Sin esto, el video usa placas con emojis grandes. Se sacan en https://dash.cloudflare.com: Account ID en la home, y token en *My Profile → API Tokens → plantilla "Workers AI"* |
| `SUPADATA_KEY` | Baja la transcripción de los videos de referencia para que la IA entienda mejor qué funcionó (https://supadata.ai, plan gratis). Sin esto, usa el título y la descripción |

---

## Horarios

Cada día sale a la hora que figura en `config.json` → `horarios` (hora de Argentina; 1 = lunes … 7 = domingo):

| Día | Serie | Hora | Por qué |
|---|---|---|---|
| Lunes | Un libro en 60 segundos | 19:30 | Salida del laburo, ganas de "arrancar la semana" |
| Martes | Plata fácil | 13:00 | Almuerzo; martes al mediodía es de lo más fuerte en Instagram |
| Miércoles | Economía | 21:30 | Después de cenar, el pico de uso en Argentina |
| Jueves | La idea de un autor | 19:30 | Salida del laburo |
| Viernes | Impuestos sin vueltas | 12:30 | Contenido de trabajo: el monotributista lo ve en horario laboral |
| Sábado | Historias de plata | 18:30 | Sábado a la tarde, entretenimiento |
| Domingo | Viral en el mundo | 21:00 | Domingo a la noche, todos en casa con el celu |

Cómo funciona: un "reloj" corre cada 30 minutos; entre 60 y 30 minutos antes del horario arranca a fabricar y, con el video listo, espera al minuto exacto para publicar. Los horarios se pueden poner entre las 12:10 y las 22:30. Si un día publicás a mano (Run workflow con "publicar" tildado), ese día no vuelve a publicar solo.

El reporte de los lunes muestra las vistas promedio por franja horaria; cuando la cuenta pase los 100 seguidores, Instagram también muestra en *Panel profesional → Seguidores* las horas en que tu público está más activo. Con eso ajustamos.

## Voz y música

- **Voz:** en `config.json`, `voz_motor` es `gemini` (más natural, usa la misma clave) o `edge` (Microsoft). `voz_gemini` en `auto` busca una voz argentina en la biblioteca de Google; si no hay, usa `Puck`. Podés probar otras: `Orus`, `Charon`, `Fenrir` (hombre) o `Kore`, `Aoede`, `Leda` (mujer). `voz_tempo` en `1.1` la hace un poco más rápida. Si la voz de Gemini falla un día, el video sale igual con la de Microsoft y queda un aviso amarillo en la ejecución.
- **Música:** subí uno o varios `.mp3` libres de derechos a la carpeta `assets/` (ver `assets/LEEME.md`). Si no hay, va sin música.
- **Fondos:** para cada escena la fábrica junta opciones (tus clips de `assets/clips/` primero y después Pixabay), descarta las que muestran otros países o monedas, y una IA mira una imagen de cada una y elige solo las que pegan con lo que se dice. Si ninguna pega, usa un comodín de plata y trámites (manos contando plata, celular, posnet, papeles). Además mete hasta 3 **postales de Argentina** por video (drones de Buenos Aires, Patagonia, Iguazú, glaciares, mar, mate, asado) en la intriga, en el cierre y donde no haya nada mejor, para enganchar la vista; solo usa tomas cuyas etiquetas dicen que son de acá. Se regula con `postales_por_video` en `config.json`. Grabar 20 o 30 clips propios con el celu (billetes, tarjeta, celular, calles de La Plata) es lo que más lo hace "argento": ver `assets/clips/LEEME.md`.

## Cómo cambiar cosas

- **Días, series y canales de referencia:** `config.json`. La serie "Mito o verdad" quedó guardada: para volver a usarla, poné `"mito"` en algún día de `plan_semanal`. En la serie viral, los países y búsquedas están en `busquedas`.
- **La voz y el estilo de escritura:** `prompts/maestro.md`. Las reglas de formato están en `prompts/formato.md` y la revisión anti-IA en `prompts/revision.md`.
- **Probar una serie puntual:** *Actions → Publicación diaria → Run workflow* y escribí la serie (por ejemplo `monotributo`, que es la de impuestos).

## Si algo falla

- GitHub te manda un mail automático cuando una ejecución falla.
- El mail diario dice qué se publicó y qué no, con el motivo.
- Todo queda registrado en `publicaciones/` (un archivo por día) y en `data/historial.json`.
