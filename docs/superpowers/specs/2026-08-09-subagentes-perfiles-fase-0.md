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

## Los tres ejes

Una corrida delegada admite **tres preguntas distintas**, y este contrato les da **tres vocabularios
separados**: qué pasó con la corrida *como proceso*, si lo que entregó *satisface su contrato de
salida*, y qué dice el trabajo entregado *sobre el objeto de la delegación*. Nombrar los ejes y
separarlos es el aporte de este documento; los literales no se inventan acá: cada uno sale de una
sección de `skills/` que ya lo usa, y su fila declara cuál.

Los tres se leen con el modo `--ejes`, que compara cada tabla contra el inventario normativo por
igualdad exacta y resuelve además el puntero de cada literal contra el árbol:

```sh
python3 scripts/verificar-matriz-despachos.py --ejes \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

Tres reglas de escritura cierran las tres formas de fusionar los ejes, que son las que este contrato
existe para impedir:

1. **Cada literal se escribe con su namespace** —`<eje>.<literal>`—. Un token desnudo citado en
   cualquier otra sección no dice de qué eje es, y esa ambigüedad es el primer paso de la fusión.
2. **Ningún eje declara un literal que pertenece a otro.** Usar el enum de un eje en el lugar de
   otro los funde sin decirlo: la tabla sigue pareciendo bien formada y la pregunta que ese eje
   contestaba deja de tener respuesta.
3. **No existe un enum unión.** Un vocabulario que responda las tres preguntas con un solo valor no
   responde ninguna: cada respuesta pisa a las otras dos.

### Eje: ciclo de vida operativo

Qué pasó con la corrida **como proceso**, con independencia de lo que haya entregado. Es el eje del
transporte: se pronuncia sobre la espera del conductor y sobre el cierre del crudo, nunca sobre el
contenido.

| literal | tipo | sede | significado |
|---|---|---|---|
| `ciclo_de_vida_operativo.resultado_entregado` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | la espera terminó con un terminal adjudicable, y eso habilita evaluar el retiro del sobre |
| `ciclo_de_vida_operativo.corte_presupuesto` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | venció el presupuesto que el conductor se puso a sí mismo; lo único que terminó es la espera y la corrida sigue activa |
| `ciclo_de_vida_operativo.error` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | terminal comprobado de fallo: se sabe qué pasó, así que se puede adjudicar en vez de tratarlo como incierto |
| `ciclo_de_vida_operativo.cancelacion` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | terminal por decisión, con un segundo componente que dice si el cese se confirmó o quedó incierto |
| `ciclo_de_vida_operativo.UNAVAILABLE` | terminal_sin_entrega | `skills/co-explore/reference.md#estados-del-worker` | el worker no respondió o no se pudo lanzar, así que no hay reporte que validar; lleva causa de un enum cerrado |
| `ciclo_de_vida_operativo.done` | marcador_de_cierre | `skills/co-explore/reference.md#senal-de-finalizacion` | el crudo cerró con su marcador de fin; pertenece al transporte y no al contenido, y tras el split no queda en ninguno de los dos archivos |

### Eje: validez del reporte entregado

Dado que el worker **entregó** algo, si eso satisface el contrato de salida. El eje no se pronuncia
sobre el mérito de lo entregado —eso es el tercero— ni sobre cómo terminó el proceso —eso es el
primero—: solo sobre si el artefacto pasa sus predicados.

| literal | tipo | sede | significado |
|---|---|---|---|
| `validez_del_reporte_entregado.READY` | clase_de_validez | `skills/co-explore/reference.md#estados-del-worker` | el reporte pasa **todos** los predicados del contrato de salida, sin excepciones |
| `validez_del_reporte_entregado.INVALID` | clase_de_validez | `skills/co-explore/reference.md#estados-del-worker` | respondió, y lo que entregó falla alguno de esos predicados |
| `validez_del_reporte_entregado.clarification-needed` | clase_de_validez | `skills/co-explore/reference.md#clarification-needed-el-cuarto-estado` | frenó ante una ambigüedad que le impedía seguir, entregó lo que alcanzó a mapear y adosó la pregunta |

### Eje: resultado semántico

Qué dice el trabajo entregado **sobre el objeto de la delegación**. Un reporte válido puede traer
cualquiera de estos valores; uno inválido no trae ninguno, porque no hay de dónde leerlo.

| literal | tipo | sede | significado |
|---|---|---|---|
| `resultado_semantico.APPROVED` | veredicto_de_revision | `skills/cross-review/reference.md#veredicto-derivado` | el ledger arbitrado no deja ningún finding en estado no terminal: la revisión convergió |
| `resultado_semantico.REVISE` | veredicto_de_revision | `skills/cross-review/reference.md#veredicto-derivado` | queda al menos un finding sin resolver, o solo terminales con alguna disputa que abre el gate humano |
| `resultado_semantico.done` | estado_de_task | `skills/sdd-flow/reference.md#prompt-del-subagente-por-task` | el subagente despachado por task ejecutó esa task tal como estaba escrita |
| `resultado_semantico.failed` | estado_de_task | `skills/sdd-flow/reference.md#prompt-del-subagente-por-task` | el subagente se bloqueó y lo dice con su razón, en lugar de improvisar otro enfoque |
| `resultado_semantico.verified` | estado_de_repo_delegado | `skills/sdd-orchestrator/reference.md#prompt-del-agente-delegado` | el agente delegado por repo cerró su parte con los criterios de aceptación cubiertos |
| `resultado_semantico.PARTIAL` | cierre_de_unidad | `skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo` | parte la hizo el implementador y parte la terminó el conductor por takeover al agotar las rondas de fix |
| `resultado_semantico.BLOCKED` | cierre_de_unidad | `skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo` | la fila nunca se pudo medir, así que no tiene criterio de «hecho» y su cierre no es exitoso |

**`done` aparece en dos ejes y no es una fusión.** En el operativo es el marcador con el que cierra
el crudo del worker —transporte, no contenido— y en el semántico es el veredicto con el que un
subagente por task informa que la ejecutó. Coincide el token y no coincide nada más: distinto tipo
—`marcador_de_cierre` contra `estado_de_task`—, distinta sede y distinto significado. Es el caso que
más se parece a un defecto sin serlo, y por eso el verificador lo acepta a propósito: **un literal
repetido es legítimo mientras nombre dos cosas distintas**, y deja de serlo cuando las dos
declaraciones traen el mismo tipo y la misma sede, que es la misma cosa escrita dos veces. Escribir
el namespace en cada celda es lo que mantiene la distinción visible sin depender de esta nota.

## Capacidades de plataforma

