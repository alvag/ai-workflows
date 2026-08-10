# Contrato de ejecución de los despachos delegados — Fase 0

**Estado:** vigente · **Fecha:** 2026-08-09 · **Alcance:** el ecosistema de siete skills de este
repositorio y sus trece puntos de despacho de trabajo delegado.

Este documento es el **contrato** de la Fase 0 del programa de subagentes y perfiles de ejecución.
Describe el estado actual del ecosistema —no lo cambia—: fija el alcance comprometido del programa,
corrige las afirmaciones que se detectaron incorrectas nombrando el documento del que salen, y
registra como diferidas las decisiones doctrinales que todavía no se tomaron.

Su compañero es `scripts/matriz-despachos.json`, la matriz de despachos: el archivo-fuente donde
cada uno de los trece puntos declara sus propiedades con la ubicación del repositorio que las
respalda. Lo que este documento afirma sobre el ecosistema se apoya en esa matriz y es comprobable
con su verificador, `scripts/verificar-matriz-despachos.py`.

## Qué congela este documento y qué no

**Congela** tres cosas: hasta dónde llega el compromiso del programa, qué afirmaciones dejan de
valer y con qué las reemplaza este contrato, y qué preguntas quedan abiertas con la fase que las va
a responder.

**No congela** ninguna de las decisiones abiertas. Diferirlas es el resultado de esta fase, no un
pendiente que se olvidó: resolverlas requiere datos que las fases siguientes producen.

**No modifica el comportamiento de ninguna skill.** Ni sus prompts, ni sus permisos, ni sus gates.
Una corrección de este contrato dice qué es cierto sobre el ecosistema; no edita el documento que
corrige.

**Se lee por predicado y no solo por lectura humana.** Sus secciones tienen forma fija —un
encabezado y una tabla o un bloque estructurado por sección— y las verifica
`scripts/verificar-matriz-despachos.py`. Las tres primeras secciones que siguen —alcance,
correcciones y decisiones diferidas— las lee el modo `--contrato`:

```sh
python3 scripts/verificar-matriz-despachos.py --contrato \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

## Alcance comprometido

El programa tiene ocho fases, de la 0 a la 7. El compromiso de esta fase llega hasta la cuarta, que
es donde el roadmap ubica el criterio de finalización; las tres últimas son optimizaciones y cambios
doctrinales que solo se emprenden si las métricas de las anteriores los justifican.

| tramo | estado |
|---|---|
| Fases 0-4 | comprometido |
| Fases 5-7 | condicionado a las métricas de las fases anteriores |

Que las Fases 5-7 estén condicionadas no las descarta: las habilita un resultado medido, no una
decisión de calendario. Y al revés, terminar la Fase 4 alcanza para dar el programa por cerrado.

## Correcciones

Cada fila reemplaza una afirmación que **vive en el documento de la última columna**, y la cláusula
de supersesión nombra ese documento: un «este contrato prevalece» que no dice sobre qué no supersede
nada. La corrección no edita la fuente —este contrato no toca las instrucciones del repositorio ni
las siete skills—; establece qué vale a partir de acá.

| id | afirmación anterior | afirmación corregida | evidencia | supersesión | documento fuente |
|---|---|---|---|---|---|
| C-01 | `co-explore` explora/hipotetiza · `cross-review` revisa documentos de diseño · `cross-implement` escribe código · `systematic-debugging` arreglar bugs · code review sobre diffs | La revisión de diffs **sí tiene dueños declarados** en el ecosistema: cuatro de los trece puntos de despacho la ejercen —`sdd-flow-reviewer-por-task`, `sdd-flow-revision-final-de-diff`, `bitbucket-code-review-panel-de-revisores` y `bitbucket-code-review-validador-adversarial`— y en `cross-implement` la ejerce el conductor. La frontera enumera la actividad sin nombrar a su dueño, y de ahí sale la lectura de que no lo tiene. Lo que hoy no tiene dueño es una cosa más angosta: la revisión **cross-family** del diff local que produce `cross-implement`. | Los cuatro puntos declaran su ancla de invocación en `skills/`: `skills/sdd-flow/reference.md#prompt-del-subagente-reviewer`, `skills/sdd-flow/reference.md#revision-final-de-diff`, `skills/bitbucket-code-review/reference.md#invocar-al-revisor-read-only` y `skills/bitbucket-code-review/reference.md#validacion-adversarial-de-hallazgos-find-then-validate`. En los dos puntos de `cross-implement` la hoja de autoridad final vale `conductor`, y sus sedes son distintas: `skills/cross-implement/SKILL.md` para el implementador inicial y `skills/cross-implement/reference.md` para la ronda del fix loop. Las seis hojas están entre las que `verificar-matriz-despachos.py --anclas` resuelve contra su sede. | Este contrato prevalece sobre `CLAUDE.md` en este punto: la regla de fronteras reparte actividades entre skills, y la revisión de diffs queda asignada a los puntos de despacho que la matriz declara. | CLAUDE.md |

**La corrección es sobre la propiedad, no sobre los nombres que la regla cita.** Lo que reemplaza es
una cosa sola: que la regla enumera la revisión de diffs entre las actividades del ecosistema sin
asignarla a ninguna skill, cuando cuatro de los trece despachos hacen exactamente eso.

