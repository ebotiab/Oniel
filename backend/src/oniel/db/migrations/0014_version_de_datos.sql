-- Versión de los datos: un número que sube cada vez que una transacción escribe en alguna tabla
-- de la red o de los horarios. La API lo lee al empezar cada petición y guarda en memoria lo que
-- leyó de la base mientras no cambie (`oniel.repo.cache`): la red y los horarios solo cambian al
-- importar, y volver a leerlos en cada petición era lo que hacía lentas las rutas.
--
-- Lo sube un disparador por sentencia, no por fila, y una sola vez por transacción: una
-- importación entera es un incremento, visible para la API cuando la transacción termina, a la
-- vez que sus datos.
CREATE TABLE data_version (
    only_row   BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (only_row),
    version    BIGINT NOT NULL DEFAULT 0,
    -- Transacción que lo subió por última vez, para no volver a subirlo en la misma.
    changed_by BIGINT
);
INSERT INTO data_version DEFAULT VALUES;

CREATE FUNCTION bump_data_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE data_version SET version = version + 1, changed_by = txid_current()
    WHERE changed_by IS DISTINCT FROM txid_current();
    RETURN NULL;
END
$$;

-- Todas las tablas que la API lee. Quedan fuera las de estado (`schema_migrations`,
-- `import_state`, `import_runs`), que no salen en ninguna respuesta. Una tabla nueva tiene que
-- llevar su disparador en su migración: `tests/test_integration_db.py` falla si a alguna le falta.
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'sources', 'operators', 'zones', 'lines', 'line_operators', 'nodes', 'line_nodes',
        'segments', 'segment_attributes', 'connections', 'annotations', 'stop_mappings',
        'datasets', 'services', 'service_dates', 'service_stops', 'service_segment_passes'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER data_version_write AFTER INSERT OR UPDATE OR DELETE ON %I'
            ' FOR EACH STATEMENT EXECUTE FUNCTION bump_data_version()', t);
        EXECUTE format(
            'CREATE TRIGGER data_version_truncate AFTER TRUNCATE ON %I'
            ' FOR EACH STATEMENT EXECUTE FUNCTION bump_data_version()', t);
    END LOOP;
END
$$;
