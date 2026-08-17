#!/usr/bin/env python3
"""Arnés de paridad entre las variantes PowerShell y POSIX de los bloques de guarda.

Ejecuta cada par `# @bloque:<n>` / `# @bloque:<n>-ps` sobre entradas equivalentes y aisladas y
compara cuatro dimensiones: clase de resultado, multiconjunto de eventos, stdout normalizado y
artefactos producidos. El cuerpo NO se reimplementa: se extrae de los marcadores vigentes.

Códigos de salida de una corrida de paridad (precedencia exclusiva, de mayor a menor):

    4  fallo interno          3  no comprobable      2  incumplimiento común
    1  divergencia            0  paridad total

Las auditorías y autotests salen 0 en verde y 4 en rojo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

CODIGO = {
    "paridad": 0,
    "divergencia": 1,
    "incumplimiento_comun": 2,
    "no_comprobable": 3,
    "fallo": 4,
}
PRECEDENCIA = ["paridad", "divergencia", "incumplimiento_comun", "no_comprobable", "fallo"]

PREFIJOS_EVENTO = ("GUARD:", "ARNES:", "BLOCKED")
CANDIDATOS_PWSH_DEFECTO = ("pwsh", "pwsh-preview", "powershell")
TIMEOUT_DEFECTO = 30

# Entorno determinista: `sort` depende de LC_COLLATE y `Sort-Object` de la cultura del proceso.
# Se declara acá y se imprime con `--entorno`; ninguna corrida lo elige sobre la marcha.
#
# `C.UTF-8` y no `C`: los dos dan la MISMA colación por bytes —`sort -u` sobre
# `Beta/alpha/BETA/Alpha` devuelve los cuatro en el mismo orden—, pero `C` trata la entrada como
# bytes sueltos y `grep -i` deja de plegar mayúsculas fuera de ASCII. Los cuerpos están escritos en
# español y comparan contra literales con acento, así que bajo `C` una guarda que sí dispara en
# cualquier entorno real deja de disparar, y el arnés lo reportaría como divergencia de PowerShell.
# Medido: `grep -qiE 'no cubrió'` contra `NO CUBRIÓ` bajo `/bin/sh` da falso con `C` y verdadero
# con `C.UTF-8`. Nadie corre estas guardas bajo `C`; medirlas ahí es medir otra cosa.
LOCALE = {"LC_ALL": "C.UTF-8", "LANG": "C.UTF-8", "LC_COLLATE": "C.UTF-8", "TZ": "UTC"}
ENCODING = "utf-8"

RAIZ_ARNES = Path(__file__).resolve().parent.parent
DIR_CASOS = "scripts/paridad-casos"

PARTICIONES_CADENA = ("positivo", "invalido", "casing")
PARTICIONES_CARDINALIDAD = ("vacio", "singleton", "par", "impar")
CLASES = ("aceptacion", "rechazo", "fallo")
DIMENSIONES = ("clase", "eventos", "stdout", "artefactos")


# ─────────────────────────────────────────────────────────────────────────────
# sección `extraccion` — T1
# ─────────────────────────────────────────────────────────────────────────────

MARCA_INICIO = "# @bloque:"
MARCA_FIN = "# @fin:"


class BloqueInvalido(Exception):
    """El bloque no se puede recortar sin ambigüedad. Nunca se devuelve cuerpo parcial."""

    def __init__(self, nombre: str, motivo: str):
        super().__init__(f"bloque '{nombre}': {motivo}")
        self.nombre = nombre
        self.motivo = motivo


def extraer_bloque(texto: str, nombre: str) -> str:
    """Devuelve el cuerpo entre marcadores, sin las líneas marcadoras.

    Falla cerrado ante bloque ausente, `@fin` ausente, cierre con otro nombre, cierre duplicado
    y apertura duplicada. El extractor archivado del que se porta esta primitiva imprimía hasta
    EOF ante una apertura sin cierre y salía 0: acá eso es `BloqueInvalido`.
    """
    lineas = texto.split("\n")
    aperturas = [i for i, l in enumerate(lineas) if l.strip() == MARCA_INICIO + nombre]
    if not aperturas:
        raise BloqueInvalido(nombre, "no existe la marca de apertura")
    if len(aperturas) > 1:
        ubic = ", ".join(str(i + 1) for i in aperturas)
        raise BloqueInvalido(nombre, f"apertura duplicada en las líneas {ubic}")

    apertura = aperturas[0]
    cierre = None
    for j in range(apertura + 1, len(lineas)):
        s = lineas[j].strip()
        if s.startswith(MARCA_INICIO):
            otro = s[len(MARCA_INICIO):].strip()
            raise BloqueInvalido(
                nombre, f"se abre '{otro}' en la línea {j + 1} sin haber cerrado este bloque")
        if s.startswith(MARCA_FIN):
            n2 = s[len(MARCA_FIN):].strip()
            if n2 != nombre:
                raise BloqueInvalido(
                    nombre, f"la línea {j + 1} cierra '{n2}', que no es este bloque")
            cierre = j
            break
    if cierre is None:
        raise BloqueInvalido(nombre, "falta la marca de cierre `@fin`")

    for j in range(cierre + 1, len(lineas)):
        if lineas[j].strip() == MARCA_FIN + nombre:
            raise BloqueInvalido(nombre, f"cierre duplicado en la línea {j + 1}")

    return "\n".join(lineas[apertura + 1:cierre])


def linea_de_apertura(texto: str, nombre: str) -> int:
    for i, l in enumerate(texto.split("\n")):
        if l.strip() == MARCA_INICIO + nombre:
            return i + 1
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# sección `inventario` — T2
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Par:
    nombre: str
    archivo: str
    linea_posix: int
    linea_ps: int
    cuerpo_posix: str
    cuerpo_ps: str

    def digest(self, sabor: str) -> str:
        cuerpo = self.cuerpo_posix if sabor == "posix" else self.cuerpo_ps
        return "sha256:" + hashlib.sha256(cuerpo.encode(ENCODING)).hexdigest()[:16]


def _archivos_de_skills(raiz: Path) -> list[Path]:
    return sorted(p for p in (raiz / "skills").rglob("*.md") if p.is_file())


def descubrir_pares(raiz: Path) -> tuple[dict[str, Par], list[str], list[str]]:
    """Descubre el inventario sin lista codificada.

    Devuelve (pares, huerfanas, solo_posix). Una variante `-ps` sin par POSIX homónimo es
    huérfana y pone el inventario en rojo; un POSIX sin `-ps` sale naturalmente de exigir el par
    en la dirección `-ps` → POSIX, sin lista de excepciones.
    """
    ubicacion: dict[str, tuple[Path, str]] = {}
    for ruta in _archivos_de_skills(raiz):
        texto = ruta.read_text(encoding=ENCODING)
        for linea in texto.split("\n"):
            s = linea.strip()
            if s.startswith(MARCA_INICIO):
                nombre = s[len(MARCA_INICIO):].strip()
                if nombre in ubicacion:
                    raise BloqueInvalido(nombre, "declarado en dos archivos distintos")
                ubicacion[nombre] = (ruta, texto)

    pares: dict[str, Par] = {}
    huerfanas: list[str] = []
    variantes = sorted(n for n in ubicacion if n.endswith("-ps"))
    for variante in variantes:
        base = variante[:-3]
        if base not in ubicacion:
            huerfanas.append(variante)
            continue
        ruta_ps, texto_ps = ubicacion[variante]
        ruta_px, texto_px = ubicacion[base]
        if ruta_ps != ruta_px:
            huerfanas.append(variante)
            continue
        pares[base] = Par(
            nombre=base,
            archivo=str(ruta_px.relative_to(raiz)),
            linea_posix=linea_de_apertura(texto_px, base),
            linea_ps=linea_de_apertura(texto_ps, variante),
            cuerpo_posix=extraer_bloque(texto_px, base),
            cuerpo_ps=extraer_bloque(texto_ps, variante),
        )
    solo_posix = sorted(
        n for n in ubicacion if not n.endswith("-ps") and n + "-ps" not in ubicacion)
    return pares, huerfanas, solo_posix


# ─────────────────────────────────────────────────────────────────────────────
# sección `runner` — T3
# ─────────────────────────────────────────────────────────────────────────────

PRELUDIO_PS = (
    "$ErrorActionPreference = 'Continue'\n"
    "if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' }\n"
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
    "$OutputEncoding = [Console]::OutputEncoding\n"
    "[System.Threading.Thread]::CurrentThread.CurrentCulture ="
    " [System.Globalization.CultureInfo]::InvariantCulture\n"
)


@dataclass
class Observacion:
    exit: int
    stdout: bytes
    stderr: bytes
    artefactos: dict[str, bytes]
    timeout: bool = False
    interprete: str = ""


class SinInterprete(Exception):
    pass


def locale_usable() -> tuple[bool, str]:
    """Comprueba POR OBSERVACIÓN que el locale declarado da semántica UTF-8, no que exista.

    Fail-closed: si el plegado de mayúsculas fuera de ASCII no funciona, caer en silencio a la
    semántica de bytes produce divergencias falsas —una guarda POSIX deja de disparar y el arnés
    se lo atribuye a PowerShell—. Preferimos `no comprobable` a un rojo inventado.
    """
    entorno = dict(os.environ)
    entorno.update(LOCALE)
    sonda = "printf '%s' 'NO CUBRIÓ' | grep -qiE 'no cubrió' && echo SI || echo NO\n"
    try:
        r = subprocess.run(["/bin/sh", "-c", sonda], env=entorno, capture_output=True,
                           timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"no se pudo ejecutar la sonda de locale: {exc}"
    if r.stdout.decode(ENCODING, "replace").strip() != "SI":
        return False, (f"el locale declarado ({LOCALE['LC_ALL']}) no pliega mayúsculas fuera de"
                       f" ASCII en este sistema; medir bajo semántica de bytes reportaría"
                       f" divergencias que no existen")
    return True, LOCALE["LC_ALL"]


def _candidatos_pwsh() -> list[str]:
    crudo = os.environ.get("PARIDAD_PWSH_CANDIDATOS")
    if crudo:
        return [c.strip() for c in crudo.split(",") if c.strip()]
    return list(CANDIDATOS_PWSH_DEFECTO)


def detectar_pwsh() -> tuple[str, str]:
    """Devuelve (ruta, versión) del primer candidato disponible. Sin ninguno, `SinInterprete`."""
    for cand in _candidatos_pwsh():
        ruta = shutil.which(cand)
        if not ruta:
            continue
        try:
            out = subprocess.run(
                [ruta, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
                 "$PSVersionTable.PSVersion.ToString()"],
                capture_output=True, timeout=60, check=False)
            version = out.stdout.decode(ENCODING, "replace").strip() or "?"
        except (OSError, subprocess.TimeoutExpired):
            continue
        return ruta, version
    raise SinInterprete("ningún candidato de PowerShell disponible: "
                        + ", ".join(_candidatos_pwsh()))


def _prologo_posix(entradas: dict[str, str]) -> str:
    import shlex
    lineas = []
    for k, v in entradas.items():
        lineas.append(f"{k}={shlex.quote(str(v))}")
        lineas.append(f"export {k}")
    return "\n".join(lineas) + ("\n" if lineas else "")


def _prologo_ps(entradas: dict[str, str]) -> str:
    lineas = [PRELUDIO_PS.rstrip("\n")]
    for k, v in entradas.items():
        lit = str(v).replace("'", "''")
        lineas.append(f"${k} = '{lit}'")
        lineas.append(f"$env:{k} = '{lit}'")
    return "\n".join(lineas) + "\n"


def _recolectar_artefactos(base: Path) -> dict[str, bytes]:
    salida: dict[str, bytes] = {}
    for p in sorted(base.rglob("*")):
        if p.is_file():
            salida[str(p.relative_to(base))] = p.read_bytes()
    return salida


def aplicar_reemplazos(caso_dir: Path, reemplazos: list[dict[str, str]]) -> None:
    """Aplica reemplazos UTF-8 ordenados, exactos y confinados a la copia del caso."""
    if not isinstance(reemplazos, list):
        raise TypeError("reemplazos debe ser una lista")

    raiz = caso_dir.resolve(strict=True)
    for indice, reemplazo in enumerate(reemplazos):
        if not isinstance(reemplazo, dict):
            raise TypeError(f"reemplazos[{indice}] debe ser un objeto")
        if set(reemplazo) != {"archivo", "buscar", "reemplazar"}:
            raise ValueError(
                f"reemplazos[{indice}] debe tener exactamente archivo, buscar y reemplazar")

        archivo = reemplazo["archivo"]
        buscar = reemplazo["buscar"]
        reemplazar = reemplazo["reemplazar"]
        if not all(isinstance(valor, str) for valor in (archivo, buscar, reemplazar)):
            raise TypeError(f"reemplazos[{indice}] exige valores string")

        ruta_relativa = Path(archivo)
        if ruta_relativa.is_absolute() or ".." in ruta_relativa.parts:
            raise ValueError(f"reemplazos[{indice}].archivo debe ser una ruta relativa confinada")
        try:
            destino = (raiz / ruta_relativa).resolve(strict=True)
            destino.relative_to(raiz)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            raise ValueError(
                f"reemplazos[{indice}].archivo sale del caso o no existe") from exc
        if not destino.is_file():
            raise ValueError(f"reemplazos[{indice}].archivo no es un archivo regular")

        contenido = destino.read_text(encoding=ENCODING)
        coincidencias = contenido.count(buscar)
        if coincidencias != 1:
            raise ValueError(
                f"reemplazos[{indice}].buscar debe aparecer exactamente una vez;"
                f" aparece {coincidencias}")
        destino.write_text(contenido.replace(buscar, reemplazar, 1), encoding=ENCODING)


def ejecutar(cuerpo: str, sabor: str, fixture_dir: Path | None, entradas: dict[str, str],
             timeout: int = TIMEOUT_DEFECTO, raiz_tmp: Path | None = None,
             interprete: str | None = None,
             reemplazos: list[dict[str, str]] | None = None) -> Observacion:
    """Corre un cuerpo sobre su PROPIA copia del fixture, fuera del árbol del repositorio."""
    tmp = Path(tempfile.mkdtemp(prefix=f"paridad-{sabor}-", dir=str(raiz_tmp) if raiz_tmp else None))
    caso_dir = tmp / "caso"
    caso_dir.mkdir()
    if fixture_dir is not None and fixture_dir.is_dir():
        shutil.copytree(fixture_dir, caso_dir, dirs_exist_ok=True)

    aplicar_reemplazos(caso_dir, [] if reemplazos is None else reemplazos)
    resueltas = {k: str(v).replace("{dir}", str(caso_dir)) for k, v in entradas.items()}

    entorno = dict(os.environ)
    entorno.update(LOCALE)
    entorno.pop("PARIDAD_PWSH_CANDIDATOS", None)
    entorno.update({k: v for k, v in resueltas.items()})

    if sabor == "posix":
        script = tmp / "cuerpo.sh"
        script.write_text(_prologo_posix(resueltas) + cuerpo + "\n", encoding=ENCODING)
        cmd = [interprete or "/bin/sh", str(script)]
        usado = interprete or "/bin/sh"
    else:
        if interprete is None:
            ruta, _ = detectar_pwsh()
        else:
            ruta = interprete
        script = tmp / "cuerpo.ps1"
        script.write_text(_prologo_ps(resueltas) + cuerpo + "\n", encoding=ENCODING)
        cmd = [ruta, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(script)]
        usado = ruta

    expiro = False
    try:
        proc = subprocess.run(cmd, cwd=str(caso_dir), env=entorno,
                              capture_output=True, timeout=timeout, check=False)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        expiro = True
        rc, out, err = -1, exc.stdout or b"", exc.stderr or b""

    # Cada sabor corre en SU copia, así que la ruta temporal difiere entre los dos por
    # construcción del arnés. Se sustituye por un testigo estable para que esa diferencia —del
    # arnés, no del predicado— no se lea como divergencia. Es la única sustitución de rutas y no
    # puede borrar una diferencia semántica: los dos lados reciben el mismo token.
    # De la más específica a la más general: sustituir primero la raíz temporal dejaría el sufijo
    # `/caso` colgando, y como el conjunto no tiene orden la salida no sería reproducible entre
    # sabores — que es justo lo que esta sustitución existe para evitar.
    variantes = sorted({str(caso_dir), str(caso_dir.resolve()), str(tmp), str(tmp.resolve())},
                       key=len, reverse=True)

    def _neutralizar(b: bytes) -> bytes:
        for variante in variantes:
            b = b.replace(variante.encode(ENCODING), b"{dir}")
        return b

    obs = Observacion(exit=rc, stdout=_neutralizar(out), stderr=_neutralizar(err),
                      artefactos={k: _neutralizar(v)
                                  for k, v in _recolectar_artefactos(caso_dir).items()},
                      timeout=expiro, interprete=usado)
    shutil.rmtree(tmp, ignore_errors=True)
    return obs


def crear_espia(destino: Path) -> Path:
    """Intérprete sustituto que registra el `argv` y el entorno reales del hijo."""
    log = destino / "espia.log"
    script = destino / "espia.sh"
    script.write_text(
        "#!/bin/sh\n"
        f'{{ echo "ARGV:"; for a in "$@"; do echo "  $a"; done; echo "ENV:"; env | sort; }} > "{log}"\n'
        "exit 0\n", encoding=ENCODING)
    script.chmod(0o755)
    return script


# ─────────────────────────────────────────────────────────────────────────────
# sección `catalogo` — T4
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Sitio:
    linea: int          # relativa al cuerpo, 1-based
    digest: str         # de la sentencia, para detectar que la plantilla cambió
    prefijo: str
    texto: str
    literal: str = ""   # el mensaje emitido, que es lo que el patrón del catálogo describe


# Conjunto CERRADO de formas de emisión. Una forma no reconocida es fallo, no omisión.
# El `)` del contexto POSIX es la rama de un `case`: `*) printf 'GUARD:…'`.
# Las formas de emisión reconocidas por sabor. Una forma que falte no se omite: el prefijo queda
# sin explicar y sale como anomalía, así que agregar una forma nueva es la única manera de que un
# bloque que la use pueda auditarse. Cada agregado tiene su control en `autotest_escaner`.
_EMISORES = {
    # `print` es el emisor de awk. Los bloques de `sdd-orchestrator` arman su diagnóstico dentro de
    # un programa awk entrecomillado, donde `echo` no existe y el canal lo fija la redirección.
    "posix": re.compile(r"(?:^|[;&|)]|\bthen\b|\bdo\b|\{)\s*(echo|printf|print)\b"),
    # `[Console]::Error.WriteLine` escribe la línea CRUDA en stderr. Es lo que usan los bloques
    # cuyo marcador se compara por línea entera: `Write-Error` le antepondría su envoltorio.
    "ps": re.compile(r"\b(Write-Error|Write-Output|Write-Host)\b"
                     r"|\[Console\]::Error\.Write(?:Line)?\b"),
}
_LITERAL = re.compile(r"'([^']*)'|\"((?:[^\"\\]|\\.)*)\"")
# Un prefijo entrecomillado y solo — `$7=="BLOCKED"` — es un VALOR del enum, no un mensaje.
# Se busca sobre la línea cruda porque suele venir anidado dentro de otro literal (un programa
# awk entero va entre comillas simples del shell).
_VALOR_ENUM = re.compile(
    "|".join(f"'{re.escape(p)}'|\"{re.escape(p)}\"" for p in PREFIJOS_EVENTO))


def _literales(linea: str) -> list[str]:
    return [m.group(1) if m.group(1) is not None else m.group(2)
            for m in _LITERAL.finditer(linea)]


def escanear_sitios(cuerpo: str, sabor: str) -> tuple[list[Sitio], list[str]]:
    """Enumera los sitios que emiten un evento. Devuelve (sitios, anomalías).

    Un sitio es una línea con una forma de emisión reconocida cuyo literal **empieza** con un
    prefijo de evento y lleva payload detrás. Un literal que es EXACTAMENTE el prefijo no es un
    mensaje sino un **valor** —`$7=="BLOCKED"` compara contra el enum del contrato, no emite—, y
    esa distinción entre mención y emisión es la que hay que escribir: contar la palabra da un
    veredicto falso en los dos sentidos.

    Una anomalía es un prefijo que no se explica ni como emisión reconocida ni como valor: no se
    omite en silencio, se reporta y pone la auditoría en rojo.
    """
    sitios: list[Sitio] = []
    anomalias: list[str] = []
    for i, linea in enumerate(cuerpo.split("\n"), start=1):
        desnuda = linea.strip()
        if desnuda.startswith("#"):
            continue
        if not any(p in linea for p in PREFIJOS_EVENTO):
            continue

        lits = _literales(linea)
        mensajes = [(l, p) for l in lits for p in PREFIJOS_EVENTO
                    if l.startswith(p) and len(l) > len(p)]
        valores = _VALOR_ENUM.search(linea)
        # Tercera explicación, junto a "mensaje" y "valor de enum": el prefijo **adentro** de un
        # literal más largo que no lo encabeza es PROSA del diagnóstico —"la fila X declara BLOCKED
        # sin justificar"—. No puede ser un evento, y no por convención: `_fragmentar` reconoce por
        # `startswith`, así que una línea que no empieza con el prefijo nunca abre un fragmento.
        prosa = any(p in l and not l.startswith(p) for l in lits for p in PREFIJOS_EVENTO)

        if mensajes:
            if not _EMISORES[sabor].search(linea):
                anomalias.append(f"línea {i}: literal de evento '{mensajes[0][0][:30]}' sin forma"
                                 f" de emisión reconocida → {desnuda[:70]}")
                continue
            sitios.append(Sitio(
                linea=i,
                digest="sha256:" + hashlib.sha256(desnuda.encode(ENCODING)).hexdigest()[:16],
                prefijo=mensajes[0][1],
                texto=desnuda,
                literal=mensajes[0][0]))
        elif not valores and not prosa:
            prefijo = next(p for p in PREFIJOS_EVENTO if p in linea)
            anomalias.append(f"línea {i}: prefijo '{prefijo}' que no es ni emisión reconocida ni"
                             f" valor de enum ni prosa de un mensaje → {desnuda[:70]}")
    return sitios, anomalias


def cargar_catalogo(raiz: Path, par: str) -> list[dict]:
    ruta = raiz / DIR_CASOS / par / "eventos.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding=ENCODING))


def auditar_catalogo_de_par(par: Par, catalogo: list[dict]) -> list[str]:
    """Biyección sitio ↔ entrada, con identidad mecánica por línea y digest."""
    problemas: list[str] = []
    for sabor in ("posix", "ps"):
        cuerpo = par.cuerpo_posix if sabor == "posix" else par.cuerpo_ps
        sitios, anomalias = escanear_sitios(cuerpo, sabor)
        problemas += [f"{par.nombre}/{sabor}: {a}" for a in anomalias]

        por_linea = {s.linea: s for s in sitios}
        vistas: dict[int, str] = {}
        for entrada in catalogo:
            solo_en = entrada.get("solo_en")
            if solo_en and solo_en != sabor:
                # Asimetría DECLARADA: el otro sabor no tiene esta rama. Se registra acá para que
                # sea visible en vez de bloquear la auditoría o desaparecer; si ese sabor llegara a
                # emitirla, su fragmento queda sin patrón y el caso cae en `fallo`.
                if not entrada.get("motivo"):
                    problemas.append(f"{par.nombre}: la entrada '{entrada['id']}' se declara"
                                     f" solo_en={solo_en} sin motivo escrito")
                continue
            sitio = entrada.get("sitio", {}).get(sabor)
            if sitio is None:
                problemas.append(f"{par.nombre}/{sabor}: la entrada '{entrada['id']}'"
                                 f" no declara sitio")
                continue
            ln = sitio.get("linea")
            if ln not in por_linea:
                problemas.append(f"{par.nombre}/{sabor}: la entrada '{entrada['id']}' apunta a la"
                                 f" línea {ln}, que no es un sitio de emisión (entrada huérfana)")
                continue
            if ln in vistas:
                problemas.append(f"{par.nombre}/{sabor}: las entradas '{vistas[ln]}' y"
                                 f" '{entrada['id']}' apuntan al mismo sitio (línea {ln})")
                continue
            vistas[ln] = entrada["id"]
            if sitio.get("digest") != por_linea[ln].digest:
                problemas.append(f"{par.nombre}/{sabor}: digest obsoleto en '{entrada['id']}'"
                                 f" (línea {ln}): declarado {sitio.get('digest')},"
                                 f" vigente {por_linea[ln].digest}")
        for ln, s in sorted(por_linea.items()):
            if ln not in vistas:
                problemas.append(f"{par.nombre}/{sabor}: sitio sin entrada en la línea {ln}"
                                 f" → {s.texto[:70]}")
    return problemas


# ─────────────────────────────────────────────────────────────────────────────
# sección `parseo` — T5
# ─────────────────────────────────────────────────────────────────────────────

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_ENVOLTORIO_PS = re.compile(r"^Write-(Error|Output|Host):\s*")


@dataclass(frozen=True)
class Evento:
    id: str
    campos: tuple[tuple[str, str], ...]


@dataclass
class Fallo:
    motivo: str


def _desenvolver(texto: str, sabor: str) -> list[str]:
    """Quita el envoltorio del canal: ANSI siempre, y el prefijo de cmdlet en PowerShell.

    El envoltorio no se compara —`Write-Error` construye un registro propio y `printf >&2`
    escribe bytes literales—; el payload que transporta, sí.
    """
    lineas = _ANSI.sub("", texto).replace("\r\n", "\n").split("\n")
    if sabor == "ps":
        lineas = [_ENVOLTORIO_PS.sub("", l) for l in lineas]
    return lineas


def _fragmentar(lineas: list[str]) -> tuple[list[list[str]], list[str]]:
    """Parte la salida en fragmentos (línea con prefijo + continuación) y diagnósticos sueltos."""
    fragmentos: list[list[str]] = []
    diagnosticos: list[str] = []
    actual: list[str] | None = None
    for l in lineas:
        if any(l.startswith(p) for p in PREFIJOS_EVENTO):
            actual = [l]
            fragmentos.append(actual)
        elif actual is not None:
            actual.append(l)
        elif l.strip():
            diagnosticos.append(l)
    return fragmentos, diagnosticos


def _separador(entrada: dict, campo: str, sabor: str) -> str:
    spec = entrada.get("campos", {}).get(campo, {})
    sep = spec.get("sep", r"\s+")
    if isinstance(sep, dict):
        sep = sep.get(sabor, r"\s+")
    return sep


def _valor_campo(entrada: dict, campo: str, crudo: str, sabor: str) -> str:
    spec = entrada.get("campos", {}).get(campo, {})
    tipo = spec.get("tipo", "texto")
    if tipo == "texto":
        return crudo.strip()
    if spec.get("items"):
        # El payload viaja unido de formas distintas —POSIX con `\n`, PowerShell con `-join ' | '`—
        # y ese pegamento es del canal. `items` extrae las ENTIDADES del payload, que son del
        # predicado; el casing NUNCA se toca, que es la propiedad en disputa. Admite un patrón por
        # sabor cuando el pegamento difiere: extraer los items es del canal, y lo que queda adentro
        # de cada item —incluido un prefijo que un sabor pone y el otro no— sigue comparándose.
        items = spec["items"]
        if isinstance(items, dict):
            items = items[sabor]
        hallados = re.findall(items, crudo)
        piezas = [(h if isinstance(h, str) else h[0]).strip() for h in hallados]
        piezas = [p for p in piezas if p]
    else:
        piezas = [p for p in re.split(_separador(entrada, campo, sabor), crudo.strip()) if p]
    if tipo == "conjunto":
        return " ".join(sorted(set(piezas)))
    if tipo == "lista":
        return " ".join(piezas)
    raise ValueError(f"tipo de campo desconocido: {tipo}")


def parsear_eventos(obs: Observacion, catalogo: list[dict], sabor: str,
                    corromper: str | None = None) -> tuple[list[Evento], list[str]] | Fallo:
    """Consumo exacto y único. Un fragmento sin patrón invalida el caso completo."""
    lineas = _desenvolver(obs.stderr.decode(ENCODING, "surrogateescape"), sabor)
    fragmentos, diagnosticos = _fragmentar(lineas)

    compilados = []
    for e in catalogo:
        if e.get("solo_en") and e["solo_en"] != sabor:
            continue
        patron = e.get(sabor)
        if patron is None:
            return Fallo(f"la entrada '{e['id']}' no declara patrón para {sabor}")
        if corromper and corromper in e.get("campos", {}):
            patron = "(?!)" + patron
        compilados.append((e, re.compile(patron)))

    eventos: list[Evento] = []
    for frag in fragmentos:
        completo = "\n".join(frag).rstrip("\n")
        solo_primera = frag[0]
        elegidos = [(e, rx.fullmatch(completo)) for e, rx in compilados]
        elegidos = [(e, m) for e, m in elegidos if m]
        cola_suelta: list[str] = []
        if not elegidos:
            elegidos = [(e, rx.fullmatch(solo_primera)) for e, rx in compilados]
            elegidos = [(e, m) for e, m in elegidos if m]
            cola_suelta = [l for l in frag[1:] if l.strip()]
        if len(elegidos) == 0:
            return Fallo(f"fragmento no consumido por ningún patrón: {completo[:90]!r}")
        if len(elegidos) > 1:
            ids = ", ".join(e["id"] for e, _ in elegidos)
            return Fallo(f"fragmento consumido por más de un patrón ({ids}): {completo[:60]!r}")
        entrada, m = elegidos[0]
        declarados = entrada.get("campos", {})
        capturados = m.groupdict()
        for campo in declarados:
            if campo not in capturados or capturados[campo] is None:
                return Fallo(f"la entrada '{entrada['id']}' declara el campo '{campo}' y el patrón"
                             f" no lo extrae")
        campos = tuple(sorted(
            (c, _valor_campo(entrada, c, capturados[c], sabor)) for c in declarados))
        eventos.append(Evento(id=entrada["id"], campos=campos))
        diagnosticos += cola_suelta

    return eventos, diagnosticos


# ─────────────────────────────────────────────────────────────────────────────
# sección `clasificacion` — T6
# ─────────────────────────────────────────────────────────────────────────────

# Tabla EXHAUSTIVA sobre (código de salida × eventos reconocidos × diagnósticos no reconocidos),
# como estructura de datos enumerable y no como cadena de `if`. `motivo` documenta cada partición.
TABLA_CLASES = [
    ("timeout",                    lambda c: c["timeout"],                    "fallo",
     "el caso agotó el timeout"),
    ("diagnostico-no-reconocido",  lambda c: c["diagnosticos"] > 0,           "fallo",
     "diagnóstico del intérprete con CUALQUIER código, incluido 0"),
    ("0-sin-evento",               lambda c: c["exit"] == 0 and c["eventos"] == 0, "aceptacion",
     "código 0 sin eventos es aceptación"),
    ("0-con-evento",               lambda c: c["exit"] == 0 and c["eventos"] > 0,  "fallo",
     "señal contradictoria: emitió evento y reportó éxito"),
    ("1-con-evento",               lambda c: c["exit"] == 1 and c["eventos"] > 0,  "rechazo",
     "código 1 con al menos un evento es rechazo del predicado"),
    ("1-sin-evento",               lambda c: c["exit"] == 1 and c["eventos"] == 0, "fallo",
     "código 1 sin ningún evento reconocido"),
    ("otro-codigo",                lambda c: True,                            "fallo",
     "cualquier otro código de salida (integracion-ownership sale 99)"),
]


def clasificar(obs: Observacion, eventos: list[Evento], diagnosticos: list[str]) -> str:
    ctx = {"timeout": obs.timeout, "exit": obs.exit,
           "eventos": len(eventos), "diagnosticos": len(diagnosticos)}
    for _, pred, clase, _ in TABLA_CLASES:
        if pred(ctx):
            return clase
    raise AssertionError("la tabla de clasificación no es exhaustiva")


def particion_de(obs: Observacion, eventos: list[Evento], diagnosticos: list[str]) -> str:
    ctx = {"timeout": obs.timeout, "exit": obs.exit,
           "eventos": len(eventos), "diagnosticos": len(diagnosticos)}
    for nombre, pred, _, _ in TABLA_CLASES:
        if pred(ctx):
            return nombre
    raise AssertionError


# ─────────────────────────────────────────────────────────────────────────────
# sección `normalizacion` — T7
# ─────────────────────────────────────────────────────────────────────────────

def normalizar_stdout(b: bytes) -> str:
    """Cerrada y fijada en el plan: fin de línea, BOM inicial y espacio/tab al final de línea.

    NO ordena líneas, NO colapsa whitespace interno, NO toca el casing.
    """
    texto = b.decode(ENCODING, "surrogateescape").replace("\r\n", "\n")
    if texto.startswith("﻿"):
        texto = texto[1:]
    return "\n".join(l.rstrip(" \t") for l in texto.split("\n"))


def normalizar_artefactos(d: dict[str, bytes]) -> dict[str, str]:
    """Rutas relativas, nombres byte a byte, contenido con la misma normalización de fin de línea."""
    return {ruta: normalizar_stdout(contenido) for ruta, contenido in sorted(d.items())}


# ─────────────────────────────────────────────────────────────────────────────
# sección `comparacion` — T8
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Veredicto:
    iguales: bool
    dimensiones_divergentes: list[str] = field(default_factory=list)

    @property
    def dimension_divergente(self) -> str | None:
        for d in DIMENSIONES:
            if d in self.dimensiones_divergentes:
                return d
        return None


def comparar(clase_px: str, ev_px: list[Evento], obs_px: Observacion,
             clase_ps: str, ev_ps: list[Evento], obs_ps: Observacion) -> Veredicto:
    """Cuatro dimensiones; cada una puede gobernar el veredicto por sí sola."""
    difieren: list[str] = []
    if clase_px != clase_ps:
        difieren.append("clase")
    if sorted(map(repr, ev_px)) != sorted(map(repr, ev_ps)):
        difieren.append("eventos")
    if normalizar_stdout(obs_px.stdout) != normalizar_stdout(obs_ps.stdout):
        difieren.append("stdout")
    if normalizar_artefactos(obs_px.artefactos) != normalizar_artefactos(obs_ps.artefactos):
        difieren.append("artefactos")
    return Veredicto(iguales=not difieren, dimensiones_divergentes=difieren)


# ─────────────────────────────────────────────────────────────────────────────
# sección `resultado` — T9
# ─────────────────────────────────────────────────────────────────────────────

def resolver(veredicto: Veredicto, clase_px: str, clase_ps: str, clase_esperada: str) -> str:
    """Contrasta cada variante contra la clase esperada, además de entre sí."""
    if clase_px == "fallo" or clase_ps == "fallo":
        return "fallo"
    if not veredicto.iguales:
        return "divergencia"
    if clase_px != clase_esperada:
        return "incumplimiento_comun"
    return "paridad"


def codigo_global(resultados: list[str]) -> int:
    """Precedencia EXCLUSIVA: fallo > no comprobable > incumplimiento > divergencia > paridad."""
    peor = "paridad"
    for r in resultados:
        if PRECEDENCIA.index(r) > PRECEDENCIA.index(peor):
            peor = r
    return CODIGO[peor]


# ─────────────────────────────────────────────────────────────────────────────
# sección `auditoria` — T10
# ─────────────────────────────────────────────────────────────────────────────

def cargar_json(ruta: Path, defecto):
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding=ENCODING))


def cargar_alcance(raiz: Path) -> dict:
    return cargar_json(raiz / DIR_CASOS / "alcance.json",
                       {"cubiertos": [], "declarados_sin_matriz": {}})


def cargar_casos(raiz: Path, par: str) -> dict | None:
    return cargar_json(raiz / DIR_CASOS / par / "casos.json", None)


def auditar_matrices(raiz: Path, pares: dict[str, Par], solo: str | None,
                     estricto_mono_causa: bool, exigir_particiones: bool) -> list[str]:
    problemas: list[str] = []
    alcance = cargar_alcance(raiz)
    huellas = cargar_json(raiz / DIR_CASOS / "huellas.json", {})
    cubiertos = alcance.get("cubiertos", [])
    declarados = alcance.get("declarados_sin_matriz", {})

    if solo is None:
        for nombre in pares:
            if nombre in cubiertos or nombre in declarados:
                continue
            problemas.append(f"{nombre}: ni cubierto ni declarado sin matriz en alcance.json")

    objetivo = [solo] if solo else cubiertos
    for nombre in objetivo:
        par = pares.get(nombre)
        if par is None:
            problemas.append(f"{nombre}: declarado cubierto pero no existe en el inventario")
            continue
        matriz = cargar_casos(raiz, nombre)
        if matriz is None:
            problemas.append(f"{nombre}: declarado cubierto y sin casos.json")
            continue

        # ── huella: un cuerpo cambiado invalida la cobertura hasta auditoría registrada
        registro = huellas.get(nombre)
        if registro is None:
            problemas.append(f"{nombre}: sin registro de auditoría en huellas.json")
        else:
            for sabor in ("posix", "ps"):
                vigente = par.digest(sabor)
                if registro.get(sabor) != vigente:
                    problemas.append(
                        f"{nombre}/{sabor}: huella obsoleta — auditada {registro.get(sabor)},"
                        f" cuerpo vigente {vigente}; la cobertura de este par queda invalidada"
                        f" hasta renovar la auditoría")

        # ── cláusulas: clave foránea al catálogo, o anclaje al observable en pares sin eventos
        catalogo = {e["id"] for e in cargar_catalogo(raiz, nombre)}
        observables = set(matriz.get("observables", {}))
        clausulas = {c["id"]: c for c in matriz.get("clausulas", [])}
        for cid, c in clausulas.items():
            if c.get("tipo") == "observable":
                if cid not in observables:
                    problemas.append(f"{nombre}: la cláusula '{cid}' es de tipo observable y no"
                                     f" está declarada en 'observables'")
            elif cid not in catalogo:
                problemas.append(f"{nombre}: la cláusula '{cid}' no corresponde a ningún"
                                 f" subpredicado del catálogo (sin respaldo en el cuerpo)")
        if not clausulas:
            problemas.append(f"{nombre}: no declara cláusulas")

        casos = matriz.get("casos", [])
        for caso in casos:
            if not caso.get("precondicion"):
                problemas.append(f"{nombre}/{caso.get('nombre')}: sin precondición observable")
            if caso.get("clase_esperada") not in CLASES:
                problemas.append(f"{nombre}/{caso.get('nombre')}: clase_esperada inválida")
            faltantes = set(clausulas) - set(caso.get("clausulas", {}))
            if faltantes:
                problemas.append(f"{nombre}/{caso.get('nombre')}: no declara el resultado esperado"
                                 f" de {sorted(faltantes)} — la mono-causalidad se mide por"
                                 f" observable, así que TODAS las cláusulas se declaran")

        # ── mono-causalidad por observable
        if estricto_mono_causa:
            positivos = [c for c in casos if c.get("particion") == "positivo"]
            if not positivos:
                problemas.append(f"{nombre}: sin caso positivo")
            for c in positivos:
                malas = [k for k, v in c.get("clausulas", {}).items() if v != "valido"]
                if malas:
                    problemas.append(f"{nombre}/{c['nombre']}: el positivo tiene {malas}"
                                     f" fuera de su lado válido")
            for c in casos:
                if c.get("particion") == "positivo":
                    continue
                invalidas = [k for k, v in c.get("clausulas", {}).items() if v == "invalido"]
                if c.get("exento_mono_causa"):
                    # La exención se REGISTRA, no se esconde: un caso que dispara dos cláusulas
                    # puede enmascarar una divergencia, y sale del estricto solo con un motivo
                    # escrito visible en cada auditoría.
                    print(f"  exento mono-causa {nombre}/{c['nombre']} ({len(invalidas)}"
                          f" cláusulas): {c['exento_mono_causa']}")
                    continue
                # Una partición de casing o de cardinalidad puede dejar la cláusula del lado
                # VÁLIDO —`**identificar**` no satisface el literal `**IDENTIFICAR**`, así que la
                # cláusula "IDENTIFICAR ausente" sigue cumpliéndose—, y ahí lo que se exige no es
                # que mute sino que declare a qué cláusula apunta. Lo que nunca se admite es más
                # de una: eso es lo que enmascara divergencias.
                minimo = 1 if c.get("particion") == "invalido" else 0
                if not minimo <= len(invalidas) <= 1:
                    problemas.append(f"{nombre}/{c['nombre']}: mueve {len(invalidas)} cláusulas al"
                                     f" lado inválido ({invalidas}); un mutante mono-causa mueve"
                                     f" exactamente una")
                elif invalidas and not set(_objetivos(c)) & set(invalidas):
                    problemas.append(f"{nombre}/{c['nombre']}: declara objetivo"
                                     f" {_objetivos(c)} y el inválido es {invalidas}")
                if not _objetivos(c):
                    problemas.append(f"{nombre}/{c['nombre']}: no declara a qué cláusula apunta")

        # ── particiones obligatorias del dominio
        if exigir_particiones:
            hay_positivo = any(x.get("particion") == "positivo" for x in casos)
            for cid, c in clausulas.items():
                dirigidos = {x.get("particion") for x in casos
                             if cid in _objetivos(x)}
                if hay_positivo:
                    dirigidos.add("positivo")
                if c.get("sin_caso"):
                    print(f"  sin caso declarado {nombre}/{cid}: {c['sin_caso']}")
                    continue
                if c.get("compara_cadenas"):
                    faltan = [p for p in PARTICIONES_CADENA if p not in dirigidos]
                    if faltan:
                        problemas.append(f"{nombre}/{cid}: compara cadenas y le faltan las"
                                         f" particiones {faltan} (el caso de casing es el que"
                                         f" revela la case-insensitivity de PowerShell)")
                if c.get("agrega"):
                    faltan = [p for p in PARTICIONES_CARDINALIDAD if p not in dirigidos]
                    if faltan:
                        problemas.append(f"{nombre}/{cid}: agrega y le faltan las particiones"
                                         f" {faltan} (el caso par es el que revela el redondeo"
                                         f" del índice medio)")
    return problemas


def _objetivos(caso: dict) -> list[str]:
    if caso.get("objetivos"):
        return list(caso["objetivos"])
    return [caso["objetivo"]] if caso.get("objetivo") else []


# ─────────────────────────────────────────────────────────────────────────────
# corrida de un caso
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ResultadoCaso:
    par: str
    caso: str
    resultado: str
    dimension: str | None = None
    detalle: str = ""
    eventos_px: list[Evento] = field(default_factory=list)
    eventos_ps: list[Evento] = field(default_factory=list)
    obs_px: Observacion | None = None
    obs_ps: Observacion | None = None


def correr_caso(raiz: Path, par: Par, matriz: dict, caso: dict, catalogo: list[dict],
                orden: tuple[str, str] = ("posix", "ps"), corromper: str | None = None,
                interprete_ps: str | None = None) -> ResultadoCaso:
    fixture = None
    if caso.get("fixture"):
        fixture = raiz / DIR_CASOS / par.nombre / "fixtures" / caso["fixture"]
    entradas = caso.get("entradas", {})
    timeout = caso.get("timeout", TIMEOUT_DEFECTO)
    reemplazos = caso.get("reemplazos", [])

    ok, detalle_locale = locale_usable()
    if not ok:
        return ResultadoCaso(par.nombre, caso["nombre"], "no_comprobable", detalle=detalle_locale)

    obs: dict[str, Observacion] = {}
    for sabor in orden:
        cuerpo = par.cuerpo_posix if sabor == "posix" else par.cuerpo_ps
        try:
            obs[sabor] = ejecutar(cuerpo, sabor, fixture, entradas, timeout=timeout,
                                  interprete=interprete_ps if sabor == "ps" else None,
                                  reemplazos=reemplazos)
        except SinInterprete as exc:
            return ResultadoCaso(par.nombre, caso["nombre"], "no_comprobable", detalle=str(exc))

    parsed: dict[str, tuple[list[Evento], list[str]]] = {}
    for sabor in ("posix", "ps"):
        r = parsear_eventos(obs[sabor], catalogo, sabor, corromper=corromper)
        if isinstance(r, Fallo):
            return ResultadoCaso(par.nombre, caso["nombre"], "fallo",
                                 detalle=f"{sabor}: {r.motivo}")
        parsed[sabor] = r

    clase_px = clasificar(obs["posix"], *parsed["posix"])
    clase_ps = clasificar(obs["ps"], *parsed["ps"])
    ver = comparar(clase_px, parsed["posix"][0], obs["posix"],
                   clase_ps, parsed["ps"][0], obs["ps"])
    res = resolver(ver, clase_px, clase_ps, caso["clase_esperada"])
    detalle = f"posix={clase_px} ps={clase_ps} esperada={caso['clase_esperada']}"
    if res == "fallo":
        for sabor, (evs, diags) in parsed.items():
            if diags:
                detalle += f" · {sabor} diagnóstico: {diags[0][:80]}"
    return ResultadoCaso(par.nombre, caso["nombre"], res, ver.dimension_divergente, detalle,
                         parsed["posix"][0], parsed["ps"][0], obs["posix"], obs["ps"])


# ─────────────────────────────────────────────────────────────────────────────
# sección `reporte` — T11
# ─────────────────────────────────────────────────────────────────────────────

NOTA_EXCLUSIONES = [
    "no cubierto: `rebaseline-worktree` — opera sobre worktrees de Git que crea y destruye;"
    " probarlo exigiría levantar repositorios desechables.",
    "fuera de detección automática: la ATOMICIDAD de publicación (`split-paginado` publica el"
    " metaíndice con temporal + `mv` en POSIX y escribe directo al destino en PowerShell);"
    " solo se observaría instrumentando operaciones o con un lector concurrente.",
]


def imprimir_exclusiones() -> None:
    print("\nExclusiones declaradas (en cada corrida):")
    for n in NOTA_EXCLUSIONES:
        print(f"  · {n}")


def cmd_entorno(raiz: Path) -> int:
    try:
        ruta, version = detectar_pwsh()
        print(f"intérprete PowerShell : {ruta} (v{version})")
    except SinInterprete as exc:
        print(f"intérprete PowerShell : AUSENTE — {exc}")
    print(f"candidatos            : {', '.join(_candidatos_pwsh())}")
    print(f"shell POSIX           : /bin/sh")
    print(f"timeout por caso      : {TIMEOUT_DEFECTO}s")
    print(f"locale                : {', '.join(f'{k}={v}' for k, v in LOCALE.items())}")
    ok, detalle = locale_usable()
    print(f"sonda de locale       : {'ok — pliega fuera de ASCII' if ok else 'FALLA — ' + detalle}")
    print(f"encoding              : {ENCODING}")
    print(f"raíz                  : {raiz}")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# autotests
# ─────────────────────────────────────────────────────────────────────────────

def _ok(cond: bool, etiqueta: str, fallos: list[str]) -> None:
    print(f"  {'ok  ' if cond else 'FALLA'} {etiqueta}")
    if not cond:
        fallos.append(etiqueta)


def autotest_extractor() -> int:
    print("autotest del extractor (recorte exacto + fallo cerrado)")
    fallos: list[str] = []
    feliz = "ruido previo\n# @bloque:x\nA\nB\n# @fin:x\nruido posterior"
    _ok(extraer_bloque(feliz, "x") == "A\nB", "recorte byte a byte entre marcadores", fallos)

    mutantes = {
        "@fin ausente": "# @bloque:x\nA\nB\nCONTENIDO AJENO",
        "cierre con otro nombre": "# @bloque:x\nA\n# @fin:y\n",
        "cierre duplicado": "# @bloque:x\nA\n# @fin:x\nB\n# @fin:x\n",
        "segundo bloque posterior": "# @bloque:x\nA\n# @fin:x\nB\n# @bloque:x\nC\n# @fin:x\n",
    }
    for etiqueta, texto in mutantes.items():
        try:
            cuerpo = extraer_bloque(texto, "x")
            _ok(False, f"{etiqueta} → devolvió cuerpo {cuerpo!r} en vez de fallar", fallos)
        except BloqueInvalido as exc:
            _ok(True, f"{etiqueta} → BloqueInvalido: {exc.motivo}", fallos)
    _ok(True, "ningún mutante devolvió cuerpo parcial", fallos)
    return 0 if not fallos else CODIGO["fallo"]


def autotest_escaner() -> int:
    """Cada forma de emisión reconocida, y cada explicación que evita una anomalía, con su control
    en las DOS direcciones: que la forma nueva produzca sitio, y que nada real pueda esconderse
    detrás de ella."""
    print("autotest del escáner de sitios (formas de emisión y explicaciones)")
    fallos: list[str] = []

    def sitios_de(cuerpo, sabor):
        s, a = escanear_sitios(cuerpo, sabor)
        return [x.literal for x in s], a

    # ── positivos: cada forma reconocida produce un sitio ────────────────────
    emisiones = [
        ("posix", 'echo "GUARD:x algo"', "GUARD:x algo"),
        ("posix", "printf 'ARNES:no existe %s\\n' \"$f\"", "ARNES:no existe %s\\n"),
        ("posix", '  print "GUARD:x " G          > "/dev/stderr"', "GUARD:x "),
        ("posix", 'if (r == "") { print "ARNES:falta algo"; exit 99 }', "ARNES:falta algo"),
        ("posix", 'if (d) for (i = 1; i <= n; i++) print "GUARD:x " a[i]', "GUARD:x "),
        ("ps", 'Write-Error "GUARD:x algo"', "GUARD:x algo"),
        ("ps", 'Write-Output "GUARD:x algo"', "GUARD:x algo"),
        ("ps", '[Console]::Error.WriteLine("GUARD:x $G")', "GUARD:x $G"),
        ("ps", "  [Console]::Error.WriteLine('ARNES:no existe')", "ARNES:no existe"),
    ]
    for sabor, linea, literal in emisiones:
        lits, anom = sitios_de(linea, sabor)
        _ok(lits == [literal] and not anom,
            f"{sabor}: {linea.strip()[:44]!r} → sitio", fallos)

    # ── negativos: lo que NO debe contarse como sitio ────────────────────────
    no_emisiones = [
        ("posix", '  if ($7 == "BLOCKED") continue', "valor de enum"),
        ("posix", '# echo "GUARD:x algo" — el comentario no emite', "comentario"),
        ("posix", 'falla("m", "la fila " id " declara BLOCKED sin justificar")', "prosa"),
        ("ps", "if ($f.base -eq 'BLOCKED') { continue }", "valor de enum"),
        ("ps", "Falla 'm' \"la fila $($f.id) declara BLOCKED sin justificar\"", "prosa"),
    ]
    for sabor, linea, motivo in no_emisiones:
        lits, anom = sitios_de(linea, sabor)
        _ok(not lits and not anom, f"{sabor}: {motivo} → ni sitio ni anomalía", fallos)

    # ── la explicación nueva no puede tapar una emisión real ─────────────────
    # Mismo literal con prosa Y con mensaje: si `prosa` ganara, el sitio desaparecería.
    lits, anom = sitios_de('print "GUARD:x algo" " y la fila declara BLOCKED"', "posix")
    _ok(lits == ["GUARD:x algo"], "prosa + mensaje en la misma línea → sigue siendo sitio", fallos)

    # Un prefijo que encabeza su literal SIN forma de emisión reconocida sigue siendo anomalía:
    # es el caso del emisor que el escáner todavía no conoce, y ese no se puede perder.
    for sabor, linea in [("posix", 'salida="GUARD:x algo"'), ("ps", '$m = "GUARD:x algo"')]:
        lits, anom = sitios_de(linea, sabor)
        _ok(not lits and len(anom) == 1, f"{sabor}: mensaje sin emisor reconocida → anomalía", fallos)

    # Y el literal que ES exactamente el prefijo sigue siendo valor, no mensaje.
    lits, anom = sitios_de('print "BLOCKED"', "posix")
    _ok(not lits and not anom, "literal exactamente igual al prefijo → valor, no mensaje", fallos)

    return 0 if not fallos else CODIGO["fallo"]


def autotest_normalizacion() -> int:
    print("autotest de normalización (colapsa lo cosmético, preserva lo semántico)")
    fallos: list[str] = []
    equivalentes = [
        ("fin de línea", b"a\r\nb\r\n", b"a\nb\n"),
        ("BOM inicial", "﻿a\n".encode(ENCODING), b"a\n"),
        ("espacio final de línea", b"a   \nb\t\n", b"a\nb\n"),
    ]
    for etiqueta, x, y in equivalentes:
        _ok(normalizar_stdout(x) == normalizar_stdout(y), f"se unifican: {etiqueta}", fallos)

    distintas = [
        ("orden de líneas", b"a\nb\n", b"b\na\n"),
        ("whitespace interno", b"a  b\n", b"a b\n"),
        ("casing", b"Alpha\n", b"alpha\n"),
        ("BOM interno (no inicial)", "a﻿b\n".encode(ENCODING), b"ab\n"),
    ]
    for etiqueta, x, y in distintas:
        _ok(normalizar_stdout(x) != normalizar_stdout(y), f"sobreviven: {etiqueta}", fallos)

    a = {"p/x.md": b"uno\r\n"}
    _ok(normalizar_artefactos(a) == normalizar_artefactos({"p/x.md": b"uno\n"}),
        "artefactos: se unifica el fin de línea del contenido", fallos)
    for etiqueta, otro in [("nombre de archivo", {"p/X.md": b"uno\n"}),
                           ("byte de contenido", {"p/x.md": b"dos\n"}),
                           ("archivo de más", {"p/x.md": b"uno\n", "p/y.md": b""})]:
        _ok(normalizar_artefactos(a) != normalizar_artefactos(otro),
            f"artefactos: sobrevive {etiqueta}", fallos)
    return 0 if not fallos else CODIGO["fallo"]


def _obs(exit=0, stdout=b"", stderr=b"", artefactos=None, timeout=False) -> Observacion:
    return Observacion(exit=exit, stdout=stdout, stderr=stderr,
                       artefactos=artefactos or {}, timeout=timeout)


def autotest_clasificador() -> int:
    print("autotest del clasificador (cada partición de la tabla, una por una)")
    fallos: list[str] = []
    ev = [Evento("x", ())]
    casos = [
        ("0-sin-evento",              _obs(exit=0), [], [],                  "aceptacion"),
        ("1-con-evento",              _obs(exit=1), ev, [],                  "rechazo"),
        ("1-sin-evento",              _obs(exit=1), [], [],                  "fallo"),
        ("0-con-evento",              _obs(exit=0), ev, [],                  "fallo"),
        ("diagnostico-no-reconocido", _obs(exit=0), [], ["InvalidOperation"], "fallo"),
        ("timeout",                   _obs(exit=-1, timeout=True), [], [],   "fallo"),
        ("otro-codigo",               _obs(exit=99), [], [],                 "fallo"),
    ]
    cubiertas = set()
    for etiqueta, obs, evs, diags, esperada in casos:
        obtenida = clasificar(obs, evs, diags)
        part = particion_de(obs, evs, diags)
        cubiertas.add(part)
        _ok(obtenida == esperada and part == etiqueta,
            f"{etiqueta} → {obtenida} (partición {part}, esperada {esperada})", fallos)
    declaradas = {n for n, _, _, _ in TABLA_CLASES}
    _ok(cubiertas == declaradas,
        f"toda partición de la tabla tiene una afirmación propia ({len(cubiertas)}/"
        f"{len(declaradas)})", fallos)
    _ok(clasificar(_obs(exit=0), [], ["ParserError"]) == "fallo",
        "un diagnóstico con exit 0 NO se lee como aceptación", fallos)
    return 0 if not fallos else CODIGO["fallo"]


def autotest_comparador(dimension: str | None) -> int:
    print("autotest del comparador (cada dimensión gobierna por sí sola)")
    fallos: list[str] = []
    base_ev = [Evento("e1", (("entidades", "A C"),))]
    base_obs = _obs(stdout=b"igual\n", artefactos={"a.txt": b"igual\n"})

    variantes = {
        "clase": ("aceptacion", base_ev, base_obs, "rechazo", base_ev, base_obs),
        "eventos": ("aceptacion", base_ev, base_obs, "aceptacion",
                    [Evento("e1", (("entidades", "C"),))], base_obs),
        "stdout": ("aceptacion", base_ev, base_obs, "aceptacion", base_ev,
                   _obs(stdout=b"otro\n", artefactos={"a.txt": b"igual\n"})),
        "artefactos": ("aceptacion", base_ev, base_obs, "aceptacion", base_ev,
                       _obs(stdout=b"igual\n", artefactos={"a.txt": b"otro\n"})),
    }
    objetivo = [dimension] if dimension else list(DIMENSIONES)
    for d in objetivo:
        args = variantes[d]
        v = comparar(*args)
        _ok(not v.iguales and v.dimensiones_divergentes == [d],
            f"solo difiere {d} → divergencia atribuida a {v.dimensiones_divergentes}", fallos)
    if not dimension:
        v = comparar("aceptacion", base_ev, base_obs, "aceptacion", base_ev, base_obs)
        _ok(v.iguales, "observaciones idénticas → sin divergencia", fallos)
    reemplazos_rc = autotest_reemplazos()
    return 0 if not fallos and reemplazos_rc == 0 else CODIGO["fallo"]


def autotest_reemplazos() -> int:
    print("autotest de reemplazos declarativos (exactitud, confinamiento y aislamiento)")
    fallos: list[str] = []

    with tempfile.TemporaryDirectory(prefix="paridad-reemplazos-") as tmp_crudo:
        raiz = Path(tmp_crudo)

        def caso(contenido: str = "alpha") -> Path:
            destino = Path(tempfile.mkdtemp(prefix="caso-", dir=raiz))
            (destino / "manifest.json").write_text(contenido, encoding=ENCODING)
            return destino

        simple = caso()
        aplicar_reemplazos(simple, [
            {"archivo": "manifest.json", "buscar": "alpha", "reemplazar": "beta"}
        ])
        _ok((simple / "manifest.json").read_text(encoding=ENCODING) == "beta",
            "una coincidencia exacta se reemplaza", fallos)

        encadenado = caso()
        aplicar_reemplazos(encadenado, [
            {"archivo": "manifest.json", "buscar": "alpha", "reemplazar": "bridge"},
            {"archivo": "manifest.json", "buscar": "bridge", "reemplazar": "omega"},
        ])
        _ok((encadenado / "manifest.json").read_text(encoding=ENCODING) == "omega",
            "los reemplazos son secuenciales", fallos)

        mutantes = [
            ("ausencia", caso(),
             [{"archivo": "manifest.json", "buscar": "missing", "reemplazar": "x"}]),
            ("duplicación", caso("alpha alpha"),
             [{"archivo": "manifest.json", "buscar": "alpha", "reemplazar": "x"}]),
            ("ruta absoluta", caso(),
             [{"archivo": str((raiz / "externo.txt").resolve()),
               "buscar": "alpha", "reemplazar": "x"}]),
            ("traversal", caso(),
             [{"archivo": "../externo.txt", "buscar": "alpha", "reemplazar": "x"}]),
            ("esquema incompleto", caso(),
             [{"archivo": "manifest.json", "buscar": "alpha"}]),
            ("tipo inválido", caso(),
             [{"archivo": "manifest.json", "buscar": 7, "reemplazar": "x"}]),
        ]
        for etiqueta, destino, reemplazos in mutantes:
            try:
                aplicar_reemplazos(destino, reemplazos)
                _ok(False, f"{etiqueta} se rechaza", fallos)
            except (TypeError, ValueError):
                _ok(True, f"{etiqueta} se rechaza", fallos)

        try:
            ejecutar("exit 0", "posix", caso(), {}, raiz_tmp=raiz, reemplazos={})
            _ok(False, "un contenedor de reemplazos no-lista se rechaza desde ejecutar", fallos)
        except TypeError:
            _ok(True, "un contenedor de reemplazos no-lista se rechaza desde ejecutar", fallos)

        exterior = raiz / "externo.txt"
        exterior.write_text("testigo exterior", encoding=ENCODING)
        con_enlace = caso()
        (con_enlace / "escape.json").symlink_to(exterior)
        try:
            aplicar_reemplazos(con_enlace, [
                {"archivo": "escape.json", "buscar": "testigo", "reemplazar": "alterado"}
            ])
            _ok(False, "un symlink exterior se rechaza", fallos)
        except (TypeError, ValueError):
            _ok(exterior.read_text(encoding=ENCODING) == "testigo exterior",
                "un symlink exterior se rechaza sin tocar el testigo", fallos)

        fixture = raiz / "fixture"
        fixture.mkdir()
        fuente = fixture / "manifest.json"
        fuente.write_text("alpha", encoding=ENCODING)
        huella_fuente = hashlib.sha256(fuente.read_bytes()).hexdigest()
        huella_exterior = hashlib.sha256(exterior.read_bytes()).hexdigest()
        observacion = ejecutar(
            "exit 0", "posix", fixture, {}, raiz_tmp=raiz,
            reemplazos=[{"archivo": "manifest.json", "buscar": "alpha", "reemplazar": "beta"}],
        )
        _ok(observacion.artefactos.get("manifest.json") == b"beta"
            and hashlib.sha256(fuente.read_bytes()).hexdigest() == huella_fuente
            and hashlib.sha256(exterior.read_bytes()).hexdigest() == huella_exterior,
            "reemplazos exactos: éxito, ausencia, duplicación e inmutabilidad", fallos)

    return 0 if not fallos else CODIGO["fallo"]


def autotest_precedencia() -> int:
    print("autotest de precedencia global (exclusiva y declarada)")
    fallos: list[str] = []
    combos = [
        (["paridad", "paridad"], "paridad"),
        (["paridad", "divergencia"], "divergencia"),
        (["divergencia", "incumplimiento_comun"], "incumplimiento_comun"),
        (["incumplimiento_comun", "no_comprobable"], "no_comprobable"),
        (["no_comprobable", "divergencia", "fallo"], "fallo"),
    ]
    for entrada, esperado in combos:
        _ok(codigo_global(entrada) == CODIGO[esperado],
            f"{entrada} → {esperado} (código {CODIGO[esperado]})", fallos)
    _ok(len({CODIGO[k] for k in PRECEDENCIA}) == len(PRECEDENCIA),
        "los cinco estados tienen código propio y distinto", fallos)
    return 0 if not fallos else CODIGO["fallo"]


def autotest_catalogo(raiz: Path, pares: dict[str, Par]) -> int:
    """Testigos centinela: el patrón matchea el testigo y extrae EXACTAMENTE lo declarado."""
    print("autotest del catálogo (testigos centinela por entrada)")
    fallos: list[str] = []
    alcance = cargar_alcance(raiz)
    total = 0
    for nombre in alcance.get("cubiertos", []):
        for entrada in cargar_catalogo(raiz, nombre):
            for sabor in ("posix", "ps"):
                if entrada.get("solo_en") and entrada["solo_en"] != sabor:
                    continue
                testigo = entrada.get("testigo", {}).get(sabor)
                if testigo is None:
                    _ok(False, f"{nombre}/{entrada['id']}/{sabor}: sin testigo centinela", fallos)
                    continue
                total += 1
                rx = re.compile(entrada[sabor])
                m = rx.fullmatch(testigo["texto"])
                if not m:
                    _ok(False, f"{nombre}/{entrada['id']}/{sabor}: el patrón no matchea su testigo",
                        fallos)
                    continue
                obtenido = {}
                falta = False
                for campo in entrada.get("campos", {}):
                    crudo = m.groupdict().get(campo)
                    if crudo is None:
                        _ok(False, f"{nombre}/{entrada['id']}/{sabor}: matchea pero descarta el"
                                   f" campo declarado '{campo}'", fallos)
                        falta = True
                        continue
                    obtenido[campo] = _valor_campo(entrada, campo, crudo, sabor)
                if falta:
                    continue
                esperado = {k: (" ".join(sorted(set(v))) if isinstance(v, list) else v)
                            for k, v in testigo.get("campos", {}).items()}
                _ok(obtenido == esperado,
                    f"{nombre}/{entrada['id']}/{sabor}: extrae {obtenido or '{}'}", fallos)
    _ok(total > 0, f"se probaron {total} testigos", fallos)
    return 0 if not fallos else CODIGO["fallo"]


# ── pares sintéticos: prueban estados del arnés que ningún par real produce a pedido
PARES_SINTETICOS = {
    "autotest-timeout": {
        "posix": "sleep 60\nexit 0",
        "ps": "Start-Sleep -Seconds 60\nexit 0",
        "clase_esperada": "aceptacion",
        "timeout": 5,
        "descripcion": "cuerpo que se cuelga; el timeout tiene que cortar y clasificar fallo",
    },
    "autotest-fallo-comun": {
        # Diagnóstico del intérprete con exit 0 en los DOS sabores: el falso verde medido.
        "posix": "printf 'sh: linea 1: cosa: comando no encontrado\\n' >&2\nexit 0",
        "ps": "$x = $null\n$y = $x.Trim()\nexit 0",
        "clase_esperada": "aceptacion",
        "descripcion": "ambos sabores emiten diagnóstico del intérprete y salen 0",
    },
    "autotest-incumplimiento-comun": {
        "posix": "exit 0",
        "ps": "exit 0",
        "clase_esperada": "rechazo",
        "descripcion": "ambos aceptan un mutante cuya clase esperada es rechazo",
    },
}


def correr_par_sintetico(nombre: str) -> ResultadoCaso:
    spec = PARES_SINTETICOS[nombre]
    par = Par(nombre, "(sintético)", 0, 0, spec["posix"], spec["ps"])
    caso = {"nombre": "unico", "clase_esperada": spec["clase_esperada"],
            "timeout": spec.get("timeout", TIMEOUT_DEFECTO), "entradas": {},
            "precondicion": spec["descripcion"]}
    return correr_caso(Path("/"), par, {}, caso, [])


# ─────────────────────────────────────────────────────────────────────────────
# comandos
# ─────────────────────────────────────────────────────────────────────────────

def cmd_listar_inventario(raiz: Path) -> int:
    pares, huerfanas, solo_posix = descubrir_pares(raiz)
    print(f"variantes -ps encontradas : {len(pares) + len(huerfanas)}")
    print(f"con par POSIX homónimo    : {len(pares)}")
    print(f"huérfanas                 : {len(huerfanas)}")
    print(f"POSIX sin variante -ps    : {len(solo_posix)} ({', '.join(solo_posix)})")
    por_archivo: dict[str, list[str]] = {}
    for p in pares.values():
        por_archivo.setdefault(p.archivo, []).append(p.nombre)
    print()
    for archivo in sorted(por_archivo):
        print(f"{archivo} ({len(por_archivo[archivo])})")
        for n in sorted(por_archivo[archivo]):
            par = pares[n]
            print(f"    {n:<32} posix:{par.linea_posix:<6} ps:{par.linea_ps}")
    if huerfanas:
        print("\nHUÉRFANAS (variante -ps sin par POSIX homónimo en el mismo archivo):")
        for h in huerfanas:
            print(f"    {h}")
        return CODIGO["fallo"]
    return 0


def cmd_auditar_catalogo(raiz: Path, pares: dict[str, Par]) -> int:
    alcance = cargar_alcance(raiz)
    cubiertos = alcance.get("cubiertos", [])
    declarados = alcance.get("declarados_sin_matriz", {})
    problemas: list[str] = []
    for nombre in pares:
        if nombre in cubiertos or nombre in declarados:
            continue
        problemas.append(f"{nombre}: ni cubierto ni declarado sin matriz en alcance.json")
    sitios_totales = 0
    for nombre in cubiertos:
        par = pares.get(nombre)
        if par is None:
            problemas.append(f"{nombre}: declarado cubierto y ausente del inventario")
            continue
        catalogo = cargar_catalogo(raiz, nombre)
        sitios_totales += len(escanear_sitios(par.cuerpo_posix, "posix")[0])
        problemas += auditar_catalogo_de_par(par, catalogo)
    print(f"pares en alcance      : {len(pares)}")
    print(f"cubiertos por catálogo: {len(cubiertos)}")
    print(f"declarados sin matriz : {len(declarados)}")
    print(f"sitios POSIX auditados: {sitios_totales}")
    for p in problemas:
        print(f"  ROJO {p}")
    if declarados:
        print("\nDeclarados sin matriz (no comprobados, distinto de en paridad):")
        for n, razon in sorted(declarados.items()):
            print(f"  · {n}: {razon}")
    return 0 if not problemas else CODIGO["fallo"]


def cmd_registrar_auditoria(raiz: Path, pares: dict[str, Par], solo: str | None) -> int:
    """Renueva el registro de auditoría: liga la cobertura al cuerpo VIGENTE.

    Es el acto que AC-5 exige tras cambiar un cuerpo. No comprueba que la cobertura siga siendo
    correcta —eso lo hace quien audita—: deja constancia de contra qué cuerpo se auditó.
    """
    ruta = raiz / DIR_CASOS / "huellas.json"
    huellas = cargar_json(ruta, {})
    alcance = cargar_alcance(raiz)
    objetivo = [solo] if solo else alcance.get("cubiertos", [])
    for nombre in objetivo:
        par = pares.get(nombre)
        if par is None:
            print(f"{nombre}: no existe en el inventario")
            return CODIGO["fallo"]
        huellas[nombre] = {"posix": par.digest("posix"), "ps": par.digest("ps")}
        print(f"registrado {nombre}: posix={huellas[nombre]['posix']} ps={huellas[nombre]['ps']}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(huellas, indent=2, ensure_ascii=False,
                               sort_keys=True) + "\n", encoding=ENCODING)
    return 0


def cmd_resincronizar_catalogo(raiz: Path, pares: dict[str, Par], solo: str | None) -> int:
    """Reubica las entradas cuyo sitio SE MOVIÓ sin cambiar, por identidad de digest.

    Distingue las dos cosas que un cambio de cuerpo mezcla: una sentencia que se corrió de línea
    sigue siendo la misma sentencia, y su entrada la sigue describiendo; una sentencia que cambió
    de texto puede haber cambiado de significado, y ahí el patrón hay que revisarlo a mano. Solo
    reubica cuando encuentra EXACTAMENTE un sitio con el mismo digest: cero o varios es rojo.
    """
    alcance = cargar_alcance(raiz)
    objetivo = [solo] if solo else alcance.get("cubiertos", [])
    problemas: list[str] = []
    movidas = 0
    for nombre in objetivo:
        par = pares.get(nombre)
        if par is None:
            problemas.append(f"{nombre}: no existe en el inventario")
            continue
        ruta = raiz / DIR_CASOS / nombre / "eventos.json"
        catalogo = cargar_catalogo(raiz, nombre)
        if not catalogo:
            continue
        cambio = False
        for sabor in ("posix", "ps"):
            cuerpo = par.cuerpo_posix if sabor == "posix" else par.cuerpo_ps
            sitios, _ = escanear_sitios(cuerpo, sabor)
            por_linea = {s.linea: s for s in sitios}
            for entrada in catalogo:
                if entrada.get("solo_en") and entrada["solo_en"] != sabor:
                    continue
                sitio = entrada.get("sitio", {}).get(sabor)
                if sitio is None:
                    continue
                ln, dg = sitio.get("linea"), sitio.get("digest")
                if ln in por_linea and por_linea[ln].digest == dg:
                    continue
                candidatos = [s for s in sitios if s.digest == dg]
                if len(candidatos) == 1:
                    sitio["linea"] = candidatos[0].linea
                    movidas += 1
                    cambio = True
                    print(f"  movida {nombre}/{sabor}/{entrada['id']}: {ln} → "
                          f"{candidatos[0].linea}")
                    continue
                if not candidatos:
                    lit = entrada.get("literal", {}).get(sabor)
                    mismos = [s for s in sitios if lit and s.literal == lit]
                    if len(mismos) == 1:
                        sitio["linea"], sitio["digest"] = mismos[0].linea, mismos[0].digest
                        movidas += 1
                        cambio = True
                        print(f"  reblanqueada {nombre}/{sabor}/{entrada['id']}: la sentencia"
                              f" cambió y el MENSAJE no → línea {mismos[0].linea}")
                        continue
                    problemas.append(
                        f"{nombre}/{sabor}/{entrada['id']}: cambió el mensaje de la línea {ln},"
                        f" no solo la sentencia — revisá el patrón a mano")
                else:
                    problemas.append(
                        f"{nombre}/{sabor}/{entrada['id']}: {len(candidatos)} sentencias con el"
                        f" mismo digest; la reubicación sería una adivinanza")
        if cambio:
            ruta.write_text(json.dumps(catalogo, indent=2, ensure_ascii=False) + "\n",
                            encoding=ENCODING)
    print(f"entradas reubicadas: {movidas}")
    for p in problemas:
        print(f"  ROJO {p}")
    return 0 if not problemas else CODIGO["fallo"]


def cmd_auditar_matrices(raiz: Path, pares: dict[str, Par], args) -> int:
    problemas = auditar_matrices(raiz, pares, args.par, args.estricto_mono_causa,
                                 args.exigir_particiones)
    alcance = cargar_alcance(raiz)
    print(f"auditoría de matrices — cubiertos: {len(alcance.get('cubiertos', []))}"
          f" · declarados sin matriz: {len(alcance.get('declarados_sin_matriz', {}))}")
    for p in problemas:
        print(f"  ROJO {p}")
    if not problemas:
        print("  todas las cláusulas cubiertas se ligan al cuerpo vigente y declaran precondición")
    return 0 if not problemas else CODIGO["fallo"]


def _huella_arbol(base: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(base.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(base)).encode(ENCODING))
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _git_status(raiz: Path) -> str:
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=str(raiz),
                           capture_output=True, timeout=60, check=False)
        return r.stdout.decode(ENCODING, "replace")
    except (OSError, subprocess.TimeoutExpired):
        return "(git no disponible)"


def cmd_correr(raiz: Path, pares: dict[str, Par], args) -> int:
    if args.par in PARES_SINTETICOS:
        r = correr_par_sintetico(args.par)
        print(f"{args.par:<32} {r.resultado:<22} {r.detalle}")
        return codigo_global([r.resultado])

    alcance = cargar_alcance(raiz)
    objetivo = [args.par] if args.par else alcance.get("cubiertos", [])
    resultados: list[ResultadoCaso] = []
    # AC-8: aislamiento comprobado, no supuesto. Se toma la huella del árbol de fixtures y el
    # estado de git ANTES, y se contrastan al final: una corrida que tocara el fixture fuente o
    # el árbol del repositorio quedaría en evidencia acá y no en la lectura del código.
    dir_fixtures = raiz / DIR_CASOS
    huella_previa = _huella_arbol(dir_fixtures) if dir_fixtures.exists() else ""
    git_previo = _git_status(raiz)

    interprete_ps = None
    espia_tmp = None
    if args.interprete_espia:
        espia_tmp = Path(tempfile.mkdtemp(prefix="paridad-espia-"))
        interprete_ps = str(crear_espia(espia_tmp))

    for nombre in objetivo:
        par = pares.get(nombre)
        if par is None:
            print(f"{nombre}: no existe en el inventario")
            return CODIGO["fallo"]
        matriz = cargar_casos(raiz, nombre)
        if matriz is None:
            print(f"{nombre}: sin casos.json")
            return CODIGO["fallo"]
        catalogo = cargar_catalogo(raiz, nombre)
        for caso in matriz.get("casos", []):
            if args.caso and caso["nombre"] != args.caso:
                continue
            ordenes = [("posix", "ps")]
            if args.ambos_ordenes:
                ordenes.append(("ps", "posix"))
            vistos = []
            for orden in ordenes:
                r = correr_caso(raiz, par, matriz, caso, catalogo, orden=orden,
                                corromper=args.corromper_patron, interprete_ps=interprete_ps)
                vistos.append(r)
            r = vistos[0]
            if len(vistos) == 2 and vistos[0].resultado != vistos[1].resultado:
                r = ResultadoCaso(nombre, caso["nombre"], "fallo",
                                  detalle=f"el orden de ejecución cambia el veredicto:"
                                          f" {vistos[0].resultado} vs {vistos[1].resultado}")
            resultados.append(r)
            linea = f"{nombre:<28} {caso['nombre']:<22} {r.resultado:<22}"
            if r.dimension:
                linea += f" dimensión={r.dimension}"
            print(linea + (f"  [{r.detalle}]" if r.detalle else ""))
            if args.explicar:
                print(f"      eventos posix: {[(e.id, dict(e.campos)) for e in r.eventos_px]}")
                print(f"      eventos ps   : {[(e.id, dict(e.campos)) for e in r.eventos_ps]}")
                _explicar_observaciones(r)
            if args.fallar_rapido and r.resultado in ("fallo", "no_comprobable"):
                print(f"  aborta por --fallar-rapido: {r.detalle}")
                if espia_tmp:
                    shutil.rmtree(espia_tmp, ignore_errors=True)
                return codigo_global([x.resultado for x in resultados])

    if espia_tmp:
        log = espia_tmp / "espia.log"
        if log.exists():
            print("\nregistro del intérprete espía (argv y entorno REALES del hijo):")
            texto = log.read_text(encoding=ENCODING, errors="replace")
            argv, _, entorno = texto.partition("ENV:")
            print(argv.rstrip())
            claves = ("LC_ALL", "LANG", "LC_COLLATE", "TZ")
            print("ENV (locale/encoding declarados):")
            for l in entorno.split("\n"):
                if any(l.startswith(k + "=") for k in claves):
                    print(f"  {l}")
        shutil.rmtree(espia_tmp, ignore_errors=True)

    if not resultados:
        print("ningún caso ejecutado")
        return CODIGO["fallo"]

    estados = [r.resultado for r in resultados]
    huella_post = _huella_arbol(dir_fixtures) if dir_fixtures.exists() else ""
    if huella_post != huella_previa:
        print(f"  AISLAMIENTO ROTO: el árbol de fixtures cambió durante la corrida"
              f" ({huella_previa} → {huella_post})")
        estados.append("fallo")
    elif args.ambos_ordenes:
        print(f"  aislamiento: fixture fuente byte-idéntico (huella {huella_post})")
    if _git_status(raiz) != git_previo:
        print("  AISLAMIENTO ROTO: `git status --porcelain` cambió durante la corrida")
        estados.append("fallo")
    elif args.ambos_ordenes:
        print("  aislamiento: `git status --porcelain` idéntico antes y después")
    return codigo_global(estados)


def _explicar_observaciones(r: ResultadoCaso) -> None:
    """Muestra la evidencia de las dimensiones de stdout y artefactos, lado a lado."""
    if r.obs_px is None or r.obs_ps is None:
        return
    a, b = normalizar_stdout(r.obs_px.stdout), normalizar_stdout(r.obs_ps.stdout)
    if a != b:
        print("      stdout posix:")
        for l in a.rstrip("\n").split("\n"):
            print(f"        {l}")
        print("      stdout ps   :")
        for l in b.rstrip("\n").split("\n"):
            print(f"        {l}")
    ax, bx = normalizar_artefactos(r.obs_px.artefactos), normalizar_artefactos(r.obs_ps.artefactos)
    if ax != bx:
        for ruta in sorted(set(ax) | set(bx)):
            if ax.get(ruta) == bx.get(ruta):
                continue
            if ruta not in bx:
                print(f"      artefacto solo en posix: {ruta}")
            elif ruta not in ax:
                print(f"      artefacto solo en ps   : {ruta}")
            else:
                print(f"      artefacto distinto: {ruta}")
                print(f"        posix: {ax[ruta]!r}")
                print(f"        ps   : {bx[ruta]!r}")


def cmd_reporte(raiz: Path, pares: dict[str, Par], args) -> int:
    alcance = cargar_alcance(raiz)
    cubiertos = alcance.get("cubiertos", [])
    declarados = alcance.get("declarados_sin_matriz", {})
    try:
        ruta, version = detectar_pwsh()
        print(f"intérprete: {ruta} (v{version})\n")
    except SinInterprete as exc:
        print(f"intérprete: AUSENTE — {exc}")
        print("resultado global: paridad no comprobable")
        imprimir_exclusiones()
        return CODIGO["no_comprobable"]

    por_par: dict[str, list[ResultadoCaso]] = {}
    for nombre in cubiertos:
        par = pares[nombre]
        matriz = cargar_casos(raiz, nombre) or {}
        catalogo = cargar_catalogo(raiz, nombre)
        for caso in matriz.get("casos", []):
            r = correr_caso(raiz, par, matriz, caso, catalogo)
            por_par.setdefault(nombre, []).append(r)

    print(f"{'par':<30} {'resultado':<22} evidencia")
    print("-" * 96)
    todos: list[str] = []
    for nombre in sorted(pares):
        if nombre in declarados:
            print(f"{nombre:<30} {'sin matriz (no comprobado)':<22}"
                  f" {declarados[nombre][:40]}")
            continue
        rs = por_par.get(nombre, [])
        if not rs:
            print(f"{nombre:<30} {'sin casos':<22}")
            todos.append("fallo")
            continue
        peor = max((r.resultado for r in rs), key=lambda x: PRECEDENCIA.index(x))
        todos += [r.resultado for r in rs]
        hallazgos = sorted({f"{r.resultado}"
                            + (f"/{r.dimension}" if r.dimension else "") for r in rs})
        print(f"{nombre:<30} {peor:<22} {len(rs)} casos · {', '.join(hallazgos)}")

    codigo = codigo_global(todos) if todos else CODIGO["fallo"]
    print("-" * 96)
    print(f"resultado global: {PRECEDENCIA[[CODIGO[k] for k in PRECEDENCIA].index(codigo)]}"
          f" (código {codigo})")
    imprimir_exclusiones()
    return codigo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raiz", default=str(RAIZ_ARNES),
                   help="raíz del repositorio a auditar (por defecto, la de este script)")
    p.add_argument("--listar-inventario", action="store_true")
    p.add_argument("--auditar-catalogo", action="store_true")
    p.add_argument("--auditar-matrices", action="store_true")
    p.add_argument("--resincronizar-catalogo", action="store_true",
                   help="reubica las entradas cuyo sitio se movió sin cambiar de texto")
    p.add_argument("--registrar-auditoria", action="store_true",
                   help="liga la cobertura al cuerpo vigente (el acto que AC-5 exige tras un"
                        " cambio de cuerpo)")
    p.add_argument("--estricto-mono-causa", action="store_true")
    p.add_argument("--exigir-particiones", action="store_true")
    p.add_argument("--autotest-extractor", action="store_true")
    p.add_argument("--autotest-escaner", action="store_true")
    p.add_argument("--autotest-normalizacion", action="store_true")
    p.add_argument("--autotest-clasificador", action="store_true")
    p.add_argument("--afirmar-particiones", action="store_true")
    p.add_argument("--autotest-comparador", action="store_true")
    p.add_argument("--dimension", choices=list(DIMENSIONES))
    p.add_argument("--autotest-precedencia", action="store_true")
    p.add_argument("--autotest-catalogo", action="store_true")
    p.add_argument("--testigos-centinela", action="store_true")
    p.add_argument("--reporte", action="store_true")
    p.add_argument("--entorno", action="store_true")
    p.add_argument("--par")
    p.add_argument("--caso")
    p.add_argument("--explicar", action="store_true")
    p.add_argument("--ambos-ordenes", action="store_true")
    p.add_argument("--fallar-rapido", action="store_true")
    p.add_argument("--interprete-espia", action="store_true")
    p.add_argument("--corromper-patron")
    args = p.parse_args(argv)

    raiz = Path(args.raiz).resolve()

    # autotests que no necesitan inventario
    if args.autotest_extractor:
        return autotest_extractor()
    if args.autotest_escaner:
        return autotest_escaner()
    if args.autotest_normalizacion:
        return autotest_normalizacion()
    if args.autotest_clasificador:
        return autotest_clasificador()
    if args.autotest_comparador:
        return autotest_comparador(args.dimension)
    if args.autotest_precedencia:
        return autotest_precedencia()
    if args.entorno:
        return cmd_entorno(raiz)

    if args.par in PARES_SINTETICOS:
        return cmd_correr(raiz, {}, args)

    try:
        pares, huerfanas, _ = descubrir_pares(raiz)
    except BloqueInvalido as exc:
        print(f"inventario en rojo: {exc}")
        return CODIGO["fallo"]

    if args.listar_inventario:
        return cmd_listar_inventario(raiz)
    if huerfanas:
        print(f"inventario en rojo: variantes sin par POSIX → {', '.join(huerfanas)}")
        return CODIGO["fallo"]
    if args.auditar_catalogo:
        return cmd_auditar_catalogo(raiz, pares)
    if args.resincronizar_catalogo:
        return cmd_resincronizar_catalogo(raiz, pares, args.par)
    if args.registrar_auditoria:
        return cmd_registrar_auditoria(raiz, pares, args.par)
    if args.auditar_matrices:
        return cmd_auditar_matrices(raiz, pares, args)
    if args.autotest_catalogo:
        return autotest_catalogo(raiz, pares)
    if args.reporte:
        return cmd_reporte(raiz, pares, args)
    if args.par or args.caso:
        return cmd_correr(raiz, pares, args)
    return cmd_reporte(raiz, pares, args)


if __name__ == "__main__":
    sys.exit(main())
