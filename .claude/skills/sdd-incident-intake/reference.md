# Referencia — `sdd-incident-intake`

Detalle que no hace falta en cada corrida. `SKILL.md` indica cuándo abrir cada sección.

| Sección | Cuándo se lee |
|---|---|
| Verificar sin investigar | En el paso 2, si el veredicto no es evidente |
| El lote, vuelta por vuelta | Solo con `cantidad > 1` |
| Mirar aguas arriba | En el paso 4, siempre |
| Resolver la plataforma | En el paso 6.1, **antes** de crear nada |
| Clasificar el hook de setup | En 6.1, después de resolver y **antes** de elegir con qué crear |
| Crear el worktree | En 6.1, con la primitiva que la clasificación eligió |
| Adoptar, abrir y rotular | En 6.1, tras crear |
| Sembrar el entorno ignorado | En el paso 6.2 |
| El dossier | En el paso 6.3, al redactarlo |
| Despachar el flujo | En el paso 6.4 |
| El volcado a issues | En el modo `volcar`, antes de publicar |
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

### Tres comprobaciones que casi siempre pagan

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

**La implementación que dice faltar.** Es la anterior en su forma más cara, y lleva método propio
porque el `grep` que la resuelve **no es el mismo**. Cuando el incidente afirma que un procedimiento
determinista no está implementado, buscar por **tipo de archivo** no alcanza: acá una implementación
puede vivir embebida como bloque ejecutable dentro del `.md` normativo. Se traza **productor → bloque
→ consumo**, en ese orden:

```
grep -rn '@bloque:' <archivos de la skill>
git -C <repo_destino> log --oneline -S '<ancla del bloque>' -- <archivo>
```

El primero encuentra la implementación donde de verdad vive; el segundo dice **desde cuándo**, que es
lo que decide si el incidente nació viejo. Si el bloque existe y es anterior al incidente, la
afirmación es falsa aunque el incidente esté impecablemente escrito.

El caso que obliga a escribir esto: dos incidentes afirmaron que una cadena de integridad estaba
especificada solo en prosa, sin implementación en ningún lado, y que por lo tanto el gate que promete
rechazar contratos rotos no rechazaba ninguno. Era falso. La cadena existía como bloque POSIX con su
gemelo PowerShell y un corpus de calibración de cinco casos, desde **un mes antes**. El incidente
había buscado `sha256` entre los `scripts/*.py` y concluido de la ausencia. **Un intake que corre ese
mismo `grep` llega a la misma conclusión falsa**, lo marca confirmado y despacha un flujo a escribir
lo que ya está — y los dos eran la prueba estrella del informe que los citó.

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

## Resolver la plataforma

**Antes de crear nada.** La plataforma no se fija: se resuelve consultando las **dos identidades
vivas**, y el resultado gobierna cada rama de este paso. El criterio vive acá, escrito y
autocontenido: esta skill se instala como copia y corre sobre repositorios ajenos, así que no puede
depender de la ruta de ningún script de otro repositorio. La **sede** de estos estados y de esta
matriz es `skills/sdd-flow/reference.md` → «Resolver la plataforma de terminales», y esta copia
**deriva de ella**: la dirección es esa y no la inversa. Sigue sin haber dependencia de ejecución
sobre ningún script, que es lo que permite aplicarla sobre un repositorio ajeno.

### Los cuatro estados por identidad

Cada plataforma se consulta por su identidad de panel. Los estados son cuatro y no dos, porque
«presente» no es «utilizable»:

| Estado | Qué se observó |
|---|---|
| `resuelve` | la identidad existe **y** la plataforma la reconoce como panel vivo |
| `rancia` | la identidad existe y la plataforma **no** la reconoce |
| `ausente` | no hay identidad declarada |
| `inconsultable` | hay identidad y la consulta a la plataforma falló |

### La matriz, y su destino

**Las variables son las que el runtime exporta de verdad, y la salida se parsea, no se grepea.**
`HERDR_PANE_ID` contra `herdr pane list`, y `ORCA_TERMINAL_HANDLE` contra `orca terminal list
--json`: la pertenencia de la identidad al conjunto vivo **es** el predicado. Inventar un nombre de
variable o un subcomando de consulta individual tiene un modo de falla mudo — la condición queda
falsa en una sesión sana y el destino cae a `headless`, que es indistinguible de no tener plataforma.

> **Por qué el parseo y no un `grep`, con el caso que lo obligó.** Un `grep` del literal acredita
> `resuelve` sobre una salida **truncada o malformada** que apenas contenga `"handle":"term-1"`, y ahí
> la comprobación deja de fallar cerrada: medido con una salida `not-json {"handle":"term-1"` que sale
> con código 0. Y ante bytes ilegibles devuelve `rancia`, que es la lectura que el adaptador dejó de
> hacer a propósito. Las dos son propiedades **estructurales** de la salida, y ningún patrón de texto
> las distingue: por eso este es el único lugar del procedimiento donde se sube de `grep` a un
> intérprete.
>
> **Y la consulta corre adentro de ese intérprete, no antes.** Una sustitución de comandos del shell
> **no conserva los bytes NUL**: medido, un CLI que emite `"handle":"term\0-1"` le entrega al parser
> `"term-1"`, que coincide con la variable y acredita `resuelve` sobre una salida corrupta. Parsear
> estricto no alcanza si los bytes ya se sanearon en el camino, así que el proceso hijo se lanza desde
> adentro y de ahí salen tanto su salida cruda como su código.

```sh
# uso: estado_identidad <herdr|orca>  → imprime resuelve|rancia|ausente|inconsultable
# la consulta corre DENTRO del intérprete: una sustitución de comandos del shell no conserva
# los bytes NUL, así que una salida corrupta llegaría saneada y se acreditaría como viva
estado_identidad() {
  estado=$(python3 -c 'import json, os, subprocess, sys
CUAL = {"herdr": ("HERDR_PANE_ID", ["herdr","pane","list"], "panes", "pane_id"),
        "orca":  ("ORCA_TERMINAL_HANDLE", ["orca","terminal","list","--json"], "terminals", "handle")}
if sys.argv[1] not in CUAL: print("inconsultable"); raise SystemExit
var, cmd, caja, clave = CUAL[sys.argv[1]]
valor = os.environ.get(var)
if not valor: print("ausente"); raise SystemExit
try: hecho = subprocess.run(cmd, capture_output=True, timeout=15)
except (OSError, subprocess.SubprocessError): print("inconsultable"); raise SystemExit
if hecho.returncode != 0: print("inconsultable"); raise SystemExit
try: texto = hecho.stdout.decode("utf-8")
except UnicodeDecodeError: print("inconsultable"); raise SystemExit
try: raiz = json.loads(texto)
except ValueError: raiz = {}
if not isinstance(raiz, dict): raiz = {}
hijos = raiz.get("result", raiz)
hijos = hijos.get(caja, []) if isinstance(hijos, dict) else []
print("resuelve" if valor in {h.get(clave) for h in hijos if isinstance(h, dict)} else "rancia")
' "$1" 2>/dev/null)
  [ -n "$estado" ] || estado=inconsultable   # sin intérprete no se acredita nada
  echo "$estado"
}
# uso: resolver_plataforma [plataforma-pedida]
#   sigue: imprime "<plataforma> <identidad>" y devuelve 0
#   para:  imprime "headless <causa>"        y devuelve 1
resolver_plataforma() {
  pedida="${1:-}"
  eh=$(estado_identidad herdr); eo=$(estado_identidad orca)
  if [ -n "$pedida" ]; then
    case "$pedida" in
      herdr) [ "$eh" = resuelve ] && { echo "herdr $HERDR_PANE_ID"; return 0; }
             echo "headless override-herdr-$eh"; return 1 ;;
      orca)  [ "$eo" = resuelve ] && { echo "orca $ORCA_TERMINAL_HANDLE"; return 0; }
             echo "headless override-orca-$eo"; return 1 ;;
      *)     echo "headless override-no-reconocido"; return 1 ;;
    esac
  fi
  case "$eh:$eo" in
    resuelve:resuelve) echo "headless ambas-resuelven"; return 1 ;;
    resuelve:*)        echo "herdr $HERDR_PANE_ID";     return 0 ;;
    *:resuelve)        echo "orca $ORCA_TERMINAL_HANDLE"; return 0 ;;
    *)                 echo "headless $eh:$eo";         return 1 ;;
  esac
}
```

