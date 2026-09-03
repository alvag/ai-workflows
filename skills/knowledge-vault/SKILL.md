---
name: knowledge-vault
description: >-
  Rescata el conocimiento de los flujos SDD a un vault de Markdown verificado
  por hash, versionado en Git y navegable en Obsidian, con el CLI `kv` (Node,
  sin dependencias). Seis verbos —"archive", "migrate", "index", "config",
  "retire" e "identity"—, con el detalle de cada uno en `reference.md`. Usarla
  para archivar un documento o un flujo, guardar algo en el vault, sacar a la
  bóveda lo que se decidió en `.plans/archived/` y dejarlo consultable sin
  leerlo entero, para declarar la identidad del repositorio, y para retirar el
  origen ya copiado. La garantía: el verbo que copia no borra; el que borra
  exige verificación previa byte a byte y un digest aprobado a mano. NO es un
  gestor de notas ni un indexador semántico: no resume, no enlaza por
  contenido ni invoca ningún modelo. No invocarla espontáneamente: solo ante
  pedido explícito del usuario.
---

# knowledge-vault — el conocimiento de los flujos, consultable

Los flujos SDD terminados van a `.plans/archived/`, que es **local, untracked e
invisible**. Lo que decidieron, por qué, qué descartaron y qué midieron muere en
un directorio que ninguna herramienta indexa y ningún agente lee.

Esta skill saca ese conocimiento a un **vault de Markdown**: verificado por hash,
versionado en Git, navegable en Obsidian y consultable por un agente sin cargarlo
entero.

## La regla que ordena todo

> **El verbo que copia no borra; el que borra exige verificación previa.** El
> archivado no toca el origen —ni con éxito, ni con error, ni con el proceso
> muerto a mitad de camino—, y el retiro sólo destruye lo que ya verificó byte a
> byte contra el vault.

Lo que se perdió al escribirlo así conviene decirlo, porque no es menor. Antes la
garantía se comprobaba por **ausencia**: no existía en la skill ningún componente
capaz de borrar fuera del vault, y eso se leía barriendo el código. Ahora se
comprueba por **enumeración**: un solo módulo puede destruir bajo el origen, la
guarda lo nombra, y cualquier otro que adquiera esa capacidad la pone roja. Es
una propiedad más fuerte de lo que suena —prohibir todo borrado volvería ilegal
la limpieza legítima dentro del vault— pero ya no se sigue de que el código no
exista.

Sigue siendo lo que la vuelve **segura de correr**: ante cualquier fallo anterior
al punto de no retorno, el origen sigue ahí y el vault se descarta y se rehace.

## Los seis verbos

| Verbo | Qué hace | Estados |
|---|---|---|
| `archive --from <flujo> --summary <línea>` | archiva un flujo | `ARCHIVED` · `ALREADY_ARCHIVED` |
| `migrate --from <raíz> --summaries <tsv>` | archiva todos los flujos de un directorio | `BATCH_OK` (0) · `BATCH_PARTIAL` (1) · `BATCH_FAILED` (1) · `DRY_RUN` |
| `index` | regenera los índices | `INDEX_OK` |
| `config --config <ruta> [--set-root <ruta>]` | lee o escribe `path_vault` | `VAULT_CONFIGURED` · `VAULT_SET` |
| `config --discover [--search-root <ruta>]` | qué vaults hay en el disco, clasificados | `VAULTS_DISCOVERED` |
| `identity --propose \| --declare <id>` | declara la identidad del repositorio en el vault | `IDENTITY_PROPOSED` · `IDENTITY_DECLARED` · `IDENTITY_ALREADY_DECLARED` |
| `retire --root <raíz> [--from <ruta-del-flujo>] --dry-run \| --approve-digest <hex>` | destruye el origen ya verificado | `DRY_RUN` · `BATCH_OK` · `BATCH_PARTIAL` · `BATCH_FAILED` |

`archive`, `migrate`, `index` y `retire` aceptan `--vault-root <ruta>` o `--config
<ruta>`; sin ninguna de las dos, la raíz sale de
`<raíz del repo>/.specify/config.yml`. Códigos de salida y enumerados completos en
`reference.md` → "Estado a código de salida"; el contrato de `retire`, en
`reference.md` → "`retire`: el verbo que destruye".

