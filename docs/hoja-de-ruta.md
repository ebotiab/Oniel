# Hoja de ruta de Oniel

Las tareas pendientes, ordenadas, y los principios con los que se construyen. Última revisión: 12 de noviembre de 2026.

Oniel es para quien no sabe de ferrocarril y quiere consultar la red española de forma clara, intuitiva y atractiva, y debe poder crecer durante años sin complicarse. Las tareas de esta lista están pensadas con eso delante: cada una deja un mecanismo que la siguiente reutiliza.

## Cómo se usa

- Cada tarea es una incidencia de GitHub en [ebotiab/Oniel](https://github.com/ebotiab/Oniel/issues) con el brief completo: **por qué** se hace, **qué datos** usa, **qué toca** en el código, **cuándo está hecha** y **de qué depende**. Las condiciones de «hecha» son el criterio de aceptación de la PR. Este documento es el índice ordenado, los principios de arquitectura y lo hecho; no repite los briefs.
- Cada tarea se hace en una sesión aislada, en su rama y en una PR pequeña contra `main`, siguiendo `CLAUDE.md`. El usuario decide qué tarea abre cada sesión; lo normal es la primera de la lista que nadie tenga empezada y cuyas dependencias estén cerradas. Para empezar: `gh issue view <número> --repo ebotiab/Oniel`.
- La PR que termina una tarea cierra su incidencia (`Closes #N` en la descripción, en inglés: GitHub no reconoce «Cierra #N»), retira su línea de la lista de abajo y añade una a «Hecho hasta ahora»; lo aprendido va a `docs/datos.md`, `docs/simulacion.md`, `docs/diseno.md` o `docs/despliegue.md`.
- Si al hacer una tarea aparece otra, no se hace de paso: se abre una incidencia nueva con el mismo formato (Por qué / Qué datos usa / Qué toca / Hecha cuando / Depende de), con sus etiquetas (`arquitectura`, `datos`, `visor`, `analisis`, `infraestructura`), y se añade a la lista en el sitio que le corresponda. Lo que cabe en una PR pequeña y no merece incidencia propia va a la lista de pendientes menores (#31).
- Las decisiones de diseño siguen `docs/diseno.md`. Si una tarea necesita una representación nueva (un trazo, un color, un panel), se propone al usuario y, decidida, se anota allí antes de implementarla.
- Toda fuente nueva se registra en `backend/data/curated/sources.json` y su fichero crudo va a `backend/data/raw/` con la fecha en el nombre. Sin fuente, el dato no entra.
- Todo lo que roce los accidentes de Adamuz (18 de enero de 2026) y Urda (28 de octubre de 2026) va en tono sobrio y neutro: hechos, fechas y fuente.

## Hecho hasta ahora

Entre el 8 y el 10 de noviembre de 2026 se fusionaron catorce PR, una por tarea:

- PR 1: segunda línea, la convencional Madrid – Alcázar de San Juan – Córdoba, con el trazado por el camino más corto en el grafo de vías de OSM, los tramos de vía única y los MD, Regional Exprés y Proximidad del GTFS.
- PR 2: trenes que cambian de línea, con reglas de recorrido (`route_overrides`) para los 24 Intercity y Alvia Madrid-Atocha Cercanías – Andalucía que, tras Urda, van por la convencional hasta Manzanares y por la alta velocidad desde Ciudad Real.
- PR 3: esquema de línea sin rótulos solapados.
- PR 4: carga del visor desde la instantánea estática, con sondeo de la API en segundo plano y despertar de Render sin reimportar.
- PR 5, 6 y 7: documentación del despliegue vigente en Vercel (la clase de PR que #30 hace innecesaria).
- PR 8: panel de línea con cabecera más ligera, descripción por párrafos y una sola nota.
- PR 9: mapa acotado a la península y sus vecinos, siempre con el norte arriba.
- PR 10: CI en GitHub Actions, `CLAUDE.md` y la primera versión de esta hoja de ruta.
- PR 12: capa de interrupciones vigentes del servicio: `interrupciones.json` curado a mano, tabla `interruptions`, `GET /api/interruptions`, tramos en rojo en el mapa y en el esquema, y una nota en las listas de trenes y en la simulación. Las dos interrupciones iniciales (alta velocidad entre La Sagra y Córdoba; obras entre Almuradiel y Alcolea de Córdoba) se comprobaron el 10 de noviembre de 2026; `docs/datos.md` dice cómo y cada cuánto se revisan.
- PR 13: tercera línea, la convencional Manzanares – Ciudad Real (Adif 522, de vía única), trazada desde OpenStreetMap, con sus MD y Regional Exprés. Los 24 Intercity y Alvia desviados tras Urda recorren ahora las tres líneas tramo a tramo, y el reparto de tiempos usa los kilómetros por cada una en vez de la línea recta entre Manzanares y Ciudad Real; `docs/datos.md` y `docs/simulacion.md` lo explican.
- PR 14: `docs/despliegue.md` anota que producción sirve el commit `883d080`, con las tres líneas y las interrupciones.
- PR 34 (11 de noviembre de 2026): Vercel conectado a GitHub. Una fusión en `main` publica el visor en https://oniel.vercel.app y cada PR tiene su vista previa; dejan de hacer falta las PR que anotaban el commit vigente.
- PR 36 (11 de noviembre de 2026): patrón de ficha del visor. Tramo, nodo y línea dicen primero lo esencial en lenguaje llano y guardan lo técnico bajo «Más detalle», con la fuente y la fecha al pie; la línea a la vista y la cobertura tienen ruta en la URL. `docs/diseno.md` recoge el patrón («Patrón de ficha» y «Rutas»).
- PR 46 (11 de noviembre de 2026): grafo de rutas y escenarios (#23). `oniel.routing` une todas las líneas en un grafo y calcula los recorridos entre dos nodos (kilómetros, tiempo estimado, vía única, líneas) sobre un escenario serializable: cerrar tramos, añadir un enlace esbozado, cambiar una velocidad. La alternativa de la simulación de cierre sale de ahí, igual que antes para una línea y ahora también por varias encadenadas (Madrid – Ciudad Real por Manzanares). `GET /api/routes`, el mismo cálculo en `frontend/src/routing/` y la ruta `#/escenario/…`; `docs/simulacion.md`, «Grafo y escenarios».
- PR del comparador de recorridos (12 de noviembre de 2026, #24): vista «Comparar recorridos» (`#/recorridos/<desde>/<hasta>`), que se abre desde la vista de la red o desde la ficha de una estación. Enseña hasta tres caminos entre dos estaciones, del más corto al más largo, con kilómetros, tiempo estimado, vía única, estaciones y trenes directos; señala los cortados por una interrupción o por un cierre hipotético y cuál queda como alternativa, y funciona sin API. Los recorridos ya no se limitan por número de líneas: se descartan los que miden más del doble que el más corto. `docs/simulacion.md`, «Comparar recorridos», y `docs/diseno.md`.
- PR de los trenes por operador (12 de noviembre de 2026, #22): los pasos por tramo se reparten por operador en `GET /api/segment-counts` y en la instantánea, y Ouigo entra como segundo operador de la alta velocidad con su GTFS del Punto de Acceso Nacional (12 trenes al día por el tronco Madrid – Córdoba y 6 hasta Sevilla el día de referencia). Iryo no publica sus horarios en un formato abierto: queda registrado como operador de la línea sin horarios y el visor dice en cada tramo que sus trenes faltan. El panel del tramo abre con el reparto y agrupa los trenes por operador; la barra del esquema es el total (`docs/diseno.md`, «Trenes por operador»). El día de referencia sale de los días que cubren todos los ficheros a la vez; `docs/datos.md`, «Operadores y sus horarios».
- PR de los destinos directos (12 de noviembre de 2026, #26): la ficha de cada estación dice a dónde se llega sin cambiar de tren el día de referencia, con cuántos trenes, de qué tipo, de qué operador y entre qué horas, también sin API (`destinations` en `GET /api/nodes/{id}/services` y en `nodes/<id>.json`). Se respetan las paradas en las que un tren solo deja o solo recoge viajeros, y el comparador de recorridos cuenta igual: de Ciudad Real a Madrid pasan 23 trenes y sirven 12. `docs/datos.md`, «Destinos directos», y `docs/diseno.md`.
- PR del refresco automático del GTFS (12 de noviembre de 2026, #29): el flujo `.github/workflows/gtfs.yml` descarga cada lunes el fichero de Renfe, lo compara con el cargado y, si cambian los trenes de las líneas cargadas en las próximas cuatro semanas o el cargado tiene 28 días o más, lo declara como un conjunto de datos más, pasa las comprobaciones y abre una PR para que la revise una persona; sin cambios, o con una PR de refresco aún abierta, no abre nada. El fichero de Ouigo sigue siendo manual (su fuente exige una cuenta) y el flujo avisa tres semanas antes de que caduque. `oniel-data refresh`; `docs/datos.md`, «Refresco de los horarios», y `docs/despliegue.md`.
- PR de las anotaciones de red (12 de noviembre de 2026, #17): un modelo común para todo lo que pasa sobre la red entre dos fechas según una fuente. `AnnotationSpec` lleva tipo, estado, alcance (de nodo a nodo en una línea, un nodo o geometría propia), fechas, título o motivo, fuentes y fecha de comprobación; los tipos se declaran en `ANNOTATION_KINDS` con sus estados válidos. Las dos interrupciones pasan sin pérdida a `anotaciones.json` como el primer tipo, la tabla `annotations` sustituye a `interruptions` (migración `0007`) y `GET /api/annotations?kind=&on=` las sirve; `interruptions` queda como alias en la API y en la instantánea. En el visor, un registro de capas (`annotationLayers.ts`) del que leen el mapa, el esquema, la leyenda, la ficha y las listas, sin cambio visible. `docs/datos.md`, «Anotaciones de red», dice cómo se añade un tipo.
- PR del glosario (12 de noviembre de 2026, #16): cada término técnico de las fichas lleva un subrayado de puntos y, a un toque, una nota con su definición; el glosario completo (`#/glosario` y `#/glosario/<entrada>`) abre con cinco conceptos de circulación (bloqueo y cantón, vía única, marcha a la vista, puesto de mando, ASFA, LZB y ERTMS), con el Reglamento de Circulación Ferroviaria como referencia registrada en `sources.json`, y sigue con los términos por orden alfabético. Se entra por el botón de la cabecera en escritorio, por el buscador, que también encuentra términos, y por la vista de la red. Los textos están en `frontend/src/panel/glosario.ts`; `docs/diseno.md`, «Glosario».
- PR de la capa de proyectos (12 de noviembre de 2026, #18): lo previsto, en obras o parado alrededor de las líneas cargadas, como anotaciones de tipo `proyecto` con sus estados, hitos fechados con la fuente de cada uno (`milestones`) y fecha de comprobación. Cinco para empezar: el tramo Mora – Alcázar de San Juan de la alta velocidad Madrid – Jaén, el baipás entre la alta velocidad y la línea de Córdoba a Jaén, la Variante de Loja, la duplicación de vía Antequera – Granada y los 13 túneles de la autopista ferroviaria, con 24 fuentes nuevas (19 anuncios del BOE). En el mapa, línea de puntos o de trazos en tinta sobre un esbozo; cada proyecto tiene su ficha (`#/proyecto/<id>`) y todos se listan en «Cobertura y fuentes». `docs/datos.md`, «Proyectos», y `docs/diseno.md`.
- PR de los atributos de tramo (12 de noviembre de 2026, #19): un mecanismo para todo lo que cambia a lo largo de una línea. Cada atributo se declara por secciones de nodo a nodo en la especificación (`attribute_sections`, con valor, fuente y fecha de comprobación), un solo reparto lo lleva a los tramos y comprueba que los obligatorios cubren la línea entera, la tabla `segment_attributes` lo guarda y cada tramo lo sirve en `attributes`. El número de vías lo estrena, sin cambio visible: `track_sections` se convirtió y se retiró, y la ficha del tramo lo pinta desde una lista declarativa (`SEGMENT_ATTRIBUTES`). Añadir un atributo es declarar sus secciones y una entrada en esa lista. `docs/datos.md`, «Atributos de tramo».
- PR de los tramos sin alternativa (12 de noviembre de 2026, #25): para cada tramo, cuántos trenes lo recorren el día de referencia y si, con el tramo cortado, tendrían otro camino en las líneas cargadas, con los kilómetros y minutos que añade. `oniel.analysis.criticality` agrupa los trenes por su recorrido en las líneas cargadas y pregunta al grafo de rutas; `GET /api/alternatives` y `alternatives.json`, que el visor no pide al arrancar. La ficha del tramo lo dice en una frase y lo desglosa en «Más detalle»; «Cobertura y fuentes» lista los tramos sin alternativa (hoy, los tres al sur de Córdoba) y pliega los demás. Siempre con el aviso de que se refiere a las líneas cargadas y de que faltan los trenes de Iryo. `docs/simulacion.md`, «Tramos sin alternativa», y `docs/diseno.md`.
- PR del glosario como página (12 de noviembre de 2026, #90): el glosario deja el panel y pasa a ser una página entera, sin mapa, con un índice, un dibujo por pasos para cada concepto (viñetas en SVG con el trazo del mapa y el color solo en las señales), los textos más cortos, las palabras aparte con un campo para filtrarlas y las referencias en un renglón discreto. Las rutas `#/glosario` y `#/glosario/<entrada>` y la nota de cada término en las fichas no cambian. `docs/diseno.md`, «Glosario como página».

## Principios de arquitectura

Oniel tiene que entenderse sin saber de ferrocarril y crecer durante años. Estos principios evitan que cada dato o capa nueva traiga su propio caso particular; la incidencia que materializa cada uno va entre paréntesis.

1. **Se entiende sin saber de ferrocarril.** Cada ficha dice primero lo esencial en lenguaje llano y guarda plegado el detalle (puntos kilométricos exactos, códigos, fuente y fecha), para que no estorbe. A quien trabaja en el sector puede serle útil, pero nada se diseña para él ni se añade complejidad por él (#15).
2. **Todo dato con fuente y fecha, como estructura.** Un dato no es un texto con una nota al pie sino un valor con `source_id`, `checked_on` y, cuando la tiene, su vigencia. Así el visor puede citar la fuente junto a cada cifra y una revisión programada puede saber qué dato envejece.
3. **Anotaciones de red: un modelo común.** Todo lo que pasa sobre la red entre dos fechas según una fuente (interrupciones, obras, proyectos, cambios de servicio) comparte un modelo con tipo, alcance, estado, fechas y fuentes. Un tipo nuevo es una entrada en un registro, no una tabla, un endpoint y una capa nuevos. Hecho en #17: `AnnotationSpec`, `anotaciones.json`, tabla `annotations` y `GET /api/annotations` (`docs/datos.md`, «Anotaciones de red»).
4. **Atributos de tramo por secciones.** Lo que cambia a lo largo de una línea (vías, electrificación, señalización, velocidad, ancho) se declara de nodo a nodo con un único mecanismo que lo reparte a los tramos, valida su cobertura y lo muestra. Hecho en #19: `attribute_sections` en la especificación de cada línea, tabla `segment_attributes`, `attributes` en cada tramo de la API y de la instantánea, y la lista `SEGMENT_ATTRIBUTES` del visor (`docs/datos.md`, «Atributos de tramo»).
5. **Grafo y escenarios.** Un grafo único de todas las líneas cargadas y un escenario serializable (una lista de modificaciones: cerrar tramos, añadir un enlace, cambiar una velocidad). De ahí salen la simulación de cierre, el comparador de recorridos y los «¿y si?» que vengan, con un solo cálculo (#23).
6. **Conjuntos de datos fechados.** Cada horario importado es un conjunto con fuente, fecha de descarga y validez; refrescar añade, no sustituye. Así se puede decir cómo ha cambiado el servicio en una estación o un tramo. Hecho en #21: tabla `datasets`, lista `feeds` de `sources.json` y conjunto activo por fuente y día (`docs/datos.md`, «Conjuntos de datos»). Desde #29 el de Renfe lo añade cada semana un flujo que abre una PR.
7. **Registro de capas en el visor.** Cada capa declara sus datos, su estilo, su entrada de leyenda, su ficha y su ruta. Añadir una capa no toca las demás. Empezado en #17 con las anotaciones: `frontend/src/app/annotationLayers.ts` tiene una entrada por tipo, y el mapa, el esquema, la leyenda, la ficha y las listas leen de ella. Las capas de anotaciones no tienen todavía ruta propia en la URL.
8. **Toda vista tiene ruta en la URL.** Una línea, un nodo, un tramo, un escenario, una comparación o un término del glosario se pueden compartir con un enlace exacto (#15).
9. **La red se carga por partes.** El visor arranca con un índice ligero de toda la red (líneas, nodos sin textos, geometría simplificada) y pide el detalle de cada línea cuando se abre o cuando el mapa se acerca a ella; añadir una línea apenas cambia lo que pesa el arranque. El grafo entero va en el índice, así que buscar, enlazar y calcular recorridos no dependen de qué líneas se hayan cargado. Hecho en #43: `index.json` y `lines/<id>.json` (que sustituyen a `network.json` y `segment-counts.json`, ya retirados), `GET /api/lines` y `GET /api/lines/{id}`, con las medidas en `docs/datos.md`, «Instantánea estática».

## Orden

6. [#20](https://github.com/ebotiab/Oniel/issues/20) Datos: señalización y protección del tren por tramo. ASFA, LZB, ERTMS, bloqueo y mando desde la Declaración sobre la Red. Los atributos de tramo (#19) y el patrón de ficha (#15) ya están.
11. [#27](https://github.com/ebotiab/Oniel/issues/27) Análisis: evolución del servicio en el tiempo por estación y tramo. Los destinos directos por estación (#26) y los conjuntos de datos fechados (#21) ya están.

El orden es orientativo. No quedan tareas de arquitectura pendientes: las que siguen se apoyan en mecanismos que ya están.

## Pendientes menores

Lo que apareció al hacer otras tareas y cabe en una PR pequeña está en [#31](https://github.com/ebotiab/Oniel/issues/31), como lista con casillas: hoy no queda ninguno sin marcar.

## `main` protegida: solo entra por PR y con el CI en verde

Activado el 12 de noviembre de 2026 con la protección clásica de rama, por `gh api`. El repositorio es público, así que está disponible en el plan gratuito. Lo que exige:

- **Comprobaciones obligatorias** `Backend` y `Frontend`, los `name:` de los trabajos de `.github/workflows/ci.yml` (con `app_id` 15368, el de GitHub Actions). Si se renombra un trabajo hay que cambiarlo también en la regla, o ninguna PR podrá fusionarse.
- **Pull request obligatoria**, sin aprobaciones (`required_approving_review_count: 0`): no se puede hacer push directo a `main`.
- **Se aplica también a los administradores** (`enforce_admins: true`). Es lo que hace que la regla valga para las sesiones, que actúan con el usuario del propietario: sin esto, `gh pr merge` fusionaría igual con el CI en rojo.
- **Sin exigir la rama al día** (`strict: false`): una PR con el CI en verde se fusiona aunque `main` haya avanzado desde que se abrió. Con varias sesiones en paralelo, `true` añadiría una vuelta de CI por PR.
- Sin force push ni borrado de `main`.

Para ver la regla:

```bash
gh api repos/ebotiab/Oniel/branches/main/protection
```

Para cambiarla, repetir el `PUT` con la configuración completa, porque la API sustituye toda la regla:

```bash
gh api -X PUT repos/ebotiab/Oniel/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": { "strict": false, "checks": [{ "context": "Backend", "app_id": 15368 }, { "context": "Frontend", "app_id": 15368 }] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

Para retirarla del todo: `gh api -X DELETE repos/ebotiab/Oniel/branches/main/protection`. Desde la web está en Settings → Branches → regla `main`. Si hace falta fusionar algo con el CI en rojo (un arreglo del propio CI, por ejemplo), lo más limpio es arreglar el CI en la misma PR; retirar la protección y volverla a poner es el último recurso.
