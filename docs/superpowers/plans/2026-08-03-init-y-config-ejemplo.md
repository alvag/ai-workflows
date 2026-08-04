# `init` reducido + config de ejemplo copiable — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que configurar un proyecto sea mirar un ejemplo completo y copiable, y que `init` pregunte solo las 3 cosas que no puede saber.

**Architecture:** Dos piezas con frontera nítida. `config-ejemplo.md` y `manifest-ejemplo.md` son **vistas** ensambladas de los bloques que cada skill **posee**; la dirección es única (dueño → vista) y dos guardas la chequean: G1 sobre el conjunto de claves, G2 sobre los tokens del enum. El wizard de `init` baja de 9 preguntas a 3 y cierra apuntando al ejemplo.

**Tech Stack:** Markdown (skills), YAML (config de ejemplo), POSIX sh + `python3` con `PyYAML` para las guardas.

**Spec:** `docs/superpowers/specs/2026-08-03-init-y-config-ejemplo-design.md`

## Global Constraints

- **Un solo commit, al final** (Task 9). Ninguna task intermedia commitea. Instrucción explícita de Max.
- El commit va con **pathspec explícito** de las rutas tocadas: hay **otro agente** trabajando en este mismo directorio. Nunca `git add .`.
- **Sin `Co-Authored-By`** ni firmas al pie. Conventional commit; el cambio cruza 5 skills, así que sin scope y con las skills nombradas en el cuerpo.
- `.plans/` es **local y untracked**: las guardas de este plan viven ahí y **no** entran al commit.
- Español neutro en todo artefacto.
- `skills-ref validate ./skills/<nombre>` debe pasar en las 5 skills al terminar.
- **`sdd-flow/SKILL.md` no debe crecer.** La reducción del wizard debe dejarlo igual o más corto que el baseline medido en Task 1.
- **Ningún default cambia.** Este plan documenta y reduce preguntas; no toca el valor que una skill aplica cuando la clave está ausente.
- **No se agregan claves al esquema.** Regla del repo: una capacidad entra con su consumidor o no entra.

## Estructura de archivos

| Archivo | Responsabilidad | Acción |
|---|---|---|
| `.plans/init-config-ejemplo/guardas/comun.sh` | primitivas: `emit`, `yamlblock`, `claves`, `enums` | crear |
| `.plans/init-config-ejemplo/guardas/vista.sh` | G1, G2, G3 sobre `sdd-flow` y `sdd-orchestrator` | crear |
| `.plans/init-config-ejemplo/guardas/init.sh` | G4 (3 preguntas), G5 (cierre nombra las 6) | crear |
| `skills/cross-implement/SKILL.md` | dueño de `cross_implement.*` — hoy no tiene bloque | modificar |
| `skills/cross-review/SKILL.md:268` | dueño de `cross_review.*` — comillas | modificar |
| `skills/co-explore/SKILL.md:379` | dueño de `co_explore.debate.*` — comillas | modificar |
| `skills/sdd-flow/config-ejemplo.md` | **vista** de las 33 claves de `.specify/config.yml` | crear |
| `skills/sdd-flow/reference.md` | esquema recortado a las 20 propias + punteros | modificar |
| `skills/sdd-flow/SKILL.md` | wizard de 9 → 3 preguntas + cierre | modificar |
| `skills/sdd-orchestrator/manifest-ejemplo.md` | **vista** de las claves de config de `manifest.yml` | crear |
| `skills/sdd-orchestrator/reference.md` | comillas + puntero a la vista | modificar |

---

### Task 1: Andamiaje de guardas y baseline

Deja las guardas escritas y **rojas contra el árbol de hoy**, más el baseline que Task 8 y el constraint de presupuesto necesitan. Sin esto, cualquier verde posterior es indistinguible de una guarda que nunca pudo ponerse roja.

**Files:**
- Create: `.plans/init-config-ejemplo/guardas/comun.sh`
- Create: `.plans/init-config-ejemplo/guardas/vista.sh`
- Create: `.plans/init-config-ejemplo/baseline.txt`

**Interfaces:**
- Produces: `emit <id> <RED|GREEN> <detalle>` · `yamlblock <archivo> <heading-regex>` → el primer fence ```yaml de esa sección · `claves <archivo> <heading>` → una clave hoja punteada por línea · `enums <archivo> <heading>` → líneas `clave<TAB>tok1,tok2,…`. Las tasks 2, 4, 6 y 8 los consumen.

- [ ] **Step 1: Crear `comun.sh` con las primitivas**

```sh
# @bloque:comun
# Predicado: no es un predicado — son las primitivas que comparten las demás guardas.
# Entradas: $REPO (raíz del repo)  $EST (archivo de estado)
# Emite: nada por sí solo.
#
# Desviación declarada: estas guardas usan python3 + PyYAML, no POSIX puro como las del
# flujo herdr-transporte-skills. Motivo: acá el predicado es sobre la ESTRUCTURA de un
# bloque YAML y sobre los tokens de sus comentarios, no sobre prosa. Un parser de YAML
# escrito en sh sería más frágil que lo que verifica.
set -u
: "${REPO:=/Users/max/Personal/repos/ai-workflows}"
: "${EST:=$REPO/.plans/init-config-ejemplo/guardas/estado.txt}"

