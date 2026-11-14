-- Un enlace es una vía corta que une un nodo de una línea con un nodo de otra (el de Monforte del
-- Cid une la línea de Murcia con la de Alicante). Esta columna dice de qué línea cuelga: el visor
-- lo lista bajo ella y el cálculo de recorridos lo cuenta como parte suya. A diferencia de un
-- baipás (`bypass_of`), elige sus trenes con su propio filtro. Tampoco lleva clave ajena;
-- `oniel-data validate` comprueba que la línea existe y que uno de los extremos es un nodo suyo.
ALTER TABLE lines ADD COLUMN link_of TEXT;
