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

## `anclas/` — el fixture del resolutor

`anclas/conforme/` no es una matriz suelta: es una **matriz con su árbol de sedes**. Ahí viven
`matriz.json` y los archivos que sus procedencias resuelven —`skills/skill-anclada/{SKILL.md,
reference.md}` y `docs/contrato.json`—, y las sedes son rutas relativas a esa carpeta, que es lo que
`--raiz` recibe. `skill-anclada` no existe en el árbol real: un fixture copiado de la matriz real
haría que el resolutor y el dato acordaran entre sí.

El conforme ejerce a propósito la combinación que **más se parece a un defecto y no lo es**: la
columna `sandbox` aparece en dos tablas, así que `permisos_efectivos` selecciona dos nodos, declara
`exactamente_n` con `n: 2` y colapsa a valor único porque los dos textos —`solo lectura` y
`read-only`— convergen al mismo token. Un resolutor demasiado estricto lo rechazaría.

Y ejerce dos casos **sensibles al orden del pipeline**, sin los cuales el orden quedaría declarado y
no verificado: `senales_de_deteccion` cambia de resultado si se ordena antes de normalizar (los
textos difieren en mayúsculas, que la normalización borra), y `modos` cambia si se ordena después de
convertir (el orden de los textos no es el de sus tokens). Editarlos sin correr `--autotest-anclas`
es la forma más rápida de perder esa cobertura.

Otras tres hojas fijan **qué es el nodo de un `heading_markdown`** y **de dónde sale el ancla
`<sede>#<slug>`**, que son dos cosas que el schema declara y que sin caso positivo quedarían
declaradas y no ejercidas. Cada una se pone roja ante una lectura distinta, y por eso son tres y no
una:

| Hoja | Qué fija | Qué la pone roja |
|---|---|---|
| `dueno` | el nodo de un `heading_markdown` es el **texto del encabezado**: el dato vive en el propio título y la captura está anclada con `^…$` | leer el cuerpo de la sección: la captura no casa contra un cuerpo |
| `ancla_de_invocacion` | `ancla_de_seccion` sobre un heading toma **su propia** sección | tomar el encabezado estrictamente anterior: resuelve a la sección de arriba |
| `contrato_de_salida` | `ancla_de_seccion` sobre una línea toma el encabezado **más cercano, de cualquier nivel** — la línea vive dentro de un `###` anidado en un `##` | armar el fragmento con el texto del nodo en vez de con su posición |

El segundo caso conforme lee esa misma ancla de la **celda que la transcribe** en `reference.md` y
exige el mismo valor. Sin él, `conversion: referencia` quedaría ejercida solo contra cadenas que el
propio resolutor fabrica —un corpus verde de autoría propia—, y además nada compararía la ancla
construida contra una escrita a mano.

## `condiciones/` — el fixture de las condiciones de existencia

`condiciones/conforme/` es una **matriz con sus escenarios**: `matriz.json` y su hermano
`matriz-escenarios.json`, que es donde el modo los busca por defecto (`<matriz>-escenarios.json`, o
lo que diga `--escenarios`). Los escenarios no caben dentro de la matriz —su schema es cerrado y no
los declara— y hornearlos en el verificador los ataría a las claves de una matriz concreta.

La matriz es **reducida a propósito**: solo `id`, `etiqueta` y `condicion_de_existencia`. Lo que el
autotest valida contra el schema son las **condiciones**, una por una contra `#/$defs/condicion`,
que es la gramática que estos dos modos consumen; los demás campos del punto no los mira ninguno de
los dos. `skill-teta` y `skill-iota` no existen en el árbol real.

Cada escenario declara su configuración completa, las capacidades presentes y el conjunto de puntos
que debe quedar activo. Once puntos y cuatro escenarios, y cada pieza cubre algo que las otras no:

| Punto | Qué ejerce |
|---|---|
| `skill-teta-siempre` | la condición constante, única exenta de la rama falsa |
| `skill-teta-implementador-{cruzado,local}` | dos modos **mutuamente excluyentes** sobre la misma clave: ningún escenario puede activar los once |
| `skill-teta-implementador-degradado` | la **degradación**: el modo pedido sin la capacidad que lo sostiene |
| `skill-teta-explorador-dual` | un `o` con **los dos operandos verdaderos**, que un `o` exclusivo rechazaría |
| `skill-teta-revision-por-profundidad` | `en` con dos valores: la cobertura exige ejercer **cada uno**, no solo uno y algo de afuera |
| `skill-iota-feedback-de-pr` | el **`no` anidado**, que equivale al átomo y no a su contrario |
| `skill-iota-sin-bitbucket` | un `no` **simple**: sin él, un evaluador que tratara `no` como identidad pasaría, porque la doble negación lo tapa |
| `skill-iota-feedback-degradado` | exclusión por `no_en` más capacidad ausente |
| `skill-iota-sin-cruzado` | exclusión por operador negativo (`distinto`) |
| `skill-iota-doble-guarda` | el operando cuyo valor falso **solo se observa donde el primero ya cortó**: es lo único que se pone rojo si la evaluación pasa a cortocircuitar |

Y los escenarios ejercen las combinaciones que **más se parecen a un defecto y no lo son**: una
capacidad ausente de la lista (legítima: `no_disponible` es verdadero), una clave presente con la
**cadena vacía** (un valor, no una ausencia) y un escenario **sin ninguna capacidad**.

Los mutantes de estos dos modos tampoco están acá: se **derivan** del corpus —uno por átomo, uno por
exclusión, uno por escenario y uno por valor de átomo—, así que un punto nuevo nace con sus mutantes.

## Cómo se corren

```sh
python3 scripts/verificar-matriz-despachos.py --autotest-schema          # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --schema <ruta-de-matriz>  # exit 0 si valida
python3 scripts/verificar-matriz-despachos.py --autotest-procedencia     # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --autotest-anclas          # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --anclas <matriz> --raiz <árbol-de-sedes>
python3 scripts/verificar-matriz-despachos.py --autotest-condiciones            # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --autotest-cobertura-condiciones  # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --condiciones <matriz> [--escenarios <ruta>]
python3 scripts/verificar-matriz-despachos.py --cobertura-condiciones <matriz>
```

Editar un conforme sin correr el autotest es la forma más rápida de romper la cobertura sin
enterarse: quitar la segunda señal de detección, o la única sede en `json`, deja huecos que el modo
detecta pero que nada más mira.
