# Referencia — `sdd-incident-intake`

Detalle que no hace falta en cada corrida. `SKILL.md` indica cuándo abrir cada sección.

| Sección | Cuándo se lee |
|---|---|
| Verificar sin investigar | En el paso 2, si el veredicto no es evidente |
| El lote, vuelta por vuelta | Solo con `cantidad > 1` |
| Mirar aguas arriba | En el paso 4, siempre |
| Worktree con `orca-cli` | En el paso 6.1, antes de crear nada |
| Sembrar el entorno ignorado | En el paso 6.2 |
| El dossier | En el paso 6.3, al redactarlo |
| Despachar el flujo | En el paso 6.4 |
| Retirar del registro | En el paso 7 |
| Cuando algo falla | Solo si el despacho no arrancó o el retiro dejó residuos |

---

## Verificar sin investigar

El paso 2 tiene que llegar a un veredicto **sin hacer el trabajo del flujo**. La diferencia no es de
grado, es de pregunta:

| El intake pregunta | El flujo pregunta |
|---|---|
| ¿La afirmación describe el árbol de hoy? | ¿Por qué el árbol es así? |
| ¿La sección que cita existe y dice eso? | ¿Qué debería decir? |
| ¿La regla que dice faltar, falta? | ¿Dónde conviene ponerla? |

### Qué se comprueba

Solo lo **comprobable por lectura**: valores por default, existencia de secciones y reglas, presencia
o ausencia de una instrucción, coherencia entre lo que una skill produce y lo que otra exige. Todo eso
sale de leer y de `grep`.

Lo que **no** se comprueba acá: si el arreglo propuesto es el correcto, si hay una solución mejor, si
el defecto tiene otras manifestaciones. Son preguntas de diseño y las contesta el flujo.

### Dos comprobaciones que casi siempre pagan

**La fecha contra el árbol.** Si el mecanismo que el incidente describe cambió después de que se
registró, el diagnóstico puede haber envejecido:

```
git -C <repo_destino> log -1 --format='%h %ad %s' --date=short -S '<frase de la sección citada>' -- <archivo>
```

Si el commit es **posterior** al incidente, leer qué cambió antes de aceptar la descripción. Si es
**anterior**, el incidente se escribió sobre el árbol actual y no hay nada que actualizar.

**La regla que dice faltar.** Cuando el incidente afirma que algo no está —"la skill no dice X"— el
`grep` que lo confirma es el que más rinde, porque una ausencia es lo más fácil de afirmar mal:

```
grep -rniE '<dos o tres formas de decir X>' <archivos de la skill>
```

Salida vacía **con patrones que de verdad cubran las formas de decirlo** confirma la ausencia. Un solo
patrón demasiado literal da vacío siempre y no prueba nada.

### Cuándo parar y admitir

Si después de leer las secciones citadas y correr esos `grep` el veredicto sigue sin estar claro, **es
confirmado y se despacha**. Se anota en el dossier qué quedó sin comprobar y por qué — el flujo tiene
el aparato para resolverlo, el intake no.

Lo que **no** es una razón para rechazar: que el incidente esté mal escrito, que le falte un campo, que
mezcle dos cosas o que su propuesta no convenza. Nada de eso dice que el defecto no exista.

---

## El lote, vuelta por vuelta

Con `cantidad > 1` el ciclo entero se repite, y lo que cambia entre vueltas es el registro.

### El estado que se arrastra

Entre vueltas solo se lleva esto:

- **Cupos restantes** y **flujos abiertos** (para el reporte final).
- **Rechazados con su evidencia** — no viven en ningún dossier, así que si se pierden acá se pierden.
- **Descartados por agrupamiento**: un incidente que se evaluó como relacionado y no entró **sigue
  siendo candidato** para su propio flujo en la vuelta siguiente. No queda quemado.

### Lo que se relee cada vuelta

El **índice**, porque la vuelta anterior lo cambió. La cabecera de reglas no: no cambia.

