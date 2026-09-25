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
Los efectos son estos seis y la lista es
exhaustiva: **crear** el worktree por la plataforma, **adoptar** un árbol creado con Git, **abrir** el
panel, **arrancar** el agente, **rotular** el worktree y **entregar** el encargo. Si la
revalidación falla, ese efecto no se ejecuta y se aplica la fila que le corresponda en «El contrato
de fallo por fase».

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
- `.plans/` — **no**, salvo retoma y la vía separada de **un solo archivo** cuando las instrucciones
  raíz del destino declaran el registro de incidentes en cada worktree. En una retoma se copia **la
  carpeta de ese plan y solo esa**; la excepción de registro no abre el resto de `.plans/`.
- `node_modules/`, `__pycache__/`, `.idea/` — **no**. Si el flujo necesita dependencias, se instalan
  en el worktree; una caché copiada puede traer rutas absolutas del árbol viejo adentro.

Ante un candidato que no encaja en ninguna fila: preguntarle al usuario. Es más barato que sembrar de
más.

### Copiar y comprobar

**Por archivo, no por directorio, y creando los intermedios.** El directorio destino puede existir ya
—medio versionado— y entonces copiar la unidad entera la anida adentro en vez de fusionarla:

Este bucle **solo** procesa `.specify/` y `.claude/`: no añadir `.plans/` al filtro. El registro
declarado se prepara después por su ruta única en «Preparar el registro declarado del worktree»;
sus comprobaciones no se sustituyen por las tres de este bucle.

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

### Preparar el registro declarado del worktree

**Cargar solo tras la declaración local concordante de 6.2.** El insumo es la tupla `(sede,
ruta relativa)` extraída de las instrucciones raíz de `repo_destino` y del worktree, no una ruta
literal de esta skill. La vía prepara **un archivo** fuera del bucle general; nunca copia el resto
de `.plans/`. Antes de crear nada, rechazar ruta vacía, absoluta, con `..` o sin destino único.
Resolver la raíz física del worktree y la ruta completa con `Path.resolve(strict=False)`, que
resuelve los enlaces de los componentes existentes aun si falta el archivo final, y exigir que
`relative_to(raíz_física)` tenga éxito y no sea `.`. Hacer la misma comparación por componentes
para la fuente normal bajo la raíz física de `repo_destino`; un prefijo textual (`startswith`) no
prueba confinamiento. Repetir el control justo antes de publicar. En Windows, una ruta con unidad
no es relativa aunque no tenga barra inicial. Si cambia la tupla o un enlace escapa, detenerse;
no corregir las instrucciones del destino ni escribir fuera del árbol.

Aplicar el mismo chequeo a `(worktree, ruta)` y a `(repo_destino, ruta)` para la fuente normal.
Cada ejecución imprime la ruta física; código distinto de cero detiene. La fuente alternativa se
compara con la **ruta física aprobada**, no se fuerza bajo `repo_destino`:

| POSIX | PowerShell |
|---|---|
| `python3 -c 'from pathlib import Path; import sys; root=Path(sys.argv[1]).resolve(strict=True); rel=Path(sys.argv[2]); sys.exit("ruta no relativa") if (rel.is_absolute() or rel.drive or not rel.parts or ".." in rel.parts) else None; target=(root/rel).resolve(strict=False); target.relative_to(root); sys.exit("ruta raíz") if target==root else None; print(target)' "$raiz" "$ruta"` | `py -3 -c 'from pathlib import Path; import sys; root=Path(sys.argv[1]).resolve(strict=True); rel=Path(sys.argv[2]); sys.exit(''ruta no relativa'') if (rel.is_absolute() or rel.drive or not rel.parts or ''..'' in rel.parts) else None; target=(root/rel).resolve(strict=False); target.relative_to(root); sys.exit(''ruta raíz'') if target==root else None; print(target)' $raiz $ruta` |

Asignar la salida **física y absoluta** del chequeo con `raiz=worktree` a `destino`, no asignarle
la ruta relativa. POSIX: `destino=$(python3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' "$worktree" "$ruta")`;
PowerShell: `$destino = py -3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' $worktree $ruta`.
Si la salida del chequeo físico anterior, o cualquiera de sus repeticiones antes y después de
publicar, difiere de `destino`, detenerse. Así `mkdir`, la creación exclusiva y el cotejo de bytes
usan el mismo archivo del worktree, no un relativo al directorio desde el que corre el intake.
Para la fuente normal, asignar a `fuente` la ruta física del chequeo con `raiz=repo_destino`:
POSIX `fuente=$(python3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' "$repo_destino" "$ruta")`;
PowerShell `$fuente = py -3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' $repo_destino $ruta`.
Exigir que coincida con la salida del chequeo y que el archivo exista. Para una fuente alternativa,
`fuente` es exactamente la ruta física concreta aprobada, no una ruta relativa inferida.

**Primero, lo que ya existe.** Contar como existente también un enlace roto (`lexists`), no solo
`Path.exists()`. Si el hook o el árbol dejó un archivo antes del primer intento de siembra, exigir
evidencia de esa procedencia; la mera existencia, el ignore o un dossier anterior no la prueban.
Al adoptar un árbol de otra sesión, o al reintentar tras una siembra acreditada cuyo dossier o
despacho falló, una procedencia no acreditada es `detenido` hasta decisión humana. Nunca borrar ni
reclasificar un residual automáticamente. Un registro preexistente válido puede estar poblado:
no se vacía, no se sobrescribe y no exige fuente. Un archivo versionado limpio o ignorado puede
servir; uno versionado modificado o no trackeado y no ignorado detiene.

Crear un scratch privado **fuera del worktree** antes de inspeccionar el previo o tomar la fuente.
Todos sus archivos se escriben por creación exclusiva, no con un editor ni con `Out-File` de
PowerShell 5.1. Definir `ref` como el `reference.md` de **esta copia instalada** de la skill. La
función extrae siempre la única unidad marcada abajo; `registro_candidato` / `Invoke-RegistroCandidato`
no son scripts nuevos ni una autorización para copiar todo `.plans/`.

POSIX:

```sh
if scratch=$(python3 -c 'import tempfile; print(tempfile.mkdtemp(prefix="registro-intake-"))') && [ -n "$scratch" ]; then
  instantanea="$scratch/fuente"; inventario="$scratch/inventario"
  mapa="$scratch/mapa"; candidato="$scratch/candidato"; previo="$scratch/previo"
  registro_candidato() {
    python3 -c 'import sys; from pathlib import Path; s=Path(sys.argv[1]).read_text(encoding="utf-8"); s=s.split("\n<!-- registro-candidato:inicio -->\n",1)[1].split("\n<!-- registro-candidato:fin -->",1)[0].split("```python\n",1)[1].rsplit("\n```",1)[0]; sys.argv=sys.argv[1:]; exec(compile(s,sys.argv[0],"exec"))' "$ref" "$@"
  }
else
  printf '%s\n' 'No se pudo crear el scratch privado' >&2
  false
fi
```

PowerShell:

```powershell
$scratch = py -3 -c 'import tempfile; print(tempfile.mkdtemp(prefix=''registro-intake-''))'
if ($LASTEXITCODE -ne 0 -or -not $scratch) { throw 'No se pudo crear el scratch privado' }
$instantanea = Join-Path $scratch 'fuente'; $inventario = Join-Path $scratch 'inventario'
$mapa = Join-Path $scratch 'mapa'; $candidato = Join-Path $scratch 'candidato'
$previo = Join-Path $scratch 'previo'
function Invoke-RegistroCandidato {
  param([string[]]$Argumentos)
  py -3 -c 'import sys; from pathlib import Path; s=Path(sys.argv[1]).read_text(encoding=''utf-8''); s=s.split(''\n<!-- registro-candidato:inicio -->\n'',1)[1].split(''\n<!-- registro-candidato:fin -->'',1)[0].split(''```python\n'',1)[1].rsplit(''\n```'',1)[0]; sys.argv=sys.argv[1:]; exec(compile(s,sys.argv[0],''exec''))' $ref @Argumentos
  if ($LASTEXITCODE -ne 0) { throw 'Registro candidato: comando fallido' }
}
```

Si la preparación del scratch devuelve un código distinto de cero, detener la vuelta; no reutilizar
variables ni rutas de un scratch anterior.

Cuando `destino` ya existe y su procedencia está acreditada, copiarlo **sin sobrescribir** a
`previo` y ejecutar `inspeccionar-previo`. Entregarle un argumento citado por cada ID del grupo a
despachar, no solo el primero. En POSIX, cargarlos primero en parámetros posicionales
con `set --`, uno citado por ID; el bloque siguiente los transmite con `"$@"`. POSIX:

```sh
python3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open("xb"); f.write(Path(sys.argv[1]).read_bytes()); f.close()' "$destino" "$previo" &&
  registro_candidato inspeccionar-previo "$previo" "$worktree" "$@"
```

PowerShell:

```powershell
py -3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open(''xb''); f.write(Path(sys.argv[1]).read_bytes()); f.close()' $destino $previo
if ($LASTEXITCODE -ne 0) { throw 'Registro previo: copia fallida' }
Invoke-RegistroCandidato -Argumentos (@('inspeccionar-previo', $previo, $worktree) + $ids_del_grupo)
```

Leer JSON, stderr y código. `count` cuenta H2 exteriores posteriores al cierre; `ids` conserva
el ID completo —fecha **y hora** local si corresponde—; `row_ids` procede solo de la primera
celda del Índice, sin buscar en `Síntoma`. El mismo ID una vez en cada conjunto es normal;
repetido **dentro** de cualquiera de ellos detiene. `targets_present` no vacío da código distinto
de cero y bloquea **todo el grupo**. Un vacío útil exige terminar exactamente en `\n---\n`;
un previo poblado no necesita separador al final de su última sección. Si es utilizable,
conservar sus bytes y su estado Git observados, borrar `scratch/previo` solo tras acreditar
`preexistente` y entregar ruta, `count`, `ids`, `row_ids` y estado Git. En cualquier fallo,
conservar `scratch/previo` y enumerarlo entre residuales; no exigir ni abrir fuente de siembra.

**Solo si falta, elegir fuente y preparar candidato.** La fuente normal es la misma ruta declarada
en `repo_destino`, resuelta físicamente dentro de esa raíz; puede coincidir con el registro de
entrada sin quedar descalificada. Si falta o su cabecera no tiene límites inequívocos, conservar el
worktree y detener el lote. No tomar automáticamente otro registro ni reconstruir reglas.
Reanudar solo cuando el usuario apruebe **un archivo y su ruta física concreta** para este
repositorio y esta ruta de registro; una salida física fuera de `repo_destino` debe estar incluida
en esa aprobación. La aprobación no viaja a otro repositorio/ruta y no congela los bytes: cada
vuelta toma otra instantánea con inventario y mapa nuevos.

Copiar la fuente a `instantanea` por creación exclusiva; no volver a leer la fuente durante esa
vuelta. POSIX:

```sh
python3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open("xb"); f.write(Path(sys.argv[1]).read_bytes()); f.close()' "$fuente" "$instantanea" &&
  registro_candidato inventariar "$instantanea" "$inventario" "$worktree"
```

PowerShell:

```powershell
py -3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open(''xb''); f.write(Path(sys.argv[1]).read_bytes()); f.close()' $fuente $instantanea
if ($LASTEXITCODE -ne 0) { throw 'Registro candidato: copia de fuente fallida' }
Invoke-RegistroCandidato -Argumentos @('inventariar', $instantanea, $inventario, $worktree)
```

**Inventario → mapa declarado → constructor → cotejo.** Leer el inventario entero: SHA-256,
tamaño, número y offsets de cada línea, todos los H2 exteriores con texto y patrón, filas,
separadores y cercas. Contrastar el contenido de cada tramo de `instantanea` y **declarar
manualmente** una lista ordenada de argumentos
`<primera-línea>:<línea-fin-exclusiva>:<clase>`; para una nota, añadir
`:nota-explicita` solo después de inspeccionar su cuerpo. Clases: `titulo`, `reglas`, `indice`,
`fila_indice`, `nota`, `cierre`, `incidente`, `blancos_finales`. No inferir notas por etiqueta ni
usar la primera fecha como límite de cabecera. `mapear` convierte líneas a bytes y copia digest,
tamaño y H2 del inventario; **no decide las clases**. Sus argumentos son los tramos declarados
por el conductor. No lo invocar con una lista vacía. En POSIX, cargar antes los tramos
en parámetros posicionales con `set --`, uno citado por tramo; `"$@"` los pasa a `mapear`
sin depender de arrays de shell.

**Fronteras canónicas para declarar `tramos` (líneas 1-based, fin exclusivo).** La lista debe
cubrir todos los bytes en orden, sin huecos ni solapamientos; fusionar tramos contiguos de la
misma clase, excepto dos notas o dos incidentes distintos. El constructor coteja esa partición
exacta, no solo la suma de bytes:

- `titulo`: desde el primer H1 hasta antes de `## Reglas de este archivo`. `reglas`: desde ese H2
  hasta antes de `## Índice`, interrumpida únicamente por notas previas al Índice; el `---` exterior
  inmediatamente anterior al Índice pertenece a `reglas`.
- `indice`: su H2, cabecera y delimitadora de la tabla; también los blancos fuera de las filas
  hasta una nota o el cierre. Todas las filas de datos contiguas forman **un** tramo
  `fila_indice`; sin filas, no se declara ese tramo.
- `nota`: empieza solo en `## Nota histórica` o `## Nota: <texto no vacío>` y llega hasta el
  siguiente ATX exterior, el separador anterior al Índice o el blanco reservado al cierre,
  lo primero; incluye sus otros blancos finales y lleva `:nota-explicita`. Una nota nueva inicia
  otro tramo, aunque sea contigua.
- `cierre`: **la línea en blanco inmediata anterior** al primer `---` exterior posterior al
  Índice **y** esa línea `---`. Los blancos anteriores siguen en `indice` o `nota`.
- `incidente`: tras el cierre, el primer tramo empieza en la línea siguiente al `---`, incluyendo
  blancos/separadores previos a su H2; cada H2 de incidente exterior inicia un tramo nuevo con
  sus propios blancos/separadores previos. Cada tramo contiene exactamente un H2 de incidente.
  `blancos_finales` contiene solo blancos tras el último incidente, o tras el cierre si no hay
  incidentes.

Así, en la secuencia `\n---\n\n## Incidente …`, el blanco **anterior** a `---` pertenece a
`cierre` y el **posterior** al primer `incidente`, no a `indice` ni a `cierre` respectivamente.
Leer los offsets y las líneas del inventario antes de declarar cada frontera; un `Mapa inválido`
identifica el primer tramo esperado/recibido, pero no sustituye esa lectura.

POSIX:

```sh
registro_candidato mapear "$inventario" "$mapa" "$worktree" "$@" &&
  registro_candidato construir "$instantanea" "$mapa" "$candidato" "$worktree" &&
registro_candidato cotejar "$instantanea" "$mapa" "$candidato" "$worktree"
```

PowerShell:

```powershell
Invoke-RegistroCandidato -Argumentos (@('mapear', $inventario, $mapa, $worktree) + $tramos)
Invoke-RegistroCandidato -Argumentos @('construir', $instantanea, $mapa, $candidato, $worktree)
Invoke-RegistroCandidato -Argumentos @('cotejar', $instantanea, $mapa, $candidato, $worktree)
```

**La unidad siguiente implementa los cinco modos; no se edita en una corrida.** `inventariar`
rechaza CRLF, UTF-8 inválido, cercas ambiguas o sin cierre y límites no legibles. `mapear`
lee solo el inventario, valida sintaxis/límites de línea y copia su digest, tamaño y patrones;
`construir` vuelve a leer la instantánea y comprueba que el mapa pertenezca a ella,
recalcula H2, valida el mapa completo contra la partición canónica y escribe el candidato por
creación exclusiva **solo** si título, reglas, Índice, filas, notas, cierre e incidentes están
clasificados sin huecos ni solapamientos. Una fuente con `## Incidente INC-1` antes del cierre,
H2 desconocido, nota fuera de zona, setext/cerca ambigua o contenido sustantivo tras el cierre
se detiene; una fuente aprobada no salta esa gramática. No exige biyección entre filas y secciones.
`cotejar` relee candidato y fuente **sin las etiquetas del mapa**, impone una lista positiva de
estructura, comprueba ausencia de filas y secciones heredadas, preservación byte a byte y cierre
exacto `\n---\n`. Una salida `0` de `construir` por sí sola no acredita siembra.

<!-- registro-candidato:inicio -->
```python
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import sys

FIELDS = ("Skill", "Síntoma", "Evidencia mínima", "Relacionado", "Conductor", "Worker", "Plataforma", "Transporte", "Resolución")
KEEP = {"titulo", "reglas", "indice", "nota", "cierre"}
KINDS = KEEP | {"fila_indice", "incidente", "blancos_finales"}
LOCAL = re.compile(r"^## (\d{2}/\d{2}/\d{4} \d{2}:\d{2})(?:[ \t].*)?$", re.S)
ISO = re.compile(r"^## (\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?)(?:[ \t].*)?$", re.S)
NUMERIC = re.compile(r"^## ([0-9]+)(?:[ .:–-].*)?$", re.S)
NAMED = re.compile(r"^## Incidente ([A-Za-z0-9][A-Za-z0-9_-]*)(?:[ \t].*)?$", re.S)
FIELD = re.compile(r"^\s*(?:(?:>\s*)|(?:[-*+]\s*)|(?:\d+[.)]\s*))*-\s*\*\*(?:" + "|".join(re.escape(x) for x in FIELDS) + r"): ?\*\*", re.U)
ATX = re.compile(r"^(#{1,6})[ \t]+(.+)$")
TABLE_DELIMITER = re.compile(r"\|(?: *:?-{3,}:? *\|)+")


def fail(message):
    raise SystemExit(message)


def digest(data):
    return sha256(data).hexdigest()


def private(path, root):
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError:
        return
    fail("El temporal debe estar fuera del worktree: " + str(path))


def read_source(path):
    data = path.read_bytes()
    if not data.endswith(b"\n") or b"\r" in data:
        fail("Fuente sin nueva línea final o con CRLF")
    try:
        lines = data.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        fail("Fuente no es UTF-8 estricto")
    if not lines or any(not line.endswith("\n") for line in lines):
        fail("Fuente con líneas no terminadas en LF")
    starts = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line.encode("utf-8"))
    return data, lines, starts + [offset]


def incident_id(heading):
    for pattern, label in ((LOCAL, "fecha-local"), (ISO, "iso")):
        match = pattern.fullmatch(heading)
        if match:
            return label, match.group(1)
    if re.match(r"^## [0-9]{4}-[0-9]{2}-[0-9]{2}", heading):
        return None, None
    for pattern, label in ((NUMERIC, "numerico"), (NAMED, "incidente-id")):
        match = pattern.fullmatch(heading)
        if match:
            return label, match.group(1)
    return None, None


def heading_kind(line):
    if line == "## Reglas de este archivo\n":
        return "reglas"
    if line == "## Índice\n":
        return "indice"
    if line == "## Nota histórica\n":
        return "nota-historica"
    if re.fullmatch(r"## Nota: [^\n]+\n", line):
        return "nota-titulada"
    return incident_id(line[:-1])[0] or "no-clasificado"


def scan(lines, starts):
    headings = []
    atx = []
    fences = set()
    separators = []
    fence_spans = []
    fence = None
    previous_outside = ""
    for n, line in enumerate(lines):
        body = line[:-1]
        fence_like = re.match(r"^[ \t]*(`{3,}|~{3,})", body)
        if fence is not None:
            fences.add(n)
            if fence_like and fence_like.group(1)[0] == fence[0]:
                marker = fence_like.group(1)
                if body == fence and marker == fence:
                    fence_spans[-1]["line_end"] = n + 2
                    fence = None
                    previous_outside = ""
                else:
                    fail("Cerca ambigua en línea " + str(n + 1))
            continue
        if fence_like:
            marker = fence_like.group(1)
            if body.startswith((" ", "\t")) or len(marker) != 3:
                fail("Cerca ambigua en línea " + str(n + 1))
            if marker.startswith("`") and "`" in body[3:]:
                fail("Info string ambigua en línea " + str(n + 1))
            fence = marker
            fences.add(n)
            fence_spans.append({"line_start": n + 1, "line_end": None, "marker": marker})
            previous_outside = body
            continue
        if re.fullmatch(r"[ \t]*[-=]+[ \t]*", body) and (body != "---" or previous_outside.strip()):
            fail("Separador o setext ambiguo en línea " + str(n + 1))
        if body == "---":
            separators.append(n)
        if re.match(r"^[ \t]+#{1,6}[ \t]+", body):
            fail("Encabezado con sangría en línea " + str(n + 1))
        match = ATX.fullmatch(body)
        if match:
            atx.append((n, len(match.group(1)), match.group(2)))
            if len(match.group(1)) == 2:
                headings.append({"line": n + 1, "start": starts[n], "pattern": heading_kind(line)})
        previous_outside = body
    if fence is not None:
        fail("Cerca sin cierre")
    return headings, atx, fences, separators, fence_spans


