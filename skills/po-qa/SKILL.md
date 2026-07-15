---
name: po-qa
description: >-
  Ayuda al Product Owner (que hace las veces de QA) a validar la entrega de un
  ticket contra sus criterios de aceptación, usando el navegador. El PO invoca
  "prueba este ticket en DEV/QA/PROD"; la skill lee el ticket de Jira (y su
  subtarea de spec si existe), establece QUÉ probar y los criterios de aceptación,
  abre el ambiente en el navegador (el PO se loguea a mano si hace falta), ejercita
  cada criterio, junta evidencia (capturas, pasos, consola/red) y produce un
  pre-check con veredicto AC por AC: cumple / no cumple / no verificable. Es un
  PRE-CHECK ASISTIDO: recomienda, pero decide el PO. Si pasa, ofrece archivar el
  ticket; si no pasa, y solo si el PO autoriza, publica un comentario en Jira
  etiquetando al asignado con las observaciones. Pensada para un PO SIN acceso al
  código: trabaja solo con Jira y el navegador. NO decide por sí sola el rechazo
  formal, NO es code review, NO arregla el bug. Invocación explícita: "/po-qa
  prueba PQTCH-649 en DEV" (o QA/PROD). No dispara sola: solo por slash o pedido
  explícito.
argument-hint: "[prueba <CLAVE-123> en <DEV|QA|PROD>]  ·  URL opcional en el prompt"
# disable-model-invocation: clave REAL de Claude Code — deja la skill solo-slash
# (/po-qa). Los triggers ("prueba el ticket", "valida esto") son genéricos y sin
# el flag competiría por el auto-trigger. Consecuencia asumida: no es invocable por
# el Skill tool de otra skill/subagente.
disable-model-invocation: true
---

# po-qa — validación asistida de la entrega para el PO

Skill orientada al **Product Owner que hace las veces de QA**. Valida que lo entregado cumple los **criterios de aceptación** del ticket, ejercitándolo en el navegador y produciendo un **pre-check** con veredicto AC por AC. El PO **no tiene acceso al código**: esta skill trabaja solo con **Jira + navegador**.

Es la contraparte de PO al cierre del ciclo: [`po-ticket`](../po-ticket/SKILL.md) produce el ticket → el developer lo implementa con `sdd-flow` → `po-qa` valida la entrega.

```
prueba CLAVE-123 en DEV ──► leer ticket + spec ──► establecer QUÉ probar (AC) ──► abrir ambiente (login manual) ──► ejercitar cada AC ──► qa-reporte.md ──► veredicto al PO
                            (Jira: ticket+subtareas)   (checklist desde los AC)    (navegador, sesión real)      (evidencia por AC)   (AC por AC)   (pasa→archiva / no→comenta)
```

## Es un pre-check asistido (no un juez)

La skill **recomienda**; el PO **decide**. Ejecuta las pruebas, junta evidencia y da un veredicto AC por AC (cumple / no cumple / no verificable), pero:

- El **rechazo o la aprobación formal** los decide el PO.
- La skill **no publica nada en Jira por su cuenta**: si el PO decide observar el ticket, la skill redacta el comentario y lo publica **solo tras autorización** (write-safety), etiquetando al asignado.

## Reglas no negociables

1. **Establecer QUÉ probar antes de probar.** No abrir el navegador sin tener claros los criterios de aceptación y de dónde salen (ver paso 2). Si no hay AC claros, resolverlo con el PO primero.
2. **Pre-check asistido.** La skill recomienda; el veredicto formal es del PO (ver arriba).
3. **Login manual del PO.** La skill nunca ingresa credenciales. Si el ambiente pide autenticación, le pide al PO que se loguee él mismo en su navegador y confirme; recién entonces continúa. Sin credenciales guardadas.
4. **Nada se publica en Jira sin autorización totalmente explícita — siempre, sin excepción.** Antes de **cualquier** escritura en Jira (comentar, adjuntar) se le muestra al PO **exactamente qué se va a publicar** —el recurso exacto (clave del ticket) y el contenido exacto, literal— y se **espera su confirmación explícita**. No vale una autorización general previa ni un "dale" anticipado: cada escritura tiene su propio STOP con el contenido a la vista. Ante cualquier duda sobre si hay autorización, **no publicar**. Es la regla de mayor prioridad de esta skill.
5. **Evidencia, no opinión.** Cada veredicto se apoya en evidencia concreta (captura, paso observado, salida de consola/red), no en una impresión general.
6. **Descubrir por capacidad, no por nombre** (Jira y navegador; ver `reference.md`). **Degradación elegante:** si falta el navegador o el acceso a Jira, avisar y seguir con lo que haya, o detener con un aviso claro si no se puede probar.

## Acceso a Jira (orden de preferencia)

