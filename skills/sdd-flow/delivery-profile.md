# Política del perfil de entrega

Este documento es la sede normativa compartida de `delivery_profile`. `sdd-flow` lo aplica de forma
directa y `sdd-orchestrator` lo consume por su dependencia de `sdd-flow`. El perfil acelera
coordinación redundante; nunca reduce investigación, revisión, pruebas, evidencia ni autorizaciones.

## 1. Vocabulario y par de estado

`delivery_profile` admite `standard | expedited`; `risk` admite `low | high | unknown`; `complexity`
admite `trivial | normal | complex`. En todo carrier nuevo, `delivery_profile` y `risk` son un par
indivisible. Un valor fuera de enum, una clave duplicada o una presencia parcial detienen el flujo.

La ausencia conjunta del par en un plan o manifest heredado significa `standard`, sin materializar
riesgo retroactivamente. Con el par presente, `complexity` también debe existir y pertenecer a su
enum. `expedited` solo es elegible con `complexity: trivial | normal` y `risk: low`.

La autoridad temporal es: evaluación vigente antes de crear el plan; header del plan después de
crearlo; header de cada plan derivado durante el fan-out. El handoff es un snapshot de recuperación,
no una autoridad paralela. En multi-repo, las filas `integration` y `repo:<path>` originan el fold;
manifest y planes son carriers cuya igualdad se verifica.

## 2. Evaluación universal de entrega

Todo flujo nuevo evalúa las dimensiones por separado, aunque no exista urgencia ni se recomiende
`expedited`. Ningún indicio del tracker ni la frase “trátalo como hotfix” decide el riesgo.

| Campo | Valores admitidos | Evidencia obligatoria | Autoridad |
|---|---|---|---|
| urgency | high, normal, unknown | necesidad y ventana de negocio | contexto confirmado |
| complexity | trivial, normal, complex | alcance técnico y superficies afectadas | análisis vigente |
| risk | low, high, unknown | impacto, invalidadores, reversión, señal y dependencias | análisis vigente |
| evidence | lista no vacía | hechos observables y rutas cuando existan | fuente citada |
| provenance | user, tracker:&lt;field&gt;, repo:&lt;path:line&gt;, inference:&lt;basis&gt; | origen literal de cada conclusión | fuente citada |
| confidence | high, medium, low | suficiencia y límites de la evidencia | evaluación vigente |

En `sdd-flow`, `gather-context` crea la evaluación provisional y `analyze` reevalúa complejidad y
riesgo para todo perfil. El plan recibe el riesgo post-análisis. La recomendación explica qué gates
se fusionan, qué capas se agregan y cuándo no hay reducción; la elección humana ocurre en el
checkpoint ya existente. Evidencia insuficiente produce `risk: unknown` y conserva `standard`.

## 3. Sensibilidad, elegibilidad y Risk and reversal

Un cambio es sensible si altera lógica, contratos o efectos en datos o schemas, autenticación,
autorización, pagos, seguridad o concurrencia. Ningún cambio sensible puede ser `risk: low`. Un cambio
puramente cosmético o documental no se vuelve sensible solo por el nombre de su archivo o dominio.

La sección `Risk and reversal` registra siempre radio de impacto, invalidadores, reversión o
forward-fix, señal observable y dependencias externas. Falta de evidencia, una dependencia incierta o
un rollback no verificable producen `risk: unknown`. `high`, `unknown` o `complex` hacen efectivo
`standard`, incluso si antes se eligió `expedited`.

## 4. Preset, overrides, degradación y revocación

El preset solo resuelve capas ausentes o `auto`; nunca pisa un valor concreto. Para capas triestado,
solo `"on"` y `"off"` son overrides concretos. `implement_mode: ask` también es concreto.

| Capa | Auto expedito | Override concreto | Resultado insuficiente |
|---|---|---|---|
| co-explore explore | "on" | "on" o "off" | "off" desactiva la capa y revoca expedited a standard; capacidad ausente también revoca |
| debate | auto | "on" o "off" | se aplica el contrato propio de debate |
| counter-plan | "off" | "on" o "off" | "on" revoca expedited a standard; se ejecuta tras la spec aprobada |
| cross-review | "on" | "on" o "off" | "off" desactiva la capa y revoca expedited a standard; capacidad ausente también revoca |
| implementación | inline | inline, cross-implement o ask | ask conserva la decisión humana final |

En co-explore, `cross_family` y `same_family` sostienen el perfil; `same_family` declara diversidad
reducida en el gate. `single_voice` o `FALLO_DE_MAPA` revocan `expedited`. En cross-review, el caller
lee el `review-log.md` retornado y el ledger del ciclo de vida. `UNAVAILABLE` sin una ronda completada
revoca el perfil; con alguna ronda se decide por las aplicaciones pendientes de la sección 6.

