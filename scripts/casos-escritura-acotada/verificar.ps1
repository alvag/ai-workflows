# Matriz de casos de scripts/escritura-acotada.ps1
# Cada caso proviene de un defecto real encontrado durante la revision del diseno: la lectura no los
# atrapo y la ejecucion si. Ese es el motivo de que esta matriz exista.
$ErrorActionPreference = 'Stop'
$enc = [System.Text.UTF8Encoding]::new($false)
$NL = [char]10
$script:fails = 0
$sut = Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) 'escritura-acotada.ps1'
$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("casos-ea-" + [System.Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $tmpDir | Out-Null

function Chk($ok, $msg) { if ($ok) { Write-Host "  OK   $msg" } else { Write-Host "  FAIL $msg"; $script:fails++ } }

# Registro de prueba: E-020 aparece ANTES que E-005 a proposito. El orden en el archivo no es
# el de los numeros, y suponer lo contrario fue un defecto real.
function Nuevo-Registro($nombre) {
  $p = Join-Path $tmpDir $nombre
  $c = @(
    '# Registro de incidentes'
    ''
    '## E-020 - ruta cambiada'
    '- **Estado:** `abierto`'
    ''
    '## E-005 - persistencia'
    '- **Estado:** `revisando`'
    ''
    '## E-030 - generalizacion'
    '- **Estado:** `abierto`'
    ''
    '## E-040 - entrada ajena de otro agente'
    '- linea ajena que NO se puede perder'
  ) -join $NL
  [System.IO.File]::WriteAllText($p, $c, $enc)
  return $p
}
$marcasOk = @(
  @{ Ancla='## E-005'; Anterior='`revisando`'; Esperado='`confirmado - correccion local`' }
  @{ Ancla='## E-020'; Anterior='`abierto`';   Esperado='`parcial`' }
  @{ Ancla='## E-030'; Anterior='`abierto`';   Esperado='`parcial`' }
)
function Correr($p, $modo, $marcas, $contenido) {
  try { $r = & $sut -Ruta $p -Modo $modo -Marcas $marcas -Contenido $contenido; return @{ ok=$true; msg=$r } }
  catch { return @{ ok=$false; msg=$_.Exception.Message } }
}

Write-Host "=== CASO 1 - anclas fuera de orden numerico (E-020 antes que E-005) ==="
$p = Nuevo-Registro 'c1.md'
$orig = [System.IO.File]::ReadAllBytes($p)
$r = Correr $p 'Acotada' $marcasOk $null
Chk $r.ok "aplica sin abortar ($($r.msg))"
$t = [System.IO.File]::ReadAllText($p, $enc)
Chk ($t.Contains('`confirmado - correccion local`')) "E-005 marcada"
Chk (($t -split $NL | Where-Object { $_ -eq '- **Estado:** `parcial`' }).Count -eq 2) "E-020 e E-030 marcadas (las DOS, no una)"
Chk ($t.Contains('linea ajena que NO se puede perder')) "entrada ajena preservada"
Chk ($r.msg -match 'offset (\d+)') "reporta el offset usado"
$off = [int]([regex]::Match($r.msg, 'offset (\d+)').Groups[1].Value)
$fin = [System.IO.File]::ReadAllBytes($p)
$pref = $true; for ($i=0; $i -lt $off; $i++) { if ($fin[$i] -ne $orig[$i]) { $pref = $false; break } }
Chk $pref "prefijo anterior al offset intacto byte a byte"
Chk (-not (Test-Path -LiteralPath ($p + '.bak'))) "resguardo borrado tras verificar"

Write-Host "=== CASO 2 - ancla ausente ==="
$p = Nuevo-Registro 'c2.md'
$orig = [System.IO.File]::ReadAllBytes($p)
$r = Correr $p 'Acotada' ($marcasOk + @{ Ancla='## E-999'; Anterior='x'; Esperado='y' }) $null
Chk (-not $r.ok) "aborta ($($r.msg))"
Chk ($r.msg -match 'ancla ausente') "el motivo nombra el ancla faltante"
Chk ([System.IO.File]::ReadAllBytes($p).Length -eq $orig.Length) "archivo sin tocar"
Chk (-not (Test-Path -LiteralPath ($p + '.bak'))) "sin .bak huerfano"
Chk (-not (Test-Path -LiteralPath ($p + '.bak.tmp'))) "sin .bak.tmp huerfano"

Write-Host "=== CASO 3 - ancla duplicada ==="
$p = Nuevo-Registro 'c3.md'
[System.IO.File]::AppendAllText($p, "$NL## E-005 - duplicada$NL", $enc)
$orig = [System.IO.File]::ReadAllBytes($p)
$r = Correr $p 'Acotada' $marcasOk $null
Chk (-not $r.ok) "aborta ($($r.msg))"
Chk ($r.msg -match 'ancla duplicada') "el motivo nombra la duplicacion"
Chk ([System.IO.File]::ReadAllBytes($p).Length -eq $orig.Length) "archivo sin tocar"

Write-Host "=== CASO 4 - marca compartida entre dos incidentes, una sin sustituir ==="
# E-020 e E-030 esperan la MISMA marca 'parcial'. Una guarda global se satisface con una sola
# aparicion; la guarda por seccion no. Este es el falso verde que hubo que cerrar.
$p = Nuevo-Registro 'c4.md'
$marcasMal = @(
  @{ Ancla='## E-005'; Anterior='`revisando`'; Esperado='`confirmado - correccion local`' }
  @{ Ancla='## E-020'; Anterior='`abierto`';   Esperado='`parcial`' }
  @{ Ancla='## E-030'; Anterior='NO-EXISTE';   Esperado='`parcial`' }   # no sustituye nada
)
$orig = [System.IO.File]::ReadAllBytes($p)
$r = Correr $p 'Acotada' $marcasMal $null
Chk (-not $r.ok) "rechaza ($($r.msg))"
Chk ($r.msg -match 'E-030') "nombra el incidente que quedo sin sustituir"
Chk ([System.IO.File]::ReadAllBytes($p).Length -eq $orig.Length) "archivo sin tocar"

Write-Host "=== CASO 5 - .bak presente al arrancar ==="
$p = Nuevo-Registro 'c5.md'
[System.IO.File]::WriteAllText($p + '.bak', 'COPIA BUENA DE UN INTENTO ANTERIOR', $enc)
$r = Correr $p 'Acotada' $marcasOk $null
Chk (-not $r.ok) "aborta ($($r.msg))"
Chk ($r.msg -match 'resguardo pendiente') "lo trata como estado de recuperacion"
Chk ([System.IO.File]::ReadAllText($p + '.bak', $enc) -ceq 'COPIA BUENA DE UN INTENTO ANTERIOR') "la copia buena queda INTACTA"
Remove-Item -LiteralPath ($p + '.bak') -Force

Write-Host "=== CASO 6 - .bak.tmp presente al arrancar ==="
$p = Nuevo-Registro 'c6.md'
$orig = [System.IO.File]::ReadAllText($p, $enc)
[System.IO.File]::WriteAllText($p + '.bak.tmp', 'COPIA A MEDIO ESCRIBIR', $enc)
$r = Correr $p 'Acotada' $marcasOk $null
Chk (-not $r.ok) "aborta ($($r.msg))"
Chk ($r.msg -match 'NO restaurar') "dice explicitamente que NO hay que restaurar"
Chk ([System.IO.File]::ReadAllText($p, $enc) -ceq $orig) "el original queda intacto (no se restauro sobre el)"
Remove-Item -LiteralPath ($p + '.bak.tmp') -Force

Write-Host "=== CASO 7 - lectura corta (alcance declarado) ==="
# No se pudo provocar una lectura corta de FileStream sobre un archivo local en este entorno.
# Se verifica por inspeccion que el bucle existe y aborta ante EOF prematuro, y se declara ese
# alcance en vez de marcar verde una comprobacion que no se ejecuto.
$src = [System.IO.File]::ReadAllText($sut, $enc)
Chk ($src -match 'while \(\$leidos -lt \$total\)') "el bucle de lectura completa existe"
Chk ($src -match "EOF prematuro") "aborta ante EOF prematuro"
Chk (-not ($src -match '\[void\]\$fs\.Read')) "no descarta el valor de retorno de Read"
Write-Host "  NOTA: caso no ejecutado, verificado por inspeccion. Alcance declarado."

Write-Host "=== CASO 8 - append puro ==="
$p = Nuevo-Registro 'c8.md'
$orig = [System.IO.File]::ReadAllBytes($p)
$r = Correr $p 'Append' $null "${NL}## V-002 - entrada nueva${NL}"
Chk $r.ok "agrega sin abortar ($($r.msg))"
$fin = [System.IO.File]::ReadAllBytes($p)
$pref = $true; for ($i=0; $i -lt $orig.Length; $i++) { if ($fin[$i] -ne $orig[$i]) { $pref = $false; break } }
Chk $pref "el contenido previo queda intacto byte a byte"
Chk ([System.IO.File]::ReadAllText($p, $enc).EndsWith("## V-002 - entrada nueva$NL")) "lo nuevo quedo al final"

Write-Host "=== CASO 9 - restauracion acotada ==="
$p = Nuevo-Registro 'c9.md'
$bueno = [System.IO.File]::ReadAllBytes($p)
[System.IO.File]::WriteAllBytes($p + '.bak', $bueno)
[System.IO.File]::WriteAllText($p, "# Registro de incidentes$NL$NL## E-020 - DA" + "NADO", $enc)
$r = Correr $p 'Restaurar' $null $null
Chk $r.ok "restaura ($($r.msg))"
Chk ($r.msg -match 'offset \d+') "la restauracion es ACOTADA, desde el primer offset divergente"
$fin = [System.IO.File]::ReadAllBytes($p)
$igual = $fin.Length -eq $bueno.Length
if ($igual) { for ($i=0; $i -lt $bueno.Length; $i++) { if ($fin[$i] -ne $bueno[$i]) { $igual = $false; break } } }
Chk $igual "el archivo quedo identico al resguardo"
Chk (-not (Test-Path -LiteralPath ($p + '.bak'))) "resguardo borrado tras verificar"

Write-Host "=== CASO 10 - modo Insertar: el ancla PERMANECE ==="
# Insertar no es sustituir: el 'Anterior' es la linea tras la cual se agrega y tiene que seguir ahi.
# Usar la guarda de sustitucion para una insercion aborta con 'valor anterior sigue presente'.
$p = Nuevo-Registro 'c10.md'
$marcasIns = @(
  @{ Ancla='## E-005'; Modo='Insertar'; Anterior='- **Estado:** `revisando`'; Esperado='- **Nota:** verificado' }
)
$r = Correr $p 'Acotada' $marcasIns $null
Chk $r.ok "inserta sin abortar ($($r.msg))"
$t = [System.IO.File]::ReadAllText($p, $enc)
Chk ($t.Contains('- **Estado:** `revisando`')) "la linea ancla PERMANECE"
Chk ($t.Contains('- **Nota:** verificado')) "la linea nueva se agrego"
Chk ($t.IndexOf('- **Nota:**') -gt $t.IndexOf('- **Estado:** `revisando`')) "quedo DESPUES del ancla"
Chk ($t.Contains('linea ajena que NO se puede perder')) "entrada ajena preservada"

Write-Host "=== CASO 11 - un fallo ANTES de escribir no deja resguardo huerfano ==="
# Si la construccion falla, el original esta intacto: no hay nada que recuperar, y conservar el .bak
# solo bloquearia la corrida siguiente con un falso 'recuperacion pendiente'.
$p = Nuevo-Registro 'c11.md'
$orig = [System.IO.File]::ReadAllBytes($p)
$marcasFallan = @(
  @{ Ancla='## E-005'; Anterior='`revisando`'; Esperado='`confirmado`' }
  @{ Ancla='## E-020'; Anterior='NO-EXISTE';   Esperado='`parcial`' }   # falla la guarda de construccion
)
$r = Correr $p 'Acotada' $marcasFallan $null
Chk (-not $r.ok) "aborta ($($r.msg))"
Chk ([System.IO.File]::ReadAllBytes($p).Length -eq $orig.Length) "archivo sin tocar"
Chk (-not (Test-Path -LiteralPath ($p + '.bak'))) "SIN .bak huerfano: el fallo fue antes de escribir"
Chk (-not (Test-Path -LiteralPath ($p + '.bak.tmp'))) "sin .bak.tmp huerfano"
# y por lo tanto la corrida siguiente NO queda bloqueada
$r2 = Correr $p 'Acotada' $marcasOk $null
Chk $r2.ok "la corrida siguiente puede proceder ($($r2.msg))"

Write-Host "=== CASO 12 - append con ID correlativo exigido, calculado BAJO EL LOCK ==="
$p = Join-Path $tmpDir 'c12.md'
[System.IO.File]::WriteAllText($p, "# Registro${NL}${NL}## V-001 - primera${NL}- algo${NL}", $enc)
# el correcto pasa
try { $r = & $sut -Ruta $p -Modo Append -Contenido "${NL}## V-002 - segunda${NL}" -RequiereIdSiguiente 'V-002'; $ok = $true } catch { $ok = $false; $msg = $_.Exception.Message }
Chk $ok "acepta el ID correlativo correcto$(if(-not $ok){" ($msg)"})"
Chk ([System.IO.File]::ReadAllText($p, $enc).Contains('## V-002')) "la entrada quedo escrita"
# el equivocado aborta, sin renumerar ni sobrescribir
$antesBytes = [System.IO.File]::ReadAllBytes($p)
try { & $sut -Ruta $p -Modo Append -Contenido "${NL}## V-002 - duplicada${NL}" -RequiereIdSiguiente 'V-002' | Out-Null; $ok2 = $true } catch { $ok2 = $false; $msg2 = $_.Exception.Message }
Chk (-not $ok2) "aborta si el correlativo ya no es el esperado ($msg2)"
Chk ($msg2 -match 'colision de ID') "el motivo nombra la colision"
Chk ([System.IO.File]::ReadAllBytes($p).Length -eq $antesBytes.Length) "archivo sin tocar: no renumera ni duplica"

Remove-Item -LiteralPath $tmpDir -Recurse -Force
Write-Host ""
if ($script:fails -eq 0) { Write-Host "MATRIZ: VERDE - 12 casos" } else { Write-Host "MATRIZ: ROJO - $($script:fails) fallaron" }
exit $script:fails
