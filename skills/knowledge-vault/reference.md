# knowledge-vault — referencia

Detalle que `SKILL.md` no necesita en cada corrida. Se lee cuando hace falta el
contrato exacto de un verbo, un código de salida, o entender por qué algo falla.

## Matriz por verbo

| Verbo | Obligatorias | Opcionales | Raíz del vault |
|---|---|---|---|
| `archive` | `--from <dir>` · `--summary <línea>` | — | `--vault-root` \| `--config` \| default |
| `migrate` | `--from <dir>` · `--summaries <tsv>` | `--dry-run` | `--vault-root` \| `--config` \| default |
| `index` | — | — | `--vault-root` \| `--config` \| default |
| `config` | `--config <ruta>`, salvo con `--discover` | `--set-root <ruta>` · `--discover` · `--search-root <ruta>` | la declara él mismo |
| `retire` | `--root <dir>` | `--from <dir>` · `--dry-run` · `--approve-digest <hex>` | `--vault-root` \| `--config` \| default |
| `identity` | `--propose` \| `--declare <id>` | — | `--vault-root` \| `--config` \| default |

`--config` y `--vault-root` son **excluyentes**: la raíz del vault se declara de
una sola forma, y "cuál manda" no tiene una respuesta que valga la pena inventar.

`config --discover` es el único modo que **no** exige `--config`: no lee ni escribe
configuración, sólo mira el disco. Busca desde el home —o desde `--search-root`—
hasta tres niveles, y devuelve cuatro cosas: `vaults` con su evidencia (cuántos
proyectos y flujos), `nuevos` (directorios con la forma de un vault nuevo, sin
marca de `kv` todavía), `sugerido` (el único vault, si hay exactamente uno) y
`ajenos`. Sale **0 siempre**, cero candidatos incluido: un descubrimiento que falla
por lo que encontró no se puede leer.

`nuevos` y `vaults` llevan candidatos completos —`root`, `clase`, `evidencia`—
porque los dos se ofrecen; `ajenos` lleva rutas planas porque no. Un candidato de
`nuevos` trae `evidencia: null`: no es un vault de `kv`, así que no hay proyectos ni
flujos que contar, y exhibir un `{proyectos: 0, flujos: 0}` lo volvería
indistinguible de un vault de `kv` recién creado. **`sugerido` sale sólo de
`vaults`**, nunca de `nuevos`: elegir dónde *crear* un vault es todavía más una
pregunta de propósito que elegir entre dos que ya existen.

**La clasificación es por marca estructural, no por ubicación**, y la diferencia se
midió: un home real tenía dos directorios bajo `~/vaults/`, y sólo uno era un vault
de `kv`. La marca es `.kv/`, o el par `index.md` + `projects/` para un vault anterior
a `.kv`. Un directorio con `.obsidian/` **y documentos** pero sin ninguna de las dos
es el vault de notas de alguien: se informa en `ajenos`, nunca se sugiere, y
`assertRootUsable` lo rechaza con `VAULT_ROOT_UNAVAILABLE` si alguien lo declara
igual. `.obsidian/` **sin** documentos no cuenta: esa es la forma de un vault de `kv`
recién creado que se abrió en Obsidian antes de archivar nada.

Todo entra por banderas largas. Un argumento suelto es `USAGE`.

## Estado a código de salida

| Código | Estados | Qué significa |
|---|---|---|
| 0 | `ARCHIVED` · `ALREADY_ARCHIVED` · `INDEX_OK` · `BATCH_OK` · `DRY_RUN` · `VAULT_CONFIGURED` · `VAULT_SET` · `IDENTITY_PROPOSED` · `IDENTITY_DECLARED` · `IDENTITY_ALREADY_DECLARED` | éxito |
| 1 | `INTERNAL_ERROR` · `BATCH_PARTIAL` · `BATCH_FAILED` | fallo de la corrida o del lote |
| 2 | `USAGE` | la invocación es inválida |
| 3 | `CONFIG_INVALID` | el config existe y no se puede leer sin adivinar |
| 4 | `PRECONDITION_NOT_MET` · `AMBIGUOUS_IDENTITY` | el vault está sucio, anidado, el nombre del flujo es reservado, el digest aprobado no describe el lote, el estado observado no lo produce la secuencia, o la identidad del repositorio no está declarada o no es única |
| 5 | `NO_VAULT` | no se declaró la raíz, o el config no la trae |
| 8 | `SOURCE_UNAVAILABLE` | el origen no se puede leer |
| 9 | `VERIFY_FAILED` · `COPY_FAILED` · `PUBLISH_FAILED` | el destino no verifica, el remanente no verifica contra el vault, o la publicación falló |

**Un lote incompleto no sale 0.** Migrar 49 de 50 deja un vault que ningún
criterio distingue de uno completo: no hay manifiesto que enumere lo que debía
entrar. Quien lo consulte va a concluir que el flujo que falta nunca existió.