Toda afirmación de este contrato sobre lo que la plataforma puede o no puede hacer vive en esta
tabla y **va marcada**. Son tres marcas y ninguna fila puede quedar sin una:

- **`portable`** — vale en las dos plataformas del corpus, POSIX y PowerShell. No registra versión
  porque no depende de ninguna.
- **`dependiente`** — vale en un runtime concreto, y entonces registra **la versión con la que se
  comprobó**.
- **`no_verificable`** — el runtime disponible no la expone, así que se registra el motivo **en
  lugar de afirmarla**. No es un defecto ni una fila incompleta: es lo que impide que una afirmación
  sin respaldo entre al contrato disfrazada de dato.

**Las versiones se midieron; no se transcribieron.** Cada fila `dependiente` nombra en su motivo el
comando que la comprueba, y todos se corrieron sobre este árbol el **2026-08-10**, en macOS sobre
arm64. Escribir un número plausible en un documento versionado es fabricar evidencia, y sale más
caro que no tener la afirmación.

Una precisión sobre la columna de versión: registra el nombre del runtime y su número. El único
PowerShell instalado acá es `pwsh-preview`, y la salida literal de `pwsh-preview --version` es
`PowerShell 7.7.0-preview.3`; la columna registra `PowerShell (pwsh-preview) 7.7.0` y el sufijo de
preview queda en esta línea para no perderlo.

La tabla se lee con el modo `--capacidades`, que recorre **fila por fila**: una sola afirmación sin
marca, o una sola dependiente sin versión, alcanza para que falle.

```sh
python3 scripts/verificar-matriz-despachos.py --capacidades \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

| afirmación | marca | versión | motivo |
|---|---|---|---|
| Las dos plataformas del corpus averiguan si un binario existe sin ejecutarlo, cada una con su primitiva y su canal propio de respuesta. | portable | — | — |
| El código de salida de un proceso hijo queda disponible para quien lo lanzó en las dos plataformas, y por eso es el canal en el que las guardas de este repositorio informan su veredicto. | portable | — | — |
| Un prompt en Markdown no se puede interpolar dentro de comillas dobles en ninguna de las dos plataformas: las dos le dan al backtick un significado propio, sustitución de comando en POSIX y escape en PowerShell. Por eso el prompt viaja por archivo. | portable | — | — |
| `codex exec` acota el sandbox del worker a `read-only`, `workspace-write` o `danger-full-access` con `-s/--sandbox`. | dependiente | codex-cli 0.146.1 | comprobado leyendo `codex exec --help`, que enumera los tres valores posibles |
| `codex exec` lee el prompt de la entrada estándar cuando el argumento posicional es `-`, que es lo que permite pasarlo por archivo en vez de interpolarlo. | dependiente | codex-cli 0.146.1 | comprobado leyendo `codex exec --help` |
| `codex exec resume` retoma una sesión previa por su identificador. | dependiente | codex-cli 0.146.1 | comprobado leyendo `codex exec resume --help` |
| El CLI de Claude corre no interactivo con `-p/--print`. | dependiente | Claude Code 2.1.226 | comprobado leyendo `claude --help` |
| El shell POSIX pasa un archivo por la entrada estándar con `< archivo`. | dependiente | bash (como /bin/sh) 3.2.57 | comprobado corriendo `sh -c 'cat < archivo'`, que imprime el contenido y termina en 0 |
| PowerShell **rechaza** `<` como redirección de entrada —reserva el operador para uso futuro— y obliga a pasar el prompt por tubería. | dependiente | PowerShell (pwsh-preview) 7.7.0 | comprobado corriendo `pwsh-preview -NoProfile -Command "Get-Content -Raw < archivo"`, que corta con ParserError y termina en 1; la variante con tubería imprime el contenido |
| `git ls-files --error-unmatch <ruta>` distingue por su código de salida una ruta versionada de una que no lo está. | dependiente | git 2.50.1 | comprobado sobre una ruta versionada (0) y una no versionada (1) |
| Los verificadores de este contrato se ejecutan con `python3` y devuelven 0 cuando el documento cumple el modo invocado. | dependiente | Python 3.14.3 | comprobado corriendo `verificar-matriz-despachos.py --contrato` sobre este documento |
| Las variantes PowerShell de los bloques duplicados del repositorio se comportan igual en el PowerShell 5.1 que Windows trae de fábrica. | no_verificable | — | esta máquina es macOS y el único intérprete instalado es PowerShell 7; ningún runtime disponible expone un 5.1 contra el que comprobarlo, así que la paridad con Windows de fábrica queda sin respaldo |
| Una cancelación pedida por el conductor detuvo efectivamente el proceso del worker. | no_verificable | — | el transporte no ofrece con qué comprobar el cese, y por eso el vocabulario del eje operativo parte la cancelación en cese confirmado y cese incierto en vez de afirmar el efecto |

## Schema del perfil de ejecución

El **perfil de ejecución** es lo que un punto de despacho le entrega al runtime del worker al
lanzarlo. Esta sección lo **declara y no lo materializa**: fija su forma, y el esquema de
configuración de las siete skills sigue sin la clave que lo alojaría. Que siga sin ella no es una
promesa en prosa. Una guarda recorre las superficies de configuración de `skills/` y falla si
alguno de los nombres reservados al contenedor aparece ahí:

```sh
python3 scripts/verificar-matriz-despachos.py --claves-perfil
```

Esos nombres, y el criterio por el que cada uno se reserva o se admite, viven en
`scripts/nombres-reservados-perfil.json`, que es la **única fuente** de la forma del contenedor: de
ahí salen la clave raíz, la ruta de cada componente, los nombres de las dos familias y la lista
blanca de parámetros. El verificador de esta sección los deriva en lugar de transcribirlos, porque
dos listas pueden divergir y la que envejeciera sería justo la que decide qué se acepta.

**Hay dos niveles, y confundirlos invierte el criterio.**

**El contenedor es obligatorio y completo.** Sus cinco componentes —versión, perfiles nombrados,
asignaciones por rol, valor por defecto y familias— van los cinco. A un contenedor al que le falta
uno no le falta un detalle: no declara un perfil que se pueda resolver.

**El objeto de parámetros de cada perfil lleva lista blanca cerrada, y admite exactamente dos:** el
**modelo** y el **esfuerzo de razonamiento**. Un perfil entrega esos dos al runtime y nada más.

La lista blanca gobierna **solo el nivel de adentro**. Los cinco componentes del contenedor viven
**fuera** del objeto de parámetros y ninguno se llama `model` ni `reasoning`, así que la lista no
los alcanza: aplicársela los rechazaría a los cinco, y quien quisiera pasar la verificación los
borraría —que es el contenedor incompleto que la regla anterior prohíbe—. Al revés, una clave de
más colgada del contenedor no infringe este criterio; la misma clave dentro del objeto de
parámetros de un perfil sí.

**Y es una lista de admitidos, no una de prohibidos.** Un tercer parámetro que no altere
herramientas, aislamiento, permisos, contrato de salida ni autoridad —una temperatura, por
ejemplo— también cae, y cae por no estar admitido. Enumerar lo prohibido deja entrar todo lo que
nadie pensó en prohibir.

**Una asignación elige qué perfil se resuelve, y eso es todo lo que hace.** Nombra un perfil: no
transporta herramientas, aislamiento, permisos, contrato de salida ni autoridad, ni como hoja del
perfil que elige ni como objeto puesto donde iría el nombre. Una asignación capaz de alterar
cualquiera de esos cinco convierte el perfil en una superficie de elevación de privilegios, que es
lo contrario de lo que declara ser.

El modo `--perfil-schema` comprueba las dos cosas —el contenedor completo y la lista blanca del
objeto de parámetros— sobre el bloque que sigue:

```sh
python3 scripts/verificar-matriz-despachos.py --perfil-schema \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

