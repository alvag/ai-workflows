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
| `retire --root <raíz> --dry-run \| --approve-digest <hex>` | destruye el origen ya verificado | `DRY_RUN` · `BATCH_OK` · `BATCH_PARTIAL` · `BATCH_FAILED` |

`archive`, `migrate`, `index` y `retire` aceptan `--vault-root <ruta>` o `--config
<ruta>`; sin ninguna de las dos, la raíz sale de
`<raíz del repo>/.specify/config.yml`. Códigos de salida y enumerados completos en
`reference.md` → "Estado a código de salida"; el contrato de `retire`, en
`reference.md` → "`retire`: el verbo que destruye".

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
   tienen marca de `kv`), `sugerido` (el único, si hay uno solo) y `ajenos`.
   Sale **0 siempre**, incluso sin candidatos.
2. Presentale al usuario lo que encontró, con su evidencia —cuántos proyectos y
   flujos tiene cada vault—, y **esperá que elija**. Con `sugerido` no nulo,
   ofrecelo como recomendado; con la lista vacía, ofrecé crear uno.
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
en Obsidian **sin** notas no cuenta como ajeno: esa es la forma de un vault nuevo.

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
convierte en `pqtch-925` solo, y `archive` y `migrate` fallan antes de copiar nada.

La salida es **renombrar el directorio de origen** al nombre canónico y reintentar; el error te
ofrece el candidato cuando existe. En `migrate` hay un paso más, porque el TSV de resúmenes
referencia el nombre viejo: el dominio exacto, el porqué de no transformar y el procedimiento
completo de los dos verbos están en `reference.md` → "El nombre del directorio es el `flow-id`".

## Después de archivar: qué hacer con lo que quedó afuera

`archive` devuelve `counts: {included, omitted}`, y **`omitted` es el dato que casi
nadie mira**. Al archivar un flujo de este mismo repositorio dio `included: 9,
omitted: 43`: nueve documentos viajaron y cuarenta y tres archivos no.

Con `omitted: 0` no hay nada que hacer. Con `omitted > 0`, seguir estos pasos **en
este orden**, y no saltear al último:

1. **Medir qué quedó.** Los `.md` de subdirectorio son la clase que importa:
   informes de exploración, veredictos de revisión, material que alguien escribió.
   `find <flujo> -mindepth 2 -name '*.md'`.
2. **Si los hay, ofrecer rescatarlos** como un flujo hermano `<flujo>-anexos`, con
   las rutas aplanadas (`reports/explore.md` → `reports__explore.md`). Va como
   hermano y no como documento agregado porque **la frontera de un flujo archivado
   no crece**: re-archivar con un `.md` de más devuelve `VERIFY_FAILED`.
3. **Recién entonces ofrecer el retiro**, y **siempre con el desglose a la vista**:
   `retire --root <raíz> --dry-run` separa lo que está a salvo de lo que se
   destruiría sin copia. Ofrecer sin ese número es pedirle a una persona que
   apruebe un borrado a ciegas.

> **Por qué el orden importa, medido.** Ofrecer el retiro apenas termina la copia es
> donde la inercia del "sí" hace daño: el flujo del ejemplo tenía 3,1 MB sin copia
> —los informes de los dos workers y los veredictos de revisión— y retirarlo ahí
> habría destruido la respuesta conservando la pregunta. En un rollout real la
> clasificación a ojo de qué material era prescindible **falló cuatro veces
> seguidas**; lo que la corrigió no fue mejor criterio sino medir antes de ofrecer.

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
