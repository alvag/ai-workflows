# sdd-co-explore — exploración paralela cross-model (diseño)

**Fecha:** 2026-07-03
**Estado:** diseño aprobado en conversación; pendiente de plan de implementación.

## Problema

En el flujo actual de `sdd-flow`, el agente conductor explora el código solo: arma el contexto
(`gather-context`), investiga los archivos, forma hipótesis y escribe la spec. Recién ahí el
revisor cross-model (`sdd-cross-review`) ve el artefacto — llega **frío**, sin exploración
propia, y ancla en el framing del autor. Su crítica es reactiva: solo puede desafiar lo que está
escrito, no lo que falta porque nadie lo miró.

## Objetivo

Balanceado entre tres beneficios (ninguno domina):

1. **Crítica informada** — el revisor critica spec y plan con contexto propio del código.
2. **Dos mapas independientes** — hallazgos, riesgos y enfoques que un solo modelo se pierde;
   las *diferencias* entre los mapas son la señal más valiosa.
3. **Paralelismo** — el revisor explora mientras el conductor explora; no se agrega latencia
   secuencial al flujo.

## Decisiones tomadas

| Decisión | Elección | Alternativas descartadas |
|---|---|---|
| Arquitectura | **Skill nueva `sdd-co-explore`**, hermana de las SDD | (A) extender `sdd-cross-review` con modo explore; (B) implementarlo dentro de `sdd-flow` |
| Punto de convergencia | **Temprana: en hallazgos**, antes de escribir la spec | Dual-spec (cada uno escribe su spec y se mergea): caro, difícil de mergear, dos documentos para arbitrar |
| Alcance | **Spec + plan** en `sdd-flow`; **master-spec + reparto** en `sdd-orchestrator` (sección 8) | Incluir tasks: descomposición mecánica, costo sin señal |
| Activación | **Sub-clave `cross_review.co_explore`** con default por complejidad | Acoplada 1:1 a cross_review; config independiente de primer nivel |

Principio rector: **divergir en la investigación, converger antes de decidir.** Los hallazgos se
mergean fácil (hechos + hipótesis); las specs no (decisiones ya tomadas).

## Diseño

### 1. Inserción en el ciclo SDD

```
gather-context ──► co-explore (ambos exploran EN PARALELO) ──► síntesis ──► specify ──► gate (crítica informada)
                     │ revisor: sdd-co-explore en background          (spec integra
                     │ conductor: su exploración de siempre            ambos mapas)
                     ▼
   ... spec aprobada → create-branch → [counter-plan del revisor] → plan ──► gate (crítica informada)
```

- **Pre-spec:** tras confirmar contexto y clasificación en `gather-context`, si co-explore está
  activo, `sdd-flow` arma el **paquete de contexto** (digest del ticket, prompt del usuario,
  complejidad) y despacha `sdd-co-explore` en background. Mientras el revisor explora, el
  conductor hace su propia exploración.
- **Punto de encuentro:** cuando ambos terminan (o vence el deadline del revisor), intercambio
  de informes y síntesis. Recién ahí el conductor escribe `spec.md`.
- **Pre-plan (`counter-plan`):** con la spec aprobada, el revisor —que ya tiene mapa propio—
  produce un contra-enfoque (qué tocaría, qué reusaría, en qué orden, riesgos). El conductor lo
  contrasta con el suyo, sintetiza y escribe `plan.md`.
- **`analyze` no desaparece:** pasa a ser refresco incremental post-`create-branch` (validar que
  el mapa pre-spec sigue vigente sobre el HEAD real de la rama), en lugar de la exploración
  profunda actual.
- **Tasks:** sin cambios (cross-review actual).

### 2. Contrato de `sdd-co-explore`

**Inputs** (de `sdd-flow`, o del usuario en modo directo):

- `mode`: `explore` (pre-spec) | `counter-plan` (pre-plan; recibe la spec aprobada + el propio
  `findings-<familia>.md` de la fase explore como contexto — con resume oportunista del thread
  si `session.json` lo permite, o sesión fresca con esos archivos si no)
- `context_package`: digest del ticket + prompt + AC preliminares si existen
- `working_dir`, `complexity`, `execution` — heredados igual que en cross-review

**Output:** informe estructurado en `.plans/<id>/co-explore/findings-<familia>.md` con secciones
fijas (el formato fijo es lo que hace barata la síntesis):

- **Mapa** — archivos/módulos relevantes con `path:line`
- **Hipótesis** — qué está pasando / cómo encaja el cambio
- **Puntos de reúso** — qué ya existe y se aprovecha
- **Riesgos** — qué puede romperse, deuda que estorba
- **Incógnitas** — preguntas abiertas que no pudo determinar (candidatas a `clarify`)
- **Supuestos** — qué asumió para poder seguir explorando, y por qué
- **Enfoque sugerido** — 3-5 bullets (en `counter-plan`, esta sección es el cuerpo principal)

