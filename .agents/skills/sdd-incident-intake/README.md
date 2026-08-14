# sdd-incident-intake

Admisión de incidentes: convierte una entrada del registro de incidentes de las skills SDD en un
flujo `sdd-flow` corriendo en su propio worktree, y recién entonces la retira del registro.

## El problema que resuelve

El registro de incidentes (`../../../.plans/incidentes-skills.md`) es una bandeja de entrada. Se llena solo —
cada corrida que tropieza con un defecto de las skills deja su registro — y **no se vacía solo**.
Vaciarlo a mano tiene cuatro trampas que se repiten:

1. **El incidente se despacha sin verificar.** Lo escribió otra corrida sobre un árbol que pudo
   cambiar. A veces el defecto sigue pero el mecanismo se refactorizó, y el arreglo se diseña contra
   una descripción vencida.
2. **Se agrupan por skill en vez de por diff.** Dos incidentes de la misma skill en fases distintas
   producen un diff que hace dos cosas y una revisión que no puede juzgar ninguna.
3. **Se retiran antes de despachar.** Si el despacho falla, se perdió la única copia.
4. **El worktree nace sin el entorno.** Git no versiona el config del flujo SDD, así que el worktree
   no lo hereda — y `sdd-flow` no falla: cree que el proyecto no está inicializado y arranca un
   wizard que nadie pidió.

## Qué hace

```
Verificar → agrupar → despachar → confirmar arranque → retirar
```

1. Lee el registro entero, incluidas sus reglas de formato.
2. Verifica cada afirmación del incidente contra el árbol real, y busca activamente dónde el árbol ya
   cambió. Eso se convierte en una **decisión abierta** para el flujo, sin pre-decidirla.
3. Busca los incidentes que se resolverían en el mismo diff — el criterio es la superficie editable,
   no la skill.
4. **Gate:** presenta la agrupación, la verificación y los descartados. Sin respuesta no avanza.
5. Crea el worktree con Orca, **lo siembra** con la configuración ignorada que el flujo necesita,
   escribe un dossier autocontenido y despacha el flujo — confirmando que arrancó de verdad.
6. Retira los incidentes tomados del índice **y** del cuerpo, y comprueba que no quedaron residuos.

## Cuándo usarla

- "toma un incidente de `<ruta>`"
- "procesa los incidentes de skills"
- "abrí un flujo para el incidente de `<fecha>`"
- `/sdd-incident-intake <ruta-del-registro> [claude|codex]`

**No se dispara sola.** Solo ante pedido explícito.

## Cuándo NO usarla

| Situación | Skill correcta |
|---|---|
| Corregir la skill defectuosa | El `sdd-flow` que esta despacha. Ésta prepara, no arregla |
| Registrar un incidente nuevo | Es una regla del `../../../CLAUDE.md` del repo, no una skill |
| Criticar una spec/plan/tasks | `cross-review` |
| Delegar la implementación | `cross-implement` |
| Explorar terreno o buscar causa raíz | `co-explore` |

## Parámetros

| Parámetro | Default |
|---|---|
| `registro` | **Obligatorio.** Ruta al archivo de incidentes o al directorio que lo contiene |
| `agente` | La familia que conduce la sesión actual (`claude` o `codex`) |
| `incidente` | El de severidad más alta; a igualdad, el más antiguo |
| `repo_destino` | El repo de skills donde vive esta skill |

`registro` y `repo_destino` **son repos distintos por diseño**: el registro vive donde el defecto se
observó, el código a corregir vive en el repo de skills.

## Requisitos

- **Orca** corriendo, con el `repo_destino` agregado (`orca repo list`).
- **`sdd-flow`** instalada para la familia elegida: en Claude se invoca `/sdd-flow`, en Codex
  `$sdd-flow` — y ahí se resuelve desde `~/.agents/skills/sdd-flow`.
- Un registro de incidentes con el formato que declara su propia cabecera.

## Instalación

```bash
ln -s "$PWD/skills/sdd-incident-intake" ~/.claude/skills/sdd-incident-intake
ln -s "$PWD/skills/sdd-incident-intake" ~/.agents/skills/sdd-incident-intake   # cross-runtime
```

## Estructura

| Archivo | Para quién |
|---|---|
| `SKILL.md` | El agente, en cada corrida: el invariante, los seis pasos, red flags |
| `reference.md` | El agente, cuando `SKILL.md` lo manda: comandos de Orca, criterio de siembra, plantilla del dossier, mecánica del despacho, retiro y fallas |
| `../../../README.md` | Humanos. No se lee en ejecución |