La tabla se redujo de dieciocho códigos a ocho al retirarse `restore`, `doctor`,
`inventory` y el aparato de retiro. Los códigos que **quedaron conservan su
número**, para no reescribirle el significado a un `9` que ya quería decir "el
destino no verifica".

Y cuando el retiro volvió, **volvió sin códigos propios**: `retire` reusa
`DRY_RUN`, `BATCH_OK`, `BATCH_PARTIAL` y `BATCH_FAILED` con exactamente el mismo
sentido que ya tenían. Quien automatiza `kv` ramifica sobre estos números, así que
un verbo nuevo que renumerara le rompería el guion sin que nada avisara.

`AMBIGUOUS_IDENTITY` es el único estado que se **agregó** a un código existente, y
entra en el 4 y no en un código propio por la misma razón: los vacantes —6 y 7—
pertenecieron a verbos retirados, y darles un sentido nuevo se lo reescribiría a
un guion viejo. La familia además es la correcta: es una precondición que hay que
resolver antes de operar. Antes de existir, un `retire` sobre un repositorio sin
identidad declarada salía `INTERNAL_ERROR`, que le dice a quien automatiza que
encontró un bug en vez de que le falta un paso.

## Qué entra: el predicado

```
isCopiable(ruta relativa) = no contiene "/" y termina en ".md"
```

La extensión se compara sin distinguir mayúsculas. La ruta relativa la produce el
inventario, que la arma siempre con `/` en cualquier plataforma, así que en POSIX
una barra invertida es un carácter más del nombre.

Nombres de flujo **reservados**: `index` y `log`. Un flujo así llamado se rechaza
en vez de pisar un archivo generado, y la comparación va por clave de colisión
—no por igualdad— porque en macOS y Windows `Index.md` pisa `index.md`.

## El nombre del directorio es el `flow-id`

El basename del directorio de origen **es** el identificador con el que el flujo queda archivado, así
que tiene que ser canónico de entrada:

```
FLOW_ID_RE = /^(?!.*\.\.)[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$/
```

En prosa: **1 a 128 caracteres**, ASCII minúsculo, extremos en `[a-z0-9]`, interior `[a-z0-9._-]`, y
`..` prohibido en cualquier posición. **No es "kebab-case"**, que sería más restrictivo: `v1.2.3` y
`a_b.c-d` son canónicos.

**La gramática no alcanza: hay dos exclusiones más, y las tres se aplican juntas.** Un nombre que la
cumpla puede rechazarse igual por ser **reservado** —`index` y `log`, por la colisión que se explica
arriba— o por ser un **nombre de dispositivo de Windows** —`con`, `prn`, `aux`, `nul`, `com1`-`com9`,
`lpt1`-`lpt9`—. Las tres condiciones son la aceptación completa, y el candidato que ofrece el error
al renombrar pasa por las tres antes de proponerse: recomendar un nombre que después se rechaza es
el mismo defecto que ese mensaje vino a corregir. Cuando ninguna variante del nombre las cumple, el
error **omite la sugerencia** en vez de inventar una.

### Por qué el nombre no se normaliza

Un nombre fuera del dominio se rechaza y **no se normaliza**, aunque transformarlo sería trivial.
Normalizar antes de validar haría converger `PQTCH-546` y `pqtch-546` al mismo `flow-id`, mezclando
dos flujos distintos como revisiones de una sola fuente — y la comprobación de identidad no lo detectaría, porque
comparten `repo_identity`.

Por eso el error **ofrece** el candidato y no lo aplica: la decisión de renombrar es de una persona.
Cuando el plegado a minúsculas no alcanza para producir un nombre válido —`ª-546`, `---`, la cadena
vacía—, el mensaje omite el candidato en vez de inventar uno.

### Renombrar hacia un id que ya existe mezcla los dos flujos

El candidato que el error propone puede **ya estar en uso** por otro flujo del mismo repositorio.
Renombrar hacia él y archivar deja los dos **bajo una sola fuente**, que es la misma colisión que
justifica no normalizar, llegando por la puerta de la recomendación. Antes de renombrar conviene
mirar `<vault>/projects/<repo>/sdd/` y elegir otro nombre si el candidato ya está tomado.

### En `migrate`, renombrar el directorio no alcanza

`migrate` valida la biyección entre los basenames y las claves del TSV **antes** de procesar el lote
(`commands/migrate.mjs`). Si se renombra el directorio y no se actualiza su **clave en el TSV**, el
reintento produce dos problemas —el flujo sin resumen y el resumen sin flujo— y sale `BATCH_FAILED`
**sin migrar ninguno**, aunque el resto del lote estuviera bien.

El procedimiento completo, entonces:

1. renombrar el directorio de origen al nombre canónico;
2. actualizar su clave en el TSV de resúmenes;
3. reintentar `migrate` con el mismo lote.

El reintento es seguro: sale `BATCH_OK` y lo que ya se había archivado en la corrida parcial cuenta
como `ALREADY_ARCHIVED` (`yaEstaban`), sin duplicar ni reescribir nada.

## El layout, completo

