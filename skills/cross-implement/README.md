# cross-implement

**Implementación cruzada cross-model.** El conductor (autor del plan) delega la implementación de
un work order **congelado** a un modelo de **otra familia** (Codex cuando conduce Claude; Claude
cuando conduce Codex), con escritura acotada al working dir; el conductor revisa el diff completo
como un PR ajeno, corre la prueba él mismo, itera fixes en la misma sesión (loop acotado) y es
quien commitea tras el gate humano.

## Qué es

La tercera pieza del trío cross-model, con el mismo fundamento que sus hermanas — romper la
correlación de errores entre autor y revisor:

- **`co-explore`** — explorar/investigar en paralelo (dos mapas independientes).
- **`cross-review`** — criticar artefactos de diseño (spec/plan/tasks) antes de implementar.
- **`cross-implement`** — implementar cruzado: uno planifica, el otro implementa, el primero
  revisa la implementación.

Hoy, cuando un modelo implementa su propio plan, autor y revisor del código son el mismo modelo
con los mismos puntos ciegos. Acá implementador y revisor son de familias distintas por
construcción, y el reporte del implementador es **advisory**: el conductor lee el diff completo y
corre la prueba él mismo antes de aceptar nada.

```
work order congelado ──► implementador (otra familia, escritura acotada, nunca commitea)
                              ▼
                    diff + reporte ──► conductor revisa como PR ajeno + corre la prueba
                              ▼
                    fix loop acotado (misma sesión) ──► gate humano ──► commit (del conductor)
```

## El contrato de verificación

Antes de delegar nada, el work order tiene que traer su **contrato de verificación congelado**: una
tabla con una fila por requisito —qué lo prueba, con qué comando, qué resultado cuenta como cumplido
y qué daba ese comando *antes* de implementar— más un bloque de baseline por versión. El gate previo
al dispatch no acepta un work order sin él.

La razón es sencilla: elegir la evidencia *después* de implementar es elegir la que ya pasa. Con el
contrato congelado antes, una fila que no discrimina se detecta cuando todavía se puede arreglar.

Cuando una fila falla, la primera pregunta no es cómo arreglarla sino **de quién es el problema**:
hay cuatro clases (defecto de implementación, de verificación, de entorno, o hueco de diseño) y solo
la primera consume una ronda de fix. Las otras tienen presupuesto propio.

El detalle vive en `contrato-verificacion.md` y `ownership.md`, que se leen en momentos distintos:
el primero al armar y aprobar el contrato, el segundo cuando una ronda falla.

## Cuándo usarla

- Modo directo: `/cross-implement .plans/ABC-123/`, `/cross-implement PLAN.md`, "que Codex
  implemente este plan", "implementa esto con Codex y revisas tú".
- Embebida por `sdd-flow` cuando `implement_mode: cross` (la pregunta del último gate ofrece la
  opción si el CLI de la otra familia está disponible).
- Trabajo que se lee como **orden de trabajo**: refactors mecánicos, migraciones, fixes con repro
  conocido, features con spec/tasks aprobadas.

## Cuándo NO usarla

- **Sin work order congelado**: si escribir el contrato obliga a decidir diseño, eso es diseño y
  va antes (sdd-flow, o `cross-review` en modo draft). Delegar diseño es cómo falla esto.
- **Cambios triviales** (~<20 líneas): el overhead de delegar supera al cambio.
- **Para revisar código existente** (eso es code review) ni artefactos de diseño (eso es
  `cross-review`).
- **Tasks que dependen de tools de sesión** (MCPs, secretos, navegador): el implementador
  delegado no las ve.

## Requisitos

Ninguno obligatorio: es una **capacidad opcional** que degrada a implementación inline. Para que
la delegación ocurra hace falta el CLI de la otra familia:

- Autor Claude → Codex: `codex exec -s workspace-write` en el PATH (codex-cli ≥ 0.130).
- Autor GPT/Codex → Claude: `claude -p` en el PATH (escritura acotada por permisos path-scoped:
  `--permission-mode default` + `Edit(./**),Write(./**)` — nunca `acceptEdits`, que escribe fuera
  del working dir; ver `reference.md` → "Matriz de verificación").

**Transporte alternativo por panes (opcional).** Si el entorno lo permite, el implementador puede
alojarse en un pane de un multiplexor de terminales en vez de lanzarse headless por CLI. Sustituye el
transporte, no la semántica —sigue siendo de la otra familia, con escritura acotada, y el conductor
sigue revisando el diff—, y si la capacidad no está la vía no se intenta: la corrida sigue por el
transporte CLI vigente con un aviso de una línea. Detalle en `transporte-herdr.md`.

`cross-review` recomendada (no obligatoria): aporta el algoritmo canónico de descubrimiento
por familia y la sección de portabilidad de shells que esta skill referencia.

## Instalación

Copia (o symlinkea) la carpeta `cross-implement/` al directorio de skills de tu entorno. Como es
portable (no solo SDD), conviene scope usuario (`~/.claude/skills/` en Claude Code,
`~/.agents/skills/` en Codex):

```
<skills>/
├─ sdd-flow/             # opcional (modo embebido)
├─ cross-review/     # opcional, recomendada
├─ co-explore/           # opcional
└─ cross-implement/
   ├─ SKILL.md
   ├─ reference.md
   └─ README.md
```

## Ejemplos de uso

**1. Embebida en sdd-flow:** con tasks aprobadas y `implement_mode: ask`, el gate pregunta
"¿implemento inline, con subagentes, o delegando a Codex (yo reviso el diff)?". Al elegir cross,
esta skill ejecuta el paso de aplicar cambios; tests+build, `verify` de AC, staging y commit
siguen siendo de sdd-flow con sus STOPs.

**2. Modo directo con un plan existente:**
```
/cross-implement PLAN.md
```
→ gates previos (work order legible, árbol limpio, proof_cmd resuelto), lanza a Codex con
`workspace-write`, revisa el diff, corre la prueba, itera hasta 2 fixes y presenta diff + prueba
para el commit.

**3. Orden de trabajo conversacional:**
```
que Codex implemente el renombre de UserService a AccountService en todo src/, prueba: npm test
```
→ destila el contrato a `cross-implement/work-order.md`, lo muestra, y sigue el flujo normal.

## Qué escribe en tu repo

El diff lo escribe el implementador en tu working tree, y el log y el scratch quedan junto al work
order. Además, cada delegación deja un **manifest de corrida** en `.cross-model/runs/`: un JSON de
unos 300 bytes con familia, transporte, duración y estado — los tres estados, porque un
`UNAVAILABLE` dice que la capacidad no existe en este entorno y un `PARTIAL` dice cuánto termina
haciendo el conductor. Local y untracked; agrega `.cross-model/` a `.git/info/exclude` si prefieres
que git deje de nombrarlo, y apágalo con `cross_model.manifest.mode: "off"`. Esquema en
`cross-review/reference.md` → "Manifest de corrida".

## Archivos

- `SKILL.md` — reglas, contrato de invocación, pasos, degradación.
- `reference.md` — vías de invocación por familia (con matriz de verificación end-to-end),
  prompt-contrato, revisión del conductor, fix loop, tiempos, scratch y log.
- `README.md` — este archivo.
