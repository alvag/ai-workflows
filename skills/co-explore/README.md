# co-explore

**Exploración paralela cross-model, con dos workers frescos.** Se despacha **uno por familia**
(Codex y Claude) a explorar el mismo código read-only, con el mismo paquete de contexto y sin verse
entre sí. El conductor **no explora**: arbitra. Lee el **índice compacto** de cada worker y abre el
**detalle** solo ante divergencia, alto riesgo, baja confianza o una decisión que arbitrar.

## Qué es

`co-explore` produce **dos mapas del terreno independientes entre sí**, para que las diferencias
salgan a la luz antes de decidir. El conductor no aporta un tercero: su trabajo es arbitrar entre
los dos con el menor contexto posible. Sirve para cuatro cosas, según
`mode`:

- **`explore`** (pre-spec, lo invoca SDD): mapear el terreno antes de una `spec.md` — archivos
  relevantes, puntos de reúso, riesgos, enfoque sugerido.
- **`counter-plan`** (pre-plan/pre-reparto, lo invoca SDD): un contra-enfoque propio para una spec
  aprobada.
- **`investigate`** (standalone, fuera de SDD): investigar un bug — dos modelos forman hipótesis
  de causa raíz por su lado y el conductor las sintetiza en **hipótesis rankeadas + plan de
  verificación**. No arregla ni verifica ejecutando como parte de la skill.
- **`debate`** (standalone, fuera de SDD): ayudar a decidir entre opciones abiertas cuando no
  estás seguro — dos familias forman posturas independientes, se critican en rondas y el
  conductor sintetiza sin elegir.

El resultado es un **envelope**: `outcome`, la rama de degradación alcanzada, la diversidad
efectiva, y por cada contribuyente sus rutas de índice y detalle (degradado, sin bloquear
nunca a la llamadora).

```
                        ┌──► worker Codex  ──► índice + detalle ──┐
paquete de contexto ────┤                                         ├──► conductor: ÁRBITRO
   (idéntico, sin       └──► worker Claude ──► índice + detalle ──┘     · lee los dos ÍNDICES
    hipótesis de nadie)                                                 · abre DETALLE por disparador
                                                                        · cierre + envelope
```

Cada worker entrega **dos capas**: un índice que enumera *todos* sus hallazgos —con ID estable,
severidad, confianza y punteros— y un detalle con el desarrollo completo. El conductor consume
siempre el índice entero; el detalle, solo la entrada que un disparador justifica. Ese es el ahorro
de contexto que el diseño compra.

El valor no es que un worker "ayude": es que los dos mapas son **independientes**, ninguno ve al
otro, y sus diferencias salen a la luz antes de que las decisiones queden tomadas. Dos exploraciones convergen fácil (son hechos + hipótesis); dos
conclusiones ya tomadas no — por eso el punto de encuentro es temprano, en los hallazgos. La
síntesis la hace el conductor: compara ambos informes, hace competir enfoques (o hipótesis de
causa raíz, en `investigate`) en méritos, y decide con rationale auditable en `synthesis.md`.

En los modos SDD, ese mismo informe alimenta más adelante la **crítica informada** de
`cross-review`: si esa skill está instalada, recibe los **índices y la síntesis** (y la sesión que fije su matriz,
si existe) como contexto persistente del gate, en vez de partir de cero. `co-explore` **no revisa
artefactos escritos** (eso es `cross-review`), **ni arregla el bug** (eso es
`superpowers:systematic-debugging`), **ni implementa** (eso es `cross-implement`): produce
hallazgos e hipótesis propios que compiten con los del conductor. Es la primera pieza del trío
cross-model — `co-explore` (explorar) · `cross-review` (criticar el diseño) ·
`cross-implement` (implementar cruzado) — todas opcionales, degradables y encadenables.

## Índice paginado y el cuarto estado

Dos capacidades que cambian lo que la skill devuelve:

**El índice se pagina sin perder nada.** Si un worker encuentra más hallazgos de los que entran en
una página, se crean páginas adicionales y un metaíndice que las lista con sus IDs. El presupuesto
limita el tamaño de cada entrada y de cada página, **nunca el total de hallazgos**. El detalle sigue
siendo un archivo por worker: es la capa que se abre por ID, así que paginarla no compraría nada.

**`clarification-needed` es un cuarto estado del worker.** Cuando una ambigüedad le impide seguir
mapeando, el worker frena, **entrega igual lo que alcanzó a mapear** y adosa la pregunta con su
impacto. El conductor intenta resolverla desde el paquete de contexto o el repositorio antes de
escalártela. Es una excepción acotada a la regla de que el explorador nunca se bloquea por dudas:
solo aplica cuando el resto del mapa depende de la respuesta.

## Cuándo usarla

