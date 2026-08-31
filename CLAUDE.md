# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Repositorio de **autoría de Agent Skills** (formato open de https://agentskills.io). No es una app: no hay build ni runtime. El "código" son skills en Markdown que instalás en `~/.claude/skills/` y que Claude Code (u otro cliente compatible) carga bajo demanda. El idioma de todos los artefactos es **español neutro** (ver preferencias globales del usuario).

Las skills forman un ecosistema **cross-model** (Claude ↔ Codex) y de **Spec-Driven Development (SDD)**. El concepto central que atraviesa todo: hay **solo dos familias** de modelos, Claude y GPT/Codex. El modelo que conduce (el "conductor", autor del plan/exploración) delega en un modelo de **la otra familia** para obtener una opinión o implementación independiente, y luego sintetiza o revisa. Nunca decir "otro modelo" a secas: es "la otra familia".

> **Familia opuesta y salida consciente.** La familia opuesta sigue siendo la **doctrina y el
> default** de `cross-review`, `cross-implement` y `debate`: es la que rompe la correlación de
> errores. `cross_model.families` puede elegir explícitamente un worker fresco de la misma familia
> que el conductor. Esa **salida consciente** conserva independencia de proceso, pero pierde
> diversidad de familia; la corrida debe nombrar ese costo y recomendar revisión humana. En la
> topología dual de `co-explore`, la diversidad se mide entre los workers seleccionados y el
> conductor solo arbitra.

## El techo de la verificación (tres reglas, no negociables)

El producto de este repo son las skills. La verificación es **medio**, no producto. Sin un techo
explícito, el endurecimiento de guardas no tiene condición de salida: cada guarda barata que resulta
mentirosa se responde endureciéndola, endurecer produce Python, Python produce fixtures, fixtures
producen sellos, y los sellos producen guardas que verifican sellos. Estas tres reglas son ese techo.
Cada una lleva **disparador, efecto y excepción**: un enunciado sin las tres no es aplicable.

### Regla 1 — escalera de evidencia

> **Disparador:** al escribir una fila del contrato de verificación.
> **Efecto:** usar el escalón más barato que alcance —inspección documentada → `grep`/`rg` de una
> línea → bloque de shell → script—. El default es `grep`.
> **Excepción:** subir un escalón exige escribir **por qué el anterior no alcanza**, y no vale
> "podría fallar": vale *falló, acá está el caso*.

### Regla 2 — techo de proporción

> **Disparador:** al cerrar `implement`, **antes** del gate de revisión manual.
> **Efecto:** si `numerador > denominador`, **el flujo se detiene**.
> **Excepción:** continúa solo con excepción aprobada por el usuario en ese gate, con el cálculo y
> el motivo a la vista.

- **Los dos términos, y qué cae en cada uno.** El **andamiaje** es todo lo que está bajo `scripts/` o
  `tests/`, más los archivos de test (`*.test.*`) y los verificadores (`verificar-*`) dondequiera que
  vivan — los patrones van escritos porque "un archivo de verificación" no es decidible y ya se
  resolvió distinto en dos flujos. El **producto** son
  las dos sedes de skills: `skills/` y `.agents/skills/`. Son dos porque hay una skill del ecosistema
  que vive fuera de `skills/`, y con una sola sede un flujo que la tocara quedaría con denominador
  cero, bloqueando por una razón que no es la suya. De la partición se sigue que
  `ninguna línea del diff puede contar en ambos` términos.
- **Un corpus de casos conserva su clase aunque viva dentro de una skill.** Si una skill necesita
  fixtures o casos para verificar sus scripts, ese corpus es **andamiaje**, no producto: cuenta en
  el numerador y queda fuera del denominador. La función del archivo manda sobre la sede; clasificar
  el corpus como producto solo por vivir bajo `skills/` financiaría su propia verificación.
- **Es una `lista cerrada`, con lo que eso cuesta.** Una lista se desactualiza sola, y su disparador
  de actualización es concreto: agregar una sede de producto, o un patrón de verificación nuevo. Se
  eligió sobre un criterio por tipo —"todo ejecutable es andamiaje"— porque ese criterio, medido
  contra el repositorio, metía al numerador el runtime y el transporte cross-model, que no son
  verificación. `tests/` se nombra de forma **preventiva**: hoy está vacío. Y hay archivos que no
  caen en ninguno de los dos términos, como la configuración de agentes y ese transporte: eso es
  correcto y no un hueco, porque no son ni el producto de este repo ni el andamiaje que lo verifica.
- **Numerador** — con denominador mayor que cero, la suma de líneas agregadas menos borradas,
  `por archivo, con piso en cero por archivo`. El piso va por archivo y no sobre el total porque
  sobre el total un borrado grande en un archivo financiaría crecimiento en otro. Así una
  reindexación pura —que agrega y borra la misma cantidad— da cero, que es lo que corresponde: ahí el
  andamiaje no creció, se reordenó. **Las líneas agregadas a un script existente cuentan igual que las
  de un archivo nuevo**: si no, la regla 3 se evade engordando lo que ya está.
- **Denominador** — las líneas **agregadas** al producto en el mismo diff, en bruto. La asimetría con
  el numerador es deliberada: el numerador mide cuánto **creció** el andamiaje y el denominador
  cuánto **producto** trajo el flujo, así que borrar producto no debe inflar el término de abajo.
