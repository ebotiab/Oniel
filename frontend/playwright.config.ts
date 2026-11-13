import { defineConfig, devices } from '@playwright/test'

// Pruebas de extremo a extremo del visor. Por defecto arrancan Vite contra la API local
// (ONIEL_API_PROXY, por defecto http://127.0.0.1:8000). Con ONIEL_E2E_STATIC=1 se prueba la
// instantánea estática sin servidor. ONIEL_E2E_PORT cambia el puerto cuando otra sesión ocupa el 5199.
//
// Cada prueba abre su propia página y no comparte estado con las demás, así que corren en paralelo
// también dentro de un mismo fichero (`fullyParallel`); eso deja además que `--shard` reparta por
// pruebas y no por ficheros, que son muy desiguales. En el CI la batería va en cuatro fragmentos
// (.github/workflows/ci.yml) y cada runner de GitHub tiene cuatro núcleos: un proceso por núcleo.
//
// En local el tope son dos procesos: suele haber varias sesiones probando a la vez en el mismo
// equipo y, con el valor por defecto de Playwright (la mitad de los núcleos cada una), se quitan
// la máquina unas a otras y todas tardan más. ONIEL_E2E_WORKERS lo cambia cuando se prueba a solas.
const localWorkers = Number(process.env.ONIEL_E2E_WORKERS ?? 2)
const port = Number(process.env.ONIEL_E2E_PORT ?? 5199)
const baseURL = `http://127.0.0.1:${port}`
// Un segundo servidor sirve el visor compilado como en producción y con un token de Logfire de
// mentira, para e2e/telemetria.spec.ts: el envío de errores solo existe en esa compilación. Va en el
// puerto siguiente; ONIEL_E2E_PORT_TELEMETRIA lo cambia si está ocupado.
const portTelemetria = Number(process.env.ONIEL_E2E_PORT_TELEMETRIA ?? port + 1)
// La prueba calcula esta misma dirección: si cambia aquí, cambia allí.
const URL_TELEMETRIA = `http://127.0.0.1:${portTelemetria}`
const dirTelemetria = 'node_modules/.cache/oniel-e2e-telemetria'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  workers: process.env.CI ? 4 : localWorkers,
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
  webServer: [
    {
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
    {
      command:
        `npx vite build --outDir ${dirTelemetria} --emptyOutDir --logLevel warn && ` +
        `npx vite preview --outDir ${dirTelemetria} --port ${portTelemetria} --strictPort --host 127.0.0.1`,
      url: URL_TELEMETRIA,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        // Lo que Vercel da al compilar producción, y un token que no existe: las pruebas responden
        // ellas mismas a lo que el visor envía y nada llega a Logfire.
        VERCEL_ENV: 'production',
        VERCEL_GIT_COMMIT_SHA: 'c0ffee0',
        VITE_LOGFIRE_TOKEN: 'token-de-prueba',
        VITE_DATA_MODE: 'estatico',
      },
    },
  ],
  projects: [
    { name: 'escritorio', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'movil', use: { ...devices['Pixel 7'] } },
  ],
})
