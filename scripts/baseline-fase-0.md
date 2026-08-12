# Baseline de la fase 0

Documento **generado**: cada número se deriva de las observaciones y ninguno se escribe a mano. Se
reproduce con `python3 scripts/instrumento-baseline.py --generar-baseline <dir-de-observaciones>`.

## Procedencia

| insumo | identidad |
| --- | --- |
| acta congelada (`preregistro_sha256`) | `b93f3abeedf5dacec10b5e376fa2d7c11db3b88b60db4bd35bcbb65d39db0105` |
| commit del código medido | `3be305e` |
| muestras de la cohorte | 13 |
| observaciones recolectadas | 13 |

## Números publicados

| métrica | valor | unidad | agregación | muestras | adjudicación |
| --- | --- | --- | --- | --- | --- |
| `latencia-hasta-resultado-utilizable` | sin observaciones | milisegundos | mediana | 10 | mst-bitbucket-code-review-panel-de-revisores-r1: ningún intento satisface la regla «primer_intento_valido» |
| `latencia-hasta-estado-terminal` | sin observaciones | milisegundos | mediana | 0 | mst-bitbucket-code-review-panel-de-revisores-r1: ningún intento satisface la regla «primer_intento_valido» |
| `tasa-de-degradacion` | `0.0` | proporcion | suma-de-numeradores-sobre-suma-de-denominadores | 13 | — |
| `conteo-de-degradaciones` | `0.0` | conteo | suma | 13 | — |
| `salidas-invalidas` | `3.0` | conteo | suma | 13 | — |
| `tasa-de-salidas-invalidas` | `0.23076923076923078` | proporcion | suma-de-numeradores-sobre-suma-de-denominadores | 13 | — |
| `hallazgos-emitidos` | `0.0` | conteo | suma | 13 | — |
| `limpieza-completa` | `0.0` | booleano | conjuncion | 13 | — |

## Valor por muestra

