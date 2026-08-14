# Referencia — `sdd-incident-intake`

Detalle que no hace falta en cada corrida. `SKILL.md` indica cuándo abrir cada sección.

| Sección | Cuándo se lee |
|---|---|
| Worktree con `orca-cli` | En el paso 5.1, antes de crear nada |
| Sembrar el entorno ignorado | En el paso 5.2 |
| El dossier | En el paso 5.3, al redactarlo |
| Despachar el flujo | En el paso 5.4 |
| Retirar del registro | En el paso 6 |
| Cuando algo falla | Solo si el despacho no arrancó o el retiro dejó residuos |

---

## Worktree con `orca-cli`

**Antes de nada, resolver el ejecutable** siguiendo la skill `orca-cli` (`ORCA_CLI_COMMAND` →
`orca-dev` → `orca-ide` en Linux fuera de Orca → `orca`) y cargar la guía versionada con
`<orca> skills get orca-cli`. Los comandos de abajo son el esqueleto; **los flags exactos los fija la
guía del binario**, que cambia entre releases.

### 1. Resolver el repo destino

```
<orca> repo list --json
```

Buscar la entrada cuyo `path` sea el `repo_destino` y copiar su `id`. Del mismo JSON sale
`hookSettings.scripts.setup`, que hace falta en el paso 5.2.

### 2. Crear

```
<orca> worktree create --repo id:<repoId> --name <nombre> --no-parent --agent <claude|codex> --json
```

- `--no-parent` porque el flujo es trabajo independiente, no una rama apilada.
- **Omitir `--base-branch`** para que use la base del repo.
- `--agent` pone al agente en la **primera** terminal. No crear la terminal aparte: eso deja un shell
  huérfano cuando el repo no tiene tabs por default configurados.
- El `worktree.id` de la respuesta ya trae las dos partes (`<repoId>::<path>`). Copiarlo entero: el
  `repoId` solo no es un selector de worktree.

### 3. Verificar la base — no es opcional

`baseRef` sale como `refs/remotes/origin/<default>`. Si el `main` local tiene commits sin pushear, el
worktree nace atrás y **la respuesta JSON se lee perfectamente normal**: trae `head` y `baseRef`, y
ninguno de los dos dice "estás atrasado".

```
git -C <repo_destino> rev-parse main origin/main
```

Si difieren y el worktree está **limpio y recién creado**:

```
git -C <worktree> status --porcelain      # tiene que salir vacío ANTES del reset
git -C <worktree> reset --hard <sha-de-main-local>
```

El `status` previo no es ceremonia: `reset --hard` sobre un árbol con cambios los destruye sin aviso.

Si el usuario pidió explícitamente basarse en otra rama, esto no aplica — se respeta lo que pidió.

---

## Sembrar el entorno ignorado

### Derivar el inventario

```
git -C <repo_destino> status --porcelain --ignored=matching -uall | grep '^!!'
```

Eso lista lo ignorado. Para lo untracked-pero-no-ignorado, `git status --porcelain` a secas. Leer la
salida **en el momento**: una lista transcrita de una corrida anterior envejece, y una entrada muerta
se lee igual de bien que una viva.

### Clasificar

El criterio de `SKILL.md` → 5.2 decide qué entra. Para cada candidato, la pregunta es:

> ¿Esto es **cómo se configura el flujo en este repo**, o es **lo que otra corrida dejó**?

Lo primero se siembra, lo segundo no. Casos que se ven seguido:

- `../../../.specify/config.yml` — **siembra**. Es el config de `sdd-flow`: comandos de test/build/lint, modo
  de implementación, política cross-model. Sin él la skill entra por `init`.
- `.specify/constitution.md` — **siembra** si existe. Son las restricciones del proyecto.
- `../../../.claude/settings.local.json` — **siembra**. Permisos ya concedidos; sin ellos el flujo se detiene
  en prompts que en el árbol principal ya estaban resueltos.
- `../../../.co-explore`, `../../../.cross-review`, `../../../.cross-implement`, `../../../.cross-model` — **no**. Artefactos de
  corridas.
- `../../../.plans` — **no**, salvo retoma. En una retoma se copia **la carpeta de ese plan y solo esa**.
- `node_modules/`, `__pycache__/`, `../../../.idea` — **no**. Si el flujo necesita dependencias, se instalan
  en el worktree; una caché copiada puede traer rutas absolutas del árbol viejo adentro.

Ante un candidato que no encaja en ninguna fila: preguntarle al usuario. Es más barato que sembrar de
más.

### Copiar y comprobar

```
cp -a <repo_destino>/.specify <worktree>/.specify
cp -a <repo_destino>/.claude  <worktree>/.claude
```

PowerShell:

```
Copy-Item -Recurse -Force <repo_destino>\.specify <worktree>\.specify
Copy-Item -Recurse -Force <repo_destino>\.claude  <worktree>\.claude
```

Después, **las dos comprobaciones** — sin ellas la siembra puede estar rota de dos formas distintas:

```
git -C <worktree> check-ignore -v .specify/config.yml .claude/settings.local.json
git -C <worktree> status --porcelain
```

1. `check-ignore` con salida por cada archivo → el destino los ignora. **Sin salida = no los ignora**,
   y van a terminar en un commit del flujo.
2. `status --porcelain` sin las rutas sembradas → confirma lo anterior desde el otro lado.

Un archivo puede estar ignorado en el árbol principal por `.git/info/exclude` (que **sí** comparten
los worktrees del mismo repo) o por el ignore global del usuario (que también aplica). Lo que **no**
viaja es `info/exclude` a un **clone** — si el destino es un clone y no un worktree, la comprobación
es la que salva.

### El hook de setup

```
<orca> repo show --repo id:<repoId> --json
```

`hookSettings.scripts.setup` puede ya copiar estos directorios — es un patrón común. Si lo hace:

- **No copiar encima.** El hook puede adaptar lo que copia al worktree; pisarlo revierte esa
  adaptación.
- Comprobar igual que el resultado está: un hook con `setupRunPolicy` que no corrió deja el worktree
  vacío y el `--json` no lo dice.

Si el hook está vacío y este repo va a repetir el flujo seguido, vale sugerirle al usuario ponerlo
ahí — pero eso es un cambio de configuración de su Orca, así que **se sugiere, no se hace**.

---

## El dossier

Va en `<worktree>/.plans/incidentes-a-corregir.md`. Es el contrato completo con un flujo que arranca
sin contexto de esta sesión, y **la única copia** de los incidentes tomados.

### Secciones obligatorias

1. **Encabezado que declara qué es** — que es la entrada del flujo, que los incidentes ya fueron
   retirados del registro de origen y que por lo tanto no hay otro lugar donde buscarlos.
2. **La causa raíz compartida**, en una frase, como cita destacada. Es lo que justifica que estos
   incidentes vayan juntos; si no se puede escribir sin forzarla, el agrupamiento del paso 3 estaba
   mal y hay que volver.
3. **La superficie común** — archivos y secciones que el diff va a tocar.
4. **Cada incidente verbatim**, con su tabla de metadatos completa. No resumidos, no parafraseados.
5. **La verificación previa** — la tabla del paso 2, con las citas textuales que la sostienen
   (`archivo:línea` sirve acá; el registro de origen las prohíbe, el dossier las necesita).
6. **Las decisiones abiertas** — dónde el árbol ya cambió respecto de lo que el incidente asume, con
   las opciones nombradas y **sin recomendar una**. Decir explícitamente que no está pre-decidida.
7. **Las restricciones del repo destino** que este flujo puede violar sin darse cuenta: topes de
   verificación, prohibiciones sobre directorios, guardas que hay que correr y **cómo se leen** (hay
   guardas cuyo código de salida no es la señal de salud).
8. **Dónde se registran los incidentes** si alguna skill falla durante el flujo — con la ruta del
   árbol principal, porque un worktree no hereda `../../../.plans`.

### Lo que no va

- Recomendaciones sobre la decisión abierta. El flujo tiene que decidirla con criterio propio; una
  recomendación escrita acá se transcribe en vez de pensarse.
- Rutas del proyecto donde el incidente se observó. Al flujo no le sirven.
- Un plan de implementación. Eso lo produce `sdd-flow`, es su trabajo.

---

## Despachar el flujo

### Esperar a que el agente esté listo

```
<orca> terminal list --worktree id:<repoId>::<worktreePath> --json
<orca> terminal wait --terminal <handle> --for tui-idle --timeout-ms 90000 --json
```

Mandar antes de `tui-idle` pierde el texto: el TUI todavía no tiene dónde recibirlo.

### El prompt

**Una sola línea.** Un salto de línea en el medio envía el texto por la mitad y el resto queda
huérfano en el buffer.

**Sin comillas dobles ni apóstrofes** si va entre comillas simples del shell — más simple que escapar.

Contenido: qué se corrige, la causa raíz compartida en una frase, **la ruta del dossier con la orden
de leerlo entero antes de cualquier otra cosa y la advertencia de que es la única copia**, la
superficie a tocar, la decisión abierta señalada como no pre-decidida, y las restricciones del repo
que el dossier detalla.

### Enviar en dos tiempos

```
<orca> terminal send --terminal <handle> --text '<prompt en una linea>' --json
<orca> terminal read  --terminal <handle> --json
<orca> terminal send  --terminal <handle> --text "" --enter --json
```

