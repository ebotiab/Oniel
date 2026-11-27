-- La estación donde se puede invertir entre los brazos de un enlace concreto.
ALTER TABLE lines ADD COLUMN link_reversal_at TEXT;

-- El GTFS da el calendario de la oferta. La fuente del itinerario acredita un día de ese
-- calendario. Una línea candidata sin fuente conserva el servicio y sus paradas comerciales.
ALTER TABLE service_dates
    ADD COLUMN itinerary_line_id TEXT REFERENCES lines(id),
    ADD COLUMN itinerary_source_id TEXT REFERENCES sources(id),
    ADD CHECK (itinerary_source_id IS NULL OR itinerary_line_id IS NOT NULL);

-- Un paso del enlace solo se enseña el día acreditado. Los tramos compartidos y los servicios
-- anteriores a esta migración conservan todos los días de su calendario.
CREATE VIEW dated_segment_passes AS
SELECT p.*, d.service_date, d.itinerary_line_id, d.itinerary_source_id
FROM service_segment_passes p
JOIN service_dates d USING (dataset_id, service_id)
JOIN segments t ON t.id = p.segment_id
WHERE d.itinerary_line_id IS DISTINCT FROM t.line_id OR d.itinerary_source_id IS NOT NULL;