Un override raíz `co_explore.mode: "off"` o `cross_review.mode: "off"` prevalece desactivando su
capa, pero por eso mismo revoca `expedited` a `standard` antes de crear dependientes o liberar el
siguiente gate. En `standard`, solo desactiva la capa. No se considera override raíz la supresión de
duplicados que `sdd-orchestrator` entrega a un flujo por repo después de completar ambas capas sobre
la master-spec y el reparto: esa ejecución hereda la evidencia upstream y conserva el par global.

Toda revocación registra motivo, restaura la secuencia `standard`, conserva rama y base, y no abre
una segunda corrida para reemplazar una revisión todavía activa.

## 5. Secuencias por complejidad y Jira

Los gates de artefactos cuentan únicamente aprobaciones locales de spec, plan o tasks. Checkpoints
cross-model y la aprobación externa de Jira no entran en ese contador. Los pasos separados por `>`
son obligatorios y su orden es normativo.

| Complejidad | Perfil | Jira | Gates de artefactos | Secuencia efectiva |
|---|---|---|---|---|
| trivial | standard | "off" | 1 | plan-combinado(spec+plan+tasks) > gate-atómico |
| trivial | expedited | "off" | 1 | explore > plan-combinado(spec+plan+tasks) > cross-review > gate-atómico |
| normal | standard | "off" | 2 | spec > gate-spec > plan+tasks > gate-plan-tasks |
| normal | expedited | "off" | 1 | spec-estable > rama+analyze > plan+tasks > reviews > gate-atómico(spec+plan+tasks) |
| normal | standard | "on" | 2 | spec > gate-spec > publicar > espera-externa > plan+tasks > gate-plan-tasks |
| normal | expedited | "on" | 2 | spec > gate-spec-local > publicar > espera-externa > plan+tasks > gate-atómico(plan+tasks) |
| complex | standard | "off" | 3 | spec > gate-spec > plan > gate-plan > tasks > gate-tasks |
| complex | standard | "on" | 3 | spec > gate-spec > publicar > espera-externa > plan > gate-plan > tasks > gate-tasks |

Para `trivial`, recomendar standard porque no se reduce ningún gate de artefactos, aunque una elección
explícita de `expedited` sea válida con riesgo bajo. Jira requiere reclasificación explícita a normal;
no se infiere desde el tracker. `complex` nunca admite `expedited`.

En normal expedito con Jira `"off"`, no se promueve estado ni se congela contrato antes de la
aprobación atómica de spec, plan y tasks. Con Jira `"on"`, se conserva el gate local de spec, la
publicación segura y la espera externa; solo después nacen plan y tasks y comparten un gate. Esta
combinación no reduce gates y la recomendación debe decirlo.

## 6. Estabilidad de cross-review y corrección upstream

Cada etapa conserva la tanda finita configurada y el veredicto derivado del contrato de cross-review.
Se abre una corrida de spec y luego una corrida de plan con tasks como contexto. Jira `"on"` no cambia
los tipos revisados, solo ubica sus gates por separado. Únicamente una elección humana posterior puede
pedir seguir hasta APPROVED, con otro tope finito explícito.

| Resultado | Rondas completadas | Aplicaciones pendientes | Acción llamadora |
|---|---|---|---|
| APPROVED | >=1 | 0 | estabilizar y habilitar dependientes |
| REVISE | >=1 | cualquiera | abrir checkpoint, revocar expedited y restaurar gate standard |
| UNAVAILABLE | 0 | cualquiera | informar degradación y revocar expedited |
| UNAVAILABLE | >=1 | 0 | mostrar limitación, estabilizar y habilitar dependientes |
| UNAVAILABLE | >=1 | >0 | abrir checkpoint y revocar expedited |

Un checkpoint conserva el mismo run_id. Puede conceder una tanda finita adicional, rechazar
aplicaciones o cambiar un criterio de aceptación. Si cambia un AC o master-spec, el orden es:
registrar arbitraje; cerrar la corrida actual; invalidar dependientes; regenerar dependientes;
repetir evidencia afectada; abrir una nueva corrida de revisión. Nunca se corrige un artefacto con
una corrida abierta ni se duplican corridas para el mismo estado.

## 7. Persistencia, resume y preservación de rama

Antes del plan, el handoff guarda `delivery_profile` y `risk` como hermanas de `complexity` y
`change_type`, además de `spec_approved_at`. `create-branch` escribe el handoff incluso si la ejecución
continúa. En trivial, `spec_approved_at` es `null`; en normal o complex contiene el timestamp de la
aprobación local o `null` cuando sigue pendiente. Después de crear el plan, manda su header.

