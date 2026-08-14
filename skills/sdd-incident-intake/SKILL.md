---
name: sdd-incident-intake
description: >-
  Toma incidentes ya registrados de las skills SDD y los convierte en un flujo
  `sdd-flow` corriendo en su propio worktree de Orca, con un dossier
  autocontenido, y recién entonces los retira del registro. El agente que conduce
  ese flujo se elige entre las dos familias (`claude` o `codex`) y por default es
  el de la sesión actual. Usar ante "toma un incidente de <ruta>", "procesa los
  incidentes de skills", "abrí un flujo para el incidente de <fecha>",
  "/sdd-incident-intake <ruta-del-registro>". NO corrige la skill: eso lo hace el
  `sdd-flow` que despacha. NO registra incidentes nuevos —eso es la regla del
  CLAUDE.md del repo—, NO revisa artefactos de diseño (eso es `cross-review`) ni
  delega implementación (eso es `cross-implement`). No invocarla espontáneamente:
  solo ante pedido explícito del usuario.
---

# sdd-incident-intake

Convierte una entrada del registro de incidentes en trabajo en curso. El registro es una bandeja
de entrada: acumula defectos observados de `sdd-flow` y sus skills hermanas, y no se vacía solo.
Esta skill es el mecanismo de admisión.

**Lo que produce:** un worktree con un flujo `sdd-flow` arrancado, un dossier autocontenido que es
la única copia de los incidentes tomados, y el registro de origen sin ellos.

**Lo que NO hace:** corregir la skill. El diagnóstico, el diseño y el parche los produce el
`sdd-flow` que se despacha. Esta skill lo prepara y se retira.

## El invariante

> **Verificar → agrupar → despachar → confirmar arranque → retirar.**

El orden **es** el procedimiento. Cada flecha depende de la anterior y ninguna se adelanta:

- Agrupar sin verificar agrupa por lo que el incidente **dice**, no por lo que pasa.
- Retirar antes de despachar borra la única copia si el despacho falla.
- Retirar sin confirmar que el flujo arrancó deja un registro vacío y un worktree inerte.

El paso que más se saltea es el último control: *mandé el prompt* no es *el flujo arrancó*.

## Parámetros

| Parámetro | Cómo se resuelve |
|---|---|
| `registro` | **Obligatorio.** Ruta al archivo de incidentes, o al directorio que lo contiene (buscar `incidentes-skills.md` adentro). Si el usuario no lo dio, preguntarlo — no adivinarlo. |
| `agente` | `claude` \| `codex`. **Default: la familia que conduce esta sesión.** Es quién conduce el `sdd-flow` en el worktree, no quién ejecuta esta skill. |
| `incidente` | Cuál tomar. Default: el de **severidad más alta**; a igualdad, el más antiguo. El usuario puede nombrarlo por su fecha y hora. |
| `repo_destino` | Dónde vive el código a corregir. Default: el repo de skills que contiene esta skill. El registro casi nunca vive ahí — es el proyecto donde el defecto se observó. |

`registro` y `repo_destino` **son repos distintos por diseño**. Confundirlos abre el worktree en el
proyecto equivocado.

## Paso 1 — Leer el registro entero, incluidas sus reglas

Leer el archivo completo, no solo el índice ni la sección del incidente elegido. La cabecera declara
el formato (cómo se forma el ID, qué campos son obligatorios, qué está prohibido escribir); el retiro
del paso 6 tiene que respetarlo y no se puede respetar un formato que no se leyó.

Del índice sale el inventario. Del cuerpo sale lo que importa: **qué skill, qué sección, qué instruía
frente a qué pasó, y qué habría que cambiar.**

## Paso 2 — Verificar cada afirmación contra el árbol

**Un incidente no verificado no se despacha.** El registro lo escribió otra corrida, en otro
momento, sobre un árbol que pudo cambiar.

Tomar cada afirmación comprobable del incidente y comprobarla en el `repo_destino`, usando el
escalón más barato que alcance — el default es `grep`. Reportar el resultado como tabla:

```
| Afirmación del incidente | Comprobado |
|---|---|
| La ranura X solo manda A | <archivo>: una sola ranura, cero menciones de B |
| La skill nunca menciona C | grep sobre la skill entera → 1 línea, y habla de otra cosa |
```

**Lo que hay que buscar activamente, no solo confirmar:** el punto donde el árbol **ya cambió**
respecto de lo que el incidente asume. Un incidente puede acertar el defecto y errar la descripción
del mecanismo, porque el mecanismo se refactorizó después de que se registró.

Eso **no invalida el incidente**. Cambia el diseño de la solución, y es exactamente lo que el flujo
despachado necesita saber. Va al dossier como **decisión abierta**, con las opciones nombradas y
**sin pre-decidirla**.

