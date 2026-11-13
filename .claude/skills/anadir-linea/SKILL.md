---
name: anadir-linea
description: Añadir una línea ferroviaria a Oniel o prolongar una ya cargada, siguiendo «Añadir otra línea» de docs/datos.md. Úsala cuando la tarea sea cargar una línea, un ramal, un baipás o un trecho nuevo de la red: trazado de OpenStreetMap, especificación curada, asignación de paradas, filtro de corredor, pruebas, instantánea y documentación.
---

# Añadir una línea

El procedimiento vive en [docs/datos.md](../../../docs/datos.md), apartado «Añadir otra línea»: diecisiete pasos y, debajo, lo aprendido con cada línea cargada. Léelo entero antes de empezar, también las lecciones, porque casi todos los tropiezos de una línea nueva ya le pasaron a otra. Esta skill no lo repite: dice en qué orden trabajar, qué comprobar antes de seguir y cuándo está terminada.

Si al terminar has aprendido algo que no estaba, va a `docs/datos.md` como un bloque «Lo aprendido al…», no a esta skill.

## Antes de escribir nada

1. Lee el brief de la tarea (`gh issue view <número>`) y el apartado «Ampliar la red» de `docs/hoja-de-ruta.md`.
2. Mira qué otras PR de datos hay abiertas (`gh pr list`). Dos PR que regeneran la instantánea se pisan: si hay otra, cuenta con fusionar `main` y regenerar al final (skill `poner-rama-al-dia`).
3. Usa una base de datos propia de la sesión, porque otras sesiones comparten el mismo PostgreSQL y las pruebas de integración vacían la base de pruebas:

   ```bash
   docker exec oniel-postgres createdb -U oniel oniel_<tarea>
   docker exec oniel-postgres createdb -U oniel oniel_<tarea>_test
   ```

   y exporta `ONIEL_DATABASE_URL` y `ONIEL_TEST_DATABASE_URL` apuntando a ellas (puerto 5433). Bórralas al terminar.
4. Decide qué estás añadiendo, porque cambia el procedimiento:
   - **Una línea o dos.** Si por una parte del recorrido circula un operador y por otra no, son dos.
   - **Prolongación.** La línea crece sin cambiar de id; por el origen cambian los kilómetros de todos sus nodos.
   - **Baipás.** Otro camino entre dos nodos de una línea cargada: `bypass_of`, sin paradas ni filtro.

## Orden de trabajo y puntos de control

No pases de una fase sin su comprobación: los errores de trazado se pagan en la asignación de paradas, y los de asignación, en los recuentos.

**1. Trazado y fuentes (pasos 1 a 4).** Cada fichero crudo va a `backend/data/raw/` con la fecha en el nombre y cada fuente a `sources.json` antes de usar el dato. Comprueba que la relación de OpenStreetMap es de una pieza trazándola de punta a punta, y mira dónde están de verdad sus extremos: el nombre de una relación no lo dice. Lo que no esté en una fuente no se estima: se deja sin poner y se dice.

**2. Especificación (pasos 5, 6 y 10).** `backend/data/curated/<línea>.json`, los puntos kilométricos tal como los da Adif y el id en `line_ids`. Los tres atributos de señalización son obligatorios. Si la línea sustituye a una conexión a trazos de otra especificación, retírala de allí.

**3. Trenes (pasos 7 a 9).** Saca del GTFS los patrones de parada de los trenes de la línea antes de escribir asignaciones: dicen qué paradas de fuera hay que asignar. Después:

```bash
cd backend && uv run oniel-data validate --spec data/curated/<línea>.json
```

hasta que no haya problemas ni ningún paso `indeterminado`, y luego `validate` sin `--spec`, que comprueba los `via` entre líneas. `validate` no ve dos cosas, y hay que mirarlas a mano:

- Los trenes que cruzan la línea sin parar en ella. Lista los pares de paradas seguidas que entran y salen, y comprueba que cada uno tiene regla de recorrido aquí y en la línea vecina.
- Una parada asignada a una salida que no es la suya. La asignación es válida; lo delata el recuento de trenes por tramo.

**4. Interrupciones (paso 12).** Mira si la línea tiene alguna vigente. Cómo leer las páginas de Adif está en la skill `revisar-interrupciones`. Si no hay ninguna, se dice con la fecha en el apartado de la línea.

**5. Importación e instantánea (paso 13).** `uv run oniel-data import all` sobre la base de la sesión. Si has retirado una conexión a trazos o has movido nodos compartidos, impórtalo sobre una base vacía antes de dar la instantánea por buena. Anota los pesos nuevos en «Medidas».

**6. Pruebas (pasos 14, 16 y 17).** La especificación entra en `SPECS` y la línea tiene su `test_<línea>.py`. El paso 14 enumera los ficheros cuyos recuentos cambian, en el backend y en el visor. Si el día de referencia se mueve, cambian los recuentos de todas las líneas, no solo los de la nueva. Ningún recuento se ajusta a ojo: se lee del resultado y se explica en la PR por qué cambia.

**7. Documentación (paso 15).** Las tablas de `docs/datos.md`, el apartado «Cómo se construyó…», la tabla de «Tramos sin alternativa» de `docs/simulacion.md`, la lista de líneas de `CLAUDE.md` y la hoja de ruta.

## Qué pasar en local

Lo que dice «Arrancar y comprobar» de `CLAUDE.md`: las comprobaciones rápidas de las dos mitades, `pytest` con la base de pruebas de la sesión, `oniel-data validate` y, con `ONIEL_E2E_STATIC=1`, solo los ficheros de Playwright que enumera el paso 14 más el de la línea nueva. La batería completa la pasa el CI.

## Está terminada cuando

- `validate` no da problemas, con y sin `--spec`.
- Todo dato nuevo tiene su fuente en `sources.json` y su fichero crudo con fecha.
- La instantánea regenerada va en la PR, con `index.json` y `lines/<id>.json` al día.
- Los recuentos que cambian están explicados en la descripción de la PR, uno por uno.
- Las tablas y los apartados del paso 15 están al día.
- La descripción lleva `Closes #N` y la hoja de ruta ya no lista la tarea.

Si la línea roza los accidentes de Adamuz o de Urda, o cualquier interrupción, el tono es el de `CLAUDE.md`: hechos con fecha y fuente, sin adjetivos.
