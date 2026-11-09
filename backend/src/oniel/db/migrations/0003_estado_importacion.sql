-- Estado de la importación: la huella de la última `import all` (commit desplegado o hash de datos
-- y código) para que `import all --if-changed` pueda saltarse el trabajo cuando nada ha cambiado.
CREATE TABLE IF NOT EXISTS import_state (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