**Emite dos campos, la plataforma y la identidad, y el segundo no es decorativo:** es lo que
revalida cada efecto. Un destino a secas obligaría a re-resolver, que es volver a **elegir**
plataforma en vez de **comprobar** la que ya se eligió.

> **De dónde salió esta matriz, y las dos divergencias que conserva.** Estados, variables y destinos
> se derivaron del adaptador que este ecosistema retiró, y esa derivación ya ocurrió: **la sede es
> ahora esta**, no aquel archivo, y la dirección no vuelve a invertirse. Se dejan escritas las dos
> divergencias porque son decisiones y no accidentes, no porque haya nada contra lo que cotejar.
> Cotejados en su momento caso por caso con la misma entrada —salida válida, identidad
> ausente de la lista, JSON truncado, bytes ilegibles, salida vacía y consulta fallida—, los dos
> coincidían. Difieren en dos puntos, los dos declarados:
>
> - el adaptador reserva un código propio para las **dos** identidades inconsultables; acá ese caso
>   cae en `headless`, que es el mismo destino que su propia tabla le asigna.
> - ante un JSON **válido** cuya raíz no es un objeto, el adaptador **termina con una excepción** en
>   vez de emitir su sobre; este bloque comprueba el tipo antes de indexar y resuelve `rancia`. La
>   divergencia es deliberada y va hacia el lado seguro: **no se replica un fallo**.
>
> Si falta el intérprete, el estado es `inconsultable` y no `rancia`: sin con qué comprobar no se
> acredita una identidad.

**`headless` no es un modo degradado de este paso: es su parada.** El paso 6 necesita un agente
interactivo al que despachar, y sin plataforma utilizable no hay dónde crearlo. Ante `headless` —por
cualquiera de sus causas, incluida la de **las dos identidades vivas**, donde no hay observación que
diga cuál es el anfitrión— el despacho **se detiene**, el registro queda intacto y ningún incidente
se retira. Es el estado del que se reintenta.

### El override del usuario dirige, no suple

**El override es el parámetro `plataforma`**, con valores `herdr` y `orca`, y es la única puerta por
la que una petición del usuario entra a este paso. Se captura del pedido —“despacha esto en Herdr”,
“que corra en Orca”— y **no tiene default**: sin él se llama a `resolver_plataforma` sin argumento y
decide la matriz. Un valor que no sea uno de esos dos no se interpreta ni se corrige: cae en
`override-no-reconocido`, que es parada.

Si el usuario pide una plataforma, esa petición **elige cuál se intenta**, no acredita que sirva:
viaja como **argumento** de `resolver_plataforma` —no como una decisión tomada antes de llamarlo— y
la identidad de la elegida se comprueba igual:

| Caso | Resultado |
|---|---|
| override, con su identidad `resuelve` | se usa la pedida |
| override, con su identidad `rancia`, `ausente` o `inconsultable` | **se detiene**; la petición no sustituye la comprobación |
| sin override, una sola identidad `resuelve` | se usa esa |
| sin override, las dos `resuelven` | **se detiene**: no hay observable que identifique al anfitrión |
| las dos `resuelven` **con** override comprobado | el override **desempata** — es el único caso en que lo hace |

### La identidad se revalida antes de cada efecto

Una identidad viva al resolver puede dejar de serlo a mitad del paso, y cada efecto que dependa de
ella la vuelve a comprobar **inmediatamente antes**, con `estado_identidad "<plataforma>"` sobre la
plataforma ya resuelta — **nunca** con `resolver_plataforma`, que volvería a elegir en vez de
comprobar, y que ante una identidad caída podría devolver la **otra** plataforma a mitad del paso.
Los efectos son estos cinco y la lista es
exhaustiva: **crear** el worktree por la plataforma, **adoptar** un árbol creado con Git, **abrir** el
panel, **arrancar** el agente y **rotular** el worktree. Si la revalidación falla, ese efecto no se
ejecuta y se aplica la fila que le corresponda en «El contrato de fallo por fase».

---

## Clasificar el hook de setup — antes de elegir cómo crear

**El orden importa y es el opuesto al que parece.** La clasificación del hook **decide con qué
primitiva se crea el worktree**, así que ocurre antes de crear, no después. El `repo_destino` es un
parámetro de cada corrida: el mismo procedimiento puede encontrar un hook vacío en uno, reproducible
en otro e inseparable de su plataforma en un tercero.

### De dónde se lee, por plataforma

| Plataforma | Autoridad del hook |
|---|---|
| Orca | `orca repo list --json` → la entrada cuyo `path` es el `repo_destino` → su `hookSettings.scripts.setup`. La variante por repositorio es `orca repo show --repo id:<repoId> --json`, y **el selector es obligatorio**: sin él la orden falla con `invalid_argument` antes de clasificar nada. Se prefiere `list` porque no exige haber resuelto el id todavía |
| Herdr | no expone hooks por repositorio: el estado es `ausente` salvo que el `repo_destino` declare uno propio en su árbol |

### El predicado, con sus tres estados

| Estado | Cómo se reconoce | Qué cambia en la creación, en Herdr | Qué cambia en la creación, en Orca |
|---|---|---|---|
| `ausente` | la autoridad no declara script de setup | **Git**: `git worktree add` con el commit explícito, y adopción con `worktree open` | `--setup skip` |
| `reproducible` | declara un script **y** ese script se puede ejecutar fuera de la creación: es un ejecutable del árbol o un comando del `PATH`, sin argumentos que la plataforma inyecte | **Git**, y el hook se ejecuta después, con las condiciones de abajo | `--setup skip`, y el hook se ejecuta después, con las mismas condiciones |
| `inseparable` | declara un script que la plataforma invoca con contexto propio —argumentos, entorno o rutas que solo ella arma— | no se da: Herdr no declara hooks por repositorio | `--setup run`, que deja el hook en manos de la plataforma |

> **La ramificación es por estado y por plataforma, y la columna lo dice.** Dónde hay dos primitivas
> —Herdr— el estado elige entre ellas; donde la plataforma ofrece una sola —Orca— elige su política
> de setup. Las dos son ramas con postcondición propia, que es lo que el paso exige: lo que **no**
> se puede prometer es que la primitiva cambie en una plataforma que tiene una.

> **`inseparable` no es un fracaso, es una rama.** Conservar la creación específica donde el hook lo
> exige es la salida correcta: lo que el defecto pedía es que la plataforma se **resuelva**, no que
> una primitiva concreta desaparezca.

### Ejecutar el hook tras una creación con Git

Con `reproducible`, después de crear y antes de sembrar: se ejecuta **con el worktree nuevo como
directorio de trabajo**, con el entorno de la sesión y sin argumentos añadidos. Su **condición de
éxito** es salida cero; su **postcondición** es que el árbol siga limpio salvo por lo que el propio
hook declare.

**Los cuatro fallos de esta fase detienen el despacho**, cada uno con su estado escrito: la consulta
de la autoridad falla; el script está declarado pero no es legible; su ejecución sale distinto de
cero; o su postcondición no se cumple. Ninguno se degrada a «seguir sin hook».

---

## Crear el worktree

**La primitiva la eligió la clasificación anterior.** Lo común a las dos ramas va acá; los comandos
van en su fila.

### 1. Resolver el repo destino

Con la plataforma ya resuelta, obtener la identidad del `repo_destino` en ella. En Orca,
`orca repo list --json`; en Herdr, el repositorio se nombra por su ruta. Del mismo lugar sale la
autoridad del hook que la clasificación consultó.

### 2. Crear

| Plataforma | Rama `ausente` o `reproducible` | Rama `inseparable` |
|---|---|---|
| Herdr | `git -C <repo_destino> worktree add -b <rama> <ruta> <sha>`, y adoptar con `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` | no aplica: Herdr no declara hooks por repositorio |
| Orca | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup skip --agent <agente> --no-parent --json` | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup run --agent <agente> --no-parent --json` |