def forbidden_preserved(line):
    if FIELD.match(line[:-1]):
        return True
    # Detecta encabezados de incidente ocultos por citas o listas sin confundir H3 numerados con IDs.
    visible = re.sub(r"^[ \t]*(?:(?:>\s*)|(?:[-*+]\s*)|(?:\d+[.)]\s*))*", "", line[:-1])
    match = re.match(r"^#{2,6}[ \t]+(.+)$", visible)
    if match:
        text = match.group(1)
        if re.match(r"(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|Incidente\s+[A-Za-z0-9])", text):
            return True
        if visible != line[:-1]:
            return True
    return False


def classify(lines, starts):
    headings, atx, fences, separators, _ = scan(lines, starts)
    h1 = [n for n, level, _ in atx if level == 1]
    rules = [h["line"] - 1 for h in headings if h["pattern"] == "reglas"]
    indexes = [h["line"] - 1 for h in headings if h["pattern"] == "indice"]
    if h1 != [0] or len(rules) != 1 or len(indexes) != 1 or not (0 < rules[0] < indexes[0]):
        fail("Título, reglas o Índice ausentes, repetidos o fuera de orden")
    r, idx = rules[0], indexes[0]
    before = [n for n in separators if r < n < idx]
    if len(before) != 1 or any(lines[n].strip() for n in range(before[0] + 1, idx)):
        fail("Separador previo al Índice ausente o ambiguo")
    presep = before[0]
    after = [n for n in separators if n > idx]
    if not after:
        fail("Separador de cierre ausente")
    closing = after[0]
    if lines[closing - 1] != "\n":
        fail("Cierre sin línea en blanco inmediata")
    close_start = closing - 1
    if any(h["pattern"] == "no-clasificado" for h in headings):
        fail("H2 exterior no clasificable")
    if any(h["pattern"] in ("nota-historica", "nota-titulada") and (h["line"] - 1 < r or h["line"] - 1 >= closing) for h in headings):
        fail("Nota fuera de cabecera")
    incidents = []
    notes = []
    for h in headings:
        n = h["line"] - 1
        kind = h["pattern"]
        if kind in ("fecha-local", "iso", "numerico", "incidente-id"):
            if n <= closing:
                fail("Incidente antes del cierre: línea " + str(n + 1))
            incidents.append(n)
        elif kind in ("nota-historica", "nota-titulada"):
            notes.append(n)
    for n, level, _ in atx:
        if n < r and level != 1:
            fail("Encabezado fuera de zona permitida")
        if idx < n < closing and level != 2:
            fail("ATX entre Índice y cierre")
    table = idx + 1
    while table < closing and not lines[table].strip():
        table += 1
    if table + 1 >= closing or not (lines[table].startswith("|") and lines[table].rstrip("\n").endswith("|")):
        fail("Encabezado del Índice ausente")
    if not TABLE_DELIMITER.fullmatch(lines[table + 1][:-1]):
        fail("Delimitadora del Índice ausente")
    row_start = table + 2
    row_end = row_start
    while row_end < close_start and lines[row_end].startswith("|"):
        if not lines[row_end][:-1].endswith("|"):
            fail("Fila de Índice incompleta")
        row_end += 1
    if any(lines[n].lstrip().startswith("|") for n in range(row_end, closing) if n not in fences):
        fail("Fila o segunda tabla fuera del Índice")
    kinds = ["titulo"] * len(lines)
    for n in range(r, idx): kinds[n] = "reglas"
    for n in range(idx, close_start): kinds[n] = "indice"
    for n in range(row_start, row_end): kinds[n] = "fila_indice"
    for n in range(close_start, closing + 1): kinds[n] = "cierre"
    for n in notes:
        boundary = presep if n < idx else close_start
        next_head = min((x for x, _, _ in atx if x > n and x < boundary), default=boundary)
        for j in range(n, next_head):
            if j not in fences and lines[j].startswith("|"):
                fail("Nota contiene fila")
            kinds[j] = "nota"
    for n in range(0, closing + 1):
        if n in fences:
            continue
        if kinds[n] in KEEP and forbidden_preserved(lines[n]):
            fail("Historial oculto en cabecera: línea " + str(n + 1))
    for n in range(row_end, close_start):
        if kinds[n] == "indice" and lines[n].strip():
            fail("Texto no clasificable tras tabla")
    # Cada incidente empieza en su H2; antes solo hay blancos o separadores.
    if incidents:
        if any(lines[n].strip() and lines[n] != "---\n" for n in range(closing + 1, incidents[0])):
            fail("Contenido antes del primer incidente")
        starts_inc = []
        for pos, h in enumerate(incidents):
            lower = closing + 1 if pos == 0 else incidents[pos - 1] + 1
            start = h
            while start > lower and (not lines[start - 1].strip() or lines[start - 1] == "---\n"):
                start -= 1
            starts_inc.append(start)
        last = len(lines)
        while last > incidents[-1] + 1 and not lines[last - 1].strip():
            last -= 1
        for pos, start in enumerate(starts_inc):
            end = starts_inc[pos + 1] if pos + 1 < len(starts_inc) else last
            for n in range(start, end): kinds[n] = "incidente"
        for n in range(last, len(lines)): kinds[n] = "blancos_finales"
    else:
        if any(line.strip() for line in lines[closing + 1:]):
            fail("Contenido sustantivo después del cierre")
        for n in range(closing + 1, len(lines)): kinds[n] = "blancos_finales"
    ranges = []
    n = 0
    while n < len(lines):
        kind = kinds[n]
        end = n + 1
        if kind == "incidente":
            end = next((x for x in starts_inc if x > n), last)
        elif kind == "nota":
            while end < len(lines) and kinds[end] == "nota" and end not in notes: end += 1
        else:
            while end < len(lines) and kinds[end] == kind: end += 1
        item = {"kind": kind, "start": starts[n], "end": starts[end]}
        if kind == "nota": item["basis"] = "nota-explicita"
        ranges.append(item)
        n = end
    return ranges, headings, incidents, row_start, row_end, closing


