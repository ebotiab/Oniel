import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

import { escapar, htmlConMeta, META_COBERTURA, META_GLOSARIO, META_GUIA, META_RED, META_SIN_OTRO_CAMINO, SITIO, metaLinea, metaNodo, metaRecorridos, metaTramo, type Meta } from './src/app/meta.ts'
import { routePath } from './src/app/state.ts'

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

/** React sustituye este contenido al arrancar. Sin JavaScript, las fichas se pueden recorrer con enlaces normales. */
function lecturaInicial(meta: Meta, navegacion: string): string {
  return `<div class="inicio-estatico">
    <div class="app carga-inicial" hidden>
      <header class="cabecera">
        <a class="marca" href="/" aria-label="Oniel, ir al inicio">
          <svg class="marca-o" viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="10" cy="10" r="8.2" fill="var(--papel)" stroke="currentColor" stroke-width="3.4"/>
          </svg><span aria-hidden="true">niel</span>
        </a>
      </header>
      <div class="panel"><div class="panel-contenido">
        <p class="suave cargando" role="status">Cargando la red…</p>
      </div></div>
    </div>
    <main class="lectura-inicial"><h1>${escapar(meta.title)}</h1><p>${escapar(meta.description)}</p>${navegacion}</main>
  </div>`
}

/** Las mismas rutas públicas alimentan las páginas estáticas y el sitemap en cada compilación. */
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
        ['/', META_RED],
        ['/cobertura', META_COBERTURA],
        ['/glosario', META_GLOSARIO],
        ['/guia', META_GUIA],
        ['/sin-otro-camino', META_SIN_OTRO_CAMINO],
        ['/recorridos', metaRecorridos()],
      ])
      const enlaces = indice.lines.map((linea) => {
        const ruta = routePath({ selection: null, simulacion: false, linea: linea.id })
        paginas.set(ruta, metaLinea(linea))
        return `<li><a href="${escapar(ruta)}">${escapar(linea.name)}</a></li>`
      })
      for (const nodo of indice.nodes) {
        const ruta = routePath({ selection: { type: 'nodo', id: nodo.id }, simulacion: false })
        paginas.set(ruta, metaNodo(nodo))
      }
      for (const { id, properties: tramo } of indice.segment_features.features) {
        const ruta = routePath({ selection: { type: 'tramo', id }, simulacion: false })
        paginas.set(ruta, metaTramo(tramo, lineas.get(tramo.line_id)))
      }
      const lista = `<nav aria-label="Líneas, baipases y enlaces"><h2>Líneas, baipases y enlaces</h2><ul>${enlaces.join('\n')}</ul></nav>`
      for (const [ruta, meta] of paginas) {
        const fichero = join(salida, ruta === '/' ? 'index.html' : `${ruta}.html`)
        const contenido = lecturaInicial(meta, ruta === '/' ? lista : '<a href="/">Volver al mapa de la red</a>')
        const pagina = htmlConMeta(html, meta, ruta).replace('<div id="root"></div>', () => `<div id="root">${contenido}</div>`)
        mkdirSync(dirname(fichero), { recursive: true })
        writeFileSync(fichero, pagina)
      }

      const urls = Array.from(paginas.keys(), (ruta) => `  <url><loc>${escapar(SITIO + ruta)}</loc></url>`)
      writeFileSync(join(salida, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>\n`)
      writeFileSync(join(salida, 'robots.txt'), `User-agent: *\nAllow: /\n\nSitemap: ${SITIO}/sitemap.xml\n`)
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
