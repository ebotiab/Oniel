# Diseño de Oniel

## Brief resumido

Oniel es una web en español para descubrir cómo está conectada la red ferroviaria española. Su función principal es explorar la red en un mapa interactivo; la simulación de cierres es una herramienta secundaria. La primera versión cubre la línea de alta velocidad Madrid–Sevilla (Adif, línea 010), que en 2026 ha sufrido dos accidentes graves (Adamuz, enero; Urda, octubre). El tono debe ser sobrio, preciso y respetuoso.

## Referencias

- Cartografía oficial (hojas del IGN, mapa de la red de Adif): papel mate, tinta negra, el ferrocarril como línea negra con trazos.
- Esquemas de línea de las estaciones y de los cuadros de mando (TCO): una línea recta con puntos kilométricos, estaciones y bifurcaciones.
- Señalización ferroviaria: verde (vía libre), ámbar (anuncio de precaución), rojo (parada). En Oniel el color solo aparece cuando significa algo.

## Direcciones exploradas

Se construyeron dos maquetas reales con el trazado y se revisaron en escritorio y móvil (capturas en `docs/capturas/exploracion/`).

**A. Cuaderno cartográfico (elegida).** Fondo papel claro, vía en tinta negra con trazos blancos, panel lateral con el esquema vertical de la línea (PK, estaciones, PAET, bifurcaciones). El color de señalización se reserva para estados: azul selección, verde publicado, ámbar estimado, rojo cierre.

**B. Cuadro de mando.** Fondo pizarra azul verdosa, vía en tiza luminosa, esquema horizontal al pie como un TCO. Más espectacular, pero más cercano al "panel oscuro" genérico, menos legible en móvil y demasiado dramático para el contexto de la línea.

Se eligió A por legibilidad, sobriedad y porque el esquema vertical junto al mapa funciona como índice de la línea en escritorio y como hoja inferior en móvil.

## Sistema de tokens

Color
- `--papel` `#EDEFE9` fondo del mapa y de la interfaz
- `--papel-2` `#E3E6DF` zonas hundidas (pie de panel, chips)
- `--tinta` `#17201E` texto principal y vía disponible
- `--tinta-2` `#4B5551` texto secundario
- `--tinta-3` `#8B9490` texto terciario, conexiones no cargadas
- `--regla` `#C9CEC6` bordes y reglas
- `--senal-verde` `#1F7A4D` paso publicado
- `--senal-ambar` `#C67F12` paso estimado
- `--senal-roja` `#B4232A` sin circulación: interrupción vigente del servicio, cierre simulado / afectado
- `--senal-azul` `#1E4F9A` selección

Mapa base (sobre teselas vectoriales de OpenFreeMap): agua `#D3DCDF`, tierra `#EDEFE9`, zonas urbanas `#E4E7E0`, carreteras `#DCE0D8`, otros ferrocarriles `#C3C8C0`, límites `#C0C6BF`, rótulos `#6B7470`.

Tipografía
- Una sola familia: **Archivo** variable (ejes de anchura 62–125 y peso 100–900), autoalojada.
- Marca "Oniel": Archivo ancho (wdth 118), peso 700.
- Interfaz: Archivo normal. Datos y PK: Archivo estrecho (wdth 88–90) con cifras tabulares.
- Escala: 11 / 12,5 / 14 / 17 / 22 / 28 px. Interlineado 1,35 en texto corrido.

Composición
- Escritorio: mapa a sangre; panel izquierdo de 420 px con cabecera de línea, esquema vertical y pie de selección; leyenda abajo a la derecha; buscador en la cabecera, junto a la marca; recuento de la red arriba a la derecha.
- Cabecera de la línea: título, una ficha de una sola línea (longitud y velocidad máxima) y una frase de entrada en cuerpo normal. El resto de la descripción y los datos técnicos quedan plegados bajo «Más detalle» (véase «Patrón de ficha») y se leen en párrafos cortos, en tinta, con interlineado 1,5. Bajo el esquema, una sola nota en gris terciario con la fecha de las barras y la pista de uso; la columna de barras lleva su propio rótulo («trenes el 13 nov»). La ficha no se repite en la descripción.
- Móvil: mapa arriba, hoja inferior arrastrable con el esquema compacto y la selección.
- Varias líneas: el mapa las dibuja todas y el panel muestra una a la vez. Cómo se elige está en «Elegir línea». Un nodo común a dos líneas (Madrid-Puerta de Atocha, Córdoba, Manzanares, Ciudad Real) es un solo punto en el mapa y aparece en el esquema de cada línea con su kilómetro.

