#!/usr/bin/env python3
"""Runner de la cohorte de la fase 0: provisiona, preflightea, ejecuta y captura.

Un modo que **valida** evidencia no es el que la **produce**. El instrumento juzga bundles,
observaciones y baseline; este archivo crea el árbol desechable donde corre cada caso, prueba antes
de correr que su receta es lanzable, la ejecuta y captura lo que pasó. Los dos lados se separan a
propósito: quien produce la evidencia no puede ser quien la declara válida.

Siete modos:

- `--provisionar` — crea el repositorio desechable a partir del árbol medido, retira los remotos,
  las credenciales alcanzables y la red del worker, y deja de **cada retiro una constancia
  comprobable**: el comando que la produce y la salida observada después de aplicarlo. El acta que
  escribe no dice que el árbol quedó aislado: dice qué se retiró y qué se observó. Juzgarlo es otra
  capacidad, y su punto de enganche es `JUECES_DE_AISLAMIENTO`.
- `--preflight` — por cada receta seleccionada prueba que su adaptador está disponible y que su
  lanzamiento es controlable, y **adjudica el caso `runnable` o `blocked` con causa del conjunto
  cerrado**. Un bloqueo es un resultado válido y no un fallo del modo: el modo falla si falta una
  adjudicación, no si alguna adjudica bloqueo. Para el paso de `cli-resume` prueba el `resume` con
  una **sesión desechable**, con sus tres negativos.
- `--ejecutar-caso` — corre un caso por su receta, sella cada evento **por la interfaz de reloj** y
  emite el bundle con la secuencia de apertura en orden. Los dos adaptadores cargan las mismas
  obligaciones; el de sesión **no se autoatestigua**: su bundle se construye desde el recibo de
  frontera, nunca desde lo que la sesión declare.
- `--autotest-provisionamiento`, `--autotest-preflight`, `--autotest-adaptadores` y
  `--autotest-journal` — los controles de los tres modos anteriores y del journal de anomalías,
  cada uno con sus negativos.

## El journal de anomalías lo escribe este archivo

Si el runner falla **antes** de construir el bundle, la anomalía no puede vivir en la sede que se le
había asignado: el manifest detecta el bundle ausente, pero al corregir y repetir ese defecto
desaparece sin haber entrado nunca al ledger. Por eso hay un journal propio, append-only, con una
apertura **antes** de cada operación que pueda impedir el bundle y **exactamente un** resultado
terminal después. Su completitud se deriva del manifest independiente de intentos, nunca de las
entradas que el journal resulte tener.

## Lo que este archivo captura y no juzga

Las tres pruebas de aislamiento salen de acá **con su evidencia comparada** —snapshots antes y
después, y las constancias del provisionamiento—, y el acta de provisionamiento nunca se declara
aislada sola: mientras `JUECES_DE_AISLAMIENTO` esté vacío su veredicto es `sin_juez_registrado`.
Provisionar la evidencia y juzgarla son dos capacidades, y esa es la línea que separa a este
archivo del modo que la juzga.

## Cómo se agrega un modo

Igual que en el instrumento, y por el mismo motivo: el despacho es una tabla.

1. Escribí `modo_<nombre>(args) -> int` en una sección propia.
2. Registrala con `registrar_modo(...)`.
3. No toques `main()`: construye el parser y el despacho desde `MODOS`.

Códigos de salida, iguales en todos los modos: **0** sano, **1** hallazgos, **2** invocación
inválida.

## Por qué acá no hay validador de schemas

El instrumento tiene uno; este archivo **no lo porta**. Un runner que valida con su propia copia el
bundle que él mismo acaba de escribir es un conjunto validado contra sí mismo, que es justo lo que
el diseño de esta fase prohíbe. El juez del bundle es el instrumento, invocado como **proceso
aparte** —`instrumento-baseline.py --validar-bundles`—, así que una mutación del runner no puede
tocar a la vez lo que produce y lo que decide si vale.

Del instrumento sí se porta el andamiaje del CLI —`Argumento`, `Auxiliar`, `Modo`,
`registrar_modo`, `main`—, que es plomería sin decisiones: no tiene comportamiento que pueda
divergir en silencio, y compartirlo por import ataría dos archivos que las tasks siguientes editan
por separado.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple

RAIZ = Path(__file__).resolve().parent.parent
DIR_SCRIPTS = RAIZ / "scripts"
RUTA_RECETAS = DIR_SCRIPTS / "recetas-cohorte.json"
RUTA_INTERFAZ_DE_RELOJ = DIR_SCRIPTS / "interfaz-de-reloj.json"
RUTA_MATRIZ_DESPACHOS = DIR_SCRIPTS / "matriz-despachos.json"
RUTA_SUPERFICIES_DE_EGRESO = DIR_SCRIPTS / "superficies-de-egreso.json"
RUTA_INSTRUMENTO = DIR_SCRIPTS / "instrumento-baseline.py"
RUTA_PREREGISTRO_FASE_0 = DIR_SCRIPTS / "preregistro-fase-0.json"
DIR_RECIBOS_FASE_0 = DIR_SCRIPTS / "recibos-frontera-fase-0"
DIR_JOURNAL_FASE_0 = DIR_SCRIPTS / "journal-anomalias-fase-0"
DIR_FIXTURES_RUNNER = DIR_SCRIPTS / "fixtures-baseline" / "runner"
RUTA_MANIFEST_RUNNER = DIR_FIXTURES_RUNNER / "manifest.json"

NOMBRE_DEL_ACTA = "provisionamiento.json"
VERSION_DEL_ACTA = "1.0.0"


# ---------------------------------------------------------------------------------------------
# El andamiaje del CLI, portado del instrumento sin cambios de comportamiento.
# ---------------------------------------------------------------------------------------------

class Argumento(NamedTuple):
    """El insumo posicional de un modo: `--provisionar <dir>` lo lleva, `--preflight` no."""
    metavar: str
    const: str | None = None


class Auxiliar(NamedTuple):
    """Una bandera que modifica a un modo (`--receta`, `--acta`…), nunca lo selecciona."""
    bandera: str
    ayuda: str
    metavar: str | None = None
    por_defecto: str | None = None


class Modo(NamedTuple):
    bandera: str
    ayuda: str
    handler: Callable[[argparse.Namespace], int]
    argumento: Argumento | None = None
    auxiliares: tuple[Auxiliar, ...] = ()

    @property
    def destino(self) -> str:
        return self.bandera[2:].replace("-", "_")


MODOS: list[Modo] = []


def registrar_modo(bandera: str, ayuda: str, handler: Callable[[argparse.Namespace], int],
                   argumento: Argumento | None = None,
                   auxiliares: tuple[Auxiliar, ...] = ()) -> None:
    """Da de alta un modo. Es el único punto de contacto con el CLI: nadie edita `main()`."""
    if any(m.bandera == bandera for m in MODOS):
        raise ValueError(f"el modo {bandera} ya está registrado")
    MODOS.append(Modo(bandera, ayuda, handler, argumento, auxiliares))


def _cargar_json(ruta: Path) -> tuple[Any, str]:
    try:
        return json.loads(ruta.read_text(encoding="utf-8")), ""
    except FileNotFoundError:
        return None, f"no existe {_relativa(ruta)}"
    except json.JSONDecodeError as exc:
        return None, f"{_relativa(ruta)} no es JSON válido: {exc}"


def _relativa(ruta: Path) -> str:
    try:
        return str(ruta.resolve().relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def _ruta_absoluta(valor: str) -> Path:
    ruta = Path(valor)
    return ruta if ruta.is_absolute() else RAIZ / ruta


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _escribir_json(ruta: Path, datos: Any) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _correr(comando: list[str], *, cwd: Path | None = None,
            entorno: dict[str, str] | None = None) -> tuple[int, str]:
    """Ejecuta y devuelve `(código, salida combinada y recortada)`.

    La salida se devuelve entera y sin interpretar: la constancia de un retiro es lo que se
    observó, no el resumen de quien lo aplicó.
    """
    try:
        proc = subprocess.run(comando, cwd=str(cwd) if cwd else None, env=entorno,
                              capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return 127, f"no se encontró el ejecutable {comando[0]}"
    except subprocess.TimeoutExpired:
        return 124, "el comando no terminó dentro del tope"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


# ---------------------------------------------------------------------------------------------
# La interfaz de reloj: todo sello del runner sale de acá.
#
# El bundle exige que cada sello declare su procedencia como texto libre; la interfaz cierra el
# conjunto. Leerla en vez de escribir la constante acá es lo que hace que agregar una procedencia
# nueva no requiera tocar este archivo, y que citar una que no existe se caiga en el acto.
# ---------------------------------------------------------------------------------------------

class Reloj:
    """Emisor de sellos monotónicos bajo autoridad del harness."""

    def __init__(self, procedencia: str, precision_ns: int) -> None:
        self.procedencia = procedencia
        self.precision_ns = precision_ns
        self._base = time.monotonic_ns()

    def sello(self) -> dict[str, Any]:
        return {
            "valor_ns": time.monotonic_ns() - self._base,
            "fuente": "reloj_monotonico_del_harness",
            "autoridad": "harness",
            "precision_ns": self.precision_ns,
            "procedencia": self.procedencia,
        }


def cargar_reloj(adaptador: str) -> tuple[Reloj | None, str]:
    """Construye el reloj del adaptador desde la interfaz declarada, o dice por qué no puede."""
    interfaz, error = _cargar_json(RUTA_INTERFAZ_DE_RELOJ)
    if error:
        return None, error
    admitidas = [p for p in interfaz.get("procedencias_admitidas") or []
                 if adaptador in (p.get("adaptadores") or [])]
    if not admitidas:
        return None, f"la interfaz de reloj no admite ninguna procedencia para `{adaptador}`"
    if len(admitidas) > 1:
        ids = ", ".join(p["procedencia_id"] for p in admitidas)
        return None, (f"la interfaz admite {len(admitidas)} procedencias para `{adaptador}` "
                      f"({ids}) y el runner no elige: el pre-registro tiene que fijar cuál")
    precision = (interfaz.get("precision_ns") or {}).get("minimo")
    if not isinstance(precision, int):
        return None, "la interfaz de reloj no declara una precisión mínima entera"
    return Reloj(admitidas[0]["procedencia_id"], precision), ""


# ---------------------------------------------------------------------------------------------
# Modo `--provisionar`.
#
# Tres retiros, cada uno con su constancia. La constancia NO es el comando que aplica el retiro:
# es el que lo comprueba DESPUÉS, con su salida observada. Un retiro que solo registra «ejecuté
# `git remote remove origin`» acredita una intención; lo que hay que acreditar es que después no
# quedó ningún remoto.
#
# El retiro de red es el único que el runner no aplica: la red del worker la quita el sandbox de su
# propio comando. Por eso su constancia es el flag de sandbox presente en el comando literal que se
# va a ejecutar —capturado del comando, no asumido— y un comando sin sandbox deja el retiro sin
# comprobar, que es lo que después bloquea el caso.
# ---------------------------------------------------------------------------------------------

CLAVES_DE_RETIRO = ("remotos", "credenciales", "red")

# Los archivos de credenciales que el retiro tiene que volver inalcanzables. Se enumeran para poder
# comprobar la ausencia: preguntar «¿hay credenciales?» sobre un conjunto que se descubre al correr
# haría que un archivo nuevo pasara sin que nada lo notara.
ARCHIVOS_DE_CREDENCIAL = (
    ".netrc",
    ".git-credentials",
    ".config/gh/hosts.yml",
    ".codex/auth.json",
    ".ssh/id_rsa",
    ".ssh/id_ed25519",
)


class Constancia(NamedTuple):
    """Lo que se observó DESPUÉS de aplicar un retiro."""
    comando: str
    salida_observada: str
    comprobado: bool
    detalle: str

    def como_json(self) -> dict[str, Any]:
        return {
            "comando": self.comando,
            "salida_observada": self.salida_observada,
            "comprobado": self.comprobado,
            "detalle": self.detalle,
        }


class JuezDeAislamiento(NamedTuple):
    """Punto de enganche del validador de aislamiento.

    El runner **provisiona** la evidencia; juzgarla es otra capacidad y vive en el instrumento.
    Mientras esta lista esté vacía, el acta declara `sin_juez_registrado` y **nunca** que el árbol
    quedó aislado: un acta que se declarara aislada sola sería la evidencia declarativa que el
    criterio prohíbe.
    """
    clave: str
    que_juzga: str
    juzgar: Callable[[dict[str, Any]], list[str]]


JUECES_DE_AISLAMIENTO: list[JuezDeAislamiento] = []


def registrar_juez_de_aislamiento(clave: str, que_juzga: str,
                                  juzgar: Callable[[dict[str, Any]], list[str]]) -> None:
    if any(j.clave == clave for j in JUECES_DE_AISLAMIENTO):
        raise ValueError(f"el juez de aislamiento {clave} ya está registrado")
    JUECES_DE_AISLAMIENTO.append(JuezDeAislamiento(clave, que_juzga, juzgar))


def variables_de_credencial(entorno: dict[str, str]) -> list[str]:
    """Los nombres del entorno que la regla de egreso marcaría como credencial.

    Se derivan de `scripts/superficies-de-egreso.json` y no de una lista escrita acá. Con dos
    listas paralelas, el entorno cree haber quitado credenciales que la regla sigue descubriendo
    —medido sobre este host: tres tokens reales sobrevivían al entorno «desechable»—, y el worker
    recibiría justo lo que se quería retirar.
    """
    inventario, error = _cargar_json(RUTA_SUPERFICIES_DE_EGRESO)
    if error:
        return [n for n in sorted(entorno) if "TOKEN" in n or "SECRET" in n or "API_KEY" in n]
    definidas = next(c for c in inventario["clases"] if c["clase"] == "variable_de_entorno")
    patrones = definidas["patrones_de_nombre"]
    return [n for n in sorted(entorno)
            if n in definidas["variables_de_token"] or any(p in n for p in patrones)]


def entorno_sin_credenciales(hogar: Path) -> dict[str, str]:
    """El entorno con el que corre todo comando del árbol desechable.

    No se toca el HOME real: se apunta el del proceso hijo a un directorio desechable y se cortan
    las vías por las que git vuelve al del usuario —el config global, el del sistema y el que la
    instalación deja junto al binario—. Lo que se retira es el **alcance**, no los archivos.
    """
    entorno = dict(os.environ)
    entorno["HOME"] = str(hogar)
    entorno["GIT_CONFIG_GLOBAL"] = os.devnull
    entorno["GIT_CONFIG_SYSTEM"] = os.devnull
    # Apuntar `GIT_CONFIG_SYSTEM` a /dev/null NO apaga el gitconfig que la instalación deja junto
    # al binario. Medido sobre este host con git 2.50.1 (Apple Git-155): el `credential.helper
    # osxkeychain` de `/Applications/Xcode.app/…/git-core/gitconfig` se sigue leyendo, y solo
    # `GIT_CONFIG_NOSYSTEM` lo apaga. Sin esta línea el retiro de credenciales se declara hecho y
    # el worker conserva un helper que consulta el llavero.
    entorno["GIT_CONFIG_NOSYSTEM"] = "1"
    entorno["GIT_TERMINAL_PROMPT"] = "0"
    entorno["GIT_ASKPASS"] = ""
    entorno.pop("SSH_AUTH_SOCK", None)
    for variable in variables_de_credencial(entorno):
        entorno.pop(variable, None)
    return entorno


def constatar_remotos(arbol: Path, entorno: dict[str, str]) -> Constancia:
    comando = f"git -C {_relativa(arbol)} remote"
    codigo, salida = _correr(["git", "-C", str(arbol), "remote"], entorno=entorno)
    if codigo != 0:
        return Constancia(comando, salida, False, "el comando de comprobación no pudo correr")
    if salida:
        return Constancia(comando, salida, False,
                          f"quedaron remotos configurados: {salida.splitlines()}")
    return Constancia(comando, salida, True, "no quedó ningún remoto configurado")


def constatar_credenciales(hogar: Path, entorno: dict[str, str]) -> Constancia:
    comando = (f"comprobar que {len(ARCHIVOS_DE_CREDENCIAL)} archivos de credencial no son "
               f"alcanzables desde HOME={_relativa(hogar)}")
    alcanzables = [nombre for nombre in ARCHIVOS_DE_CREDENCIAL
                   if (Path(entorno["HOME"]) / nombre).exists()]
    variables = (["SSH_AUTH_SOCK"] if "SSH_AUTH_SOCK" in entorno else []) \
        + variables_de_credencial(entorno)
    salida = json.dumps({"archivos_alcanzables": alcanzables, "variables_presentes": variables},
                        ensure_ascii=False)
    if alcanzables or variables:
        return Constancia(comando, salida, False,
                          "el entorno del hijo todavía alcanza credenciales")
    return Constancia(comando, salida, True,
                      "ningún archivo de credencial ni variable de token es alcanzable")


# Los dos modos de sandbox del ecosistema. Un comando que pidiera otro no está pidiendo ninguno de
# los que se midieron corriendo sin red, así que su retiro no queda comprobado.
MODOS_DE_SANDBOX = ("read-only", "workspace-write")

# Las dos formas en que un comando pide sandbox. Son dos y no una porque la invocación de `resume`
# no acepta `-s`: lo pide por configuración. Enumerarlas es lo que impide que la forma que no se
# reconoce se lea como «este comando no pide sandbox» —que fue el primer resultado de este modo, y
# era falso—.
FORMAS_DE_PEDIR_SANDBOX = (
    ("-s", "-s {modo}"),
    ("-c sandbox_mode=", '-c sandbox_mode="{modo}"'),
)


def sandbox_pedido(comando: str) -> str | None:
    """El modo de sandbox que pide un comando literal, o `None` si no pide ninguno conocido."""
    for modo in MODOS_DE_SANDBOX:
        for _, plantilla in FORMAS_DE_PEDIR_SANDBOX:
            if plantilla.format(modo=modo) in comando:
                return modo
    return None


def constatar_red(comandos_a_ejecutar: tuple[str, ...]) -> Constancia:
    """La red del worker la retira el sandbox de su propio comando, y eso se **captura**.

    El sandbox se lee del comando literal que se va a ejecutar. Un comando que no lo pide deja el
    retiro sin comprobar: no se asume que el entorno lo imponga por su cuenta.
    """
    comando = "leer el sandbox pedido por cada comando literal que se va a ejecutar"
    sin_sandbox = [c for c in comandos_a_ejecutar if sandbox_pedido(c) is None]
    salida = json.dumps({"comandos": len(comandos_a_ejecutar),
                         "sin_sandbox_pedido": sin_sandbox}, ensure_ascii=False)
    if not comandos_a_ejecutar:
        return Constancia(comando, salida, False,
                          "no hay ningún comando del que capturar el sandbox: nada que constatar")
    if sin_sandbox:
        return Constancia(comando, salida, False,
                          f"{len(sin_sandbox)} comandos no piden sandbox: el retiro de red no es "
                          f"comprobable y esos casos se bloquean")
    return Constancia(comando, salida, True,
                      "todos los comandos piden sandbox, que es lo que retira la red del worker")


def exige_confirmacion_del_usuario(punto: str) -> bool:
    """Si la matriz declara que este punto de despacho no corre sin confirmación humana."""
    matriz, error = _cargar_json(RUTA_MATRIZ_DESPACHOS)
    if error:
        raise AnomaliaDelRunner("fallo_previo_al_bundle", f"no se pudo leer la matriz: {error}")
    for entrada in matriz.get("puntos") or []:
        ident = entrada.get("id")
        ident = ident["valor"] if isinstance(ident, dict) and "valor" in ident else ident
        if ident == punto:
            campo = entrada.get("requiere_confirmacion_del_usuario") or {}
            valor = campo.get("valor") if isinstance(campo, dict) else campo
            return valor is True
    return False


def constatar_retiros_del_caso(receta: dict[str, Any], recibo: dict[str, Any] | None) -> bool:
    """Si el retiro de red quedó comprobado para ESTE caso, por la vía de su adaptador.

    Los dos adaptadores cargan la misma obligación y difieren en de dónde sale lo que pasó
    (ver `ADAPTADORES`). Un `script` la comprueba leyendo el sandbox que pide su comando congelado.
    Una `sesion_de_agente` no tiene comando del que leerlo, y su constancia es el recibo de
    frontera —emitido bajo autoridad del harness ANTES de la tool call—, cuyos permisos declaran
    bajo qué régimen se despachó; la sesión no se autoatestigua. Sin recibo no hay constancia, que
    es el mismo criterio con el que `constatar_red` trata un conjunto de comandos vacío: no se
    asume que el entorno imponga el retiro por su cuenta.
    """
    if receta.get("adaptador") == "script":
        return constatar_red((receta["comando"],)).comprobado
    if recibo is None:
        return False
    apertura = next((e for e in recibo["recibo"]["eventos"]
                     if e["evento"] == "dispatch_started"), None)
    return bool(apertura and apertura.get("permisos"))


def _comandos_de_las_recetas() -> tuple[str, ...]:
    recetas, error = _cargar_json(RUTA_RECETAS)
    if error:
        return ()
    return tuple(r["comando"] for r in recetas.get("recetas") or [] if "comando" in r)


def provisionar(destino: Path,
                comandos: tuple[str, ...] | None = None) -> tuple[dict[str, Any] | None, list[str]]:
    """Crea el árbol desechable y devuelve su acta, o los problemas que lo impidieron.

    Los comandos son un insumo del provisionamiento —son las recetas seleccionadas de la cohorte— y
    por eso entran por parámetro: el retiro de red se constata sobre ellos, y una cohorte que
    selecciona otro conjunto tiene otro retiro que constatar.
    """
    problemas: list[str] = []
    if destino.exists():
        return None, [f"el destino {_relativa(destino)} ya existe: un árbol reutilizado arrastra "
                      f"el estado de la corrida anterior y su identidad de limpieza deja de valer"]

    codigo, commit = _correr(["git", "-C", str(RAIZ), "rev-parse", "HEAD"])
    if codigo != 0:
        return None, [f"no se pudo leer el HEAD del árbol medido: {commit}"]
    codigo, sucio = _correr(["git", "-C", str(RAIZ), "status", "--porcelain"])
    if codigo != 0:
        return None, [f"no se pudo leer el estado del árbol medido: {sucio}"]

    destino.mkdir(parents=True)
    hogar = destino.parent / f"{destino.name}-hogar"
    hogar.mkdir(parents=True, exist_ok=True)
    entorno = entorno_sin_credenciales(hogar)

    codigo, salida = _correr(["git", "clone", "--no-hardlinks", "--quiet",
                              str(RAIZ), str(destino)], entorno=entorno)
    if codigo != 0:
        problemas.append(f"no se pudo clonar el árbol medido: {salida}")
        return None, problemas

    for remoto in _correr(["git", "-C", str(destino), "remote"], entorno=entorno)[1].split():
        _correr(["git", "-C", str(destino), "remote", "remove", remoto], entorno=entorno)

    retiros = [
        {"clave": "remotos", "que_retira": "los remotos configurados del árbol desechable",
         "constancia": constatar_remotos(destino, entorno).como_json()},
        {"clave": "credenciales",
         "que_retira": "el alcance a credenciales del entorno con el que corre el worker",
         "constancia": constatar_credenciales(hogar, entorno).como_json()},
        {"clave": "red", "que_retira": "la red del worker, que impone el sandbox de su comando",
         "constancia": constatar_red(
             _comandos_de_las_recetas() if comandos is None else comandos).como_json()},
    ]

    acta = {
        "version_acta": VERSION_DEL_ACTA,
        "arbol_desechable": _relativa(destino),
        "hogar_desechable": _relativa(hogar),
        "origen": {"commit": commit, "arbol_limpio": not sucio},
        "retiros": retiros,
        "juzgado_por": [j.clave for j in JUECES_DE_AISLAMIENTO],
        "veredicto_de_aislamiento": veredicto_de_aislamiento(retiros),
    }
    return acta, problemas


def veredicto_de_aislamiento(retiros: list[dict[str, Any]]) -> str:
    """El acta no se declara aislada sola.

    Sin juez registrado el veredicto es `sin_juez_registrado`, aunque los tres retiros estén
    comprobados: la evidencia capturada no es su propio juicio. Con jueces registrados, el veredicto
    sale de ellos.
    """
    if not JUECES_DE_AISLAMIENTO:
        return "sin_juez_registrado"
    problemas = [p for juez in JUECES_DE_AISLAMIENTO for p in juez.juzgar({"retiros": retiros})]
    return "aislado" if not problemas else "no_aislado"


def reportar_provisionamiento(acta: dict[str, Any], ruta_acta: Path) -> int:
    """Imprime el acta y decide el código de salida.

    Es una función propia y no el cuerpo del modo porque es **la decisión**: un control que quiera
    probar que un retiro sin constancia hace fallar el modo tiene que ejercer esta, no reescribir su
    predicado al lado.
    """
    sin_comprobar = []
    for retiro in acta["retiros"]:
        constancia = retiro["constancia"]
        estado = "OK    " if constancia["comprobado"] else "FALLA "
        if not constancia["comprobado"]:
            sin_comprobar.append(retiro["clave"])
        print(f"[{retiro['clave']}] {estado} {retiro['que_retira']}")
        print(f"       comando: {constancia['comando']}")
        print(f"       observado: {constancia['salida_observada']}")
        print(f"       {constancia['detalle']}")

    print()
    print(f"Acta: {_relativa(ruta_acta)} — veredicto de aislamiento: "
          f"{acta['veredicto_de_aislamiento']}")
    if acta["veredicto_de_aislamiento"] == "sin_juez_registrado":
        print("       la evidencia queda capturada y SIN juzgar: el juez es otra capacidad y "
              "todavía no hay ninguno registrado")
    if sin_comprobar:
        print()
        print(f"RESULTADO: FALLA — retiros sin constancia comprobable: {', '.join(sin_comprobar)}")
        return 1
    print()
    print(f"RESULTADO: OK — los {len(CLAVES_DE_RETIRO)} retiros dejaron constancia comprobable")
    return 0


def modo_provisionar(args: argparse.Namespace) -> int:
    destino = _ruta_absoluta(getattr(args, "provisionar"))
    acta, problemas = provisionar(destino)
    if acta is None:
        for p in problemas:
            print(f"FALLA  {p}")
        print()
        print("RESULTADO: FALLA — el árbol desechable no se provisionó")
        return 1

    ruta_acta = destino / NOMBRE_DEL_ACTA
    _escribir_json(ruta_acta, acta)
    return reportar_provisionamiento(acta, ruta_acta)


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-provisionamiento`.
#
# Nueve controles. Los negativos ejercen las funciones de constatación reales sobre entradas reales
# —un remoto que vuelve, un HOME con una credencial adentro, un comando sin sandbox—, no una
# bandera de sabotaje: un modo que solo se pudiera romper por una bandera que existe para romperlo
# no probaría nada sobre cómo se rompe de verdad.
#
# El conjunto de retiros ejercidos se **acumula corriendo**. Transcribirlo dejaría que un retiro
# nuevo entrara sin negativo y el control siguiera en verde.
# ---------------------------------------------------------------------------------------------

class Resultado(NamedTuple):
    clave: str
    que_prueba: str
    problemas: list[str]


def _imprimir_controles(titulo: str, resultados: list[Resultado]) -> int:
    rojos = [r for r in resultados if r.problemas]
    for r in resultados:
        if r.problemas:
            print(f"[{r.clave}] FALLA  {r.que_prueba} — {len(r.problemas)}:")
            for p in r.problemas[:8]:
                print(f"       - {p}")
        else:
            print(f"[{r.clave}] OK     {r.que_prueba}")
    print()
    if rojos:
        print(f"RESULTADO: FALLA — controles en rojo: {', '.join(r.clave for r in rojos)}")
        return 1
    print(f"RESULTADO: OK — {titulo}: los {len(resultados)} controles pasan")
    return 0


COMANDO_CON_SANDBOX_POR_FLAG = "codex exec -s read-only -C . --skip-git-repo-check --json"
COMANDO_CON_SANDBOX_POR_CONFIG = (
    'codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write" --skip-git-repo-check')
COMANDO_SIN_SANDBOX = "codex exec -C . --skip-git-repo-check --json"


def modo_autotest_provisionamiento(args: argparse.Namespace) -> int:
    del args
    resultados: list[Resultado] = []
    ejercidos: set[str] = set()

    with tempfile.TemporaryDirectory(prefix="runner-prov-") as tmp:
        base = Path(tmp)

        # [A] El camino positivo, sobre un destino limpio.
        destino = base / "arbol"
        acta, problemas = provisionar(destino)
        fallas = list(problemas)
        if acta is None:
            fallas.append("el provisionamiento no produjo acta sobre un destino limpio")
        else:
            _escribir_json(destino / NOMBRE_DEL_ACTA, acta)
            sin_comprobar = [r["clave"] for r in acta["retiros"]
                             if not r["constancia"]["comprobado"]]
            if sin_comprobar:
                fallas.append(f"retiros sin constancia en el camino positivo: {sin_comprobar}")
            if not (destino / ".git").exists():
                fallas.append("el árbol desechable no es un repositorio")
        resultados.append(Resultado("A", "provisiona un árbol desechable y deja las tres "
                                         "constancias comprobadas", fallas))

        # [B] El acta declara exactamente el conjunto cerrado de retiros, en las dos direcciones.
        fallas = []
        if acta is not None:
            declaradas = [r["clave"] for r in acta["retiros"]]
            faltan = [c for c in CLAVES_DE_RETIRO if c not in declaradas]
            sobran = [c for c in declaradas if c not in CLAVES_DE_RETIRO]
            if faltan:
                fallas.append(f"el acta no declara estos retiros: {faltan}")
            if sobran:
                fallas.append(f"el acta declara retiros que no son del conjunto: {sobran}")
            if len(declaradas) != len(set(declaradas)):
                fallas.append("el acta repite alguna clave de retiro")
        resultados.append(Resultado("B", "el acta declara el conjunto cerrado de retiros, "
                                         "comparado en las dos direcciones", fallas))

        # [C] Negativo: árbol reutilizado. El segundo provisionamiento falla y no pisa el acta.
        fallas = []
        antes = (destino / NOMBRE_DEL_ACTA).read_bytes()
        segunda, problemas_segunda = provisionar(destino)
        if segunda is not None:
            fallas.append("provisionar sobre un destino que ya existe devolvió acta")
        if not problemas_segunda:
            fallas.append("reutilizar el árbol no reportó ningún problema")
        if (destino / NOMBRE_DEL_ACTA).read_bytes() != antes:
            fallas.append("el intento sobre el árbol reutilizado pisó el acta del original")
        resultados.append(Resultado("C", "un árbol reutilizado se rechaza y no toca el acta "
                                         "del original", fallas))

        # [D] Negativo: remoto sobreviviente.
        fallas = []
        hogar = base / "arbol-hogar"
        entorno = entorno_sin_credenciales(hogar)
        _correr(["git", "-C", str(destino), "remote", "add", "origin",
                 "https://example.invalid/repo.git"], entorno=entorno)
        constancia = constatar_remotos(destino, entorno)
        if constancia.comprobado:
            fallas.append("un remoto sobreviviente dejó la constancia en comprobado")
        elif "origin" not in constancia.salida_observada:
            fallas.append("la constancia no nombra el remoto que sobrevivió")
        else:
            ejercidos.add("remotos")
        _correr(["git", "-C", str(destino), "remote", "remove", "origin"], entorno=entorno)
        if not constatar_remotos(destino, entorno).comprobado:
            fallas.append("quitar el remoto no devolvió la constancia a comprobado: el control "
                          "no distingue el retiro de su ausencia")
        resultados.append(Resultado("D", "un remoto sobreviviente deja el retiro sin constancia, "
                                         "y quitarlo la devuelve", fallas))

        # [E] Negativo: credencial alcanzable.
        fallas = []
        hogar_sucio = base / "hogar-con-credencial"
        (hogar_sucio / ".config" / "gh").mkdir(parents=True, exist_ok=True)
        (hogar_sucio / ".config" / "gh" / "hosts.yml").write_text("token: falso\n",
                                                                 encoding="utf-8")
        entorno_sucio = entorno_sin_credenciales(hogar_sucio)
        constancia = constatar_credenciales(hogar_sucio, entorno_sucio)
        if constancia.comprobado:
            fallas.append("una credencial alcanzable dejó la constancia en comprobado")
        elif ".config/gh/hosts.yml" not in constancia.salida_observada:
            fallas.append("la constancia no nombra la credencial alcanzable")
        else:
            ejercidos.add("credenciales")
        entorno_con_token = entorno_sin_credenciales(base / "hogar-limpio")
        entorno_con_token["GITHUB_TOKEN"] = "falso"
        if constatar_credenciales(base / "hogar-limpio", entorno_con_token).comprobado:
            fallas.append("un token en el entorno dejó la constancia en comprobado: el control "
                          "mira los archivos y no las variables")
        resultados.append(Resultado("E", "una credencial alcanzable —archivo o variable— deja el "
                                         "retiro sin constancia", fallas))

        # [F] Negativo: comando sin sandbox. Con su positivo por las DOS formas de pedirlo.
        fallas = []
        constancia = constatar_red((COMANDO_SIN_SANDBOX,))
        if constancia.comprobado:
            fallas.append("un comando sin sandbox dejó el retiro de red en comprobado")
        else:
            ejercidos.add("red")
        for etiqueta, comando in (("por flag", COMANDO_CON_SANDBOX_POR_FLAG),
                                  ("por configuración", COMANDO_CON_SANDBOX_POR_CONFIG)):
            if not constatar_red((comando,)).comprobado:
                fallas.append(f"un comando que pide sandbox {etiqueta} quedó sin constancia: la "
                              f"forma no se reconoce y se lee como si no lo pidiera")
        if constatar_red(()).comprobado:
            fallas.append("sin ningún comando la constancia dio comprobada: nada que constatar no "
                          "es lo mismo que constatado")
        if sandbox_pedido('codex exec -s inventado -c sandbox_mode="inventado"') is not None:
            fallas.append("un modo de sandbox que no es del conjunto cerrado contó como pedido")
        resultados.append(Resultado("F", "el retiro de red se constata sobre el sandbox que pide "
                                         "el comando, en sus dos formas", fallas))

        # [G] El enganche del juez, en las dos direcciones.
        fallas = []
        retiros_sanos = acta["retiros"] if acta else []
        if veredicto_de_aislamiento(retiros_sanos) != "sin_juez_registrado":
            fallas.append("sin juez registrado el acta no declaró `sin_juez_registrado`")
        previos = list(JUECES_DE_AISLAMIENTO)
        try:
            JUECES_DE_AISLAMIENTO.clear()
            registrar_juez_de_aislamiento("prueba-rechaza", "rechaza siempre",
                                          lambda _: ["rechazado por el juez de prueba"])
            if veredicto_de_aislamiento(retiros_sanos) != "no_aislado":
                fallas.append("con un juez que rechaza el veredicto no fue `no_aislado`")
            JUECES_DE_AISLAMIENTO.clear()
            registrar_juez_de_aislamiento("prueba-acepta", "acepta siempre", lambda _: [])
            if veredicto_de_aislamiento(retiros_sanos) != "aislado":
                fallas.append("con un juez que acepta el veredicto no fue `aislado`")
        finally:
            JUECES_DE_AISLAMIENTO.clear()
            JUECES_DE_AISLAMIENTO.extend(previos)
        resultados.append(Resultado("G", "el enganche del juez de aislamiento puede ponerse rojo "
                                         "y verde, y sin juez nunca declara aislamiento", fallas))

        # [H] La decisión del modo: un retiro sin constancia devuelve un código distinto de 0.
        fallas = []
        destino_flojo = base / "arbol-sin-sandbox"
        acta_floja, _ = provisionar(destino_flojo, comandos=(COMANDO_SIN_SANDBOX,))
        if acta_floja is None:
            fallas.append("no se pudo provisionar el árbol del negativo del modo")
        else:
            ruta = destino_flojo / NOMBRE_DEL_ACTA
            _escribir_json(ruta, acta_floja)
            # La salida del negativo se captura: un `RESULTADO: FALLA` impreso en medio de un
            # autotest verde se lee como una regresión y no como el negativo que es.
            with contextlib.redirect_stdout(io.StringIO()) as capturado:
                codigo = reportar_provisionamiento(acta_floja, ruta)
            if codigo == 0:
                fallas.append("un retiro sin constancia comprobable devolvió 0")
            if "red" not in capturado.getvalue():
                fallas.append("el reporte del negativo no nombra el retiro que quedó sin "
                              "constancia")
            if acta_floja["veredicto_de_aislamiento"] == "aislado":
                fallas.append("un acta con un retiro sin constancia se declaró aislada")
        resultados.append(Resultado("H", "la decisión del modo devuelve distinto de 0 cuando un "
                                         "retiro no dejó constancia", fallas))

        # [I] Cobertura: cada clave del conjunto cerrado fue ejercida por un negativo.
        fallas = []
        sin_negativo = [c for c in CLAVES_DE_RETIRO if c not in ejercidos]
        inexistentes = sorted(ejercidos - set(CLAVES_DE_RETIRO))
        if sin_negativo:
            fallas.append(f"retiros sin negativo que los ponga en rojo: {sin_negativo}")
        if inexistentes:
            fallas.append(f"se ejercieron claves que no son retiros: {inexistentes}")
        resultados.append(Resultado("I", f"los {len(CLAVES_DE_RETIRO)} retiros tienen un negativo "
                                         f"que los pone en rojo, acumulado corriendo", fallas))

    return _imprimir_controles("provisionamiento", resultados)


# ---------------------------------------------------------------------------------------------
# Modo `--preflight`.
#
# Un bloqueo es un resultado válido, no un fallo del modo: el modo falla si a alguna receta le
# falta adjudicación o si una adjudicación cita una causa que no es del conjunto cerrado. Que un
# bloqueo detenga el gate lo decide el acta, no este archivo.
#
# La causa se toma de un conjunto cerrado a propósito. Una causa en texto libre deja que dos
# bloqueos por el mismo motivo se cuenten como distintos, y que uno nuevo entre sin que nadie lo
# haya previsto.
# ---------------------------------------------------------------------------------------------

CAUSAS_DE_BLOQUEO = (
    "adaptador_ausente",
    "lanzamiento_no_controlable",
    "transporte_no_resoluble",
    "sesion_desechable_no_disponible",
    "enlace_de_escenario_no_probado",
)

# Los transportes que un bundle puede declarar. `mixto` no está: es el agregado de un punto en la
# matriz, no el transporte de un intento. Un intento corre por uno solo, y cuál fue se resuelve
# antes de correr o el caso se bloquea.
TRANSPORTES_DEL_BUNDLE = ("subagent", "cli-exec", "cli-resume")

# Cómo se resuelve el transporte efectivo de una receta cuyo punto es `mixto`. No se parsea el
# comando: se lo compara contra las dos formas de invocación que el ecosistema declara, y la que
# no coincida con ninguna deja el transporte sin resolver.
FORMAS_DE_INVOCACION = (
    ("cli-resume", "codex exec resume "),
    ("cli-exec", "codex exec "),
)


class Prueba(NamedTuple):
    clave: str
    pasa: bool
    evidencia: str

    def como_json(self) -> dict[str, Any]:
        return {"prueba": self.clave, "pasa": self.pasa, "evidencia": self.evidencia}


class Adjudicacion(NamedTuple):
    receta_id: str
    punto_de_despacho: str
    estado: str
    causa: str | None
    detalle: str
    pruebas: tuple[Prueba, ...]

    def como_json(self) -> dict[str, Any]:
        return {
            "receta_id": self.receta_id,
            "punto_de_despacho": self.punto_de_despacho,
            "estado": self.estado,
            "causa": self.causa,
            "detalle": self.detalle,
            "pruebas": [p.como_json() for p in self.pruebas],
        }


def transporte_efectivo(receta: dict[str, Any]) -> tuple[str | None, str]:
    """El transporte por el que va a correr este intento, o por qué no se pudo resolver."""
    declarado = receta.get("transporte")
    if declarado in TRANSPORTES_DEL_BUNDLE:
        return declarado, f"la receta declara `{declarado}`, que es un transporte de intento"
    comando = receta.get("comando")
    if not comando:
        return None, (f"la receta declara `{declarado}`, que no es un transporte de intento, y no "
                      f"tiene comando del que resolverlo")
    for transporte, forma in FORMAS_DE_INVOCACION:
        if comando.startswith(forma):
            return transporte, (f"`{declarado}` se resolvió a `{transporte}` por la forma de "
                                f"invocación `{forma.strip()}` de su comando congelado")
    return None, (f"`{declarado}` no se resolvió: el comando congelado no empieza por ninguna de "
                  f"las {len(FORMAS_DE_INVOCACION)} formas de invocación declaradas")


def _binario_del_comando(comando: str) -> str:
    return comando.split(maxsplit=1)[0] if comando.strip() else ""


def _variables_del_comando(comando: str) -> set[str]:
    """Los marcadores `<…>` que el comando congelado deja por sustituir."""
    return set(re.findall(r"<([^<>]+)>", comando))


class Sesionador(NamedTuple):
    """Cómo se crea y se reanuda una sesión desechable.

    Es una interfaz y no una llamada directa porque el preflight de verdad prueba el `resume` del
    CLI —con su costo y su latencia— y los controles necesitan ejercer las mismas adjudicaciones
    sin despachar un modelo. Las dos implementaciones comparten el probador, que es donde vive la
    decisión; lo que cambia es de dónde salen las sesiones.

    `reanudar` devuelve el identificador del hilo que quedó abierto, no un booleano: medido sobre el
    CLI de hoy, reanudar una sesión inexistente **sale en 0 y arranca una sesión fresca**. Un
    probador que leyera el código de salida daría verde justo en el caso que la regla de enlace
    existe para impedir.
    """
    nombre: str
    crear_desechable: Callable[[], tuple[str | None, str]]
    reanudar: Callable[[str], tuple[str | None, str]]


def _hilo_del_jsonl(texto: str) -> str | None:
    """El identificador del hilo que abrió una corrida, leído de su primer evento que lo declare."""
    for linea in texto.splitlines():
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if not isinstance(evento, dict):
            continue
        for clave in ("thread_id", "session_id"):
            if isinstance(evento.get(clave), str):
                return evento[clave]
    return None


def sesionador_codex(directorio: Path) -> Sesionador:
    """El sesionador real: crea una sesión desechable con el CLI y la reanuda."""

    def _correr_hilo(comando: str, nombre_del_hilo: str) -> tuple[str | None, str]:
        directorio.mkdir(parents=True, exist_ok=True)
        prompt = directorio / "prompt-desechable.txt"
        prompt.write_text("responde únicamente: ok\n", encoding="utf-8")
        hilo = directorio / nombre_del_hilo
        # El prompt viaja por archivo y no inline, como en todo el ecosistema: el markdown con
        # backticks rompe el quoting. Y va redirigido para que `-` no se quede leyendo el stdin
        # del proceso padre.
        codigo, salida = _correr(["sh", "-c", f"{comando} - < {prompt} > {hilo}"])
        if codigo != 0:
            return None, f"la invocación salió en {codigo}: {salida[:200]}"
        return _hilo_del_jsonl(hilo.read_text(encoding="utf-8")), "hilo leído de la salida `--json`"

    def crear() -> tuple[str | None, str]:
        if shutil.which("codex") is None:
            return None, "no hay binario `codex` en PATH"
        hilo, detalle = _correr_hilo(
            f"codex exec -s read-only -C {directorio} --skip-git-repo-check --json",
            "hilo-desechable.jsonl")
        if hilo is None:
            return None, f"la sesión desechable no se pudo crear: {detalle}"
        return hilo, "sesión desechable creada"

    def reanudar(session_id: str) -> tuple[str | None, str]:
        if shutil.which("codex") is None:
            return None, "no hay binario `codex` en PATH"
        hilo, detalle = _correr_hilo(
            f'codex exec resume {session_id} -c sandbox_mode="read-only" '
            f"--skip-git-repo-check --json",
            "hilo-resume.jsonl")
        return hilo, detalle

    return Sesionador("codex", crear, reanudar)


class ResultadoDeResume(NamedTuple):
    pasa: bool
    pruebas: tuple[Prueba, ...]
    detalle: str


def reanudar_con_guarda(sesionador: Sesionador, session_id: str,
                        propias: set[str]) -> tuple[bool, str]:
    """Reanuda una sesión y comprueba que se haya reanudado **esa**.

    Dos guardas, y ninguna reemplaza a la otra. La primera es de propiedad: una sesión que este
    runner no creó es ajena, y eso no se puede preguntar a la plataforma —hay que saberlo—, así que
    se rechaza antes de invocar. La segunda es de identidad: el hilo que quedó abierto tiene que ser
    el que se pidió, porque reanudar uno inexistente arranca uno fresco sin decirlo.
    """
    if session_id not in propias:
        return False, ("la sesión no la creó este runner: reanudarla mediría una sesión ajena, "
                       "cuyo contenido previo no está en el pre-registro")
    hilo, detalle = sesionador.reanudar(session_id)
    if hilo is None:
        return False, f"el `resume` no abrió ningún hilo: {detalle}"
    if hilo != session_id:
        return False, (f"el `resume` abrió el hilo `{hilo}` y se había pedido `{session_id}`: no "
                       f"reanudó, arrancó una sesión fresca")
    return True, f"el hilo abierto es el que se pidió: `{hilo}`"


def probar_resume(sesionador: Sesionador, repeticiones: int = 2) -> ResultadoDeResume:
    """Prueba el `resume` con una sesión desechable y sus tres negativos.

    Los tres negativos son los que la regla de enlace del escenario declara. El positivo va primero
    a propósito: sin él, tres negativos que fallan por un `resume` roto se leerían como tres
    negativos que funcionan.
    """
    pruebas: list[Prueba] = []
    sesiones: list[str] = []
    for _ in range(repeticiones):
        session_id, detalle = sesionador.crear_desechable()
        if session_id is None:
            return ResultadoDeResume(False, (), detalle)
        sesiones.append(session_id)
    propias = set(sesiones)

    pasa, detalle = reanudar_con_guarda(sesionador, sesiones[0], propias)
    pruebas.append(Prueba("resume-de-sesion-desechable", pasa, detalle))

    pasa, detalle = reanudar_con_guarda(sesionador, "sesion-que-no-existe", propias | {"sesion-que-no-existe"})
    pruebas.append(Prueba("negativo-sesion-ausente", not pasa, detalle))

    pasa, detalle = reanudar_con_guarda(sesionador, "sesion-ajena-de-otro-productor", propias)
    pruebas.append(Prueba("negativo-sesion-ajena", not pasa, detalle))

    reutilizada = len(set(sesiones)) != len(sesiones)
    pruebas.append(Prueba(
        "negativo-sesion-reutilizada-entre-repeticiones", not reutilizada,
        f"{repeticiones} repeticiones produjeron {len(set(sesiones))} sesiones distintas: "
        f"reutilizar una entre repeticiones haría que dos muestras midieran la misma"))

    fallidas = [p.clave for p in pruebas if not p.pasa]
    return ResultadoDeResume(
        not fallidas, tuple(pruebas),
        "el `resume` se probó con sesión desechable y sus tres negativos" if not fallidas
        else f"pruebas del `resume` en rojo: {', '.join(fallidas)}")


def preflightear(receta: dict[str, Any], *, recibos: Path,
                 sesionador: Sesionador | None = None) -> Adjudicacion:
    """Adjudica una receta `runnable` o `blocked`, con causa del conjunto cerrado."""
    pruebas: list[Prueba] = []
    receta_id = receta.get("receta_id", "<sin id>")
    punto = receta.get("punto_de_despacho", "<sin punto>")
    adaptador = receta.get("adaptador")

    def bloqueo(causa: str, detalle: str) -> Adjudicacion:
        return Adjudicacion(receta_id, punto, "blocked", causa, detalle, tuple(pruebas))

    transporte, detalle_transporte = transporte_efectivo(receta)
    pruebas.append(Prueba("transporte-resoluble", transporte is not None, detalle_transporte))
    if transporte is None:
        return bloqueo("transporte_no_resoluble", detalle_transporte)

    if adaptador == "script":
        comando = receta.get("comando") or ""
        binario = _binario_del_comando(comando)
        ruta_binario = shutil.which(binario) if binario else None
        pruebas.append(Prueba("adaptador-disponible", ruta_binario is not None,
                              f"`{binario}` {'está en ' + ruta_binario if ruta_binario else 'no está en PATH'}"))
        if ruta_binario is None:
            return bloqueo("adaptador_ausente",
                           f"el comando de la receta invoca `{binario}`, que no está en PATH")

        modo = sandbox_pedido(comando)
        admitidas = set(receta.get("variables_admitidas") or [])
        no_admitidas = sorted(_variables_del_comando(comando) - admitidas)
        controlable = modo is not None and not no_admitidas
        pruebas.append(Prueba(
            "lanzamiento-controlable", controlable,
            f"sandbox pedido: {modo or 'ninguno'}; "
            f"marcadores fuera de `variables_admitidas`: {no_admitidas or 'ninguno'}"))
        if not controlable:
            return bloqueo("lanzamiento_no_controlable",
                           "un comando sin sandbox pedido, o con marcadores que la receta no "
                           "admite, no se lanza de forma controlada: no se sabe con qué corre")

    elif adaptador == "sesion_de_agente":
        # Un script no puede despachar un subagente, así que su disponibilidad no se prueba
        # invocándolo: se prueba contra el recibo de conformance del despacho nativo desechable,
        # que es la evidencia de frontera de ese transporte. Sin recibo, el adaptador está ausente
        # aunque la plataforma exista: lo que falta es la prueba, no la capacidad.
        recibo, detalle_recibo = recibo_de_conformance_de(recibos, punto)
        pruebas.append(Prueba("adaptador-disponible", recibo is not None, detalle_recibo))
        if recibo is None:
            return bloqueo("adaptador_ausente", detalle_recibo)

        apertura = next((e for e in recibo["recibo"]["eventos"]
                         if e["evento"] == "dispatch_started"), None)
        controlable = apertura is not None and bool(apertura.get("prompt_sha256"))
        pruebas.append(Prueba(
            "lanzamiento-controlable", controlable,
            "el recibo declara el hash del prompt congelado antes de despachar" if controlable
            else "el recibo no acredita un prompt congelado antes del despacho"))
        if not controlable:
            return bloqueo("lanzamiento_no_controlable",
                           "sin prompt congelado antes del despacho, dos intentos del mismo punto "
                           "no son la misma medición")

        # La apertura sola NO alcanza. Se emite ANTES de la tool call, así que acredita lo que se
        # sabía al despachar y nada sobre si el despacho ocurrió: un recibo abierto y nunca cerrado
        # es indistinguible de un despacho que se anunció y no se hizo. Medido: con cinco recibos
        # que solo tenían su apertura, el preflight adjudicaba los seis puntos de subagente
        # `runnable`. V35 pide un despacho «que prueba el protocolo de frontera de punta a punta»,
        # y la otra punta es el retorno.
        retorno = next((e for e in recibo["recibo"]["eventos"]
                        if e["evento"] == "dispatch_returned"), None)
        completo = (retorno is not None
                    and retorno.get("referencia_evento_id") == apertura.get("evento_id")
                    and bool(retorno.get("salida_sha256")))
        pruebas.append(Prueba(
            "despacho-completado", completo,
            "el recibo cierra con el retorno del despacho, referenciando su apertura y con el "
            "hash de la salida cosechada" if completo
            else "el recibo no acredita que el despacho haya vuelto: solo tiene la apertura, que "
                 "se emite antes de la tool call"))
        if not completo:
            return bloqueo("adaptador_ausente",
                           "el despacho nativo desechable no se probó de punta a punta: su recibo "
                           "no tiene retorno que referencie la apertura con la salida cosechada")
    else:
        return bloqueo("adaptador_ausente", f"adaptador desconocido: {adaptador!r}")

    if transporte == "cli-resume":
        if sesionador is None:
            return bloqueo("sesion_desechable_no_disponible",
                           "el paso de `cli-resume` necesita probar el `resume` y no hay "
                           "sesionador con el que hacerlo")
        resultado = probar_resume(sesionador)
        pruebas.extend(resultado.pruebas)
        if not resultado.pasa:
            causa = ("sesion_desechable_no_disponible" if not resultado.pruebas
                     else "enlace_de_escenario_no_probado")
            return bloqueo(causa, resultado.detalle)

    return Adjudicacion(receta_id, punto, "runnable", None,
                        f"lanzable por `{transporte}` con el adaptador `{adaptador}`",
                        tuple(pruebas))


def recibo_de_conformance_de(directorio: Path,
                             punto: str) -> tuple[dict[str, Any] | None, str]:
    """Busca el recibo de conformance del punto en la sede de recibos."""
    if not directorio.is_dir():
        return None, f"no existe la sede de recibos {_relativa(directorio)}"
    for ruta in sorted(directorio.glob("*.json")):
        if ruta.name.endswith(".schema.json"):
            continue
        datos, error = _cargar_json(ruta)
        if error or not isinstance(datos, dict):
            continue
        recibo = datos.get("recibo") or {}
        if (recibo.get("protocolo") == "conformance"
                and recibo.get("punto_de_despacho") == punto):
            return datos, f"recibo de conformance en {_relativa(ruta)}"
    return None, (f"no hay recibo de conformance para `{punto}` en "
                  f"{_relativa(directorio)}: el despacho nativo desechable no se probó")


def preflightear_recetas(recetas: list[dict[str, Any]], *, recibos: Path,
                         sesionador: Sesionador | None = None) -> list[Adjudicacion]:
    return [preflightear(r, recibos=recibos, sesionador=sesionador) for r in recetas]


def revisar_adjudicaciones(recetas: list[dict[str, Any]],
                           adjudicaciones: list[Adjudicacion]) -> list[str]:
    """Lo que hace fallar al modo: una receta sin adjudicar, o una causa fuera del conjunto."""
    problemas: list[str] = []
    esperadas = [r.get("receta_id") for r in recetas]
    adjudicadas = [a.receta_id for a in adjudicaciones]
    for receta_id in esperadas:
        if receta_id not in adjudicadas:
            problemas.append(f"la receta `{receta_id}` quedó sin adjudicar")
    for receta_id in adjudicadas:
        if receta_id not in esperadas:
            problemas.append(f"se adjudicó `{receta_id}`, que no es una receta de la cohorte")
    for adjudicacion in adjudicaciones:
        if adjudicacion.estado not in ("runnable", "blocked"):
            problemas.append(f"`{adjudicacion.receta_id}`: estado desconocido "
                             f"`{adjudicacion.estado}`")
        if adjudicacion.estado == "blocked" and adjudicacion.causa not in CAUSAS_DE_BLOQUEO:
            problemas.append(f"`{adjudicacion.receta_id}`: bloqueo con causa "
                             f"`{adjudicacion.causa}`, que no es del conjunto cerrado")
        if adjudicacion.estado == "runnable" and adjudicacion.causa is not None:
            problemas.append(f"`{adjudicacion.receta_id}`: adjudicado lanzable y con causa de "
                             f"bloqueo, que es contradictorio")
        if not adjudicacion.pruebas:
            problemas.append(f"`{adjudicacion.receta_id}`: adjudicado sin ninguna prueba que lo "
                             f"sostenga")
    return problemas


def materializar_egreso(destino: Path) -> tuple[dict[str, Any] | None, str]:
    """Corre el recibo de egreso del INSTRUMENTO, como proceso aparte.

    El runner no importa el instrumento —el juez de lo que produce nunca comparte proceso con él—,
    así que el inventario que el acta congela se pide por la misma frontera que la validación de
    bundles: un subproceso, con su código de salida como veredicto. Reimplementar la regla acá la
    volvería un dato declarado dos veces, que es lo que AC-23 prohíbe.
    """
    comando = [sys.executable, str(RUTA_INSTRUMENTO),
               "--recibo-de-egreso", "--salida", str(destino)]
    try:
        proc = subprocess.run(comando, capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return None, f"el recibo de egreso no pudo correr: {type(exc).__name__}"
    if proc.returncode != 0:
        cola = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
        return None, ("el recibo de egreso falló (exit "
                      f"{proc.returncode}): {' | '.join(cola)}")
    recibo, error = _cargar_json(destino)
    if error:
        return None, error
    return recibo, f"inventario materializado en {_relativa(destino)}"


def adjuntar_al_acta(acta: Path, adjudicaciones: list[Adjudicacion],
                     recibo_de_egreso: dict[str, Any],
                     recibos: Path) -> tuple[list[str], dict[str, Any]]:
    """Escribe en el acta el inventario materializado y el recibo del preflight (D-14).

    Lo que el usuario aprueba es la versión que YA los lleva: adjuntarlos después del STOP haría
    que lo aprobado y lo congelado fueran documentos distintos.
    """
    documento, error = _cargar_json(acta)
    if error:
        return [error], {}

    identidades: list[str] = []
    for ruta in sorted(recibos.glob("*.json")) if recibos.is_dir() else []:
        if ruta.name.endswith(".schema.json"):
            continue
        datos, err = _cargar_json(ruta)
        if err or not isinstance(datos, dict):
            continue
        cuerpo = datos.get("recibo") or {}
        if cuerpo.get("protocolo") == "conformance" and cuerpo.get("recibo_id"):
            identidades.append(cuerpo["recibo_id"])

    documento["inventario_de_egreso"] = recibo_de_egreso["inventario_de_egreso"]
    documento["recibo_del_preflight"] = {
        "recibo_sha256": recibo_de_egreso["recibo_sha256"],
        "adjudicaciones": [
            {"receta_id": a.receta_id, "adjudicacion": a.estado}
            if a.estado == "runnable"
            else {"receta_id": a.receta_id, "adjudicacion": a.estado, "causa_id": a.causa}
            for a in adjudicaciones
        ],
        "recibos_de_frontera_de_conformance": sorted(set(identidades)),
    }
    acta.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [], documento


def revisar_cobertura_contra_bloqueos(documento: dict[str, Any],
                                      adjudicaciones: list[Adjudicacion],
                                      recetas: list[dict[str, Any]]) -> list[str]:
    """Lo único por lo que un bloqueo hace fallar el modo: que viole la cobertura pre-registrada.

    Un bloqueo es un resultado válido (D-15) y el acta decide qué hacer con él; pero un punto que
    el acta declara observado y cuya receta no se puede lanzar no es una decisión pendiente: es una
    cohorte que no se puede correr como está escrita.
    """
    observados = set(((documento.get("cobertura") or {}).get("puntos_observados")) or [])
    punto_de = {r.get("receta_id"): r.get("punto_de_despacho") for r in recetas}
    problemas: list[str] = []
    for adjudicacion in adjudicaciones:
        if adjudicacion.estado != "blocked":
            continue
        punto = punto_de.get(adjudicacion.receta_id)
        if punto in observados:
            problemas.append(
                f"`{punto}` está declarado observado y su receta `{adjudicacion.receta_id}` quedó "
                f"bloqueada por `{adjudicacion.causa}`: la cobertura pre-registrada no se puede "
                f"cumplir con esta cohorte")
    return problemas


def modo_preflight(args: argparse.Namespace) -> int:
    recetas_json, error = _cargar_json(RUTA_RECETAS)
    if error:
        print(f"FALLA  {error}")
        return 1
    recetas = recetas_json.get("recetas") or []

    crudo_recibos = getattr(args, "recibos", None)
    recibos = _ruta_absoluta(crudo_recibos) if crudo_recibos else DIR_RECIBOS_FASE_0

    with tempfile.TemporaryDirectory(prefix="runner-resume-") as tmp:
        adjudicaciones = preflightear_recetas(recetas, recibos=recibos,
                                              sesionador=sesionador_codex(Path(tmp)))

    for adjudicacion in adjudicaciones:
        if adjudicacion.estado == "runnable":
            print(f"[runnable] {adjudicacion.receta_id} — {adjudicacion.detalle}")
        else:
            print(f"[blocked ] {adjudicacion.receta_id} — {adjudicacion.causa}: "
                  f"{adjudicacion.detalle}")

    problemas = revisar_adjudicaciones(recetas, adjudicaciones)
    lanzables = sum(1 for a in adjudicaciones if a.estado == "runnable")
    bloqueados = len(adjudicaciones) - lanzables
    print()
    print(f"Adjudicadas {len(adjudicaciones)} de {len(recetas)} recetas: "
          f"{lanzables} lanzables, {bloqueados} bloqueadas")

    crudo_acta = getattr(args, "acta", None)
    if crudo_acta:
        acta = _ruta_absoluta(crudo_acta)
        if not acta.is_file():
            print(f"FALLA  no existe el acta {_relativa(acta)}")
            return 1
        recibo_de_egreso, detalle = materializar_egreso(acta.parent / "recibo-de-egreso.json")
        print(detalle)
        if recibo_de_egreso is None:
            problemas.append(detalle)
        else:
            fallas, documento = adjuntar_al_acta(acta, adjudicaciones, recibo_de_egreso, recibos)
            problemas += fallas
            if not fallas:
                print(f"adjuntados al acta el inventario "
                      f"({len(recibo_de_egreso['inventario_de_egreso']['superficies'])} "
                      f"superficies) y el recibo del preflight "
                      f"({len(adjudicaciones)} adjudicaciones, "
                      f"{len(documento['recibo_del_preflight']['recibos_de_frontera_de_conformance'])}"
                      f" recibos de conformance)")
                problemas += revisar_cobertura_contra_bloqueos(documento, adjudicaciones, recetas)

    if problemas:
        for p in problemas:
            print(f"FALLA  {p}")
        print()
        print(f"RESULTADO: FALLA — {len(problemas)} problemas de adjudicación")
        return 1
    print("RESULTADO: OK — toda receta quedó adjudicada con causa del conjunto cerrado; un "
          "bloqueo es un resultado, y qué hacer con él lo decide el acta")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-preflight`.
#
# El corpus vive en disco y su manifest es INDEPENDIENTE: declara aparte qué adjudicación tiene que
# dar cada caso y, cuando bloquea, **por qué motivo** tiene que caer. Sin el motivo, un caso que
# bloquea por otra cláusula se lee como cubierto.
#
# Los sesionadores de los controles reproducen el comportamiento MEDIDO del CLI, no uno idealizado:
# `que-no-reanuda` abre un hilo fresco y sale bien, que es lo que hace hoy `codex exec resume` con
# una sesión inexistente. Un doble que fallara con código distinto de 0 probaría un negativo que en
# la realidad no ocurre, y dejaría pasar el que sí.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_PREFLIGHT = DIR_FIXTURES_RUNNER / "preflight"
RUTA_CORPUS_PREFLIGHT = DIR_FIXTURES_PREFLIGHT / "recetas.json"
RUTA_MANIFEST_PREFLIGHT = DIR_FIXTURES_PREFLIGHT / "manifest.json"
DIR_RECIBOS_PREFLIGHT = DIR_FIXTURES_PREFLIGHT / "recibos"


@contextlib.contextmanager
def path_con_binario(nombre: str):
    """Pone en PATH un binario con ese nombre, creado para la corrida del control.

    Los controles no pueden depender de qué esté instalado en la máquina: en una sin `codex` el
    caso lanzable adjudicaría `adaptador_ausente` y el control se pondría rojo por el entorno y no
    por el código. El negativo del binario ausente sigue siendo real —usa un nombre que ninguna
    instalación tiene—, así que la independencia no le quita filo.
    """
    with tempfile.TemporaryDirectory(prefix="runner-bin-") as tmp:
        ruta = Path(tmp) / nombre
        ruta.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        ruta.chmod(0o755)
        previo = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{tmp}{os.pathsep}{previo}"
        try:
            yield Path(tmp)
        finally:
            os.environ["PATH"] = previo


def sesionador_local(clase: str) -> Sesionador | None:
    """Los sesionadores de los controles. `ninguno` es la ausencia de sesionador, no un doble."""
    if clase == "ninguno":
        return None

    contador = {"n": 0}

    def crear_sano() -> tuple[str | None, str]:
        contador["n"] += 1
        return f"hilo-desechable-{contador['n']}", "sesión desechable creada"

    def crear_caido() -> tuple[str | None, str]:
        return None, "la sesión desechable no se pudo crear: el sesionador no responde"

    def reanudar_fiel(session_id: str) -> tuple[str | None, str]:
        if session_id.startswith("hilo-desechable-"):
            return session_id, "hilo reanudado"
        return f"hilo-fresco-{session_id}", "el hilo abierto no es el que se pidió"

    def reanudar_fresco(session_id: str) -> tuple[str | None, str]:
        del session_id
        contador["n"] += 1
        return f"hilo-fresco-{contador['n']}", "se abrió un hilo fresco"

    if clase == "sano":
        return Sesionador("local-sano", crear_sano, reanudar_fiel)
    if clase == "caido":
        return Sesionador("local-caido", crear_caido, reanudar_fiel)
    if clase == "que-no-reanuda":
        return Sesionador("local-que-no-reanuda", crear_sano, reanudar_fresco)
    raise ValueError(f"clase de sesionador desconocida: {clase!r}")


def modo_autotest_preflight(args: argparse.Namespace) -> int:
    del args
    resultados: list[Resultado] = []
    causas_ejercidas: set[str] = set()

    corpus, error_corpus = _cargar_json(RUTA_CORPUS_PREFLIGHT)
    manifest, error_manifest = _cargar_json(RUTA_MANIFEST_PREFLIGHT)
    if error_corpus or error_manifest:
        for e in (error_corpus, error_manifest):
            if e:
                print(f"FALLA  {e}")
        return 1
    recetas = corpus["recetas"]
    por_id = {r["receta_id"]: r for r in recetas}
    casos = manifest["casos"]

    # [A] El corpus y su manifest se comparan en las DOS direcciones.
    fallas = []
    del_corpus = [r["receta_id"] for r in recetas]
    del_manifest = [c["receta_id"] for c in casos]
    faltan = [r for r in del_corpus if r not in del_manifest]
    sobran = [r for r in del_manifest if r not in del_corpus]
    if faltan:
        fallas.append(f"recetas del corpus sin caso en el manifest: {faltan}")
    if sobran:
        fallas.append(f"casos del manifest sin receta en el corpus: {sobran}")
    resultados.append(Resultado("A", "el corpus y su manifest independiente coinciden en las dos "
                                     "direcciones", fallas))

    # [B] Cada caso adjudica lo que el manifest declara, y los bloqueos caen POR SU MOTIVO.
    fallas = []
    adjudicaciones: list[Adjudicacion] = []
    with path_con_binario("codex"):
        for caso in casos:
            receta = por_id.get(caso["receta_id"])
            if receta is None:
                continue
            adjudicaciones.append(preflightear(
                receta, recibos=DIR_RECIBOS_PREFLIGHT,
                sesionador=sesionador_local(caso["sesionador"])))
    for caso, adjudicacion in zip(casos, adjudicaciones):
        if adjudicacion.estado != caso["estado_esperado"]:
            fallas.append(f"`{caso['receta_id']}`: adjudicó `{adjudicacion.estado}` y se esperaba "
                          f"`{caso['estado_esperado']}`")
            continue
        if adjudicacion.causa != caso["causa_esperada"]:
            fallas.append(f"`{caso['receta_id']}`: causa `{adjudicacion.causa}` y se esperaba "
                          f"`{caso['causa_esperada']}`")
            continue
        fragmento = caso.get("fragmento_esperado")
        if fragmento:
            visto = adjudicacion.detalle + " " + " ".join(p.evidencia for p in adjudicacion.pruebas)
            if fragmento not in visto:
                fallas.append(f"`{caso['receta_id']}`: bloqueó por `{adjudicacion.causa}` pero no "
                              f"por su motivo — se esperaba «{fragmento}» y no aparece")
                continue
        if adjudicacion.causa:
            causas_ejercidas.add(adjudicacion.causa)
    resultados.append(Resultado("B", "cada caso adjudica lo que el manifest declara, y los "
                                     "bloqueos caen por su motivo", fallas))

    # [C] El transporte efectivo es el que el manifest declara, y `mixto` se resuelve o bloquea.
    fallas = []
    for caso in casos:
        esperado = caso.get("transporte_esperado")
        if not esperado:
            continue
        resuelto, detalle = transporte_efectivo(por_id[caso["receta_id"]])
        if resuelto != esperado:
            fallas.append(f"`{caso['receta_id']}`: transporte `{resuelto}` y se esperaba "
                          f"`{esperado}` — {detalle}")
    if transporte_efectivo({"transporte": "mixto"})[0] is not None:
        fallas.append("una receta `mixto` sin comando resolvió transporte: no hay de dónde")
    if "mixto" in TRANSPORTES_DEL_BUNDLE:
        fallas.append("`mixto` figura entre los transportes que un bundle puede declarar")
    resultados.append(Resultado("C", "el transporte efectivo se resuelve por la forma de "
                                     "invocación congelada, y `mixto` no es uno de bundle", fallas))

    # [D] Las pruebas declaradas se ejecutaron, en su orden y sin faltar ninguna.
    fallas = []
    por_receta = {a.receta_id: a for a in adjudicaciones}
    for caso in casos:
        esperadas = caso.get("pruebas_esperadas")
        if not esperadas:
            continue
        corridas = [p.clave for p in por_receta[caso["receta_id"]].pruebas]
        if corridas != esperadas:
            fallas.append(f"`{caso['receta_id']}`: corrió {corridas} y se esperaba {esperadas}")
    resultados.append(Resultado("D", "cada caso corre las pruebas que el manifest declara, en su "
                                     "orden", fallas))

    # [E] El `resume` y sus tres negativos, cada uno cayendo por su propia guarda.
    fallas = []
    sano = sesionador_local("sano")
    resultado = probar_resume(sano)
    if not resultado.pasa:
        fallas.append(f"el `resume` sano no pasó: {resultado.detalle}")
    motivos = {
        "negativo-sesion-ausente": "arrancó una sesión fresca",
        "negativo-sesion-ajena": "mediría una sesión ajena",
        "negativo-sesion-reutilizada-entre-repeticiones": "sesiones distintas",
    }
    for clave, motivo in motivos.items():
        prueba = next((p for p in resultado.pruebas if p.clave == clave), None)
        if prueba is None:
            fallas.append(f"la prueba `{clave}` no se corrió")
        elif motivo not in prueba.evidencia:
            fallas.append(f"`{clave}` pasó pero no por su motivo: se esperaba «{motivo}» y la "
                          f"evidencia dice «{prueba.evidencia}»")
    # La guarda de identidad y la de propiedad son dos, y se comprueba que ninguna cubra a la otra:
    # una sesión propia pero inexistente tiene que caer por identidad, no por propiedad.
    pasa, detalle = reanudar_con_guarda(sano, "sesion-propia-pero-inexistente",
                                        {"sesion-propia-pero-inexistente"})
    if pasa or "no reanudó" not in detalle:
        fallas.append("una sesión que el runner cree propia pero no existe no cayó por identidad: "
                      f"«{detalle}»")
    resultados.append(Resultado("E", "el `resume` pasa y sus tres negativos caen, cada uno por su "
                                     "propia guarda", fallas))

    # [F] Un bloqueo NO hace fallar al modo; lo que lo hace fallar es otra cosa.
    fallas = []
    todas_bloqueadas = [a for a in adjudicaciones if a.estado == "blocked"]
    recetas_bloqueadas = [por_id[a.receta_id] for a in todas_bloqueadas]
    if revisar_adjudicaciones(recetas_bloqueadas, todas_bloqueadas):
        fallas.append("un conjunto enteramente bloqueado produjo problemas de adjudicación: un "
                      "bloqueo es un resultado válido y no un fallo")
    if not revisar_adjudicaciones(recetas, adjudicaciones[:-1]):
        fallas.append("faltando una adjudicación el modo no reportó problema")
    inventada = Adjudicacion("pf-script-sano", "x", "blocked", "causa_inventada", "d",
                             (Prueba("p", True, "e"),))
    if not revisar_adjudicaciones([por_id["pf-script-sano"]], [inventada]):
        fallas.append("una causa fuera del conjunto cerrado no reportó problema")
    sin_pruebas = Adjudicacion("pf-script-sano", "x", "runnable", None, "d", ())
    if not revisar_adjudicaciones([por_id["pf-script-sano"]], [sin_pruebas]):
        fallas.append("una adjudicación sin ninguna prueba que la sostenga no reportó problema")
    contradictoria = Adjudicacion("pf-script-sano", "x", "runnable", "adaptador_ausente", "d",
                                  (Prueba("p", True, "e"),))
    if not revisar_adjudicaciones([por_id["pf-script-sano"]], [contradictoria]):
        fallas.append("una adjudicación lanzable con causa de bloqueo no reportó problema")
    resultados.append(Resultado("F", "un bloqueo no hace fallar al modo, y una adjudicación "
                                     "faltante, inventada, vacía o contradictoria sí", fallas))

    # [G] Cobertura: cada causa del conjunto cerrado fue ejercida, acumulada corriendo.
    fallas = []
    sin_ejercer = [c for c in CAUSAS_DE_BLOQUEO if c not in causas_ejercidas]
    inexistentes = sorted(causas_ejercidas - set(CAUSAS_DE_BLOQUEO))
    declaradas = manifest.get("causas_ejercidas") or []
    if sin_ejercer:
        fallas.append(f"causas de bloqueo sin ningún caso que las produzca: {sin_ejercer}")
    if inexistentes:
        fallas.append(f"se produjeron causas que no son del conjunto cerrado: {inexistentes}")
    if sorted(declaradas) != sorted(CAUSAS_DE_BLOQUEO):
        fallas.append(f"el manifest declara otras causas que el conjunto cerrado: {declaradas}")
    resultados.append(Resultado("G", f"las {len(CAUSAS_DE_BLOQUEO)} causas de bloqueo se "
                                     f"ejercieron, acumuladas corriendo", fallas))

    return _imprimir_controles("preflight", resultados)


# ---------------------------------------------------------------------------------------------
# El journal de anomalías.
#
# Lo escribe el runner, y su completitud NO se deriva de las entradas que el journal resulte tener:
# se deriva del manifest independiente de intentos. Un journal que se validara contra sí mismo daría
# verde omitiendo una anomalía, que es el conjunto encontrado validándose solo.
#
# La apertura va ANTES de cada operación que pueda impedir el bundle, no después de que algo salga
# mal: emitirla al fallar solo registraría las anomalías que el runner llegó a manejar, y una caída
# sin apertura previa no dejaría rastro.
# ---------------------------------------------------------------------------------------------

OPERACIONES_DEL_JOURNAL = (
    "captura_de_evidencia",
    "sanitizacion",
    "construccion_del_bundle",
    "recoleccion",
    "importacion_al_arbol",
)

CLASES_DE_ANOMALIA = (
    "fallo_previo_al_bundle",
    "sanitizacion_rechazada",
    "caida_durante_la_construccion",
    "recibo_de_frontera_invalido",
    "excepcion_del_recolector",
)


class AnomaliaDelRunner(Exception):
    """Lo que corta una operación y tiene que quedar en el journal antes de propagarse."""

    def __init__(self, clase: str, detalle: str) -> None:
        super().__init__(detalle)
        self.clase = clase
        self.detalle = detalle


class Journal:
    """El journal append-only de una corrida.

    `operacion` es un context manager a propósito: abrir y cerrar desde dos llamadas separadas deja
    que un `return` temprano se lleve el terminal, y una operación abierta sin terminal es
    exactamente el agujero que la reconciliación existe para detectar. Acá el terminal lo escribe el
    bloque al salir, pase lo que pase adentro.
    """

    def __init__(self, journal_id: str, preregistro_sha256: str, reloj: Reloj) -> None:
        self.journal_id = journal_id
        self.preregistro_sha256 = preregistro_sha256
        self.reloj = reloj
        self.entradas: list[dict[str, Any]] = []
        self._n = 0

    def _siguiente(self, prefijo: str) -> str:
        self._n += 1
        return f"{prefijo}-{self.journal_id}-{self._n}"

    @contextlib.contextmanager
    def operacion(self, operacion: str, sample_id: str, attempt_id: str):
        if operacion not in OPERACIONES_DEL_JOURNAL:
            raise ValueError(f"operación fuera del conjunto cerrado: {operacion!r}")
        entrada_id = self._siguiente("ap")
        self.entradas.append({
            "evento": "operacion_abierta",
            "entrada_id": entrada_id,
            "sample_id": sample_id,
            "attempt_id": attempt_id,
            "operacion": operacion,
            "sello": self.reloj.sello(),
        })
        try:
            yield
        except AnomaliaDelRunner as anomalia:
            self._terminar_con_anomalia(entrada_id, attempt_id, operacion, anomalia.clase,
                                        anomalia.detalle)
            raise
        except Exception as exc:  # una caída sin apertura previa no dejaría rastro: acá sí lo deja
            self._terminar_con_anomalia(entrada_id, attempt_id, operacion,
                                        "caida_durante_la_construccion",
                                        f"{type(exc).__name__} durante `{operacion}`")
            raise
        else:
            self.entradas.append({
                "evento": "operacion_terminada",
                "entrada_id": self._siguiente("tm"),
                "referencia_entrada_id": entrada_id,
                "resultado": "clean",
                "sello": self.reloj.sello(),
            })

    def _terminar_con_anomalia(self, entrada_id: str, attempt_id: str, operacion: str,
                               clase: str, detalle: str) -> None:
        self.entradas.append({
            "evento": "operacion_terminada",
            "entrada_id": self._siguiente("tm"),
            "referencia_entrada_id": entrada_id,
            "resultado": "anomaly",
            # El `candidate_id` es POR ANOMALÍA y no por corrida: una corrida puede producir varias
            # independientes, y reconciliarlas bajo el `run_id` de su contenedor deja perder una sin
            # diferencia visible.
            "candidate_id": f"cnd-{attempt_id}-{operacion}-{clase}",
            "clase": clase,
            "detalle": detalle,
            "sello": self.reloj.sello(),
        })

    def candidate_ids(self) -> list[str]:
        return [e["candidate_id"] for e in self.entradas if e.get("resultado") == "anomaly"]

    def como_json(self) -> dict[str, Any]:
        return {
            "version_schema": "1.0.0",
            "journal_id": self.journal_id,
            "preregistro_sha256": self.preregistro_sha256,
            "entradas": list(self.entradas),
        }


def reconciliar_journal(journal: dict[str, Any],
                        intentos_del_manifest: list[dict[str, Any]]) -> list[str]:
    """La completitud se deriva del manifest de intentos, nunca de las entradas del journal."""
    problemas: list[str] = []
    entradas = journal.get("entradas") or []
    aperturas = [e for e in entradas if e.get("evento") == "operacion_abierta"]
    terminales = [e for e in entradas if e.get("evento") == "operacion_terminada"]

    por_apertura: dict[str, list[dict[str, Any]]] = {}
    for terminal in terminales:
        por_apertura.setdefault(terminal.get("referencia_entrada_id"), []).append(terminal)

    for apertura in aperturas:
        cierres = por_apertura.get(apertura["entrada_id"], [])
        if len(cierres) != 1:
            problemas.append(f"la apertura `{apertura['entrada_id']}` "
                             f"({apertura['operacion']}) tiene {len(cierres)} resultados "
                             f"terminales y tiene que tener exactamente uno")
    huerfanos = [t["entrada_id"] for t in terminales
                 if t.get("referencia_entrada_id") not in {a["entrada_id"] for a in aperturas}]
    if huerfanos:
        problemas.append(f"resultados terminales sin apertura que los reclame: {huerfanos}")

    esperados = {(i["sample_id"], i["attempt_id"]) for i in intentos_del_manifest}
    vistos = {(a["sample_id"], a["attempt_id"]) for a in aperturas}
    faltan = sorted(esperados - vistos)
    if faltan:
        problemas.append(f"intentos del manifest sin ninguna operación abierta en el journal: "
                         f"{faltan}")
    sobran = sorted(vistos - esperados)
    if sobran:
        problemas.append(f"el journal abrió operaciones de intentos que el manifest no declara: "
                         f"{sobran}")

    for entrada in entradas:
        if entrada.get("resultado") == "anomaly" and entrada.get("clase") not in CLASES_DE_ANOMALIA:
            problemas.append(f"anomalía con clase `{entrada.get('clase')}`, fuera del conjunto "
                             f"cerrado")
    return problemas


# ---------------------------------------------------------------------------------------------
# Modo `--ejecutar-caso`: los dos adaptadores y sus obligaciones comunes.
#
# Las obligaciones son un conjunto cerrado y **el mismo para los dos**. Un predicado escrito sobre
# «el runner» dejaría fuera los seis casos que no ejecuta el script, así que lo que se comprueba es
# que cada adaptador implemente las tres y que la lista no dependa de cuál sea.
# ---------------------------------------------------------------------------------------------

OBLIGACIONES_DEL_ADAPTADOR = (
    "validar_preregistro",
    "correr_preflight",
    "emitir_bundle_canonico",
)

# La secuencia de apertura, en el orden que exige el criterio. `confirmacion_humana` es opcional:
# solo la llevan los puntos que requieren confirmación del usuario.
SECUENCIA_DE_APERTURA = (
    "validacion_de_hash_congelado",
    "preflight_de_receta",
    "confirmacion_humana",
    "despacho",
)


class ContextoDeEjecucion(NamedTuple):
    receta: dict[str, Any]
    sample_id: str
    attempt_id: str
    attempt_ordinal: int
    run_id: str
    preregistro_sha256: str
    arbol: Path
    recibo: dict[str, Any] | None
    recibos_usados: set[str]
    identidad_del_entorno: dict[str, Any]
    recibos: Path
    sesionador: Sesionador | None
    despachar_comando: Callable[[str, Path], tuple[int, str]]
    # Dónde se materializan el prompt y las salidas que el comando congelado nombra por marcador.
    # No es el árbol del worker: ahí el worker corre, y acá deja lo que produce.
    scratch: Path = Path(".")
    # El ancla del punto en la matriz: de ahí sale el prompt que el worker recibe.
    ancla_de_invocacion: str = ""
    # Se completa al materializar la entrada, antes de lanzar. Es una lista de un
    # elemento y no un campo suelto porque `NamedTuple` es inmutable y el bundle se
    # arma después del despacho.
    entrada: list[Path] = []
    # De dónde sale: `constatar_retiros_del_caso`, por la vía del adaptador. Tuvo default `False`
    # y NINGUNA construcción lo asignaba, así que `sin_red_ni_credenciales` no podía dar `pasa`
    # para ningún escritor —una guarda que no puede ponerse verde—. Lo destapó correr la cohorte
    # real: los read_only se eximen con `not_applicable` y tapaban el caso.
    retiros_comprobados: bool = False
    # El directorio de la corrida, donde se cosecha la evidencia. Lo conoce quien invoca el modo,
    # no `ejecutar_caso`, así que viaja por acá.
    destino: Path | None = None
    # Con qué se acredita la confirmación del usuario, para los puntos que la matriz declara que no
    # corren sin ella. Vacío significa que no hay ninguna, y entonces esos puntos se bloquean: es
    # el dato que el conductor aporta, no algo que el runner pueda deducir de su entorno.
    confirmacion: str = ""


class ResultadoDelDespacho(NamedTuple):
    terminal: str
    # SIEMPRE el texto de la salida del worker, en los dos adaptadores. Llevó el `salida_sha256`
    # del recibo en la rama de sesión, y como un hash hexadecimal no contiene rutas ni credenciales,
    # la sanitización de esos seis puntos pasaba en verde sin haber mirado nunca la evidencia.
    salida: str
    session_id: str | None
    modelo_o_familia: str | None
    # Lo que el recibo declaró al cerrarse. Se conserva aparte para poder comprobar que el texto
    # cosechado es el que el despacho acreditó, en vez de creerle a la ruta.
    salida_sha256_declarado: str | None = None


def _despachador_real(comando: str, arbol: Path) -> tuple[int, str]:
    return _correr(["sh", "-c", comando], cwd=arbol)


# --- Resolución de marcadores: del comando congelado al comando ejecutable ---------------------
#
# El comando de una receta CLI es el que su sede declara, con los marcadores `<…>` que esa sede
# escribe. Ejecutarlo tal cual no lanza nada: `sh` muere en el parseo, porque `<` es redirección.
# Medido sobre las 7 recetas de script: las 7 fallan con `syntax error near unexpected token '<'`
# y `codex` no llega a invocarse.
#
# La sustitución es SOLO para ejecutar. El bundle sigue registrando el comando **congelado** —lo
# hace `_invocacion_del_bundle`— y eso es deliberado: el literal de la receta es lo que identifica
# la invocación y es publicable, mientras que los valores concretos son del entorno de la corrida y
# llevarían rutas del host al artefacto final.
#
# Cada familia se resuelve por su significado, no por su nombre exacto, porque la misma cosa se
# llama distinto en cada sede: el árbol del worker es `working_dir` en una receta, `dir-código` en
# otra y `raíz-repo` en una tercera.

MARCADORES_DEL_ARBOL = ("working_dir", "dir-código", "raíz-repo")
MARCADORES_DEL_SCRATCH = ("S", "scratch")
# Los opcionales de la sede viajan entre corchetes —`[-m <MODEL>]`—, que tampoco es shell. Si no se
# fija un valor, el grupo entero se retira; dejarlo pondría un corchete literal en la línea.
MARCADORES_OPCIONALES = ("MODEL", "EFFORT")


# El encuadre que acompaña a la sección anclada. La sección DESCRIBE el punto de despacho; no le
# pide nada a nadie, así que un worker que solo la reciba contesta preguntando qué hacer con ella
# —medido: «¿Qué quieres que haga con este fragmento?»— y la corrida mide un encargo vacío. El
# encuadre la convierte en una tarea concreta e idéntica para los trece puntos, que es lo que hace
# comparables sus latencias.
#
# Va versionado y su identidad viaja en el bundle: dos corridas con el mismo comando y distinto
# encuadre no miden lo mismo, y sin declararlo serían indistinguibles.
ENCUADRE_ID = "encuadre-de-cohorte-1.0.0"
ENCUADRE = (
    "\n\n---\n\n"
    "Arriba está la sección que define este punto de despacho, tal como la recibe un agente en "
    "producción. Corré en solo lectura sobre el árbol: no edites archivos y no publiques nada.\n\n"
    "Devolvé un reporte breve que responda: (1) qué encargo concreto describe esa sección para el "
    "agente que la recibe, (2) qué entrada necesitarías para ejecutarlo y (3) qué producirías al "
    "terminar. No ejecutes el encargo: lo que se mide es que el despacho, el prompt congelado y la "
    "cosecha de la salida funcionen de punta a punta.\n\n"
    "No cites rutas absolutas del sistema de archivos en tu respuesta: nombrá los archivos por su "
    "ruta relativa al repositorio. Tu salida se publica.\n")


def _slug_de_heading(texto: str) -> str:
    """El fragmento con el que la matriz ancla una sección, desde el texto de su heading.

    Es la normalización de anclas de markdown: minúsculas, sin marcas de énfasis ni código, y todo
    lo que no sea alfanumérico colapsado a guiones. Se implementa acá y no se transcribe el
    fragmento en ningún lado: el ancla vive en la matriz y la sección en la skill, y este predicado
    es lo único que las une.
    """
    limpio = re.sub(r"[`*_]", "", texto).lower()
    limpio = unicodedata.normalize("NFKD", limpio)
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", limpio)).strip("-")


def prompt_desde_el_ancla(ancla: str, raiz: Path) -> tuple[str | None, str]:
    """El prompt de un punto es la SECCIÓN que su ancla nombra, tomada literal de su sede.

    Se resuelve en vez de transcribirse porque una copia del prompt en otro archivo diverge de la
    sección que el punto realmente usa, y entonces la cohorte mediría un encargo que ningún punto
    hace. El ancla es `<ruta>#<fragmento>`, y el fragmento se compara contra el slug de cada
    heading de esa sede.
    """
    ruta, _, fragmento = ancla.partition("#")
    sede = raiz / ruta
    if not sede.is_file():
        return None, f"la sede `{ruta}` del ancla no existe"
    lineas = sede.read_text(encoding="utf-8").splitlines()
    patron = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
    inicio: int | None = None
    nivel_de_inicio = 0
    for numero, linea in enumerate(lineas):
        coincide = patron.match(linea)
        if not coincide:
            continue
        nivel = len(coincide.group(1))
        if inicio is None:
            if _slug_de_heading(coincide.group(2)) == fragmento:
                inicio, nivel_de_inicio = numero, nivel
            continue
        if nivel <= nivel_de_inicio:
            return "\n".join(lineas[inicio:numero]).strip() + "\n", f"{ruta} § {fragmento}"
    if inicio is None:
        return None, f"`{ruta}` no tiene ninguna sección cuyo ancla sea `{fragmento}`"
    return "\n".join(lineas[inicio:]).strip() + "\n", f"{ruta} § {fragmento}"


def materializar_entrada(contexto: "ContextoDeEjecucion") -> tuple[Path | None, str]:
    """Escribe el prompt de la corrida en cada archivo de entrada que el comando lee.

    El comando congelado nombra su entrada por marcador —`<scratch>/prompt.txt`,
    `<raíz-repo>/.pr-review/<id>/prompt.txt`—; el runner tiene que dejarla escrita antes de lanzar,
    o `sh` muere en la redirección y el intento se bloquea por un archivo que faltaba, no por el
    transporte.
    """
    ancla = contexto.ancla_de_invocacion
    if not ancla:
        return None, "el punto no declara `ancla_de_invocacion` en la matriz"
    seccion, detalle = prompt_desde_el_ancla(ancla, RAIZ)
    if seccion is None:
        return None, detalle
    prompt = seccion + ENCUADRE

    comando = contexto.receta.get("comando") or ""
    ejecutable = resolver_comando(
        comando, arbol=contexto.arbol, scratch=contexto.scratch, run_id=contexto.run_id,
        ordinal=contexto.attempt_ordinal,
        admitidas=tuple(contexto.receta.get("variables_admitidas") or ()))
    # Las entradas son las rutas que el comando lee por `<` — lo que el worker recibe.
    entradas = re.findall(r"<\s*(\S+)", ejecutable.linea)
    escritas = []
    for relativa in entradas:
        destino = contexto.arbol / relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(prompt, encoding="utf-8")
        escritas.append(destino)
    if not escritas:
        return None, "el comando congelado no lee ninguna entrada por redirección"
    return escritas[0], (f"{detalle} + {ENCUADRE_ID} → {len(escritas)} entrada(s), "
                         f"{len(prompt)} chars")


class ComandoEjecutable(NamedTuple):
    """El comando ya resuelto, con lo que hizo falta resolverlo. Se reporta para que la sustitución
    quede auditable: un comando que se ejecuta sin decir con qué valores no es reproducible."""
    linea: str
    sustituciones: dict[str, str]
    opcionales_retirados: tuple[str, ...]
    sin_resolver: tuple[str, ...]


def resolver_comando(comando: str, *, arbol: Path, scratch: Path, run_id: str, ordinal: int,
                     admitidas: tuple[str, ...] = ()) -> ComandoEjecutable:
    """Sustituye los marcadores del comando congelado por los valores de esta corrida.

    Lo que queda sin resolver se decide contra `variables_admitidas` —la sede que declara cuáles
    son los marcadores— y NO buscando `<…>` en la línea ya sustituida: una redirección de entrada
    seguida de una de salida (`- < prompt.txt > salida.txt`) forma un par `<…>` que no es ningún
    marcador. Medido: ese falso positivo bloqueaba tres de las siete recetas, todas correctamente
    resueltas.
    """
    # Todo se sustituye RELATIVO al árbol, porque el comando corre con `cwd` ahí. Con rutas
    # absolutas el comando funciona igual, pero su salida capturada las arrastra y el pipeline de
    # sanitización rechaza la evidencia entera por `ruta_absoluta_del_host` — medido: el primer
    # caso murió así, sin llegar a producir bundle. Una ruta del host en la evidencia es
    # exactamente lo que ese pipeline existe para impedir, y acá la habría puesto el arnés.
    valores: dict[str, str] = {}
    for nombre in MARCADORES_DEL_ARBOL:
        valores[nombre] = "."
    relativo = scratch.relative_to(arbol).as_posix() if scratch.is_relative_to(arbol) else "."
    for nombre in MARCADORES_DEL_SCRATCH:
        valores[nombre] = relativo
    valores["id"] = run_id
    valores["N"] = str(ordinal)

    # Las rutas que la sede escribe como marcador —`<ruta/al/veredicto.txt>`— se materializan en el
    # scratch conservando su nombre de archivo: es lo que hace cosechable la salida desde disco.
    for marcador in set(re.findall(r"<([^<>]+)>", comando)):
        if "/" in marcador and marcador not in valores:
            valores[marcador] = f"{relativo}/{Path(marcador).name}"

    linea = comando
    retirados: list[str] = []
    for nombre in MARCADORES_OPCIONALES:
        patron = re.compile(r"\[[^\[\]]*<" + re.escape(nombre) + r">[^\[\]]*\]\s*")
        if patron.search(linea):
            linea = patron.sub("", linea)
            retirados.append(nombre)

    usados: dict[str, str] = {}
    for nombre, valor in valores.items():
        marcador = f"<{nombre}>"
        if marcador in linea:
            linea = linea.replace(marcador, valor)
            usados[nombre] = valor

    pendientes = tuple(sorted(n for n in admitidas
                              if n not in MARCADORES_OPCIONALES and f"<{n}>" in linea))
    return ComandoEjecutable(linea, usados, tuple(retirados), pendientes)


# --- Obligación 1: validar el pre-registro -----------------------------------------------------

def validar_preregistro(contexto: ContextoDeEjecucion) -> None:
    """Una corrida que se inicia sin el contenido congelado se rechaza en vez de ejecutarse."""
    sha = contexto.preregistro_sha256
    if not re.fullmatch(r"[0-9a-f]{64}", sha or ""):
        raise AnomaliaDelRunner("fallo_previo_al_bundle",
                                "el pre-registro no tiene un hash de contenido congelado: sin él "
                                "la corrida no sabe contra qué se pre-registró")


# --- Obligación 2: correr el preflight de la receta --------------------------------------------

def correr_preflight_de_la_receta(contexto: ContextoDeEjecucion) -> Adjudicacion:
    adjudicacion = preflightear(contexto.receta, recibos=contexto.recibos,
                                sesionador=contexto.sesionador)
    if adjudicacion.estado == "blocked":
        raise AnomaliaDelRunner("fallo_previo_al_bundle",
                                f"el preflight bloqueó el caso por `{adjudicacion.causa}` antes de "
                                f"ejecutarlo: {adjudicacion.detalle}")
    return adjudicacion


# --- Obligación 3: emitir el bundle canónico ---------------------------------------------------

# Las ocho comprobaciones del recibo. `dos_eventos` y `apertura_antes_del_retorno` son dos claves y
# no una: un recibo con un solo evento y uno con los sellos invertidos son dos formas distintas de
# fabricarlo, y colapsarlas dejaría que el ataque de una se leyera como cobertura de la otra.
CONTROLES_DEL_RECIBO = (
    "recibo_presente",
    "protocolo_de_produccion",
    "preregistro_coincide",
    "intento_coincide",
    "dos_eventos",
    "apertura_antes_del_retorno",
    "retorno_referencia_la_apertura",
    "recibo_no_reutilizado",
)


def revisar_recibo_de_frontera(recibo: dict[str, Any] | None,
                               contexto: ContextoDeEjecucion) -> list[str]:
    """Las siete comprobaciones del recibo. Cada una rechaza un modo distinto de fabricarlo."""
    if recibo is None:
        return ["[recibo_presente] el adaptador de sesión no trajo recibo de frontera: un bundle "
                "armado desde lo que la sesión declare de sí misma no acredita nada"]
    cuerpo = recibo.get("recibo") or {}
    problemas: list[str] = []

    if cuerpo.get("protocolo") != "produccion":
        problemas.append(f"[protocolo_de_produccion] el recibo es de protocolo "
                         f"`{cuerpo.get('protocolo')}`: los de conformance se emiten en el "
                         f"preflight, contra la propuesta de acta, y no valen para una corrida")
        return problemas

    if cuerpo.get("preregistro_sha256") != contexto.preregistro_sha256:
        problemas.append("[preregistro_coincide] el recibo cita otro pre-registro que el de esta "
                         "corrida")
    if (cuerpo.get("sample_id"), cuerpo.get("attempt_id")) != (contexto.sample_id,
                                                               contexto.attempt_id):
        problemas.append(f"[intento_coincide] el recibo acredita el intento "
                         f"`{cuerpo.get('sample_id')}/{cuerpo.get('attempt_id')}` y se está "
                         f"ejecutando `{contexto.sample_id}/{contexto.attempt_id}`")

    eventos = cuerpo.get("eventos") or []
    apertura = next((e for e in eventos if e.get("evento") == "dispatch_started"), None)
    retorno = next((e for e in eventos if e.get("evento") == "dispatch_returned"), None)
    if apertura is None or retorno is None:
        problemas.append("[dos_eventos] el recibo no tiene sus dos eventos: uno solo acredita un "
                         "despacho abierto o un retorno suelto, y un recibo escrito después del "
                         "hecho tiene exactamente esa forma")
    else:
        if apertura["sello"]["valor_ns"] > retorno["sello"]["valor_ns"]:
            problemas.append("[apertura_antes_del_retorno] el sello de la apertura es posterior al "
                             "del retorno: la apertura no se emitió antes de despachar")
        if retorno.get("referencia_evento_id") != apertura.get("evento_id"):
            problemas.append("[retorno_referencia_la_apertura] el retorno no referencia a la "
                             "apertura: son dos hechos sueltos y no un despacho")

    if cuerpo.get("recibo_id") in contexto.recibos_usados:
        problemas.append(f"[recibo_no_reutilizado] el recibo `{cuerpo.get('recibo_id')}` ya "
                         f"acreditó otro intento: reutilizarlo haría que dos intentos citen el "
                         f"mismo despacho")
    return problemas


def _dato_de_plataforma(valor: str | None) -> dict[str, Any]:
    """Lo que la plataforma no expone se escribe como no expuesto, nunca relleno."""
    if valor is None:
        return {"estado": "no_expuesto", "adjudicacion": "bloqueo"}
    return {"estado": "expuesto", "valor": valor}


def despachar(contexto: ContextoDeEjecucion,
              adjudicacion: Adjudicacion) -> ResultadoDelDespacho:
    """De dónde sale lo que pasó, según el adaptador.

    El script lo observa ejecutando; la sesión **no se observa a sí misma**: lo que pasó sale del
    recibo de frontera, que se emitió bajo autoridad del harness alrededor de la tool call.
    """
    del adjudicacion
    adaptador = contexto.receta.get("adaptador")
    if adaptador == "script":
        contexto.scratch.mkdir(parents=True, exist_ok=True)
        # La entrada se materializa para los puntos REALES, que son los que la matriz ancla. Un
        # corpus sintético corre recetas que no están en la matriz y no tiene sección que resolver:
        # ahí no hay prompt que dejar escrito y el comando se lanza tal cual, que es lo que esos
        # controles prueban. Exigirlo igual haría que la guarda descarrilara los controles ajenos
        # antes de que ejerzan lo suyo — medido: rompía `--autotest-journal` y `--autotest-adaptadores`.
        if contexto.ancla_de_invocacion:
            entrada, detalle_entrada = materializar_entrada(contexto)
            if entrada is None:
                raise AnomaliaDelRunner(
                    "entrada_no_materializable",
                    f"el prompt del punto no se pudo dejar escrito antes de lanzar: "
                    f"{detalle_entrada}")
            contexto.entrada.append(entrada)
        ejecutable = resolver_comando(
            contexto.receta["comando"], arbol=contexto.arbol, scratch=contexto.scratch,
            run_id=contexto.run_id, ordinal=contexto.attempt_ordinal,
            admitidas=tuple(contexto.receta.get("variables_admitidas") or ()))
        # Un marcador que sobrevive a la resolución NO se lanza: `sh` lo leería como redirección y
        # el intento moriría en el parseo, que es un fallo del arnés disfrazado de fallo del worker.
        if ejecutable.sin_resolver:
            raise AnomaliaDelRunner(
                "comando_sin_resolver",
                f"el comando congelado dejó marcadores que esta corrida no sabe sustituir: "
                f"{list(ejecutable.sin_resolver)}")
        codigo, salida = contexto.despachar_comando(ejecutable.linea, contexto.arbol)
        return ResultadoDelDespacho(
            "completado" if codigo == 0 else "fallido", salida, None, None)

    problemas = revisar_recibo_de_frontera(contexto.recibo, contexto)
    if problemas:
        raise AnomaliaDelRunner("recibo_de_frontera_invalido", " · ".join(problemas))
    cuerpo = contexto.recibo["recibo"]
    contexto.recibos_usados.add(cuerpo["recibo_id"])
    retorno = next(e for e in cuerpo["eventos"] if e["evento"] == "dispatch_returned")

    def valor(campo: str) -> str | None:
        dato = retorno[campo]
        return dato["valor"] if dato["estado"] == "expuesto" else None

    # La salida de una sesión no la observa el runner: la escribe el harness a un archivo y el
    # recibo lo apunta. Sin esa ruta no hay evidencia que cosechar —solo su hash—, y el intento se
    # bloquea en vez de manifestar un conjunto vacío como si fuera una corrida sin artefactos.
    declarado = retorno["salida_sha256"]
    relativa = retorno.get("salida_ruta_relativa")
    if not relativa:
        raise AnomaliaDelRunner(
            "salida_de_la_sesion_no_localizable",
            "el recibo declara el hash de la salida pero no dónde quedó escrita: sin la ruta, la "
            "evidencia del despacho no se puede cosechar ni sanitizar")
    archivo = RAIZ / relativa
    if not archivo.is_file():
        raise AnomaliaDelRunner(
            "salida_de_la_sesion_no_localizable",
            f"el recibo apunta a `{relativa}` y ahí no hay ningún archivo")
    texto = archivo.read_text(encoding="utf-8")
    if hashlib.sha256(archivo.read_bytes()).hexdigest() != declarado:
        raise AnomaliaDelRunner(
            "salida_de_la_sesion_discordante",
            f"el archivo `{relativa}` no es el que el recibo acreditó al cerrarse: su hash no "
            f"coincide con el declarado")
    return ResultadoDelDespacho(valor("terminal") or "no_expuesto", texto,
                                valor("session_id"), valor("modelo_o_familia"), declarado)


def _invocacion_del_bundle(contexto: ContextoDeEjecucion) -> dict[str, Any]:
    receta = contexto.receta
    directorio = _relativa(contexto.arbol)
    if receta.get("adaptador") == "script":
        invocacion: dict[str, Any] = {"tipo": "comando", "comando_literal": receta["comando"],
                                      "directorio_de_trabajo": directorio}
        # El hash es del prompt que el worker REALMENTE recibió —sección anclada + encuadre—, leído
        # del archivo escrito y no recompuesto: recomponerlo acá permitiría que difiera de lo que
        # se despachó sin que nada lo note.
        materializada = contexto.entrada[0] if contexto.entrada else None
        if materializada is not None and materializada.is_file():
            invocacion["prompt_sha256"] = hashlib.sha256(materializada.read_bytes()).hexdigest()
            invocacion["encuadre_id"] = ENCUADRE_ID
        return invocacion
    apertura = next(e for e in contexto.recibo["recibo"]["eventos"]
                    if e["evento"] == "dispatch_started")
    return {"tipo": "accion", "accion_literal": receta["accion"],
            "prompt_sha256": apertura["prompt_sha256"], "directorio_de_trabajo": directorio}


def reejecutar_inventario_de_egreso() -> dict[str, Any]:
    """Reejecuta la regla de descubrimiento EN ESTA CORRIDA, para compararla contra la congelada.

    Es lo que T21 pide de cada corrida. El campo llevaba `superficies` vacío con un
    `inventario_sha256` que era el de la lista de archivos de credencial —otro dato bajo el nombre
    de éste—, así que lo que el bundle traía era una declaración de no publicación y no una
    auditoría: `--aislamiento` bloqueaba a los cinco escritores por `evidencia_declarativa`.

    Va por `--solo-inventario` y no por el recibo completo, que EJECUTA los mutantes de publicación
    —diecisiete intentos contra el canary y un `git push`—: una corrida que se acredita sin red no
    puede abrirla para probar que no la tiene. El instrumento se invoca como proceso aparte, igual
    que en el resto: la regla no se reimplementa acá.
    """
    with tempfile.TemporaryDirectory(prefix="egreso-de-corrida-") as tmp:
        destino = Path(tmp) / "inventario.json"
        comando = [sys.executable, str(RUTA_INSTRUMENTO),
                   "--recibo-de-egreso", "--solo-inventario", "--salida", str(destino)]
        try:
            proc = subprocess.run(comando, capture_output=True, text=True, timeout=600)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise AnomaliaDelRunner("inventario_de_egreso_no_reejecutable",
                                    f"el descubrimiento no pudo correr: {type(exc).__name__}")
        if proc.returncode != 0:
            cola = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
            raise AnomaliaDelRunner(
                "inventario_de_egreso_no_reejecutable",
                f"el descubrimiento falló (exit {proc.returncode}): {' | '.join(cola)}")
        documento, error = _cargar_json(destino)
        if error:
            raise AnomaliaDelRunner("inventario_de_egreso_no_reejecutable", error)
        return dict(documento["inventario_de_egreso"])


def clasificar_reporte_del_worker(contexto: ContextoDeEjecucion,
                                  resultado: ResultadoDelDespacho,
                                  artefactos: list[dict[str, Any]]) -> dict[str, Any]:
    """Qué llegó del worker, contra lo que su receta declara esperar.

    El campo iba fijo en `ausente`, y el vocabulario cuenta `ausente` como reporte inválido a
    propósito (`intento-con-reporte-invalido`). Con las trece corridas así, el baseline publicaba
    `tasa-de-salidas-invalidas = 1.0`: que el ecosistema entero produce salidas inválidas, cuando lo
    que pasaba es que nadie evaluaba ninguna. **Ausente e inválido no son lo mismo**, y la
    diferencia es un número publicado.

    El criterio sale de `salida_esperada.clase` de la receta y no de un formato inventado acá: las
    recetas declaran qué esperan —un archivo en una ruta, o el reporte que la sesión devuelve— y no
    un esquema del contenido. `interpretable` dice que llegó lo que la receta espera y se puede
    leer, no que alguien lo haya interpretado.
    """
    clase = (contexto.receta.get("salida_esperada") or {}).get("clase")
    del_scratch = [a for a in artefactos if a["ruta_relativa"].startswith("evidencia/scratch/")]
    if clase == "archivo":
        # Lo que la receta espera es un archivo que el comando nombra por marcador. El stdout no lo
        # reemplaza: un worker que escribe en la consola lo que debía dejar en disco no cumplió su
        # contrato de salida, y contarlo como llegado taparía justamente ese modo de fallar.
        candidatos = [a for a in del_scratch if a["bytes"] > 0]
        if not candidatos:
            return {"estado": "ausente",
                    "causa": "la receta espera un archivo de salida y el worker no dejó ninguno "
                             "con contenido en el scratch de la corrida"}
        elegido = max(candidatos, key=lambda a: a["bytes"])
    else:
        salida = next((a for a in artefactos
                       if a["ruta_relativa"] == NOMBRE_DE_LA_SALIDA), None)
        if salida is None or salida["bytes"] == 0:
            return {"estado": "ausente",
                    "causa": "el despacho no devolvió ninguna salida que interpretar"}
        elegido = salida
    return {"estado": "interpretable",
            "ruta_relativa": elegido["ruta_relativa"],
            "sha256": elegido["sha256"]}


def construir_bundle(contexto: ContextoDeEjecucion, adjudicacion: Adjudicacion,
                     resultado: ResultadoDelDespacho, eventos: list[dict[str, Any]],
                     journal: Journal, ventana: dict[str, str],
                     antes: Snapshot, despues: Snapshot,
                     artefactos: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Arma el bundle canónico desde lo capturado, nunca desde lo que el worker declare."""
    del adjudicacion
    transporte, _ = transporte_efectivo(contexto.receta)
    punto = contexto.receta["punto_de_despacho"]
    evento_terminal = next((e for e in eventos if e["tipo"] == "estado_terminal_de_trabajo"), None)
    trabajo_id = f"trb-{contexto.run_id}"
    if evento_terminal is not None:
        estado_terminal: dict[str, Any] = {"estado": "comprobado",
                                           "evento_terminal_id": evento_terminal["evento_id"]}
    else:
        # Sin evento que lo acredite no hay terminal que registrar, y apuntar a otro evento para
        # llenar el campo es justo lo que la unión disjunta impide.
        estado_terminal = {"estado": "no_comprobable",
                           "causa": "la plataforma no expuso el terminal del trabajo delegado"}
    clase_de_recurso = "proceso" if contexto.receta["adaptador"] == "script" else "sesion"
    recurso_id = f"rec-{contexto.run_id}"
    bundle: dict[str, Any] = {
        "version_schema": "1.0.0",
        "run_id": contexto.run_id,
        "sample_id": contexto.sample_id,
        "attempt_id": contexto.attempt_id,
        "attempt_ordinal": contexto.attempt_ordinal,
        "preregistro_sha256": contexto.preregistro_sha256,
        "punto_de_despacho": punto,
        "skill": _skill_del_punto(punto),
        "familia_de_rol": _familia_del_punto(punto),
        "transporte": transporte,
        "adaptador": contexto.receta["adaptador"],
        "invocacion": _invocacion_del_bundle(contexto),
        "ventana_de_pared_utc": ventana,
        # El estado sale del terminal observado y no de haber llegado hasta acá. Un intento cuyo
        # despacho no completó es un intento **bloqueado canónico**: se conserva append-only y no
        # se descarta, porque toda muestra pre-registrada necesita al menos un intento.
        "estado_del_intento": (
            {"resultado": "completado"} if resultado.terminal == "completado" else
            {"resultado": "bloqueado",
             "causa_de_bloqueo": f"el despacho terminó en `{resultado.terminal}` y no completó"}),
        "eventos": eventos,
        "reporte_del_worker": clasificar_reporte_del_worker(contexto, resultado,
                                                            list(artefactos or [])),
        "veredicto_de_conformance": {
            "resultado": "no_evaluable",
            "causa": "sin reporte interpretable no hay qué comparar contra el contrato",
        },
        "trabajos_delegados": [{
            "trabajo_delegado_id": trabajo_id,
            "estado_terminal": estado_terminal,
            "recursos_ids": [recurso_id],
        }],
        "artefactos_producidos": list(artefactos or []),
        "recursos": [{
            "recurso_id": recurso_id,
            "clase": clase_de_recurso,
            "life_state": ("terminado_comprobado" if resultado.terminal == "completado"
                           else "cese_no_comprobable"),
            "ownership_state": "sin_transferir",
            "evidencia_de_cese": (
                "el proceso del despacho devolvió su código de salida y dejó de existir"
                if clase_de_recurso == "proceso" else
                "el recibo de frontera registra el terminal que la plataforma expuso al retorno"),
        }],
        "pruebas_de_aislamiento": capturar_pruebas_de_aislamiento(
            permiso_efectivo_del_punto(punto), antes, despues, contexto.retiros_comprobados),
        "inventario_de_egreso_reejecutado": reejecutar_inventario_de_egreso(),
        "identidad_del_entorno": contexto.identidad_del_entorno,
        "pipeline_de_sanitizacion": {
            "orden_aplicado": list(ORDEN_DE_SANITIZACION),
            # El hash del MANIFEST ORDENADO de la evidencia, que es lo que AC-41 pide y lo que el
            # instrumento recomputa. Llevó `_sha256(resultado.salida)` —el hash de la salida
            # cruda—: un dato distinto bajo el mismo nombre, que coincidía con el correcto solo
            # cuando la salida era vacía, porque ahí los dos son el sha256 de la cadena vacía.
            "manifest_sha256": hashlib.sha256(
                manifest_canonico(list(artefactos or []))).hexdigest(),
        },
        "journal_candidate_ids": journal.candidate_ids(),
    }
    if contexto.recibo is not None:
        cuerpo = contexto.recibo["recibo"]
        bundle["recibo_de_frontera"] = {
            "recibo_id": cuerpo["recibo_id"],
            "protocolo": cuerpo["protocolo"],
            "recibo_sha256": _sha256(json.dumps(contexto.recibo, ensure_ascii=False,
                                                sort_keys=True)),
        }
        bundle["identidad_del_entorno"] = dict(contexto.identidad_del_entorno)
        bundle["identidad_del_entorno"]["ejecutor"] = {
            "perfil_esperado": contexto.identidad_del_entorno["ejecutor"]["perfil_esperado"],
            "instancia_efectiva": _dato_de_plataforma(resultado.session_id),
        }
    return bundle


