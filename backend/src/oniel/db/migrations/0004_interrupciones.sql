-- Interrupciones del servicio, curadas a mano en data/curated/interrupciones.json.
-- Cada una va de un nodo a otro de la misma línea; los tramos afectados no se guardan: se deducen
-- del orden de esos nodos en line_nodes, de modo que reimportar la red no las deja huérfanas.
-- ended_on es el día en que se reanudó la circulación: la interrupción está vigente los días
-- start_date <= día < ended_on, o desde start_date sin límite mientras ended_on sea nulo.
CREATE TABLE interruptions (
    id                TEXT PRIMARY KEY,
    line_id           TEXT NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    from_node_id      TEXT NOT NULL REFERENCES nodes(id),
    to_node_id        TEXT NOT NULL REFERENCES nodes(id),
    start_date        DATE NOT NULL,
    expected_end_date DATE,
    expected_end_text TEXT,
    ended_on          DATE,
    reason            TEXT NOT NULL,
    note              TEXT,
    source_ids        TEXT[] NOT NULL CHECK (cardinality(source_ids) >= 1),
    checked_on        DATE NOT NULL,
    CHECK (from_node_id <> to_node_id),
    CHECK (expected_end_date IS NULL OR expected_end_date >= start_date),
    CHECK (ended_on IS NULL OR (ended_on >= start_date AND ended_on <= checked_on))
);
CREATE INDEX interruptions_line_idx ON interruptions (line_id);