emit() { printf '%-28s %-5s %s\n' "$1" "$2" "${3:-}" >> "$EST"; }

# yamlblock <archivo> <heading-regex> — primer fence ```yaml bajo ese heading
yamlblock() {
  [ -f "$1" ] || return 1
  awk -v h="$2" '
    $0 ~ "^#+ " h { on=1; next }
    on && /^[[:space:]]*```yaml/ { f=1; next }
    on && f && /^[[:space:]]*```/ { exit }
    on && f { print }
  ' "$1"
}

# claves <archivo> <heading> — una clave hoja punteada por línea, ordenadas
claves() {
  yamlblock "$1" "$2" | python3 -c '
import sys, yaml
try: d = yaml.safe_load(sys.stdin.read()) or {}
except Exception as e: sys.stderr.write(f"YAML inválido: {e}\n"); sys.exit(2)
out = []
def walk(n, pre=""):
    if isinstance(n, dict):
        for k, v in n.items():
            p = f"{pre}{k}"
            walk(v, p + ".") if isinstance(v, dict) else out.append(p)
walk(d)
print("\n".join(sorted(out)))
'
}

# enums <archivo> <heading> — "clave<TAB>tok1,tok2" por cada clave cuyo comentario declara un enum.
# Normalización: se corta en el primer em-dash, se parte por |, se quita el paréntesis
# aclaratorio y las comillas. Sin esa normalización `"on" (default)` y `"on"` no son iguales
# y G2 daría rojos que no dicen nada.
enums() {
  yamlblock "$1" "$2" | python3 -c '
import sys, re
for raw in sys.stdin:
    line = raw.rstrip("\n")
    m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):.*?#\s*(.+)$", line)
    if not m: continue
    indent, key, comment = m.group(1), m.group(2), m.group(3)
    head = re.split(r"—", comment)[0]
    if "|" not in head: continue
    toks = []
    for t in head.split("|"):
        t = re.sub(r"\([^)]*\)", "", t).strip().strip("`").strip('"'"'"'"'"'"'"'"'"')
        if t: toks.append(t)
    if toks: print(f"{key}\t" + ",".join(sorted(set(toks))))
'
}
# @fin:comun
```

- [ ] **Step 2: Crear `vista.sh` con G1, G2 y G3**

```sh
# @bloque:vista
# Predicado: la vista está completa (G1), no contradice a sus dueños (G2) y ningún ejemplo
# YAML del repo produce un booleano donde la skill espera un string (G3).
. "$(dirname "$0")/comun.sh"
rc=0

VISTA="$REPO/skills/sdd-flow/config-ejemplo.md"
H='Ejemplo de `\.specify/config\.yml`'

# ---- G1: conjunto de claves de la vista == unión de los dueños --------------------------
duenos() {
  claves "$REPO/skills/sdd-flow/reference.md"        'Esquema de `\.specify/config\.yml`'
  claves "$REPO/skills/cross-review/SKILL.md"        'Configuración'
  claves "$REPO/skills/co-explore/SKILL.md"          'Configuración'
  claves "$REPO/skills/cross-implement/SKILL.md"     'Configuración'
}
u=$(duenos | sort -u); v=$(claves "$VISTA" "$H" | sort -u)
solo_d=$(comm -23 <(printf '%s\n' "$u") <(printf '%s\n' "$v") | tr '\n' ' ')
solo_v=$(comm -13 <(printf '%s\n' "$u") <(printf '%s\n' "$v") | tr '\n' ' ')
if [ -z "$solo_d" ] && [ -z "$solo_v" ] && [ -n "$v" ]; then
  emit G1 GREEN "$(printf '%s\n' "$v" | wc -l | tr -d ' ') claves, vista == unión de dueños"
else
  emit G1 RED "solo-en-dueños: ${solo_d:-—} | solo-en-vista: ${solo_v:-—}"; rc=1
fi

# ---- G2: por clave, los tokens del enum de la vista == los del dueño --------------------
ed=$(mktemp); ev=$(mktemp)
{ enums "$REPO/skills/sdd-flow/reference.md"    'Esquema de `\.specify/config\.yml`'
  enums "$REPO/skills/cross-review/SKILL.md"    'Configuración'
  enums "$REPO/skills/co-explore/SKILL.md"      'Configuración'
  enums "$REPO/skills/cross-implement/SKILL.md" 'Configuración'; } | sort -u > "$ed"
enums "$VISTA" "$H" | sort -u > "$ev"
difs=$(join -t"$(printf '\t')" -j1 \
        <(sort -k1,1 -t"$(printf '\t')" "$ed") \
        <(sort -k1,1 -t"$(printf '\t')" "$ev") \
      | awk -F'\t' '$2 != $3 {print $1" dueño=["$2"] vista=["$3"]"}')
n=$(printf '%s' "$difs" | grep -c . || true)
if [ "$n" -eq 0 ] && [ -s "$ev" ]; then
  emit G2 GREEN "$(wc -l < "$ev" | tr -d ' ') claves con enum, 0 discrepancias"
else
  emit G2 RED "$n discrepancias: $(printf '%s' "$difs" | head -3 | tr '\n' ';')"; rc=1
fi
rm -f "$ed" "$ev"