Igual que [`po-ticket`](../po-ticket/SKILL.md): por **capacidad**, **1º el conector de Atlassian del Claude Code desktop**, **2º el MCP de Atlassian** configurado. Operaciones que necesita: resolver `cloudId`, leer el ticket y sus **subtareas** (`getJiraIssue`), leer el **asignado** (`assignee.accountId`, para etiquetarlo) y, solo si el PO autoriza una observación, comentar (`addCommentToJiraIssue`, ADF con `mention`). Detalle en `reference.md` → "Flujo de Jira". Sin ninguna vía → degradar: leer el `ticket.md` local si existe y presentar el pre-check sin tocar Jira.

## Modelo de artefactos en disco

Comparte la estructura de [`po-ticket`](../po-ticket/SKILL.md): carpeta del proyecto cuyo nombre es la clave de proyecto, un dir por ticket, y `.po-config.yml` con las URLs por ambiente.

```
/Jira/PQTCH/
├── .po-config.yml            # environments: dev/qa/prod (base URLs)
├── PQTCH-649/
│   ├── ticket.md             # lo publicado por po-ticket (si se usó)
│   ├── capturas/             # evidencia de la validación (se suma acá)
│   └── qa-reporte.md         # ⟵ lo escribe po-qa (pre-check, AC por AC)
└── done/
    └── PQTCH-649/            # ⟵ po-qa mueve el dir acá si el PO aprueba
```

- La **ubicación es el estado**: en la raíz = activo/en validación; en `done/` = aprobado. No hay archivo de estado.
- Si no existe el dir del ticket (p. ej. el ticket no se creó con `po-ticket`), crearlo para alojar `qa-reporte.md` y `capturas/`.

## Flujo

1. **Resolver proyecto/config y parsear el pedido.** Inferir `project_key` del nombre del directorio; leer `.po-config.yml` si existe. Del prompt, extraer la **clave del ticket** (`[A-Z][A-Z0-9]+-\d+`) y el **ambiente** (`DEV`/`QA`/`PROD`). La config se completa **on-demand**: si falta la URL del ambiente a probar, se pide en el paso 3 y se ofrece guardarla (ver "Resolución del ambiente" en `reference.md`).
2. **Establecer QUÉ probar y los AC** (paso crítico — no arranca la prueba sin esto claro):
   - Leer el ticket de Jira (`getJiraIssue`). Se asume que su descripción coincide con el `ticket.md` local; si hay local, cruzarlos y avisar diferencias.
   - Listar las **subtareas** del ticket e **identificar la subtarea de spec** (la que publica `sdd-flow`, típicamente titulada `SPEC: <título>`, con `AC-n` verificables). Ojo: puede haber también subtareas de área `[Front]`/`[Back]` creadas por `po-ticket` — esas no son la spec.
   - **Casos borde:**
     - **No hay subtarea de spec** → avisar al PO que no encontró la spec del developer y ofrecer probar solo contra los AC del ticket / `ticket.md`.
     - **Varias subtareas y no está claro cuál es la spec** → consultar al PO para que indique cuál corresponde.
   - **Consolidar los AC** (ticket + spec elegida) y derivar de ellos la **checklist de prueba**. Confirmar brevemente con el PO qué se va a probar **antes** de abrir el navegador.
3. **Resolver la URL y abrir el ambiente.** URL por precedencia: prompt > el ticket > `environments.<ambiente>` del `.po-config.yml`. Abrir en el navegador (por capacidad). Si aparece **login**, pedir al PO que se autentique él mismo y confirme; recién entonces seguir (regla 3). Con `PROD`, avisar explícitamente que se está validando en producción.
4. **Ejercitar cada AC.** Recorrer la checklist; por cada AC, reproducir el escenario y capturar **evidencia**: captura a `capturas/`, pasos observados, y consola/red si aporta. Registrar cumple / no cumple / no verificable con su evidencia.
5. **Escribir `qa-reporte.md`** con la plantilla de `reference.md` → "Plantilla de `qa-reporte.md`": veredicto **AC por AC** con evidencia + recomendación global. Es el pre-check.
6. **Presentar el veredicto al PO** y actuar según su decisión:
   - **Aprueba** → ofrecer **archivar**: mover el dir del ticket a `done/` (solo tras confirmación).
   - **Observa / no pasa** → si el PO **autoriza**, publicar un comentario en Jira (**write-safety STOP**) **etiquetando al asignado** (nodo `mention` con `assignee.accountId`) con las observaciones. Detalle en `reference.md` → "Comentario de observaciones". El dir se queda en la raíz para re-validar tras el arreglo.

## Compatibilidad con Plan Mode / modos no mutantes

Si el entorno prohíbe mutaciones: ejecutar la validación en el navegador y presentar el pre-check de forma conversacional, **sin** escribir `qa-reporte.md`, sin mover el dir a `done/` y sin comentar en Jira. Avisar que esas acciones quedan bloqueadas por el modo.

---

Detalle operativo (acceso a Jira, identificación de la spec, plantilla del reporte, comentario de observaciones) en `reference.md`.
