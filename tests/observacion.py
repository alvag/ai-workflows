"""Oracle durable para ejecutar y comparar observaciones de guardas."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


ENCODING = "utf-8"
LOCALE = {"LC_ALL": "C.UTF-8", "LANG": "C.UTF-8", "LC_COLLATE": "C.UTF-8", "TZ": "UTC"}
CANDIDATOS_PWSH_DEFECTO = ("pwsh", "pwsh-preview", "powershell")
TIMEOUT_DEFECTO = 30
DIMENSIONES = ("clase", "eventos", "stdout", "artefactos", "codigo")

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


@dataclass(frozen=True)
class Evento:
    id: str
    campos: tuple[tuple[str, str], ...]


@dataclass
class Veredicto:
    iguales: bool
    dimensiones_divergentes: list[str] = field(default_factory=list)

    @property
    def dimension_divergente(self) -> str | None:
        for dimension in DIMENSIONES:
            if dimension in self.dimensiones_divergentes:
                return dimension
        return None


class SinInterprete(Exception):
    pass


def _candidatos_pwsh() -> list[str]:
    crudo = os.environ.get("PARIDAD_PWSH_CANDIDATOS")
    if crudo:
        return [candidato.strip() for candidato in crudo.split(",") if candidato.strip()]
    return list(CANDIDATOS_PWSH_DEFECTO)


def detectar_pwsh() -> tuple[str, str]:
    """Devuelve la ruta y versión del primer candidato de PowerShell disponible."""
    for candidato in _candidatos_pwsh():
        ruta = shutil.which(candidato)
        if not ruta:
            continue
        try:
            resultado = subprocess.run(
                [ruta, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
                 "$PSVersionTable.PSVersion.ToString()"],
                capture_output=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        version = resultado.stdout.decode(ENCODING, "replace").strip() or "?"
        return ruta, version
    raise SinInterprete(
        "ningún candidato de PowerShell disponible: " + ", ".join(_candidatos_pwsh()))


def _prologo_posix(entradas: dict[str, str]) -> str:
    lineas = []
    for clave, valor in entradas.items():
        lineas.append(f"{clave}={shlex.quote(str(valor))}")
        lineas.append(f"export {clave}")
    return "\n".join(lineas) + ("\n" if lineas else "")


def _prologo_ps(entradas: dict[str, str]) -> str:
    lineas = [PRELUDIO_PS.rstrip("\n")]
    for clave, valor in entradas.items():
        literal = str(valor).replace("'", "''")
        lineas.append(f"${clave} = '{literal}'")
        lineas.append(f"$env:{clave} = '{literal}'")
    return "\n".join(lineas) + "\n"


def _recolectar_artefactos(base: Path) -> dict[str, bytes]:
    salida: dict[str, bytes] = {}
    for ruta in sorted(base.rglob("*")):
        if ruta.is_file():
            # Los artefactos son observables binarios: su contenido puede no ser texto UTF-8.
            salida[str(ruta.relative_to(base))] = ruta.read_bytes()
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
    resueltas = {clave: str(valor).replace("{dir}", str(caso_dir))
                 for clave, valor in entradas.items()}

    entorno = dict(os.environ)
    entorno.update(LOCALE)
    entorno.pop("PARIDAD_PWSH_CANDIDATOS", None)
    entorno.update(resueltas)

    if sabor == "posix":
        script = tmp / "cuerpo.sh"
        script.write_text(_prologo_posix(resueltas) + cuerpo + "\n", encoding=ENCODING)
        usado = interprete or "/bin/sh"
        comando = [usado, str(script)]
    else:
        usado = interprete or detectar_pwsh()[0]
        script = tmp / "cuerpo.ps1"
        script.write_text(_prologo_ps(resueltas) + cuerpo + "\n", encoding=ENCODING)
        comando = [usado, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(script)]

    expiro = False
    try:
        proceso = subprocess.run(
            comando,
            cwd=str(caso_dir),
            env=entorno,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        codigo, stdout, stderr = proceso.returncode, proceso.stdout, proceso.stderr
    except subprocess.TimeoutExpired as exc:
        expiro = True
        codigo, stdout, stderr = -1, exc.stdout or b"", exc.stderr or b""

    # Cada sabor corre en SU copia, así que la ruta temporal difiere entre los dos por
    # construcción del arnés. Se sustituye por un testigo estable para que esa diferencia —del
    # arnés, no del predicado— no se lea como divergencia. Es la única sustitución de rutas y no
    # puede borrar una diferencia semántica: los dos lados reciben el mismo token.
    # De la más específica a la más general: sustituir primero la raíz temporal dejaría el sufijo
    # `/caso` colgando, y como el conjunto no tiene orden la salida no sería reproducible entre
    # sabores — que es justo lo que esta sustitución existe para evitar.
    variantes = sorted(
        {str(caso_dir), str(caso_dir.resolve()), str(tmp), str(tmp.resolve())},
        key=len,
        reverse=True,
    )

    def neutralizar(contenido: bytes) -> bytes:
        for variante in variantes:
            contenido = contenido.replace(variante.encode(ENCODING), b"{dir}")
        return contenido

    observacion = Observacion(
        exit=codigo,
        stdout=neutralizar(stdout),
        stderr=neutralizar(stderr),
        artefactos={ruta: neutralizar(contenido)
                    for ruta, contenido in _recolectar_artefactos(caso_dir).items()},
        timeout=expiro,
        interprete=usado,
    )
    shutil.rmtree(tmp, ignore_errors=True)
    return observacion


def normalizar_stdout(contenido: bytes) -> str:
    """Fin de línea, BOM inicial y espacio/tab al final de línea.

    NO ordena líneas, NO colapsa whitespace interno, NO toca el casing.
    """
    texto = contenido.decode(ENCODING, "surrogateescape").replace("\r\n", "\n")
    if texto.startswith("\ufeff"):
        texto = texto[1:]
    return "\n".join(linea.rstrip(" \t") for linea in texto.split("\n"))


def normalizar_artefactos(artefactos: dict[str, bytes]) -> dict[str, str]:
    """Rutas relativas, nombres byte a byte, contenido con la misma normalización de fin de línea."""
    return {ruta: normalizar_stdout(contenido)
            for ruta, contenido in sorted(artefactos.items())}


def comparar(clase_px: str, ev_px: list[Evento], obs_px: Observacion,
             clase_ps: str, ev_ps: list[Evento], obs_ps: Observacion) -> Veredicto:
    """Compara cinco dimensiones; cada una puede gobernar el veredicto por sí sola."""
    difieren: list[str] = []
    if clase_px != clase_ps:
        difieren.append("clase")
    if sorted(map(repr, ev_px)) != sorted(map(repr, ev_ps)):
        difieren.append("eventos")
    if normalizar_stdout(obs_px.stdout) != normalizar_stdout(obs_ps.stdout):
        difieren.append("stdout")
    if normalizar_artefactos(obs_px.artefactos) != normalizar_artefactos(obs_ps.artefactos):
        difieren.append("artefactos")
    if obs_px.exit != obs_ps.exit:
        difieren.append("codigo")
    return Veredicto(iguales=not difieren, dimensiones_divergentes=difieren)
