# Fusion Harness frente al ecosistema cross-model de `ai-workflows`

- **Fecha:** 2026-07-22
- **Autor del análisis:** Codex
- **Repositorio analizado:** [`disler/fusion-harness`](https://github.com/disler/fusion-harness)
- **Snapshot:** [`5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4`](https://github.com/disler/fusion-harness/tree/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4)
- **Presentación analizada:** [Engineers... STOP Picking GPT-5.6 Sol OR Claude Fable 5… FUSE THEM](https://www.youtube.com/watch?v=AQl5Q-0l7FQ) (26:22)

## Conclusión ejecutiva

No conviene reemplazar nuestras skills ni migrar el ecosistema a Pi/Fusion Harness.
La dirección actual es más segura, portable y auditable: separa exploración, revisión e
implementación; conserva al conductor como autoridad; limita la escritura; valida el diff real;
y el transporte `cross-model-orca` tiene una base de pruebas muy superior.

Sí conviene adoptar cuatro ideas de Fusion Harness:

1. **Contrato de verificación antes de implementar**, con baseline RED y trazabilidad AC → prueba.
2. **Manifiesto uniforme por corrida**, con timings, resultado, roles, transporte, rondas y hashes.
3. **Triage de propiedad de la falla**, distinguiendo defecto de implementación, gate, entorno o diseño.
4. **Prompts versionados como archivos**, separados de la lógica y del documento de la skill.

La síntesis recomendada es:

> Mantener nuestras skills como políticas de workflow y convertir `cross-model-orca` en un kernel
> de ejecución más observable. Adoptar de Fusion el gate-first y la telemetría, no su modelo de
> dos escritores concurrentes ni la ejecución ciega de validadores generados.

## Recomendación de rumbo

| Decisión | Recomendación |
|---|---|
| Arquitectura general | **Seguir con la actual**: `sdd-flow` como coordinador y skills especializadas por intención. |
| Transporte | **Profundizar `cross-model-orca`**, no sustituirlo por una extensión Pi. |
| Validación | **Adoptar el principio gate-first**, pero como contrato declarativo revisado y ejecutado por el conductor. |
| Fusión de opiniones | **Mantener la síntesis del conductor**; no agregar un tercer agente obligatorio. |
| Sesiones | **Mantener políticas por workflow**; no usar memoria persistente global por rol como default. |
| Escritura | **Rechazar escritores paralelos en el mismo working tree**. |
| Modelos | **Mantener familia opuesta como invariante** y registrar el modelo efectivo; no fijar IDs trimestrales en la skill. |
| Observabilidad | **Adoptar ya** duración, estado, rondas, recuperación y manifest por corrida; tokens/costo solo cuando la fuente sea confiable. |

## Alcance y método

Se revisaron:

- los 59 archivos versionados de Fusion Harness;
- el archivo principal `fusion-harness.ts` completo, de 2.506 líneas;
- todos sus prompts, recetas, artefactos del ejemplo y gate de validación;
- el README y el historial disponible del repositorio;
- los subtítulos automáticos completos del video, no solo el README;
- nuestras skills `cross-model-orca`, `co-explore`, `cross-review`, `cross-implement` y su integración con `sdd-flow`/`sdd-orchestrator`;
- el runtime real de `cross-model-orca` y su suite local.

### Verificación realizada

- Fusion Harness fue clonado y fijado al commit `5852f2e`.
- El video no fue accesible mediante WebFetch, pero YouTube sí expuso captions automáticos
  `en-orig`; se revisaron 788 segmentos, unas 6.096 palabras.
- La suite de `cross-model-orca` se ejecutó fresca:

```text
tests 103
pass 103
fail 0
duration_ms 305.401292
```

### Límite de la verificación

No se ejecutó Fusion Harness contra APIs reales porque el entorno no tiene `pi` ni `just`, y una
corrida necesitaría credenciales y consumiría modelos de pago. El repositorio no incluye
`package.json`, `tsconfig.json` ni tests automatizados que permitan una prueba offline equivalente.
La evaluación de su runtime se apoya en código, contratos y artefactos versionados.

## Qué construye Fusion Harness

Fusion Harness es una extensión monolítica para el agente Pi. Lanza subprocesses
`pi --mode json -p`, asigna modelos a roles y ofrece tres workflows:

| Comando | Flujo | Equivalente más cercano en nuestro ecosistema |
|---|---|---|
| `/opinion` | Dos respuestas paralelas, sin merge. | `co-explore explore` o `debate` R0. |
| `/fusion` | Dos workers paralelos + tercer agente que fusiona. | Síntesis de `co-explore`; parcialmente `cross-review` draft. |
| `/auto-validate` | Validator diseña gate, builder implementa, gate corrige hasta PASS o halt. | `cross-implement` + `sdd-flow verify`, pero el gate se diseña antes. |

La [tabla canónica de comandos](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/README.md#L70-L92)
presenta los tres como una escalera de valor: perspectivas, síntesis y construcción validada.

### Arquitectura operacional

```text
HOST Pi = modelo BUILDER
│
├─ /opinion
│  ├─ ARCHITECT ─┐
│  └─ BUILDER ───┴─► panel comparativo
│
├─ /fusion
│  ├─ ARCHITECT ─┐
│  ├─ BUILDER ───┴─► FUSION fresco ─► resultado atribuido
│  └─ ambos workers pueden escribir en el mismo cwd
│
└─ /auto-validate
   ├─ VALIDATOR ─► gate.py ─► baseline
   ├─ BUILDER ───► cambios
   ├─ gate.py ───► PASS | FAIL
   └─ FAIL repetido ─► TRIAGE ─► fix o reparación única del gate
```

### Aislamiento y contexto

Los hijos arrancan con `--no-skills --no-extensions --no-context-files`, por lo que su contrato
completo vive en los prompts del harness. El mecanismo está implementado en
[`runChild`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/extensions/fusion-harness/fusion-harness.ts#L439-L478).

Esto reduce variabilidad y recursión, pero no significa contexto siempre fresco:

- el ARCHITECT conserva una sesión por proyecto y modelo;
- el BUILDER intenta bifurcar la sesión del host;
- si no puede, usa una sesión persistente propia;
- solo el agente FUSION nace siempre fresco.

La implementación está en las
[`sesiones por rol/modelo`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/extensions/fusion-harness/fusion-harness.ts#L1069-L1185).

### Observabilidad

Fusion captura por agente:

- modelo y rol;
- estado y duración;
- tokens de entrada/salida;
- costo reportado por el provider;
- número de tool calls;
- contexto consumido;
- respuesta y errores atribuidos.

Además guarda `prompt.md`, respuestas por rol, resultado fusionado o gates, rondas y
`summary.json` en un directorio temporal. La [documentación de artifacts](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/README.md#L289-L293)
lo trata como superficie de grounding y auditoría, no solo como log de depuración.

### El aporte central del video

El video añade contexto que el README resume, pero no reemplaza:

- [00:00–01:17](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=0s): propone combinar modelos por rol en lugar de elegir un ganador.
- [01:53–04:38](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=113s): usa latencia, tokens y costo como benchmark relativo sobre trabajo real.
- [04:47–08:00](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=287s): presenta el gate antes de construir como respuesta al problema de revisión.
- [12:55–13:24](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=775s): describe `opinion → fusion → auto-validate` como un micro-SDLC.
- [16:18–17:25](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=978s): diferencia el patrón de una delegación clásica; el valor está en combinar perspectivas.
- [20:21–24:36](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=1221s): sitúa el harness como un nodo dentro de un AI Developer Workflow mayor.

La última idea encaja especialmente bien con nuestra arquitectura: `cross-model-orca` no debería
convertirse en el SDLC; debe seguir siendo un nodo reusable bajo `sdd-flow` y las skills de intención.

## Comparación con lo que ya tenemos

| Dimensión | Fusion Harness | `ai-workflows` | Veredicto |
|---|---|---|---|
| Unidad de diseño | Un harness con tres comandos. | Skills separadas por intención + transporte compartido. | Nuestra separación escala mejor. |
| Autoridad | ARCHITECT fusiona/valida; HOST es BUILDER. | El conductor sintetiza, arbitra, verifica y commitea. | Mantener la nuestra. |
| Independencia | Roles separados, pero sesiones persistentes. | Mapa propio antes de leer al secundario; sesiones frescas salvo loops acotados. | Nuestra independencia es más explícita. |
| Exploración | Dos agentes responden el mismo prompt. | `co-explore` distingue explore, counter-plan, investigate y debate. | Nuestra semántica es más rica. |
| Revisión | Fusión general o validator. | `cross-review` revisa spec/plan/tasks con findings, confianza y arbitraje. | Nuestra revisión está mejor tipada. |
| Implementación | BUILDER escribe con full tools; en `/fusion` hay dos escritores. | Un implementador de otra familia, work order congelado, clean tree, diff como verdad. | Nuestra disciplina es superior. |
| Verificación | Gate ejecutable generado antes del build. | `proof_cmd`, tests/build y gate function por AC después del build. | Fusion gana en anticipación; nosotros en control. |
| Falla repetida | Triage del validator y una reparación de gate. | Fix loop acotado, takeover y retorno a plan ante fallo repetido. | Conviene fusionar ambos enfoques. |
| Seguridad | Tool list + instrucciones; sin sandbox de proyecto visible. | Sandbox, MCP off/controlado, contención, nonce, dedup y recuperación. | Mantener nuestra base. |
| Transporte | Subprocess Pi acoplado a una superficie. | CLI portable + sesión Orca interactiva + fallback. | Nuestra portabilidad es mayor. |
| Estado | Memoria persistente por rol/modelo. | Estado por workflow y resume controlado. | Mantener políticas por flujo. |
| Observabilidad | UI viva, tokens, costo, duración y summary. | Logs por skill y estados de transporte; sin telemetría uniforme. | Oportunidad clara de mejora. |
| Prompts | Archivos separados con interpolación. | Principalmente plantillas dentro de `reference.md`. | Adoptar el patrón de archivos. |
| Pruebas | No hay tests versionados. | `cross-model-orca`: 103 tests verdes. | No retroceder. |

## Lo que Fusion Harness hace mejor

### 1. Diseña la prueba antes de construir

El gate-first evita que el implementador defina retrospectivamente qué significa “terminado”.
El [flujo RED → build → PASS/FAIL](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/README.md#L138-L154)
obliga a convertir requisitos en evidencia antes de ver la solución.

Nuestro `sdd-flow verify` es fuerte: exige evidencia fresca por AC y revert-to-confirm cuando hay
test de comportamiento. Sin embargo, la selección final de la evidencia ocurre después de
implementar. Existe un seam concreto para mejorar: congelar antes del dispatch una tabla
`AC → prueba → resultado esperado → baseline`.

### 2. Convierte cada corrida en datos comparables

La frase “relativity is the best benchmark” del autor se materializa en métricas por rol. Nosotros
tenemos evidencia cualitativa y smoke tests, pero todavía no podemos responder sistemáticamente:

- cuánto tarda cada familia por modo;
- cuántas rondas consume;
- cuánto falla cada transporte;
- qué porcentaje de findings se acepta;
- cuánto cuesta una tercera fusión frente a la síntesis del conductor;
- cuándo una sesión persistente mejora o degrada el resultado.

Sin esos datos, las decisiones sobre modelos, esfuerzo y deadlines dependen de anécdotas.

### 3. Trata el fallo del verificador como una clase de falla propia

Fusion no asume que todo rojo es culpa del builder. Tras fallas repetidas, el validator diagnostica
y puede reparar una vez su gate sin gastar una ronda del builder. Este principio falta como contrato
explícito en `cross-implement`.

### 4. Separa prompts y runtime

Todos los prompts viven junto al código y se interpolan. Esto permite:

- versionarlos y hashearlos;
- probar el renderer sin lanzar modelos;
- comparar cambios de prompt;
- evitar duplicación entre transportes;
- mantener `SKILL.md` concentrado en decisiones y procedimiento.

### 5. Expone el estado mientras trabaja

La UI muestra rol, modelo, fase, actividad, duración y costo; `escape` cancela subprocesses. Orca
ya nos da visibilidad mediante terminales reales, pero el conductor no recibe hoy una superficie
uniforme de estado. Un stream estructurado del kernel serviría tanto a Orca como a CLI.

## Lo que no debemos copiar

### 1. Dos escritores concurrentes en el mismo cwd

`/fusion` entrega `FULL_TOOLS` a ARCHITECT y BUILDER en paralelo
([código](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/extensions/fusion-harness/fusion-harness.ts#L1801-L1825)).
La prevención de colisiones depende de una instrucción de naming. El propio README reconoce la
[carrera entre escritores](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/README.md#L303-L310).

Esto es inferior a nuestros invariantes:

- `co-explore` y `cross-review` son read-only;
- `cross-implement` exige un solo escritor;
- `sdd-flow` ejecuta tasks secuencialmente en un working tree;
- la paralelización multi-repo usa working trees disjuntos.

La instrucción “no colisiones” no reemplaza el aislamiento físico.

### 2. Ejecutar ciegamente un gate generado

El validator escribe Python y el host ejecuta `uv run gate.py`. El prompt pide cero efectos
laterales, pero el control real es insuficiente:

- `write` se restringe a una ruta por instrucción, no por sandbox demostrado;
- el script puede ejecutar procesos, red o modificar archivos;
- PEP 723 admite dependencias, por lo que `uv` puede descargar código;
- el gate se ejecuta antes de una revisión humana o estática del conductor.

Debemos adoptar el **contrato de aceptación anticipado**, no la ejecución automática de código
arbitrario producido por el modelo.

### 3. Memoria persistente global por rol como default

La persistencia acelera continuidad, pero también acumula supuestos, datos y sesgos. El propio
repositorio documenta bloqueos de policy y contexto stale. Para nuestras skills, la política debe
depender del trabajo:

- `co-explore explore`: fresco para evitar anclaje;
- `cross-review`: persistente solo durante sus rondas;
- `cross-implement`: persistente solo durante implementación/fixes;
- workflows futuros: opt-in explícito, nunca memoria indefinida por proyecto.

### 4. IDs de modelos fijos dentro del producto

Separar rol y modelo es correcto. Fijar el producto a nombres de modelos concretos no lo es: deriva
rápido, crea mantenimiento y confunde capacidad con marca. Nuestro invariante “familia opuesta” es
más estable. La mejora correcta es registrar modelo y esfuerzo efectivos y permitir perfiles de
presupuesto, no hardcodear ganadores.

### 5. Tercer agente de fusión obligatorio

Un tercer agente puede aportar en decisiones grandes, pero también:

- agrega latencia y costo;
- puede borrar divergencias útiles;
- introduce otro punto de alucinación;
- reduce el rol del conductor a aceptar una síntesis ajena.

`co-explore` ya obliga al conductor a producir su mapa antes de leer el secundario y luego sintetizar
con rationale. Ese diseño es más barato y conserva responsabilidad. Un fuser separado debería ser
opt-in para material muy grande, no el default.

### 6. Monolito de runtime sin suite

La extensión central tiene 2.506 líneas y mezcla spawn, sessions, telemetría, render TUI, prompts,
gates, parsing y comandos. No hay tests ni configuración de typecheck versionados. Nuestra
implementación también tiene complejidad, pero está separada en módulos y su kernel suma 103 pruebas.
La lección no es copiar el archivo; es mover más invariantes repetidos desde Markdown a módulos
pequeños y testeados.

## Hallazgo importante en los artefactos del demo

El ejemplo versionado no terminó verde. El manifest declara que la última corrida acabó RED porque
`clean_md()` borraba underscores y hacía imposibles cuatro checks. Esto se confirma en
[`gate.py:60-61`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/live_final_generation/harness-artifacts/gate.py#L60-L61)
y en el
[`MANIFEST`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/live_final_generation/MANIFEST-claude-fable-5-gpt-5.6-sol.md#L22-L36).

Esto no invalida gate-first. Demuestra algo más útil:

> El verificador también es software y necesita versión, pruebas, ownership de fallas y evidencia
> de que el artefacto promocionado corresponde exactamente a la corrida reportada.

Hay además una tensión de procedencia: el README describe reparación automática del gate y un flujo
“shipped”, mientras el snapshot del demo conserva la corrida histórica RED. Un manifiesto con commit,
versión de prompts, hashes y status final evitaría que código actual, narrativa y artifacts parezcan
la misma ejecución cuando no lo son.

## Arquitectura objetivo propuesta

```text
┌──────────────────────────────────────────────────────────────┐
│ Workflow policies                                           │
│ co-explore · cross-review · cross-implement · sdd-flow      │
│ Decide cuándo, por qué, gates humanos y autoridad final.    │
└───────────────────────────┬──────────────────────────────────┘
                            │ typed invocation
┌───────────────────────────▼──────────────────────────────────┐
│ Cross-model runtime kernel                                  │
│ resolve transport · profiles · dispatch · harvest · resume  │
│ cancel · recover · lifecycle events · telemetry             │
└───────────────────────────┬──────────────────────────────────┘
                            │ artifacts
┌───────────────────────────▼──────────────────────────────────┐
│ Run protocol                                                │
│ run.json · prompt · raw report · synthesis/review/diff      │
│ verification contract · proof outputs · hashes              │
└───────────────────────────┬──────────────────────────────────┘
                            │ evidence
┌───────────────────────────▼──────────────────────────────────┐
│ Human/conductor gate                                        │
│ adjudica · revisa diff · corre proof · commit/push           │
└──────────────────────────────────────────────────────────────┘
```

La frontera clave es la misma que ya tenemos: el runtime ejecuta y reporta; las skills deciden; el
conductor conserva autoridad.

## Mejoras propuestas

### P0.1 — Manifiesto uniforme y telemetría mínima

Agregar un `run.json` producido por `cross-model-orca` y enriquecido por la skill llamadora.

```json
{
  "schemaVersion": 1,
  "runId": "uuid",
  "workflow": "co-explore",
  "mode": "explore",
  "role": "reviewer",
  "family": "codex",
  "model": null,
  "effort": null,
  "transport": {
    "desired": "auto",
    "effective": "orca-session",
    "fallbackUsed": false
  },
  "timing": {
    "startedAt": "ISO-8601",
    "finishedAt": "ISO-8601",
    "durationMs": 123456
  },
  "outcome": {
    "status": "ready",
    "code": 0,
    "rounds": 1,
    "recovered": null
  },
  "usage": {
    "inputTokens": null,
    "outputTokens": null,
    "costUsd": null,
    "source": "unavailable"
  },
  "artifacts": [
    { "kind": "prompt", "path": "prompt.md", "sha256": "..." },
    { "kind": "report", "path": "findings-codex.md", "sha256": "..." }
  ]
}
```

Reglas:

- `durationMs`, outcome y transporte son obligatorios.
- Tokens/costo son nullable; nunca estimarlos ni mezclar fuentes incompatibles.
- Registrar la procedencia de cada métrica.
- No guardar razonamiento interno; solo datos operacionales y artefactos autorizados.
- El manifest se escribe atómicamente y se finaliza incluso en error/abort.

**Beneficio:** habilita benchmark real sin alterar el comportamiento de las skills.

### P0.2 — Contrato de verificación antes del dispatch

Para `cross-implement` y `sdd-flow` normal/complex, congelar antes de implementar:

```markdown
## Verification contract

| ID | AC | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| V1 | AC-1 | test | npm test -- --run foo.spec.ts | exit 0, test X passes | RED |
| V2 | AC-2 | build | npm run build | exit 0 | N/A |
| V3 | AC-3 | manual | viewport 390x844 | CTA visible | pending |
```

Flujo:

1. El conductor deriva el contrato desde spec/plan/tasks.
2. Lo revisa antes de delegar; no contiene decisiones abiertas.
3. Corre baseline solo donde deba existir señal RED.
4. Si baseline ya es GREEN, clasifica `already_satisfied | weak_check | invalid_assumption`.
5. Congela el contrato y lo incluye en el work order.
6. El implementador no puede modificarlo.
7. El conductor vuelve a correr cada prueba y mantiene `sdd-flow verify` como autoridad final.

No crear un `gate.py` arbitrario por defecto. Preferir comandos existentes, tests específicos y
observaciones declarativas. Si se genera un helper ejecutable, debe pasar revisión del conductor,
allowlist de comandos, sandbox sin red, dependencias vacías y timeout estricto.

### P0.3 — Triage de propiedad antes de gastar otra ronda

Agregar una clasificación obligatoria cuando la misma prueba falla repetidamente:

| Clase | Acción | Consume fix round del implementador |
|---|---|---|
| `IMPLEMENTATION_DEFECT` | Feedback concreto a la misma sesión. | Sí |
| `VERIFICATION_DEFECT` | Corregir/versionar el contrato; re-run gratuito. | No |
| `ENVIRONMENT_FAILURE` | Reparar/preparar entorno o marcar blocked. | No |
| `DESIGN_GAP` | Volver a plan/spec; no seguir parchando. | No |

El conductor realiza el triage. No hace falta otro agente por default. En un caso ambiguo y costoso,
puede pedir una opinión cross-model read-only.

### P0.4 — Prompts como assets versionados

Extraer las plantillas ejecutables hoy embebidas en `reference.md` a archivos, por ejemplo:

```text
skills/cross-model-orca/assets/prompts/
├── explore.md
├── counter-plan.md
├── investigate.md
├── debate-round-0.md
├── debate-cross.md
├── review.md
├── implement.md
└── fix.md
```

El renderer debe:

- validar placeholders faltantes;
- producir el mismo prompt para CLI y Orca;
- calcular `promptVersion`/SHA-256;
- permitir golden tests;
- mantener el output contract separado del transporte.

`SKILL.md` conserva reglas y routing. `reference.md` documenta contratos. Los assets contienen la
entrada exacta que recibe el secundario.

### P1.1 — Eventos de lifecycle y cancelación

Emitir JSONL opcional desde el runner:

```text
session_created
boot_wait
dispatched
working
harvesting
promoted
completed | aborted | failed
```

Cada evento debe incluir `runId`, timestamp, family, role y transport. El caller puede renderizar
una línea, una UI rica o nada. La portabilidad queda intacta.

La cancelación debe reutilizar la recuperación existente: para rol write no se habilita fallback
ni otro escritor hasta demostrar cierre/idle. Fusion acierta al distinguir “detenido por usuario”
de “falló el modelo”; debemos conservar esa atribución.

### P1.2 — Perfiles de ejecución, no modelos ganadores

Agregar perfiles semánticos opcionales:

| Perfil | Uso | Política sugerida |
|---|---|---|
| `economy` | smoke, tareas normales, exploración amplia | esfuerzo medio, deadline corto |
| `deep` | high-risk, arquitectura, disputa no resuelta | esfuerzo alto, deadline mayor |
| `inherit` | default portable | heredar configuración activa |

El modelo efectivo se descubre y registra. La familia opuesta sigue siendo obligatoria. No duplicar
en config una lista de IDs que caduca cada trimestre.

### P1.3 — Artifact protocol común

Unificar nombres mínimos por workflow:

```text
<workflow-run>/
├── run.json
├── prompt.md
├── source-context.json
├── raw-report.md
├── result.md
├── rounds/
│   └── 01.json
└── proofs/
    └── V1.txt
```

Los paths públicos de cada skill pueden mantenerse para compatibilidad. El manifest los referencia;
no hace falta migrar todo de una vez.

### P2.1 — Evals de relatividad sobre nuestro trabajo

Formalizar los smokes recientes como dataset pequeño y repetible:

- exploración de feature acotada;
- revisión de plan con defectos sembrados;
- implementación desde work order congelado;
- timeout y recovery;
- reporte grande;
- gate defectuoso;
- drift fuera de alcance;
- Windows/POSIX.

Métricas:

| Métrica | Qué responde |
|---|---|
| `wall_ms` | ¿Cuánto tarda el workflow completo? |
| `secondary_ms` | ¿Cuánto consume la otra familia? |
| `accepted_findings / findings` | ¿La segunda opinión aporta señal? |
| `fix_rounds` | ¿El work order era suficiente? |
| `verification_defects` | ¿Nuestros gates producen falsos rojos/verdes? |
| `fallback_rate` | ¿Qué tan estable es el transporte preferido? |
| `recovery_failure_rate` | ¿Hay riesgo de doble escritor? |
| `drift_hunks` | ¿El implementador respeta alcance? |
| `human_interventions` | ¿El workflow reduce o desplaza trabajo? |
| `cost_usd` | Solo cuando el provider lo reporta de forma confiable. |

La decisión “usar workhorse o deep” debe salir de estas corridas, no de benchmarks externos.

## Cambios concretos por archivo

| Archivo | Cambio sugerido |
|---|---|
| `skills/cross-model-orca/assets/orca-session.mjs` | Añadir `runId`, timestamps, `durationMs`, outcome normalizado y hooks de lifecycle. |
| `skills/cross-model-orca/assets/run-orca-session.mjs` | Emitir resultado/manifest en JSON estable y soportar abort explícito. |
| `skills/cross-model-orca/assets/run-manifest.mjs` | Nuevo módulo: schema, escritura atómica, hashes y finalización en error. |
| `skills/cross-model-orca/assets/prompts/` | Nuevos templates canónicos compartidos por CLI/Orca. |
| `skills/cross-model-orca/assets/test/` | Golden tests de prompts, manifest, abort, métricas y crash paths. |
| `skills/co-explore/SKILL.md` | Referenciar manifest y política de sesión; no cambiar su síntesis humana. |
| `skills/cross-review/SKILL.md` | Registrar rounds/findings/adjudicación en manifest. |
| `skills/cross-implement/SKILL.md` | Exigir verification contract congelado y triage de propiedad de fallas. |
| `skills/cross-implement/reference.md` | Definir baseline, categorías de falla y reparación versionada del contrato. |
| `skills/sdd-flow/SKILL.md` | Crear/fijar verification contract antes de `implement`; `verify` lo consume y sigue siendo autoridad. |
| `skills/sdd-flow/reference.md` | Plantilla del contrato y evidencia de baseline/final. |

## Secuencia de implementación recomendada

### Fase 1 — Solo observabilidad

1. `run.json` y `durationMs` en `cross-model-orca`.
2. Tests unitarios y de crash paths.
3. Consumo opcional desde las tres skills.
4. Ningún cambio de gates, sesiones o permisos.

**Salida:** datos reales sin riesgo funcional.

### Fase 2 — Pilotear gate-first en `cross-implement`

1. Añadir verification contract al work order.
2. Ejecutar baseline antes del dispatch.
3. Añadir triage de ownership antes de la última ronda.
4. Probar en work orders normales y complejos, no triviales.

**Salida:** comprobar si reduce fixes y falsos “IMPLEMENTED”.

### Fase 3 — Integrar con `sdd-flow`

1. Generar el contrato desde AC y Verification del plan.
2. Reusar el mismo contrato en `cross-implement` y `verify`.
3. Persistir baseline y evidencia final en `plan.md`/artifacts.
4. Mantener gates humanos y revert-to-confirm.

### Fase 4 — Decidir UX y perfiles con datos

1. Evaluar lifecycle events, status y cancelación.
2. Comparar `economy` vs `deep` sobre evals reales.
3. Considerar un fuser opt-in solo si las síntesis grandes muestran dolor concreto.

## Criterios de aceptación para esta evolución

1. Toda corrida cross-model genera un manifest final, incluso si falla o se aborta.
2. `durationMs`, transporte efectivo, rol, familia, status y recovery son verificables.
3. CLI y Orca renderizan el mismo prompt a partir del mismo template/version.
4. `cross-implement` no despacha sin verification contract y baseline resueltos.
5. Un defecto del contrato no consume ronda del implementador ni habilita gate gaming.
6. El conductor sigue corriendo la prueba y leyendo el diff completo.
7. Ningún modo agrega escritores concurrentes sobre el mismo working tree.
8. Tokens/costo ausentes permanecen `null`, nunca estimados.
9. La suite existente sigue verde y añade cobertura de manifest/gate/abort.
10. Ningún artefacto público filtra nombres de modelos ni mecánica interna del workflow.

## Decisión final: keep, adapt, reject

### Keep

- separación `co-explore` / `cross-review` / `cross-implement`;
- `sdd-flow` como autoridad y SDLC;
- familia opuesta por construcción;
- clean-tree y escritor único;
- diff y pruebas frescas como verdad;
- sesiones frescas o acotadas al workflow;
- transporte portable con fallback;
- gates humanos;
- seguridad y suite de `cross-model-orca`.

### Adapt

- gate/verification contract antes del build;
- baseline RED explícito;
- triage de implementación vs verificación vs entorno vs diseño;
- reparación versionada del contrato sin gastar ronda;
- manifest por corrida;
- telemetría y benchmarking relativo;
- prompts separados y hasheados;
- lifecycle events y cancelación atribuida;
- perfiles semánticos de esfuerzo.

### Reject

- migración completa a Pi;
- monolito único para workflow, transporte y UI;
- dos escritores concurrentes en el mismo cwd;
- ejecución ciega de Python generado;
- memoria persistente global por rol como default;
- IDs de modelos hardcodeados como arquitectura;
- tercer fuser obligatorio;
- aceptar un PASS cuyo baseline ya era GREEN sin adjudicación.

## Fuentes principales

- [Fusion Harness README, snapshot analizado](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/README.md)
- [Runtime `fusion-harness.ts`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/extensions/fusion-harness/fusion-harness.ts)
- [Prompts del validator y triage](https://github.com/disler/fusion-harness/tree/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/extensions/fusion-harness)
- [Artefactos del demo SOTA](https://github.com/disler/fusion-harness/tree/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/live_final_generation)
- [Video del autor](https://www.youtube.com/watch?v=AQl5Q-0l7FQ)
- `skills/cross-model-orca/`
- `skills/co-explore/`
- `skills/cross-review/`
- `skills/cross-implement/`
- `skills/sdd-flow/`
- `docs/research/cross-model-real-sessions/`

## Próximo paso recomendado

No editar todavía las skills de comportamiento. El primer cambio debería ser un SDD acotado a
**manifiesto + duración + lifecycle mínimo en `cross-model-orca`**, porque entrega datos para decidir
el resto y no altera autoridad, permisos, prompts ni gates. Después, con telemetría disponible,
pilotear el verification contract gate-first únicamente en `cross-implement`.
