---
name: revisar-interrupciones
description: Revisar a mano las interrupciones del servicio que Oniel registra en anotaciones.json, consultando Adif y Renfe. Úsala cuando esté abierta la incidencia «Revisar las interrupciones del servicio», cuando una fuente anuncie una reanudación o un corte nuevo, al refrescar los horarios o al comprobar si una línea nueva tiene alguna interrupción vigente.
---

# Revisar las interrupciones del servicio

El procedimiento vive en [docs/datos.md](../../../docs/datos.md): «Interrupciones del servicio» explica los campos y «Cómo se actualiza», los cinco pasos y cada cuánto toca. «Interrupciones registradas» cuenta qué decía cada fuente en las revisiones anteriores y cómo se fijaron los extremos: léelo antes de consultar nada, porque dice qué había que volver a mirar.

Esta skill añade lo que no cabe allí: cómo leer unas páginas que no se dejan descargar, y qué tiene que quedar hecho.

## Qué hay que revisar

```bash
jq -r '.annotations[] | select(.kind == "interrupcion" and .ended_on == null) | "\(.id)  \(.line_id)  \(.from_node) → \(.to_node)  revisada el \(.checked_on)"' backend/data/curated/anotaciones.json
```

```bash
gh issue list --state open --label revision-interrupciones
```

Si hay una incidencia abierta con esa etiqueta, la PR de la revisión la cierra (`Closes #N`); mientras siga abierta, el recordatorio diario no abre otra.

## Cómo leer las fuentes

Las fuentes de cada entrada están en su `source_ids`. Casi siempre son estas:

- **Adif.** `adif.es` responde 403 a las descargas automáticas, también a las herramientas de lectura de páginas: se abre en el navegador integrado, sin iniciar sesión. Sirven `adif.es/viajeros/estado-de-la-red`, `adif.es/viajeros/avisos` y el panel de salidas y llegadas de cada estación, en `adif.es/w/<código>-<nombre>` (por ejemplo `50500-córdoba-j.-anguita`, `03100-jaén`, `50200-sta.cruz-de-mudela`).
- **Los paneles de estación** fijan hasta dónde llegan los trenes: la observación de cada tren dice si hace un trayecto por carretera o si está suspendido. Dos cosas confunden:
  - La primera carga suele dar «No se ha podido recuperar información». Se vuelve a navegar a la misma URL. Si tras varios intentos sigue igual, ese panel queda **sin comprobar** y se dice; no se da por bueno lo del día anterior como si se hubiera visto.
  - Cada tabla trae los trenes que quedan del día y, después, otra tanda sin fecha que empieza hacia las 7.00. Esa segunda tanda no es el día en curso.
- **Renfe.** El listado de la sala de prensa se pinta con JavaScript y no aparece en el texto de la página. Desde el navegador integrado se lee pidiendo con `fetch` la dirección del atributo `endpoint` del elemento `<wrg-news-view>` (`….newsresults.json?page=N`).
- **Prensa.** Solo como fuente secundaria, citada como tal, cuando recoge algo que la fuente oficial no publica.

Apunta la hora de cada página que leas: son avisos en tiempo real, sin histórico, y lo que quede escrito será lo único que se conserve.

## Reglas

- **No se infiere nada.** Lo que la fuente no dice, no se escribe. Un anuncio de la prensa sin nota oficial va a la nota de la entrada con su fuente, y los extremos no se tocan hasta que las fuentes muestren trenes.
- **Los extremos son lo que ve el viajero**: hasta dónde llegan los trenes, no dónde están las obras.
- **Lo que no da para la entrada va al registro de consultas**, no a la nota: una observación que las fuentes no explican se guarda para la siguiente revisión.
- **Tono.** Hechos con fecha y fuente, sin adjetivos y sin hablar de causas ni de responsabilidades. Vale para la entrada, para el registro, para `docs/datos.md` y para la PR.
- **Una interrupción que termina no se borra**: se le pone `ended_on` y pasa a `terminada`.

## Qué tiene que quedar hecho

1. `backend/data/raw/interrupciones/consultas_<fecha>.json`, con la misma forma que los anteriores: `descripcion`, `consultado_el` y una lista `consultas` con `source_id`, `titulo`, `editor`, `url`, `fecha_de_la_pagina`, `resumen` y `que_aporta`. Con palabras propias: no se copia el texto de las páginas.
2. `sources.json`: `retrieved_on`, `file` y `notes` de cada fuente consultada, y las fuentes nuevas que hagan falta.
3. `anotaciones.json`: `checked_on` cambia siempre, haya o no novedades. El resto, solo si la fuente lo sostiene.
4. `uv run oniel-data validate` y `uv run oniel-data import all`, que regenera la instantánea.
5. `docs/datos.md`: la tabla de «Interrupciones registradas», la frase que dice cuándo se comprobaron y un párrafo sobre esta revisión si cambió algo o quedó algo sin ver.
6. Pruebas: las de «Arrancar y comprobar» de `CLAUDE.md` y, con `ONIEL_E2E_STATIC=1`, `e2e/anotaciones.spec.ts`, `e2e/interrupciones.spec.ts` y el fichero de la línea afectada si lo tiene. Las pruebas fijan como «hoy» el 10 de noviembre de 2026: poner `ended_on` o cambiar una previsión no las rompe; cambiar extremos o la fecha de inicio, sí, y se corrigen en la misma PR.

## La PR

La descripción dice, fuente por fuente y con su hora, qué decía cada una; qué cambia en cada entrada, o que no cambia nada; y, en un apartado propio, **qué quedó sin comprobar** y por qué. Si conviene repetir la revisión antes de una semana, también.

Toca `backend/data/`, así que al fusionarse Render reimporta la base: la tarea termina cuando `oniel-data obs estado` enseña el commit desplegado y sin errores, como dice `CLAUDE.md`.
