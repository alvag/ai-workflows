# spec-jira — referencia

Cada sección se lee en el paso de `SKILL.md` que la nombra.

| Sección | Se lee en |
|---|---|
| Documento de la feature | paso 3 |
| Operaciones de Jira | pasos 1, 4 y 6 |
| Texto de la subtarea y Sanitización | paso 4 |
| Qué hacer con lo que vuelve | paso 6 |
| Comentario de ajuste | paso 6, si la spec cambió |

## Documento de la feature

`odd/tasks/<feature>.md` es la única fuente de verdad. Respeta el orden de ODD: cabecera,
`## Specs`, `## Tasks`, `## Log`. Si el archivo ya existe, se completa sin duplicar secciones.

```markdown
# <título corto>
Ticket: <CLAVE> · Spec Jira: <SUBTAREA> (<url>) · estado: borrador · modo: —

## Specs
**Resumen para PO**
- **Problema / Objetivo:** <en lenguaje de negocio, sin jerga técnica>
- **Alcance:** <qué entra> · **Fuera de alcance:** <qué queda afuera>
- **Criterios de aceptación:**
  1. <AC-1 como resultado observable para el PO>
  2. <AC-2 ...>

**Problema / Objetivo:** <por qué existe el cambio, 1-3 párrafos>
**Incluye:** <qué entra>
**No incluye:** <qué queda afuera, explícito>

- **S1 / AC-1** (pedido): Given <contexto>, When <acción>, Then <resultado observable>.
  > «<cita textual del pedido o del ticket que lo sostiene>»
- **S2 / AC-2** (clarify Q1): <...>

**Clarifications**
- **Q1:** <pregunta> — **A:** <respuesta> (afecta: AC-n)

## Tasks
- T1 · S1 · <ruta> · <commit cuando cierre>

## Log
- L1: <pedido original, textual>
```

- **El origen del criterio.** `pedido`: lo pidió el usuario o el ticket. `clarify`: sale de una
  `Q<n>`. `repositorio`: sale de una convención escrita en `AGENTS.md`, `CLAUDE.md` o
  `CONTRIBUTING.md`. El usuario lo comprueba al aprobar la spec. No hay validador.
- **El resumen para PO.** Lo lee el PO, no el agente: sin nombres de código, rutas ni jerga. Tiene un
  punto por cada `AC-n` vigente, con el mismo número y en el mismo orden. Si cambia un AC, cambia
  su punto.
- **La cita.** Cada `S<n>` conserva el texto literal que lo origina, como pide ODD. El AC es su
  forma verificable.
- **El estado.** La cabecera lleva `estado: borrador | awaiting | changes-requested | approved` y
  `modo: A | B`. Es lo que se lee al retomar.

## Operaciones de Jira

Los nombres de las tools cambian entre entornos. Se resuelven **por capacidad**: se listan las
tools disponibles, se buscan las que contengan `jira` o `atlassian`, y solo entonces se degrada.

1. `getAccessibleAtlassianResources` devuelve el `cloudId`, que se cachea para la sesión.
2. `getJiraIssue` con `{ cloudId, issueIdOrKey }` trae `summary`, `issuetype`, `description` (el
   ADF se pasa a texto), `status` y los links.
3. `createJiraIssue` crea la subtarea: `{ cloudId, fields: { project, parent: { key: "<CLAVE>" },
   issuetype: { name: "<subtarea>" }, summary: "SPEC: <título>", description } }`. El nombre del
   tipo de subtarea varía («Subtarea», «Sub-task»): se descubre con `createmeta`, buscando el
   issuetype con `subtask: true`.
4. `editJiraIssue` actualiza la descripción con la spec vigente.
5. `addCommentToJiraIssue` agrega el comentario. El cuerpo va en ADF y menciona a cada persona
   con un nodo `{ type: "mention", attrs: { id: "<accountId>" } }`.

**Degradación:** si no hay MCP, si solo permite lectura o si la escritura falla, se avisa y se
entrega el mismo texto en un bloque listo para pegar. Después, el usuario pega en el chat la clave
de la subtarea o la versión aprobada.

## Texto de la subtarea

Primero el resumen para PO y después la definición técnica. Las dos partes salen del documento ya
aprobado: acá no se redacta nada nuevo.

```markdown
## Resumen
<el bloque «Resumen para PO» del documento, tal cual>

---

## Definición técnica
<el resto de `## Specs`: problema, alcance, AC-n y Clarifications, casi literales; solo se les
aplica la sanitización de abajo>
```

## Sanitización

Se quitan **solo** estas tres cosas; todo lo demás se publica tal cual, incluidos los `AC-n`, los
nombres de métodos y las rutas de código fuente del proyecto.

- La mecánica del agente: ODD, `S<n>`, `T<n>`, el `## Log`, `odd/`, subagentes, modelos y
  revisiones cruzadas.
- Lo local: `localhost`, `127.0.0.1`, hosts de desarrollo, `file://`, las rutas absolutas de la
  máquina y las indicaciones de cómo probar en local.
- Lo de Git y del flujo: ramas, SHAs, commits, y los comandos de test y de build.

## Qué hacer con lo que vuelve

Primero se lee el estado de la subtarea y los comentarios posteriores a la última publicación. Si
el usuario dice «ya aprobaron», se le cree.

| Vuelve | Modo A | Modo B |
|---|---|---|
| aprobada **sin cambios** | `estado: approved`; empieza la implementación | `estado: approved`; se sigue |
| cambios **editoriales**: redacción, orden, un ejemplo, también en el resumen para PO | se ajusta la spec y se republica; no hay código que tocar | lo mismo; el código no cambia |
| cambios en **uno o más `AC-n`** | se ajusta la spec, se republica y se vuelve a `awaiting` | ver el procedimiento de abajo |
| cambios de **alcance o de enfoque** | se ajusta la spec y se republica | **STOP:** se pregunta antes de tocar código, porque puede haber trabajo descartable |
| **sin respuesta** | se sigue esperando | se sigue, y el cierre informa que la spec no está aprobada |

**Procedimiento ante un AC cambiado, en modo B:**

1. Agregar al `## Log` el cambio textual, con su fuente: el comentario de Jira y su autor.
2. Reescribir **solo** los `S<n> / AC-n` afectados, y sus puntos en el «Resumen para PO». Un AC nuevo toma el número siguiente; uno
   retirado queda tachado, sin renumerar los demás.
3. Reabrir **solo** las tareas ligadas a esos `S<n>`.
4. Primero se ajusta el test del criterio y se lo ve fallar; después, el código. Al final corren
   los checks completos para confirmar que los demás criterios siguen en verde.
5. Republicar la descripción y dejar el comentario de ajuste.

## Comentario de ajuste

Un único comentario consolidado, que menciona a quienes dejaron las observaciones; no se responde
hilo por hilo:

```markdown
@<autor> — ajustes tras la revisión:
- <qué cambió; un bullet por observación atendida>

La descripción quedó actualizada con la versión vigente. Vuelve a revisión.
```

Si el MCP no acepta menciones, o no se resuelve el `accountId`, se publica el mismo comentario sin
la mención.