**Dudas del explorador en background:** el revisor corre no-interactivo y read-only — no puede
preguntar a mitad de la exploración, y **nunca se bloquea esperando una respuesta**. El prompt lo
instruye: toda duda se registra (pregunta abierta → *Incógnitas*; decisión tomada para avanzar →
*Supuestos*) y se sigue explorando. En la síntesis, el conductor mergea las incógnitas de ambos
mapas; las que cambiarían el diseño alimentan `clarify` (obligatorio en complejos), y las
respuestas quedan en `## Clarifications` de la spec — el revisor las recibe al momento de la
crítica, donde además puede marcar si alguno de sus supuestos resultó equivocado.

Más una referencia de sesión opcional (`co-explore/session.json`) para el resume oportunista.

### 3. Independencia (regla anti-anclaje)

Regla dura: **ambos parten del mismo paquete de contexto y no ven nada del otro hasta que ambos
terminaron.** El conductor no lee `findings-<familia>.md` hasta cerrar su propia exploración, y
su informe (`findings-<familia-conductor>.md`, mismo formato) queda escrito **antes** de leer el
del revisor. La síntesis produce una tabla corta de **convergencias / divergencias**; las
divergencias no resueltas no se esconden: se presentan en un **checkpoint informativo** previo a
escribir la spec (no es un gate SDD y solo ocurre si hay divergencias sin resolver; si los mapas
convergen, se sigue directo a `specify` sin stop extra).

**Competencia de enfoques (síntesis ≠ solo mergear hechos).** Los dos *Enfoques sugeridos*
compiten: el conductor los evalúa en méritos (reúso, riesgo, simplicidad, encaje con el repo),
elige uno o hibrida, y **registra el porqué en `synthesis.md`** — la solución de uno puede ser
mejor que la del otro, y esa evaluación debe quedar auditable, no implícita. Si ambos enfoques
son viables pero materialmente distintos, es una divergencia: se presenta en el checkpoint
informativo para que el usuario decida. El `counter-plan` pre-plan es la segunda ronda de esta
competencia, ya con la spec aprobada como marco.

### 4. Integración con `sdd-cross-review` (crítica informada)

Base **stateless, por convención de archivos** — cero acoplamiento entre skills:

- En los gates de spec/plan, `sdd-flow` pasa el informe del revisor como `context_paths`
  adicional a `sdd-cross-review`. **El informe es el contexto persistente**: la crítica sale
  informada aunque no haya sesión que reanudar. Cross-review no sabe que co-explore existe.
- **Mejora oportunista:** si `co-explore/session.json` existe y el runtime del revisor soporta
  resume, cross-review reanuda ese thread (el crítico es el mismo agente que exploró). Si el
  resume falla → cae a la base stateless.
- El contra-enfoque también se pasa como contexto a la crítica del plan: el crítico verifica si
  el plan final consideró su propuesta, en vez de repetirla como finding.

### 5. Descubrimiento del revisor (sin duplicar)

`sdd-co-explore` necesita el mismo "Paso 0" que cross-review (familia del autor, sondas de
entorno, vías de invocación, higiene de entorno). Una sola fuente canónica con fallback:

- El algoritmo canónico sigue en `sdd-cross-review/reference.md → "Descubrir el revisor"`;
  `sdd-co-explore` lo referencia por puntero y lo lee de ahí cuando esa skill está instalada.
- Si co-explore está instalada sin cross-review, usa un **fallback mínimo embebido**: regla de
  familia + sonda de entorno + invocación directa del CLI del revisor en read-only.

### 6. Config y activación

```yaml
cross_review:
  mode: auto              # crítica en gates (comportamiento actual)
  co_explore:
    mode: auto            # auto | "on" | "off"  → exploración paralela + counter-plan
    deadline: 600         # segundos, opcional (default propuesto: 600 explore / 300 counter-plan;
                          # una exploración tarda más que una crítica — topes exactos en reference.md)
```

- `mode: auto` = por complejidad: **complejo on, normal opt-in (off salvo pedido), trivial
  nunca** — misma política que cross-review.
- Override conversacional de la corrida: "con co-exploración" / "sin co-exploración" (entra al
  router de `sdd-flow` como los demás overrides).
- Las dos claves son **ortogonales**: `co_explore` gobierna exploración + contra-enfoque;
  `cross_review.mode` gobierna las críticas en gates. Quien lee ambas y orquesta es `sdd-flow`.

### 7. Degradación (nunca bloquea) y artefactos

Mismo patrón del ecosistema — aviso de una línea + el flujo sigue:

1. Skill no instalada → `sdd-flow` la omite y sigue el flujo actual.
2. Sin revisor de otra familia → `UNAVAILABLE`; el conductor explora solo.
3. Deadline vencido → se sigue con los hallazgos del conductor; se registra; la crítica del
   gate cae al modo frío actual.
4. Informe no parseable → se registra y se degrada (texto libre como contexto, o descarte si es
   ruido).