`--from <ruta-del-flujo>` dirige el ensayo a un único flujo, hijo directo de
`<raíz>` (`<raíz>/<flujo>`). Sólo en esa combinación —`--dry-run` **y** `--from`
juntos— el informe trae `omitidos`: el inventario completo de lo que `archive`
dejaría afuera, con ruta, tamaño y SHA-256. El lote sin `--from` y el retiro real
no lo llevan; la forma exacta está en `reference.md` → "`retire`: el verbo que
destruye".

```bash
node <skills>/knowledge-vault/scripts/kv.mjs config --config .specify/config.yml --set-root ~/vaults/dev-memory
node <skills>/knowledge-vault/scripts/kv.mjs archive --from .plans/archived/abc-1 --summary "De qué se trató el flujo."
```

## El primer uso en un proyecto: qué hacer ante `NO_VAULT`

`kv` **no tiene registro global**: cada proyecto declara su vault en su propio
`.specify/config.yml`, bajo una sección `knowledge-vault:` que nadie más toca. Es
lo que permite que dos proyectos apunten a vaults distintos, y el precio es que un
proyecto nuevo no declara ninguno y `archive` sale con `NO_VAULT` (código 5).

Ante ese estado, **no inventes una ruta ni la pidas a ciegas**:

1. Corré `config --discover`. Busca desde el home y devuelve `vaults` (los que
   tienen marca de `kv`), `nuevos` (directorios con la forma de un vault nuevo:
   `.obsidian/` y ninguna nota, sin marca de `kv` todavía), `sugerido` (el único
   vault, si hay uno solo) y `ajenos`. Sale **0 siempre**, incluso sin candidatos.
2. Presentale al usuario lo que encontró y **esperá que elija**. Los `vaults` van
   con su evidencia —cuántos proyectos y flujos tiene cada uno—; los `nuevos`, como
   lo que son: destinos a estrenar, sin nada adentro todavía. Con `sugerido` no
   nulo, ofrecelo como recomendado. Con las dos listas vacías, ofrecé crear uno.
   **Antes de cerrar la elección, preguntá si el vault que busca está en la lista.**
   El descubrimiento tiene fronteras deliberadas y no es exhaustivo: poda los
   nombres ocultos, `node_modules`, `Library` y `Applications`; baja **tres
   niveles** y no más; y arranca del home, o de donde apunte `--search-root`. Un
   vault fuera de eso existe y no aparece, y la salida no tiene forma de insinuarlo.
3. Persistí la elección con `config --set-root`. Inserta **por líneas**: no
   reescribe el resto del archivo ni le pierde los comentarios.
4. **Ofrecé dejarlo escrito para los agentes que vengan.** Un vault lleno de
   conocimiento no sirve de nada si ningún agente sabe que existe: esta skill no
   se auto-invoca y **no tiene verbo de búsqueda**, así que sin una instrucción
   persistida nadie lo va a consultar. El bloque listo para copiar y las sedes
   donde va están en `instrucciones-para-agentes.md`, hermano de este archivo. Se
   ofrece **una sola vez** —si la sede ya lo tiene, no se repite— y se **agrega**,
   nunca reescribiendo el archivo del usuario.

**Los `ajenos` se informan y no se ofrecen.** Son directorios con `.obsidian/` y
documentos pero sin marca de `kv`: el vault de notas de alguien. Apuntar `archive`
ahí lo convertiría en un vault de `kv`, y `ensureVaultRepo` le haría `git init`
antes de que ninguna otra guarda mire — por eso `assertRootUsable` los rechaza con
`VAULT_ROOT_UNAVAILABLE` en vez de advertir y seguir. Un directorio recién abierto
en Obsidian **sin** notas no cuenta como ajeno: esa es la forma de un vault nuevo,
y por eso **se ofrece** en `nuevos` en vez de quedar invisible — que es justo el
candidato que busca quien todavía no tiene ninguno.

La marca es `.obsidian/` **como directorio**, y el corte está ahí y no en "todo
directorio vacío" por una razón medida: sobre un home real hay diecisiete
directorios que clasifican vacío y ninguno es un vault —son carpetas internas de
otras aplicaciones—. Ofrecerlos a todos enterraría al candidato de verdad en vez de
revelarlo.

