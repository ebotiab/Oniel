// El título y la descripción de cada vista: lo que dice la pestaña del navegador y lo que enseña la
// tarjeta de un enlace compartido (Open Graph). Son funciones sin dependencias del navegador ni del
// resto del visor, porque las usan dos sitios: el visor, que las aplica al navegar (`aplicarMeta.ts`), y
// la compilación, que escribe con ellas una página estática por vista principal (`vite.config.ts`)
// para los rastreadores que no ejecutan JavaScript.

/** La dirección pública de Oniel: las etiquetas de un enlace compartido necesitan direcciones completas. */
export const SITIO = 'https://oniel.vercel.app'

export interface Meta {
  title: string
  description: string
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

/** «2026-11-20» → «20 de noviembre de 2026», sin depender de la configuración regional de quien compila. */
export function fechaLarga(iso: string): string {
  const [anio, mes, dia] = iso.split('-').map(Number)
  return `${dia} de ${MESES[(mes ?? 1) - 1]} de ${anio}`
}

const km = (n: number) => n.toFixed(1).replace('.', ',')
const minuscula = (texto: string) => texto.charAt(0).toLowerCase() + texto.slice(1)
const titulo = (vista: string) => `${vista} · Oniel`

/** La vista de la red, y lo que ve quien abre una dirección que el visor no conoce. */
export const META_RED: Meta = {
  title: 'Oniel · Cómo está conectada la red ferroviaria',
  description:
    'Mapa de la red ferroviaria española para recorrerla línea a línea: estaciones, tramos y los trenes que pasan por cada uno, con las fuentes y la fecha de cada dato.',
}

export const META_COBERTURA: Meta = {
  title: titulo('Cobertura y fuentes'),
  description: 'Qué líneas y qué horarios hay cargados en Oniel, de qué fecha son, de dónde sale cada dato y con qué licencia, y cómo citar Oniel.',
}

export const META_SIN_OTRO_CAMINO: Meta = {
  title: titulo('Tramos sin otro camino'),
  description: 'Los tramos de la red ferroviaria española cuyos trenes no tendrían otro camino por vía si se cortaran, línea a línea y con los trenes de un día.',
}

export const META_GUIA: Meta = {
  title: titulo('Guía del atlas'),
  description: 'Cómo utilizar Oniel para entender la red ferroviaria española. Explora una línea de ejemplo, sus estaciones y sus tramos, y compara dos recorridos en el mapa.',
}

export const META_GLOSARIO: Meta = {
  title: titulo('Glosario'),
  description: 'Las palabras del ferrocarril explicadas para quien no las conoce: ancho de vía, bloqueo, vía única, bifurcación y las demás que usa Oniel.',
}

export function metaEntradaGlosario(nombre: string): Meta {
  return { title: titulo(`${nombre} · Glosario`), description: `Qué significa «${minuscula(nombre)}» en el ferrocarril, explicado para quien no lo conoce.` }
}

export function metaLinea(linea: { name: string; length_km: number }): Meta {
  return {
    title: titulo(linea.name),
    description: `${linea.name}: ${km(linea.length_km)} km en el mapa, con sus estaciones, sus tramos y los trenes que pasan por cada uno.`,
  }
}

export function metaNodo(nodo: { name: string }): Meta {
  return {
    title: titulo(nodo.name),
    description: `${nodo.name} en la red ferroviaria española: en qué líneas está, qué trenes pasan y qué tramos salen de aquí.`,
  }
}

interface Tramo {
  from_name: string
  to_name: string
  length_km: number
}

export function metaTramo(tramo: Tramo, linea?: { name: string } | null): Meta {
  const donde = linea ? ` de la ${minuscula(linea.name)}` : ''
  return {
    title: titulo(`Tramo ${tramo.from_name} – ${tramo.to_name}`),
    description: `Tramo ${tramo.from_name} – ${tramo.to_name}${donde}: ${km(tramo.length_km)} km. Cuántos trenes lo recorren y si tendrían otro camino.`,
  }
}

/** El día y la franja de un cierre simulado, como van en la URL. */
export interface Franja {
  date: string
  start: string
  end: string
}

export function metaSimulacion(tramo: Tramo, franja?: Franja | null): Meta {
  const cuando = franja ? ` el ${fechaLarga(franja.date)}, de ${franja.start} a ${franja.end}` : ' un día y a unas horas'
  return {
    title: titulo(`Cierre hipotético de ${tramo.from_name} – ${tramo.to_name}`),
    description: `Qué trenes se verían afectados si el tramo ${tramo.from_name} – ${tramo.to_name} se cerrara${cuando}. Es una simulación, no un aviso.`,
  }
}

export function metaRecorridos(desde?: string | null, hasta?: string | null): Meta {
  if (!desde || !hasta)
    return {
      title: titulo('Comparar recorridos'),
      description: 'Elige dos estaciones y compara los recorridos por vía que las unen: kilómetros, líneas por las que pasan y un tiempo estimado sin paradas.',
    }
  return {
    title: titulo(`Recorridos de ${desde} a ${hasta}`),
    description: `Los recorridos por vía de ${desde} a ${hasta}: kilómetros, líneas por las que pasan y un tiempo estimado sin paradas, que no es el de ningún tren.`,
  }
}

export function metaProyecto(nombre: string): Meta {
  return { title: titulo(nombre), description: `${nombre}: qué es, en qué estado está y según qué fuente, sobre el mapa de la red ferroviaria española.` }
}

export const escapar = (texto: string) => texto.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/**
 * El index.html compilado con el título y la descripción de una vista, para escribirlo como página
 * estática. Cambia las mismas etiquetas que `aplicarMeta` (`aplicarMeta.ts`); el resto del fichero queda igual, así que
 * la página carga el mismo visor.
 */
export function htmlConMeta(html: string, meta: Meta, ruta: string): string {
  const url = SITIO + ruta
  const contenido = (etiqueta: RegExp, valor: string) => {
    html = html.replace(etiqueta, (_todo, antes: string, despues: string) => `${antes}${escapar(valor)}${despues}`)
  }
  contenido(/(<title>)[^<]*(<\/title>)/, meta.title)
  contenido(/(<meta name="description" content=")[^"]*(")/, meta.description)
  contenido(/(<meta property="og:title" content=")[^"]*(")/, meta.title)
  contenido(/(<meta property="og:description" content=")[^"]*(")/, meta.description)
  contenido(/(<meta property="og:url" content=")[^"]*(")/, url)
  contenido(/(<meta name="twitter:title" content=")[^"]*(")/, meta.title)
  contenido(/(<meta name="twitter:description" content=")[^"]*(")/, meta.description)
  contenido(/(<link rel="canonical" href=")[^"]*(")/, url)
  return html
}
