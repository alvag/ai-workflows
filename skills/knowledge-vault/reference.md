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

El parser **no es YAML y no tiene escapes**. Cuatro clases de valor no vuelven
idénticas, y por eso se **rechazan** en vez de escaparse — escapar sin desescapar
produce un archivo que se ve bien y miente:

| Se emite | Se lee |
|---|---|
| `"envuelto"` | `envuelto` |
| `con # numeral` | `con` |
| `#empieza` | vacío |
| `  con espacios  ` | `con espacios` |

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

## Casos borde

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
