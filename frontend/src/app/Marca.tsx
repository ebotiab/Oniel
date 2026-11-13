import { abreAparte, navegar } from './navegacion'

/**
 * La marca de la cabecera: la O es el círculo de una estación, y la vía le llega desde el borde de la página
 * (la dibuja la hoja de estilos). Es un enlace a la portada (`/`, la vista de la red) que no recarga la página;
 * el clic que pide abrirla aparte se deja al navegador.
 */
export function Marca() {
  return (
    <a
      className="marca"
      href="/"
      aria-label="Oniel, ir al inicio"
      data-testid="marca"
      onClick={(e) => {
        if (abreAparte(e)) return
        e.preventDefault()
        navegar('/')
      }}
    >
      <svg className="marca-o" viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="10" cy="10" r="8.2" fill="var(--papel)" stroke="currentColor" strokeWidth="3.4" />
      </svg>
      <span aria-hidden="true">niel</span>
    </a>
  )
}
