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

## Principios de arquitectura

Oniel tiene que entenderse sin saber de ferrocarril y crecer durante años. Estos principios evitan que cada dato o capa nueva traiga su propio caso particular; la incidencia que materializa cada uno va entre paréntesis.

1. **Se entiende sin saber de ferrocarril.** Cada ficha dice primero lo esencial en lenguaje llano y guarda plegado el detalle (puntos kilométricos exactos, códigos, fuente y fecha), para que no estorbe. A quien trabaja en el sector puede serle útil, pero nada se diseña para él ni se añade complejidad por él (#15).
2. **Todo dato con fuente y fecha, como estructura.** Un dato no es un texto con una nota al pie sino un valor con `source_id`, `checked_on` y, cuando la tiene, su vigencia. Así el visor puede citar la fuente junto a cada cifra y una revisión programada puede saber qué dato envejece.
3. **Anotaciones de red: un modelo común.** Todo lo que pasa sobre la red entre dos fechas según una fuente (interrupciones, obras, proyectos, cambios de servicio) comparte un modelo con tipo, alcance, estado, fechas y fuentes. Un tipo nuevo es una entrada en un registro, no una tabla, un endpoint y una capa nuevos (#17).
4. **Atributos de tramo por secciones.** Lo que cambia a lo largo de una línea (vías, electrificación, señalización, velocidad, ancho) se declara de nodo a nodo con un único mecanismo que lo reparte a los tramos, valida su cobertura y lo muestra (#19).
5. **Grafo y escenarios.** Un grafo único de todas las líneas cargadas y un escenario serializable (una lista de modificaciones: cerrar tramos, añadir un enlace, cambiar una velocidad). De ahí salen la simulación de cierre, el comparador de recorridos y los «¿y si?» que vengan, con un solo cálculo (#23).
6. **Conjuntos de datos fechados.** Cada horario importado es un conjunto con fuente, fecha de descarga y validez; refrescar añade, no sustituye. Así se puede decir cómo ha cambiado el servicio en una estación o un tramo. Hecho en #21: tabla `datasets`, lista `feeds` de `sources.json` y conjunto activo por fuente y día (`docs/datos.md`, «Conjuntos de datos»).
7. **Registro de capas en el visor.** Cada capa declara sus datos, su estilo, su entrada de leyenda, su ficha y su ruta. Añadir una capa no toca las demás; se empieza con las anotaciones (#17).
8. **Toda vista tiene ruta en la URL.** Una línea, un nodo, un tramo, un escenario, una comparación o un término del glosario se pueden compartir con un enlace exacto (#15).
9. **La red se carga por partes.** El visor arranca con un índice ligero de toda la red (líneas, nodos sin textos, geometría simplificada) y pide el detalle de cada línea cuando se abre o cuando el mapa se acerca a ella; añadir una línea apenas cambia lo que pesa el arranque. El grafo entero va en el índice, así que buscar, enlazar y calcular recorridos no dependen de qué líneas se hayan cargado. Hecho en #43: `index.json` y `lines/<id>.json` (que sustituyen a `network.json` y `segment-counts.json`, ya retirados), `GET /api/lines` y `GET /api/lines/{id}`, con las medidas en `docs/datos.md`, «Instantánea estática».

## Orden

2. [#16](https://github.com/ebotiab/Oniel/issues/16) Visor: glosario didáctico y conceptos. Cada término a un toque y un glosario con los conceptos que hacen falta para entender la red. Depende de #15.
3. [#17](https://github.com/ebotiab/Oniel/issues/17) Datos: anotaciones de red con fecha y fuente. El modelo común; las interrupciones pasan a ser su primer tipo sin cambio visible.
4. [#18](https://github.com/ebotiab/Oniel/issues/18) Datos: capa de proyectos e infraestructura planeada. Mora – Alcázar, baipás de Montoro, Variante de Loja, Despeñaperros, como anotaciones de tipo proyecto. Depende de #17.
5. [#19](https://github.com/ebotiab/Oniel/issues/19) Datos: atributos de tramo por secciones. Un mecanismo para todos; `tracks` lo estrena.
6. [#20](https://github.com/ebotiab/Oniel/issues/20) Datos: señalización y protección del tren por tramo. ASFA, LZB, ERTMS, bloqueo y mando desde la Declaración sobre la Red. Depende de #19 y #15.
9. [#25](https://github.com/ebotiab/Oniel/issues/25) Análisis: tramos sin alternativa. Carga por tramo y si la red cargada ofrece otro camino cuando se corta. Los recuentos por operador (#22) y el grafo de rutas (#23) ya están.
10. [#26](https://github.com/ebotiab/Oniel/issues/26) Visor: cobertura por estación, destinos directos y frecuencias.
11. [#27](https://github.com/ebotiab/Oniel/issues/27) Análisis: evolución del servicio en el tiempo por estación y tramo. Depende de #26; los conjuntos de datos fechados ya están (#21).
12. [#29](https://github.com/ebotiab/Oniel/issues/29) Infraestructura: refresco automático del GTFS. Se apoya en los conjuntos de datos fechados, ya hechos (#21).

El orden es orientativo. #16 no depende de nada y puede adelantarse cuando convenga; #15 conviene el primero porque fija el patrón de las fichas que usan #16, #20 y #17. Las dos tareas de arquitectura que quedan (#17 y #19) son independientes entre sí y cada una desbloquea las que la siguen; conviene hacerlas antes que sus dependientes y no en paralelo con ellas.

## Pendientes menores

Lo que apareció al hacer otras tareas y cabe en una PR pequeña está en [#31](https://github.com/ebotiab/Oniel/issues/31), como lista con casillas: interrupciones anteriores a las registradas y la escala del mapa detrás de la leyenda.

## Proteger `main` exigiendo el CI

Es una decisión del usuario; no está activado. El repositorio es público, así que la protección de ramas está disponible en el plan gratuito. Las comprobaciones se llaman como los trabajos de `.github/workflows/ci.yml`: `Backend` y `Frontend`. Tienen que haberse ejecutado al menos una vez para aparecer en la lista de la web; la API acepta los nombres directamente.

Desde la web: Settings → Branches → Add branch protection rule → nombre `main` → «Require status checks to pass before merging» → añadir `Backend` y `Frontend` → Create. O con un conjunto de reglas: Settings → Rules → Rulesets → New branch ruleset → objetivo `main` → «Require status checks to pass» con las dos comprobaciones → Active.

Con `gh api` (protección clásica):

```bash
gh api -X PUT repos/ebotiab/Oniel/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": { "strict": false, "checks": [{ "context": "Backend" }, { "context": "Frontend" }] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
```

Qué significa cada opción:

- `strict: false` permite fusionar una PR cuyo CI está en verde aunque `main` haya avanzado desde que se creó. Con `true`, cada PR tendría que actualizarse (y volver a pasar el CI) antes de fusionarse; con varias sesiones en paralelo eso añade una vuelta por PR. Se puede empezar en `false`.
- `required_pull_request_reviews: null` no exige PR: un push directo a `main` seguiría siendo posible. Para exigir PR sin exigir aprobaciones (una persona sola con sesiones aisladas), sustituirlo por `{ "required_approving_review_count": 0 }`.
- `enforce_admins: false` deja al administrador saltarse la regla en caso de urgencia; `true` la aplica también a él.

Para ver el estado o retirarla: `gh api repos/ebotiab/Oniel/branches/main/protection` y `gh api -X DELETE repos/ebotiab/Oniel/branches/main/protection`.
