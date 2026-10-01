# Referencia — `sdd-incident-intake`

Detalle que no hace falta en cada corrida. `SKILL.md` indica cuándo abrir cada sección.

| Sección | Cuándo se lee |
|---|---|
| Verificar sin investigar | En el paso 2, si el veredicto no es evidente |
| Preparar y reanudar la vuelta congelada | Siempre, antes del primer efecto de cada selección o issue, también con `cantidad = 1`, `registro: issues` o sin declaración de 6.2 |
| El lote, vuelta por vuelta | Solo con `cantidad > 1` |
| Mirar aguas arriba | En el paso 4, siempre |
| Resolver la plataforma | En el paso 6.1, **antes** de crear nada |
| Clasificar el hook de setup | En 6.1, después de resolver y **antes** de elegir con qué crear |
| Crear el worktree | En 6.1, con la primitiva que la clasificación eligió |
| Adoptar, abrir y rotular | En 6.1, tras crear |
| Sembrar el entorno ignorado | En el paso 6.2 |
| El dossier | En el paso 6.3, al redactarlo |
| Despachar el flujo | En el paso 6.4 |
| El volcado a issues | En el modo `volcar`, antes de publicar |
| Retirar del registro | Antes de 6.1, de publicar o del gate de rechazo, y otra vez en el paso 7; también al reentrar tras un efecto |
| Cuando algo falla | Solo si el despacho no arrancó o el retiro dejó residuos |

---

## Preparar y reanudar la vuelta congelada

**Carga incondicional antes del primer efecto**, no subordinada a 6.2 ni al modo lote. Cada
selección de `despachar`, incluso un rechazo que no consume cupo, y cada issue de `volcar` inicia
una vuelta propia. `registro: issues` también crea scratch, manifiesto y unidad congelada, pero
no crea recibos ni respaldo de retiro de archivo. El scratch de siembra de 6.2 es **otro** y
solo ese se limpia tras 6.3. Al detenerse, entregar la ruta literal del scratch de vuelta;
si falta al reentrar, parar para reconciliación humana, nunca llamar de nuevo a `mkdtemp`
como si reabriera la vuelta anterior.

`preparar-vuelta` recibe la unidad extraída de **una lectura** de la referencia instalada y
guarda esos mismos bytes en `unidad.py` por creación exclusiva. Su manifiesto
`scratch-vuelta/1` contiene `vuelta_id`, `modo`, `registro_ruta` recibida,
`registro_fisico` informativa, `registro_kind`, `unit_sha256` y ruta de la unidad. La ruta
devuelta es absoluta y privada. Definir `ref`, `registro_abs` y `modo_intake` con valores
concretos de esta vuelta antes de ejecutar uno de estos bloques:

POSIX:

```sh
ref='/ruta/absoluta/de/la/copia-instalada/reference.md'
registro_abs='/ruta/absoluta/del/registro' # o 'issues'
modo_intake='despachar' # o 'volcar'
if vuelta_json=$(python3 -c 'import sys; from pathlib import Path; s=Path(sys.argv[1]).read_text(encoding="utf-8"); a="\n<!-- registro-candidato:inicio -->\n"; b="\n<!-- registro-candidato:fin -->"; x=s.split(a,1)[1].split(b,1)[0].split("```python\n",1)[1].rsplit("\n```",1)[0]; ref,reg,modo=sys.argv[1:4]; sys.argv=[ref,"preparar-vuelta",reg,modo]; exec(compile(x,ref,"exec"),{"__name__":"__main__","FROZEN_UNIT":(x+"\n").encode("utf-8")})' "$ref" "$registro_abs" "$modo_intake"); then
  scratch_vuelta=$(printf '%s' "$vuelta_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["scratch"])') || exit 3
  unidad="$scratch_vuelta/unidad.py"
  printf '%s\n' "$scratch_vuelta"
else
  vuelta_codigo=$?
  [ -z "$vuelta_json" ] || printf '%s\n' "$vuelta_json"
  printf '%s\n' 'No se pudo preparar la vuelta; no efectuar nada' >&2
  case "$vuelta_codigo" in 2|3|12) [ -n "$vuelta_json" ] || exit 3 ;; *) exit 3 ;; esac
  exit "$vuelta_codigo"
fi
```

PowerShell:

```powershell
$ref = '/ruta/absoluta/de/la/copia-instalada/reference.md'
$registroAbs = '/ruta/absoluta/del/registro' # o 'issues'
$modoIntake = 'despachar' # o 'volcar'
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Python no disponible'); exit 3 }
$vueltaJson = py -3 -c 'import sys; from pathlib import Path; s=Path(sys.argv[1]).read_text(encoding=''utf-8''); a=''\n<!-- registro-candidato:inicio -->\n''; b=''\n<!-- registro-candidato:fin -->''; x=s.split(a,1)[1].split(b,1)[0].split(''```python\n'',1)[1].rsplit(''\n```'',1)[0]; ref,reg,modo=sys.argv[1:4]; sys.argv=[ref,''preparar-vuelta'',reg,modo]; exec(compile(x,ref,''exec''),{''__name__'':''__main__'',''FROZEN_UNIT'':(x+''\n'').encode(''utf-8'')})' $ref $registroAbs $modoIntake
$vueltaCodigo = $LASTEXITCODE
if ($vueltaCodigo -ne 0) { $vueltaJson; [Console]::Error.WriteLine('No se pudo preparar la vuelta; no efectuar nada'); if (-not $vueltaJson -or $vueltaCodigo -notin @(2, 3, 12)) { exit 3 }; exit $vueltaCodigo }
try { $scratchVuelta = ($vueltaJson | ConvertFrom-Json).scratch } catch { [Console]::Error.WriteLine('Respuesta de preparación inválida'); exit 3 }
$unidad = Join-Path $scratchVuelta 'unidad.py'
$scratchVuelta
```

En un shell nuevo **no** repetir `preparar-vuelta`: asignar la ruta literal devuelta a
`scratch_vuelta`/`$scratchVuelta`, `registro_abs`/`$registroAbs` y `ref`/`$ref`; derivar
`unidad`/`$unidad` de ese scratch. Validar antes de toda etapa:

```sh
scratch_vuelta='/ruta/literal/devuelta'; registro_abs='/ruta/absoluta/del/registro'; ref='/ruta/absoluta/de/la/copia-instalada/reference.md'
unidad="$scratch_vuelta/unidad.py"
if validacion_json=$(python3 "$unidad" validar-vuelta "$scratch_vuelta" "$registro_abs"); then validacion_codigo=0; else validacion_codigo=$?; fi
[ -z "$validacion_json" ] || printf '%s\n' "$validacion_json"
if [ "$validacion_codigo" -ne 0 ]; then
  case "$validacion_codigo" in 2|3|12) [ -n "$validacion_json" ] || exit 3 ;; *) exit 3 ;; esac
  exit "$validacion_codigo"
fi
registro_candidato() { python3 "$unidad" "$@"; }
registro_retiro() { python3 "$unidad" "$@"; }
```

```powershell
$scratchVuelta = '/ruta/literal/devuelta'; $registroAbs = '/ruta/absoluta/del/registro'; $ref = '/ruta/absoluta/de/la/copia-instalada/reference.md'
$unidad = Join-Path $scratchVuelta 'unidad.py'
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Python no disponible'); exit 3 }
$validacionJson = py -3 $unidad validar-vuelta $scratchVuelta $registroAbs
$validacionCodigo = $LASTEXITCODE
$validacionJson
if ($validacionCodigo -ne 0) { [Console]::Error.WriteLine('Vuelta congelada no validada'); if (-not $validacionJson -or $validacionCodigo -notin @(2, 3, 12)) { exit 3 }; exit $validacionCodigo }
function Invoke-RegistroCandidato {
  param([string[]]$Argumentos)
  if (-not (Get-Command py -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Python no disponible'); exit 3 }
  $candidatoJson = py -3 $unidad @Argumentos
  $candidatoCodigo = $LASTEXITCODE
  $candidatoJson
  if ($candidatoCodigo -ne 0) { if (-not $candidatoJson -or $candidatoCodigo -notin @(2, 3, 10, 11, 12)) { exit 3 }; exit $candidatoCodigo }
}
function Invoke-RegistroRetiro {
  param([string[]]$Argumentos)
  if (-not (Get-Command py -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Python no disponible'); exit 3 }
  $retiroJson = py -3 $unidad @Argumentos
  $retiroCodigo = $LASTEXITCODE
  $retiroJson
  if ($retiroCodigo -ne 0 -and (-not $retiroJson -or $retiroCodigo -notin @(2, 3, 10, 11, 12))) { exit 3 }
}
function Invoke-RegistroEvento {
  param([string]$Tipo, [string[]]$Ids, [object]$Datos)
  if (-not $Ids -or $Ids.Count -eq 0) { throw 'Evento sin IDs definitivos' }
  $idsJson = ConvertTo-Json -InputObject @($Ids) -Compress -Depth 8
  $datosJson = ConvertTo-Json -InputObject $Datos -Compress -Depth 8
  $ids64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($idsJson))
  $datos64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($datosJson))
  if (-not (Get-Command py -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Python no disponible'); exit 3 }
  $eventoJson = py -3 -c 'import base64,runpy,sys; unit=sys.argv[1]; sys.argv=[unit,''registrar-evento'',sys.argv[2],sys.argv[3],sys.argv[4],base64.b64decode(sys.argv[5]).decode(''utf-8''),base64.b64decode(sys.argv[6]).decode(''utf-8'')]; runpy.run_path(unit,run_name=''__main__'')' $unidad $scratchVuelta $registroAbs $Tipo $ids64 $datos64
  $eventoCodigo = $LASTEXITCODE
  $eventoJson
  if ($eventoCodigo -ne 0) { if (-not $eventoJson -or $eventoCodigo -notin @(2, 3, 12)) { exit 3 }; exit $eventoCodigo }
}
```

`registro_candidato` y `Invoke-RegistroCandidato` sirven solo a 6.2;
`registro_retiro` y `Invoke-RegistroRetiro` conservan el código y stdout semánticos de
`10/11/12`, sin terminar el shell con el `exit` del wrapper de siembra. Tras definirlos, cada etapa puede correr
en un shell distinto con la misma ruta literal. `validar-vuelta` comprueba manifiesto,
digest de unidad y eventos `evento-<secuencia>-<tipo>.json` por creación exclusiva,
contiguos y con esquema. Cada evento lleva `schema_version: 1`, `secuencia`, `tipo`,
`vuelta_id`, `instante_utc`, `ids` y `datos`. `ids-definitivos` se puede repetir solo
antes del efecto y deja obsoletas las raíces previas; un `efecto-acreditado` o
`rechazo-aprobado` es único y no coexisten. `reconciliacion-aprobada` enlaza identidad
externa y ruta/digest de cotejo; `ventana-plazo-aprobada` conserva plazo anterior,
nuevo y decisión solo tras `motivo: plazo-vencido`, no ante un ancla inconsistente.
**Validar un JSON no demuestra aprobación humana**: el conductor
acredita el gate y la evidencia externa antes de escribir el evento. Una reentrada
sin scratch o con cadena inválida se detiene, no repite el efecto.

`registrar-evento <scratch_abs> <registro_abs|issues> <tipo> <ids_json> <datos_json>`
publica el siguiente evento sin sobrescribir. `comparar-unidad <scratch_abs>
<registro_abs|issues> <ref_abs>` informa `instalada_coincide`: antes de un efecto,
`false` detiene y obliga a empezar otra vuelta; después del efecto solo se informa
y se continúa con la copia congelada. No sustituir `unidad.py` por la instalada.

En **cada** shell nuevo, ejecutar primero el bloque de reentrada de arriba con las tres
rutas literales. Para `ids-definitivos`, tomar como argumentos los IDs elegidos de esta
vuelta; para un efecto, rechazo o reconciliación, volver a dar **los mismos** IDs y los
datos acreditados de esa etapa. No inferir identidad, evidencia, decisión ni cotejo del
nombre del scratch. Los siguientes bloques contienen las cuatro variantes del evento;
seleccionar solo la que corresponde y detener ante un dato ausente:

En PowerShell, si la etapa corre como `.ps1`, incluir la reentrada al comienzo de **ese mismo
archivo**; ejecutarla solo en el shell que invoca `pwsh -File` no carga las funciones en el
proceso hijo.

En PowerShell, los bloques que leen `$args` se ejecutan como archivo `.ps1` con argumentos
(`pwsh -File <archivo> '<ID>'`) o dentro de una función invocada con esos IDs **en el shell
de esa etapa**. No anexar IDs al texto de `pwsh -Command` ni pegar el bloque al nivel
superior: allí `$args` no recibe los IDs de la vuelta. Esta forma de invocación rige también
los bloques de inspección, mapa y ventana que usan `$args` más adelante.

```sh
tipo_evento='ids-definitivos' # o efecto-acreditado, rechazo-aprobado, reconciliacion-aprobada
[ "$#" -gt 0 ] || { printf '%s\n' 'Faltan IDs definitivos de esta etapa' >&2; exit 2; }
ids_json=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:],ensure_ascii=True))' "$@") || exit 3
case "$tipo_evento" in
  ids-definitivos) datos_json='{}' ;;
  efecto-acreditado)
    [ -n "${identidad:-}" ] && [ -n "${evidencia:-}" ] || exit 2
    datos_json=$(python3 -c 'import json,sys; print(json.dumps(dict(identidad=sys.argv[1],evidencia=sys.argv[2]),ensure_ascii=True))' "$identidad" "$evidencia") || exit 3 ;;
  rechazo-aprobado)
    [ -n "${decision:-}" ] && [ -n "${evidencia:-}" ] || exit 2
    datos_json=$(python3 -c 'import json,sys; print(json.dumps(dict(decision=sys.argv[1],evidencia=sys.argv[2]),ensure_ascii=True))' "$decision" "$evidencia") || exit 3 ;;
  reconciliacion-aprobada)
    [ -n "${identidad:-}" ] && [ -n "${cotejo_ruta:-}" ] && [ -n "${cotejo_sha256:-}" ] && [ -n "${decision:-}" ] || exit 2
    datos_json=$(python3 -c 'import json,sys; print(json.dumps(dict(identidad=sys.argv[1],cotejo_ruta=sys.argv[2],cotejo_sha256=sys.argv[3],decision=sys.argv[4]),ensure_ascii=True))' "$identidad" "$cotejo_ruta" "$cotejo_sha256" "$decision") || exit 3 ;;
  *) printf '%s\n' 'Tipo de evento no reconocido' >&2; exit 2 ;;
esac
if evento_json=$(python3 "$unidad" registrar-evento "$scratch_vuelta" "$registro_abs" "$tipo_evento" "$ids_json" "$datos_json"); then evento_codigo=0; else evento_codigo=$?; fi
printf '%s\n' "$evento_json"; [ "$evento_codigo" -eq 0 ] || exit "$evento_codigo"
```

```powershell
if (-not (Get-Command Invoke-RegistroEvento -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de evento no cargada'); exit 3 }
$tipoEvento = 'ids-definitivos' # o efecto-acreditado, rechazo-aprobado, reconciliacion-aprobada
$idsDefinitivos = @($args) # un ID completo por argumento de esta etapa
if ($idsDefinitivos.Count -eq 0 -or @($idsDefinitivos | Where-Object { -not $_ }).Count -ne 0) { throw 'Faltan IDs definitivos de esta etapa' }
switch ($tipoEvento) {
  'ids-definitivos' { $datosEvento = @{} }
  'efecto-acreditado' {
    if (-not $identidad -or -not $evidencia) { throw 'Falta identidad o evidencia del efecto' }
    $datosEvento = @{ identidad = $identidad; evidencia = $evidencia }
  }
  'rechazo-aprobado' {
    if (-not $decision -or -not $evidencia) { throw 'Falta decisión o evidencia del rechazo' }
    $datosEvento = @{ decision = $decision; evidencia = $evidencia }
  }
  'reconciliacion-aprobada' {
    if (-not $identidad -or -not $cotejoRuta -or -not $cotejoSha256 -or -not $decision) { throw 'Faltan datos de la reconciliación' }
    $datosEvento = @{ identidad = $identidad; cotejo_ruta = $cotejoRuta; cotejo_sha256 = $cotejoSha256; decision = $decision }
  }
  default { throw 'Tipo de evento no reconocido' }
}
Invoke-RegistroEvento -Tipo $tipoEvento -Ids $idsDefinitivos -Datos $datosEvento
```

`$args` y `"$@"` se suministran de nuevo en **esa** etapa, no se heredan del shell de
preparación. `Invoke-RegistroEvento` codifica los dos JSON en base64 antes de llamar a
`py -3`, porque el paso de argumentos `Legacy` de PowerShell elimina comillas dobles
embebidas. Para comprobar la unidad instalada, sin sustituir la congelada:

```sh
if comparacion_json=$(python3 "$unidad" comparar-unidad "$scratch_vuelta" "$registro_abs" "$ref"); then comparacion_codigo=0; else comparacion_codigo=$?; fi
[ -z "$comparacion_json" ] || printf '%s\n' "$comparacion_json"
if [ "$comparacion_codigo" -ne 0 ]; then
  case "$comparacion_codigo" in 2|3|12) [ -n "$comparacion_json" ] || exit 3 ;; *) exit 3 ;; esac
  exit "$comparacion_codigo"
fi
```

```powershell
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Python no disponible'); exit 3 }
$comparacionJson = py -3 $unidad comparar-unidad $scratchVuelta $registroAbs $ref
$comparacionCodigo = $LASTEXITCODE
$comparacionJson
if ($comparacionCodigo -ne 0) { if (-not $comparacionJson -or $comparacionCodigo -notin @(2, 3, 12)) { exit 3 }; exit $comparacionCodigo }
```

**Frontera de estos modos:** todos emiten JSON ASCII; la ruta de preparación y los
eventos se publican por creación exclusiva. El código `3` es fallo de ejecución y
no un veredicto semántico. La clase y la dirección siguientes se refieren al
predicado de cada modo, no al flujo de datos:

| Modo | Qué acredita `0` o qué evidencia entrega | No detecta | Clase de salida | Dirección de error |
|---|---|---|---|---|
| `preparar-vuelta` | unidad congelada y scratch creado; ruta literal impresa | existencia y procedencia del registro o efecto externo | `veredicto` | `admite-de-mas`: una ruta absoluta aún puede nombrar un registro inexistente |
| `validar-vuelta` | manifiesto, digest y secuencia de eventos íntegros | si una persona aprobó los datos declarados | `veredicto` | `admite-de-mas`: un evento formalmente válido puede declarar una aprobación no real |
| `registrar-evento` | forma, orden y publicación exclusiva del evento | realidad del efecto o decisión humana | `veredicto` | `admite-de-mas`: acepta una declaración bien formada aunque sea falsa |
| `comparar-unidad` | booleano de igualdad de digests para que el conductor decida antes del efecto | equivalencia de contexto o permiso de seguir | `evidencia` | `admite-de-mas`: igualdad de digest leída como equivalencia conductual excede lo comparado |
| `preparar-cotejo` | JSON ASCII exclusivo y digests del externo regular, con IDs definitivos y título tipado | asociación del externo con el efecto ni permiso humano | `evidencia` | `admite-de-mas`: puede preparar bytes de un archivo ajeno aunque esté bien formado |

En `comparar-unidad`, código `0` solo acredita que la consulta se ejecutó: el conductor
lee el booleano y adjudica si puede continuar. Un `12` de validación o evento es un
rechazo semántico, distinto del fallo de ejecución `3`.

---

## Verificar sin investigar

El paso 2 tiene que llegar a un veredicto **sin hacer el trabajo del flujo**. La diferencia no es de
grado, es de pregunta:

| El intake pregunta | El flujo pregunta |
|---|---|
| ¿La afirmación describe el árbol de hoy? | ¿Por qué el árbol es así? |
| ¿La sección que cita existe y dice eso? | ¿Qué debería decir? |
| ¿La regla que dice faltar, falta? | ¿Dónde conviene ponerla? |

### Qué se comprueba

Solo lo **comprobable por lectura**: valores por default, existencia de secciones y reglas, presencia
o ausencia de una instrucción, coherencia entre lo que una skill produce y lo que otra exige. Todo eso
sale de leer y de `grep`.

Lo que **no** se comprueba acá: si el arreglo propuesto es el correcto, si hay una solución mejor, si
el defecto tiene otras manifestaciones. Son preguntas de diseño y las contesta el flujo.

### Tres comprobaciones que casi siempre pagan

**La fecha contra el árbol.** Si el mecanismo que el incidente describe cambió después de que se
registró, el diagnóstico puede haber envejecido:

```
git -C <repo_destino> log -1 --format='%h %ad %s' --date=short -S '<frase de la sección citada>' -- <archivo>
```

Si el commit es **posterior** al incidente, leer qué cambió antes de aceptar la descripción. Si es
**anterior**, el incidente se escribió sobre el árbol actual y no hay nada que actualizar.

**La regla que dice faltar.** Cuando el incidente afirma que algo no está —"la skill no dice X"— el
`grep` que lo confirma es el que más rinde, porque una ausencia es lo más fácil de afirmar mal:

```
grep -rniE '<dos o tres formas de decir X>' <archivos de la skill>
```

Salida vacía **con patrones que de verdad cubran las formas de decirlo** confirma la ausencia. Un solo
patrón demasiado literal da vacío siempre y no prueba nada.

**La implementación que dice faltar.** Es la anterior en su forma más cara, y lleva método propio
porque el `grep` que la resuelve **no es el mismo**. Cuando el incidente afirma que un procedimiento
determinista no está implementado, buscar por **tipo de archivo** no alcanza: acá una implementación
puede vivir embebida como bloque ejecutable dentro del `.md` normativo. Se traza **productor → bloque
→ consumo**, en ese orden:

```
grep -rn '@bloque:' <archivos de la skill>
git -C <repo_destino> log --oneline -S '<ancla del bloque>' -- <archivo>
```

El primero encuentra la implementación donde de verdad vive; el segundo dice **desde cuándo**, que es
lo que decide si el incidente nació viejo. Si el bloque existe y es anterior al incidente, la
afirmación es falsa aunque el incidente esté impecablemente escrito.

El caso que obliga a escribir esto: dos incidentes afirmaron que una cadena de integridad estaba
especificada solo en prosa, sin implementación en ningún lado, y que por lo tanto el gate que promete
rechazar contratos rotos no rechazaba ninguno. Era falso. La cadena existía como bloque POSIX con su
gemelo PowerShell y un corpus de calibración de cinco casos, desde **un mes antes**. El incidente
había buscado `sha256` entre los `scripts/*.py` y concluido de la ausencia. **Un intake que corre ese
mismo `grep` llega a la misma conclusión falsa**, lo marca confirmado y despacha un flujo a escribir
lo que ya está — y los dos eran la prueba estrella del informe que los citó.

### Cuándo parar y admitir

Si después de leer las secciones citadas y correr esos `grep` el veredicto sigue sin estar claro, **es
confirmado y se despacha**. Se anota en el dossier qué quedó sin comprobar y por qué — el flujo tiene
el aparato para resolverlo, el intake no.

Lo que **no** es una razón para rechazar: que el incidente esté mal escrito, que le falte un campo, que
mezcle dos cosas o que su propuesta no convenza. Nada de eso dice que el defecto no exista.

---

## El lote, vuelta por vuelta

Con `cantidad > 1` el ciclo entero se repite, y lo que cambia entre vueltas es el registro.

### El estado que se arrastra

Entre vueltas solo se lleva esto:

- **Cupos restantes** y **flujos abiertos** (para el reporte final).
- **Rechazados con su evidencia** — no viven en ningún dossier, así que si se pierden acá se pierden.
- **Descartados por agrupamiento**: un incidente que se evaluó como relacionado y no entró **sigue
  siendo candidato** para su propio flujo en la vuelta siguiente. No queda quemado.

### Lo que se relee cada vuelta

El **índice**, porque la vuelta anterior lo cambió. La cabecera de reglas no: no cambia.

Releer el índice no es formalidad — es lo que impide elegir un incidente que la vuelta anterior ya se
llevó como relacionado. Elegir desde una lista en memoria es la forma exacta de despachar dos veces el
mismo incidente y descubrirlo cuando dos worktrees tocan las mismas líneas.

### Cuándo el lote termina antes

- **El registro se agotó.** Se abren los que haya y se dice.
- **Un gate quedó sin respuesta.** No se sigue con el resto: el usuario está mirando una decisión, y
  abrir worktrees mientras tanto le cambia el terreno abajo de los pies.
- **Un despacho no arrancó.** Se corrige ese antes de seguir; nunca se retira su incidente ni se pasa
  al siguiente dejando el worktree inerte.
- **La barrera de retiro no se acreditó.** Antes del efecto no se despacha ni publica; después,
  se detiene el lote con doble sede, scratch, imagen de respaldo y efecto externo enumerados.
  Un `10` exige resimular dentro del plazo; `11/12` o tiempo agotado requieren la salida del
  contrato de fallo, nunca elegir el siguiente ID ni repetir el efecto.

### Nombres de worktree

Cada flujo necesita el suyo y son de la misma tanda, así que los nombres genéricos colisionan. Derivar
el nombre de **qué corrige**, no de la posición en el lote: `incidente-2` no le dice nada a nadie
dentro de una semana.

---

## Mirar aguas arriba

El paso 4 contesta dos preguntas que el árbol local no puede contestar: **¿esto ya se arregló en el
remoto?** y **¿alguien lo está arreglando ahora?**. La entrada es la **superficie editable** que salió
del paso 3 — los archivos que el diff iba a tocar.

Los comandos de acá **no usan pipes ni redirecciones**, así que corren igual en POSIX y en PowerShell
sin una segunda variante. Mantenerlos así al editarlos.

### 1. Sincronizar las refs

```
git -C <repo_destino> fetch --quiet origin
```

Sin esto, `origin/<default>` es la foto de la última sincronización y **todo lo que sigue devuelve
vacío por mirar un remoto viejo** — un verde que se lee igual que un verde real. Actualiza refs
remotas: no toca el árbol, no mueve ramas locales, no necesita árbol limpio.

Resolver el nombre de la rama por default en vez de asumir `main`:

```
git -C <repo_destino> rev-parse --abbrev-ref origin/HEAD
```

Devuelve **`origin/<default>`, con el prefijo puesto** — `origin/main`, no `main`. La rama local es
esa cadena sin el `origin/`, y confundirlas produce un `origin/origin/main` que corta con "unknown
revision" en el mejor caso.

### 2. Commits que están arriba y no acá

```
git -C <repo_destino> log --oneline main..origin/main -- <archivo> <archivo>
```

`main..origin/main` es exactamente "lo que tiene el remoto y no tiene el local". Sin el `--` y la
lista de archivos trae todo el retraso, que no dice nada; con ellos, trae solo lo que toca la
superficie del incidente.

**El complemento que caza lo que el cruce por ruta no ve** — un arreglo que resolvió lo mismo en otro
archivo:

```
git -C <repo_destino> log --oneline -S "<frase literal que el incidente cita>" main..origin/main
```

Es complemento, no reemplazo: `-S` cuenta apariciones de una cadena, así que solo encuentra el commit
si el arreglo movió esa frase exacta.

### 3. Releer contra `origin`, no contra el árbol

Si algo apareció, la tabla del paso 2 se midió sobre archivos viejos. Rehacer **las filas que ese
commit toca**, leyendo la versión del remoto:

```
git -C <repo_destino> show origin/main:<archivo>
git -C <repo_destino> diff main origin/main -- <archivo>
```

El `show` sirve para volver a correr el `grep` del paso 2 sobre el contenido de arriba; el `diff` para
ver qué cambió y decidir si el defecto sobrevivió. **El veredicto se re-emite sobre `origin/<default>`
porque ahí nace el worktree**, no sobre el árbol local.

### 4. PRs abiertos

Con GitHub, si `gh` está y está autenticado:

```
gh pr list --state open --json number,title,headRefName,url
gh pr diff <número> --name-only
```

El primero da los candidatos; **el segundo es el que decide**, cruzando sus archivos contra la
superficie. Filtrar por título es lo que produce los dos errores simétricos: un PR con título ajeno
que toca la sección exacta, y uno con título parecido que no toca nada.

Con Bitbucket, el mismo cruce con las herramientas de listado de PR y de diff del MCP `bb_*` — las
que usa `bitbucket-code-review`. La forma de la comprobación no cambia: **archivos del PR ∩
superficie del incidente**.

**Degradación.** Sin `gh` (o sin auth), sin MCP, o sin remoto configurado: se reporta
`PRs: no comprobado — <razón>` y se sigue. Lo que no se puede hacer es omitirlo del reporte: un
chequeo que no corrió y uno que salió limpio se leen igual si nadie los distingue.

### Qué queda escrito

Sea cual sea el resultado, el dossier lleva la sección "Estado aguas arriba" (ver "El dossier" →
sección 6). Un flujo que no sabe que hay un PR abierto sobre sus archivos lo descubre en el conflicto.

---

## Resolver la plataforma

**Antes de crear nada.** La plataforma no se fija: se resuelve consultando las **dos identidades
vivas**, y el resultado gobierna cada rama de este paso. El criterio vive acá, escrito y
autocontenido: esta skill se instala como copia y corre sobre repositorios ajenos, así que no puede
depender de la ruta de ningún script de otro repositorio. La **sede** de estos estados y de esta
matriz es `skills/sdd-flow/reference.md` → «Resolver la plataforma de terminales», y esta copia
**deriva de ella**: la dirección es esa y no la inversa. Sigue sin haber dependencia de ejecución
sobre ningún script, que es lo que permite aplicarla sobre un repositorio ajeno.

### Los cuatro estados por identidad

Cada plataforma se consulta por su identidad de panel. Los estados son cuatro y no dos, porque
«presente» no es «utilizable»:

| Estado | Qué se observó |
|---|---|
| `resuelve` | la identidad existe **y** la plataforma la reconoce como panel vivo |
| `rancia` | la identidad existe y la plataforma **no** la reconoce |
| `ausente` | no hay identidad declarada |
| `inconsultable` | hay identidad y la consulta a la plataforma falló |

### La matriz, y su destino

**Las variables son las que el runtime exporta de verdad, y la salida se parsea, no se grepea.**
`HERDR_PANE_ID` contra `herdr pane list`, y `ORCA_TERMINAL_HANDLE` contra `orca terminal list
--json`: la pertenencia de la identidad al conjunto vivo **es** el predicado. Inventar un nombre de
variable o un subcomando de consulta individual tiene un modo de falla mudo — la condición queda
falsa en una sesión sana y el destino cae a `headless`, que es indistinguible de no tener plataforma.

> **Por qué el parseo y no un `grep`, con el caso que lo obligó.** Un `grep` del literal acredita
> `resuelve` sobre una salida **truncada o malformada** que apenas contenga `"handle":"term-1"`, y ahí
> la comprobación deja de fallar cerrada: medido con una salida `not-json {"handle":"term-1"` que sale
> con código 0. Y ante bytes ilegibles devuelve `rancia`, que es la lectura que el adaptador dejó de
> hacer a propósito. Las dos son propiedades **estructurales** de la salida, y ningún patrón de texto
> las distingue: por eso este es el único lugar del procedimiento donde se sube de `grep` a un
> intérprete.
>
> **Y la consulta corre adentro de ese intérprete, no antes.** Una sustitución de comandos del shell
> **no conserva los bytes NUL**: medido, un CLI que emite `"handle":"term\0-1"` le entrega al parser
> `"term-1"`, que coincide con la variable y acredita `resuelve` sobre una salida corrupta. Parsear
> estricto no alcanza si los bytes ya se sanearon en el camino, así que el proceso hijo se lanza desde
> adentro y de ahí salen tanto su salida cruda como su código.

```sh
# uso: estado_identidad <herdr|orca>  → imprime resuelve|rancia|ausente|inconsultable
# la consulta corre DENTRO del intérprete: una sustitución de comandos del shell no conserva
# los bytes NUL, así que una salida corrupta llegaría saneada y se acreditaría como viva
estado_identidad() {
  estado=$(python3 -c 'import json, os, subprocess, sys
CUAL = {"herdr": ("HERDR_PANE_ID", ["herdr","pane","list"], "panes", "pane_id"),
        "orca":  ("ORCA_TERMINAL_HANDLE", ["orca","terminal","list","--json"], "terminals", "handle")}
if sys.argv[1] not in CUAL: print("inconsultable"); raise SystemExit
var, cmd, caja, clave = CUAL[sys.argv[1]]
valor = os.environ.get(var)
if not valor: print("ausente"); raise SystemExit
try: hecho = subprocess.run(cmd, capture_output=True, timeout=15)
except (OSError, subprocess.SubprocessError): print("inconsultable"); raise SystemExit
if hecho.returncode != 0: print("inconsultable"); raise SystemExit
try: texto = hecho.stdout.decode("utf-8")
except UnicodeDecodeError: print("inconsultable"); raise SystemExit
try: raiz = json.loads(texto)
except ValueError: raiz = {}
if not isinstance(raiz, dict): raiz = {}
hijos = raiz.get("result", raiz)
hijos = hijos.get(caja, []) if isinstance(hijos, dict) else []
print("resuelve" if valor in {h.get(clave) for h in hijos if isinstance(h, dict)} else "rancia")
' "$1" 2>/dev/null)
  [ -n "$estado" ] || estado=inconsultable   # sin intérprete no se acredita nada
  echo "$estado"
}
# uso: resolver_plataforma [plataforma-pedida]
#   sigue: imprime "<plataforma> <identidad>" y devuelve 0
#   para:  imprime "headless <causa>"        y devuelve 1
resolver_plataforma() {
  pedida="${1:-}"
  eh=$(estado_identidad herdr); eo=$(estado_identidad orca)
  if [ -n "$pedida" ]; then
    case "$pedida" in
      herdr) [ "$eh" = resuelve ] && { echo "herdr $HERDR_PANE_ID"; return 0; }
             echo "headless override-herdr-$eh"; return 1 ;;
      orca)  [ "$eo" = resuelve ] && { echo "orca $ORCA_TERMINAL_HANDLE"; return 0; }
             echo "headless override-orca-$eo"; return 1 ;;
      *)     echo "headless override-no-reconocido"; return 1 ;;
    esac
  fi
  case "$eh:$eo" in
    resuelve:resuelve) echo "headless ambas-resuelven"; return 1 ;;
    resuelve:*)        echo "herdr $HERDR_PANE_ID";     return 0 ;;
    *:resuelve)        echo "orca $ORCA_TERMINAL_HANDLE"; return 0 ;;
    *)                 echo "headless $eh:$eo";         return 1 ;;
  esac
}
```

**Emite dos campos, la plataforma y la identidad, y el segundo no es decorativo:** es lo que
revalida cada efecto. Un destino a secas obligaría a re-resolver, que es volver a **elegir**
plataforma en vez de **comprobar** la que ya se eligió.

> **De dónde salió esta matriz, y las dos divergencias que conserva.** Estados, variables y destinos
> se derivaron del adaptador que este ecosistema retiró, y esa derivación ya ocurrió: **la sede es
> ahora esta**, no aquel archivo, y la dirección no vuelve a invertirse. Se dejan escritas las dos
> divergencias porque son decisiones y no accidentes, no porque haya nada contra lo que cotejar.
> Cotejados en su momento caso por caso con la misma entrada —salida válida, identidad
> ausente de la lista, JSON truncado, bytes ilegibles, salida vacía y consulta fallida—, los dos
> coincidían. Difieren en dos puntos, los dos declarados:
>
> - el adaptador reserva un código propio para las **dos** identidades inconsultables; acá ese caso
>   cae en `headless`, que es el mismo destino que su propia tabla le asigna.
> - ante un JSON **válido** cuya raíz no es un objeto, el adaptador **termina con una excepción** en
>   vez de emitir su sobre; este bloque comprueba el tipo antes de indexar y resuelve `rancia`. La
>   divergencia es deliberada y va hacia el lado seguro: **no se replica un fallo**.
>
> Si falta el intérprete, el estado es `inconsultable` y no `rancia`: sin con qué comprobar no se
> acredita una identidad.

**`headless` no es un modo degradado de este paso: es su parada.** El paso 6 necesita un agente
interactivo al que despachar, y sin plataforma utilizable no hay dónde crearlo. Ante `headless` —por
cualquiera de sus causas, incluida la de **las dos identidades vivas**, donde no hay observación que
diga cuál es el anfitrión— el despacho **se detiene**, el registro queda intacto y ningún incidente
se retira. Es el estado del que se reintenta.

### El override del usuario dirige, no suple

**El override es el parámetro `plataforma`**, con valores `herdr` y `orca`, y es la única puerta por
la que una petición del usuario entra a este paso. Se captura del pedido —“despacha esto en Herdr”,
“que corra en Orca”— y **no tiene default**: sin él se llama a `resolver_plataforma` sin argumento y
decide la matriz. Un valor que no sea uno de esos dos no se interpreta ni se corrige: cae en
`override-no-reconocido`, que es parada.

Si el usuario pide una plataforma, esa petición **elige cuál se intenta**, no acredita que sirva:
viaja como **argumento** de `resolver_plataforma` —no como una decisión tomada antes de llamarlo— y
la identidad de la elegida se comprueba igual:

| Caso | Resultado |
|---|---|
| override, con su identidad `resuelve` | se usa la pedida |
| override, con su identidad `rancia`, `ausente` o `inconsultable` | **se detiene**; la petición no sustituye la comprobación |
| sin override, una sola identidad `resuelve` | se usa esa |
| sin override, las dos `resuelven` | **se detiene**: no hay observable que identifique al anfitrión |
| las dos `resuelven` **con** override comprobado | el override **desempata** — es el único caso en que lo hace |

### La identidad se revalida antes de cada efecto

Una identidad viva al resolver puede dejar de serlo a mitad del paso, y cada efecto que dependa de
ella la vuelve a comprobar **inmediatamente antes**, con `estado_identidad "<plataforma>"` sobre la
plataforma ya resuelta — **nunca** con `resolver_plataforma`, que volvería a elegir en vez de
comprobar, y que ante una identidad caída podría devolver la **otra** plataforma a mitad del paso.
Los efectos son estos seis y la lista es
exhaustiva: **crear** el worktree por la plataforma, **adoptar** un árbol creado con Git, **abrir** el
panel, **arrancar** el agente, **rotular** el worktree y **entregar** el encargo. Si la
revalidación falla, ese efecto no se ejecuta y se aplica la fila que le corresponda en «El contrato
de fallo por fase».

---

## Clasificar el hook de setup — antes de elegir cómo crear

**El orden importa y es el opuesto al que parece.** La clasificación del hook **decide con qué
primitiva se crea el worktree**, así que ocurre antes de crear, no después. El `repo_destino` es un
parámetro de cada corrida: el mismo procedimiento puede encontrar un hook vacío en uno, reproducible
en otro e inseparable de su plataforma en un tercero.

### De dónde se lee, por plataforma

| Plataforma | Autoridad del hook |
|---|---|
| Orca | `orca repo list --json` → la entrada cuyo `path` es el `repo_destino` → su `hookSettings.scripts.setup`. La variante por repositorio es `orca repo show --repo id:<repoId> --json`, y **el selector es obligatorio**: sin él la orden falla con `invalid_argument` antes de clasificar nada. Se prefiere `list` porque no exige haber resuelto el id todavía |
| Herdr | no expone hooks por repositorio: el estado es `ausente` salvo que el `repo_destino` declare uno propio en su árbol |

### El predicado, con sus tres estados

| Estado | Cómo se reconoce | Qué cambia en la creación, en Herdr | Qué cambia en la creación, en Orca |
|---|---|---|---|
| `ausente` | la autoridad no declara script de setup | **Git**: `git worktree add` con el commit explícito, y adopción con `worktree open` | `--setup skip` |
| `reproducible` | declara un script **y** ese script se puede ejecutar fuera de la creación: es un ejecutable del árbol o un comando del `PATH`, sin argumentos que la plataforma inyecte | **Git**, y el hook se ejecuta después, con las condiciones de abajo | `--setup skip`, y el hook se ejecuta después, con las mismas condiciones |
| `inseparable` | declara un script que la plataforma invoca con contexto propio —argumentos, entorno o rutas que solo ella arma— | no se da: Herdr no declara hooks por repositorio | `--setup run`, que deja el hook en manos de la plataforma |

> **La ramificación es por estado y por plataforma, y la columna lo dice.** Dónde hay dos primitivas
> —Herdr— el estado elige entre ellas; donde la plataforma ofrece una sola —Orca— elige su política
> de setup. Las dos son ramas con postcondición propia, que es lo que el paso exige: lo que **no**
> se puede prometer es que la primitiva cambie en una plataforma que tiene una.

> **`inseparable` no es un fracaso, es una rama.** Conservar la creación específica donde el hook lo
> exige es la salida correcta: lo que el defecto pedía es que la plataforma se **resuelva**, no que
> una primitiva concreta desaparezca.

### Ejecutar el hook tras una creación con Git

Con `reproducible`, después de crear y antes de sembrar: se ejecuta **con el worktree nuevo como
directorio de trabajo**, con el entorno de la sesión y sin argumentos añadidos. Su **condición de
éxito** es salida cero; su **postcondición** es que el árbol siga limpio salvo por lo que el propio
hook declare.

**Los cuatro fallos de esta fase detienen el despacho**, cada uno con su estado escrito: la consulta
de la autoridad falla; el script está declarado pero no es legible; su ejecución sale distinto de
cero; o su postcondición no se cumple. Ninguno se degrada a «seguir sin hook».

---

## Crear el worktree

**La primitiva la eligió la clasificación anterior.** Lo común a las dos ramas va acá; los comandos
van en su fila.

### 1. Resolver el repo destino

Con la plataforma ya resuelta, obtener la identidad del `repo_destino` en ella. En Orca,
`orca repo list --json`; en Herdr, el repositorio se nombra por su ruta. Del mismo lugar sale la
autoridad del hook que la clasificación consultó.

### 2. Crear

| Plataforma | Rama `ausente` o `reproducible` | Rama `inseparable` |
|---|---|---|
| Herdr | `git -C <repo_destino> worktree add -b <rama> <ruta> <sha>`, y adoptar con `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` | no aplica: Herdr no declara hooks por repositorio |
| Orca | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup skip --agent <agente> --no-parent --json` | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup run --agent <agente> --no-parent --json` |

> **`--agent` va en las dos ramas, y no es redundante.** Una creación sin él abre un shell de
> fallback, y `orca terminal list` **observa** la terminal pero no arranca ninguna: sin la flag, las
> dos ramas llegan al despacho con una terminal viva y **sin agente de la familia esperada**, que es
> el estado que el control de familia iba a cazar recién al final.

> **En Orca la primitiva es una sola, y no porque se haya elegido así.** Su CLI **no tiene verbo de
> adopción**: `orca worktree create` no acepta una ruta destino —crea un checkout nuevo— y el grupo
> `orca worktree` no expone ningún otro que registre un árbol ya existente. Así que un worktree
> creado con Git en Orca **no se puede continuar**: no hay con qué registrarlo, y sin registro no hay
> panel, ni agente, ni rótulo. La rama de Git queda para Herdr, que sí adopta con `worktree open`.
>
> **Tampoco lo adopta por descubrimiento, y eso se midió en vez de suponerse.** Un worktree creado
> con `git worktree add` y consultado enseguida devuelve `selector_not_found`, en dos rutas
> distintas —una fuera del árbol habitual y otra hermana de un worktree que Orca **sí** resuelve—.
> Que resuelva ese otro prueba que alguien lo registró antes, no que los descubra. Es el control que
> cierra la búsqueda de una segunda primitiva: no la hay.
>
> **Lo que la clasificación decide en Orca es la política de setup** — `--setup skip` con hook
> `ausente` o `reproducible` (y entonces, si es `reproducible`, se ejecuta aparte con las condiciones
> de su sección), `--setup run` con `inseparable`. La consulta por corrida, la ramificación por estado
> y las postcondiciones por rama siguen enteras; lo único que no varía es la primitiva, porque la
> plataforma ofrece una sola. Prometer que variara exigiría un verbo que su CLI hoy no tiene.

**Crear con Git retira el peligro de base, no lo traslada.** El bloque que verificaba la base existía
porque el verbo de creación de una plataforma usa su referencia remota por defecto y el worktree podía
nacer atrasado sin que nada lo dijera. Pasando el **commit explícito** —el que el paso 4 ya
resolvió— ese peligro deja de existir: no hay que comparar ni realinear nada.

> **Donde crea la plataforma, el peligro sigue vivo: en Orca, en sus dos ramas.** `--base-branch`
> recibe el ref que el paso 4 resolvió, pero que la flag lo acepte **no se midió** como equivalente a
> pasarle un commit a Git, así que ahí se compara igual el `head` devuelto contra ese commit y se
> realinea **solo** si el que está adelante es el local. Ante divergencia real se para y se le muestra
> al usuario. En Herdr, donde crea Git con el commit explícito, no hay nada que comparar.

---

## Adoptar, abrir y rotular

Un árbol creado con Git **no lo conoce la plataforma**: sin adopción no se puede abrir el panel,
arrancar el agente ni rotular. Cada fila lleva su comando y el observable que lo acredita.

La adopción **ancla el repositorio de origen con `--cwd <checkout principal del repo_destino>`**, y
ese anclaje es el arreglo entero. Sin él, `worktree open` parte del **workspace enfocado**, que en un
lote ya es el worktree del flujo anterior. Tampoco sirve la variable de entorno del panel llamador:
identifica el workspace donde corre el intake, no el repositorio sobre el que se adopta.

**Medido, con un worktree linked enfocado:** la misma adopción **sin** `--cwd` devuelve
`{"error":{"code":"linked_worktree_source"}}` —el fallo que esta receta corrige— y con `--cwd` al
checkout principal adopta y devuelve su panel raíz. El contraejemplo no se escribe entero a
propósito: una invocación sin anclar, copiable, es la forma exacta del defecto.

> **`--cwd` nombra el checkout principal, y si no lo es falla cerrada.** Medido: apuntándolo a un
> worktree **linked** del mismo repositorio, `worktree open` devuelve `linked_worktree_source` igual
> que sin anclaje — no camina hasta el padre, a diferencia de `worktree list --cwd`, que sí lo hace.
> Los dos verbos resuelven la misma bandera distinto, así que el valor no se deriva de una consulta
> previa: se pasa el checkout principal. Si el `<repo_destino>` de la corrida fuera un worktree
> linked, la adopción **no adopta nada** y lo dice — la orden sale con código distinto de cero y el
> sobre de error viaja por **stderr**. Se lee el `error.code`, nunca el mensaje.

Las demás invocaciones —`agent start`, `pane split` y `workspace rename`— ya nombran su destino con
`--pane` o un id explícito, así que no hay nada más que anclar.

> **Panel libre o panel ocupado se lee sin escribir en él.** `herdr pane process-info --pane <id>`
> devuelve `foreground_processes[]`, y el discriminante es **cuál** es el proceso, no cuántos hay:
> el panel está libre cuando su único proceso en foreground es **su shell de login** —medido `zsh`,
> y `bash` donde ese sea el shell—. **La cantidad no sirve**, y conviene decirlo porque es la
> lectura que se cae sola: medido, un panel libre trae **uno** (`zsh`) y uno ocupado con un agente
> Codex trae **uno** también (`codex`). Un panel de Claude Code trae diez, pero eso es su pila de
> MCP en el mismo grupo de procesos, no una propiedad de estar ocupado — leerlo como umbral deja
> pasar por libre justamente al panel con otro agente, que es el caso que esta rama existe para
> cazar. Se prefiere a dejar que `agent start` agote su `--timeout`, que es el escalón caro **y con
> efecto colateral**: antes de rendirse escribe en el panel, así que si ahí corre un editor o una
> suite de tests el texto entra en ese proceso. Caveat medido: recién adoptado, el panel puede estar
> corriendo todavía su propio `rc` —apareció un `brew shellenv`—, que por identidad lee **ocupado** y
> es transitorio, así que se relee antes de darlo por tal.

> **`--no-focus` se conserva explícito, y no porque haya un robo de foco que impedir.** Medido:
> `worktree open` sin ninguna de las dos banderas devuelve el workspace con `focused: false` y deja
> el foco donde estaba. El esquema de la API declara `focus` con `default: false` y el `--help` del
> CLI no declara ninguno, así que el flag fija un default que la superficie del CLI no confiesa.

| Plataforma | Adoptar | Abrir y arrancar | Rotular | Observable que acredita |
|---|---|---|---|---|
| Herdr | `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` sobre el árbol ya existente — `open` adopta y devuelve el panel raíz en `.result.root_pane.pane_id`, mientras `create` crearía uno nuevo | Ramificar por `.result.root_pane` de esa misma respuesta —`already_open` es un booleano y no discrimina nada—: con `.agent` nulo y `.cwd` igual a `<ruta>`, arrancar ahí con `herdr agent start <nombre> --kind <familia> --pane <.pane_id>`; con `.agent` igual a la familia esperada y ese mismo `.cwd`, reutilizarlo; en todo otro caso —otra familia, `.cwd` distinto, o el panel ocupado —su único proceso en foreground no es su shell de login— según `herdr pane process-info --pane <.pane_id>`— abrir uno propio con `herdr pane split --pane <.pane_id> --direction right --cwd <ruta> --no-focus` y arrancar ahí | lo deja puesto `--label` en la misma adopción, **también cuando `already_open` viene verdadero** —medido: una re-apertura con `--label` distinto reescribe la etiqueta del workspace y `workspace list` la devuelve cambiada—; para cambiarlo después, `herdr workspace rename <.result.workspace.workspace_id> "<qué flujo corre acá>"` | `herdr agent get <nombre>` devuelve el mismo `pane_id`, la familia esperada, su `cwd` igual a la ruta del worktree, y un `agent_status` que la plataforma declara listo —`idle` o `done`—; ante cualquier otro resultado, incluido `blocked`, y ante discrepancias con el resultado de `agent start`, seguir «Esperar a que el agente esté listo» |
| Orca | nada que adoptar: el árbol lo creó su propio verbo y ya está registrado. Un árbol creado con Git **no** se puede adoptar acá, y por eso Orca no tiene rama de Git | lo arranca `--agent <familia>` **en la creación**, que es el único modo: `orca terminal list --worktree id:<repoId>::<ruta> --json` **observa** la terminal, no la inicia | `orca worktree set --worktree id:<repoId>::<ruta> --comment "<qué corre acá>" --json` | `orca terminal list --worktree id:<repoId>::<ruta> --json` devuelve una terminal con el agente de la familia esperada |

**La comprobación de familia y directorio no es opcional.** Un agente de la familia equivocada
responde razonablemente y no reconoce el prefijo; uno en el directorio equivocado trabaja sobre el
repositorio que no es. Las dos se leen del mismo observable, antes de despachar.

**Del mismo observable sale la identidad que el dossier lleva**, y es la de **este** panel —el del
flujo—, no la del panel del intake: en Herdr, el panel **donde quedó el agente** —el raíz que
`worktree open` devuelve en `.result.root_pane.pane_id`, o el que se abrió aparte si ese estaba
ocupado—, que es el `pane_id` que `agent get <nombre>` acredita; en Orca, el
`handle` de la terminal que `terminal list --worktree` devuelve para el worktree recién creado.
Anotarla acá es lo que permite escribirla en la sección 11 del dossier, que se redacta después.

## Sembrar el entorno ignorado

### Derivar el inventario

```
git -C <repo_destino> status --porcelain --ignored=matching -uall | grep '^!!'
```

Eso lista lo ignorado. Para lo untracked-pero-no-ignorado, `git status --porcelain` a secas. Leer la
salida **en el momento**: una lista transcrita de una corrida anterior envejece, y una entrada muerta
se lee igual de bien que una viva.

### Clasificar

El criterio de `SKILL.md` → 6.2 decide qué entra. Para cada candidato, la pregunta es:

> ¿Esto es **cómo se configura el flujo en este repo**, o es **lo que otra corrida dejó**?

Lo primero se siembra, lo segundo no. Todas las rutas de abajo se leen **dentro del
`<repo_destino>`**, que es el repo donde va a correr el flujo — nunca el repo donde vive esta skill.
Casos que se ven seguido:

- `.specify/config.yml` — **siembra**. Es el config de `sdd-flow`: comandos de test/build/lint, modo
  de implementación, política cross-model. Sin él la skill entra por `init`.
- `.specify/constitution.md` — **siembra** si existe. Son las restricciones del proyecto.
- `.claude/settings.local.json` — **siembra**. Permisos ya concedidos; sin ellos el flujo se detiene
  en prompts que en el árbol principal ya estaban resueltos.
- `.co-explore/`, `.cross-review/`, `.cross-implement/`, `.cross-model/` — **no**. Artefactos de
  corridas.
- `.plans/` — **no**, salvo retoma y la vía separada de **un solo archivo** cuando las instrucciones
  raíz del destino declaran el registro de incidentes en cada worktree. En una retoma se copia **la
  carpeta de ese plan y solo esa**; la excepción de registro no abre el resto de `.plans/`.
- `node_modules/`, `__pycache__/`, `.idea/` — **no**. Si el flujo necesita dependencias, se instalan
  en el worktree; una caché copiada puede traer rutas absolutas del árbol viejo adentro.

Ante un candidato que no encaja en ninguna fila: preguntarle al usuario. Es más barato que sembrar de
más.

### Copiar y comprobar

**Por archivo, no por directorio, y creando los intermedios.** El directorio destino puede existir ya
—medio versionado— y entonces copiar la unidad entera la anida adentro en vez de fusionarla:

Este bucle **solo** procesa `.specify/` y `.claude/`: no añadir `.plans/` al filtro. El registro
declarado se prepara después por su ruta única en «Preparar el registro declarado del worktree»;
sus comprobaciones no se sustituyen por las tres de este bucle.

```
for f in $(git -C <repo_destino> status --porcelain --ignored=matching -uall \
             | grep '^!!' | awk '{print $2}' | grep -E '^\.(specify|claude)/'); do
  mkdir -p "<worktree>/$(dirname "$f")"
  cp -a "<repo_destino>/$f" "<worktree>/$f"
done
```

PowerShell:

```
git -C <repo_destino> status --porcelain --ignored=matching -uall |
  Where-Object { $_ -like '!!*' } | ForEach-Object { ($_ -split '\s+')[1] } |
  Where-Object { $_ -match '^\.(specify|claude)/' } | ForEach-Object {
    $d = Split-Path "<worktree>\$_" -Parent
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    Copy-Item -Force "<repo_destino>\$_" "<worktree>\$_"
  }
```

Después, **las tres comprobaciones** — cada una caza una forma distinta de siembra rota:

```
git -C <worktree> check-ignore -v .specify/config.yml .claude/settings.local.json
git -C <worktree> status --porcelain
ls <worktree>/.specify/config.yml <worktree>/.claude/settings.local.json
```

1. `check-ignore` con salida por cada archivo → el destino los ignora. **Sin salida = no los ignora**,
   y van a terminar en un commit del flujo.
2. `status --porcelain` sin las rutas sembradas → confirma lo anterior desde el otro lado.
3. `ls` de cada archivo **en la ruta esperada** → caza el anidamiento. Sin ésta, un
   `.claude/.claude/settings.local.json` pasa las dos primeras sin una queja: también está ignorado,
   así que el árbol se ve limpio y la siembra parece hecha.

Un archivo puede estar ignorado en el árbol principal por `.git/info/exclude` (que **sí** comparten
los worktrees del mismo repo) o por el ignore global del usuario (que también aplica). Lo que **no**
viaja es `info/exclude` a un **clone** — si el destino es un clone y no un worktree, la comprobación
es la que salva.

### Preparar el registro declarado del worktree

**Cargar al clasificar la declaración de 6.2; ejecutar la siembra solo con sede local concordante.** Leer `AGENTS.md` y `CLAUDE.md`
de la raíz de `repo_destino`, si existen, tal como están en disco. Extraer **solo** una instrucción
explícita que declare sede y ruta del registro de incidentes de skills en cada worktree; el
silencio de un archivo no contradice al otro. No inferirla de palabras sueltas, del pedido
conversacional ni de la constitution local. Si divergen, falta la ruta o la lectura es ambigua,
detener antes de escribir y pedir corrección o decisión humana; el intake no edita instrucciones.
Repetir la extracción en el worktree recién creado y comparar `(sede, ruta)`, no textos completos.
Una diferencia detiene. Sin declaración concordante: `sin-declaración`; con otra sede:
`otra-sede` con sede y ruta, sin copiar. Solo este worktree activa la vía siguiente.

El insumo es la tupla `(sede,
ruta relativa)` extraída de las instrucciones raíz de `repo_destino` y del worktree, no una ruta
literal de esta skill. La vía prepara **un archivo** fuera del bucle general; nunca copia el resto
de `.plans/`. Antes de crear nada, rechazar ruta vacía, absoluta, con `..` o sin destino único.
Resolver la raíz física del worktree y la ruta completa con `Path.resolve(strict=False)`, que
resuelve los enlaces de los componentes existentes aun si falta el archivo final, y exigir que
`relative_to(raíz_física)` tenga éxito y no sea `.`. Hacer la misma comparación por componentes
para la fuente normal bajo la raíz física de `repo_destino`; un prefijo textual (`startswith`) no
prueba confinamiento. Repetir el control justo antes de publicar. En Windows, una ruta con unidad
no es relativa aunque no tenga barra inicial. Si cambia la tupla o un enlace escapa, detenerse;
no corregir las instrucciones del destino ni escribir fuera del árbol.

Aplicar el mismo chequeo a `(worktree, ruta)` y a `(repo_destino, ruta)` para la fuente normal.
Cada ejecución imprime la ruta física; código distinto de cero detiene. La fuente alternativa se
compara con la **ruta física aprobada**, no se fuerza bajo `repo_destino`:

| POSIX | PowerShell |
|---|---|
| `python3 -c 'from pathlib import Path; import sys; root=Path(sys.argv[1]).resolve(strict=True); rel=Path(sys.argv[2]); sys.exit("ruta no relativa") if (rel.is_absolute() or rel.drive or not rel.parts or ".." in rel.parts) else None; target=(root/rel).resolve(strict=False); target.relative_to(root); sys.exit("ruta raíz") if target==root else None; print(target)' "$raiz" "$ruta"` | `py -3 -c 'from pathlib import Path; import sys; root=Path(sys.argv[1]).resolve(strict=True); rel=Path(sys.argv[2]); sys.exit(''ruta no relativa'') if (rel.is_absolute() or rel.drive or not rel.parts or ''..'' in rel.parts) else None; target=(root/rel).resolve(strict=False); target.relative_to(root); sys.exit(''ruta raíz'') if target==root else None; print(target)' $raiz $ruta` |

Asignar la salida **física y absoluta** del chequeo con `raiz=worktree` a `destino`, no asignarle
la ruta relativa. POSIX: `destino=$(python3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' "$worktree" "$ruta")`;
PowerShell: `$destino = py -3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' $worktree $ruta`.
Si la salida del chequeo físico anterior, o cualquiera de sus repeticiones antes y después de
publicar, difiere de `destino`, detenerse. Así `mkdir`, la creación exclusiva y el cotejo de bytes
usan el mismo archivo del worktree, no un relativo al directorio desde el que corre el intake.
Para la fuente normal, asignar a `fuente` la ruta física del chequeo con `raiz=repo_destino`:
POSIX `fuente=$(python3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' "$repo_destino" "$ruta")`;
PowerShell `$fuente = py -3 -c 'from pathlib import Path; import sys; print((Path(sys.argv[1])/sys.argv[2]).resolve(strict=False))' $repo_destino $ruta`.
Exigir que coincida con la salida del chequeo y que el archivo exista. Para una fuente alternativa,
`fuente` es exactamente la ruta física concreta aprobada, no una ruta relativa inferida.

**Primero, lo que ya existe.** Contar como existente también un enlace roto (`lexists`), no solo
`Path.exists()`. Si el hook o el árbol dejó un archivo antes del primer intento de siembra, exigir
evidencia de esa procedencia; la mera existencia, el ignore o un dossier anterior no la prueban.
Al adoptar un árbol de otra sesión, o al reintentar tras una siembra acreditada cuyo dossier o
despacho falló, una procedencia no acreditada es `detenido` hasta decisión humana. Nunca borrar ni
reclasificar un residual automáticamente. Un registro preexistente válido puede estar poblado:
no se vacía, no se sobrescribe y no exige fuente. Un archivo versionado limpio o ignorado puede
servir; uno versionado modificado o no trackeado y no ignorado detiene.
Un comentario legado posterior al cierre no invalida un previo **poblado**; el mismo formato
**vacío** no sirve para el primer alta porque no termina en `\n---\n`. La inspección no infiere
procedencia por la mera presencia de una nota o comentario: el origen del archivo debe estar
acreditado por separado.

Crear **otro** scratch privado de intento de siembra fuera del worktree antes de inspeccionar
el previo o tomar la fuente. No reutilizar ni limpiar aquí `scratch_vuelta`; sus wrappers ya
se reconstruyeron desde la unidad congelada en «Preparar y reanudar la vuelta congelada».
Todos los archivos de este intento se escriben por creación exclusiva, no con un editor ni
con `Out-File` de PowerShell 5.1. Un reintento de 6.2 crea otro scratch de siembra.

POSIX:

```sh
if scratch=$(python3 -c 'import tempfile; print(tempfile.mkdtemp(prefix="registro-intake-"))') && [ -n "$scratch" ]; then
  instantanea="$scratch/fuente"; inventario="$scratch/inventario"
  mapa="$scratch/mapa"; candidato="$scratch/candidato"; previo="$scratch/previo"
else
  printf '%s\n' 'No se pudo crear el scratch privado' >&2
  exit 3
fi
printf '%s\n' "$scratch"
```

PowerShell:

```powershell
$scratch = py -3 -c 'import tempfile; print(tempfile.mkdtemp(prefix=''registro-intake-''))'
if ($LASTEXITCODE -ne 0 -or -not $scratch) { throw 'No se pudo crear el scratch privado' }
$instantanea = Join-Path $scratch 'fuente'; $inventario = Join-Path $scratch 'inventario'
$mapa = Join-Path $scratch 'mapa'; $candidato = Join-Path $scratch 'candidato'
$previo = Join-Path $scratch 'previo'
$scratch
```

Conservar la ruta literal que imprimió la preparación. Al reentrar en **cada** shell nuevo
de 6.2, después de validar `scratch_vuelta` y reconstruir el wrapper de la unidad congelada,
asignar esa misma ruta de siembra y derivar sus cinco archivos; no llamar otra vez a
`mkdtemp` ni aprovechar el scratch de otro intento:

```sh
scratch='/ruta/literal/devuelta/registro-intake-…'
worktree='/ruta/fisica/ya-acreditada/del/worktree'
ruta='ruta/relativa/declarada/del/registro'
[ -d "$scratch" ] && [ ! -L "$scratch" ] || exit 3
[ -d "$worktree" ] && [ -n "$ruta" ] || exit 3
destino=$(python3 -c 'from pathlib import Path; import sys; root=Path(sys.argv[1]).resolve(strict=True); rel=Path(sys.argv[2]); sys.exit("ruta no relativa") if (rel.is_absolute() or rel.drive or not rel.parts or ".." in rel.parts) else None; target=(root/rel).resolve(strict=False); target.relative_to(root); sys.exit("ruta raíz") if target==root else None; print(target)' "$worktree" "$ruta") || exit 3
instantanea="$scratch/fuente"; inventario="$scratch/inventario"
mapa="$scratch/mapa"; candidato="$scratch/candidato"; previo="$scratch/previo"
```

```powershell
$scratch = '/ruta/literal/devuelta/registro-intake-…'
$worktree = '/ruta/fisica/ya-acreditada/del/worktree'
$ruta = 'ruta/relativa/declarada/del/registro'
if (-not (Test-Path -LiteralPath $scratch -PathType Container) -or
    (Get-Item -LiteralPath $scratch).LinkType -eq 'SymbolicLink') { exit 3 }
if (-not (Test-Path -LiteralPath $worktree -PathType Container) -or -not $ruta) { exit 3 }
$destino = py -3 -c 'from pathlib import Path; import sys; root=Path(sys.argv[1]).resolve(strict=True); rel=Path(sys.argv[2]); sys.exit(''ruta no relativa'') if (rel.is_absolute() or rel.drive or not rel.parts or ''..'' in rel.parts) else None; target=(root/rel).resolve(strict=False); target.relative_to(root); sys.exit(''ruta raíz'') if target==root else None; print(target)' $worktree $ruta
if ($LASTEXITCODE -ne 0 -or -not $destino) { exit 3 }
$instantanea = Join-Path $scratch 'fuente'; $inventario = Join-Path $scratch 'inventario'
$mapa = Join-Path $scratch 'mapa'; $candidato = Join-Path $scratch 'candidato'
$previo = Join-Path $scratch 'previo'
```

`worktree` y `ruta` son los literales ya contrastados entre destino y árbol nuevo; `destino` se
recalcula y se compara con la salida física del chequeo anterior antes de publicar. No tomar estos
operandos del cwd ni de un shell anterior. `fuente` se reconstruye solo al entrar en la rama de
siembra, desde la ruta física normal o la alternativa aprobada. Si la preparación del scratch
devuelve un código distinto de cero, detener la vuelta; no reutilizar variables ni rutas de un
scratch anterior.

Cuando `destino` ya existe y su procedencia está acreditada, copiarlo **sin sobrescribir** a
`previo` y ejecutar `inspeccionar-previo`. Entregarle un argumento citado por cada ID del grupo a
despachar, no solo el primero. En POSIX, cargarlos primero en parámetros posicionales
con `set --`, uno citado por ID; el bloque siguiente los transmite con `"$@"`. POSIX:

```sh
python3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open("xb"); f.write(Path(sys.argv[1]).read_bytes()); f.close()' "$destino" "$previo" &&
  registro_candidato inspeccionar-previo "$previo" "$worktree" "$@"
```

PowerShell:

```powershell
if (-not (Get-Command Invoke-RegistroCandidato -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de candidato no cargada'); exit 3 }
$ids_del_grupo = @($args) # argumentos literales de esta etapa: un ID completo por argumento
if ($ids_del_grupo.Count -eq 0 -or @($ids_del_grupo | Where-Object { -not $_ }).Count -ne 0) { throw 'Asignar IDs definitivos en este shell' }
py -3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open(''xb''); f.write(Path(sys.argv[1]).read_bytes()); f.close()' $destino $previo
if ($LASTEXITCODE -ne 0) { throw 'Registro previo: copia fallida' }
Invoke-RegistroCandidato -Argumentos (@('inspeccionar-previo', $previo, $worktree) + $ids_del_grupo)
```

Leer JSON, stderr y código. `count` cuenta H2 exteriores posteriores al cierre; `ids` conserva
el ID completo —fecha **y hora** local si corresponde—; `row_ids` procede solo de la primera
celda del Índice, sin buscar en `Síntoma`. El mismo ID una vez en cada conjunto es normal;
repetido **dentro** de cualquiera de ellos detiene. `targets_present` no vacío da código `12`
y bloquea **todo el grupo**; un ID objetivo vacío también da `12`. Un vacío útil exige terminar exactamente en `\n---\n`;
un previo poblado no necesita separador al final de su última sección. Si es utilizable,
conservar sus bytes y su estado Git observados, borrar `scratch/previo` solo tras acreditar
`preexistente` y entregar ruta, `count`, `ids`, `row_ids`, `anotacion_historica` y estado Git.
`anotacion_historica.presente` describe bytes previos, no trabajo de esta corrida. En cualquier fallo,
conservar `scratch/previo` y enumerarlo entre residuales; no exigir ni abrir fuente de siembra.

**Solo si falta, elegir fuente y preparar candidato.** La fuente normal es la misma ruta declarada
en `repo_destino`, resuelta físicamente dentro de esa raíz; puede coincidir con el registro de
entrada sin quedar descalificada. Si falta o su cabecera no tiene límites inequívocos, conservar el
worktree y detener el lote. No tomar automáticamente otro registro ni reconstruir reglas.
Reanudar solo cuando el usuario apruebe **un archivo y su ruta física concreta** para este
repositorio y esta ruta de registro; una salida física fuera de `repo_destino` debe estar incluida
en esa aprobación. La aprobación no viaja a otro repositorio/ruta y no congela los bytes: cada
vuelta toma otra instantánea con inventario y mapa nuevos.

Copiar la fuente a `instantanea` por creación exclusiva; no volver a leer la fuente durante esa
vuelta. POSIX:

```sh
fuente='/ruta/fisica/de/la/fuente-ya-acreditada'
[ -f "$fuente" ] || exit 3
python3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open("xb"); f.write(Path(sys.argv[1]).read_bytes()); f.close()' "$fuente" "$instantanea" &&
  registro_candidato inventariar "$instantanea" "$inventario" "$worktree"
```

PowerShell:

```powershell
if (-not (Get-Command Invoke-RegistroCandidato -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de candidato no cargada'); exit 3 }
$fuente = '/ruta/fisica/de/la/fuente-ya-acreditada'
if (-not (Test-Path -LiteralPath $fuente -PathType Leaf)) { exit 3 }
py -3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open(''xb''); f.write(Path(sys.argv[1]).read_bytes()); f.close()' $fuente $instantanea
if ($LASTEXITCODE -ne 0) { throw 'Registro candidato: copia de fuente fallida' }
Invoke-RegistroCandidato -Argumentos @('inventariar', $instantanea, $inventario, $worktree)
```

**Inventario → mapa declarado → constructor → cotejo.** Leer el inventario entero: SHA-256,
tamaño, número y offsets de cada línea, todos los H2 exteriores con texto y patrón, filas,
separadores y cercas. Contrastar el contenido de cada tramo de `instantanea` y **declarar
manualmente** una lista ordenada de argumentos
`<primera-línea>:<línea-fin-exclusiva>:<clase>`; para una nota, añadir
`:nota-explicita` solo después de inspeccionar su cuerpo. Clases: `titulo`, `reglas`, `indice`,
`fila_indice`, `nota`, `comentario`, `cierre`, `incidente`, `blancos_finales`. No inferir notas por etiqueta ni
usar la primera fecha como límite de cabecera. `mapear` convierte líneas a bytes y copia digest,
tamaño y H2 del inventario; **no decide las clases**. Sus argumentos son los tramos declarados
por el conductor. No lo invocar con una lista vacía. En POSIX, cargar antes los tramos
en parámetros posicionales con `set --`, uno citado por tramo; `"$@"` los pasa a `mapear`
sin depender de arrays de shell.

**Fronteras canónicas para declarar `tramos` (líneas 1-based, fin exclusivo).** La lista debe
cubrir todos los bytes en orden, sin huecos ni solapamientos; fusionar tramos contiguos de la
misma clase, excepto dos notas o dos incidentes distintos. El constructor coteja esa partición
exacta, no solo la suma de bytes:

- `titulo`: desde el primer H1 hasta antes de `## Reglas de este archivo`. `reglas`: desde ese H2
  hasta antes de `## Índice`, interrumpida únicamente por notas previas al Índice; el `---` exterior
  inmediatamente anterior al Índice pertenece a `reglas`.
- `indice`: su H2, cabecera y delimitadora de la tabla; también los blancos fuera de las filas
  hasta una nota o el cierre. Todas las filas de datos contiguas forman **un** tramo
  `fila_indice`; sin filas, no se declara ese tramo.
- `nota`: empieza solo en `## Nota histórica` o `## Nota: <texto no vacío>` y llega hasta el
  siguiente ATX exterior, el separador anterior al Índice o el blanco reservado al cierre,
  lo primero; incluye sus otros blancos finales y lleva `:nota-explicita`. Una nota nueva inicia
  otro tramo, aunque sea contigua.
- `comentario`: solo el bloque exterior único que comienza en columna cero con
  `<!-- procedencia:`. El inventario informa `comment.line_start` y
  `comment.line_end_exclusive`; contrastar los bytes físicos y declarar en el mapa el tramo
  que incluye los blancos contiguos antes del bloque y, en la disposición legada, también
  los posteriores. Si está antes del cierre, el tramo termina antes del blanco inmediato
  reservado a `cierre`. Una nota después de la tabla y antes del comentario detiene.
- `cierre`: **la línea exactamente `\n` inmediata anterior** al primer `---` exterior posterior
  al Índice **y** esa línea `---`. En la disposición legada, este tramo precede a `comentario`
  en el mapa de la fuente, pero `construir` mueve sus bytes originales detrás de todos los
  blancos conservados del comentario. No agregar otro separador. Sin comentario, los blancos
  anteriores siguen en `indice` o `nota`.
- `incidente`: tras el cierre, el primer tramo empieza en la línea siguiente al `---`, incluyendo
  blancos/separadores previos a su H2; cada H2 de incidente exterior inicia un tramo nuevo con
  sus propios blancos/separadores previos. Cada tramo contiene exactamente un H2 de incidente.
  `blancos_finales` contiene solo blancos tras el último incidente, o tras el cierre si no hay
  incidentes.

Así, en la secuencia `\n---\n\n## Incidente …`, el blanco **anterior** a `---` pertenece a
`cierre` y el **posterior** al primer `incidente`, no a `indice` ni a `cierre` respectivamente.
Con comentario legado, los blancos entre cierre histórico y primer incidente pertenecen a
`comentario`, no al primer incidente. Para un bloque en ambas posiciones, declarar por separado
sus dos rangos literales `primera:fin:clase`; un mapa que absorbe el blanco de `cierre` en
`comentario`, o que deja uno de los blancos legados en `incidente`, se rechaza.
Leer los offsets y las líneas del inventario antes de declarar cada frontera; un `Mapa inválido`
identifica el primer tramo esperado/recibido, pero no sustituye esa lectura.

POSIX:

```sh
registro_candidato mapear "$inventario" "$mapa" "$worktree" "$@" &&
  registro_candidato construir "$instantanea" "$mapa" "$candidato" "$worktree" &&
registro_candidato cotejar "$instantanea" "$mapa" "$candidato" "$worktree"
```

PowerShell:

```powershell
if (-not (Get-Command Invoke-RegistroCandidato -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de candidato no cargada'); exit 3 }
$tramos = @($args) # argumentos literales declarados tras leer este inventario, uno por tramo
if ($tramos.Count -eq 0 -or @($tramos | Where-Object { $_ -notmatch '^[0-9]+:[0-9]+:[a-z_]+(?::[a-z-]+)?$' }).Count -ne 0) { throw 'Declarar tramos de este inventario en este shell' }
Invoke-RegistroCandidato -Argumentos (@('mapear', $inventario, $mapa, $worktree) + $tramos)
Invoke-RegistroCandidato -Argumentos @('construir', $instantanea, $mapa, $candidato, $worktree)
Invoke-RegistroCandidato -Argumentos @('cotejar', $instantanea, $mapa, $candidato, $worktree)
```

**Frontera de los modos de siembra (la unidad siguiente no se edita en una corrida).**

| Modo | Detecta | No detecta | Datos de salida | Clase de salida | Dirección de error | Fallo de ejecución |
|---|---|---|---|---|---|---|
| `inventariar` | LF/UTF-8, cercas, H2, separadores, filas y límites del comentario exterior | si la posición del comentario forma una fuente publicable | inventario exclusivo para que el conductor declare tramos | `veredicto` | `las dos`: un límite omitido o añadido cambia los tramos candidatos | código 3, sin inventario acreditado |
| `mapear` | sintaxis, offsets y cobertura de tramos, incluida clase `comentario` | verdad semántica de las clases declaradas | mapa exclusivo | `veredicto` | `admite-de-mas`: un mapa cubriente puede atribuir una clase falsa | código 3, sin mapa acreditado |
| `construir` | gramática completa, doce campos de incidente y partición exacta, reubicación del cierre original | efecto posterior sobre el registro de entrada | `cierre_reubicado`, `comentario_zona` y candidato exclusivo | `veredicto` | `admite-de-mas`: una fuente aceptada aún puede fallar el cotejo independiente | código 3, sin candidato acreditado |
| `cotejar` | por recorrido propio, candidato canónico, fuente, bytes preservables, doce campos y reubicación; después coteja el mapa | autorización de publicación y procedencia Git del destino | `accredited`, `anotacion_historica`, `cierre_reubicado` | `veredicto` | `las dos`: una divergencia del recorrido propio puede aceptar o rechazar una frontera incorrectamente | código 3, sin acreditación |
| `inspeccionar-previo` | estructura del registro presente, filas/H2/IDs objetivo y anotación histórica; legado poblado sí, vacío legado no | origen del archivo o limpieza del estado Git | `count`, `ids`, `row_ids`, `anotacion_historica` para decisión del conductor | `veredicto` | `las dos`: un ID omitido o añadido cambia la decisión de utilidad | código 3, sin previo acreditado |

`inventariar` acredita con `0` solo que pudo construir el inventario sintáctico; el conductor
todavía declara y adjudica los tramos. `inspeccionar-previo` acredita con `0` la estructura
admitida y ausencia de IDs objetivo, no la procedencia ni el estado Git que exige el paso 6.
En todos los modos `veredicto`, `0` autoriza solo la propiedad de su columna «Detecta», no las
ausencias declaradas; los datos de salida siguen requiriendo lectura del conductor.
Las paradas de estructura son distintas de un fallo de ejecución; stdout semántico es JSON ASCII.
`inventariar` cuenta el marcador `<!-- procedencia:` solo fuera de cercas, aun si aparece en
una zona que `construir` rechazará. Las líneas físicas se parten solo por LF; únicamente
espacios o tabulaciones forman un blanco ordinario. FF, NBSP y otros caracteres UTF-8 no son
cortes ni blancos. Un comentario canónico o legado termina con `-->` al final de línea,
sin delimitadores anidados ni historial Markdown, y exige blanco antes y después salvo EOF
inmediato tras un comentario legado vacío.
Las salidas semánticas son `0` para acreditado y `12` para estructura/ID inadmisible;
una invocación mal formada da `2`. Ninguno se interpreta como un fallo de ejecución `3`.
`anotacion_historica.tipos` enumera en orden de aparición, sin repetir, `comentario`,
`nota-historica` o `nota-etiquetada`; la última proyecta el tipo interno `nota-titulada`.
`presente` solo dice que esos bytes ya estaban en la fuente o en el previo: no atribuye
la anotación a esta siembra.

**La unidad siguiente implementa los modos de siembra y retiro; no se edita en una corrida.** `inventariar`
rechaza CRLF, UTF-8 inválido, cercas ambiguas o sin cierre y límites no legibles. `mapear`
lee solo el inventario, valida sintaxis/límites de línea y copia su digest, tamaño y patrones;
`construir` vuelve a leer la instantánea y comprueba que el mapa pertenezca a ella,
recalcula H2, valida el mapa completo contra la partición canónica y escribe el candidato por
creación exclusiva **solo** si título, reglas, Índice, filas, notas, cierre e incidentes están
clasificados sin huecos ni solapamientos. Una fuente con `## Incidente INC-1` antes del cierre,
H2 desconocido, nota fuera de zona, setext/cerca ambigua o contenido sustantivo tras el cierre
se detiene; una fuente aprobada no salta esa gramática. No exige biyección entre filas y secciones.
`cotejar` relee candidato y fuente **sin las etiquetas del mapa**, impone una lista positiva de
estructura, comprueba ausencia de filas y secciones heredadas, preservación byte a byte y cierre
exacto `\n---\n`. Una salida `0` de `construir` por sí sola no acredita siembra.

<!-- registro-candidato:inicio -->
```python
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import base64
import json
import os
import re
import stat
import sys
import tempfile
import time
from collections import Counter
from uuid import uuid4

FIELDS = ("Skill", "Síntoma", "Evidencia mínima", "Relacionado", "Conductor", "Worker", "Plataforma", "Transporte", "Resolución", "Skill / sección", "Consecuencia", "Corrección propuesta")
ISSUE_HEADER_FIELDS = frozenset(("Skill", "Relacionado", "Conductor", "Worker", "Plataforma", "Transporte"))
KEEP = {"titulo", "reglas", "indice", "nota", "comentario", "cierre"}
KINDS = KEEP | {"fila_indice", "incidente", "blancos_finales"}
LOCAL = re.compile(r"^## (\d{2}/\d{2}/\d{4} \d{2}:\d{2})(?:[ \t].*)?$", re.S)
ISO = re.compile(r"^## (\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?)(?:[ \t].*)?$", re.S)
NUMERIC = re.compile(r"^## ([0-9]+)(?:[ .:–-].*)?$", re.S)
NAMED = re.compile(r"^## Incidente ([A-Za-z0-9][A-Za-z0-9_-]*)(?:[ \t].*)?$", re.S)
FIELD = re.compile(r"^[ \t]*(?:(?:>[ \t]*)|(?:[-*+][ \t]*)|(?:\d+[.)][ \t]*))*\*\*(?:" + "|".join(re.escape(x) for x in FIELDS) + r"): ?\*\*", re.U)
ATX = re.compile(r"^(#{1,6})[ \t]+(.+)$")
TABLE_DELIMITER = re.compile(r"\|(?: *:?-{3,}:? *\|)+")


class ValidationError(Exception):
    def __init__(self, message, code=12, payload=None):
        super().__init__(message)
        self.code = code
        self.payload = payload or {}


def fail(message, code=12, payload=None):
    raise ValidationError(message, code, payload)


def digest(data):
    return sha256(data).hexdigest()


def write_json_exclusive(path, payload):
    data = (json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    with path.open("xb") as stream:
        stream.write(data)
    return digest(data)


def read_json_regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        fail("Scratch con archivo no regular o enlazado: " + str(path))
    return json.loads(path.read_text(encoding="ascii"))


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


EVENT_TYPES = {"ids-definitivos", "efecto-acreditado", "rechazo-aprobado", "reconciliacion-aprobada", "ventana-plazo-aprobada"}


def validate_event(previous, event, manifest):
    required = {"schema_version", "secuencia", "tipo", "vuelta_id", "instante_utc", "ids", "datos"}
    if (not isinstance(event, dict) or set(event) != required or event["schema_version"] != 1 or
            type(event["secuencia"]) is not int or event["secuencia"] != len(previous) + 1 or
            event["tipo"] not in EVENT_TYPES or event["vuelta_id"] != manifest["vuelta_id"] or
            not isinstance(event["instante_utc"], str) or not event["instante_utc"].endswith("Z") or
            not isinstance(event["ids"], list) or not event["ids"] or
            any(not isinstance(value, str) or not value for value in event["ids"]) or
            len(set(event["ids"])) != len(event["ids"]) or not isinstance(event["datos"], dict)):
        fail("Evento de vuelta mal formado")
    try:
        datetime.fromisoformat(event["instante_utc"].replace("Z", "+00:00"))
    except ValueError:
        fail("Instante UTC de evento inválido")
    kind, data = event["tipo"], event["datos"]
    effects = [entry for entry in previous if entry["tipo"] in ("efecto-acreditado", "rechazo-aprobado")]
    reconciliations = [entry for entry in previous if entry["tipo"] == "reconciliacion-aprobada"]
    latest_ids = next((entry["ids"] for entry in reversed(previous) if entry["tipo"] == "ids-definitivos"), None)
    if kind == "ids-definitivos":
        if effects or reconciliations or data:
            fail("IDs definitivos posteriores al efecto o con datos extra")
    elif kind in ("efecto-acreditado", "rechazo-aprobado"):
        keys = {"identidad", "evidencia"} if kind == "efecto-acreditado" else {"decision", "evidencia"}
        if effects or reconciliations or set(data) != keys or any(not isinstance(data[key], str) or not data[key] for key in keys):
            fail("Efecto o rechazo duplicado o sin evidencia")
        if latest_ids != event["ids"]:
            fail("Efecto no enlazado a los últimos IDs definitivos")
    elif kind == "reconciliacion-aprobada":
        keys = {"identidad", "cotejo_ruta", "cotejo_sha256", "decision"}
        if effects or reconciliations or set(data) != keys or any(not isinstance(data[key], str) or not data[key] for key in keys):
            fail("Reconciliación duplicada o incompleta")
        if latest_ids != event["ids"] or not Path(data["cotejo_ruta"]).is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", data["cotejo_sha256"]):
            fail("Reconciliación sin enlace a IDs y cotejo")
        if digest(Path(data["cotejo_ruta"]).read_bytes()) != data["cotejo_sha256"]:
            fail("Cotejo de reconciliación cambió")
    else:
        keys = {"plazo_anterior", "plazo_nuevo", "decision"}
        if not (effects or reconciliations) or set(data) != keys or any(not isinstance(data[key], str) or not data[key] for key in keys):
            fail("Nueva ventana sin efecto y decisión")
        if latest_ids != event["ids"]:
            fail("Nueva ventana con IDs distintos")
        deadline_file = Path(manifest["unidad_ruta"]).parent / "plazo-retiro.json"
        deadline = read_json_regular(deadline_file)
        windows = [entry for entry in previous if entry["tipo"] == "ventana-plazo-aprobada"]
        previous_end = windows[-1]["datos"]["plazo_nuevo"] if windows else deadline.get("limite_utc")
        try:
            event_time = datetime.fromisoformat(event["instante_utc"].replace("Z", "+00:00"))
            old_time = datetime.fromisoformat(previous_end.replace("Z", "+00:00"))
            new_time = datetime.fromisoformat(data["plazo_nuevo"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            fail("Sellos de ventana inválidos")
        if (not data["plazo_nuevo"].endswith("Z") or new_time.utcoffset() != timedelta(0) or
                data["plazo_anterior"] != previous_end or event_time <= old_time or
                new_time <= event_time):
            fail("Ventana nueva sin vencimiento anterior o plazo posterior")


def validate_round(scratch, register):
    if not scratch.is_absolute() or not register or not scratch.exists() or scratch.is_symlink():
        fail("Ruta de scratch ausente o no absoluta")
    scratch = scratch.resolve(strict=True)
    if not stat.S_ISDIR(scratch.lstat().st_mode):
        fail("Scratch no es directorio regular")
    manifest = read_json_regular(scratch / "manifiesto.json")
    if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "vuelta_id", "modo", "registro_ruta", "registro_fisico", "registro_kind", "unit_sha256", "unidad_ruta", "creado_utc"} or
            manifest["schema_version"] != "scratch-vuelta/1" or manifest["modo"] not in ("despachar", "volcar") or
            not re.fullmatch(r"[0-9a-f]{32}", str(manifest["vuelta_id"])) or
            manifest["registro_ruta"] != register or manifest["registro_kind"] not in ("archivo", "issues") or
            not re.fullmatch(r"[0-9a-f]{64}", str(manifest["unit_sha256"])) or
            manifest["unidad_ruta"] != str(scratch / "unidad.py")):
        fail("Manifiesto de vuelta inválido o de otro registro")
    if (manifest["registro_kind"] == "issues") != (register == "issues"):
        fail("Tipo de registro de vuelta contradictorio")
    if register != "issues" and (not Path(register).is_absolute() or manifest["registro_fisico"] != str(Path(register).resolve(strict=False))):
        fail("Ruta física de registro cambió")
    unit = scratch / "unidad.py"
    info = unit.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or digest(unit.read_bytes()) != manifest["unit_sha256"]:
        fail("Unidad congelada ausente o alterada")
    events = []
    paths = sorted(scratch.glob("evento-*.json"))
    for path in paths:
        event = read_json_regular(path)
        if path.name != f"evento-{len(events)+1:06d}-{event.get('tipo')}.json":
            fail("Secuencia de eventos no contigua")
        validate_event(events, event, manifest)
        events.append(event)
    return manifest, events


def blank(line):
    return re.fullmatch(r"[ \t]*\n", line) is not None


def private(path, root):
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError:
        return
    fail("El temporal debe estar fuera del worktree: " + str(path))


def read_source(path):
    data = path.read_bytes()
    if not data.endswith(b"\n") or b"\r" in data:
        fail("Fuente sin nueva línea final o con CRLF")
    try:
        decoded = data.decode("utf-8")
        lines = [part + "\n" for part in decoded.split("\n")[:-1]]
    except UnicodeDecodeError:
        fail("Fuente no es UTF-8 estricto")
    starts = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line.encode("utf-8"))
    return data, lines, starts + [offset]


def incident_id(heading):
    for pattern, label in ((LOCAL, "fecha-local"), (ISO, "iso")):
        match = pattern.fullmatch(heading)
        if match:
            return label, match.group(1)
    if re.match(r"^## [0-9]{4}-[0-9]{2}-[0-9]{2}", heading):
        return None, None
    for pattern, label in ((NUMERIC, "numerico"), (NAMED, "incidente-id")):
        match = pattern.fullmatch(heading)
        if match:
            return label, match.group(1)
    return None, None


def heading_kind(line):
    if line == "## Reglas de este archivo\n":
        return "reglas"
    if line == "## Índice\n":
        return "indice"
    if line == "## Nota histórica\n":
        return "nota-historica"
    if re.fullmatch(r"## Nota: [^\n]+\n", line):
        return "nota-titulada"
    return incident_id(line[:-1])[0] or "no-clasificado"


def scan(lines, starts, retirement=False):
    headings = []
    atx = []
    fences = set()
    separators = []
    fence_spans = []
    fence = None
    previous_outside = ""
    body_started = False
    index_seen = False
    closing_seen = False
    for n, line in enumerate(lines):
        body = line[:-1]
        fence_like = re.match(r"^[ \t]*(`{3,}|~{3,})", body)
        if fence is not None:
            fences.add(n)
            if fence_like and fence_like.group(1)[0] == fence[0]:
                if body == fence:
                    fence_spans[-1]["line_end"] = n + 2
                    fence = None
                    previous_outside = body
                else:
                    fail("Cerca ambigua en línea " + str(n + 1))
            continue
        if fence_like:
            marker = fence_like.group(1)
            if body.startswith((" ", "\t")) or len(marker) != 3:
                fail("Cerca ambigua en línea " + str(n + 1))
            if marker.startswith("`") and "`" in body[3:]:
                fail("Info string ambigua en línea " + str(n + 1))
            fence = marker
            fences.add(n)
            fence_spans.append({"line_start": n + 1, "line_end": None, "marker": marker})
            continue
        setext = re.fullmatch(r"[ \t]*[-=]+[ \t]*", body)
        structural = body == "---" and re.fullmatch(r"[ \t]*", previous_outside) is not None
        if setext and not structural and not (retirement and body_started):
            fail("Separador o setext ambiguo en línea " + str(n + 1))
        if structural:
            separators.append(n)
            if retirement and index_seen:
                closing_seen = True
        if re.match(r"^[ \t]+#{1,6}[ \t]+", body):
            fail("Encabezado con sangría en línea " + str(n + 1))
        if re.fullmatch(r"##[ \t]*", body):
            fail("H2 vacío en línea " + str(n + 1))
        match = ATX.fullmatch(body)
        if match:
            atx.append((n, len(match.group(1)), match.group(2)))
            if len(match.group(1)) == 2:
                kind = heading_kind(line)
                headings.append({"line": n + 1, "start": starts[n], "pattern": kind})
                if retirement:
                    if kind == "indice":
                        index_seen = True
                    elif closing_seen:
                        body_started = True
        previous_outside = body
    if fence is not None:
        fail("Cerca sin cierre")
    return headings, atx, fences, separators, fence_spans