```json
{
  "subagents": {
    "schema_version": 1,
    "profiles": {
      "economy": {
        "codex": {"model": "inherit", "reasoning": "low"},
        "claude": {"model": "inherit", "reasoning": "low"}
      },
      "balanced": {
        "codex": {"model": "inherit", "reasoning": "medium"},
        "claude": {"model": "inherit", "reasoning": "medium"}
      },
      "deep-review": {
        "codex": {"model": "inherit", "reasoning": "high"},
        "claude": {"model": "inherit", "reasoning": "high"}
      }
    },
    "bindings": {
      "default": "balanced",
      "roles": {
        "explorer": "economy",
        "investigator": "deep-review",
        "design-reviewer": "deep-review",
        "bounded-implementer": "balanced",
        "diff-reviewer": "deep-review"
      }
    }
  }
}
```

**El bloque declara la forma con un ejemplar completo, y la forma es lo único que este contrato
congela.** Un schema que no se puede instanciar tampoco se puede verificar, así que los perfiles
llevan valores: `inherit` es el valor con el que un perfil declara que no fija modelo, y el
esfuerzo de razonamiento se escribe con el literal portable de este contrato y no con el nombre
nativo de ninguna familia. Qué perfil le toca a cada rol **no** queda congelado acá: es la decisión
de la fase que materialice la superficie de configuración, y hasta entonces el reparto de arriba es
el ejemplar y no el compromiso.

## Precedencia del perfil de ejecución

Los niveles se recorren en orden y **el primero que resuelve gana**. Lo que sigue no describe la
precedencia: **es** la precedencia, con el corpus de escenarios contra el que se ejecuta. Cada
escenario trae la superficie de configuración entera y declara qué tiene que resolver; el modo
`--perfil-precedencia` corre la resolución y la coteja contra lo declarado, en vez de creerle al
documento lo que resolvería.