- **Denominador cero** — `con denominador cero el numerador se mide bruto`, así que el flujo se detiene
  salvo que ese numerador bruto sea **cero**. El neto existe para no castigar el reordenamiento que **acompaña** a un
  cambio de producto; sin producto no hay nada que acompañar. Sin esta condición, 100 líneas
  agregadas y 100 borradas en un script sin tocar el producto pasarían — y la fórmula anterior, que
  contaba solo agregadas, sí frenaba ese caso.
- **Borrados** — `descuentan solo cuando hay producto` en el diff, que es la rama neta. Retirar
  andamiaje nunca puede violar el techo.
- **Cómo y cuándo se mide** — con `git diff --numstat <base_commit>` **después de implementar**, más
  `git ls-files --others --exclude-from=.gitignore -z` para los archivos nuevos: el diff no ve lo que
  todavía no está trackeado, y el techo se mide antes del staging. Un rename `se atribuye al destino`, con
  las agregadas y borradas de su contenido, así que un rename puro aporta cero. Ante una fila no
  numérica —un binario— `la medición se detiene` y se resuelve a mano, en vez de leer el guion como
  un cero. Medirlo en el gate de tasks daría cero en ambos términos: ahí todavía no se tocó una línea.
- **Por qué la enumeración no usa `--exclude-standard`, que es lo que uno escribiría.** Ese flag aplica
  **tres** fuentes de exclusión —los `.gitignore` del árbol, el `.git/info/exclude` del clon y el
  `core.excludesFile` del usuario— y **dos de las tres no viajan con el commit**. Con él, el mismo commit
  medido en dos clones da números distintos por la configuración de cada persona, y el veredicto deja de
  ser una propiedad de lo que se escribió. `--exclude-from=.gitignore` lee **solo** el archivo versionado:
  medido en un repositorio de prueba, ignora `.git/info/exclude` en las dos direcciones. Si ese archivo no
  existe, `la medición se detiene`, porque sin fuente versionada no hay medición reproducible; degradar en
  silencio a la enumeración vieja devolvería un número dependiente del clon con apariencia de válido.
- **Artefactos generados: no cuentan, en ninguno de los tres términos.** Lo que ninguna persona escribió
  no puede contar como escrito. El dominio es una `lista cerrada`, y es la tercera de esta regla:

  | Patrón | Qué es |
  |---|---|
  | `__pycache__/` | bytecode de Python, que nace al importar un módulo |
  | `.pytest_cache/` | cache de corridas de test |
  | `dist/` | salida de empaquetado |
  | `coverage/` | reportes de cobertura |
  | `node_modules/` | dependencias instaladas |
  | `.DS_Store` | metadatos del explorador de archivos de macOS |

  El `disparador del dominio de generados: agregar o retirar un patrón` es cuando el repositorio empieza
  o deja de producir una clase de artefacto que nadie escribe. Los seis patrones viven además en el
  `.gitignore` versionado, y `medir-techo.py --dominio` los imprime para que las tres representaciones se
  puedan comparar con un `diff` en vez de confiar en que alguien las mantuvo iguales.

  El caso que obligó a escribir esto: un `.pyc` de 124 líneas, generado por una guarda del propio
  repositorio al importar otra, entraba al numerador como andamiaje recién escrito. Y el simétrico es peor
  porque **afloja** el techo: un `.DS_Store` bajo `skills/` sumaba al denominador.
- **Los directorios de artefactos del ecosistema SDD tampoco cuentan**, y su descarte vive **acá** y no en
  el `.gitignore`: `.plans/`, `.specify/`, `.cross-model/`, `.cross-review/`, `.co-explore/`,
  `.cross-implement/`, `.handoffs/` y `.superpowers/`. La razón no es de estilo — la regla 10 de `sdd-flow` prohíbe
  explícitamente agregarlos a un ignore compartido, porque son un flujo personal y no del equipo. Sin este
  descarte, enumerar sin las fuentes locales mete al numerador los archivos de flujos viejos: medido, dos
  rutas `*.test.mjs.before-promotion` bajo `.plans/archived/` clasifican como andamiaje.
  `.superpowers/` está en la lista por la misma razón y no por simetría: este repositorio se desarrolla
  a sí mismo con estas skills y ahí viven sus briefs, reports y diffs de review. Su riesgo es el mismo
  y está medido: un archivo llamado `verificar-…` o `….test.…` ahí dentro clasifica como andamiaje.

  **Lo que queda afuera, y por qué.** `.idea/` es configuración del IDE y no entra en ninguna de las dos
  listas: hoy todo su contenido clasifica `ninguno`, y agregarlo expandiría el dominio a herramientas de
  terceros sin un caso medido que lo pida. La regla 1 exige que un escalón se suba con evidencia de que
  el anterior falló, no con la sospecha de que podría.
- **Esta regla mide el techo y `no gobierna qué se stagea`.** Qué archivo entra a un commit lo decide el
  paso `implement` de `sdd-flow`, que es portable y no puede depender de este documento. Son dos criterios
  con dominios disjuntos, y decirlo es lo que impide que se lean como discrepantes: durante un tiempo las
  dos sedes hablaron de archivos generados sin declarar dónde terminaba cada una, y sobre el mismo hecho
  tres flujos resolvieron distinto.