# ---- G3: ningún ejemplo YAML del repo resuelve un `mode` a booleano ---------------------
mal=$(grep -rnE '^[[:space:]]*(mode|manifest\.mode):[[:space:]]*(on|off)[[:space:]]*(#.*)?$' \
        "$REPO/skills" 2>/dev/null | wc -l | tr -d ' ')
malc=$(grep -rn '|' "$REPO/skills"/*/SKILL.md "$REPO/skills"/*/reference.md 2>/dev/null \
        | grep -E '#.*\|' | grep -vE '"on"' | grep -cE '\|[[:space:]]*(on|off)([[:space:]]*\||[[:space:]]*$|[[:space:]]*—)' || true)
if [ "$mal" -eq 0 ] && [ "$malc" -eq 0 ]; then
  emit G3 GREEN "0 valores y 0 enums con on/off sin comillas"
else
  emit G3 RED "valores sin comillas=$mal · enums sin comillas=$malc"; rc=1
fi
exit $rc
# @fin:vista
```

- [ ] **Step 3: Correr las guardas y comprobar que están ROJAS**

```sh
cd /Users/max/Personal/repos/ai-workflows/.plans/init-config-ejemplo/guardas
: > estado.txt; sh vista.sh; echo "rc=$?"; cat estado.txt
```

Esperado: **G1 RED** (`config-ejemplo.md` no existe → vista vacía), **G2 RED** (ídem), **G3 RED** (los enums sin comillas de `cross-review`, `co-explore` y `sdd-orchestrator`). Si alguna sale verde acá, la guarda no discrimina: arreglarla antes de seguir.

- [ ] **Step 4: Capturar el baseline**

```sh
cd /Users/max/Personal/repos/ai-workflows
{ echo "# baseline previo al cambio — $(git rev-parse --short HEAD)"
  printf 'sdd-flow/SKILL.md %s lineas\n'      "$(wc -l < skills/sdd-flow/SKILL.md)"
  printf 'sdd-flow/reference.md %s lineas\n'  "$(wc -l < skills/sdd-flow/reference.md)"
  printf 'claves del esquema %s\n' "$(sh -c '. .plans/init-config-ejemplo/guardas/comun.sh; claves skills/sdd-flow/reference.md "Esquema de \`\.specify/config\.yml\`"' | wc -l | tr -d ' ')"
  printf 'preguntas del wizard %s\n' "$(grep -c 'Pantalla [0-9]' skills/sdd-flow/SKILL.md)"
} > .plans/init-config-ejemplo/baseline.txt
cat .plans/init-config-ejemplo/baseline.txt
```

Esperado: `claves del esquema 33`. Si da otro número, el `yamlblock`/`claves` está mal y hay que arreglarlo antes de confiar en G1.

---

### Task 2: `cross-implement` gana su bloque de dueño

G1 exige que los cuatro dueños existan. `cross_implement.*` hoy solo vive en prosa (`SKILL.md:111-118`) y dentro del esquema de `sdd-flow`, así que la unión de dueños está incompleta.

**Files:**
- Modify: `skills/cross-implement/SKILL.md` — agregar sección `## Configuración` antes de `## Router de intención`

**Interfaces:**
- Consumes: `claves`/`enums` de Task 1.
- Produces: dueño de `cross_implement.execution`, `cross_implement.max_fix_rounds`, `cross_implement.deadline`.

- [ ] **Step 1: Agregar la sección**

Ubicarla donde la tienen sus hermanas (antes de `## Router de intención`), con el mismo formato:

````markdown
## Configuración

Claves bajo `cross_implement` en `.specify/config.yml` (sdd-flow) o en el `manifest.yml` de la
orquestación. Solo aplican con `implement_mode: cross`; en los otros modos se ignoran. Todas
opcionales:

```yaml
cross_implement:
  execution: auto        # auto (por tamaño del work order) | sync | background — cómo espera al implementador
  max_fix_rounds: 2      # tope del fix loop antes del takeover del conductor
  deadline: 1800         # segundos; tope duro del wait en background
  # sin `implementer:` — la familia la fija el conductor, no es configurable
```

Esta skill es **dueña** de estas tres claves: su enum y su descripción se definen acá. El
ejemplo copiable del archivo completo vive en `sdd-flow/config-ejemplo.md`, que es una **vista**
ensamblada de este bloque y sus hermanos; ante discrepancia manda este bloque.

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default de la skill**.
````

- [ ] **Step 2: Comprobar que el dueño se lee**

```sh
cd /Users/max/Personal/repos/ai-workflows
. .plans/init-config-ejemplo/guardas/comun.sh
claves skills/cross-implement/SKILL.md 'Configuración'
```

Esperado, exactamente estas 3 líneas:
```
cross_implement.deadline
cross_implement.execution
cross_implement.max_fix_rounds
```

- [ ] **Step 3: Validar la skill**

```sh
skills-ref validate ./skills/cross-implement
```
Esperado: `Valid skill: skills/cross-implement`

---

### Task 3: Cerrar el defecto de comillas en los tres dueños

G3 rojo. Tres lugares enseñan la forma que YAML convierte en booleano. Se arregla en el **dueño**, no en la vista: la vista todavía no existe y la dirección es dueño → vista.

**Files:**
- Modify: `skills/cross-review/SKILL.md:268`
- Modify: `skills/co-explore/SKILL.md:379`
- Modify: `skills/sdd-orchestrator/reference.md` — bloque `cross_review` del esquema de `manifest.yml`

**Interfaces:**
- Consumes: G3 de Task 1.

- [ ] **Step 1: Confirmar el problema con el parser**

```sh
python3 -c 'import yaml; print(repr(yaml.safe_load("mode: on")["mode"]), repr(yaml.safe_load("mode: \"on\"")["mode"]))'
```
Esperado: `True 'on'` — tipos distintos, no es cosmético.

- [ ] **Step 2: `cross-review/SKILL.md`**

Reemplazar:
```
  mode: auto            # auto (por complejidad) | on | off
```
por:
```
  mode: auto            # auto (por complejidad) | "on" | "off"  (entre comillas: sin ellas YAML los parsea como booleanos)
```

- [ ] **Step 3: `co-explore/SKILL.md`**

Reemplazar:
```
    mode: auto      # off | on | auto  — cuándo se OFRECE el debate (nunca corre sin confirmación)
```
por:
```
    mode: auto      # auto | "on" | "off"  — cuándo se OFRECE el debate (nunca corre sin confirmación; comillas obligatorias)
```

- [ ] **Step 4: `sdd-orchestrator/reference.md`**

En el bloque `cross_review` del esquema de `manifest.yml`, reemplazar:
```
  mode: auto                   # auto | on | off
```
por:
```
  mode: auto                   # auto | "on" | "off"  (entre comillas: sin ellas YAML los parsea como booleanos)
```

- [ ] **Step 5: Correr G3**

```sh
cd /Users/max/Personal/repos/ai-workflows/.plans/init-config-ejemplo/guardas
: > estado.txt; sh vista.sh; grep '^G3' estado.txt
```
Esperado: `G3 GREEN 0 valores y 0 enums con on/off sin comillas`. G1 y G2 siguen rojas: la vista todavía no existe.

---

### Task 4: La vista de `sdd-flow` — `config-ejemplo.md`

**Files:**
- Create: `skills/sdd-flow/config-ejemplo.md`

**Interfaces:**
- Consumes: los cuatro dueños (tasks 2 y 3 incluidas).
- Produces: el heading `## Ejemplo de \`.specify/config.yml\`` con un fence ```yaml de 33 claves, que G1/G2 leen.

- [ ] **Step 1: Escribir el archivo**

Encabezado obligatorio —es lo que lo declara vista— y la convención de marcas:

````markdown
# Ejemplo de `.specify/config.yml`

**Este archivo es una vista.** Está ensamblado de los bloques que cada skill posee:
`sdd-flow/reference.md` → "Esquema" (20 claves), `cross-review/SKILL.md` → "Configuración" (6),
`co-explore/SKILL.md` → "Configuración" (4) y `cross-implement/SKILL.md` → "Configuración" (3).
**Ante discrepancia manda el dueño.** Existe para poder mirar el archivo completo y copiar lo que
sirva; no para ser la autoridad de ninguna clave.

**Copialo entero o por bloques.** Toda clave que borres vuelve a su default, que es lo que la
skill aplica cuando la clave está ausente — por eso este ejemplo no se materializa en tu repo con
`init`: un default copiado queda congelado, uno ausente sigue la skill.

Cada valor lleva una marca, y solo una:

- `[def]` — **es el default**. Copiarlo no cambia nada; borrarlo tampoco.
- `[ej]` — **es un ejemplo**, no un default: no hay valor por defecto y se autodetecta o se
  pregunta. Copiarlo tal cual probablemente esté mal para tu proyecto.

## Ejemplo de `.specify/config.yml`

```yaml
# ── sdd-flow: entorno del proyecto (se autodetecta; el ejemplo es de un repo Node) ──
stack: node                      # [ej] node | go | rust | python | java | dotnet | other
test_cmd: "npm test"             # [ej] comando de tests
build_cmd: "npm run build"       # [ej] omitir si el stack no compila
lint_cmd: "npm run lint"         # [ej] opcional
test_scope_hint: "vitest run {name}"   # [ej] plantilla de COMANDO para acotar tests; {name} = archivo/patrón
default_branch: main             # [ej] rama base; se detecta, nunca se asume main/master

# ── sdd-flow: convenciones ──
branch_format: "{type}/{ticket}-{slug}"  # [def] placeholders {type} {ticket} {slug}
branch_prefix: ""                # [ej] reemplaza {type} (p. ej. "feature/"); vacío → prefijo semántico
commit_style: conventional       # [def] conventional | plain
tracker: jira                    # [ej] jira | github | gitlab | linear | none
implement_mode: ask              # [def] ask | inline | subagent | cross

# ── sdd-flow: gates opcionales ──
domain_context:
  mode: auto                     # [def] auto | "on" | "off" — leer docs de dominio/ADRs; solo lectura
  context_paths: []              # [def] docs de dominio a leer si existen
  adr_paths: []                  # [def] ADRs vigentes a leer si existen
final_diff_review:
  mode: auto                     # [def] auto (complex/high-risk inline) | "on" | "off"
jira_approval:                   # solo si tracker: jira
  mode: "off"                    # [def] "on" | "off" — publica la spec en Jira y espera aprobación
  subtask_issuetype: auto        # [def] auto | "Subtarea" | "Sub-task"
  approval_signal: ask           # [def] ask | status:"<estado Jira que cuenta como aprobado>"

# ── ecosistema cross-model (lo resuelve y ecoa sdd-flow) ──
cross_model:
  schema_version: 1              # [def] obligatorio si el bloque existe
  transport: cli                 # [def] cli | herdr — dónde se aloja cada corrida delegada
  manifest:                      # dueño: cross-review/reference.md → "Manifest de corrida"
    mode: "on"                   # [def] "on" | "off" — registro por corrida de las skills cross-model

# ── dueño: cross-review/SKILL.md → "Configuración" ──
cross_review:
  mode: auto                     # [def] auto (por complejidad) | "on" | "off"
  execution: auto                # [def] auto | sync | background
  artifacts: [spec, plan, tasks] # [def] qué artefactos revisar
  max_rounds: 3                  # [def] tope de rondas
  reviewer: auto                 # [def] auto | claude | codex — nunca la familia del autor

# ── dueño: co-explore/SKILL.md → "Configuración" ──
co_explore:
  mode: auto                     # [def] auto (por complejidad) | "on" | "off"
  deadline: 600                  # [def] segundos; override del default por modo
  debate:
    mode: auto                   # [def] auto | "on" | "off" — cuándo se OFRECE el debate
    max_rounds: 3                # [def] tope de rondas de cruce

# ── dueño: cross-implement/SKILL.md → "Configuración" (solo con implement_mode: cross) ──
cross_implement:
  execution: auto                # [def] auto | sync | background
  max_fix_rounds: 2              # [def] tope del fix loop antes del takeover
  deadline: 1800                 # [def] segundos; tope duro del wait en background
```
````

- [ ] **Step 2: Comprobar que el YAML es válido y tiene 33 claves**

```sh
cd /Users/max/Personal/repos/ai-workflows
. .plans/init-config-ejemplo/guardas/comun.sh
claves skills/sdd-flow/config-ejemplo.md 'Ejemplo de `\.specify/config\.yml`' | wc -l
```
Esperado: `33`

- [ ] **Step 3: Comprobar que ninguna marca falta ni se duplica**

```sh
cd /Users/max/Personal/repos/ai-workflows
. .plans/init-config-ejemplo/guardas/comun.sh
b=$(yamlblock skills/sdd-flow/config-ejemplo.md 'Ejemplo de `\.specify/config\.yml`')
printf 'con marca:   %s\n' "$(printf '%s\n' "$b" | grep -cE '#.*\[(def|ej)\]')"
printf 'con las dos: %s\n' "$(printf '%s\n' "$b" | grep -cE '\[def\].*\[ej\]|\[ej\].*\[def\]')"
```
Esperado: `con marca: 33` y `con las dos: 0`. Un valor sin marca es el defecto original volviendo.

- [ ] **Step 4: Correr G1 y G2**

```sh
cd /Users/max/Personal/repos/ai-workflows/.plans/init-config-ejemplo/guardas
: > estado.txt; sh vista.sh; cat estado.txt
```
Esperado: **G1 GREEN**, **G2 GREEN**, **G3 GREEN**. Si G2 sale roja, el detalle nombra la clave y los dos conjuntos de tokens: alinear **la vista al dueño**, nunca al revés.

---

### Task 5: Recortar el esquema de `sdd-flow/reference.md`

Si la vista lista 33 y el esquema también, la duplicación queda dentro de una misma skill — peor que lo que este plan arregla. El esquema pasa a ser dueño de **sus 20** y apunta por las otras 13.

**Files:**
- Modify: `skills/sdd-flow/reference.md` — sección "Esquema de `.specify/config.yml`"

**Interfaces:**
- Consumes: la vista de Task 4.
- Produces: dueño de 20 claves (18 propias + `cross_model.schema_version` y `cross_model.transport`).

- [ ] **Step 1: Quitar del bloque los 13 de las hermanas**

Borrar del fence ```yaml del esquema los sub-bloques completos `cross_review:` (5), `co_explore:` (4), `cross_implement:` (3) y la clave `cross_model.manifest.mode` (1). Dejar `cross_model.schema_version` y `cross_model.transport`.

- [ ] **Step 2: Agregar el párrafo de fronteras justo después del fence**

```markdown
**Este bloque es dueño de las 20 claves que `sdd-flow` gobierna.** Las 13 restantes las poseen sus
hermanas y su enum se define allá: `cross_review.*` y `cross_model.manifest.mode` en
`cross-review/SKILL.md` → "Configuración"; `co_explore.*` en `co-explore/SKILL.md` →
"Configuración"; `cross_implement.*` en `cross-implement/SKILL.md` → "Configuración". El archivo
**completo**, con las 33 juntas y listo para copiar, está en `config-ejemplo.md`, que es una vista
de todos estos dueños.
```

- [ ] **Step 3: Comprobar el recorte y que G1 sigue verde**

```sh
cd /Users/max/Personal/repos/ai-workflows
. .plans/init-config-ejemplo/guardas/comun.sh
claves skills/sdd-flow/reference.md 'Esquema de `\.specify/config\.yml`' | wc -l
cd .plans/init-config-ejemplo/guardas && : > estado.txt && sh vista.sh && cat estado.txt
```
Esperado: `20`, y **G1/G2/G3 GREEN**. G1 verde acá es la prueba de que el recorte no perdió ninguna clave: la unión de dueños sigue dando 33.

---

### Task 6: La vista del orquestador — `manifest-ejemplo.md`

**Files:**
- Create: `skills/sdd-orchestrator/manifest-ejemplo.md`
- Modify: `.plans/init-config-ejemplo/guardas/vista.sh` — agregar G1o/G2o
- Modify: `skills/sdd-orchestrator/reference.md` — puntero a la vista

**Interfaces:**
- Consumes: `claves`/`enums` de Task 1; los dueños de tasks 2 y 3.

- [ ] **Step 1: Escribir `manifest-ejemplo.md`**

Solo las claves de **config**. `id`, `created_at`, `master_spec`, `repos` y `status` son **estado de corrida**, no configuración, y no van: el archivo dice esto explícitamente en su encabezado, con la misma cabecera de vista y las mismas marcas `[def]`/`[ej]` de Task 4.

```yaml
branch_prefix: ""                # [ej] prefijo único de la orquestación; vacío → semántico por repo
execution_mode: fanout           # [def] fanout (agentes paralelos) | inline (de a un repo)
implement_mode: ""               # [def] vacío → cada sdd-flow resuelve el suyo | inline | subagent | cross
cross_review:                    # dueño: cross-review/SKILL.md → "Configuración"
  mode: auto                     # [def] auto (por complejidad) | "on" | "off"
  execution: auto                # [def] auto | sync | background
  artifacts: [master-spec, reparto]   # [def] qué artefactos revisar (difiere de sdd-flow)
  max_rounds: 3                  # [def] tope de rondas
co_explore:                      # dueño: co-explore/SKILL.md → "Configuración"
  mode: auto                     # [def] auto | "on" | "off"; default on en orquestación
  deadline: 600                  # [def] segundos
cross_model:
  schema_version: 1              # [def] obligatorio si el bloque existe
  transport: cli                 # [def] cli | herdr — lo heredan los sdd-flow delegados
```

- [ ] **Step 2: Registrar la asimetría de `cross_review.reviewer`, sin resolverla**

El `cross_review` del orquestador tiene **4** claves y el de `sdd-flow` tiene **5**: falta `reviewer`. No se agrega —sería una clave nueva sin consumidor verificado, y el plan prohíbe eso—. Se declara en el archivo:

```markdown
> **`cross_review.reviewer` no está acá y sí en `sdd-flow`.** No se agrega en este cambio: sería
> una clave sin consumidor comprobado en el orquestador. Si hace falta, entra con su consumidor.
```

- [ ] **Step 3: Agregar G1o/G2o a `vista.sh`**

Mismo predicado que G1/G2 pero con `VISTA` = `manifest-ejemplo.md`, heading `Ejemplo de \`manifest\.yml\``, y como dueños el esquema de `sdd-orchestrator/reference.md` más `cross-review` y `co-explore`. Emitir con los ids `G1o` y `G2o`.

- [ ] **Step 4: Correr las cinco guardas**

```sh
cd /Users/max/Personal/repos/ai-workflows/.plans/init-config-ejemplo/guardas
: > estado.txt; sh vista.sh; cat estado.txt
```
Esperado: `G1 G2 G3 G1o G2o` todas **GREEN**.

---

### Task 7: `init` de 9 preguntas a 3

**Files:**
- Modify: `skills/sdd-flow/SKILL.md:362-366` — pasos 4 y 5 del paso `init`
- Modify: `skills/sdd-flow/reference.md` — sección "Qué escribe `init`", el párrafo que enumera los campos del wizard
- Create: `.plans/init-config-ejemplo/guardas/init.sh` — G4 y G5

**Interfaces:**
- Consumes: la vista de Task 4 (el cierre la apunta).

- [ ] **Step 1: Escribir G4 y G5 y verlas ROJAS**

```sh
# @bloque:init
. "$(dirname "$0")/comun.sh"
rc=0
SK="$REPO/skills/sdd-flow/SKILL.md"
b=$(seccion "$SK" 'Paso `init`')

# G4 — el wizard tiene UNA pantalla y las tres preguntas
c=0
printf '%s' "$b" | grep -qiE 'una sola pantalla|una pantalla' && c=$((c+1))
printf '%s' "$b" | grep -q '`tracker`'                        && c=$((c+1))
printf '%s' "$b" | grep -q '`branch_prefix`'                  && c=$((c+1))
printf '%s' "$b" | grep -qE 'jira_approval.*(solo si|condicional)' && c=$((c+1))
printf '%s' "$b" | grep -qiE 'Pantalla 2'                     && c=$((c+1))   # NO debe estar
if [ "$c" -eq 4 ]; then emit G4 GREEN "1 pantalla + las 3 preguntas, sin Pantalla 2"
else emit G4 RED "$c de 4 (5 = quedó Pantalla 2)"; rc=1; fi

# G5 — el cierre nombra las 6 que salieron y apunta al ejemplo
c=0
for k in commit_style implement_mode cross_review domain_context final_diff_review debate; do
  printf '%s' "$b" | grep -q "$k" && c=$((c+1))
done
printf '%s' "$b" | grep -q 'config-ejemplo.md' && c=$((c+1))
if [ "$c" -eq 7 ]; then emit G5 GREEN "las 6 nombradas + puntero al ejemplo"
else emit G5 RED "$c de 7"; rc=1; fi
exit $rc
# @fin:init
```

Correr: `sh init.sh` → esperado **G4 RED** (hoy hay dos pantallas) y **G5 RED** (no existe el puntero).

- [ ] **Step 2: Reemplazar los pasos 4 y 5 del wizard**

```markdown
4. **Wizard de decisiones — una sola pantalla, tres preguntas.** Se pregunta **solo lo que la skill no puede saber**: lo que tiene default lo decide ella, y lo autodetectable se detecta. Si hay una herramienta de **selección interactiva** (descubrir por capacidad, no por nombre), presentar con descripción y el valor actual/detectado marcado "(actual)":
   - **`tracker`** (jira · github · gitlab · linear · none) — sin default; con varios MCP disponibles la autodetección es ambigua, y fijarlo hace el paso determinista.
   - **`branch_prefix`** (vacío → prefijo semántico · fijo, p. ej. `feature/`) — sin default; es política de CI/CD del equipo y nada en el repo la revela.
   - **`jira_approval.mode`** (`"off"` · `"on"`) — **solo si se acaba de elegir `tracker: jira`**; con otro tracker la clave no aplica y no se pregunta. Tiene default (`"off"`), pero es un hecho de proceso del equipo que ninguna skill puede detectar y cambia el flujo: publica la spec en Jira y espera aprobación.
   - **Sin** herramienta de selección → **degradar** al modo conversacional: proponer los valores y confirmar (regla 6).
5. **Todo lo demás no se pregunta.** Los comandos y paths (`test_cmd`/`build_cmd`/`lint_cmd`/`test_scope_hint`, `default_branch`, `stack`, y los `context_paths`/`adr_paths` de `domain_context`) se **autodetectan** y quedan editables en el preview del paso 6. Las **25 claves con default** —entre ellas `commit_style`, `implement_mode`, `cross_review`, `domain_context`, `final_diff_review` y el `debate` de `co_explore`— no van al wizard: la skill las resuelve, y quien quiera fijarlas las copia del ejemplo (paso 8).
```

- [ ] **Step 3: Agregar el cierre como paso 8, renumerando la re-corrida a 9**

```markdown
8. **Cierre — apuntar al resto.** Al confirmar, decir en una línea que el config admite **33 claves** y que las **25 con default** están en `config-ejemplo.md`, listas para copiar por bloques, con cada valor marcado como default o como ejemplo. Sin este cierre, reducir el wizard convierte "no te lo pregunto" en "no existe": las seis preguntas que salieron —`commit_style`, `implement_mode`, `cross_review`, `domain_context`, `final_diff_review` y `debate`— tienen que quedar descubribles.
```

- [ ] **Step 4: Alinear "Qué escribe `init`" en `reference.md`**

Reemplazar la enumeración de campos del wizard (hoy nombra 9) por las 3 de arriba, conservando intacta la frase sobre las comillas de `on`/`off` al emitir el YAML.

- [ ] **Step 5: Correr G4/G5 y el presupuesto**

```sh
cd /Users/max/Personal/repos/ai-workflows
sh .plans/init-config-ejemplo/guardas/init.sh; cat .plans/init-config-ejemplo/guardas/estado.txt
printf 'SKILL.md ahora %s · baseline %s\n' "$(wc -l < skills/sdd-flow/SKILL.md)" \
  "$(grep 'sdd-flow/SKILL.md' .plans/init-config-ejemplo/baseline.txt)"
```
Esperado: **G4 GREEN**, **G5 GREEN**, y `sdd-flow/SKILL.md` **igual o menor** que el baseline.

---

### Task 8: Probar por mutación que las guardas discriminan

Una guarda que nace verde y nunca se vio roja no prueba nada. Cinco de las siete llegan verdes a esta task sin haberse visto rojas en su forma final.

**Files:**
- Create: `.plans/init-config-ejemplo/mutaciones.txt`

**Interfaces:**
- Consumes: las 7 guardas (G1, G2, G3, G1o, G2o, G4, G5).

- [ ] **Step 1: Mutar sobre una COPIA, nunca sobre el árbol**

```sh
cd /Users/max/Personal/repos/ai-workflows
rm -rf /tmp/mut && cp -R skills /tmp/mut-skills && mkdir -p /tmp/mut && mv /tmp/mut-skills /tmp/mut/skills
```
Correr cada mutante con `REPO=/tmp/mut`. Mutar el worktree compartido es lo que deja el repo roto si el proceso muere, y otro agente no distingue la ventana de un cambio real.

- [ ] **Step 2: Aplicar los siete mutantes, verificando que cada uno se aplicó**

| # | Guarda | Mutación | Esperado |
|---|---|---|---|
| 1 | G1 | borrar una clave del fence de `config-ejemplo.md` | RED, nombrando esa clave en `solo-en-dueños` |
| 2 | G1 | agregar `foo: bar` al fence de la vista | RED, nombrando `foo` en `solo-en-vista` |
| 3 | G2 | en la vista, cambiar `transport: cli # [def] cli \| herdr` por `cli \| tmux` | RED, nombrando `transport` con los dos conjuntos |
| 4 | G3 | poner `mode: on` sin comillas en `cross-review/SKILL.md` | RED, `valores sin comillas=1` |
| 5 | G1o | borrar `execution_mode` de `manifest-ejemplo.md` | RED |
| 6 | G4 | reponer un heading `Pantalla 2` en el paso `init` | RED, `5 de 4` |
| 7 | G5 | borrar la mención a `config-ejemplo.md` del cierre | RED, `6 de 7` |

Antes de leer el veredicto de cada uno, **contar ocurrencias antes/después** para confirmar que el mutante se aplicó: un mutante no-op da un verde que parece hueco de cobertura.

- [ ] **Step 3: Escribir `mutaciones.txt`**

Una fila por mutante: qué se mutó, en qué archivo, esperado, obtenido, y si el conteo confirmó que se aplicó. Más los defectos de guarda que aparezcan en el camino, con su causa.

- [ ] **Step 4: Confirmar que el árbol real quedó intacto**

```sh
cd /Users/max/Personal/repos/ai-workflows && git status --short && rm -rf /tmp/mut
```
Esperado: solo los archivos que este plan toca. Ninguna mutación filtrada.

---

### Task 9: Verificación final y **el único commit**

**Files:**
- Modify: ninguno. Solo verifica y commitea.

- [ ] **Step 1: Las siete guardas en verde, de una**

```sh
cd /Users/max/Personal/repos/ai-workflows/.plans/init-config-ejemplo/guardas
: > estado.txt; sh vista.sh; sh init.sh
echo "--- estado ---"; cat estado.txt
echo "por veredicto:"; awk '{print $2}' estado.txt | sort | uniq -c
awk '$2!="GREEN"' estado.txt; echo "(vacío = las 7 en verde)"
```
Esperado: 7 líneas, 7 `GREEN`. Leer el **detalle** de cada una, no solo el veredicto: un mensaje que contradice su propio veredicto es el único síntoma de una guarda defectuosa.

- [ ] **Step 2: Validar las cinco skills**

```sh
cd /Users/max/Personal/repos/ai-workflows
for s in sdd-flow sdd-orchestrator co-explore cross-review cross-implement; do
  printf '%-20s ' "$s"; skills-ref validate ./skills/$s 2>&1 | tail -1
done
```
Esperado: `Valid skill` en las cinco.

- [ ] **Step 3: Comprobar que nada de `.plans/` se cuela**

```sh
cd /Users/max/Personal/repos/ai-workflows
git status --short | grep -E '^\?\?|^ M' | grep -E '\.plans/|\.specify/' && echo "!! HAY ARTEFACTOS LOCALES" || echo "(limpio: .plans/ sigue untracked)"
git diff --cached --name-only; echo "(índice vacío = nadie más stageó)"
```

- [ ] **Step 4: El commit único, con pathspec explícito**

```sh
cd /Users/max/Personal/repos/ai-workflows
git commit -F <mensaje> -- \
  docs/superpowers/specs/2026-08-03-init-y-config-ejemplo-design.md \
  docs/superpowers/plans/2026-08-03-init-y-config-ejemplo.md \
  skills/sdd-flow/config-ejemplo.md \
  skills/sdd-flow/SKILL.md \
  skills/sdd-flow/reference.md \
  skills/sdd-orchestrator/manifest-ejemplo.md \
  skills/sdd-orchestrator/reference.md \
  skills/co-explore/SKILL.md \
  skills/cross-review/SKILL.md \
  skills/cross-implement/SKILL.md
```

Los archivos nuevos necesitan `git add` de esas rutas antes; el pathspec en el `commit` es lo que impide arrastrar lo que otro agente haya stageado. Mensaje `feat:` **sin scope** (cruza 5 skills, se nombran en el cuerpo), sin `Co-Authored-By`.

**Este commit requiere permiso explícito de Max en el momento**, aunque el plan lo prevea: aprobar el plan no aprueba el commit.

---

## Self-review

**Cobertura del spec.** Las cuatro piezas y las secciones de verificación tienen task: ejemplo copiable → T4, T6 · dueño/vista + G1/G2 → T1, T2, T4, T5, T6 · `init` reducido → T7 · orquestador → T6 · las 4 propiedades de copiabilidad → T4 steps 1-3 (marcas), T3 (comillas), T4 step 1 (atribución y descripción) · mapa de dueños → T5 · fuera de alcance respetado: ninguna task valida el config del usuario, cambia un default ni agrega claves.

**Sin placeholders.** Cada step trae el comando exacto y el resultado esperado; los bloques de código son completos, no ilustrativos.

**Consistencia de nombres.** `emit`/`yamlblock`/`claves`/`enums` se definen en T1 y se usan con esa firma en T2, T4, T5, T6. Los ids de guarda son `G1 G2 G3 G1o G2o G4 G5` en todas las tasks y en el mutante que le corresponde. El heading de la vista es `Ejemplo de \`.specify/config.yml\`` en T4, T5 y en el regex de `vista.sh`.

**Un riesgo declarado.** `enums()` normaliza el comentario cortando en el em-dash y quitando paréntesis. Si un dueño escribe un enum con un guion común en vez de em-dash, la normalización no corta y G2 compara de más. El mutante 3 lo ejercita parcialmente; si aparece en la implementación, se arregla en `comun.sh` y se re-corren los siete.