## Qué entra al vault

**Los archivos `.md` de la raíz del flujo, y nada más.** Ningún subdirectorio.

El corte es posicional y no de contenido, y esa es la decisión de diseño que más
cuesta entender hasta que se mide: **lo que el flujo decidió vive en la raíz de su
directorio; lo que usó para decidirlo vive en subdirectorios.** Las reglas
anteriores filtraban salida cruda de máquina —binarios, volcados— y por eso
dejaban pasar el andamiaje de proceso, que es texto legítimo: transcripciones de
revisión, árboles de prueba, veredictos. Medido sobre cincuenta flujos reales,
colaban un 65 % de material que nadie querría consultar.

Con el corte posicional: **277 documentos copiados, 10.726 omitidos.**

### El nombre del directorio también entra en el trato

El directorio del flujo tiene que llamarse con el **dominio canónico** del `flow-id` —minúsculas
ASCII, con `.`, `_` y `-` adentro—, porque ese nombre **es** el identificador con el que el flujo
queda archivado. Un nombre fuera del dominio **se rechaza sin transformarse**: `PQTCH-925` no se
convierte en `pqtch-925` solo. `archive` falla **antes de copiar nada**; `migrate` valida el
nombre **por flujo, dentro del lote**, así que los que ya pasaron quedan archivados y la corrida
termina en `BATCH_PARTIAL` con el resto en `fallidos` — reintentar tras renombrar es seguro,
porque los ya archivados devuelven `ALREADY_ARCHIVED`.

La salida es **renombrar el directorio de origen** al nombre canónico y reintentar; el error te
ofrece el candidato cuando existe. En `migrate` hay un paso más, porque el TSV de resúmenes
referencia el nombre viejo: el dominio exacto, el porqué de no transformar y el procedimiento
completo de los dos verbos están en `reference.md` → "El nombre del directorio es el `flow-id`".

## Después de archivar: qué hacer con lo que quedó afuera

`archive` devuelve `counts: {included, omitted}`, y **`omitted` es el dato que casi
nadie mira**. Al archivar un flujo de este mismo repositorio dio `included: 9,
omitted: 43`: nueve documentos viajaron y cuarenta y tres archivos no.

Con `omitted: 0` no hay nada que hacer. Con `omitted > 0` — o al ofrecer el retiro
de un flujo que ya se archivó bajo este mismo procedimiento — el rescate de lo
que quedó afuera es **obligatorio**, y las dos puertas convergen en el mismo
ensayo: `retire --root <raíz> --from <raíz>/<flujo> --dry-run`. Su campo
`omitidos` es la **única autoridad** de candidatos — nada de `find ... -name
'*.md'` ni ningún otro filtro por extensión o nombre. Este procedimiento gobierna
la skill; no afirma corregir la cadena llamadora de `sdd-flow`, que queda fuera
de alcance.

### Antes de empezar: la matriz de recuperación manda

Con `hayRemanente` o `hayManifiesto` en verdadero para el flujo, **no se inicia
un rescate nuevo**: se sigue la matriz de recuperación existente —"El estado
durable son dos señales" en `reference.md`—, que restaura el origen, termina una
destrucción ya autorizada, o se detiene ante un estado imposible.

Con un flujo fresco:

- Si el comando no entrega informe (código de salida distinto de cero antes de
  emitirlo), o la entrada del flujo trae `bytes: null` o `error`, `omitidos` vale
  `null` —nunca `[]` ni ausente—. Eso bloquea **tanto el rescate como el
  retiro**: se informa la medición fallida con su causa exacta y ahí se detiene,
  hasta que el ensayo pueda medir.
- `hayManifiesto: false` por sí solo no bloquea nada: sólo dice que el retiro
  todavía no empezó.
- Con inventario completo y `aSalvo: false` se puede evaluar `omitidos` —tiene
  sentido decidir el rescate— pero **no se ofrece el retiro** del original.
- Con causa `EMPTY_SET` se puede rescatar lo que `omitidos` liste, pero nunca se
  ofrece retirar el original.

### 1. Seleccionar qué rescatar