- **Lo que la fórmula no detecta** — mover contenido entre archivos distintos cuenta como crecimiento
  en el destino. Es consecuencia de medir por archivo, la misma propiedad que impide que un borrado
  financie crecimiento ajeno. No se agrega mecanismo para eso: la regla 1 pide evidencia de que el
  escalón barato falló, y ese caso todavía no ocurrió.
- **Por qué bloquea** — un techo que solo obliga a declarar es un techo **sin condición de salida**,
  que es exactamente la causa que estas reglas vienen a cortar.

### Regla 3 — ningún archivo nuevo en el `scripts/` raíz dentro de un flujo de skills

> **Disparador:** al crear un archivo bajo `scripts/` durante un flujo cuyo objeto son las skills.
> **Efecto:** no se crea. Si de verdad hace falta, es un **flujo aparte**, con su propio gate y con
> la evidencia de que la guarda barata falló.
> **Excepción:** ninguna dentro del flujo en curso. La escalada es una decisión con gate propio, no
> un atajo a mitad de una task.

**Qué hace el disparador ante un artefacto generado.** La señal de esta regla comparte enumeración con
el numerador de la regla 2, así que hay que decir qué pasa con lo que aparece bajo `scripts/` sin que
nadie lo escriba: `un artefacto generado no dispara la señal`. Se reconoce por el dominio cerrado de la
regla 2, y queda fuera del contador igual que del numerador.

**Lo que no cambia es la prohibición.** Un archivo **escrito** bajo `scripts/` sigue prohibido sin
excepción; lo único que se acota es qué cuenta como archivo nuevo. Sin esta distinción el bytecode de
una guarda del propio repositorio disparaba una regla pensada para frenar andamiaje escrito a mano, y el
veredicto pasaba a depender de si alguien había corrido un verificador antes de medir.

**Los scripts propios de una skill viven en `skills/<nombre>/scripts/`.** Esa es su sede de producto
y esta regla no prohíbe crearlos: la prohibición alcanza al directorio `scripts/` de la raíz. Sus
tests o corpus siguen la clasificación funcional de la regla 2.

## Anatomía de una skill (patrón obligatorio del repo)

Cada `skills/<nombre>/` tiene tres archivos, alineados con la **divulgación progresiva** de agentskills.io:

- **`SKILL.md`** — frontmatter + instrucciones que se cargan al **activar** la skill. Es lo que el agente lee y ejecuta.
- **`reference.md`** — detalle técnico pesado (matrices de detección, invocación de CLIs, casos borde, PowerShell vs POSIX). Se carga **solo cuando el SKILL.md lo indica explícitamente** ("ver `reference.md` → sección X"). Acá va lo que no se necesita en cada corrida.
- **`README.md`** — documentación para humanos (qué hace, cuándo usarla, instalación). No lo lee el agente en ejecución.

**La capa de referencia puede ser más de un archivo.** Cuando el detalle de una skill se lee en
**momentos distintos**, se parte en varios `.md` hermanos de `reference.md` (el patrón `pptx` de
agentskills.io, con su `pptxgenjs.md` y su `ooxml.md`). El criterio de corte es el momento de
lectura, no el tamaño: cargar en cada corrida un documento que solo hace falta cuando algo falla es
desperdiciar contexto. `cross-implement` es el caso vivo — `reference.md` (toda corrida),
`contrato-verificacion.md` (antes de delegar) y `ownership.md` (cuando una ronda falla)—, y su
`reference.md` abre con una tabla que dice cuál se lee cuándo. `SKILL.md` y `README.md` siguen
siendo **uno** por skill.

### Qué dispara verificación, y qué no

La **regla de entrada** gobierna la lista de abajo, y por eso va antes que ella.

> **Disparador:** al cerrar un cambio cuyo objeto son las skills.
> **Efecto:** si el cambio **no toca ninguna** de las superficies compartidas que nombran los
> disparadores de abajo, **no corre ninguna verificación**. Editar el texto de un `SKILL.md`, un
> `reference.md` o un `README.md` —redactar, agregar un paso, cambiar un ejemplo, reescribir una
> sección— es el caso ordinario y no dispara nada. El techo tampoco: si el diff no toca andamiaje, su
> numerador es cero por construcción y medirlo no puede cambiar el veredicto.
> **Excepción:** los disparadores de abajo, que se leen **por lo que el cambio toca** y no por lo que
> el cambio parece.

**Por qué existe.** Medido el 2026-08-30: de las 4.370 líneas de `scripts/`, **3.008 (69 %)** son dos
verificadores —`verificar-sobre-en-vuelo.py` y `verificar-vistas-config.py`— cuyo trabajo es comprobar
que **copias de un mismo dato** no divergieron, no que una skill funcione. Correr esa batería ante un
cambio de prosa hace pagar la deuda de una duplicación que ese cambio no introdujo, y no es barato:
dos de las cinco invocaciones obligatorias corren la misma suite —`--ac 16` invoca `python3 -m tests`—
y dos están **rojas en `main`**, así que cada corrida termina en un juicio a mano sobre si el rojo es
el de siempre. La lista de abajo no se toca: lo que cambia es que **se lee para decidir si algo corre,
no para correrlo todo**.

