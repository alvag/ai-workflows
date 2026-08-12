# Recorte literal de `dossier-arnes/spec.md` — el insumo de `--consumidor`

**Generado, no escrito.** Es la copia literal del encabezado de contrato, del enunciado de
AC-11 y de la nota histórica que lo sigue, tal como están en la spec del consumidor. Existe
porque esa spec vive bajo `.plans/`, que no viaja en un clon: sin el recorte, el autotest de
`--consumidor` no tendría corpus. Que siga siendo la copia vigente lo comprueba el propio
autotest contra el archivo real cuando está presente.
**Contrato compartido:** `contrato-extraccion.md`, hermano de este archivo ·
`sha256 224167cf9d48ee40bc0a81e521051a0fa2ae047e2fff748cfa57c3e05555dadb`.

- **AC-11 — Control positivo sobre la COBERTURA del corpus real, con conjunto esperado independiente:**
  Given el corpus congelado de AC-3, When corre el censo, Then el arnés reporta, **por flujo y por
  fuente de R2**, cuántas tasks declaran cobertura y cuántas resolvieron, y **falla** si: (a) el
  total global de declaraciones resueltas es **cero**; (b) alguna fuente de R2 resuelve **cero** en
  todo el corpus; o (c) el conjunto resuelto **pierde** tasks respecto de un conjunto esperado
  congelado, producido por un **camino independiente del parser**. Una task sin AC solo es admisible
  con su causa del enum de AC-5 **nombrada**.

  > **El método lo fija `dossier-oraculo`, que es su dueño — esta spec no lo prescribe.** La
  > redacción anterior decía «(un barrido textual mínimo, no la gramática de R1–R2)», y eso fijaba el
  > *cómo* en un artefacto ajeno. **Se midió y ese camino no era el bueno:** una derivación mecánica
  > comparte autor con el parser, así que reproduce su mismo punto ciego. El método vigente es
  > **detección independiente y adjudicación** —`dossier-oraculo` → AC-6, AC-8 y AC-9—: un worker de
  > la otra familia detecta sin el contrato, el conductor compara contra el predicado y adjudica cada
  > desacuerdo una vez, como `punto_ciego` o `exclusion_deliberada`. Corregido el 2026-08-12; el dato
  > está en `.plans/dossier-oraculo/sondeo-productor-independiente.md`.