De cada entrada de `omitidos` el agente decide si es **texto rescatable**:
decodifica sus bytes con `TextDecoder` UTF-8 estricto —sin sustituciones— y
exige la ausencia de NUL. Sólo eso califica. Dentro de lo textual, una entrada
sólo se clasifica como **derivado recreable** —y se ofrece como descarte, no
como rescate— si el agente puede nombrar la fuente y el comando exactos que lo
reproducen.

El agente presenta la lista completa: los candidatos recomendados para
rescatar y los descartes propuestos, cada uno **con su motivo**. Nada se
rescata ni se descarta sin la aprobación nominal de esa lista, entrada por
entrada.

### 2. Materializar lo aprobado en `<flujo>-anexos`

Este paso corre **sólo si el paso 1 aprobó al menos un rescate**. Si no se
aprobó ninguno, no se crea ningún anexo y el procedimiento sigue directo en el
paso 4.

Cada aprobado se vuelca a un documento Markdown en la raíz de un flujo hermano
`<raíz>/<flujo>-anexos` —hijo directo de la misma `<raíz>` que recibió
`--root`, nunca dentro del original—: **la frontera de un flujo archivado no
crece**, y re-archivar con un documento de más devuelve `VERIFY_FAILED`.

El nombre de cada documento es determinista:
`anexo-<sha256(UTF-8(ruta-relativa-original))>.md`, con el digest completo de 64
hexadecimales minúsculos. Antes de escribir el primero se comprueba que el
conjunto completo de nombres generados sea único; cualquier colisión **detiene
sin escribir nada**.

**Toda fuente aprobada usa el mismo wrapper y el mismo verificador, Markdown
anidado incluido.** El documento envuelve los bytes UTF-8 literales del origen
con la metadata, el marcador y el cerco adaptativo que define `reference.md` →
"El wrapper literal y su verificador" —esa es su única sede—; `Source format`
declara `text/markdown` para un origen `.md` y el tipo que corresponda para
cualquier otro, sin que el resto del wrapper cambie entre los dos casos. Antes
de seguir se corre el verificador Node que ahí se publica: confirma que lo
extraído iguala tamaño y SHA-256 contra los valores que trajo `omitidos`.

Si `<flujo>-anexos` ya existe, no se lo toca a ciegas —una frontera ya archivada
no se modifica—: se resuelve `repoId` desde el informe del original y se
comprueba `<vault>/projects/<repoId>/sdd/<flujo>-anexos.md`. Si el anexo sólo
existe local, sin archivar, se informa su estado y se pide decidir si se repara
o se usa otro identificador; si ya está en el vault, se pide un identificador
canónico nuevo.

**El agente crea estos documentos a mano; el CLI no gana un verbo de
conversión.**

Cualquier fallo en esta materialización —creación, verificación de fidelidad o
archivado del anexo— **detiene el procedimiento**: el original queda intacto, no
se ofrece su retiro, se informan los archivos parciales y la causa exacta, y se
pide decidir entre repararlos, descartarlos con aprobación nominal, o reintentar
con otro identificador. Ningún residuo se borra automáticamente.

### 3. Archivar el anexo y exigirle su propio ensayo a salvo

Corre sólo cuando el paso 2 produjo al menos un documento. El agente archiva
`<flujo>-anexos` con un resumen derivado de la lista aprobada, y exige que
**su propio** ensayo dirigido —`retire --root <raíz> --from
<raíz>/<flujo>-anexos --dry-run`— devuelva `aSalvo: true`. Que `archive` haya
respondido `ARCHIVED` o `ALREADY_ARCHIVED` no alcanza: sólo ese ensayo autoriza
seguir.

### 4. Ofrecer el retiro del original, con el inventario completo a la vista

Si hubo al menos un rescate aprobado, recién con el anexo a salvo (paso 3) se
repite el ensayo original —los mismos `--root` y `--from` que va a usar el
retiro real—, se revalida tamaño y SHA-256 de cada rescate contra el origen
actual con el mismo verificador, y se rotula **cada** entrada de `omitidos`
como `rescatada en anexos` o `se destruirá sin rescate`.

Si no se aprobó ningún rescate, **no hace falta ningún anexo**: se repite
directamente el ensayo dirigido del original —los mismos `--root` y `--from`—
y se rotula **cada** entrada de `omitidos` como `se destruirá sin rescate`. La
exigencia de un anexo a salvo del paso 3 aplica sólo cuando hubo al menos un
rescate aprobado.

