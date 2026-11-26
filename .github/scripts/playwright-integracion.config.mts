import { fileURLToPath } from 'node:url'

import base from '../../frontend/playwright.config.ts'

// Hereda dispositivos, plazos y diagnóstico. Solo necesita Vite: no compila el servidor de telemetría.
export default {
  ...base,
  testDir: '../../frontend/e2e',
  outputDir: '../../frontend/test-results',
  grep: /@api/,
  forbidOnly: true,
  workers: 2,
  globalTimeout: 300_000,
  webServer: [{
    ...(Array.isArray(base.webServer) ? base.webServer[0] : base.webServer),
    cwd: fileURLToPath(new URL('../../frontend', import.meta.url)),
  }],
}
