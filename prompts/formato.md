Formato: VIDEO CORTO (Reel, Short o TikTok) con voz en off y videos de fondo.
- Entre 8 y 13 escenas. Cada escena es UNA sola frase de 4 a 12 palabras (se dice en 2 a 3 segundos). En total, entre 70 y 110 palabras (25 a 40 segundos). Más corto retiene más.
- Estructura, en este orden:
  1. Gancho (escena 1, máximo 9 palabras): una situación concreta, un dato que sorprenda o una pregunta que le toque a quien mira. Tiene que frenar el scroll en el primer segundo. Nunca una presentación.
  2. Intriga (escena 2): abrí una pregunta que se responde recién al final ("y lo mejor es que se puede recuperar", "pero hay un detalle que casi nadie mira").
  3. Desarrollo: un ejemplo concreto, una idea por escena, y que cada frase empuje a la siguiente ("y ahí", "el tema es que", "pero ojo").
  4. Remate: la respuesta o el dato útil, dicho clarísimo.
  5. Cierre (última escena): invitá a mandárselo a alguien puntual o a guardarlo, con una frase distinta cada vez.
- texto_voz: lo que se dice, escrito para el oído, como se habla.
- texto_pantalla: solo en la escena 1, el gancho escrito para leer sin sonido (máximo 7 palabras). En las demás escenas dejalo vacío.
- broll: búsqueda en inglés para encontrar un video de stock que muestre lo que se dice en esa escena. De 2 a 4 palabras, algo filmable y concreto (personas, manos, objetos, lugares). Sin marcas, logos, texto ni ideas abstractas. Ejemplos: "paying with credit card", "man counting cash", "woman looking at phone", "receipt printer", "calculator on desk", "busy city street".
- Para cada escena agregá también: emoji (UN solo emoji común de un objeto o símbolo, sin banderas) y prompt (descripción en inglés de una ilustración simple estilo dibujo animado, sin texto ni números), por si no aparece un video que sirva.

Formato: CARRUSEL de 6 a 8 placas.
- Placa 1 (portada): máximo 7 palabras que generen curiosidad o toquen un problema real. Más una línea chica de apoyo de máximo 5 palabras.
- Placas del medio: una idea por placa. Título corto (máximo 6 palabras) + texto de máximo 25 palabras.
- Penúltima placa: el dato o tip más útil (es la que la gente guarda).
- Última placa: cierre con llamada a la acción ("Guardalo para cuando cobres", "Mandáselo a quien siempre llega justo a fin de mes").
- En la placa 1, titulo es la frase de portada y texto la línea de apoyo. En la última, titulo es la llamada a la acción y texto una frase corta de apoyo.
- Para cada placa, un emoji (UN solo emoji común de un objeto o símbolo, sin banderas) para ilustrarla.

TEXTOS PARA PUBLICAR (los mismos en las 3 redes):
- titulo: máximo 55 caracteres, escrito como una oración normal: mayúscula solo al principio y en las siglas (ARCA, IVA, CUIT, ANSES), nunca Título En Mayúsculas. Con curiosidad real y sin mentir. Sin emojis.
- descripcion: 2 o 3 frases como si le escribieras a alguien por WhatsApp. La última invita a comentar con una pregunta concreta ("¿Vos en qué gastás el aguinaldo?").
- hashtags: 5 a 7, en minúscula, sin tildes, siempre #argentina más los de la serie (#finanzaspersonales, #ahorro, #economia, #monotributo, #libros, #plata).
- miniatura: linea1 (máximo 4 palabras) y linea2 (máximo 3), pensadas para que alguien frene el scroll.
- miniatura.emoji: un emoji que acompañe la portada. miniatura.prompt: ilustración en inglés de un personaje simple de dibujo animado con una emoción clara (sorpresa, preocupación, alegría), sin texto.

El video y el carrusel tratan el MISMO tema, pero el carrusel se lee (más concreto, más guardable) y el video se escucha.

FORMATO DE RESPUESTA
Respondé SOLO con un JSON válido con esta forma exacta:
{
  "titulo": "...",
  "descripcion": "...",
  "hashtags": ["#...", "#..."],
  "miniatura": { "linea1": "...", "linea2": "...", "emoji": "...", "prompt": "..." },
  "escenas": [ { "texto_voz": "...", "texto_pantalla": "...", "broll": "...", "emoji": "...", "prompt": "..." } ],
  "carrusel": [ { "titulo": "...", "texto": "...", "emoji": "..." } ]
}
