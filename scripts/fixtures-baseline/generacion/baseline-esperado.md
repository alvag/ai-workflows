# Baseline de la fase 0

Documento **generado**: cada número se deriva de las observaciones y ninguno se escribe a mano. Se
reproduce con `python3 scripts/instrumento-baseline.py --generar-baseline <dir-de-observaciones>`.

## Procedencia

| insumo | identidad |
| --- | --- |
| acta congelada (`preregistro_sha256`) | `5555555555555555555555555555555555555555555555555555555555555555` |
| commit del código medido | `73457f2` |
| muestras de la cohorte | 3 |
| observaciones recolectadas | 4 |

## Números publicados

| métrica | valor | unidad | agregación | muestras | adjudicación |
| --- | --- | --- | --- | --- | --- |
| `latencia-hasta-resultado-utilizable` | `50000.0` | milisegundos | mediana | 3 | — |
| `tasa-de-degradacion` | `0.25` | proporcion | suma-de-numeradores-sobre-suma-de-denominadores | 3 | — |
| `conteo-de-degradaciones` | `1.0` | conteo | suma | 3 | — |
| `salidas-invalidas` | `1.0` | conteo | suma | 3 | — |
| `tasa-de-salidas-invalidas` | sin observaciones | proporcion | suma-de-numeradores-sobre-suma-de-denominadores | 0 | mst-cross-implement-implementador-inicial-r1: sin valores que agregar |
| `hallazgos-emitidos` | sin observaciones | conteo | suma | 0 | mst-cross-implement-implementador-inicial-r1: sin valores que agregar |
| `limpieza-completa` | `1.0` | booleano | conjuncion | 3 | — |

## Valor por muestra

| métrica | muestra | valor |
| --- | --- | --- |
| `latencia-hasta-resultado-utilizable` | `mst-cross-implement-implementador-inicial-r1` | `50000.0` |
| `latencia-hasta-resultado-utilizable` | `mst-cross-implement-implementador-inicial-r2` | `60000.0` |
| `latencia-hasta-resultado-utilizable` | `mst-sdd-flow-revision-final-de-diff-r1` | `30000.0` |
| `tasa-de-degradacion` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-cross-implement-implementador-inicial-r2` | `0.0` |
| `tasa-de-degradacion` | `mst-sdd-flow-revision-final-de-diff-r1` | `1.0` |
| `conteo-de-degradaciones` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-cross-implement-implementador-inicial-r2` | `0.0` |
| `conteo-de-degradaciones` | `mst-sdd-flow-revision-final-de-diff-r1` | `1.0` |
| `salidas-invalidas` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `salidas-invalidas` | `mst-cross-implement-implementador-inicial-r2` | `1.0` |
| `salidas-invalidas` | `mst-sdd-flow-revision-final-de-diff-r1` | `0.0` |
| `limpieza-completa` | `mst-cross-implement-implementador-inicial-r1` | `1.0` |
| `limpieza-completa` | `mst-cross-implement-implementador-inicial-r2` | `1.0` |
| `limpieza-completa` | `mst-sdd-flow-revision-final-de-diff-r1` | `1.0` |

## Métricas sin observaciones

Ninguna se publica como cero. Cada una declara por qué el agregado no tiene valor y qué dijo
cada observación, que es lo único que separa «la cohorte no la cubre» de «la corrida impidió
medirla».

### `tasa-de-salidas-invalidas`

Adjudicación del agregado: mst-cross-implement-implementador-inicial-r1: sin valores que agregar

| observación | estado de la medición | adjudicación |
| --- | --- | --- |
| `obs-mst-cross-implement-implementador-inicial-r1-a1` | bloqueada | el intento no conservó su salida cruda: la población elegible de la tasa no es comprobable |
| `obs-mst-cross-implement-implementador-inicial-r2-a1` | bloqueada | el intento no conservó su salida cruda: la población elegible de la tasa no es comprobable |
| `obs-mst-cross-implement-implementador-inicial-r2-a2` | bloqueada | el intento no conservó su salida cruda: la población elegible de la tasa no es comprobable |
| `obs-mst-sdd-flow-revision-final-de-diff-r1-a1` | bloqueada | el intento no conservó su salida cruda: la población elegible de la tasa no es comprobable |

### `hallazgos-emitidos`

Adjudicación del agregado: mst-cross-implement-implementador-inicial-r1: sin valores que agregar

| observación | estado de la medición | adjudicación |
| --- | --- | --- |
| `obs-mst-cross-implement-implementador-inicial-r1-a1` | no_observada | ningún punto de despacho de esta cohorte emite hallazgos: la métrica no está cubierta |
| `obs-mst-cross-implement-implementador-inicial-r2-a1` | no_observada | ningún punto de despacho de esta cohorte emite hallazgos: la métrica no está cubierta |
| `obs-mst-cross-implement-implementador-inicial-r2-a2` | no_observada | ningún punto de despacho de esta cohorte emite hallazgos: la métrica no está cubierta |
| `obs-mst-sdd-flow-revision-final-de-diff-r1-a1` | no_observada | ningún punto de despacho de esta cohorte emite hallazgos: la métrica no está cubierta |