```
<vault>/.gitignore                            `.obsidian/` y `.DS_Store`; sembrado al crear el vault
<vault>/.kv/identidades.tsv                   identidad DECLARADA de cada repositorio
<vault>/.kv/retiros/<repo>/<flujo>.json       manifiesto de retiro: autorización y registro
<vault>/index.md                              índice raíz, agrega TODOS los flujos
<vault>/log.md                                una línea por archivado
<vault>/projects/index.md                     índice
<vault>/projects/<repo>/index.md              índice
<vault>/projects/<repo>/sdd/index.md          índice
<vault>/projects/<repo>/sdd/<flujo>.md        el NODO, hermano del directorio
<vault>/projects/<repo>/sdd/<flujo>/          FRONTERA VERIFICADA
<vault>/projects/<repo>/sdd/<flujo>/*.md      copiados, byte-idénticos
```

**Los tres primeros son infraestructura y viven fuera de `projects/`**, que es donde
Obsidian mira. `.kv/` empieza con punto porque Obsidian ignora los directorios
ocultos y Git no: el registro de identidades y los manifiestos de retiro se
versionan —son autoridad, no cache— sin ensuciar la bóveda de quien la consulta.

**Agregación transitiva, no listado de hijos.** Un índice que liste sólo su nivel
deja la raíz con una entrada —`projects/`— y obliga a bajar cuatro niveles. Cada
índice lista todos los flujos que cuelgan de él, así que la raíz alcanza para
ubicar cualquiera.

**Regenerar da los mismos bytes.** Nada de timestamps, orden explícito en vez del
que devuelva el filesystem, y ninguna fuente externa al vault — en particular
ningún modelo redactando nada.

## El nodo: los ocho campos

| Campo | De dónde |
|---|---|
| `type` | constante |
| `title` | encabezado `# ` de `spec.md` → el de `plan.md` → el id del flujo |
| `project` | el slug del repositorio |
| `flow` | el id del flujo |
| `branch` | `branch` del frontmatter de `plan.md` → `desconocido` |
| `date` | `created_at` del frontmatter de `plan.md` → `desconocido` |
| `provenance` | las dos últimas partes de la ubicación de origen, más el id |
| `state` | `status` del frontmatter, **literal** → `desconocido` |

Más `summary`, que lo provee quien llama.

**Nunca se infiere del sistema de archivos.** La tentación concreta es la fecha:
el directorio tiene `mtime` y siempre está ahí. Pero copiar al vault lo reescribe,
con lo cual esa fecha sería la de la migración disfrazada de fecha del trabajo.

### Lo que el frontmatter no puede representar

El parser **no es YAML y no tiene escapes**. Tres clases de valor no vuelven
idénticas, y por eso se **rechazan** en vez de escaparse — escapar sin desescapar
produce un archivo que se ve bien y miente:

| Se emite | Se lee |
|---|---|
| `"envuelto"` | `envuelto` |
| `  con espacios  ` | `con espacios` |
| un carácter de control | otra clave, u otra línea |

**El numeral sí se representa, entrecomillado.** El parser mira las comillas antes
de descartar el comentario, así que un valor citado vuelve literal con su `#`
adentro. Importa porque el `title` del nodo se **deriva** del encabezado del
documento: una ronda de feedback que cita el número de su PR trae el numeral
puesto, y quien archiva no lo elige.

El delimitador lo elige el emisor según el contenido, y ahí queda la cuarta clase
irrepresentable, que depende del valor:

| El valor con `#` contiene | Se emite | Por qué |
|---|---|---|
| ninguna comilla simple | `'…'` | dentro de comillas simples YAML no interpreta escapes |
| simple, pero ni doble ni barra inversa | `"…"` | no queda nada que un lector de YAML reinterprete |
| simple **y** (doble o barra inversa) | se rechaza | no hay delimitador que lo devuelva idéntico |

Los `:` y las comillas interiores sí vuelven idénticos. El emisor además **relee
su propia salida** antes de devolverla.

## La capa de configuración

`kv` **no tiene un archivo propio**. Escribe en el que ya usa el consumidor —para
un repositorio con flujos SDD, `.specify/config.yml`— bajo una sección
`knowledge-vault:` que nadie más toca:

```yaml
knowledge-vault:
  path_vault: "/Users/alguien/vaults/dev-memory"
```

Como ese archivo es **por proyecto**, un repositorio archiva en un vault y otro en
otro sin ningún registro global. La escritura es **por líneas**: el archivo es de
otro, y reserializarlo le reescribiría el formato entero.

`~/` se expande con el home del sistema, así que la misma declaración sirve en
Windows. Una raíz relativa, con `..`, o con una forma de `~` no soportada se
rechaza **antes** de escribir.

## La matriz de rutas

Antes de operar se exige que:

1. el **vault** sea disjunto del repositorio y de la raíz de archivados, en las
   dos direcciones;
2. el **flujo** sea hijo directo de la raíz de archivados.

