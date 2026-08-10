# Contrato sintético de ejecución

**Este documento no es el contrato del repositorio.** Es el fixture **conforme** de los modos
`--contrato`, `--ejes` y `--capacidades` de `scripts/verificar-matriz-despachos.py`: congela la
**forma** que el contrato real tendrá que cumplir, y se escribe antes que él a propósito. Al revés,
el parser heredaría la interpretación de quien escribió el texto y los dos pasarían de acuerdo entre
sí aunque ambos estuvieran mal.

Su alcance, sus correcciones y sus decisiones diferidas son **sintéticos**, y sus documentos fuente
viven en `fuentes/`. Los **tres ejes** son la excepción declarada: sus literales y sus punteros son
los **normativos**, porque la propiedad que esa sección ejerce es justamente la igualdad exacta
contra el inventario congelado, y con literales inventados no probaría nada.

## Alcance comprometido

| tramo | estado |
|---|---|
| Fases 0-4 | comprometido |
| Fases 5-7 | condicionado a las métricas de las anteriores |

## Correcciones

Cada fila reemplaza una afirmación que vive en el documento de la última columna. La cláusula de
supersesión nombra ese documento: sin nombrarlo, «este contrato prevalece» no dice sobre qué.

| id | afirmación anterior | afirmación corregida | evidencia | supersesión | documento fuente |
|---|---|---|---|---|---|
| C-01 | La revisión de artefactos sintéticos no tiene dueño declarado en el ecosistema de ejemplo. | La revisión de artefactos sintéticos tiene dueño declarado: la skill de revisión del corpus de ejemplo. | La skill de revisión del corpus declara el artefacto entre sus entradas admitidas. | Este contrato prevalece sobre `propuesta-doctrinal.md` en este punto. | fuentes/propuesta-doctrinal.md |
| C-02 | Un archivo de política de invocación sintética queda definido por su extensión. | Un archivo de política de invocación sintética queda definido por su ubicación y su clave de habilitación, no por su extensión. | Dos archivos con la misma extensión y distinta ubicación reciben trato distinto en el corpus. | Este contrato prevalece sobre `exploracion-previa.md` en este punto. | fuentes/exploracion-previa.md |
| C-03 | El despacho sintético de la familia beta corre siempre en primer plano. | El despacho sintético de la familia beta corre en segundo plano cuando el presupuesto de espera supera el tope conversacional. | El corpus de escenarios registra dos despachos beta en segundo plano. | Este contrato prevalece sobre `propuesta-doctrinal.md` en este punto. | fuentes/propuesta-doctrinal.md |

## Decisiones diferidas

Ninguna se resuelve acá: quedan **íntegramente diferidas**, cada una con la fase que la va a tomar.

| id | decisión | estado | fase de destino |
|---|---|---|---|
| D-01 | Si el arbitraje sintético lo ejerce el conductor o un tercero. | diferida | Fase 3 |
| D-02 | Con qué granularidad se mide el presupuesto sintético de espera. | diferida | Fase 5 |

## Los tres ejes

Tres preguntas distintas sobre una misma corrida delegada, con **vocabularios separados**. Nombrarlas
y separarlas es el aporte de este contrato; los literales salen de sedes que ya existen, y cada uno
declara la suya.

Cada literal se escribe **con su namespace** —`<eje>.<literal>`—: sin él, el mismo token citado en
otra sección no dice de qué eje es, que es exactamente la fusión que estas tres tablas existen para
impedir.

### Eje: ciclo de vida operativo

Qué pasó con la corrida **como proceso**, con independencia de lo que haya entregado.

| literal | tipo | sede | significado |
|---|---|---|---|
| `ciclo_de_vida_operativo.resultado_entregado` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | la espera terminó con un resultado terminal que se puede adjudicar |
| `ciclo_de_vida_operativo.corte_presupuesto` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | venció el presupuesto de espera del conductor; la corrida sigue activa |
| `ciclo_de_vida_operativo.error` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | terminal comprobado de fallo: se sabe qué pasó y se puede adjudicar |
| `ciclo_de_vida_operativo.cancelacion` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | terminal por decisión, con su segundo componente de cese confirmado o incierto |
| `ciclo_de_vida_operativo.UNAVAILABLE` | terminal_sin_entrega | `skills/co-explore/reference.md#estados-del-worker` | el worker no respondió o no se pudo lanzar, así que no hay reporte que validar |
| `ciclo_de_vida_operativo.done` | marcador_de_cierre | `skills/co-explore/reference.md#senal-de-finalizacion` | el crudo cerró con su marcador de fin; pertenece al transporte y no al contenido |

