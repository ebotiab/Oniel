-- Zonas en las que el visor agrupa las líneas (Andalucía, Cataluña…). Es una clasificación propia de
-- Oniel, no un dato con fuente: el registro está en data/curated/zonas.json y cada línea declara la suya.
CREATE TABLE zones (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    cities     TEXT[] NOT NULL DEFAULT '{}'
);

ALTER TABLE lines ADD COLUMN zone_id TEXT REFERENCES zones(id);