Elegir línea (decidido el 11 de noviembre de 2026, con dos variantes delante; capturas en `docs/capturas/selector-lineas/`)
- Ningún elemento de la interfaz crece con el número de líneas: no hay pestañas ni enumeraciones. La navegación tiene tres niveles, cada uno con su ruta: la red (`#/`), una línea (`#/linea/<id>`) y un tramo o una estación.
- Sin línea elegida, el panel muestra la vista de la red: un título, el recuento («3 líneas · 976 km», y las estaciones), una frase que dice por dónde empezar y la lista de líneas. Oniel ya no arranca en la primera línea.
- La lista agrupa las líneas por tipo (alta velocidad, línea convencional), con la muestra del trazo de la leyenda y cuántas hay. Cada línea son dos renglones: los extremos en negrita y, debajo, en gris, cuánto mide y a qué velocidad se circula; si hoy tiene un tramo sin circulación, lo dice la señal roja. Al pasar por encima, el fondo hundido y el filete azul de los resultados del buscador. La lista se desplaza dentro del panel y, a partir de ocho líneas, lleva un campo «Filtrar por nombre» (sin acentos ni mayúsculas, como el buscador).
- Se llega a una línea por tres caminos: tocar su vía en el mapa, buscarla en el buscador o elegirla en la lista. Al elegirla, el mapa la encuadra; al volver a la red, encuadra la red.
- En la cabecera de la línea, sobre el título, «← Toda la red» vuelve a la vista de la red, igual que «← Toda la línea» vuelve de un tramo o de una estación. Se descartó un botón «Cambiar de línea» que abría la lista sin salir de la línea: eran dos listas casi iguales y un control más compitiendo con el título en el móvil.
- La pastilla de la cabecera ya no enumera las líneas: es el recuento de la red y lleva a la vista de la red desde cualquier ficha. Conserva el punto verde y el estado del servidor («despertando el servidor…», «vista estática»); en el móvil, si falta sitio, se recorta el estado y no el recuento. «Cobertura y fuentes» se abre desde el pie de la vista de la red.
- La ficha de un nodo común a varias líneas las lista, y cada una es un enlace que salta a esa línea.
- Agrupar por zona, cuando haga falta, necesita un campo nuevo en la especificación de cada línea: se decide entonces.

Trazo de la vía (decidido el 11 de noviembre de 2026, con las variantes delante: `docs/capturas/escritorio-16-trazos.jpg` y `movil-07-trazos.jpg`)
- La vía sigue siendo tinta y no usa color: lo que dice de qué vía se trata es el dibujo del trazo y, además, el grosor, como en los mapas topográficos. Se descartó distinguirla solo por el grosor (había que comparar dos líneas para notarlo) y solo por el dibujo (el filete se perdía en la vista general).
- Alta velocidad: trazo grueso (4,2 px a zoom 5) con un filete claro continuo por el centro. Línea convencional de vía doble: trazo medio (2,55 px) con los trazos blancos clásicos. Vía única, sea cual sea la línea: trazo fino (1,5 px) con los trazos blancos más espaciados. Todos crecen con el zoom.
- El tipo de línea y el número de vías son dos propiedades distintas de cada tramo (`tipo` y `vias` en `frontend/src/map/layers.ts`); el trazo sale de las dos.
- El esquema vertical usa la misma convención (5 px con filete, 3 px con trazos, 2 px con trazos espaciados) y la leyenda enseña los tres trazos con su dibujo. En la ficha del tramo, la primera línea lo dice en palabras: «Alta velocidad», «Línea convencional, vía única».
- Cada trazo de la leyenda es un botón: al pasar por encima o al llegar con el teclado se resalta ese trazo en el mapa y los demás se atenúan; un clic lo deja fijado y otro lo suelta. Es movimiento en respuesta a una acción, sin animación.
- En el móvil no cabe la leyenda sobre el mapa, así que los trazos de la vía van en un renglón dentro del panel (decidido el 11 de noviembre de 2026), sobre el esquema de la línea. La vista de la red no lo lleva: la lista de líneas ya enseña la muestra de alta velocidad y de línea convencional, y repetirlas justo encima sobraba. Un toque resalta ese trazo en el mapa y otro lo suelta; al abrir un tramo o una estación se suelta solo. Los estados (sin circulación, selección, cierre) no van en ese renglón: los dicen el color y los textos del panel.
- Los estados van encima del dibujo y no lo cambian: el rojo de «sin circulación» y el azul de la selección tiñen la tinta y conservan el filete o los trazos; el halo y el engrosado siguen marcando la selección y el cierre simulado.
- Los nodos secundarios (apeaderos y estaciones menores) se dibujan más pequeños, con rótulo en gris y solo a partir del zoom 7,5; en el esquema compacto del móvil se ven como marcas sin rótulo.