El criterio ingenuo —"que ninguna ruta se solape"— **bloquea el archivado
entero**: el directorio de un flujo vive dentro del repositorio por construcción.
Se compara sobre rutas resueltas, porque un vault que es un enlace simbólico al
repositorio no comparte un carácter de prefijo con él y es el mismo directorio.

## Las cuatro postcondiciones

`ARCHIVED` y `ALREADY_ARCHIVED` exigen las cuatro: **frontera publicada, nodo
escrito, índices regenerados y commit creado.** Si falta alguna, el reintento la
reconstruye.

Con la definición fácil —"publicado = la frontera existe"— una caída entre la
publicación y el commit dejaría un flujo copiado que el reintento reporta como
completo y que no aparece en ningún índice: presente en disco e invisible para
siempre.

## `identity`: de qué repositorio estamos hablando

La ruta dentro del vault es `projects/<repo-id>/sdd/<flujo>/`, y ese `<repo-id>`
**se declara**. Antes se derivaba del nombre del directorio, y el propio módulo de
identidad ya advertía que ese nombre no es identidad: con N repositorios en N
máquinas, dos clones que se llamen `api` comparten sitio en el vault y un retiro
decidiría sobre el flujo equivocado.

### Las dos banderas son un gate, no dos modos

```bash
kv identity --propose            # lee el repositorio y propone; no escribe nada
kv identity --declare <id>       # escribe el que le pasen, y lo commitea
```

Son **excluyentes**, y es la misma forma que tiene el retiro con `--dry-run` y
`--approve-digest`: entre las dos hay una persona que lee la propuesta y **tipea**
el identificador. Un solo comando que propusiera y declarara de una eliminaría esa
confirmación sin que ninguna bandera lo delatara.

La propuesta sale del **remoto** si lo hay y del **nombre del directorio** si no.
Sin remoto y sin ningún commit se detiene: el nombre del directorio no es una
señal, es lo que se está reemplazando.

### Qué se niega a hacer, y por qué

| Situación | Resultado |
|---|---|
| declarar dos veces el mismo identificador | **no-op**: `IDENTITY_ALREADY_DECLARED` |
| declarar un **segundo** identificador para el mismo repositorio | **detiene**: un repositorio con dos identidades es la ambigüedad que el diseño prohíbe |
| declarar un identificador que **ya usa otro** repositorio | **detiene**: compartirían ruta dentro del vault |
| declarar uno distinto del derivado **con material ya archivado** | **detiene**: ese material quedaría en una ruta que ningún verbo vuelve a mirar |

El último es el que menos se ve venir. Si ya se archivó sin declarar identidad, el
material quedó bajo el derivado; declarar otro identificador lo **huerfana** —y
`retire` reportaría todos los flujos como no-a-salvo sin decir por qué—. La salida
es declarar el derivado, o mover ese directorio a mano antes de cambiar.

### Copiar y borrar resuelven el identificador de una sola forma

`archive`, `migrate` y `retire` lo piden al mismo sitio, con una **asimetría
deliberada**: los que copian caen al derivado si no hay identidad declarada
—copiar bajo un nombre heurístico es benigno—, y el que borra **no cae a nada**.
Destruir bajo una identidad que nadie declaró es destruir el flujo de otro
repositorio.

Que los tres la resolvieran por su cuenta es exactamente cómo se partieron antes:
`archive` escribía en una ruta y `retire` miraba en otra, y **ningún** flujo se
podía retirar nunca.

## `retire`: el verbo que destruye

Es el único verbo que borra, y su forma entera está gobernada por una asimetría:
copiar mal se repara borrando el vault y volviendo a copiar; **borrar mal no se
repara**.

### La secuencia, y por qué en ese orden

```
reclamar → verificar → autorizar → destruir
```

1. **Reclamar** — el flujo se renombra a un hermano reservado `.kv-retirando-<id>`.
2. **Verificar** — sobre el remanente, con la sonda de solo lectura.
3. **Autorizar** — se commitea el manifiesto en el vault. **Punto de no retorno.**
4. **Destruir** — archivo por archivo, directorios vacíos en postorden.

El orden natural sería verificar y después borrar, y deja una ventana: entre
comprobar y destruir, otro proceso puede escribir en el flujo. La salida clásica
es un lock, y acá está descartada —el lock transaccional del árbol de origen se
retiró con el aparato viejo, y volver a meterlo era volver a meter journal, dueño,
expiración y recuperación—. **La ventana se cierra por el orden**: tras el
renombrado ningún proceso que busque el flujo por su ruta lo alcanza.

El costo está asumido y se declara: un aborto ya no deja el origen "sin tocar"
sino **sin cambio neto** — mismo conjunto de archivos, mismos hashes, misma ruta.

### El estado durable son dos señales, y no hay journal

| Objetivo | Remanente | Manifiesto | Estado | Salida |
|---|---|---|---|---|
| no | no | no | nada ocurrió | nada que hacer |
| no | no | **sí** | terminal alcanzado | nada que hacer |
| no | **sí** | no | reclamo sin autorizar | **deshacer**: el flujo vuelve |
| no | **sí** | **sí** | destrucción autorizada | **terminar** |
| **sí** | no | no | sin empezar | **reclamar** |
| **sí** | \* | \* | objetivo recreado | **detener** |

