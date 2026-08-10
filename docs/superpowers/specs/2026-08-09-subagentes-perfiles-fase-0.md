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
