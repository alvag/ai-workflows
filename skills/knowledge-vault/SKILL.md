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

## Los cuatro verbos

| Verbo | Qué hace | Estados |
|---|---|---|
| `archive --from <flujo> --summary <línea>` | archiva un flujo | `ARCHIVED` · `ALREADY_ARCHIVED` |
| `migrate --from <raíz> --summaries <tsv>` | archiva todos los flujos de un directorio | `BATCH_OK` (0) · `BATCH_PARTIAL` (1) · `BATCH_FAILED` (1) · `DRY_RUN` |
| `index` | regenera los índices | `INDEX_OK` |
| `config --config <ruta> [--set-root <ruta>]` | lee o escribe `path_vault` | `VAULT_CONFIGURED` · `VAULT_SET` |

Los tres primeros aceptan `--vault-root <ruta>` o `--config <ruta>`; sin ninguna
de las dos, la raíz sale de `<raíz del repo>/.specify/config.yml`. Códigos de
salida y enumerados completos en `reference.md` → "Estado a código de salida".

```bash
node <skills>/knowledge-vault/scripts/kv.mjs config --config .specify/config.yml --set-root ~/vaults/dev-memory
node <skills>/knowledge-vault/scripts/kv.mjs archive --from .plans/archived/abc-1 --summary "De qué se trató el flujo."
```

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
- `README.md` — qué es, cuándo usarla e instalación.
