-- Un operador cuyos trenes se cargan de una compilación que no publica él ('no_oficial'): sus
-- horarios están, pero la fuente no es oficial y el visor lo dice.
ALTER TABLE operators DROP CONSTRAINT IF EXISTS operators_timetable_check;
ALTER TABLE operators
    ADD CONSTRAINT operators_timetable_check
    CHECK (timetable IN ('cargado', 'no_publicado', 'no_oficial'));