**La matriz de superficies.** Es la **sede operativa** del disparo: si el cambio no toca ninguna de
estas filas, no corre nada. Los bullets de más abajo conservan el **fundamento** de cada guarda —por
qué existe y qué defecto medido la produjo—, no su disparador; el disparador vive acá y en un solo
lugar.

| Si el cambio toca… | Correr | Se lee por |
|---|---|---|
| el **frontmatter** de una skill, su `name`, o crea/renombra una skill | `skills-ref validate ./skills/<nombre>` | **contra la base**, no contra cero (ver abajo) |
| `config-ejemplo.md`, `manifest-ejemplo.md`, o el esquema/"Configuración" de alguno de sus seis dueños | `python3 scripts/verificar-vistas-config.py` | **código de salida** |
| `corridas-en-vuelo.md` | `verificar-sobre-en-vuelo.py --sincronizar`, después `--ac 13` | **código de salida** |
| una **receta de despacho**, una marca `despacho:`, la tabla de política de aislamiento, o el inventario de puntos de despacho | `--ac 12` **y** el verificador de aislamiento (`correccion`) | **código de salida** |
| el contrato del manifest de corrida, sus autoridades o su cierre en los cuatro productores | `--ac 17` | su salida |
| cualquier `.py` bajo `scripts/`, o `tests/` | `python3 -m tests` **y** el autotest del verificador que tocaste | **código de salida** |
| la regla 2 o `medir-techo.py` | `medir-techo.test.py` y sus dos autotests (`--autotest-banda`, `--autotest-dominio`) | **código de salida** |
| **retirar** una vía, un modo o una capacidad | los veinte modos `--ac` (ver el bullet del retiro) | **código de salida** |
| cerrar `implement` con andamiaje en el diff | `python3 scripts/medir-techo.py <base_commit>` | código de salida |

**Nada más dispara.** La prosa de un `SKILL.md`, un `reference.md` o un `README.md` no está en la
tabla, y ese es el caso ordinario. La tabla se lee por **lo que el cambio toca**, nunca por el nombre
de la sección que lo contiene: anclar un disparador a un título es el defecto medido de `--ac 12`,
cuyo enunciado viejo no disparaba ante un cambio de receta.

