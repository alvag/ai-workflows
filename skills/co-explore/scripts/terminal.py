#!/usr/bin/env python3
"""Adaptador de transporte por terminales del flujo SDD."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import re
from datetime import datetime, timezone
from pathlib import Path

# Lo que la via declara del worker, para cotejar contra la sede headless de `co-explore/reference.md`
# -> "Estados del worker" y "Envelope de retorno". Se declara aca y se compara; no se copia el texto.
ESTADOS_WORKER = ["INVALID", "READY", "UNAVAILABLE", "clarification-needed"]
CAMPOS_WORKER = ["cause", "detail", "family", "index", "parity", "session", "state"]
# Lo que la plataforma admite, capturado de `orca agent-context --json`. Los stubs de los autotests
# lo hacen cumplir: un stub que acepta cualquier bandera deja verde una invocacion que la plataforma
# rechaza, y eso ya paso dos veces. Se compara contra el esquema vivo con --autotest-contrato.
CONTRATO_ORCA = {
    "terminal split": {"command", "direction", "json", "terminal"},
    "terminal list": {"include-visual-layouts", "json", "limit", "worktree"},
    "terminal close": {"json", "tab", "terminal"},
    "terminal read": {"cursor", "json", "limit", "screen", "terminal"},
    "terminal rename": {"json", "terminal", "title"},
    "terminal send": {"enter", "interrupt", "json", "terminal", "text"},
    "orchestration run-create": {"from", "json", "objective", "retry-request"},
    "orchestration task-create": {"deps", "display-name", "from", "json", "parent", "retry-request",
                                  "run", "spec", "task-title"},
    "orchestration worker-start": {"agent", "base-branch", "comment", "display-name", "effort", "from",
                                   "json", "model", "name", "on", "repo", "retry-of", "retry-request",
                                   "run", "setup", "task", "terminal", "timeout-ms", "worktree"},
    "orchestration worker-show": {"dispatch", "json"},
    "orchestration worker-list": {"json", "run", "terminal-state"},
    "orchestration worker-release": {"dispatch", "json", "retry-request"},
    "orchestration worker-abandon": {"dispatch", "json", "retry-request"},
    "orchestration check": {"ack", "all", "format", "json", "peek", "retry-request", "run", "terminal",
                            "timeout-ms", "types", "unread", "wait"},
}

# Preambulo que todo stub de `orca` ejecuta antes de responder: rechaza lo que la plataforma
# rechazaria. Sin el, el oraculo no conoce la plataforma y no puede contradecir al codigo.
GUARDA_STUB = """
import json as _j, os as _o, sys as _s
_c = _j.loads(_o.environ.get("ORCA_CONTRATO", "{}"))
if _c and _o.path.basename(_s.argv[0]) == "orca":
    _a = _s.argv[1:]
    _cam = []
    for _p in _a:
        if _p.startswith("-"): break
        _cam.append(_p)
    _n = " ".join(_cam[:2])
    _adm = _c.get(_n)
    if _adm is None:
        _s.stderr.write("STUB: comando fuera del contrato: " + _n + chr(10)); _s.exit(9)
    for _k in range(len(_cam), len(_a)):
        _t = _a[_k]
        if _t.startswith("--"):
            if _t.lstrip("-").split("=")[0] not in _adm:
                _s.stderr.write("STUB: bandera inexistente en " + _n + ": " + _t + chr(10)); _s.exit(9)
        elif _t.startswith("-"):
            _s.stderr.write("STUB: bandera corta no admitida: " + _t + chr(10)); _s.exit(9)
        elif not _a[_k - 1].startswith("--"):
            _s.stderr.write("STUB: posicional suelto en " + _n + ": " + _t + chr(10)); _s.exit(9)
