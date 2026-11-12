-- Hitos fechados de una anotación de red (un estudio informativo, una licitación, un inicio de
-- obras), cada uno con la fuente que da su fecha: una lista de {date, text, source_id}. La fecha es
-- texto porque de muchos hitos solo se conoce el año o el mes.
ALTER TABLE annotations ADD COLUMN milestones JSONB NOT NULL DEFAULT '[]'::jsonb;