Al crear o editar skills, seguí las buenas prácticas de agentskills.io (referencia pedida explícitamente):
- **Specification:** https://agentskills.io/specification — `name` (== nombre del directorio, minúsculas/números/guiones, sin guion inicial/final ni `--`), `description` (máx 1024 chars, tercera persona, qué hace **y cuándo** usarla, con keywords de trigger).
- **Best practices:** https://agentskills.io/skill-creation/best-practices — SKILL.md idealmente <500 líneas / <5000 tokens; mover el detalle a `reference.md`; dar **un default, no un menú**; secciones "Gotchas" y "red flags"; procedimientos reutilizables, no respuestas puntuales.
- `skills-ref validate ./skills/<nombre>` (de https://github.com/agentskills/agentskills) comprueba el spec. Su disparador es el **frontmatter**, no el cuerpo: validar prosa no cambia su veredicto. **Y su veredicto se lee contra la base, no contra cero**: hoy fallan cuatro de las ocho skills —`bitbucket-code-review`, `sdd-flow`, `sdd-orchestrator` y `sdd-pr-feedback`— con `Unexpected fields in frontmatter: argument-hint, disable-model-invocation`. Ese rojo es **deliberado**: son claves reales de Claude Code que el spec de agentskills.io no contempla, y quitarlas para poner la validación en verde rompería el comportamiento solo-slash que la sección de frontmatter explica. Lo que hay que comprobar es que los diagnósticos de la skill tocada sean **los mismos que antes del cambio**.
- **El techo de proporción de la regla 2 se mide con `python3 scripts/medir-techo.py <base_commit>`**, al cerrar `implement` y antes del gate de revisión manual. Imprime en una línea los archivos nuevos bajo `scripts/`, el numerador, el denominador y el veredicto, y distingue por código de salida `pasa` (0), `bloquea` (1), error de invocación (2) y **medición detenida** (3) — que no es un veredicto y no se puede leer como uno. La **sede normativa de la fórmula sigue siendo la regla 2**: el script la implementa y ancla el hash de esa sección, así que si la regla cambia se detiene en vez de calcular con una fórmula vieja. Reimplementarla a mano en un bloque del plan es lo que produjo doce defectos en tres flujos; su suite —`scripts/medir-techo.test.py`, con `--listar` y `--autotest`— los tiene mapeados uno por uno.
- **`verificar-vistas-config.py`** cubre `config-ejemplo.md` y `manifest-ejemplo.md` contra sus **seis dueños** (`sdd-flow`, `sdd-orchestrator`, `cross-review`, `co-explore`, `cross-implement`, `knowledge-vault`): valida que esas vistas sigan fieles a sus dueños (claves, enums, valores, marcas `[def]`/`[ej]`/`[obl]` y comillas en `on`/`off`).
- `corridas-en-vuelo.md` es **contenido replicado**: la sede canónica es `skills/cross-review/corridas-en-vuelo.md` y las otras seis son copias byte-idénticas generadas. **Editar una copia a mano es una divergencia silenciosa**; el generador la evita y el hash la detecta.
- **El baseline está sellado como historial y salió del gate.** `scripts/baseline-sobre-en-vuelo.md` conserva los rojos conocidos y las transiciones de v2 a v13, que es su valor real; `--validar-baseline` sigue existiendo pero **ya no es obligatorio y no se re-emite**. Motivo, medido: su validador comprueba forma, `sha256` y vínculo con el commit — nunca ejecuta V1–V20 ni contrasta los estados declarados contra corridas, así que una tabla inventada de veinte `GREEN_ALREADY` bien formada pasaba igual. A cambio, ataba cada cambio del `.py` a re-emitir veinte estados a mano: procedencia al precio de una ceremonia por commit.
- `--ac 12` cubre el inventario de los **once** puntos de despacho: verifica biyección entre lo declarado en el árbol y el inventario del verificador, así que agregar o retirar un punto de despacho sin actualizarlo la pone roja.
- `--ac 17` cubre el contrato del manifest de corrida en `skills/cross-review/reference.md` y su cierre en los cuatro productores (`co-explore`, `cross-review`, `cross-implement`, `bitbucket-code-review`).
- **Un retiro corre la batería completa, no el subconjunto documentado.** `verificar-sobre-en-vuelo.py` tiene **20 modos `--ac`** y las unidades de arriba nombran **tres**; los otros diecisiete existen, corren y pueden ponerse rojos sin que ningún procedimiento los invoque. Al **retirar** algo —una vía, un modo, una capacidad— hay que correr los veinte (`for m in 1 1b 2 2b 3 3b 4 5 6 7 8 9 10 11 12 13 14 15 16 17`), porque retirar es la operación que **arrastra cláusulas ajenas**: el texto que rodea a lo que se va se lleva puesto lo que no era suyo, y lo que queda **se lee perfecto**. Ya pasó: el retiro del transporte por panes borró una cláusula de doctrina que vivía dentro de un párrafo sobre esa vía, `--ac 1b` la cazó en el acto, y estuvo roja **noventa commits** porque nadie la corría.
- Las **tres** invocaciones de `verificar-sobre-en-vuelo.py` que se leen por código de salida son `--ac 12`, `--ac 13` y `--autotest`: **0 en verde**. Las de `verificar-vistas-config.py` (sin banderas) y `python3 -m tests`, lo mismo.
- **`--ac 16` salió de las obligaciones**, y sigue disponible para quien lo quiera correr. No verificaba nada propio: ejecutaba `verificar-vistas-config.py` y `python3 -m tests` —las dos ya obligatorias por su cuenta— más la comparación de `skills-ref` contra la base, que ahora vive en la fila del frontmatter de la matriz. Medido: **719 s**, contra **560 s** de la suite que volvía a ejecutar. Era la mitad del costo de un gate para una sola propiedad que cabe en una fila de tabla.
- La suite durable `python3 -m tests` sustituye las auditorías y el reporte del arnés retirado: un
  código `0` acredita el catálogo migrado, las guardas portadas y las cinco dimensiones del oracle
  durable. La evidencia dual histórica vive sellada fuera del corpus y no se regenera.

- **El verificador de aislamiento** cubre cuatro superficies: una receta de despacho, una marca `despacho:`, la tabla de política de aislamiento y este mismo bloque. Es un bloque de shell —no hay archivo bajo `scripts/`, regla 3— con dos salidas que son **dos propiedades distintas**:

  ```bash
  # uso: verificar_aislamiento <raíz> <correccion|candidatos>
  verificar_aislamiento() {
    raiz="${1:?raíz}" modo="${2:?modo}"
    pol="$raiz/skills/cross-review/reference.md"
    # la política se LEE de su tabla delimitada; duplicar los flags acá crearía una segunda sede
    leer_pol() {
      awk -v fam="$1" '/politica-aislamiento:inicio/{f=1;next} /politica-aislamiento:fin/{f=0}
                       f && $0 ~ "^\\| `" fam "`"' "$pol" |
        grep -o '`--[a-z-]*\( [a-z]*\)\?`' | tr -d '`' | paste -sd'|' -
    }
    CM=$(leer_pol codex); LM=$(leer_pol claude)
    [ -n "$CM" ] && [ -n "$LM" ] || { echo "política ilegible en $pol"; return 2; }
    archivos=$(grep -Rl --include='*.md' 'despacho:inicio:' "$raiz/skills" 2>/dev/null)
    case "$modo" in
      correccion)
        salida=$(
          printf '%s\n' "$archivos" | while IFS= read -r f; do [ -n "$f" ] && grep -o 'despacho:inicio:[a-z0-9-]*' "$f"; done \
            | sort | uniq -d | sed 's/^/GLOBAL 0 /;s/$/ id duplicado/'
          printf '%s\n' "$archivos" | while IFS= read -r f; do
            [ -n "$f" ] || continue
            awk -v F="$f" -v CM="$CM" -v LM="$LM" '
              /<!-- despacho:inicio:/ {
                if (ab) { print F " " ini " " id " apertura sin cierre, o region anidada (indistinguibles desde el texto)" }
                match($0,/despacho:inicio:[a-z0-9-]+:[a-z]+/); s=substr($0,RSTART,RLENGTH)
                split(s,p,":"); id=p[3]; fam=p[4]
                if (fam!="codex" && fam!="claude") print F " " NR " " id " familia no declarada"
                ab=1; ini=NR; cuerpo=""; next }
              /<!-- despacho:fin:/ {
                match($0,/despacho:fin:[a-z0-9-]+/); s=substr($0,RSTART,RLENGTH); split(s,p,":")
                if (!ab) { print F " " NR " " p[3] " cierre sin apertura"; next }
                if (p[3]!=id) print F " " NR " " id " emparejamiento roto (cierra " p[3] ")"
                if (cuerpo ~ /^[[:space:]]*$/) print F " " ini " " id " region vacia"
                n=split((fam=="codex")?CM:LM, ms, "|")
                for (i=1;i<=n;i++) {
                  if (ms[i]=="") continue
                  # dos formas equivalentes: POSIX `--disable hooks` y PowerShell `'"'"'--disable'"'"','"'"'hooks'"'"'`
                  ps=ms[i]; gsub(/ /, "'"'"','"'"'", ps)
                  if (index(cuerpo,ms[i])==0 && index(cuerpo,ps)==0)
                    print F " " ini " " id " falta mecanismo: " ms[i] }
                ab=0; next }
              # los comentarios NO cuentan como mecanismo: nombrar el flag en prosa no lo aplica
              { if (ab) { linea=$0; sub(/^[[:space:]]+/,"",linea)
                          if (linea !~ /^#/) cuerpo = cuerpo "\n" $0 } }
              END { if (ab) print F " " ini " " id " apertura sin cierre" }' "$f"
          done )
        [ -z "$salida" ] && return 0
        printf '%s\n' "$salida"; return 1 ;;
      candidatos)
        grep -Rn --include='*.md' -e 'codex exec' -e 'claude -p' "$raiz/skills" 2>/dev/null |
          while IFS= read -r linea; do
            f=${linea%%:*}; n=$(printf '%s' "$linea" | cut -d: -f2)
            awk -v N="$n" 'NR<=N { if (/despacho:inicio:/) d=1; if (/despacho:fin:/) d=0 }
                           END { exit d?1:0 }' "$f" && printf '%s\n' "$linea"
          done
        return 0 ;;
      *) echo "modo desconocido: $modo"; return 2 ;;
    esac
  }
  ```

  **Cómo se lee.** `correccion` es el **veredicto**: 0 en verde, 1 con una línea por violación
  (`<archivo>:<línea> <id> <causa>`). `candidatos` es **evidencia de revisión**, siempre 0, y lista
  toda invocación fuera de región para que una persona la adjudique en
  `.plans/<id>/candidatos-despacho.md` con su clasificación y fundamento.

  > **Las dos cosas que no detecta, y conviene que estén escritas al lado.** Primero, **que un
  > conductor se desvíe de la receta en runtime**: esto verifica el texto documentado, no el comando
  > que se ejecutó. Segundo, y más importante, **la completitud del inventario no es automatizable** —
  > que no exista un despacho sin marcar—. No es un hueco reparable con un predicado mejor: el
  > instrumento de escalón 4 que existió para esto (`scripts/verificar-matriz-despachos.py`, retirado
  > en `d31fe87` como andamiaje sin consumidor) midió **64 sitios detectados en el árbol, 44 de ellos
  > fuera de toda sección anclada**, y la mayoría eran documentación, ejemplos y tablas de vías.
  > Distinguir un despacho real de su documentación es una adjudicación humana, y por eso `candidatos`
  > **lista** en vez de fallar. Un verificador que prometiera completitud terminaría permanentemente en
  > rojo, o —peor— con una allowlist congelada que se desactualiza sola.

> Nota: varios SKILL.md de este repo (p. ej. `sdd-flow`) exceden holgadamente el presupuesto de tokens sugerido. Es una tensión conocida por la complejidad del flujo; al editar, empujá contenido hacia `reference.md` antes que engordar el SKILL.md.

## Convenciones de frontmatter propias del repo

Más allá del spec, estas skills usan patrones consistentes que hay que respetar:

- **`description` como router:** describe modos, frases de invocación literales ("/co-explore ...", "que Codex explore esto"), **scoping negativo** ("NO es code review: eso es X") y casi siempre la cláusula **"No invocarla espontáneamente: solo ante pedido explícito del usuario o invocada por <skill>"**. Es deliberado: evita auto-triggers no deseados.
- **`disable-model-invocation: true`** (clave real de Claude Code) en las skills que deben ser **solo-slash** (`sdd-flow`, `sdd-orchestrator`, `sdd-pr-feedback`): bloquea la invocación vía Skill tool porque sus triggers son genéricos ("arma el plan", "implementa") y competirían por el auto-trigger. Consecuencia asumida y documentada en el propio frontmatter: otras skills no pueden invocarlas programáticamente (delegan leyendo sus archivos).
- **`argument-hint`** documenta la gramática de sub-comandos del router (init / implement / retoma / estado / doctor…).

## El ecosistema de skills

- **`sdd-flow`** — SDD de un solo repo, punta a punta: `constitution → gather-context → specify → clarify → create-branch → plan → tasks → implement → verify`, con gates escalados por complejidad (trivial/normal/complejo). Es la skill más grande y el hub del que dependen las demás.
- **`sdd-orchestrator`** — SDD multi-repo: un objetivo que cruza 2+ repos bajo una carpeta contenedora; arma spec madre, reparte un sub-plan por repo y delega cada uno a `sdd-flow`.
- **`sdd-pr-feedback`** — procesa comentarios de review de PRs de **Bitbucket** (MCP `bb_*`).
- **`co-explore`** — exploración paralela cross-model (read-only). Modos: `explore`, `counter-plan`, `investigate`, `debate`. La invocan `sdd-flow`/`sdd-orchestrator` cuando `co_explore` está activo; `investigate`/`debate` son standalone.
- **`cross-review`** — segunda opinión adversarial sobre **artefactos de diseño** (spec/plan/tasks), no sobre código. Modo `draft` cuando hay idea pero no artefacto.
- **`cross-implement`** — delega la implementación de un work order **congelado** a la otra familia; el conductor revisa el diff como un PR ajeno y commitea tras el gate humano.
- **`bitbucket-code-review`** — code review de PRs de **Bitbucket** (MCP `bb_*`): panel de revisores externos **uno por familia disponible**, author-aware, sobre el diff del PR; publica la decisión con gate. Es la sede de "code review sobre diffs" de la regla de fronteras.
- **`sdd-incident-intake`** — admisión del registro de incidentes: verifica un incidente contra el árbol, agrupa los que se resolverían en el mismo diff, abre un worktree sembrado con la config ignorada, despacha un `sdd-flow` y recién entonces retira los incidentes tomados. **No corrige la skill** —eso es el `sdd-flow` que despacha—: es el único punto donde `.plans/incidentes-skills.md` se vacía.

**Escalera de rigor.** Las fronteras dicen *qué* hace cada una; la escalera dice *cuál alcanza*:
respuesta local → `co-explore` (mapa, causa raíz o decisión) → `cross-review` (crítica de una
decisión escrita) → `cross-implement` (construcción desde contrato congelado) → `verify` de
`sdd-flow` (evidencia por AC). La pregunta al elegir no es cuál es la mejor sino **cuál es la más
barata que alcanza**. Canónica en `co-explore/reference.md` → "Escalera de rigor".

Regla de fronteras entre skills (aparece repetida en las descripciones y hay que preservarla): `co-explore` explora/hipotetiza · `cross-review` revisa documentos de diseño · `cross-implement` escribe código · `systematic-debugging` arreglar bugs · code review sobre diffs. No solapar.

> **«Code review sobre diffs» sí tiene skill —`bitbucket-code-review`— y el único punto ciego que sobrevive es el del autor del contrato.** Conviene tenerlo preciso porque es fácil enunciarlo de más. Quién mira un diff, y contra qué familia:
>
> | Revisor | ¿De otra familia que quien escribió el código? |
> |---|---|
> | `bitbucket-code-review` · panel externo del Paso 7 | **sí** — author-aware por contrato, uno por familia disponible. Requiere PR de Bitbucket y su MCP: es post-push |
> | `cross-implement` · el conductor (regla 4) | **sí** — la regla 8 manda que implemente la otra familia, así que el conductor revisa código que no escribió su familia |
> | `sdd-flow` · revisión final de diff | **no** — mismo modelo, y su sección lo declara |
>
> Lo que **ninguno** cubre es el par **autor del work order ↔ revisor del diff**, que en `cross-implement` es la misma familia: si el contrato se escribió ambiguo o mal, el implementador lo transcribe fielmente y el revisor comparte el punto ciego que lo produjo. Es un hueco **estrecho y de una sola clase** —no "nadie revisa diffs cross-family"—, y **hoy no se escribe nada para cubrirlo**: se mide en vez de discutirse. El log de `cross-implement` registra la clase de cada falla y si el work order admitía otra lectura, y **la condición exacta para reabrirlo vive ahí mismo**, junto al registro que la alimenta (`cross-implement/reference.md` → "Qué hacer cuando el registro muestre algo"). No se repite acá a propósito: una condición escrita en dos lados se desincroniza. Lo que sí queda decidido de este lado, porque es lo que esta regla gobierna: si alguna vez se cubre, la sede es `cross-implement` y **no se crea una skill nueva** — sería una frontera nueva contra esta misma regla y competiría con `bitbucket-code-review`.

## Invocación cross-model (el mecanismo compartido)

Cuando conduce Claude, la otra familia es **Codex**; el detalle canónico vive en cada `reference.md`. La delegación viaja por el **CLI headless**: el worker se lanza como proceso hijo y su salida se cosecha del disco. Patrón:

- **Detección de binario:** POSIX `command -v codex` · PowerShell `Get-Command codex -ErrorAction SilentlyContinue`.
- **Read-only** (co-explore, cross-review): `codex exec -s read-only -C <working_dir> --skip-git-repo-check --json ...`
- **Workspace-write** (cross-implement): `codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json ...`; resume con `codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write" ...`
- **`exec resume` NO acepta las mismas flags que `exec`** — rechaza `-C`, `-s`/`--sandbox`, `--add-dir` y cinco más. Por eso el sandbox viaja como `-c sandbox_mode=...`, y el working dir **es el cwd del proceso**: hay que posicionarse antes de invocar. Copiar el comando de lanzamiento y cambiarle el subcomando falla; y la flag que falta no siempre grita —`-C` de más corta con error, `-C` de menos opera sobre el repo equivocado con exit 0—. Tabla derivada del CLI en `cross-review/reference.md` → "Asimetría de flags entre `exec` y `exec resume`".
- **Prompt por archivo, nunca inline:** el markdown con backticks rompe el quoting del shell. POSIX pasa el prompt por `< prompt.txt`; **PowerShell no soporta `<`** → `Get-Content -Raw prompt.txt | codex exec ... -`. Todo comando nuevo que invoque un CLI debe ofrecer **ambas** variantes (POSIX y PowerShell).
- Degradación elegante: si falta el binario/MCP, avisar y continuar con lo que haya.