> **`--agent` va en las dos ramas, y no es redundante.** Una creación sin él abre un shell de
> fallback, y `orca terminal list` **observa** la terminal pero no arranca ninguna: sin la flag, las
> dos ramas llegan al despacho con una terminal viva y **sin agente de la familia esperada**, que es
> el estado que el control de familia iba a cazar recién al final.

> **En Orca la primitiva es una sola, y no porque se haya elegido así.** Su CLI **no tiene verbo de
> adopción**: `orca worktree create` no acepta una ruta destino —crea un checkout nuevo— y el grupo
> `orca worktree` no expone ningún otro que registre un árbol ya existente. Así que un worktree
> creado con Git en Orca **no se puede continuar**: no hay con qué registrarlo, y sin registro no hay
> panel, ni agente, ni rótulo. La rama de Git queda para Herdr, que sí adopta con `worktree open`.
>
> **Tampoco lo adopta por descubrimiento, y eso se midió en vez de suponerse.** Un worktree creado
> con `git worktree add` y consultado enseguida devuelve `selector_not_found`, en dos rutas
> distintas —una fuera del árbol habitual y otra hermana de un worktree que Orca **sí** resuelve—.
> Que resuelva ese otro prueba que alguien lo registró antes, no que los descubra. Es el control que
> cierra la búsqueda de una segunda primitiva: no la hay.
>
> **Lo que la clasificación decide en Orca es la política de setup** — `--setup skip` con hook
> `ausente` o `reproducible` (y entonces, si es `reproducible`, se ejecuta aparte con las condiciones
> de su sección), `--setup run` con `inseparable`. La consulta por corrida, la ramificación por estado
> y las postcondiciones por rama siguen enteras; lo único que no varía es la primitiva, porque la
> plataforma ofrece una sola. Prometer que variara exigiría un verbo que su CLI hoy no tiene.

**Crear con Git retira el peligro de base, no lo traslada.** El bloque que verificaba la base existía
porque el verbo de creación de una plataforma usa su referencia remota por defecto y el worktree podía
nacer atrasado sin que nada lo dijera. Pasando el **commit explícito** —el que el paso 4 ya
resolvió— ese peligro deja de existir: no hay que comparar ni realinear nada.

> **Donde crea la plataforma, el peligro sigue vivo: en Orca, en sus dos ramas.** `--base-branch`
> recibe el ref que el paso 4 resolvió, pero que la flag lo acepte **no se midió** como equivalente a
> pasarle un commit a Git, así que ahí se compara igual el `head` devuelto contra ese commit y se
> realinea **solo** si el que está adelante es el local. Ante divergencia real se para y se le muestra
> al usuario. En Herdr, donde crea Git con el commit explícito, no hay nada que comparar.

---

## Adoptar, abrir y rotular

Un árbol creado con Git **no lo conoce la plataforma**: sin adopción no se puede abrir el panel,
arrancar el agente ni rotular. Cada fila lleva su comando y el observable que lo acredita.

La adopción **ancla el repositorio de origen con `--cwd <checkout principal del repo_destino>`**, y
ese anclaje es el arreglo entero. Sin él, `worktree open` parte del **workspace enfocado**, que en un
lote ya es el worktree del flujo anterior. Tampoco sirve la variable de entorno del panel llamador:
identifica el workspace donde corre el intake, no el repositorio sobre el que se adopta.

**Medido, con un worktree linked enfocado:** la misma adopción **sin** `--cwd` devuelve
`{"error":{"code":"linked_worktree_source"}}` —el fallo que esta receta corrige— y con `--cwd` al
checkout principal adopta y devuelve su panel raíz. El contraejemplo no se escribe entero a
propósito: una invocación sin anclar, copiable, es la forma exacta del defecto.

> **`--cwd` nombra el checkout principal, y si no lo es falla cerrada.** Medido: apuntándolo a un
> worktree **linked** del mismo repositorio, `worktree open` devuelve `linked_worktree_source` igual
> que sin anclaje — no camina hasta el padre, a diferencia de `worktree list --cwd`, que sí lo hace.
> Los dos verbos resuelven la misma bandera distinto, así que el valor no se deriva de una consulta
> previa: se pasa el checkout principal. Si el `<repo_destino>` de la corrida fuera un worktree
> linked, la adopción **no adopta nada** y lo dice — la orden sale con código distinto de cero y el
> sobre de error viaja por **stderr**. Se lee el `error.code`, nunca el mensaje.

Las demás invocaciones —`agent start`, `pane split` y `workspace rename`— ya nombran su destino con
`--pane` o un id explícito, así que no hay nada más que anclar.

> **Panel libre o panel ocupado se lee sin escribir en él.** `herdr pane process-info --pane <id>`
> devuelve `foreground_processes[]`, y el discriminante es **cuál** es el proceso, no cuántos hay:
> el panel está libre cuando su único proceso en foreground es **su shell de login** —medido `zsh`,
> y `bash` donde ese sea el shell—. **La cantidad no sirve**, y conviene decirlo porque es la
> lectura que se cae sola: medido, un panel libre trae **uno** (`zsh`) y uno ocupado con un agente
> Codex trae **uno** también (`codex`). Un panel de Claude Code trae diez, pero eso es su pila de
> MCP en el mismo grupo de procesos, no una propiedad de estar ocupado — leerlo como umbral deja
> pasar por libre justamente al panel con otro agente, que es el caso que esta rama existe para
> cazar. Se prefiere a dejar que `agent start` agote su `--timeout`, que es el escalón caro **y con
> efecto colateral**: antes de rendirse escribe en el panel, así que si ahí corre un editor o una
> suite de tests el texto entra en ese proceso. Caveat medido: recién adoptado, el panel puede estar
> corriendo todavía su propio `rc` —apareció un `brew shellenv`—, que por identidad lee **ocupado** y
> es transitorio, así que se relee antes de darlo por tal.

> **`--no-focus` se conserva explícito, y no porque haya un robo de foco que impedir.** Medido:
> `worktree open` sin ninguna de las dos banderas devuelve el workspace con `focused: false` y deja
> el foco donde estaba. El esquema de la API declara `focus` con `default: false` y el `--help` del
> CLI no declara ninguno, así que el flag fija un default que la superficie del CLI no confiesa.

| Plataforma | Adoptar | Abrir y arrancar | Rotular | Observable que acredita |
|---|---|---|---|---|
| Herdr | `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` sobre el árbol ya existente — `open` adopta y devuelve el panel raíz en `.result.root_pane.pane_id`, mientras `create` crearía uno nuevo | Ramificar por `.result.root_pane` de esa misma respuesta —`already_open` es un booleano y no discrimina nada—: con `.agent` nulo y `.cwd` igual a `<ruta>`, arrancar ahí con `herdr agent start <nombre> --kind <familia> --pane <.pane_id>`; con `.agent` igual a la familia esperada y ese mismo `.cwd`, reutilizarlo; en todo otro caso —otra familia, `.cwd` distinto, o el panel ocupado —su único proceso en foreground no es su shell de login— según `herdr pane process-info --pane <.pane_id>`— abrir uno propio con `herdr pane split --pane <.pane_id> --direction right --cwd <ruta> --no-focus` y arrancar ahí | lo deja puesto `--label` en la misma adopción, **también cuando `already_open` viene verdadero** —medido: una re-apertura con `--label` distinto reescribe la etiqueta del workspace y `workspace list` la devuelve cambiada—; para cambiarlo después, `herdr workspace rename <.result.workspace.workspace_id> "<qué flujo corre acá>"` | `herdr agent get <nombre>` devuelve el mismo `pane_id`, la familia esperada, su `cwd` igual a la ruta del worktree, y un `agent_status` que la plataforma declara listo —`idle` o `done`—; ante cualquier otro resultado, incluido `blocked`, y ante discrepancias con el resultado de `agent start`, seguir «Esperar a que el agente esté listo» |
| Orca | nada que adoptar: el árbol lo creó su propio verbo y ya está registrado. Un árbol creado con Git **no** se puede adoptar acá, y por eso Orca no tiene rama de Git | lo arranca `--agent <familia>` **en la creación**, que es el único modo: `orca terminal list --worktree id:<repoId>::<ruta> --json` **observa** la terminal, no la inicia | `orca worktree set --worktree id:<repoId>::<ruta> --comment "<qué corre acá>" --json` | `orca terminal list --worktree id:<repoId>::<ruta> --json` devuelve una terminal con el agente de la familia esperada |

