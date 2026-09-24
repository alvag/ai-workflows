# Suite durable

Ejecutar toda la suite:

```sh
python3 -m tests
```

Listar su inventario autocontenido:

```sh
python3 -m tests --listar
```

El runner descubre recursivamente cada archivo `test_*.py`. Cada módulo declara una lista `CASOS`
con tuplas `(id, grupo, función)`. El conjunto de funciones `test_*` debe coincidir exactamente con
el inventario del módulo: una función elegible omitida, un ID duplicado o una selección vacía ponen
la suite en rojo. `python3 -m tests --autotest` ejerce esos controles positivos.

El mismo descubrimiento valida la procedencia en tres direcciones: cada guarda e infraestructura
del inventario tiene al menos un test, cada par `matriz/caso` migrado conserva su test nominal y
ningún test carece de un origen reconocido. La procedencia vive en `tests/origenes.py`; no exige
igualdad entre conjuntos de distinta naturaleza.

El grupo `delivery-profile` cubre hoy **una sola** propiedad: la frontera estructural del parser
compartido del manifest (`delivery-profile:parser-boundary`). Las secuencias del perfil de entrega
que también cubría se retiraron junto con el perfil, y el nombre del grupo sobrevive porque es la
identidad con la que su caso entró al inventario.

La ejecución integrada vigente termina con `598 casos ok` y `574 casos node ok`.

La fidelidad entre schemas y vistas se verifica aparte con
`python3 scripts/verificar-vistas-config.py`. Su salida informa los conteos vigentes derivados
de los dueños, sin fijar otra copia de esos números aquí.
