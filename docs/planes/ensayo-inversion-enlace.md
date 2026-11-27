# Un enlace directo y una parada con inversión de marcha

En el grafo ficticio, la consulta ordinaria devuelve primero el enlace (178,4 km) y después el recorrido por la estación (181,6 km). El visor identifica el segundo con «Invierte la marcha en Parada». El orden, los tramos, los kilómetros y los minutos coinciden con la API en ambos sentidos. El ensayo parte del [plan de Conxo](enlace-conxo.md#comprobaciones-de-aceptación) y de [`main` en 2db93535](https://github.com/ebotiab/Oniel/commit/2db935354ae7ab2dfc2498d2849a738d52d46bd7).

## Repetir la prueba

En un clon con uv, Python 3.13 y Node con la versión que admite el visor (probado con Node 24), desde la raíz de esta rama:

```bash
(cd frontend && npm ci && ONIEL_E2E_STATIC=1 npx playwright test e2e/inversion-enlace.spec.ts --project=escritorio)
```

Playwright ejecuta la [prueba Python](../../backend/tests/test_ensayo_inversion.py) con las dependencias del fichero de bloqueo. Esta prueba llama a `GET /api/routes` en memoria con el grafo ficticio en lugar del leído de PostgreSQL. Solo envía origen, destino y, en los cierres y la vía supuesta, el escenario. Comprueba los resultados contra caminos escritos a mano. La [prueba TypeScript](../../frontend/e2e/inversion-enlace.spec.ts) recibe el mismo grafo y compara las rutas completas y ordenadas con la respuesta de la API. Comprueba además las alternativas disponibles y el texto de inversión que prepara `compararRecorridos`. El ensayo necesita los dos motores y funciona sin una base de datos ni un navegador instalado.

El mismo comando en el [commit de referencia 4992eeff](https://github.com/ebotiab/Oniel/commit/4992eeffd2d186a212bb5e614a8f2dd600293941) reproduce la columna «Antes» con los motores de `main`.

## Qué se midió

Los cinco nodos son Origen, Este, Parada, Oeste y Destino. Origen–Este mide 85,702 km y Oeste–Destino, 91,699 km. Entre las agujas Este y Oeste se puede tomar el enlace de 1,011 km o los brazos de 2,138 y 2,102 km que se encuentran en Parada. En cada aguja, el enlace y el brazo hacia el andén salen por el mismo lado. Las velocidades de prueba son 200 km/h en los accesos exteriores, 90 en los brazos y 50 en el enlace. Los minutos representan marcha sin tiempo de parada.

| Consulta, en ambos sentidos | Antes | Con la regla candidata |
| --- | --- | --- |
| Origen ↔ Destino, red abierta | Directo | 1.º directo, 178,4 km / 54 min · 2.º por Parada, 181,6 km / 56 min |
| Mismo viaje, enlace cerrado | Ninguna ruta | Por Parada, con inversión |
| Cierre de uno de los dos brazos, por separado | Directo | Directo |
| Parada pasa a ser una bifurcación de dos brazos del mismo lado, incluso con el permiso declarado | Directo · al cerrarlo, ninguna | Directo · al cerrarlo, ninguna |
| Estación sin permiso explícito | Directo · al cerrarlo, ninguna | Directo · al cerrarlo, ninguna |
| Solo se orienta el enlace con `link_towards` | Directo · al cerrarlo, por Parada | Directo · al cerrarlo, por Parada |
| Aguja ↔ Parada con su propio brazo cerrado (cada aguja por separado) | Ninguna ruta | Ninguna ruta |

Origen ↔ Parada y Parada ↔ Destino conservan la continuidad de su línea en ambos sentidos. La prueba candidata incluye 44 consultas. En todas rigen `max_ratio=2` y los cambios de línea sin tope.

## Regla candidata

1. En un triángulo ordinario de `link_of`, el enlace puede declarar `link_reversal_at`, el ID de la estación donde se unen los dos brazos. Solo allí se permite pasar de un brazo al otro y se anota la inversión en `reverse_node_ids`. El tren recorre cada brazo una vez. Los movimientos entre el enlace y el brazo del andén siguen prohibidos en ambas agujas.
2. El comparador recorta los tramos comunes. Si un recorrido usa únicamente el enlace en la parte distinta y el otro usa exclusivamente los brazos de ese mismo triángulo, sin repetir tramo y con la inversión declarada, aplica el mismo límite al viaje completo. En el ensayo la relación local es 4,240 / 1,011 ≈ 4,19 y la del viaje completo es 181,641 / 178,412 ≈ 1,018. El resto de comparaciones conserva el criterio local. La lista específica de rodeos de un cierre conserva también su criterio local.
3. Dos controles fuerzan los límites de la regla. Entre las propias agujas, la vuelta por Parada supera el doble incluso en el viaje completo y se descarta. Al añadir una vía supuesta de 0,5 km entre las mismas agujas, el filtro local descarta las dos opciones más largas frente a esa vía ajena al permiso.

## Qué necesitaría la carga real

La declaración debe identificar el enlace, la estación y el movimiento recíproco acreditado entre sus dos brazos. En este triángulo los brazos se deducen de las dos líneas y de la estación común. Para adoptarla habría que conservar la fuente y validar que el nodo sea una estación en el vértice correcto, con brazos identificables sin ambigüedad. El permiso llegaría desde la especificación al grafo del servidor y al índice que lee el visor.

Las dos agujas del ensayo reciben sus lados físicos como entrada. Para Conxo hay que acreditar esos lados localmente por las tangentes próximas a cada aguja, como describe el plan. La posibilidad de invertir es un dato de infraestructura. La atribución de una parada comercial o del enlace a un servicio concreto requiere la evidencia de itinerario y vigencia indicada en la #322.
