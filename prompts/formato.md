Formato: VIDEO CORTO con voz en off y placas.
- Entre 6 y 8 escenas. Entre 90 y 130 palabras en total (se dice en 35 a 50 segundos).
- Escena 1 = el gancho. Máximo 10 palabras. Tiene que funcionar aunque alguien lo vea sin sonido.
- Cada escena: texto_voz (lo que se dice, escrito para el oído) y texto_pantalla (máximo 6 palabras, lo que se lee en la placa, no repite la voz palabra por palabra).
- La última escena invita a seguir o a guardar, con una frase distinta cada vez (ver banco de cierres).
- Escribí como se habla: contracciones naturales, nada de oraciones con tres comas.
- Para cada escena agregá también: emoji (UN solo emoji estándar que ilustre la escena, sin banderas ni tonos de piel) y prompt (descripción en inglés de una ilustración simple con stick figures, sin texto ni números).

Formato: CARRUSEL de 6 a 8 placas.
- Placa 1 (portada): máximo 7 palabras que generen curiosidad o toquen un dolor. Más una línea chica de apoyo de máximo 5 palabras.
- Placas del medio: una idea por placa. Título corto (máximo 6 palabras) + cuerpo de máximo 25 palabras.
- Penúltima placa: el dato o tip más útil (es la que la gente guarda).
- Última placa: cierre con llamada a la acción ("Guardalo para cuando cobres", "Mandáselo a quien siempre llega pelado a fin de mes").
- En la placa 1, titulo es la frase de portada y cuerpo la línea de apoyo. En la última, titulo es la llamada a la acción y cuerpo una frase corta de apoyo.
- Para cada placa, un emoji (UN solo emoji estándar, sin banderas ni tonos de piel) para ilustrarla.

TEXTOS PARA PUBLICAR (los mismos en las 3 redes):
- titulo: máximo 55 caracteres, escrito como una oración normal: mayúscula solo al principio y en las siglas (ARCA, IVA, CUIT, ANSES), nunca Título En Mayúsculas. Con curiosidad real y sin mentir. Sin emojis.
- descripcion: 2 o 3 frases como si le escribieras a alguien por WhatsApp. La última invita a comentar con una pregunta concreta ("¿Vos en qué gastás el aguinaldo?").
- hashtags: 5 a 7, en minúscula, sin tildes, siempre #argentina más los de la serie (#finanzaspersonales, #ahorro, #economia, #monotributo, #libros, #plata).
- miniatura: linea1 (máximo 4 palabras) y linea2 (máximo 3), pensadas para que alguien frene el scroll.
- miniatura.emoji: un emoji que acompañe la portada. miniatura.prompt: ilustración en inglés con un stick figure exagerado (sorpresa, preocupación, alegría), sin texto.

El video y el carrusel tratan el MISMO tema, pero el carrusel se lee (más concreto, más guardable) y el video se escucha.

FORMATO DE RESPUESTA
Respondé SOLO con un JSON válido con esta forma exacta:
{
  "titulo": "...",
  "descripcion": "...",
  "hashtags": ["#...", "#..."],
  "miniatura": { "linea1": "...", "linea2": "...", "emoji": "...", "prompt": "..." },
  "escenas": [ { "texto_voz": "...", "texto_pantalla": "...", "emoji": "...", "prompt": "..." } ],
  "carrusel": [ { "titulo": "...", "cuerpo": "...", "emoji": "..." } ]
}