```sh
python3 scripts/verificar-matriz-despachos.py --perfil-precedencia \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

**Antes que cualquier nivel se evalúa la validez, y falla cerrado.** Tres situaciones resuelven
**inválidas** y no ignoradas: un perfil declarado que ninguna asignación usa, una asignación que
nombra un perfil inexistente y una referencia rota —el valor por defecto de la superficie apuntando
a un perfil que no existe—. Ignorarlas dejaría que una superficie mal escrita resolviera igual que
una bien escrita, que es la forma en que un error de configuración se vuelve invisible: el despacho
sale con un perfil que nadie pidió y nada lo dice.

**La ausencia legítima resuelve al perfil default portable, y sus dos escenarios van por separado.**
No son el mismo caso:

- **(a) sin asignación, habiendo superficie de configuración** — la superficie existe, no asigna
  perfil para ese rol y tampoco declara un valor por defecto que lo cubra. Es el escenario `P-04`.
- **(b) sin superficie de configuración alguna** — no hay dónde buscar. Es el escenario `P-05`.

Los dos caen al mismo perfil por **causas distintas**, y el corpus trae un escenario por cada una.
Un solo caso los confundiría: leídos desde el resultado son indistinguibles, y es la causa la que
dice si falta una asignación o falta la superficie entera. **El perfil default portable es el que
declara el contenedor de la sección anterior** —`balanced`— y no uno de la superficie: por eso hay a
dónde caer incluso cuando no hay superficie.

**Y (a) exige que la superficie no declare su valor por defecto.** Una superficie que sí lo declara
no produce la ausencia legítima: resuelve un nivel antes, en el valor por defecto de la superficie.
`P-03` y `P-04` son ese par y se diferencian en **una sola clave**.

**El orden declara los niveles que la precedencia ejecuta**, y cada uno tiene al menos un escenario
que lo alcanza. Dos candidatos quedaron afuera a propósito: una asignación propia del punto de
despacho —la precedencia resuelve por rol y esa superficie no existe todavía, así que ningún
escenario podría alcanzar ese nivel— y el default de la sesión o de la plataforma —que es el suelo
sobre el que se apoya el perfil default portable, no un nivel por encima de él: el portable siempre
resuelve antes—. Un nivel que ningún escenario puede alcanzar es una afirmación que ninguna guarda
puede poner roja; cuando una fase materialice esa superficie, el nivel entra con su escenario.

**Las superficies del corpus son fragmentos y no contenedores completos.** Ejercen la precedencia,
no el schema: la ausencia legítima (a) necesita justamente una superficie sin valor por defecto, y
exigirle ahí los cinco componentes volvería inejecutable el escenario que ese requisito existe para
cubrir. La completitud del contenedor se comprueba en la sección anterior y sobre el contenedor.

```json
{
  "niveles": [
    "override_explicito_del_usuario",
    "asignacion_por_rol_de_la_superficie",
    "valor_por_defecto_de_la_superficie",
    "perfil_default_portable"
  ],
  "default_portable": "balanced",
  "escenarios": [
    {
      "id": "P-01",
      "descripcion": "el usuario fija el perfil de la corrida y su elección gana sobre la superficie",
      "rol": "explorer",
      "override": "deep-review",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {"model": "inherit", "reasoning": "low"},
              "claude": {"model": "inherit", "reasoning": "low"}
            },
            "deep-review": {
              "codex": {"model": "inherit", "reasoning": "high"},
              "claude": {"model": "inherit", "reasoning": "high"}
            }
          },
          "bindings": {
            "default": "economy",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "deep-review",
        "nivel": "override_explicito_del_usuario"
      }
    },
    {
      "id": "P-02",
      "descripcion": "la superficie asigna un perfil para el rol que se está resolviendo",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {"model": "inherit", "reasoning": "low"},
              "claude": {"model": "inherit", "reasoning": "low"}
            },
            "balanced": {
              "codex": {"model": "inherit", "reasoning": "medium"},
              "claude": {"model": "inherit", "reasoning": "medium"}
            }
          },
          "bindings": {
            "default": "balanced",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "economy",
        "nivel": "asignacion_por_rol_de_la_superficie"
      }
    },
    {
      "id": "P-03",
      "descripcion": "sin asignación para el rol, la superficie declara su valor por defecto: resuelve un nivel antes que la ausencia legítima",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {"model": "inherit", "reasoning": "low"},
              "claude": {"model": "inherit", "reasoning": "low"}
            }
          },
          "bindings": {
            "default": "economy",
            "roles": {
              "investigator": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "economy",
        "nivel": "valor_por_defecto_de_la_superficie"
      }
    },
    {
      "id": "P-04",
      "descripcion": "ausencia legítima (a): la misma superficie que P-03 sin su valor por defecto, así que nada cubre al rol",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {"model": "inherit", "reasoning": "low"},
              "claude": {"model": "inherit", "reasoning": "low"}
            }
          },
          "bindings": {
            "roles": {
              "investigator": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "balanced",
        "nivel": "perfil_default_portable",
        "causa": "sin_asignacion_para_el_rol"
      }
    },
    {
      "id": "P-05",
      "descripcion": "ausencia legítima (b): el punto no tiene superficie de configuración alguna",
      "rol": "explorer",
      "superficie": null,
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "balanced",
        "nivel": "perfil_default_portable",
        "causa": "sin_superficie_de_configuracion"
      }
    },
    {
      "id": "P-06",
      "descripcion": "un perfil declarado que ninguna asignación y ningún valor por defecto usa",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {"model": "inherit", "reasoning": "low"},
              "claude": {"model": "inherit", "reasoning": "low"}
            },
            "deep-review": {
              "codex": {"model": "inherit", "reasoning": "high"},
              "claude": {"model": "inherit", "reasoning": "high"}
            }
          },
          "bindings": {
            "default": "economy",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "invalido",
        "causa": "perfil_sin_uso"
      }
    },
    {
      "id": "P-07",
      "descripcion": "una asignación que nombra un perfil que la superficie no declara",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {"model": "inherit", "reasoning": "low"},
              "claude": {"model": "inherit", "reasoning": "low"}
            }
          },
          "bindings": {
            "default": "economy",
            "roles": {
              "explorer": "economy",
              "diff-reviewer": "turbo"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "invalido",
        "causa": "asignacion_a_perfil_inexistente"
      }
    },
    {
      "id": "P-08",
      "descripcion": "el valor por defecto de la superficie apunta a un perfil que no existe",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {"model": "inherit", "reasoning": "low"},
              "claude": {"model": "inherit", "reasoning": "low"}
            }
          },
          "bindings": {
            "default": "no-existe",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "invalido",
        "causa": "referencia_rota"
      }
    }
  ]
}
```

## Familias de rol

Las **cinco familias de rol** del programa —`explorer`, `investigator`, `design-reviewer`,
`bounded-implementer` y `diff-reviewer`— no se eligen acá: se derivan de la tabla de consumidores
del roadmap del programa, y cada una lleva el **puntero normativo** del que sale. El modo `--roles`
resuelve ese puntero contra el árbol y exige que la sección que señala nombre a la familia, así que
el puntero se ejerce en vez de decorar.

**Ese puntero apunta a un artefacto de trabajo no versionado**
(`.plans/doctrina-implementador/roadmap.md`), y hay que decirlo con las mismas palabras con que esta fase lo
dijo de la propuesta doctrinal. Es el único documento del árbol que enumera las cinco familias en
una sección legible por sección. El único **archivo versionado** que las nombra a las cinco es
`scripts/matriz-despachos.schema.json`, que no sirve de sede por dos motivos independientes: es un
artefacto de este mismo flujo —el resolutor de procedencias rechaza por construcción toda sede que
lo sea, porque una hoja que se cita a sí misma coincide siempre consigo misma— y no es Markdown, así
que no tiene secciones contra las que resolver un puntero. La consecuencia queda declarada y no
tapada: la derivación de las cinco familias se apoya en un artefacto que el árbol versionado no
contiene.

**Cada campo del contrato de una familia declara su estado**, y son cuatro: `vigente` en una sede
normativa, `observado` en el comportamiento, `ausente`, o `propuesto` para una fase futura. Los dos
primeros van **anclados** y los resuelve el mismo verificador semántico que las hojas de la matriz,
de modo que sustituir un valor por otro plausible deja de coincidir con lo que la sede dice. Los dos
últimos no llevan puntero: declaran por qué no lo tienen.

**Hoy los quince campos de las cinco familias están sin anclar, y ese es el resultado honesto de
esta fase.** El motivo es uno solo y está medido: el repositorio declara los contratos **por punto
de despacho**, no por familia. `scripts/matriz-despachos.json` ancla el ancla de invocación, el
contrato de salida y los permisos efectivos de cada uno de los trece puntos contra su sección de
`skills/`, y su
propia hoja `rol` registra que «la taxonomía de roles conductuales de esta matriz no está declarada
en ninguna skill del repositorio». Un contrato por familia sería una generalización sobre puntos que
hoy declaran cosas distintas, y anclarlo a la sede de uno de ellos lo haría coincidir con una fuente
que no lo respalda. Las entradas y las salidas quedan **ausentes con su motivo**; los scopes quedan
**propuestos**, con la fase que el roadmap declara que los toma: la Fase 2 para las cuatro familias
read-only y la Fase 3 para el writer, que es la que se propone adoptarlo «con scope explícito».

**La autoridad final no aparece acá.** Va por punto y variante, en la sección siguiente: dos puntos
de la misma familia pueden cerrarse en manos distintas, y de hecho lo hacen.

```sh
python3 scripts/verificar-matriz-despachos.py --roles \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

