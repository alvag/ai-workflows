# knowledge-vault

Saca el conocimiento de los flujos SDD terminados de `.plans/archived/` —que es
local, untracked e invisible— a un **vault de Markdown** verificado por hash,
versionado en Git y navegable en Obsidian.

## El problema

Un flujo SDD terminado deja en disco lo que se decidió, por qué, qué se descartó
y qué se midió. Todo eso queda en un directorio que ninguna herramienta indexa y
ningún agente lee.

## Qué hace

- **Copia** once formatos documentales y de script desde la raíz y desde tres
  subdirectorios explícitos, verificando cada byte por hash.
- **Escribe un nodo** por flujo con ocho campos de metadatos, un resumen de una
  línea y un enlace por documento.
- **Genera índices** regenerables que dejan ubicar cualquier flujo sin abrir un
  solo documento.
- **Commitea** el vault, un commit por flujo.

## Subdirectorios opt-in

En la raíz entran `.md`, `.sh`, `.js`, `.mjs`, `.py`, `.ts`, `.ps1`, `.json`,
`.yml`, `.txt` y `.jsonl`, sin distinguir mayúsculas. La misma lista se aplica
recursivamente sólo bajo `evidencia/`, `runs/` y `decisiones/`, con esos nombres
exactos. PDF y cualquier otro formato quedan fuera. El selector usa la ubicación
y el sufijo; no inspecciona contenido ni tamaño.

La regla sólo crea fronteras nuevas. Un flujo ya archivado conserva su conjunto
histórico: rearchivarlo con archivos que ahora serían elegibles devuelve
`VERIFY_FAILED`, y `migrate` lo deja sin cambios dentro de `BATCH_PARTIAL`. No hay
backfill automático.

## Qué NO hace

**El verbo que copia no borra.** `archive` y `migrate` dejan el origen
exactamente como estaba, ante el éxito y ante cualquier fallo; es lo que vuelve
seguro correrlos, porque el vault se descarta y se rehace.

**El que borra exige verificación previa.** `retire` es un verbo aparte: sólo
destruye lo que ya verificó byte a byte contra el vault, y sólo con un digest que
una persona aprobó sobre un ensayo medido. La garantía dejó de comprobarse por
ausencia de código y pasa a comprobarse enumerando quién puede destruir.

Tampoco resume, enlaza por contenido ni invoca ningún modelo. El resumen lo
escribe quien archiva.

## Cuándo usarla

- Para rescatar flujos ya acumulados en `.plans/archived/`.
- Para archivar un flujo recién cerrado, a mano.
- Para consultar, desde un agente o desde Obsidian, qué se decidió y por qué.

**Cuándo no:** si buscás un gestor de notas, un indexador semántico o un buscador
por embeddings, esta no es la herramienta.

## Instalación

Copie `skills/knowledge-vault/` a la sede de skills del operador. El CLI es
Node sin dependencias; no hay build ni instalación de paquetes. Las copias ya
instaladas requieren reinstalación manual para recibir este selector. Si una
frontera nueva ya fue publicada, el rollback seguro es detener `archive` y
`retire` y reinstalar completa la versión nueva; volver al selector anterior
haría incompatibles esos flujos. No mezcle scripts y documentación de versiones
distintas.

## Uso

```bash
KV=~/.claude/skills/knowledge-vault/scripts/kv.mjs

# una vez por proyecto: dónde vive su vault
node $KV config --config .specify/config.yml --set-root ~/vaults/dev-memory

# un flujo
node $KV archive --from .plans/archived/abc-1 --summary "De qué se trató el flujo."

# todos los de un directorio, con un TSV de <flujo><tab><resumen>
node $KV migrate --from .plans/archived --summaries resumenes.tsv --dry-run
node $KV migrate --from .plans/archived --summaries resumenes.tsv

# regenerar los índices
node $KV index
```

Como el config es **por proyecto**, cada repositorio archiva en su propio vault
sin ninguna configuración global.

## Consultar el vault

El índice raíz lista todos los flujos con título, ruta y resumen, así que ubicar
uno no exige abrir nada. Para buscar dentro:

```bash
rg -i "cross-review" ~/vaults/dev-memory
```

En Obsidian: abrilo como bóveda, sin plugins de comunidad. Los enlaces resuelven
y el grafo muestra cada nodo de flujo unido a sus documentos.

## Detalle

- `SKILL.md` — lo que el agente lee al activarla.
- `reference.md` — matriz por verbo, códigos de salida, layout, configuración y
  casos borde.