Interrupciones del servicio (decidido el 10 de noviembre de 2026)
- El rojo ya significaba «cierre»: un tramo con una interrupción vigente hoy se dibuja con la vía en rojo, en el mapa y en el esquema, con su grosor y su dibujo de siempre. No hay iconos, animaciones ni avisos emergentes.
- Se distingue del cierre simulado por el énfasis: el cierre simulado lleva el trazo grueso y un halo rojo; la interrupción real, solo el color. Un tramo interrumpido sigue en rojo al seleccionarlo: la selección la dicen el grosor y el halo azul (en el esquema, un borde azul alrededor del rojo).
- La leyenda añade «Sin circulación hoy» con una muestra roja fina, solo cuando hay alguna interrupción vigente. En el móvil la leyenda del panel solo lleva los trazos: la interrupción la explica la línea de texto que va sobre el esquema.
- En el panel, la interrupción es un bloque como el del contexto de un nodo, con el filete en rojo: la etiqueta «sin circulación» y los extremos, el motivo, desde cuándo y hasta cuándo se prevé, una nota opcional, las fuentes con enlace y la fecha de la última comprobación. Aparece en el tramo, en los nodos del corte y en el panel de cobertura.
- Donde hay una lista de trenes o un formulario sobre un tramo interrumpido, basta una línea de texto con un filete rojo: «Horario publicado; sin circulación real desde el … (fuente).» Sobre el esquema de la línea, otra línea por interrupción dice qué está cortado, desde cuándo y según quién, y lleva al primer tramo.
- Alineación a la izquierda en todo el texto. Sin mayúsculas sostenidas, sin etiquetas numeradas.

Patrón de ficha (aplicado el 11 de noviembre de 2026 a tramo, nodo y línea)
- Toda ficha tiene tres partes, en este orden. Primero, un resumen en lenguaje llano: qué es, entre qué va, cuánto mide, a qué velocidad se circula, cuántos trenes pasan. Después, un plegable con el rótulo «Más detalle», cerrado de entrada, con lo que para un visitante es ruido: puntos kilométricos, códigos de Adif, número de línea, ancho, electrificación, velocidad habitual. Al pie del detalle, la fuente y la fecha en que se consultó, con su identificador en `sources.json`.
- Ninguna pantalla exige saber de ferrocarril para entenderse. Lo que queda a la vista se lee sin conocimientos previos; cuando un término técnico aparece en el detalle, una frase lo explica allí mismo («El punto kilométrico es la distancia medida a lo largo de la vía desde el origen de la línea»).
- El detalle no se quita ni se resume: se mueve. Todo lo que se mostraba sigue a un toque.
- El plegable es uno solo por ficha y es el mismo componente en todas (`Plegable` en `frontend/src/panel/Plegable.tsx`): un `<details>` nativo, que se abre con el teclado, con el rótulo en el azul de los enlaces y el contenido sangrado tras un filete gris. Recuerda durante la sesión si el visitante lo dejó abierto, y lo recuerda para todas las fichas a la vez: quien abre el detalle de un tramo lo encuentra abierto en el siguiente. La fuente la pinta `PieFuente`, del mismo fichero.
- Una ficha nueva (glosario, señalización, anotaciones) sigue el patrón sin discutirlo de nuevo: decide qué va en el resumen y mete lo demás en el mismo plegable; no añade un segundo plegable ni otro rótulo.
- Los bloques de contexto y de interrupción no son detalle técnico: van fuera del plegable, a la vista, con sus propias fuentes.

Rutas
- Toda vista tiene su ruta en el hash de la URL, para poder compartir un enlace exacto: `#/` (la vista de la red, sin línea elegida), `#/linea/<id>` (la línea a la vista en el panel), `#/tramo/<id>`, `#/nodo/<id>`, `#/tramo/<id>/cierre` (la simulación) y `#/cobertura`. Se leen y se escriben en `parseHash` y `toHash` (`frontend/src/app/state.ts`).
- Una vista nueva lleva la suya desde el primer día y se añade a esas dos funciones. No tienen ruta los estados que no son una vista: si el detalle está plegado, el punto por el que se pasa el ratón, la hoja del móvil ampliada o no. El resultado de una simulación todavía no la tiene (la ventana horaria no va en la URL); le corresponde al escenario serializable de la hoja de ruta.

