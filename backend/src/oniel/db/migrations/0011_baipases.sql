-- Un baipás es una línea corta que une dos nodos de otra por un camino que evita lo que hay entre
-- ellos (el de Zaragoza rodea Zaragoza-Delicias). Esta columna dice de qué línea lo es: el visor lo
-- cuelga de ella en la lista y el cálculo de recorridos lo trata como parte suya. No lleva clave
-- ajena para que el orden de importación no importe; `oniel-data validate` comprueba que la línea
-- existe y que los dos extremos del baipás son nodos suyos.
ALTER TABLE lines ADD COLUMN bypass_of TEXT;
