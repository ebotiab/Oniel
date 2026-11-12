-- Atributos de tramo: lo que cambia a lo largo de una línea (el número de vías hoy; señalización,
-- bloqueo o electrificación después), una fila por tramo y atributo en vez de una columna por
-- atributo. El valor es JSON (un número o un texto corto) y lleva la fuente que lo da y el día en
-- que se comprobó. Las filas las escribe la importación de la red, repartiendo las secciones de
-- la especificación de cada línea.
CREATE TABLE segment_attributes (
    segment_id  TEXT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    attribute   TEXT NOT NULL,
    value       JSONB NOT NULL,
    source_id   TEXT REFERENCES sources(id),
    checked_on  DATE,
    PRIMARY KEY (segment_id, attribute)
);

-- `segments.tracks` se conserva: el cálculo de recorridos y el mapa leen el número de vías de
-- cada tramo, y la importación lo escribe desde el atributo. Lo ya cargado pasa a la tabla nueva
-- para que la API responda igual hasta la siguiente importación.
INSERT INTO segment_attributes (segment_id, attribute, value)
SELECT id, 'tracks', to_jsonb(tracks) FROM segments WHERE tracks IS NOT NULL;