**Por qué separado del Enter:** un texto largo entra al TUI como bloque pegado y se muestra colapsado
(`[Pasted text #1]`). Un `--enter` en el mismo envío puede ser consumido por el autocompletado del
menú de slash commands en vez de enviar el mensaje. El `read` intermedio confirma que el texto entró
entero antes de confirmarlo.

### Diferencia entre familias

**El prefijo de invocación cambia con la familia.** Es lo único que cambia — el cuerpo del prompt es
el mismo:

| Agente | Cómo arranca el flujo |
|---|---|
| `claude` | **`/sdd-flow <contexto>`** |
| `codex` | **`$sdd-flow <contexto>`** |

No es intercambiable: el prefijo equivocado deja el texto como un mensaje común, el agente contesta
razonablemente **sin la skill cargada**, y eso se lee igual que un arranque exitoso.

`sdd-flow` tiene `disable-model-invocation: true` —clave de Claude Code— así que en Claude es
**solo-slash**: no se puede invocar con el Skill tool ni pedírselo en prosa.

Del lado de Codex, las skills se resuelven desde `~/.agents/skills/`, el alias cross-runtime donde
las de este ecosistema están simlinkeadas. **Comprobar el symlink antes de despachar a `codex`** en
vez de asumirlo:

```
ls -l ~/.agents/skills/sdd-flow
```

### Confirmar el arranque — el control que cierra el paso

```
<orca> terminal read --terminal <handle> --json
```

Buscar la señal de que **la skill cargó**, no de que el agente respondió. En Claude Code es una línea
explícita de carga de skill. Un agente que contesta razonablemente sin haber cargado la skill es el
modo de falla exacto que este control existe para cazar: la respuesta se lee bien y el flujo no es un
flujo.

### Marcar el worktree

```
<orca> worktree set --worktree id:<repoId>::<path> --comment "<qué flujo corre acá>" --json
```

Es lo que hace legible la tarjeta en Orca cuando hay varios worktrees abiertos.

---

## Retirar del registro

El retiro toca **dos lugares**, y el orden entre ellos no importa; que estén los dos, sí.

**El índice** — una edición exacta sobre la fila. Anclar en el texto de la fila anterior y la
posterior para no borrar de más.

**El cuerpo** — la sección completa con su separador. Cuando los incidentes tomados son los
**últimos** del archivo, alcanza con cortar desde el separador que los precede; cuando están en el
medio, es una edición por sección.

Un corte por offset tiene que verificar sus supuestos antes de escribir:

```python
marca = '\n---\n\n## <fecha y hora> — <inicio literal del título>'
i = s.find(marca)
assert i != -1                      # la marca existe
assert s.count('## <fecha y hora>') == 1   # y es única
```

Sin el `assert` de unicidad, un título repetido corta en el lugar equivocado y el archivo queda
plausible.

### Comprobar residuos

```
grep -n '<fecha y hora>' <registro>
grep -n '<término distintivo del título>' <registro>
```

Los dos, no uno: la fecha caza la sección, el término caza la fila del índice si la edición falló.
**Salida vacía en ambos = retirado.** Y contar líneas antes y después para reportarlo.

### Lo que nunca se toca

- La cabecera de reglas.
- Los incidentes que no se tomaron — **ni siquiera para "arreglarlos de paso"**. La regla 2 del
  registro dice que una reincidencia se agrega y nunca se edita; editar un incidente ajeno borra la
  frecuencia, que es lo único que distingue una trampa estructural de un descuido puntual.
- El orden cronológico de los que quedan.

---

## Cuando algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El agente responde pero la skill no cargó | El slash quedó dentro del texto pegado, o el agente es `codex` y no tiene el slash | Reenviar nombrando la skill y su ruta. No retirar nada hasta que cargue |
| El flujo pregunta cosas que el config ya responde | El worktree no está sembrado | Copiar `../../../.specify` y avisarle al agente que relea el config |
| El flujo arranca un `init` que nadie pidió | Igual que arriba, caso agudo | Igual, y verificar que el `init` no haya sobrescrito nada |
| `git status` del worktree muestra lo sembrado | El destino no ignora esos paths | Sacarlos del árbol y resolver el ignore antes de seguir |
| El diff del flujo sale contra un árbol raro | El worktree nació en `origin/<default>` | Se previene en 5.1. Ya avanzado, es rebase — y el techo de proporción del repo, si lo tiene, se midió contra el commit equivocado |
| El registro quedó sin la fila pero con la sección | El retiro tocó un solo lugar | Completar el retiro y **registrar el incidente**: es un defecto de procedimiento |

Todo fallo atribuible a una skill SDD —esta incluida— se registra según la regla del `../../../CLAUDE.md` del
repo: en `../../../.plans/incidentes-skills.md` del **árbol principal**, resuelto con `git worktree list` si
la sesión corre en un worktree.