Buscador (decidido el 11 de noviembre de 2026)
- Un solo buscador, en la cabecera, para llegar a cualquier estación, a cualquier otro punto de la red o a una línea. En escritorio es un campo junto a la marca, sobre el panel, y su lista de resultados ocupa el ancho del panel. En el móvil es una lupa al final de la cabecera, tras el recuento de la red, que despliega el campo a todo el ancho; «Cerrar» lo recoge. Se descartó ponerlo dentro del panel: en el móvil obligaba a abrir la hoja inferior y el teclado tapaba los resultados. Capturas en `docs/capturas/buscador/`.
- Se escribe el nombre como salga: sin acentos ni mayúsculas («alcazar», «anover»). El código de Adif se admite, pero no se pide ni se enseña salvo que se haya buscado por él.
- Cada resultado son dos líneas: el nombre en negrita y, debajo, en gris, qué es y en qué líneas está («Estación · Madrid – Sevilla y Manzanares – Ciudad Real», «Puesto de adelantamiento (PAET) · Madrid – Sevilla», «Línea convencional · 64,4 km»). El resultado activo lleva el fondo hundido y un filete azul, el color de la selección.
- Con el campo vacío ofrece las líneas, bajo el rótulo «Líneas»: se llega a cualquiera sin escribir.
- Teclado: «/» o Ctrl/⌘ + K enfocan el campo (la tecla «/» se muestra dentro del campo en escritorio), las flechas recorren los resultados, Intro abre el primero o el elegido y Escape cierra. Es un «combobox» de WAI-ARIA con su lista de opciones.
- Elegir una estación la selecciona como al tocarla en el mapa; elegir una línea la pone en el panel. Las dos cosas quedan en la URL (`#/nodo/<id>`, `#/linea/<id>`), como dice «Rutas».
- El mismo componente (`SearchBox` con `scope="nodos"`) es el selector de estación para otros paneles, como el comparador de recorridos.

Movimiento
- Solo en respuesta a una acción: enfocar el mapa al seleccionar, abrir el panel de simulación, resaltar en el esquema lo que se resalta en el mapa. Se respeta `prefers-reduced-motion`.

Encuadre
- El mapa no sale de la península y sus vecinos: longitud −12,5 a 6 y latitud 34 a 46 (`IBERIA_BOUNDS` en `frontend/src/map/bounds.ts`), es decir, España, Portugal, Baleares, el sur de Francia y el norte del Magreb. Canarias queda fuera: no tiene ferrocarril y meterla haría la caja tan grande que la restricción casi desaparecería.
- MapLibre obliga a que todo el lienzo quepa dentro de la caja, así que el zoom mínimo efectivo depende de la pantalla: unos 5,8 en escritorio (1440 px) y 5,4 en un móvil, frente al 4,5 nominal. El límite oeste va bastante más allá de Portugal porque el panel de escritorio tapa unos cinco grados por la izquierda; con menos margen, Sevilla quedaría bajo el panel al alejar el mapa. El encuadre inicial de las líneas (`SPAIN_BOUNDS`) no cambia.
- Medido el 9 de noviembre de 2026: cada pantalla fuera de España descarga de 1 a 4 MB de teselas de OpenFreeMap (de 80 a 325 KB por tesela a zoom 4–6). Ese coste es del visitante y de OpenFreeMap, no de Oniel; la caja se puso por foco de producto.
- Siempre con el norte arriba y sin inclinación, como una hoja de mapa: ni el arrastre con el botón derecho, ni los dos dedos, ni el teclado giran el mapa. La brújula ya estaba oculta.

Principios
- La vía es tinta; el color es señal. Nada se colorea por decoración.
- El esquema de línea y el mapa son la misma cosa vista de dos formas: siempre sincronizados.
- Todo lo que se muestra dice de dónde viene (fuente, licencia, fecha).
- Los textos hablan al visitante que sabe poco de ferrocarril: "tramo", "estación", "cierre", no jerga.
- Lo esencial primero y el detalle plegado: cada ficha sigue el «Patrón de ficha».