**La comprobación de familia y directorio no es opcional.** Un agente de la familia equivocada
responde razonablemente y no reconoce el prefijo; uno en el directorio equivocado trabaja sobre el
repositorio que no es. Las dos se leen del mismo observable, antes de despachar.

**Del mismo observable sale la identidad que el dossier lleva**, y es la de **este** panel —el del
flujo—, no la del panel del intake: en Herdr, el panel **donde quedó el agente** —el raíz que
`worktree open` devuelve en `.result.root_pane.pane_id`, o el que se abrió aparte si ese estaba
ocupado—, que es el `pane_id` que `agent get <nombre>` acredita; en Orca, el
`handle` de la terminal que `terminal list --worktree` devuelve para el worktree recién creado.
Anotarla acá es lo que permite escribirla en la sección 11 del dossier, que se redacta después.

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

### El hook de setup ya corrió, o no

**La autoridad del hook y su clasificación viven en «Clasificar el hook de setup»**, que corre antes
de crear y decide con qué primitiva se crea. Acá solo importa una consecuencia para la siembra: si el
hook clasificó `reproducible` o `inseparable` y **corrió**, puede haber copiado ya estos directorios
— es un patrón común. Si lo hizo:

- **No copiar encima.** El hook puede adaptar lo que copia al worktree; pisarlo revierte esa
  adaptación.
- Comprobar igual que el resultado está: un hook que **no corrió** —en Orca, por su
  `setupRunPolicy`— deja el worktree vacío, y la salida de la creación no lo dice.

Si el hook clasificó `ausente` y este repo va a repetir el flujo seguido, vale sugerirle al usuario
declararlo donde su plataforma lo aloje: en Orca, el `hookSettings.scripts.setup` del repo; en Herdr,
un script del propio árbol, que es el único lugar donde esta clasificación lo busca. En las dos es
configuración ajena al flujo, así que **se sugiere, no se hace**.

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
9. **Dónde se registran los incidentes** si alguna skill falla durante el flujo — con la ruta que
   el archivo de instrucciones del repo destino declare, que es su autoridad.
10. **El issue de origen**, si el incidente vino de uno: su número, su URL, y la instrucción de
    escribir `Closes #<n>` en el PR. Sin esto el flujo no tiene cómo saber a qué issue pertenece —
    arranca sin contexto de esta sesión— y el issue queda `en-curso` para siempre aunque el arreglo
    se haya mergeado. Con varios incidentes agrupados van **todos** los números, uno por línea:
    GitHub cierra tantos `Closes` como el PR declare.

11. **La plataforma anfitriona** — sobre cuál de las dos corre el panel donde este flujo vive, y si
    salió de la matriz o de un pedido del usuario. El flujo arranca **sin contexto de esta sesión**:
    la resolución del paso 6.1 es justamente contexto que no tiene, y sin ella vuelve a enfrentar la
    pregunta desde cero —incluido el caso de las **dos** identidades vivas, donde su propio detector
    no tiene observable que identifique al anfitrión—. Tres campos, y ninguno se deduce:

    | Campo | Valores | Qué dice |
    |---|---|---|
    | `plataforma` | `herdr` \| `orca` | la que el paso 6.1 resolvió, y sobre la que se creó el worktree y el panel |
    | `origen` | `resuelta` \| `pedida` | `resuelta`, la eligió la matriz sobre las identidades vivas; `pedida`, el usuario la dio en el parámetro `plataforma` |
    | `identidad` | el valor observado | la identidad del panel **de este flujo**, no la del panel del intake: son dos paneles distintos |

    > **Es un hecho observado, no un consentimiento de transporte.** `sdd-flow` persiste su elección
    > en el bloque `transporte` de su frontmatter, y esa elección se sella con el **texto exacto que
    > se le mostró al usuario** y su `digest`. Nada de eso puede producirlo el intake en nombre de
    > nadie. Lo que esta sección aporta es **de dónde arranca**, no qué eligió: el flujo sigue
    > debiendo su propio ofrecimiento y su propio sellado si va a despachar por plataforma. Un
    > `origen: pedida` es una **preferencia declarada del usuario**, que la oferta puede nombrar; no
    > es la respuesta a esa oferta.

### Lo que no va

- Un consentimiento de transporte pre-sellado, o un bloque `transporte` escrito por adelantado. El
  intake observa la plataforma; consentir la vía es del flujo, con el usuario delante.
- Recomendaciones sobre la decisión abierta. El flujo tiene que decidirla con criterio propio; una
  recomendación escrita acá se transcribe en vez de pensarse.
- Rutas del proyecto donde el incidente se observó. Al flujo no le sirven.
- Un plan de implementación. Eso lo produce `sdd-flow`, es su trabajo.

---

## Despachar el flujo

### Esperar a que el agente esté listo

| Plataforma | Comando | Observable |
|---|---|---|
| Herdr | `herdr agent get <nombre>` | `agent_status` que la plataforma declara listo: `idle` o `done` |
| Orca | `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 90000 --json` | el estado que devuelve |

`herdr agent get` es la autoridad.

Sus resultados se clasifican por **tres discriminantes en este orden —código de salida, parseo y
contenido—**, y cada fila es el caso que las anteriores no tomaron. No se clasifica por la
descripción del síntoma: un `agent get <nombre-inexistente>` sale **distinto de cero** y trae
`error.code: agent_not_found`, así que «no devuelve el agente» y «el comando falla» describen **el
mismo** resultado y no pueden ser dos filas.

| Código de salida | Salida | Identidad | `agent_status` | Resultado observable |
|---|---|---|---|---|
| `0` | parsea | la esperada | `idle` o `done` | **continuar**, cualquiera sea el código de salida de `agent start` |
| `0` | parsea | la esperada | `working` | **esperar y reconsultar** |
| `0` | parsea | la esperada | `blocked` | **detener y mostrar la aprobación o la pregunta abierta**: el agente responde, pero lo que reciba entra en esa UI y no en el compositor |
| `0` | parsea | la esperada | `unknown`, o un estado que esta tabla no enumera | **detener sin destruir**: la plataforma declara que `unknown` no prueba completitud, y un estado que no conocemos tampoco |
| `0` | parsea | **cualquier otra**: una **identidad distinta** —otro panel, otra familia u otro `cwd`—, o una respuesta que no trae el agente | — | **detener y mostrar lo que devolvió**; nunca esperar, porque esperar a que cambie una identidad equivocada no la corrige |
| `0` | no parsea | — | — | **detener sin destruir**: una salida que no se puede leer no prueba que el agente no esté |
| ≠ `0` | `error.code` es `agent_not_found` | — | — | **detener sin destruir**: el agente no está registrado con ese nombre, que no es lo mismo que no existir el panel |
| ≠ `0` | cualquier otro `error.code`, o ninguno legible | — | — | **detener sin destruir**: la consulta no se pudo hacer, así que no dice nada del agente |

**Quien declara el readiness es `agent_status`, no `interactive_ready`, y eso está medido.** La
plataforma define `idle` como listo para recibir input, `done` como **ese mismo estado** después de
un trabajo en background que nadie miró, `blocked` como una UI de aprobación o pregunta reconocida, y
`unknown` como presente pero sin clasificar, que **no prueba completitud**. Contra el runtime,
`interactive_ready` **no sigue esa semántica**: viene `true` en un agente `blocked` —que no puede
recibir el encargo, porque lo que llegue entra en su aprobación— y **no viene** en uno `done`, que sí
está listo. Clasificar por esa clave tomaba las dos decisiones al revés: despachaba dentro de una
pregunta abierta y rechazaba a un agente disponible.