"""


VERBOS = ["detectar", "crear", "lanzar", "enviar", "esperar", "cosechar", "renombrar", "cerrar", "lanzar-conductor"]
CASOS = ["sin-plataforma", "orca-rancia", "solo-orca", "orca-inconsultable", "herdr-rancia", "identidades-rancias", "solo-herdr", "herdr-inconsultable", "ambas-resuelven", "mecanica-ilegible"]
DESTINOS = {
    ("ausente", "ausente"): ("sin-plataforma", "headless"),
    ("ausente", "rancia"): ("orca-rancia", "headless"),
    ("ausente", "resuelve"): ("solo-orca", "orca"),
    ("ausente", "inconsultable"): ("orca-inconsultable", "headless"),
    ("rancia", "ausente"): ("herdr-rancia", "headless"),
    ("rancia", "rancia"): ("identidades-rancias", "headless"),
    ("rancia", "resuelve"): ("solo-orca", "orca"),
    ("rancia", "inconsultable"): ("herdr-rancia", "headless"),
    ("resuelve", "ausente"): ("solo-herdr", "herdr"),
    ("resuelve", "rancia"): ("solo-herdr", "herdr"),
    ("resuelve", "resuelve"): ("ambas-resuelven", "headless"),
    ("resuelve", "inconsultable"): ("solo-herdr", "herdr"),
    ("inconsultable", "ausente"): ("herdr-inconsultable", "headless"),
    ("inconsultable", "rancia"): ("herdr-inconsultable", "headless"),
    ("inconsultable", "resuelve"): ("solo-orca", "orca"),
    ("inconsultable", "inconsultable"): ("mecanica-ilegible", None),
}


def emitir(codigo, verbo, resultado, plataforma, **campos):
    """Imprime el sobre universal y devuelve el codigo de proceso."""
    salida = {"verbo": verbo, "resultado": resultado, "plataforma": plataforma}
    salida.update(campos)
    print(json.dumps(salida, ensure_ascii=True, separators=(",", ":")))
    return codigo


def _consultar(cmd, causa=None):
    """Sondea un CLI y devuelve (ok, texto); `causa` recibe el motivo cuando `ok` es falso.

    Lee bytes y decodifica aca: con `text=True` la decodificacion la hace un hilo lector de
    `subprocess`, donde el UnicodeDecodeError NO propaga —el except de esta funcion no puede
    verlo— y el fallo vuelve como exito con la salida en None. Ante una salida ilegible el texto
    se devuelve igual, con reemplazo: la politica estricta es la que clasifica, y doce llamadores
    rebanan ese texto para su `detalle`, que sin el quedaria mudo.
    """
    def anotar(motivo):
        if causa is not None:
            causa.append(motivo)

    try:
        proceso = subprocess.run(cmd, capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        anotar("sin-ejecutable")
        return False, ""
    ok = proceso.returncode == 0
    crudo = proceso.stdout if ok else proceso.stderr
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError:
        anotar("salida-ilegible")
        return False, crudo.decode("utf-8", errors="replace")
    if not ok:
        anotar("consulta-fallida")
    return ok, texto


def _json(texto):
    try:
        return json.loads(texto)
    except (TypeError, ValueError):
        return {}


def _panes(texto):
    return {p.get("pane_id") for p in _json(texto).get("result", {}).get("panes", []) if p.get("pane_id")}


def _terminales(texto):
    raiz = _json(texto)
    return {p.get("handle") for p in raiz.get("result", raiz).get("terminals", []) if p.get("handle")}


def estado_identidad(var, cmd, extraer, causa=None):
    """Devuelve ausente, rancia, resuelve o inconsultable para una identidad.

    `causa` va por parametro de salida y no como tercer elemento del retorno: el otro llamador
    —`_identidad_registrada`, que consume la retoma— desempaqueta dos y no publica motivos.
    """
    valor = os.environ.get(var)
    if not valor:
        return "ausente", None
    ok, salida = _consultar(cmd, causa)
    if not ok:
        return "inconsultable", valor
    return ("resuelve" if valor in extraer(salida) else "rancia"), valor


def detectar(args):
    causa_herdr, causa_orca = [], []
    herdr, hp = estado_identidad("HERDR_PANE_ID", ["herdr", "pane", "list"], _panes, causa_herdr)
    orca, op = estado_identidad("ORCA_TERMINAL_HANDLE", ["orca", "terminal", "list", "--json"], _terminales, causa_orca)
    identidades = {"herdr": {"estado": herdr, "valor": hp}, "orca": {"estado": orca, "valor": op}}
    # la clave se omite cuando no hubo fallo: en null seria indistinguible de un fallo sin motivo
    for clave, motivos in (("herdr", causa_herdr), ("orca", causa_orca)):
        if motivos:
            identidades[clave]["causa"] = motivos[-1]
    caso, plataforma = DESTINOS[(herdr, orca)]
    if plataforma is None:
        return emitir(3, "detectar", "error", None, causa=caso, detalle="no se pudieron consultar los registros vivos", identidades=identidades)
    afirmativo = plataforma != "headless"
    return emitir(0 if afirmativo else 1, "detectar", "afirmativo" if afirmativo else "adverso", plataforma,
                  adaptador=(plataforma if afirmativo else None), caso=caso,
                  panel_propio=(hp if plataforma == "herdr" else op if plataforma == "orca" else None),
                  identidades=identidades, acredita={"identidad": "nativo"}, evidencia=["registro-vivo"])


def _leer_json(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


class LedgerIlegible(Exception):
    """Una linea del ledger no es JSON. Se distingue del ledger ausente, que es vacio y legitimo."""


def _ledger(ruta):
    if not os.path.exists(ruta):
        return []
    entradas = []
    with open(ruta, encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, 1):
            if not linea.strip():
                continue
            try:
                dato = json.loads(linea)
            except json.JSONDecodeError as error:
                # No se saltea la linea: saltearla perderia un efecto en silencio, y el ledger es la
                # autoridad de lo que ocurrio. Se corta con una causa que el llamador pueda emitir.
                raise LedgerIlegible("linea %d: %s" % (numero, error)) from error
            # JSON valido no alcanza: todo consumidor hace `.get("efecto")`, asi que una cadena, una
            # lista o un numero pasan el decodificador y revientan un nivel mas abajo, donde ya no hay
            # causa que emitir. La forma es parte de la legibilidad, no un detalle del tipo.
            if not isinstance(dato, dict):
                raise LedgerIlegible("linea %d: se esperaba un objeto y llego %s" % (numero, type(dato).__name__))
            entradas.append(dato)
    return entradas


def _asentar(ruta, dato):
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(dato, ensure_ascii=True) + "\n")


ESQUEMA_RETOMADO = 1
CAMPOS_RETOMADO = ("plataforma", "esquema", "consentimiento", "workspace")
CAUSAS_RETOMA = {
    "ausente": "la plataforma registrada ya no expone una identidad viva",
    "inconsultable": "no se pudo consultar el registro vivo de la plataforma registrada",
    "rancia": "la identidad viva es de otra instalacion que la registrada",
    "esquema": "el documento declara un esquema de transporte que esta version no interpreta",
    "propietario": "el propietario de la corrida registrada no esta vivo",
    "adopcion": "la corrida sigue en vuelo bajo otro propietario y no hay consentimiento",
}


def _identidad_registrada(plataforma):
    """Consulta la identidad de la plataforma persistida y de ninguna otra: la retoma no detecta."""
    if plataforma == "herdr":
        return estado_identidad("HERDR_PANE_ID", ["herdr", "pane", "list"], _panes)
    if plataforma == "orca":
        return estado_identidad("ORCA_TERMINAL_HANDLE", ["orca", "terminal", "list", "--json"], _terminales)
    return "ausente", None


def _en_vuelo(corrida):
    entradas = _ledger(corrida)
    cerrados = {x.get("panel") for x in entradas if x.get("efecto") == "cerrar"}
    return bool({x.get("panel") for x in entradas if x.get("efecto") == "lanzar"} - cerrados)


def _escalar_retomado(bruto):
    """Un escalar del frontmatter. Recorta el comentario de linea solo si va tras espacio."""
    valor = bruto.strip()
    if valor[:1] not in ("'", '"'):
        corte = re.search(r"(?:^|\s)#", valor)
        if corte:
            valor = valor[: corte.start()].strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
        return valor[1:-1]
    if valor in ("", "null", "~"):
        return None
    if valor in ("true", "false"):
        return valor == "true"
    return int(valor) if re.fullmatch(r"-?\d+", valor) else valor


def _bloque_retomado(ruta, clave):
    """Lee UN bloque del frontmatter de `handoff.md`, que es lo unico que la retoma consume.

    Lector dirigido, no un parser de YAML: reconoce la apertura del frontmatter, la clave pedida y
    sus hijos escalares indentados. Cualquier otra construccion —una lista, un anidamiento mas
    hondo— hace que el bloque no se reconozca, y eso degrada, que es la salida segura. Se lee el
    `.md` y no un `.json` porque el documento de retomado que el flujo escribe es ese: contra un
    `handoff.md` real, `json.load` levantaba un traceback en vez de degradar.
    """
    try:
        lineas = Path(ruta).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lineas or lineas[0].strip() != "---":
        return None
    try:
        fin = lineas.index("---", 1)
    except ValueError:
        return None
    bloque, dentro = {}, False
    for linea in lineas[1:fin]:
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        sangrado = linea[:1] in (" ", "\t")
        if not sangrado:
            dentro = linea.split(":", 1)[0].strip() == clave
            continue
        if not dentro or ":" not in linea:
            continue
        nombre, _, resto = linea.strip().partition(":")
        bloque[nombre.strip()] = _escalar_retomado(resto)
    return bloque or None


def _degradar(causa, recuperado):
    return emitir(1, "retomar", "adverso", "headless", ofertas=0, causa=causa, recuperado=recuperado,
                  acredita={"retoma": "documento"}, evidencia=["retomado"])


def retomar(args):
    transporte = _bloque_retomado(args.retomar, "transporte")
    if not isinstance(transporte, dict) or not transporte.get("plataforma"):
        return _degradar(None, None)
    recuperado = {campo: transporte.get(campo) for campo in CAMPOS_RETOMADO}
    if recuperado["esquema"] != ESQUEMA_RETOMADO:
        return _degradar(CAUSAS_RETOMA["esquema"], recuperado)
    estado, _ = _identidad_registrada(recuperado["plataforma"])
    if estado != "resuelve":
        return _degradar(CAUSAS_RETOMA[estado], recuperado)
    corrida = transporte.get("corrida")
    propietario = next((x for x in _ledger(corrida) if x.get("efecto") == "propietario"), None) if corrida else None
    if propietario:
        vivo, _ = _vivo(recuperado["plataforma"], propietario.get("panel"))
        if not vivo:
            return _degradar(CAUSAS_RETOMA["propietario"], recuperado)
        if propietario.get("sesion") != args.sesion and _en_vuelo(corrida) and not args.consentimiento:
            return _degradar(CAUSAS_RETOMA["adopcion"], recuperado)
    return emitir(0, "retomar", "afirmativo", recuperado["plataforma"], ofertas=0, causa=None,
                  recuperado=recuperado, acredita={"retoma": "documento"}, evidencia=["retomado"])




def _conductor_vigente(entradas):
    """El conductor tras un prefijo del ledger. `None` significa cadena rota, que es el observable
    de haber tenido dos conductores o ninguno: un traspaso que no sale de quien conduce la rompe."""
    actual = None
    for x in entradas:
        if x.get("efecto") != "conductor":
            continue
        if x.get("de") != actual:
            return None
        actual = x.get("a")
    return actual



def lanzar_conductor(args):
    """No transfiere la autoridad, y eso es el resultado de haber intentado que lo hiciera.

    Cinco rondas de revision sobre este verbo: cada intento de acreditar la transferencia por
    observacion acoto una superficie y dejo elegible la contigua —el acuse en archivo, la terminal
    observada, la marca buscada, el dispatch y la sesion destinataria—. La ultima salida candidata
    era el canal que Orca dice atribuir, y se midio: `orchestration send --type worker_done` **sin**
    `--from` lo rechaza con `sender_not_assignee`, pero **con** `--from <handle del asignado>` lo
    acepta desde cualquier terminal, falseando `from_handle` y `sender_pane_key`, y completando la
    task y el dispatch. La evidencia esta en `pruebas-herdr.md` → Parte 37.

    Conclusion: ninguna superficie medida sostiene un acuse **atribuible a la sesion nueva** frente a
    un llamador decidido, y un booleano de CLI no es un gate porque el verbo no puede constatar quien
    lo corrio. Asi que el verbo se comporta como lo declaraba el documento de plataforma antes de que
    se implementara: devuelve la mecanica como no obtenida y el conductor original sigue conduciendo.

    No consulta la plataforma. Preguntarle algo insinuaria que alguna respuesta podria cambiar el
    resultado, y ninguna puede: lo que falta no es un dato sino una capacidad que el medio no ofrece.
    """
    # El conductor vigente sale de los efectos `conductor` del ledger, y este adaptador NO los
    # produce: `crear` y `lanzar` asientan otros efectos, y el unico productor de aquellos era el
    # camino retirado. Asi que en una corrida normal el campo sale nulo, y eso se DECLARA en vez de
    # presentarlo como si nombrara a alguien: un nulo silencioso en un campo que el documento
    # prometia como autoridad es peor que decir que no se puede obtener.
    vigente = _conductor_vigente(_ledger(args.corrida))
    return emitir(1, "lanzar-conductor", "adverso", args.plataforma, causa="mecanica-no-obtenida",
                  detalle="ninguna superficie medida acredita un acuse atribuible a la sesion nueva; ver pruebas-herdr.md Parte 37",
                  conductor=vigente, transferido=False,
                  recuperacion="la conduccion se transfiere a mano: el launcher imprime el comando de arranque y una persona lo ejecuta, igual que en la via headless",
                  # El ledger es un JSONL local y apendable: registra lo que se escribio, no quien lo
                  # escribio. Llamarlo `ledger` a secas insinuaba una autoridad de identidad que no
                  # tiene —medido: una fila inventada a mano sale como conductor acreditado—, y es el
                  # mismo error que este verbo existe para no cometer.
                  acredita={"transferencia": "no-obtenida",
                            "conductor": "declarado-en-ledger-local" if vigente else "no-registrado"},
                  evidencia=["ledger"])


def _cerrar(plataforma, panel):
    return _consultar(["herdr", "pane", "close", panel] if plataforma == "herdr" else ["orca", "terminal", "close", "--terminal", panel, "--json"])


def _panel_creado(plataforma, texto):
    resultado = _json(texto).get("result", {})
    if plataforma == "herdr":
        return resultado.get("pane_id") or resultado.get("pane", {}).get("pane_id")
    return resultado.get("split", {}).get("handle") or resultado.get("handle")


def _worktree(plataforma, panel):
    if plataforma == "herdr":
        ok, texto = _consultar(["herdr", "pane", "get", panel])
        dato = _json(texto).get("result", {})
        return ok, dato.get("cwd") or dato.get("pane", {}).get("cwd")
    ok, texto = _consultar(["orca", "terminal", "list", "--json"])
    datos = _json(texto).get("result", {}).get("terminals", [])
    return ok, next((x.get("worktreePath") for x in datos if x.get("handle") == panel), None)


def crear(args):
    try:
        consentimiento = _leer_json(args.consentimiento)
        alcance = consentimiento["alcance"]
        digest = hashlib.sha256(consentimiento["mostrado"].encode()).hexdigest()
        if digest != consentimiento["digest"] or consentimiento["corrida"] != args.corrida:
            raise ValueError("consentimiento no coincide")
        cwd = str(Path(args.cwd).resolve())
        if not cwd.startswith(str(Path(alcance["worktree"]).resolve()) + os.sep) and cwd != str(Path(alcance["worktree"]).resolve()):
            raise ValueError("cwd fuera del alcance")
        if args.rol not in alcance["roles"]:
            raise ValueError("rol fuera del alcance")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return emitir(2, "crear", "error", args.plataforma, causa="consentimiento-invalido", detalle=str(error))
    existentes = _ledger(args.corrida)
    anterior_mismo_rol = next((x for x in existentes if x.get("efecto") == "crear" and x.get("rol") == args.rol and x.get("desde") == args.desde), None)
    ordinal = anterior_mismo_rol["ordinal"] if anterior_mismo_rol else sum(x.get("efecto") == "crear" for x in existentes) + 1
    clave = hashlib.sha256(f"{args.corrida}|{args.rol}|{args.desde}|{ordinal}".encode()).hexdigest()
    previo = next((x for x in existentes if x.get("efecto") == "crear" and x.get("clave") == clave), None)
    if previo:
        return emitir(0, "crear", "afirmativo", args.plataforma, panel=previo["panel"], desde=args.desde, direccion=args.direccion, orden=f"worker-{previo['ordinal']}", replayed=True, acredita={"geometria": "derivado"}, evidencia=["ledger"])
    if sum(x.get("efecto") == "crear" for x in existentes) >= alcance["paneles_max"]:
        return emitir(2, "crear", "error", args.plataforma, causa="consentimiento-agotado", detalle="paneles_max alcanzado")
    direccion = {"herdr": {"derecha": "right", "abajo": "down"}, "orca": {"derecha": "vertical", "abajo": "horizontal"}}[args.plataforma][args.direccion]
    cmd = (["herdr", "pane", "split", args.desde, "--direction", direccion, "--cwd", cwd] if args.plataforma == "herdr" else ["orca", "terminal", "split", "--terminal", args.desde, "--direction", direccion, "--json"])
    ok, texto = _consultar(cmd)
    if not ok:
        return emitir(1, "crear", "adverso", args.plataforma, causa="split-rechazado", detalle=texto[:200])
    panel = _panel_creado(args.plataforma, texto)
    if not panel:
        return emitir(3, "crear", "error", args.plataforma, causa="identificador-no-obtenible", detalle=texto[:200])
    _, real = _worktree(args.plataforma, panel)
    if real is None or Path(real).resolve() != Path(cwd).resolve():
        _cerrar(args.plataforma, panel)
        return emitir(1, "crear", "adverso", args.plataforma, causa="panel-fuera-del-alcance", detalle="el panel se cerro", panel_cerrado=panel)
    _asentar(args.corrida, {"efecto": "crear", "clave": clave, "panel": panel, "rol": args.rol, "desde": args.desde, "ordinal": ordinal})
    return emitir(0, "crear", "afirmativo", args.plataforma, panel=panel, desde=args.desde, direccion=args.direccion, orden=f"worker-{ordinal}", replayed=False, acredita={"geometria": "nativo" if args.plataforma == "herdr" else "derivado"}, evidencia=["split"])


def _perfil(ruta):
    perfil = _leer_json(ruta)
    for campo in ("modelo", "esfuerzo"):
        if not isinstance(perfil.get(campo), dict) or not {"valor", "fuente", "escalon"} <= perfil[campo].keys():
            raise ValueError("perfil incompleto")
    return perfil


def _flags(familia, perfil):
    # Autoridad: skills/sdd-flow/reference.md, "Enum portable de esfuerzo".
    # Si cambia esa tabla, este mapeo de CLI debe cambiar con ella.
    esfuerzo = {"bajo": "low", "medio": "medium", "alto": "high", "muy_alto": "xhigh", "maximo": "max"}.get(perfil["esfuerzo"]["valor"])
    if esfuerzo is None:
        raise ValueError("esfuerzo fuera del dominio portable")
    flags = [familia, "--model", str(perfil["modelo"]["valor"])]
    return flags + (["-c", "model_reasoning_effort=" + esfuerzo] if familia == "codex" else ["--effort", esfuerzo])


def _prompt(encargo, artefacto):
    return f"Lee el encargo en {Path(encargo).resolve()}. Persiste tu salida con archivo temporal hermano y renombre atomico en {Path(artefacto).resolve()}. Declara hash_encargo_leido con el digest que leiste."


def lanzar(args):
    try:
        perfil, contenido = _perfil(args.perfil), Path(args.encargo).read_bytes()
        flags = _flags(args.familia, perfil)
        limite, intervalo = int(args.limite), float(args.intervalo)
        if limite < 1 or intervalo < 0:
            raise ValueError("presupuesto de readiness invalido")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return emitir(2, "lanzar", "error", args.plataforma, causa="entrada-ilegible", detalle=str(error))
    if not any(x.get("efecto") == "crear" and x.get("panel") == args.panel for x in _ledger(args.corrida)):
        return emitir(1, "lanzar", "adverso", args.plataforma, causa="panel-no-asentado", detalle="el panel no pertenece a la corrida")
    hash_encargo = hashlib.sha256(contenido).hexdigest()
    previos = [x for x in _ledger(args.corrida) if x.get("efecto") == "lanzar"]
    if any(x.get("panel") != args.panel and x.get("familia") == args.familia for x in previos):
        return emitir(1, "lanzar", "adverso", args.plataforma, causa="familia-duplicada", detalle="la corrida ya despacho un worker de esa familia")
    if any(x.get("hash_encargo") != hash_encargo for x in previos):
        return emitir(1, "lanzar", "adverso", args.plataforma, causa="encargo-divergente", detalle="el encargo difiere del de los workers ya despachados")
    prompt = _prompt(args.encargo, args.artefacto)
    if args.plataforma == "herdr":
        nombre = args.rol
        # Medido contra el CLI real: `agent start` NO admite `--encargo` —lo rechaza en el parser,
        # antes de mirar el panel—, y el encargo ya viaja por ruta dentro del prompt. Y como `--kind`
        # fija el ejecutable, los argumentos tras `--` son solo los del agente: repetir ahi el
        # ejecutable no falla, lo entrega como PROMPT INICIAL y le consume un turno al worker antes
        # de que lea su encargo. El ejecutable se descarta aca y no en `_flags`, que se lo debe a la
        # otra plataforma: alli los flags se envian como linea de shell y ahi el ejecutable ES el
        # primer elemento.
        _, *argumentos = flags
        comando = ["herdr", "agent", "start", nombre, "--kind", args.familia, "--pane", args.panel, "--"] + argumentos
        ok, texto = _consultar(comando)
        if not ok:
            return emitir(1, "lanzar", "adverso", "herdr", causa="agent-start-rechazado", detalle=texto[:200], invocacion=comando)
        ok, texto = _consultar(["herdr", "agent", "prompt", nombre, prompt])
        if not ok:
            return emitir(1, "lanzar", "adverso", "herdr", causa="prompt-rechazado", detalle=texto[:200], invocacion=comando)
        extra = {"run": None, "task": None, "dispatch": None, "agente": nombre, "readiness": {"estado": "interactive_ready"}, "acuse": {"estado": "prompt-aceptado"}}
    else:
        comandos = []
        # El agente lo arranca ESTE verbo dentro del panel que `crear` dejo vacio, con su perfil en
        # las banderas del propio CLI: medido, `worker-start --terminal` se ADJUNTA a un agente que ya
        # corre —declara `launch.requested {agent,model,effort} = null`— y sus notas prohiben
        # `--model`/`--effort` junto a `--terminal`. Un split sin agente deja `agentIdentity` ausente
        # y la readiness no puede llegar nunca.
        envio_cmd = ["orca", "terminal", "send", "--terminal", args.panel, "--text", " ".join(flags), "--enter", "--json"]
        ok, texto = _consultar(envio_cmd); comandos.append(envio_cmd)
        if not ok:
            return emitir(1, "lanzar", "adverso", "orca", causa="agente-no-arrancado", detalle=texto[:200], invocacion=comandos)
        listo = False
        for _ in range(limite):
            ok, estado = _consultar(["orca", "terminal", "list", "--json"])
            terminal = next((x for x in _json(estado).get("result", {}).get("terminals", []) if x.get("handle") == args.panel), {}) if ok else {}
            if terminal.get("agentIdentity") == args.familia:
                listo = True
                break
            time.sleep(intervalo)
        if not listo:
            return emitir(1, "lanzar", "adverso", "orca", causa="readiness-no-alcanzada", detalle="agentIdentity no alcanzo la familia", invocacion=comandos, segundos_readiness=limite * intervalo)
        run_cmd = ["orca", "orchestration", "run-create", "--objective", f"transporte: {args.rol}", "--json"]
        ok, texto = _consultar(run_cmd); comandos.append(run_cmd)
        run = _json(texto).get("result", {}).get("run", {}).get("id") if ok else None
        if not run:
            return emitir(3, "lanzar", "error", "orca", causa="run-no-creado", detalle=texto[:200])
        task_cmd = ["orca", "orchestration", "task-create", "--run", run, "--task-title", f"transporte {args.rol}", "--spec", prompt, "--json"]
        ok, texto = _consultar(task_cmd); comandos.append(task_cmd)
        task = _json(texto).get("result", {}).get("task", {}).get("id") if ok else None
        if not task:
            return emitir(3, "lanzar", "error", "orca", causa="task-no-creado", detalle=texto[:200])
        # Medido contra el esquema de la plataforma: `worker-start` no admite `--encargo` (el encargo
        # viaja dentro de `--spec` de task-create), no admite posicionales, y sus notas declaran que
        # `--model`/`--effort` **no se combinan con `--terminal`**. Colocar el worker en un panel
        # propio y elegirle perfil son excluyentes en Orca, asi que el perfil queda OMITIDO: se
        # registra lo que se pidio, y el sobre no lo acredita.
        inicio_cmd = ["orca", "orchestration", "worker-start", "--run", run, "--task", task,
                      "--terminal", args.panel, "--json"]
        ok, texto = _consultar(inicio_cmd); comandos.append(inicio_cmd)
        respuesta = _json(texto).get("result", {}) if ok else {}
        dispatch = respuesta.get("dispatchId") or respuesta.get("dispatch", {}).get("id")
        if not dispatch:
            return emitir(1, "lanzar", "adverso", "orca", causa="adjuntar-rechazado", detalle=texto[:200], run=run, task=task)
        comando = comandos
        extra = {"run": run, "task": task, "dispatch": dispatch, "agente": args.familia, "readiness": {"estado": respuesta.get("state", "ready"), "etapa": respuesta.get("stage", "input_accepted")}, "acuse": {"estado": respuesta.get("stage", "input_accepted")}}
    _asentar(args.corrida, {"efecto": "lanzar", "panel": args.panel, "familia": args.familia, "hash_encargo": hash_encargo, "perfil_lanzado": perfil})
    return emitir(0, "lanzar", "afirmativo", args.plataforma, panel=args.panel, familia=args.familia, intento=1, hash_encargo=hash_encargo, artefacto=str(Path(args.artefacto).resolve()), perfil_lanzado=perfil, efectivo_observable=False, invocacion=comando, replayed=False, acredita={"readiness": "nativo" if args.plataforma == "herdr" else "derivado", "perfil": "derivado"}, evidencia=["invocacion", "ruta-encargo"], **extra)


def _fecha(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone(timezone.utc)


def _vivo(plataforma, panel):
    if plataforma == "orca":
        ok, texto = _consultar(["orca", "terminal", "list", "--json"])
        if not ok:
            return None, None
        terminal = next((x for x in _json(texto).get("result", {}).get("terminals", []) if x.get("handle") == panel), None)
        return terminal is not None, terminal or {}
    ok, texto = _consultar(["herdr", "pane", "get", panel])
    if not ok:
        return False, {}
    dato = _json(texto).get("result", {})
    return dato.get("alive", True) is not False, dato


def enviar(args):
    try:
        contenido = Path(args.encargo).read_bytes()
        if int(args.intento) < 2 or int(args.limite) < 1 or float(args.intervalo) < 0:
            raise ValueError("reintento o presupuesto invalido")
    except (OSError, ValueError) as error:
        return emitir(2, "enviar", "error", args.plataforma, causa="entrada-ilegible", detalle=str(error))
    if not any(x.get("efecto") == "lanzar" and x.get("panel") == args.panel for x in _ledger(args.corrida)):
        return emitir(1, "enviar", "adverso", args.plataforma, causa="panel-no-lanzado", detalle="el panel no fue lanzado", acredita={"acuse": "derivado"}, evidencia=["ledger"])
    if args.plataforma == "orca":
        return emitir(3, "enviar", "error", "orca", causa="reintento-no-obtenible", detalle="el dispatch activo impide reenviar")
    ok, previo = _consultar(["herdr", "agent", "get", args.panel])
    secuencia = _json(previo).get("result", {}).get("state_change_seq") if ok else None
    prompt = _prompt(args.encargo, args.artefacto)
    ok, texto = _consultar(["herdr", "agent", "prompt", args.panel, prompt])
    if not ok:
        return emitir(1, "enviar", "adverso", "herdr", causa="prompt-rechazado", detalle=texto[:200], acredita={"acuse": "nativo"}, evidencia=["agent-prompt"])
    aceptado = False
    for _ in range(int(args.limite)):
        ok, estado = _consultar(["herdr", "agent", "get", args.panel])
        actual = _json(estado).get("result", {}).get("state_change_seq") if ok else None
        if secuencia is not None and actual is not None and actual > secuencia:
            aceptado = True; break
        time.sleep(float(args.intervalo))
    digest = hashlib.sha256(contenido).hexdigest()
    if not aceptado:
        return emitir(1, "enviar", "adverso", "herdr", causa="acuse-no-obtenido", detalle="state_change_seq no avanzo", intento=int(args.intento), hash_encargo=digest, acredita={"acuse": "nativo"}, evidencia=["agent-get"])
    _asentar(args.corrida, {"efecto": "enviar", "panel": args.panel, "intento": int(args.intento), "hash_encargo": digest})
    return emitir(0, "enviar", "afirmativo", "herdr", intento=int(args.intento), hash_encargo=digest, acredita={"acuse": "nativo"}, evidencia=["state_change_seq"])


def esperar(args):
    if args.corrida:
        entradas = _ledger(args.corrida)
        lanzados = {x.get("panel") for x in entradas if x.get("efecto") == "lanzar"}
        pendientes = sorted({x.get("panel") for x in entradas if x.get("efecto") == "crear"} - lanzados)
        if pendientes:
            return emitir(1, "esperar", "adverso", args.plataforma, causa="fan-out-incompleto",
                          detalle="quedan paneles creados sin despachar", pendientes=pendientes)
    try:
        actual = hashlib.sha256(Path(args.encargo).read_bytes()).hexdigest()
        vencido = datetime.now(timezone.utc) >= _fecha(args.vence_en)
    except (OSError, ValueError) as error:
        return emitir(2, "esperar", "error", args.plataforma, causa="entrada-ilegible", detalle=str(error))
    presente = Path(args.artefacto).exists()
    cierre = False
    if presente:
        ok, _ = _consultar([sys.executable, str(Path(__file__).with_name("status.py")), args.artefacto])
        cierre = ok
    vivo, dato = _vivo(args.plataforma, args.panel)
    if vivo is None:
        return emitir(3, "esperar", "error", args.plataforma, causa="liveness-no-obtenible", detalle="no se pudo consultar el panel")
    estado_agente = None
    if args.plataforma == "herdr":
        ok, texto = _consultar(["herdr", "agent", "get", args.panel])
        if ok:
            estado_agente = _json(texto).get("result", {}).get("agent_status")
    # La terminalidad la da el artefacto VALIDO, no su existencia. Un archivo a medio escribir
    # existe, y leerlo como terminal deja de esperar antes de que el worker publique: el estado
    # baja un escalon y el proceso sigue mandando mientras siga vivo.
    if presente and cierre:
        estado, autoridad = ("terminado-vivo" if vivo else "terminado"), "artefacto"
    elif not vivo:
        estado, autoridad = "muerto", "liveness"
    elif vencido:
        estado, autoridad = "vencido", "deadline"
    elif estado_agente in ("interactive_ready", "ready", "idle"):
        estado, autoridad = "listo", "estado_agente"
    elif estado_agente in ("blocked", "waiting_approval"):
        estado, autoridad = "bloqueado", "estado_agente"
    else:
        estado, autoridad = "trabajando", "liveness"
    vigente = actual == args.hash_encargo
    codigo = 0 if estado.startswith("terminado") and vigente else 1
    resultado = "afirmativo" if codigo == 0 else "adverso"
    return emitir(codigo, "esperar", resultado, args.plataforma, estado=estado, fuente_estado=autoridad, autoridad=autoridad, artefacto_presente=presente, cierre_marcado=cierre, intento_vigente=vigente, hash_encargo_actual=actual, estado_agente=estado_agente, acredita={"liveness": "nativo" if args.plataforma == "herdr" else "derivado", "estado_agente": "nativo" if args.plataforma == "herdr" else "omitido"}, evidencia=["ruta-artefacto", "panel", "hash-encargo"])


def _digest_declarado(ruta):
    texto = Path(ruta).read_text(encoding="utf-8")
    dato = _json(texto)
    if isinstance(dato, dict) and "hash_encargo_leido" in dato:
        return dato["hash_encargo_leido"]
    hallado = re.search(r'"hash_encargo_leido"\s*:\s*"([0-9a-f]+)"', texto)
    return hallado.group(1) if hallado else None


def _pipeline(args):
    raiz = Path(__file__).parent
    pasos = [[sys.executable, str(raiz / "status.py"), args.crudo]]
    if args.sin_paginar:
        pasos += [[sys.executable, str(raiz / "split.py"), args.crudo, args.indice, args.detalle], [sys.executable, str(raiz / "validador.py"), args.indice, args.detalle, args.familia, args.rol, args.modo]]
    else:
        pasos += [[sys.executable, str(raiz / "split-paginado.py"), args.crudo, args.base, str(args.por_pagina)], [sys.executable, str(raiz / "validador-paginado.py"), args.base, str(Path(args.base).parent / ("detail-" + Path(args.base).name + ".md"))]]
    for numero, comando in enumerate(pasos):
        # reemplazo y no estricto: estos hijos son los scripts de la propia skill, que emiten en la
        # codificacion local del sistema. Con estricto los dos flujos vuelven None y la
        # concatenacion de abajo levanta TypeError, justo en el camino de error de la cosecha.
        proceso = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proceso.returncode:
            return proceso.returncode, ("status" if numero == 0 else "split" if numero == 1 else "validador"), proceso.stdout + proceso.stderr, pasos
    return 0, "validador", pasos[-1] and "", pasos


def cosechar(args):
    if not Path(args.crudo).exists():
        return emitir(2, "cosechar", "error", args.plataforma, causa="crudo-ausente", detalle="el artefacto no existe")
    try:
        declarado = _digest_declarado(args.crudo)
    except OSError as error:
        return emitir(2, "cosechar", "error", args.plataforma, causa="entrada-ilegible", detalle=str(error))
    if declarado is None or declarado != args.hash_encargo:
        detalle = "hash_encargo_leido ausente" if declarado is None else f"declarado {declarado}, asignado {args.hash_encargo}"
        return emitir(1, "cosechar", "adverso", args.plataforma, etapa="digest", veredicto="rechazado", etapas=[{"digest": "ausente" if declarado is None else "distinto"}], salida=detalle, acredita={"pipeline": "derivado", "digest_declarado": "derivado"}, evidencia=["artefacto"])
    codigo, etapa, salida, pasos = _pipeline(args)
    if codigo:
        return emitir(codigo, "cosechar", "adverso", args.plataforma, etapa=etapa, veredicto="rechazado", etapas=[{"digest": "ok"}, {etapa: "rechazado"}], salida=salida, acredita={"pipeline": "derivado", "digest_declarado": "derivado"}, evidencia=["pipeline"])
    acuse = None
    if args.plataforma == "orca" and args.run:
        ok, texto = _consultar(["orca", "orchestration", "check", "--run", args.run])
        lote = _json(texto).get("result", {}).get("messages", []) if ok else []
        entrega = _json(texto).get("result", {}).get("deliveryId") if ok else None
        try:
            for mensaje in lote: _asentar(args.corrida, {"efecto": "buzon", "dispatch": mensaje.get("dispatch"), "worker": mensaje.get("worker"), "mensaje": mensaje})
        except OSError:
            acuse = {"deliveryId": entrega, "mensajes": len(lote), "asentados": 0, "acusado": False}
        else:
            acusado = bool(entrega and _consultar(["orca", "orchestration", "check", "--run", args.run, "--ack", entrega])[0])
            acuse = {"deliveryId": entrega, "mensajes": len(lote), "asentados": len(lote), "acusado": acusado}
    _asentar(args.corrida, {"efecto": "cosechar", "crudo": str(Path(args.crudo).resolve()), "contribuyente": "informe-cosechado"})
    return emitir(0, "cosechar", "afirmativo", args.plataforma, etapa="validador", veredicto="aceptado", etapas=[{"digest": "ok"}, {"pipeline": "ok"}], acuse_cosechado=acuse, acredita={"pipeline": "derivado", "digest_declarado": "derivado"}, evidencia=["pipeline", "artefacto"])


def _nombre(dato):
    return dato.get("name") or dato.get("title") or dato.get("label")


def renombrar(args):
    if args.plataforma == "herdr":
        ok, antes = _consultar(["herdr", "pane", "list"])
        if not ok:
            return emitir(3, "renombrar", "error", "herdr", causa="panel-no-consultable", detalle=antes[:200])
        ok, texto = _consultar(["herdr", "pane", "rename", args.panel, args.nombre])
        if not ok:
            return emitir(1, "renombrar", "adverso", "herdr", aplicado=False, causa="renombrado-rechazado", detalle=texto[:200], motivo_omision=None, acredita={"nombre": "nativo"}, evidencia=["pane-rename"])
        ok, texto = _consultar(["herdr", "pane", "get", args.panel])
        dato = _json(texto).get("result", {})
        leido = _nombre(dato)
        return emitir(0 if leido == args.nombre else 1, "renombrar", "afirmativo" if leido == args.nombre else "adverso", "herdr", panel=args.panel, aplicado=leido == args.nombre, nombre_leido=leido, alcance_real="panel", hermanos=[], arrastrados=[], motivo_omision=None, acredita={"nombre": "nativo"}, evidencia=["pane-get"])
    ok, texto = _consultar(["orca", "terminal", "list", "--json"])
    terminales = _json(texto).get("result", {}).get("terminals", []) if ok else []
    propio = next((x for x in terminales if x.get("handle") == args.panel), None)
    if not propio:
        return emitir(1, "renombrar", "adverso", "orca", aplicado=False, causa="panel-ausente", detalle="panel no vivo", motivo_omision="panel no disponible", acredita={"nombre": "omitido"}, evidencia=["terminal-list"])
    hermanos = [x for x in terminales if x.get("tabId") == propio.get("tabId") and x.get("handle") != args.panel]
    ok, texto = _consultar(["orca", "terminal", "rename", "--terminal", args.panel, "--title", args.nombre, "--json"])
    if not ok:
        return emitir(1, "renombrar", "adverso", "orca", aplicado=False, causa="renombrado-rechazado", detalle=texto[:200], motivo_omision="no se pudo medir el alcance", acredita={"nombre": "omitido"}, evidencia=["terminal-rename"])
    ok, texto = _consultar(["orca", "terminal", "list", "--json"])
    despues = _json(texto).get("result", {}).get("terminals", []) if ok else []
    arrastrados = [x.get("handle") for x in despues if x.get("handle") in {h.get("handle") for h in hermanos} and _nombre(x) == args.nombre]
    leido = _nombre(next((x for x in despues if x.get("handle") == args.panel), {}))
    omision = "el renombrado alcanza la pestana" if arrastrados else "el alcance del panel no se pudo acreditar"
    return emitir(0, "renombrar", "afirmativo", "orca", panel=args.panel, aplicado=False, nombre_leido=leido, alcance_real="pestana", hermanos=[x.get("handle") for x in hermanos], arrastrados=arrastrados, motivo_omision=omision, acredita={"nombre": "omitido"}, evidencia=["terminal-list"])


def cerrar(args):
    vivo, dato = _vivo(args.plataforma, args.panel)
    if vivo is None:
        return emitir(3, "cerrar", "error", args.plataforma, causa="cese-no-medible", detalle="panel no consultable")
    if not vivo:
        return emitir(1, "cerrar", "adverso", args.plataforma, modo=args.modo, cerrado=True, cese_acreditado=False, metodo="ninguno", pasos=[], residuales=["ya-estaba-cerrado"], archivado=False, acredita={"cese": "derivado", "archivado": "omitido"}, evidencia=["panel"])
    pasos = []
    if args.plataforma == "herdr":
        ok, texto = _consultar(["herdr", "pane", "process-info", args.panel]); pasos.append("process-info")
        grupo = _json(texto).get("result", {}).get("process_group") if ok else None
        _consultar(["herdr", "pane", "close", args.panel]); pasos.append("pane-close")
        if grupo is None:
            residuales, medido = ["grupo-no-medido"], False
        else:
            try:
                proceso = subprocess.run(["pgrep", "-g", str(grupo)], capture_output=True, text=True, timeout=15)
                medido, residuales = True, proceso.stdout.split()
            except (OSError, subprocess.SubprocessError):
                medido, residuales = False, ["conteo-no-medido"]
        acreditado = medido and not residuales and args.modo == "liquidar"
        if acreditado and args.corrida:
            _asentar(args.corrida, {"efecto": "cerrar", "panel": args.panel})
        return emitir(0 if acreditado else 1, "cerrar", "afirmativo" if acreditado else "adverso", "herdr", modo=args.modo, cerrado=True, cese_acreditado=acreditado, clasificacion="un-solo-uso", residuales_propios=len(residuales), reutilizacion="sin-reuso", metodo="pane-close", pasos=pasos, residuales=residuales, archivado=False, acredita={"cese": "nativo" if medido else "omitido", "archivado": "omitido"}, evidencia=["process-info", "pgrep"])
    ok_close, _ = _consultar(["orca", "terminal", "close", "--terminal", args.panel, "--json"]); pasos.append("terminal-close")
    residuales = [] if ok_close else ["terminal-close-fallido"]
    estado_terminal = None
    if not args.dispatch:
        residuales.append("sin-dispatch-no-medible")
    else:
        accion = "worker-release" if args.modo == "liquidar" else "worker-abandon"
        ok, _ = _consultar(["orca", "orchestration", accion, "--dispatch", args.dispatch, "--json"]); pasos.append(accion)
        if not ok:
            residuales.append("dispatch-no-liberado")
        # El codigo de salida de `release` NO acredita el cese: la plataforma declara que solo
        # `release_unknown` sale 1, y que `retained`, `release_pending` y `already_released` salen 0.
        # `retained` es literalmente el worker todavia activo, o una identidad que Orca no pudo
        # probar. Lo unico que acredita es su propia contabilidad, leida despues del intento.
        ok_estado, texto = _consultar(["orca", "orchestration", "worker-list", "--json"]); pasos.append("worker-list")
        fila = next((w for w in _json(texto).get("result", {}).get("workers", []) if w.get("dispatchId") == args.dispatch), None) if ok_estado else None
        estado_terminal = fila.get("terminalState") if fila else None
        if estado_terminal != "released":
            residuales.append("terminalState:" + str(estado_terminal))
    acreditado = args.modo == "liquidar" and not residuales
    # Solo un cese acreditado sale del vuelo. Asentar un cierre no acreditado seria peor que no
    # asentarlo: la retoma dejaria de pedir adopcion sobre un panel que puede seguir escribiendo.
    if acreditado and args.corrida:
        _asentar(args.corrida, {"efecto": "cerrar", "panel": args.panel})
    return emitir(0 if acreditado else 1, "cerrar", "afirmativo" if acreditado else "adverso", "orca", modo=args.modo, cerrado=ok_close, cese_acreditado=acreditado, clasificacion="un-solo-uso", residuales_propios=len(residuales), reutilizacion="sin-reuso", metodo="terminal-close", pasos=pasos, residuales=residuales, estado_terminal=estado_terminal, archivado=False, acredita={"cese": "nativo" if estado_terminal else "omitido", "archivado": "omitido"}, evidencia=pasos)


def _armar_stub(codigo):
    """Inyecta la guarda de contrato tras el shebang: ningun stub de `orca` se escribe sin ella."""
    return codigo.replace("#!/usr/bin/env python3", "#!/usr/bin/env python3" + GUARDA_STUB, 1)


def _stub_herdr(ruta, registro, cwd):
    codigo = '''#!/usr/bin/env python3
import json, os, sys
a=sys.argv[1:]
with open(os.environ["TERMINAL_LOG"],"a") as f: f.write(json.dumps(a)+"\\n")
if a[:2] == ["pane","split"]:
 n=sum(1 for x in open(os.environ["TERMINAL_LOG"]) if "split" in x)
 print(json.dumps({"result":{"pane_id":"worker-"+str(n)}}))
elif a[:2] == ["pane","get"]:
 print(json.dumps({"result":{"cwd":os.environ["TERMINAL_CWD"]}}))
elif a[:2] == ["pane","list"]:
 print(json.dumps({"result":{"panes":[{"pane_id":"conductor","rect":{"x":0,"y":0,"width":10,"height":10},"tab_id":"tab-1"},{"pane_id":"worker-1","rect":{"x":10,"y":0,"width":10,"height":10},"tab_id":"tab-1"},{"pane_id":"worker-2","rect":{"x":10,"y":10,"width":10,"height":10},"tab_id":"tab-1"}]}}))
else: print(json.dumps({"result":{}}))
'''
    archivo = Path(ruta) / "herdr"
    archivo.write_text(_armar_stub(codigo), encoding="utf-8")
    archivo.chmod(0o755)


def _ejecutar_crear(raiz, registro):
    binario, cwd = raiz / "bin", raiz / "worktree"
    binario.mkdir(parents=True); cwd.mkdir()
    _stub_herdr(binario, registro, cwd)
    corrida, consentimiento = raiz / "corrida.jsonl", raiz / "consentimiento.json"
    mostrado = "oferta"
    consentimiento.write_text(json.dumps({"corrida": str(corrida), "mostrado": mostrado, "digest": hashlib.sha256(mostrado.encode()).hexdigest(), "momento": "2026-01-01T00:00:00+00:00", "alcance": {"worktree": str(cwd), "paneles_max": 2, "roles": ["w1", "w2"]}}), encoding="utf-8")
    entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(registro), "TERMINAL_CWD": str(cwd)}
    base = [sys.executable, __file__, "crear", "--corrida", str(corrida), "--plataforma", "herdr", "--cwd", str(cwd), "--consentimiento", str(consentimiento)]
    salida1 = subprocess.run(base + ["--rol", "w1", "--desde", "conductor", "--direccion", "derecha"], env=entorno, capture_output=True, text=True)
    salida2 = subprocess.run(base + ["--rol", "w2", "--desde", "worker-1", "--direccion", "abajo"], env=entorno, capture_output=True, text=True)
    return salida1, salida2


def _stub_orca(ruta):
    codigo = '''#!/usr/bin/env python3
import json, os, sys
a=sys.argv[1:]
with open(os.environ["TERMINAL_LOG"],"a") as f: f.write(json.dumps(a)+"\\n")
if a[:2] == ["orchestration","run-create"]: r={"run":{"id":"run-1"}}
elif a[:2] == ["orchestration","task-create"]: r={"task":{"id":"task-1"}}
elif a[:2] == ["orchestration","worker-start"]: r={"dispatchId":"dispatch-1","state":"ready","stage":"input_accepted"}
elif a[:2] == ["terminal","list"]: r={"terminals":[{"handle":"panel-1","agentIdentity":"codex"}]}
else: r={}
print(json.dumps({"result":r}))
'''
    archivo = Path(ruta) / "orca"
    archivo.write_text(_armar_stub(codigo), encoding="utf-8")
    archivo.chmod(0o755)


def _stub_orca_layout(ruta):
    codigo = '''#!/usr/bin/env python3
import json, os, sys
a=sys.argv[1:]
with open(os.environ["TERMINAL_LOG"],"a") as f: f.write(json.dumps(a)+"\\n")
if a[:2] == ["terminal","split"]:
 n=sum(1 for x in open(os.environ["TERMINAL_LOG"]) if "split" in x)
 print(json.dumps({"result":{"split":{"handle":"worker-"+str(n)}}}))
elif a[:2] == ["terminal","list"]:
 n=sum(1 for x in open(os.environ["TERMINAL_LOG"]) if "split" in x)
 ts=[{"handle":"worker-"+str(i),"worktreePath":os.environ["TERMINAL_CWD"],"tabId":"tab-1"} for i in range(1,n+1)]
 print(json.dumps({"result":{"terminals":ts}}))
else: print(json.dumps({"result":{}}))
'''
    archivo = Path(ruta) / "orca"
    archivo.write_text(_armar_stub(codigo), encoding="utf-8")
    archivo.chmod(0o755)


def _ejecutar_crear_orca(raiz, registro):
    binario, cwd = raiz / "bin", raiz / "worktree"
    binario.mkdir(parents=True); cwd.mkdir(); _stub_orca_layout(binario)
    corrida, consentimiento = raiz / "corrida.jsonl", raiz / "consentimiento.json"
    mostrado = "oferta"
    consentimiento.write_text(json.dumps({"corrida": str(corrida), "mostrado": mostrado, "digest": hashlib.sha256(mostrado.encode()).hexdigest(), "momento": "2026-01-01T00:00:00+00:00", "alcance": {"worktree": str(cwd), "paneles_max": 2, "roles": ["w1", "w2"]}}), encoding="utf-8")
    entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(registro), "TERMINAL_CWD": str(cwd)}
    base = [sys.executable, __file__, "crear", "--corrida", str(corrida), "--plataforma", "orca", "--cwd", str(cwd), "--consentimiento", str(consentimiento)]
    uno = subprocess.run(base + ["--rol", "w1", "--desde", "conductor", "--direccion", "derecha"], env=entorno, capture_output=True, text=True)
    dos = subprocess.run(base + ["--rol", "w2", "--desde", "worker-1", "--direccion", "abajo"], env=entorno, capture_output=True, text=True)
    return uno, dos, entorno


def _autotest(nombre):
    if nombre in ("estados", "intervencion", "cosecha", "renombrar", "omision", "ciclo", "cese"):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); binario = raiz / "bin"; binario.mkdir(); log = raiz / "log"
            falso = '''#!/usr/bin/env python3
import json,os,sys
a=sys.argv[1:]
open(os.environ["TERMINAL_LOG"],"a").write(json.dumps(a)+"\\n")
if sys.argv[0].endswith("orca") and a[:2]==["terminal","list"]:
 cerrada=any(json.loads(x)[:2]==["terminal","close"] and "p" in json.loads(x) for x in open(os.environ["TERMINAL_LOG"]))
 r={"terminals":([{"handle":"conductor","tabId":"t"},{"handle":"hermano","tabId":"t"}] + ([] if cerrada or os.environ.get("MUERTO")=="1" else [{"handle":"p","tabId":"t","title":"rol","agentIdentity":"codex"}]))}
elif sys.argv[0].endswith("orca") and a[:2]==["orchestration","worker-list"]:
 r={"workers":[{"dispatchId":"d","terminalState":os.environ.get("ORCA_TERMINAL_STATE","released")}]}
elif sys.argv[0].endswith("orca") and a[:2]==["orchestration","check"]: r=({"deliveryId":"d1","messages":[{"dispatch":"d1","worker":"w1"},{"dispatch":"d2","worker":"w2"}]} if "--ack" not in a else {"ok":True})
elif sys.argv[0].endswith("herdr") and a[:2]==["pane","get"]: r={"alive":os.environ.get("MUERTO")!="1","name":"rol"}
elif sys.argv[0].endswith("herdr") and a[:2]==["pane","process-info"]: r={}
elif sys.argv[0].endswith("herdr") and a[:2]==["agent","get"]: r={"agent_status":"working","state_change_seq":2}
else: r={"ok":True}
print(json.dumps({"result":r}))
'''
            for comando in ("orca", "herdr"):
                ruta = binario / comando; ruta.write_text(_armar_stub(falso), encoding="utf-8"); ruta.chmod(0o755)
            entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(log)}
            encargo, crudo, corrida = raiz / "encargo", raiz / "crudo", raiz / "corrida"
            encargo.write_text("uno", encoding="utf-8"); digest = hashlib.sha256(b"uno").hexdigest()
            base = [sys.executable, __file__]
            if nombre == "estados":
                def sondeo(plataforma, vivo, artefacto, vence):
                    crudo.unlink(missing_ok=True)
                    if artefacto: crudo.write_text("STATUS: done\n" if artefacto != "invalido" else "INVALID ARTIFACT\n", encoding="utf-8")
                    p = subprocess.run(base + ["esperar", "--plataforma", plataforma, "--panel", "p", "--artefacto", str(crudo), "--encargo", str(encargo), "--hash-encargo", digest, "--vence-en", vence], env=entorno | ({"MUERTO":"1"} if not vivo else {}), capture_output=True, text=True)
                    return json.loads(p.stdout)
                futuro, pasado = "2999-01-01T00:00:00+00:00", "2000-01-01T00:00:00+00:00"
                for plataforma in ("orca", "herdr"):
                    assert sondeo(plataforma, False, True, pasado)["estado"] == "terminado"
                    assert sondeo(plataforma, True, True, pasado)["estado"] == "terminado-vivo"
                    assert sondeo(plataforma, True, False, futuro)["estado"] == "trabajando"
                    assert sondeo(plataforma, True, False, pasado)["estado"] == "vencido"
                    assert sondeo(plataforma, False, False, pasado)["estado"] == "muerto"
                # un artefacto que EXISTE pero que el validador rechaza no es terminal: si lo fuera,
                # el sondeo dejaria de esperar antes de que el worker publique. La pareja de abajo es
                # lo que discrimina: mismo `artefacto_presente`, distinto estado.
                for plataforma in ("orca", "herdr"):
                    invalido_vivo = sondeo(plataforma, True, "invalido", futuro)
                    assert invalido_vivo["artefacto_presente"] is True and invalido_vivo["cierre_marcado"] is False
                    assert invalido_vivo["estado"] == "trabajando", invalido_vivo["estado"]
                    invalido_muerto = sondeo(plataforma, False, "invalido", pasado)
                    assert invalido_muerto["estado"] == "muerto", invalido_muerto["estado"]
                assert sondeo("herdr", True, False, futuro)["acredita"]["estado_agente"] == "nativo"
                assert sondeo("orca", True, False, futuro)["acredita"]["estado_agente"] == "omitido"
            elif nombre == "intervencion":
                encargo.write_text("dos", encoding="utf-8")
                p = subprocess.run(base + ["esperar", "--plataforma", "orca", "--panel", "p", "--artefacto", str(crudo), "--encargo", str(encargo), "--hash-encargo", digest, "--vence-en", "2999-01-01T00:00:00+00:00"], env=entorno, capture_output=True, text=True)
                assert json.loads(p.stdout)["intento_vigente"] is False
                encargo.write_text("uno", encoding="utf-8")
                crudo.write_text('{"hash_encargo_leido":"otro"}\\nSTATUS: done\\n', encoding="utf-8")
                p = subprocess.run(base + ["cosechar", "--plataforma", "orca", "--crudo", str(crudo), "--base", str(raiz / "base"), "--familia", "codex", "--rol", "r", "--modo", "m", "--corrida", str(corrida), "--hash-encargo", digest], env=entorno, capture_output=True, text=True)
                assert p.returncode == 1 and json.loads(p.stdout)["etapa"] == "digest"
            elif nombre == "cosecha":
                valido = '{"hash_encargo_leido":"' + digest + '"}\\n## Índice\\n| ID | T | P | I | E |\\n|---|---|---|---|---|\\n| COD-R-MOD-001 | x | high | low | N/A: x |\\n## Detalle\\n### COD-R-MOD-001\\nSTATUS: done\\n'
                valido = valido.replace("\\n", "\n")
                crudo.write_text(valido, encoding="utf-8")
                comun = ["cosechar", "--plataforma", "orca", "--crudo", str(crudo), "--base", str(raiz / "base"), "--familia", "COD", "--rol", "R", "--modo", "MOD", "--corrida", str(corrida), "--hash-encargo", digest, "--sin-paginar", "--indice", str(raiz / "indice"), "--detalle", str(raiz / "detalle")]
                p = subprocess.run(base + comun + ["--run", "r1"], env=entorno, capture_output=True, text=True)
                directo = subprocess.run([sys.executable, str(Path(__file__).with_name("validador.py")), str(raiz / "indice"), str(raiz / "detalle"), "COD", "R", "MOD"], capture_output=True, text=True)
                assert p.returncode == directo.returncode == 0 and p.stdout and len([x for x in _ledger(corrida) if x.get("efecto") == "buzon"]) == 2
                traza = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
                assert any(x[:2] == ["orchestration", "check"] and "--ack" in x for x in traza)
                crudo.write_text(valido.replace("COD-R-MOD-001 | x", "malo | x"), encoding="utf-8")
                p = subprocess.run(base + comun, env=entorno, capture_output=True, text=True)
                directo = subprocess.run([sys.executable, str(Path(__file__).with_name("validador.py")), str(raiz / "indice"), str(raiz / "detalle"), "COD", "R", "MOD"], capture_output=True, text=True)
                assert p.returncode == directo.returncode == 1
            elif nombre == "renombrar":
                p = subprocess.run(base + ["renombrar", "--plataforma", "herdr", "--panel", "p", "--nombre", "rol"], env=entorno, capture_output=True, text=True)
                assert p.returncode == 0 and json.loads(p.stdout)["nombre_leido"] == "rol"
            elif nombre == "omision":
                p = subprocess.run(base + ["renombrar", "--plataforma", "orca", "--panel", "p", "--nombre", "rol"], env=entorno, capture_output=True, text=True)
                assert p.returncode == 0 and not json.loads(p.stdout)["aplicado"]
            elif nombre == "ciclo":
                def sembrar(*paneles):
                    corrida.write_text("\n".join(json.dumps({"efecto":"lanzar", "panel": panel, "clasificacion":"un-solo-uso"}) for panel in paneles) + "\n", encoding="utf-8")
                sembrar("p", "hermano")
                p = subprocess.run(base + ["cerrar", "--plataforma", "orca", "--panel", "p", "--modo", "liquidar", "--dispatch", "d", "--corrida", str(corrida)], env=entorno, capture_output=True, text=True)
                sobre = json.loads(p.stdout)
                vivos = _json(subprocess.run(["orca", "terminal", "list", "--json"], env=entorno, capture_output=True, text=True).stdout)["result"]["terminals"]
                clasificados = [x for x in _ledger(corrida) if x.get("efecto") == "lanzar"]
                assert p.returncode == 0 and sobre["clasificacion"] == "un-solo-uso" and sobre["residuales_propios"] == 0 and sobre["reutilizacion"] == "sin-reuso"
                assert {x["handle"] for x in vivos} == {"conductor", "hermano"} and all(x.get("clasificacion") for x in clasificados)
                # el cese acreditado SALE del vuelo: sin este asiento la retoma sigue exigiendo
                # adopcion sobre un panel liquidado
                assert sobre["estado_terminal"] == "released"
                assert [x for x in _ledger(corrida) if x.get("efecto") == "cerrar"] == [{"efecto": "cerrar", "panel": "p"}]
                # el asiento es POR PANEL: `p` sale del vuelo y `hermano`, que nadie cerro, sigue.
                # Afirmar que la corrida entera dejo de estar en vuelo seria mas fuerte y falso.
                assert _en_vuelo(corrida), "hermano sigue lanzado y sin cerrar"
                # `retained` es el worker TODAVIA activo, y `release` sale 0 igual: lo unico que
                # discrimina es la contabilidad de la plataforma, leida despues del intento
                # `hermano` y no `q`: el panel tiene que estar VIVO para llegar a la rama del cese.
                # Con un panel que la plataforma ya no lista, el verbo sale por `ya-estaba-cerrado`
                # y el caso no ejerce nada de lo que viene a probar.
                sembrar("hermano", "otro")
                p = subprocess.run(base + ["cerrar", "--plataforma", "orca", "--panel", "hermano", "--modo", "liquidar", "--dispatch", "d", "--corrida", str(corrida)], env=entorno | {"ORCA_TERMINAL_STATE": "retained"}, capture_output=True, text=True)
                retenido = json.loads(p.stdout)
                assert p.returncode == 1 and retenido["cese_acreditado"] is False
                assert retenido["residuales"] == ["terminalState:retained"], retenido["residuales"]
                assert [x for x in _ledger(corrida) if x.get("efecto") == "cerrar"] == [], "un cese no acreditado asento el cierre"
                assert _en_vuelo(corrida)
            else:
                p = subprocess.run(base + ["cerrar", "--plataforma", "herdr", "--panel", "p", "--modo", "liquidar"], env=entorno, capture_output=True, text=True)
                assert p.returncode == 1 and not json.loads(p.stdout)["cese_acreditado"]
            print(f"autotest-{nombre}: ok")
            return 0
    if nombre == "determinismo":
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); registro1, registro2 = raiz / "uno.log", raiz / "dos.log"
            uno = _ejecutar_crear(raiz / "uno", registro1)
            dos = _ejecutar_crear(raiz / "dos", registro2)
            assert uno[0].returncode == dos[0].returncode == 0
            assert uno[1].returncode == dos[1].returncode == 0
            def normalizada(ruta):
                return [["<cwd>" if x.endswith("/worktree") else x for x in fila] for fila in (json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines())]
            assert normalizada(registro1) == normalizada(registro2)
            assert json.loads(uno[0].stdout)["orden"] == "worker-1"
    elif nombre == "layout":
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); registro = raiz / "traza.log"
            primero, segundo = _ejecutar_crear(raiz / "herdr", registro)
            traza = [json.loads(x) for x in registro.read_text(encoding="utf-8").splitlines()]
            splits = [x for x in traza if x[:2] == ["pane", "split"]]
            assert primero.returncode == segundo.returncode == 0
            assert splits[0][2] == "conductor" and splits[0][4] == "right"
            assert splits[1][2] == "worker-1" and splits[1][4] == "down"
            entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(raiz / "herdr" / "bin") + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(registro), "TERMINAL_CWD": str(raiz / "herdr" / "worktree")}
            panes = _json(subprocess.run(["herdr", "pane", "list"], env=entorno, capture_output=True, text=True).stdout)["result"]["panes"]
            rects = {p["pane_id"]: p["rect"] for p in panes}
            assert rects["worker-1"]["x"] >= rects["conductor"]["x"] + rects["conductor"]["width"]
            assert rects["worker-2"]["y"] >= rects["worker-1"]["y"] + rects["worker-1"]["height"]
            registro_orca = raiz / "orca.log"
            uno, dos, entorno_orca = _ejecutar_crear_orca(raiz / "orca", registro_orca)
            traza_orca = [json.loads(x) for x in registro_orca.read_text(encoding="utf-8").splitlines()]
            splits_orca = [x for x in traza_orca if x[:2] == ["terminal", "split"]]
            terminales = _json(subprocess.run(["orca", "terminal", "list", "--json"], env=entorno_orca, capture_output=True, text=True).stdout)["result"]["terminals"]
            assert uno.returncode == dos.returncode == 0
            assert splits_orca[0][splits_orca[0].index("--direction") + 1] == "vertical"
            assert splits_orca[1][splits_orca[1].index("--direction") + 1] == "horizontal"
            assert {t["tabId"] for t in terminales} == {"tab-1"}
    elif nombre == "perfil":
        perfil = {"modelo": {"valor": "x", "fuente": "rol", "escalon": 1}, "esfuerzo": {"valor": "alto", "fuente": "rol", "escalon": 1}}
        comando = _flags("codex", perfil)
        assert perfil["modelo"]["valor"] in comando and "model_reasoning_effort=high" in comando
        # `_flags` sola no acredita nada: lo que AC-9 pide es que cada campo llegue a la INVOCACION.
        # Probar solo el armador dejaba la fila verde mientras la rama Orca no pasaba el perfil.
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); binario = raiz / "bin"; binario.mkdir(); _stub_orca(binario)
            encargo, ruta_perfil, corrida, artefacto, registro = raiz / "e", raiz / "p.json", raiz / "c.jsonl", raiz / "a", raiz / "t.log"
            encargo.write_text("x", encoding="utf-8")
            ruta_perfil.write_text(json.dumps({"modelo": {"valor": "gpt-5-codex", "fuente": "rol", "escalon": 1}, "esfuerzo": {"valor": "alto", "fuente": "rol", "escalon": 1}}), encoding="utf-8")
            corrida.write_text(json.dumps({"efecto": "crear", "panel": "panel-1"}) + "\n", encoding="utf-8")
            entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(registro)}
            proceso = subprocess.run([sys.executable, __file__, "lanzar", "--corrida", str(corrida), "--plataforma", "orca", "--panel", "panel-1",
                                      "--familia", "codex", "--rol", "w", "--perfil", str(ruta_perfil), "--encargo", str(encargo),
                                      "--artefacto", str(artefacto), "--limite", "3", "--intervalo", "0"], env=entorno, capture_output=True, text=True)
            assert proceso.returncode == 0, proceso.stdout[:300]
            sobre = json.loads(proceso.stdout)
            plano = " ".join(" ".join(x) for x in sobre["invocacion"])
            assert "gpt-5-codex" in plano, "el modelo no llego a la invocacion en Orca"
            assert "model_reasoning_effort=high" in plano, "el esfuerzo no llego a la invocacion en Orca"
            assert all(campo["fuente"] for campo in sobre["perfil_lanzado"].values())
            assert sobre["efectivo_observable"] is False
            # rama negativa: el panel hospeda `codex`, asi que pedir `claude` no alcanza readiness.
            # Sin este caso, anular la comparacion de familia deja el autotest verde.
            ajeno = subprocess.run([sys.executable, __file__, "lanzar", "--corrida", str(corrida), "--plataforma", "orca", "--panel", "panel-1",
                                    "--familia", "claude", "--rol", "w", "--perfil", str(ruta_perfil), "--encargo", str(encargo),
                                    "--artefacto", str(artefacto), "--limite", "2", "--intervalo", "0"], env=entorno, capture_output=True, text=True)
            fallido = json.loads(ajeno.stdout)
            assert ajeno.returncode == 1 and fallido["causa"] == "readiness-no-alcanzada", ajeno.stdout[:200]
    elif nombre == "encargo":
        contenido = b"x" * 131072
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); binario = raiz / "bin"; binario.mkdir(); _stub_orca(binario)
            encargo, perfil, corrida, artefacto, registro = raiz / "encargo", raiz / "perfil.json", raiz / "corrida.jsonl", raiz / "artefacto", raiz / "traza.log"
            encargo.write_bytes(contenido)
            perfil.write_text(json.dumps({"modelo": {"valor": "x", "fuente": "rol", "escalon": 1}, "esfuerzo": {"valor": "alto", "fuente": "rol", "escalon": 1}}), encoding="utf-8")
            corrida.write_text(json.dumps({"efecto": "crear", "panel": "panel-1"}) + "\n", encoding="utf-8")
            entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(registro)}
            proceso = subprocess.run([sys.executable, __file__, "lanzar", "--corrida", str(corrida), "--plataforma", "orca", "--panel", "panel-1", "--familia", "codex", "--rol", "w1", "--perfil", str(perfil), "--encargo", str(encargo), "--artefacto", str(artefacto), "--limite", "1", "--intervalo", "0"], env=entorno, capture_output=True, text=True)
            sobre = json.loads(proceso.stdout)
            comando = next(x for x in (json.loads(x) for x in registro.read_text(encoding="utf-8").splitlines()) if x[:2] == ["orchestration", "worker-start"])
            assert proceso.returncode == 0 and len(" ".join(comando).encode()) < 4096
            assert sobre["hash_encargo"] == hashlib.sha256(contenido).hexdigest()
            assert "renombre atomico" in _prompt(encargo, artefacto) and "hash_encargo_leido" in _prompt(encargo, artefacto)
    elif nombre == "mudanza":
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); binario = raiz / "bin"; binario.mkdir(); registro = raiz / "traza.log"
            # El stub responde que SI a todo. Es deliberado: si el verbo consultara, una respuesta
            # afirmativa podria cambiar su resultado, y lo que esta prueba afirma es que ninguna
            # puede. Un stub que negara haria pasar el caso por la razon equivocada.
            codigo = '''#!/usr/bin/env python3
import json, os, sys
a=sys.argv[1:]
with open(os.environ["TERMINAL_LOG"],"a") as f: f.write(json.dumps(a)+"\\n")
print(json.dumps({"result":{"dispatch":{"launch_token_hash":"tok-1"},
                            "worker":{"agent_terminal_handle":"term_nueva"},
                            "terminal":{"handle":"term_nueva","tail":["listo"]}}}))
'''
            for comando in ("orca", "herdr"):
                archivo = binario / comando; archivo.write_text(_armar_stub(codigo), encoding="utf-8"); archivo.chmod(0o755)
            entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(registro)}
            flujo = raiz / "flujo"; flujo.mkdir(); (flujo / "plan.md").write_text("el plan del flujo\n", encoding="utf-8")
            digest = hashlib.sha256((flujo / "plan.md").read_bytes()).hexdigest()
            corrida = raiz / "corrida.jsonl"
            _asentar(corrida, {"efecto": "conductor", "de": None, "a": "original"})
            acuse = raiz / "acuse.json"
            acuse.write_text(json.dumps({"token": "tok-1", "flujo": str(flujo), "digest": digest}), encoding="utf-8")

            def mudar(plataforma, extra=()):
                antes = len(_ledger(corrida)); registro.unlink(missing_ok=True); registro.touch()
                proceso = subprocess.run([sys.executable, __file__, "lanzar-conductor", "--corrida", str(corrida),
                                          "--plataforma", plataforma, *extra],
                                         env=entorno, capture_output=True, text=True)
                traza = [json.loads(x) for x in registro.read_text(encoding="utf-8").splitlines() if x.strip()]
                return json.loads(proceso.stdout), proceso.returncode, len(_ledger(corrida)) - antes, traza

            # El acuse mas favorable que se pueda construir —token que coincide, flujo real, digest
            # correcto, panel derivable, terminal legible— y las dos plataformas. Ninguna combinacion
            # transfiere: la mecanica no esta obtenida, y esa es la afirmacion entera de la fila.
            completo = ["--dispatch", "ctx_1", "--flujo", str(flujo), "--acuse", str(acuse), "--sesion", "nueva"]
            casos = [("orca con todo a favor", "orca", completo), ("herdr con todo a favor", "herdr", completo),
                     ("orca sin argumentos opcionales", "orca", []), ("herdr sin argumentos opcionales", "herdr", [])]
            for etiqueta, plataforma, extra in casos:
                sobre, codigo_salida, crecio, traza = mudar(plataforma, extra)
                assert codigo_salida == 1, etiqueta
                assert sobre["causa"] == "mecanica-no-obtenida", f"{etiqueta}: llego {sobre['causa']!r}"
                assert sobre["transferido"] is False and sobre["conductor"] == "original", etiqueta
                assert sobre["acredita"]["transferencia"] == "no-obtenida", etiqueta
                # el conductor no se puede nombrar en una corrida normal: este adaptador no produce
                # efectos `conductor`. El sobre lo DECLARA en vez de devolver un nulo silencioso.
                assert sobre["acredita"]["conductor"] == "declarado-en-ledger-local", etiqueta
                assert sobre["recuperacion"], etiqueta
                assert crecio == 0, f"{etiqueta}: un rechazo asento en el ledger"
                # no consulta la plataforma: preguntarle insinuaria que alguna respuesta podria
                # cambiar el resultado, y la medicion de la Parte 37 dice que ninguna puede
                assert traza == [], f"{etiqueta}: consulto la plataforma: {traza}"
            # exactamente UN conductor en todo instante, que es lo que AC-13 exige de la secuencia
            entradas = _ledger(corrida)
            conductores = [_conductor_vigente(entradas[:n]) for n in range(1, len(entradas) + 1)]
            assert conductores == ["original"], conductores
            # y la rama que importa en produccion: un ledger SIN efectos `conductor` —el caso real,
            # porque `crear` y `lanzar` asientan otros— sale con el campo nulo y declarado
            sin_conductor = raiz / "sin-conductor.jsonl"
            _asentar(sin_conductor, {"efecto": "crear", "panel": "p", "rol": "codex"})
            proceso = subprocess.run([sys.executable, __file__, "lanzar-conductor", "--corrida", str(sin_conductor),
                                      "--plataforma", "orca"], env=entorno, capture_output=True, text=True)
            real = json.loads(proceso.stdout)
            assert proceso.returncode == 1 and real["causa"] == "mecanica-no-obtenida"
            assert real["conductor"] is None and real["acredita"]["conductor"] == "no-registrado", real
            # un ledger con una fila inventada a mano SI nombra un conductor, y por eso la etiqueta
            # no puede decir `ledger` a secas: el archivo registra lo que se escribio, no quien
            inventado = raiz / "inventado.jsonl"
            _asentar(inventado, {"efecto": "conductor", "de": None, "a": "inventada"})
            proceso = subprocess.run([sys.executable, __file__, "lanzar-conductor", "--corrida", str(inventado),
                                      "--plataforma", "orca"], env=entorno, capture_output=True, text=True)
            falso = json.loads(proceso.stdout)
            assert falso["acredita"]["conductor"] == "declarado-en-ledger-local", falso["acredita"]
            # un ledger ilegible sale por SOBRE, no por traceback: el verbo que existe para rechazar
            # con seguridad no puede morir antes de emitir su rechazo
            roto = raiz / "roto.jsonl"
            roto.write_text('{"efecto": "crear", "panel": "p"}\n{"efecto": "cond', encoding="utf-8")
            proceso = subprocess.run([sys.executable, __file__, "lanzar-conductor", "--corrida", str(roto),
                                      "--plataforma", "orca"], env=entorno, capture_output=True, text=True)
            assert proceso.returncode == 2 and not proceso.stderr.strip(), proceso.stderr[-200:]
            ilegible = json.loads(proceso.stdout)
            assert ilegible["causa"] == "ledger-ilegible" and "linea 2" in ilegible["detalle"], ilegible
            # una linea JSON VALIDA que no es objeto tambien tiene que salir por sobre: pasa el
            # decodificador y reventaba un nivel mas abajo, en el `.get("efecto")` de cada consumidor
            for contenido, esperado_tipo in (('"solo una cadena"\n', "str"), ("[1, 2]\n", "list"), ("42\n", "int")):
                roto.write_text(contenido, encoding="utf-8")
                proceso = subprocess.run([sys.executable, __file__, "lanzar-conductor", "--corrida", str(roto),
                                          "--plataforma", "orca"], env=entorno, capture_output=True, text=True)
                assert proceso.returncode == 2 and not proceso.stderr.strip(), proceso.stderr[-200:]
                sobre_roto = json.loads(proceso.stdout)
                assert sobre_roto["causa"] == "ledger-ilegible" and esperado_tipo in sobre_roto["detalle"], sobre_roto

    elif nombre == "orden":
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); binario = raiz / "bin"; binario.mkdir(); registro = raiz / "traza.log"
            codigo = '''#!/usr/bin/env python3
import json, os, sys
a=sys.argv[1:]
with open(os.environ["TERMINAL_LOG"],"a") as f: f.write(json.dumps(a)+"\\n")
if a[:2] == ["orchestration","run-create"]: r={"run":{"id":"run-1"}}
elif a[:2] == ["orchestration","task-create"]: r={"task":{"id":"task-1"}}
elif a[:2] == ["orchestration","worker-start"]: r={"dispatchId":"d1","state":"ready","stage":"input_accepted"}
elif a[:2] == ["terminal","list"]: r={"terminals":[{"handle":h,"agentIdentity":h.split("-")[-1]} for h in ("panel-codex","panel-claude","panel-extra")]}
else: r={}
print(json.dumps({"result":r}))
'''
            archivo = binario / "orca"; archivo.write_text(_armar_stub(codigo), encoding="utf-8"); archivo.chmod(0o755)
            entorno = os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(registro)}
            encargo, otro, perfil = raiz / "encargo", raiz / "otro", raiz / "perfil.json"
            encargo.write_text("el mismo encargo para los dos", encoding="utf-8"); otro.write_text("distinto", encoding="utf-8")
            perfil.write_text(json.dumps({"modelo": {"valor": "x", "fuente": "rol", "escalon": 1}, "esfuerzo": {"valor": "alto", "fuente": "rol", "escalon": 1}}), encoding="utf-8")
            def corrida_con(nombre_archivo, paneles):
                ruta = raiz / nombre_archivo
                for panel in paneles: _asentar(ruta, {"efecto": "crear", "panel": panel})
                return ruta
            def correr(*argumentos):
                proceso = subprocess.run([sys.executable, __file__, *[str(x) for x in argumentos]], env=entorno, capture_output=True, text=True)
                return json.loads(proceso.stdout), proceso.returncode
            def despachar(ruta, panel, familia, cual=encargo):
                return correr("lanzar", "--corrida", ruta, "--plataforma", "orca", "--panel", panel, "--familia", familia,
                              "--rol", familia, "--perfil", perfil, "--encargo", cual, "--artefacto", raiz / f"art-{panel}", "--limite", "1", "--intervalo", "0")
            def sondear(ruta, panel, vence):
                return correr("esperar", "--corrida", ruta, "--plataforma", "orca", "--panel", panel, "--artefacto", raiz / f"art-{panel}",
                              "--encargo", encargo, "--hash-encargo", hashlib.sha256(encargo.read_bytes()).hexdigest(), "--vence-en", vence)
            futuro, pasado = "2999-01-01T00:00:00+00:00", "2000-01-01T00:00:00+00:00"
            fan = corrida_con("fan.jsonl", ("panel-codex", "panel-claude"))
            # ningun `esperar` precede al ULTIMO `lanzar`: se rechaza con cero y con uno despachado
            vacio = sondear(fan, "panel-codex", futuro)
            assert vacio[1] == 1 and vacio[0]["causa"] == "fan-out-incompleto"
            assert sorted(vacio[0]["pendientes"]) == ["panel-claude", "panel-codex"]
            uno = despachar(fan, "panel-codex", "codex")
            assert uno[1] == 0
            medio = sondear(fan, "panel-claude", futuro)
            assert medio[1] == 1 and medio[0]["causa"] == "fan-out-incompleto" and medio[0]["pendientes"] == ["panel-claude"]
            dos = despachar(fan, "panel-claude", "claude")
            assert dos[1] == 0
            # encargo identico para los dos, y un worker por familia
            digest = hashlib.sha256(encargo.read_bytes()).hexdigest()
            assert uno[0]["hash_encargo"] == dos[0]["hash_encargo"] == digest
            assert {x["familia"] for x in _ledger(fan) if x.get("efecto") == "lanzar"} == {"codex", "claude"}
            repetida = corrida_con("rep.jsonl", ("panel-codex", "panel-extra"))
            assert despachar(repetida, "panel-codex", "codex")[1] == 0
            duplicado = despachar(repetida, "panel-extra", "codex")
            assert duplicado[1] == 1 and duplicado[0]["causa"] == "familia-duplicada"
            divergente_c = corrida_con("div.jsonl", ("panel-codex", "panel-claude"))
            assert despachar(divergente_c, "panel-codex", "codex")[1] == 0
            divergente = despachar(divergente_c, "panel-claude", "claude", otro)
            assert divergente[1] == 1 and divergente[0]["causa"] == "encargo-divergente"
            # cada worker lleva SU vencimiento: el mismo sondeo, dos deadlines, dos estados
            vencido, vigente = sondear(fan, "panel-codex", pasado), sondear(fan, "panel-claude", futuro)
            assert vencido[0]["estado"] == "vencido" and vigente[0]["estado"] != "vencido"
            # los estados terminales y la forma del envelope coinciden con la sede headless
            sede = (Path(__file__).resolve().parents[1] / "reference.md").read_text(encoding="utf-8").splitlines()
            def tramo(desde, hasta):
                inicio = next(i for i, x in enumerate(sede) if x.startswith(desde))
                return sede[inicio:next(i for i, x in enumerate(sede) if i > inicio and x.startswith(hasta))]
            estados = sorted({m.group(1) for x in tramo("### Estados del worker", "**`UNAVAILABLE` lleva causa")
                              for m in [re.match(r"^\| `([A-Za-z-]+)` \|", x)] if m})
            campos = sorted({m.group(1) for x in tramo("workers:", "contributors:")
                             for m in [re.match(r"^\s+-?\s*([a-z_]+):", x)] if m})
            assert estados and campos, "la sede headless no rindio estados ni campos"
            assert estados == sorted(ESTADOS_WORKER), f"estados: {estados} != {sorted(ESTADOS_WORKER)}"
            assert campos == sorted(CAMPOS_WORKER), f"campos: {campos} != {sorted(CAMPOS_WORKER)}"
    elif nombre in ("retomado", "persistencia"):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal); binario = raiz / "bin"; binario.mkdir(); log = raiz / "log"
            falso = '''#!/usr/bin/env python3
import json,os,sys
open(os.environ["TERMINAL_LOG"],"a").write(json.dumps([os.path.basename(sys.argv[0])]+sys.argv[1:])+"\\n")
if os.environ.get("ORCA_FALLA")=="1": sys.exit(1)
print(json.dumps({"result":{"terminals":[{"handle":h,"tabId":"t"} for h in os.environ.get("ORCA_VIVOS","").split(",") if h]}}))
'''
            for comando in ("orca", "herdr"):
                ruta = binario / comando; ruta.write_text(_armar_stub(falso), encoding="utf-8"); ruta.chmod(0o755)
            corrida, documento = raiz / "corrida.jsonl", raiz / "handoff.md"
            escrito = {"plataforma": "orca", "esquema": ESQUEMA_RETOMADO, "consentimiento": str(raiz / "consentimiento.json"), "workspace": str(raiz / "wt")}
            def retoma(transporte, entorno, extra=()):
                log.unlink(missing_ok=True); log.touch()
                # el documento de retomado es el `handoff.md` que el flujo escribe, con su
                # frontmatter: un JSON sintetico no ejerce el contrato real y deja pasar un lector
                # que contra el artefacto de verdad levantaba un traceback en vez de degradar
                cuerpo = "".join("  %s: %s\n" % (k, v) for k, v in (transporte or {}).items())
                documento.write_text("---\nphase: implement\n" + ("transporte:\n" + cuerpo if transporte else "") + "---\n\ncuerpo narrativo\n", encoding="utf-8")
                proceso = subprocess.run([sys.executable, __file__, "--retomar", str(documento), "--sesion", "yo", *extra],
                                         env=os.environ | {"ORCA_CONTRATO": json.dumps({k: sorted(v) for k, v in CONTRATO_ORCA.items()}), "PATH": str(binario) + os.pathsep + os.environ["PATH"], "TERMINAL_LOG": str(log), "HERDR_PANE_ID": "otro-panel"} | entorno,
                                         capture_output=True, text=True)
                traza = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
                return json.loads(proceso.stdout), proceso.returncode, traza
            _asentar(corrida, {"efecto": "propietario", "sesion": "otra", "panel": "duenio"})
            _asentar(corrida, {"efecto": "lanzar", "panel": "duenio"})
            # la corrida propia aisla la rama de liveness: con la misma sesion, la guarda de adopcion
            # no puede dispararse, asi que un propietario muerto solo puede degradar por SU causa
            propia = raiz / "propia.jsonl"
            _asentar(propia, {"efecto": "propietario", "sesion": "yo", "panel": "duenio"})
            _asentar(propia, {"efecto": "lanzar", "panel": "duenio"})
            con_corrida = dict(escrito, corrida=str(corrida))
            vivos = {"ORCA_TERMINAL_HANDLE": "mio", "ORCA_VIVOS": "mio,duenio"}
            # el lector del ledger alcanza a MAS de un verbo, y `retomar` es otro consumidor real
            # —`cosechar` no lo es—. Se asierta la CAUSA exacta y no la ausencia de traceback:
            # "no revento" lo satisface tambien un verbo que nunca llego al lector, que es como se
            # cuela una asercion vacua.
            roto = raiz / "roto.jsonl"
            roto.write_text('{"efecto": "propietario", "sesion": "otra", "panel": "duenio"}\n{"efecto": "cond', encoding="utf-8")
            sobre_roto, codigo_roto, _ = retoma(dict(escrito, corrida=str(roto)), vivos)
            assert codigo_roto == 2 and sobre_roto["causa"] == "ledger-ilegible", sobre_roto
            assert "linea 2" in sobre_roto["detalle"], sobre_roto

            sin_campo = retoma(None, {})
            assert sin_campo[1] == 1 and sin_campo[0]["plataforma"] == "headless" and sin_campo[0]["ofertas"] == 0
            assert sin_campo[0]["causa"] is None and sin_campo[2] == []
            ausente = retoma(escrito, {"ORCA_TERMINAL_HANDLE": ""})
            inconsultable = retoma(escrito, {"ORCA_TERMINAL_HANDLE": "mio", "ORCA_FALLA": "1"})
            rancia = retoma(escrito, {"ORCA_TERMINAL_HANDLE": "mio", "ORCA_VIVOS": "ajeno"})
            viejo_esquema = retoma(dict(escrito, esquema=ESQUEMA_RETOMADO + 1), vivos)
            assert viejo_esquema[1] == 1 and viejo_esquema[0]["causa"] == CAUSAS_RETOMA["esquema"]
            causas = [x[0]["causa"] for x in (ausente, inconsultable, rancia)]
            assert all(x[1] == 1 and x[0]["plataforma"] == "headless" and x[0]["ofertas"] == 0 for x in (ausente, inconsultable, rancia))
            assert all(causas) and len(set(causas)) == 3
            muerto = retoma(dict(escrito, corrida=str(propia)), dict(vivos, ORCA_VIVOS="mio"))
            assert muerto[1] == 1 and muerto[0]["plataforma"] == "headless"
            assert muerto[0]["causa"] == CAUSAS_RETOMA["propietario"] and muerto[0]["causa"] not in causas
            adopcion = retoma(con_corrida, vivos)
            assert adopcion[1] == 1 and adopcion[0]["plataforma"] == "headless" and adopcion[0]["causa"] == CAUSAS_RETOMA["adopcion"]
            consentida = retoma(con_corrida, vivos, ("--consentimiento-adopcion",))
            resuelve = retoma(escrito, vivos)
            for sobre, codigo, traza in (consentida, resuelve):
                assert codigo == 0 and sobre["plataforma"] == "orca" and sobre["ofertas"] == 0 and sobre["causa"] is None
            if nombre == "persistencia":
                sobre, _, traza = resuelve
                assert sobre["recuperado"] == escrito
                assert [x for x in traza if x[0] == "orca"] and not [x for x in traza if x[0] == "herdr"]
    print(f"autotest-{nombre}: ok")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--casos", action="store_true")
    parser.add_argument("--verbos", action="store_true")
    parser.add_argument("--retomar")
    parser.add_argument("--sesion")
    parser.add_argument("--consentimiento-adopcion", dest="consentimiento", action="store_true")
    for nombre in ("determinismo", "layout", "perfil", "encargo", "estados", "intervencion", "cosecha", "renombrar", "omision", "ciclo", "cese", "orden", "retomado", "persistencia", "mudanza"):
        parser.add_argument(f"--autotest-{nombre}", action="store_true")
    sub = parser.add_subparsers(dest="verbo")
    sub.add_parser("detectar").add_argument("--casos", action="store_true")
    crear_p = sub.add_parser("crear")
    for campo in ("corrida", "plataforma", "rol", "desde", "direccion", "cwd", "consentimiento"):
        crear_p.add_argument("--" + campo, required=True)
    crear_p.choices = None
    lanzar_p = sub.add_parser("lanzar")
    for campo in ("corrida", "plataforma", "panel", "familia", "rol", "perfil", "encargo", "artefacto", "limite", "intervalo"):
        lanzar_p.add_argument("--" + campo, required=True)
    enviar_p = sub.add_parser("enviar")
    for campo in ("corrida", "plataforma", "panel", "encargo", "artefacto", "intento", "limite", "intervalo"):
        enviar_p.add_argument("--" + campo, required=True)
    enviar_p.add_argument("--task")
    esperar_p = sub.add_parser("esperar")
    for campo in ("plataforma", "panel", "artefacto", "encargo", "hash-encargo", "vence-en"):
        esperar_p.add_argument("--" + campo, dest=campo.replace("-", "_"), required=True)
    esperar_p.add_argument("--dispatch")
    esperar_p.add_argument("--corrida")
    cosechar_p = sub.add_parser("cosechar")
    for campo in ("plataforma", "crudo", "base", "familia", "rol", "modo", "corrida", "hash-encargo"):
        cosechar_p.add_argument("--" + campo, dest=campo.replace("-", "_"), required=True)
    cosechar_p.add_argument("--run"); cosechar_p.add_argument("--sin-paginar", action="store_true")
    cosechar_p.add_argument("--indice"); cosechar_p.add_argument("--detalle"); cosechar_p.add_argument("--por-pagina", default="100")
    renombrar_p = sub.add_parser("renombrar")
    for campo in ("plataforma", "panel", "nombre"): renombrar_p.add_argument("--" + campo, required=True)
    cerrar_p = sub.add_parser("cerrar")
    for campo in ("plataforma", "panel", "modo"): cerrar_p.add_argument("--" + campo, required=True)
    cerrar_p.add_argument("--dispatch")
    cerrar_p.add_argument("--corrida")
    conductor_p = sub.add_parser("lanzar-conductor")
    conductor_p.add_argument("--corrida", required=True)
    conductor_p.add_argument("--plataforma", required=True)
    # los demas argumentos se conservan opcionales para que una invocacion escrita contra la version
    # anterior no muera en el parser: recibe el mismo rechazo que cualquier otra, que es lo que
    # tiene que leer
    for campo in ("dispatch", "flujo", "acuse", "sesion"):
        conductor_p.add_argument("--" + campo)
    args = parser.parse_args(argv)
    for nombre in ("determinismo", "layout", "perfil", "encargo", "estados", "intervencion", "cosecha", "renombrar", "omision", "ciclo", "cese", "orden", "retomado", "persistencia", "mudanza"):
        if getattr(args, "autotest_" + nombre):
            return _autotest(nombre)
    # Un ledger ilegible sale por sobre, no por traceback, y en TODOS los verbos: el defecto vive en
    # la lectura y no en un verbo, asi que arreglarlo en uno solo dejaria a los demas reventando.
    # Un verbo cuyo trabajo es rechazar con seguridad no puede morir antes de emitir su rechazo.
    try:
        return _despachar(args, parser)
    except LedgerIlegible as error:
        return emitir(2, getattr(args, "verbo", None) or "lectura", "error",
                      getattr(args, "plataforma", None) or "headless",
                      causa="ledger-ilegible", detalle=str(error))


def _despachar(args, parser):
    if args.retomar:
        return retomar(args)
    if args.casos or getattr(args, "casos", False):
        return emitir(0, "introspeccion", "afirmativo", "headless", casos=CASOS, destinos=[{"herdr": h, "orca": o, "caso": c, "destino": d} for (h, o), (c, d) in DESTINOS.items()], acredita={"dominio": "derivado"}, evidencia=["contrato"])
    if args.verbos:
        return emitir(0, "introspeccion", "afirmativo", "headless", verbos=VERBOS, acredita={"dominio": "derivado"}, evidencia=["contrato"])
    if args.verbo == "lanzar-conductor": return lanzar_conductor(args)
    if args.verbo == "detectar": return detectar(args)
    if args.verbo == "crear":
        if args.plataforma not in ("herdr", "orca") or args.direccion not in ("derecha", "abajo"):
            return emitir(2, "crear", "error", args.plataforma, causa="invocacion-invalida", detalle="plataforma o direccion invalida")
        return crear(args)
    if args.verbo == "lanzar":
        if args.plataforma not in ("herdr", "orca") or args.familia not in ("claude", "codex"):
            return emitir(2, "lanzar", "error", args.plataforma, causa="invocacion-invalida", detalle="plataforma o familia invalida")
        return lanzar(args)
    if args.verbo == "enviar": return enviar(args)
    if args.verbo == "esperar": return esperar(args)
    if args.verbo == "cosechar": return cosechar(args)
    if args.verbo == "renombrar": return renombrar(args)
    if args.verbo == "cerrar": return cerrar(args)
    return parser.error("indique un verbo o una introspeccion")


if __name__ == "__main__":
    sys.exit(main())
