<#
.SYNOPSIS
  Escritura segura sobre registros de texto con escritores concurrentes.

.DESCRIPTION
  Dos operaciones, bajo el mismo contrato de exclusión:

    -Modo Acotada  Muta marcas dentro de un archivo sin reescribirlo entero. Se escribe desde el
                   offset de la primera ancla hacia el final; el prefijo anterior no se toca.
    -Modo Append   Agrega contenido al final. Sin ancla, sin cola reescrita, sin ajuste de longitud.

  El contrato, igual en las dos: exclusión mutua ReadWrite+None sostenida de punta a punta, lectura
  completa en bucle, resguardo publicado atómicamente, guarda por sección, verificación posterior y
  liberación en finally.

  Por qué no un rewrite completo, ni siquiera bajo lock: el lock evita escritores concurrentes, pero
  no evita que una caída después de truncar deje el registro vacío.

.NOTES
  Los dos sidecars significan cosas OPUESTAS y por eso no comparten nombre:
    <ruta>.bak.tmp  la corrida cayó CREANDO la copia -> el original está intacto -> NO restaurar.
    <ruta>.bak      la copia se verificó y publicó   -> el original puede estar a medio mutar -> restaurar.
  Cualquiera de los dos presente aborta la corrida siguiente.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$Ruta,
  [Parameter(Mandatory)][ValidateSet('Acotada','Append','Restaurar')][string]$Modo,
  # Acotada: @( @{ Ancla='## E-001'; Anterior='`pendiente`'; Esperado='`cerrado`' }, ... )
  [array]$Marcas,
  # Append: el texto a agregar al final.
  [string]$Contenido,
  # Append: exige que el siguiente ID correlativo, calculado BAJO EL LOCK, sea exactamente este.
  # Cierra la carrera entre calcular el ID y escribirlo, que es donde nace una colision.
  [string]$RequiereIdSiguiente,
  # Patron del ID; el grupo 1 debe capturar el numero. Default: '## V-(\d+)'
  [string]$PatronId = '##\s+V-(\d+)'
)

$ErrorActionPreference = 'Stop'
$enc = [System.Text.UTF8Encoding]::new($false)
$bak = $Ruta + '.bak'
$bakTmp = $bak + '.tmp'
$NL = [char]10

function Read-Completo([System.IO.FileStream]$fs) {
  $fs.Position = 0
  $total = [int]$fs.Length
  $buf = New-Object byte[] $total
  $leidos = 0
  while ($leidos -lt $total) {
    $n = $fs.Read($buf, $leidos, $total - $leidos)
    if ($n -le 0) { throw "EOF prematuro a los $leidos de $total bytes: no se escribe" }
    $leidos += $n
  }
  return $buf
}

function Get-Seccion([string]$texto, [string]$ancla) {
  $i = $texto.IndexOf($ancla, [System.StringComparison]::Ordinal)
  if ($i -lt 0) { return '' }
  $j = $texto.IndexOf("$NL## ", $i + $ancla.Length, [System.StringComparison]::Ordinal)
  if ($j -lt 0) { return $texto.Substring($i) }
  return $texto.Substring($i, $j - $i)
}

function Test-Guarda([string]$cola, [array]$marcas) {
  foreach ($m in $marcas) {
    $s = Get-Seccion $cola $m.Ancla
    if ($s -eq '') { throw "seccion no encontrada tras escribir: $($m.Ancla)" }
    if (-not $s.Contains($m.Esperado)) { throw "cambio faltante en $($m.Ancla)" }
    # Sustituir exige que el valor viejo desaparezca. Insertar NO: ahi el 'Anterior' es la linea
    # ancla tras la cual se agrega, y tiene que seguir estando.
    if ((Modo-De $m) -eq 'Sustituir' -and $s.Contains($m.Anterior)) {
      throw "valor anterior sigue presente en $($m.Ancla)"
    }
  }
}

function Modo-De($m) { if ($m.Modo) { return $m.Modo } else { return 'Sustituir' } }

# --- guardas de estado, antes de abrir nada ---
if ($Modo -ne 'Restaurar') {
  if ([System.IO.File]::Exists($bakTmp)) {
    throw "resguardo a medio crear ($bakTmp): el original esta INTACTO, NO restaurar; descartar ese archivo y reintentar"
  }
  if ([System.IO.File]::Exists($bak)) {
    throw "resguardo pendiente ($bak): un intento anterior quedo a medias; restaurar con -Modo Restaurar antes de reintentar"
  }
}
if (-not [System.IO.File]::Exists($Ruta)) { throw "el archivo no existe: $Ruta" }

