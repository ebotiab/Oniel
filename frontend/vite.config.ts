import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

import { htmlConMeta, META_COBERTURA, META_GLOSARIO, META_SIN_OTRO_CAMINO, metaLinea, metaNodo, metaRecorridos, metaTramo, type Meta } from './src/app/meta.ts'

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

/** Lo que la compilación lee del índice de la instantánea para titular las páginas estáticas. */
interface IndiceDeLaRed {
  lines: { id: string; name: string; length_km: number }[]
  nodes: { id: string; name: string }[]
  segment_features: { features: { id: string; properties: { line_id: string; from_name: string; to_name: string; length_km: number } }[] }
}

/**
 * Una página estática por vista principal, con su título, su descripción y sus etiquetas de enlace
 * compartido ya escritas. El visor es una sola página que pinta cada vista con JavaScript, y los
 * rastreadores de las redes sociales y de la mensajería no lo ejecutan: sin esto, cualquier enlace a
 * Oniel enseñaría la tarjeta de la portada. Cada página es el mismo index.html con otras etiquetas, en
 * `<ruta>/index.html`; Vercel sirve un fichero que existe antes de aplicar la regla que lo manda todo
 * a index.html (`vercel.json`), y el visor arranca igual. Las vistas que no caben en una lista (una
 * comparación entre dos estaciones, una simulación con su franja) siguen con la tarjeta común.
 */
function paginasEstaticas(): Plugin {
  let salida = 'dist'
  return {
    name: 'oniel-paginas-estaticas',
    apply: 'build',
    configResolved(config) {
      salida = config.build.outDir
    },
    closeBundle() {
      const html = readFileSync(join(salida, 'index.html'), 'utf-8')
      const indice = JSON.parse(readFileSync(new URL('./public/data/index.json', import.meta.url), 'utf-8')) as IndiceDeLaRed
      const lineas = new Map(indice.lines.map((l) => [l.id, l]))
      const paginas = new Map<string, Meta>([
        ['/cobertura', META_COBERTURA],
        ['/glosario', META_GLOSARIO],
        ['/sin-otro-camino', META_SIN_OTRO_CAMINO],
        ['/recorridos', metaRecorridos()],
      ])
      for (const l of indice.lines) paginas.set(`/linea/${l.id}`, metaLinea(l))
      for (const n of indice.nodes) paginas.set(`/nodo/${n.id}`, metaNodo(n))
      for (const { id, properties: t } of indice.segment_features.features) paginas.set(`/tramo/${id}`, metaTramo(t, lineas.get(t.line_id)))
      for (const [ruta, meta] of paginas) {
        const fichero = join(salida, ruta, 'index.html')
        mkdirSync(dirname(fichero), { recursive: true })
        writeFileSync(fichero, htmlConMeta(html, meta, ruta))
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), precargarMapa(), paginasEstaticas()],
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
