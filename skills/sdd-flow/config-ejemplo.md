# Ejemplo de `.specify/config.yml`

**Este archivo es una vista.** Está ensamblado de los bloques que cada skill posee:
`sdd-flow/reference.md` → "Esquema" (22 claves), `cross-review/SKILL.md` → "Configuración" (5),
`co-explore/SKILL.md` → "Configuración" (5) y `cross-implement/SKILL.md` → "Configuración" (3).
**Ante discrepancia manda el dueño.** Existe para poder mirar el archivo completo y copiar lo que
sirva; no para ser la autoridad de ninguna clave.

**Copialo entero o por bloques.** Una clave que borres vuelve a su default —salvo las marcadas
`[obl]`, que no tienen uno—, que es lo que la skill aplica cuando la clave está ausente — por eso
este ejemplo no se materializa en tu repo con `init`: un default copiado queda congelado, uno
ausente sigue la skill.

Cada valor lleva una marca, y solo una:

- `[def]` — **copiarla no cambia nada, y borrarla tampoco**: la skill aplica ese mismo valor
  cuando la clave está ausente.
- `[ej]` — **copiarla puede cambiar el comportamiento**, o estar mal para tu proyecto: no hay un
  default único al que volver.
- `[obl]` — **obligatoria si copiás el bloque**: el dueño la declara obligatoria mientras el
  bloque exista. Qué pasa si la borrás no está documentado por el dueño.

## Ejemplo de `.specify/config.yml`

```yaml
# ── sdd-flow: entorno del proyecto (se autodetecta; el ejemplo es de un repo Node) ──
stack: node                      # node | go | rust | python | java | dotnet | other — [ej]
test_cmd: "npm test"             # [ej] comando de tests
build_cmd: "npm run build"       # [ej] omitir si el stack no compila
lint_cmd: "npm run lint"         # [ej] opcional
test_scope_hint: "vitest run {name}"   # [ej] plantilla de COMANDO para acotar tests; {name} = archivo/patrón
default_branch: main             # [ej] rama base; se detecta, nunca se asume main/master

# ── sdd-flow: convenciones ──
branch_format: "{type}/{ticket}-{slug}"  # [def] placeholders {type} {ticket} {slug}
branch_prefix: ""                # [def] reemplaza {type} (p. ej. "feature/"); vacío → prefijo semántico
commit_style: conventional       # conventional | plain — [def]
tracker: jira                    # jira | github | gitlab | linear | none — [ej]
implement_mode: ask              # ask | inline | cross | workers — [def]

# ── sdd-flow: gates opcionales ──
domain_context:
  mode: auto                     # auto | "on" | "off" — [def] leer docs de dominio/ADRs; solo lectura
  context_paths: []              # [def] docs de dominio a leer si existen
  adr_paths: []                  # [def] ADRs vigentes a leer si existen
final_diff_review:
  mode: auto                     # auto (complex/high-risk inline) | "on" | "off" — [def]
vault_archive:                   # requiere la skill `knowledge-vault`; el disparador es esta clave, no la instalación
  mode: auto                     # auto (consulta destino declarado: ofrece activarlo, o descubre y persiste) | "on" | "off" — [def] rescatar el flujo al vault al archivarlo
jira_approval:                   # solo si tracker: jira
  mode: "off"                    # "on" | "off" — [def] publica la spec en Jira y espera aprobación
  subtask_issuetype: auto        # auto | "Subtarea" | "Sub-task" — [def]
  approval_signal: ask           # ask | status:"<estado Jira que cuenta como aprobado>" — [def]

# ── ecosistema cross-model (lo resuelve y ecoa sdd-flow) ──
cross_model:
  schema_version: 1              # [obl] obligatorio si el bloque existe
  families: [claude, codex]      # claude | codex — [ej] allowlist de workers; el conductor no entra
  selection: full                # full | user_choice — [obl] obligatorio con families; sin default
  manifest:                      # formato en cross-review/reference.md → "Manifest de corrida"
    mode: "on"                   # "on" | "off" — [def] registro por corrida de las skills cross-model

# ── dueño: cross-review/SKILL.md → "Configuración" ──
cross_review:
  mode: auto                     # auto (por complejidad) | "on" | "off" — [def]
  execution: auto                # auto (por capacidad del conductor) | sync | background — [def]
  artifacts: [spec, plan, tasks] # [def] qué artefactos revisar
  max_rounds: 3                  # [def] rondas por TANDA, no de la corrida entera
  reviewer: auto                 # auto | claude | codex — [def] solo dentro de families; error canónico en "Descubrir el revisor"

# ── dueño: co-explore/SKILL.md → "Configuración" ──
co_explore:
  mode: auto                     # auto (por complejidad) | "on" | "off" — [def]
  deadline: 600                  # [ej] segundos (explore; counter-plan usa 300 salvo override)
  debate:
    mode: auto                   # auto | "on" | "off" — [def] cuándo se OFRECE el debate
    max_rounds: 3                # [def] tope de rondas de cruce
  tercera_pasada:
    mode: auto                   # auto | "on" | "off" — [def] cuándo se OFRECE la crítica de la síntesis

# ── dueño: cross-implement/SKILL.md → "Configuración" (solo con implement_mode: cross o workers) ──
cross_implement:
  execution: auto                # auto (por tamaño del work order) | sync | background — [def]
  max_fix_rounds: 2              # [def] tope del fix loop antes del takeover
  deadline: 1800                 # [def] segundos; tope duro del wait en background

# ── dueño: knowledge-vault/reference.md → "La capa de configuración" ──
knowledge-vault:
  path_vault: "/Users/alguien/vaults/dev-memory"  # [ej] raíz del vault donde `kv` archiva flujos
```

## Ejemplo de `.specify/workers.yml`

**Esta sección es una vista.** El dueño del esquema es `sdd-flow/reference.md` → "Esquema de
`.specify/workers.yml`". Los valores de modelo y esfuerzo muestran la forma completa; no declaran
defaults.

```yaml
schema_version: 1
roles:
  explore:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
  counter-plan:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
  investigate:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
  debate:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
  design-review:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
  implement:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
  refute:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
  pr:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-5.6-sol
      effort: alto
```

`model` admite un string no vacío. `effort` admite exactamente estos cinco literales portables; la
traducción es idéntica para ambas familias:

| Portable | Claude (`--effort`) | Codex (`model_reasoning_effort`) |
|---|---|---|
| `bajo` | `low` | `low` |
| `medio` | `medium` | `medium` |
| `alto` | `high` | `high` |
| `muy_alto` | `xhigh` | `xhigh` |
| `maximo` | `max` | `max` |

Las únicas claves admitidas son `schema_version` y `roles` en la raíz; los ocho nombres de rol bajo
`roles`; `claude` y `codex` bajo cada rol; y `model` y `effort` bajo cada familia. No se admite
ninguna otra clave en ningún nivel.