```json
{
  "familias": [
    {
      "familia": "explorer",
      "puntero": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "ausente",
          "motivo": "ninguna sede versionada declara qué recibe un `explorer` como familia. El paquete de contexto está descrito por punto —`skills/co-explore/reference.md` para el fan-out y `skills/sdd-flow/SKILL.md#paso-analyze` para analyze—, y el punto del fan-out sirve además a dos familias, así que su entrada no se puede leer como entrada de una sola"
        },
        "salida": {
          "estado": "ausente",
          "motivo": "la matriz ancla `contrato_de_salida` por punto y no por familia: los dos puntos de esta familia apuntan a `skills/co-explore/reference.md#envelope-de-retorno` y a `skills/sdd-flow/SKILL.md#paso-analyze`, que son dos contratos distintos"
        },
        "scope": {
          "estado": "propuesto",
          "fase": "Fase 2"
        }
      }
    },
    {
      "familia": "investigator",
      "puntero": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "ausente",
          "motivo": "el único punto que despacha esta familia es el fan-out dual de `co-explore` en modo `investigate`, que comparte sede con el modo `explore`: la sede describe la entrada del punto, no la de la familia, y las dos familias entran por ahí"
        },
        "salida": {
          "estado": "ausente",
          "motivo": "su único punto comparte el contrato de salida con el `explorer` del mismo fan-out, así que de ahí no se puede leer una salida propia de esta familia"
        },
        "scope": {
          "estado": "propuesto",
          "fase": "Fase 2"
        }
      }
    },
    {
      "familia": "design-reviewer",
      "puntero": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "ausente",
          "motivo": "sus dos puntos —el revisor por ronda de `cross-review` y el worker de debate de `co-explore`— reciben cosas distintas (un artefacto de diseño con su criterio, una postura en discusión) y cada sede describe la suya; ninguna declara la entrada de la familia"
        },
        "salida": {
          "estado": "ausente",
          "motivo": "sus dos puntos declaran contratos de salida distintos —un veredicto derivado de un ledger y una plantilla de debate—, y el roadmap dice explícitamente que `decision-debate` produce posturas y no `APPROVED | REVISE`: la salida es de la variante, no de la familia"
        },
        "scope": {
          "estado": "propuesto",
          "fase": "Fase 2"
        }
      }
    },
    {
      "familia": "bounded-implementer",
      "puntero": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "ausente",
          "motivo": "sus cuatro puntos viven en cuatro skills distintas y cada una declara su propio prompt de entrada; ninguna sede versionada enuncia qué recibe la familia con independencia del punto"
        },
        "salida": {
          "estado": "ausente",
          "motivo": "sus cuatro puntos anclan tres contratos de salida distintos —los dos de `cross-implement` comparten sede y los otros dos no—; ninguna de las tres declara la salida de la familia"
        },
        "scope": {
          "estado": "propuesto",
          "fase": "Fase 3"
        }
      }
    },
    {
      "familia": "diff-reviewer",
      "puntero": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "ausente",
          "motivo": "sus cuatro puntos declaran la entrada dentro del prompt de cada revisor, y esos prompts difieren en qué acompaña al diff; una entrada por familia sería una generalización que ninguna de las cuatro sedes hace"
        },
        "salida": {
          "estado": "ausente",
          "motivo": "sus cuatro puntos anclan cuatro contratos de salida distintos; el de la validación adversarial ni siquiera revisa el diff, sino que intenta invalidar un finding ajeno"
        },
        "scope": {
          "estado": "propuesto",
          "fase": "Fase 2"
        }
      }
    }
  ]
}
```

## Asignaciones de despacho

El mapa **punto → familia → variante** de los trece puntos de despacho. **No se deriva de ninguna
fuente:** la tabla del roadmap mapea *skill → roles reusables*, no *punto → variante*. Está medido:
esa tabla tiene siete filas y trece puntos, y su columna de roles enumera por skill y no por punto,
así que en tres de las siete los números no cuadran —`co-explore` lista dos puntos y tres roles,
`sdd-flow` cuatro puntos y tres roles, y `bitbucket-code-review` dos puntos y un solo rol con dos
variantes—. Construir el mapa fue decidir, y por eso cada fila declara su procedencia:

- **`puntero`** cuando el roadmap **nombra la variante**. Son ocho, y el modo resuelve su puntero
  contra el árbol y exige encontrar ahí el literal de la variante: la fila lleva la carga de la
  prueba.
- **`decision`** cuando la asignación se tomó en esta fase. Son cinco, no tienen dónde apuntar, y
  cada una lleva su justificación escrita. Una decisión sin argumento la vuelve a tomar distinta el
  próximo que la necesite.

**La autoridad final va por punto y variante**, y está anclada: cada fila la resuelve contra la
misma sede de `skills/` con la que `scripts/matriz-despachos.json` la declara, de modo que
sustituirla por otra plausible deja de coincidir. Diez puntos cierran en el conductor y tres en el
usuario, y **los tres** pertenecen a familias cuyos otros puntos cierran en el conductor: el debate
de `co-explore` es `design-reviewer` y el revisor por ronda de `cross-review` también, y el fan-out
por repo y el implement delegado son `bounded-implementer` como los tres puntos que sí cierran en el
conductor. Por eso la autoridad no puede declararse por familia: declarada ahí, cada una de esas dos
familias tendría que elegir entre dos respuestas ciertas.

**Dos variantes cuyo resultado hoy tiene forma distinta no comparten declaración de salida.** La
declaración es la sede que la matriz ancla como contrato de salida del punto; la forma del resultado
es un nombre corto que **decide este contrato** y que no tiene sede —ninguna existe—. Lo verificable
no es la forma en sí sino su coherencia con la declaración: dos puntos que comparten declaración
—los dos de `cross-implement`, que anclan la misma sección— tienen que traer la misma forma, y
traerla distinta es el defecto que este criterio existe para impedir.

```json
{
  "asignaciones": [
    {
      "punto": "co-explore · fan-out dual",
      "familia": "explorer / investigator",
      "variante": "fan-out en modos explore y counter-plan; root-cause en modo investigate",
      "procedencia": "decision",
      "forma_de_resultado": "mapa_comparable",
      "declaracion_de_salida": "skills/co-explore/reference.md#envelope-de-retorno",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/co-explore/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^8\\. \\*\\*El conductor arbitra, no explora\\.\\*\\*"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "^8\\. \\*\\*El (conductor) arbitra",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "justificacion": "el roadmap lista tres roles para los dos puntos de la skill y no dice cuál va en cuál. El fan-out sirve a `explorer` en los modos `explore` y `counter-plan` y a `investigator` en `investigate`, así que la asignación es condicionada por modo y no única: la fila declara las dos familias en vez de elegir una y perder la otra"
    },
    {
      "punto": "co-explore · debate",
      "familia": "design-reviewer",
      "variante": "decision-debate",
      "procedencia": "puntero",
      "forma_de_resultado": "postura_de_debate",
      "declaracion_de_salida": "skills/co-explore/reference.md#plantilla-de-debate-md",
      "autoridad": {
        "estado": "vigente",
        "valor": "usuario",
        "procedencia": {
          "sede": "skills/co-explore/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^voz, la otra familia es la otra, y el conductor además sintetiza"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "el (usuario) es el árbitro",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "cross-review · revisor por ronda",
      "familia": "design-reviewer",
      "variante": "artifact-review",
      "procedencia": "puntero",
      "forma_de_resultado": "veredicto_de_revision_de_artefacto",
      "declaracion_de_salida": "skills/cross-review/reference.md#formato-de-salida",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/cross-review/reference.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^del revisor y arbitraje del conductor\\."
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "arbitraje del (conductor)\\.",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "cross-implement · implementador inicial",
      "familia": "bounded-implementer",
      "variante": "work-order",
      "procedencia": "puntero",
      "forma_de_resultado": "diff_con_reporte",
      "declaracion_de_salida": "skills/cross-implement/reference.md#formato-del-reporte",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/cross-implement/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^Nunca bloquea\\. Cuatro vías de falla, mismo final — el conductor implementa inline:$"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "— el (conductor) implementa inline",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "cross-implement · fix loop",
      "familia": "bounded-implementer",
      "variante": "fix-round",
      "procedencia": "decision",
      "forma_de_resultado": "diff_con_reporte",
      "declaracion_de_salida": "skills/cross-implement/reference.md#formato-del-reporte",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/cross-implement/reference.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^- Tope `max_fix_rounds` \\(default 2\\) → \\*\\*takeover\\*\\*"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "el (conductor) termina directamente",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "justificacion": "el roadmap escribe «`bounded-implementer[work-order]`; después `diff-reviewer`» para los dos puntos de la skill, pero el revisor del diff de `cross-implement` es el conductor y no un despacho delegado —la matriz le da autoridad final `conductor` a los dos puntos—. Lo que se despacha en el fix loop es el implementador corrigiendo contra el mismo work order, y por eso lleva variante propia en vez de repetir `work-order`"
    },
    {
      "punto": "sdd-flow · analyze",
      "familia": "explorer",
      "variante": "codebase-survey",
      "procedencia": "decision",
      "forma_de_resultado": "mapa_para_el_plan",
      "declaracion_de_salida": "skills/sdd-flow/SKILL.md#paso-analyze",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/sdd-flow/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "el mapa del conductor sí es el insumo\\.$"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "el mapa del (conductor) sí es el insumo",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "justificacion": "el roadmap asigna la familia (`explorer`) y ninguna variante. Se separa del fan-out de `co-explore` porque el contrato de salida difiere: analyze ancla `skills/sdd-flow/SKILL.md#paso-analyze` y alimenta un plan, y el fan-out ancla `skills/co-explore/reference.md#envelope-de-retorno` y produce mapas destinados a compararse entre sí"
    },
    {
      "punto": "sdd-flow · implementer por task",
      "familia": "bounded-implementer",
      "variante": "task",
      "procedencia": "puntero",
      "forma_de_resultado": "estado_de_task",
      "declaracion_de_salida": "skills/sdd-flow/reference.md#prompt-del-subagente-por-task",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/sdd-flow/reference.md",
          "tipo_de_sede": "heading_markdown",
          "selector": {
            "texto": "Lado conductor (al volver cada subagente)",
            "nivel": 3
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "^Lado (conductor)",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "sdd-flow · reviewer por task",
      "familia": "diff-reviewer",
      "variante": "task",
      "procedencia": "decision",
      "forma_de_resultado": "veredicto_de_revision_de_diff",
      "declaracion_de_salida": "skills/sdd-flow/reference.md#prompt-del-subagente-reviewer",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/sdd-flow/reference.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^El conductor: \\*\\*SPEC ok \\+ QUALITY ok\\*\\*"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "^El (conductor):",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "justificacion": "el roadmap nombra `diff-reviewer` dentro del alcance de `sdd-flow` sin darle variante. Se le asigna `task` —la misma que el implementador— porque la unidad de despacho es la misma: uno por task. Lo que separa a los dos puntos no es la variante sino la familia y la declaración de salida, que son distintas"
    },
    {
      "punto": "sdd-flow · revisión final",
      "familia": "diff-reviewer",
      "variante": "final",
      "procedencia": "decision",
      "forma_de_resultado": "veredicto_de_revision_de_diff",
      "declaracion_de_salida": "skills/sdd-flow/reference.md#revision-final-de-diff",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/sdd-flow/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^5\\. \\*\\*Gate de revisión manual \\(STOP\\):\\*\\*"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "revisión liviana del (conductor)\\.",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "justificacion": "el roadmap la enumera en el alcance de la Fase 2 sin nombrarle variante. No puede compartir `task` porque no se despacha por unidad de trabajo sino una vez por rama, sobre el diff acumulado, y su declaración de salida es otra sección"
    },
    {
      "punto": "sdd-orchestrator · fan-out por repo",
      "familia": "bounded-implementer",
      "variante": "repo-runner",
      "procedencia": "puntero",
      "forma_de_resultado": "estado_de_repo_delegado",
      "declaracion_de_salida": "skills/sdd-orchestrator/reference.md#prompt-del-agente-delegado",
      "autoridad": {
        "estado": "vigente",
        "valor": "usuario",
        "procedencia": {
          "sede": "skills/sdd-orchestrator/SKILL.md",
          "tipo_de_sede": "heading_markdown",
          "selector": {
            "texto": "Fase 3 · Cierre (centralizada, el usuario al mando)",
            "nivel": 2
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "\\(centralizada, el (usuario) al mando\\)$",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "sdd-pr-feedback · implement delegado",
      "familia": "bounded-implementer",
      "variante": "work-order",
      "procedencia": "puntero",
      "forma_de_resultado": "estado_de_task",
      "declaracion_de_salida": "skills/sdd-pr-feedback/reference.md#delegacion-a-sdd-flow-prompt-del-subagente",
      "autoridad": {
        "estado": "vigente",
        "valor": "usuario",
        "procedencia": {
          "sede": "skills/sdd-pr-feedback/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^Tras el implement \\(el subagente frenó antes de commitear\\), con el usuario al mando\\."
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "con el (usuario) al mando",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "bitbucket-code-review · panel",
      "familia": "diff-reviewer",
      "variante": "review",
      "procedencia": "puntero",
      "forma_de_resultado": "findings_de_revision",
      "declaracion_de_salida": "skills/bitbucket-code-review/reference.md#formato-de-salida-el-revisor-responde-exactamente-esto",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/bitbucket-code-review/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^### 11\\. Publicar \\(solo el conductor, tras confirmación\\)$"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "\\(solo el (conductor), tras confirmación\\)",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "bitbucket-code-review · validador adversarial",
      "familia": "diff-reviewer",
      "variante": "refute",
      "procedencia": "puntero",
      "forma_de_resultado": "refutacion_de_finding",
      "declaracion_de_salida": "skills/bitbucket-code-review/reference.md#validacion-adversarial-de-hallazgos-find-then-validate",
      "autoridad": {
        "estado": "vigente",
        "valor": "conductor",
        "procedencia": {
          "sede": "skills/bitbucket-code-review/SKILL.md",
          "tipo_de_sede": "patron_de_linea",
          "selector": {
            "patron": "^### 11\\. Publicar \\(solo el conductor, tras confirmación\\)$"
          },
          "cardinalidad": {
            "tipo": "exactamente_una"
          },
          "extraccion": {
            "tipo": "captura_de_grupo",
            "patron": "\\(solo el (conductor), tras confirmación\\)",
            "grupo": 1
          },
          "normalizacion": "minusculas",
          "conversion": "enum:autoridad_final"
        }
      },
      "puntero_variante": ".plans/doctrina-implementador/roadmap.md#1-que-significa-soportado-por-las-siete-skills"
    }
  ]
}
```

## Política de diversidad

Por **intento** se registran las **tres identidades** —quien conduce, quien escribió el artefacto en
juego y quien hizo el trabajo delegado— y las **relaciones** entre ellas. Tres identidades y no dos:
`cross_family` sin decir respecto de qué no dice nada, y la relación que importa para la evidencia
es la que va del worker al **autor del artefacto**, que no siempre es el conductor.

**La topología agregada de la corrida se deriva de los registros.** Está escrita abajo para que se
pueda leer, y el modo `--diversidad` la recalcula desde los intentos y la coteja: si el documento
declarara una topología que sus propios registros no producen, el modo lo dice. Declararla sin
registros por intento es exactamente lo que esta sección existe para impedir.

**Regla de evidencia independiente, ejecutable:** un resultado cuenta como evidencia independiente
**si y solo si** el trabajo delegado es de otra familia que quien escribió el artefacto que ese
trabajo juzga, **y** la corrida no fue de una sola voz. Una corrida de una sola voz no se confirma a
sí misma; un resultado de la misma familia que el autor mide la misma correlación de errores dos
veces, por más intentos que se acumulen. `same_family` puede estar presente sin ser un defecto
—registrarlo lo es de hecho—; contarlo como independiente sí lo es.

**Los cuatro intentos de abajo son los de esta corrida y no un ejemplo.** Los tres primeros son las
tandas de cross-review que este flujo despachó a la otra familia, cada una con el `run_id` que su
registro conserva; el cuarto es la implementación por task, que se despachó a subagentes de la
familia del conductor. La unidad del registro es la **tanda de despacho**, no el subagente
individual: los subagentes de la cuarta comparten conductor, autor y familia, así que una fila por
subagente repetiría la misma relación y el agregado contaría N veces la misma medición.

```sh
python3 scripts/verificar-matriz-despachos.py --diversidad \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

```json
{
  "intentos": [
    {
      "id": "I-01",
      "despacho": "cross-review de la spec de este flujo (run_id `mcs01`, 3 rondas)",
      "conductor": "claude",
      "autor_del_artefacto": "claude",
      "worker": "codex",
      "relaciones": {
        "worker_vs_conductor": "cross_family",
        "worker_vs_autor": "cross_family"
      },
      "cuenta_como_evidencia_independiente": true
    },
    {
      "id": "I-02",
      "despacho": "cross-review del plan de este flujo (run_id `mcp01`, 2 rondas)",
      "conductor": "claude",
      "autor_del_artefacto": "claude",
      "worker": "codex",
      "relaciones": {
        "worker_vs_conductor": "cross_family",
        "worker_vs_autor": "cross_family"
      },
      "cuenta_como_evidencia_independiente": true
    },
    {
      "id": "I-03",
      "despacho": "cross-review de las tasks de este flujo (run_id `mct01`, 12 rondas)",
      "conductor": "claude",
      "autor_del_artefacto": "claude",
      "worker": "codex",
      "relaciones": {
        "worker_vs_conductor": "cross_family",
        "worker_vs_autor": "cross_family"
      },
      "cuenta_como_evidencia_independiente": true
    },
    {
      "id": "I-04",
      "despacho": "implementación por task de este flujo (`implement_mode: subagent`)",
      "conductor": "claude",
      "autor_del_artefacto": "claude",
      "worker": "claude",
      "relaciones": {
        "worker_vs_conductor": "same_family",
        "worker_vs_autor": "same_family"
      },
      "cuenta_como_evidencia_independiente": false
    }
  ],
  "topologia": {
    "intentos": 4,
    "single_voice": 1,
    "cross_vs_conductor": 3,
    "cross_vs_autor": 3,
    "evidencia_independiente": 3,
    "familias_presentes": [
      "claude",
      "codex"
    ]
  }
}
```

## Inventario de defectos

Los defectos **ya verificados** de este repositorio, cada uno con su ubicación, su naturaleza y la
fase que lo corrige. El inventario **no los corrige**: este contrato no edita las instrucciones del
repositorio ni las siete skills, y registrar el defecto con su destino es exactamente lo que puede
hacer una fase cuyo rollback «no aplica: solo artefactos de diseño».

**El mínimo son seis y se comparan por identidad, no por cantidad.** El modo `--defectos` conoce las
seis identidades y exige que estén; un criterio de cardinalidad —«al menos seis»— aceptaría un
inventario que cambió uno de los seis por otro conservando el total, que es la forma en que un
inventario se vacía sin que el conteo se mueva. Puede contener más y no menos.

```sh
python3 scripts/verificar-matriz-despachos.py --defectos \
    docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md
```

**Cada ubicación es un puntero comprobado, y conviene decir hasta dónde llega la comprobación.** El
modo exige que la ubicación tenga **forma** de puntero —ruta relativa, con fragmento o sin él— y no
la resuelve contra el árbol: «documental» o «en las instrucciones» se rechazan, pero una ruta
inventada pasaría. Las seis de abajo se resolvieron contra el árbol versionado una por una, con el
mismo resolutor de anclas que usa `--anclas`: las seis existen y las seis contienen el texto que el
defecto describe.

**La fase de corrección sale de un criterio y no de una preferencia:** es la **primera fase cuyo
alcance declarado ya abre la sede del defecto**. Corregir antes obliga a abrir esa sede dos veces
—una para el arreglo suelto y otra para el cambio que la fase le va a hacer igual—, y corregir
después deja el defecto vivo mientras alguien trabaja encima. Ninguna fila dice «Fase 0»: esta fase
no toca ninguna de las seis sedes.

```json
{
  "defectos": [
    {
      "id": "instruccion-del-repositorio-contra-guarda",
      "descripcion": "la instrucción del repositorio que contradice el estado de una guarda",
      "ubicacion": "CLAUDE.md#anatomia-de-una-skill-patron-obligatorio-del-repo",
      "naturaleza": "documental: la instrucción declara que el modo `--vias` de `scripts/verificar-retiro-transporte.py` «aún no está implementado y no cuenta como guarda», y el modo está implementado — su propio encabezado lo marca «AC-15 · implementado», está declarado en el parser de argumentos y corre con código de salida 0 sobre el árbol de hoy. Quien sigue la instrucción no lo ejecuta: la guarda existe y nadie la dispara, que es el estado en el que una guarda no protege nada",
      "fase": "Fase 1"
    },
    {
      "id": "conteo-de-skills-del-manifest",
      "descripcion": "la discrepancia entre el número declarado de skills del manifest y su tabla",
      "ubicacion": "skills/cross-review/reference.md#manifest-de-corrida",
      "naturaleza": "documental: la sede canónica del manifest de corrida dice «las tres» dos veces —al declararse sede y al justificar por qué la clave vive en `cross_model`— y su propia tabla de vocabulario, dentro de esa misma sección, tiene cuatro filas: `co-explore`, `cross-review`, `cross-implement` y `bitbucket-code-review`. El comentario del esquema de configuración que apunta a esa sede repite el mismo tres. Un lector que se guíe por la prosa deja una de las cuatro skills fuera de una política que la sede declara del ecosistema entero",
      "fase": "Fase 2"
    },
    {
      "id": "frontera-que-nombra-skill-inexistente",
      "descripcion": "la regla de fronteras que nombra una skill inexistente",
      "ubicacion": "CLAUDE.md#el-ecosistema-de-skills",
      "naturaleza": "documental: la regla de fronteras reparte cinco actividades y le asigna «arreglar bugs» a `systematic-debugging`, que no es ninguna de las siete skills de este repositorio; es una skill externa, y las propias skills la citan con su prefijo de plugin. La lista de la misma sección enumera además seis de las siete —`bitbucket-code-review` no figura—, así que la sección reparte trabajo a un nombre sin sede en el árbol y omite a un consumidor que sí la tiene",
      "fase": "Fase 1"
    },
    {
      "id": "registro-historico-rechazado-por-su-guarda",
      "descripcion": "los archivos del registro histórico que su propia guarda rechaza",
      "ubicacion": "skills/cross-review/reference.md#validar-un-manifest",
      "naturaleza": "instrumental: la guarda que valida el registro por corrida rechaza 38 de los 66 archivos que hoy viven en `.cross-model/runs/`, medido corriendo el bloque tal como está escrito, archivo por archivo. Treinta y cinco son sobres de corrida retirados —una clase de archivo que el contrato del directorio nunca admitió: declara que `runs/` acumula el manifest que cada corrida deja al terminar— y los tres restantes son manifests propios con un `transport` fuera del vocabulario de su fila —uno declara la vía de transporte que el ecosistema ya retiró y el otro declara `mixto`— o con un campo recortado presente (`attempts`). Una serie que su propia guarda rechaza no sostiene ningún baseline: el rechazo no distingue el registro inválido del registro de otra clase",
      "fase": "Fase 2"
    },
    {
      "id": "familia-dura-con-override-explicito",
      "descripcion": "la regla de familia declarada dura que a la vez admite override explícito",
      "ubicacion": "skills/cross-review/SKILL.md#reglas-no-negociables",
      "naturaleza": "doctrinal: la regla no negociable declara «regla dura: el revisor nunca es de la misma familia de modelos que el autor del artefacto», y el paso de descubrimiento de la misma skill resuelve que, si la configuración fuerza una vía que coincide con la familia del autor, se avisa que se pierde el valor cross-model y se continúa porque «el override explícito manda». Las dos no pueden valer a la vez: o la regla es dura y el override se rechaza, o el override manda y lo que la regla fija es un default. Hoy conviven, y cuál gana lo decide el orden en que se leyó la skill",
      "fase": "Fase 2"
    },
    {
      "id": "sede-del-fan-out-vs-prompt",
      "descripcion": "la divergencia entre la sede del fan-out por repo y el prompt con que ese fan-out despacha",
      "ubicacion": "skills/sdd-orchestrator/reference.md#prompt-del-agente-delegado",
      "naturaleza": "instrumental: la sede del fan-out por repo declara dos cosas que la plantilla del prompt no transmite. La sede apaga `cross_review.mode` y `co_explore.mode` —«ortogonales; se apagan ambos explícitos»— y el prompt declara el override de `cross_review.mode` solamente. La sede dice que el agente delegado hereda el `implement_mode` del manifest, incluido `cross`, y el prompt le ordena usar `inline` salvo que su entorno permita despachar subagentes, sin nombrar el `implement_mode` ni `cross`. El worker cumple el contrato que le llega, que es el que ninguna de las dos sedes declara",
      "fase": "Fase 3"
    }
  ]
}
```

### El séptimo candidato, evaluado y descartado

El `analyze` de este flujo registró una asimetría como candidata a séptimo defecto: **seis de las
siete skills declararían en prosa cuántos puntos de despacho propios tienen y `sdd-orchestrator`
no**. Se evaluó contra el árbol y **no entra al inventario, porque la asimetría no existe**.

Las siete lo declaran, en la sección «Corridas delegadas en vuelo» de su `SKILL.md`, y los siete
números suman los trece puntos del inventario:

| Skill | Lo que declara | Puntos |
|---|---|---:|
| `sdd-flow` | «Los puntos de despacho propios son cuatro:» | 4 |
| `bitbucket-code-review` | «Los puntos de despacho propios son dos:» | 2 |
| `co-explore` | «Los puntos de despacho propios son dos:» | 2 |
| `cross-implement` | «Los puntos de despacho propios son dos:» | 2 |
| `cross-review` | «El punto de despacho propio es uno:» | 1 |
| `sdd-orchestrator` | «El punto de despacho propio es uno:» | 1 |
| `sdd-pr-feedback` | «El punto de despacho propio es uno:» | 1 |

La declaración de `sdd-orchestrator` no se agregó después de la observación: entró junto con las
otras seis, en el commit que introdujo el sobre de corrida delegada, cuatro días antes de que el
`analyze` la diera por ausente. **Lo que el candidato tenía de defecto no era la sede sino la
observación**, y por eso se descarta acá en lugar de registrarse como un séptimo.

### Lo que este inventario no va a incluir, y por qué se dice

**Los defectos que descubra el flujo del instrumento y el baseline quedan fuera.** El criterio que
manda cerrar este inventario pertenece a este flujo y a ningún otro: ninguna tarea del otro flujo lo
actualiza ni lo verifica, así que decir «los va a agregar» sería una promesa sin dueño contractual.
Quedan registrados como pendientes en los artefactos de trabajo de ese flujo. **La pérdida de alcance
se declara acá en lugar de taparse**, que es el mismo trato que esta fase le da a la completitud del
inventario de despachos.