**Y la ausencia no se resuelve esperando.** Medido con dos lecturas separadas del mismo agente
`done`: el estado y la ausencia de la clave se conservan, así que reconsultar no converge y el único
final posible era agotar el límite. Una espera que por construcción no puede terminar bien no es una
espera: es un rechazo con demora.

**Qué pasa entonces con `interactive_ready`: nada.** Deja de ser condición de acreditación, **no
aparece en la tabla y no tiene poder de veto**. La tabla es la única sede que clasifica, así que una
entrada tiene exactamente una salida y ninguna superficie que la consuma necesita recordar una guarda
aparte.

Hubo una versión intermedia que sí le daba veto —«si está presente y es falso mientras el estado
declara listo, no se continúa»—, y **se retiró por dos razones**. La primera es que contradecía a la
tabla: el mismo caso tenía dos resultados, continuar y detener, y el contrato no decía cuál manda. La
segunda es que esa guarda **no nacía de un caso observado**: se escribió por precaución, para no
tener que decidirlo si alguna vez aparecía. Darle poder de veto a un observable que esta misma
sección declara no autoritativo, sobre un caso que nadie vio, es exactamente lo que el escalón barato
evita. Si alguna vez se observa esa combinación, será un caso medido y entonces se decidirá con él
delante.

**La quinta fila es el complemento, y por eso la tabla es total.** Las cuatro primeras exigen la
identidad esperada y se reparten por `agent_status`; la quinta toma **toda identidad distinta** —incluida
una respuesta que no trae el agente—, así que ningún contenido con `exit 0` queda sin clasificar.
Enumerar solo los desvíos que uno se imagina es como se abren los huecos: el de la clave ausente
estuvo abierto una versión entera, y el de `blocked` sobrevivió a que la tabla ya fuera total en la
forma.

**El límite no es un resultado de `agent get`, y por eso no es una fila.** Es una transición del
estado de espera: reconsulta **la única fila que espera**, la de `working`, cada 2 s hasta 60 s. Al
agotarse, la acreditación **nunca se completó**, así que se **detiene sin destruir** y toda
liquidación posterior pasa por el gate humano.

**El invariante de orden nombra sus hitos, porque `acreditar` designa dos distintos:**

    arrancar el agente → acreditar identidad y readiness → primer tiempo
      → acreditar el reconocimiento → cuerpo

`acreditar identidad y readiness` es esta sección y se resuelve con la tabla de arriba.
`acreditar el reconocimiento` es el paso 2 del envío en tres tiempos —leer el compositor y buscar la
señal de esa familia— y ocurre **después** del primer tiempo, no antes. Llamar `acreditar` a los dos
ponía el segundo delante de su propio prerequisito.

Esta regla rige desde la siguiente activación, porque una sesión que ya cargó el archivo sigue con
lo que cargó.

Mandar antes de eso pierde el texto: el TUI todavía no tiene dónde recibirlo.

### El prompt es un puntero, no el encargo

**El prompt no transporta el encargo: lo apunta.** El dossier ya existe en disco antes de este
sub-paso —es el invariante de orden del paso 6— así que el prompt solo tiene que decir dónde está y
que se lea entero antes de nada.

```
<prefijo> corregí los incidentes del dossier <ruta absoluta>, leelo entero antes de nada: es la única copia
```

**Por qué apuntar y no transportar.** Un encargo largo entra al TUI como bloque pegado, y de ahí
salen dos fallos distintos: el prefijo queda dentro del bloque, y el cuerpo puede llegar incompleto.
Un puntero corto no los elimina —la relación entre largo y fallo es una hipótesis, no un hecho
medido— pero los **reduce**, y el control de abajo es obligatorio igual.

> **Lo que el prompt deja de llevar, el dossier tiene que tenerlo.** Antes viajaban en el prompt la
> causa raíz, la superficie, las decisiones abiertas, las restricciones del repositorio y el PR
> abierto si lo había. Todo eso va **al dossier**, y su plantilla lo exige. Un puntero a un dossier
> incompleto es peor que un encargo largo.

### Comprobar el dossier antes de enviar

Tres cosas, y las tres antes del primer tiempo: que **exista**, que sea **legible**, y que su
**digest** sea el que se calculó **al escribirlo**. El tercero es el que importa y el que se olvida:
el digest se liga a la **fuente** —los bytes que se escribieron— y no a lo que se mandó, porque un
digest calculado sobre lo enviado sella también lo que el envío haya roto.

### Enviar en tres tiempos

El corte no es texto/Enter: es **prefijo / cuerpo / Enter**, y entre el primero y el segundo hay una
comprobación que decide si se sigue.

1. **El prefijo solo**, en la forma que su familia exige.
2. **Leer el compositor** y buscar la señal de reconocimiento **de esa familia**. Sin la señal, no se
   manda el cuerpo: se aplica la fila de recuperación.
3. **El cuerpo**, y leerlo para comprobar que entró entero.
4. **El Enter**, sobre ese mismo compositor y sin nada tipeado en el medio.

### Qué se escribe y qué se busca, por familia

**La secuencia no es la misma, y la diferencia es un espacio.** Está medido: en una familia el espacio
final revela la señal, y en la otra la oculta. Un procedimiento que use la misma forma para las dos
falla en una — y falla mostrando el texto correcto sin la señal, que es indistinguible de un prefijo
no reconocido.

| Familia | Qué se escribe en el primer tiempo | Qué acredita el reconocimiento |
|---|---|---|
| `claude` | `/sdd-flow` **con** espacio final | el compositor muestra la **gramática de argumentos** de la skill a continuación del prefijo |
| `codex` | `$sdd-flow` **sin** espacio final | el compositor muestra la **entrada de la skill en el menú filtrado**, con su descripción. El espacio se manda con el cuerpo |

| Plataforma | Cómo se escribe sin enviar | Cómo se lee el compositor | Cómo se manda el Enter |
|---|---|---|---|
| Herdr | `herdr pane send-text <id> '<texto>'` | `herdr pane read <id> --source visible` | `herdr pane send-keys <id> enter` |
| Orca | `orca terminal send --terminal <handle> --text '<texto>' --json` | `orca terminal read --terminal <handle> --json` → campo `draft` | `orca terminal send --terminal <handle> --text "" --enter --json` |

**Sin comillas dobles ni apóstrofes** en el texto si va entre comillas simples del shell — más simple
que escapar.

### Confirmar el arranque — tres propiedades, y ninguna sustituye a la otra

El control viejo buscaba «la señal de que la skill cargó». Eso lo satisface también un agente que
**compensó** leyendo el archivo de la skill por su cuenta, así que no distingue un arranque bueno de
uno malo. Se parte en tres:

| Propiedad | Qué acredita | Qué **no** acredita | Cómo se comprueba |
|---|---|---|---|
| **procedencia** | que la invocación entró por el prefijo, reconocido por el host | nada sobre el contenido del encargo | la **cadena** del envío: el prefijo se reconoció en el tiempo 2, no se tipeó nada en el medio, y el Enter fue sobre ese compositor |
| **integridad** | que el flujo leyó el dossier que se le escribió | nada sobre **cómo** se invocó la skill ni sobre el cuerpo del prompt | el flujo despachado congela su pedido con el `sha256` de cada fuente: se comprueba que exista una entrada cuyo hash sea el del dossier **en su origen** |
| **completitud** | que el cuerpo del encargo entró entero en el compositor antes del Enter | nada sobre si el agente lo ejecutó ni sobre cómo se invocó la skill | la **primera** entrada `origen: usuario` del `literal.jsonl` que el flujo despachado congela —la de menor `n`— contiene el cuerpo canónico del puntero |

**Se exigen las tres.** El hash correcto con procedencia no acreditada **no** cierra el paso: un
arranque compensado también lee el dossier entero y produce exactamente el mismo hash. Ese mismo
agente puede compensar tras recibir un cuerpo truncado: con prefijo reconocido y dossier intacto,
procedencia e integridad dan verde; la completitud lo discrimina porque falta el puntero canónico entero.

