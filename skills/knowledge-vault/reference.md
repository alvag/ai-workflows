# knowledge-vault — referencia

Detalle que `SKILL.md` no necesita en cada corrida. Se lee cuando hace falta el
contrato exacto de un verbo, un código de salida, o entender por qué algo falla.

## Matriz por verbo

| Verbo | Obligatorias | Opcionales | Raíz del vault |
|---|---|---|---|
| `archive` | `--from <dir>` · `--summary <línea>` | — | `--vault-root` \| `--config` \| default |
| `migrate` | `--from <dir>` · `--summaries <tsv>` | `--dry-run` | `--vault-root` \| `--config` \| default |
| `index` | — | — | `--vault-root` \| `--config` \| default |
| `config` | `--config <ruta>` | `--set-root <ruta>` | la declara él mismo |

`--config` y `--vault-root` son **excluyentes**: la raíz del vault se declara de
una sola forma, y "cuál manda" no tiene una respuesta que valga la pena inventar.

Todo entra por banderas largas. Un argumento suelto es `USAGE`.

## Estado a código de salida

| Código | Estados | Qué significa |
|---|---|---|
| 0 | `ARCHIVED` · `ALREADY_ARCHIVED` · `INDEX_OK` · `BATCH_OK` · `DRY_RUN` · `VAULT_CONFIGURED` · `VAULT_SET` | éxito |
| 1 | `INTERNAL_ERROR` · `BATCH_PARTIAL` · `BATCH_FAILED` | fallo de la corrida o del lote |
| 2 | `USAGE` | la invocación es inválida |
| 3 | `CONFIG_INVALID` | el config existe y no se puede leer sin adivinar |
| 4 | `PRECONDITION_NOT_MET` | el vault está sucio, anidado, o el nombre del flujo es reservado |
| 5 | `NO_VAULT` | no se declaró la raíz, o el config no la trae |
| 8 | `SOURCE_UNAVAILABLE` | el origen no se puede leer |
| 9 | `VERIFY_FAILED` · `COPY_FAILED` · `PUBLISH_FAILED` | el destino no verifica, o la publicación falló |

**Un lote incompleto no sale 0.** Migrar 49 de 50 deja un vault que ningún
criterio distingue de uno completo: no hay manifiesto que enumere lo que debía
entrar. Quien lo consulte va a concluir que el flujo que falta nunca existió.

La tabla se redujo de dieciocho códigos a ocho al retirarse `restore`, `doctor`,
`inventory` y el aparato de retiro. Los códigos que **quedaron conservan su
número**, para no reescribirle el significado a un `9` que ya quería decir "el
destino no verifica".

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

## El layout, completo

```
<vault>/index.md                              índice raíz, agrega TODOS los flujos
<vault>/log.md                                una línea por archivado
<vault>/projects/index.md                     índice
<vault>/projects/<repo>/index.md              índice
<vault>/projects/<repo>/sdd/index.md          índice
<vault>/projects/<repo>/sdd/<flujo>.md        el NODO, hermano del directorio
<vault>/projects/<repo>/sdd/<flujo>/          FRONTERA VERIFICADA
<vault>/projects/<repo>/sdd/<flujo>/*.md      copiados, byte-idénticos
```

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

## Casos borde

- **Un flujo sin ningún `.md` en su raíz** se archiva igual: su frontera queda
  vacía y su nodo no lleva enlaces. Git no versiona directorios vacíos, así que en
  el vault ese flujo existe como nodo y como entrada del índice.
- **Un archivo suelto en la raíz de archivados no es un flujo.** `migrate`
  enumera **directorios**. Medido en un árbol real: 51 entradas, 50 directorios.
- **Un `index.md` dentro de un flujo** se copia como cualquier documento y no
  colisiona: los índices generados viven en niveles superiores.
- **El vault sucio por cambios ajenos** frena el archivado antes de escribir. Los
  archivos del propio archivado en curso no cuentan como ajenos — si contaran, una
  corrida caída no se podría completar nunca.
- **Un staging huérfano** de una corrida muerta se barre antes de reintentar: la
  copia usa creación exclusiva, así que sin limpieza el reintento queda bloqueado.

## Cómo correr los tests

```bash
node --test 'tests/skills/knowledge-vault/*.test.mjs'
```

Sin dependencias: `node:test` y `node:assert`. Los tests de Git usan repositorios
temporales reales, no mocks — lo que hay que verificar es cómo se comporta `git`,
y un mock afirma lo que uno ya creía.
