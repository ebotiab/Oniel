// Reparto de rótulos a lo largo de un eje para que no se pisen.

/**
 * Coloca rótulos sobre un eje. Cada uno quiere estar en su ancla (`anchors`, en orden ascendente) y dos
 * consecutivos deben distar al menos `gaps[i]` (entre el i y el i+1). Devuelve las posiciones que cumplen
 * esas distancias moviendo lo mínimo: los rótulos holgados no se mueven y los apretados se reparten
 * centrados en torno a sus anclas, sin cambiar de orden.
 *
 * Minimiza la suma de los desplazamientos al cuadrado. Al restar a cada ancla las distancias mínimas
 * acumuladas, la condición pasa a ser «posiciones no decrecientes» y el problema es una regresión
 * isotónica, que resuelve de forma exacta el algoritmo de los violadores adyacentes (PAV).
 */
export function spreadLabels(anchors: readonly number[], gaps: readonly number[]): number[] {
  const n = anchors.length
  if (gaps.length !== Math.max(0, n - 1)) {
    throw new Error(`spreadLabels: ${n} anclas necesitan ${Math.max(0, n - 1)} distancias, no ${gaps.length}`)
  }
  for (let i = 1; i < n; i++) {
    if (anchors[i]! < anchors[i - 1]!) throw new Error('spreadLabels: las anclas deben ir en orden ascendente')
  }

  // Desplazamiento acumulado de las distancias mínimas: offset[i] = suma de gaps[0..i-1].
  const offsets: number[] = [0]
  for (let i = 1; i < n; i++) offsets.push(offsets[i - 1]! + gaps[i - 1]!)

  // PAV sobre las anclas corregidas: bloques de rótulos que se funden cuando el anterior quedaría por debajo.
  const blocks: { sum: number; count: number }[] = []
  for (let i = 0; i < n; i++) {
    let block = { sum: anchors[i]! - offsets[i]!, count: 1 }
    while (blocks.length > 0) {
      const prev = blocks[blocks.length - 1]!
      if (prev.sum / prev.count <= block.sum / block.count) break
      blocks.pop()
      block = { sum: prev.sum + block.sum, count: prev.count + block.count }
    }
    blocks.push(block)
  }

  const positions: number[] = []
  for (const block of blocks) {
    const mean = block.sum / block.count
    for (let k = 0; k < block.count; k++) positions.push(mean + offsets[positions.length]!)
  }
  return positions
}