La contención busca el cuerpo canónico del puntero que manda escribir la plantilla, **excluidos el
prefijo y el separador que lo activa**, dentro del campo `texto` decodificado de esa primera entrada.
La receta manda el separador dentro del prefijo en una familia y dentro del cuerpo en la otra, por lo
que incluirlo cambiaría el operando según la familia. Es contención y no igualdad porque no está
comprobado si el host captura el prefijo junto con el cuerpo; un truncamiento rompe la contención
igual.

Esta regla rige desde la siguiente activación: el despacho ya iniciado cierra con el contrato que
cargó, conserva el hueco y no se reacredita. La lectura posterior del literal es una auditoría sin
efecto sobre ese cierre: no lo revierte, no reabre el despacho ni cambia el estado del incidente, del
issue o del worktree; solo es posible mientras el literal exista.

> **El punto ciego de la procedencia, declarado.** La cadena se apoya en que nadie tipeó nada entre
> el tiempo 2 y el Enter, y **eso no es observable en ninguna plataforma soportada**: ni Herdr ni Orca
> exponen el input del usuario como algo consultable. La defensa es de proceso —no tipear en el panel
> mientras el despacho corre— y esta línea existe para que la ausencia esté declarada y no se
> descubra después.

**Sin observable de reconocimiento**, el arranque se declara **no confirmado**: el incidente **no se
retira** y el issue conserva su etiqueta del pool. Eso vale para la pérdida en runtime de un
observable que sí existe; que una combinación **nunca** lo tenga es otra cosa y la gobierna la matriz
de soporte.

### Marcar el worktree

| Plataforma | Comando |
|---|---|
| Herdr | `herdr workspace rename <workspace_id, el que la adopción devuelve en .result.workspace.workspace_id> "<qué flujo corre acá>"`, o `--label` en la propia adopción, que lo deja puesto sin una llamada más. No `pane rename`: rotula el panel, no la tarjeta |
| Orca | `orca worktree set --worktree id:<repoId>::<path> --comment "<qué flujo corre acá>" --json` |

Es lo que hace legible la tarjeta cuando hay varios worktrees abiertos.

### La matriz de soporte

Las cuatro combinaciones que esta skill promete, cada una con su camino completo. **Ninguna celda
remite a otra fila.**

| Plataforma × familia | Crear | Abrir y arrancar | Acreditar el arranque | Primer tiempo | Observable que acredita |
|---|---|---|---|---|---|
| Herdr × claude | `git -C <repo_destino> worktree add -b <rama> <ruta> <sha>`, y adoptar con `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` | Ramificar por `.result.root_pane` de esa misma respuesta —`already_open` es un booleano y no discrimina nada—: con `.agent` nulo y `.cwd` igual a `<ruta>`, arrancar ahí con `herdr agent start <nombre> --kind claude --pane <.pane_id>`; con `.agent` igual a la familia esperada y ese mismo `.cwd`, reutilizarlo; en todo otro caso —otra familia, `.cwd` distinto, o el panel ocupado —su único proceso en foreground no es su shell de login— según `herdr pane process-info --pane <.pane_id>`— abrir uno propio con `herdr pane split --pane <.pane_id> --direction right --cwd <ruta> --no-focus` y arrancar ahí | `herdr agent get <nombre>` devuelve el mismo `pane_id`, la familia esperada, el `cwd` del worktree, y `agent_status` `idle` o `done`; ante cualquier otro resultado, incluido `blocked`, seguir «Esperar a que el agente esté listo» | `/sdd-flow ` con espacio | gramática de argumentos en el compositor |
| Herdr × codex | `git -C <repo_destino> worktree add -b <rama> <ruta> <sha>`, y adoptar con `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` | Ramificar por `.result.root_pane` de esa misma respuesta —`already_open` es un booleano y no discrimina nada—: con `.agent` nulo y `.cwd` igual a `<ruta>`, arrancar ahí con `herdr agent start <nombre> --kind codex --pane <.pane_id>`; con `.agent` igual a la familia esperada y ese mismo `.cwd`, reutilizarlo; en todo otro caso —otra familia, `.cwd` distinto, o el panel ocupado —su único proceso en foreground no es su shell de login— según `herdr pane process-info --pane <.pane_id>`— abrir uno propio con `herdr pane split --pane <.pane_id> --direction right --cwd <ruta> --no-focus` y arrancar ahí | `herdr agent get <nombre>` devuelve el mismo `pane_id`, la familia esperada, el `cwd` del worktree, y `agent_status` `idle` o `done`; ante cualquier otro resultado, incluido `blocked`, seguir «Esperar a que el agente esté listo» | `$sdd-flow` sin espacio | la skill en el menú filtrado |
| Orca × claude | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup skip --agent claude --no-parent --json`; con hook `inseparable`, el mismo comando con `--setup run` | lo arranca `--agent claude` **en la creación**, que es el único modo: `orca terminal list --worktree id:<repoId>::<ruta> --json` **observa** la terminal, no la inicia | `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 90000 --json` devuelve su estado | `/sdd-flow ` con espacio | gramática de argumentos en el campo `draft` |
| Orca × codex | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup skip --agent codex --no-parent --json`; con hook `inseparable`, el mismo comando con `--setup run` | lo arranca `--agent codex` **en la creación**, que es el único modo: `orca terminal list --worktree id:<repoId>::<ruta> --json` **observa** la terminal, no la inicia | `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 90000 --json` devuelve su estado | `$sdd-flow` sin espacio | la skill en el menú filtrado, en `draft` |

> **Si una combinación deja de tener observable acreditable, la promesa se cambia con gate humano.**
> No se la declara soportada con el control apagado: una fila que siempre termina en «no confirmado»
> no es soporte, es un no-op con buena prosa.

## El volcado a issues

Sede del formato y de los comandos del modo `volcar`. El destino es el repositorio de las skills
—`repo_destino`—, no el proyecto donde se observó el defecto.

### Las etiquetas

Tres ejes, y ninguno se inventa por incidente:

| Eje | Valores | De dónde sale |
|---|---|---|
| skill | `skill:<nombre>` — una por cada skill que el incidente nombra | el campo `Skill` del registro; un incidente que nombra dos lleva las dos |
| severidad | `severidad:alta` \| `severidad:media` | el campo `Severidad`. **Si el registro no lo declara, el issue va sin esta etiqueta** |
| plataforma | `plataforma:macos` \| `plataforma:windows` \| `plataforma:linux` | el campo `Plataforma`. **Si el registro no lo declara, el issue va sin esta etiqueta** |
| transporte | `transporte:cli` \| `transporte:herdr` \| `transporte:orca` | el campo `Transporte`. **Si el registro no lo declara, el issue va sin esta etiqueta** |
| estado | `needs-triage` \| `en-curso` | nace `needs-triage`; pasa a `en-curso` cuando el intake lo despacha (paso 6.5) |

Crear la etiqueta que falte antes de publicar (`gh label create <nombre> --color <hex> --description
<texto>`); `gh issue create` falla si la etiqueta no existe.

### El formato del issue

**Título:** `[<skill>] <el titular del incidente, sin la fecha>`. El prefijo hace la lista legible y
agrupable; la fecha no va acá porque es ilegible en una lista y su lugar es el cuerpo.

**Cuerpo:** los campos del registro como líneas en negrita, después el incidente **verbatim**, y al
pie la procedencia.

```
**ID de registro:** `DD/MM/AAAA HH:MM`
**Skill:** `<skill>`
**Sección:** <la seccion o regla que el incidente cita>
**Conductor:** <herramienta → modelo>
**Worker:** <herramienta → modelo, o — con el motivo>
**Plataforma:** <macos|windows|linux, o "no declarada en el registro de origen">
**Transporte:** <cli|herdr|orca, o "no declarado en el registro de origen">
**Severidad:** <alta|media, o "no declarada en el registro de origen">
**Relacionado:** <`DD/MM/AAAA HH:MM` (#<n>) del antecedente; la fecha sola si no tiene
issue, con el motivo; o — si no hay>

---

<los bloques verbatim: Qué instruía · Qué pasó · Por qué es defecto de la
 skill · Consecuencia · Qué habría que cambiar>

---
<sub>Volcado desde el registro local `<ruta>`. **Sin verificar contra el árbol**: la
verificación es del paso `sdd-incident-intake`.</sub>
```

