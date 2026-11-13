---
name: poner-rama-al-dia
description: Traer main a la rama de una PR de Oniel y dejarla lista para fusionar, resolviendo los conflictos habituales y regenerando la instantánea. Úsala cuando una PR tenga conflictos con main, cuando main haya avanzado y la PR regenere frontend/public/data, o cuando la app despierte la sesión por un conflicto.
---

# Poner la rama al día con `main`

Las PR que regeneran la instantánea se pisan entre sí: cuando una se fusiona, las demás tienen que traer `main`, regenerar y esperar otra vuelta de CI. Esta skill es ese rato, hecho siempre igual.

Si la PR es la del refresco automático de horarios (rama `datos/gtfs-<fecha>`), no se resuelve: se cierra y se relanza el flujo, como dice la skill `refresco-gtfs`.

## Pasos

1. Trae `main` y fusiónalo en la rama:

   ```bash
   git fetch origin
   ```

   ```bash
   git merge origin/main
   ```

2. Resuelve cada conflicto según el fichero (tabla de abajo). Deja la instantánea para el final.
3. Si la PR toca datos, o si `main` trae datos nuevos y la PR también, regenera:

   ```bash
   cd backend && uv run oniel-data validate
   ```

   ```bash
   cd backend && uv run oniel-data import all
   ```

   con la base de datos de la sesión (`ONIEL_DATABASE_URL`). Si entre las dos ramas hay líneas nuevas, nodos compartidos que cambian o conexiones a trazos retiradas, sobre una base vacía.
4. Pasa las comprobaciones rápidas de las mitades tocadas, las de «Antes de abrir la PR» del `README.md`. Las pruebas no se repiten en local salvo las de los recuentos que el cruce haya podido mover: lo demás lo vuelve a pasar el CI.
5. Confirma la fusión con un mensaje en español y sube. La marca de fusión automática de la PR se mantiene.
6. Si la descripción de la PR daba cifras (viajes, pasos, pesos de la instantánea), ponlas al día.

## Cómo se resuelve cada fichero

| Fichero | Qué se hace |
|---|---|
| `frontend/public/data/**` | Nunca a mano. Se toma cualquiera de los dos lados para salir del conflicto y se regenera con `import all` cuando lo demás está resuelto. |
| `backend/data/curated/sources.json`, `anotaciones.json` | A mano, conservando las entradas de los dos lados. Después, `validate`. |
| `backend/data/curated/<línea>.json` | A mano. Si las dos ramas añaden `via` o reglas de recorrido a la misma línea, van las de ambas; `validate` dice si alguna ya no encaja. |
| `backend/src/oniel/settings.py` (`line_ids`) | Las líneas de los dos lados. La primera de la lista define los nodos compartidos: no se mueve. |
| Recuentos de las pruebas (`backend/tests/`, `frontend/e2e/`) | No se elige un lado. Se regenera, se pasa la prueba y se escribe lo que da. Si el número no es el de ninguna de las dos ramas, es lo esperable cuando las dos añaden trenes, y se explica en la PR. |
| `docs/datos.md`, `docs/simulacion.md` | Las filas y los apartados de los dos lados. Las cifras que suman toda la red (líneas, kilómetros, nodos, tramos, pesos de la instantánea) se vuelven a leer del resultado. |
| `docs/hoja-de-ruta.md`, `CLAUDE.md` | Lo de los dos lados. Comprueba que la lista de líneas y su número siguen cuadrando. |
| `frontend/src/app/app.css` | A mano, mirando el final de cada lado: varias sesiones añaden reglas al final y la llave de cierre puede quedar fuera del bloque en conflicto. Después, `npm run build`, que comprueba las hojas compiladas. |
| `.github/scripts/que-cambia.sh`, flujos de CI | A mano, y se lee el resultado entero: una regla perdida no hace fallar nada, solo deja de lanzar pruebas. |

## Señales de que algo ha quedado mal

- `validate` da una parada sin asignar o una regla que no encaja con ningún viaje: una de las dos ramas cambió el filtro o las asignaciones de una línea que la otra también toca.
- El día de referencia ha cambiado: los recuentos de todas las líneas se mueven, no solo los de la PR.
- `git status` enseña en `frontend/public/data` ficheros que ninguna de las dos ramas explica: la base de la sesión tenía datos de otra tarea. Se reimporta sobre una base vacía.
- El CSS compilado trae un selector anidado donde no toca (`body{` dentro de otra regla): falta una llave.

## Después

Si mientras esperas el CI se fusiona otra PR de datos, toca repetirlo. Conviene decirlo al usuario cuando haya más de dos PR de datos abiertas a la vez: cada una fusionada obliga a las demás a otra vuelta.