En los dos casos, cualquier cambio intermedio en el origen o en el vault
invalida el digest y obliga a repetir el ensayo antes de pedir su aprobación.
El inventario completo se muestra **siempre**, aunque no haya un solo
aprobado —se puede agrupar visualmente, nunca ocultar, truncar ni diferir el
detalle— antes de solicitar la aprobación del digest.

### 5. Retirar el anexo

Sólo corre si hubo al menos un rescate aprobado —sin anexo, no hay nada que
retirar acá—. El anexo se retira automáticamente cuando el original ya no
existe en la raíz, o cuando el ensayo dirigido **del original**
—`retire --root <raíz> --from <raíz>/<flujo> --dry-run`, no el propio ensayo
del anexo— declara causa `EMPTY_SET`. En cualquier otro estado del original
—presente con cualquier otra causa, incluido `aSalvo: true`— hace falta una
declinación humana **renovada en la sesión actual** —no se persiste— antes de
ofrecer el retiro del anexo.

Mientras original y anexo coexistan, el retiro **por lote está prohibido**: cada
uno se retira con su propio `--from` y su propio digest, para acreditar que el
orden se respetó. Ante cualquier fallo del retiro no se borra nada adicional:
si el original existe se conserva; se informan los residuos y la causa exacta,
y se pide una decisión nominal.

**El agente ofrece; el CLI nunca pregunta.** `kv` escribe JSON y sale con un código:
no hay TTY garantizado y un lote de cincuenta flujos quedaría preguntando cincuenta
veces. La conversación vive acá, y el borrado sigue exigiendo sus tres cerrojos:
ensayo, digest aprobado por una persona, y `--approve-digest` con ese digest exacto.

## El resumen lo provee quien llama

`--summary` es obligatorio y **ningún módulo lo infiere**. Un resumen derivado
mecánicamente repetiría el título, y entonces el índice no agregaría nada sobre
la ruta —que es exactamente lo que el índice existe para evitar—. El título sí se
deriva: del encabezado `# ` del documento principal, y si no hay, del nombre del
directorio.

## El layout

```
<vault>/index.md                          índice raíz: los N flujos, con título, ruta y resumen
<vault>/log.md                            una línea por archivado
<vault>/projects/<repo>/sdd/<flujo>.md    el NODO: ocho campos de metadatos, resumen y enlaces
<vault>/projects/<repo>/sdd/<flujo>/      FRONTERA VERIFICADA: exactamente los documentos copiados
```

Lo generado —el nodo y los índices— vive **fuera** de la frontera. No es una
preferencia de orden: la verificación compara conjuntos exactos y reporta
sobrantes, así que un nodo adentro haría fallar cada rearchivado.

## Red flags — detente y reconsidera

| Racionalización | Realidad |
|---|---|
| "El flujo está a medias, mejor no archivarlo" | Ningún verbo **evalúa estado**, tampoco el que retira. `status` vive en `plan.md`, que es opcional; lo que autoriza un retiro es que el contenido copiable esté a salvo y verifique, no en qué fase quedó el flujo. |
| "Le genero el resumen desde el título" | Repetiría el título y dejaría al índice sin nada que agregar. El resumen se escribe leyendo el flujo. |
| "Migré 49 de 50, ya está" | Un lote incompleto sale distinto de cero. Sin manifiesto, un vault al que le falta un flujo es indistinguible de uno completo. |
| "El índice quedó raro, lo edito a mano" | Es un derivado: `kv index` lo regenera. Editarlo lo pierde en la próxima corrida. |
| "Ya que está copiado, borro el original" | El retiro es un **verbo aparte** que exige la verificación previa y un digest aprobado a mano. No es un efecto secundario de archivar, y ningún camino encadena el ensayo con el borrado real. |

## Referencias internas

- `reference.md` — matriz por verbo, estados y códigos de salida, el layout
  completo, la capa de configuración, casos borde y cómo correr los tests.
- `instrucciones-para-agentes.md` — el bloque que se persiste en la sede de
  instrucciones del usuario para que un agente fresco sepa que el vault existe.
  Se lee **una sola vez**: al configurar el primer vault.
- `README.md` — qué es, cuándo usarla e instalación.
