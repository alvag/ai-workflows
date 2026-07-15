# po-ticket

Skill orientada al **Product Owner** para redactar **tickets de Jira claros y accionables** a partir de un problema mal descrito. Convierte "esto no anda, mirá esta URL" en un ticket con contexto, objetivo y **criterios de aceptación verificables**, en lenguaje **no técnico**.

Pensada para un PO **sin acceso al código ni al repo**: trabaja solo con **Jira + navegador**.

## Qué hace

```
descripción + URL + contexto ──► reproducir en navegador ──► clarificar (negocio) ──► ticket.md ──► GATE (PO revisa) ──► publicar en Jira
     (o CLAVE-123 para enriquecer)     (evidencia observable)        (diálogo)                                          (write-safety STOP)
```

- **Dos modos:** crear un ticket nuevo (desde descripción + URL + contexto), o **enriquecer** uno existente ambiguo (pasando su clave, p. ej. `PQTCH-649`).
- **Reproduce el error** en el navegador y captura **evidencia observable** (pasos, capturas, consola/red). No diagnostica a nivel código (eso lo hace el developer luego con `sdd-flow`): lo observado se rotula como "pistas para el equipo".
- **Clarifica en diálogo de negocio** antes de redactar, sin inventar contexto.
- **Estructura estándar** con encabezados con emoji y **prefijo de área** en el título (`[Front]` / `[Back]` / `[Front/Back]`); si es `[Front/Back]`, ofrece crear las subtareas por área.
- **Publica en Jira** tras confirmación (write-safety), adjuntando capturas por capacidad.

## Cuándo usarla

Invocación explícita (no dispara sola): `/po-ticket`.

- `/po-ticket <descripción + URL de reproducción + contexto>` → crea un ticket nuevo.
- `/po-ticket PQTCH-649` → enriquece/reescribe un ticket existente ambiguo.

## Estructura del ticket

```
# [Front|Back|Front/Back] <título>
## 📋 Descripción / Contexto     (incluye el síntoma / comportamiento actual)
## 🔁 Pasos para Reproducir
## 📸 Evidencia                   (capturas)
## 🎯 Objetivo
## ✅ Criterios de Aceptación     (AC-1..N, observables; formalizan lo esperado)
## 🛠️ Pistas para el Equipo      (opcional; observado, no diagnóstico de código)
```

Los AC son la única fuente de "qué debe cumplirse" (no se duplican como "resultado esperado/actual"), y son los que después valida [`po-qa`](../po-qa/SKILL.md).

## Artefactos en disco

El directorio de trabajo es la carpeta del proyecto; su nombre es la clave de proyecto de Jira.

```
/Jira/PQTCH/                 # nombre del dir = clave de proyecto (PQTCH)
├── .po-config.yml           # project_key, default_issuetype, URLs por ambiente
├── PQTCH-649/
│   ├── ticket.md            # lo publicado (o a publicar) en Jira
│   └── capturas/            # screenshots (evidencia / adjuntos)
└── done/                    # tickets aprobados por po-qa (los mueve po-qa)
```

Todo es **local**: la skill no asume git ni trackea nada.

## Acceso a Jira

Por capacidad, con orden de preferencia: **1º el conector de Atlassian del Claude Code desktop**, **2º el MCP de Atlassian** configurado. Si no hay ninguno, degrada: deja el `ticket.md` como borrador para que el PO lo cree/actualice a mano.

## Dependencias

Ninguna obligatoria. Aprovecha, si están:

- Conector de Atlassian del desktop **o** MCP de Atlassian (leer/crear/editar tickets).
- Tool de navegador (Chrome/Playwright/DevTools) para reproducir y capturar evidencia.
- Tool de selección interactiva (tipo `AskUserQuestion`) para clarificar.

Sin ellas, degrada: borrador local, o pedir capturas/pasos al PO.

## Relación con otras skills

- **`sdd-flow`** — el developer toma el ticket y lo lleva a implementación con SDD.
- **[`po-qa`](../po-qa/SKILL.md)** — el PO valida la entrega contra los AC de este ticket.

## Archivos

- `SKILL.md` — el flujo y las reglas.
- `reference.md` — detección por capacidad, flujo de Jira, esquema de `.po-config.yml`, plantilla del ticket, subtareas por área, sanitización, adjuntos.
- `README.md` — este archivo.