def checked_map(path, data, starts, headings, canonical):
    mapping = json.loads(path.read_text(encoding="utf-8"))
    if mapping.get("schema_version") != "registro-rangos/1" or mapping.get("snapshot_sha256") != digest(data) or mapping.get("size") != len(data):
        fail("Mapa inválido: otra instantánea")
    ranges = mapping.get("ranges")
    if not isinstance(ranges, list) or not ranges:
        fail("Mapa inválido: sin tramos")
    cursor = 0
    for item in ranges:
        if not isinstance(item, dict) or set(item) != ({"kind", "start", "end", "basis"} if item.get("kind") == "nota" else {"kind", "start", "end"}) or item.get("kind") not in KINDS or not all(type(item.get(k)) is int for k in ("start", "end")) or (item.get("kind") == "nota" and item.get("basis") != "nota-explicita"):
            fail("Mapa inválido: tramo mal formado")
        a, b = item["start"], item["end"]
        if a != cursor or b <= a or b not in starts:
            fail("Mapa inválido: hueco, solapamiento o límite fuera de línea")
        cursor = b
    if cursor != len(data): fail("Mapa inválido: incompleto")
    if mapping.get("headings") != headings:
        fail("Mapa inválido: H2 inventariados no coinciden")
    if ranges != canonical:
        for index, (actual, expected) in enumerate(zip(ranges, canonical)):
            if actual != expected:
                fail("Mapa inválido: tramo " + str(index + 1) + " esperado " + repr(expected) + ", recibido " + repr(actual))
        fail("Mapa inválido: cantidad de tramos esperada " + str(len(canonical)) + ", recibida " + str(len(ranges)))
    return mapping


def positive_candidate(candidate, source_lines):
    # Un segundo recorrido lee bytes sin llamar al clasificador del mapa o del constructor.
    data, lines, _ = read_source(candidate)
    table_delimiter = re.compile(r"\|(?: *:?-{3,}:? *\|)+")
    incident_patterns = (
        re.compile(r"^## \d{2}/\d{2}/\d{4} \d{2}:\d{2}(?:[ \t].*)?$"),
        re.compile(r"^## \d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?(?:[ \t].*)?$"),
        re.compile(r"^## [0-9]+(?:[ .:–-].*)?$"),
        re.compile(r"^## Incidente [A-Za-z0-9][A-Za-z0-9_-]*(?:[ \t].*)?$"),
    )

    def exterior(seq):
        h2, atx, fenced, separators = [], [], set(), []
        marker = None
        previous = ""
        for n, line in enumerate(seq):
            body = line[:-1]
            fence_line = re.match(r"^[ \t]*(`{3,}|~{3,})", body)
            if marker:
                fenced.add(n)
                if fence_line and fence_line.group(1)[0] == marker[0]:
                    if body != marker or fence_line.group(1) != marker:
                        fail("Cotejo positivo: cerca ambigua")
                    marker = None
                    previous = ""
                continue
            if fence_line:
                opening = fence_line.group(1)
                if body.startswith((" ", "\t")) or len(opening) != 3 or (opening[0] == "`" and "`" in body[3:]):
                    fail("Cotejo positivo: cerca ambigua")
                marker = opening
                fenced.add(n)
                previous = ""
                continue
            if re.fullmatch(r"[ \t]*[-=]+[ \t]*", body) and (body != "---" or previous.strip()):
                fail("Cotejo positivo: separador o setext ambiguo")
            if body == "---": separators.append(n)
            if re.match(r"^[ \t]+#{1,6}[ \t]+", body):
                fail("Cotejo positivo: encabezado sangrado")
            found = re.fullmatch(r"(#{1,6})[ \t]+(.+)", body)
            if found:
                atx.append((n, len(found.group(1)), found.group(2)))
                if len(found.group(1)) == 2: h2.append((n, line))
            previous = body
        if marker: fail("Cotejo positivo: cerca sin cierre")
        return h2, atx, fenced, separators

    h2, atx, fences, separators = exterior(lines)
    if not data.endswith(b"\n---\n"):
        fail("Cotejo positivo: cierre no exacto")
    if not lines[0].startswith("# ") or [(n, level) for n, level, _ in atx if level == 1] != [(0, 1)]:
        fail("Cotejo positivo: título inválido")
    rules = [n for n, line in h2 if line == "## Reglas de este archivo\n"]
    indexes = [n for n, line in h2 if line == "## Índice\n"]
    if len(rules) != 1 or len(indexes) != 1 or not (0 < rules[0] < indexes[0]):
        fail("Cotejo positivo: anclas inválidas")
    r, idx = rules[0], indexes[0]
    pre = [n for n in separators if r < n < idx]
    post = [n for n in separators if n > idx]
    if len(pre) != 1 or post != [len(lines) - 1] or lines[-2] != "\n":
        fail("Cotejo positivo: separadores inválidos")
    if any(lines[n].strip() for n in range(pre[0] + 1, idx)):
        fail("Cotejo positivo: contenido entre separador e Índice")
    def note(line):
        return line == "## Nota histórica\n" or bool(re.fullmatch(r"## Nota: [^\n]+\n", line))
    notes = [n for n, line in h2 if note(line)]
    if any(n not in (r, idx) and n not in notes for n, _ in h2):
        fail("Cotejo positivo: H2 no permitido")
    if any(n < r for n in notes):
        fail("Cotejo positivo: nota fuera de zona")
    table = idx + 1
    while table < len(lines)-2 and not lines[table].strip(): table += 1
    if (table + 1 >= len(lines)-2 or not lines[table].startswith("|")
            or not lines[table][:-1].endswith("|")
            or not table_delimiter.fullmatch(lines[table+1][:-1])):
        fail("Cotejo positivo: Índice inválido")
    if any(lines[n].lstrip().startswith("|") for n in range(table + 2, len(lines)) if n not in fences):
        fail("Cotejo positivo: fila heredada")
    field = re.compile(r"^\s*(?:(?:>\s*)|(?:[-*+]\s*)|(?:\d+[.)]\s*))*-\s*\*\*(?:" + "|".join(re.escape(x) for x in FIELDS) + r"): ?\*\*")
    for n, line in enumerate(lines):
        if table+2 <= n < len(lines)-2 and line.strip():
            inside_note = any(start <= n < min((x for x, _, _ in atx if x > start), default=len(lines)-2) for start in notes)
            if not inside_note: fail("Cotejo positivo: texto tras tabla")
        if n in fences: continue
        if field.match(line[:-1]):
            fail("Cotejo positivo: campo de incidente en línea " + str(n+1))
        visible = re.sub(r"^[ \t]*(?:(?:>\s*)|(?:[-*+]\s*)|(?:\d+[.)]\s*))*", "", line[:-1])
        heading = re.match(r"^#{2,6}[ \t]+(.+)$", visible)
        if heading and (re.match(r"(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|Incidente\s+[A-Za-z0-9])", heading.group(1)) or visible != line[:-1]):
            fail("Cotejo positivo: encabezado de historial en línea " + str(n+1))
    # Reconstruye solo las dos eliminaciones autorizadas con un recorrido de fuente sin etiquetas.
    source_h2, _, source_fences, source_seps = exterior(source_lines)
    source_rules = [n for n, line in source_h2 if line == "## Reglas de este archivo\n"]
    source_indexes = [n for n, line in source_h2 if line == "## Índice\n"]
    if len(source_rules) != 1 or len(source_indexes) != 1:
        fail("Cotejo positivo: anclas de fuente inválidas")
    source_idx = source_indexes[0]
    source_closings = [n for n in source_seps if n > source_idx]
    if not source_closings or source_lines[source_closings[0]-1] != "\n":
        fail("Cotejo positivo: cierre de fuente inválido")
    source_close = source_closings[0]
    source_notes = [n for n, line in source_h2 if note(line)]
    if any(n < source_rules[0] or n >= source_close for n in source_notes):
        fail("Cotejo positivo: nota de fuente fuera de cabecera")
    if len(source_notes) != len(notes):
        fail("Cotejo positivo: nota perdida")
    for n, line in source_h2:
        if n < source_close and n not in (source_rules[0], source_idx) + tuple(source_notes):
            fail("Cotejo positivo: H2 no clasificable en fuente")
        if n > source_close:
            date_shaped = re.match(r"^## [0-9]{4}-[0-9]{2}-[0-9]{2}", line[:-1])
            if ((date_shaped and not incident_patterns[1].fullmatch(line[:-1]))
                    or not any(pattern.fullmatch(line[:-1]) for pattern in incident_patterns)):
                fail("Cotejo positivo: sección posterior desconocida")
    source_table = source_idx + 1
    while source_table < source_close and not source_lines[source_table].strip(): source_table += 1
    if (source_table + 1 >= source_close or not source_lines[source_table].startswith("|")
            or not source_lines[source_table][:-1].endswith("|")
            or not table_delimiter.fullmatch(source_lines[source_table+1][:-1])):
        fail("Cotejo positivo: tabla de fuente inválida")
    source_row_start = source_table + 2
    source_row_end = source_row_start
    while source_row_end < source_close and source_lines[source_row_end].startswith("|"):
        if not source_lines[source_row_end][:-1].endswith("|"):
            fail("Cotejo positivo: fila de fuente incompleta")
        source_row_end += 1
    if any(source_lines[n].lstrip().startswith("|") for n in range(source_row_end, source_close) if n not in source_fences):
        fail("Cotejo positivo: tabla de fuente discontinua")
    expected_from_source = "".join(source_lines[:source_row_start] + source_lines[source_row_end:source_close+1]).encode("utf-8")
    if data != expected_from_source:
        fail("Cotejo positivo: bytes de cabecera, Índice o notas alterados")
    return data