ORDEN_DE_SANITIZACION = (
    "captura",
    "normalizacion_de_rutas",
    "validacion_y_escaneo",
    "canonicalizacion_y_hash",
    "recoleccion",
    "versionado",
)


class Snapshot(NamedTuple):
    """Lo que se mira antes y después de correr, para poder compararlo.

    Se captura con comandos y no se declara: la evidencia de que las refs no cambiaron es haberlas
    leído dos veces, no afirmarlo.
    """
    refs: str
    objetos: str
    head_del_original: str
    sucio_del_original: str


def tomar_snapshot(arbol: Path) -> Snapshot:
    return Snapshot(
        refs=_correr(["git", "-C", str(arbol), "for-each-ref",
                      "--format=%(refname) %(objectname)"])[1],
        objetos=_correr(["git", "-C", str(arbol), "count-objects", "-v"])[1],
        head_del_original=_correr(["git", "-C", str(RAIZ), "rev-parse", "HEAD"])[1],
        sucio_del_original=_correr(["git", "-C", str(RAIZ), "status", "--porcelain"])[1],
    )


def _prueba(identico: bool, que_se_comparo: str) -> dict[str, Any]:
    return {"resultado": "pasa" if identico else "falla", "evidencia": que_se_comparo}


def capturar_pruebas_de_aislamiento(permiso_efectivo: str, antes: Snapshot, despues: Snapshot,
                                    retiros_comprobados: bool) -> dict[str, Any]:
    """Las tres pruebas, capturadas por snapshot.

    Un punto de solo lectura registra `not_applicable` con su permiso, que es lo único que el
    contrato admite para esquivarlas — y un escritor no puede escribirlo, así que falsear el
    permiso para eximirse deja rastro. Un escritor las lleva con su evidencia comparada.

    Capturar no es juzgar: el runner deja las tres con lo que observó, y quien decide si eso
    alcanza es el modo de aislamiento, que es otra capacidad.
    """
    if permiso_efectivo == "read_only":
        exenta = {
            "resultado": "not_applicable",
            "causa": "el permiso efectivo que declara la matriz para este punto es de solo "
                     "lectura, así que no hay escritura de la que probar el aislamiento",
            "permiso_efectivo": "read_only",
        }
        return {clave: dict(exenta) for clave in
                ("refs_y_objetos_identicos", "sin_red_ni_credenciales", "arbol_original_intacto")}

    return {
        "refs_y_objetos_identicos": _prueba(
            antes.refs == despues.refs and antes.objetos == despues.objetos,
            "refs y conteo de objetos del árbol desechable, leídos antes y después de la corrida "
            "y comparados"),
        "sin_red_ni_credenciales": _prueba(
            retiros_comprobados,
            "constancias del provisionamiento: el sandbox pedido por el comando retira la red y "
            "el entorno del hijo no alcanza credenciales"),
        "arbol_original_intacto": _prueba(
            antes.head_del_original == despues.head_del_original
            and antes.sucio_del_original == despues.sucio_del_original,
            "HEAD y estado sin commitear del árbol original, leídos antes y después y comparados"),
    }


