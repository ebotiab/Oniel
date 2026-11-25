import { expect, test } from '@playwright/test'

import { todayIso } from '../src/app/state.ts'

test('el día de la red empieza a medianoche en Madrid en invierno y en verano', () => {
  expect(todayIso(new Date('2026-01-18T22:59:59.999Z'))).toBe('2026-01-18')
  expect(todayIso(new Date('2026-01-18T23:00:00.000Z'))).toBe('2026-01-19')
  expect(todayIso(new Date('2026-09-05T21:59:59.999Z'))).toBe('2026-09-05')
  expect(todayIso(new Date('2026-09-05T22:00:00.000Z'))).toBe('2026-09-06')
})

test('una ficha abierta señala la interrupción desde la medianoche peninsular', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-09-05T21:55:00Z') })
  await page.clock.pauseAt(new Date('2026-09-05T21:59:58Z'))
  await page.goto('/tramo/convencional-madrid-alcazar-cordoba:venta-de-cardenas:vilches')
  await expect(page.getByTestId('detalle-tramo')).toBeAttached()
  await expect(page.getByTestId('interrupcion')).toHaveCount(0)
  await page.clock.fastForward(2000)
  await expect(page.getByTestId('interrupcion')).toHaveCount(1)
})

test('la fecha de consulta se actualiza al recuperar la pestaña tras varios días', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-23T18:00:00Z') })
  await page.clock.pauseAt(new Date('2026-10-23T19:00:00Z'))
  await page.goto('/cobertura')
  const cita = page.getByTestId('citar-ejemplo')
  await expect(cita).toContainText('consultado el 23 de octubre de 2026')
  // El reloj del sistema avanza sin ejecutar temporizadores mientras la pestaña está suspendida.
  await page.clock.setSystemTime(new Date('2026-10-25T23:05:00Z'))
  await page.locator('html').dispatchEvent('visibilitychange', { bubbles: true })
  await expect(cita).toContainText('consultado el 26 de octubre de 2026')
})
