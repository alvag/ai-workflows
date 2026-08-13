# El acotado del diff por task — análisis de un flujo diferido

**Estado:** diferido, sin gate ni aprobación. Salió de la Fase 0.5 el 2026-08-12 ·
**Complejidad estimada:** complex

> **Qué es este documento.** No es una spec aprobada ni un plan: es el **depósito de lo que se
> retiró** de la Fase 0.5 del roadmap de subagentes, versionado para que no se pierda y para que
> quien lo retome no vuelva a descubrir lo mismo. Se escribió como `spec.md` de un flujo SDD que
> nunca abrió su gate; vive acá porque `.plans/` es local y untracked, y un análisis que solo existe
> en una máquina no está conservado. El roadmap lo declara fuera de fase en
> `docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md` → Fase 0.5.

## Por qué salió

Estaba dentro de `dossier-prompts` como AC-5, AC-6 y AC-13. Tres razones, en orden de peso:

1. **No es sobre el dossier.** Acotar el diff es cómo el conductor **valida lo que volvió**; el
   dossier es **qué contexto recibe** el agente. Entraron juntos por un entregable del roadmap, pero
   no comparten sujeto. **Esta es la razón de peso.**
2. **Generaba una crítica desproporcionada y creciente.** 3 de 13 AC (23%) produjeron **10 de 31
   findings** (32%) entre la revisión de la spec y la del plan, subiendo de 29% a 35%. Y **3 de los 6
   findings del plan eran sobre su aparato de verificación**, no sobre la política: el arnés
   empezando a comerse el cambio.
3. **Una razón que NO vale, y que conviene no repetir al retomarlo.** El primer argumento fue «un
   script Python no prueba que el conductor siga la política». Es cierto y **no distingue pathspec
   del resto de la fase**: `validar-para-despacho` y la transcripción del contrato también son prosa
   que ejecuta un agente. Si ese argumento sacara a pathspec, sacaría a la fase entera. La brecha es
   real pero se **declara** —dos niveles de evidencia: conformidad estática y conducta diferida—, no
   se usa para mover trabajo de lugar.

## Qué contiene, ya trabajado

### La política de pathspec, cerrada por forma

| Forma en `Archivos` | Resultado |
|---|---|
| `ruta/archivo.py` | pathspec literal |
| `ruta/dir/` (con barra final) | **recursivo** bajo ese directorio |
| `ruta/dir` (sin barra) que existe como directorio | **recursivo**; se normaliza a la forma con barra |
| `ruta/*.py`, glob | **se expande** contra el árbol; si no matchea nada → error `glob_vacio` |
| `ruta/archivo.py:120-160` (rango de línea) | se **descarta el rango** y queda el path |
| path que no existe **y** la task no lo crea | error `path_inexistente` |
| rename / delete | se incluyen **ambos lados** (origen y destino) |
| path que escape del working dir (`../`, absoluto) | error `path_fuera_de_alcance`, **bloquea** |

Más: baseline capturado **antes** del despacho, inclusión de **archivos nuevos no trackeados** —que
`git diff -- <paths>` no muestra— y la comparación contra `git status --porcelain` de la regla 8.

### Los findings que este flujo hereda sin resolver

| ID | Qué falta |
|---|---|
| `PATHSPEC-ORACLE-NO-PRODUCTION-SUBJECT` | **el problema de fondo**: qué sujeto verificable tiene una política que ejecuta un agente leyendo prosa. Hay que resolverlo **antes** de escribir AC, no después |
| `PATHSPEC-DECLARATION-GRAMMAR` | cómo una task **declara** que crea, renombra o borra un path; «ambos lados» no significa nada para un delete, y un glob expandido antes del despacho no puede incluir archivos futuros |
| `TASK-DELTA-SEMANTICS` | qué estado captura el baseline y cómo se resta: working tree previamente sucio, staged changes, cambios de modo, binarios, y un archivo tocado por dos tasks |
| `UNDECLARED-PATH-OUTCOME` | qué pasa con paths tocados **fuera** del pathspec: hoy pueden quedar sin revisión y la task marcarse completa igual |
| `PATHSPEC-AUTOTEST-NONVACUITY` | el autotest debe exigir control verde previo, mutación efectivamente aplicada, señal roja **por su causa**, y restauración — el patrón que los verificadores del repo ya usan |
| `PATHSPEC-VERIFIER-LIFECYCLE` | si nace un verificador: su trigger documentado en `CLAUDE.md`, sus códigos sanos, y su eliminación en el rollback |

### Lo que ya está decidido y no hay que rediscutir

- El reviewer **hoy** recibe `FILES` del implementer y `git diff -- <paths>`
  (`reference.md:865-873`). `dossier-prompts` **no lo cambia**, así que este flujo parte de ese
  estado, no de uno intermedio.
- El repo ya registró que en una corrida real hubo **cuatro reportes `FILES` consecutivos sin
  entregar**. Ese es el problema que motivó acotar por `Archivos`, y sigue vivo.

## Precondición para retomarlo

Resolver primero `PATHSPEC-ORACLE-NO-PRODUCTION-SUBJECT`. Si la respuesta es que **no hay** sujeto
verificable para una política de prosa, entonces la pregunta correcta no es «cómo verifico esta
tabla» sino **si el acotado del diff debe ser prosa del conductor o una capacidad ejecutable de otra
sede** — y esa es una decisión de doctrina, no de este flujo.
