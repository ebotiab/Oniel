# Ejecuta las mismas condiciones que los checks obligatorios, inyectando resultados controlados.
require "yaml"
require "open3"

ci = YAML.load_file(".github/workflows/ci.yml", aliases: true)
jobs = ci.fetch("jobs")

def comprobar(condicion, mensaje)
  abort mensaje unless condicion
end

# Las tres salidas son independientes: tocar la API no repite la batería estática.
{
  "backend/src/oniel/api/main.py" => [true, false, true],
  "backend/uv.lock" => [true, false, true],
  "backend/data/raw/horarios.zip" => [true, true, true],
  "backend/src/oniel/export/snapshot.py" => [true, true, true],
  "frontend/src/data/api.ts" => [false, true, true],
  "frontend/e2e/rutas.spec.ts" => [false, true, true],
  "frontend/package-lock.json" => [false, true, true],
  "frontend/public/data/index.json" => [true, true, true],
  "frontend/e2e/fixtures/rutas-paridad.json" => [true, true, true],
  ".github/workflows/ci.yml" => [true, true, true],
  ".github/scripts/integracion-api.sh" => [true, true, true],
  "README.md" => [false, false, false],
  "docs/diseno.md" => [false, false, false],
  "AGENTS.md" => [true, false, false],
  "docs/datos.md" => [true, false, false],
  "" => [true, true, true],
}.each do |ruta, valores|
  salida, estado = Open3.capture2("bash", ".github/scripts/que-cambia.sh", stdin_data: "#{ruta}\n")
  esperado = %w[backend frontend integracion].zip(valores).map { |nombre, valor| "#{nombre}=#{valor}\n" }.join
  comprobar(estado.success? && salida == esperado, "Selección incorrecta para #{ruta.inspect}: #{salida}")
end

%w[backend frontend].each do |nombre|
  job = jobs.fetch(nombre)
  comprobar(job.fetch("needs").include?("integracion-api"), "#{nombre} debe esperar a la integración")
  comprobar(job.fetch("if") == "always()", "#{nombre} debe comprobar también fallos y cancelaciones")
  paso = job.fetch("steps").first
  env = paso.fetch("env")
  comprobar(env.fetch("INTEGRACION_APLICA") == '${{ needs.cambios.outputs.integracion }}', "Falta la selección de integración")
  comprobar(env.fetch("INTEGRACION_RESULTADO") == '${{ needs.integracion-api.result }}', "Falta el resultado real de integración")
  # failure incluye errores de importación y del servicio PostgreSQL; skipped puede ser una
  # preparación que impide arrancar el trabajo. Ninguno permite aprobar una PR pertinente.
  %w[success failure cancelled skipped].each do |resultado|
    %w[true false].each do |aplica|
      %w[true false].each do |mitad|
        salida, estado = Open3.capture2e({
          "CAMBIOS" => "success", "APLICA" => mitad,
          "RESULTADOS" => mitad == "true" ? "success" : "skipped",
          "INTEGRACION_APLICA" => aplica, "INTEGRACION_RESULTADO" => resultado,
        }, "bash", "-euo", "pipefail", "-c", paso.fetch("run"))
        permitido = (aplica == "true" && resultado == "success") || (aplica == "false" && resultado == "skipped")
        comprobar(estado.success? == permitido, "#{nombre}: aplica=#{aplica}, resultado=#{resultado}: #{salida}")
      end
    end
  end
  ["failure", "cancelled", "skipped"].each do |preparacion|
    _, estado = Open3.capture2e({"CAMBIOS" => preparacion, "APLICA" => "", "RESULTADOS" => "skipped",
      "INTEGRACION_APLICA" => "", "INTEGRACION_RESULTADO" => "skipped"}, "bash", "-euo", "pipefail", "-c", paso.fetch("run"))
    comprobar(!estado.success?, "#{nombre} aprobó una preparación #{preparacion}")
  end
  puts "#{job.fetch('name')}: bloquea fallo, cancelación, omisión indebida y preparación fallida."
end
puts "Selección de rutas y checks obligatorios comprobados."