> **El CLI headless es el transporte, y cambiarlo exige medirlo — no que la arquitectura sea más linda.** Cada tanto aparece un runtime que promete resolver esto mejor (paneles de terminal, IDEs agénticos con threads y salida estructurada, hosts multi-máquina). Encajan: el transporte está detrás de una abstracción en los `reference.md` de `co-explore` y `cross-implement`, así que sustituirlo es posible. El criterio para juzgarlos es **transporte contra criterio**: esos runtimes resuelven el transporte —lanzar, esperar, cosechar, reanudar, aislar—, y **ninguno tiene el criterio**: no saben si les están pidiendo un mapa o una crítica, y sobre todo **no tienen el invariante de familia opuesta** (se pueden lanzar dos workers del mismo proveedor y no se enteran). De ahí que lo único que se porta bien sea plomería, nunca doctrina.
>
> **La condición para adoptar uno:** una corrida real de `co-explore` con ese transporte contra la misma corrida por CLI, comparando **latencia, fidelidad de la cosecha y líneas de plomería**. Sin ese delta medido, no se adopta. El precedente que fija la regla: la vía de paneles costó **1.245 líneas y nunca se activó** —6 de 6 corridas se fueron por CLI— y se cerró con evidencia, no con opinión. Tampoco esperar un ahorro económico: todos corren sobre la misma suscripción vía CLI headless.

