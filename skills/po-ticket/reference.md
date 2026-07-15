# po-ticket — Referencia

Detalle operativo de la skill `po-ticket`. El `SKILL.md` apunta acá para el acceso a Jira, el esquema de configuración, la plantilla del ticket y la sanitización.

## Tabla de contenidos

- [Detección por capacidad](#detección-por-capacidad)
- [Flujo de Jira](#flujo-de-jira)
- [Esquema de `.po-config.yml`](#esquema-de-po-configyml)
- [Plantilla de `ticket.md`](#plantilla-de-ticketmd)
- [Subtareas por área](#subtareas-por-área)
- [Sanitización](#sanitización)
- [Adjuntar capturas](#adjuntar-capturas)

---

## Detección por capacidad

Los nombres de tools/MCP cambian entre entornos. Resolver por **capacidad**: probar la vía preferida y, si no existe, buscar variantes por keyword antes de degradar.

| Capacidad | Cómo intentarlo (orden) | Fallback / degradación |
|---|---|---|
| Acceso a Jira | 1º **conector de Atlassian del Claude Code desktop** si está presente; 2º **MCP de Atlassian** configurado. Buscar la tool cuyo nombre contenga `jira`/`atlassian`. | Dejar `ticket.md` como borrador local; el PO crea/actualiza el ticket a mano y pega la clave. |
| Reproducción en navegador | Cualquier tool con `chrome`/`browser`/`playwright`/`devtools`. | Pedir al PO captura/video/pasos; redactar con eso. |
| Selección interactiva (clarify) | Tool de selección tipo `AskUserQuestion` si existe. | Preguntar de forma conversacional, con recomendación. |

> Regla: antes de fallar por "tool X no existe", listar las tools disponibles y buscar coincidencias por capacidad/keyword. Solo entonces avisar y degradar.

## Flujo de Jira

El **conector del desktop** y el **MCP de Atlassian** exponen operaciones equivalentes; los nombres de tool pueden diferir (por eso se descubre por capacidad). Al implementar, **verificar el surface real** de la vía disponible. Operaciones que la skill necesita:

- **Resolver `cloudId` del site** (p. ej. `getAccessibleAtlassianResources` o equivalente del conector). Cachearlo para la sesión. `getJiraIssue`/escrituras suelen necesitar el `cloudId`, no solo la clave.
- **Leer ticket** (modo enriquecer): `getJiraIssue` con `{ cloudId, issueIdOrKey: "<CLAVE>" }`. Extraer `summary`, `issuetype.name`, `description` (renderizar ADF a texto), `priority`, `labels`, `status`. En enriquecer, heredar `project` e `issuetype` del ticket base.
- **Crear ticket** (modo nuevo): `createJiraIssue` con `{ cloudId, fields: { project: { key: "<project_key>" }, issuetype: { name: "<default_issuetype>" }, summary, description } }`. Devuelve la **clave real** → renombrar el dir provisional `NUEVO-<slug>/` a `<CLAVE>/`.
- **Editar ticket** (modo enriquecer): `editJiraIssue` para actualizar `summary`/`description`.
- **Comentar** (opcional, si el PO lo pide): `addCommentToJiraIssue`; el cuerpo va en ADF.

**Toda escritura** (crear/editar/comentar) pasa por el **STOP de write-safety**: mostrar (1) recurso exacto (proyecto + issuetype para nuevo; clave para enriquecer) y (2) contenido exacto, y esperar confirmación antes de ejecutar.

**Descripción en ADF.** Jira almacena la descripción en ADF (Atlassian Document Format). El cuerpo del `ticket.md` (Markdown) se convierte a ADF al publicar. Si la vía disponible acepta Markdown/`wiki` directamente, usarlo; si exige ADF, construir el documento con nodos de párrafo, `bulletList`/`orderedList` y `heading`. Mantener el contenido idéntico al `ticket.md` aprobado en el gate.

## Esquema de `.po-config.yml`

Vive en la raíz de la carpeta del proyecto (`/Jira/PQTCH/.po-config.yml`). Todos los campos son opcionales; lo que falte se pregunta y se ofrece guardar. Es **local**: la skill no lo trackea.

```yaml
# .po-config.yml — config del proyecto para las skills del PO (po-ticket / po-qa)
project_key: PQTCH          # opcional; por defecto = nombre del directorio de trabajo
default_issuetype: Bug      # tipo de issue por defecto al crear (Bug | Historia | Tarea | ...)
environments:               # base URLs por ambiente (las usa po-qa; útil registrarlas acá)
  dev:  https://dev.ejemplo.com
  qa:   https://qa.ejemplo.com
  prod: https://www.ejemplo.com
```

- `project_key`: si el nombre del directorio ya es la clave (`/Jira/PQTCH` → `PQTCH`), este campo es redundante; sirve para overridear cuando el nombre del dir no coincide.
- `default_issuetype`: el nombre exacto como aparece en Jira. Si al crear no matchea, descubrir los tipos válidos del proyecto (p. ej. `createmeta`) y preguntar.
- `environments`: compartido con `po-qa`. `po-ticket` no lo necesita para crear, pero conviene mantenerlo acá para que ambas skills lean la misma config.

### Creación on-demand e incremental

No hay comando de setup: el archivo se crea y completa **a medida que hace falta**.

1. **Inferir sin preguntar** lo que se pueda: `project_key` sale del nombre del directorio de trabajo.
2. **Preguntar solo el dato que falta** en el momento en que se necesita: `po-ticket` pregunta `default_issuetype` la primera vez que va a crear un ticket (con opciones Bug/Historia/Tarea si hay tool de selección; si no, conversacional); `po-qa` pide la URL del ambiente que va a probar cuando no está.
3. **Mostrar el YAML exacto** que se va a escribir/actualizar y crear/mergear el archivo **tras confirmación**. Nunca sobrescribir a ciegas: si el archivo ya existe, agregar/actualizar solo el campo faltante y respetar el resto.
4. El archivo es **local**; no se trackea. Si el PO prefiere no guardarlo, seguir con los valores de la corrida sin persistirlos.

Así el `.po-config.yml` empieza vacío o inexistente y se va llenando: `po-ticket` deja `project_key` + `default_issuetype`; `po-qa` suma las `environments` a medida que se prueban DEV/QA/PROD.

## Plantilla de `ticket.md`

`<CLAVE>/ticket.md` — el ticket en **lenguaje no técnico**. Es lo que se publica en Jira (tras sanitizar y convertir a ADF). Los encabezados de sección llevan **emoji** (convención del equipo) y el título lleva **prefijo de área** (ver abajo).

```markdown
# [Front|Back|Front/Back] <Título claro y accionable, desde la vista del usuario>

## 📋 Descripción / Contexto
<Qué está pasando hoy, desde la perspectiva del usuario o del negocio: el
comportamiento actual/roto (el síntoma, con el mensaje de error visible si lo
hay), a quién afecta y en qué situación. 1-3 párrafos, sin jerga técnica.>

## 🔁 Pasos para Reproducir
1. <paso observado>
2. <paso observado>
3. <...>

## 📸 Evidencia
- Captura: `capturas/<archivo>.png`
- <Observación en lenguaje llano — p. ej. "al enviar el formulario aparece un
  mensaje de error rojo y la página no avanza".>

## 🎯 Objetivo
<Por qué importa resolverlo: qué se gana o qué riesgo/costo evita. En términos de
negocio/usuario.>

## ✅ Criterios de Aceptación
<El comportamiento esperado, formalizado y verificable. Cada AC es una condición
observable de "cuándo está resuelto"; cubren también los casos borde.>
- **AC-1:** <resultado observable, verificable, en lenguaje de negocio>
- **AC-2:** <...>

## 🛠️ Pistas para el Equipo  <!-- opcional; observado, NO diagnóstico de código -->
<Solo hechos observados en el navegador que podrían orientar al developer — p. ej.
"la consola muestra un error 500 al guardar". Nunca análisis de código ni propuesta
de solución técnica. Omitir la sección si no hay nada observable útil.>
```

> **Sin solapamiento Esperado/Actual vs. AC.** El comportamiento **actual** (el síntoma) vive en 📋 Descripción/Contexto; el comportamiento **esperado** se formaliza en los ✅ Criterios de Aceptación (que además cubren casos borde). No se usan secciones separadas de "Resultado esperado/actual": los AC son la única fuente de "qué debe cumplirse".

### Prefijo de área en el título (`[Front]` / `[Back]` / `[Front/Back]`)

Convención del equipo: el título del ticket (y de sus subtareas, si las hay) empieza con el área afectada.

- **`[Front]`** — el problema es visual / de interfaz (lo que el usuario ve o con lo que interactúa en pantalla).
- **`[Back]`** — el problema es de datos, guardado, cálculo o de un error que viene del servidor.
- **`[Front/Back]`** — involucra ambas.

Como el PO no es técnico, la skill **propone** el área a partir de los **síntomas observables** (bug visual → `[Front]`; error al guardar / dato incorrecto / error del servidor en consola → `[Back]`; ambos → `[Front/Back]`) y **lo confirma con el PO** en el gate. Nunca imponerla en silencio.

### Emoji de encabezados (referencia)

| Sección | Emoji |
|---|---|
| Descripción / Contexto | 📋 |
| Pasos para Reproducir | 🔁 |
| Evidencia | 📸 |
| Objetivo | 🎯 |
| Criterios de Aceptación | ✅ |
| Pistas para el Equipo | 🛠️ |

**Criterios de aceptación observables.** Cada `AC-n` debe poder comprobarse mirando el comportamiento, no el código — así `po-qa` los puede validar después. Formato preferido: resultado observable, o Given/When/Then si ayuda.

Ejemplo (mismo dominio que un bug de exportación):

```markdown
- **AC-1:** Dado un listado con resultados, cuando el usuario exporta a Excel,
  entonces se descarga un archivo con una fila por resultado.
- **AC-2:** Dado un listado vacío, cuando el usuario intenta exportar,
  entonces el botón de exportar está deshabilitado y no se descarga nada.
```

## Subtareas por área

Solo cuando el ticket quedó **`[Front/Back]`** (ver "Prefijo de área"). Tras publicar el ticket padre y **con confirmación del PO**, crear dos subtareas —una `[Front]` y otra `[Back]`—, cada una con un **resumen heredado del padre**, no una copia completa.

- **Tipo:** subtarea (`issuetype` subtask) con el ticket recién creado como **padre**. El nombre del issuetype de subtarea varía ("Subtarea"/"Sub-task") → tomarlo del proyecto (p. ej. `createmeta`, el issuetype con `subtask: true`) o preguntar.
- **Título:** `[Front] <mismo título del padre>` y `[Back] <mismo título del padre>` (sin el `[Front/Back]` del padre; cada subtarea lleva solo su área).
- **Descripción (resumen heredado):** contexto breve del padre + **solo los AC que le tocan a esa área** + un puntero al padre. Reparto de AC:
  - La skill **propone** qué AC caen en Front (lo visible/interfaz) y cuáles en Back (datos/guardado/servidor) a partir de cómo está redactado cada AC, y lo **confirma con el PO** (no adivinar en silencio). Un AC que involucra ambas áreas puede quedar en las dos subtareas.

```markdown
> Subtarea de **<CLAVE-del-padre>**. Detalle completo en el ticket padre.

## 📋 Contexto
<2-3 líneas del contexto del padre, acotadas a esta área.>

## ✅ Criterios de Aceptación (de esta área)
- **AC-1:** <el/los AC del padre que corresponden a esta área>
```

- **Payload:** `createJiraIssue` con `{ cloudId, fields: { project: { key }, parent: { key: "<padre>" }, issuetype: { name: "<subtask>" }, summary, description } }`.
- **Write-safety:** cada subtarea con su propio STOP (recurso + contenido a la vista) antes de crearla.
- Guardar las claves de las subtareas creadas en `ticket.md` (al pie, como referencia local).

## Sanitización

Antes de publicar, el entregable habla del **objetivo**, no del método. Quitar del contenido a publicar:

- Rutas locales y nombres de archivos del flujo (`ticket.md`, `.po-config.yml`, `capturas/`, paths absolutos de la máquina).
- Cualquier mención a esta skill, a su mecánica o al proceso interno del PO.
- URLs de entornos locales o de prueba que no correspondan al ticket (`localhost`, `127.0.0.1`, `file://`), salvo que sean parte legítima de los pasos de reproducción.

La referencia a las capturas en el cuerpo (`capturas/<archivo>.png`) se reemplaza por el adjunto real en Jira (ver "Adjuntar capturas") o por una nota de que se adjuntan aparte.

## Adjuntar capturas

Intentar adjuntar las capturas de `capturas/` al ticket **por capacidad**:

1. Si la vía de Jira disponible (conector desktop o MCP) expone una operación de **adjuntar archivo** a un issue, usarla tras el STOP de write-safety (mostrar qué archivo se adjunta a qué issue).
2. Si **no** la soporta → degradar: dejar las capturas en `capturas/`, referenciarlas en el cuerpo y **avisar al PO** para que las adjunte a mano en Jira. No bloquear la publicación del ticket por esto.