- La invocan `sdd-flow` y `sdd-orchestrator` (modos `explore`/`counter-plan`) cuando
  `co_explore` está activo (modo embebido, post-`gather-context` o pre-`plan`/reparto).
- Modo directo `explore`: `/co-explore <ticket|descripción>` → corre la síntesis y presenta la
  conclusión.
- Modo directo `investigate`: `/co-explore <bug>` o "que Codex investigue este bug en paralelo" →
  dos modelos investigan la causa raíz, el conductor sintetiza hipótesis rankeadas + plan de
  verificación, y ofrece el handoff a `systematic-debugging`.
- Pedidos en lenguaje natural: "que Codex explore/investigue esto en paralelo".
- Override conversacional en una corrida de `sdd-flow`/`sdd-orchestrator`: "con co-exploración" /
  "sin co-exploración" → fuerza `mode: on`/`off` para esa corrida.

## Cuándo NO usarla

- **Para revisar artefactos ya escritos** (`spec.md`, `plan.md`, `tasks.md`, reparto): eso es
  `cross-review`. `co-explore` corre **antes** de que el artefacto exista.
- **Para atacar un enfoque ya elegido** (aunque no haya artefacto): eso es el **modo draft** de
  `cross-review`. Regla rápida: **¿mapa o veredicto?** — terreno abierto, sin enfoque decidido →
  co-explore (mapa); enfoque ya decidido que quieres stress-testear → cross-review draft
  (veredicto).
- **Para arreglar o verificar el bug** (en `investigate`): la skill termina en hipótesis + plan de
  verificación; verificar/arreglar es `superpowers:systematic-debugging`, el paso siguiente.
- **Esperando que el conductor aporte su propio mapa:** en la topología nominal no lo hace, y es
  deliberado. Solo vuelve a explorar si un worker cae y la corrida degrada — y entonces se declara
  qué diversidad quedó.
- **En cambios triviales** (modos SDD): el default por complejidad es "nunca" (ver "Configuración");
  no aporta frente al costo de dos exploraciones completas.

## Requisitos

Ninguno obligatorio: es una **capacidad opcional**. Para que la exploración efectivamente ocurra,
hace falta un **segundo modelo de otra familia que el autor** (el agente que conduce la skill):

- Autor Claude → Codex, vía `codex exec -s read-only` en el PATH.
- Autor GPT/Codex → Claude, vía `claude -p --allowedTools=Read,Grep,Glob` en el PATH.