**La plataforma y el transporte no se deducen de la sesión que vuelca.** El volcado corre después
del incidente, y a menudo en otra máquina o por otra vía: publicar los de quien vuelca le atribuiría
al defecto un entorno que nunca tuvo. Salen del registro, igual que la severidad, y si no están se
publica su ausencia dicha. Son **dos ejes independientes** —`plataforma:windows` con
`transporte:orca` es una combinación real— así que ninguno se deriva del otro. Pagan su lugar porque
separan las dos clases de defecto que más se confunden al triar: el que solo aparece en un shell
—las variantes PowerShell contra POSIX— y el que solo aparece por una vía de transporte.

**La primera línea es el mecanismo de idempotencia**, no decoración. GitHub indexa el cuerpo, así que
la fecha y hora se busca; y es lo que permite que el campo `Relacionado` siga cruzando incidentes por
su ID después de que el archivo ya no exista.

### Los comandos

```bash
# 1. ya volcado? — busca el ID de registro entre abiertos Y cerrados
gh issue list --repo <owner/repo> --state all --search '"DD/MM/AAAA HH:MM"' \
  --json number --jq '.[].number'

# 2. publicar (el cuerpo va por archivo: el markdown con backticks rompe el quoting)
gh issue create --repo <owner/repo> --title "[<skill>] <titular>" \
  --body-file <ruta/al/cuerpo.md> \
  --label "skill:<nombre>" --label "severidad:<n>" --label "needs-triage" \
  --label "plataforma:<p>" --label "transporte:<t>"   # omitir la que el registro no declare

# 3. cotejar lo publicado contra el original, antes de retirar
gh issue view <n> --repo <owner/repo> --json body --jq .body > <ruta/al/publicado.md>
```

PowerShell usa los mismos comandos: `gh` no cambia de sintaxis entre shells, y el cuerpo viaja por
`--body-file` en las dos.

### Los issues relacionados

El registro tiene **tres** relaciones distintas y se confunden con facilidad, porque las tres se
dicen "está relacionado con". Cada una tiene su mecanismo:

| Relación | Qué significa | Cómo se expresa |
|---|---|---|
| **Reincidencia** (campo `Relacionado`) | el **mismo** defecto volvió a aparecer | mención `#<n>` en el cuerpo del issue nuevo |
| **Agrupamiento** (paso 3) | defectos **distintos** que se resuelven en el mismo diff | un flujo, y su PR declara un `Closes #<n>` por cada uno |
| **Redimensionado** (paso 2) | el issue describe **otro** defecto del que dice | issue nuevo que lo menciona; el viejo se cierra apuntando al nuevo |

> **Una reincidencia NO se cierra como duplicada.** Es el reflejo natural en GitHub y borra
> exactamente lo que la regla 2 del registro protege: la **frecuencia** es lo único que distingue una
> trampa estructural de la skill de un descuido puntual. Tres issues abiertos sobre el mismo defecto
> son el dato, no ruido a limpiar. Se cierran juntos cuando el arreglo llega —un PR puede declarar
> varios `Closes`—, nunca antes y nunca por parecidos.

**La mención hace el trabajo sola, y en las dos direcciones.** Escribir `#<n>` en el cuerpo del issue
nuevo agrega la referencia al timeline del viejo **sin editarlo**. Eso es la regla 2 del registro
—"una reincidencia se agrega, nunca se edita"— cumplida por el mecanismo y no por disciplina.

