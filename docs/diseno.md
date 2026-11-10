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
- `--senal-roja` `#B4232A` cierre simulado / afectado
- `--senal-azul` `#1E4F9A` selección

Mapa base (sobre teselas vectoriales de OpenFreeMap): agua `#D3DCDF`, tierra `#EDEFE9`, zonas urbanas `#E4E7E0`, carreteras `#DCE0D8`, otros ferrocarriles `#C3C8C0`, límites `#C0C6BF`, rótulos `#6B7470`.

Tipografía
- Una sola familia: **Archivo** variable (ejes de anchura 62–125 y peso 100–900), autoalojada.
- Marca "Oniel": Archivo ancho (wdth 118), peso 700.
- Interfaz: Archivo normal. Datos y PK: Archivo estrecho (wdth 88–90) con cifras tabulares.
- Escala: 11 / 12,5 / 14 / 17 / 22 / 28 px. Interlineado 1,35 en texto corrido.

Composición
- Escritorio: mapa a sangre; panel izquierdo de 420 px con cabecera de línea, esquema vertical y pie de selección; leyenda abajo a la derecha; cobertura arriba a la derecha.
- Móvil: mapa arriba, hoja inferior arrastrable con el esquema compacto y la selección.
- Varias líneas: el mapa las dibuja todas; el panel muestra una a la vez, elegida con pestañas sobre el esquema, y cambia solo a la línea de lo que se selecciona en el mapa. Un nodo común a dos líneas (Madrid-Puerta de Atocha, Córdoba) es un solo punto en el mapa y aparece en el esquema de cada línea con su kilómetro.

Trazo de la vía
- Sigue siendo tinta; el grosor dice de qué vía se trata, como en las hojas del IGN: alta velocidad 3 px, línea convencional 2,4 px, vía única 1,8 px (a zoom 5; crecen con el zoom). Los trazos blancos se mantienen en todas.
- En el esquema vertical la vía doble es un trazo de 3 px y la vía única de 1,5 px; la leyenda del mapa explica los tres grosores.
- Los nodos secundarios (apeaderos y estaciones menores) se dibujan más pequeños, con rótulo en gris y solo a partir del zoom 7,5; en el esquema compacto del móvil se ven como marcas sin rótulo.
- Alineación a la izquierda en todo el texto. Sin mayúsculas sostenidas, sin etiquetas numeradas.

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
