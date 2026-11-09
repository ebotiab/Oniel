import { defineConfig, devices } from '@playwright/test'

// Pruebas de extremo a extremo del visor. Por defecto arrancan Vite contra la API local
// (ONIEL_API_PROXY, por defecto http://127.0.0.1:8000). Con ONIEL_E2E_STATIC=1 se prueba la
// instantánea estática sin servidor.
const port = 5199
const baseURL = `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL,
    locale: 'es-ES',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `npm run dev -- --port ${port} --strictPort --host 127.0.0.1`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      ONIEL_API_PROXY: process.env.ONIEL_API_PROXY ?? 'http://127.0.0.1:8000',
      VITE_DATA_MODE: process.env.ONIEL_E2E_STATIC ? 'estatico' : '',
      // El visor sondea /healthz hasta dos minutos y medio; en las pruebas basta con 20 s.
      VITE_API_WAKE_MS: '20000',
    },
  },
  projects: [
    { name: 'escritorio', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'movil', use: { ...devices['Pixel 7'] } },
  ],
})
