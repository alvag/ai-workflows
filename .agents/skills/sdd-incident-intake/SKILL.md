---
name: sdd-incident-intake
description: >-
  Toma incidentes ya registrados de las skills SDD, comprueba que el defecto
  exista, y convierte los que se sostienen en flujos `sdd-flow` corriendo cada
  uno en su worktree de Orca, con un dossier autocontenido, retirándolos del
  registro. Procesa uno por default o los que se le pidan ("revisá 3
  incidentes"), siempre de a uno y en secuencia. El agente que conduce cada flujo
  se elige entre las dos familias (`claude` o `codex`) y por default es el de la
  sesión actual. Usar ante "toma un incidente de <ruta>", "procesa los incidentes
  de skills", "revisá N incidentes", "/sdd-incident-intake <ruta-del-registro>".
  NO corrige la skill: eso lo hace el `sdd-flow` que despacha. NO registra
  incidentes nuevos —eso es la regla del CLAUDE.md del repo—, NO revisa
  artefactos de diseño (eso es `cross-review`) ni delega implementación (eso es
  `cross-implement`). No invocarla espontáneamente: solo ante pedido explícito
  del usuario.
---

# sdd-incident-intake

Convierte entradas del registro de incidentes en trabajo en curso. El registro es una bandeja de
entrada: acumula defectos observados de `sdd-flow` y sus skills hermanas, y no se vacía solo. Esta
skill es el mecanismo de admisión.

**Lo que produce:** por cada incidente admitido, un worktree con un flujo `sdd-flow` arrancado y un
dossier autocontenido que es la única copia de lo que lleva. Y el registro sin lo procesado.

**Lo que NO hace:** corregir la skill. El diagnóstico, el diseño y el parche los produce el
`sdd-flow` que se despacha. Esta skill lo prepara y se retira.

## Las dos reglas que gobiernan todo lo demás

### 1. El registro es insumo, no una orden

> **Un incidente es el reporte de alguien que vio algo, no un ticket aprobado.** La pregunta al
> abrirlo no es "cómo lo arreglo" sino **"¿esto es así?"**.

Lo escribió otra corrida, en otro momento, sobre un árbol que pudo cambiar, y bajo la presión de
haber tropezado con algo. Eso produce reportes fieles, y también estos tres, que se ven igual de
convincentes:

- **El que acierta el síntoma y erra la causa.** El defecto existe; el mecanismo que describe, no.
- **El que llama estructural a un descuido.** Pasó una vez, por una razón que no se repite.
- **El que ya no aplica.** El árbol cambió y el defecto se fue con él.

**Ninguno se detecta leyendo el incidente con más atención.** Se detectan mirando el árbol.

### 2. Verificar es barato, y si deja de serlo ya no es verificar

> **La verificación tiene techo.** Es un chequeo, no una investigación. Si para saber si el problema
> existe hay que reconstruir el escenario, correr el flujo o leer media skill, **la respuesta es que
> se admite**: averiguarlo es el trabajo del flujo despachado, no del intake.

Concretamente: leer las secciones que el incidente cita y correr los `grep` que confirman o refutan
sus afirmaciones. Ese es el alcance. Un intake que se convierte en la investigación **hace dos veces
el trabajo** y encima lo hace sin el aparato del flujo.

## El invariante

> **Verificar → decidir → agrupar → despachar → confirmar arranque → retirar.**

El orden **es** el procedimiento. Cada flecha depende de la anterior y ninguna se adelanta:

- Agrupar sin verificar agrupa por lo que el incidente **dice**, no por lo que pasa.
- Retirar antes de despachar borra la única copia si el despacho falla.
- Retirar sin confirmar que el flujo arrancó deja un registro vacío y un worktree inerte.

El paso que más se saltea es el último control: *mandé el prompt* no es *el flujo arrancó*.

## Parámetros

| Parámetro | Cómo se resuelve |
|---|---|
| `registro` | **Obligatorio.** Ruta al archivo de incidentes, o al directorio que lo contiene (buscar `incidentes-skills.md` adentro). Si el usuario no lo dio, preguntarlo — no adivinarlo. |
| `cantidad` | Cuántos **flujos** abrir. Default **1**. "revisá 3 incidentes" → 3. Cuenta worktrees, no incidentes: un flujo que agrupa dos consume **un** cupo. |
| `agente` | `claude` \| `codex`. **Default: la familia que conduce esta sesión.** Es quién conduce el `sdd-flow` en el worktree, no quién ejecuta esta skill. |
| `incidente` | Cuál tomar. Default: el de **severidad más alta**; a igualdad, el más antiguo. El usuario puede nombrarlo por su fecha y hora. |
| `repo_destino` | Dónde vive el código a corregir. Default: el repo de skills que contiene esta skill. El registro casi nunca vive ahí — es el proyecto donde el defecto se observó. |

`registro` y `repo_destino` **son repos distintos por diseño**. Confundirlos abre el worktree en el
proyecto equivocado.

## Con `cantidad > 1`: de a uno, en secuencia

**Un ciclo completo por flujo, y recién entonces el siguiente.** Nada de verificar los tres juntos y
despachar al final: cada retiro cambia el registro sobre el que se elige el siguiente, y ese orden es
lo que evita que dos flujos se pisen el mismo incidente.

```
por cada cupo:
  elegir → verificar → decidir → agrupar → [gate si hay duda] → worktree → despachar → retirar
```

**Un rechazo no consume cupo.** Si el incidente no se sostiene, se retira igual (ver "El veredicto") y
se sigue bajando por el registro hasta juntar los `cantidad` flujos pedidos.

**El lote termina antes si el registro se agota.** Pedir 3 sobre un registro de 2 abre 2 y lo dice; no
inventa un tercero ni parte un grupo para llegar al número.

## Paso 1 — Leer el registro entero, incluidas sus reglas

Leer el archivo completo, no solo el índice ni la sección del incidente elegido. La cabecera declara
el formato (cómo se forma el ID, qué campos son obligatorios, qué está prohibido escribir); el retiro
del paso 6 tiene que respetarlo y no se puede respetar un formato que no se leyó.

Con `cantidad > 1` se lee **una vez**, al principio del lote. Lo que sí se relee en cada vuelta es el
índice, que cambió.

## Paso 2 — Comprobar contra el árbol y emitir veredicto

Tomar cada afirmación **comprobable** del incidente y comprobarla en el `repo_destino`, con el
escalón más barato que alcance — el default es `grep`. Reportar como tabla:

```
| Afirmación del incidente | Comprobado |
|---|---|
| La ranura X solo manda A | <archivo>: una sola ranura, cero menciones de B |
| La skill nunca menciona C | grep sobre la skill entera → 1 línea, y habla de otra cosa |
```

Buscar activamente, no solo confirmar: **dónde el árbol ya cambió** respecto de lo que el incidente
asume, y **si el arreglo que propone ataca lo que reporta** — un incidente puede describir bien el
defecto y proponer una solución que no lo toca.

### El veredicto

Cada incidente sale con uno de tres, y **decirlo es obligatorio**: un intake que nunca rechazó nada
no está verificando, está transcribiendo.

| Veredicto | Cuándo | Qué pasa |
|---|---|---|
| **Confirmado** | Las afirmaciones se sostienen | Se despacha |
| **Redimensionado** | El defecto existe pero no es el que dice: otra causa, otro alcance, otra sección | Se despacha **con el diagnóstico corregido** en el dossier, y el gate se abre para que el usuario lo vea |
| **Rechazado** | El defecto no está en el árbol | **No se despacha.** Gate obligatorio con la evidencia |

**Un rechazado se retira igual, con permiso del usuario.** La regla 1 del registro dice que un
incidente se remueve **cuando se revisa** — no cuando se arregla. Dejarlo ahí garantiza que la próxima
corrida repita la verificación y llegue a lo mismo. Pero como no habrá dossier donde viva la
evidencia, **la evidencia va en el reporte de cierre**: es lo único que queda de por qué se fue.

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

Cada candidato a relacionado **se verifica también** (paso 2) antes de entrar al grupo. Un incidente
sin verificar entra al dossier como una premisa que nadie comprobó.

## Paso 4 — Gate, pero solo si hay duda

Con la verificación limpia y la agrupación evidente, **se despacha derecho**. Parar en cada flujo
convierte un lote de tres en tres interrupciones y no agrega información: el usuario ya sabe lo que
pidió.

**Se para si se cumple cualquiera de estas — es lista cerrada, no criterio:**

1. El veredicto fue **rechazado** o **redimensionado**.
2. Hay **más de una agrupación defendible** — un candidato comparte archivo pero no sección, o
   comparte causa pero no superficie.
3. La verificación destapó que **el arreglo correcto es otro** que el que el incidente propone.
4. El grupo cruza **más de una skill dueña**: el diff toca a dos, y quién manda no lo decide el intake.
5. El grupo pasa de **tres** incidentes. Un diff que resuelve muchos ya no es evidente para nadie.

Ninguna se cumple → no se pregunta. Al menos una → se para y se muestra: incidentes elegidos y su
causa raíz en una frase, la tabla de verificación, las decisiones abiertas y los descartados.

Sin respuesta no se avanza — **ni en ese flujo ni en el resto del lote**: un "no contestó" no es un sí.

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

Todo lo de abajo se nombra **dentro del `repo_destino`** — es el repo donde va a correr el flujo, no
el repo donde vive esta skill:

| | Qué, dentro de `<repo_destino>/` | Por qué |
|---|---|---|
| **Sí** | `.specify/` — config del flujo, constitution | Sin esto el flujo se cree no inicializado y arranca un `init` que nadie pidió |
| **Sí** | `.claude/` — settings locales, permisos concedidos | Sin esto el flujo se traba pidiendo permisos que en el árbol principal ya están dados |
| **No** | Directorios de trabajo de las skills: `.co-explore/`, `.cross-review/`, `.cross-implement/`, `.cross-model/` | Son corridas anteriores. El flujo nuevo genera las suyas; arrastrarlas le da un estado que no es el suyo |
| **No** | El resto de `.plans/` | Son flujos ajenos. Salvo que este flujo sea una **retoma**, y entonces se copia **ese** plan y solo ese |
| **No** | Cachés, `.idea/`, `.handoffs/` | Ruido; y una caché con rutas del árbol viejo adentro es peor que ruido |

**El inventario se deriva, el criterio se congela.** No transcribir una lista de directorios: leerlos
del repo en el momento, porque la lista de arriba envejece y una entrada que ya no existe se lee
igual de bien que una vigente.

```
git -C <repo_destino> status --porcelain --ignored=matching -uall | grep '^!!'
```

> **Se siembra por archivo, no por directorio.** Un directorio puede estar **medio versionado** — con
> archivos trackeados adentro y solo alguno ignorado. Copiarlo entero sobre un destino que ya existe
> **anida la copia adentro** y no fusiona nada; y como lo anidado también queda ignorado, la
> comprobación de árbol limpio **pasa igual** y la siembra se declara hecha sin estarlo. El comando de
> arriba ya lista archivo por archivo: usar esa granularidad.

**Después de copiar, comprobar las tres cosas** — `git check-ignore -v` sobre cada archivo sembrado,
`git status --porcelain` limpio, y que **el archivo esté en la ruta esperada**. Las dos primeras no
detectan el anidamiento; la tercera sí.

> **Antes de copiar, ver si el hook de setup del repo ya lo hizo.** Orca corre un script de setup por
> repo al crear el worktree, y algunos repos ya siembran ahí (`orca repo show` →
> `hookSettings.scripts.setup`). Si ya sembró, no volver a copiar encima: se pisan archivos que el
> hook pudo adaptar al worktree.

### 5.3 — Dossier

En `<worktree>/.plans/incidentes-a-corregir.md`. Plantilla y contrato de contenido en `reference.md`
→ "El dossier". La regla que lo gobierna:

> **El dossier es la única copia.** Después del paso 6 los incidentes no existen en ningún otro lado.
> Van **verbatim**, no resumidos.

Si el veredicto fue **redimensionado**, el dossier lleva las dos versiones: el incidente tal como se
escribió y el diagnóstico corregido, marcado como tal. Reemplazar una por la otra borra la evidencia
de que hubo una corrección.

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

Recién ahora, y solo si el paso 5 confirmó el arranque (o si el veredicto fue **rechazado** y el
usuario lo aprobó en el gate). **Dos lugares, siempre los dos:**

1. **El índice** — la fila de cada incidente tomado.
2. **El cuerpo** — la sección completa de cada uno, con su separador.

Después, comprobar que no quedaron residuos: `grep` de la fecha y hora de cada incidente y de dos o
tres términos distintivos de su título. Un retiro que deja el índice limpio y la sección en el cuerpo
es peor que no retirar: el archivo pierde su propio inventario.

**Lo que nunca se toca:** la cabecera de reglas, el resto de los incidentes, y el orden cronológico
de los que quedan. **Nunca se edita un incidente ajeno "de paso"** — la regla 2 del registro dice que
una reincidencia se agrega y nunca se edita, y esa regla protege la frecuencia, que es el dato más
valioso del archivo.

En modo lote, este paso cierra la vuelta: recién con el registro actualizado se elige el siguiente.

## Cierre

Reportar, por cada flujo: incidentes tomados, **veredicto de cada uno**, por qué se agruparon, tabla
de verificación, decisiones abiertas que quedaron en el dossier, worktree y rama, y estado del flujo.

Y una vez para todo el lote: los **rechazados con su evidencia** —es lo único que queda de ellos—, los
cupos que se repusieron, y el conteo del registro antes y después.

## Red flags — parar

| Pensamiento | Realidad |
|---|---|
| "El incidente está bien escrito, lo despacho" | Está bien escrito **para el árbol de su fecha**. Comprobarlo cuesta un `grep`. |
| "Verifiqué los tres y ninguno falló" | Posible, pero revisalo: un intake que nunca rechaza nada está transcribiendo. |
| "Para saber si esto pasa tengo que reproducirlo" | Entonces se admite. Reproducir es el trabajo del flujo, no del intake. |
| "Los retiro ahora que ya los elegí" | Retirados antes del dossier, no queda copia de nada. |
| "Mandé el prompt, sigo" | El prefijo puede haber quedado dentro del texto pegado, o ser el de la otra familia. Leer el terminal. |
| "Son de la misma skill, van juntos" | La misma skill en otra fase es otro diff. El criterio es la superficie. |
| "Orca lo creó, está en main" | Está en `origin/main`. Comparar contra `git rev-parse main`. |
| "Es el mismo repo, el worktree tiene todo" | Tiene lo **versionado**. El config del flujo SDD, por diseño, no lo está. |
| "Copio el directorio entero y listo" | Puede estar medio versionado: la copia se anida y la comprobación pasa igual. Por archivo. |
| "Al dossier le pongo un resumen" | Es la única copia. Verbatim. |
| "Verifico los tres y después despacho los tres" | Cada retiro cambia el registro sobre el que se elige el siguiente. De a uno. |
| "Me falta uno para llegar a tres, agrupo distinto" | El número es de flujos, no una cuota. Un grupo forzado es un diff que hace dos cosas. |
| "Aprovecho y corrijo la skill acá" | Esta skill prepara el flujo. Corregir es del `sdd-flow` despachado. |

## Gotchas

- **Ignorar y heredar son cosas distintas.** Un worktree **no hereda el contenido** untracked, pero
  **sí hereda las reglas de ignore**: comparte `info/exclude` con el commondir, y el ignore global del
  usuario aplica igual. Por eso el dossier y lo sembrado quedan fuera de git sin configurar nada — y
  por eso mismo la falta de la config del flujo no se nota hasta que el flujo ya arrancó mal.
- **El registro puede estar en un repo que no es el destino.** Es lo normal, no una anomalía.
- **El dossier tiene que llevar las restricciones del `repo_destino`.** El flujo despachado arranca
  sin contexto de esta sesión: si el repo tiene reglas que un flujo puede violar sin darse cuenta
  (topes de verificación, prohibiciones sobre directorios, guardas que hay que correr), van escritas.
  `reference.md` → "El dossier" lo detalla.
- **Si algo de este procedimiento falla por culpa de una skill SDD**, eso es un incidente y se
  registra según la regla del archivo de instrucciones del `repo_destino` — en el árbol principal,
  nunca en el worktree.
