# Guía: del primer vistazo a una consulta propia

Revisión del 25 de noviembre de 2026, partiendo de `main` en `f1d5bbe`. Capturas del visor con la instantánea real: escritorio de 1440 × 900 y móvil de 390 × 844. Se mantiene la columna, Archivo, el papel, las reglas y el azul de los enlaces de Oniel.

## Lo que faltaba explicar

La guía anterior llevaba a las fichas, pero no explicaba por qué Almagro está abajo en el esquema, qué enseña un destino fuera de la línea o en qué se diferencia una hora estimada de una publicada. El comparador permitía elegir Ávila o Segovia sin explicar la diferencia entre su tiempo sin paradas y los trenes directos del horario. La vuelta a una guía más larga necesitaba conservar el lugar de lectura.

## Recorrido comprobado

- La invitación al mapa aparece sin desplazarse. Las cuatro estaciones abren sus fichas; Atrás devuelve al enlace de salida.
- Desde Manzanares – Ciudad Real se abre Daimiel en el esquema, se consulta Alcázar de San Juan entre sus destinos, se vuelve a toda la línea y se abre el tramo Daimiel – Almagro. La vía única y las horas calculadas se explican antes de abrirlo.
- En Madrid – Valladolid se seleccionan los dos caminos, por Segovia y por Ávila. Se comprueban las cifras sin paradas y la información de trenes directos.
- La pregunta sobre fechas abre Cobertura y fuentes. Desde su índice se consultan los operadores y se despliegan las fuentes de los horarios. El ejemplo del Glosario lleva al dibujo de los cruces en vía única.
- El cierre permanece plegado como exploración opcional: abre el formulario del tramo correcto y permite volver. La prueba estática comprueba el acceso y los controles; no calcula una simulación, que necesita la API y no se ha modificado.
- Guía en la cabecera o el menú recupera el apartado abierto, la posición y el foco. Mapa recupera la última ficha o comparación. Tab, Intro, Mayús+Tab y Espacio permiten recorrer el ejemplo del tramo y regresar sin ratón.

`e2e/guia.spec.ts`: 16 casos pasados, ocho en cada proyecto, con `ONIEL_E2E_STATIC=1` y Chromium instalado en el entorno (configuración local temporal, sin cambios en la configuración del CI). También pasan tipos, lint y compilación. La guía se comprueba con las peticiones de datos bloqueadas. Se revisaron además renderizados los apartados de fechas, alcance y cierre desplegados.

## Capturas

| Vista | Escritorio | Móvil |
| --- | --- | --- |
| Primera pantalla | [Entrada](escritorio-entrada.jpg) | [Entrada](movil-entrada.jpg) |
| Pregunta sobre el tramo abierta | [Preguntas](escritorio-preguntas.jpg) | [Preguntas](movil-preguntas.jpg) |
| La misma línea en el mapa y el esquema | [Línea](escritorio-linea.jpg) | [Línea](movil-linea.jpg) |
| Ficha real de Daimiel – Almagro | [Tramo](escritorio-tramo.jpg) | [Tramo](movil-tramo.jpg) |

Un aprendizaje concreto: «vía única» significa que los dos sentidos comparten vía. Al abrir el tramo, el visitante encuentra esa característica y distingue las horas publicadas de las calculadas; el dibujo del Glosario explica cómo pueden cruzarse dos trenes. Las cifras y fechas de las capturas pertenecen a la instantánea de ese día; la guía no las fija en el texto.
