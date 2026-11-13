import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// En desarrollo, /api se redirige al backend local (uv run uvicorn oniel.api.main:app --reload → :8000, o el puerto que uses).
const apiTarget = process.env.ONIEL_API_PROXY ?? 'http://127.0.0.1:8000'

/**
 * El mapa (MapLibre) se carga con un import() para que el panel no lo espere. Sin más, el navegador no
 * sabría que lo necesita hasta ejecutar el fichero principal; con estas etiquetas lo descarga desde el
 * primer momento, a la vez que el resto.
 */
function precargarMapa(): Plugin {
  return {
    name: 'oniel-precargar-mapa',
    transformIndexHtml(_html, ctx) {
      const chunks = Object.values(ctx.bundle ?? {})
      const mapa = chunks.find((c) => c.type === 'chunk' && c.isDynamicEntry && c.name === 'MapView')
      if (!mapa || mapa.type !== 'chunk') return []
      const css = [...(mapa.viteMetadata?.importedCss ?? [])]
      return [
        { tag: 'link', attrs: { rel: 'modulepreload', crossorigin: true, href: `/${mapa.fileName}` }, injectTo: 'head' },
        ...css.map((href) => ({ tag: 'link', attrs: { rel: 'preload', as: 'style', crossorigin: true, href: `/${href}` }, injectTo: 'head' as const })),
      ]
    },
  }
}

export default defineConfig({
  plugins: [react(), precargarMapa()],
  // MapLibre carga su worker como módulo propio; si Vite lo preempaqueta, la URL del worker deja de ser válida.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/healthz': { target: apiTarget, changeOrigin: true },
    },
  },
  // Vercel da el entorno del despliegue y el commit al compilar; el visor los usa para decidir si
  // envía sus errores a Logfire y con qué versión (src/telemetria/arranque.ts). Fuera de Vercel quedan vacíos.
  define: {
    'import.meta.env.VITE_ENTORNO': JSON.stringify(process.env.VERCEL_ENV ?? ''),
    'import.meta.env.VITE_COMMIT': JSON.stringify(process.env.VERCEL_GIT_COMMIT_SHA ?? ''),
  },
  build: { sourcemap: false, chunkSizeWarningLimit: 1500 },
})