def forbidden_preserved(line):
    if FIELD.match(line[:-1]):
        return True
    # Detecta encabezados de incidente ocultos por citas o listas sin confundir H3 numerados con IDs.
    visible = re.sub(r"^[ \t]*(?:(?:>[ \t]*)|(?:[-*+][ \t]*)|(?:\d+[.)][ \t]*))*", "", line[:-1])
    match = re.match(r"^#{2,6}[ \t]+(.+)$", visible)
    if match:
        text = match.group(1)
        if re.match(r"(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|Incidente\s+[A-Za-z0-9])", text):
            return True
        if visible != line[:-1]:
            return True
    return False


def historical_comment(lines, fences):
    markers = [n for n, line in enumerate(lines) if n not in fences and line.startswith("<!-- procedencia:")]
    if len(markers) > 1:
        fail("Más de un comentario histórico de procedencia")
    if not markers:
        return None
    start = markers[0]
    if start == 0 or not blank(lines[start - 1]):
        fail("Comentario histórico sin blanco anterior")
    end = start
    while end < len(lines):
        body = lines[end][:-1]
        if end in fences or (end > start and "<!--" in body) or (end == start and "<!--" in body[len("<!-- procedencia:"):]):
            fail("Comentario histórico anidado o en cerca")
        if (ATX.match(body) or re.fullmatch(r" {0,3}#{1,6}[ \t]*", body) or
                re.match(r"^[ \t]*(`{3,}|~{3,})", body) or
                re.fullmatch(r"[ \t]*[-=]+[ \t]*", body) or
                re.fullmatch(r" {0,3}([*_-])(?:[ \t]*\1){2,}[ \t]*", body) or FIELD.match(body) or
                body.lstrip(" \t").startswith("|")):
            fail("Comentario histórico contiene estructura Markdown")
        if "-->" in body:
            if not body.endswith("-->") or body.count("-->") != 1:
                fail("Cierre de comentario histórico ambiguo")
            return start, end + 1
        end += 1
    fail("Comentario histórico sin cierre")


def classify(lines, starts):
    headings, atx, fences, separators, _ = scan(lines, starts)
    h1 = [n for n, level, _ in atx if level == 1]
    rules = [h["line"] - 1 for h in headings if h["pattern"] == "reglas"]
    indexes = [h["line"] - 1 for h in headings if h["pattern"] == "indice"]
    if h1 != [0] or len(rules) != 1 or len(indexes) != 1 or not (0 < rules[0] < indexes[0]):
        fail("Título, reglas o Índice ausentes, repetidos o fuera de orden")
    r, idx = rules[0], indexes[0]
    before = [n for n in separators if r < n < idx]
    if len(before) != 1 or any(not blank(lines[n]) for n in range(before[0] + 1, idx)):
        fail("Separador previo al Índice ausente o ambiguo")
    presep = before[0]
    after = [n for n in separators if n > idx]
    if not after:
        fail("Separador de cierre ausente")
    closing = after[0]
    if lines[closing - 1] != "\n":
        fail("Cierre sin línea en blanco inmediata")
    close_start = closing - 1
    comment = historical_comment(lines, fences)
    if any(h["pattern"] == "no-clasificado" for h in headings):
        fail("H2 exterior no clasificable")
    if any(h["pattern"] in ("nota-historica", "nota-titulada") and (h["line"] - 1 < r or h["line"] - 1 >= closing) for h in headings):
        fail("Nota fuera de cabecera")
    incidents = []
    notes = []
    for h in headings:
        n = h["line"] - 1
        kind = h["pattern"]
        if kind in ("fecha-local", "iso", "numerico", "incidente-id"):
            if n <= closing:
                fail("Incidente antes del cierre: línea " + str(n + 1))
            incidents.append(n)
        elif kind in ("nota-historica", "nota-titulada"):
            notes.append(n)
    comment_zone = None
    if comment:
        first, end = comment
        if idx < first < close_start:
            comment_zone = "canonica"
        elif closing < first and (not incidents or end <= incidents[0]):
            comment_zone = "legada"
        else:
            fail("Comentario histórico fuera de zona")
        if end < len(lines) and not blank(lines[end]):
            fail("Comentario histórico sin blanco posterior")
    for n, level, _ in atx:
        if n < r and level != 1:
            fail("Encabezado fuera de zona permitida")
        if idx < n < closing and level != 2:
            fail("ATX entre Índice y cierre")
    table = idx + 1
    while table < closing and blank(lines[table]):
        table += 1
    if table + 1 >= closing or not (lines[table].startswith("|") and lines[table].rstrip("\n").endswith("|")):
        fail("Encabezado del Índice ausente")
    if not TABLE_DELIMITER.fullmatch(lines[table + 1][:-1]):
        fail("Delimitadora del Índice ausente")
    row_start = table + 2
    row_end = row_start
    while row_end < close_start and lines[row_end].startswith("|"):
        if not lines[row_end][:-1].endswith("|"):
            fail("Fila de Índice incompleta")
        row_end += 1
    if any(lines[n].lstrip().startswith("|") for n in range(row_end, closing) if n not in fences):
        fail("Fila o segunda tabla fuera del Índice")
    if comment_zone == "canonica":
        first, end = comment
        if first < row_end or any(n >= row_end for n in notes) or any(not blank(lines[n]) for n in range(row_end, first)) or any(not blank(lines[n]) for n in range(end, close_start)):
            fail("Comentario histórico canónico fuera del límite del Índice")
    if comment_zone == "legada":
        first, end = comment
        if any(n >= row_end for n in notes):
            fail("Nota histórica tras tabla incompatible con comentario legado")
        limit = incidents[0] if incidents else len(lines)
        if any(not blank(lines[n]) for n in range(closing + 1, first)) or any(not blank(lines[n]) for n in range(end, limit)):
            fail("Contenido no clasificable junto al comentario histórico legado")
    if comment and len([n for n in after if n < (incidents[0] if incidents else len(lines))]) != 1:
        fail("Más de un separador candidato al cierre histórico")
    kinds = ["titulo"] * len(lines)
    for n in range(r, idx): kinds[n] = "reglas"
    for n in range(idx, close_start): kinds[n] = "indice"
    for n in range(row_start, row_end): kinds[n] = "fila_indice"
    for n in range(close_start, closing + 1): kinds[n] = "cierre"
    for n in notes:
        boundary = presep if n < idx else close_start
        next_head = min((x for x, _, _ in atx if x > n and x < boundary), default=boundary)
        for j in range(n, next_head):
            if j not in fences and lines[j].startswith("|"):
                fail("Nota contiene fila")
            kinds[j] = "nota"
    if comment_zone == "canonica":
        for n in range(row_end, close_start): kinds[n] = "comentario"
    elif comment_zone == "legada":
        for n in range(closing + 1, incidents[0] if incidents else len(lines)): kinds[n] = "comentario"
    for n in range(0, closing + 1):
        if n in fences:
            continue
        if kinds[n] in KEEP and forbidden_preserved(lines[n]):
            fail("Historial oculto en cabecera: línea " + str(n + 1))
    for n in range(row_end, close_start):
        if kinds[n] == "indice" and not blank(lines[n]):
            fail("Texto no clasificable tras tabla")
    # Cada incidente empieza en su H2; antes solo hay blancos o separadores.
    if incidents:
        first_content = incidents[0] if comment_zone != "legada" else closing + 1
        if any(not blank(lines[n]) and lines[n] != "---\n" for n in range(closing + 1, first_content)):
            fail("Contenido antes del primer incidente")
        starts_inc = []
        for pos, h in enumerate(incidents):
            lower = (incidents[0] if comment_zone == "legada" else closing + 1) if pos == 0 else incidents[pos - 1] + 1
            start = h
            while start > lower and (blank(lines[start - 1]) or lines[start - 1] == "---\n"):
                start -= 1
            starts_inc.append(start)
        last = len(lines)
        while last > incidents[-1] + 1 and blank(lines[last - 1]):
            last -= 1
        for pos, start in enumerate(starts_inc):
            end = starts_inc[pos + 1] if pos + 1 < len(starts_inc) else last
            for n in range(start, end): kinds[n] = "incidente"
        for n in range(last, len(lines)): kinds[n] = "blancos_finales"
    else:
        if comment_zone != "legada" and any(not blank(line) for line in lines[closing + 1:]):
            fail("Contenido sustantivo después del cierre")
        if comment_zone != "legada":
            for n in range(closing + 1, len(lines)): kinds[n] = "blancos_finales"
    ranges = []
    n = 0
    while n < len(lines):
        kind = kinds[n]
        end = n + 1
        if kind == "incidente":
            end = next((x for x in starts_inc if x > n), last)
        elif kind == "nota":
            while end < len(lines) and kinds[end] == "nota" and end not in notes: end += 1
        else:
            while end < len(lines) and kinds[end] == kind: end += 1
        item = {"kind": kind, "start": starts[n], "end": starts[end]}
        if kind == "nota": item["basis"] = "nota-explicita"
        ranges.append(item)
        n = end
    return ranges, headings, incidents, row_start, row_end, closing, comment_zone