Releer el índice no es formalidad — es lo que impide elegir un incidente que la vuelta anterior ya se
llevó como relacionado. Elegir desde una lista en memoria es la forma exacta de despachar dos veces el
mismo incidente y descubrirlo cuando dos worktrees tocan las mismas líneas.

### Cuándo el lote termina antes

- **El registro se agotó.** Se abren los que haya y se dice.
- **Un gate quedó sin respuesta.** No se sigue con el resto: el usuario está mirando una decisión, y
  abrir worktrees mientras tanto le cambia el terreno abajo de los pies.
- **Un despacho no arrancó.** Se corrige ese antes de seguir; nunca se retira su incidente ni se pasa
  al siguiente dejando el worktree inerte.

### Nombres de worktree

Cada flujo necesita el suyo y son de la misma tanda, así que los nombres genéricos colisionan. Derivar
el nombre de **qué corrige**, no de la posición en el lote: `incidente-2` no le dice nada a nadie
dentro de una semana.

---

## Mirar aguas arriba

El paso 4 contesta dos preguntas que el árbol local no puede contestar: **¿esto ya se arregló en el
remoto?** y **¿alguien lo está arreglando ahora?**. La entrada es la **superficie editable** que salió
del paso 3 — los archivos que el diff iba a tocar.

Los comandos de acá **no usan pipes ni redirecciones**, así que corren igual en POSIX y en PowerShell
sin una segunda variante. Mantenerlos así al editarlos.

### 1. Sincronizar las refs

```
git -C <repo_destino> fetch --quiet origin
```

Sin esto, `origin/<default>` es la foto de la última sincronización y **todo lo que sigue devuelve
vacío por mirar un remoto viejo** — un verde que se lee igual que un verde real. Actualiza refs
remotas: no toca el árbol, no mueve ramas locales, no necesita árbol limpio.

Resolver el nombre de la rama por default en vez de asumir `main`:

```
git -C <repo_destino> rev-parse --abbrev-ref origin/HEAD
```

Devuelve **`origin/<default>`, con el prefijo puesto** — `origin/main`, no `main`. La rama local es
esa cadena sin el `origin/`, y confundirlas produce un `origin/origin/main` que corta con "unknown
revision" en el mejor caso.

### 2. Commits que están arriba y no acá

```
git -C <repo_destino> log --oneline main..origin/main -- <archivo> <archivo>
```

`main..origin/main` es exactamente "lo que tiene el remoto y no tiene el local". Sin el `--` y la
lista de archivos trae todo el retraso, que no dice nada; con ellos, trae solo lo que toca la
superficie del incidente.

**El complemento que caza lo que el cruce por ruta no ve** — un arreglo que resolvió lo mismo en otro
archivo:

```
git -C <repo_destino> log --oneline -S "<frase literal que el incidente cita>" main..origin/main
```

Es complemento, no reemplazo: `-S` cuenta apariciones de una cadena, así que solo encuentra el commit
si el arreglo movió esa frase exacta.

### 3. Releer contra `origin`, no contra el árbol

Si algo apareció, la tabla del paso 2 se midió sobre archivos viejos. Rehacer **las filas que ese
commit toca**, leyendo la versión del remoto:

```
git -C <repo_destino> show origin/main:<archivo>
git -C <repo_destino> diff main origin/main -- <archivo>
```

El `show` sirve para volver a correr el `grep` del paso 2 sobre el contenido de arriba; el `diff` para
ver qué cambió y decidir si el defecto sobrevivió. **El veredicto se re-emite sobre `origin/<default>`
porque ahí nace el worktree**, no sobre el árbol local.

### 4. PRs abiertos

Con GitHub, si `gh` está y está autenticado:

```
gh pr list --state open --json number,title,headRefName,url
gh pr diff <número> --name-only
```

El primero da los candidatos; **el segundo es el que decide**, cruzando sus archivos contra la
superficie. Filtrar por título es lo que produce los dos errores simétricos: un PR con título ajeno
que toca la sección exacta, y uno con título parecido que no toca nada.

Con Bitbucket, el mismo cruce con las herramientas de listado de PR y de diff del MCP `bb_*` — las
que usa `bitbucket-code-review`. La forma de la comprobación no cambia: **archivos del PR ∩
superficie del incidente**.

