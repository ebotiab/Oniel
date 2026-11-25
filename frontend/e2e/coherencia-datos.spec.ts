import { expect, test } from '@playwright/test'

import { indice } from './instantanea.ts'

test('la instantánea mantiene máximas, longitudes y fuentes coherentes en toda la red', () => {
  for (const line of indice.lines) {
    const segments = indice.segment_features.features.map((f) => ({ id: String(f.id), ...f.properties })).filter((s) => s.line_id === line.id)
    const speeds = segments.flatMap((s) => s.max_speed_kmh === null ? [] : [s.max_speed_kmh])
    expect(line.max_speed_kmh, line.id).toBe(speeds.length ? Math.max(...speeds) : null)
    // Cada tramo se redondea a metros al exportarlo.
    expect(Math.abs(line.length_km - segments.reduce((sum, s) => sum + s.length_km, 0)), line.id).toBeLessThan(segments.length * 0.001)
    for (const segment of segments) {
      expect(segment.attributes?.tracks.source_id, segment.id).toBeTruthy()
      expect(segment.attributes?.tracks.checked_on, segment.id).toMatch(/^\d{4}-\d{2}-\d{2}$/)
      const power = segment.attributes?.electrification?.value ?? line.electrification
      if (power !== null) expect(['Sin electrificar', '3 kV CC', '25 kV 50 Hz'], segment.id).toContain(power)
    }
  }
})

for (const caso of [
  { line: 'lav-madrid-barcelona', segment: 'guadalajara-yebes:las-inviernas', speed: 300, power: '25 kV 50 Hz' },
  { line: 'burgos-miranda-vitoria', segment: 'burgos-rosa-manzano:briviesca', speed: 160, power: '3 kV CC' },
]) {
  test(`${caso.line}: cabecera y tramo corregido con fuente oficial`, async ({ page }) => {
    await page.goto(`/linea/${caso.line}`)
    await expect(page.getByTestId('ficha-linea')).toContainText(`hasta ${caso.speed} km/h`)
    await page.goto(`/tramo/${caso.line}:${caso.segment}`)
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toContainText(`${caso.speed} km/h`)
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('tramo-atributo-electrification')).toHaveText(caso.power)
    const sources = page.getByTestId('atributos-fuente')
    await expect(sources).toContainText(/velocidad máxima/i)
    await expect(sources).toContainText('Vías')
    await expect(sources).toContainText('adif-declaracion-red-2026-mapas')
    await expect(sources).toContainText('25 de noviembre de 2026')
  })
}
