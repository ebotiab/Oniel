// Comprueba las hojas de estilo del visor después de compilar. Lo ejecuta `npm run build`, así que
// lo pasan el CI y el despliegue de Vercel: una hoja rota no llega a publicarse.
//
// Una llave sin cerrar no es un error para el navegador ni para Vite: la regla se cierra sola al
// final del fichero y todo lo que venía detrás queda anidado dentro de ella. En desarrollo cada hoja
// se carga aparte y apenas se nota; al compilar van todas en un fichero, y las reglas de base
// (`:root`, `body`) dejan de aplicarse. Las pruebas Playwright corren contra el servidor de
// desarrollo, de modo que no lo ven.

import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const raiz = join(import.meta.dirname, '..')

/** Las hojas propias del visor, que se editan a mano. */
const FUENTES = ['src/index.css', 'src/app/app.css']
/** Reglas de base que tienen que estar en el primer nivel de la hoja compilada. */
const DE_BASE = [':root', 'body']

/** El CSS sin comentarios ni cadenas, para que una llave dentro de ellos no cuente. */
function limpio(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g, '""')
}

/** Recorre las llaves: cuántas quedan abiertas al final, si sobra alguna y los selectores del primer nivel. */
function leer(css) {
  let nivel = 0
  let sobra = false
  let preludio = ''
  const selectores = new Set()
  for (const c of limpio(css)) {
    if (c === '{') {
      if (nivel === 0) for (const s of preludio.split(',')) selectores.add(s.trim())
      nivel += 1
      preludio = ''
    } else if (c === '}') {
      if (nivel === 0) sobra = true
      else nivel -= 1
      preludio = ''
    } else if (c === ';') preludio = ''
    else if (nivel === 0) preludio += c
  }
  return { abiertas: nivel, sobra, selectores }
}

const fallos = []

for (const fichero of FUENTES) {
  const { abiertas, sobra } = leer(readFileSync(join(raiz, fichero), 'utf8'))
  if (abiertas > 0) fallos.push(`${fichero}: ${abiertas === 1 ? 'queda una llave sin cerrar' : `quedan ${abiertas} llaves sin cerrar`}.`)
  if (sobra) fallos.push(`${fichero}: sobra una llave de cierre.`)
}

const assets = join(raiz, 'dist', 'assets')
let compiladas = []
try {
  compiladas = readdirSync(assets).filter((f) => /^index-.*\.css$/.test(f))
} catch {
  // sin dist/ no hay nada compilado: lo dice el fallo de abajo
}
if (compiladas.length === 0) fallos.push('dist/assets: no hay hoja de estilos compilada (index-*.css). Ejecuta antes `vite build`.')
for (const fichero of compiladas) {
  const { abiertas, sobra, selectores } = leer(readFileSync(join(assets, fichero), 'utf8'))
  if (abiertas > 0 || sobra) fallos.push(`dist/assets/${fichero}: las llaves no cuadran.`)
  for (const s of DE_BASE) {
    if (!selectores.has(s)) fallos.push(`dist/assets/${fichero}: la regla «${s}» no está en el primer nivel; ha quedado anidada dentro de otra o falta.`)
  }
}

if (fallos.length > 0) {
  console.error('Las hojas de estilo del visor no están bien formadas:')
  for (const f of fallos) console.error(`- ${f}`)
  process.exit(1)
}
console.log(`✓ hojas de estilo: llaves cerradas y reglas de base en su sitio (${[...FUENTES, ...compiladas.map((f) => `dist/assets/${f}`)].join(', ')})`)
