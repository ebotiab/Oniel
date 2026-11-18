// La mitad de `meta.ts` que toca el documento: va aparte porque `meta.ts` también lo lee la compilación, sin navegador.

import { SITIO, type Meta } from './meta.ts'

/** Las etiquetas de index.html que cambian con la vista, con el atributo que las identifica. */
const ETIQUETAS: { selector: string; atributo: 'content' | 'href'; valor: (m: Meta, url: string) => string }[] = [
  { selector: 'meta[name="description"]', atributo: 'content', valor: (m) => m.description },
  { selector: 'meta[property="og:title"]', atributo: 'content', valor: (m) => m.title },
  { selector: 'meta[property="og:description"]', atributo: 'content', valor: (m) => m.description },
  { selector: 'meta[property="og:url"]', atributo: 'content', valor: (_m, url) => url },
  { selector: 'meta[name="twitter:title"]', atributo: 'content', valor: (m) => m.title },
  { selector: 'meta[name="twitter:description"]', atributo: 'content', valor: (m) => m.description },
  { selector: 'link[rel="canonical"]', atributo: 'href', valor: (_m, url) => url },
]

/** Pone el título y la descripción de la vista en el documento. `ruta` es la del visor (`routePath`). */
export function aplicarMeta(doc: Document, meta: Meta, ruta: string): void {
  doc.title = meta.title
  for (const e of ETIQUETAS) doc.head.querySelector(e.selector)?.setAttribute(e.atributo, e.valor(meta, SITIO + ruta))
}