def permiso_efectivo_del_punto(punto: str) -> str:
    return _campo_del_punto(punto, "escritura_agregada")


def _campo_del_punto(punto: str, campo: str) -> str:
    """Lee un campo del punto en la matriz. No hay valor por omisión a propósito.

    Un punto que la matriz no tiene es un bundle que declara una skill o una familia inventadas, y
    el schema las aceptaría si por casualidad caen dentro del enum. La ausencia se registra como
    anomalía en vez de rellenarse.
    """
    matriz, error = _cargar_json(RUTA_MATRIZ_DESPACHOS)
    if error:
        raise AnomaliaDelRunner("fallo_previo_al_bundle", f"no se pudo leer la matriz: {error}")
    for p in matriz.get("puntos") or []:
        if p.get("id") == punto:
            valor = p.get(campo)
            valor = valor.get("valor") if isinstance(valor, dict) else valor
            if isinstance(valor, str):
                return valor
            break
    raise AnomaliaDelRunner("fallo_previo_al_bundle",
                            f"la matriz no declara `{campo}` para el punto `{punto}`")


def _skill_del_punto(punto: str) -> str:
    return _campo_del_punto(punto, "skill")


def _familia_del_punto(punto: str) -> str:
    return _campo_del_punto(punto, "rol")


class Adaptador(NamedTuple):
    nombre: str
    obligaciones: tuple[str, ...]
    de_donde_sale_lo_que_paso: str


