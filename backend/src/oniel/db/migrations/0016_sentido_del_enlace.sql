-- Primer nodo de la línea principal por el que continúa un acceso desde una terminal.
ALTER TABLE lines ADD COLUMN link_towards TEXT;