**Resolver la fecha a un número, al volcar.** El campo `Relacionado` cita una fecha y hora, que es el
ID del registro. Buscarla como cualquier ID (el comando de idempotencia) y escribir las dos cosas:
`` `27/08/2026 17:12` (#12) ``. La fecha se conserva porque es el ID canónico y sobrevive a que el
issue se borre; el número, porque es lo que GitHub enlaza.

**Publicar en orden cronológico ascendente** es lo que hace que el número exista cuando se lo
necesita: una reincidencia siempre cita a su antecedente, nunca al revés. Medido sobre el registro
vivo: de 18 incidentes con `Relacionado`, **cero** apuntan a un incidente posterior.

**Si el antecedente no tiene issue**, se deja la fecha sola y se dice por qué —"antecedente retirado
del registro antes del volcado"—. Pasa: en el mismo registro, 3 de esas 18 referencias apuntan a
incidentes que ya no están en el archivo. Inventar un número o silenciar la referencia son las dos
formas de perder el rastro.

### El cotejo, y por qué línea por línea

Antes de retirar, cada línea sustantiva del original tiene que aparecer en algún cuerpo publicado.
Se saltean las vacías, los separadores, las cabeceras de tabla y el encabezado `##` —que vive en el
título—; las filas de campos se cotejan por su **valor**, porque el formato las transformó.

Un muestreo no alcanza: lo que se pierde en un volcado no es un bloque entero sino un **campo**, y un
campo ausente se lee igual de bien que uno presente.

### Dos formas de leer un verde que no lo es

- **El campo que desaparece al parsear.** Extraer los campos con una clase de caracteres que no cubra
  los acentos minúsculos hace que `Sección` no matchee, y el campo se cae **sin error**. Medido: se
  perdió en los cuatro incidentes de un volcado y solo lo delató el conteo de campos, que dio seis
  donde debía dar siete. Contar los campos extraídos contra los esperados, y no confiar en que el
  parseo anduvo porque no tiró excepción.
- **El `gh` que corre fuera del repo.** Sin `--repo` y con el cwd fuera del árbol, `gh` falla con
  `not a git repository` y **escribe un archivo vacío**. Un `grep` posterior sobre ese archivo informa
  que el contenido falta, que es lo mismo que informaría si de verdad faltara. Pasar `--repo` siempre,
  y comprobar el tamaño de lo descargado antes de creerle a la comparación.

## Retirar del registro

El retiro toca **dos lugares**, y el orden entre ellos no importa; que estén los dos, sí.

**El índice** — una edición exacta sobre la fila. Anclar en el texto de la fila anterior y la
posterior para no borrar de más.

**El cuerpo** — la sección completa con su separador. Cuando los incidentes tomados son los
**últimos** del archivo, alcanza con cortar desde el separador que los precede; cuando están en el
medio, es una edición por sección.

**Ese corte no aplica cuando los incidentes tomados son todos**, y la diferencia no es un matiz: es
la fórmula opuesta. El separador que precede al primer incidente tomado pertenece al **par de
arriba** mientras quede alguno por encima, así que se va con la sección. Pero si no queda ninguno,
ese mismo separador es el **separador de cierre de la cabecera**, y descartarlo se la come en
silencio —cinco bytes, `\n---\n`, medidos— justo en el paso que promete no tocarla. La operación que
lo reemplaza es conservar el prefijo **hasta el final de ese separador, inclusive**.

Un corte por offset tiene que verificar sus supuestos antes de escribir, y ramificar por el caso:

```python
SEP = '\n---\n'
marca = SEP + '\n## ' + fecha       # `fecha` es el DD/MM/AAAA HH:MM del primer incidente tomado;
i = s.find(marca)                   # alcanza para anclar, porque la regla 1 la declara única
assert i != -1                      # la marca existe
assert s.count('## ' + fecha) == 1  # y es única
# el separador precedente se va con la sección mientras quede algún incidente por encima; si los
# tomados son TODOS, ese separador cierra la cabecera y se conserva
resto = s[:i + len(SEP)] if todos else s[:i]
```

`resto` es **lo que se escribe de vuelta al archivo**: el prefijo conservado reemplaza al contenido
anterior, y ahí termina el retiro sobre el cuerpo.

Sin el `assert` de unicidad, un título repetido corta en el lugar equivocado y el archivo queda
plausible. Y sin la ramificación, una de las dos ramas siempre sale mal: con `s[:i]` el caso de todos
pierde el cierre de la cabecera, y con `s[:i + len(SEP)]` el caso del último de varios deja un
separador huérfano al final.

### Comprobar residuos

```
grep -n '<fecha y hora>' <registro>
grep -n '<término distintivo del título>' <registro>
```

Los dos, no uno: la fecha caza la sección, el término caza la fila del índice si la edición falló.
**La salida vacía en ambos no acredita el retiro por sí sola.** Hacen falta tres condiciones juntas:
que **el archivo existe**, que **conserva su cabecera**, y que no quedó **ningún incidente retirado**
—que es lo que los dos `grep` miran—. La salida vacía sola
**no las distingue de un archivo que no existe**: sobre un registro borrado `grep` imprime lo mismo
que sobre uno limpio, y lo único que los
separa es el código de salida, 2 contra 1. Comprobar la existencia y la cabecera antes de leer esas
salidas es lo que impide que un borrado entero se acredite como un retiro prolijo. Y contar líneas
antes y después para reportarlo.

### Lo que nunca se toca

- La cabecera de reglas.
- Los incidentes que no se tomaron — **ni siquiera para "arreglarlos de paso"**. La regla 2 del
  registro dice que una reincidencia se agrega y nunca se edita; editar un incidente ajeno borra la
  frecuencia, que es lo único que distingue una trampa estructural de un descuido puntual.
- El orden cronológico de los que quedan.

---

## El contrato de fallo por fase

Cada efecto de este paso puede fallar **después** de haber dejado algo en pie. Sin una regla por
fase, el intento siguiente duplica recursos o abandona una corrida viva. Una fila por efecto:

| Fase | Observable previo | Qué queda ligado a la corrida | Si falla | Registro e issue | Residuales | Reintento |
|---|---|---|---|---|---|---|
| resolver plataforma | — | nada | se detiene | intactos | ninguno | inmediato |
| clasificar el hook | plataforma resuelta | nada | se detiene | intactos | ninguno | inmediato |
| crear el worktree | identidad revalidada | el árbol, si alcanzó a crearse | se detiene | intactos | **el árbol no se elimina**: su ciclo de vida es el del flujo, no el de este paso. Se enumera | el intento siguiente **adopta** el árbol existente si su rama y su commit coinciden; si no, para y lo muestra |
| ejecutar el hook | árbol creado | el árbol, ya creado | se detiene | intactos | el árbol, y lo que el hook haya escrito | no se re-ejecuta el hook sobre un árbol a medias: se descarta el árbol **con confirmación** y se recrea |
| sembrar | árbol creado | el árbol y lo sembrado | se detiene | intactos | lo copiado | se completa la siembra sobre el mismo árbol |
| escribir el dossier | árbol sembrado | el árbol, la siembra y el dossier parcial | se detiene | intactos | el dossier a medias | se reescribe entero: es la única copia y no se parchea |
| adoptar y abrir | identidad revalidada | el panel, si se abrió | se detiene | intactos | el panel | se cierra el panel con su modo de cierre y se reabre |
| arrancar el agente | panel abierto | el panel y el agente | el resultado se decide en «Esperar a que el agente esté listo», no por el código de salida | intactos | panel y agente | no liquida ni reintenta por su cuenta; sigue con la acreditación |
| acreditar identidad y readiness | panel abierto y arranque intentado | el panel siempre; el agente solo si `get` lo devolvió | **no confirmado** — se detiene sin liquidar | intactos; el incidente **no se retira** | el panel queda en pie; el agente se enumera solo si se acreditó que existe | solo la fila que reconsulta de «Esperar a que el agente esté listo» lo hace dentro del límite; las demás siguen su salida propia; agotado el límite, decisión del usuario. Rige el invariante de orden de esa sede |
| acreditar el arranque del flujo | reconocimiento acreditado | todo lo anterior | **no confirmado** | el incidente **no se retira**; el issue conserva su etiqueta del pool | el árbol y el panel quedan en pie, enumerados | decisión del usuario: reintentar el envío o abandonar la corrida |
| marcar el issue | arranque acreditado | la escritura externa | se detiene | el issue puede haber quedado a medias: se comprueba y se repara | ninguno | se repite la escritura, que es idempotente |
| retirar del registro | issue marcado | la edición del registro | se detiene | **se completa el retiro**: dejarlo a medias es el defecto que su propia fila describe | ninguno | se completa, no se revierte |

**Ninguna limpieza destructiva ocurre sin su gate.** Descartar un árbol, cerrar un panel con trabajo
sin cosechar o revertir una escritura externa se le pregunta al usuario; nada de eso se infiere de un
fallo.

**El registro de incidentes nunca se vacía como parte de una reversión.** Es la única copia de lo que
se iba a corregir, y un fallo de este paso no es motivo para perderla.

## Cuando algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `agent start` devuelve `agent_not_ready` con el agente vivo y listo | **Hipótesis no comprobada:** el CLI puede reportar el error aunque el agente haya quedado disponible | Consultar las cuatro condiciones de «Esperar a que el agente esté listo» y continuar si acreditan; cualquier limpieza pasa por el gate del contrato de fallo por fase |
| El compositor no muestra la señal de reconocimiento | El prefijo entró dentro del texto pegado, o se usó la forma de la otra familia —con espacio donde iba sin él, o al revés— | Limpiar el compositor, restablecer readiness y **repetir desde el prefijo**, acreditando su reconocimiento antes de mandar el cuerpo. Si no se acredita, el arranque queda **no confirmado** y no se retira nada. La ruta de la skill sirve para **diagnosticar** cuál está instalada, nunca como forma de activarla: pedirle al agente que la lea produce exactamente el arranque compensado que el control existe para rechazar |
| El flujo pregunta cosas que el config ya responde | El worktree no está sembrado | Sembrar `.specify/` del `<repo_destino>` y avisarle al agente que relea el config |
| El flujo arranca un `init` que nadie pidió | Igual que arriba, caso agudo | Igual, y verificar que el `init` no haya sobrescrito nada |
| `git status` del worktree muestra lo sembrado | El destino no ignora esos paths | Sacarlos del árbol y resolver el ignore antes de seguir |
| El diff del flujo sale contra un árbol raro | El worktree nació en la referencia remota por defecto | Solo puede pasar en la rama `inseparable`, que es la única que conserva la creación de la plataforma; con creación por Git el commit va explícito y el caso no existe. Ya avanzado, es rebase — y el techo de proporción del repo, si lo tiene, se midió contra el commit equivocado |
| El registro quedó sin la fila pero con la sección | El retiro tocó un solo lugar | Completar el retiro y **registrar el incidente**: es un defecto de procedimiento |
| El flujo abre un diff sobre líneas que ya no existen | El paso 4 no corrió, o corrió sin `fetch` | Rehacer el paso 4 y re-emitir el veredicto contra `origin/<default>`. Si el defecto ya no está, el flujo se cierra y el incidente se reporta como resuelto aguas arriba |
| El PR del flujo entra en conflicto con otro PR abierto | El cruce del paso 4 se hizo por título y no por archivos | Cruzar `gh pr diff --name-only` contra la superficie. Con el conflicto ya abierto, el orden de merge lo decide el usuario |
| El worktree perdió commits que estaban en `origin` | El realineo se hizo sin comprobar la dirección, en la rama `inseparable` | `reset --hard origin/<default>` y rehacer 6.2. Es un defecto de procedimiento: se registra |
| El flujo arrancó pero el hash del dossier no coincide | El encargo se leyó de otro archivo, o el dossier cambió después de calcular su digest | Arranque **no confirmado**: no se retira nada. Recalcular el digest del dossier en su origen y comparar; si difiere del que se envió, el dossier se reescribió a mitad del despacho |
| La plataforma resolvió `headless` | Ninguna identidad viva, o las dos vivas sin observable que distinga al anfitrión | **No es un modo degradado: es parada.** El despacho no ocurre, el registro queda intacto y se reintenta cuando haya plataforma. Un override no lo arregla: también se comprueba |

Todo fallo atribuible a una skill SDD —esta incluida— se registra según la regla del archivo de
instrucciones del `<repo_destino>`, que declara su sede. Esta skill no la fija ni la supone: la
lee de ahí.
