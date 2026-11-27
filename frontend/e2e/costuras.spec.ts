import { expect, test } from '@playwright/test'

import { indice } from './instantanea.ts'

// Las costuras entre líneas (#264): una conexión a trazos que une dos nodos cargados sale en la
// ficha de los dos, y en cada uno dice adónde lleva desde él; los nombres de las conexiones siguen
// un solo criterio; el texto de un nodo de varias líneas no habla desde una sola.

const conexiones = indice.connections
const deDosExtremos = conexiones.filter((c) => c.to_node_id)

test.describe('Conexiones a trazos entre dos nodos cargados', () => {
  test('la que llega a otro nodo cargado dice adónde lleva desde él, y ese nodo existe', () => {
    const nodos = new Set(indice.nodes.map((n) => n.id))
    expect(deDosExtremos.length).toBeGreaterThan(0)
    for (const c of deDosExtremos) {
      expect(nodos.has(c.to_node_id!), c.id).toBe(true)
      expect(c.towards_back, c.id).toBeTruthy()
      expect(c.to_node_id, c.id).not.toBe(c.node_id)
    }
    // las que solo tienen un extremo cargado no llevan texto de vuelta
    for (const c of conexiones.filter((c) => !c.to_node_id)) expect(c.towards_back ?? null, c.id).toBeNull()
  })

  test('su trazo acaba en el otro nodo', () => {
    const lugar = new Map(indice.nodes.map((n) => [n.id, [n.lon, n.lat]]))
    for (const c of deDosExtremos) {
      const trazo = indice.connection_features.features.find((f) => f.id === c.id)
      expect(trazo, c.id).toBeTruthy()
      const puntos = (trazo!.geometry as { coordinates: number[][] }).coordinates
      const [lon, lat] = lugar.get(c.to_node_id!)!
      const [x, y] = puntos[puntos.length - 1]
      // 0,004° son unos 400 m: el croquis acaba en el nodo, no cerca de otro
      expect(Math.abs(x - lon) + Math.abs(y - lat), c.id).toBeLessThan(0.004)
    }
  })

  test('los nombres siguen un solo criterio: raya con espacios y «Línea» con su tipo', () => {
    for (const c of conexiones) {
      expect(c.name, c.id).not.toMatch(/\S–|–\S/)
      if (c.name.startsWith('Línea ')) expect(c.name, c.id).toMatch(/^Línea (convencional|antigua|de alta velocidad) /)
    }
  })

  test('las dos bifurcaciones permiten abrir el tramo de la 014', async ({ page }) => {
    for (const [id, nombre] of [['bif-bobadilla', 'Bifurcación Bobadilla'], ['bif-gobantes', 'Bifurcación Gobantes']]) {
      await page.goto('/nodo/' + id)
      const ficha = page.getByTestId('detalle-nodo')
      await expect(ficha.getByRole('heading', { name: nombre })).toBeVisible()
      await ficha.getByRole('button', { name: 'Bifurcación Gobantes – Bifurcación Bobadilla' }).click()
      await expect(page).toHaveURL('/tramo/enlace-gobantes-bobadilla:bif-gobantes:bif-bobadilla')
      await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    }
  })

  test('Burgos dice por dónde llegan los regionales de Valladolid: la línea convencional, a trazos', async ({ page }) => {
    await page.goto('/nodo/burgos-rosa-manzano')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Burgos-Rosa Manzano' })).toBeVisible()
    await expect(ficha).toContainText('Línea convencional Valladolid – Venta de Baños – Burgos hacia Venta de Baños y Valladolid')
    await expect(ficha).not.toContainText('donde acaba esta línea')
  })

  test('Sevilla-Santa Justa no se presenta como el final de una línea: salen de ella otras dos', async ({ page }) => {
    await page.goto('/nodo/sevilla-santa-justa')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Sevilla-Santa Justa' })).toBeVisible()
    await expect(ficha).toContainText('de ella salen las líneas convencionales de Cádiz y de Huelva')
    await expect(ficha).not.toContainText('Final de la línea')
  })
})
