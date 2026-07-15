---
name: po-ticket
description: >-
  Ayuda al Product Owner a redactar tickets de Jira claros y accionables a partir
  de un problema mal descrito. El PO pasa una descripción del problema, una URL
  para reproducirlo y el contexto; la skill reproduce el error en el navegador,
  captura evidencia observable (pasos, capturas, consola/red), clarifica en
  diálogo de negocio y redacta un ticket en lenguaje NO técnico con objetivo,
  impacto y criterios de aceptación verificables. Publica el ticket en Jira tras
  confirmación. Dos modos: crear uno nuevo, o enriquecer/reescribir un ticket
  existente ambiguo (pasando su clave, p. ej. PQTCH-649). Pensada para un PO SIN
  acceso al código ni al repo: trabaja solo con Jira y el navegador. NO diagnostica
  a nivel código (eso lo hace el developer luego con sdd-flow), NO es code review.
  Invocación explícita: "/po-ticket <descripción + URL + contexto>" para uno nuevo,
  o "/po-ticket PQTCH-649" para enriquecer uno existente. No dispara sola: solo por
  slash o pedido explícito.
argument-hint: "[<descripción + URL de reproducción + contexto> | <CLAVE-123> para enriquecer]"
# disable-model-invocation: clave REAL de Claude Code — deja la skill solo-slash
# (/po-ticket). Los triggers ("arma el ticket", "crea el ticket") son genéricos y
# sin el flag competiría por el auto-trigger. Consecuencia asumida: no es invocable
# por el Skill tool de otra skill/subagente.
disable-model-invocation: true
---

# po-ticket — redacción de tickets de Jira para el PO

Skill orientada al **Product Owner**. Convierte un problema descrito de forma vaga en un **ticket de Jira claro, con criterios de aceptación verificables**, en lenguaje **no técnico**, para que llegue accionable al developer. El PO **no tiene acceso al código ni a un repo git**: esta skill trabaja solo con **Jira + navegador**.

Es la contraparte de PO al inicio del ciclo: `po-ticket` produce el ticket → el developer lo toma con `sdd-flow` → [`po-qa`](../po-qa/SKILL.md) valida la entrega.

```
descripción + URL + contexto ──► reproducir en navegador ──► clarificar (negocio) ──► ticket.md ──► GATE (PO revisa) ──► publicar en Jira
     (o CLAVE-123 para enriquecer)     (evidencia observable)        (diálogo)                                          (write-safety STOP)
```

## Alcance y límite honesto

- **Sí:** reproducir el síntoma en el navegador, observar lo que pasa (pasos, pantallas, mensajes de error visibles, consola/red), y traducir eso a un ticket claro con objetivo, impacto y AC.
- **No:** diagnosticar la causa a nivel código ni proponer la solución técnica. El PO no tiene el código; la skill tampoco lo asume. Lo observado se rotula como **"pistas para el equipo de desarrollo"**, nunca como análisis de código. El diagnóstico real lo hace el developer después con `sdd-flow`.

## Reglas no negociables

1. **Lenguaje no técnico en el ticket.** Todo lo que se publica en Jira habla del problema desde la vista del usuario/negocio. La jerga técnica solo aparece, si acaso, en la sección separada de "pistas para el equipo".
2. **Nada se publica en Jira sin autorización totalmente explícita — siempre, sin excepción.** Antes de **cualquier** escritura en Jira (crear ticket, crear subtarea, editar, comentar, adjuntar) se le muestra al PO **exactamente qué se va a publicar** —el recurso exacto (proyecto + tipo, o clave del ticket) y el contenido exacto, literal— y se **espera su confirmación explícita**. No vale una autorización general previa ni un "dale" anticipado: cada escritura tiene su propio STOP con el contenido a la vista. Ante cualquier duda sobre si hay autorización, **no publicar**. Es la regla de mayor prioridad de esta skill.
3. **Evidencia observable, no diagnóstico de código.** Ver "Alcance y límite honesto".
4. **La clarificación va primero, de a una pregunta.** No inventar contexto que el PO no dio: cuando falte información que cambia el ticket (comportamiento esperado, frecuencia, usuarios afectados, prioridad), preguntar — una a una, con una opción recomendada.
5. **Descubrir por capacidad, no por nombre.** El acceso a Jira y al navegador se resuelve por capacidad (ver "Acceso a Jira" y "Reproducción en navegador"). Antes de fallar por "tool X no existe", listar las disponibles y buscar coincidencias.
6. **Degradación elegante.** Si falta el navegador o el acceso a Jira, avisar en una línea y seguir con lo que haya (pedir capturas/pasos al PO; dejar el ticket como borrador local para publicar a mano).
7. **Sanitización antes de publicar.** El entregable habla del objetivo, no del método: nunca publicar rutas locales, nombres de archivos del flujo, ni mención a esta skill o su mecánica (ver `reference.md` → "Sanitización").

## Acceso a Jira (orden de preferencia)

Resolver por **capacidad**, con este orden:

1. **Conector de Atlassian del Claude Code desktop**, si está presente (uso principal esperado = app de escritorio).
2. **MCP de Atlassian** configurado, si no hay conector.

La skill busca la herramienta cuyo nombre matchee `jira`/`atlassian` y usa la que haya — no depende de cuál de las dos vías la provee. Operaciones esperadas (equivalentes en ambas): resolver `cloudId` del site, leer ticket (`getJiraIssue`), crear (`createJiraIssue`), editar (`editJiraIssue`), y comentar (`addCommentToJiraIssue`). Detalle en `reference.md` → "Flujo de Jira". Si no hay ninguna de las dos vías → degradar (regla 6): dejar el `ticket.md` como borrador y ofrecer que el PO lo cree/actualice a mano y pegue la clave.