| Estado del carrier | Autoridad | Acción al retomar | Tratamiento de rama |
|---|---|---|---|
| plan existente | header del plan | continuar desde status y perfil persistidos | conservar rama y base |
| trivial pre-plan | handoff | reconstruir plan combinado y mostrar su gate final | conservar rama y base |
| normal o complex con timestamp | handoff | continuar después del gate de spec | conservar rama y base |
| spec_approved_at: null explícito | handoff | volver al gate de spec y no volver a preguntar | conservar rama y base |
| heredado pre-plan sin spec_approved_at | evidencia humana | preguntar una vez y persistir timestamp o null | conservar rama y base |
| perfil revocado o Jira cambiado | plan o handoff vigente | restaurar el gate standard pendiente | conservar rama y base; create-branch consumido |
| par ausente heredado | carrier vigente | anunciar fallback standard sin elevar riesgo | conservar rama y base |

La existencia de una rama nunca prueba aprobación. Si el orden restaurado exige publicar spec antes
de crear rama, la rama ya creada es una excepción durable: se publica sin crear, borrar, renombrar ni
volver a ofrecer la rama.

## 8. Orquestación all-or-nothing

Antes de elegir el perfil, el orquestador ejecuta una vez el preflight del helper. Evalúa filas
`global`, `integration` y `repo:<path>` con el schema de la sección 2. Solo `integration.risk` participa
en el fold; `integration.complexity` es informativa. El riesgo global es `high` si cualquier riesgo es
`high`; en caso contrario es `unknown` si alguno es `unknown`; solo es `low` cuando todos son `low`.

`expedited` exige integración `low` y cada repo `trivial | normal` con riesgo `low`. La elección es
all-or-nothing, ocurre en la confirmación existente de repos y se persiste en manifest y bitácora
antes del co-explore global. El análisis posterior puede revocarla, pero nunca activarla sin una nueva
elección humana.

Manifest, todos los planes y el contrato de integración se materializan como candidatos antes del
gate de reparto. Se ejecutan los predicados independientes del sellado; solo tras la aprobación se
congela una vez y corre el conjunto canónico completo. Un fallo solo de hash o cadena con contenido
idéntico permite volver a sellar. Cualquier otro rojo reabre diseño/reparto y bloquea fan-out.

Antes de cada despacho se exige igualdad de `delivery_profile` y `risk` globales entre la raíz del
manifest y todos los planes; igualdad de `complexity` y `risk` locales entre cada fila
`repo:<path>` del assessment y su repo del manifest; e igualdad de `complexity` local también entre
esa fila y su plan. El plan conserva el `risk` global; no copia el riesgo local. Ante divergencia:
registrar intento rechazado, no crear sobre, conservar estado, bloquear dependientes y continuar
repos independientes.

## 9. Piso de calidad y autorización externa

Ambos perfiles conservan: búsqueda completa de antecedentes; causa raíz antes de editar; criterios de
aceptación observables; pruebas enfocadas; evidencia fresca; checks relevantes; revisión final del
diff; reversión o forward-fix; y la regla de nunca silenciar linters o compiladores.

En ejecución inline, `final_diff_review.mode: auto` se activa por `complexity: complex` o por
`risk: high | risk: unknown`. Los modos delegados conservan sus revisiones y gates propios. El perfil
no concede permiso para crear rama, commit, push, pull request, merge ni escritura externa. Cada
autorización vigente sigue siendo explícita e independiente.

## 10. Matriz de escenarios y dry runs

Estas pruebas funcionales miden transiciones y gates de artefactos, no ahorro ni métricas temporales.

| Escenario | Entrada | Perfil esperado | Observación obligatoria |
|---|---|---|---|
| normal-low-jira-off | normal, low, Jira "off" | expedited elegible | 2 a 1 gates; gate atómico triple |
| normal-low-jira-on | normal, low, Jira "on" | expedited elegible | gate spec, espera externa y gate plan-tasks; sin reducción |
| trivial-low | trivial, low, Jira "off" | standard recomendado; expedited permitido | plan combinado y un gate |
| complex-low | complex, low | standard | expedited-inelegible |
| normal-unknown | normal, unknown | standard | riesgo insuficiente falla cerrado |
| legacy-dual-absence | sin par nuevo | standard heredado | continuar sin materializar riesgo |
| multi-repo-low | integración low; repos trivial o normal low | expedited elegible | fold low y carrier igual en todos |
| multi-repo-one-high | un repo high | standard | fold high y revocación global |
| partial-carrier | solo delivery_profile o solo risk | inválido | diagnóstico par-parcial antes del orden histórico |
| review-unavailable-zero-rounds | UNAVAILABLE sin ronda | standard | revocar antes de crear dependientes |

Los dry runs incluyen además enum desconocido, claves duplicadas, delimitador ausente o mal cerrado, helper
ausente o incompatible, divergencia manifest-plan, integración compleja informativa con todos los
riesgos bajos, cambio de Jira con rama existente y corrección upstream con cierre previo de corrida.