$fs = [System.IO.File]::Open($Ruta, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
try {
  $buf = Read-Completo $fs
  $antes = $enc.GetString($buf)

  if ($Modo -eq 'Restaurar') {
    if (-not [System.IO.File]::Exists($bak)) { throw "no hay resguardo que restaurar: $bak" }
    $bb = [System.IO.File]::ReadAllBytes($bak)
    # restauracion ACOTADA: desde el primer offset divergente, no desde 0.
    $min = [Math]::Min($bb.Length, $buf.Length); $div = -1
    for ($i = 0; $i -lt $min; $i++) { if ($bb[$i] -ne $buf[$i]) { $div = $i; break } }
    if ($div -lt 0) { if ($bb.Length -eq $buf.Length) { Remove-Item -LiteralPath $bak -Force; return 'sin divergencia: nada que restaurar' } ; $div = $min }
    $fs.Position = $div
    $fs.Write($bb, $div, $bb.Length - $div)
    $fs.SetLength($bb.Length)
    $fs.Flush()
    $ver = Read-Completo $fs
    if ($ver.Length -ne $bb.Length) { throw 'restauracion no verificable' }
    for ($i = 0; $i -lt $bb.Length; $i++) { if ($ver[$i] -ne $bb[$i]) { throw "restauracion divergente en $i" } }
    Remove-Item -LiteralPath $bak -Force
    return "restaurado desde el offset $div"
  }

  # --- prevalidacion: TODAS las anclas, presencia y unicidad, antes de escribir nada ---
  $offset = 0
  if ($Modo -eq 'Acotada') {
    if (-not $Marcas -or $Marcas.Count -eq 0) { throw 'el modo Acotada requiere -Marcas' }
    $indices = @()
    foreach ($m in $Marcas) {
      $i = $antes.IndexOf($m.Ancla, [System.StringComparison]::Ordinal)
      if ($i -lt 0) { throw "ancla ausente: $($m.Ancla)" }
      if ($antes.IndexOf($m.Ancla, $i + 1, [System.StringComparison]::Ordinal) -ge 0) { throw "ancla duplicada: $($m.Ancla)" }
      $indices += $i
    }
    # el MINIMO REAL: el orden en el archivo no es el de los numeros de incidente
    $iMin = ($indices | Measure-Object -Minimum).Minimum
    $offset = $enc.GetByteCount($antes.Substring(0, $iMin))
  } else {
    $offset = $buf.Length
  }

  # --- resguardo: sidecar -> verificar -> publicar por rename ---
  $bfs = [System.IO.File]::Open($bakTmp, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
  try { $bfs.Write($buf, 0, $buf.Length); $bfs.Flush() } finally { $bfs.Dispose() }
  $vb = [System.IO.File]::ReadAllBytes($bakTmp)
  if ($vb.Length -ne $buf.Length) { throw 'resguardo no verificable: longitud distinta' }
  for ($i = 0; $i -lt $buf.Length; $i++) { if ($vb[$i] -ne $buf[$i]) { throw "resguardo no coincide en $i" } }
  Move-Item -LiteralPath $bakTmp -Destination $bak

  # A partir de aca el resguardo importa. Antes de la primera escritura, un fallo NO deja nada que
  # recuperar —el original esta intacto— y conservar el .bak solo bloquearia la corrida siguiente
  # con un falso "recuperacion pendiente". Por eso los fallos de construccion lo limpian.
  $escrituraIniciada = $false
  try {

  # --- construir la escritura, y comprobarla ANTES de tocar el archivo ---
  if ($Modo -eq 'Acotada') {
    $cola = $antes.Substring($enc.GetString($buf, 0, $offset).Length)
    foreach ($m in $Marcas) {
      $s = Get-Seccion $cola $m.Ancla
      if ($s -eq '') { throw "el ancla $($m.Ancla) quedo fuera de la cola reescribible" }
      if ((Modo-De $m) -eq 'Insertar') {
        # se agrega DESPUES de la linea ancla, que permanece
        if (-not $s.Contains($m.Anterior)) { throw "linea de insercion no encontrada en $($m.Ancla)" }
        $nuevo = $s.Replace($m.Anterior, $m.Anterior + $NL + $m.Esperado)
      } else {
        $nuevo = $s.Replace($m.Anterior, $m.Esperado)
      }
      $cola = $cola.Replace($s, $nuevo)
    }
    Test-Guarda $cola $Marcas
    $out = $enc.GetBytes($cola)
  } else {
    if ([string]::IsNullOrEmpty($Contenido)) { throw 'el modo Append requiere -Contenido' }
    if ($RequiereIdSiguiente) {
      # se calcula sobre lo que este stream leyo, no sobre una lectura previa
      $nums = @([regex]::Matches($antes, $PatronId) | ForEach-Object { [int]$_.Groups[1].Value })
      $sig = if ($nums.Count -eq 0) { 1 } else { ($nums | Measure-Object -Maximum).Maximum + 1 }
      $esperado = $RequiereIdSiguiente -replace '\D', ''
      if ([int]$esperado -ne $sig) {
        throw "colision de ID: se esperaba $RequiereIdSiguiente pero el siguiente correlativo es $sig. No se renumera ni se sobrescribe: abortar y escalar."
      }
    }
    $out = $enc.GetBytes($Contenido)
  }

  $escrituraIniciada = $true
  $fs.Position = $offset
  $fs.Write($out, 0, $out.Length)
  $fs.SetLength($offset + $out.Length)
  $fs.Flush()

  # --- verificacion posterior, por el MISMO stream ---
  $fin = Read-Completo $fs
  for ($i = 0; $i -lt $offset; $i++) { if ($fin[$i] -ne $buf[$i]) { throw "el prefijo intacto fue alterado en $i" } }
  $textoFin = $enc.GetString($fin)
  if ($Modo -eq 'Acotada') { Test-Guarda $textoFin $Marcas }
  else { if (-not $textoFin.EndsWith($Contenido)) { throw 'el append no quedo al final' } }

  Remove-Item -LiteralPath $bak -Force
  return "ok: offset $offset, prefijo intacto, $($fin.Length) bytes finales"

  } catch {
    if (-not $escrituraIniciada) { Remove-Item -LiteralPath $bak -Force -ErrorAction SilentlyContinue }
    throw
  }
}
finally { $fs.Dispose() }
