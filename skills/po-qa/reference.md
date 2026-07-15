# po-qa — Referencia

Detalle operativo de la skill `po-qa`. El `SKILL.md` apunta acá para el acceso a Jira, la identificación de la spec, la plantilla del reporte y el comentario de observaciones.

## Tabla de contenidos

- [Detección por capacidad](#detección-por-capacidad)
- [Flujo de Jira](#flujo-de-jira)
- [Identificar la subtarea de spec](#identificar-la-subtarea-de-spec)
- [Resolución del ambiente](#resolución-del-ambiente)
- [Plantilla de `qa-reporte.md`](#plantilla-de-qa-reportemd)
- [Comentario de observaciones](#comentario-de-observaciones)

---

## Detección por capacidad

Los nombres de tools/MCP cambian entre entornos. Resolver por **capacidad**: probar la vía preferida y, si no existe, buscar variantes por keyword antes de degradar.

| Capacidad | Cómo intentarlo (orden) | Fallback / degradación |
|---|---|---|
| Acceso a Jira | 1º **conector de Atlassian del Claude Code desktop** si está presente; 2º **MCP de Atlassian** configurado. Buscar la tool cuyo nombre contenga `jira`/`atlassian`. | Leer `ticket.md` local si existe; presentar el pre-check sin tocar Jira. |
| Prueba en navegador | Cualquier tool con `chrome`/`browser`/`playwright`/`devtools`. | Sin navegador no hay validación real: avisar y detener, o pedir al PO que pruebe y reporte. |
| Selección interactiva | Tool de selección tipo `AskUserQuestion` si existe. | Preguntar de forma conversacional, con recomendación. |

> Regla: antes de fallar por "tool X no existe", listar las tools disponibles y buscar coincidencias por capacidad/keyword. Solo entonces avisar y degradar.

## Flujo de Jira

El **conector del desktop** y el **MCP de Atlassian** exponen operaciones equivalentes; los nombres de tool pueden diferir (por eso se descubre por capacidad). Al implementar, **verificar el surface real** de la vía disponible. Operaciones que la skill necesita:

- **Resolver `cloudId` del site** (p. ej. `getAccessibleAtlassianResources` o equivalente). Cachearlo para la sesión.
- **Leer el ticket + subtareas:** `getJiraIssue` con `{ cloudId, issueIdOrKey: "<CLAVE>" }`. Extraer `summary`, `description` (ADF → texto), `status`, `assignee` (con `accountId`) y la lista de **subtareas** (`subtasks`: clave + título de cada una).
- **Leer una subtarea** (la spec): `getJiraIssue` sobre su clave, para sacar sus `AC-n`.
- **Comentar** (solo si el PO autoriza una observación): `addCommentToJiraIssue` con `{ cloudId, issueIdOrKey, body }`; el cuerpo va en ADF y admite un nodo `mention` (`{ type: "mention", attrs: { id: "<accountId>" } }`) para etiquetar al asignado. Ver "Comentario de observaciones".

**Toda escritura** (comentar) pasa por el **STOP de write-safety**: mostrar (1) recurso exacto (clave del ticket) y (2) contenido exacto del comentario, y esperar autorización antes de ejecutar.

## Identificar la subtarea de spec

El ticket puede tener varias subtareas de distinta naturaleza:

- **Subtarea de spec** — la publica `sdd-flow` (gate `publish-spec`), típicamente titulada `SPEC: <título>`. Trae la definición técnica con `AC-n` verificables. **Es la que aporta los AC del developer.**
- **Subtareas de área** `[Front]` / `[Back]` — las puede crear `po-ticket`. **No** son la spec: son el reparto de trabajo por área.

Reglas para elegir:

1. Preferir la subtarea cuyo título empiece por `SPEC:` (o contenga "spec"/"especificación").
2. **No hay ninguna así** → avisar al PO: "no encontré la spec del developer" y ofrecer validar solo contra los AC del ticket / `ticket.md`.
3. **Hay varias candidatas ambiguas** (o ninguna con título claro y más de una subtarea que no es `[Front]`/`[Back]`) → **preguntar al PO** cuál subtarea corresponde a la spec. No adivinar.

Los AC a validar = **unión** de los AC del ticket (lenguaje de negocio, escritos por `po-ticket`) + los `AC-n` de la spec elegida (si la hay). Si un AC del ticket y uno de la spec son el mismo, no duplicarlo en el reporte.

## Resolución del ambiente

La URL a probar se resuelve por precedencia:

1. **URL explícita en el prompt** ("prueba PQTCH-649 en https://qa.ejemplo.com/reportes").
2. **URL en el ticket** (si la descripción trae una URL de la pantalla afectada).
3. **`environments.<ambiente>` del `.po-config.yml`** — el ambiente sale del prompt (`DEV`/`QA`/`PROD`, case-insensitive) y se mapea a `dev`/`qa`/`prod`.

Si no se puede resolver ninguna URL, preguntar al PO. Cuando el PO la provee y no estaba en `.po-config.yml`, **ofrecer guardarla** en `environments.<ambiente>` (mostrar el YAML y escribir/mergear tras confirmación; ver `po-ticket` → "Creación on-demand e incremental"): así la próxima validación en ese ambiente ya la toma sola. Con `PROD`, avisar explícitamente que la validación corre en **producción** antes de empezar.

## Plantilla de `qa-reporte.md`

`<CLAVE>/qa-reporte.md` — el pre-check, AC por AC. Local; no se publica (a Jira solo va, si el PO autoriza, el comentario de observaciones).

```markdown
# Pre-check de QA — <CLAVE> · ambiente <DEV|QA|PROD>

- **Ticket:** <CLAVE> — <título>
- **Spec validada:** <clave de la subtarea SPEC, o "sin spec — validado contra AC del ticket">
- **URL probada:** <url>
- **Recomendación global:** ✅ Cumple todo · ⚠️ Cumple con observaciones · ❌ No cumple

## Resultado por criterio
| AC | Veredicto | Evidencia |
|---|---|---|
| AC-1 | ✅ cumple | <captura + paso observado> |
| AC-2 | ❌ no cumple | <qué se esperaba vs. qué pasó; captura `capturas/...`> |
| AC-3 | ⚠️ no verificable | <por qué no se pudo validar — falta dato/acceso/escenario> |

## Observaciones (si hay ❌ o ⚠️)
- <AC-n>: <descripción clara del problema para el equipo, en lenguaje de negocio>
```

- **Veredictos:** `✅ cumple` / `❌ no cumple` / `⚠️ no verificable`. La evidencia es concreta (captura, paso, salida observada), no "se ve bien".
- Las capturas de la validación se guardan en `capturas/` (junto a las de `po-ticket`, si existen).

## Comentario de observaciones

Solo cuando el PO **decide observar** el ticket y **autoriza** publicar. Un único comentario consolidado que **@menciona al asignado** del ticket, con las observaciones en lenguaje de negocio:

```markdown
@<asignado> — validación de QA en <ambiente>: el desarrollo no cumple con lo siguiente:
- <AC-n>: <qué se esperaba vs. qué se observó>
- <AC-m>: <...>

Detalle y capturas en el ticket. Quedo atento para re-validar tras el ajuste.
```

- **Cómo se etiqueta:** el cuerpo va en ADF con un nodo `mention` (`{ type: "mention", attrs: { id: "<accountId>" } }`); el `accountId` sale de `assignee` del ticket (`getJiraIssue`).
- **Degradación:** si no hay asignado, o el MCP/conector no acepta menciones ADF, o no se pudo resolver el `accountId` → publicar el mismo comentario **sin** la @mención (no bloquear).
- **Write-safety:** mostrar el recurso (clave del ticket) + el contenido exacto del comentario y esperar autorización antes de publicar. Nunca publicar por iniciativa propia.
- Adjuntar capturas de la observación por capacidad (igual que en `po-ticket`); si no se puede, referenciarlas y avisar al PO para que las suba a mano.