La fase se **deriva del estado observable** en vez de leerse de un registro que
puede contradecir al árbol. Las tres filas que detienen —objetivo recreado,
colisión de nombres y varios remanentes del mismo flujo— no son fallos de la
secuencia: son estados que la secuencia **no puede producir**, así que su causa es
externa y adivinarla sería destruir sobre una hipótesis.

**La ruta original recreada tiene precedencia sobre todo lo demás.** Si el flujo
reapareció en su sitio mientras el remanente sigue ahí, el original no se toca
nunca y el estado del remanente viaja como detalle, no como un segundo estado en
competencia.

### El manifiesto, y por qué su commit cumple tres papeles

Vive en `<vault>/.kv/retiros/<repo-id>/<flow-id>.json`, versionado. Su commit es a
la vez **autorización durable**, **autoridad del conjunto en el reintento** y
**registro de que el origen fue retirado**. Un solo artefacto en vez de tres
marcas que sincronizar.

Que sea la autoridad importa en el reintento: enumerar lo que quedó en disco daría
el remanente, no el conjunto que alguien aprobó. Lo que queda tiene que ser un
**subconjunto exacto** del manifiesto —mismos hashes, **sin sobrantes**—; ante un
archivo nuevo o modificado el comando falla **sin tocar nada**.

Su digest cubre siete cosas: identidad, alcance, inventario con hashes,
clasificación, directorios, bytes y el commit del vault. Un digest sobre conteos
agregados no distingue dos árboles distintos del mismo tamaño.

### Dos digests, con dos alcances

- **el del lote** cubre el conjunto de flujos y las precondiciones globales: si
  cambió, no se toca nada, porque lo aprobado era otra cosa;
- **el de cada flujo** cubre su propio árbol: si cambió, falla ese flujo y el lote
  sigue.

Uno solo obligaría a elegir entre abortar todo por un archivo ajeno o no detectar
un cambio de alcance.

### El gate humano no se automatiza

`--dry-run` recorre el camino completo **sin una escritura**, clasifica cada
entrada entre a salvo y sin copia, y emite el digest. Sale con código **cero
siempre**, incluso al encontrar discrepancias: un ensayo que falla por lo que
encontró es un ensayo que no se puede leer.

El retiro real **exige** ese digest por argumento y lo compara contra lo que vuelve
a escanear. No lo recalcula —eso sería aprobarse solo—, y `--dry-run` y
`--approve-digest` son **excluyentes**: correr el ensayo y pasar su digest en la
misma invocación es la forma exacta que tiene un guion de eliminar el gate.

### `omitidos`: el inventario omitido del ensayo dirigido

Con `--dry-run` **y** `--from <ruta-del-flujo>` a la vez —y sólo entonces— el
informe agrega a la entrada de ese flujo:

```
omitidos: Array<{ path: string, size: number, sha256: string }> | null
```

`<ruta-del-flujo>` es el hijo directo `<raíz>/<flujo>` que recibió `--root`. Un
lote sin `--from` —aunque enumere un único flujo— y el retiro real, con o sin
`--from`, nunca llevan este campo: es exclusivo del ensayo dirigido.

Con manifiesto disponible, el array es el **complemento exacto** de la
selección de `archive`: recorre `manifiesto.inventario` en su mismo orden y
conserva las entradas cuyo `path` no satisface `isCopiable(path)` —lo que no es
un `.md` de raíz—, proyectando sólo `path`, `size` y `sha256`. Cada `path` pasa
por `assertContainedPath` antes de viajar: una ruta que no se puede reportar
hace fallar el comando entero, nunca produce un informe engañoso.

Sin manifiesto —una medición fallida— `omitidos` vale `null`, nunca `[]`: un
conjunto vacío diría "no quedó nada afuera" sobre un flujo que no se llegó a
medir. `null` no reemplaza ni borra `causa` ni `error`, que viajan intactos
junto a él; la interpretación es **fail-closed**: ningún consumidor puede tratar
`omitidos: null` como "nada que rescatar" ni seguir adelante sin la medición.

### La identidad del repositorio se declara, no se deriva

La ruta dentro del vault sale de un identificador **declarado**, guardado en
`<vault>/.kv/identidades.tsv` junto a sus señales de respaldo —remoto, commit raíz
y ruta observada—. La sede es el vault y no la configuración del proyecto, que es
local y no viaja entre clones: el mismo repositorio tendría otra identidad en cada
máquina.

Con N repositorios en N máquinas, dos clones que se llamen igual dejan de ser un
caso teórico, y derivar el nombre del directorio los mandaría al mismo sitio del
vault. Una resolución ambigua —ninguna identidad compatible, o más de una—
**detiene**; nunca se elige por proximidad.

### La matriz de rutas de un objetivo destructivo

