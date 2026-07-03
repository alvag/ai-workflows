# co-explore

**Exploración paralela cross-model.** Un modelo de **otra familia que el autor** (Codex cuando
conduce Claude; Claude cuando conduce Codex) explora el mismo código en background, read-only, y
devuelve su propio informe estructurado — mientras el conductor hace su exploración de siempre, en
paralelo, sin esperas secuenciales — y al final el conductor **sintetiza** los dos mapas
independientes.

## Qué es

`co-explore` despacha un segundo mapa del terreno, independiente del que arma el conductor, para
que las diferencias entre ambos salgan a la luz antes de decidir. Sirve para tres cosas, según
`mode`:

- **`explore`** (pre-spec, lo invoca SDD): mapear el terreno antes de una `spec.md` — archivos
  relevantes, puntos de reúso, riesgos, enfoque sugerido.
- **`counter-plan`** (pre-plan/pre-reparto, lo invoca SDD): un contra-enfoque propio para una spec
  aprobada.
- **`investigate`** (standalone, fuera de SDD): investigar un bug — dos modelos forman hipótesis
  de causa raíz por su lado y el conductor las sintetiza en **hipótesis rankeadas + plan de
  verificación**. No arregla ni verifica ejecutando como parte de la skill.

El resultado es `READY` (con el informe en `co-explore/findings-<familia>.md`,
`counter-plan-<familia>.md` o `investigate-<familia>.md`) o `UNAVAILABLE` (degradado, sin bloquear
nunca a la llamadora).

```
paquete de contexto ──► [co-explore: revisor explora en background, read-only]
                              │                        (el conductor explora en paralelo
                              ▼                         por su cuenta — no espera)
                    informe-<familia>.md ──► síntesis del conductor ──► spec / plan / conclusión
```

El valor no es que el explorador "ayude": es que produce un mapa **independiente**, sin ver nada
de lo que el conductor ya pensó, para que las diferencias salgan a la luz antes de que las
decisiones queden tomadas. Dos exploraciones convergen fácil (son hechos + hipótesis); dos
conclusiones ya tomadas no — por eso el punto de encuentro es temprano, en los hallazgos. La
síntesis la hace el conductor: compara ambos informes, hace competir enfoques (o hipótesis de
causa raíz, en `investigate`) en méritos, y decide con rationale auditable en `synthesis.md`.

En los modos SDD, ese mismo informe alimenta más adelante la **crítica informada** de
`sdd-cross-review`: si esa skill está instalada, recibe `findings-<familia>.md` (y `session.json`,
si existe) como contexto persistente del gate, en vez de partir de cero. `co-explore` **no revisa
artefactos escritos** (eso es `sdd-cross-review`) **ni arregla el bug** (eso es
`superpowers:systematic-debugging`): produce hallazgos e hipótesis propios que compiten con los
del conductor.

## Cuándo usarla

- La invocan `sdd-flow` y `sdd-orchestrator` (modos `explore`/`counter-plan`) cuando
  `cross_review.co_explore` está activo (modo embebido, post-`gather-context` o pre-`plan`/reparto).
- Modo directo `explore`: `/co-explore <ticket|descripción>` → corre la síntesis y presenta la
  conclusión.
- Modo directo `investigate`: `/co-explore <bug>` o "que Codex investigue este bug en paralelo" →
  dos modelos investigan la causa raíz, el conductor sintetiza hipótesis rankeadas + plan de
  verificación, y ofrece el handoff a `systematic-debugging`.
- Pedidos en lenguaje natural: "que Codex explore/investigue esto en paralelo".
- Override conversacional en una corrida de `sdd-flow`/`sdd-orchestrator`: "con co-exploración" /
  "sin co-exploración" → fuerza `mode: on`/`off` para esa corrida.

## Cuándo NO usarla

- **Para revisar artefactos ya escritos** (`spec.md`, `plan.md`, `tasks.md`, reparto): eso es
  `sdd-cross-review`. `co-explore` corre **antes** de que el artefacto exista.
- **Para arreglar o verificar el bug** (en `investigate`): la skill termina en hipótesis + plan de
  verificación; verificar/arreglar es `superpowers:systematic-debugging`, el paso siguiente.
- **Para reemplazar la exploración del conductor:** no la sustituye, corre en paralelo con ella —
  el conductor siempre escribe su propio informe.
- **En cambios triviales** (modos SDD): el default por complejidad es "nunca" (ver "Configuración");
  no aporta frente al costo de una segunda exploración completa.

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
el gate. Sin ella, `co-explore` usa su propio fallback mínimo (mismo algoritmo de descubrimiento
por capacidad, sondeo de entorno incluido, pero sin la higiene de entorno completa).

Sin ningún modelo de otra familia disponible, con `mode: off`, o ante un fallo en runtime, la skill
devuelve `UNAVAILABLE` en una línea y la llamadora sigue con la exploración del conductor solamente.

## Instalación

Copia (o symlinkea) la carpeta `co-explore/` al directorio de skills de tu entorno, junto a
`sdd-flow/` y, si la usas, `sdd-cross-review/`:

```
<skills>/
├─ sdd-flow/
├─ sdd-cross-review/     # opcional, recomendada
└─ co-explore/
   ├─ SKILL.md
   ├─ reference.md
   └─ README.md
```

Como `investigate` es standalone (no SDD), conviene instalarla a **scope usuario**
(`~/.claude/skills/` para Claude Code, `~/.agents/skills/` para Codex) en vez de por proyecto:
así está disponible en cualquier repo y es inmune a los worktrees (el cwd deja de importar).

## Configuración

Clave bajo `cross_review` en `.specify/config.yml` (`sdd-flow`) o en el `manifest.yml` de la
orquestación (`sdd-orchestrator`). **Gobierna solo los modos `explore`/`counter-plan`;
`investigate` es standalone y no lee config** (su deadline se overridea conversacionalmente):

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

**3. Modo directo `explore`:**
```
/co-explore PROJ-123
```
→ infiere `mode: explore`, arma el `context_package` desde el ticket (si hay clave y MCP
disponible) y el prompt del usuario, lanza el explorador, corre la síntesis y presenta la
conclusión al usuario.

**4. Modo directo `investigate` (bug, standalone):**
```
/co-explore el selector de fechas tira "Cannot read properties of undefined" al abrir el rango
```
→ infiere `mode: investigate`, arma el `context_package` con el síntoma + evidencia de
reproducción si el conductor la capturó, lanza al revisor read-only mientras el conductor
investiga en paralelo, sintetiza y presenta **hipótesis de causa raíz rankeadas + plan de
verificación**, y ofrece verificar la líder con `systematic-debugging`.

## Archivos

- `SKILL.md` — el flujo, las reglas, el contrato de invocación y la guía de síntesis.
- `reference.md` — prompts de exploración por modo, formato del informe, plantilla de
  `synthesis.md`, descubrimiento del revisor, latencia y deadlines, archivos de trabajo.
- `README.md` — este archivo.
