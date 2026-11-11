import { expect, test } from '@playwright/test'

// La API en Render duerme tras 15 minutos sin tráfico y tarda más de un minuto en despertar.
// El visor no debe esperar a /healthz: pinta la instantánea estática y cambia a la API cuando responde.
const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

test.describe('Arranque con el servidor dormido', () => {
  test.skip(estatico, 'en modo estático no se sondea el servidor')

  test('la red se pinta desde la instantánea mientras el servidor despierta', async ({ page }) => {
    const errores: string[] = []
    page.on('console', (m) => {
      if (m.type() === 'error') errores.push(m.text())
    })
    let despertar!: () => void
    const dormido = new Promise<void>((resolve) => {
      despertar = resolve
    })
    // Como el proxy de Render: retiene /healthz hasta que el servidor está listo.
    await page.route('**/healthz', async (route) => {
      await dormido
      await route.continue().catch(() => {}) // la petición retenida puede haberse cancelado ya
    })

    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible({ timeout: 5_000 })
    const cobertura = page.getByTestId('recuento-red')
    await expect(cobertura).toContainText('despertando el servidor')

    despertar()
    await expect(cobertura).not.toContainText('despertando el servidor')
    await expect(cobertura).not.toContainText('vista estática')
    expect(errores.filter((e) => e.includes('[oniel mapa]'))).toEqual([])
  })

  test('si el servidor no llega a responder, queda la vista estática', async ({ page }) => {
    await page.route('**/healthz', (route) => route.abort('connectionrefused'))
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible({ timeout: 5_000 })
    // un fallo rápido no basta para rendirse: se reintenta durante VITE_API_WAKE_MS (20 s en las pruebas)
    const cobertura = page.getByTestId('recuento-red')
    await expect(cobertura).toContainText('despertando el servidor')
    await expect(cobertura).toContainText('vista estática', { timeout: 30_000 })
  })
})