La de arriba vale para copiar. Para borrar, el flujo y su raíz llegan por
**parámetros distintos** —`--from` y `--root`—, porque derivar la raíz del propio
objetivo vuelve tautológica la condición de hijo directo: siempre se cumple, nunca
detecta nada, y el borrado queda autorizado sobre cualquier ruta del disco.

Además el objetivo no puede **contener un repositorio Git**, en sus tres formas:
`.git` como directorio (clon), `.git` como archivo (árbol de trabajo enlazado o
submódulo) y el repositorio desnudo (`HEAD` + `objects/` + `refs/`). Un error de
permisos durante esa búsqueda **detiene** en vez de leerse como ausencia: leerlo
como "no pude entrar, así que no hay nada" es cómo un borrado se come un
repositorio que no llegó a ver.

## El wrapper literal y su verificador

Ésta es la sede única de la **forma exacta** que usa el rescate textual del
procedimiento posterior a `archive` (`SKILL.md` → "Después de archivar: qué
hacer con lo que quedó afuera"): esa sección decide **cuándo** envolver un
archivo omitido y qué gates humanos lo rodean; acá vive **cómo** se ve el
documento y cómo se comprueba que no miente.

### El nombre del documento

`anexo-<sha256(UTF-8(ruta-relativa-original))>.md`, con el digest completo — 64
caracteres hexadecimales minúsculos. Antes de escribir el primer documento del
lote se comprueba que **todos** los nombres generados sean únicos entre sí;
cualquier colisión detiene el rescate sin escribir ninguno.

### La forma exacta del wrapper

**Toda fuente aprobada usa el mismo wrapper y el mismo verificador, Markdown
anidado incluido** — no hay un camino separado para `.md`. El documento
declara, en este orden y literales, antes del payload:

```
Source path (JSON): <JSON.stringify(ruta-relativa-original)>
Source format (JSON): <JSON.stringify(formato-de-origen)>
Source size: <tamaño en bytes, decimal>
Source SHA-256: <64 hexadecimales minúsculos>
<!-- kv-literal-content -->
```

`Source format` es lo único que distingue el origen: `text/markdown` para un
`.md` anidado, y el tipo que corresponda —por ejemplo `text/plain` o
`application/json`— para cualquier otro. El resto de la metadata, el marcador,
el cerco y el payload son idénticos en los dos casos.

El marcador estructural `<!-- kv-literal-content -->` ocupa la línea inmediata
posterior a las cuatro líneas de metadata. El verificador lo ubica por esa
frontera, no contando ocurrencias en el documento: la misma cadena puede
aparecer dentro de la ruta declarada o del payload sin volverlo irrescatable.
Inmediatamente después abre un cerco de backticks con info string `text`,
repetidos `max(3, mayor-corrida-de-backticks-del-origen + 1)` veces: la longitud
se **adapta** al contenido para que ninguna corrida de backticks *dentro* del
origen pueda cerrarlo antes de tiempo. El payload arranca en el byte siguiente
al salto de línea que abre el cerco, ocupa exactamente `Source size` bytes tal
cual —sin transformar— y el cierre es literalmente `\n<cerco>\n`: ese salto de
línea previo al cierre **no** es parte del contenido extraído.

Ejemplo fiel y completo, listo para pegar (la corrida más larga de backticks del
origen es de tres, así que el cerco de este wrapper usa cuatro; el origen no
termina en salto de línea):

`````
Source path (JSON): "notas/ejemplo.txt"
Source format (JSON): "text/plain"
Source size: 36
Source SHA-256: 466e4ae11e6fd4164d53e89095f364f93ba493edb3bd91d3d44690186d440d53
<!-- kv-literal-content -->
````text
revisar ```bloque``` sin salto final
````
`````

### El verificador

Un comando completo, ejecutable tal cual —sin placeholders—, publicado acá y en
ningún otro lado. `$origen` y `$wrapper` son variables de shell con las rutas a
comparar; el quoting es POSIX válido, así que rutas con espacios no lo rompen:

```bash
node --input-type=module -e '
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

const [origenPath, wrapperPath] = process.argv.slice(1);
const origen = readFileSync(origenPath);
const wrapper = readFileSync(wrapperPath);

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

let texto;
try {
  texto = new TextDecoder("utf-8", { fatal: true }).decode(origen);
} catch {
  fail("el origen no es UTF-8 válido");
}
if (texto.includes("\0")) fail("el origen contiene NUL");

const marcador = Buffer.from("<!-- kv-literal-content -->", "utf8");
let finCabecera = 0;
for (let linea = 0; linea < 4; linea += 1) {
  const finLinea = wrapper.indexOf(0x0a, finCabecera);
  if (finLinea === -1) fail("metadata incompleta: faltan las cuatro líneas iniciales");
  finCabecera = finLinea + 1;
}

const cabecera = wrapper.subarray(0, finCabecera).toString("utf8");
const metaMatch = cabecera.match(
  /^Source path \(JSON\): (.+)\nSource format \(JSON\): (.+)\nSource size: (\d+)\nSource SHA-256: ([0-9a-f]{64})\n$/,
);
if (!metaMatch) fail("metadata inválida, incompleta o fuera de orden");
const [, pathJson, formatJson, sizeStr, sha256Declarado] = metaMatch;
let rutaDeclarada;
let formatoDeclarado;
try {
  rutaDeclarada = JSON.parse(pathJson);
  formatoDeclarado = JSON.parse(formatJson);
} catch {
  fail("Source path/format no son JSON válido");
}
if (typeof rutaDeclarada !== "string" || rutaDeclarada.length === 0) fail("Source path no es un string no vacío");
if (typeof formatoDeclarado !== "string" || formatoDeclarado.length === 0) fail("Source format no es un string no vacío");
const size = Number(sizeStr);

const idx = finCabecera;
if (!wrapper.subarray(idx, idx + marcador.length).equals(marcador)) {
  fail("marcador estructural ausente después de la metadata");
}

const corridas = texto.match(/`+/g) ?? [];
const maxCorrida = corridas.reduce((m, c) => Math.max(m, c.length), 0);
const cerco = "`".repeat(Math.max(3, maxCorrida + 1));