**Degradación.** Sin `gh` (o sin auth), sin MCP, o sin remoto configurado: se reporta
`PRs: no comprobado — <razón>` y se sigue. Lo que no se puede hacer es omitirlo del reporte: un
chequeo que no corrió y uno que salió limpio se leen igual si nadie los distingue.

### Qué queda escrito

Sea cual sea el resultado, el dossier lleva la sección "Estado aguas arriba" (ver "El dossier" →
sección 6). Un flujo que no sabe que hay un PR abierto sobre sus archivos lo descubre en el conflicto.

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
`hookSettings.scripts.setup`, que hace falta en el paso 6.2.

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

**Que difieran no dice de qué lado está el retraso, y el reset solo es correcto en una dirección:**

```
git -C <repo_destino> merge-base --is-ancestor origin/main main
```

Sale 0 cuando el **local contiene a `origin`** — es decir, el local está adelante y el worktree nació
atrasado. Ese es el único caso donde se realinea. Si sale distinto de 0, el que está adelante es
`origin` (o las ramas divergieron), y **resetear al `main` local le borra al worktree el arreglo que
vino de arriba** — que es justamente lo que el paso 4 fue a buscar. Ante divergencia real, se para y
se le muestra al usuario.

Con el ancestro confirmado y el worktree **limpio y recién creado**:

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

El criterio de `SKILL.md` → 6.2 decide qué entra. Para cada candidato, la pregunta es:

> ¿Esto es **cómo se configura el flujo en este repo**, o es **lo que otra corrida dejó**?

Lo primero se siembra, lo segundo no. Todas las rutas de abajo se leen **dentro del
`<repo_destino>`**, que es el repo donde va a correr el flujo — nunca el repo donde vive esta skill.
Casos que se ven seguido:

- `.specify/config.yml` — **siembra**. Es el config de `sdd-flow`: comandos de test/build/lint, modo
  de implementación, política cross-model. Sin él la skill entra por `init`.
- `.specify/constitution.md` — **siembra** si existe. Son las restricciones del proyecto.
- `.claude/settings.local.json` — **siembra**. Permisos ya concedidos; sin ellos el flujo se detiene
  en prompts que en el árbol principal ya estaban resueltos.
- `.co-explore/`, `.cross-review/`, `.cross-implement/`, `.cross-model/` — **no**. Artefactos de
  corridas.
- `.plans/` — **no**, salvo retoma. En una retoma se copia **la carpeta de ese plan y solo esa**.
- `node_modules/`, `__pycache__/`, `.idea/` — **no**. Si el flujo necesita dependencias, se instalan
  en el worktree; una caché copiada puede traer rutas absolutas del árbol viejo adentro.

Ante un candidato que no encaja en ninguna fila: preguntarle al usuario. Es más barato que sembrar de
más.

### Copiar y comprobar

**Por archivo, no por directorio, y creando los intermedios.** El directorio destino puede existir ya
—medio versionado— y entonces copiar la unidad entera la anida adentro en vez de fusionarla:

```
for f in $(git -C <repo_destino> status --porcelain --ignored=matching -uall \
             | grep '^!!' | awk '{print $2}' | grep -E '^\.(specify|claude)/'); do
  mkdir -p "<worktree>/$(dirname "$f")"
  cp -a "<repo_destino>/$f" "<worktree>/$f"
done
```

PowerShell:

```
git -C <repo_destino> status --porcelain --ignored=matching -uall |
  Where-Object { $_ -like '!!*' } | ForEach-Object { ($_ -split '\s+')[1] } |
  Where-Object { $_ -match '^\.(specify|claude)/' } | ForEach-Object {
    $d = Split-Path "<worktree>\$_" -Parent
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    Copy-Item -Force "<repo_destino>\$_" "<worktree>\$_"
  }
```

Después, **las tres comprobaciones** — cada una caza una forma distinta de siembra rota:

