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

La cobertura contra los orígenes del inventario de migración se incorporará cuando esos orígenes
existan; este entrypoint solo establece desde ahora el mecanismo de descubrimiento cerrado.