const despuesDelMarcador = wrapper.subarray(idx + marcador.length);
const apertura = Buffer.from(`\n${cerco}text\n`, "utf8");
if (!despuesDelMarcador.subarray(0, apertura.length).equals(apertura)) {
  fail("cerco de apertura ausente o de longitud incorrecta");
}

const payload = despuesDelMarcador.subarray(apertura.length, apertura.length + size);
if (payload.length !== size) fail("el wrapper quedó truncado antes del tamaño declarado");

const cierre = despuesDelMarcador.subarray(apertura.length + size);
const cierreEsperado = Buffer.from(`\n${cerco}\n`, "utf8");
if (!cierre.equals(cierreEsperado)) fail("el cierre del cerco no coincide con el patrón salto, cerco, salto");

if (!payload.equals(origen)) fail("el payload extraído no coincide byte a byte con el origen");

const sha256Real = createHash("sha256").update(origen).digest("hex");
if (sha256Real !== sha256Declarado) {
  fail(`SHA-256 declarado no coincide: esperado ${sha256Real}, declarado ${sha256Declarado}`);
}

console.log("wrapper fiel: tamaño, cerco y SHA-256 verificados");
' -- "$origen" "$wrapper"
```

Lee origen y wrapper como `Buffer`. Decodifica el origen con
`new TextDecoder('utf-8', { fatal: true })` —cualquier byte inválido lo
rechaza— y exige la ausencia de NUL. Lee exactamente cuatro líneas de metadata,
las valida en orden, parsea `Source path` y `Source format` como JSON y exige que
los dos den un string no vacío. Luego exige el marcador estructural en el offset
siguiente; no interpreta como estructura las apariciones de esa cadena dentro
de la metadata o del payload. Valida la longitud adaptativa del cerco, corta
desde el byte posterior a la apertura exactamente `Source size` bytes, exige
que el resto sea `\n<cerco>\n` exacto, compara el payload extraído contra el
origen con `Buffer.equals` y recalcula su SHA-256 contra el declarado. Toda
diferencia —metadata, marcador estructural, cerco, tamaño, bytes o hash— termina
con código de salida distinto de cero; el caso fiel sale **0** e imprime su
confirmación.

## Casos borde

- **Sin candidatos aprobados para rescate.** No se crea ni se archiva ningún
  anexo: se repite directamente el ensayo dirigido del original y el agente
  muestra igual el inventario completo de `omitidos`, con cada entrada rotulada
  `se destruirá sin rescate`, antes de pedir la aprobación del digest — ver
  `SKILL.md` → "4. Ofrecer el retiro del original, con el inventario completo a
  la vista".
- **`<flujo>-anexos` ya existe, sólo local.** No se pisa: se informa su estado y
  se pide decidir entre repararlo o usar otro identificador — ver `SKILL.md` →
  "2. Materializar lo aprobado en `<flujo>-anexos`".
- **`<flujo>-anexos` ya existe, archivado en el vault.** Se resuelve por
  `repoId` contra `<vault>/projects/<repoId>/sdd/<flujo>-anexos.md` y se pide un
  identificador canónico nuevo; una frontera ya archivada no se modifica — misma
  sede.
- **El ensayo dirigido del original da `EMPTY_SET`** —no el ensayo propio del
  anexo—. El retiro del anexo se permite sin declinación humana nueva, pero
  `EMPTY_SET` nunca autoriza el retiro del propio original — ver `SKILL.md` →
  "5. Retirar el anexo".
- **El original ya no existe cuando se evalúa el retiro del anexo.** Mismo
  efecto que `EMPTY_SET`: se permite sin declinación renovada — misma sede.
- **El original sigue presente, con cualquier otra causa.** El retiro del
  anexo exige una declinación humana renovada en la sesión actual; no se
  persiste entre corridas — misma sede.
- **Original y anexo coexisten.** El retiro por lote está prohibido: cada uno se
  retira con su propio `--from` y su propio digest, para acreditar el orden —
  misma sede.
- **El origen o el vault cambian entre el ensayo y la aprobación.** El digest ya
  no describe lo que se va a destruir y el ensayo se repite antes de pedir
  aprobación de nuevo — ver `SKILL.md` → "4. Ofrecer el retiro del original, con
  el inventario completo a la vista".
- **Dos rutas aprobadas producen el mismo nombre de anexo.** Se detecta antes de
  escribir el primer documento y el rescate se detiene sin escribir ninguno —
  ver "El nombre del documento" arriba.
- **Un wrapper infiel** —metadata alterada, cerco corto, payload truncado o
  bytes distintos del origen— hace que el verificador salga con código distinto
  de cero, y el rescate de esa entrada no se da por completo.
- **La ruta o el origen contienen `<!-- kv-literal-content -->`.** Es contenido
  literal: sólo la aparición situada inmediatamente después de las cuatro líneas
  de metadata funciona como marcador estructural, y las demás no afectan la
  extracción ni la comprobación byte a byte.
- **Un fallo a mitad de la materialización, verificación o archivado del
  anexo.** El original queda intacto y sin ofrecerse para retiro; los archivos
  parciales y la causa exacta se informan, y ningún residuo se limpia
  automáticamente — ver `SKILL.md` → "2. Materializar lo aprobado en
  `<flujo>-anexos`".

- **Un flujo sin ningún `.md` en su raíz** se archiva igual: su frontera queda
  vacía y su nodo no lleva enlaces. Git no versiona directorios vacíos, así que en
  el vault ese flujo existe como nodo y como entrada del índice. **Para `retire`
  ese mismo flujo se rechaza** con `EMPTY_SET`: comparar dos conjuntos vacíos pasa
  de forma vacua, y retirarlo destruiría el 100 % de un flujo que no tiene un byte
  suyo a salvo. Medido en un árbol real: 1 de 50.
- **Un archivo suelto en la raíz de archivados no es un flujo.** `migrate`
  enumera **directorios**. Medido en un árbol real: 51 entradas, 50 directorios.
- **Un `index.md` dentro de un flujo** se copia como cualquier documento y no
  colisiona: los índices generados viven en niveles superiores.
- **El vault sucio por cambios ajenos** frena el archivado antes de escribir. Los
  archivos del propio archivado en curso no cuentan como ajenos — si contaran, una
  corrida caída no se podría completar nunca.
- **Un staging huérfano** de una corrida muerta se barre antes de reintentar: la
  copia usa creación exclusiva, así que sin limpieza el reintento queda bloqueado.
- **La frontera de un flujo archivado no crece.** La verificación compara
  conjuntos exactos en las **dos** direcciones: un archivo de más en el destino es
  sobrante, y uno de menos hace fallar la comprobación. Así que agregar un `.md` a
  la raíz de un flujo ya archivado y volver a archivar devuelve `VERIFY_FAILED`
  nombrando el documento nuevo, en vez de republicar la frontera. Medido, no
  deducido. **Si un flujo gana documentos después de archivarse, van como flujo
  propio**: la frontera vieja queda intacta y el material nuevo obtiene su nodo y
  su entrada en el índice. Es la salida para el material de origen que vive en un
  subdirectorio —`insumos/`, por ejemplo— y que la selección deja afuera.
- **Abrir el vault en Obsidian lo ensucia, y eso frena el archivado.** Obsidian
  crea `.obsidian/` con su configuración, macOS deja `.DS_Store` al navegar las
  carpetas, y **hacer clic en un `[[enlace]]` no resuelto crea la nota vacía** en
  la raíz del vault. Cualquiera de las tres deja el árbol sucio con cambios
  ajenos, y el archivado frena antes de escribir para no llevárselos puestos. El
  remedio para las dos primeras ya viene puesto: **`ensureVaultRepo` siembra el
  `.gitignore` al crear el vault** con `.obsidian/` y `.DS_Store`, y lo commitea en
  el mismo acto —dejarlo suelto lo convertiría en un cambio ajeno permanente que
  bloquea el primer archivado—. Son dos patrones y ninguno más: en un almacén cuyo
  punto es la procedencia verificada, cada exclusión es un lugar donde algo puede
  desaparecer sin que nadie lo note. **Un vault anterior a la siembra, o uno con
  `.gitignore` propio, no se toca**: reponer patrones sobre una decisión ajena es
  peor que no sembrar nada, así que ahí el archivo se agrega a mano.
  La **tercera no se previene ignorándola**, y es la que sobrevive: la nota vacía
  es un `.md` legítimo que ningún patrón distingue de un documento real. Se borra,
  y conviene saber que **todo documento archivado que contenga un wikilink sin
  resolver es un botón que crea archivos**.

## Cómo correr los tests

```bash
node --test 'tests/skills/knowledge-vault/*.test.mjs'
```

Sin dependencias: `node:test` y `node:assert`. Los tests de Git usan repositorios
temporales reales, no mocks — lo que hay que verificar es cómo se comporta `git`,
y un mock afirma lo que uno ya creía.
