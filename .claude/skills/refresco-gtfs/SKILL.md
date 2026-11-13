---
name: refresco-gtfs
description: Revisar o hacer a mano el refresco de los horarios GTFS de Oniel. Úsala cuando haya una PR con la etiqueta refresco-gtfs, cuando esté abierta la incidencia «El fichero nuevo de horarios de Renfe no pasa las comprobaciones» o «Descargar a mano los horarios que están a punto de caducar», o cuando se pida cargar un fichero de horarios más reciente de Renfe o de Ouigo.
---

# Refresco de los horarios

El detalle vive en [docs/datos.md](../../../docs/datos.md): «Conjuntos de datos» explica qué es un conjunto vigente y uno activo, y «Refresco de los horarios», qué hace el flujo semanal `.github/workflows/gtfs.yml`, qué cuenta como cambio y por qué. Léelo antes de opinar sobre una PR de refresco. Esta skill dice qué hacer en cada uno de los tres casos en que te van a llamar.

```bash
gh pr list --state open --label refresco-gtfs
```

```bash
gh issue list --state open --label refresco-gtfs
```

## Caso 1: hay una PR de refresco abierta

La abre el flujo, no una sesión, y **fusionarla publica los horarios**: eso lo decide quien mantiene Oniel. La sesión la revisa, dice lo que ha visto y recomienda; solo la fusiona si se lo han pedido.

Qué mirar:

1. **Por qué se abrió.** La descripción lo dice: porque cambian trenes en las próximas cuatro semanas, o porque el fichero cargado tiene 28 días o más. En el segundo caso puede no cambiar ningún tren, y está bien.
2. **La validez.** Los ficheros vigentes de todos los operadores tienen que coincidir en algún día. Si el de Ouigo está a punto de caducar, dilo aunque la PR pase.
3. **Los viajes por línea y los pasos por tramo que cambian.** Una diferencia pequeña y repartida es un horario nuevo. Una línea que pierde muchos trenes de golpe, o un tramo que se queda a cero, pide una explicación antes de fusionar: una interrupción del servicio que Renfe ya refleja en el horario, o una parada o una regla de recorrido que han dejado de encajar.
4. **El día de referencia.** Si se mueve, cambian las cifras que enseña el visor en todas las líneas y las tablas de `docs/datos.md` que las citan.
5. **El CI.** GitHub retiene los flujos de una PR abierta por otro flujo («Approve workflows to run»); ese clic es del usuario. El flujo lanza además el CI sobre la rama, y ese resultado sí se puede leer:

   ```bash
   gh run list --branch datos/gtfs-<fecha> --workflow ci.yml
   ```

6. **Las interrupciones.** Un refresco de horarios es uno de los momentos en que toca revisarlas (skill `revisar-interrupciones`), en su propia PR.

Si la PR entra en conflicto con `main` porque se fusionó otra que regenera la instantánea, no se resuelve: se cierra sin fusionar, se borra su rama y se relanza el flujo, que abre otra sobre el `main` actual.

```bash
gh workflow run gtfs.yml
```

Cerrar la PR y relanzar el flujo se le propone al usuario; no se hace por iniciativa propia.

Tras la fusión cambia `backend/data/`: Render reimporta, y la tarea termina cuando `oniel-data obs estado` enseña el commit desplegado y su importación completada, como dice `CLAUDE.md`.

## Caso 2: el fichero nuevo no pasa las comprobaciones

El flujo terminó en rojo, no abrió la PR y abrió una incidencia con el enlace a la ejecución. Mira primero qué paso falló allí y después reprodúcelo:

```bash
cd backend && uv run oniel-data refresh gtfs
```

```bash
cd backend && uv run oniel-data validate
```

```bash
cd backend && uv run oniel-data import all
```

Lo habitual es una de estas tres cosas:

- **Una parada sin asignar.** Un tren nuevo llega a una parada de fuera que ninguna línea tenía. Se asigna a su salida en la especificación de cada línea que recorre.
- **Una regla de recorrido que ya no encaja con ningún viaje.** El tren que la justificaba ya no circula o ha cambiado de paradas. Se corrige o se retira, y se dice en la PR.
- **Una prueba del visor que da por fijo un recuento de la instantánea.** Las de `pytest` no cambian, porque leen siempre los dos ficheros fijos de `backend/tests/conftest.py`; las de Playwright leen la instantánea regenerada.

La PR que lo arregla lleva el fichero nuevo, la instantánea y las tablas de `docs/datos.md`, y cierra la incidencia (`Closes #N`).

## Caso 3: un fichero de descarga manual está a punto de caducar

Hoy es el de Ouigo. El Punto de Acceso Nacional exige iniciar sesión, y Oniel no guarda credenciales de nadie. La sesión no crea cuentas ni escribe contraseñas: pide a quien mantiene Oniel que descargue el fichero (conjunto 1515) o que inicie sesión en su navegador, y pide permiso antes de descargar nada diciendo fichero, origen y tamaño.

Con el zip ya descargado:

1. Guárdalo en `backend/data/raw/ouigo/gtfs_ouigo_<fecha>.zip`, con el día de descarga en el nombre.
2. Añádelo al final de `feeds` en `sources.json`, copiando `product` y `stop_id_prefix` de la entrada anterior, y pon al día `retrieved_on`, la cobertura y las notas de su fuente.
3. `validate`, `import all` y las tablas «Conjuntos de datos» y «Operadores y sus horarios» de `docs/datos.md`.
4. La PR cierra la incidencia.

El fichero anterior sigue declarado: el histórico se conserva mientras esté en `feeds` y en `backend/data/raw/`.

## Qué no hacer

- No abrir a mano una PR de refresco de Renfe mientras haya otra abierta con la etiqueta: el flujo no descarga nada hasta que se cierre.
- No comparar los zip por su SHA-256: Renfe sirve bytes distintos con el mismo contenido. `refresh gtfs` compara el contenido y los trenes.
- No tocar los recuentos de `pytest` por un fichero nuevo. Si cambian, el fallo está en otra parte.