En disco, local y untracked (regla #10 de `sdd-flow`):

```
.plans/<id>/co-explore/
├─ findings-codex.md     # informe del revisor
├─ findings-claude.md    # informe del conductor (escrito ANTES de leer el otro)
├─ synthesis.md          # convergencias/divergencias + qué decidió el conductor (audit trail)
└─ session.json          # ref del thread del revisor (opcional, para resume oportunista)
```

(Los nombres `findings-codex.md`/`findings-claude.md` son ilustrativos: el sufijo es la familia
real de cada lado, resuelta por la sonda de entorno.)

### 8. Soporte en `sdd-orchestrator` (multi-repo)

El orquestador aplica el mismo patrón sobre sus dos artefactos de Fase 1, que ya se revisan como
`complex`:

- **Pre-`master-spec` (`mode: explore`):** tras la **selección de repos confirmada** (el revisor
  necesita saber dónde explorar), `sdd-orchestrator` despacha `sdd-co-explore` con el paquete de
  contexto global y el conjunto de repos confirmados como `working_dir`s. Ambos exploran
  **cross-repo** en paralelo; el foco del informe se corre a nivel sistema: contratos entre
  servicios existentes, superficies de integración, riesgos `[integration]`. Si el revisor
  descubre señales de que **otro repo no confirmado** está involucrado, lo registra en
  *Riesgos/Incógnitas* — en la síntesis eso puede llevar a re-abrir la selección de repos con el
  usuario antes de escribir la `master-spec.md`.
- **Pre-reparto (`mode: counter-plan`):** análogo al counter-plan de `sdd-flow` — con la
  `master-spec.md` aprobada, el revisor propone su propio **reparto tentativo** (qué repo cubre
  qué AC, dependencias entre repos, orden) que el conductor contrasta antes de escribir el
  reparto real. Los errores de DAG y cobertura AC↔repo son justo donde una segunda mirada paga.
- **Artefactos:** en `.sdd/<id>/co-explore/` (mismos nombres que en `sdd-flow`), local y
  untracked como el resto de `.sdd/`.
- **Config:** misma sub-clave `cross_review.co_explore` pero en el `manifest.yml` de la
  orquestación. Default `auto` = **on** (los artefactos de orquestación son el caso complejo por
  definición, igual que su cross-review). Deadlines mayores que en `sdd-flow` (exploración
  multi-repo).
- **Sin doble co-exploración:** la Fase 2 delega a `sdd-flow` con `cross_review.mode: off`, lo
  que también apaga `co_explore` en los flujos por-repo (la exploración global ya cubrió ese
  terreno; misma lógica anti-redundancia que el review en capas).

## Cambios requeridos por skill

- **`sdd-co-explore` (nueva):** `SKILL.md` (contrato, modos, loop de exploración, independencia,
  degradación, router de intención), `reference.md` (prompt de exploración por modo, formato del
  informe, plantilla de `synthesis.md`, fallback de descubrimiento, portabilidad POSIX/
  PowerShell, deadlines), `README.md`.
- **`sdd-flow`:** hook post-`gather-context` (despacho en background + exploración propia +
  síntesis + checkpoint de divergencias), `analyze` como refresco incremental, paso de
  `context_paths` extra a cross-review en gates de spec/plan, invocación `counter-plan`
  pre-`plan`, clave `co_explore` en el esquema de config, override conversacional en el router,
  eco del checkpoint de inicio (sumar `co_explore` a los valores ecoados).
- **`sdd-cross-review`:** sin cambios estructurales; documentar la aceptación de
  `context_paths` de co-explore y el resume oportunista vía `session.json`.
- **`sdd-orchestrator`:** despacho de `explore` post-selección de repos y `counter-plan`
  pre-reparto (sección 8), clave `co_explore` en el esquema del `manifest.yml`, artefactos en
  `.sdd/<id>/co-explore/`, propagación del apagado a los `sdd-flow` delegados.

## Fuera de alcance

- Aporte paralelo en **tasks** (descartado: costo sin señal).
- Conformance cross-model pre-commit (ya descartado en `sdd-flow`, sin cambios).

## Criterios de éxito

1. En un flujo *complejo* con Codex disponible, la spec presenta la síntesis con convergencias/
   divergencias de dos exploraciones independientes, y la crítica del gate referencia hallazgos
   del propio mapa del revisor.
2. En el gate del plan, existe un contra-enfoque del revisor previo a `plan.md` y la crítica
   verifica su consideración.
3. Con Codex ausente o vencido el deadline, el flujo completo funciona igual que hoy, con un
   aviso de una línea.
4. `.plans/<id>/co-explore/` reconstruye la corrida completa (informes, síntesis, decisiones),
   incluida la evaluación de enfoques en competencia.
5. En una orquestación multi-repo, la `master-spec.md` nace de dos exploraciones cross-repo
   independientes y el reparto se contrasta contra un reparto tentativo del revisor; los flujos
   por-repo delegados no re-exploran.
