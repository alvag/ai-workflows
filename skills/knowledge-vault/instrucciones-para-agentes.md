# Instrucciones para agentes — el bloque a persistir

**Qué es esto.** Un vault lleno de conocimiento no sirve de nada si ningún agente sabe que existe.
Este archivo tiene el bloque que se copia a la sede de instrucciones del usuario cuando decide usar
un vault, para que un agente fresco —en este proyecto o en cualquier otro— sepa que puede
consultarlo.

**Por qué existe como archivo y no inline en el `SKILL.md`.** Es contenido para **copiar**, no
instrucciones para **ejecutar**, y se lee una sola vez: cuando alguien configura su primer vault.
Cargarlo en cada corrida sería desperdiciar contexto. Mismo criterio que `config-ejemplo.md` en
`sdd-flow`.

## Cuándo se ofrece

Después de un `config --set-root` exitoso —el usuario acaba de declarar su vault—, y **una sola vez**:
si la sede ya contiene el bloque, no se vuelve a ofrecer.

## Dónde va

La sede depende de qué alcance quiera el usuario, y conviene ofrecerle las dos opciones en vez de
elegir por él:

| Sede | Alcance | Cuándo conviene |
|---|---|---|
| `~/.claude/CLAUDE.md` y `~/.codex/AGENTS.md` | global, todos los proyectos | el vault es transversal, que es el caso normal: **son dos, una por familia**, y escribir en una sola deja ciega a la otra |
| `CLAUDE.md` / `AGENTS.md` del repositorio | sólo ese proyecto | el vault es de un proyecto en particular, o el usuario no quiere tocar su config global |

**Se agrega, nunca se reescribe el archivo.** El bloque va delimitado por sus marcas de comentario,
que es lo que permite actualizarlo o retirarlo después sin tocar el resto. Si el archivo no existe, se
crea con el bloque solo.

## El bloque

Copiar entre las marcas, inclusive. **Ajustar sólo la ruta del CLI** si la skill está instalada en
otro lado; el resto es literal.

```markdown
<!-- knowledge-vault -->
## Vault de conocimiento (knowledge-vault)

Hay un **vault de Markdown** con lo que decidieron los flujos SDD ya terminados: un documento
por artefacto (`spec.md`, `plan.md`, `handoff.md`, veredictos de revisión, informes de
exploración), con frontmatter que declara `flow`, `branch`, `date`, `state` y un `summary`.
Algunos de esos flujos **ya no existen en disco**: su origen se retiró y el vault es la única
copia.

**Consultalo ante estos disparadores, no en cada tarea:**
- "¿por qué se decidió X?", "¿de dónde salió esta regla?", "¿qué alternativas se descartaron?"
- antes de rediseñar algo que huele a ya resuelto, o de repetir una investigación
- cuando un comentario o una guarda del código citan un motivo que no está escrito ahí

**No** lo consultes para tareas de código corriente: el fuente y el historial de Git alcanzan.

### Cuál vault, cuando haya más de uno

1. **El config del proyecto manda.** `.specify/config.yml` → `knowledge-vault.path_vault`. Si
   está declarado, ese es el vault de este proyecto y no hay nada que resolver.
2. **Si no está**, descubrí los que haya con el CLI de la skill instalada
   (`~/.claude/skills/knowledge-vault/scripts/kv.mjs`, o el mismo bajo `~/.agents/skills/`):
   `node <ruta>/scripts/kv.mjs config --discover`. Devuelve cada vault con los proyectos que
   contiene; elegí el que contenga este repositorio. Si la skill no está instalada, buscá a mano
   un directorio con `.kv/` o con `index.md` junto a `projects/`.
3. **Ante ambigüedad** —dos vaults con un proyecto del mismo nombre—, no adivines por nombre:
   cotejá `<vault>/.kv/identidades.tsv` (columnas `repoId`, `remoto`, `commitRaiz`,
   `rutaObservada`) contra `git remote get-url origin` y
   `git rev-list --max-parents=0 HEAD`. El commit raíz es identidad; el nombre del directorio no.

### Cómo buscar

Con `grep`/`rg` sobre `<vault>/projects/<repo>/`. **La skill no tiene verbo de búsqueda** —sus
seis verbos escriben o resuelven configuración— y tampoco se auto-invoca. Cada flujo tiene su
nodo `sdd/<flujo>.md` con el frontmatter y el resumen; los documentos viven en `sdd/<flujo>/`.

**Si `projects/<repo>/` no existe, este proyecto no está en ningún vault. Eso es normal y no es
un problema que reportar**: seguí con la tarea sin mencionarlo.
<!-- knowledge-vault -->
```

## Lo que el bloque resuelve, y por qué está redactado así

**Condicional, no imperativo.** Un "siempre consultá el vault" produce búsquedas inútiles en cada
tarea. Los disparadores son preguntas por el *porqué* de algo, no por el *qué*.

**Degrada en silencio.** La última línea existe porque un vault nuevo tiene un solo proyecto: en
cualquier otro repositorio el directorio no está, y sin esa línea el agente reporta un hallazgo
negativo en cada sesión.

**Nombra las tres formas de resolver cuál vault.** La primera es autoritativa y cierra el caso; las
otras dos existen para el proyecto que todavía no archivó nada. La tercera advierte que el nombre del
directorio no es identidad, que es la misma razón por la que el registro de identidades existe.