## Artefactos en disco (dogfooding)

Las skills SDD escriben artefactos **locales y untracked** (nunca se commitean): `.specify/config.yml` + `constitution.md` por proyecto, y `.plans/<id>/` por flujo. **Este repo se desarrolla a sí mismo con esas skills:** `.superpowers/sdd/` contiene los artefactos SDD (briefs, reports, diffs de review) usados para construir las propias skills, y `docs/superpowers/{specs,plans}/` guarda specs y planes de diseño versionados. Al retomar trabajo, esos archivos son la memoria del flujo.

### Registro de incidentes con las skills

**Todo incidente que tengas usando las skills SDD `sdd-flow` y sus skills hermanas (`cross-review`, `cross-implement`,
`co-explore`, `bitbucket-code-review`, `sdd-pr-feedback`) se registra en
`.plans/incidentes-skills.md`, en el momento en que ocurre.** Alcanza a las skills mismas, a los
artefactos que generan y a las instrucciones erróneas que contengan: una instrucción que produce
un artefacto que otra skill rechaza, un gate que se dispara sin salida practicable, una plantilla que no
coincide con lo que su validador exige, un paso cuyo orden vuelve imposible cumplir el siguiente.

**Siempre el archivo del árbol principal del repo, nunca el del worktree en el que estés
corriendo.** Como `.plans/` es local y untracked, un worktree no lo hereda: escribir ahí crea un
segundo registro que nadie lee y que desaparece cuando el worktree se remueve, y el archivo único es
justamente lo que permite ver que un incidente se repite. Si la sesión corre en un worktree, el
árbol principal se resuelve con `git worktree list` —es la primera entrada— y el registro va a
`<árbol-principal>/.plans/incidentes-skills.md`.

El destinatario del archivo es **el agente que va a corregir la skill**, no quien trabaja en el
proyecto donde se usó: nada de rutas ni artefactos del proyecto, sí la skill, la sección o regla
concreta, qué instruía frente a qué pasó, por qué el defecto es de la skill, la consecuencia y qué
habría que cambiar.

**Una reincidencia se agrega, nunca se edita.** Si el mismo defecto vuelve a aparecer, igual o
parecido, va un registro nuevo cruzado con el anterior por su fecha y hora en el campo
`Relacionado`. Editar el registro viejo para "actualizarlo" borra la frecuencia, que es lo único que
distingue una trampa estructural de la skill de un descuido puntual. Las reglas completas del
formato viven en la cabecera del propio archivo.

## Git

- Conventional commits con **scope = nombre de la skill** afectada: `feat(sdd-flow): ...`, `fix(co-explore): ...`, `docs(sdd-flow): ...`. Un commit que toca varias skills lo indica en el cuerpo (ej: `fix: ... (co-explore) y ... (sdd-flow)`).
- Sin líneas `Co-Authored-By` ni firmas al pie (preferencia global del usuario).
