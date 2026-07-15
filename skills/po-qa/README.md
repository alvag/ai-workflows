# po-qa

Skill orientada al **Product Owner que hace las veces de QA**. Valida que la entrega de un ticket cumple sus **criterios de aceptación**, ejercitándola en el navegador y produciendo un **pre-check** con veredicto AC por AC.

Pensada para un PO **sin acceso al código**: trabaja solo con **Jira + navegador**.

## Qué hace

```
prueba CLAVE-123 en DEV ──► leer ticket + spec ──► establecer QUÉ probar (AC) ──► abrir ambiente (login manual) ──► ejercitar cada AC ──► qa-reporte.md ──► veredicto al PO
```

- **Establece qué probar** leyendo el ticket de Jira y su **subtarea de spec** (la que publica `sdd-flow`); si no la encuentra o hay varias, se lo consulta al PO. Consolida los AC y arma la checklist.
- **Abre el ambiente** (DEV/QA/PROD) en el navegador. Si pide login, el **PO se autentica a mano** en su sesión real; sin credenciales guardadas.
- **Ejercita cada AC** y junta evidencia (capturas, pasos, consola/red).
- **Pre-check asistido:** da un veredicto AC por AC (✅ cumple / ❌ no cumple / ⚠️ no verificable) y una recomendación global. **Recomienda, pero decide el PO.**
- **Si pasa** → ofrece archivar el ticket (mover a `done/`). **Si no pasa** → solo si el PO autoriza, comenta en Jira **etiquetando al asignado** con las observaciones.

## Es un pre-check, no un juez

La skill nunca decide el rechazo o la aprobación formal por su cuenta, y **no publica nada en Jira sin autorización totalmente explícita del PO**, mostrando siempre el contenido exacto del comentario y esperando confirmación.

## Cuándo usarla

Invocación explícita (no dispara sola): `/po-qa`.

- `/po-qa prueba PQTCH-649 en DEV` (o `QA` / `PROD`).
- URL opcional en el prompt (tiene prioridad sobre la del ticket y la del `.po-config.yml`).

## Artefactos en disco

Comparte la carpeta del proyecto con [`po-ticket`](../po-ticket/SKILL.md):

```
/Jira/PQTCH/
├── .po-config.yml            # environments: dev/qa/prod (base URLs)
├── PQTCH-649/
│   ├── ticket.md             # lo publicado por po-ticket (si se usó)
│   ├── capturas/             # evidencia de la validación
│   └── qa-reporte.md         # ⟵ lo escribe po-qa (pre-check, AC por AC)
└── done/
    └── PQTCH-649/            # ⟵ po-qa mueve el dir acá si el PO aprueba
```

La **ubicación es el estado**: raíz = activo/en validación; `done/` = aprobado. No hay archivo de estado.

## Acceso a Jira

Por capacidad, con orden de preferencia: **1º el conector de Atlassian del Claude Code desktop**, **2º el MCP de Atlassian**. Sin ninguno, degrada: lee el `ticket.md` local y presenta el pre-check sin tocar Jira.

## Dependencias

Ninguna obligatoria, pero:

- **Navegador** (Chrome/Playwright/DevTools) — imprescindible para validar de verdad; sin él no hay QA real.
- Conector de Atlassian del desktop **o** MCP de Atlassian (leer ticket/subtareas, comentar).
- Tool de selección interactiva (tipo `AskUserQuestion`) para consultar al PO.

## Relación con otras skills

- **[`po-ticket`](../po-ticket/SKILL.md)** — creó el ticket con los AC que esta skill valida.
- **`sdd-flow`** — el developer implementó el ticket y publicó la subtarea de spec que esta skill lee.

## Archivos

- `SKILL.md` — el flujo y las reglas.
- `reference.md` — detección por capacidad, flujo de Jira, identificación de la spec, resolución del ambiente, plantilla del reporte, comentario de observaciones.
- `README.md` — este archivo.
