-- Esquema inicial de Oniel. Pensado para añadir líneas, operadores y modos sin rehacer nada:
-- las líneas tienen modo y administrador, los nodos son independientes de la línea y los
-- servicios se refieren a paradas GTFS que se resuelven contra la red mediante stop_mappings.

CREATE TABLE sources (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    publisher       TEXT NOT NULL,
    url             TEXT,
    license         TEXT,
    license_url     TEXT,
    retrieved_on    DATE,
    coverage        TEXT,
    notes           TEXT,
    checksum_sha256 TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE operators (
    id        TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    role      TEXT NOT NULL CHECK (role IN ('operador', 'administrador_infraestructura')),
    source_id TEXT REFERENCES sources(id)
);

CREATE TABLE lines (
    id                         TEXT PRIMARY KEY,
    name                       TEXT NOT NULL,
    short_name                 TEXT,
    mode                       TEXT NOT NULL DEFAULT 'ferrocarril',
    infrastructure_manager_id  TEXT REFERENCES operators(id),
    gauge_mm                   INTEGER,
    electrification            TEXT,
    max_speed_kmh              INTEGER,
    opened_on                  DATE,
    length_km                  NUMERIC(8, 3) NOT NULL,
    reference_length_km        NUMERIC(8, 3),
    status                     TEXT NOT NULL CHECK (status IN ('disponible', 'prevista')),
    description                TEXT,
    geometry                   JSONB NOT NULL,
    source_id                  TEXT REFERENCES sources(id),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE nodes (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('estacion', 'paet', 'pb', 'bifurcacion', 'cambiador', 'referencia')),
    lon         DOUBLE PRECISION NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    adif_code   TEXT,
    description TEXT,
    details     JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_id   TEXT REFERENCES sources(id)
);

CREATE TABLE line_nodes (
    line_id          TEXT NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    node_id          TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    seq              INTEGER NOT NULL,
    km               NUMERIC(8, 3) NOT NULL,
    reference_pk_km  NUMERIC(8, 3),
    PRIMARY KEY (line_id, node_id),
    UNIQUE (line_id, seq)
);

CREATE TABLE segments (
    id                TEXT PRIMARY KEY,
    line_id           TEXT NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    seq               INTEGER NOT NULL,
    from_node_id      TEXT NOT NULL REFERENCES nodes(id),
    to_node_id        TEXT NOT NULL REFERENCES nodes(id),
    km_from           NUMERIC(8, 3) NOT NULL,
    km_to             NUMERIC(8, 3) NOT NULL,
    length_km         NUMERIC(8, 3) NOT NULL,
    max_speed_kmh     INTEGER,
    typical_speed_kmh INTEGER,
    tracks            INTEGER,
    status            TEXT NOT NULL CHECK (status IN ('disponible', 'prevista')),
    geometry          JSONB NOT NULL,
    source_id         TEXT REFERENCES sources(id),
    UNIQUE (line_id, seq)
);

-- Conexiones hacia partes de la red que todavía no están cargadas en Oniel.
CREATE TABLE connections (
    id        TEXT PRIMARY KEY,
    node_id   TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    towards   TEXT NOT NULL,
    status    TEXT NOT NULL CHECK (status IN ('no_cargada', 'disponible')),
    line_id   TEXT REFERENCES lines(id),
    geometry  JSONB
);

-- Paradas GTFS resueltas contra la red: o son un nodo, o salen/entran por un nodo de la línea.
CREATE TABLE stop_mappings (
    stop_id             TEXT PRIMARY KEY,
    stop_name           TEXT,
    lon                 DOUBLE PRECISION,
    lat                 DOUBLE PRECISION,
    node_id             TEXT REFERENCES nodes(id),
    exit_node_ids       TEXT[] NOT NULL DEFAULT '{}',
    source_id           TEXT REFERENCES sources(id)
);

CREATE TABLE import_runs (
    id           SERIAL PRIMARY KEY,
    command      TEXT NOT NULL,
    source_id    TEXT,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    status       TEXT NOT NULL,
    stats        JSONB NOT NULL DEFAULT '{}'::jsonb,
    feed_version TEXT
);

CREATE TABLE services (
    id                  TEXT PRIMARY KEY,
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
    source_id           TEXT REFERENCES sources(id),
    import_run_id       INTEGER REFERENCES import_runs(id),
    feed_version        TEXT
);
CREATE INDEX services_train_number_idx ON services (train_number);

CREATE TABLE service_dates (
    service_id   TEXT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    service_date DATE NOT NULL,
    PRIMARY KEY (service_id, service_date)
);
CREATE INDEX service_dates_date_idx ON service_dates (service_date);

CREATE TABLE service_stops (
    service_id    TEXT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    stop_id       TEXT NOT NULL,
    stop_name     TEXT NOT NULL,
    arrival_s     INTEGER NOT NULL,
    departure_s   INTEGER NOT NULL,
    pickup_type   INTEGER,
    drop_off_type INTEGER,
    PRIMARY KEY (service_id, seq)
);

-- Paso de cada servicio por cada tramo, calculado en la importación con las reglas de oniel.sim.
CREATE TABLE service_segment_passes (
    service_id     TEXT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    segment_id     TEXT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL CHECK (kind IN ('publicado', 'estimado', 'indeterminado')),
    enter_s        NUMERIC(9, 1),
    exit_s         NUMERIC(9, 1),
    enter_margin_s NUMERIC(9, 1),
    exit_margin_s  NUMERIC(9, 1),
    km_increasing  BOOLEAN,
    basis          TEXT NOT NULL,
    PRIMARY KEY (service_id, segment_id)
);
CREATE INDEX service_segment_passes_segment_idx ON service_segment_passes (segment_id);
