# sdd-co-explore

**Exploración paralela cross-model** para flujos de Spec-Driven Development. Antes de que el
conductor escriba `spec.md` (modo `explore`) o `plan.md` (modo `counter-plan`), un modelo de
**otra familia que el autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) explora
el mismo código en background, read-only, y devuelve su propio informe estructurado — mientras el
conductor hace su exploración de siempre, en paralelo, sin esperas secuenciales.

## Qué es

`sdd-co-explore` despacha, antes de que existan decisiones escritas, un segundo mapa del terreno:
archivos relevantes, hipótesis, puntos de reúso, riesgos, incógnitas y un enfoque sugerido — en el
mismo formato que produce el conductor. El resultado es `READY` (con el informe en
`co-explore/findings-<familia>.md` para `explore`, o `co-explore/counter-plan-<familia>.md` para
`counter-plan`) o `UNAVAILABLE` (degradado, sin bloquear nunca el flujo SDD).

```
paquete de contexto ──► [sdd-co-explore: revisor explora en background, read-only]
                              │                        (el conductor explora en paralelo
                              ▼                         por su cuenta — no espera)
                    findings-<familia>.md ──► síntesis del conductor ──► spec/plan
```

El valor no es que el explorador "ayude": es que produce un mapa **independiente**, sin ver nada
de lo que el conductor ya pensó, para que las diferencias entre los dos mapas salgan a la luz
antes de que las decisiones queden tomadas. Dos exploraciones convergen fácil (son hechos +
hipótesis); dos specs no (son decisiones ya tomadas) — por eso el punto de encuentro es temprano,
en los hallazgos, no al final. La síntesis la hace el conductor: compara ambos informes, hace
competir los enfoques en méritos y decide con rationale auditable en `synthesis.md`.

Ese mismo informe, además, alimenta más adelante la **crítica informada** de `sdd-cross-review`:
si esa skill está instalada, recibe `findings-<familia>.md` (y `session.json`, si existe) como
contexto persistente del gate, en vez de partir de cero. `sdd-co-explore` **no revisa artefactos
escritos** — eso lo hace `sdd-cross-review`; esta skill produce hallazgos e hipótesis propios que
compiten con los del conductor, no una crítica de lo que el conductor ya escribió.

## Cuándo usarla

- La invocan `sdd-flow` y `sdd-orchestrator` cuando `cross_review.co_explore` está activo (modo
  embebido, post-`gather-context` o pre-`plan`/reparto).
- Modo directo: `/sdd-co-explore <ticket|descripción>` → infiere `mode: explore`, corre y presenta
  el informe.
- Pedidos en lenguaje natural: "que Codex explore esto en paralelo" → mismo flujo que el modo
  directo.
- Override conversacional en una corrida de `sdd-flow`/`sdd-orchestrator`: "con co-exploración" /
  "sin co-exploración" → fuerza `mode: on`/`off` para esa corrida.

## Cuándo NO usarla

- **Para revisar artefactos ya escritos** (`spec.md`, `plan.md`, `tasks.md`, reparto): eso es
  `sdd-cross-review`. `sdd-co-explore` corre **antes** de que el artefacto exista.
- **Para reemplazar la exploración del conductor:** no la sustituye, corre en paralelo con ella —
  el conductor siempre escribe su propio informe.
- **En cambios triviales:** el default por complejidad es "nunca" (ver "Configuración"); no aporta
  frente al costo de una segunda exploración completa.

## Requisitos

Ninguno obligatorio: es una **capacidad opcional**. Para que la exploración efectivamente ocurra,
hace falta un **segundo modelo de otra familia que el autor** (el agente que conduce la skill):

- Autor Claude (Claude Code) → Codex, vía `codex exec -s read-only` en el PATH.
- Autor GPT/Codex (Codex CLI) → Claude, vía `claude -p --allowedTools=Read,Grep,Glob` en el PATH.
- o cualquier otro segundo modelo de familia distinta capaz de explorar en modo read-only.

**`sdd-cross-review` recomendada (no obligatoria).** Si está instalada en el entorno, aporta el
algoritmo canónico de descubrimiento del revisor (`sdd-cross-review/reference.md` → "Descubrir el
revisor"), la higiene de entorno completa cuando el autor está redirigido a un modelo no-Anthropic,
y consume el informe de esta skill como contexto persistente para su propia crítica informada en
el gate. Sin ella, `sdd-co-explore` usa su propio fallback mínimo (mismo algoritmo de descubrimiento
por capacidad, sondeo de entorno incluido, pero sin la higiene de entorno completa).

Sin ningún modelo de otra familia disponible, con `mode: off`, o ante un fallo en runtime, la skill
devuelve `UNAVAILABLE` en una línea y la llamadora sigue con la exploración del conductor solamente.

## Instalación

Copia (o symlinkea) la carpeta `sdd-co-explore/` al directorio de skills de tu entorno, junto a
`sdd-flow/` y, si la usas, `sdd-cross-review/`:

```
<skills>/
├─ sdd-flow/
├─ sdd-cross-review/     # opcional, recomendada
└─ sdd-co-explore/
   ├─ SKILL.md
   ├─ reference.md
   └─ README.md
```

## Configuración

Clave bajo `cross_review` en `.specify/config.yml` (`sdd-flow`) o en el `manifest.yml` de la
orquestación (`sdd-orchestrator`):

```yaml
cross_review:
  co_explore:
    mode: auto        # auto (por complejidad: complejo on, normal opt-in, trivial nunca) | "on" | "off"
    deadline: 600     # segundos (explore; counter-plan usa 300 salvo override)
```

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default por complejidad**. `co_explore` es **ortogonal** a `cross_review.mode`: esta clave
gobierna la exploración paralela y el contra-enfoque; `cross_review.mode` gobierna las críticas en
los gates. Detalle completo en `SKILL.md` → "Configuración".

## Ejemplos de uso

**1. Embebida por sdd-flow en un cambio complejo (automático):** al clasificar el cambio como
*complejo*, `sdd-flow` invoca esta skill con `mode: explore` en el gate post-`gather-context`
(default `complex`: on). El explorador corre en background mientras `sdd-flow` hace su propia
exploración; en el punto de encuentro, ambos informes se sintetizan (convergencias/divergencias +
duelo de enfoques) antes de escribir `spec.md`.

**2. Override conversacional en un cambio normal:**
```
/sdd-flow empezar PROJ-128: exportar resultados a CSV desde la tabla de reportes, con co-exploración
```
→ *normal* es opt-in por defecto (off salvo pedido); el override activa `mode: on` para esa
corrida, y `sdd-flow` lo registra.

**3. Modo directo:**
```
/sdd-co-explore PROJ-123
```
→ infiere `mode: explore`, arma el `context_package` desde el ticket (si hay clave y MCP
disponible) y el prompt del usuario, lanza el explorador y presenta el informe al usuario.

## Archivos

- `SKILL.md` — el flujo, las reglas, el contrato de invocación y la guía de síntesis.
- `reference.md` — prompts de exploración por modo, formato del informe, plantilla de
  `synthesis.md`, descubrimiento del revisor, latencia y deadlines, archivos de trabajo.
- `README.md` — este archivo.