**`cross-review` recomendada (no obligatoria).** Si está instalada en el entorno, aporta el
algoritmo canónico de descubrimiento del revisor (`cross-review/reference.md` → "Descubrir el
revisor") y consume el informe de esta skill como contexto persistente para su propia crítica
informada en el gate. Sin ella, `co-explore` usa su propio fallback mínimo (mismo algoritmo de
descubrimiento por capacidad).

Sin el modelo de la otra familia disponible, con `mode: off`, o ante un fallo en runtime, la skill
devuelve `UNAVAILABLE` en una línea y la llamadora sigue con la exploración del conductor solamente.

## Instalación

Copia (o symlinkea) la carpeta `co-explore/` al directorio de skills de tu entorno, junto a
`sdd-flow/` y, si la usas, `cross-review/`:

```
<skills>/
├─ sdd-flow/
├─ cross-review/     # opcional, recomendada
└─ co-explore/
   ├─ SKILL.md
   ├─ reference.md
   ├─ corridas-en-vuelo.md
   └─ README.md
```

Como `investigate` es standalone (no SDD), conviene instalarla a **scope usuario**
(`~/.claude/skills/` para Claude Code, `~/.agents/skills/` para Codex) en vez de por proyecto:
así está disponible en cualquier repo y es inmune a los worktrees (el cwd deja de importar).

**Cuidado con las copias mezcladas.** El contrato del sobre viaja replicado: cada skill que despacha
trabajo delegado lleva su propio `corridas-en-vuelo.md`, y las siete copias son byte-idénticas por
construcción. Si actualizas `co-explore/` y dejas `cross-review/` o `cross-implement/` en una versión
anterior, tu instalación queda con versiones **mezcladas** —dos skills despachando sobre el mismo
repo bajo dos contratos distintos, que es exactamente lo que la copia byte-idéntica existe para
impedir— y nada en tu entorno lo detecta: el chequeo de identidad vive en el repo de autoría, no en
tu directorio de skills. Para reconocer a ojo cuál quedó atrás, la **primera línea** de cada copia
nombra su **sede canónica**, `cross-review/corridas-en-vuelo.md`: compara cada copia contra esa y
actualiza la que difiera.

## Configuración

Clave **top-level** `co_explore` (hermana de `cross_review`, **no** anidada — son ortogonales) en
`.specify/config.yml` (`sdd-flow`) o en el `manifest.yml` de la orquestación (`sdd-orchestrator`).
**Gobierna solo los modos `explore`/`counter-plan`; `investigate` es standalone y no lee config**
(su deadline se overridea conversacionalmente):

```yaml
co_explore:
  mode: auto        # auto (por complejidad: complejo on, normal opt-in, trivial nunca) | "on" | "off"
  deadline: 600     # segundos (explore; counter-plan usa 300 salvo override)
```

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default por complejidad**. `co_explore` es **ortogonal** a `cross_review.mode`: esta clave
gobierna la exploración paralela y el contra-enfoque; `cross_review.mode` gobierna las críticas en
los gates. Detalle completo en `SKILL.md` → "Configuración".

## Ejemplos de uso

**1. Embebida por sdd-flow en un cambio complejo (automático):** al clasificar el cambio como
*complejo*, `sdd-flow` invoca esta skill con `mode: explore` en el gate post-`gather-context`
(default `complex`: on). El explorador corre en background mientras `sdd-flow` hace su propia
exploración; en el punto de encuentro, ambos informes se sintetizan (convergencias/divergencias +
duelo de enfoques) antes de escribir `spec.md`.

**2. Override conversacional en un cambio normal:**
```
/sdd-flow empezar PROJ-128: exportar resultados a CSV desde la tabla de reportes, con co-exploración
```
→ *normal* es opt-in por defecto (off salvo pedido); el override activa `mode: on` para esa
corrida, y `sdd-flow` lo registra.

**3. Modo directo `explore`:**
```
/co-explore PROJ-123
```
→ infiere `mode: explore`, arma el `context_package` desde el ticket (si hay clave y MCP
disponible) y el prompt del usuario, lanza el explorador, corre la síntesis y presenta la
conclusión al usuario.

**4. Modo directo `investigate` (bug, standalone):**
```
/co-explore el selector de fechas tira "Cannot read properties of undefined" al abrir el rango
```
→ infiere `mode: investigate`, arma el `context_package` con el síntoma + evidencia de
reproducción si el conductor la capturó, lanza al revisor read-only mientras el conductor
investiga en paralelo, sintetiza y presenta **hipótesis de causa raíz rankeadas + plan de
verificación**, y ofrece verificar la líder con `systematic-debugging`.

## Qué escribe en tu repo

Los informes y el scratch viven junto al flujo que la invoca. Fuera de ahí se escriben dos archivos,
y los dos cuelgan de `.cross-model/`. El primero es el **manifest de corrida**, en `runs/`: un JSON
de unos 300 bytes por cada exploración **ya terminada**, incluidas las que se degradaron a una sola
voz — que son las que dicen con qué frecuencia la topología dual no se sostiene. Local y untracked;
agrega `.cross-model/` a `.git/info/exclude` si prefieres que git deje de nombrarlo, y apágalo con
`cross_model.manifest.mode: "off"`. Esquema en `cross-review/reference.md` → "Manifest de corrida".

El segundo es el **sobre de la corrida en vuelo**, en `.cross-model/active/co-explore/`: mientras los
dos exploradores están despachados, ahí queda registrado cuál salió por cada familia, dónde escribe
cada uno, por qué transporte viaja y hasta cuándo se lo espera. Es lo que permite que una sesión que
arranca de cero —o el mismo conductor, después de que su turno se cortó respondiendo otra cosa—
encuentre la exploración en vuelo en vez de darla por perdida o lanzar otra encima. El archivo se
retira cuando la corrida llega a un final comprobado y sus dos informes quedaron adjudicados, así que
`active/` contiene únicamente lo que sigue corriendo. El contrato completo está en
`corridas-en-vuelo.md`, hermano de `reference.md`.

**El sobre no es telemetría, y por eso `cross_model.manifest.mode` no lo apaga.** Esa clave gobierna
el manifest, que se escribe cuando la corrida ya terminó y existe para poder mirar cien juntas y
decidir si la segunda voz se gana su costo. El sobre resuelve otro problema —no perder el hilo de lo
que está corriendo ahora—, así que es obligatorio e **independiente** de esa clave: un proyecto que
decidió no medir sus exploraciones sigue necesitando saber qué workers tiene despachados. Tampoco hay
una clave propia que lo desactive.

## Archivos

- `SKILL.md` — el flujo, las reglas, el contrato de invocación y la guía de síntesis.
- `reference.md` — prompts de exploración por modo, formato del informe, plantilla de
  `synthesis.md`, descubrimiento del revisor, latencia y deadlines, archivos de trabajo.
- `corridas-en-vuelo.md` — el contrato del sobre, copia byte-idéntica de su sede canónica.
- `README.md` — este archivo.
