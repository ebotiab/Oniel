-- Conjuntos de datos fechados: cada fichero de horarios importado es una fila de datasets, con su
-- fuente, su operador, su SHA-256, el día en que se descargó y los días que cubre. Los servicios
-- cuelgan del conjunto, de modo que importar un fichero nuevo no borra el anterior y el mismo
-- trip_id puede existir en varios conjuntos.
--
-- Los servicios guardados hasta ahora no tenían conjunto y se derivan por completo de los ficheros
-- de data/raw: las cuatro tablas se rehacen vacías y la siguiente `import all` las vuelve a cargar
-- (el cambio de código cambia la huella, así que `--if-changed` no la salta).
CREATE TABLE datasets (
    id           TEXT PRIMARY KEY,
    source_id    TEXT NOT NULL REFERENCES sources(id),
    operator_id  TEXT REFERENCES operators(id),
    file         TEXT NOT NULL,
    sha256       TEXT NOT NULL UNIQUE,
    retrieved_on DATE NOT NULL,
    valid_from   DATE NOT NULL,
    valid_to     DATE NOT NULL,
    imported_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (valid_to >= valid_from)
);
CREATE INDEX datasets_source_idx ON datasets (source_id, retrieved_on);

DROP TABLE service_segment_passes;
DROP TABLE service_stops;
DROP TABLE service_dates;
DROP TABLE services;

CREATE TABLE services (
    dataset_id          TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    id                  TEXT NOT NULL,
    operator_id         TEXT NOT NULL REFERENCES operators(id),
    train_number        TEXT NOT NULL,
    product             TEXT NOT NULL,
    origin_stop_id      TEXT,
    origin_name         TEXT,
    destination_stop_id TEXT,
    destination_name    TEXT,
    valid_from          DATE NOT NULL,
    valid_to            DATE NOT NULL,
    gtfs_route_id       TEXT,
    gtfs_service_id     TEXT,
    resolution          TEXT NOT NULL CHECK (resolution IN ('completa', 'parcial')),
    import_run_id       INTEGER REFERENCES import_runs(id),
    PRIMARY KEY (dataset_id, id)
);
CREATE INDEX services_train_number_idx ON services (train_number);
CREATE INDEX services_id_idx ON services (id);

CREATE TABLE service_dates (
    dataset_id   TEXT NOT NULL,
    service_id   TEXT NOT NULL,
    service_date DATE NOT NULL,
    PRIMARY KEY (dataset_id, service_id, service_date),
    FOREIGN KEY (dataset_id, service_id) REFERENCES services(dataset_id, id) ON DELETE CASCADE
);
CREATE INDEX service_dates_date_idx ON service_dates (service_date, dataset_id);

CREATE TABLE service_stops (
    dataset_id    TEXT NOT NULL,
    service_id    TEXT NOT NULL,
    seq           INTEGER NOT NULL,
    stop_id       TEXT NOT NULL,
    stop_name     TEXT NOT NULL,
    arrival_s     INTEGER NOT NULL,
    departure_s   INTEGER NOT NULL,
    pickup_type   INTEGER,
    drop_off_type INTEGER,
    PRIMARY KEY (dataset_id, service_id, seq),
    FOREIGN KEY (dataset_id, service_id) REFERENCES services(dataset_id, id) ON DELETE CASCADE
);
CREATE INDEX service_stops_stop_idx ON service_stops (stop_id);

-- Paso de cada servicio por cada tramo, calculado en la importación con las reglas de oniel.sim.
CREATE TABLE service_segment_passes (
    dataset_id     TEXT NOT NULL,
    service_id     TEXT NOT NULL,
    segment_id     TEXT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL CHECK (kind IN ('publicado', 'estimado', 'indeterminado')),
    enter_s        NUMERIC(9, 1),
    exit_s         NUMERIC(9, 1),
    enter_margin_s NUMERIC(9, 1),
    exit_margin_s  NUMERIC(9, 1),
    km_increasing  BOOLEAN,
    basis          TEXT NOT NULL,
    PRIMARY KEY (dataset_id, service_id, segment_id),
    FOREIGN KEY (dataset_id, service_id) REFERENCES services(dataset_id, id) ON DELETE CASCADE
);
CREATE INDEX service_segment_passes_segment_idx ON service_segment_passes (segment_id);
