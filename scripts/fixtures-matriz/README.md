# Fixtures de la matriz de despachos

Corpus sintético de `scripts/verificar-matriz-despachos.py`. Ninguna de estas matrices describe el
árbol real: la matriz real es `scripts/matriz-despachos.json` y la puebla otra task. Estos archivos
existen para probar el schema **antes** de que exista lo que valida, que es lo que impide que el
verificador herede la interpretación de quien escribió los datos.

## Los conformes

Tres archivos, y cada uno cubre algo que los otros no. Los tres tienen que **pasar**: sin casos
positivos, un validador que rechace toda entrada satisface todos los mutantes y su autotest cierra en
verde sin haber aceptado jamás una matriz válida.

| Archivo | Qué ejerce |
|---|---|
| `conforme-minimo.json` | la forma mínima —un punto, un trabajo delegado, un intento— y la **ausencia legítima de sede**, que es la variante que más se parece a un defecto sin serlo |
| `conforme-multiplicidad.json` | los valores **simultáneos**: dos trabajos delegados con familias distintas, transportes distintos entre intentos y la derivación del transporte agregado a `mixto` |
| `conforme-operaciones.json` | el vocabulario operacional que a los otros dos no les toca: la sede estructurada en `json`, el colapso `unico_si_iguales`, los seis operadores de condición y los conectores `o` y `no` |

Entre los tres instancian **todas** las definiciones del schema y ejercen **valor a valor** los
vocabularios operacionales. No es cortesía: una operación declarada y nunca ejercida está tan sin
probar como una que no existe, y el autotest se pone rojo si alguna queda sin ejercer.

## Los mutantes no están acá, y es a propósito

`--autotest-schema` **genera** un mutante por cada elemento del inventario que el schema declara
—cada campo obligatorio, cada vocabulario cerrado, cada constante, cada acoplamiento, cada
restricción de arreglo, cada mínimo, cada longitud, cada patrón, cada objeto cerrado, cada agregado
derivado y cada propiedad simultánea—, transformando estos conformes. Hoy son más de doscientos.

Guardarlos como archivos los volvería una transcripción a mano de algo que el schema ya declara:
quedarían viejos en cuanto el schema cambiara, y un elemento nuevo nacería sin mutante sin que nada
lo señalara. Generándolos, la correspondencia elemento ↔ mutante es por construcción.

## Cómo se corren

```sh
python3 scripts/verificar-matriz-despachos.py --autotest-schema          # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --schema <ruta-de-matriz>  # exit 0 si valida
```

Editar un conforme sin correr el autotest es la forma más rápida de romper la cobertura sin
enterarse: quitar la segunda señal de detección, o la única sede en `json`, deja huecos que el modo
detecta pero que nada más mira.