| métrica | muestra | valor |
| --- | --- | --- |
| `tasa-de-degradacion` | `mst-bitbucket-code-review-panel-de-revisores-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-bitbucket-code-review-validador-adversarial-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-co-explore-fan-out-dual-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-co-explore-worker-por-ronda-de-debate-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-cross-implement-ronda-de-fix-loop-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-cross-review-revisor-por-ronda-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-sdd-flow-analyze-exploracion-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-sdd-flow-implementer-por-task-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-sdd-flow-reviewer-por-task-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-sdd-flow-revision-final-de-diff-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-sdd-orchestrator-fan-out-por-repo-r1` | `0.0` |
| `tasa-de-degradacion` | `mst-sdd-pr-feedback-implement-delegado-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-bitbucket-code-review-panel-de-revisores-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-bitbucket-code-review-validador-adversarial-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-co-explore-fan-out-dual-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-co-explore-worker-por-ronda-de-debate-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-cross-implement-ronda-de-fix-loop-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-cross-review-revisor-por-ronda-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-sdd-flow-analyze-exploracion-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-sdd-flow-implementer-por-task-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-sdd-flow-reviewer-por-task-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-sdd-flow-revision-final-de-diff-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-sdd-orchestrator-fan-out-por-repo-r1` | `0.0` |
| `conteo-de-degradaciones` | `mst-sdd-pr-feedback-implement-delegado-r1` | `0.0` |
| `salidas-invalidas` | `mst-bitbucket-code-review-panel-de-revisores-r1` | `1.0` |
| `salidas-invalidas` | `mst-bitbucket-code-review-validador-adversarial-r1` | `1.0` |
| `salidas-invalidas` | `mst-co-explore-fan-out-dual-r1` | `1.0` |
| `salidas-invalidas` | `mst-co-explore-worker-por-ronda-de-debate-r1` | `0.0` |
| `salidas-invalidas` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `salidas-invalidas` | `mst-cross-implement-ronda-de-fix-loop-r1` | `0.0` |
| `salidas-invalidas` | `mst-cross-review-revisor-por-ronda-r1` | `0.0` |
| `salidas-invalidas` | `mst-sdd-flow-analyze-exploracion-r1` | `0.0` |
| `salidas-invalidas` | `mst-sdd-flow-implementer-por-task-r1` | `0.0` |
| `salidas-invalidas` | `mst-sdd-flow-reviewer-por-task-r1` | `0.0` |
| `salidas-invalidas` | `mst-sdd-flow-revision-final-de-diff-r1` | `0.0` |
| `salidas-invalidas` | `mst-sdd-orchestrator-fan-out-por-repo-r1` | `0.0` |
| `salidas-invalidas` | `mst-sdd-pr-feedback-implement-delegado-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-bitbucket-code-review-panel-de-revisores-r1` | `1.0` |
| `tasa-de-salidas-invalidas` | `mst-bitbucket-code-review-validador-adversarial-r1` | `1.0` |
| `tasa-de-salidas-invalidas` | `mst-co-explore-fan-out-dual-r1` | `1.0` |
| `tasa-de-salidas-invalidas` | `mst-co-explore-worker-por-ronda-de-debate-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-cross-implement-ronda-de-fix-loop-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-cross-review-revisor-por-ronda-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-sdd-flow-analyze-exploracion-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-sdd-flow-implementer-por-task-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-sdd-flow-reviewer-por-task-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-sdd-flow-revision-final-de-diff-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-sdd-orchestrator-fan-out-por-repo-r1` | `0.0` |
| `tasa-de-salidas-invalidas` | `mst-sdd-pr-feedback-implement-delegado-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-bitbucket-code-review-panel-de-revisores-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-bitbucket-code-review-validador-adversarial-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-co-explore-fan-out-dual-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-co-explore-worker-por-ronda-de-debate-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-cross-implement-implementador-inicial-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-cross-implement-ronda-de-fix-loop-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-cross-review-revisor-por-ronda-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-sdd-flow-analyze-exploracion-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-sdd-flow-implementer-por-task-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-sdd-flow-reviewer-por-task-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-sdd-flow-revision-final-de-diff-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-sdd-orchestrator-fan-out-por-repo-r1` | `0.0` |
| `hallazgos-emitidos` | `mst-sdd-pr-feedback-implement-delegado-r1` | `0.0` |
| `limpieza-completa` | `mst-bitbucket-code-review-panel-de-revisores-r1` | `1.0` |
| `limpieza-completa` | `mst-bitbucket-code-review-validador-adversarial-r1` | `1.0` |
| `limpieza-completa` | `mst-co-explore-fan-out-dual-r1` | `0.0` |
| `limpieza-completa` | `mst-co-explore-worker-por-ronda-de-debate-r1` | `1.0` |
| `limpieza-completa` | `mst-cross-implement-implementador-inicial-r1` | `1.0` |
| `limpieza-completa` | `mst-cross-implement-ronda-de-fix-loop-r1` | `1.0` |
| `limpieza-completa` | `mst-cross-review-revisor-por-ronda-r1` | `1.0` |
| `limpieza-completa` | `mst-sdd-flow-analyze-exploracion-r1` | `1.0` |
| `limpieza-completa` | `mst-sdd-flow-implementer-por-task-r1` | `1.0` |
| `limpieza-completa` | `mst-sdd-flow-reviewer-por-task-r1` | `1.0` |
| `limpieza-completa` | `mst-sdd-flow-revision-final-de-diff-r1` | `1.0` |
| `limpieza-completa` | `mst-sdd-orchestrator-fan-out-por-repo-r1` | `1.0` |
| `limpieza-completa` | `mst-sdd-pr-feedback-implement-delegado-r1` | `1.0` |

## Métricas sin observaciones

Ninguna se publica como cero. Cada una declara por qué el agregado no tiene valor y qué dijo
cada observación, que es lo único que separa «la cohorte no la cubre» de «la corrida impidió
medirla».

### `latencia-hasta-resultado-utilizable`

Adjudicación del agregado: mst-bitbucket-code-review-panel-de-revisores-r1: ningún intento satisface la regla «primer_intento_valido»

| observación | estado de la medición | adjudicación |
| --- | --- | --- |
| — | — | ninguna observación declara esta métrica |

### `latencia-hasta-estado-terminal`

Adjudicación del agregado: mst-bitbucket-code-review-panel-de-revisores-r1: ningún intento satisface la regla «primer_intento_valido»

| observación | estado de la medición | adjudicación |
| --- | --- | --- |
| — | — | ninguna observación declara esta métrica |
