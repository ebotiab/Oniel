-- Varias líneas en el mismo visor: orden de presentación de las líneas y relevancia de los nodos.
-- Los nodos compartidos (una estación en dos líneas) ya cabían en el modelo (line_nodes);
-- aquí solo se añade lo que el visor necesita para dibujar más de una línea de forma legible.

ALTER TABLE lines ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 1;

ALTER TABLE nodes ADD COLUMN rank TEXT NOT NULL DEFAULT 'principal'
    CHECK (rank IN ('principal', 'secundario'));