ADAPTADORES = (
    Adaptador("script", OBLIGACIONES_DEL_ADAPTADOR,
              "de ejecutar el comando congelado y observar su resultado"),
    Adaptador("sesion_de_agente", OBLIGACIONES_DEL_ADAPTADOR,
              "del recibo de frontera, emitido alrededor de la tool call bajo autoridad del "
              "harness: la sesión no se autoatestigua"),
)


def ejecutar_caso(contexto: ContextoDeEjecucion,
                  journal: Journal, reloj: Reloj) -> tuple[dict[str, Any] | None, list[str]]:
    """Corre un caso y devuelve su bundle, o los problemas que lo impidieron.

    Las tres obligaciones corren en orden y cada una abre su operación en el journal ANTES de
    intentarla. Una anomalía corta la ejecución y ya quedó registrada: el bundle ausente lo detecta
    el manifest, y el defecto que lo causó ya está en el journal aunque después se corrija.
    """
    eventos: list[dict[str, Any]] = []
    inicio = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    problemas: list[str] = []

    def evento(tipo: str, detalle: str | None = None) -> None:
        registro = {"evento_id": f"evt-{contexto.run_id}-{len(eventos) + 1}", "tipo": tipo,
                    "sello": reloj.sello()}
        if detalle:
            registro["detalle"] = detalle
        eventos.append(registro)

    try:
        with journal.operacion("captura_de_evidencia", contexto.sample_id, contexto.attempt_id):
            antes = tomar_snapshot(contexto.arbol)
            validar_preregistro(contexto)
            evento("validacion_de_hash_congelado")
            adjudicacion = correr_preflight_de_la_receta(contexto)
            evento("preflight_de_receta")
            # La confirmación va DONDE LA MATRIZ LA PIDE y en su lugar de la secuencia, entre el
            # preflight y el despacho. Nunca se emitía, así que cuatro puntos que no corren sin
            # confirmación quedaban clasificados `automatizable` —el estrato sale de este evento— y
            # un intento sin ella se estratificaba como si no hubiera hecho falta. Sin acreditación
            # el intento BLOQUEA, que es lo que el juicio de estratos ya exigía: la ausencia del
            # evento no es prueba de que la confirmación sobraba.
            if exige_confirmacion_del_usuario(contexto.receta["punto_de_despacho"]):
                if not contexto.confirmacion:
                    raise AnomaliaDelRunner(
                        "confirmacion_no_acreditada",
                        f"la matriz declara que `{contexto.receta['punto_de_despacho']}` no corre "
                        f"sin confirmación del usuario, y esta corrida no trae ninguna que "
                        f"acreditarla: el intento se bloquea en vez de estratificarse como "
                        f"automatizable")
                evento("confirmacion_humana", contexto.confirmacion)
            resultado = despachar(contexto, adjudicacion)
            evento("despacho")
            evento("estado_terminal_de_trabajo")
            eventos[-1]["trabajo_delegado_id"] = f"trb-{contexto.run_id}"
            evento("resultado_utilizable")
            # La cosecha va DENTRO de la captura y antes del snapshot de cierre: lo que el worker
            # dejó en el scratch se lee mientras el árbol desechable todavía existe.
            crudos = recolectar_crudos(contexto, resultado)
            despues = tomar_snapshot(contexto.arbol)

        with journal.operacion("sanitizacion", contexto.sample_id, contexto.attempt_id):
            # Toda la evidencia, no solo la salida: el pipeline canónico normaliza y escanea antes
            # de hashear, y un artefacto del scratch que entrara sin pasar por acá haría que el
            # `manifest_sha256` identificara un crudo que nunca se versiona.
            sanitizados = [(relativa, sanitizar(contenido)) for relativa, contenido in crudos]

        with journal.operacion("construccion_del_bundle", contexto.sample_id,
                               contexto.attempt_id):
            artefactos = escribir_evidencia(contexto.destino, sanitizados)
            ventana = {"inicio": inicio,
                       "fin": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            bundle = construir_bundle(contexto, adjudicacion, resultado, eventos, journal, ventana,
                                      antes, despues, artefactos)
    except AnomaliaDelRunner as anomalia:
        return None, [f"[{anomalia.clase}] {anomalia.detalle}"]

    problemas.extend(revisar_secuencia_de_apertura(eventos))
    return bundle, problemas


# Los patrones que la sanitización rechaza. Una anomalía es justo el momento en que es fácil volcar
# un traceback crudo con el entorno adentro, así que el rechazo es del pipeline y no del criterio de
# quien escribe.
PATRONES_PROHIBIDOS = (
    (r"ghp_[A-Za-z0-9]{16,}", "un token de GitHub"),
    (r"sk-[A-Za-z0-9]{20,}", "una clave de API"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "una clave privada"),
)

# Las rutas del host se NORMALIZAN, no se rechazan, y la diferencia es de clase. Un token o una
# clave privada no tienen forma segura de conservarse: si aparecen, la evidencia se descarta. Una
# ruta del host es un dato de ubicación, y lo que hay que impedir es que viaje al artefacto
# publicado, no que la corrida exista.
#
# Rechazarla convertía la publicabilidad en un sorteo sobre la redacción del worker. Medido: al
# encuadre que le pide decir qué entrada necesitaría, un worker contestó citando
# `/Users/<usuario>/.agents/skills/...` cuatro veces, y la corrida entera se perdió — la misma
# receta había pasado minutos antes, porque esa vez contestó otra cosa. Una cohorte que depende de
# eso no mide el transporte.
PATRONES_DE_RUTA_DEL_HOST = (
    (r"/Users/[^/\s]+/", "<HOME>/"),
    (r"/home/[^/\s]+/", "<HOME>/"),
    (r"[A-Za-z]:\\\\Users\\\\[^\\\\\s]+\\\\", "<HOME>\\\\"),
)


def sanitizar(texto: str) -> str:
    """Normaliza las rutas del host y rechaza lo que no puede conservarse de ninguna forma."""
    for patron, marcador in PATRONES_DE_RUTA_DEL_HOST:
        texto = re.sub(patron, marcador, texto)
    for patron, que_es in PATRONES_PROHIBIDOS:
        if re.search(patron, texto):
            raise AnomaliaDelRunner("sanitizacion_rechazada",
                                    f"la salida capturada contiene {que_es}: la evidencia se "
                                    f"rechaza en vez de importarse con el secreto adentro")
    return texto


# Dónde queda la evidencia dentro del directorio de la corrida. El bundle y el journal son el
# juicio y el registro; esto es lo que el worker produjo.
NOMBRE_DE_LA_SALIDA = "evidencia/salida-del-worker.txt"

# El formato del manifest es CONTRATO —AC-41 lo fija y el instrumento lo recomputa para juzgarlo—,
# y por eso está acá TRANSCRITO y no importado: el runner produce la evidencia y el instrumento
# decide si vale, y compartir el código borraría la separación que hace que ese juicio signifique
# algo. Es el mismo dato declarado en dos lugares que `ORDEN_DE_SANITIZACION`, con el mismo dueño
# (T23/T25). Lo que sostiene la transcripción es que el juez la recomputa: si las dos
# serializaciones divergen, `--sanitizar` corta por `manifest_sha256_discordante` — que es
# exactamente cómo se descubrió que este número venía siendo el de otra cosa.
def manifest_canonico(artefactos: list[dict[str, Any]]) -> bytes:
    filas = sorted((str(a["ruta_relativa"]), int(a["bytes"]), str(a["sha256"]))
                   for a in artefactos)
    return "".join(f"{ruta}\t{tamano}\t{sha}\n" for ruta, tamano, sha in filas).encode("utf-8")


def recolectar_crudos(contexto: ContextoDeEjecucion,
                      resultado: ResultadoDelDespacho) -> list[tuple[str, str]]:
    """La evidencia cruda del intento: (ruta dentro de la corrida, contenido), sin sanitizar.

    Son dos fuentes y las dos hacen falta. La salida del worker es lo que el despacho devolvió; los
    archivos del scratch son los que el comando congelado nombra por marcador y el worker escribió
    ahí. El scratch vive DENTRO del árbol desechable, así que todo lo que no se coseche en este
    paso se va con él: sin esto el manifest hashea un conjunto vacío y el bundle acredita una
    evidencia que ya no existe en ninguna parte.
    """
    crudos = [(NOMBRE_DE_LA_SALIDA, resultado.salida)]
    # El scratch se barre SOLO en una corrida que captura a disco y tiene el suyo propio. El
    # default del contexto es `.` —los controles no capturan—, y sin esta condición el barrido
    # recorría el repositorio entero: la primera corrida murió por `sanitizacion_rechazada` al
    # encontrar un token de GitHub en un archivo que no era evidencia de nada.
    cosechable = (contexto.destino is not None
                  and contexto.scratch != contexto.arbol
                  and contexto.scratch.is_dir())
    if cosechable:
        for archivo in sorted(contexto.scratch.rglob("*")):
            if not archivo.is_file():
                continue
            try:
                contenido = archivo.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                # Lo que no es texto no se puede escanear, y publicar sin escanear es justo lo que
                # AC-41 impide. Queda fuera del manifest en vez de entrar sin haberse mirado.
                continue
            relativa = archivo.relative_to(contexto.scratch).as_posix()
            crudos.append((f"evidencia/scratch/{relativa}", contenido))
    return crudos


def escribir_evidencia(destino: Path | None,
                       sanitizados: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Escribe la evidencia ya sanitizada y devuelve su manifest ordenado.

    Sin destino —los controles, que no capturan a disco— el manifest se computa igual: así el
    camino que produce el número se ejerce en los autotests y no solo en la cohorte real.
    """
    artefactos: list[dict[str, Any]] = []
    for relativa, contenido in sanitizados:
        crudo = contenido.encode("utf-8")
        if destino is not None:
            archivo = destino / relativa
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(crudo)
        artefactos.append({"ruta_relativa": relativa, "bytes": len(crudo),
                           "sha256": hashlib.sha256(crudo).hexdigest()})
    return sorted(artefactos, key=lambda a: (a["ruta_relativa"], a["bytes"], a["sha256"]))


def revisar_secuencia_de_apertura(eventos: list[dict[str, Any]]) -> list[str]:
    """La secuencia de apertura va en su orden y con sellos monótonamente crecientes."""
    problemas: list[str] = []
    presentes = [e for e in eventos if e["tipo"] in SECUENCIA_DE_APERTURA]
    orden_esperado = [t for t in SECUENCIA_DE_APERTURA
                      if any(e["tipo"] == t for e in presentes)]
    orden_visto = [e["tipo"] for e in presentes]
    if orden_visto != orden_esperado:
        problemas.append(f"la secuencia de apertura salió en el orden {orden_visto} y el criterio "
                         f"exige {orden_esperado}")
    obligatorios = [t for t in SECUENCIA_DE_APERTURA if t != "confirmacion_humana"]
    faltan = [t for t in obligatorios if t not in orden_visto]
    if faltan:
        problemas.append(f"faltan eventos de la secuencia de apertura: {faltan}")
    sellos = [e["sello"]["valor_ns"] for e in eventos]
    if sellos != sorted(sellos):
        problemas.append("los sellos no son monótonamente crecientes: un evento fuera de orden se "
                         "rechaza, no se reordena")
    for e in eventos:
        if e["sello"]["fuente"] != "reloj_monotonico_del_harness":
            problemas.append(f"el evento `{e['evento_id']}` no se selló con el reloj del harness")
    return problemas


def commit_que_fija_el_preregistro() -> tuple[str, str | None]:
    """El último commit que tocó `scripts/preregistro-fase-0.json`, o el motivo de no resolverlo.

    El observable está TRANSCRITO a propósito y no se comparte con el instrumento, que resuelve el
    mismo commit por su cuenta para juzgar la anterioridad: dos implementaciones del mismo número
    pueden divergir, y esa divergencia es justamente lo que el juez tiene que poder ver. Si
    compartieran código, un productor equivocado arrastraría al juez y la comprobación no podría
    ponerse roja.

    De dónde sale que esto haga falta: `preregistration_commit` llevaba el HEAD del momento de la
    corrida, que es el dato de `code_commit` bajo otro nombre. Coincidía con el correcto mientras el
    congelamiento fuera el último commit del árbol —que es lo que pasa cuando se congela y se corre
    seguido—, así que D-18 declaraba dos campos distintos y ningún bundle llegó a expresarlos.
    """
    codigo, salida = _correr(["git", "-C", str(RAIZ), "log", "-1", "--format=%H", "--",
                              RUTA_PREREGISTRO_FASE_0.relative_to(RAIZ).as_posix()])
    if codigo != 0:
        return "", f"git no pudo resolver el congelamiento: {salida}"
    if not salida.strip():
        return "", ("`scripts/preregistro-fase-0.json` no tiene ningún commit que lo fije: una "
                    "corrida no puede declararse posterior a un congelamiento que no ocurrió")
    return salida.strip()[:40], None


def identidad_del_entorno_de_hoy(preregistration_commit: str = "") -> dict[str, Any]:
    """La identidad efectiva del entorno, leída y no declarada."""
    _, commit = _correr(["git", "-C", str(RAIZ), "rev-parse", "HEAD"])
    _, sucio = _correr(["git", "-C", str(RAIZ), "status", "--porcelain"])
    _, version_cli = _correr(["codex", "--version"])
    # Sin congelamiento resoluble el campo queda vacío y el schema rechaza el bundle. Rellenarlo con
    # el HEAD sería inventar el dato, que es exactamente el defecto que este parámetro repara.
    if not preregistration_commit:
        preregistration_commit, _ = commit_que_fija_el_preregistro()
    return {
        "code_commit": commit[:40],
        "preregistration_commit": preregistration_commit,
        "arbol_limpio": not sucio,
        "matriz_sha256": _sha256_de(RUTA_MATRIZ_DESPACHOS),
        "instrumento_sha256": _sha256_de(RUTA_INSTRUMENTO),
        "runner_sha256": _sha256_de(Path(__file__)),
        "version_cli": version_cli or "no expuesta",
        "version_runtime": f"python {sys.version_info.major}.{sys.version_info.minor}",
        "hooks": [],
        "ejecutor": {
            "perfil_esperado": "runner de la cohorte, sin hooks de sesión",
            "instancia_efectiva": _dato_de_plataforma("runner-cohorte"),
        },
        "eventos_de_intervencion_humana": [],
        "modelo": {
            "solicitado": _dato_de_plataforma(None),
            "efectivo": _dato_de_plataforma(None),
        },
    }


def _sha256_de(ruta: Path) -> str:
    try:
        return hashlib.sha256(ruta.read_bytes()).hexdigest()
    except OSError:
        return "0" * 64


def _ancla_del_punto(punto: str) -> str:
    """El `ancla_de_invocacion` que la matriz declara para este punto."""
    matriz, error = _cargar_json(RUTA_MATRIZ_DESPACHOS)
    if error:
        return ""
    for entrada in matriz.get("puntos") or []:
        ident = entrada.get("id")
        ident = ident["valor"] if isinstance(ident, dict) and "valor" in ident else ident
        if ident == punto:
            ancla = entrada.get("ancla_de_invocacion")
            return ancla["valor"] if isinstance(ancla, dict) and "valor" in ancla else (ancla or "")
    return ""


def modo_ejecutar_caso(args: argparse.Namespace) -> int:
    receta_id = getattr(args, "receta", None)
    if not receta_id:
        print("FALLA  `--ejecutar-caso` necesita `--receta <receta_id>`", file=sys.stderr)
        return 2
    recetas_json, error = _cargar_json(RUTA_RECETAS)
    if error:
        print(f"FALLA  {error}")
        return 1
    receta = next((r for r in recetas_json["recetas"] if r["receta_id"] == receta_id), None)
    if receta is None:
        print(f"FALLA  no hay ninguna receta `{receta_id}` en {_relativa(RUTA_RECETAS)}")
        return 1

    sample_id = getattr(args, "muestra", None) or f"mst-{receta['punto_de_despacho']}-r1"
    ordinal = int(getattr(args, "intento", None) or 1)
    attempt_id = f"int-{sample_id}-a{ordinal}"
    run_id = getattr(args, "ejecutar_caso", None) or f"run-{attempt_id}"
    arbol = _ruta_absoluta(getattr(args, "arbol", None) or ".")
    salida = _ruta_absoluta(getattr(args, "salida", None) or "scripts/corridas-fase-0")
    crudo_recibos = getattr(args, "recibos", None)
    recibos = _ruta_absoluta(crudo_recibos) if crudo_recibos else DIR_RECIBOS_FASE_0

    preregistro_sha256 = getattr(args, "preregistro", None) or ""
    recibo = None
    crudo_recibo = getattr(args, "recibo", None)
    if crudo_recibo:
        recibo, error = _cargar_json(_ruta_absoluta(crudo_recibo))
        if error:
            print(f"FALLA  {error}")
            return 1

    reloj, error = cargar_reloj(receta["adaptador"])
    if reloj is None:
        print(f"FALLA  {error}")
        return 1

    # La corrida real resuelve su congelamiento ANTES de construir nada y corta acá si no puede: un
    # bundle que no sabe decir contra qué congelamiento corrió no es una observación de esta cohorte.
    congelamiento, error = commit_que_fija_el_preregistro()
    if error:
        print(f"FALLA  {error}")
        return 1

    journal = Journal(f"jrn-{run_id}", preregistro_sha256 or "0" * 64, reloj)
    with tempfile.TemporaryDirectory(prefix="runner-caso-") as tmp:
        contexto = ContextoDeEjecucion(
            receta=receta, sample_id=sample_id, attempt_id=attempt_id, attempt_ordinal=ordinal,
            run_id=run_id, preregistro_sha256=preregistro_sha256, arbol=arbol, recibo=recibo,
            recibos_usados=set(),
            identidad_del_entorno=identidad_del_entorno_de_hoy(congelamiento),
            recibos=recibos, sesionador=sesionador_codex(Path(tmp)),
            despachar_comando=_despachador_real,
            # El scratch vive DENTRO del árbol desechable para que toda ruta del comando
            # sea relativa a su `cwd`. El árbol es desechable; lo que se cosecha se
            # importa al staging después, que es lo que D-19 pide sacar del árbol medido.
            scratch=arbol / ".cohorte-scratch" / run_id,
            ancla_de_invocacion=_ancla_del_punto(receta["punto_de_despacho"]),
            retiros_comprobados=constatar_retiros_del_caso(receta, recibo),
            destino=salida / run_id,
            confirmacion=getattr(args, "confirmacion", None) or "")
        bundle, problemas = ejecutar_caso(contexto, journal, reloj)

    ruta_journal = salida / run_id / "journal-anomalias.json"
    _escribir_json(ruta_journal, journal.como_json())
    print(f"Journal: {_relativa(ruta_journal)} — {len(journal.entradas)} entradas, "
          f"{len(journal.candidate_ids())} anomalías")

    if bundle is None:
        for p in problemas:
            print(f"FALLA  {p}")
        print()
        print("RESULTADO: FALLA — el caso no produjo bundle; la anomalía quedó en el journal")
        return 1

    ruta_bundle = salida / run_id / "bundle.json"
    _escribir_json(ruta_bundle, bundle)
    print(f"Bundle:  {_relativa(ruta_bundle)} — {len(bundle['eventos'])} eventos")
    if problemas:
        for p in problemas:
            print(f"FALLA  {p}")
        print()
        print(f"RESULTADO: FALLA — {len(problemas)} problemas en la captura")
        return 1
    print()
    print("RESULTADO: OK — el caso corrió y su bundle quedó escrito; validarlo es del instrumento")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-adaptadores`.
#
# El bundle que producen los dos adaptadores lo juzga **el instrumento, como proceso aparte**. Que
# el runner lo validara con una copia propia sería el conjunto validándose contra sí mismo: una
# mutación podría cambiar a la vez lo que se emite y lo que decide si vale.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_ADAPTADORES = DIR_FIXTURES_RUNNER / "adaptadores"
RUTA_CORPUS_ADAPTADORES = DIR_FIXTURES_ADAPTADORES / "recetas.json"
RUTA_MANIFEST_ADAPTADORES = DIR_FIXTURES_ADAPTADORES / "manifest.json"
DIR_RECIBOS_ADAPTADORES = DIR_FIXTURES_ADAPTADORES / "recibos"


def _despachador_de_control(comando: str, arbol: Path) -> tuple[int, str]:
    """El despacho de los controles no invoca un modelo: lo que se prueba es la captura."""
    del comando, arbol
    return 0, "STATUS: done\nFILES: scripts/ejemplo.py\n"


def _contexto_de_control(receta: dict[str, Any], intento: dict[str, Any], *,
                         recibo: dict[str, Any] | None = None,
                         recibos_usados: set[str] | None = None,
                         preregistro: str | None = None,
                         recibos: Path | None = None,
                         run_id: str = "run-ad-1") -> ContextoDeEjecucion:
    return ContextoDeEjecucion(
        receta=receta,
        sample_id=intento["sample_id"],
        attempt_id=intento["attempt_id"],
        attempt_ordinal=intento["attempt_ordinal"],
        run_id=run_id,
        preregistro_sha256=(intento["preregistro_sha256"] if preregistro is None else preregistro),
        arbol=RAIZ,
        recibo=recibo,
        recibos_usados=set() if recibos_usados is None else recibos_usados,
        identidad_del_entorno=identidad_del_entorno_de_hoy(),
        recibos=DIR_RECIBOS_ADAPTADORES if recibos is None else recibos,
        sesionador=sesionador_local("sano"),
        despachar_comando=_despachador_de_control,
        # Por la misma vía que la corrida real: si los controles lo dejaran en su default, el
        # camino que decide el aislamiento de un escritor seguiría sin ejercerse en ningún test.
        retiros_comprobados=constatar_retiros_del_caso(receta, recibo),
    )


def _correr_adaptador(receta: dict[str, Any], intento: dict[str, Any],
                      despachador: Callable[[str, Path], tuple[int, str]] | None = None,
                      **kwargs: Any) -> tuple[dict[str, Any] | None, list[str], Journal]:
    reloj, error = cargar_reloj(receta["adaptador"])
    if reloj is None:
        raise RuntimeError(error)
    contexto = _contexto_de_control(receta, intento, **kwargs)
    if despachador is not None:
        contexto = contexto._replace(despachar_comando=despachador)
    journal = Journal(f"jrn-{contexto.run_id}", contexto.preregistro_sha256 or "0" * 64, reloj)
    bundle, problemas = ejecutar_caso(contexto, journal, reloj)
    return bundle, problemas, journal


def validar_bundle_con_el_instrumento(bundle: dict[str, Any]) -> tuple[bool, str]:
    """El juez del bundle es el instrumento, invocado como proceso aparte."""
    with tempfile.TemporaryDirectory(prefix="runner-validar-") as tmp:
        raiz = Path(tmp)
        _escribir_json(raiz / bundle["run_id"] / "bundle.json", bundle)
        codigo, salida = _correr([sys.executable, str(RUTA_INSTRUMENTO),
                                  "--validar-bundles", str(raiz)])
    return codigo == 0, salida


def modo_autotest_adaptadores(args: argparse.Namespace) -> int:
    del args
    resultados: list[Resultado] = []
    controles_ejercidos: set[str] = set()

    corpus, error_corpus = _cargar_json(RUTA_CORPUS_ADAPTADORES)
    manifest, error_manifest = _cargar_json(RUTA_MANIFEST_ADAPTADORES)
    if error_corpus or error_manifest:
        for e in (error_corpus, error_manifest):
            if e:
                print(f"FALLA  {e}")
        return 1
    por_id = {r["receta_id"]: r for r in corpus["recetas"]}
    intento = manifest["intento"]
    recibo_sano, _ = _cargar_json(DIR_RECIBOS_ADAPTADORES / "rcb-sano.json")

    # [A] Los dos adaptadores declaran EXACTAMENTE el mismo conjunto de obligaciones.
    fallas = []
    for adaptador in ADAPTADORES:
        faltan = [o for o in OBLIGACIONES_DEL_ADAPTADOR if o not in adaptador.obligaciones]
        sobran = [o for o in adaptador.obligaciones if o not in OBLIGACIONES_DEL_ADAPTADOR]
        if faltan:
            fallas.append(f"`{adaptador.nombre}` no carga estas obligaciones: {faltan}")
        if sobran:
            fallas.append(f"`{adaptador.nombre}` carga obligaciones que no son del conjunto: "
                          f"{sobran}")
    if len({a.obligaciones for a in ADAPTADORES}) != 1:
        fallas.append("los dos adaptadores no cargan el mismo conjunto de obligaciones")
    if len({a.de_donde_sale_lo_que_paso for a in ADAPTADORES}) != len(ADAPTADORES):
        fallas.append("los dos adaptadores declaran la misma procedencia de la evidencia: la "
                      "diferencia entre ellos es de dónde sale lo que pasó, no qué se les exige")
    resultados.append(Resultado("A", f"los {len(ADAPTADORES)} adaptadores cargan las mismas "
                                     f"{len(OBLIGACIONES_DEL_ADAPTADOR)} obligaciones", fallas))

    # [B] Los dos emiten un bundle que EL INSTRUMENTO valida.
    fallas = []
    bundles: dict[str, dict[str, Any]] = {}
    with path_con_binario("codex"):
        for receta_id, extra in (("ad-script", {}), ("ad-sesion", {"recibo": recibo_sano})):
            bundle, problemas, _ = _correr_adaptador(por_id[receta_id], intento,
                                                     run_id=f"run-{receta_id}", **extra)
            if bundle is None:
                fallas.append(f"`{receta_id}` no produjo bundle: {problemas}")
                continue
            if problemas:
                fallas.append(f"`{receta_id}` produjo bundle con problemas: {problemas}")
            bundles[receta_id] = bundle
            valido, salida = validar_bundle_con_el_instrumento(bundle)
            if not valido:
                fallas.append(f"el instrumento rechazó el bundle de `{receta_id}`: "
                              f"{salida.strip().splitlines()[-3:]}")
    # El estado del intento sale del terminal observado, no de haber llegado al final: un despacho
    # que falla y se registra como completado es un intento inventado con forma válida.
    with path_con_binario("codex"):
        fallido, _, _ = _correr_adaptador(
            por_id["ad-script"], intento, run_id="run-ad-script-fallido",
            despachador=lambda comando, arbol: (1, "el worker no arrancó"))
    if fallido is None:
        fallas.append("el despacho fallido no produjo bundle: un intento bloqueado es canónico y "
                      "se conserva")
    else:
        if fallido["estado_del_intento"]["resultado"] != "bloqueado":
            fallas.append("un despacho que falló quedó registrado como intento completado")
        valido, salida = validar_bundle_con_el_instrumento(fallido)
        if not valido:
            fallas.append(f"el instrumento rechazó el bundle del intento bloqueado: "
                          f"{salida.strip().splitlines()[-3:]}")
    resultados.append(Resultado("B", "los dos adaptadores emiten un bundle que el instrumento "
                                     "valida, y un despacho fallido queda como intento bloqueado "
                                     "canónico", fallas))

    # [C] Los dos validan el pre-registro: sin contenido congelado, ninguno ejecuta.
    fallas = []
    with path_con_binario("codex"):
        for receta_id, extra in (("ad-script", {}), ("ad-sesion", {"recibo": recibo_sano})):
            bundle, problemas, journal = _correr_adaptador(
                por_id[receta_id], intento, preregistro="", **extra)
            if bundle is not None:
                fallas.append(f"`{receta_id}` ejecutó sin pre-registro congelado")
            if not any(e.get("clase") == "fallo_previo_al_bundle" for e in journal.entradas):
                fallas.append(f"`{receta_id}`: el rechazo del pre-registro no quedó en el journal")
    resultados.append(Resultado("C", "los dos adaptadores rechazan una corrida sin pre-registro "
                                     "congelado, y el rechazo queda en el journal", fallas))

    # [D] Los dos corren el preflight de su receta: un bloqueo LE IMPIDE ejecutar a cada uno.
    #
    # Hay un bloqueo por adaptador y no uno solo: que los dos ejecuten no prueba que los dos hayan
    # corrido el preflight, y con un único caso bloqueado el otro adaptador quedaría sin ejercer
    # esa obligación.
    fallas = []
    declarados = {b["adaptador"] for b in manifest["bloqueos_por_adaptador"]}
    if declarados != {a.nombre for a in ADAPTADORES}:
        fallas.append(f"el manifest no declara un bloqueo por adaptador: {sorted(declarados)}")
    with tempfile.TemporaryDirectory(prefix="runner-sin-recibos-") as vacio:
        for bloqueo in manifest["bloqueos_por_adaptador"]:
            receta = por_id[bloqueo["receta"]]
            extra: dict[str, Any] = {}
            if receta["adaptador"] == "sesion_de_agente":
                extra = {"recibo": recibo_sano, "recibos": Path(vacio)}
            with path_con_binario("codex"):
                bundle, problemas, journal = _correr_adaptador(
                    receta, intento, run_id=f"run-bloqueado-{receta['receta_id']}", **extra)
            if bundle is not None:
                fallas.append(f"`{bloqueo['receta']}` ejecutó con su preflight bloqueado")
            elif not any(f"el preflight bloqueó el caso por `{bloqueo['causa_esperada']}`" in p
                         for p in problemas):
                fallas.append(f"`{bloqueo['receta']}` no ejecutó, pero no por "
                              f"`{bloqueo['causa_esperada']}`: {problemas}")
            elif not any(e.get("clase") == "fallo_previo_al_bundle" for e in journal.entradas):
                fallas.append(f"`{bloqueo['receta']}`: el bloqueo del preflight no quedó en el "
                              f"journal")
    resultados.append(Resultado("D", "los dos adaptadores corren el preflight de su receta y un "
                                     "bloqueo le impide ejecutar a cada uno", fallas))

    # [E] El bundle del adaptador de sesión sale DEL RECIBO, no de lo que la sesión declare.
    fallas = []
    bundle = bundles.get("ad-sesion")
    if bundle is None:
        fallas.append("no hay bundle de sesión que inspeccionar")
    else:
        apertura = next(e for e in recibo_sano["recibo"]["eventos"]
                        if e["evento"] == "dispatch_started")
        retorno = next(e for e in recibo_sano["recibo"]["eventos"]
                       if e["evento"] == "dispatch_returned")
        if bundle["invocacion"].get("prompt_sha256") != apertura["prompt_sha256"]:
            fallas.append("el `prompt_sha256` del bundle no es el que el recibo congeló")
        efectiva = bundle["identidad_del_entorno"]["ejecutor"]["instancia_efectiva"]
        if efectiva.get("valor") != retorno["session_id"]["valor"]:
            fallas.append("la instancia efectiva del ejecutor no salió del recibo")
        if bundle.get("recibo_de_frontera", {}).get("recibo_id") != "rcb-sano":
            fallas.append("el bundle no referencia el recibo del que se construyó")
        # El control en la otra dirección: cambiar el recibo cambia el bundle. Si no cambiara, el
        # bundle no estaría saliendo de ahí y las tres comprobaciones de arriba serían casualidad.
        otro = json.loads(json.dumps(recibo_sano))
        otro["recibo"]["recibo_id"] = "rcb-sano-variante"
        for evento in otro["recibo"]["eventos"]:
            if evento["evento"] == "dispatch_returned":
                evento["session_id"]["valor"] = "ses-otra-instancia"
        with path_con_binario("codex"):
            variante, _, _ = _correr_adaptador(por_id["ad-sesion"], intento, recibo=otro,
                                               run_id="run-ad-sesion-variante")
        if variante is None:
            fallas.append("la variante del recibo no produjo bundle")
        elif (variante["identidad_del_entorno"]["ejecutor"]["instancia_efectiva"].get("valor")
              == efectiva.get("valor")):
            fallas.append("cambiar el recibo no cambió el bundle: no se está construyendo desde "
                          "ahí")
    resultados.append(Resultado("E", "el bundle del adaptador de sesión se construye desde el "
                                     "recibo, y cambiar el recibo lo cambia", fallas))

    # [F] Cada ataque al recibo cae POR SU CONTROL, uno a uno.
    fallas = []
    for ataque in manifest["ataques"]:
        recibo, error = _cargar_json(DIR_RECIBOS_ADAPTADORES / f"{ataque['recibo']}.json")
        if error:
            fallas.append(f"`{ataque['recibo']}`: {error}")
            continue
        contexto = _contexto_de_control(por_id["ad-sesion"], intento, recibo=recibo)
        problemas = revisar_recibo_de_frontera(recibo, contexto)
        claves = {p.split("]")[0].lstrip("[") for p in problemas}
        esperada = ataque["control_esperado"]
        if not problemas:
            fallas.append(f"`{ataque['recibo']}` no fue rechazado: {ataque['que_ataca']}")
        elif esperada not in claves:
            fallas.append(f"`{ataque['recibo']}` cayó por {sorted(claves)} y no por su control "
                          f"`{esperada}`")
        else:
            controles_ejercidos.add(esperada)
    # Los dos ataques sin archivo: el recibo ausente y el reutilizado.
    contexto = _contexto_de_control(por_id["ad-sesion"], intento, recibo=None)
    claves = {p.split("]")[0].lstrip("[") for p in revisar_recibo_de_frontera(None, contexto)}
    if "recibo_presente" not in claves:
        fallas.append(f"un bundle sin recibo de frontera no cayó por `recibo_presente`: {claves}")
    else:
        controles_ejercidos.add("recibo_presente")
    contexto = _contexto_de_control(por_id["ad-sesion"], intento, recibo=recibo_sano,
                                    recibos_usados={"rcb-sano"})
    claves = {p.split("]")[0].lstrip("[")
              for p in revisar_recibo_de_frontera(recibo_sano, contexto)}
    if "recibo_no_reutilizado" not in claves:
        fallas.append(f"un recibo ya usado no cayó por `recibo_no_reutilizado`: {claves}")
    else:
        controles_ejercidos.add("recibo_no_reutilizado")
    # El positivo: el recibo sano no cae por ninguno.
    contexto = _contexto_de_control(por_id["ad-sesion"], intento, recibo=recibo_sano)
    sobrantes = revisar_recibo_de_frontera(recibo_sano, contexto)
    if sobrantes:
        fallas.append(f"el recibo sano fue rechazado: {sobrantes}")
    resultados.append(Resultado("F", "cada ataque al recibo cae por su propio control, y el "
                                     "recibo sano no cae por ninguno", fallas))

    # [G] Los sellos salen de la interfaz de reloj, y la secuencia de apertura va en orden.
    fallas = []
    interfaz, error = _cargar_json(RUTA_INTERFAZ_DE_RELOJ)
    admitidas = {p["procedencia_id"] for p in (interfaz or {}).get("procedencias_admitidas") or []}
    for receta_id, bundle in bundles.items():
        for evento in bundle["eventos"]:
            sello = evento["sello"]
            if sello["procedencia"] not in admitidas:
                fallas.append(f"`{receta_id}`: el evento `{evento['evento_id']}` cita una "
                              f"procedencia que la interfaz no admite")
            if sello["autoridad"] != "harness":
                fallas.append(f"`{receta_id}`: el evento `{evento['evento_id']}` no se selló bajo "
                              f"autoridad del harness")
        if revisar_secuencia_de_apertura(bundle["eventos"]):
            fallas.append(f"`{receta_id}`: la secuencia de apertura no está en orden")
    # El negativo del revisor: una secuencia desordenada y una incompleta tienen que caer.
    if bundles:
        eventos = list(bundles["ad-script"]["eventos"])
        desordenada = [eventos[1], eventos[0]] + eventos[2:]
        if not revisar_secuencia_de_apertura(desordenada):
            fallas.append("una secuencia de apertura desordenada no fue rechazada")
        if not revisar_secuencia_de_apertura([e for e in eventos if e["tipo"] != "despacho"]):
            fallas.append("una secuencia sin el evento de despacho no fue rechazada")
        con_sello_ajeno = json.loads(json.dumps(eventos))
        con_sello_ajeno[0]["sello"]["fuente"] = "tiempo de pared del worker"
        if not revisar_secuencia_de_apertura(con_sello_ajeno):
            fallas.append("un sello que no es del reloj del harness no fue rechazado")
    resultados.append(Resultado("G", "los sellos salen de la interfaz de reloj y la secuencia de "
                                     "apertura va en su orden, con sus negativos", fallas))

    # [H] Cobertura de los controles del recibo, acumulada corriendo.
    fallas = []
    sin_ejercer = [c for c in CONTROLES_DEL_RECIBO if c not in controles_ejercidos]
    inexistentes = sorted(controles_ejercidos - set(CONTROLES_DEL_RECIBO))
    declarados = manifest.get("controles_ejercidos") or []
    if sin_ejercer:
        fallas.append(f"controles del recibo sin ataque que los ejerza: {sin_ejercer}")
    if inexistentes:
        fallas.append(f"se ejercieron controles que no existen: {inexistentes}")
    if sorted(declarados) != sorted(CONTROLES_DEL_RECIBO):
        fallas.append(f"el manifest declara otros controles que el conjunto cerrado: {declarados}")
    resultados.append(Resultado("H", f"los {len(CONTROLES_DEL_RECIBO)} controles del recibo tienen "
                                     f"un ataque que los ejerce, acumulado corriendo", fallas))

    return _imprimir_controles("adaptadores", resultados)


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-journal`.
#
# Lo que se prueba no es que el journal tenga entradas: es que su completitud se derive del
# **manifest independiente de intentos**. Un journal comparado contra sí mismo daría verde
# omitiendo una anomalía, conservando un bundle bloqueado y cerrando el ledger incompleto sin que
# nada falle.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_JOURNAL = DIR_FIXTURES_RUNNER / "journal"
RUTA_CORPUS_JOURNAL = DIR_FIXTURES_JOURNAL / "recetas.json"
RUTA_MANIFEST_JOURNAL = DIR_FIXTURES_JOURNAL / "manifest.json"
DIR_RECIBOS_JOURNAL = DIR_FIXTURES_JOURNAL / "recibos"
RUTA_SCHEMA_JOURNAL = DIR_JOURNAL_FASE_0 / "journal-anomalias.schema.json"
RUTA_SCHEMA_BUNDLE = DIR_SCRIPTS / "bundle-corrida.schema.json"

SALIDA_CON_SECRETO = "STATUS: done\nel token quedó en el log: ghp_0123456789abcdefghij\n"


def _despachador_con_secreto(comando: str, arbol: Path) -> tuple[int, str]:
    del comando, arbol
    return 0, SALIDA_CON_SECRETO


def modo_autotest_journal(args: argparse.Namespace) -> int:
    del args
    resultados: list[Resultado] = []
    clases_ejercidas: set[str] = set()

    corpus, error_corpus = _cargar_json(RUTA_CORPUS_JOURNAL)
    manifest, error_manifest = _cargar_json(RUTA_MANIFEST_JOURNAL)
    schema_journal, error_schema = _cargar_json(RUTA_SCHEMA_JOURNAL)
    schema_bundle, error_bundle = _cargar_json(RUTA_SCHEMA_BUNDLE)
    for e in (error_corpus, error_manifest, error_schema, error_bundle):
        if e:
            print(f"FALLA  {e}")
            return 1
    por_id = {r["receta_id"]: r for r in corpus["recetas"]}
    intento = manifest["intento"]

    def correr(receta_id: str, *, preregistro: str | None = None,
               despachador: Callable[[str, Path], tuple[int, str]] = _despachador_de_control,
               run_id: str = "run-jr") -> tuple[dict[str, Any] | None, Journal]:
        receta = por_id[receta_id]
        reloj, error = cargar_reloj(receta["adaptador"])
        if reloj is None:
            raise RuntimeError(error)
        contexto = _contexto_de_control(
            receta, intento, preregistro=preregistro, recibos=DIR_RECIBOS_JOURNAL,
            recibo=_cargar_json(DIR_RECIBOS_JOURNAL / "rcb-jr-produccion.json")[0]
            if receta["adaptador"] == "sesion_de_agente" else None,
            run_id=run_id)
        contexto = contexto._replace(despachar_comando=despachador,
                                     sample_id=intento["sample_id"],
                                     attempt_id=intento["attempt_id"])
        journal = Journal(f"jrn-{run_id}", contexto.preregistro_sha256 or "0" * 64, reloj)
        try:
            bundle, _ = ejecutar_caso(contexto, journal, reloj)
        except Exception:  # la caída se registró en el journal y acá se la deja seguir su curso
            bundle = None
        return bundle, journal

    # [A] Los tres mutantes de D-25 quedan registrados, cada uno con SU clase y en SU operación.
    fallas = []
    journals: dict[str, Journal] = {}
    with path_con_binario("codex"):
        for mutante in manifest["mutantes"]:
            kwargs: dict[str, Any] = {"run_id": f"run-{mutante['clave']}"}
            if mutante["clase_esperada"] == "fallo_previo_al_bundle":
                kwargs["preregistro"] = ""
            if mutante["clase_esperada"] == "sanitizacion_rechazada":
                kwargs["despachador"] = _despachador_con_secreto
            bundle, journal = correr(mutante["receta"], **kwargs)
            journals[mutante["clave"]] = journal
            if bundle is not None:
                fallas.append(f"`{mutante['clave']}` produjo bundle: el mutante no se aplicó")
                continue
            anomalias = [e for e in journal.entradas if e.get("resultado") == "anomaly"]
            clases = {a["clase"] for a in anomalias}
            if mutante["clase_esperada"] not in clases:
                fallas.append(f"`{mutante['clave']}` quedó registrado como {sorted(clases)} y no "
                              f"como `{mutante['clase_esperada']}`")
                continue
            aperturas = {a["entrada_id"]: a for a in journal.entradas
                         if a["evento"] == "operacion_abierta"}
            operacion = aperturas[anomalias[0]["referencia_entrada_id"]]["operacion"]
            if operacion != mutante["operacion_esperada"]:
                fallas.append(f"`{mutante['clave']}` cayó en la operación `{operacion}` y se "
                              f"esperaba `{mutante['operacion_esperada']}`")
                continue
            clases_ejercidas.add(mutante["clase_esperada"])
    resultados.append(Resultado("A", f"los {len(manifest['mutantes'])} mutantes de D-25 quedan "
                                     f"registrados, cada uno con su clase y en su operación",
                                fallas))

    # [B] Cada apertura tiene EXACTAMENTE un terminal, y omitir uno falla.
    fallas = []
    with path_con_binario("codex"):
        bundle_sano, journal_sano = correr("jr-sano", run_id="run-jr-sano")
    if bundle_sano is None:
        fallas.append("la corrida sana no produjo bundle")
    esperados = manifest["intentos_esperados"]
    problemas = reconciliar_journal(journal_sano.como_json(), esperados)
    if problemas:
        fallas.append(f"la corrida sana no reconcilia: {problemas}")
    sin_terminal = journal_sano.como_json()
    sin_terminal["entradas"] = [e for e in sin_terminal["entradas"]
                                if e["evento"] != "operacion_terminada"][:1] + [
        e for e in sin_terminal["entradas"] if e["evento"] == "operacion_terminada"][1:]
    if not reconciliar_journal(sin_terminal, esperados):
        fallas.append("omitir un resultado terminal no hizo fallar la reconciliación")
    duplicado = journal_sano.como_json()
    terminal = next(e for e in duplicado["entradas"] if e["evento"] == "operacion_terminada")
    duplicado["entradas"] = duplicado["entradas"] + [dict(terminal, entrada_id="tm-duplicado")]
    if not reconciliar_journal(duplicado, esperados):
        fallas.append("dos resultados terminales para la misma apertura no hicieron fallar la "
                      "reconciliación")
    resultados.append(Resultado("B", "cada apertura tiene exactamente un terminal, y omitir o "
                                     "duplicar uno hace fallar la reconciliación", fallas))

    # [C] La apertura va ANTES de la operación: una anomalía deja apertura aunque nada termine bien.
    fallas = []
    for clave, journal in journals.items():
        entradas = journal.entradas
        if not entradas or entradas[0]["evento"] != "operacion_abierta":
            fallas.append(f"`{clave}`: la primera entrada del journal no es una apertura")
        anomalia = next((e for e in entradas if e.get("resultado") == "anomaly"), None)
        if anomalia is None:
            continue
        indice_anomalia = entradas.index(anomalia)
        apertura = next((e for e in entradas
                         if e["entrada_id"] == anomalia["referencia_entrada_id"]), None)
        if apertura is None:
            fallas.append(f"`{clave}`: la anomalía no referencia ninguna apertura")
        elif entradas.index(apertura) > indice_anomalia:
            fallas.append(f"`{clave}`: la apertura se emitió después de la anomalía, así que una "
                          f"caída sin manejo no habría dejado rastro")
    resultados.append(Resultado("C", "la apertura se emite antes de la operación, y una anomalía "
                                     "la encuentra ya escrita", fallas))

    # [D] La completitud se deriva DEL MANIFEST, no de las entradas del journal.
    fallas = []
    otro_intento = esperados + [{"sample_id": "mst-journal-r2",
                                 "attempt_id": "int-mst-journal-r2-a1"}]
    if not reconciliar_journal(journal_sano.como_json(), otro_intento):
        fallas.append("un intento del manifest sin ninguna operación abierta no hizo fallar la "
                      "reconciliación: la completitud se está derivando del journal")
    if not reconciliar_journal(journal_sano.como_json(), []):
        fallas.append("un journal con operaciones de intentos que el manifest no declara no hizo "
                      "fallar la reconciliación")
    huerfano = journal_sano.como_json()
    huerfano["entradas"] = [e for e in huerfano["entradas"] if e["evento"] != "operacion_abierta"]
    if not reconciliar_journal(huerfano, esperados):
        fallas.append("terminales sin apertura que los reclame no hicieron fallar la "
                      "reconciliación")
    resultados.append(Resultado("D", "la completitud se deriva del manifest independiente de "
                                     "intentos y no de las entradas del journal", fallas))

    # [E] El `candidate_id` es por anomalía y no por corrida.
    fallas = []
    ids = [c for j in journals.values() for c in j.candidate_ids()]
    if len(ids) != len(set(ids)):
        fallas.append(f"dos anomalías comparten `candidate_id`: {ids}")
    if not all("-" in c for c in ids):
        fallas.append("algún `candidate_id` no distingue el intento de la operación")
    resultados.append(Resultado("E", "el `candidate_id` es por anomalía: dos anomalías nunca "
                                     "comparten identidad", fallas))

    # [F] Los conjuntos cerrados del runner son los del contrato, en las dos direcciones.
    #
    # Es lo que impide la divergencia silenciosa entre lo que el runner sabe emitir y lo que el
    # schema admite: un valor nuevo en el contrato que el runner no conozca, o al revés.
    fallas = []
    defs_journal = schema_journal["$defs"]
    defs_bundle = schema_bundle["$defs"]
    for nombre, del_runner, del_contrato in (
            ("operaciones", OPERACIONES_DEL_JOURNAL, defs_journal["enum_operacion"]["enum"]),
            ("clases de anomalía", CLASES_DE_ANOMALIA,
             defs_journal["enum_clase_de_anomalia"]["enum"]),
            ("pasos de sanitización", ORDEN_DE_SANITIZACION,
             defs_bundle["enum_paso_de_sanitizacion"]["enum"]),
            ("transportes de bundle", TRANSPORTES_DEL_BUNDLE,
             defs_bundle["enum_transporte"]["enum"]),
            ("tipos de evento", SECUENCIA_DE_APERTURA,
             [t for t in defs_bundle["enum_tipo_de_evento"]["enum"]
              if t in SECUENCIA_DE_APERTURA])):
        if sorted(del_runner) != sorted(del_contrato):
            fallas.append(f"{nombre}: el runner conoce {sorted(del_runner)} y el contrato declara "
                          f"{sorted(del_contrato)}")
    if list(SECUENCIA_DE_APERTURA) != [t for t in defs_bundle["enum_tipo_de_evento"]["enum"]
                                       if t in SECUENCIA_DE_APERTURA]:
        fallas.append("el orden de la secuencia de apertura del runner no es el del contrato")
    resultados.append(Resultado("F", "los conjuntos cerrados del runner son los del contrato, "
                                     "comparados en las dos direcciones", fallas))

    # [G] Un valor fuera del conjunto cerrado se rechaza, en las dos puntas.
    fallas = []
    try:
        with Journal("jrn-x", "0" * 64, Reloj("p", 1)).operacion("operacion-inventada", "s", "a"):
            pass
    except ValueError:
        pass
    else:
        fallas.append("abrir una operación fuera del conjunto cerrado no se rechazó")
    con_clase_inventada = journals["sanitizacion-rechazada"].como_json()
    for entrada in con_clase_inventada["entradas"]:
        if entrada.get("resultado") == "anomaly":
            entrada["clase"] = "clase_inventada"
    if not reconciliar_journal(con_clase_inventada,
                               [{"sample_id": intento["sample_id"],
                                 "attempt_id": intento["attempt_id"]}]):
        fallas.append("una clase de anomalía fuera del conjunto cerrado no se detectó")
    resultados.append(Resultado("G", "una operación o una clase fuera del conjunto cerrado se "
                                     "rechazan", fallas))

    # [H] El bundle referencia los `candidate_id` del journal de su corrida.
    fallas = []
    if bundle_sano is not None and bundle_sano["journal_candidate_ids"] != \
            journal_sano.candidate_ids():
        fallas.append("el bundle no referencia los `candidate_id` del journal de su corrida")
    declaradas = manifest.get("clases_ejercidas") or []
    sin_ejercer = [c for c in declaradas if c not in clases_ejercidas]
    if sin_ejercer:
        fallas.append(f"clases declaradas por el manifest que ningún mutante produjo: "
                      f"{sin_ejercer}")
    no_declaradas = sorted(clases_ejercidas - set(declaradas))
    if no_declaradas:
        fallas.append(f"se produjeron clases que el manifest no declara: {no_declaradas}")
    fuera_del_contrato = [c for c in declaradas if c not in CLASES_DE_ANOMALIA]
    if fuera_del_contrato:
        fallas.append(f"el manifest declara clases que el contrato no tiene: {fuera_del_contrato}")
    resultados.append(Resultado("H", "el bundle referencia los `candidate_id` de su journal, y las "
                                     "clases ejercidas son las que el manifest declara", fallas))

    return _imprimir_controles("journal", resultados)


# ---------------------------------------------------------------------------------------------
# Registro de modos.
# ---------------------------------------------------------------------------------------------

registrar_modo(
    "--provisionar",
    "crea el repositorio desechable a partir del árbol medido, retira remotos, credenciales "
    "alcanzables y la red del worker, y deja de cada retiro una constancia comprobable con el "
    "comando que la produce y la salida observada después de aplicarlo",
    modo_provisionar,
    argumento=Argumento("<dir-destino>"),
)

registrar_modo(
    "--autotest-provisionamiento",
    "control positivo y negativo del provisionamiento: un remoto sobreviviente, una credencial "
    "alcanzable, un árbol reutilizado y un comando sin sandbox dejan su retiro sin constancia, y "
    "cada retiro del conjunto cerrado tiene un negativo que lo pone en rojo",
    modo_autotest_provisionamiento,
)

registrar_modo(
    "--preflight",
    "adjudica cada receta de la cohorte `runnable` o `blocked` con causa del conjunto cerrado, "
    "probando que su adaptador está disponible y que su lanzamiento es controlable; el paso de "
    "`cli-resume` se prueba con una sesión desechable y sus tres negativos",
    modo_preflight,
    auxiliares=(
        Auxiliar("--recibos", "la sede de recibos de frontera contra la que se prueba la "
                              "disponibilidad del adaptador de sesión",
                 metavar="<dir-de-recibos>"),
        Auxiliar("--acta", "la propuesta de acta a la que se adjuntan el inventario de egreso "
                           "materializado y el recibo del preflight, antes del STOP (D-14); con "
                           "ella, un bloqueo que viole la cobertura declarada hace fallar el modo",
                 metavar="<ruta>"),
    ),
)

registrar_modo(
    "--autotest-preflight",
    "control positivo y negativo del preflight sobre su corpus: adaptador ausente y lanzamiento no "
    "controlable bloquean el caso ANTES de ejecutarlo, el `resume` se prueba con una sesión "
    "desechable y sus tres negativos, y cada causa del conjunto cerrado tiene quien la produzca",
    modo_autotest_preflight,
)

registrar_modo(
    "--ejecutar-caso",
    "corre un caso por su receta, sella cada evento con la interfaz de reloj y emite el bundle con "
    "la secuencia de apertura en orden; el adaptador de sesión lo construye desde el recibo de "
    "frontera y nunca desde lo que la sesión declare de sí misma",
    modo_ejecutar_caso,
    argumento=Argumento("<run_id>"),
    auxiliares=(
        Auxiliar("--receta", "el `receta_id` del caso a correr", metavar="<receta_id>"),
        Auxiliar("--muestra", "el `sample_id` de la muestra pre-registrada", metavar="<sample_id>"),
        Auxiliar("--intento", "el ordinal del intento dentro de su muestra", metavar="<n>"),
        Auxiliar("--preregistro", "el hash del pre-registro congelado contra el que corre",
                 metavar="<sha256>"),
        Auxiliar("--arbol", "el árbol desechable sobre el que corre el caso", metavar="<dir>"),
        Auxiliar("--recibo", "el recibo de frontera del despacho, obligatorio para el adaptador "
                             "de sesión", metavar="<ruta>"),
        Auxiliar("--salida", "dónde escribir `<run_id>/bundle.json` y su journal",
                 metavar="<dir-de-corridas>"),
        Auxiliar("--confirmacion",
                 "con qué se acredita la confirmación del usuario, para los puntos que la matriz "
                 "declara que no corren sin ella; sin esto, esos puntos bloquean el intento en vez "
                 "de estratificarse como automatizables", metavar="<texto>"),
    ),
)

registrar_modo(
    "--autotest-adaptadores",
    "control de que los dos adaptadores cargan las MISMAS obligaciones: los dos validan el "
    "pre-registro, los dos corren el preflight de su receta y los dos emiten un bundle que el "
    "instrumento valida; y el de sesión rechaza recibos ausentes, reutilizados, discordantes o "
    "generados a posteriori",
    modo_autotest_adaptadores,
)

registrar_modo(
    "--autotest-journal",
    "control del journal de anomalías: los tres mutantes de D-25 —fallo anterior al bundle, "
    "sanitización rechazada y caída durante su construcción— quedan registrados con su clase, y "
    "cada intento del manifest tiene exactamente un resultado terminal; omitir uno falla",
    modo_autotest_journal,
)


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runner-cohorte.py",
        description="Runner de la cohorte de la fase 0: provisiona, preflightea, ejecuta y captura.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    for modo in MODOS:
        if modo.argumento is None:
            parser.add_argument(modo.bandera, action="store_true", help=modo.ayuda)
        elif modo.argumento.const is None:
            parser.add_argument(modo.bandera, metavar=modo.argumento.metavar, help=modo.ayuda)
        else:
            parser.add_argument(modo.bandera, nargs="?", const=modo.argumento.const,
                                metavar=modo.argumento.metavar, help=modo.ayuda)
        for auxiliar in modo.auxiliares:
            if auxiliar.metavar is None:
                parser.add_argument(auxiliar.bandera, action="store_true", help=auxiliar.ayuda)
            else:
                parser.add_argument(auxiliar.bandera, metavar=auxiliar.metavar,
                                    default=auxiliar.por_defecto, help=auxiliar.ayuda)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _construir_parser()
    args = parser.parse_args(argv)

    seleccionados = [m for m in MODOS if getattr(args, m.destino)]
    if len(seleccionados) != 1:
        banderas = ", ".join(m.bandera for m in MODOS)
        print(f"Invocación inválida: exactamente uno de {banderas}.", file=sys.stderr)
        return 2
    return seleccionados[0].handler(args)


if __name__ == "__main__":
    sys.exit(main())
