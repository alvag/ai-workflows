# pr-bitbucket — referencia

| Sección | Se lee en |
|---|---|
| Comandos | paso 1 |
| Operaciones de Bitbucket | pasos 2 y 6 |
| Descripción y Sanitización | paso 3 |
| Revisores | paso 4 |
| Vista previa | paso 5 |

## Comandos

```sh
git remote get-url origin              # git@bitbucket.org:acme/webapp.git → acme/webapp
git branch --show-current              # rama origen
git remote show origin | sed -n 's/.*HEAD branch: //p'   # rama destino por defecto
git fetch origin <rama> && git rev-list --count origin/<rama>..HEAD   # > 0: hay commits sin pushear
git log -1 --pretty=%s                 # título
```

Si `origin/<rama>` no existe, la rama no está pusheada: se aplica la regla 2.

## Operaciones de Bitbucket

Los nombres de las tools se resuelven por capacidad: se listan las disponibles y se buscan las
que contengan `bitbucket` o `bb_`. Las de uso habitual son `mcp__bitbucket__bb_get`, `bb_post` y
`bb_put`.

- **Probar el MCP:** `bb_get` a `/repositories/<workspace>/<repo>` con `jq: "name"`. Si falla, se
  aplica la regla 5.
- **Duplicados:** `bb_get` a `/repositories/<workspace>/<repo>/pullrequests` con
  `queryParams: { "q": "state=\"OPEN\" AND source.branch.name=\"<rama>\"", "pagelen": "5" }`.
- **Crear:** `bb_post` a `/repositories/<workspace>/<repo>/pullrequests`:

  ```json
  {
    "title": "<título>",
    "source": { "branch": { "name": "<rama origen>" } },
    "destination": { "branch": { "name": "<rama destino>" } },
    "description": "<markdown>",
    "reviewers": [ { "account_id": "…" } ],
    "close_source_branch": true
  }
  ```

  con `jq: "{id: id, url: links.html.href, reviewers: reviewers[*].display_name}"`.
- **Actualizar:** `bb_put` a `/repositories/<workspace>/<repo>/pullrequests/<id>` con `title`,
  `description` y `reviewers`.
- **Un `account_id` que da 400** se quita del payload, se reintenta y se avisa para corregir la
  memoria.
- **Nunca** se llama a `.../approve` ni a `.../merge`.

## Descripción

Compacta: resume, no vuelca la spec. Cada sección sale de `odd/tasks/<feature>.md`.

```markdown
## Ticket
[<CLAVE>](<site_url>/browse/<CLAVE>)
Spec: [<SUBTAREA>](<url de la subtarea>)

## Problema
- <1-2 bullets del Problema / Objetivo>

## Solución
- <1-3 bullets: el enfoque y los archivos clave, no todos>

## Criterios de aceptación
- [ ] **AC-1** — <resultado observable, una línea>
- [ ] **AC-2** — <…>
```

- **Ticket y Spec:** salen de la cabecera del documento. `Spec:` aparece solo si hubo subtarea, y
  la sección entera se omite si no hay ticket. `<site_url>` lo da el MCP de Atlassian o el link del
  ticket.
- **Criterios:** los `AC-n` vigentes, uno por línea. Un AC tachado no entra. Sirven de plan de
  pruebas para quien revisa.
- **Solución:** sale del diff contra la rama destino (`git diff --stat origin/<destino>...HEAD`) y
  de las tareas cerradas.

## Sanitización

Se quitan:

- el origen de cada criterio (`(pedido)`, `(clarify Q1)`), los `S<n>`, `T<n>`, el Log, `odd/` y
  la mecánica del agente;
- `localhost`, hosts de desarrollo, `file://` y las rutas absolutas de la máquina;
- los SHAs.

Las rutas de código del proyecto y los nombres de métodos sí se publican.

## Revisores

1. **Memoria.** Buscar en la memoria del runtime (en gentle-shell, `mem_search` de Engram) con
   `reviewers <workspace>/<repo>`. Si hay un resultado, se usa.
2. **Usuario.** Sin resultado, o sin memoria, preguntar dónde encontrarlos o quiénes son. Si se
   indica una fuente (un archivo, un PR anterior, una página), leerla y extraer `display_name` y
   `account_id`. Si solo se dan nombres, resolver el `account_id` con `bb_get` a
   `/workspaces/<workspace>/members` y filtrar por nombre; si queda ambiguo, preguntar.
3. **Guardar.** Una vez confirmados en la vista previa, guardarlos en la memoria con
   `topic_key: reviewers/<workspace>/<repo>`, así se actualizan en lugar de duplicarse:

   ```
   Reviewers de <workspace>/<repo>: <display_name> (<account_id>), …
   Fuente: <de dónde salieron>
   ```

Se excluye al autor del PR: Bitbucket rechaza un PR que tiene al autor como revisor. Si el usuario
cambia la lista en la vista previa, se guarda la nueva.

## Vista previa

Antes de crear o actualizar, mostrar en un solo bloque:

- `<workspace>/<repo>`, la rama origen → la destino, y si es crear o actualizar (con el ID);
- el título y la descripción completa, ya sanitizada;
- los revisores con su fuente: memoria, usuario o ninguno;
- `close_source_branch: true`;
- lo degradado: sin documento → sin checklist de criterios.

Sin un sí explícito no se escribe.
