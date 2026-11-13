-- Cada conexión a trazos recuerda qué línea la declara en su especificación.
--
-- Al reimportar una línea se borran sus conexiones y se vuelven a crear las que declara. Hasta
-- ahora «sus conexiones» eran las de sus nodos propios, y una conexión retirada de la
-- especificación se quedaba en la base si colgaba de un nodo compartido con otra línea (la que
-- anunciaba el camino de Levante desde la bifurcación de Torrejón de Velasco, al cargarse la
-- línea de Valencia). Las filas anteriores a esta migración no tienen dueño: la primera
-- reimportación de cada línea las sustituye.
ALTER TABLE connections ADD COLUMN declared_by TEXT REFERENCES lines(id) ON DELETE CASCADE;