**Si una afirmación cae del todo** —el defecto ya no existe—: el incidente no se despacha y **no se
retira en silencio**. Reportarlo al usuario con la evidencia y preguntar si se retira como resuelto
o se deja.

## Paso 3 — Agrupar por superficie editable

Buscar en el mismo registro los incidentes que se resolverían en **el mismo diff**.

> **El criterio es la superficie editable y la causa raíz compartida — no la skill.**

Dos incidentes de la misma skill, en fases distintas del flujo y sobre archivos distintos, son **dos
flujos**. Agruparlos porque comparten el nombre de la skill produce un diff que hace dos cosas y una
revisión que no puede juzgar ninguna.

Señales de que **sí** van juntos:

- Editan los mismos archivos y las mismas secciones.
- Se pueden enunciar como **una** causa raíz sin forzar la frase.
- El incidente A, corregido, cambia el mejor arreglo de B.

Señales de que **no**:

- Comparten skill pero no archivos.
- Están en fases distintas (uno en un gate previo, otro en el prompt despachado).
- La causa raíz común solo se sostiene subiendo el nivel de abstracción hasta "es todo lo mismo".

## Paso 4 — Gate: presentar la agrupación

**Parar y mostrar al usuario**, antes de crear nada:

1. Los incidentes elegidos y la causa raíz que comparten, en una frase.
2. La tabla de verificación del paso 2.
3. Las decisiones abiertas que el paso 2 destapó.
4. Los **descartados** y por qué — en particular los que comparten skill y no se agruparon.

El usuario puede reagrupar. Sin su respuesta, no se avanza: un "no contestó" no es un sí.

## Paso 5 — Worktree, siembra, dossier y despacho

Los cuatro son un solo paso porque el orden entre ellos también es el invariante: **el worktree está
sembrado antes de que el flujo arranque**, el dossier existe antes de que el prompt se mande, y el
prompt se manda antes de que el registro se toque.

### 5.1 — Worktree

Con `orca-cli`, desde la rama base del `repo_destino`, con `--agent <agente>`. Comandos exactos en
`reference.md` → "Worktree con orca-cli".

> **Verificar la base.** `worktree create` usa el base ref del repo —`origin/<default>`—, **no el
> `main` local. Si el local está adelante, el worktree nace atrasado y nada lo señala.** Comparar el
> `head` del JSON contra `git rev-parse main` y realinear si difieren.

### 5.2 — Sembrar el entorno ignorado

**Un worktree nace sin nada de lo que git no versiona.** El flujo SDD depende de archivos que están
justamente ahí: su config, su constitution, los permisos locales. Sin ellos `sdd-flow` no falla —
**hace algo peor: cree que el proyecto no está inicializado y arranca un wizard de `init`**, o vuelve
a preguntar decisiones que el config ya tenía resueltas.

> **Se siembra la configuración del entorno. No se siembra el historial de corridas ajenas.**

| | Qué | Por qué |
|---|---|---|
| **Sí** | `.specify/` (config del flujo, constitution) | Sin esto el flujo se cree no inicializado y arranca un `init` que nadie pidió |
| **Sí** | `.claude/` (settings locales, permisos concedidos) | Sin esto el flujo se traba pidiendo permisos que en el árbol principal ya están dados |
| **No** | Directorios de trabajo de las skills (`.co-explore/`, `.cross-review/`, `.cross-implement/`, `.cross-model/`) | Son corridas anteriores. El flujo nuevo genera las suyas; arrastrarlas le da un estado que no es el suyo |
| **No** | El resto de `.plans/` | Son flujos ajenos. Salvo que este flujo sea una **retoma**, y entonces se copia **ese** plan y solo ese |
| **No** | Cachés, `.idea/`, `.handoffs/` | Ruido; y una caché con rutas del árbol viejo adentro es peor que ruido |

**El inventario se deriva, el criterio se congela.** No transcribir una lista de directorios: leerlos
del repo en el momento, porque la lista de arriba envejece y una entrada que ya no existe se lee
igual de bien que una vigente.

```
git -C <repo_destino> status --porcelain --ignored=matching -uall | grep '^!!'
```

**Después de copiar, comprobar que lo copiado sigue ignorado en el destino** — `git check-ignore -v`
sobre cada archivo sembrado, y `git status --porcelain` limpio. El modo de falla es silencioso: un
archivo sembrado que el destino **no** ignora queda como untracked y termina en un commit del flujo.

> **Antes de copiar, ver si el hook de setup del repo ya lo hizo.** Orca corre un script de setup por
> repo al crear el worktree, y algunos repos ya siembran ahí (`orca repo show` →
> `hookSettings.scripts.setup`). Si ya sembró, no volver a copiar encima: se pisan archivos que el
> hook pudo adaptar al worktree.

