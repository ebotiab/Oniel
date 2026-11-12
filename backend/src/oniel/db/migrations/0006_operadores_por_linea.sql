-- Qué operadores de trenes circulan por cada línea y si sus horarios están cargados. Un operador
-- que no publica sus horarios en un formato abierto se registra igualmente ('no_publicado'), para
-- poder decir en cada línea qué trenes faltan en los recuentos.
ALTER TABLE operators
    ADD COLUMN timetable TEXT CHECK (timetable IN ('cargado', 'no_publicado'));
UPDATE operators SET timetable = 'cargado' WHERE role = 'operador';

CREATE TABLE line_operators (
    line_id     TEXT NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    operator_id TEXT NOT NULL REFERENCES operators(id),
    PRIMARY KEY (line_id, operator_id)
);
INSERT INTO line_operators (line_id, operator_id)
SELECT l.id, o.id FROM lines l CROSS JOIN operators o WHERE o.role = 'operador';
