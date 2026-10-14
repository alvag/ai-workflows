---
name: pr-bitbucket
description: >-
  Crea o actualiza el PR de Bitbucket de la rama actual con un formato fijo: ticket y link a la
  spec, problema, solución y los criterios AC-n como checklist, sacados del documento de la
  feature; carga los revisores desde la memoria o los pregunta. Siempre muestra el PR antes de
  crearlo. Usar ante “abre el PR”, “crea el PR”, “pull request” o mediante /pr-bitbucket. No
  pushea, no aprueba ni mergea, y no es code review: eso es bitbucket-code-review. No invocarla
  espontáneamente: solo ante pedido explícito del usuario.
argument-hint: "[<rama destino>]"
---

# pr-bitbucket

Crea el PR; no hace push, no aprueba ni mergea. Es la versión liviana del paso `open-pr` de
`sdd-flow`, sin `.specify/`.

## Reglas duras

1. **Sin confirmación no se escribe en Bitbucket.** Antes de crear o actualizar, mostrar la vista
   previa completa (`reference.md` → "Vista previa") y esperar el sí.
2. **La rama tiene que estar pusheada.** Si no lo está, o tiene commits sin pushear, parar y
   avisar; el push es decisión del usuario.
3. **Los revisores nunca se adivinan:** salen de la memoria o del usuario, sin incluir al autor.
4. **Nada local sale del repo:** se quita lo que dice `reference.md` → "Sanitización".
5. **Sin MCP de Bitbucket, se degrada y no se bloquea:** se entregan el título, la descripción y
   las ramas para crear el PR a mano.

## Pasos

1. **Ubicar.** Derivar `<workspace>/<repo>` del remote, la rama origen y la destino: el argumento,
   si se dio; si no, la rama por defecto del remote. Comprobar la regla 2 (`reference.md` →
   "Comandos").
2. **Duplicados.** Buscar un PR abierto desde la misma rama. Si hay uno, ofrecer actualizarlo en
   lugar de crear otro.
3. **Contenido.** Título: el asunto del commit más reciente de la rama. Descripción: la plantilla
   de `reference.md` → "Descripción", armada desde `odd/tasks/<feature>.md`. Sin documento, salen
   del diff y de los commits, y la vista previa avisa que falta el checklist de criterios.
4. **Revisores.** Seguir `reference.md` → "Revisores": memoria, después el usuario, y guardar.
5. **Vista previa y confirmación** (regla 1). Si el usuario pide cambios, aplicarlos y volver a
   mostrarla.
6. **Crear o actualizar** el PR. Si en el documento hay una cabecera, agregarle `PR: <url>`.

## Salida

Devolver: URL e ID del PR, si se creó o se actualizó, las ramas origen y destino, los revisores y
lo que quedó degradado: sin MCP, sin documento o sin revisores.

## Referencias

- `reference.md` — comandos, operaciones del MCP, plantilla, revisores, sanitización y vista
  previa. Cada paso nombra la sección que lee.
- `../sdd-flow/reference.md` → "Apertura de PR (opcional, tras push)": la versión SDD.
