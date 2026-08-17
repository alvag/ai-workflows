# sdd-incident-intake

Admisión de incidentes: convierte una entrada del registro de incidentes de las skills SDD en un
flujo `sdd-flow` corriendo en su propio worktree, y recién entonces la retira del registro.

## El problema que resuelve

El registro de incidentes (`.plans/incidentes-skills.md` del proyecto donde ocurrió) es una bandeja
de entrada. Se llena solo —
cada corrida que tropieza con un defecto de las skills deja su registro — y **no se vacía solo**.
Vaciarlo a mano tiene cinco trampas que se repiten:

1. **El incidente se despacha sin verificar.** Lo escribió otra corrida sobre un árbol que pudo
   cambiar. A veces el defecto sigue pero el mecanismo se refactorizó, y el arreglo se diseña contra
   una descripción vencida.
2. **Se agrupan por skill en vez de por diff.** Dos incidentes de la misma skill en fases distintas
   producen un diff que hace dos cosas y una revisión que no puede juzgar ninguna.
3. **Se retiran antes de despachar.** Si el despacho falla, se perdió la única copia.
4. **Se despacha sin mirar el remoto.** El `grep` mira el árbol local: no ve el commit que `origin`
   ya tiene ni el PR abierto que está tocando esas mismas líneas. Y el worktree nace de `origin`, así
   que el flujo arranca sobre una base que el veredicto nunca midió.
5. **El worktree nace sin el entorno.** Git no versiona el config del flujo SDD, así que el worktree
   no lo hereda — y `sdd-flow` no falla: cree que el proyecto no está inicializado y arranca un
   wizard que nadie pidió.

## Qué hace

```
Verificar → agrupar → mirar aguas arriba → despachar → confirmar arranque → retirar
```

1. Lee el registro entero, incluidas sus reglas de formato.
2. Verifica cada afirmación del incidente contra el árbol real, y busca activamente dónde el árbol ya
   cambió. Eso se convierte en una **decisión abierta** para el flujo, sin pre-decidirla.
3. Busca los incidentes que se resolverían en el mismo diff — el criterio es la superficie editable,
   no la skill.
4. **Mira aguas arriba:** con `fetch`, cruza la superficie del incidente contra los commits que
   `origin` tiene y el local no, y contra los PRs abiertos. Un defecto ya resuelto arriba no se
   despacha; un PR abierto sobre los mismos archivos va al gate.
5. **Gate:** presenta la agrupación, la verificación, el estado aguas arriba y los descartados. Sin
   respuesta no avanza.
6. Crea el worktree con Orca, **lo siembra** con la configuración ignorada que el flujo necesita,
   escribe un dossier autocontenido y despacha el flujo — confirmando que arrancó de verdad.
7. Retira los incidentes tomados del índice **y** del cuerpo, y comprueba que no quedaron residuos.

## Cuándo usarla

- "toma un incidente de `<ruta>`"
- "procesa los incidentes de skills"
- "abrí un flujo para el incidente de `<fecha>`"
- "revisá 3 incidentes" — abre 3 flujos, uno por vez
- `/sdd-incident-intake <ruta-del-registro> [claude|codex]`

**No se dispara sola.** Solo ante pedido explícito.

## Cuándo NO usarla

| Situación | Skill correcta |
|---|---|
| Corregir la skill defectuosa | El `sdd-flow` que esta despacha. Ésta prepara, no arregla |
| Registrar un incidente nuevo | Es una regla del archivo de instrucciones del repo, no una skill |
| Criticar una spec/plan/tasks | `cross-review` |
| Delegar la implementación | `cross-implement` |
| Explorar terreno o buscar causa raíz | `co-explore` |

## Parámetros

| Parámetro | Default |
|---|---|
| `registro` | **Obligatorio.** Ruta al archivo de incidentes o al directorio que lo contiene |
| `cantidad` | **1.** Cuántos **flujos** abrir. Cuenta worktrees, no incidentes: uno que agrupa dos consume un cupo |
| `agente` | La familia que conduce la sesión actual (`claude` o `codex`) |
| `incidente` | El de severidad más alta; a igualdad, el más antiguo |
| `repo_destino` | El repo de skills donde vive esta skill |

`registro` y `repo_destino` **son repos distintos por diseño**: el registro vive donde el defecto se
observó, el código a corregir vive en el repo de skills.

## Requisitos

- **Orca** corriendo, con el `repo_destino` agregado (`orca repo list`).
- Acceso al **remoto** del `repo_destino` para el `fetch` del paso 4. Para los PRs abiertos, `gh`
  autenticado (GitHub) o el MCP `bb_*` (Bitbucket): si no hay ninguno, el chequeo se reporta como
  no comprobado en vez de darse por limpio.
- **`sdd-flow`** instalada para la familia elegida: en Claude se invoca `/sdd-flow`, en Codex
  `$sdd-flow` — y ahí se resuelve desde `~/.agents/skills/sdd-flow`.
- Un registro de incidentes con el formato que declara su propia cabecera.

## Instalación

Vive **solo en este repo**, sin symlinks al home. Está en **dos** directorios, con contenido
idéntico:

| Ruta | Para qué |
|---|---|
| `.agents/skills/sdd-incident-intake/` | **La sede canónica.** El alias cross-runtime que reconocen ambas familias; es de donde la toma Codex |
| `.claude/skills/sdd-incident-intake/` | La copia que hace que Claude Code la vea a nivel proyecto |

> **Son dos copias reales, no un symlink, y la razón es Windows.** Antes `.claude/skills` era un
> symlink relativo a `../.agents/skills`, que no duplicaba nada. Pero un symlink versionado no
> sobrevive el checkout en Windows: Git para Windows trae `core.symlinks=false` por default, así que
> materializa el enlace como **un archivo de texto de 17 bytes** con la ruta destino adentro. Claude
> Code busca un directorio, encuentra un archivo, y la skill no carga — **sin ningún error**. Activar
> `core.symlinks` no alcanza por sí solo: crear symlinks en Windows exige además el privilegio, que un
> usuario sin permisos de administrador solo tiene con el Modo de desarrollador activado.
>
> **Editar una sola copia es una divergencia silenciosa.** Nada la detecta hoy. Al tocar la skill, el
> cambio va en `.agents/` y después se copia:
>
> ```sh
> cp -R .agents/skills/sdd-incident-intake/. .claude/skills/sdd-incident-intake/
> diff -r .agents/skills/sdd-incident-intake .claude/skills/sdd-incident-intake   # sin salida = ok
> ```

## Estructura

| Archivo | Para quién |
|---|---|
| `SKILL.md` | El agente, en cada corrida: el invariante, los siete pasos, red flags |
| `reference.md` | El agente, cuando `SKILL.md` lo manda: comandos de Orca, criterio de siembra, plantilla del dossier, mecánica del despacho, retiro y fallas |
| `README.md` | Humanos. No se lee en ejecución |
