export function Legend({ closed }: { closed: boolean }) {
  return (
    <div className="leyenda" aria-label="Leyenda">
      <span className="muestra via" aria-hidden="true" />
      <span>Tramo disponible en Oniel</span>
      <span className="muestra conexion" aria-hidden="true" />
      <span>Conexión no cargada todavía</span>
      <span className="muestra seleccion" aria-hidden="true" />
      <span>Tramo seleccionado</span>
      {closed && (
        <>
          <span className="muestra cierre" aria-hidden="true" />
          <span>Cierre simulado</span>
        </>
      )}
    </div>
  )
}
