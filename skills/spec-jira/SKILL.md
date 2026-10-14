---
name: spec-jira
description: >-
  Escribe la spec de un cambio (problema, alcance y criterios AC-n verificables) en el documento
  de la feature, la publica en una subtarea de Jira para que la apruebe el PO o el TL y concilia lo
  que vuelve: espera la aprobación o implementa en paralelo y ajusta solo los criterios que cambian.
  Usar ante “crea la spec”, “arma la spec de <TICKET>”, “sube la spec a Jira”, “ya aprobaron la
  spec” o “revisa las observaciones del PO”, o mediante /spec-jira. Es la versión liviana de
  publish-spec de sdd-flow: no escribe plan ni tasks de SDD ni hace code review. No invocarla
  espontáneamente: solo ante pedido explícito del usuario.
argument-hint: "[<TICKET> | retoma <feature> | estado <feature>]"
---

# spec-jira

Spec con aprobación externa, sin el resto de SDD. La implementación sigue el flujo del runtime
(en gentle-shell, ODD); esta skill solo produce la spec, la publica y concilia los cambios.

## Reglas duras

1. **Toda escritura en Jira se confirma antes.** Mostrar el recurso exacto (proyecto, issue
   padre o subtarea) y el contenido exacto, y esperar el sí. Sin excepción.
2. **Nada local sale del repo.** Antes de publicar se aplica la sanitización de `reference.md` →
   "Sanitización".
3. **Cada criterio es un `AC-n` y a la vez un `S<n>`** con el mismo número, y declara su origen:
   `pedido`, `clarify` o `repositorio`. Un criterio sin origen no entra a la spec.
4. **En modo A no se escribe código** hasta que el usuario confirme la aprobación.
5. **Sin MCP de Jira con escritura, se degrada y no se bloquea:** se entrega el texto listo para
   pegar y se sigue.

## Pasos

1. **Contexto.** Si el pedido trae una clave `[A-Z][A-Z0-9]+-\d+`, leer el issue por el MCP de
   Atlassian (`reference.md` → "Operaciones de Jira"). Sin MCP, pedir que peguen el resumen.
   Explorar el código lo justo para escribir criterios verificables.
2. **Dudas.** Si el código no responde una duda que cambia el diseño, preguntar **una por vez**,
   con la respuesta recomendada primero, y registrarla como `Q<n>`.
3. **Spec local.** Escribir o actualizar `odd/tasks/<feature>.md` con la plantilla de
   `reference.md` → "Documento de la feature", **incluido el resumen para PO**, en lenguaje de
   negocio y con un punto por cada `AC-n`. **STOP:** presentar las dos partes, el resumen y la
   definición técnica, y esperar la aprobación local.
4. **Publicar.** Armar el texto copiando las dos partes ya aprobadas (`reference.md` → "Texto de
   la subtarea"), sanitizarlo y aplicar la regla 1. Crear la subtarea `SPEC: <título corto>` bajo el ticket. Registrar en el
   documento la clave, la URL y `estado: awaiting`.
5. **Modo.** Preguntar siempre, con estas dos opciones:
   - **A, esperar al PO:** se termina acá; se retoma con «ya aprobaron» o «revisa el ticket».
   - **B, implementar en paralelo:** se sigue con las tareas del documento, ligadas a sus `S<n>`.
6. **Conciliar.** Al retomar, o en modo B antes de cerrar, leer el estado y los comentarios
   nuevos de la subtarea y resolver con la tabla de `reference.md` → "Qué hacer con lo que
   vuelve". Si la spec cambia, actualizar la descripción y dejar **un** comentario consolidado
   (`reference.md` → "Comentario de ajuste"), con la regla 1 en cada escritura.

## Salida

Devolver: ruta del documento, `AC-n` vigentes con su origen, clave y URL de la subtarea (o «texto
para pegar»), modo elegido, estado (`awaiting | changes-requested | approved`) y qué `S<n>` o
tareas se reabrieron.

## Referencias

- `reference.md` — plantillas, operaciones de Jira, sanitización y tabla de conciliación. Leer la
  sección que nombra cada paso, en el momento de ese paso.
- `../sdd-flow/SKILL.md` → "Paso `publish-spec`": la versión SDD completa de este gate.
