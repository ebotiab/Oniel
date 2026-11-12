-- Anotaciones de red: todo lo que pasa sobre la red entre dos fechas según una fuente, curado a
-- mano en data/curated/anotaciones.json. Las interrupciones del servicio son el primer tipo; la
-- tabla interruptions pasa aquí y se retira.
-- El tipo (kind) y sus estados válidos se declaran en el código (oniel.domain.annotations) y los
-- comprueba la importación, de modo que un tipo nuevo no necesita migración.
-- El alcance es uno de tres: de un nodo a otro de la misma línea (los tramos afectados no se
-- guardan: se deducen del orden de esos nodos en line_nodes, y así reimportar la red no las deja
-- huérfanas), un nodo, o una geometría GeoJSON propia para lo que no cuelga de la red cargada.
-- ended_on es el día en que termina: la anotación está vigente los días start_date <= día <
-- ended_on, o sin límite mientras ended_on sea nulo.
CREATE TABLE annotations (
    id                TEXT PRIMARY KEY,
    kind              TEXT NOT NULL,
    status            TEXT NOT NULL,
    line_id           TEXT REFERENCES lines(id) ON DELETE CASCADE,
    from_node_id      TEXT REFERENCES nodes(id),
    to_node_id        TEXT REFERENCES nodes(id),
    node_id           TEXT REFERENCES nodes(id),
    geometry          JSONB,
    start_date        DATE,
    expected_end_date DATE,
    expected_end_text TEXT,
    ended_on          DATE,
    title             TEXT,
    reason            TEXT,
    note              TEXT,
    source_ids        TEXT[] NOT NULL CHECK (cardinality(source_ids) >= 1),
    checked_on        DATE NOT NULL,
    CHECK (
        (line_id IS NOT NULL AND from_node_id IS NOT NULL AND to_node_id IS NOT NULL
            AND from_node_id <> to_node_id AND node_id IS NULL AND geometry IS NULL)
        OR (node_id IS NOT NULL AND line_id IS NULL AND from_node_id IS NULL
            AND to_node_id IS NULL AND geometry IS NULL)
        OR (geometry IS NOT NULL AND line_id IS NULL AND from_node_id IS NULL
            AND to_node_id IS NULL AND node_id IS NULL)
    ),
    CHECK (title IS NOT NULL OR reason IS NOT NULL),
    CHECK (expected_end_date IS NULL OR start_date IS NULL OR expected_end_date >= start_date),
    CHECK (ended_on IS NULL OR ((start_date IS NULL OR ended_on >= start_date) AND ended_on <= checked_on))
);
CREATE INDEX annotations_kind_idx ON annotations (kind);
CREATE INDEX annotations_line_idx ON annotations (line_id);

INSERT INTO annotations (id, kind, status, line_id, from_node_id, to_node_id, start_date,
    expected_end_date, expected_end_text, ended_on, reason, note, source_ids, checked_on)
SELECT id, 'interrupcion', CASE WHEN ended_on IS NULL THEN 'vigente' ELSE 'terminada' END,
    line_id, from_node_id, to_node_id, start_date, expected_end_date, expected_end_text, ended_on,
    reason, note, source_ids, checked_on
FROM interruptions;

DROP TABLE interruptions;
