# Maquetas 3D de La Plata (a mano, gratis, con la app de Gemini)

Sirven para tener cada edificio en el mismo estilo "maqueta" (como datitalaplata) y parecido al real.

## Cómo hacerlas
1. Corré primero el workflow **Banco de imágenes de La Plata** en modo completo: te deja las fotos reales en `assets/laplata/`.
2. Abrí la app de Gemini (gemini.google.com). Adjuntá **una** foto real del edificio (la de frente que mejor se vea).
3. Pegá el **pedido base** y abajo la línea del edificio.
4. Si sale bien, pedile la versión vertical: "la misma imagen en formato vertical 9:16, con más fondo arriba y abajo".
5. Guardala con el nombre que dice cada línea y subila a `assets/laplata/maquetas/` (Add file → Upload files).
6. Si queda raro, pedile "más parecido a la foto" o "menos detalle, más simple". No aceptes una que cambie la forma del edificio.

Ojo: la app tiene un cupo diario gratis de imágenes. No sé el número exacto hoy; si se corta, seguí al otro día.

## Pedido base (copiar y pegar siempre)
```
Convertí el edificio de la foto en una maqueta 3D isométrica estilo low-poly, vista desde arriba en diagonal (unos 45 grados).
Respetá la forma real del edificio: cantidad de torres, ventanas principales, techo y proporciones.
Estilo: colores apagados (crema, verde oliva, terracota, gris piedra), luz suave de tarde, sombras largas, sin texturas fotográficas.
Alrededor: la vereda y un pedacito de calle y árboles redondeados, todo en el mismo estilo. Fondo liso color crema.
Sin personas, sin autos, sin carteles, sin texto, sin logos, sin marca de agua.
```

## Una línea por edificio (pegar debajo del pedido base)
| Archivo | Edificio | Línea para agregar |
|---|---|---|
| catedral.png | Catedral | Catedral neogótica de ladrillo rojizo con dos torres altas y puntiagudas al frente y un gran rosetón. |
| catedral_sin_torres.png | Catedral antes de 1999 | La misma catedral pero SIN las dos torres altas del frente: la fachada termina más baja. |
| palacio_municipal.png | Palacio Municipal | Palacio con una torre central con reloj. Respetá la fachada de la foto. |
| casa_gobierno.png | Casa de Gobierno | Palacio con techos de pizarra oscura. Respetá la fachada de la foto. |
| legislatura.png | Legislatura | Edificio público del siglo XIX. Respetá la fachada de la foto. |
| pasaje_dardo_rocha.png | Pasaje Dardo Rocha | Edificio largo del siglo XIX que fue estación de tren. Respetá la fachada de la foto. |
| museo_la_plata.png | Museo de La Plata | Edificio neoclásico con columnas y escalinata, rodeado de árboles del bosque. |
| observatorio.png | Observatorio | Edificios bajos con cúpulas blancas de telescopio, entre árboles. |
| teatro_argentino_antiguo.png | Teatro Argentino original | Teatro del siglo XIX. Adjuntá la postal antigua y respetá su fachada. |
| teatro_argentino.png | Teatro Argentino actual | Edificio moderno de hormigón, grande y macizo (estilo brutalista). |
| casa_curutchet.png | Casa Curutchet | Casa moderna blanca de Le Corbusier con parasoles en la fachada y un árbol en el medio. |
| republica_ninos.png | República de los Niños | Castillos y palacios de cuento en miniatura, con torres de colores, rodeados de pasto. |
| estadio_unico.png | Estadio Único | Estadio moderno con techo blanco de lona tensada. Respetá la forma de la foto. |
| estacion_trenes.png | Estación de trenes | Estación de tren clásica. Respetá la fachada de la foto. |
| plaza_moreno.png | Plaza Moreno | Plaza grande con caminos cruzados, árboles redondeados y un monumento en el centro, vista desde arriba. |

## Escenas genéricas (estas no necesitan foto)
Sirven para historias. Pedilas solo con el pedido base y la línea, sin adjuntar nada:
- `ladrillos_horno.png`: un horno de ladrillos del siglo XIX con pilas de ladrillos y una carreta tirada por bueyes.
- `fundacion_1882.png`: campo abierto con una carpa, gente vestida de época y una piedra en el centro, año 1882.
- `tranvia_1892.png`: un tranvía eléctrico antiguo en una avenida ancha con árboles, fines del siglo XIX.
- `panuelo_plano.png`: un pañuelo de tela con el plano cuadrado de una ciudad con diagonales impreso, sobre una mesa.
