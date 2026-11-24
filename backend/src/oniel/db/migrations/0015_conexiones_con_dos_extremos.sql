-- Una conexión a trazos puede unir dos nodos cargados.
--
-- Hasta ahora colgaba de un solo nodo (``node_id``) y, si llegaba a otro también cargado, en
-- ese otro no se veía: ni en su ficha ni en el esquema de su línea. ``to_node_id`` es ese otro
-- nodo y ``towards_back``, adónde lleva la conexión vista desde él (``towards`` lo dice visto
-- desde ``node_id``). No lleva clave ajena: el nodo puede ser de una línea que se importa después.
ALTER TABLE connections ADD COLUMN to_node_id TEXT;
ALTER TABLE connections ADD COLUMN towards_back TEXT;
