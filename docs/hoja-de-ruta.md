# Hoja de ruta de Oniel

Las tareas pendientes, ordenadas, y los principios con los que se construyen. Última revisión: 13 de noviembre de 2026.

Oniel es para quien no sabe de ferrocarril y quiere consultar la red española de forma clara, intuitiva y atractiva, y debe poder crecer durante años sin complicarse. Las tareas de esta lista están pensadas con eso delante: cada una deja un mecanismo que la siguiente reutiliza.

## Cómo se usa

- Cada tarea es una incidencia de GitHub en [ebotiab/Oniel](https://github.com/ebotiab/Oniel/issues) con el brief completo: **por qué** se hace, **qué datos** usa, **qué toca** en el código, **cuándo está hecha** y **de qué depende**. Las condiciones de «hecha» son el criterio de aceptación de la PR. Este documento es el índice ordenado y los principios de arquitectura; no repite los briefs, y lo hecho está en `docs/historial.md`.
- Cada tarea se hace en una sesión aislada, en su rama y en una PR pequeña contra `main`, siguiendo `CLAUDE.md`. El usuario decide qué tarea abre cada sesión; lo normal es la primera de la lista que nadie tenga empezada y cuyas dependencias estén cerradas. Para empezar: `gh issue view <número> --repo ebotiab/Oniel`.
- Las tareas de datos van de una en una: la siguiente arranca cuando la anterior se ha fusionado. Cada PR que entra en `main` obliga a las demás a traer `main`, regenerar la instantánea, rehacer los recuentos y repetir las pruebas y el CI, y ese trabajo repetido es lo que más tiempo y más cuota de uso gasta. Chocan siempre la instantánea de `frontend/public/data/`, este documento, `docs/historial.md`, `CLAUDE.md`, `docs/datos.md` y los recuentos de las pruebas. A la vez que una tarea de datos sí puede ir otra de solo visor, de código del backend o de documentación. Una sesión con la PR fusionada y producción comprobada ha terminado y se archiva.
- La PR que termina una tarea cierra su incidencia (`Closes #N` en la descripción, en inglés: GitHub no reconoce «Cierra #N»), retira su línea de la lista de abajo y añade una entrada de dos o tres frases al final de `docs/historial.md`; lo aprendido va a `docs/datos.md`, `docs/simulacion.md`, `docs/diseno.md` o `docs/despliegue.md`.
- Si al hacer una tarea aparece otra, no se hace de paso: se abre una incidencia nueva con el mismo formato (Por qué / Qué datos usa / Qué toca / Hecha cuando / Depende de), con sus etiquetas (`arquitectura`, `datos`, `visor`, `analisis`, `infraestructura`), y se añade a la lista en el sitio que le corresponda. Lo que cabe en una PR pequeña y no merece incidencia propia va a la lista de pendientes menores (#31).
- Las decisiones de diseño siguen `docs/diseno.md`. Si una tarea necesita una representación nueva (un trazo, un color, un panel), se propone al usuario y, decidida, se anota allí antes de implementarla.
- Toda fuente nueva se registra en `backend/data/curated/sources.json` y su fichero crudo va a `backend/data/raw/` con la fecha en el nombre. Sin fuente, el dato no entra.
- Todo lo que roce los accidentes de Adamuz (18 de enero de 2026) y Urda (28 de octubre de 2026) va en tono sobrio y neutro: hechos, fechas y fuente.

## Hecho hasta ahora

El registro de lo ya fusionado, PR a PR, está en [historial.md](historial.md). No hace falta leerlo para empezar una tarea: se busca en él cuando se necesita saber cuándo y por qué entró algo.

## Principios de arquitectura

Oniel tiene que entenderse sin saber de ferrocarril y crecer durante años. Estos principios evitan que cada dato o capa nueva traiga su propio caso particular; la incidencia que materializa cada uno va entre paréntesis.

1. **Se entiende sin saber de ferrocarril.** Cada ficha dice primero lo esencial en lenguaje llano y guarda plegado el detalle (puntos kilométricos exactos, códigos, fuente y fecha), para que no estorbe. A quien trabaja en el sector puede serle útil, pero nada se diseña para él ni se añade complejidad por él (#15).
2. **Todo dato con fuente y fecha, como estructura.** Un dato no es un texto con una nota al pie sino un valor con `source_id`, `checked_on` y, cuando la tiene, su vigencia. Así el visor puede citar la fuente junto a cada cifra y una revisión programada puede saber qué dato envejece.
3. **Anotaciones de red: un modelo común.** Todo lo que pasa sobre la red entre dos fechas según una fuente (interrupciones, obras, proyectos, cambios de servicio) comparte un modelo con tipo, alcance, estado, fechas y fuentes. Un tipo nuevo es una entrada en un registro, no una tabla, un endpoint y una capa nuevos. Hecho en #17: `AnnotationSpec`, `anotaciones.json`, tabla `annotations` y `GET /api/annotations` (`docs/datos.md`, «Anotaciones de red»).
4. **Atributos de tramo por secciones.** Lo que cambia a lo largo de una línea (vías, electrificación, señalización, velocidad, ancho) se declara de nodo a nodo con un único mecanismo que lo reparte a los tramos, valida su cobertura y lo muestra. Hecho en #19: `attribute_sections` en la especificación de cada línea, tabla `segment_attributes`, `attributes` en cada tramo de la API y de la instantánea, y la lista `SEGMENT_ATTRIBUTES` del visor (`docs/datos.md`, «Atributos de tramo»). La señalización (#20) entró así: secciones, tres reglas y tres entradas de la lista.
5. **Grafo y escenarios.** Un grafo único de todas las líneas cargadas y un escenario serializable (una lista de modificaciones: cerrar tramos, añadir un enlace, cambiar una velocidad). De ahí salen la simulación de cierre, el comparador de recorridos y los «¿y si?» que vengan, con un solo cálculo (#23).
6. **Conjuntos de datos fechados.** Cada horario importado es un conjunto con fuente, fecha de descarga y validez; refrescar añade, no sustituye. Así se puede decir cómo ha cambiado el servicio en una estación o un tramo. Hecho en #21: tabla `datasets`, lista `feeds` de `sources.json` y conjunto activo por fuente y día (`docs/datos.md`, «Conjuntos de datos»). Desde #27 las fichas comparan los conjuntos de una misma fuente («Evolución del servicio»). Desde #29 el de Renfe lo añade cada semana un flujo que abre una PR.
7. **Registro de capas en el visor.** Cada capa declara sus datos, su estilo, su entrada de leyenda, su ficha y su ruta. Añadir una capa no toca las demás. Empezado en #17 con las anotaciones: `frontend/src/app/annotationLayers.ts` tiene una entrada por tipo, y el mapa, el esquema, la leyenda, la ficha y las listas leen de ella. Las capas de anotaciones no tienen todavía ruta propia en la URL.
8. **Toda vista tiene ruta en la URL.** Una línea, un nodo, un tramo, un escenario, una comparación o un término del glosario se pueden compartir con un enlace exacto (#15). Desde #107 la ruta es una dirección limpia, sin almohadilla, que una sola función construye y otra interpreta (`docs/diseno.md`, «Rutas»).
9. **La red se carga por partes.** El visor arranca con un índice ligero de toda la red (líneas, nodos sin textos, geometría simplificada) y pide el detalle de cada línea cuando se abre o cuando el mapa se acerca a ella; añadir una línea apenas cambia lo que pesa el arranque. El grafo entero va en el índice, así que buscar, enlazar y calcular recorridos no dependen de qué líneas se hayan cargado. Hecho en #43: `index.json` y `lines/<id>.json` (que sustituyen a `network.json` y `segment-counts.json`, ya retirados), `GET /api/lines` y `GET /api/lines/{id}`, con las medidas en `docs/datos.md`, «Instantánea estática».

## Orden

Aparte de las líneas que quedan por cargar, que van en «Ampliar la red», no hay ninguna tarea abierta.

Las que vengan se añaden aquí como incidencias nuevas, con el formato de «Cómo se usa».

## Ampliar la red

La red crece poco a poco, una línea por PR, con «Añadir otra línea» de `docs/datos.md`, y por etapas. Las incidencias abiertas, en este orden:

**Granada y Jaén.** Para que el comparador de recorridos enseñe los dos caminos de Madrid a Granada. Hecha: la línea convencional Linares-Baeza – Moreda – Granada (#101), el ramal Espelúy – Jaén (#102) y la alta velocidad de Córdoba a Granada por Antequera (#103), que entró como dos líneas. La línea de alta velocidad Córdoba – Málaga llega ya hasta Málaga-María Zambrano (#118).

**Levante.** Para ver por qué los trenes de Madrid a Valencia y Alicante dejaron el camino de Alcázar y Albacete. Hecha: la línea convencional Alcázar de San Juan – Albacete (#114), la de alta velocidad Madrid – Cuenca – Valencia (#115) y la de alta velocidad Albacete – Alicante (#116). El comparador enseña los dos caminos de Madrid a Albacete: 277,6 km y 1 h 46 min por Alcázar, 313,6 km y 1 h 5 min por Cuenca. La línea de Valencia empieza ya en Madrid-Chamartín (#168), de donde salen casi todos sus trenes.

**Murcia.** Hecha: la línea de alta velocidad Monforte del Cid – Murcia (#170), que cierra el corredor de Levante y, con él, los corredores de alta velocidad más usados desde Madrid. El comparador enseña Madrid – Murcia: 529,5 km y 2 h 3 min desde Madrid-Chamartín. El enlace de Monforte del Cid, por el que llegan a ella los trenes de Alicante, se cargó después como una línea corta que cuelga de ella: de Alicante a Murcia el comparador da 88,4 km.

**Norte y noroeste.** Hechas: la línea de alta velocidad Madrid – Segovia – Valladolid (#171), la puerta de todo el norte, la de Valladolid a León por Palencia (#172), la de Olmedo a Ourense por Zamora (#174), el camino a Galicia, la de Venta de Baños a Burgos (#173) la de León a Oviedo y Gijón por la variante de Pajares (#176) la convencional de Burgos a Vitoria por Miranda de Ebro (#177) y las dos de Galicia, la alta velocidad de Ourense a Santiago y la de A Coruña a Vigo por Santiago, el Eje Atlántico (#175). El comparador enseña Madrid – León: 344,6 km desde Madrid-Chamartín; Madrid – Ourense, 461,4 km; Madrid – Zamora, 231,5 km; Madrid – Burgos, 303,2 km; Madrid – Oviedo, 445,5 km, Madrid – Gijón, 477,1 km; Madrid – Vitoria, 420,5 km; Madrid – A Coruña, 610,6 km, y Madrid – Vigo, 643,0 km. El orden de las demás lo marcan las dependencias: cada línea cuelga de un nodo que carga la anterior. De `miranda-de-ebro` cuelga #219, y de `vitoria-gasteiz`, #220. En Galicia quedan a trazos, sin incidencia abierta, las líneas convencionales de Ourense a Vigo y a Monforte de Lemos y Lugo, la de A Coruña a Ferrol y a Lugo, la línea antigua de Ourense a Santiago por Lalín, las vías antiguas de Padrón y de Redondela a Vigo-Guixar, con la salida hacia Portugal, y el enlace de Conxo, por el que algunos trenes de Madrid a Vigo evitan la estación de Santiago; si se carga, será como un enlace (`link_of`). Logroño y Pamplona, que salen a trazos de Miranda de Ebro y de Altsasu, van en #213. Quedan a trazos, sin incidencia abierta, la vía antigua del puerto de Pajares, de la bifurcación Pajares a Pola de Lena, por la que van los regionales, y el ramal de Villabona de Asturias a Avilés. El ramal de Soto de Cerrato, por el que los trenes de Palencia llegan a la línea de Burgos, sigue a trazos; si se carga, será como un enlace (`link_of`). Las zonas de la lista ya están en el registro: Valladolid – León y Venta de Baños – Burgos van en «Castilla y León»; Olmedo – Ourense y las dos de Santiago, en «Galicia»; León – Gijón y Burgos – Vitoria, en «Asturias, Cantabria y País Vasco». El encuadre del mapa ya es la península entera (`docs/diseno.md`, «Encuadre»).

- [#219](https://github.com/ebotiab/Oniel/issues/219) Datos: línea convencional Miranda de Ebro – Orduña – Bilbao. Depende de #177, ya cerrada.
- [#220](https://github.com/ebotiab/Oniel/issues/220) Datos: línea convencional Vitoria – Altsasu – San Sebastián – Irún, sin los servicios de Cercanías. Depende de #177, ya cerrada.

**Extremadura.** Para ver qué parte del camino de Madrid a Badajoz es nueva y cuál no. Hecha (#179): la línea convencional Madrid – Talavera de la Reina – Plasencia, la de alta velocidad Plasencia – Cáceres – Badajoz, la convencional Aljucén – Mérida y la línea antigua Monfragüe – Cañaveral – Cáceres. Quedan a trazos, sin incidencia abierta, las líneas de Cáceres a Valencia de Alcántara, de Badajoz a Elvas, de Mérida a Sevilla por Zafra y de Mérida a Ciudad Real.

**Completar la alta velocidad.** Lo que le falta a la red de alta velocidad en servicio, después del norte. Hecha: la línea de alta velocidad Barcelona – Girona – Figueres (#204), que continúa la de Madrid hasta el límite con la sección internacional de Perpiñán y entra como línea aparte, porque Ouigo e Iryo acaban en Barcelona. Los TGV de SNCF de París a Barcelona la recorren y no están cargados: cargar sus horarios, que SNCF publica, va en #230. También están hechos los ramales de La Sagra a Toledo y de Zaragoza a Huesca (#205). El comparador enseña Madrid – Toledo, 74,9 km desde Madrid-Puerta de Atocha, y Madrid – Huesca, 390,7 km. Quedan a trazos, sin incidencia abierta, la línea convencional de Tardienta a Monzón y Lleida y la de Huesca a Jaca y Canfranc. Queda:

- [#230](https://github.com/ebotiab/Oniel/issues/230) Datos: horarios de SNCF para los TGV de París a Barcelona. Depende de #204, ya cerrada.

**Media distancia.** Las líneas convencionales con más viajeros fuera de Cercanías y las capitales que aún no están en el mapa. Ninguna carga servicios de Cercanías. Hecha: la línea Sevilla – Cádiz (#206), que sigue desde Sevilla-Santa Justa; el comparador enseña Madrid – Cádiz, 622,7 km. Queda a trazos, sin incidencia abierta, la línea de Utrera a Marchena, Osuna y Bobadilla, por la que van los trenes de Sevilla a Málaga. Hecha también la línea convencional Barcelona – Girona – Portbou (#210), por Granollers, que comparte con la alta velocidad Barcelona-Sants y Girona: el comparador enseña los dos caminos de Barcelona a Girona y a Figueres. Quedan a trazos, sin incidencia abierta, la línea del Maresme, de Maçanet-Massanes a Barcelona por la costa, y la continuación de Portbou a Cerbère.

- [#209](https://github.com/ebotiab/Oniel/issues/209) Datos: línea Tarragona – Barcelona por la costa. Une el Corredor Mediterráneo con Barcelona.
- [#208](https://github.com/ebotiab/Oniel/issues/208) Datos: línea València – Xàtiva – La Encina – Alicante.
- [#211](https://github.com/ebotiab/Oniel/issues/211) Datos: línea convencional Madrid – Ávila – Medina del Campo – Valladolid.
- [#212](https://github.com/ebotiab/Oniel/issues/212) Datos: línea Palencia – Santander.
- [#213](https://github.com/ebotiab/Oniel/issues/213) Datos: línea Zaragoza – Castejón – Pamplona y Logroño.
- [#207](https://github.com/ebotiab/Oniel/issues/207) Datos: línea Sevilla – Huelva.

**Cercanías.** Lo que más gente usa y lo último en entrar, porque es otro tipo de red y antes hay que decidir cómo se ve:

- [#214](https://github.com/ebotiab/Oniel/issues/214) Diseño: cómo se enseña un núcleo de Cercanías sin saturar el mapa, con Madrid como piloto. De ella saldrán las incidencias de datos, un núcleo por incidencia.

Las PR de datos se pisan en la instantánea y en los recuentos de las pruebas: estas líneas entran de una en una.

## Pendientes menores

Lo que apareció al hacer otras tareas y cabe en una PR pequeña está en [#31](https://github.com/ebotiab/Oniel/issues/31), como lista con casillas: hoy no queda ninguno sin marcar.

## `main` protegida: solo entra por PR y con el CI en verde

Activado el 12 de noviembre de 2026 con la protección clásica de rama, por `gh api`. El repositorio es público, así que está disponible en el plan gratuito. Lo que exige:

- **Comprobaciones obligatorias** `Backend` y `Frontend`, los `name:` de los dos trabajos finales de `.github/workflows/ci.yml` (con `app_id` 15368, el de GitHub Actions). Desde #96 esos dos trabajos no prueban nada: resumen a los que sí prueban (el backend, la compilación del visor y los cuatro fragmentos de Playwright) y fallan si alguno falla, de modo que repartir el trabajo de otra forma no obliga a tocar la regla. Si se renombra uno de los dos hay que cambiarlo también en la regla, o ninguna PR podrá fusionarse.
- **Pull request obligatoria**, sin aprobaciones (`required_approving_review_count: 0`): no se puede hacer push directo a `main`.
- **Se aplica también a los administradores** (`enforce_admins: true`). Es lo que hace que la regla valga para las sesiones, que actúan con el usuario del propietario: sin esto, `gh pr merge` fusionaría igual con el CI en rojo.
- **Sin exigir la rama al día** (`strict: false`): una PR con el CI en verde se fusiona aunque `main` haya avanzado desde que se abrió. Con varias sesiones en paralelo, `true` añadiría una vuelta de CI por PR.
- Sin force push ni borrado de `main`.

Desde el 12 de noviembre de 2026 el repositorio tiene además activada la fusión automática («Allow auto-merge», `gh api -X PATCH repos/ebotiab/Oniel -f allow_auto_merge=true`). No es parte de la regla ni la relaja: permite marcar una PR con `gh pr merge --squash --auto` para que GitHub la fusione cuando las comprobaciones obligatorias pasen.

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