def checked_map(path, data, starts, headings, canonical):
    mapping = json.loads(path.read_text(encoding="utf-8"))
    if mapping.get("schema_version") != "registro-rangos/1" or mapping.get("snapshot_sha256") != digest(data) or mapping.get("size") != len(data):
        fail("Mapa inválido: otra instantánea")
    ranges = mapping.get("ranges")
    if not isinstance(ranges, list) or not ranges:
        fail("Mapa inválido: sin tramos")
    cursor = 0
    for item in ranges:
        if not isinstance(item, dict) or set(item) != ({"kind", "start", "end", "basis"} if item.get("kind") == "nota" else {"kind", "start", "end"}) or item.get("kind") not in KINDS or not all(type(item.get(k)) is int for k in ("start", "end")) or (item.get("kind") == "nota" and item.get("basis") != "nota-explicita"):
            fail("Mapa inválido: tramo mal formado")
        a, b = item["start"], item["end"]
        if a != cursor or b <= a or b not in starts:
            fail("Mapa inválido: hueco, solapamiento o límite fuera de línea")
        cursor = b
    if cursor != len(data): fail("Mapa inválido: incompleto")
    if mapping.get("headings") != headings:
        fail("Mapa inválido: H2 inventariados no coinciden")
    if ranges != canonical:
        for index, (actual, expected) in enumerate(zip(ranges, canonical)):
            if actual != expected:
                fail("Mapa inválido: tramo " + str(index + 1) + " esperado " + repr(expected) + ", recibido " + repr(actual))
        fail("Mapa inválido: cantidad de tramos esperada " + str(len(canonical)) + ", recibida " + str(len(ranges)))
    return mapping


def positive_candidate(candidate, source_lines):
    # Un segundo recorrido lee bytes sin llamar al clasificador del mapa o del constructor.
    data, lines, _ = read_source(candidate)
    def local_blank(line):
        return re.fullmatch(r"[ \t]*\n", line) is not None

    table_delimiter = re.compile(r"\|(?: *:?-{3,}:? *\|)+")
    field = re.compile(r"^[ \t]*(?:(?:>[ \t]*)|(?:[-*+][ \t]*)|(?:\d+[.)][ \t]*))*\*\*(?:" + "|".join(re.escape(x) for x in FIELDS) + r"): ?\*\*")
    incident_patterns = (
        re.compile(r"^## \d{2}/\d{2}/\d{4} \d{2}:\d{2}(?:[ \t].*)?$"),
        re.compile(r"^## \d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?(?:[ \t].*)?$"),
        re.compile(r"^## [0-9]+(?:[ .:–-].*)?$"),
        re.compile(r"^## Incidente [A-Za-z0-9][A-Za-z0-9_-]*(?:[ \t].*)?$"),
    )

    def exterior(seq):
        h2, atx, fenced, separators = [], [], set(), []
        marker = None
        previous = ""
        for n, line in enumerate(seq):
            body = line[:-1]
            fence_line = re.match(r"^[ \t]*(`{3,}|~{3,})", body)
            if marker:
                fenced.add(n)
                if fence_line and fence_line.group(1)[0] == marker[0]:
                    if body != marker:
                        fail("Cotejo positivo: cerca ambigua")
                    marker = None
                    previous = ""
                continue
            if fence_line:
                opening = fence_line.group(1)
                if body.startswith((" ", "\t")) or len(opening) != 3 or (opening[0] == "`" and "`" in body[3:]):
                    fail("Cotejo positivo: cerca ambigua")
                marker = opening
                fenced.add(n)
                continue
            if re.fullmatch(r"[ \t]*[-=]+[ \t]*", body) and (body != "---" or re.fullmatch(r"[ \t]*", previous) is None):
                fail("Cotejo positivo: separador o setext ambiguo")
            if body == "---": separators.append(n)
            if re.match(r"^[ \t]+#{1,6}[ \t]+", body):
                fail("Cotejo positivo: encabezado sangrado")
            found = re.fullmatch(r"(#{1,6})[ \t]+(.+)", body)
            if found:
                atx.append((n, len(found.group(1)), found.group(2)))
                if len(found.group(1)) == 2: h2.append((n, line))
            previous = body
        if marker: fail("Cotejo positivo: cerca sin cierre")
        return h2, atx, fenced, separators

    def provenance(seq, fenced):
        starts = [n for n, line in enumerate(seq) if n not in fenced and line.startswith("<!-- procedencia:")]
        if len(starts) > 1:
            fail("Cotejo positivo: comentario histórico duplicado")
        if not starts:
            return None
        start = starts[0]
        if start == 0 or not local_blank(seq[start - 1]):
            fail("Cotejo positivo: blanco anterior al comentario ausente")
        for n in range(start, len(seq)):
            body = seq[n][:-1]
            if (n in fenced or (n > start and "<!--" in body) or
                    (n == start and "<!--" in body[len("<!-- procedencia:"):]) or
                    re.match(r"^#{1,6}[ \t]+", body) or
                    re.fullmatch(r" {0,3}#{1,6}[ \t]*", body) or
                    re.match(r"^[ \t]*(`{3,}|~{3,})", body) or
                    re.fullmatch(r"[ \t]*[-=]+[ \t]*", body) or
                    re.fullmatch(r" {0,3}([*_-])(?:[ \t]*\1){2,}[ \t]*", body) or
                    field.match(body) or body.lstrip(" \t").startswith("|")):
                fail("Cotejo positivo: estructura dentro del comentario")
            if "-->" in body:
                if not body.endswith("-->") or body.count("-->") != 1:
                    fail("Cotejo positivo: cierre de comentario ambiguo")
                end = n + 1
                if end < len(seq) and not local_blank(seq[end]):
                    fail("Cotejo positivo: blanco posterior al comentario ausente")
                return start, end
        fail("Cotejo positivo: comentario sin cierre")

    h2, atx, fences, separators = exterior(lines)
    candidate_comment = provenance(lines, fences)
    if not data.endswith(b"\n---\n"):
        fail("Cotejo positivo: cierre no exacto")
    if not lines[0].startswith("# ") or [(n, level) for n, level, _ in atx if level == 1] != [(0, 1)]:
        fail("Cotejo positivo: título inválido")
    rules = [n for n, line in h2 if line == "## Reglas de este archivo\n"]
    indexes = [n for n, line in h2 if line == "## Índice\n"]
    if len(rules) != 1 or len(indexes) != 1 or not (0 < rules[0] < indexes[0]):
        fail("Cotejo positivo: anclas inválidas")
    r, idx = rules[0], indexes[0]
    pre = [n for n in separators if r < n < idx]
    post = [n for n in separators if n > idx]
    if len(pre) != 1 or post != [len(lines) - 1] or lines[-2] != "\n":
        fail("Cotejo positivo: separadores inválidos")
    if any(not local_blank(lines[n]) for n in range(pre[0] + 1, idx)):
        fail("Cotejo positivo: contenido entre separador e Índice")
    def note(line):
        return line == "## Nota histórica\n" or bool(re.fullmatch(r"## Nota: [^\n]+\n", line))
    notes = [n for n, line in h2 if note(line)]
    if any(n not in (r, idx) and n not in notes for n, _ in h2):
        fail("Cotejo positivo: H2 no permitido")
    if any(n < r for n in notes):
        fail("Cotejo positivo: nota fuera de zona")
    table = idx + 1
    while table < len(lines)-2 and local_blank(lines[table]): table += 1
    if (table + 1 >= len(lines)-2 or not lines[table].startswith("|")
            or not lines[table][:-1].endswith("|")
            or not table_delimiter.fullmatch(lines[table+1][:-1])):
        fail("Cotejo positivo: Índice inválido")
    if any(lines[n].lstrip().startswith("|") for n in range(table + 2, len(lines)) if n not in fences):
        fail("Cotejo positivo: fila heredada")
    if candidate_comment:
        first, end = candidate_comment
        if (first < table + 2 or end > len(lines) - 2 or
                any(n >= table + 2 for n in notes) or
                any(not local_blank(lines[n]) for n in range(table + 2, first)) or
                any(not local_blank(lines[n]) for n in range(end, len(lines) - 2))):
            fail("Cotejo positivo: comentario fuera de zona canónica")
    for n, line in enumerate(lines):
        if table+2 <= n < len(lines)-2 and not local_blank(line):
            inside_note = any(start <= n < min((x for x, _, _ in atx if x > start), default=len(lines)-2) for start in notes)
            inside_comment = candidate_comment and candidate_comment[0] <= n < candidate_comment[1]
            if not inside_note and not inside_comment: fail("Cotejo positivo: texto tras tabla")
        if n in fences: continue
        if field.match(line[:-1]):
            fail("Cotejo positivo: campo de incidente en línea " + str(n+1))
        visible = re.sub(r"^[ \t]*(?:(?:>[ \t]*)|(?:[-*+][ \t]*)|(?:\d+[.)][ \t]*))*", "", line[:-1])
        heading = re.match(r"^#{2,6}[ \t]+(.+)$", visible)
        if heading and (re.match(r"(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|Incidente\s+[A-Za-z0-9])", heading.group(1)) or visible != line[:-1]):
            fail("Cotejo positivo: encabezado de historial en línea " + str(n+1))
    # Reconstruye solo las dos eliminaciones autorizadas con un recorrido de fuente sin etiquetas.
    source_h2, _, source_fences, source_seps = exterior(source_lines)
    source_comment = provenance(source_lines, source_fences)
    source_rules = [n for n, line in source_h2 if line == "## Reglas de este archivo\n"]
    source_indexes = [n for n, line in source_h2 if line == "## Índice\n"]
    if len(source_rules) != 1 or len(source_indexes) != 1:
        fail("Cotejo positivo: anclas de fuente inválidas")
    source_idx = source_indexes[0]
    source_closings = [n for n in source_seps if n > source_idx]
    if not source_closings or source_lines[source_closings[0]-1] != "\n":
        fail("Cotejo positivo: cierre de fuente inválido")
    source_close = source_closings[0]
    source_first_incident = min((n for n, line in source_h2 if n > source_close), default=len(source_lines))
    source_zone = None
    if source_comment:
        first, end = source_comment
        if source_idx < first < source_close - 1:
            source_zone = "canonica"
        elif source_close < first and end <= source_first_incident:
            source_zone = "legada"
        else:
            fail("Cotejo positivo: comentario de fuente fuera de zona")
        if len([n for n in source_closings if n < source_first_incident]) != 1:
            fail("Cotejo positivo: cierres candidatos duplicados")
    source_notes = [n for n, line in source_h2 if note(line)]
    if any(n < source_rules[0] or n >= source_close for n in source_notes):
        fail("Cotejo positivo: nota de fuente fuera de cabecera")
    if len(source_notes) != len(notes):
        fail("Cotejo positivo: nota perdida")
    for n, line in source_h2:
        if n < source_close and n not in (source_rules[0], source_idx) + tuple(source_notes):
            fail("Cotejo positivo: H2 no clasificable en fuente")
        if n > source_close:
            date_shaped = re.match(r"^## [0-9]{4}-[0-9]{2}-[0-9]{2}", line[:-1])
            if ((date_shaped and not incident_patterns[1].fullmatch(line[:-1]))
                    or not any(pattern.fullmatch(line[:-1]) for pattern in incident_patterns)):
                fail("Cotejo positivo: sección posterior desconocida")
    source_table = source_idx + 1
    while source_table < source_close and local_blank(source_lines[source_table]): source_table += 1
    if (source_table + 1 >= source_close or not source_lines[source_table].startswith("|")
            or not source_lines[source_table][:-1].endswith("|")
            or not table_delimiter.fullmatch(source_lines[source_table+1][:-1])):
        fail("Cotejo positivo: tabla de fuente inválida")
    source_row_start = source_table + 2
    source_row_end = source_row_start
    while source_row_end < source_close and source_lines[source_row_end].startswith("|"):
        if not source_lines[source_row_end][:-1].endswith("|"):
            fail("Cotejo positivo: fila de fuente incompleta")
        source_row_end += 1
    if any(source_lines[n].lstrip().startswith("|") for n in range(source_row_end, source_close) if n not in source_fences):
        fail("Cotejo positivo: tabla de fuente discontinua")
    if source_zone == "canonica":
        first, end = source_comment
        if (first < source_row_end or any(n >= source_row_end for n in source_notes) or
                any(not local_blank(source_lines[n]) for n in range(source_row_end, first)) or
                any(not local_blank(source_lines[n]) for n in range(end, source_close - 1))):
            fail("Cotejo positivo: comentario de fuente fuera del Índice")
    elif source_zone == "legada":
        first, end = source_comment
        if (any(not local_blank(source_lines[n]) for n in range(source_close + 1, first)) or
                any(not local_blank(source_lines[n]) for n in range(end, source_first_incident))):
            fail("Cotejo positivo: contenido junto al comentario legado")
    if source_zone == "legada":
        preserved = (source_lines[:source_row_start] + source_lines[source_row_end:source_close-1] +
                     source_lines[source_close+1:source_first_incident] + source_lines[source_close-1:source_close+1])
    else:
        preserved = source_lines[:source_row_start] + source_lines[source_row_end:source_close+1]
    expected_from_source = "".join(preserved).encode("utf-8")
    if data != expected_from_source:
        fail("Cotejo positivo: bytes de cabecera, Índice o notas alterados")
    annotations = [(n, "nota-historica" if line == "## Nota histórica\n" else "nota-etiquetada")
                   for n, line in source_h2 if note(line)]
    if source_comment:
        annotations.append((source_comment[0], "comentario"))
    types = list(dict.fromkeys(kind for _, kind in sorted(annotations)))
    return data, {"presente": bool(types), "tipos": types}, source_zone


CHRONOLOGY = "Los registros van en **orden cronológico ascendente**."
DATE_ID = re.compile(r"(?:\d{2}/\d{2}/\d{4} \d{2}:\d{2}|\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?)\Z")


def dated_key(value):
    if not DATE_ID.fullmatch(value):
        fail("Retiro bloqueado para todo el registro: ID no fechado; requiere decisión humana")
    try:
        if "/" in value:
            parsed = datetime.strptime(value, "%d/%m/%Y %H:%M")
        elif len(value) == 10:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        else:
            parsed = datetime.strptime(value.replace("T", " "), "%Y-%m-%d %H:%M")
    except ValueError:
        fail("Retiro bloqueado para todo el registro: fecha de ID inválida; requiere decisión humana")
    return (parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute)


def ordered_dated(values, zone):
    keys = [dated_key(value) for value in values]
    if any(left >= right for left, right in zip(keys, keys[1:])):
        fail("Retiro bloqueado para todo el registro: IDs duplicados o desordenados en " + zone + "; requiere decisión humana")
    return keys