## Reproducción en navegador

Buscar por capacidad cualquier tool con `chrome`/`browser`/`playwright`/`devtools`. Con ella: abrir la URL de reproducción, seguir los pasos, y capturar **evidencia observable** — pasos reproducidos, capturas a `capturas/`, y un digest de consola/red (errores visibles, requests fallidos) como hechos, sin hipótesis de código. Sin tool de navegador → degradar (regla 6): pedir al PO capturas/video/pasos.

## Modelo de artefactos en disco

El directorio de trabajo es la **carpeta del proyecto**; su nombre es la **clave de proyecto de Jira**.

```
/Jira/PQTCH/                      # nombre del dir = clave de proyecto (PQTCH)
├── .po-config.yml                # config del proyecto (ver reference.md)
├── PQTCH-649/                    # un ticket
│   ├── ticket.md                 # lo que se publicó (o va a publicarse) en Jira
│   └── capturas/                 # screenshots (evidencia / adjuntos)
└── done/                         # tickets aprobados por po-qa (los mueve po-qa)
```

- **`.po-config.yml`** guarda `project_key`, `default_issuetype` y las URLs por ambiente. Esquema en `reference.md` → "Esquema de `.po-config.yml`". Si falta un dato al crear (proyecto/tipo), preguntar y ofrecer guardarlo.
- **Ticket nuevo:** hasta que Jira asigne la clave, el dir es **provisional** (`NUEVO-<slug>/`); al publicar, renombrarlo a la clave real (`PQTCH-<n>/`).
- Todo esto es **local**: la skill no asume git ni trackea nada.

## Flujo

1. **Resolver proyecto y config.** Inferir `project_key` del nombre del directorio de trabajo; leer `.po-config.yml` si existe. La config se crea/completa **on-demand**: no hay setup previo — solo se pregunta el dato que falte cuando hace falta (p. ej. `default_issuetype` al momento de crear), se muestra el YAML exacto y se escribe/mergea tras confirmación (ver `reference.md` → "Creación on-demand e incremental"). Si el directorio no parece una carpeta de proyecto, avisar y confirmar dónde trabajar.
2. **Detectar modo.** Si el prompt trae una clave `[A-Z][A-Z0-9]+-\d+` → **enriquecer**: leer el ticket de Jira (`getJiraIssue`) y tomarlo como base. Si no → **nuevo**.
3. **Reproducir** (si hay URL + navegador). Abrir la URL, reproducir el síntoma, capturar pasos + capturas a `capturas/` + digest de consola/red. Evidencia observable, no diagnóstico de código (regla 3). Sin navegador → pedir capturas/pasos al PO.
4. **Clarificar** (regla 4). Preguntas de negocio, de a una, con recomendación: comportamiento esperado, frecuencia/alcance, usuarios afectados, prioridad, y lo que falte para AC verificables. En modo enriquecer, preguntar solo lo que el ticket base no responde.
5. **Redactar `ticket.md`** en el dir del ticket, en lenguaje no técnico, con la plantilla de `reference.md` → "Plantilla de `ticket.md`": título (con **prefijo de área**) · 📋 descripción/contexto (incluye el comportamiento actual/síntoma) · 🔁 pasos para reproducir · 📸 evidencia (capturas) · 🎯 objetivo · ✅ criterios de aceptación (`AC-1..N`, formalizan el comportamiento esperado) · 🛠️ pistas para el equipo (observado, opcional). Los encabezados llevan emoji (convención del equipo). No usar secciones separadas de "Resultado esperado/actual": el síntoma va en Descripción y lo esperado en los AC. **Proponer el prefijo de área** (`[Front]` / `[Back]` / `[Front/Back]`) a partir de los síntomas observables (ver `reference.md` → "Prefijo de área"); confirmarlo con el PO en el gate, nunca imponerlo.
6. **GATE — el PO revisa el borrador.** Presentar `ticket.md` (incluido el prefijo de área propuesto) y esperar aprobación. Si el PO corrige, actualizar y volver a ofrecer. No publicar sin aprobación. Si el área quedó `[Front/Back]`, avisar que en el gate de publicación se ofrecerá crear las dos subtareas.
7. **Publicar en Jira (write-safety STOP).** Sanitizar (regla 7). Mostrar recurso exacto (proyecto + `default_issuetype` para nuevo; clave para enriquecer) + contenido exacto, y esperar confirmación. Recién entonces: `createJiraIssue` (nuevo) o `editJiraIssue` (enriquecer). Adjuntar las capturas **por capacidad**; si la vía de Jira no soporta adjuntar archivos, dejarlas en `capturas/`, referenciarlas en el ticket y avisar al PO para que las adjunte a mano. Guardar en `ticket.md` la versión publicada; si es nuevo, renombrar el dir provisional a la clave real que devolvió Jira.
8. **Subtareas por área (solo si `[Front/Back]`).** Ofrecer crear dos subtareas del ticket recién publicado —una `[Front]` y otra `[Back]`—, cada una con un **resumen heredado del padre** (contexto + los AC que le tocan a esa área) y apuntando al padre. Crearlas **solo tras confirmación** del PO, cada una con su STOP de write-safety. Detalle del payload en `reference.md` → "Subtareas por área". Si el ticket es `[Front]` o `[Back]` solo, no se crean subtareas.

## Compatibilidad con Plan Mode / modos no mutantes

Si el entorno prohíbe mutaciones: ejecutar solo los pasos read-only (reproducir, clarificar, proponer el ticket de forma conversacional), **no** escribir `ticket.md` ni publicar en Jira, y avisar que la publicación queda bloqueada por el modo.

---

Detalle operativo (acceso a Jira, esquema de config, plantilla, sanitización) en `reference.md`.
