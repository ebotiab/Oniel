# Comprueba los procedimientos versionados desde un clon limpio y también en un equipo con extensiones locales.
require "yaml"

abort "CLAUDE.md debe enlazar la guía común AGENTS.md" unless File.identical?("CLAUDE.md", "AGENTS.md")

ficheros = IO.popen(["git", "ls-files", "-z", "--", ".claude/skills/*/SKILL.md"], &:read).split("\0")
abort "Faltan los procedimientos del proyecto" if ficheros.empty?
ficheros.each do |fichero|
  nombre = File.basename(File.dirname(fichero))
  enlace = File.join(".agents/skills", nombre)
  abort "Falta el enlace de Codex para #{nombre}" unless File.identical?(File.join(enlace, "SKILL.md"), fichero)
  cabecera = File.read(fichero)[/\A---\r?\n(.*?)\r?\n---\s*$/m, 1]
  datos = cabecera && YAML.safe_load(cabecera)
  abort "Cabecera incorrecta en #{fichero}" unless datos.is_a?(Hash) && datos["name"] == nombre &&
    datos["description"].is_a?(String) && !datos["description"].strip.empty?
end