```
git -C <worktree> check-ignore -v .specify/config.yml .claude/settings.local.json
git -C <worktree> status --porcelain
ls <worktree>/.specify/config.yml <worktree>/.claude/settings.local.json
```

1. `check-ignore` con salida por cada archivo → el destino los ignora. **Sin salida = no los ignora**,
   y van a terminar en un commit del flujo.
2. `status --porcelain` sin las rutas sembradas → confirma lo anterior desde el otro lado.
3. `ls` de cada archivo **en la ruta esperada** → caza el anidamiento. Sin ésta, un
   `.claude/.claude/settings.local.json` pasa las dos primeras sin una queja: también está ignorado,
   así que el árbol se ve limpio y la siembra parece hecha.

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
   (`archivo:línea` sirve acá; el registro de origen las prohíbe, el dossier las necesita). Si el
   paso 4 obligó a rehacer filas contra `origin`, decir cuáles y contra qué commit.
6. **El estado aguas arriba** — el resultado del paso 4, en tres líneas: los commits de
   `origin/<default>` que tocan la superficie y **ya están en la base de este worktree**, los PRs
   abiertos que la tocan con su número y sus archivos, y —si no se pudo mirar— que no se comprobó y
   por qué. Un PR abierto sobre los mismos archivos es una restricción para este flujo, no un dato de
   color: cambia el alcance que conviene tomar.
7. **Las decisiones abiertas** — dónde el árbol ya cambió respecto de lo que el incidente asume, con
   las opciones nombradas y **sin recomendar una**. Decir explícitamente que no está pre-decidida.
8. **Las restricciones del repo destino** que este flujo puede violar sin darse cuenta: topes de
   verificación, prohibiciones sobre directorios, guardas que hay que correr y **cómo se leen** (hay
   guardas cuyo código de salida no es la señal de salud).
9. **Dónde se registran los incidentes** si alguna skill falla durante el flujo — con la ruta del
   árbol principal, porque un worktree no hereda `.plans/`.

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
que el dossier detalla. **Si el paso 4 encontró un PR abierto sobre la superficie, va en el prompt**
con su número: es una condición de contorno del trabajo, y el dossier solo se lee si el agente llegó
a leerlo.

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
| El flujo pregunta cosas que el config ya responde | El worktree no está sembrado | Sembrar `.specify/` del `<repo_destino>` y avisarle al agente que relea el config |
| El flujo arranca un `init` que nadie pidió | Igual que arriba, caso agudo | Igual, y verificar que el `init` no haya sobrescrito nada |
| `git status` del worktree muestra lo sembrado | El destino no ignora esos paths | Sacarlos del árbol y resolver el ignore antes de seguir |
| El diff del flujo sale contra un árbol raro | El worktree nació en `origin/<default>` | Se previene en 6.1. Ya avanzado, es rebase — y el techo de proporción del repo, si lo tiene, se midió contra el commit equivocado |
| El registro quedó sin la fila pero con la sección | El retiro tocó un solo lugar | Completar el retiro y **registrar el incidente**: es un defecto de procedimiento |
| El flujo abre un diff sobre líneas que ya no existen | El paso 4 no corrió, o corrió sin `fetch` | Rehacer el paso 4 y re-emitir el veredicto contra `origin/<default>`. Si el defecto ya no está, el flujo se cierra y el incidente se reporta como resuelto aguas arriba |
| El PR del flujo entra en conflicto con otro PR abierto | El cruce del paso 4 se hizo por título y no por archivos | Cruzar `gh pr diff --name-only` contra la superficie. Con el conflicto ya abierto, el orden de merge lo decide el usuario |
| El worktree perdió commits que estaban en `origin` | El realineo de 6.1 se hizo sin comprobar la dirección | `reset --hard origin/<default>` y rehacer 6.2. Es un defecto de procedimiento: se registra |

Todo fallo atribuible a una skill SDD —esta incluida— se registra según la regla del archivo de
instrucciones del `<repo_destino>`: en su `.plans/incidentes-skills.md` del **árbol principal**,
resuelto con `git worktree list` si
la sesión corre en un worktree.