def retirement_source(path):
    if not path.is_absolute():
        fail("Registro de retiro no absoluto", 2)
    try:
        info = path.lstat()
    except OSError:
        fail("Registro de retiro ausente o ruta no accesible; corregir ruta antes de retirar")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        fail("Registro no regular, enlace simbólico o enlace duro; corregir ruta antes de retirar")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or
                    (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
                fail("Registro cambió de identidad durante la lectura")
            data = stream.read()
        after = path.lstat()
    except OSError:
        fail("Registro cambió de ruta o enlace durante la lectura")
    if (not stat.S_ISREG(after.st_mode) or after.st_nlink != 1 or
            (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)):
        fail("Registro cambió de identidad durante la lectura")
    if not data or not data.endswith(b"\n"):
        fail("Registro sin terminador de línea final")
    try:
        physical = [part + "\n" for part in data.decode("utf-8").split("\n")[:-1]]
    except UnicodeDecodeError:
        fail("Registro no es UTF-8 estricto")
    if any("\r" in (line[:-2] if line.endswith("\r\n") else line[:-1]) for line in physical):
        fail("Registro con terminador distinto de LF o CRLF")
    lines = [line[:-2] + "\n" if line.endswith("\r\n") else line for line in physical]
    starts = [0]
    for line in physical:
        starts.append(starts[-1] + len(line.encode("utf-8")))
    return data, lines, starts, info


def retirement_analysis(path):
    data, lines, starts, info = retirement_source(path)
    all_headings, _, fences, separators, _ = scan(lines, starts, retirement=True)
    index_headings = [h["line"] - 1 for h in all_headings if h["pattern"] == "indice"]
    if len(index_headings) != 1:
        fail("Retiro bloqueado para todo el registro: Índice ambiguo")
    closing_lines = [n for n in separators if n > index_headings[0]]
    if not closing_lines:
        fail("Retiro bloqueado para todo el registro: cierre ausente")
    first_body = next((h["line"] - 1 for h in all_headings if h["line"] - 1 > closing_lines[0]), None)
    if first_body is None:
        fail("Retiro bloqueado para todo el registro: no hay H2 con ID fechado")
    # La siembra interpreta la cabecera completa, pero el cuerpo retirado tiene otra gramática.
    _, headings, _, row_start, row_end, closing, comment_zone = classify(
        lines[:first_body], starts[:first_body + 1])
    if comment_zone == "legada" and historical_comment(lines[:first_body], {n for n in fences if n < first_body})[1] == first_body:
        fail("Comentario histórico sin blanco posterior")
    index = next(h["line"] - 1 for h in headings if h["pattern"] == "indice")
    chronological = [n for n in range(first_body) if n not in fences and lines[n][:-1] == CHRONOLOGY]
    if len(chronological) != 1 or chronological[0] >= index:
        fail("Falta o está fuera de cabecera el literal exacto '" + CHRONOLOGY +
             "'. Corregir la cabecera y pedir otra simulación; bloquea todo retiro, no solo anexos")
    rows = []
    for n in range(row_start, row_end):
        cell = lines[n].split("|", 2)[1].strip(" \t")
        if cell.startswith("`") and cell.endswith("`") and len(cell) > 1:
            cell = cell[1:-1]
        rows.append({"id": cell, "bytes": data[starts[n]:starts[n+1]]})
    ordered_dated([row["id"] for row in rows], "Índice")
    body_headings = [h for h in all_headings if h["line"] - 1 >= first_body]
    start_lines = []
    for pos, heading in enumerate(body_headings):
        n = heading["line"] - 1
        kind = heading["pattern"]
        if kind in ("reglas", "numerico", "incidente-id"):
            fail("Retiro bloqueado para todo el registro: H2 estructural o ID no fechado")
        if kind == "no-clasificado" and re.match(r"^##[ \t]+(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|\d+(?:[ .:–-]|$)|Incidente[ \t]+)", lines[n]):
            fail("Retiro bloqueado para todo el registro: ID no admisible")
        if pos == 0:
            start = n if comment_zone == "legada" else closing + 1
        else:
            previous = body_headings[pos - 1]["line"] - 1
            cursor = n - 1
            while cursor > previous and blank(lines[cursor]):
                cursor -= 1
            if cursor not in separators:
                fail("H2 ajeno sin separador estructural")
            earlier = cursor - 1
            while earlier > previous and blank(lines[earlier]):
                earlier -= 1
            if earlier in separators:
                fail("Separadores estructurales duplicados")
            start = cursor
            while start > previous + 1 and blank(lines[start - 1]):
                start -= 1
        start_lines.append(start)
    sections = []
    for pos, heading in enumerate(body_headings):
        n = heading["line"] - 1
        kind, value = incident_id(lines[n][:-1])
        value = value if kind in ("fecha-local", "iso") else None
        start = starts[start_lines[pos]]
        end = starts[start_lines[pos + 1]] if pos + 1 < len(start_lines) else len(data)
        prelude = data[start:starts[n]]
        sections.append({"id": value, "start": start, "end": end,
                         "heading": starts[n], "prelude": prelude, "bytes": data[start:end]})
    section_keys = ordered_dated([section["id"] for section in sections if section["id"] is not None], "secciones")
    if not section_keys:
        fail("Retiro bloqueado para todo el registro: no hay H2 con ID fechado")
    return {"data": data, "info": info, "lines": lines, "fences": fences, "rows": rows,
            "sections": sections,
            "row_start": starts[row_start], "row_end": starts[row_end],
            "header_end": sections[0]["start"]}


def retirement_candidate(analysis, ids):
    chosen = set(ids)
    sections = analysis["sections"]
    in_sections = [section["id"] for section in sections]
    if not chosen <= set(in_sections):
        fail("ID objetivo ausente, solo en Índice o repetido en secciones")
    data = analysis["data"]
    rows = analysis["rows"]
    head = data[:analysis["row_start"]] + b"".join(row["bytes"] for row in rows if row["id"] not in chosen)
    head += data[analysis["row_end"]:analysis["header_end"]]
    survivors = [section for section in sections if section["id"] not in chosen]
    if not survivors:
        return head
    if sections[0]["id"] in chosen:
        first = survivors[0]
        # El prefijo del primer incidente contiene el blanco tras el cierre; el del nuevo primero,
        # que antes era un separador intermedio, no debe duplicarlo.
        head += sections[0]["prelude"] + data[first["heading"]:first["end"]]
        survivors = survivors[1:]
    return head + b"".join(section["bytes"] for section in survivors)


def issue_heading_skill(analysis, section):
    first = analysis["data"][:section["heading"]].count(b"\n")
    end = analysis["data"][:section["end"]].count(b"\n")
    physical = [(analysis["lines"][n][:-1], n in analysis["fences"]) for n in range(first, end)]
    title = physical[0][0].split(section["id"], 1)[1].lstrip(" \t")
    if len(title) > 1 and title[0] in "—–-:" and title[1] in " \t":
        title = title[1:].lstrip(" \t")
    skill_lines = [re.match(r"^[ \t]*(?:[-*+][ \t]*)?\*\*Skill:\*\*[ \t]*(.*)$", line)
                   for line, fenced in physical[1:] if not fenced]
    skills = [match.group(1).strip(" \t`") for match in skill_lines if match]
    return title, skills, physical


def verify_reconciled_content(analysis, event, manifest):
    evidence_path = Path(event["datos"]["cotejo_ruta"])
    scratch = Path(manifest["unidad_ruta"]).parent
    if evidence_path.parent != scratch:
        fail("Cotejo de reconciliación fuera del scratch")
    evidence = read_json_regular(evidence_path)
    keys = {"schema_version", "modo", "ids", "identidad", "externo_ruta", "externo_sha256", "titulo"}
    if (not isinstance(evidence, dict) or set(evidence) != keys or
            evidence["schema_version"] != "reconciliacion-cotejo/1" or
            evidence["modo"] != manifest["modo"] or evidence["ids"] != event["ids"] or
            evidence["identidad"] != event["datos"]["identidad"] or
            not re.fullmatch(r"[0-9a-f]{64}", str(evidence["externo_sha256"]))):
        fail("Cotejo de reconciliación no vinculado al efecto y los IDs")
    outside = Path(evidence["externo_ruta"])
    if not outside.is_absolute():
        fail("Evidencia externa de reconciliación no absoluta")
    try:
        info = outside.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            fail("Evidencia externa de reconciliación enlazada")
        descriptor = os.open(outside, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            external = stream.read()
    except OSError:
        fail("Evidencia externa de reconciliación ilegible")
    if digest(external) != evidence["externo_sha256"]:
        fail("Evidencia externa de reconciliación cambió")
    selected = [section for section in analysis["sections"] if section["id"] in event["ids"]]
    if len(selected) != len(event["ids"]):
        fail("Cotejo post-efecto sin todos los incidentes seleccionados")
    if manifest["modo"] == "despachar":
        if evidence["titulo"] is not None:
            fail("Dossier original con título de issue ajeno")
        for section in selected:
            body = section["bytes"][section["heading"]-section["start"]:]
            if external.count(body) != 1:
                fail("Dossier original no conserva bytes verbatim del incidente: " + section["id"])
            offset = external.find(body)
            following = external[offset + len(body):]
            if ((offset > 0 and external[offset - 1] != 10) or
                    not re.match(rb"(?:\r?\n)*(?:---\r?\n(?:\r?\n)*)?(?:##[ \t]+|\Z)", following)):
                fail("Dossier original no conserva bytes verbatim del incidente: " + section["id"])
    else:
        if len(selected) != 1 or not isinstance(evidence["titulo"], str) or not evidence["titulo"].startswith("["):
            fail("Issue existente sin título y único ID acreditados")
        try:
            published = external.decode("utf-8")
        except UnicodeDecodeError:
            fail("Cotejo de issue no UTF-8")
        title, skills, source_lines = issue_heading_skill(analysis, selected[0])
        if (not title or len(skills) != 1 or not skills[0] or
                evidence["titulo"] != "[" + skills[0] + "] " + title):
            fail("Título de issue no corresponde al H2 original")
        published_lines = [line[:-1] if line.endswith("\r") else line for line in published.split("\n")]
        if (published_lines[0] != "**ID de registro:** `" + selected[0]["id"] + "`" or
                published_lines.count("---") < 2):
            fail("Issue existente sin ID, separadores o procedencia acreditados")
        first_separator = published_lines.index("---")
        last_separator = len(published_lines) - 1 - published_lines[::-1].index("---")
        footer = "\n".join(published_lines[last_separator + 1:])
        if ("Volcado desde el registro local `" + manifest["registro_ruta"] + "`" not in footer or
                "**Sin verificar contra el árbol**" not in footer):
            fail("Pie de procedencia fuera del final del issue existente")
        header_lines = published_lines[:first_separator]
        body_lines = published_lines[first_separator + 1:last_separator]
        published_fences = set()
        fence = None
        for n, line in enumerate(body_lines):
            fence_like = re.match(r"^[ \t]*(`{3,}|~{3,})", line)
            if fence is not None:
                published_fences.add(n)
                if fence_like and fence_like.group(1)[0] == fence[0]:
                    if line != fence:
                        fail("Cerca ambigua en el cuerpo del issue existente")
                    fence = None
            elif fence_like:
                marker = fence_like.group(1)
                if line.startswith((" ", "\t")) or len(marker) != 3 or (marker[0] == "`" and "`" in line[3:]):
                    fail("Cerca ambigua en el cuerpo del issue existente")
                fence = marker
                published_fences.add(n)
        if fence is not None:
            fail("Cerca sin cierre en el cuerpo del issue existente")
        body_exterior_counts = Counter(line for n, line in enumerate(body_lines) if n not in published_fences)
        fenced_blocks = []
        block = []
        for line, fenced in source_lines[1:]:
            if fenced:
                block.append(line)
            elif block:
                fenced_blocks.append(block)
                block = []
        if block:
            fenced_blocks.append(block)
        cursor = 0
        for block in fenced_blocks:
            match = next((n for n in range(cursor, len(body_lines) - len(block) + 1)
                          if body_lines[n:n + len(block)] == block and
                          all(i in published_fences for i in range(n, n + len(block)))), None)
            if match is None:
                fail("Bloque citado ausente del cuerpo verbatim del issue existente")
            cursor = match + len(block)
        for line, fenced in source_lines[1:]:
            if fenced or not line.strip(" \t") or line == "---":
                continue
            field = re.match(r"^[ \t]*(?:[-*+][ \t]*)?\*\*([^*]+):\*\*[ \t]*(.*)$", line)
            if field and field.group(1) in ISSUE_HEADER_FIELDS:
                label, value = field.groups()
                matches = [entry for entry in header_lines if entry.startswith("**" + label + ":**")]
                rendered = matches[0][len("**" + label + ":**"):].strip(" \t`") if len(matches) == 1 else ""
                source_value = value.strip(" \t`")
                related_date = (label == "Relacionado" and
                                re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", source_value))
                related_number = (related_date and
                                  re.fullmatch(re.escape(source_value) + r"`? \(#[0-9]+\)", rendered))
                related_tail = rendered[len(source_value):] if rendered.startswith(source_value) else ""
                if related_tail.startswith("`"):
                    related_tail = related_tail[1:]
                related_reason = (related_date and related_tail and not related_tail[0].isalnum() and
                                  any(char.isalpha() for char in related_tail))
                if len(matches) != 1 or (source_value and rendered != source_value and not related_number and not related_reason):
                    fail("Campo de issue perdido: " + label)
            elif not body_exterior_counts[line]:
                fail("Línea sustantiva ausente del cuerpo verbatim del issue existente")
            else:
                body_exterior_counts[line] -= 1


def retirement_signature(analysis):
    data = analysis["data"]
    sections = analysis["sections"]
    def core(chunk):
        physical = chunk.split(b"\n")
        while len(physical) > 1 and not physical[-1].strip(b" \t\r"):
            physical.pop()
        return b"\n".join(physical)
    return {"before_rows": digest(data[:analysis["row_start"]]),
            "after_rows": digest(data[analysis["row_end"]:analysis["header_end"]]),
            "rows": [digest(row["bytes"]) for row in analysis["rows"]],
            "sections_full": [digest(section["bytes"]) for section in sections],
            "sections_core": [digest(core(section["bytes"])) for section in sections],
            "section_ids": [section["id"] for section in sections]}


def compatible_with_root(current, root):
    original = retirement_analysis(Path(root["snapshot_path"]))
    if digest(original["data"]) != root["input_sha256"]:
        fail("Imagen raíz alterada", 11)
    before, now = retirement_signature(original), retirement_signature(current)
    if before["before_rows"] != now["before_rows"] or before["after_rows"] != now["after_rows"]:
        fail("Deriva de cabecera o límite de filas frente a la raíz", 11)
    for key in ("rows", "section_ids"):
        if now[key][:len(before[key])] != before[key]:
            fail("Deriva de fila, tramo tomado o límite frente a la raíz", 11)
    new_rows = current["rows"][len(original["rows"]):]
    new_sections = current["sections"][len(original["sections"]):]
    if not new_sections and current["data"] != original["data"]:
        fail("Bytes cambiados sin anexo posterior frente a la raíz", 11)
    if new_sections:
        count = len(original["sections"])
        if (now["sections_full"][:count-1] != before["sections_full"][:count-1] or
                now["sections_core"][count-1] != before["sections_core"][count-1]):
            fail("Tramo o separador previo cambiado frente a la raíz", 11)
    if any(row["id"] not in {section["id"] for section in new_sections} for row in new_rows):
        fail("Fila anexada sin su sección", 11)
    if any(section["id"] is None for section in new_sections):
        fail("Anexo ajeno no acreditado frente a la raíz", 11)


def retirement_receipt(scratch, payload):
    path = scratch / ("retiro-" + uuid4().hex + ".json")
    payload["recibo_ruta"] = str(path)
    write_json_exclusive(path, payload)
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return path


def read_private_bytes(path, scratch):
    if not path.is_absolute() or path.parent != scratch:
        fail("Imagen o candidato fuera del scratch")
    try:
        info = path.lstat()
    except OSError:
        fail("Imagen o candidato ausente")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        fail("Imagen o candidato no regular o enlazado")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or
                    (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
                fail("Imagen o candidato cambió durante lectura")
            return stream.read()
    except OSError:
        fail("Imagen o candidato no accesible sin seguir enlaces")


def retirement_semantic_guard(scratch, register, mode, ids, action, source_receipt=None):
    try:
        return action()
    except ValidationError as exc:
        if exc.code not in (10, 11, 12):
            raise
        if not scratch.is_absolute() or scratch.is_symlink() or not scratch.is_dir():
            raise
        manifest = read_json_regular(scratch / "manifiesto.json")
        payload = {"schema_version": "retiro-recibo/1", "modo": mode,
                   "status": "resimular" if exc.code == 10 else "deriva-detener" if exc.code == 11 else "estructura",
                   "registro_ruta": register, "registro_fisico": str(Path(register).resolve(strict=False)),
                   "ids": ids, "input_sha256": None, "unit_sha256": manifest["unit_sha256"],
                   "snapshot_path": None, "candidate_path": None, "backup_path": None,
                   "error": str(exc)}
        expected_mode = "simular-retiro" if mode in ("simular-retiro", "revalidar-retiro", "validar-publicacion") else "revalidar-retiro"
        if source_receipt is not None and source_receipt.is_absolute() and source_receipt.parent == scratch:
            try:
                source = read_json_regular(source_receipt)
            except (OSError, ValueError, UnicodeError, ValidationError):
                source = None
            if (isinstance(source, dict) and source.get("schema_version") == "retiro-recibo/1" and
                    source.get("modo") == expected_mode and source.get("status") == "ok" and
                    source.get("registro_ruta") == register and source.get("unit_sha256") == manifest["unit_sha256"] and
                    source.get("recibo_ruta") == str(source_receipt) and
                    isinstance(source.get("ids"), list) and source["ids"] and
                    all(isinstance(value, str) and value for value in source["ids"]) and
                    isinstance(source.get("input_sha256"), str) and
                    re.fullmatch(r"[0-9a-f]{64}", source["input_sha256"]) and
                    isinstance(source.get("candidate_sha256"), str) and
                    re.fullmatch(r"[0-9a-f]{64}", source["candidate_sha256"]) and
                    all(isinstance(source.get(key), str) and Path(source[key]).is_absolute() and
                        Path(source[key]).parent == scratch for key in ("snapshot_path", "candidate_path", "backup_path")) and
                    source["backup_path"] == source["snapshot_path"] and
                    (mode != "simular-retiro" or source.get("raiz_ruta") == str(source_receipt))):
                payload.update({key: source[key] for key in
                                ("ids", "input_sha256", "snapshot_path", "candidate_path", "candidate_sha256", "backup_path")})
                if mode == "simular-retiro":
                    payload["raiz_ruta"] = str(source_receipt)
                elif mode in ("revalidar-retiro", "validar-publicacion"):
                    payload["simulacion_ruta"] = str(source_receipt)
                else:
                    payload["revalidacion_ruta"] = str(source_receipt)
        payload.update(exc.payload)
        retirement_receipt(scratch, payload)
        print(str(exc), file=sys.stderr)
        raise SystemExit(exc.code)


def deadline_status(scratch, events, begin=False):
    path = scratch / "plazo-retiro.json"
    if not path.exists():
        if not begin:
            return {"status": "sin-iniciar", "plazo_ruta": str(path)}
        now = datetime.now(timezone.utc).replace(microsecond=0)
        payload = {"schema_version": "plazo-retiro/2", "inicio_utc": now.isoformat().replace("+00:00", "Z"),
                   "limite_utc": (now + timedelta(seconds=120)).isoformat().replace("+00:00", "Z"),
                   "inicio_monotonico_ns": time.monotonic_ns()}
        write_json_exclusive(path, payload)
    deadline = read_json_regular(path)
    if (not isinstance(deadline, dict) or set(deadline) != {"schema_version", "inicio_utc", "limite_utc", "inicio_monotonico_ns"} or
            deadline["schema_version"] != "plazo-retiro/2" or
            type(deadline["inicio_monotonico_ns"]) is not int or deadline["inicio_monotonico_ns"] < 0):
        fail("Sello de plazo inválido")
    try:
        started = datetime.fromisoformat(deadline["inicio_utc"].replace("Z", "+00:00"))
        original_end = datetime.fromisoformat(deadline["limite_utc"].replace("Z", "+00:00"))
        windows = [entry for entry in events if entry["tipo"] == "ventana-plazo-aprobada"]
        end = datetime.fromisoformat((windows[-1]["datos"]["plazo_nuevo"] if windows else deadline["limite_utc"]).replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        fail("Sello de plazo inválido")
    if (started.utcoffset() != timedelta(0) or original_end.utcoffset() != timedelta(0) or
            end.utcoffset() != timedelta(0) or original_end - started != timedelta(seconds=120)):
        fail("Sello de plazo fuera de contrato")
    monotonic_elapsed_ns = time.monotonic_ns() - deadline["inicio_monotonico_ns"]
    now = datetime.now(timezone.utc)
    wall_elapsed = now - started
    wall_elapsed_ns = ((wall_elapsed.days * 86400 + wall_elapsed.seconds) * 1_000_000 + wall_elapsed.microseconds) * 1000
    rollback = monotonic_elapsed_ns < 0 or wall_elapsed_ns < monotonic_elapsed_ns
    motivo = "reloj-retrocedido" if rollback else "plazo-vencido" if now >= end else None
    return {"status": "tiempo-agotado" if motivo else "vigente", "motivo": motivo,
            "plazo_ruta": str(path), "inicio_utc": deadline["inicio_utc"],
            "limite_utc": end.isoformat().replace("+00:00", "Z")}


def retirement_chain(path, scratch, register, manifest):
    if not path.is_absolute() or path.parent != scratch:
        fail("Recibo de retiro fuera del scratch")
    receipt = read_json_regular(path)
    if (receipt.get("schema_version") != "retiro-recibo/1" or
            receipt.get("registro_ruta") != register or
            receipt.get("unit_sha256") != manifest["unit_sha256"] or
            receipt.get("recibo_ruta") != str(path) or
            receipt.get("modo") != "simular-retiro" or
            receipt.get("status") != "ok"):
        fail("Recibo de simulación no pertenece a esta vuelta")
    root_path = Path(receipt.get("raiz_ruta", ""))
    if not root_path.is_absolute() or root_path.parent != scratch:
        fail("Raíz de retiro fuera del scratch")
    root = receipt if root_path == path else read_json_regular(root_path)
    if (root.get("raiz_ruta") != str(root_path) or root.get("recibo_ruta") != str(root_path) or
            root.get("ids") != receipt.get("ids") or root.get("schema_version") != "retiro-recibo/1"):
        fail("Cadena de simulación desvinculada")
    for entry in (root, receipt):
        image = Path(entry.get("snapshot_path", ""))
        candidate = Path(entry.get("candidate_path", ""))
        if (digest(read_private_bytes(image, scratch)) != entry.get("input_sha256") or
                digest(read_private_bytes(candidate, scratch)) != entry.get("candidate_sha256")):
            fail("Imagen o candidato de simulación alterado", 11)
    return receipt, root


def validate_publication(register, scratch, simulation_path):
    manifest, events = validate_round(scratch, register)
    if manifest["modo"] != "volcar" or manifest["registro_kind"] != "archivo":
        fail("Validar publicación exige una vuelta de volcado sobre archivo", 2)
    if any(event["tipo"] in ("efecto-acreditado", "rechazo-aprobado", "reconciliacion-aprobada") for event in events):
        fail("Publicación solicitada después de un efecto o rechazo")
    simulation, root = retirement_chain(simulation_path, scratch, register, manifest)
    ids = simulation["ids"]
    latest = next((event for event in reversed(events) if event["tipo"] == "ids-definitivos"), None)
    if (len(ids) != 1 or root.get("raiz_tipo") != "nuevo" or latest is None or latest["ids"] != ids or
            simulation.get("evento_ids_ruta") != str(scratch / f"evento-{latest['secuencia']:06d}-ids-definitivos.json")):
        fail("Publicación sin simulación previa vigente de un único ID")
    current, _, _, info = retirement_source(Path(register))
    if digest(current) != simulation["input_sha256"] or [info.st_dev, info.st_ino] != simulation["identidad"]:
        fail("Registro cambió desde la simulación; resimular antes de publicar", 10)
    analysis = retirement_analysis(Path(simulation["snapshot_path"]))
    selected = [section for section in analysis["sections"] if section["id"] == ids[0]]
    if len(selected) != 1:
        fail("Volcado exige un solo incidente por issue")
    title, skills, _ = issue_heading_skill(analysis, selected[0])
    if not title or len(skills) != 1 or not skills[0]:
        fail("Volcado sin un campo Skill único y no vacío: detener antes de publicar y pedir decisión humana")
    print(json.dumps({"status": "ok", "ids": ids, "titulo": title, "skill": skills[0],
                      "simulacion_ruta": str(simulation_path), "unit_sha256": manifest["unit_sha256"]},
                     ensure_ascii=True, sort_keys=True))


def retirement_simulation(register, scratch, root_arg, ids):
    manifest, events = validate_round(scratch, register)
    deadline = deadline_status(scratch, events)
    if deadline["status"] == "tiempo-agotado":
        print(json.dumps(deadline, ensure_ascii=True))
        print("Plazo de retiro agotado o reloj retrocedido", file=sys.stderr)
        raise SystemExit(3)
    if manifest["registro_kind"] != "archivo" or len(set(ids)) != len(ids):
        fail("Retiro exige registro de archivo e IDs únicos", 2)
    latest = next((event for event in reversed(events) if event["tipo"] == "ids-definitivos"), None)
    if latest is None or latest["ids"] != ids:
        fail("IDs de simulación sin evento definitivo de esta vuelta")
    latest_path = str(scratch / f"evento-{latest['secuencia']:06d}-ids-definitivos.json")
    effect = next((event for event in events if event["tipo"] in ("efecto-acreditado", "rechazo-aprobado")), None)
    reconciliation = next((event for event in events if event["tipo"] == "reconciliacion-aprobada"), None)
    if root_arg == "nuevo":
        if effect or reconciliation:
            fail("Raíz anterior al efecto solicitada después del efecto")
        root = None
    elif root_arg == "nuevo-post-efecto":
        if not reconciliation or effect or reconciliation["ids"] != ids:
            fail("Raíz post-efecto sin reconciliación aprobada enlazada")
        root = None
    else:
        previous, root = retirement_chain(Path(root_arg), scratch, register, manifest)
        if previous is not root or root["ids"] != ids:
            fail("Resimulación exige recibo raíz e IDs idénticos", 2)
        if root["evento_ids_ruta"] != str(scratch / f"evento-{latest['secuencia']:06d}-ids-definitivos.json"):
            fail("Raíz sustituida por evento de IDs posterior")
    if root is None:
        for path in scratch.glob("retiro-*.json"):
            prior = read_json_regular(path)
            if (prior.get("modo") == "simular-retiro" and prior.get("status") == "ok" and
                    prior.get("raiz_ruta") == str(path) and prior.get("evento_ids_ruta") == latest_path):
                fail("Ya existe primera raíz para estos IDs; resimular desde ella o iniciar otra vuelta")
    try:
        current = retirement_analysis(Path(register))
    except ValidationError as exc:
        if root is not None and (effect or reconciliation) and exc.code == 12 and "enlace" not in str(exc):
            fail("Deriva estructural posterior al efecto: " + str(exc), 11)
        raise
    if root is not None:
        compatible_with_root(current, root)
    if root_arg == "nuevo-post-efecto":
        verify_reconciled_content(current, reconciliation, manifest)
    candidate = retirement_candidate(current, ids)
    token = uuid4().hex
    image_path = scratch / ("imagen-" + token)
    candidate_path = scratch / ("candidato-" + token)
    with image_path.open("xb") as stream:
        stream.write(current["data"])
    with candidate_path.open("xb") as stream:
        stream.write(candidate)
    receipt_path = scratch / ("retiro-" + token + ".json")
    root_path = receipt_path if root is None else Path(root["recibo_ruta"])
    payload = {"schema_version": "retiro-recibo/1", "modo": "simular-retiro", "status": "ok",
               "registro_ruta": register, "registro_fisico": str(Path(register).resolve(strict=False)),
               "ids": ids, "input_sha256": digest(current["data"]),
               "unit_sha256": manifest["unit_sha256"], "snapshot_path": str(image_path),
               "candidate_path": str(candidate_path), "candidate_sha256": digest(candidate),
               "backup_path": str(image_path), "raiz_ruta": str(root_path),
               "recibo_ruta": str(receipt_path), "raiz_tipo": root_arg if root is None else root["raiz_tipo"],
               "evento_ids_ruta": str(scratch / f"evento-{latest['secuencia']:06d}-ids-definitivos.json"),
               "evento_efecto_ruta": None if not (effect or reconciliation) else str(scratch / f"evento-{(effect or reconciliation)['secuencia']:06d}-{(effect or reconciliation)['tipo']}.json"),
               "identidad": [current["info"].st_dev, current["info"].st_ino]}
    write_json_exclusive(receipt_path, payload)
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def retirement_revalidation(register, scratch, simulation_path):
    manifest, events = validate_round(scratch, register)
    simulation, root = retirement_chain(simulation_path, scratch, register, manifest)
    effect = next((event for event in events if event["tipo"] in ("efecto-acreditado", "rechazo-aprobado", "reconciliacion-aprobada")), None)
    latest = next((event for event in reversed(events) if event["tipo"] == "ids-definitivos"), None)
    if (latest is None or effect is None or effect["ids"] != root["ids"] or
            root["evento_ids_ruta"] != str(scratch / f"evento-{latest['secuencia']:06d}-ids-definitivos.json")):
        fail("Revalidación con IDs o efecto no vinculados a la primera raíz")
    expected_effect = str(scratch / f"evento-{effect['secuencia']:06d}-{effect['tipo']}.json")
    if simulation is not root and simulation["evento_efecto_ruta"] not in (None, expected_effect):
        fail("Simulación no enlazada al efecto")
    deadline = deadline_status(scratch, events, begin=True)
    if deadline["status"] == "tiempo-agotado":
        print(json.dumps(deadline, ensure_ascii=True))
        print("Plazo de retiro agotado o reloj retrocedido", file=sys.stderr)
        raise SystemExit(3)
    try:
        current = retirement_analysis(Path(register))
        compatible_with_root(current, root)
        if root["raiz_tipo"] == "nuevo-post-efecto":
            verify_reconciled_content(current, effect, manifest)
        same_bytes = current["data"] == read_private_bytes(Path(simulation["snapshot_path"]), scratch)
        same_identity = [current["info"].st_dev, current["info"].st_ino] == simulation["identidad"]
        code, status = (0, "ok") if same_bytes and same_identity else (10, "resimular")
        error = None
    except ValidationError as exc:
        code = 12 if "enlace" in str(exc) or "no regular" in str(exc) else 11
        status, error = "estructura" if code == 12 else "deriva-detener", str(exc)
    payload = {"schema_version": "retiro-recibo/1", "modo": "revalidar-retiro", "status": status,
               "registro_ruta": register, "registro_fisico": str(Path(register).resolve(strict=False)),
               "ids": simulation["ids"], "input_sha256": simulation["input_sha256"],
               "unit_sha256": manifest["unit_sha256"], "snapshot_path": simulation["snapshot_path"],
               "candidate_path": simulation["candidate_path"], "candidate_sha256": simulation["candidate_sha256"],
               "backup_path": simulation["snapshot_path"], "simulacion_ruta": str(simulation_path),
               "raiz_ruta": root["recibo_ruta"], "identidad": simulation["identidad"]}
    if error:
        payload["error"] = error
    retirement_receipt(scratch, payload)
    if code:
        print(error or "Identidad o bytes de origen cambiaron: resimular", file=sys.stderr)
        raise SystemExit(code)


def checked_revalidation(path, scratch, register, manifest):
    if not path.is_absolute() or path.parent != scratch:
        fail("Recibo de revalidación fuera del scratch")
    check = read_json_regular(path)
    if (check.get("schema_version") != "retiro-recibo/1" or check.get("modo") != "revalidar-retiro" or
            check.get("status") != "ok" or check.get("recibo_ruta") != str(path) or
            check.get("registro_ruta") != register or check.get("unit_sha256") != manifest["unit_sha256"]):
        fail("Recibo de revalidación no acreditado")
    simulation, root = retirement_chain(Path(check.get("simulacion_ruta", "")), scratch, register, manifest)
    for key in ("ids", "input_sha256", "snapshot_path", "candidate_path", "candidate_sha256", "identidad"):
        if check.get(key) != simulation.get(key):
            fail("Revalidación desvinculada de simulación")
    if check.get("raiz_ruta") != root["recibo_ruta"]:
        fail("Revalidación desvinculada de raíz")
    return check, simulation, root


def retirement_write(register, scratch, revalidation_path):
    manifest, events = validate_round(scratch, register)
    check, simulation, _ = checked_revalidation(revalidation_path, scratch, register, manifest)
    deadline = deadline_status(scratch, events)
    if deadline["status"] != "vigente":
        print(json.dumps(deadline, ensure_ascii=True))
        print("Plazo de retiro no vigente: " + deadline["status"], file=sys.stderr)
        raise SystemExit(3)
    try:
        data, _, _, info = retirement_source(Path(register))
    except ValidationError:
        retirement_revalidation(register, scratch, Path(simulation["recibo_ruta"]))
        fail("Revalidación contradictoria tras cambio de ruta", 3)
    if data != read_private_bytes(Path(simulation["snapshot_path"]), scratch) or [info.st_dev, info.st_ino] != check["identidad"]:
        retirement_revalidation(register, scratch, Path(simulation["recibo_ruta"]))
        fail("Revalidación contradictoria tras cambio de origen", 3)
    candidate = read_private_bytes(Path(check["candidate_path"]), scratch)
    if digest(candidate) != check["candidate_sha256"]:
        fail("Candidato sellado alterado", 11,
             {"ids": check["ids"], "snapshot_path": check["snapshot_path"],
              "candidate_path": check["candidate_path"], "candidate_sha256": check["candidate_sha256"],
              "backup_path": check["snapshot_path"]})
    fd, temporary = tempfile.mkstemp(prefix=".registro-retiro-", dir=str(Path(register).parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(candidate)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(info.st_mode))
        os.replace(temporary, register)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    payload = {"schema_version": "retiro-recibo/1", "modo": "escribir-retiro", "status": "pendiente-cotejo",
               "registro_ruta": register, "registro_fisico": str(Path(register).resolve(strict=False)),
               "ids": check["ids"], "input_sha256": check["input_sha256"],
               "unit_sha256": manifest["unit_sha256"], "snapshot_path": check["snapshot_path"],
               "candidate_path": check["candidate_path"], "candidate_sha256": check["candidate_sha256"],
               "backup_path": check["snapshot_path"], "revalidacion_ruta": str(revalidation_path),
               "output_sha256": digest(candidate)}
    retirement_receipt(scratch, payload)


def independent_retirement_expected(image, ids):
    try:
        text = image.decode("utf-8")
    except UnicodeDecodeError:
        fail("Cotejo: imagen no UTF-8", 11)
    physical = [part + "\n" for part in text.split("\n")[:-1]]
    if not image.endswith(b"\n"):
        fail("Cotejo: imagen sin final físico", 11)
    bodies = [line[:-2] if line.endswith("\r\n") else line[:-1] for line in physical]
    offsets = [0]
    for line in physical:
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    outside = []
    fence = None
    for n, body in enumerate(bodies):
        marker = re.match(r"^(`{3}|~{3})", body)
        if fence is None:
            outside.append(n)
            if marker:
                fence = marker.group(1)
        elif body == fence:
            fence = None
    if fence:
        fail("Cotejo: cerca sin cierre", 11)
    indexes = [n for n in outside if bodies[n] == "## Índice"]
    if len(indexes) != 1:
        fail("Cotejo: Índice ambiguo", 11)
    index = indexes[0]
    closings = [n for n in outside if n > index and bodies[n] == "---"]
    if not closings:
        fail("Cotejo: cierre ausente", 11)
    closing = closings[0]
    table = next((n for n in range(index+1, closing) if bodies[n].startswith("|")), None)
    if table is None or table + 1 >= closing:
        fail("Cotejo: tabla ausente", 11)
    row_start = table + 2
    row_end = row_start
    while row_end < closing and bodies[row_end].startswith("|"):
        row_end += 1
    rows = []
    for n in range(row_start, row_end):
        cell = bodies[n].split("|", 2)[1].strip(" \t")
        if cell.startswith("`") and cell.endswith("`"):
            cell = cell[1:-1]
        rows.append((cell, image[offsets[n]:offsets[n+1]]))
    headings = []
    for n in outside:
        if n > closing and re.match(r"^##[ \t]+", bodies[n]):
            match = re.fullmatch(
                r"## ((?:[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2})|"
                r"(?:[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[ T][0-9]{2}:[0-9]{2})?))(?:[ \t].*)?",
                bodies[n])
            if match is None:
                if re.match(r"##[ \t]+(?:[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]+(?:[ .:–-]|$)|Incidente[ \t]+)", bodies[n]):
                    fail("Cotejo: H2 sin ID fechado admisible", 11)
                headings.append((n, None))
            else:
                headings.append((n, match.group(1)))
    if not any(ident is not None for _, ident in headings):
        fail("Cotejo: sección fechada ausente", 11)
    legacy = any(bodies[n].startswith("<!-- procedencia:") for n in range(closing+1, headings[0][0]))
    if legacy and bodies[headings[0][0]-1].strip(" \t"):
        fail("Cotejo: comentario histórico sin blanco posterior", 11)
    sections = []
    for pos, (n, ident) in enumerate(headings):
        if pos == 0:
            start = n if legacy else closing + 1
        else:
            cursor = n - 1
            while cursor > headings[pos-1][0] and not bodies[cursor].strip(" \t"):
                cursor -= 1
            if bodies[cursor] != "---" or bodies[cursor-1].strip(" \t"):
                fail("Cotejo: separador anterior ausente", 11)
            earlier = cursor - 1
            while earlier > headings[pos-1][0] and not bodies[earlier].strip(" \t"):
                earlier -= 1
            if bodies[earlier] == "---" and not bodies[earlier-1].strip(" \t"):
                fail("Cotejo: separadores estructurales duplicados", 11)
            start = cursor
            while start > headings[pos-1][0] + 1 and not bodies[start-1].strip(" \t"):
                start -= 1
        end = len(image) if pos == len(headings)-1 else None
        sections.append({"id": ident, "start": offsets[start], "heading": offsets[n], "end": end})
    for pos in range(len(sections)-1):
        sections[pos]["end"] = sections[pos+1]["start"]
    prefix = image[:offsets[row_start]] + b"".join(raw for ident, raw in rows if ident not in ids)
    prefix += image[offsets[row_end]:sections[0]["start"]]
    kept = [section for section in sections if section["id"] not in ids]
    if not kept:
        return prefix
    if sections[0]["id"] in ids:
        first = kept.pop(0)
        prefix += image[sections[0]["start"]:sections[0]["heading"]]
        prefix += image[first["heading"]:first["end"]]
    return prefix + b"".join(image[section["start"]:section["end"]] for section in kept)


def retirement_check(register, scratch, revalidation_path, result_path):
    manifest, _ = validate_round(scratch, register)
    check, _, _ = checked_revalidation(revalidation_path, scratch, register, manifest)
    if not result_path.is_absolute() or result_path.parent != scratch:
        fail("Resultado de escritura fuera del scratch")
    result = read_json_regular(result_path)
    if (result.get("schema_version") != "retiro-recibo/1" or result.get("modo") != "escribir-retiro" or
            result.get("revalidacion_ruta") != str(revalidation_path) or
            result.get("recibo_ruta") != str(result_path) or result.get("ids") != check["ids"] or
            result.get("backup_path") != check["snapshot_path"]):
        fail("Resultado de escritura no vinculado")
    expected = independent_retirement_expected(read_private_bytes(Path(check["snapshot_path"]), scratch), check["ids"])
    current, _, _, _ = retirement_source(Path(register))
    if current != expected or result.get("output_sha256") != digest(current):
        fail("Cotejo independiente: bytes, filas, secciones o separadores difieren", 11,
             {"ids": check["ids"], "snapshot_path": check["snapshot_path"],
              "candidate_path": check["candidate_path"], "candidate_sha256": check["candidate_sha256"],
              "backup_path": check["snapshot_path"], "resultado_ruta": str(result_path)})
    payload = {"schema_version": "retiro-recibo/1", "modo": "cotejar-retiro", "status": "acreditado",
               "registro_ruta": register, "registro_fisico": str(Path(register).resolve(strict=False)),
               "ids": check["ids"], "input_sha256": check["input_sha256"],
               "unit_sha256": manifest["unit_sha256"], "snapshot_path": check["snapshot_path"],
               "candidate_path": check["candidate_path"], "candidate_sha256": check["candidate_sha256"],
               "backup_path": check["snapshot_path"], "resultado_ruta": str(result_path),
               "output_sha256": digest(current)}
    retirement_receipt(scratch, payload)


def extract_installed_unit(path):
    source = path.read_text(encoding="utf-8")
    start = "\n<!-- registro-candidato:inicio -->\n"
    end = "\n<!-- registro-candidato:fin -->"
    if source.count(start) != 1 or source.count(end) != 1:
        fail("Marcadores de unidad instalada ambiguos")
    block = source.split(start, 1)[1].split(end, 1)[0]
    if block.count("```python\n") != 1 or block.count("\n```") != 1:
        fail("Cerca de unidad instalada ambigua")
    return (block.split("```python\n", 1)[1].rsplit("\n```", 1)[0] + "\n").encode("utf-8")


def run():
    if len(sys.argv) < 3: fail("Uso: modo <rutas/argumentos>", 2)
    mode = sys.argv[1]
    if mode == "preparar-vuelta" and len(sys.argv) == 4:
        register, intake_mode = sys.argv[2:4]
        if (intake_mode not in ("despachar", "volcar") or
                (register != "issues" and not Path(register).is_absolute()) or
                (register == "issues" and intake_mode != "despachar")):
            fail("Registro o modo de vuelta inválido", 2)
        unit_bytes = globals().get("FROZEN_UNIT")
        if not isinstance(unit_bytes, bytes) or not unit_bytes:
            fail("Preparar vuelta exige bytes de unidad ejecutada", 2)
        scratch = Path(tempfile.mkdtemp(prefix="registro-vuelta-")).resolve(strict=True)
        unit = scratch / "unidad.py"
        with unit.open("xb") as stream:
            stream.write(unit_bytes)
        manifest = {"schema_version": "scratch-vuelta/1", "vuelta_id": uuid4().hex,
                    "modo": intake_mode, "registro_ruta": register,
                    "registro_fisico": register if register == "issues" else str(Path(register).resolve(strict=False)),
                    "registro_kind": "issues" if register == "issues" else "archivo",
                    "unit_sha256": digest(unit_bytes), "unidad_ruta": str(unit), "creado_utc": utc_now()}
        write_json_exclusive(scratch / "manifiesto.json", manifest)
        print(json.dumps({"scratch": str(scratch), "unidad_ruta": str(unit), "unit_sha256": manifest["unit_sha256"], "vuelta_id": manifest["vuelta_id"]}, ensure_ascii=True))
    elif mode == "validar-vuelta" and len(sys.argv) == 4:
        manifest, events = validate_round(Path(sys.argv[2]), sys.argv[3])
        print(json.dumps({"status": "ok", "vuelta_id": manifest["vuelta_id"], "unit_sha256": manifest["unit_sha256"], "registro_kind": manifest["registro_kind"], "eventos": events}, ensure_ascii=True))
    elif mode == "registrar-evento" and len(sys.argv) == 7:
        scratch, register, kind = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
        manifest, previous = validate_round(scratch, register)
        ids = json.loads(sys.argv[5])
        data = json.loads(sys.argv[6])
        event = {"schema_version": 1, "secuencia": len(previous) + 1, "tipo": kind,
                 "vuelta_id": manifest["vuelta_id"], "instante_utc": utc_now(), "ids": ids, "datos": data}
        validate_event(previous, event, manifest)
        path = scratch / f"evento-{event['secuencia']:06d}-{kind}.json"
        sha = write_json_exclusive(path, event)
        print(json.dumps({"status": "ok", "evento_ruta": str(path), "evento_sha256": sha, "secuencia": event["secuencia"]}, ensure_ascii=True))
    elif mode == "comparar-unidad" and len(sys.argv) == 5:
        manifest, _ = validate_round(Path(sys.argv[2]), sys.argv[3])
        installed_sha = digest(extract_installed_unit(Path(sys.argv[4])))
        print(json.dumps({"unit_sha256": manifest["unit_sha256"], "installed_sha256": installed_sha,
                          "instalada_coincide": installed_sha == manifest["unit_sha256"]}, ensure_ascii=True))
    elif mode == "preparar-cotejo" and len(sys.argv) == 5:
        scratch, register = Path(sys.argv[2]), sys.argv[3]
        manifest, events = validate_round(scratch, register)
        try:
            request = json.loads(base64.b64decode(sys.argv[4], validate=True).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            fail("Solicitud de cotejo inválida", 2)
        keys = {"ids", "identidad", "externo_ruta", "titulo"}
        latest_ids = next((entry["ids"] for entry in reversed(events) if entry["tipo"] == "ids-definitivos"), None)
        if (not isinstance(request, dict) or set(request) != keys or latest_ids is None or
                request["ids"] != latest_ids or
                not isinstance(request["identidad"], str) or not request["identidad"] or
                not isinstance(request["externo_ruta"], str) or
                (manifest["modo"] == "despachar" and request["titulo"] is not None) or
                (manifest["modo"] == "volcar" and
                 (not isinstance(request["titulo"], str) or not request["titulo"].startswith("["))) or
                any(entry["tipo"] in ("efecto-acreditado", "rechazo-aprobado", "reconciliacion-aprobada") for entry in events)):
            fail("Cotejo sin IDs definitivos, identidad o título acreditados")
        outside = Path(request["externo_ruta"])
        if not outside.is_absolute():
            fail("Evidencia externa de reconciliación no absoluta")
        try:
            info = outside.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                fail("Evidencia externa de reconciliación enlazada")
            descriptor = os.open(outside, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(descriptor, "rb") as stream:
                external = stream.read()
        except OSError:
            fail("Evidencia externa de reconciliación ilegible")
        payload = {"schema_version": "reconciliacion-cotejo/1", "modo": manifest["modo"],
                   "ids": request["ids"], "identidad": request["identidad"],
                   "externo_ruta": str(outside), "externo_sha256": digest(external), "titulo": request["titulo"]}
        path = scratch / ("reconciliacion-cotejo-" + uuid4().hex + ".json")
        sha = write_json_exclusive(path, payload)
        print(json.dumps({"cotejo_ruta": str(path), "cotejo_sha256": sha,
                          "externo_sha256": payload["externo_sha256"]}, ensure_ascii=True))
    elif mode == "simular-retiro" and len(sys.argv) >= 6:
        register, scratch, root_arg = sys.argv[2], Path(sys.argv[3]), sys.argv[4]
        retirement_semantic_guard(scratch, register, mode, sys.argv[5:],
                                  lambda: retirement_simulation(register, scratch, root_arg, sys.argv[5:]),
                                  None if root_arg in ("nuevo", "nuevo-post-efecto") else Path(root_arg))
    elif mode == "validar-publicacion" and len(sys.argv) == 5:
        register, scratch, simulation = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
        retirement_semantic_guard(scratch, register, mode, [],
                                  lambda: validate_publication(register, scratch, simulation), simulation)
    elif mode == "plazo-retiro" and len(sys.argv) == 4:
        register, scratch = sys.argv[2], Path(sys.argv[3])
        _, events = validate_round(scratch, register)
        print(json.dumps(deadline_status(scratch, events), ensure_ascii=True))
    elif mode == "revalidar-retiro" and len(sys.argv) == 5:
        register, scratch, simulation = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
        retirement_semantic_guard(scratch, register, mode, [],
                                  lambda: retirement_revalidation(register, scratch, simulation), simulation)
    elif mode == "escribir-retiro" and len(sys.argv) == 5:
        register, scratch, check = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
        retirement_semantic_guard(scratch, register, mode, [],
                                  lambda: retirement_write(register, scratch, check), check)
    elif mode == "cotejar-retiro" and len(sys.argv) == 6:
        register, scratch, check, result = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
        retirement_semantic_guard(scratch, register, mode, [],
                                  lambda: retirement_check(register, scratch, check, result), check)
    elif mode == "inventariar" and len(sys.argv) == 5:
        snapshot, inventory, worktree = map(Path, sys.argv[2:5])
        root = worktree.resolve(strict=True)
        for p in (snapshot, inventory): private(p, root)
        data, lines, starts = read_source(snapshot)
        headings, _, fences, separators, fence_spans = scan(lines, starts)
        comment = historical_comment(lines, fences)
        payload = {
            "schema_version": "registro-inventario/1",
            "snapshot_sha256": digest(data),
            "size": len(data),
            "lines": [{"number": n + 1, "start": starts[n], "end": starts[n + 1]} for n in range(len(lines))],
            "headings": [{**h, "text": lines[h["line"] - 1][3:-1]} for h in headings],
            "rows": [{"line": n + 1, "start": starts[n], "end": starts[n + 1], "text": line[:-1]}
                     for n, line in enumerate(lines) if n not in fences and line.lstrip().startswith("|")],
            "separators": [{"line": n + 1, "start": starts[n], "end": starts[n + 1]} for n in separators],
            "fences": fence_spans,
            "comment": None if comment is None else {"line_start": comment[0] + 1, "line_end_exclusive": comment[1] + 1},
        }
        with inventory.open("xb") as f: f.write((json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        print(json.dumps({"snapshot_sha256": digest(data), "size": len(data), "line_count": len(lines), "headings": payload["headings"], "rows": len(payload["rows"]), "separators": len(separators), "fences": len(fence_spans), "comment": payload["comment"]}, ensure_ascii=True))
    elif mode == "mapear" and len(sys.argv) >= 6:
        inventory, map_path, worktree = map(Path, sys.argv[2:5])
        root = worktree.resolve(strict=True)
        for p in (inventory, map_path): private(p, root)
        inv = json.loads(inventory.read_text(encoding="utf-8"))
        entries = inv.get("lines")
        size = inv.get("size")
        if (inv.get("schema_version") != "registro-inventario/1" or
                not re.fullmatch(r"[0-9a-f]{64}", str(inv.get("snapshot_sha256"))) or
                type(size) is not int or size < 1 or not isinstance(entries, list) or not entries or
                any(not isinstance(inv.get(key), list) for key in ("headings", "rows", "separators", "fences"))):
            fail("Inventario inválido")
        previous_end = 0
        for number, entry in enumerate(entries, 1):
            if (not isinstance(entry, dict) or set(entry) != {"number", "start", "end"} or
                    entry.get("number") != number or type(entry.get("start")) is not int or
                    type(entry.get("end")) is not int or entry["start"] != previous_end or
                    entry["end"] <= entry["start"] or entry["end"] > size):
                fail("Inventario con líneas inválidas")
            previous_end = entry["end"]
        if previous_end != size:
            fail("Inventario incompleto")
        headings = inv["headings"]
        if any(not isinstance(h, dict) or set(h) != {"line", "start", "text", "pattern"} or
               type(h["line"]) is not int or h["line"] < 1 or h["line"] > len(entries) or
               h["start"] != entries[h["line"] - 1]["start"] or not isinstance(h["text"], str) or
               h["pattern"] not in ("reglas", "indice", "nota-historica", "nota-titulada", "fecha-local", "iso", "incidente-id", "numerico", "no-clasificado")
               for h in headings):
            fail("Inventario con H2 inválidos")
        starts = [entry["start"] for entry in entries] + [size]
        ranges = []
        for arg in sys.argv[5:]:
            parts = arg.split(":")
            if (not arg.isascii() or len(parts) not in (3, 4) or
                    not all(re.fullmatch(r"[0-9]+", x) for x in parts[:2]) or parts[2] not in KINDS):
                fail("Argumento de tramo inválido: " + arg)
            a, b = map(int, parts[:2])
            kind = parts[2]
            if a < 1 or b > len(starts) or b <= a: fail("Límites de tramo inválidos")
            item = {"start": starts[a - 1], "end": starts[b - 1], "kind": kind}
            if kind == "nota":
                if len(parts) != 4 or parts[3] != "nota-explicita": fail("Nota sin fundamento explícito")
                item["basis"] = parts[3]
            elif len(parts) != 3: fail("Fundamento en tramo no nota")
            ranges.append(item)
        map_headings = [{"start": h["start"], "line": h["line"], "pattern": h["pattern"]} for h in headings]
        payload = {"schema_version": "registro-rangos/1", "snapshot_sha256": inv["snapshot_sha256"], "size": size, "headings": map_headings, "ranges": ranges}
        checked_map_payload = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        with map_path.open("xb") as f: f.write(checked_map_payload.encode("utf-8"))
        print(json.dumps({"map_sha256": digest(checked_map_payload.encode("utf-8")), "ranges": len(ranges)}, ensure_ascii=True))
    elif mode in ("construir", "cotejar") and len(sys.argv) == 6:
        snapshot, map_path, candidate, worktree = map(Path, sys.argv[2:6])
        root = worktree.resolve(strict=True)
        for p in (snapshot, map_path, candidate): private(p, root)
        data, lines, starts = read_source(snapshot)
        if mode == "construir":
            canonical, headings, incidents, row_start, row_end, _, comment_zone = classify(lines, starts)
            mapping = checked_map(map_path, data, starts, headings, canonical)
            kept = [item for item in mapping["ranges"] if item["kind"] in KEEP]
            if comment_zone == "legada":
                closure = next(item for item in kept if item["kind"] == "cierre")
                kept = [item for item in kept if item is not closure] + [closure]
            output = b"".join(data[item["start"]:item["end"]] for item in kept)
            with candidate.open("xb") as f: f.write(output)
            print(json.dumps({"snapshot_sha256": digest(data), "map_sha256": digest(map_path.read_bytes()), "candidate_sha256": digest(output), "copied_at": datetime.fromtimestamp(snapshot.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"), "removed_index_rows": row_end-row_start, "removed_incidents": len(incidents), "cierre_reubicado": comment_zone == "legada", "comentario_zona": comment_zone}, ensure_ascii=True))
        else:
            # Inspecciona primero el candidato: un mapa autoconsistente pero inválido no puede acreditarlo.
            output, annotation, comment_zone = positive_candidate(candidate, lines)
            canonical, headings, _, _, _, _, _ = classify(lines, starts)
            checked_map(map_path, data, starts, headings, canonical)
            print(json.dumps({"snapshot_sha256": digest(data), "map_sha256": digest(map_path.read_bytes()), "candidate_sha256": digest(output), "copied_at": datetime.fromtimestamp(snapshot.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"), "accredited": True, "anotacion_historica": annotation, "cierre_reubicado": comment_zone == "legada", "comentario_zona": comment_zone}, ensure_ascii=True))
    elif mode == "inspeccionar-previo" and len(sys.argv) >= 5:
        snapshot, worktree = map(Path, sys.argv[2:4])
        root = worktree.resolve(strict=True)
        private(snapshot, root)
        if any(not target for target in sys.argv[4:]):
            fail("ID objetivo vacío")
        data, lines, starts = read_source(snapshot)
        _, headings, incidents, row_start, row_end, closing, comment_zone = classify(lines, starts)
        ids = []
        for n in incidents:
            _, value = incident_id(lines[n][:-1])
            ids.append(value)
        row_ids = []
        for n in range(row_start, row_end):
            cell = lines[n].split("|", 2)[1].strip(" \t")
            if cell.startswith("`") and cell.endswith("`") and len(cell) > 1: cell = cell[1:-1]
            if not cell: fail("ID vacío en Índice")
            row_ids.append(cell)
        if len(ids) != len(set(ids)) or len(row_ids) != len(set(row_ids)):
            fail("ID repetido dentro del Índice o las secciones")
        if not incidents and not row_ids and data != data[:starts[closing+1]]:
            fail("Registro vacío con contenido tras cierre")
        targets = set(sys.argv[4:]) & (set(ids) | set(row_ids))
        if targets:
            fail("ID objetivo ya presente en registro previo: " + ", ".join(sorted(targets)),
                 payload={"targets_present": sorted(targets), "count": len(incidents), "ids": ids, "row_ids": row_ids})
        annotations = [(h["line"], "nota-historica" if h["pattern"] == "nota-historica" else "nota-etiquetada")
                       for h in headings if h["pattern"] in ("nota-historica", "nota-titulada")]
        if comment_zone:
            _, _, fences, _, _ = scan(lines, starts)
            annotations.append((historical_comment(lines, fences)[0] + 1, "comentario"))
        types = list(dict.fromkeys(kind for _, kind in sorted(annotations)))
        print(json.dumps({"count": len(incidents), "ids": ids, "row_ids": row_ids, "targets_present": [], "snapshot_sha256": digest(data), "empty": not incidents and not row_ids, "anotacion_historica": {"presente": bool(types), "tipos": types}, "cierre_reubicado": False, "comentario_zona": comment_zone}, ensure_ascii=True))
    else:
        fail("Uso: preparar-vuelta|validar-vuelta|registrar-evento|comparar-unidad|preparar-cotejo|inventariar|mapear|construir|cotejar|inspeccionar-previo|plazo-retiro|simular-retiro|validar-publicacion|revalidar-retiro|escribir-retiro|cotejar-retiro", 2)


if __name__ == "__main__":
    try:
        run()
    except ValidationError as exc:
        print(json.dumps({"status": "detenido", "error": str(exc), **exc.payload}, ensure_ascii=True))
        print(str(exc), file=sys.stderr)
        raise SystemExit(exc.code)
    except Exception as exc:
        print(json.dumps({"status": "fallo-ejecucion", "error": str(exc)}, ensure_ascii=True))
        print(str(exc), file=sys.stderr)
        raise SystemExit(3)
```
<!-- registro-candidato:fin -->
**Acreditar antes de 6.3.** Leer completos los JSON, stderr y códigos de las cuatro llamadas.
Exigir digests de instantánea, mapa y candidato de **esta** vuelta, además de `accredited: true`,
`anotacion_historica` y `cierre_reubicado`
en `cotejar`; comprobar los mismos bytes físicos que se publicarán. Si `mapear` falla o
`construir` informa `Mapa inválido`, mostrar el diagnóstico y, cuando la salida lo incluya,
el primer tramo esperado/recibido; conservar scratch/inventario/mapa;
solicitar decisión humana para abandonar o preparar **otra** instantánea, inventario y mapa, no
pedir una fuente nueva como remedio automático ni entrar en bucle. Ante cualquier otra estructura
no clasificable o cotejo rojo, detener sin publicar y enumerar temporales. Nunca llamar
`preexistente` a un candidato residual de este intento.

Con salida verde, comprobar **antes** de publicar que la ruta ausente está ignorada y que su
resolución física sigue confinada. POSIX `git -C "$worktree" check-ignore -q -- "$ruta"`;
PowerShell `git -C $worktree check-ignore -q -- $ruta`. Código distinto de cero detiene sin escribir.
Capturar el estado Git previo — POSIX `git -C "$worktree" status --porcelain --untracked-files=all`;
PowerShell `git -C $worktree status --porcelain --untracked-files=all`.

Crear únicamente los directorios intermedios de esa ruta tras comprobar su confinamiento:
POSIX `mkdir -p "$(dirname "$destino")"`; PowerShell
`New-Item -ItemType Directory -Force -Path (Split-Path $destino -Parent) | Out-Null`.
Repetir el chequeo físico **después de crear los directorios y antes de publicar**.

Publicar el candidato **solo por creación exclusiva**. La ruta puede haber aparecido entre la
inspección y este punto: `xb` falla sin sobrescribirla. En esa colisión volver a inspeccionarla
como en el primer apartado; solo avanzar si su procedencia y utilidad se acreditan.

| POSIX | PowerShell |
|---|---|
| `python3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open("xb"); f.write(Path(sys.argv[1]).read_bytes()); f.close()' "$candidato" "$destino"` | `py -3 -c 'from pathlib import Path; import sys; f=Path(sys.argv[2]).open(''xb''); f.write(Path(sys.argv[1]).read_bytes()); f.close()' $candidato $destino` |

Repetir el chequeo físico **después de publicar**. Comprobar ubicación exacta e igualdad de bytes
con el candidato: POSIX `cmp -s "$candidato" "$destino"`; PowerShell
`py -3 -c 'from pathlib import Path; import sys; sys.exit(0 if Path(sys.argv[1]).read_bytes()==Path(sys.argv[2]).read_bytes() else 1)' $candidato $destino`.
Comparar el estado Git posterior con el capturado antes y exigir que no se hayan sumado cambios
versionables. Si falla cualquier comprobación posterior, conservar el archivo publicado y los
temporales como residuales; **no** convertirlo en preexistente al reintentar. Solo tras acreditar,
entregar `sembrado` con ruta, fuente normal o aprobada, ruta física aprobada si la hubo, `copied_at`,
`snapshot_sha256`, `map_sha256`, `candidate_sha256`, los bytes UTF-8 completos de `scratch/mapa`
y conteos retirados. **No borrar `scratch/mapa` aún**: 6.3 lo inserta byte a byte en la sección 9
del dossier y verifica su digest antes de limpiar scratch. Si 6.3 falla, scratch sigue siendo
residual enumerado, junto al árbol, registro y dossier parcial.

**Contrato de parada.** Cada fallo conserva origen, issue y resto del lote sin despachar ni
retirar. Fuente ausente o estructura inadmisible → mostrar árbol y pedir archivo/ruta física
aprobados; instrucciones ambiguas o divergentes → decisión humana y nueva extracción de ambas
tuplas; previo inválido o ID duplicado → decisión sobre ese archivo sin vaciarlo; mapa inválido →
mostrar el diagnóstico y el primer tramo esperado/recibido si está disponible, conservar scratch
y pedir decisión humana sobre abandono o nueva vuelta; ruta no ignorada, cotejo o publicación
fallidos → árbol, temporales y archivo
publicado, si existe, hasta decisión. Para procedencia incierta o residual de siembra, el usuario
elige explícitamente inspeccionarlo y aceptarlo como `preexistente` con estado y cantidad observados,
autorizar su retiro y nueva siembra en el mismo árbol, o abandonar. Ninguna salida borra un residual
ni restablece `sembrado` por inferencia.

### El hook de setup ya corrió, o no

**La autoridad del hook y su clasificación viven en «Clasificar el hook de setup»**, que corre antes
de crear y decide con qué primitiva se crea. Acá solo importa una consecuencia para la siembra: si el
hook clasificó `reproducible` o `inseparable` y **corrió**, puede haber copiado ya estos directorios
— es un patrón común. Si lo hizo:

- **No copiar encima.** El hook puede adaptar lo que copia al worktree; pisarlo revierte esa
  adaptación.
- Comprobar igual que el resultado está: un hook que **no corrió** —en Orca, por su
  `setupRunPolicy`— deja el worktree vacío, y la salida de la creación no lo dice.

Si el hook clasificó `ausente` y este repo va a repetir el flujo seguido, vale sugerirle al usuario
declararlo donde su plataforma lo aloje: en Orca, el `hookSettings.scripts.setup` del repo; en Herdr,
un script del propio árbol, que es el único lugar donde esta clasificación lo busca. En las dos es
configuración ajena al flujo, así que **se sugiere, no se hace**.

---

## El dossier

Va en `<worktree>/.plans/incidentes-a-corregir.md`. Es el contrato completo con un flujo que arranca
sin contexto de esta sesión, y **la única copia** de los incidentes tomados.

### Secciones obligatorias

1. **Encabezado que declara qué es** — que es la entrada del flujo y conserva verbatim los
   incidentes aunque el retiro del registro de origen todavía esté pendiente. Solo tras
   `cotejar-retiro` acreditado se puede informar que el registro ya no los contiene.
2. **La causa raíz compartida**, en una frase, como cita destacada. Es lo que justifica que estos
   incidentes vayan juntos; si no se puede escribir sin forzarla, el agrupamiento del paso 3 estaba
   mal y hay que volver.
3. **La superficie común** — archivos y secciones que el diff va a tocar.
4. **Cada incidente verbatim**, con su tabla de metadatos completa. No resumidos, no parafraseados.
   Si fue redimensionado, poner el diagnóstico corregido bajo un H2 propio
   (`## Diagnóstico corregido`) después del incidente original completo; H3, negrita y cita no
   delimitan la versión original para el cotejo post-efecto.
5. **La verificación previa** — la tabla del paso 2, con las citas textuales que la sostienen
   (`archivo:línea` sirve acá; el registro de origen las prohíbe, el dossier las necesita). Si el
   paso 4 obligó a rehacer filas contra `origin`, decir cuáles y contra qué commit.
6. **El estado aguas arriba** — el resultado del paso 4, en tres líneas: los commits de
   `origin/<default>` que tocan la superficie y **ya están en la base de este worktree**, los PRs
   abiertos que la tocan con su número y sus archivos, y —si no se pudo mirar— que no se comprobó y
   por qué. Un PR abierto sobre los mismos archivos es una restricción para este flujo, no un dato de
   color: cambia el alcance que conviene tomar.
7. **Las decisiones abiertas** — dónde el árbol ya cambió respecto de lo que el incidente asume, con
   las opciones nombradas y **sin recomendar una**. Decir explícitamente que no está pre-decidida.
8. **Las restricciones del repo destino** que este flujo puede violar sin darse cuenta: topes de
   verificación, prohibiciones sobre directorios, guardas que hay que correr y **cómo se leen** (hay
   guardas cuyo código de salida no es la señal de salud).
9. **Dónde se registran los incidentes** si alguna skill falla durante el flujo — consumir el
   resultado acreditado de 6.2, no inferirlo de que exista un archivo. Con `sembrado`, declarar
   ruta del registro, archivo fuente y fecha de lectura/copia; si la fuente fue aprobada tras una
   parada, identificar también su ruta física aprobada. Declarar **en toda siembra**, incluso si
   no se detectó una nota concreta, que cualquier anotación ya presente en la cabecera copiada
   pertenece a la historia de la fuente y no a esta siembra. No añadir una anotación nueva dentro
   del registro sembrado. Con `preexistente`, declarar ruta, estado Git y cantidad de incidentes
   conservados. Con `otra-sede`, conservar la sede y ruta que el destino declaró; con
   `sin-declaración`, decir que no declaró ninguna, sin inventar ruta. `Detenido` no produce dossier
   ni despacho: su motivo y residuales van al cierre de la corrida detenida.
   En `sembrado`, consignar además `snapshot_sha256`, `candidate_sha256`, `map_sha256`,
   `cierre_reubicado`, `comentario_zona` y `anotacion_historica` acreditados por `cotejar`.
   En `preexistente`, llevar `anotacion_historica`, `cierre_reubicado` y `comentario_zona`
   acreditados por `inspeccionar-previo`, incluso cuando hay una nota H2 sin comentario.
   `cierre_reubicado` es `false` en un previo: se inspecciona sin trasladar el cierre, aunque
   `comentario_zona` sea `legada`.
   `anotacion_historica.presente` describe historia de la **fuente o del previo**, no una
   anotación creada por esta siembra; sin declaración no se inventa historia.
   Dar a esta sección el H2 literal `## 9. Dónde se registran los incidentes`; un `## 9. `
   citado dentro de un incidente no la identifica. Escribir el digest del mapa como una única
   línea literal `map_sha256: <64 caracteres hexadecimales minúsculos>`, sin lista, tabla,
   comillas ni cerca; el cotejo siguiente lee esa forma concreta, no Markdown libre.
   Insertar **los bytes UTF-8 completos** de `scratch/mapa`, incluida su única nueva línea
   final, dentro de una cerca `json` de tres backticks situada entre las líneas únicas
   `<!-- registro-mapa:inicio -->` y `<!-- registro-mapa:fin -->` de esta sección. No
   reserializar, normalizar ni añadir contenido al registro sembrado. Antes de borrar scratch,
   verificar que el bloque literal coincide con el archivo y con el digest declarado. Aislar la
   sección 9 por su H2 y el H2 siguiente **exteriores a cercas**; marcadores citados fuera de ella
   no cuentan, y dos pares dentro de ella detienen. `dossier` es la ruta física del dossier ya
   escrito; `mapa` es `scratch/mapa`. Tras escribir el dossier y antes de borrar scratch,
   ejecutar la sección «Verificar el mapa de la sección 9» más abajo; sus comandos imprimen el SHA
   solo con código `0`.

   Si escribir o verificar el dossier falla, conservar scratch y enumerar árbol, registro,
   mapa y dossier parcial como residuales; no limpiar ni despachar. Solo después del código `0`
   de este cotejo puede limpiarse el scratch privado. En `preexistente`, `otra-sede` y
   `sin-declaración` no se inventa un mapa ni un digest.
10. **El issue de origen**, si el incidente vino de uno: su número, su URL, y la instrucción de
    escribir `Closes #<n>` en el PR. Sin esto el flujo no tiene cómo saber a qué issue pertenece —
    arranca sin contexto de esta sesión— y el issue queda `en-curso` para siempre aunque el arreglo
    se haya mergeado. Con varios incidentes agrupados van **todos** los números, uno por línea:
    GitHub cierra tantos `Closes` como el PR declare.

11. **La plataforma anfitriona** — sobre cuál de las dos corre el panel donde este flujo vive, y si
    salió de la matriz o de un pedido del usuario. El flujo arranca **sin contexto de esta sesión**,
    y la resolución del paso 6.1 no queda escrita en ningún otro lado. Tres campos, y ninguno se
    deduce:

    | Campo | Valores | Qué dice |
    |---|---|---|
    | `plataforma` | `herdr` \| `orca` | la que el paso 6.1 resolvió, y sobre la que se creó el worktree y el panel |
    | `origen` | `resuelta` \| `pedida` | `resuelta`, la eligió la matriz sobre las identidades vivas; `pedida`, el usuario la dio en el parámetro `plataforma` |
    | `identidad` | el valor observado | la identidad del panel **de este flujo**, no la del panel del intake: son dos paneles distintos |

    > **Es un hecho observado, y queda escrito.** Lo que esta sección aporta es **de dónde arranca**
    > el flujo. `sdd-flow` no la consume para despachar: sus workers van por CLI, sea cual sea la
    > plataforma.

### Verificar el mapa de la sección 9

Con `dossier` y `mapa` definidos como en el ítem 9, ejecutar uno de estos comandos solo después
de escribir el dossier de una siembra y antes de borrar `scratch/mapa`.

**POSIX:**

```sh
python3 -c 'from hashlib import sha256
from pathlib import Path
import re
import sys

document = Path(sys.argv[1]).read_bytes()
original = Path(sys.argv[2]).read_bytes()
def exterior_h2(data):
    headings = []
    fence = None
    offset = 0
    for line in data.splitlines(keepends=True):
        token = re.match(rb"^ {0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            if token and token.group(1)[:1] == fence[:1] and len(token.group(1)) >= len(fence) and not line[token.end():].strip():
                fence = None
        elif token:
            fence = token.group(1)
        elif re.fullmatch(rb"## [^\n]*\n", line):
            headings.append((offset, offset + len(line), line))
        offset += len(line)
    return headings

headings = exterior_h2(document)
headers = [(start, end) for start, end, line in headings if line == "## 9. Dónde se registran los incidentes\n".encode("utf-8")]
if len(headers) != 1:
    raise SystemExit("Sección 9 ausente o repetida")
following = next((start for start, _, _ in headings if start >= headers[0][1]), len(document))
section = document[headers[0][1]:following]
begin = b"<!-- registro-mapa:inicio -->\n"
end = b"<!-- registro-mapa:fin -->\n"
if section.count(begin) != 1 or section.count(end) != 1 or section.index(begin) >= section.index(end):
    raise SystemExit("Marcadores de mapa ausentes, repetidos o invertidos")
inside = section.split(begin, 1)[1].split(end, 1)[0]
lines = inside.splitlines(keepends=True)
while lines and not lines[0].strip(): lines.pop(0)
while lines and not lines[-1].strip(): lines.pop()
if len(lines) < 3 or lines[0] != b"```json\n" or lines[-1] != b"```\n":
    raise SystemExit("Bloque JSON literal mal delimitado")
payload = b"".join(lines[1:-1])
asserted = re.findall(rb"(?m)^map_sha256: ([0-9a-f]{64})\n", section)
if len(asserted) != 1:
    raise SystemExit("Línea literal map_sha256: ausente o repetida en sección 9")
if sha256(payload).hexdigest().encode() != asserted[0] or payload != original:
    raise SystemExit("Mapa del dossier no coincide con scratch o digest declarado")
print(sha256(payload).hexdigest())' "$dossier" "$mapa"
```

**PowerShell:**

```powershell
if (-not (Get-Command py -CommandType Application -ErrorAction SilentlyContinue)) { throw 'Lanzador Python no disponible' }
$shaMapa = py -3 -c 'from hashlib import sha256
from pathlib import Path
import re
import sys

document = Path(sys.argv[1]).read_bytes()
original = Path(sys.argv[2]).read_bytes()
def exterior_h2(data):
    headings = []
    fence = None
    offset = 0
    for line in data.splitlines(keepends=True):
        token = re.match(rb''^ {0,3}(`{3,}|~{3,})'', line)
        if fence is not None:
            if token and token.group(1)[:1] == fence[:1] and len(token.group(1)) >= len(fence) and not line[token.end():].strip():
                fence = None
        elif token:
            fence = token.group(1)
        elif re.fullmatch(rb''## [^\n]*\n'', line):
            headings.append((offset, offset + len(line), line))
        offset += len(line)
    return headings

headings = exterior_h2(document)
headers = [(start, end) for start, end, line in headings if line == ''## 9. Dónde se registran los incidentes\n''.encode(''utf-8'')]
if len(headers) != 1:
    raise SystemExit(''Sección 9 ausente o repetida'')
following = next((start for start, _, _ in headings if start >= headers[0][1]), len(document))
section = document[headers[0][1]:following]
begin = b''<!-- registro-mapa:inicio -->\n''
end = b''<!-- registro-mapa:fin -->\n''
if section.count(begin) != 1 or section.count(end) != 1 or section.index(begin) >= section.index(end):
    raise SystemExit(''Marcadores de mapa ausentes, repetidos o invertidos'')
inside = section.split(begin, 1)[1].split(end, 1)[0]
lines = inside.splitlines(keepends=True)
while lines and not lines[0].strip(): lines.pop(0)
while lines and not lines[-1].strip(): lines.pop()
if len(lines) < 3 or lines[0] != b''```json\n'' or lines[-1] != b''```\n'':
    raise SystemExit(''Bloque JSON literal mal delimitado'')
payload = b''''.join(lines[1:-1])
asserted = re.findall(rb''(?m)^map_sha256: ([0-9a-f]{64})\n'', section)
if len(asserted) != 1:
    raise SystemExit(''Línea literal map_sha256: ausente o repetida en sección 9'')
if sha256(payload).hexdigest().encode() != asserted[0] or payload != original:
    raise SystemExit(''Mapa del dossier no coincide con scratch o digest declarado'')
print(sha256(payload).hexdigest())' $dossier $mapa
$pyCorrecto = $?
$pyCodigo = $LASTEXITCODE
if (-not $pyCorrecto -or $pyCodigo -ne 0 -or $shaMapa -isnot [string] -or $shaMapa -cnotmatch '^[0-9a-f]{64}$') { throw 'Verificación del mapa fallida' }
$shaMapa
```

**Frontera del verificador de sección 9:** detecta un único H2 literal exterior a cercas,
marcadores reales en su tramo, digest y bytes íntegros del mapa; no acredita que la siembra
publicó el registro ni que el origen declarado sea veraz. Clase de salida: `veredicto`;
el código `0` acredita solo el mapa literal y emite su SHA-256. Dirección de error:
`las dos`, porque un H2 exterior omitido o contado de más altera qué tramo se coteja.
Error de ejecución o parseo detiene 6.3,
conserva scratch, dossier parcial y árbol; no degrada a `preexistente`.

### Lo que no va

- Recomendaciones sobre la decisión abierta. El flujo tiene que decidirla con criterio propio; una
  recomendación escrita acá se transcribe en vez de pensarse.
- Rutas del proyecto donde el incidente se observó. Al flujo no le sirven.
- Un plan de implementación. Eso lo produce `sdd-flow`, es su trabajo.

---

## Despachar el flujo

### Esperar a que el agente esté listo

| Plataforma | Comando | Observable |
|---|---|---|
| Herdr | `herdr agent get <nombre>` | `agent_status` que la plataforma declara listo: `idle` o `done` |
| Orca | `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 90000 --json` | el estado que devuelve |

`herdr agent get` es la autoridad.

Sus resultados se clasifican por **tres discriminantes en este orden —código de salida, parseo y
contenido—**, y cada fila es el caso que las anteriores no tomaron. No se clasifica por la
descripción del síntoma: un `agent get <nombre-inexistente>` sale **distinto de cero** y trae
`error.code: agent_not_found`, así que «no devuelve el agente» y «el comando falla» describen **el
mismo** resultado y no pueden ser dos filas.

| Código de salida | Salida | Identidad | `agent_status` | Resultado observable |
|---|---|---|---|---|
| `0` | parsea | la esperada | `idle` o `done` | **continuar**, cualquiera sea el código de salida de `agent start` |
| `0` | parsea | la esperada | `working` | **esperar y reconsultar** |
| `0` | parsea | la esperada | `blocked` | **detener y mostrar la aprobación o la pregunta abierta**: el agente responde, pero lo que reciba entra en esa UI y no en el compositor |
| `0` | parsea | la esperada | `unknown`, o un estado que esta tabla no enumera | **detener sin destruir**: la plataforma declara que `unknown` no prueba completitud, y un estado que no conocemos tampoco |
| `0` | parsea | **cualquier otra**: una **identidad distinta** —otro panel, otra familia u otro `cwd`—, o una respuesta que no trae el agente | — | **detener y mostrar lo que devolvió**; nunca esperar, porque esperar a que cambie una identidad equivocada no la corrige |
| `0` | no parsea | — | — | **detener sin destruir**: una salida que no se puede leer no prueba que el agente no esté |
| ≠ `0` | `error.code` es `agent_not_found` | — | — | **detener sin destruir**: el agente no está registrado con ese nombre, que no es lo mismo que no existir el panel |
| ≠ `0` | cualquier otro `error.code`, o ninguno legible | — | — | **detener sin destruir**: la consulta no se pudo hacer, así que no dice nada del agente |

**Quien declara el readiness es `agent_status`, no `interactive_ready`, y eso está medido.** La
plataforma define `idle` como listo para recibir input, `done` como **ese mismo estado** después de
un trabajo en background que nadie miró, `blocked` como una UI de aprobación o pregunta reconocida, y
`unknown` como presente pero sin clasificar, que **no prueba completitud**. Contra el runtime,
`interactive_ready` **no sigue esa semántica**: viene `true` en un agente `blocked` —que no puede
recibir el encargo, porque lo que llegue entra en su aprobación— y **no viene** en uno `done`, que sí
está listo. Clasificar por esa clave tomaba las dos decisiones al revés: despachaba dentro de una
pregunta abierta y rechazaba a un agente disponible.

**Y la ausencia no se resuelve esperando.** Medido con dos lecturas separadas del mismo agente
`done`: el estado y la ausencia de la clave se conservan, así que reconsultar no converge y el único
final posible era agotar el límite. Una espera que por construcción no puede terminar bien no es una
espera: es un rechazo con demora.

**Qué pasa entonces con `interactive_ready`: nada.** Deja de ser condición de acreditación, **no
aparece en la tabla y no tiene poder de veto**. La tabla es la única sede que clasifica, así que una
entrada tiene exactamente una salida y ninguna superficie que la consuma necesita recordar una guarda
aparte.

Hubo una versión intermedia que sí le daba veto —«si está presente y es falso mientras el estado
declara listo, no se continúa»—, y **se retiró por dos razones**. La primera es que contradecía a la
tabla: el mismo caso tenía dos resultados, continuar y detener, y el contrato no decía cuál manda. La
segunda es que esa guarda **no nacía de un caso observado**: se escribió por precaución, para no
tener que decidirlo si alguna vez aparecía. Darle poder de veto a un observable que esta misma
sección declara no autoritativo, sobre un caso que nadie vio, es exactamente lo que el escalón barato
evita. Si alguna vez se observa esa combinación, será un caso medido y entonces se decidirá con él
delante.

**La quinta fila es el complemento, y por eso la tabla es total.** Las cuatro primeras exigen la
identidad esperada y se reparten por `agent_status`; la quinta toma **toda identidad distinta** —incluida
una respuesta que no trae el agente—, así que ningún contenido con `exit 0` queda sin clasificar.
Enumerar solo los desvíos que uno se imagina es como se abren los huecos: el de la clave ausente
estuvo abierto una versión entera, y el de `blocked` sobrevivió a que la tabla ya fuera total en la
forma.

**El límite no es un resultado de `agent get`, y por eso no es una fila.** Es una transición del
estado de espera: reconsulta **la única fila que espera**, la de `working`, cada 2 s hasta 60 s. Al
agotarse, la acreditación **nunca se completó**, así que se **detiene sin destruir** y toda
liquidación posterior pasa por el gate humano.

**El invariante de orden nombra sus hitos, porque `acreditar` designa dos distintos:**

    arrancar el agente → acreditar identidad y readiness → primer tiempo
      → acreditar el reconocimiento → cuerpo

`acreditar identidad y readiness` es esta sección y se resuelve con la tabla de arriba.
`acreditar el reconocimiento` es el paso 2 del envío en tres tiempos —leer el compositor y buscar la
señal de esa familia— y ocurre **después** del primer tiempo, no antes. Llamar `acreditar` a los dos
ponía el segundo delante de su propio prerequisito.

Esta regla rige desde la siguiente activación, porque una sesión que ya cargó el archivo sigue con
lo que cargó.

Mandar antes de eso pierde el texto: el TUI todavía no tiene dónde recibirlo.

### El prompt es un puntero, no el encargo

**El prompt no transporta el encargo: lo apunta.** El dossier ya existe en disco antes de este
sub-paso —es el invariante de orden del paso 6— así que el prompt solo tiene que decir dónde está y
que se lea entero antes de nada.

```
<prefijo> corregí los incidentes del dossier <ruta absoluta>, leelo entero antes de nada: es la única copia
```

**Por qué apuntar y no transportar.** Un encargo largo entra al TUI como bloque pegado, y de ahí
salen dos fallos distintos: el prefijo queda dentro del bloque, y el cuerpo puede llegar incompleto.
Un puntero corto no los elimina —la relación entre largo y fallo es una hipótesis, no un hecho
medido— pero los **reduce**, y el control de abajo es obligatorio igual.

> **Lo que el prompt deja de llevar, el dossier tiene que tenerlo.** Antes viajaban en el prompt la
> causa raíz, la superficie, las decisiones abiertas, las restricciones del repositorio y el PR
> abierto si lo había. Todo eso va **al dossier**, y su plantilla lo exige. Un puntero a un dossier
> incompleto es peor que un encargo largo.

### Comprobar el dossier antes de enviar

Tres cosas, y las tres antes del primer tiempo: que **exista**, que sea **legible**, y que su
**digest** sea el que se calculó **al escribirlo**. El tercero es el que importa y el que se olvida:
el digest se liga a la **fuente** —los bytes que se escribieron— y no a lo que se mandó, porque un
digest calculado sobre lo enviado sella también lo que el envío haya roto.

### Enviar en tres tiempos

El corte no es texto/Enter: es **prefijo / cuerpo / Enter**, y entre el primero y el segundo hay una
comprobación que decide si se sigue.

1. **El prefijo solo**, en la forma que su familia exige.
2. **Leer el compositor** y buscar la señal de reconocimiento **de esa familia**. Sin la señal, no se
   manda el cuerpo: se aplica la fila de recuperación.
3. **El cuerpo**, y leerlo para comprobar que entró entero. Si el compositor devuelve el marcador de
   colapso, esa lectura queda **inconcluyente y no negativa** —el marcador dice que el host colapsó el
   bloque pegado para mostrarlo, no que el cuerpo haya llegado truncado—, así que se sigue: un cuerpo
   roto no sobrevive al primer artefacto que el flujo somete a gate, con el usuario delante.
4. **El Enter**, sobre ese mismo compositor y sin nada tipeado en el medio.

> **Por qué el tercer tiempo no recupera y el segundo sí.** No es una asimetría de rigor sino de qué
> observable sobrevive. El segundo protege la **procedencia**, que solo existe como cadena del envío:
> un prefijo no reconocido no deja rastro en ningún artefacto posterior, así que perderla ahí es
> perderla del todo. El cuerpo no está en esa situación: lo que llegue roto se ve en lo que el flujo
> produce, y frenar acá lo tapa, porque sin Enter no hay flujo y sin flujo no hay artefacto que
> delate el defecto.
>
> Una recuperación acá tampoco sería **ejecutable**: vaciar el compositor exige borrar el draft, y
> ningún subcomando de `orca terminal` lo hace —medido contra 1.4.205, donde `send` admite `--text`,
> `--enter` e `--interrupt` y ninguna operación de tecla—. Prescribirla dejaría a las dos familias
> sobre esa plataforma con un paso sin salida practicable.

### Qué se escribe y qué se busca, por familia

**La secuencia no es la misma, y la diferencia es un espacio.** Está medido: en una familia el espacio
final revela la señal, y en la otra la oculta. Un procedimiento que use la misma forma para las dos
falla en una — y falla mostrando el texto correcto sin la señal, que es indistinguible de un prefijo
no reconocido.

| Familia | Qué se escribe en el primer tiempo | Qué acredita el reconocimiento |
|---|---|---|
| `claude` | `/sdd-flow` **con** espacio final | el compositor muestra la **gramática de argumentos** de la skill a continuación del prefijo |
| `codex` | `$sdd-flow` **sin** espacio final | el compositor muestra la **entrada de la skill en el menú filtrado**, con su descripción. El espacio se manda con el cuerpo |

| Plataforma | Cómo se escribe sin enviar | Cómo se lee el compositor | Cómo se manda el Enter |
|---|---|---|---|
| Herdr | `herdr pane send-text <id> '<texto>'`; para el primer tiempo de `claude` en Git Bash o cualquier shell MSYS sobre Windows: `MSYS_NO_PATHCONV=1 herdr pane send-text <id> '/sdd-flow '` | `herdr pane read <id> --source visible` | `herdr pane send-keys <id> enter` |
| Orca | `orca terminal send --terminal <handle> --text '<texto>' --json`; para el primer tiempo de `claude` en Git Bash o cualquier shell MSYS sobre Windows: `MSYS_NO_PATHCONV=1 orca terminal send --terminal <handle> --text '/sdd-flow ' --json` | `orca terminal read --terminal <handle> --json` → campo `draft` | `orca terminal send --terminal <handle> --text "" --enter --json` |

**Sin comillas dobles ni apóstrofes** en el texto si va entre comillas simples del shell — más simple
que escapar. Como condición distinta, un argumento que abre con barra se convierte en ruta bajo Git
Bash o cualquier shell MSYS sobre Windows, cualquiera sea la comilla que lo rodee. La forma con
`MSYS_NO_PATHCONV=1` solo aplica al shell que convierte; PowerShell y los POSIX reales no convierten,
no la necesitan y la invocación sin ella sigue siendo válida ahí.

Esta clasificación se midió: el cuerpo, el prefijo de la otra familia y el texto vacío del Enter no
abren con barra y por eso no se convierten.

### Confirmar el arranque — la procedencia, y lo que ya no se acredita

El control viejo buscaba «la señal de que la skill cargó». Eso lo satisface también un agente que
**compensó** leyendo el archivo de la skill por su cuenta, así que no distingue un arranque bueno de
uno malo. Lo que sí discrimina:

| Propiedad | Qué acredita | Qué **no** acredita | Cómo se comprueba |
|---|---|---|---|
| **procedencia** | que la invocación entró por el prefijo, reconocido por el host | nada sobre el contenido del encargo ni sobre el cuerpo del prompt | la **cadena** del envío: el prefijo se reconoció en el tiempo 2, no se tipeó nada en el medio, y el Enter fue sobre ese compositor |

**Y nada más, a propósito.** Antes se exigían dos propiedades más: que el `sha256` del dossier
apareciera entre las fuentes que el flujo congelaba, y que el cuerpo canónico del puntero estuviera
en la primera entrada de su literal. Las dos se comprobaban contra artefactos de acreditación que
`sdd-flow` **ya no produce**, así que seguir exigiéndolas deja este paso sin salida practicable:
ningún arranque puede confirmarse, y entonces ningún incidente puede retirarse nunca.

**Qué queda sin cubrir, dicho en concreto.** Que el flujo haya leído **ese** dossier y no otro, y que
el cuerpo haya entrado entero en el compositor. Las dos las delata el flujo despachado un paso más
adelante y con el usuario delante: sin el puntero entero no hay dossier que leer, y el primer
artefacto que somete a gate se escribe sobre lo que el flujo sí leyó. Pero el retiro del incidente
ocurre **antes** de ese gate, así que el riesgo se acepta con nombre: **un despacho que arrancó bien
y entendió mal deja el registro vacío**, y el defecto se vuelve a registrar como incidente nuevo.

> **El punto ciego de la procedencia, declarado.** La cadena se apoya en que nadie tipeó nada entre
> el tiempo 2 y el Enter, y **eso no es observable en ninguna plataforma soportada**: ni Herdr ni Orca
> exponen el input del usuario como algo consultable. La defensa es de proceso —no tipear en el panel
> mientras el despacho corre— y esta línea existe para que la ausencia esté declarada y no se
> descubra después.

**Sin observable de reconocimiento**, el arranque se declara **no confirmado**: el incidente **no se
retira** y el issue conserva su etiqueta del pool. Eso vale para la pérdida en runtime de un
observable que sí existe; que una combinación **nunca** lo tenga es otra cosa y la gobierna la matriz
de soporte.

### Marcar el worktree

| Plataforma | Comando |
|---|---|
| Herdr | `herdr workspace rename <workspace_id, el que la adopción devuelve en .result.workspace.workspace_id> "<qué flujo corre acá>"`, o `--label` en la propia adopción, que lo deja puesto sin una llamada más. No `pane rename`: rotula el panel, no la tarjeta |
| Orca | `orca worktree set --worktree id:<repoId>::<path> --comment "<qué flujo corre acá>" --json` |

Es lo que hace legible la tarjeta cuando hay varios worktrees abiertos.

### La matriz de soporte

Las cuatro combinaciones que esta skill promete, cada una con su camino completo. **Ninguna celda
remite a otra fila.**

| Plataforma × familia | Crear | Abrir y arrancar | Acreditar el arranque | Primer tiempo | Observable que acredita |
|---|---|---|---|---|---|
| Herdr × claude | `git -C <repo_destino> worktree add -b <rama> <ruta> <sha>`, y adoptar con `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` | Ramificar por `.result.root_pane` de esa misma respuesta —`already_open` es un booleano y no discrimina nada—: con `.agent` nulo y `.cwd` igual a `<ruta>`, arrancar ahí con `herdr agent start <nombre> --kind claude --pane <.pane_id>`; con `.agent` igual a la familia esperada y ese mismo `.cwd`, reutilizarlo; en todo otro caso —otra familia, `.cwd` distinto, o el panel ocupado —su único proceso en foreground no es su shell de login— según `herdr pane process-info --pane <.pane_id>`— abrir uno propio con `herdr pane split --pane <.pane_id> --direction right --cwd <ruta> --no-focus` y arrancar ahí | `herdr agent get <nombre>` devuelve el mismo `pane_id`, la familia esperada, el `cwd` del worktree, y `agent_status` `idle` o `done`; ante cualquier otro resultado, incluido `blocked`, seguir «Esperar a que el agente esté listo» | `/sdd-flow ` con espacio | gramática de argumentos en el compositor |
| Herdr × codex | `git -C <repo_destino> worktree add -b <rama> <ruta> <sha>`, y adoptar con `herdr worktree open --path <ruta> --cwd <checkout principal del repo_destino> --label "<qué flujo corre acá>" --no-focus` | Ramificar por `.result.root_pane` de esa misma respuesta —`already_open` es un booleano y no discrimina nada—: con `.agent` nulo y `.cwd` igual a `<ruta>`, arrancar ahí con `herdr agent start <nombre> --kind codex --pane <.pane_id>`; con `.agent` igual a la familia esperada y ese mismo `.cwd`, reutilizarlo; en todo otro caso —otra familia, `.cwd` distinto, o el panel ocupado —su único proceso en foreground no es su shell de login— según `herdr pane process-info --pane <.pane_id>`— abrir uno propio con `herdr pane split --pane <.pane_id> --direction right --cwd <ruta> --no-focus` y arrancar ahí | `herdr agent get <nombre>` devuelve el mismo `pane_id`, la familia esperada, el `cwd` del worktree, y `agent_status` `idle` o `done`; ante cualquier otro resultado, incluido `blocked`, seguir «Esperar a que el agente esté listo» | `$sdd-flow` sin espacio | la skill en el menú filtrado |
| Orca × claude | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup skip --agent claude --no-parent --json`; con hook `inseparable`, el mismo comando con `--setup run` | lo arranca `--agent claude` **en la creación**, que es el único modo: `orca terminal list --worktree id:<repoId>::<ruta> --json` **observa** la terminal, no la inicia | `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 90000 --json` devuelve su estado | `/sdd-flow ` con espacio | gramática de argumentos en el campo `draft` |
| Orca × codex | `orca worktree create --repo id:<repoId> --name <nombre> --base-branch <sha> --setup skip --agent codex --no-parent --json`; con hook `inseparable`, el mismo comando con `--setup run` | lo arranca `--agent codex` **en la creación**, que es el único modo: `orca terminal list --worktree id:<repoId>::<ruta> --json` **observa** la terminal, no la inicia | `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 90000 --json` devuelve su estado | `$sdd-flow` sin espacio | la skill en el menú filtrado, en `draft` |

> **Si una combinación deja de tener observable acreditable, la promesa se cambia con gate humano.**
> No se la declara soportada con el control apagado: una fila que siempre termina en «no confirmado»
> no es soporte, es un no-op con buena prosa.

## El volcado a issues

Sede del formato y de los comandos del modo `volcar`. El destino es el repositorio de las skills
—`repo_destino`—, no el proyecto donde se observó el defecto.

### Las etiquetas

Tres ejes, y ninguno se inventa por incidente:

| Eje | Valores | De dónde sale |
|---|---|---|
| skill | `skill:<nombre>` — una por cada skill que el incidente nombra | el campo `Skill` del registro; un incidente que nombra dos lleva las dos |
| severidad | `severidad:alta` \| `severidad:media` | el campo `Severidad`. **Si el registro no lo declara, el issue va sin esta etiqueta** |
| plataforma | `plataforma:macos` \| `plataforma:windows` \| `plataforma:linux` | el campo `Plataforma`. **Si el registro no lo declara, el issue va sin esta etiqueta** |
| transporte | `transporte:cli` \| `transporte:herdr` \| `transporte:orca` | el campo `Transporte`. **Si el registro no lo declara, el issue va sin esta etiqueta** |
| estado | `needs-triage` \| `en-curso` | nace `needs-triage`; pasa a `en-curso` cuando el intake lo despacha (paso 6.5) |

Crear la etiqueta que falte antes de publicar (`gh label create <nombre> --color <hex> --description
<texto>`); `gh issue create` falla si la etiqueta no existe.

### El formato del issue

**Título:** `[<skill>] <el titular del incidente, sin la fecha>`. El prefijo hace la lista legible y
agrupable; la fecha no va acá porque es ilegible en una lista y su lugar es el cuerpo.

**Cuerpo:** los campos del registro como líneas en negrita, después el incidente **verbatim**, y al
pie la procedencia.

```
**ID de registro:** `DD/MM/AAAA HH:MM`
**Skill:** `<skill>`
**Sección:** <la seccion o regla que el incidente cita>
**Conductor:** <herramienta → modelo>
**Worker:** <herramienta → modelo, o — con el motivo>
**Plataforma:** <macos|windows|linux, o "no declarada en el registro de origen">
**Transporte:** <cli|herdr|orca, o "no declarado en el registro de origen">
**Severidad:** <alta|media, o "no declarada en el registro de origen">
**Relacionado:** <`DD/MM/AAAA HH:MM` (#<n>) del antecedente; la fecha sola si no tiene
issue, con el motivo; o — si no hay>

---

<los bloques verbatim: Qué instruía · Qué pasó · Por qué es defecto de la
 skill · Consecuencia · Qué habría que cambiar>

---
<sub>Volcado desde el registro local `<ruta>`. **Sin verificar contra el árbol**: la
verificación es del paso `sdd-incident-intake`.</sub>
```

**La plataforma y el transporte no se deducen de la sesión que vuelca.** El volcado corre después
del incidente, y a menudo en otra máquina o por otra vía: publicar los de quien vuelca le atribuiría
al defecto un entorno que nunca tuvo. Salen del registro, igual que la severidad, y si no están se
publica su ausencia dicha. Son **dos ejes independientes** —`plataforma:windows` con
`transporte:orca` es una combinación real— así que ninguno se deriva del otro. Pagan su lugar porque
separan las dos clases de defecto que más se confunden al triar: el que solo aparece en un shell
—las variantes PowerShell contra POSIX— y el que solo aparece por una vía de transporte.

**La primera línea es el mecanismo de idempotencia**, no decoración. GitHub indexa el cuerpo, así que
la fecha y hora se busca; y es lo que permite que el campo `Relacionado` siga cruzando incidentes por
su ID después de que el archivo ya no exista.

### Los comandos

Antes de `gh issue create`, la unidad congelada debe devolver `status: ok` para
`validar-publicacion <registro_abs> <scratch_abs> <recibo_simulacion_abs>`. Ese recibo
es el de la simulación vigente del único ID definitivo; la validación comprueba sus bytes,
el registro actual y el campo `Skill` único y no vacío en una línea física exterior a cercas
de la imagen. Un `10` exige resimular antes de crear el issue; un `12` detiene la
publicación para decisión humana; no se infiere `Skill` de `Skill / sección`. Este preflight
no se ejecuta si el incidente se resolvió aguas arriba y se retirará sin issue.

POSIX, con las variables de la vuelta y el recibo que devolvió la simulación:

```sh
registro_retiro validar-publicacion "$registro_abs" "$scratch_vuelta" "$recibo_simulacion"
```

PowerShell, con las variables equivalentes:

```powershell
if (-not (Get-Command Invoke-RegistroRetiro -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de retiro no cargada'); exit 3 }
$publicacionJson = Invoke-RegistroRetiro -Argumentos @('validar-publicacion', $registroAbs, $scratchVuelta, $reciboSimulacion)
$publicacionCodigo = $LASTEXITCODE
$publicacionJson
if ($null -eq $publicacionCodigo -or -not $publicacionJson) { [Console]::Error.WriteLine('Respuesta de publicación ausente'); exit 3 }
if ($publicacionCodigo -ne 0) { exit $publicacionCodigo }
```

Leer el JSON y el código de salida; solo `0` permite pasar a `gh issue create`.

```bash
# 1. ya volcado? — busca el ID de registro entre abiertos Y cerrados
gh issue list --repo <owner/repo> --state all --search '"DD/MM/AAAA HH:MM"' \
  --json number --jq '.[].number'

# 2. publicar (el cuerpo va por archivo: el markdown con backticks rompe el quoting)
gh issue create --repo <owner/repo> --title "[<skill>] <titular>" \
  --body-file <ruta/al/cuerpo.md> \
  --label "skill:<nombre>" --label "severidad:<n>" --label "needs-triage" \
  --label "plataforma:<p>" --label "transporte:<t>"   # omitir la que el registro no declare

# 3. cotejar lo publicado contra la imagen de simulación, antes de retirar
gh issue view <n> --repo <owner/repo> --json body --jq .body > <ruta/al/publicado.md>
```

PowerShell usa los mismos comandos: `gh` no cambia de sintaxis entre shells, y el cuerpo viaja por
`--body-file` en las dos.

### Los issues relacionados

El registro tiene **tres** relaciones distintas y se confunden con facilidad, porque las tres se
dicen "está relacionado con". Cada una tiene su mecanismo:

| Relación | Qué significa | Cómo se expresa |
|---|---|---|
| **Reincidencia** (campo `Relacionado`) | el **mismo** defecto volvió a aparecer | mención `#<n>` en el cuerpo del issue nuevo |
| **Agrupamiento** (paso 3) | defectos **distintos** que se resuelven en el mismo diff | un flujo, y su PR declara un `Closes #<n>` por cada uno |
| **Redimensionado** (paso 2) | el issue describe **otro** defecto del que dice | issue nuevo que lo menciona; el viejo se cierra apuntando al nuevo |

> **Una reincidencia NO se cierra como duplicada.** Es el reflejo natural en GitHub y borra
> exactamente lo que la regla 2 del registro protege: la **frecuencia** es lo único que distingue una
> trampa estructural de la skill de un descuido puntual. Tres issues abiertos sobre el mismo defecto
> son el dato, no ruido a limpiar. Se cierran juntos cuando el arreglo llega —un PR puede declarar
> varios `Closes`—, nunca antes y nunca por parecidos.

**La mención hace el trabajo sola, y en las dos direcciones.** Escribir `#<n>` en el cuerpo del issue
nuevo agrega la referencia al timeline del viejo **sin editarlo**. Eso es la regla 2 del registro
—"una reincidencia se agrega, nunca se edita"— cumplida por el mecanismo y no por disciplina.

**Resolver la fecha a un número, al volcar.** El campo `Relacionado` cita una fecha y hora, que es el
ID del registro. Buscarla como cualquier ID (el comando de idempotencia) y escribir las dos cosas:
`` `27/08/2026 17:12` (#12) ``. La fecha se conserva porque es el ID canónico y sobrevive a que el
issue se borre; el número, porque es lo que GitHub enlaza.

**Publicar en orden cronológico ascendente** es lo que hace que el número exista cuando se lo
necesita: una reincidencia siempre cita a su antecedente, nunca al revés. Medido sobre el registro
vivo: de 18 incidentes con `Relacionado`, **cero** apuntan a un incidente posterior.

**Si el antecedente no tiene issue**, se deja la fecha sola y se dice por qué —"antecedente retirado
del registro antes del volcado"—. Pasa: en el mismo registro, 3 de esas 18 referencias apuntan a
incidentes que ya no están en el archivo. Inventar un número o silenciar la referencia son las dos
formas de perder el rastro.

El cotejo conserva exactamente la fecha original. Solo una fecha local del origen admite el número
del issue o un motivo no vacío añadido tras un límite no alfanumérico; no se exige una raya concreta.
Un origen `—` no puede adquirir un número. El cotejo acredita la presencia de texto en el motivo,
no su veracidad: si el antecedente realmente carece de issue sigue siendo un juicio del conductor.

### El cotejo, y por qué línea por línea

Antes de retirar, cada línea sustantiva del tramo tomado de **`snapshot_path` del recibo de
simulación vigente** tiene que aparecer en el cuerpo publicado o ya existente. No usar una lectura
nueva del registro ni el candidato de retiro para reconstruir ese cuerpo. Un issue ya publicado
se coteja igual, sin segunda publicación; su identidad queda en el evento de efecto o en la
reconciliación humana. El cotejo exige el título sin fecha y con skill, cada campo por valor,
separadores y pie de procedencia según «El formato del issue», y los bloques sustantivos
verbatim. Una etiqueta citada dentro de una cerca no aporta un campo de cabecera: cada cerca,
incluidos sus delimitadores y separadores citados, se coteja como bloque contiguo dentro del cuerpo
verbatim y conserva la multiplicidad de bloques repetidos.
Las líneas sustantivas exteriores a cercas se cotejan solo con líneas exteriores del cuerpo verbatim,
consumiendo una ocurrencia por cada línea original; una copia en la cabecera, el pie o una cerca no la suple.
Solo se admiten las transformaciones nombradas aquí; no se exige igualdad de bytes
del cuerpo completo, pero tampoco se acepta pérdida de una línea o campo.
En particular, cada línea sustantiva del original tiene que aparecer en algún cuerpo publicado.
Se saltean las vacías, los separadores, las cabeceras de tabla y el encabezado `##` —que vive en el
título—; las filas de campos se cotejan por su **valor**, porque el formato las transformó.

Un muestreo no alcanza: lo que se pierde en un volcado no es un bloque entero sino un **campo**, y un
campo ausente se lee igual de bien que uno presente.
Al cotejar un issue ya existente, buscar las cabeceras de campos solo **antes del primer `---`**:
una línea igual en el bloque verbatim no reemplaza la cabecera ausente ni la duplica.
Las etiquetas del registro que la plantilla deja en el bloque verbatim se exigen allí como líneas
sustantivas, no como cabeceras; la lista de campos de siembra no define el encabezado del issue.

### Dos formas de leer un verde que no lo es

- **El campo que desaparece al parsear.** Extraer los campos con una clase de caracteres que no cubra
  los acentos minúsculos hace que `Sección` no matchee, y el campo se cae **sin error**. Medido: se
  perdió en los cuatro incidentes de un volcado y solo lo delató el conteo de campos, que dio seis
  donde debía dar siete. Contar los campos extraídos contra los esperados, y no confiar en que el
  parseo anduvo porque no tiró excepción.
- **El `gh` que corre fuera del repo.** Sin `--repo` y con el cwd fuera del árbol, `gh` falla con
  `not a git repository` y **escribe un archivo vacío**. Un `grep` posterior sobre ese archivo informa
  que el contenido falta, que es lo mismo que informaría si de verdad faltara. Pasar `--repo` siempre,
  y comprobar el tamaño de lo descargado antes de creerle a la comparación.

## Retirar del registro

No editar por offset ni ejecutar `grep` como acreditación. La barrera usa **la unidad congelada de
la vuelta** y cuatro modos en este orden: `simular-retiro` antes del efecto, `revalidar-retiro`
después de acreditarlo, `escribir-retiro` solo con recibo `0`, y `cotejar-retiro`. `volcar` opera
una vuelta por issue; `despachar` usa una vuelta por grupo o rechazo. El registro recibido debe
ser una ruta absoluta a archivo regular con un solo enlace; el `lstat` y la escritura usan esa
ruta, no `registro_fisico`, que solo informa. El scratch es el de «Preparar y reanudar la vuelta
congelada», nunca el intento de siembra de 6.2. No retirar con `registro: issues`.

`simular-retiro <registro_abs> <scratch_abs> <nuevo|nuevo-post-efecto|recibo_raiz_abs> <id>...`
exige los últimos IDs del evento `ids-definitivos`. `nuevo` crea raíz antes del efecto;
no distingue si `volcar` publicará un issue o retirará un incidente resuelto aguas arriba.
Antes de **crear** un issue, `validar-publicacion <registro_abs> <scratch_abs>
<recibo_simulacion_abs>` exige raíz `nuevo`, único ID definitivo, recibo e imagen intactos,
registro sin deriva y exactamente un `Skill` no vacío. Devuelve JSON con `status: ok`,
`ids`, `titulo`, `skill`, `simulacion_ruta` y `unit_sha256`, sin recibo de éxito. La unidad
usa las líneas físicas LF/CRLF y las cercas reconocidas por el análisis de retiro; FF, VT y
separadores Unicode son contenido, no cortes. Un `10` con recibo exige resimular antes de
publicar; un `12` con recibo detiene si falta el campo; `Skill / sección` no lo sustituye.
Este preflight no autoriza repetir una
publicación ni sustituye el cotejo post-efecto del título, campos y bloque verbatim.
`nuevo-post-efecto` exige reconciliación y aprobación humana separada, y **no habilita repetir
despacho ni publicación**. Tras `10`, pasar siempre el recibo **raíz**, no el de la última
simulación, con idénticos IDs. Si cambia un ID antes del efecto, registrar nuevos IDs y hacer
otra raíz. Una simulación nunca escribe el registro: guarda imagen, candidato y recibo exclusivos.
El recibo raíz permanece inmutable a través de todos los anexos.
Una resimulación desde esa raíz **antes** del efecto conserva `evento_efecto_ruta: null`:
revalidarla después es válida si el evento causal actual corresponde a los IDs y la primera
raíz. Una resimulación posterior al efecto lleva la ruta de ese evento; una ruta distinta detiene.

Para `nuevo-post-efecto`, el evento `reconciliacion-aprobada` lleva `identidad`,
`cotejo_ruta`, `cotejo_sha256` y decisión humana literal. `cotejo_ruta` es un JSON privado del
scratch con esquema `reconciliacion-cotejo/1` y **exactamente** `schema_version`, `modo`
(`despachar` o `volcar`), `ids`, `identidad`, `externo_ruta`, `externo_sha256` y `titulo`
(`null` para dossier original; título observado para issue). La unidad comprueba digest,
identidad e IDs, lee el externo regular sin seguir enlace final y coteja contenido desde la
   instantánea fresca: en `despachar`, cada incidente desde su H2, incluidos sus terminadores
   de línea, aparece **byte a byte una vez** al inicio de línea y termina ante el siguiente H2,
   un separador estructural o el fin de la versión **original** del dossier asociado. Un dossier
   redimensionado conserva esa versión original y abre el diagnóstico corregido con un H2 propio.
   En `volcar`, un solo ID, título sin fecha, campos por etiqueta/valor y líneas
sustantivas del issue existente. El conductor acredita aparte la asociación del dossier/issue
con el efecto real y la aprobación humana; **un JSON inventado no prueba permiso humano**.
Si falta la versión original, es ilegible o difiere, no crear raíz post-efecto ni retirar.

Tras acreditar la identidad externa y recibir la decisión humana, `preparar-cotejo` crea ese
JSON en el scratch de la vuelta congelada, por apertura exclusiva, ASCII escapado y SHA-256
minúsculo. No usar `ConvertTo-Json` ni `Get-FileHash` para escribirlo o calcular su digest:
PowerShell puede emitir Unicode literal y hex mayúsculo, incompatibles con la unidad. El archivo
externo debe ser la **versión original** del dossier (`despachar`) o el cuerpo observado del issue
(`volcar`), en ruta absoluta y archivo regular de un solo enlace. El conductor comprueba que
corresponde al efecto real; el modo solo prepara bytes y no acredita esa asociación ni el permiso.
En un shell nuevo, ejecutar antes el bloque de reentrada de «Preparar y reanudar la vuelta
congelada». Pasar de nuevo los IDs definitivos como argumentos de **esta** etapa.

POSIX (`titulo_observado` es `-` solo para `despachar`; para `volcar` es el título literal
observado, con prefijo `[skill]`):

```sh
identidad='identidad externa acreditada'; externo_ruta='/ruta/absoluta/al/original-o-cuerpo'; titulo_observado='-'
[ "$#" -gt 0 ] && [ -n "$identidad" ] && [ -n "$externo_ruta" ] || exit 2
solicitud64=$(python3 -c 'import base64,json,sys; identity,external,title,*ids=sys.argv[1:]; payload=dict(ids=ids,identidad=identity,externo_ruta=external,titulo=None if title=="-" else title); print(base64.b64encode(json.dumps(payload,ensure_ascii=False).encode("utf-8")).decode("ascii"))' "$identidad" "$externo_ruta" "$titulo_observado" "$@") || exit 3
if cotejo_json=$(registro_retiro preparar-cotejo "$scratch_vuelta" "$registro_abs" "$solicitud64"); then cotejo_codigo=0; else cotejo_codigo=$?; fi
printf '%s\n' "$cotejo_json"; [ "$cotejo_codigo" -eq 0 ] || exit "$cotejo_codigo"
cotejo_ruta=$(printf '%s' "$cotejo_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cotejo_ruta"])') || exit 3
cotejo_sha256=$(printf '%s' "$cotejo_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cotejo_sha256"])') || exit 3
```

PowerShell (`$tituloObservado = $null` solo para `despachar`; para `volcar`, título
literal observado). Ejecutar como `.ps1` con los IDs de la etapa, según el contrato de `$args`
de arriba:

```powershell
$identidad = 'identidad externa acreditada'; $externoRuta = '/ruta/absoluta/al/original-o-cuerpo'; $tituloObservado = $null
$idsDefinitivos = @($args)
if (-not $identidad -or -not $externoRuta -or $idsDefinitivos.Count -eq 0) { throw 'Faltan datos o IDs del cotejo' }
$solicitud = @{ ids = $idsDefinitivos; identidad = $identidad; externo_ruta = $externoRuta; titulo = $tituloObservado }
$solicitud64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $solicitud -Compress -Depth 8)))
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Python no disponible'); exit 3 }
$cotejoJson = py -3 $unidad preparar-cotejo $scratchVuelta $registroAbs $solicitud64
$cotejoCodigo = $LASTEXITCODE
$cotejoJson
if ($cotejoCodigo -ne 0) { if (-not $cotejoJson -or $cotejoCodigo -notin @(2, 3, 12)) { exit 3 }; exit $cotejoCodigo }
try { $cotejo = $cotejoJson | ConvertFrom-Json -ErrorAction Stop } catch { [Console]::Error.WriteLine('Respuesta de cotejo inválida'); exit 3 }
if (-not $cotejo.cotejo_ruta -or -not $cotejo.cotejo_sha256 -or -not $cotejo.externo_sha256) { [Console]::Error.WriteLine('Cotejo sin rutas o digests'); exit 3 }
$cotejoRuta = $cotejo.cotejo_ruta; $cotejoSha256 = $cotejo.cotejo_sha256
```

Comprobar en el JSON devuelto `cotejo_ruta`, `cotejo_sha256` y `externo_sha256` contra
el archivo externo observado. Solo entonces usar la variante `reconciliacion-aprobada` del
bloque «Registrar eventos de la vuelta», con la **decisión humana literal** y los mismos IDs.
Si esa etapa corre en otro `.ps1`, reconstruir `$cotejoRuta` y `$cotejoSha256` desde los
valores literales del JSON impreso: las variables del primer proceso no sobreviven.
Después invocar `simular-retiro … nuevo-post-efecto`: la unidad coteja el contenido y detiene
con `12` si el externo, título, ID o digest no corresponde; no repetir el efecto externo.

El modo reconoce la línea física de cabecera
`Los registros van en **orden cronológico ascendente**.` exactamente una vez, antes de `Índice`
y fuera de cercas; solo descarta el terminador LF/CRLF para comparar. Sin ella, duplicada o fuera
de sitio: `12`, corregir cabecera, pedir otra simulación y **bloquear todo retiro**. Las filas se
identifican por primera celda, con backticks opcionales, y las secciones por H2 exterior.
Ambas series deben ser fechadas, únicas y ascendentes por separado: `DD/MM/AAAA HH:MM`,
`AAAA-MM-DD HH:MM`, `AAAA-MM-DDTHH:MM` o fecha ISO sola a `00:00`, validadas como tuplas
calendario sin conversión de zona. Un ID no fechado —incluidos números e `Incidente INC-…`—,
inválido o fuera de orden bloquea **todo** el retiro (`12` antes del efecto; deriva `11`
después): pedir decisión humana, no corregir otros incidentes dentro de intake. No se exige
biyección histórica: una sección sin fila puede retirarse; fila objetivo sin sección o ID
objetivo ausente/duplicado no. El candidato quita filas y secciones elegidas, incluidos sus
separadores propios; conserva bytes ajenos y el cierre de cabecera cuando retira todos. En legado
vacío conserva el comentario en su posición original y no añade otro cierre; el próximo alta va
**después** del comentario, con blanco.

`plazo-retiro <registro_abs> <scratch_abs>` devuelve `sin-iniciar`, `vigente` o
`tiempo-agotado` en JSON ASCII; en la última clase, `motivo` distingue `plazo-vencido` de
`reloj-retrocedido`. Antes de **cada** resimulación y revalidación y al reentrar,
consultarlo y detener sin invocar otra etapa ante `tiempo-agotado`, reloj retrocedido o sello
inválido. La primera revalidación crea exclusivamente `plazo-retiro.json` con inicio UTC,
límite a 120 segundos y ancla monotónica para contrastar el avance del reloj entre procesos;
no se modifica el sello. Si el reloj UTC avanza menos que esa ancla o la ancla retrocede,
la consulta se detiene con `motivo: reloj-retrocedido`, también dentro de la ventana UTC.
Solo con `motivo: plazo-vencido`, pedir autorización humana para nueva ventana y registrar
`ventana-plazo-aprobada` con `plazo_anterior`, `plazo_nuevo` y decisión literal; la unidad exige
vencimiento anterior y plazo nuevo posterior. `motivo: reloj-retrocedido` también cubre un reinicio
del monotónico: conservar scratch, imagen y efecto y pedir reconciliación humana; una nueva ventana
UTC no corrige el ancla inicial inmutable. Nunca sobrescribir el sello ni reiniciar automáticamente.
El vencimiento es una parada del conductor, **no** deriva `11`: los modos
`simular-retiro`, `revalidar-retiro` y `escribir-retiro` imprimen el estado JSON con código `3`,
sin crear recibo ni escribir el registro. El modo de consulta `plazo-retiro` conserva código `0`.

Tras aprobación **explícita** de otra ventana, conservar la respuesta humana literal y elegir
`plazo_nuevo` UTC. Estos bloques solo serializan y publican el evento; no sustituyen ese gate:

```sh
plazo_json=$(python3 "$unidad" plazo-retiro "$registro_abs" "$scratch_vuelta") || exit 3
[ "$(printf '%s' "$plazo_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["status"], d["motivo"])')" = 'tiempo-agotado plazo-vencido' ] || { printf '%s\n' 'Ventana no renovable: conservar residual y pedir decisión humana' >&2; exit 3; }
plazo_anterior=$(printf '%s' "$plazo_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["limite_utc"])')
plazo_nuevo='AAAA-MM-DDTHH:MM:SSZ' # fijado tras el gate; posterior al instante actual
decision_humana='texto literal de aprobación'
datos_ventana=$(python3 -c 'import json,sys; print(json.dumps(dict(plazo_anterior=sys.argv[1],plazo_nuevo=sys.argv[2],decision=sys.argv[3]),ensure_ascii=True))' "$plazo_anterior" "$plazo_nuevo" "$decision_humana") || exit 1
ids_json=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:],ensure_ascii=True))' "$@") || exit 1
if evento_json=$(python3 "$unidad" registrar-evento "$scratch_vuelta" "$registro_abs" ventana-plazo-aprobada "$ids_json" "$datos_ventana"); then evento_codigo=0; else evento_codigo=$?; fi
printf '%s\n' "$evento_json"; [ "$evento_codigo" -eq 0 ] || exit "$evento_codigo"
```

```powershell
if (-not (Get-Command Invoke-RegistroEvento -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de evento no cargada'); exit 3 }
$plazoJson = py -3 $unidad plazo-retiro $registroAbs $scratchVuelta
if ($LASTEXITCODE -ne 0) { throw 'Plazo de retiro no validado' }
$plazo = $plazoJson | ConvertFrom-Json
if ($plazo.status -ne 'tiempo-agotado' -or $plazo.motivo -ne 'plazo-vencido') { [Console]::Error.WriteLine('Ventana no renovable: conservar residual y pedir decisión humana'); exit 3 }
$plazoAnterior = $plazo.limite_utc
$plazoNuevo = 'AAAA-MM-DDTHH:MM:SSZ' # fijado tras el gate; posterior al instante actual
$decisionHumana = 'texto literal de aprobación'
$idsDefinitivos = @($args) # mismos IDs definitivos, dados otra vez en esta etapa
if ($idsDefinitivos.Count -eq 0) { throw 'Faltan IDs de la ventana aprobada' }
$datosVentana = @{ plazo_anterior = $plazoAnterior; plazo_nuevo = $plazoNuevo; decision = $decisionHumana }
Invoke-RegistroEvento -Tipo 'ventana-plazo-aprobada' -Ids $idsDefinitivos -Datos $datosVentana
```

`revalidar-retiro <registro_abs> <scratch_abs> <recibo_simulacion_abs>` compara bytes e
identidad de dispositivo/inode contra la simulación vigente y todos los tramos/límites contra la
primera raíz. `0` solo con igualdad exacta y recibo que enlaza imagen/candidato; `10` ante
identidad nueva con bytes iguales o anexo benigno, incluida sección nueva sin fila y blancos
finales que pasan a separador. Una fila nueva necesita sección nueva; intercalación, edición de
fila/sección tomada o límite, o anexo no posterior después del efecto dan `11` con residual.
Symlink/hardlink nuevo da `12`. No hay cuota de anexos; cada `10` exige resimular desde la raíz.

`escribir-retiro <registro_abs> <scratch_abs> <recibo_revalidacion_0_abs>` comprueba de nuevo
imagen, inode y digest del candidato. Si el origen cambió, propaga la nueva revalidación
`10/11/12` sin escribir; con igualdad copia el candidato a temporal del mismo directorio,
conserva modo, lo reemplaza atómicamente y deja **la imagen de la simulación** como respaldo.
El recibo de escritura es `pendiente-cotejo`, no acreditación. Escritores no cooperantes aún
pueden correr entre el último `lstat` y el reemplazo: detener y reconciliar si aparecen.
`cotejar-retiro <registro_abs> <scratch_abs> <recibo_revalidacion_0_abs> <resultado_abs>`
reconstruye independientemente filas y secciones desde la imagen, **sin leer el candidato del
simulador como esperado**, y compara bytes actuales y digest del resultado. Solo `acreditado`
permite avanzar; `11` conserva respaldo y residual, sin repetir el efecto.

Bloque POSIX por etapa (definir `registro_abs`, `scratch_vuelta`, `unidad` y `recibo_raiz`
con rutas literales; `set --` contiene los IDs definitivos). El efecto externo y su cotejo
ocurren **entre** la primera y la segunda llamada; al reentrar reconstruir esas variables y
los recibos por ruta literal antes de la segunda:

```sh
if plazo_json=$(registro_retiro plazo-retiro "$registro_abs" "$scratch_vuelta"); then
  plazo_estado=$(printf '%s' "$plazo_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])') || exit 3
  [ "$plazo_estado" != tiempo-agotado ] || { printf '%s\n' 'Tiempo agotado: decisión humana' >&2; exit 3; }
else
  plazo_codigo=$?; printf '%s\n' "$plazo_json"; printf '%s\n' 'Consulta de plazo no acreditada' >&2; exit "$plazo_codigo"
fi
if etapa_json=$(registro_retiro simular-retiro "$registro_abs" "$scratch_vuelta" "$recibo_raiz" "$@"); then etapa_codigo=0; else etapa_codigo=$?; fi
printf '%s\n' "$etapa_json"
[ "$etapa_codigo" -eq 0 ] || exit "$etapa_codigo"
recibo_simulacion=$(printf '%s' "$etapa_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["recibo_ruta"])') || exit 3
# Tras acreditar el efecto, reconstruir rutas literales y releer plazo en el shell actual.
if plazo_json=$(registro_retiro plazo-retiro "$registro_abs" "$scratch_vuelta"); then
  plazo_estado=$(printf '%s' "$plazo_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])') || exit 3
  [ "$plazo_estado" != tiempo-agotado ] || { printf '%s\n' 'Tiempo agotado: decisión humana' >&2; exit 3; }
else
  plazo_codigo=$?; printf '%s\n' "$plazo_json"; printf '%s\n' 'Consulta de plazo no acreditada' >&2; exit "$plazo_codigo"
fi
if etapa_json=$(registro_retiro revalidar-retiro "$registro_abs" "$scratch_vuelta" "$recibo_simulacion"); then etapa_codigo=0; else etapa_codigo=$?; fi
printf '%s\n' "$etapa_json"
[ "$etapa_codigo" -eq 0 ] || exit "$etapa_codigo"
recibo_revalidacion=$(printf '%s' "$etapa_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["recibo_ruta"])') || exit 3
if etapa_json=$(registro_retiro escribir-retiro "$registro_abs" "$scratch_vuelta" "$recibo_revalidacion"); then etapa_codigo=0; else etapa_codigo=$?; fi
printf '%s\n' "$etapa_json"
[ "$etapa_codigo" -eq 0 ] || exit "$etapa_codigo"
resultado=$(printf '%s' "$etapa_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["recibo_ruta"])') || exit 3
if etapa_json=$(registro_retiro cotejar-retiro "$registro_abs" "$scratch_vuelta" "$recibo_revalidacion" "$resultado"); then etapa_codigo=0; else etapa_codigo=$?; fi
printf '%s\n' "$etapa_json"
[ "$etapa_codigo" -eq 0 ] || exit "$etapa_codigo"
```

Bloque PowerShell equivalente, en shell nuevo **tras ejecutar el bloque de reentrada**
de «Preparar y reanudar la vuelta congelada», con `$unidad`, `$registroAbs`,
`$scratchVuelta`, `$reciboRaiz` y `$idsDefinitivos` reconstruidos literalmente. Al reentrar
**después del efecto**, reconstruir también `$reciboSimulacion` con la ruta literal de
`recibo_ruta` del JSON de simulación impreso antes del efecto; no repetir la simulación ni
depender del objeto `$simulacion` del shell anterior. Conservar el
`$LASTEXITCODE` **inmediatamente** después de cada llamada antes de convertir JSON:

```powershell
if (-not (Get-Command Invoke-RegistroRetiro -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de retiro no cargada'); exit 3 }
$plazoJson = Invoke-RegistroRetiro -Argumentos @('plazo-retiro', $registroAbs, $scratchVuelta)
$plazoCodigo = $LASTEXITCODE
if ($plazoCodigo -ne 0) { $plazoJson; [Console]::Error.WriteLine('Consulta de plazo no acreditada'); exit $plazoCodigo }
try { $plazoEstado = ($plazoJson | ConvertFrom-Json).status } catch { [Console]::Error.WriteLine('Respuesta de plazo inválida'); exit 3 }
if ($plazoEstado -eq 'tiempo-agotado') { [Console]::Error.WriteLine('Tiempo agotado: decisión humana'); exit 3 }
if ($plazoEstado -notin @('vigente', 'sin-iniciar')) { [Console]::Error.WriteLine('Estado de plazo inválido'); exit 3 }
$etapaJson = Invoke-RegistroRetiro -Argumentos (@('simular-retiro', $registroAbs, $scratchVuelta, $reciboRaiz) + @($idsDefinitivos))
$etapaCodigo = $LASTEXITCODE
$etapaJson
if ($etapaCodigo -ne 0) { exit $etapaCodigo }
try { $simulacion = $etapaJson | ConvertFrom-Json } catch { [Console]::Error.WriteLine('Respuesta de simulación inválida'); exit 3 }
$reciboSimulacion = $simulacion.recibo_ruta
# Tras acreditar el efecto, reconstruir rutas literales y releer plazo en el shell actual.
if (-not (Get-Command Invoke-RegistroRetiro -CommandType Function -ErrorAction SilentlyContinue)) { [Console]::Error.WriteLine('Función de retiro no cargada'); exit 3 }
$plazoJson = Invoke-RegistroRetiro -Argumentos @('plazo-retiro', $registroAbs, $scratchVuelta)
$plazoCodigo = $LASTEXITCODE
if ($plazoCodigo -ne 0) { $plazoJson; [Console]::Error.WriteLine('Consulta de plazo no acreditada'); exit $plazoCodigo }
try { $plazoEstado = ($plazoJson | ConvertFrom-Json).status } catch { [Console]::Error.WriteLine('Respuesta de plazo inválida'); exit 3 }
if ($plazoEstado -eq 'tiempo-agotado') { [Console]::Error.WriteLine('Tiempo agotado: decisión humana'); exit 3 }
if ($plazoEstado -notin @('vigente', 'sin-iniciar')) { [Console]::Error.WriteLine('Estado de plazo inválido'); exit 3 }
$etapaJson = Invoke-RegistroRetiro -Argumentos @('revalidar-retiro', $registroAbs, $scratchVuelta, $reciboSimulacion)
$etapaCodigo = $LASTEXITCODE
$etapaJson
if ($etapaCodigo -ne 0) { exit $etapaCodigo }
try { $revalidacion = $etapaJson | ConvertFrom-Json } catch { [Console]::Error.WriteLine('Respuesta de revalidación inválida'); exit 3 }
$etapaJson = Invoke-RegistroRetiro -Argumentos @('escribir-retiro', $registroAbs, $scratchVuelta, $revalidacion.recibo_ruta)
$etapaCodigo = $LASTEXITCODE
$etapaJson
if ($etapaCodigo -ne 0) { exit $etapaCodigo }
try { $resultado = $etapaJson | ConvertFrom-Json } catch { [Console]::Error.WriteLine('Respuesta de escritura inválida'); exit 3 }
$etapaJson = Invoke-RegistroRetiro -Argumentos @('cotejar-retiro', $registroAbs, $scratchVuelta, $revalidacion.recibo_ruta, $resultado.recibo_ruta)
$etapaCodigo = $LASTEXITCODE
$etapaJson
if ($etapaCodigo -ne 0) { exit $etapaCodigo }
```

En la primera simulación, `recibo_raiz`/`$reciboRaiz` vale literalmente `nuevo` o
`nuevo-post-efecto`; luego es la ruta del recibo raíz. Los cuatro modos de retiro emiten
JSON ASCII y recibo exclusivo para salidas semánticas `0/10/11/12`; `validar-publicacion`
emite JSON sin recibo en `0` y recibo semántico en `10/11/12`. `2` es invocación errónea y `3`
detiene sin recibo ante un fallo de ejecución o una etapa que no se ejecuta por plazo vencido.
Todo recibo lleva esquema, ruta recibida/física, IDs, digest de
entrada/unidad, imagen y, cuando existe, candidato/digest y respaldo; escritura añade digest
de salida. **Frontera:**

| Modo | Qué acredita `0` | No detecta | Clase de salida | Dirección de error |
|---|---|---|---|---|
| `plazo-retiro` | estado de ventana UTC y avance respecto del ancla monotónica; `tiempo-agotado` detiene por vencimiento o reloj retrocedido | cambios del reloj compensados por otro ajuste antes de consultar, ni identidad de arranque tras reiniciar el host | `veredicto` | `las dos`: un ajuste compensado puede quedar invisible; un reinicio del monotónico puede detener de más |
| `simular-retiro` | estructura, cronología y candidato para los IDs definitivos | realidad del efecto externo | `veredicto` | `las dos`: la gramática puede aceptar un límite que el cotejo rechace o rechazar una forma exterior válida |
| `validar-publicacion` | recibo vigente, imagen y campo `Skill` antes de crear un issue | realidad del issue aún no publicado ni verdad del valor de `Skill` | `veredicto` | `las dos`: una sintaxis de campo no reconocida puede detener un volcado válido; un valor formalmente presente puede ser inexacto |
| `revalidar-retiro` | identidad, anexos y ausencia de deriva observada frente a la simulación | permiso humano o escritor no cooperante posterior a la lectura | `veredicto` | `las dos`: una frontera mal clasificada acepta deriva o rechaza un anexo benigno |
| `escribir-retiro` | reemplazo por el candidato sellado tras comparar la imagen observada | escrituras ajenas concurrentes después de la última comprobación | `veredicto` | `admite-de-mas`: un escritor no cooperante puede invalidar el resultado sin que el código lo vea |
| `cotejar-retiro` | bytes actuales contra la expectativa del recorrido independiente | acreditación del efecto externo | `veredicto` | `las dos`: una divergencia de gramática puede aceptar bytes indebidos o rechazar un candidato correcto |

Los códigos `10/11/12` son paradas semánticas con recibo; un fallo de ejecución
`3` se declara aparte, conserva los residuales y detiene.

---

## El contrato de fallo por fase

Cada efecto de este paso puede fallar **después** de haber dejado algo en pie. Sin una regla por
fase, el intento siguiente duplica recursos o abandona una corrida viva. Una fila por efecto:

| Fase | Observable previo | Qué queda ligado a la corrida | Si falla | Registro e issue | Residuales | Reintento |
|---|---|---|---|---|---|---|
| resolver plataforma | — | nada | se detiene | intactos | ninguno | inmediato |
| clasificar el hook | plataforma resuelta | nada | se detiene | intactos | ninguno | inmediato |
| crear el worktree | identidad revalidada | el árbol, si alcanzó a crearse | se detiene | intactos | **el árbol no se elimina**: su ciclo de vida es el del flujo, no el de este paso. Se enumera | el intento siguiente **adopta** el árbol existente si su rama y su commit coinciden; si no, para y lo muestra |
| ejecutar el hook | árbol creado | el árbol, ya creado | se detiene | intactos | el árbol, y lo que el hook haya escrito | no se re-ejecuta el hook sobre un árbol a medias: se descarta el árbol **con confirmación** y se recrea |
| sembrar configuración | árbol creado | el árbol y la configuración copiada | se detiene | intactos | lo copiado | se completa esa configuración sobre el mismo árbol; **no** se borra ni reclasifica por esta fila un registro preexistente o residual |
| resolver el registro declarado | árbol creado | el árbol; ningún registro nuevo | se detiene ante instrucciones ambiguas, divergentes o ruta fuera del árbol | intactos | el árbol y todo archivo previo | decisión humana sobre instrucciones/ruta y nueva comparación de ambas tuplas, sin que el intake edite las instrucciones |
| inspeccionar registro previo | tupla concordante y procedencia acreditada | archivo existente intacto y `scratch/previo` por creación exclusiva | se detiene si no es utilizable, repite un ID dentro del Índice/secciones, coincide con cualquier ID del grupo o su procedencia es incierta | intactos | árbol, archivo previo y `scratch/previo` | inválido o ID duplicado: corrección/decisión sobre ese archivo; procedencia incierta: inspeccionar y aceptar como preexistente **solo si resulta utilizable**, con estado y cantidad observados, autorizar retiro y nueva siembra, o abandonar; nunca vaciarlo automáticamente |
| elegir fuente y preparar candidato | ruta declarada ausente en el worktree | árbol, `scratch/fuente`, `scratch/inventario`, `scratch/mapa` y candidato si se crearon | se detiene si falta cabecera inequívoca, la clasificación es ambigua, el mapa es inválido o falla el cotejo independiente | intactos | árbol y cada temporal existente, con sus rutas y digests disponibles | fuente ausente: aprobación de archivo y ruta física concretos; **mapa inválido**: mostrar primer tramo esperado/recibido y pedir decisión humana para abandonar o crear nueva instantánea/inventario/mapa; cotejo fallido: decisión humana antes de otra vuelta; nunca usar el registro de entrada automáticamente |
| publicar registro declarado | candidato acreditado por `cotejar` y ruta ignorada | archivo publicado si la creación exclusiva llegó a escribirlo; scratch con mapa retenido para 6.3 | colisión: volver a inspección sin sobrescribir; ruta no ignorada o comprobación de bytes/Git fallida: se detiene | intactos | árbol, scratch y archivo publicado si existe, todos enumerados | solo avanzar tras acreditar el nuevo estado; un publicado residual no se convierte en preexistente por inferencia ni se borra sin decisión |
| escribir el dossier | estado distinto de `detenido`; si `sembrado`, mapa y digests acreditados en scratch | árbol, registro, `scratch/mapa` y dossier parcial | se detiene ante escritura fallida, marcadores ambiguos o digest/bytes del mapa distintos en sección 9 | intactos | árbol, registro, scratch con mapa y dossier parcial, cada uno enumerado | reescribir el dossier entero, no parchar; verificar bloque literal y digest antes de limpiar scratch; no reetiquetar el registro como preexistente ni retirarlo automáticamente |
| adoptar y abrir | identidad revalidada | el panel, si se abrió | se detiene | intactos | el panel | se cierra el panel con su modo de cierre y se reabre |
| arrancar el agente | panel abierto | el panel y el agente | el resultado se decide en «Esperar a que el agente esté listo», no por el código de salida | intactos | panel y agente | no liquida ni reintenta por su cuenta; sigue con la acreditación |
| acreditar identidad y readiness | panel abierto y arranque intentado | el panel siempre; el agente solo si `get` lo devolvió | **no confirmado** — se detiene sin liquidar | intactos; el incidente **no se retira** | el panel queda en pie; el agente se enumera solo si se acreditó que existe | solo la fila que reconsulta de «Esperar a que el agente esté listo» lo hace dentro del límite; las demás siguen su salida propia; agotado el límite, decisión del usuario. Rige el invariante de orden de esa sede |
| acreditar el arranque del flujo | reconocimiento acreditado | todo lo anterior | **no confirmado** | el incidente **no se retira**; el issue conserva su etiqueta del pool | el árbol y el panel quedan en pie, enumerados | decisión del usuario: reintentar el envío o abandonar la corrida |
| marcar el issue | arranque acreditado | la escritura externa | se detiene | el issue puede haber quedado a medias: se comprueba y se repara | ninguno | se repite la escritura, que es idempotente |
| simular retiro | IDs definitivos; gate de despacho resuelto si aplica, gate de rechazo todavía no abierto | raíz, imagen y candidato exclusivos | `12` o ejecución fallida: se detiene antes del efecto | registro intacto | scratch de vuelta y recibo si existe | corregir cabecera/ruta o decisión humana; nunca saltar la barrera |
| revalidar retiro | efecto acreditado y raíz válida | recibo de simulación vigente y respaldo | `10` resimula desde la raíz; `11/12` o plazo vencido detienen | doble sede hasta cotejo verde | scratch, raíz, imagen, IDs y efecto | sin segundo efecto; reconciliación humana si falta evidencia |
| escribir retiro | recibo de revalidación `0` | imagen de respaldo y resultado pendiente | cambio de origen propaga `10/11/12`; ejecución fallida detiene | doble sede; no afirmar retiro | respaldo y recibos | revalidar solo si la cadena sigue vigente, sin repetir efecto |
| cotejar retiro | resultado de escritura vinculado | imagen anterior y bytes actuales | `11` detiene sin revertir automáticamente | doble sede; registro escrito no acreditado | respaldo, resultado y recibos | decisión humana desde el respaldo, no completar por inferencia |

**Ninguna limpieza destructiva ocurre sin su gate.** Descartar un árbol, cerrar un panel con trabajo
sin cosechar o revertir una escritura externa se le pregunta al usuario; nada de eso se infiere de un
fallo.

**El registro de incidentes nunca se vacía como parte de una reversión.** Es la única copia de lo que
se iba a corregir, y un fallo de este paso no es motivo para perderla.

**Reentrada tras efecto.** Antes de repetir cualquier despacho o publicación en otra sesión,
cotejar el ID en `git worktree list --porcelain` y la plataforma activa, los dossiers/paneles
asociados y, para issues, los abiertos **y cerrados**. Si una superficie necesaria no se puede
consultar, detener para decisión humana; no deducir ausencia. Con scratch/recibo válidos,
cotejar el efecto existente y continuar **solo** el retiro. Si falta identidad, recibo o
acreditación, reconciliación humana. Una raíz `nuevo-post-efecto` de `despachar` requiere comparar
por cada ID los bytes verbatim de la instantánea fresca con la **versión original** del dossier
asociado al worktree (si hubo redimensionado, no la versión corregida). Worktree/panel existentes
no bastan. Dossier ilegible, no asociable inequívocamente o distinto: parar sin raíz nueva ni
retiro automático. El cambio de unidad instalada después del efecto se informa; la copia
congelada continúa. Antes del efecto, un cambio de unidad instalada exige otra vuelta.

## Cuando algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `agent start` devuelve `agent_not_ready` con el agente vivo y listo | **Hipótesis no comprobada:** el CLI puede reportar el error aunque el agente haya quedado disponible | Consultar las cuatro condiciones de «Esperar a que el agente esté listo» y continuar si acreditan; cualquier limpieza pasa por el gate del contrato de fallo por fase |
| El compositor no muestra la señal de reconocimiento | El prefijo entró dentro del texto pegado, se usó la forma de la otra familia —con espacio donde iba sin él, o al revés—, o actuó la conversión de rutas: en el compositor aparece una ruta absoluta del sistema de archivos en lugar del prefijo | Limpiar el compositor, restablecer readiness y **repetir desde el prefijo**, acreditando su reconocimiento antes de mandar el cuerpo. Ante la conversión de rutas, usar la forma con `MSYS_NO_PATHCONV=1` de la tabla de plataformas. Si no se acredita, el arranque queda **no confirmado** y no se retira nada. La ruta de la skill sirve para **diagnosticar** cuál está instalada, nunca como forma de activarla: pedirle al agente que la lea produce exactamente el arranque compensado que el control existe para rechazar |
| El compositor devuelve el marcador de colapso | El host colapsó el bloque pegado para mostrarlo; no dice nada sobre si el cuerpo llegó entero | Mandar el Enter igual: la lectura del compositor es una comprobación temprana y barata, y acá queda inconcluyente y no negativa. Un cuerpo truncado ya no lo caza el cierre —ver «Confirmar el arranque»—, lo delata el primer artefacto que el flujo somete a gate |
| El flujo pregunta cosas que el config ya responde | El worktree no está sembrado | Sembrar `.specify/` del `<repo_destino>` y avisarle al agente que relea el config |
| El flujo arranca un `init` que nadie pidió | Igual que arriba, caso agudo | Igual, y verificar que el `init` no haya sobrescrito nada |
| `git status` del worktree muestra la configuración sembrada | El destino no ignora esos paths | Sacar del árbol la configuración sembrada y resolver su ignore antes de seguir; esta salida **no** borra registros preexistentes ni residuales de siembra del registro |
| El diff del flujo sale contra un árbol raro | El worktree nació en la referencia remota por defecto | Solo puede pasar en la rama `inseparable`, que es la única que conserva la creación de la plataforma; con creación por Git el commit va explícito y el caso no existe. Ya avanzado, es rebase — y el techo de proporción del repo, si lo tiene, se midió contra el commit equivocado |
| El registro quedó sin la fila pero con la sección | Se editó fuera de la cadena simulación/revalidación/escritura/cotejo | Detener con doble sede y respaldo; reconciliar humanamente, no completar por offset. **Registrar el incidente**: es un defecto de procedimiento |
| El flujo abre un diff sobre líneas que ya no existen | El paso 4 no corrió, o corrió sin `fetch` | Rehacer el paso 4 y re-emitir el veredicto contra `origin/<default>`. Si el defecto ya no está, el flujo se cierra y el incidente se reporta como resuelto aguas arriba |
| El PR del flujo entra en conflicto con otro PR abierto | El cruce del paso 4 se hizo por título y no por archivos | Cruzar `gh pr diff --name-only` contra la superficie. Con el conflicto ya abierto, el orden de merge lo decide el usuario |
| El worktree perdió commits que estaban en `origin` | El realineo se hizo sin comprobar la dirección, en la rama `inseparable` | `reset --hard origin/<default>` y rehacer 6.2. Es un defecto de procedimiento: se registra |
| El flujo arrancó pero el hash del dossier no coincide | El encargo se leyó de otro archivo, o el dossier cambió después de calcular su digest | Arranque **no confirmado**: no se retira nada. Recalcular el digest del dossier en su origen y comparar; si difiere del que se envió, el dossier se reescribió a mitad del despacho |
| La plataforma resolvió `headless` | Ninguna identidad viva, o las dos vivas sin observable que distinga al anfitrión | **No es un modo degradado: es parada.** El despacho no ocurre, el registro queda intacto y se reintenta cuando haya plataforma. Un override no lo arregla: también se comprueba |

Todo fallo atribuible a una skill SDD —esta incluida— se registra según la regla del archivo de
instrucciones del `<repo_destino>`, que declara su sede. Esta skill no la fija ni la supone: la
lee de ahí.