### Eje: validez del reporte entregado

Dado que el worker **entregó** algo, si eso satisface el contrato de salida. El eje no se pronuncia
sobre el mérito de lo entregado: eso es el tercer eje.

| literal | tipo | sede | significado |
|---|---|---|---|
| `validez_del_reporte_entregado.READY` | clase_de_validez | `skills/co-explore/reference.md#estados-del-worker` | el reporte pasa todos los predicados del contrato de salida, sin excepciones |
| `validez_del_reporte_entregado.INVALID` | clase_de_validez | `skills/co-explore/reference.md#estados-del-worker` | respondió, y lo que entregó falla alguno de esos predicados |
| `validez_del_reporte_entregado.clarification-needed` | clase_de_validez | `skills/co-explore/reference.md#clarification-needed-el-cuarto-estado` | frenó ante una ambigüedad, entregó lo que alcanzó a mapear y adosó la pregunta |

### Eje: resultado semántico

Qué dice el trabajo entregado **sobre el objeto de la delegación**. Un reporte válido puede traer
cualquiera de estos valores, y uno inválido no trae ninguno.

| literal | tipo | sede | significado |
|---|---|---|---|
| `resultado_semantico.APPROVED` | veredicto_de_revision | `skills/cross-review/reference.md#veredicto-derivado` | el ledger no deja findings en estado no terminal: la revisión convergió |
| `resultado_semantico.REVISE` | veredicto_de_revision | `skills/cross-review/reference.md#veredicto-derivado` | queda al menos un finding sin resolver, o una disputa que abre el gate humano |
| `resultado_semantico.done` | estado_de_task | `skills/sdd-flow/reference.md#prompt-del-subagente-por-task` | el subagente delegado ejecutó la task tal como estaba escrita |
| `resultado_semantico.failed` | estado_de_task | `skills/sdd-flow/reference.md#prompt-del-subagente-por-task` | el subagente delegado se bloqueó y lo dice, en vez de improvisar otro enfoque |
| `resultado_semantico.verified` | estado_de_repo_delegado | `skills/sdd-orchestrator/reference.md#prompt-del-agente-delegado` | el agente delegado por repo dejó su parte verde y con sus AC cubiertos |
| `resultado_semantico.PARTIAL` | cierre_de_unidad | `skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo` | parte la hizo el implementador y parte la terminó el conductor por takeover |
| `resultado_semantico.BLOCKED` | cierre_de_unidad | `skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo` | la fila nunca se pudo medir, así que no tiene criterio de «hecho» |

**`done` aparece en dos ejes y no es una fusión.** En el primero es el marcador de cierre del crudo
—transporte, no contenido— y en el tercero es el veredicto de una task delegada. Distinto tipo,
distinta sede y distinto significado: el literal coincide y la cosa que nombra, no.

## Capacidades de plataforma

Toda afirmación de plataforma va marcada. `dependiente` registra **con qué versión** se comprobó;
`no_verificable` registra **por qué** el runtime no la expone, que es la forma correcta de tratarla y
no un defecto.

| afirmación | marca | versión | motivo |
|---|---|---|---|
| El corte por `\|` no escapado parte una fila de tabla igual en cualquier intérprete de Markdown del corpus. | portable | — | — |
| Un rename dentro del mismo directorio publica el archivo sin dejar ver un estado intermedio. | portable | — | — |
| `herramienta-sintetica exec` acepta acotar el sandbox a solo lectura con una bandera propia. | dependiente | herramienta-sintetica 3.12.0 | — |
| El intérprete sintético de la familia beta no admite redirección de entrada por `<` y exige tubería. | dependiente | interprete-beta 7.4 | — |
| El runtime sintético expone un identificador de proceso consultable para el worker delegado. | no_verificable | — | el harness del corpus no publica ningún identificador de proceso, así que la afirmación no se puede comprobar desde adentro |
