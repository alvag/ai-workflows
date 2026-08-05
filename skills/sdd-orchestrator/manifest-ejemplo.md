# Ejemplo de `manifest.yml`

**Este archivo es una vista.** Está ensamblado de los bloques que cada skill posee: la config
propia de la orquestación en `sdd-orchestrator/reference.md` → "Esquema de `manifest.yml`"
(`branch_prefix`, `execution_mode`, `implement_mode`), `cross-review/SKILL.md` → "Configuración"
(4 de sus 5 claves), `co-explore/SKILL.md` → "Configuración" (2 de sus 4) y `sdd-flow/reference.md`
→ "Esquema de `.specify/config.yml`" (2 de las 3 de `cross_model`). **Ante discrepancia manda el
dueño.** Existe para poder mirar el archivo completo y copiar lo que sirva; no para ser la
autoridad de ninguna clave.

**Solo configuración.** El esquema completo de `manifest.yml` (`sdd-orchestrator/reference.md` →
"Esquema de `manifest.yml`") tiene 17 hojas; 5 son **estado de corrida** de la orquestación, no
configuración, y no aparecen acá: `id`, `created_at`, `master_spec`, `repos` y
`orchestration_tasks`. Las dos últimas anidan estado propio: `repos` incluye, por cada repo del DAG,
`branch`, `status`, `depends_on` y `covers_ac`; y `orchestration_tasks`, por cada tarea, su `phase`,
`owner`, `status` y `done_when` — también estado, no config. Este archivo documenta las 12
restantes.

**Copialo entero o por bloques.** Una clave que borres vuelve a su default —salvo las marcadas
`[obl]`, que no tienen uno—, que es lo que la skill aplica cuando la clave está ausente del
`manifest.yml`. El `manifest.yml` real lo escribe y mantiene el propio orquestador durante la
orquestación (junto al estado de corrida que este ejemplo deja afuera); este archivo es la
referencia para copiar o revisar su bloque de configuración.

Cada valor lleva una marca, y solo una:

- `[def]` — **copiarla no cambia nada, y borrarla tampoco**: la skill aplica ese mismo valor
  cuando la clave está ausente.
- `[ej]` — **copiarla puede cambiar el comportamiento**, o estar mal para tu proyecto: no hay un
  default único al que volver.
- `[obl]` — **obligatoria si copiás el bloque**: el dueño la declara obligatoria mientras el
  bloque exista. Qué pasa si la borrás no está documentado por el dueño.

## Ejemplo de `manifest.yml`

```yaml
branch_prefix: ""                # [def] prefijo único de la orquestación; vacío → semántico por repo
execution_mode: fanout           # fanout | inline — [def] fanout = agentes paralelos, inline = de a un repo (en la sesión del orquestador)
implement_mode: ""               # inline | subagent | cross — [def] vacío → cada sdd-flow resuelve el suyo (config del repo > default)

# ── dueño: cross-review/SKILL.md → "Configuración" ──
cross_review:
  mode: auto                     # auto (por complejidad) | "on" | "off" — [def]
  execution: auto                # auto (por capacidad del conductor) | sync | background — [def]
  artifacts: [master-spec, reparto]   # [def] qué artefactos revisar (difiere del default de sdd-flow)
  max_rounds: 3                  # [def] rondas por TANDA, no de la corrida entera
  reviewer: auto                 # auto | claude | codex — [def] nunca la familia del autor

# ── dueño: co-explore/SKILL.md → "Configuración" ──
co_explore:
  mode: auto                     # auto (por complejidad) | "on" | "off" — [def] default on en orquestación
  deadline: 600                  # [ej] segundos (explore; counter-plan usa 300 salvo override)

# ── dueño: sdd-flow/reference.md → "Esquema de `.specify/config.yml`" ──
cross_model:
  schema_version: 1              # [obl] obligatorio si el bloque existe
  transport: cli                 # cli | herdr — [def] lo heredan los sdd-flow delegados para sus corridas
```

> **Tres claves de sus dueños no están acá, y no se agregan sin consumidor.**
>
> - **`cross_review.reviewer`** — la posee `cross-review/SKILL.md` → "Configuración"; el
>   `manifest.yml` de la orquestación no la usa.
> - **`co_explore.debate.mode`** y **`co_explore.debate.max_rounds`** — las posee
>   `co-explore/SKILL.md` → "Configuración"; ninguna vive en el `manifest.yml`.
> - **`cross_model.manifest.mode`** — la posee `sdd-flow/reference.md` → "Esquema de
>   `.specify/config.yml`"; el `manifest.yml` de la orquestación solo usa `schema_version` y
>   `transport` de ese bloque.
>
> Ninguna se agrega en este cambio: sería una clave sin consumidor comprobado en el orquestador.
> Si alguna hace falta, entra junto con su consumidor.
