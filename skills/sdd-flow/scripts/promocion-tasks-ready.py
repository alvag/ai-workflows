"""Predicado: promueve el congelamiento inicial o refresca sus claves desde tasks-ready o
implementing sin cambiar estado; el refresh exige ledger terminal, paquete histórico, owner,
recibo y ausencia de un sobre activo, y publica o reemplaza el plan de forma atómica."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

try:
    import delivery_profile as _delivery_profile
except ImportError:
    _delivery_profile = None
    _DELIVERY_PROFILE_FAILURE = "ausente"
except Exception:
    _delivery_profile = None
    _DELIVERY_PROFILE_FAILURE = "incompatible"
else:
    _REQUIRED_DELIVERY_SYMBOLS = (
        "parse_plan_frontmatter", "read_plan_frontmatter", "resolve_delivery_pair",
        "DeliveryProfileError",
    )
    if (getattr(_delivery_profile, "DELIVERY_PROFILE_CONTRACT_VERSION", None) != 1
            or not all(hasattr(_delivery_profile, symbol)
                       for symbol in _REQUIRED_DELIVERY_SYMBOLS)):
        _DELIVERY_PROFILE_FAILURE = "incompatible"
    else:
        _DELIVERY_PROFILE_FAILURE = ""


def fallo(mensaje: str, codigo: int) -> int:
    print(f"GUARD:promocion-tasks-ready {mensaje}", file=sys.stderr)
    return codigo


def leer_header(texto: str) -> Dict[str, List[str]]:
    parsed = _delivery_profile.parse_plan_frontmatter(texto)
    campos: Dict[str, List[str]] = {
        clave: list(parsed.fields.get(clave, ()))
        for clave in ("status", "complexity", "delivery_profile", "risk", "contract_procedure",
                      "contract_frozen_version", "contract_frozen_hash")
    }
    return campos


def timestamp_valido(valor: str) -> bool:
    match = re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", valor)
    if not match:
        return False
    zona = match.group(1)
    if zona != "Z":
        horas, minutos = map(int, zona[1:].split(":"))
        if horas > 14 or minutos > 59 or (horas == 14 and minutos != 0):
            return False
    try:
        datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def clasificar_constancia(texto: str) -> str:
    paso = actor = todos = timestamp_invalido = False
    prefijo = "- `paso: congelar` · `actor: conductor` · `timestamp: "
    for linea in texto.splitlines():
        tiene_paso = "`paso: congelar`" in linea
        tiene_actor = "`actor: conductor`" in linea
        tiene_timestamp = "`timestamp: " in linea
        paso = paso or tiene_paso
        actor = actor or (tiene_paso and tiene_actor)
        todos = todos or (tiene_paso and tiene_actor and tiene_timestamp)
        if linea.startswith(prefijo) and linea.endswith("`"):
            if timestamp_valido(linea[len(prefijo) : -1]):
                return "ok"
            timestamp_invalido = True
    if not paso:
        return "paso"
    if not actor:
        return "actor"
    if not todos or timestamp_invalido:
        return "timestamp"
    return "formato/anclaje"


def ruta_cadena() -> Path:
    return (Path(__file__).resolve().parent.parent.parent
            / "cross-implement" / "scripts" / "contrato-cadena.py")


@lru_cache(maxsize=1)
def _cargar_invariantes() -> Optional[ModuleType]:
    ruta = ruta_cadena().with_name("contrato-invariantes.py")
    especificacion = importlib.util.spec_from_file_location("promocion_contrato_invariantes", ruta)
    if especificacion is None or especificacion.loader is None:
        return None
    modulo = importlib.util.module_from_spec(especificacion)
    try:
        especificacion.loader.exec_module(modulo)
    except Exception:
        return None
    return modulo if callable(getattr(modulo, "campos_linea", None)) else None


def _campos_linea(linea: str, prefijo: str = "- ") -> Dict[str, str]:
    modulo = _cargar_invariantes()
    return modulo.campos_linea(linea, prefijo) if modulo is not None else {}


def validar_cadena(plan_arg: str) -> int:
    """Corre el validador de la estructura y la cadena, y devuelve su código sin interpretarlo.

    Va acá y no en la prosa de un paso: la sede normativa exige validar antes de congelar tanto la
    estructura como la cadena. Una precondición que solo vive en prosa es una precondición que nadie
    ejecuta.
    """
    try:
        corrida = subprocess.run([sys.executable, str(ruta_cadena()), plan_arg],
                                 capture_output=True)
    except OSError:
        return 2
    if corrida.returncode != 0:
        # El diagnóstico específico nombra la propiedad y su ubicación; el código solo dice que
        # algo falló. Reemitirlo evita que el conductor tenga que repetir la corrida para conocerla.
        detalle = corrida.stderr.decode("utf-8", "replace").strip()
        if detalle:
            print(detalle, file=sys.stderr)
    return corrida.returncode


def congelar_contrato(texto: str) -> Optional[Tuple[int, str]]:
    """La versión vigente del contrato de verificación y el `hash` que ella misma declara.

    El hash no se recalcula: se **lee** el que la versión declara, que es el mismo que
    `contrato-cadena.py` valida al encadenarla. Recomputarlo acá crearía una segunda definición del
    mismo dato, y las dos se desincronizan en cuanto una cambie de canonicalización.
    """
    # El parser de versiones es el de `contrato-cadena.py`, importado y no reescrito: un segundo
    # regex sobre el mismo formato es una segunda definición que se desincroniza con la primera en
    # cuanto el formato cambie, y es esa cadena la que define qué versión existe.
    especificacion = importlib.util.spec_from_file_location("contrato_cadena", ruta_cadena())
    if especificacion is None or especificacion.loader is None:
        return None
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    halladas = modulo.versiones(texto)
    if not halladas:
        return None
    numero, bloque = halladas[-1]
    declarado = re.search(r"`hash: ([0-9a-f]{64})`", "\n".join(bloque))
    if declarado is None:
        return None
    return numero, declarado.group(1)


def _cargar_ledger() -> Optional[ModuleType]:
    ruta = Path(__file__).resolve().with_name("_ledger.py")
    especificacion = importlib.util.spec_from_file_location("sdd_flow_promocion_ledger", ruta)
    if especificacion is None or especificacion.loader is None:
        return None
    modulo = importlib.util.module_from_spec(especificacion)
    try:
        especificacion.loader.exec_module(modulo)
    except Exception:
        return None
    return modulo


def _aprobacion_vigente(bitacora: str, version: int, hash_candidato: str
                        ) -> Optional[Dict[str, str]]:
    candidatas: List[Dict[str, str]] = []
    for linea in bitacora.splitlines():
        if "`paso: aprobar-reparación`" not in linea:
            continue
        campos = _campos_linea(linea)
        if campos.get("hash") == hash_candidato and campos.get("contract_version") == str(version):
            candidatas.append(campos)
    return candidatas[0] if len(candidatas) == 1 else None


def _sequence_id(predecesor: str, check_id: str, ordinal: str) -> str:
    material = "\0".join((predecesor, check_id, ordinal)).encode("utf-8")
    return "rotation-" + hashlib.sha256(material).hexdigest()


def _sobre_activo(directorio: Path, worktree: Path) -> bool:
    if not directorio.exists():
        return False
    try:
        directorio = directorio.resolve(strict=True)
        if not directorio.is_dir():
            return True
        entradas = list(directorio.iterdir())
    except OSError:
        return True
    for ruta in entradas:
        if not ruta.is_file() or ruta.suffix != ".json":
            continue
        try:
            sobre = json.loads(ruta.read_text(encoding="utf-8"))
            declarado = Path(str(sobre.get("scope", {}).get("worktree", "")))
            if not declarado.is_absolute():
                return True
            observado = declarado.resolve(strict=True)
        except (OSError, ValueError, TypeError, RuntimeError):
            return True
        if observado == worktree:
            return True
    return False


def _bytes_archivo(ruta: Path) -> bytes:
    # Los paquetes históricos conservan bytes exactos, no una recodificación de texto.
    return ruta.read_bytes()


def _aprobaciones(texto: str) -> List[Dict[str, str]]:
    aprobaciones = []
    for linea in texto.splitlines():
        if "`paso: aprobar-reparación`" not in linea:
            continue
        campos = _campos_linea(linea)
        if any(not campos.get(nombre) for nombre in (
                "token", "hash", "checkId", "contract_version", "verification_defect_ordinal")):
            raise ValueError("aprobación malformada")
        aprobaciones.append(campos)
    return aprobaciones


def _reparacion_vigente(plan: str, version: int, aprobacion: Dict[str, str]) -> bool:
    bloques = re.split(r"(?m)(?=^#+ v[1-9][0-9]*$)", plan)
    encabezado = re.compile(r"^#+ v" + str(version) + r"(?:\n|$)")
    for bloque in bloques:
        if not bloque or encabezado.match(bloque) is None:
            continue
        for linea in bloque.splitlines():
            if not linea.startswith("- reparación: "):
                continue
            campos = _campos_linea(linea, "- reparación: ")
            if (campos.get("version_previa") == str(version - 1)
                    and campos.get("id") == aprobacion["checkId"]
                    and campos.get("token") == aprobacion["token"]):
                return True
    return False


def _leer_link(ruta: Path) -> Optional[Dict[str, Any]]:
    try:
        cuerpo = ruta.read_bytes()
        link = json.loads(cuerpo.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        return None
    canon = (json.dumps(link, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
             + "\n").encode("utf-8")
    return link if cuerpo == canon and isinstance(link, dict) else None


def _validar_paquete(destino: Path, fuentes: Dict[str, Path], ledger: Dict[str, Any],
                     aprobacion: Dict[str, str], aprobaciones: List[Dict[str, str]],
                     version: int, sucesor: str, forma: str) -> bool:
    link = _leer_link(destino / "rotation-link.json")
    if link is None:
        return False
    campos = {
        "predecessor_sequence_id", "successor_sequence_id", "checkId",
        "verification_defect_ordinal", "approval_token", "candidate_hash", "forma",
        "predecessor_terminal", "pending_delta_sha256",
    }
    if set(link) != campos:
        return False
    secuencia = ledger["sequence"]
    ordinal = aprobacion["verification_defect_ordinal"]
    if (link["predecessor_sequence_id"] != secuencia["sequence_id"]
            or link["successor_sequence_id"] != sucesor
            or destino.name != sucesor or link["checkId"] != aprobacion["checkId"]
            or isinstance(link["verification_defect_ordinal"], bool)
            or link["verification_defect_ordinal"] != int(ordinal)
            or str(link["verification_defect_ordinal"]) != ordinal
            or link["forma"] != forma
            or link["predecessor_terminal"] != secuencia["terminal"]):
        return False
    historica = next((item for item in aprobaciones
                      if item["token"] == link["approval_token"]
                      and item["hash"] == link["candidate_hash"]), None)
    if historica is None or any(historica[campo] != aprobacion[campo] for campo in (
            "checkId", "contract_version", "verification_defect_ordinal")):
        return False
    delta = secuencia["delta"]["material"]
    pendiente = destino / "pending-delta.patch"
    if pendiente.exists():
        if secuencia["terminal"] != "abandoned" or delta != "":
            return False
        esperado = "sha256:" + hashlib.sha256(pendiente.read_bytes()).hexdigest()
        if link["pending_delta_sha256"] != esperado:
            return False
    elif link["pending_delta_sha256"] is not None:
        return False
    nombres = set(fuentes) | {"rotation-link.json"}
    if pendiente.exists():
        nombres.add("pending-delta.patch")
    try:
        if {ruta.name for ruta in destino.iterdir()} != nombres:
            return False
        for nombre, fuente in fuentes.items():
            if nombre == "plan.md":
                claves = rb"(?m)^contract_frozen_(?:version|hash):[^\n]*\n"
                if re.sub(claves, b"", _bytes_archivo(destino / nombre)) != re.sub(
                        claves, b"", _bytes_archivo(fuente)):
                    return False
                continue
            if _bytes_archivo(destino / nombre) != _bytes_archivo(fuente):
                return False
        if "tasks.md" in fuentes and link["forma"] != "tasks":
            return False
        if "tasks.md" not in fuentes and link["forma"] != "embebida":
            return False
    except OSError:
        return False
    return True


def _publicar_paquete(plan_path: Path, ledger_path: Path, ledger: Dict[str, Any],
                      aprobacion: Dict[str, str], aprobaciones: List[Dict[str, str]],
                      version: int) -> Optional[Path]:
    secuencia = ledger.get("sequence", {})
    predecesor = secuencia.get("sequence_id")
    terminal = secuencia.get("terminal")
    modo = secuencia.get("mode")
    check_id = aprobacion["checkId"]
    ordinal = aprobacion["verification_defect_ordinal"]
    if not isinstance(predecesor, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", predecesor) is None:
        return None
    if predecesor in {".", ".."} or terminal not in {"abandoned", "rolled_back"}:
        return None
    if modo not in {"inline", "blocks"} or not ordinal.isdigit() or ordinal.startswith("0"):
        return None
    sucesor = _sequence_id(predecesor, check_id, ordinal)
    forma = "embebida" if modo == "inline" else "tasks"
    raiz = plan_path.parent
    fuentes = {
        "sequence-ledger.yml": ledger_path,
        "plan.md": plan_path,
    }
    if modo == "blocks":
        if secuencia.get("receipt_ref") != "partition-receipt.yml":
            return None
        fuentes["partition-receipt.yml"] = raiz / "partition-receipt.yml"
        fuentes["tasks.md"] = raiz / "tasks.md"
    if any(not ruta.is_file() for ruta in fuentes.values()):
        return None
    link = {
        "approval_token": aprobacion["token"],
        "candidate_hash": aprobacion["hash"],
        "checkId": check_id,
        "forma": forma,
        "pending_delta_sha256": None,
        "predecessor_sequence_id": predecesor,
        "predecessor_terminal": terminal,
        "successor_sequence_id": sucesor,
        "verification_defect_ordinal": int(ordinal),
    }
    contenido_link = json.dumps(link, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    destino = raiz / "sequences" / sucesor
    esperado = {nombre: _bytes_archivo(ruta) for nombre, ruta in fuentes.items()}
    esperado["rotation-link.json"] = contenido_link.encode("utf-8")
    if destino.exists():
        return destino if _validar_paquete(
            destino, fuentes, ledger, aprobacion, aprobaciones, version, sucesor, forma) else None
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.parent / ("." + sucesor + ".tmp-" + str(os.getpid()))
    if temporal.exists():
        return None
    try:
        temporal.mkdir(mode=0o700)
        for nombre, cuerpo in esperado.items():
            (temporal / nombre).write_bytes(cuerpo)
        os.rename(temporal, destino)
    except OSError:
        shutil.rmtree(temporal, ignore_errors=True)
        return None
    return destino


def _validar_refresh(plan_path: Path, bitacora: str, ledger_path: Path,
                     envelopes_path: Path, version: int, hash_candidato: str) -> Optional[str]:
    try:
        plan_resuelto = plan_path.resolve(strict=True)
        ledger_resuelto = ledger_path.resolve(strict=True)
        worktree = plan_resuelto.parents[2].resolve(strict=True)
    except (OSError, IndexError, RuntimeError):
        return "rutas"
    if (plan_resuelto.name != "plan.md" or ledger_resuelto.name != "sequence-ledger.yml"
            or ledger_resuelto.parent != plan_resuelto.parent):
        return "rutas"
    if not envelopes_path.is_absolute() or tuple(envelopes_path.parts[-3:]) != \
            (".cross-model", "active", "cross-implement"):
        return "rutas"
    if _sobre_activo(envelopes_path, worktree):
        return "sobre"
    owner = ledger_resuelto.parent / "sequence-ledger.owner" / "token"
    try:
        if not owner.read_text(encoding="utf-8").strip():
            return "owner"
    except (OSError, UnicodeError):
        return "owner"
    modulo = _cargar_ledger()
    if modulo is None:
        return "ledger-helper-no-cargable"
    try:
        documento = modulo.leer(ledger_resuelto.read_text(encoding="utf-8"))
        if modulo.validar(documento, "ledger"):
            return "ledger"
    except Exception:
        return "ledger"
    if _cargar_invariantes() is None:
        return "contrato-helper-no-cargable"
    aprobacion = _aprobacion_vigente(bitacora, version, hash_candidato)
    if aprobacion is None or not aprobacion["checkId"] or not aprobacion["verification_defect_ordinal"]:
        return "aprobacion"
    try:
        plan = plan_resuelto.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "plan"
    if not _reparacion_vigente(plan, version, aprobacion):
        return "reparacion"
    try:
        aprobaciones = _aprobaciones(bitacora)
    except ValueError:
        return "aprobacion"
    paquete = _publicar_paquete(
        plan_resuelto, ledger_resuelto, documento, aprobacion, aprobaciones, version)
    return None if paquete is not None else "paquete"


def _sellar_version(lineas: List[str]) -> Tuple[List[str], str]:
    canon = [re.sub(r"`hash: [^`]*`", "`hash: `", linea).rstrip() for linea in lineas]
    while canon and canon[-1] == "":
        canon.pop()
    digest = hashlib.sha256(("\n".join(canon) + "\n").encode("utf-8")).hexdigest()
    return [re.sub(r"`hash: [^`]*`", f"`hash: {digest}`", linea) for linea in lineas], digest


def preparar_estado_refresh(arena: Path, *, status: str = "tasks-ready",
                            terminal: str = "abandoned", modo: str = "inline",
                            owner: bool = True, sobre: bool = False) -> Tuple[Path, Path, Path, Path, str]:
    """Materializa la entrada mínima compartida por la matriz y la prueba de inmutabilidad."""
    flujo = arena / ".plans" / "caso"
    flujo.mkdir(parents=True)
    tabla = ["| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |",
             "|---|---|---|---|---|---|", "| A | conducta | test | predicado | RED | N/A |"]
    pertinencia = ("- pertinencia: `id: A` · `autoridad: conducta` · `relación: no-aplica` · "
                   "`baseline_tipo: otro` · `baseline_fundamento: observación ordinaria`")
    v1, hash_v1 = _sellar_version(
        ["## v1", "", "`hash_previo:` · `hash: `", "", *tabla, "", pertinencia])
    token = "2:A:esperado-corregido:a1"
    tabla[-1] = "| A | conducta | test | predicado | GREEN | N/A |"
    v2, hash_v2 = _sellar_version([
        "## v2", "", f"`hash_previo: {hash_v1}` · `hash: `", "", *tabla, "", pertinencia,
        (f"- reparación: `version_previa: 1` · `id: A` · `operación: esperado-corregido` · "
         f"`token: {token}` · `esperado_previo_sha256: "
         f"{hashlib.sha256(b'RED').hexdigest()}`"),
    ])
    plan = flujo / "plan.md"
    plan.write_text(
        f"---\nstatus: {status}\ncomplexity: normal\ncontract_procedure: measured-v1\n"
        f"contract_frozen_version: 1\ncontract_frozen_hash: {hash_v1}\n---\n"
        + "\n".join(v1 + [""] + v2) + "\n", encoding="utf-8")
    bitacora = flujo / "bitacora.md"
    bitacora.write_text(
        "- `paso: congelar` · `actor: conductor` · `timestamp: 2026-01-01T00:00:00Z`\n"
        f"- `paso: aprobar-reparación` · `actor: usuario` · `token: {token}` · "
        f"`hash: {hash_v2}` · `timestamp: 2026-01-01T00:01:00Z` · `checkId: A` · "
        "`contract_version: 2` · `verification_defect_ordinal: 1`\n",
        encoding="utf-8")
    ledger = flujo / "sequence-ledger.yml"
    recibo = "  receipt_ref: partition-receipt.yml\n" if modo == "blocks" else ""
    machine, cutpoint = (("block-machine", "C8") if modo == "blocks"
                         else ("inline-machine", "inline-terminal"))
    cerrado = "null" if terminal in {"active", "suspended"} else "2026-01-01T00:03:00Z"
    ledger.write_text(
        "schema_version: 1\nsequence:\n  sequence_id: predecessor-1\n"
        f"  mode: {modo}\n  base_anchor: '{'0' * 40}'\n"
        f"  coverage_fingerprint: sha256:{'1' * 64}\n{recibo}  join_state: null\n"
        f"  delta:\n    algorithm: sha256\n    digest: sha256:{'2' * 64}\n"
        f"    material: \"\"\n  cursor:\n    machine: {machine}\n    cutpoint: {cutpoint}\n"
        f"  terminal: {terminal}\ntransitions: []\neffect_events: []\nresult:\n"
        f"  status: {terminal}\n  closed_at: {cerrado}\n", encoding="utf-8")
    if owner:
        token_dir = flujo / "sequence-ledger.owner"
        token_dir.mkdir()
        (token_dir / "token").write_text("owner-predecessor-1\n", encoding="utf-8")
    if modo == "blocks":
        (flujo / "partition-receipt.yml").write_bytes(b"receipt\n")
        (flujo / "tasks.md").write_bytes(b"tasks\n")
    envelopes = arena / ".cross-model" / "active" / "cross-implement"
    if sobre:
        envelopes.mkdir(parents=True)
        (envelopes / "activo.json").write_text(
            json.dumps({"scope": {"worktree": str(arena.resolve())}}) + "\n", encoding="utf-8")
    return plan, bitacora, ledger, envelopes, hash_v2


def verificar_promocion() -> None:
    """Ejecuta las dieciséis transiciones cerradas sobre árboles temporales."""
    import contextlib
    import io

    identidades = (
        "inicial", "refresh-tasks-ready", "refresh-implementing", "refresh-tras-rollback",
        "fallo-publicacion-tasks-ready", "fallo-publicacion-implementing",
        "cadena-invalida-refresh", "estado-invalido-refresh",
        "refresh-con-ledger-vivo-rechazado", "refresh-sin-paquete-rechazado",
        "paquete-historico-byte-identico", "lector-ledger-ausente-rechazado",
        "refresh-sin-owner-rechazado", "paquete-derivado-por-sequence-id",
        "recibo-referenciado-byte-identico", "secuencia-nueva-con-claves-refrescadas",
    )
    if len(identidades) != 16 or len(set(identidades)) != 16:
        raise AssertionError("la matriz de promoción no conserva sus 16 identidades")

    def ejecutar(estado: Tuple[Path, Path, Path, Path, str], *, falla_replace: bool = False,
                 helper_ausente: bool = False) -> Tuple[int, str]:
        anterior_argv, reemplazo, cargar = sys.argv, os.replace, globals()["_cargar_ledger"]
        stderr = io.StringIO()
        if falla_replace:
            os.replace = lambda _origen, _destino: (_ for _ in ()).throw(OSError("inyectado"))
        if helper_ausente:
            globals()["_cargar_ledger"] = lambda: None
        try:
            plan, log, ledger, envelopes, _hash = estado
            sys.argv = [__file__, str(plan), str(log), str(ledger), str(envelopes)]
            with contextlib.redirect_stderr(stderr):
                codigo = main()
        finally:
            sys.argv, os.replace, globals()["_cargar_ledger"] = anterior_argv, reemplazo, cargar
        return codigo, stderr.getvalue()

    def instantanea(ruta: Path) -> Dict[str, bytes]:
        return {str(archivo.relative_to(ruta)): archivo.read_bytes()
                for archivo in ruta.rglob("*") if archivo.is_file()}

    observadas = []
    for identidad in identidades:
        with tempfile.TemporaryDirectory(prefix="promocion-contract-") as temporal:
            arena = Path(temporal)
            estado = preparar_estado_refresh(
                arena, status="implementing" if "implementing" in identidad else "tasks-ready",
                terminal="rolled_back" if identidad == "refresh-tras-rollback" else
                ("active" if identidad == "refresh-con-ledger-vivo-rechazado" else "abandoned"),
                modo="blocks" if identidad in {
                    "refresh-sin-paquete-rechazado", "recibo-referenciado-byte-identico"} else "inline",
                owner=identidad != "refresh-sin-owner-rechazado")
            plan, log, ledger, _envelopes, hash_v2 = estado
            previo = plan.read_bytes()
            if identidad == "inicial":
                inicial = plan.read_text(encoding="utf-8").replace(
                    "status: tasks-ready\n", "status: planned\n", 1)
                inicial = re.sub(r"^contract_frozen_(?:version|hash): .*\n", "", inicial,
                                 flags=re.M)
                plan.write_text(inicial, encoding="utf-8")
                ledger.unlink()
                codigo, _ = ejecutar(estado)
                assert codigo == 0 and "contract_frozen_version: 2\n" in plan.read_text(
                    encoding="utf-8")
            elif identidad in {"refresh-tasks-ready", "refresh-implementing", "refresh-tras-rollback"}:
                codigo, error = ejecutar(estado)
                assert codigo == 0, error
            elif identidad.startswith("fallo-publicacion-"):
                codigo, _ = ejecutar(estado, falla_replace=True)
                assert codigo == 2 and plan.read_bytes() == previo
            elif identidad == "cadena-invalida-refresh":
                plan.write_text(plan.read_text(encoding="utf-8").replace(
                    f"`hash: {hash_v2}`", f"`hash: {'f' * 64}`"), encoding="utf-8")
                corrupto = plan.read_bytes()
                codigo, _ = ejecutar(estado)
                assert codigo == 1 and plan.read_bytes() == corrupto
            elif identidad == "estado-invalido-refresh":
                plan.write_text(plan.read_text(encoding="utf-8").replace(
                    "status: tasks-ready", "status: verified"), encoding="utf-8")
                corrupto = plan.read_bytes()
                codigo, _ = ejecutar(estado)
                assert codigo == 1 and plan.read_bytes() == corrupto
            elif identidad in {"refresh-con-ledger-vivo-rechazado", "refresh-sin-owner-rechazado"}:
                codigo, _ = ejecutar(estado)
                assert codigo == 1 and plan.read_bytes() == previo
            elif identidad == "refresh-sin-paquete-rechazado":
                (plan.parent / "tasks.md").unlink()
                codigo, _ = ejecutar(estado)
                assert codigo == 1 and plan.read_bytes() == previo
            elif identidad == "paquete-historico-byte-identico":
                assert ejecutar(estado, falla_replace=True)[0] == 2
                paquete = next((plan.parent / "sequences").iterdir())
                archivo = instantanea(paquete)
                link_path = paquete / "rotation-link.json"
                link = json.loads(link_path.read_text(encoding="utf-8"))
                pendiente = paquete / "pending-delta.patch"
                pendiente.write_bytes(b"pending\n")
                link["pending_delta_sha256"] = "sha256:" + hashlib.sha256(
                    pendiente.read_bytes()).hexdigest()
                link_path.write_text(json.dumps(
                    link, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")
                assert _validar_refresh(
                    plan, log.read_text(encoding="utf-8"), ledger, estado[3], 2, hash_v2) is None
                link["pending_delta_sha256"] = "sha256:" + "0" * 64
                link_path.write_text(json.dumps(
                    link, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")
                assert _validar_refresh(
                    plan, log.read_text(encoding="utf-8"), ledger, estado[3], 2,
                    hash_v2) == "paquete"
                pendiente.unlink()
                link["pending_delta_sha256"] = None
                link_path.write_text(json.dumps(
                    link, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")
                plan_archivado = paquete / "plan.md"
                cuerpo_archivado = plan_archivado.read_bytes()
                plan_archivado.write_bytes(cuerpo_archivado + b"corrupto\n")
                assert _validar_refresh(
                    plan, log.read_text(encoding="utf-8"), ledger, estado[3], 2,
                    hash_v2) == "paquete"
                plan_archivado.write_bytes(cuerpo_archivado)
                assert ejecutar(estado)[0] == 0 and instantanea(paquete) == archivo
            elif identidad == "lector-ledger-ausente-rechazado":
                codigo, error = ejecutar(estado, helper_ausente=True)
                assert codigo == 99 and "ledger-helper-no-cargable" in error
            elif identidad == "paquete-derivado-por-sequence-id":
                sucesor = _sequence_id("predecessor-1", "A", "1")
                assert ejecutar(estado)[0] == 0
                paquete = plan.parent / "sequences" / sucesor
                link_path = paquete / "rotation-link.json"
                link = json.loads(link_path.read_text(encoding="utf-8"))
                assert paquete.is_dir() and link["successor_sequence_id"] == sucesor
                assert link["forma"] == "embebida" and link["checkId"] == "A"
                original = dict(link)
                for clave, valor in (("forma", None), ("forma", "desconocida"),
                                     ("forma", "tasks"), ("approval_token", "otro"),
                                     ("candidate_hash", "0" * 64), ("checkId", "B"),
                                     ("verification_defect_ordinal", 2)):
                    mutado = dict(original)
                    if valor is None:
                        mutado.pop(clave)
                    else:
                        mutado[clave] = valor
                    link_path.write_text(json.dumps(
                        mutado, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                        encoding="utf-8")
                    assert _validar_refresh(
                        plan, log.read_text(encoding="utf-8"), ledger, estado[3], 2,
                        hash_v2) == "paquete"
                historico = dict(original)
                historico.update(approval_token="token-historico", candidate_hash="e" * 64)
                link_path.write_text(json.dumps(
                    historico, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")
                log.write_text(
                    log.read_text(encoding="utf-8")
                    + "- `paso: aprobar-reparación` · `token: token-historico` · "
                    f"`hash: {'e' * 64}` · `checkId: A` · `contract_version: 2` · "
                    "`verification_defect_ordinal: 1`\n", encoding="utf-8")
                assert _validar_refresh(
                    plan, log.read_text(encoding="utf-8"), ledger, estado[3], 2, hash_v2) is None
            elif identidad == "recibo-referenciado-byte-identico":
                assert ejecutar(estado)[0] == 0
                paquete = next((plan.parent / "sequences").iterdir())
                assert ((paquete / "partition-receipt.yml").read_bytes()
                        == (plan.parent / "partition-receipt.yml").read_bytes())
                (plan.parent / "partition-receipt.yml").write_bytes(b"otro\n")
                assert _validar_refresh(
                    plan, log.read_text(encoding="utf-8"), ledger, estado[3], 2,
                    hash_v2) == "paquete"
            elif identidad == "secuencia-nueva-con-claves-refrescadas":
                inmutables = {str(ruta): ruta.read_bytes() for ruta in (
                    ledger, log, plan.parent / "sequence-ledger.owner" / "token")}
                assert ejecutar(estado)[0] == 0
                assert f"contract_frozen_hash: {hash_v2}\n" in plan.read_text(encoding="utf-8")
                assert all(Path(ruta).read_bytes() == cuerpo for ruta, cuerpo in inmutables.items())
            observadas.append(identidad)
    if tuple(observadas) != identidades:
        raise AssertionError("la matriz de promoción no ejecutó cada identidad exactamente una vez")


def main() -> int:
    if len(sys.argv) != 5:
        print("USO:promocion-tasks-ready plan log ledger active_envelopes", file=sys.stderr)
        return 2
    plan_arg, log_arg, ledger_arg, envelopes_arg = sys.argv[1:]
    for valor, nombre, etiqueta in ((plan_arg, "plan", "plan"), (log_arg, "bitacora", "bitácora")):
        if not valor:
            return fallo(f"la entrada {nombre} no fue declarada", 2)
        ruta = Path(valor)
        if not ruta.is_file():
            return fallo(f"el {etiqueta} no existe: {valor}", 2)
        if not os.access(ruta, os.R_OK):
            return fallo(f"el {etiqueta} no es legible: {valor}", 2)
    if _DELIVERY_PROFILE_FAILURE:
        print("ARNES:promocion-tasks-ready "
              f"delivery-profile-helper-{_DELIVERY_PROFILE_FAILURE}", file=sys.stderr)
        return 99
    try:
        # newline="" preserves the plan's original LF/CRLF representation.
        with open(plan_arg, encoding="utf-8", newline="") as archivo:
            plan = archivo.read()
        with open(log_arg, encoding="utf-8", newline="") as archivo:
            bitacora = archivo.read()
    except (OSError, UnicodeError):
        return fallo("el frontmatter del plan no se pudo leer", 2)

    try:
        campos = leer_header(plan)
    except _delivery_profile.DeliveryProfileError as error:
        return fallo(error.code, 1 if error.code == "expedited-inelegible" else 2)
    status = campos["status"][0] if campos["status"] else ""
    complexity = campos["complexity"][0] if campos["complexity"] else ""
    marker = campos["contract_procedure"][0] if campos["contract_procedure"] else ""
    if not campos["status"]:
        return fallo("falta la clave status en el frontmatter", 2)
    if status not in {"planned", "plan-approved", "tasks-ready", "implementing", "verified", "committed", "pushed", "pr-open", "done"}:
        return fallo(f'status tiene un valor no soportado: "{status}"', 2)
    if not campos["complexity"]:
        return fallo("falta la clave complexity en el frontmatter", 2)
    if complexity not in {"trivial", "normal", "complex"}:
        return fallo(f'complexity tiene un valor no soportado: "{complexity}"', 2)
    if len(campos["status"]) != 1:
        return fallo("la clave status está duplicada", 2)
    if len(campos["complexity"]) != 1:
        return fallo("la clave complexity está duplicada", 2)
    try:
        _delivery_profile.resolve_delivery_pair(campos, complexity)
    except _delivery_profile.DeliveryProfileError as error:
        return fallo(error.code, 1 if error.code == "expedited-inelegible" else 2)
    if len(campos["contract_procedure"]) > 1:
        return fallo("la clave contract_procedure está duplicada", 2)
    if len(campos["contract_procedure"]) != 1:
        return fallo("falta el marcador contract_procedure", 1)
    if marker != "measured-v1":
        return fallo(f'contract_procedure tiene un valor no soportado: "{marker}"', 1)
    ledger_path = Path(ledger_arg)
    envelopes_path = Path(envelopes_arg)
    if ledger_path.name != "sequence-ledger.yml":
        return fallo("ledger debe usar el basename sequence-ledger.yml", 1)
    if not envelopes_path.is_absolute() or tuple(envelopes_path.parts[-3:]) != \
            (".cross-model", "active", "cross-implement"):
        return fallo("active_envelopes debe ser absoluto y terminar en "
                     ".cross-model/active/cross-implement", 1)

    constancia = clasificar_constancia(bitacora)
    if constancia != "ok":
        return fallo(f"la constancia canónica falla en {constancia}", 1)
    # La versión que se congela es la **vigente en este gate**, no la última que llegue después: el
    # contrato lo declara así, y por eso las dos claves nacen acá y no se recomputan. Sin este paso
    # nadie las escribía y el ejecutable de las huellas, que las exige, devolvía `3` en todo flujo
    # real: el ledger no se creaba y la receta no podía arrancar.
    codigo_cadena = validar_cadena(plan_arg)
    if codigo_cadena != 0:
        return fallo("la estructura o la cadena del contrato no valida: "
                     f"contrato-cadena.py devolvió {codigo_cadena}", 1)
    congelada = congelar_contrato(plan)
    if congelada is None:
        return fallo("no se pudo determinar la versión vigente del contrato ni su hash", 1)
    version_congelada, hash_congelado = congelada
    if len(campos["contract_frozen_version"]) > 1 or len(campos["contract_frozen_hash"]) > 1:
        return fallo("las claves congeladas están duplicadas", 2)
    tiene_version = len(campos["contract_frozen_version"]) == 1
    tiene_hash = len(campos["contract_frozen_hash"]) == 1
    if tiene_version != tiene_hash:
        return fallo("las claves congeladas deben aparecer juntas", 1)
    coincide = (tiene_version and campos["contract_frozen_version"] == [str(version_congelada)]
                and campos["contract_frozen_hash"] == [hash_congelado])
    if coincide and status in {"tasks-ready", "implementing"}:
        return 0
    esperado = "plan-approved" if complexity == "complex" else "planned"
    inicial = not tiene_version
    refresco = tiene_version and not coincide
    if inicial and status != esperado:
        return fallo(f'status "{status}" no permite promover; se esperaba "{esperado}"', 1)
    if refresco and status not in {"tasks-ready", "implementing"}:
        return fallo(f'status "{status}" no permite refrescar claves congeladas', 1)
    if refresco:
        plan_path = Path(plan_arg)
        log_path = Path(log_arg)
        try:
            plan_resuelto = plan_path.resolve(strict=True)
            log_resuelto = log_path.resolve(strict=True)
        except (OSError, RuntimeError):
            return fallo("refresh no pudo resolver plan.md y bitacora.md", 1)
        if plan_resuelto.name != "plan.md" or log_resuelto.name != "bitacora.md" or \
                log_resuelto.parent != plan_resuelto.parent:
            return fallo("refresh exige plan.md y bitacora.md hermanos", 1)
        defecto_refresh = _validar_refresh(
            plan_resuelto, bitacora, ledger_path, envelopes_path,
            version_congelada, hash_congelado)
        if defecto_refresh == "ledger-helper-no-cargable":
            print("ARNES:promocion-tasks-ready ledger-helper-no-cargable", file=sys.stderr)
            return 99
        if defecto_refresh == "contrato-helper-no-cargable":
            print("ARNES:promocion-tasks-ready contrato-helper-no-cargable", file=sys.stderr)
            return 99
        if defecto_refresh is not None:
            return fallo("refresh sin ledger terminal, paquete, aprobación, owner o cese válidos", 1)
    status_destino = "tasks-ready" if inicial else status

    lineas = plan.splitlines(keepends=True)
    dentro = False
    cambiado = False
    escritas = set()
    salida: List[str] = []
    for indice, linea in enumerate(lineas):
        contenido = linea.rstrip("\r\n")
        fin = linea[len(contenido) :]
        if indice == 0 and contenido.strip() == "---":
            dentro = True
        elif dentro and contenido.strip() == "---":
            # Las dos claves congeladas se emiten al cerrar el header si no estaban; si estaban, ya
            # se reescribieron en su lugar y el orden del header no se altera.
            faltantes = [(k, v) for k, v in (("contract_frozen_version", str(version_congelada)),
                                             ("contract_frozen_hash", hash_congelado))
                         if k not in escritas]
            for clave, valor in faltantes:
                salida.append(f"{clave}: {valor}\n")
            dentro = False
        elif dentro and not cambiado and re.match(r"^status\s*:\s*", contenido):
            contenido = f"status: {status_destino}"
            cambiado = True
        elif dentro and re.match(r"^contract_frozen_version:\s*", contenido):
            contenido = f"contract_frozen_version: {version_congelada}"
            escritas.add("contract_frozen_version")
        elif dentro and re.match(r"^contract_frozen_hash:\s*", contenido):
            contenido = f"contract_frozen_hash: {hash_congelado}"
            escritas.add("contract_frozen_hash")
        salida.append(contenido + fin)
    if not cambiado:
        return fallo("no encontró una clave status reescribible en el header", 2)

    ruta = Path(plan_arg)
    fd = -1
    temporal = ""
    try:
        fd, temporal = tempfile.mkstemp(prefix=f".{ruta.name}.promocion.", dir=str(ruta.parent))
        os.close(fd)
        fd = -1
    except OSError:
        if fd >= 0:
            os.close(fd)
        if temporal:
            Path(temporal).unlink(missing_ok=True)
        return fallo("falló la creación del temporal hermano del plan", 2)
    try:
        with open(temporal, "w", encoding="utf-8", newline="") as archivo:
            archivo.write("".join(salida))
    except OSError:
        Path(temporal).unlink(missing_ok=True)
        return fallo("falló la escritura del temporal hermano del plan", 2)
    candidato = "".join(salida)
    try:
        nuevos = leer_header(candidato)
    except _delivery_profile.DeliveryProfileError:
        nuevos = {}
    consistente = (
        nuevos.get("status") == [status_destino]
        and nuevos["complexity"] == [complexity]
        and nuevos["contract_procedure"] == ["measured-v1"]
        and nuevos["contract_frozen_version"] == [str(version_congelada)]
        and nuevos["contract_frozen_hash"] == [hash_congelado]
    )
    if not consistente:
        Path(temporal).unlink(missing_ok=True)
        return fallo("falló la validación del candidato: promoción o contrato inconsistente", 2)
    try:
        os.replace(temporal, ruta)
    except OSError:
        Path(temporal).unlink(missing_ok=True)
        return fallo("falló el reemplazo atómico del plan", 2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