**Una segunda imprecisión detectada queda sin registrar como corrección, y conviene decir por qué.**
La exploración previa que precedió a este programa concluyó que un archivo `agents/*.yaml` alojado
dentro de una skill no define un subagente de Codex —es política de invocación de la skill, y las
definiciones de agente viven en otro lado—. Esa afirmación no aparece en ningún documento versionado
de este repositorio: vive solo en artefactos de trabajo bajo `.plans/`, que no forman parte del
árbol versionado. Una corrección cuya fuente no se puede resolver de forma independiente no es una
corrección, es una atribución sin respaldo, así que no entra a la tabla. Queda anotada acá para que
se registre cuando exista un documento versionado que la sostenga.

## Decisiones diferidas

Ninguna de estas decisiones se resuelve en esta fase: quedan **íntegramente diferidas**, cada una
con la fase que la va a tomar. Se derivan de la sección «Decisiones que requieren a Max» de la
propuesta doctrinal (`.plans/doctrina-implementador/propuesta.md`, artefacto de trabajo no
versionado), que es el único lugar donde esas preguntas están enumeradas.

Diferir no es postergar sin plazo: cada fila declara a dónde va, y la fase de destino sale de lo que
el roadmap del programa ubica en cada una.

| id | decisión | estado | fase de destino |
|---|---|---|---|
| D-01 | Si se adopta la invariante de posiciones —que al menos una de las dos, implementador o revisor del diff, la ocupe la otra familia— con su default, o si la regla vigente de `cross-implement` se conserva como está. | diferida | Fase 7 |
| D-02 | Qué obliga a hacer el conductor con los findings del revisor ajeno del diff. Sin respuesta, esa mitad de la invariante no tiene fuerza. | diferida | Fase 4 |
| D-03 | Si la elección se toma con la medición que clasifica los findings del conductor en ambigüedad del contrato y defecto de implementación, o si se decide por argumento. | diferida | Fase 4 |
| D-04 | Si se acepta que el autor del work order juzgue la ambigüedad de su propio work order, o si esa elección la toma el humano en el gate. | diferida | Fase 7 |
| D-05 | Si se habilita el nivel degradado en el que las dos posiciones son de la familia del conductor —con su acuerdo sin valor de evidencia— o si se conserva el salto actual del nivel pleno al inline. | diferida | Fase 7 |

Las tres que apuntan a la Fase 7 comparten motivo: esa fase es la que decide con datos si se habilita
la rama inversa, y es la última justamente porque hoy no existe un predicado independiente para que
el autor de un work order juzgue su propia ambigüedad. Las dos de la Fase 4 son las que el piloto de
revisión de diff responde al adjudicar y clasificar cada finding.

## Completitud del inventario de despachos

**La completitud de los trece puntos conserva adjudicación humana.** No se presenta como verificada,
y esta sección declara por qué.

El control automático existe y corre: `verificar-matriz-despachos.py --completitud` comprueba que
cada uno de los trece puntos tenga su ancla de invocación —los trece la tienen— y busca en el árbol
sitios de despacho que la matriz no haya inventariado. Su recibo se escribe en
`scripts/completitud-fase-0.json`, y el estado que declara hoy es `adjudicacion_humana`.

El motivo es acotado y está medido. El detector reconoce un despacho por las marcas de invocación de
CLI que sabe leer (`codex exec` y `claude -p`). **Ocho de los trece puntos anclan a secciones que no
contienen ninguna de esas marcas**, así que cómo despacha cada uno de esos ocho queda fuera del
alcance del detector y lo adjudica una persona:

- `skills/bitbucket-code-review/reference.md#validacion-adversarial-de-hallazgos-find-then-validate`
- `skills/co-explore/SKILL.md#el-loop-de-debate-modo-debate`
- `skills/co-explore/reference.md#fan-out-dual-y-orden-de-lanzamiento`
- `skills/cross-implement/reference.md#fix-loop`
- `skills/sdd-flow/SKILL.md#paso-analyze`
- `skills/sdd-flow/reference.md#prompt-del-subagente-reviewer`
- `skills/sdd-flow/reference.md#revision-final-de-diff`
- `skills/sdd-orchestrator/reference.md#prompt-del-agente-delegado`

El recibo registra además 64 sitios detectados en el árbol, de los cuales 44 caen fuera de toda
sección anclada por la matriz. **Que un sitio quede fuera del inventario no lo vuelve un punto de
despacho faltante:** la mayoría son documentación del comando, ejemplos y tablas de vías de
invocación. Distinguir un despacho real de su documentación es, otra vez, la adjudicación que el
detector no puede hacer solo.

Por eso el modo termina con código distinto de cero, y ese es su resultado honesto: informa que hay
44 sitios sin adjudicar, no que a la matriz le falte un punto. **La señal es el campo `estado` del
recibo, y la lista completa de zonas ciegas vive en el archivo**: la consola trunca esa lista a seis
de las ocho, así que un lector que se guíe por la pantalla declara menos de las que hay.