def run():
    if len(sys.argv) < 3: fail("Uso: modo <rutas/argumentos>")
    mode = sys.argv[1]
    if mode == "inventariar" and len(sys.argv) == 5:
        snapshot, inventory, worktree = map(Path, sys.argv[2:5])
        root = worktree.resolve(strict=True)
        for p in (snapshot, inventory): private(p, root)
        data, lines, starts = read_source(snapshot)
        headings, _, fences, separators, fence_spans = scan(lines, starts)
        payload = {
            "schema_version": "registro-inventario/1",
            "snapshot_sha256": digest(data),
            "size": len(data),
            "lines": [{"number": n + 1, "start": starts[n], "end": starts[n + 1]} for n in range(len(lines))],
            "headings": [{**h, "text": lines[h["line"] - 1][3:-1]} for h in headings],
            "rows": [{"line": n + 1, "start": starts[n], "end": starts[n + 1], "text": line[:-1]}
                     for n, line in enumerate(lines) if n not in fences and line.lstrip().startswith("|")],
            "separators": [{"line": n + 1, "start": starts[n], "end": starts[n + 1]} for n in separators],
            "fences": fence_spans,
        }
        with inventory.open("xb") as f: f.write((json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        print(json.dumps({"snapshot_sha256": digest(data), "size": len(data), "line_count": len(lines), "headings": payload["headings"], "rows": len(payload["rows"]), "separators": len(separators), "fences": len(fence_spans)}, ensure_ascii=False))
    elif mode == "mapear" and len(sys.argv) >= 6:
        inventory, map_path, worktree = map(Path, sys.argv[2:5])
        root = worktree.resolve(strict=True)
        for p in (inventory, map_path): private(p, root)
        inv = json.loads(inventory.read_text(encoding="utf-8"))
        entries = inv.get("lines")
        size = inv.get("size")
        if (inv.get("schema_version") != "registro-inventario/1" or
                not re.fullmatch(r"[0-9a-f]{64}", str(inv.get("snapshot_sha256"))) or
                type(size) is not int or size < 1 or not isinstance(entries, list) or not entries or
                any(not isinstance(inv.get(key), list) for key in ("headings", "rows", "separators", "fences"))):
            fail("Inventario inválido")
        previous_end = 0
        for number, entry in enumerate(entries, 1):
            if (not isinstance(entry, dict) or set(entry) != {"number", "start", "end"} or
                    entry.get("number") != number or type(entry.get("start")) is not int or
                    type(entry.get("end")) is not int or entry["start"] != previous_end or
                    entry["end"] <= entry["start"] or entry["end"] > size):
                fail("Inventario con líneas inválidas")
            previous_end = entry["end"]
        if previous_end != size:
            fail("Inventario incompleto")
        headings = inv["headings"]
        if any(not isinstance(h, dict) or set(h) != {"line", "start", "text", "pattern"} or
               type(h["line"]) is not int or h["line"] < 1 or h["line"] > len(entries) or
               h["start"] != entries[h["line"] - 1]["start"] or not isinstance(h["text"], str) or
               h["pattern"] not in ("reglas", "indice", "nota-historica", "nota-titulada", "fecha-local", "iso", "incidente-id", "numerico", "no-clasificado")
               for h in headings):
            fail("Inventario con H2 inválidos")
        starts = [entry["start"] for entry in entries] + [size]
        ranges = []
        for arg in sys.argv[5:]:
            parts = arg.split(":")
            if (not arg.isascii() or len(parts) not in (3, 4) or
                    not all(re.fullmatch(r"[0-9]+", x) for x in parts[:2]) or parts[2] not in KINDS):
                fail("Argumento de tramo inválido: " + arg)
            a, b = map(int, parts[:2])
            kind = parts[2]
            if a < 1 or b > len(starts) or b <= a: fail("Límites de tramo inválidos")
            item = {"start": starts[a - 1], "end": starts[b - 1], "kind": kind}
            if kind == "nota":
                if len(parts) != 4 or parts[3] != "nota-explicita": fail("Nota sin fundamento explícito")
                item["basis"] = parts[3]
            elif len(parts) != 3: fail("Fundamento en tramo no nota")
            ranges.append(item)
        map_headings = [{"start": h["start"], "line": h["line"], "pattern": h["pattern"]} for h in headings]
        payload = {"schema_version": "registro-rangos/1", "snapshot_sha256": inv["snapshot_sha256"], "size": size, "headings": map_headings, "ranges": ranges}
        checked_map_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        with map_path.open("xb") as f: f.write(checked_map_payload.encode("utf-8"))
        print(json.dumps({"map_sha256": digest(checked_map_payload.encode("utf-8")), "ranges": len(ranges)}, ensure_ascii=False))
    elif mode in ("construir", "cotejar") and len(sys.argv) == 6:
        snapshot, map_path, candidate, worktree = map(Path, sys.argv[2:6])
        root = worktree.resolve(strict=True)
        for p in (snapshot, map_path, candidate): private(p, root)
        data, lines, starts = read_source(snapshot)
        if mode == "construir":
            canonical, headings, incidents, row_start, row_end, _ = classify(lines, starts)
            mapping = checked_map(map_path, data, starts, headings, canonical)
            output = b"".join(data[item["start"]:item["end"]] for item in mapping["ranges"] if item["kind"] in KEEP)
            with candidate.open("xb") as f: f.write(output)
            print(json.dumps({"snapshot_sha256": digest(data), "map_sha256": digest(map_path.read_bytes()), "candidate_sha256": digest(output), "copied_at": datetime.fromtimestamp(snapshot.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"), "removed_index_rows": row_end-row_start, "removed_incidents": len(incidents)}, ensure_ascii=False))
        else:
            # Inspecciona primero el candidato: un mapa autoconsistente pero inválido no puede acreditarlo.
            output = positive_candidate(candidate, lines)
            mapping = json.loads(map_path.read_text(encoding="utf-8"))
            if mapping.get("schema_version") != "registro-rangos/1" or mapping.get("snapshot_sha256") != digest(data) or mapping.get("size") != len(data):
                fail("Cotejo: mapa de otra instantánea")
            spans = mapping.get("ranges")
            if not isinstance(spans, list) or not spans:
                fail("Cotejo: mapa sin tramos")
            cursor = 0
            selected = []
            for item in spans:
                if not isinstance(item, dict) or item.get("kind") not in KINDS or type(item.get("start")) is not int or type(item.get("end")) is not int:
                    fail("Cotejo: tramo mal formado")
                a, b = item["start"], item["end"]
                if a != cursor or b <= a or b not in starts:
                    fail("Cotejo: mapa con hueco, solapamiento o límite inválido")
                if item["kind"] in KEEP:
                    selected.append(data[a:b])
                cursor = b
            if cursor != len(data): fail("Cotejo: mapa incompleto")
            if output != b"".join(selected): fail("Cotejo: bytes conservados no coinciden")
            print(json.dumps({"snapshot_sha256": digest(data), "map_sha256": digest(map_path.read_bytes()), "candidate_sha256": digest(output), "copied_at": datetime.fromtimestamp(snapshot.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"), "accredited": True}, ensure_ascii=False))
    elif mode == "inspeccionar-previo" and len(sys.argv) >= 5:
        snapshot, worktree = map(Path, sys.argv[2:4])
        root = worktree.resolve(strict=True)
        private(snapshot, root)
        data, lines, starts = read_source(snapshot)
        _, _, incidents, row_start, row_end, closing = classify(lines, starts)
        ids = []
        for n in incidents:
            _, value = incident_id(lines[n][:-1])
            ids.append(value)
        row_ids = []
        for n in range(row_start, row_end):
            cell = lines[n].split("|", 2)[1].strip()
            if cell.startswith("`") and cell.endswith("`") and len(cell) > 1: cell = cell[1:-1]
            if not cell: fail("ID vacío en Índice")
            row_ids.append(cell)
        if len(ids) != len(set(ids)) or len(row_ids) != len(set(row_ids)):
            fail("ID repetido dentro del Índice o las secciones")
        if not incidents and not row_ids and data != data[:starts[closing+1]]:
            fail("Registro vacío con contenido tras cierre")
        targets = set(sys.argv[4:]) & (set(ids) | set(row_ids))
        print(json.dumps({"count": len(incidents), "ids": ids, "row_ids": row_ids, "targets_present": sorted(targets), "snapshot_sha256": digest(data), "empty": not incidents and not row_ids}, ensure_ascii=False))
        if targets: fail("ID objetivo ya presente en registro previo")
    else:
        fail("Uso: inventariar|mapear|construir|cotejar|inspeccionar-previo")


if __name__ == "__main__":
    run()
```
<!-- registro-candidato:fin -->
**Acreditar antes de 6.3.** Leer completos los JSON, stderr y códigos de las cuatro llamadas.
Exigir digests de instantánea, mapa y candidato de **esta** vuelta, además de `accredited: true`
en `cotejar`; comprobar los mismos bytes físicos que se publicarán. Si `mapear` falla o
`construir` informa `Mapa inválido`, mostrar el diagnóstico y, cuando la salida lo incluya,
el primer tramo esperado/recibido; conservar scratch/inventario/mapa;
solicitar decisión humana para abandonar o preparar **otra** instantánea, inventario y mapa, no
pedir una fuente nueva como remedio automático ni entrar en bucle. Ante cualquier otra estructura
no clasificable o cotejo rojo, detener sin publicar y enumerar temporales. Nunca llamar
`preexistente` a un candidato residual de este intento.

Con salida verde, comprobar **antes** de publicar que la ruta ausente está ignorada y que su
resolución física sigue confinada. POSIX `git -C "$worktree" check-ignore -q -- "$ruta"`;
PowerShell `git -C $worktree check-ignore -q -- $ruta`. Código distinto de cero detiene sin escribir.
Capturar el estado Git previo — POSIX `git -C "$worktree" status --porcelain --untracked-files=all`;
PowerShell `git -C $worktree status --porcelain --untracked-files=all`.

Crear únicamente los directorios intermedios de esa ruta tras comprobar su confinamiento:
POSIX `mkdir -p "$(dirname "$destino")"`; PowerShell
`New-Item -ItemType Directory -Force -Path (Split-Path $destino -Parent) | Out-Null`.
Repetir el chequeo físico **después de crear los directorios y antes de publicar**.

Publicar el candidato **solo por creación exclusiva**. La ruta puede haber aparecido entre la
inspección y este punto: `xb` falla sin sobrescribirla. En esa colisión volver a inspeccionarla
como en el primer apartado; solo avanzar si su procedencia y utilidad se acreditan.

| POSIX | PowerShell |
|---|---|
| `python3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open("xb"); f.write(Path(sys.argv[1]).read_bytes()); f.close()' "$candidato" "$destino"` | `py -3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open(''xb''); f.write(Path(sys.argv[1]).read_bytes()); f.close()' $candidato $destino` |

Repetir el chequeo físico **después de publicar**. Comprobar ubicación exacta e igualdad de bytes
con el candidato: POSIX `cmp -s "$candidato" "$destino"`; PowerShell
`py -3 -c 'from pathlib import Path; import sys; sys.exit(0 if Path(sys.argv[1]).read_bytes()==Path(sys.argv[2]).read_bytes() else 1)' $candidato $destino`.
Comparar el estado Git posterior con el capturado antes y exigir que no se hayan sumado cambios
versionables. Si falla cualquier comprobación posterior, conservar el archivo publicado y los
temporales como residuales; **no** convertirlo en preexistente al reintentar. Solo tras acreditar,
entregar `sembrado` con ruta, fuente normal o aprobada, ruta física aprobada si la hubo, `copied_at`,
`snapshot_sha256`, `map_sha256`, `candidate_sha256`, los bytes UTF-8 completos de `scratch/mapa`
y conteos retirados. **No borrar `scratch/mapa` aún**: 6.3 lo inserta byte a byte en la sección 9
del dossier y verifica su digest antes de limpiar scratch. Si 6.3 falla, scratch sigue siendo
residual enumerado, junto al árbol, registro y dossier parcial.

**Contrato de parada.** Cada fallo conserva origen, issue y resto del lote sin despachar ni
retirar. Fuente ausente o estructura inadmisible → mostrar árbol y pedir archivo/ruta física
aprobados; instrucciones ambiguas o divergentes → decisión humana y nueva extracción de ambas
tuplas; previo inválido o ID duplicado → decisión sobre ese archivo sin vaciarlo; mapa inválido →
mostrar el diagnóstico y el primer tramo esperado/recibido si está disponible, conservar scratch
y pedir decisión humana sobre abandono o nueva vuelta; ruta no ignorada, cotejo o publicación
fallidos → árbol, temporales y archivo
publicado, si existe, hasta decisión. Para procedencia incierta o residual de siembra, el usuario
elige explícitamente inspeccionarlo y aceptarlo como `preexistente` con estado y cantidad observados,
autorizar su retiro y nueva siembra en el mismo árbol, o abandonar. Ninguna salida borra un residual
ni restablece `sembrado` por inferencia.

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
9. **Dónde se registran los incidentes** si alguna skill falla durante el flujo — consumir el
   resultado acreditado de 6.2, no inferirlo de que exista un archivo. Con `sembrado`, declarar
   ruta del registro, archivo fuente y fecha de lectura/copia; si la fuente fue aprobada tras una
   parada, identificar también su ruta física aprobada. Declarar **en toda siembra**, incluso si
   no se detectó una nota concreta, que cualquier anotación ya presente en la cabecera copiada
   pertenece a la historia de la fuente y no a esta siembra. No añadir una anotación nueva dentro
   del registro sembrado. Con `preexistente`, declarar ruta, estado Git y cantidad de incidentes
   conservados. Con `otra-sede`, conservar la sede y ruta que el destino declaró; con
   `sin-declaración`, decir que no declaró ninguna, sin inventar ruta. `Detenido` no produce dossier
   ni despacho: su motivo y residuales van al cierre de la corrida detenida.
   En `sembrado`, consignar además `snapshot_sha256`, `candidate_sha256` y `map_sha256`.
   Dar a esta sección un H2 que empiece exactamente por `## 9. ` (por ejemplo,
   `## 9. Dónde se registran los incidentes`). Escribir el digest del mapa como una única
   línea literal `map_sha256: <64 caracteres hexadecimales minúsculos>`, sin lista, tabla,
   comillas ni cerca; el cotejo siguiente lee esa forma concreta, no Markdown libre.
   Insertar **los bytes UTF-8 completos** de `scratch/mapa`, incluida su única nueva línea
   final, dentro de una cerca `json` de tres backticks situada entre las líneas únicas
   `<!-- registro-mapa:inicio -->` y `<!-- registro-mapa:fin -->` de esta sección. No
   reserializar, normalizar ni añadir contenido al registro sembrado. Antes de borrar scratch,
   verificar que el bloque literal coincide con el archivo y con el digest declarado. Aislar la
   sección 9 por su H2 y el H2 siguiente **exteriores a cercas**; marcadores citados fuera de ella
   no cuentan, y dos pares dentro de ella detienen. `dossier` es la ruta física del dossier ya
   escrito; `mapa` es `scratch/mapa`. Tras escribir el dossier y antes de borrar scratch,
   ejecutar la sección «Verificar el mapa de la sección 9» más abajo; sus comandos imprimen el SHA
   solo con código `0`.

   Si escribir o verificar el dossier falla, conservar scratch y enumerar árbol, registro,
   mapa y dossier parcial como residuales; no limpiar ni despachar. Solo después del código `0`
   de este cotejo puede limpiarse el scratch privado. En `preexistente`, `otra-sede` y
   `sin-declaración` no se inventa un mapa ni un digest.
10. **El issue de origen**, si el incidente vino de uno: su número, su URL, y la instrucción de
    escribir `Closes #<n>` en el PR. Sin esto el flujo no tiene cómo saber a qué issue pertenece —
    arranca sin contexto de esta sesión— y el issue queda `en-curso` para siempre aunque el arreglo
    se haya mergeado. Con varios incidentes agrupados van **todos** los números, uno por línea:
    GitHub cierra tantos `Closes` como el PR declare.

11. **La plataforma anfitriona** — sobre cuál de las dos corre el panel donde este flujo vive, y si
    salió de la matriz o de un pedido del usuario. El flujo arranca **sin contexto de esta sesión**,
    y la resolución del paso 6.1 no queda escrita en ningún otro lado. Tres campos, y ninguno se
    deduce:

    | Campo | Valores | Qué dice |
    |---|---|---|
    | `plataforma` | `herdr` \| `orca` | la que el paso 6.1 resolvió, y sobre la que se creó el worktree y el panel |
    | `origen` | `resuelta` \| `pedida` | `resuelta`, la eligió la matriz sobre las identidades vivas; `pedida`, el usuario la dio en el parámetro `plataforma` |
    | `identidad` | el valor observado | la identidad del panel **de este flujo**, no la del panel del intake: son dos paneles distintos |

    > **Es un hecho observado, y queda escrito.** Lo que esta sección aporta es **de dónde arranca**
    > el flujo. `sdd-flow` no la consume para despachar: sus workers van por CLI, sea cual sea la
    > plataforma.

### Verificar el mapa de la sección 9

Con `dossier` y `mapa` definidos como en el ítem 9, ejecutar uno de estos comandos solo después
de escribir el dossier de una siembra y antes de borrar `scratch/mapa`.

**POSIX:**

```sh
python3 -c 'from hashlib import sha256
from pathlib import Path
import re
import sys

document = Path(sys.argv[1]).read_bytes()
original = Path(sys.argv[2]).read_bytes()
def exterior_h2(data):
    headings = []
    fence = None
    offset = 0
    for line in data.splitlines(keepends=True):
        token = re.match(rb"^ {0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            if token and token.group(1)[:1] == fence[:1] and len(token.group(1)) >= len(fence) and not line[token.end():].strip():
                fence = None
        elif token:
            fence = token.group(1)
        elif re.fullmatch(rb"## [^\n]*\n", line):
            headings.append((offset, offset + len(line), line))
        offset += len(line)
    return headings

headings = exterior_h2(document)
headers = [(start, end) for start, end, line in headings if re.fullmatch(rb"## 9\. [^\n]*\n", line)]
if len(headers) != 1:
    raise SystemExit("Sección 9 ausente o repetida")
following = next((start for start, _, _ in headings if start >= headers[0][1]), len(document))
section = document[headers[0][1]:following]
begin = b"<!-- registro-mapa:inicio -->\n"
end = b"<!-- registro-mapa:fin -->\n"
if section.count(begin) != 1 or section.count(end) != 1 or section.index(begin) >= section.index(end):
    raise SystemExit("Marcadores de mapa ausentes, repetidos o invertidos")
inside = section.split(begin, 1)[1].split(end, 1)[0]
lines = inside.splitlines(keepends=True)
while lines and not lines[0].strip(): lines.pop(0)
while lines and not lines[-1].strip(): lines.pop()
if len(lines) < 3 or lines[0] != b"```json\n" or lines[-1] != b"```\n":
    raise SystemExit("Bloque JSON literal mal delimitado")
payload = b"".join(lines[1:-1])
asserted = re.findall(rb"(?m)^map_sha256: ([0-9a-f]{64})\n", section)
if len(asserted) != 1:
    raise SystemExit("Línea literal map_sha256: ausente o repetida en sección 9")
if sha256(payload).hexdigest().encode() != asserted[0] or payload != original:
    raise SystemExit("Mapa del dossier no coincide con scratch o digest declarado")
print(sha256(payload).hexdigest())' "$dossier" "$mapa"
```

**PowerShell:**

```powershell
py -3 -c 'from hashlib import sha256
from pathlib import Path
import re
import sys

document = Path(sys.argv[1]).read_bytes()
original = Path(sys.argv[2]).read_bytes()
def exterior_h2(data):
    headings = []
    fence = None
    offset = 0
    for line in data.splitlines(keepends=True):
        token = re.match(rb''^ {0,3}(`{3,}|~{3,})'', line)
        if fence is not None:
            if token and token.group(1)[:1] == fence[:1] and len(token.group(1)) >= len(fence) and not line[token.end():].strip():
                fence = None
        elif token:
            fence = token.group(1)
        elif re.fullmatch(rb''## [^\n]*\n'', line):
            headings.append((offset, offset + len(line), line))
        offset += len(line)
    return headings

headings = exterior_h2(document)
headers = [(start, end) for start, end, line in headings if re.fullmatch(rb''## 9\. [^\n]*\n'', line)]
if len(headers) != 1:
    raise SystemExit(''Sección 9 ausente o repetida'')
following = next((start for start, _, _ in headings if start >= headers[0][1]), len(document))
section = document[headers[0][1]:following]
begin = b''<!-- registro-mapa:inicio -->\n''
end = b''<!-- registro-mapa:fin -->\n''
if section.count(begin) != 1 or section.count(end) != 1 or section.index(begin) >= section.index(end):
    raise SystemExit(''Marcadores de mapa ausentes, repetidos o invertidos'')
inside = section.split(begin, 1)[1].split(end, 1)[0]
lines = inside.splitlines(keepends=True)
while lines and not lines[0].strip(): lines.pop(0)
while lines and not lines[-1].strip(): lines.pop()
if len(lines) < 3 or lines[0] != b''```json\n'' or lines[-1] != b''```\n'':
    raise SystemExit(''Bloque JSON literal mal delimitado'')
payload = b''''.join(lines[1:-1])
asserted = re.findall(rb''(?m)^map_sha256: ([0-9a-f]{64})\n'', section)
if len(asserted) != 1:
    raise SystemExit(''Línea literal map_sha256: ausente o repetida en sección 9'')
if sha256(payload).hexdigest().encode() != asserted[0] or payload != original:
    raise SystemExit(''Mapa del dossier no coincide con scratch o digest declarado'')
print(sha256(payload).hexdigest())' $dossier $mapa
if ($LASTEXITCODE -ne 0) { throw 'Verificación del mapa fallida' }
```

### Lo que no va

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
3. **El cuerpo**, y leerlo para comprobar que entró entero. Si el compositor devuelve el marcador de
   colapso, esa lectura queda **inconcluyente y no negativa** —el marcador dice que el host colapsó el
   bloque pegado para mostrarlo, no que el cuerpo haya llegado truncado—, así que se sigue: un cuerpo
   roto no sobrevive al primer artefacto que el flujo somete a gate, con el usuario delante.
4. **El Enter**, sobre ese mismo compositor y sin nada tipeado en el medio.

> **Por qué el tercer tiempo no recupera y el segundo sí.** No es una asimetría de rigor sino de qué
> observable sobrevive. El segundo protege la **procedencia**, que solo existe como cadena del envío:
> un prefijo no reconocido no deja rastro en ningún artefacto posterior, así que perderla ahí es
> perderla del todo. El cuerpo no está en esa situación: lo que llegue roto se ve en lo que el flujo
> produce, y frenar acá lo tapa, porque sin Enter no hay flujo y sin flujo no hay artefacto que
> delate el defecto.
>
> Una recuperación acá tampoco sería **ejecutable**: vaciar el compositor exige borrar el draft, y
> ningún subcomando de `orca terminal` lo hace —medido contra 1.4.205, donde `send` admite `--text`,
> `--enter` e `--interrupt` y ninguna operación de tecla—. Prescribirla dejaría a las dos familias
> sobre esa plataforma con un paso sin salida practicable.

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
| Herdr | `herdr pane send-text <id> '<texto>'`; para el primer tiempo de `claude` en Git Bash o cualquier shell MSYS sobre Windows: `MSYS_NO_PATHCONV=1 herdr pane send-text <id> '/sdd-flow '` | `herdr pane read <id> --source visible` | `herdr pane send-keys <id> enter` |
| Orca | `orca terminal send --terminal <handle> --text '<texto>' --json`; para el primer tiempo de `claude` en Git Bash o cualquier shell MSYS sobre Windows: `MSYS_NO_PATHCONV=1 orca terminal send --terminal <handle> --text '/sdd-flow ' --json` | `orca terminal read --terminal <handle> --json` → campo `draft` | `orca terminal send --terminal <handle> --text "" --enter --json` |

**Sin comillas dobles ni apóstrofes** en el texto si va entre comillas simples del shell — más simple
que escapar. Como condición distinta, un argumento que abre con barra se convierte en ruta bajo Git
Bash o cualquier shell MSYS sobre Windows, cualquiera sea la comilla que lo rodee. La forma con
`MSYS_NO_PATHCONV=1` solo aplica al shell que convierte; PowerShell y los POSIX reales no convierten,
no la necesitan y la invocación sin ella sigue siendo válida ahí.

Esta clasificación se midió: el cuerpo, el prefijo de la otra familia y el texto vacío del Enter no
abren con barra y por eso no se convierten.

### Confirmar el arranque — la procedencia, y lo que ya no se acredita

El control viejo buscaba «la señal de que la skill cargó». Eso lo satisface también un agente que
**compensó** leyendo el archivo de la skill por su cuenta, así que no distingue un arranque bueno de
uno malo. Lo que sí discrimina:

| Propiedad | Qué acredita | Qué **no** acredita | Cómo se comprueba |
|---|---|---|---|
| **procedencia** | que la invocación entró por el prefijo, reconocido por el host | nada sobre el contenido del encargo ni sobre el cuerpo del prompt | la **cadena** del envío: el prefijo se reconoció en el tiempo 2, no se tipeó nada en el medio, y el Enter fue sobre ese compositor |

**Y nada más, a propósito.** Antes se exigían dos propiedades más: que el `sha256` del dossier
apareciera entre las fuentes que el flujo congelaba, y que el cuerpo canónico del puntero estuviera
en la primera entrada de su literal. Las dos se comprobaban contra artefactos de acreditación que
`sdd-flow` **ya no produce**, así que seguir exigiéndolas deja este paso sin salida practicable:
ningún arranque puede confirmarse, y entonces ningún incidente puede retirarse nunca.

**Qué queda sin cubrir, dicho en concreto.** Que el flujo haya leído **ese** dossier y no otro, y que
el cuerpo haya entrado entero en el compositor. Las dos las delata el flujo despachado un paso más
adelante y con el usuario delante: sin el puntero entero no hay dossier que leer, y el primer
artefacto que somete a gate se escribe sobre lo que el flujo sí leyó. Pero el retiro del incidente
ocurre **antes** de ese gate, así que el riesgo se acepta con nombre: **un despacho que arrancó bien
y entendió mal deja el registro vacío**, y el defecto se vuelve a registrar como incidente nuevo.

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
| sembrar configuración | árbol creado | el árbol y la configuración copiada | se detiene | intactos | lo copiado | se completa esa configuración sobre el mismo árbol; **no** se borra ni reclasifica por esta fila un registro preexistente o residual |
| resolver el registro declarado | árbol creado | el árbol; ningún registro nuevo | se detiene ante instrucciones ambiguas, divergentes o ruta fuera del árbol | intactos | el árbol y todo archivo previo | decisión humana sobre instrucciones/ruta y nueva comparación de ambas tuplas, sin que el intake edite las instrucciones |
| inspeccionar registro previo | tupla concordante y procedencia acreditada | archivo existente intacto y `scratch/previo` por creación exclusiva | se detiene si no es utilizable, repite un ID dentro del Índice/secciones, coincide con cualquier ID del grupo o su procedencia es incierta | intactos | árbol, archivo previo y `scratch/previo` | inválido o ID duplicado: corrección/decisión sobre ese archivo; procedencia incierta: inspeccionar y aceptar como preexistente **solo si resulta utilizable**, con estado y cantidad observados, autorizar retiro y nueva siembra, o abandonar; nunca vaciarlo automáticamente |
| elegir fuente y preparar candidato | ruta declarada ausente en el worktree | árbol, `scratch/fuente`, `scratch/inventario`, `scratch/mapa` y candidato si se crearon | se detiene si falta cabecera inequívoca, la clasificación es ambigua, el mapa es inválido o falla el cotejo independiente | intactos | árbol y cada temporal existente, con sus rutas y digests disponibles | fuente ausente: aprobación de archivo y ruta física concretos; **mapa inválido**: mostrar primer tramo esperado/recibido y pedir decisión humana para abandonar o crear nueva instantánea/inventario/mapa; cotejo fallido: decisión humana antes de otra vuelta; nunca usar el registro de entrada automáticamente |
| publicar registro declarado | candidato acreditado por `cotejar` y ruta ignorada | archivo publicado si la creación exclusiva llegó a escribirlo; scratch con mapa retenido para 6.3 | colisión: volver a inspección sin sobrescribir; ruta no ignorada o comprobación de bytes/Git fallida: se detiene | intactos | árbol, scratch y archivo publicado si existe, todos enumerados | solo avanzar tras acreditar el nuevo estado; un publicado residual no se convierte en preexistente por inferencia ni se borra sin decisión |
| escribir el dossier | estado distinto de `detenido`; si `sembrado`, mapa y digests acreditados en scratch | árbol, registro, `scratch/mapa` y dossier parcial | se detiene ante escritura fallida, marcadores ambiguos o digest/bytes del mapa distintos en sección 9 | intactos | árbol, registro, scratch con mapa y dossier parcial, cada uno enumerado | reescribir el dossier entero, no parchar; verificar bloque literal y digest antes de limpiar scratch; no reetiquetar el registro como preexistente ni retirarlo automáticamente |
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
| El compositor no muestra la señal de reconocimiento | El prefijo entró dentro del texto pegado, se usó la forma de la otra familia —con espacio donde iba sin él, o al revés—, o actuó la conversión de rutas: en el compositor aparece una ruta absoluta del sistema de archivos en lugar del prefijo | Limpiar el compositor, restablecer readiness y **repetir desde el prefijo**, acreditando su reconocimiento antes de mandar el cuerpo. Ante la conversión de rutas, usar la forma con `MSYS_NO_PATHCONV=1` de la tabla de plataformas. Si no se acredita, el arranque queda **no confirmado** y no se retira nada. La ruta de la skill sirve para **diagnosticar** cuál está instalada, nunca como forma de activarla: pedirle al agente que la lea produce exactamente el arranque compensado que el control existe para rechazar |
| El compositor devuelve el marcador de colapso | El host colapsó el bloque pegado para mostrarlo; no dice nada sobre si el cuerpo llegó entero | Mandar el Enter igual: la lectura del compositor es una comprobación temprana y barata, y acá queda inconcluyente y no negativa. Un cuerpo truncado ya no lo caza el cierre —ver «Confirmar el arranque»—, lo delata el primer artefacto que el flujo somete a gate |
| El flujo pregunta cosas que el config ya responde | El worktree no está sembrado | Sembrar `.specify/` del `<repo_destino>` y avisarle al agente que relea el config |
| El flujo arranca un `init` que nadie pidió | Igual que arriba, caso agudo | Igual, y verificar que el `init` no haya sobrescrito nada |
| `git status` del worktree muestra la configuración sembrada | El destino no ignora esos paths | Sacar del árbol la configuración sembrada y resolver su ignore antes de seguir; esta salida **no** borra registros preexistentes ni residuales de siembra del registro |
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
