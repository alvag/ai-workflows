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

El grupo `delivery-profile` cubre el contrato compartido, las secuencias `standard`/`expedited`,
los cinco consumidores registrados, la frontera estructural única del parser, el fold multi-repo,
el rechazo pre-despacho y la estabilidad de los `description`. Sus escenarios enumeran gates de
artefactos y checkpoints cross-model por separado; no miden duración ni intentan demostrar ahorro.

La ejecución integrada vigente termina con `562 casos ok` y `512 casos node ok`.

La fidelidad entre schemas y vistas se verifica aparte con
`python3 scripts/verificar-vistas-config.py`: hoy compara 37 claves de config y 13 de manifest,
derivadas de 21 hojas menos 8 de estado de corrida.