### 5.3 — Dossier

En `<worktree>/.plans/incidentes-a-corregir.md`. Plantilla y contrato de contenido en `reference.md`
→ "El dossier". La regla que lo gobierna:

> **El dossier es la única copia.** Después del paso 6 los incidentes no existen en ningún otro lado.
> Van **verbatim**, no resumidos.

### 5.4 — Despacho

Mandar el flujo al agente del worktree y **confirmar que arrancó** leyendo el terminal. Mecánica del
envío y modos de falla del transporte en `reference.md` → "Despachar el flujo".

> **El prefijo de invocación cambia con la familia:** `claude` → **`/sdd-flow`**, `codex` →
> **`$sdd-flow`**. El cuerpo del prompt es el mismo. Con el prefijo equivocado el texto entra como
> mensaje común, el agente contesta razonablemente **sin la skill cargada**, y eso se lee igual que
> un arranque exitoso.

> **`mandé el prompt` no es `el flujo arrancó`.** Leer el terminal y confirmar que la skill cargó. Si
> no cargó, corregir el envío — nunca continuar al paso 6.

## Paso 6 — Retirar del registro

Recién ahora, y solo si el paso 5 confirmó el arranque. **Dos lugares, siempre los dos:**

1. **El índice** — la fila de cada incidente tomado.
2. **El cuerpo** — la sección completa de cada uno, con su separador.

Después, comprobar que no quedaron residuos: `grep` de la fecha y hora de cada incidente y de dos o
tres términos distintivos de su título. Un retiro que deja el índice limpio y la sección en el cuerpo
es peor que no retirar: el archivo pierde su propio inventario.

**Lo que nunca se toca:** la cabecera de reglas, el resto de los incidentes, y el orden cronológico
de los que quedan. **Nunca se edita un incidente ajeno "de paso"** — la regla 2 del registro dice que
una reincidencia se agrega y nunca se edita, y esa regla protege la frecuencia, que es el dato más
valioso del archivo.

## Cierre

Reportar al usuario: incidentes tomados y por qué se agruparon, tabla de verificación, decisiones
abiertas que quedaron en el dossier, worktree y rama creados, estado del flujo, y el conteo del
registro antes y después.

## Red flags — parar

| Pensamiento | Realidad |
|---|---|
| "El incidente está bien escrito, lo despacho" | Está bien escrito **para el árbol de su fecha**. Verificarlo cuesta un `grep`. |
| "Los retiro ahora que ya los elegí" | Retirados antes del dossier, no queda copia de nada. |
| "Mandé el prompt, sigo" | El prefijo puede haber quedado dentro del texto pegado, o ser el de la otra familia. Leer el terminal. |
| "Son de la misma skill, van juntos" | La misma skill en otra fase es otro diff. El criterio es la superficie. |
| "Orca lo creó, está en main" | Está en `origin/main`. Comparar contra `git rev-parse main`. |
| "Es el mismo repo, el worktree tiene todo" | Tiene lo **versionado**. El config del flujo SDD, por diseño, no lo está. |
| "Copio todo lo ignorado y listo" | Las corridas ajenas le dan al flujo un estado que no es el suyo. Se siembra config, no historial. |
| "Al dossier le pongo un resumen" | Es la única copia. Verbatim. |
| "Una afirmación no se sostiene, la salteo" | Si el defecto ya no existe, el incidente no se despacha **y no se retira solo**. |
| "Aprovecho y corrijo la skill acá" | Esta skill prepara el flujo. Corregir es del `sdd-flow` despachado. |

## Gotchas

- **Ignorar y heredar son cosas distintas.** Un worktree **no hereda el contenido** untracked, pero
  **sí hereda las reglas de ignore**: comparte `info/exclude` con el commondir, y el ignore global del
  usuario aplica igual. Por eso el dossier y lo sembrado quedan fuera de git sin configurar nada — y
  por eso mismo la ausencia de `.specify/` no se nota hasta que el flujo ya arrancó mal.
- **El registro puede estar en un repo que no es el destino.** Es lo normal, no una anomalía.
- **El dossier tiene que llevar las restricciones del `repo_destino`.** El flujo despachado arranca
  sin contexto de esta sesión: si el repo tiene reglas que un flujo puede violar sin darse cuenta
  (topes de verificación, prohibiciones sobre directorios, guardas que hay que correr), van escritas.
  `reference.md` → "El dossier" lo detalla.
- **Si algo de este procedimiento falla por culpa de una skill SDD**, eso es un incidente y se
  registra según la regla del `CLAUDE.md` del repo — en el árbol principal, nunca en el worktree.
