import { defineConfig, devices } from '@playwright/test'

// Pruebas de extremo a extremo del visor. Por defecto arrancan Vite contra la API local
// (ONIEL_API_PROXY, por defecto http://127.0.0.1:8000). Con ONIEL_E2E_STATIC=1 se prueba la
// instantánea estática sin servidor. ONIEL_E2E_PORT cambia el puerto cuando otra sesión ocupa el 5199.
//
// Cada prueba abre su propia página y no comparte estado con las demás, así que corren en paralelo
// también dentro de un mismo fichero (`fullyParallel`); eso deja además que `--shard` reparta por
// pruebas y no por ficheros, que son muy desiguales. En el CI la batería va en cuatro fragmentos
// (.github/workflows/ci.yml) y cada runner de GitHub tiene cuatro núcleos: un proceso por núcleo.
const port = Number(process.env.ONIEL_E2E_PORT ?? 5199)
const baseURL = `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  workers: process.env.CI ? 4 : undefined,
  retries: process.env.CI ? 1 : 0,
  // En el CI, `github` anota los fallos en la PR y `list` deja en el registro cada prueba con su
  // tiempo y, al final, las que solo pasaron al reintentar.
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
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
