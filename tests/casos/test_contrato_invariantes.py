"""Matriz viva de 65 clases para la guarda direccional del contrato."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Callable, FrozenSet, List, NamedTuple, Optional, Sequence, Tuple

from tests.arbol import _instantanea


ENCODING = "utf-8"
RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "cross-implement" / "scripts" / "contrato-invariantes.py"
CABECERA = "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |"
SEPARADOR = "|---|---|---|---|---|---|"
Caso = Tuple[str, str, Callable[[Optional[object]], None]]
Constructor = Callable[[Path], None]


def _cargar_modulo() -> ModuleType:
    especificacion = importlib.util.spec_from_file_location("contrato_invariantes_bajo_prueba", SCRIPT)
    assert especificacion is not None and especificacion.loader is not None
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


MODULO = _cargar_modulo()


def _hash(bloque: Sequence[str]) -> str:
    return MODULO._hash_bloque(list(bloque))


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode(ENCODING)).hexdigest()


def _comprobar_procedimiento_cinco_mediciones() -> None:
    contrato = (RAIZ / "skills/cross-implement/contrato-verificacion.md").read_text(
        encoding=ENCODING)
    ownership = (RAIZ / "skills/cross-implement/ownership.md").read_text(encoding=ENCODING)
    flujo = (RAIZ / "skills/sdd-flow/reference.md").read_text(encoding=ENCODING)
    marcadores_contrato = (
        "una medición en el checkout de derivación",
        "cuatro invocaciones separadas de",
        "`rebaseline-worktree.py`, todas sobre el mismo commit y con el mismo comando",
        "las cinco parejas `resultado` + `observado`",
        "no se escribe el registro ni se sella la versión",
    )
    assert all(marcador in contrato for marcador in marcadores_contrato)
    assert "cinco mediciones" in ownership and "cuatro invocaciones" in ownership
    assert "una ejecución directa y cuatro invocaciones" in flujo


def _comprobar_wrapper_documentado() -> None:
    contrato = (RAIZ / "skills/cross-implement/contrato-verificacion.md").read_text(
        encoding=ENCODING)
    publicado = re.search(
        r"`contrato-invariantes\.py::PROJECTION_WRAPPER_BODY`; su SHA-256 es\n"
        r"`([0-9a-f]{64})`", contrato)
    assert publicado is not None
    observado = hashlib.sha256(MODULO.PROJECTION_WRAPPER_BODY.encode(ENCODING)).hexdigest()
    assert publicado.group(1) == observado


def _fila(identificador: str = "A", requisito: str = "hace foo", evidencia: str = "test",
          comando: str = "python3 -c 'print(1)'", esperado: str = "GREEN",
          baseline: str = "NOT_APPLICABLE") -> str:
    return f"| {identificador} | {requisito} | {evidencia} | {comando} | {esperado} | {baseline} |"


def _pertinencia(identificador: str = "A", autoridad: str = "subafirmación X",
                 relacion: str = "no-aplica", tipo: str = "otro",
                 fundamento: str = "observación ordinaria") -> str:
    return (
        f"- pertinencia: `id: {identificador}` · `autoridad: {autoridad}` · "
        f"`relación: {relacion}` · `baseline_tipo: {tipo}` · "
        f"`baseline_fundamento: {fundamento}`"
    )


def _registro(identificador: str, observado: Optional[str] = None,
              adjudicacion: Optional[str] = None, justificacion: Optional[str] = None,
              timestamp: str = "2026-01-01T00:00:00Z") -> str:
    partes = [f"- `id: {identificador}`", "`commit: abc123`", f"`timestamp: {timestamp}`"]
    if adjudicacion is not None:
        partes.append(f"`adjudicación: {adjudicacion}`")
    if observado is not None:
        partes.append(f"`observado: {observado}`")
    if justificacion is not None:
        partes.append(f"`justificación: {justificacion}`")
    return " · ".join(partes)


def _registros_por_defecto(filas: Sequence[str]) -> List[str]:
    registros: List[str] = []
    for texto in filas:
        celdas = [celda.strip() for celda in texto.strip().strip("|").split("|")]
        if len(celdas) != 6:
            continue
        identificador, baseline = celdas[0], celdas[5]
        if baseline == "RED":
            registros.append(_registro(identificador, "exit 1; ordinary=1"))
        elif baseline == "GREEN_ALREADY":
            registros.append(_registro(identificador, "exit 0; ordinary=0", "already_satisfied"))
        elif baseline == "NOT_APPLICABLE":
            registros.append(_registro(
                identificador, justificacion="la evidencia no tiene baseline ejecutable"))
        else:
            registros.append(_registro(identificador))
    return registros


def _version(numero: int, previa: Optional[Sequence[str]], filas: Sequence[str],
             pertinencias: Sequence[str], reparaciones: Sequence[str] = (),
             adopcion: Optional[str] = None,
             registros: Optional[Sequence[str]] = None) -> List[str]:
    hash_previo = _hash(previa) if previa is not None else ""
    bloque = [
        f"## v{numero}", "", f"`hash_previo: {hash_previo}` · `hash: `", "",
        CABECERA, SEPARADOR, *filas, "", *pertinencias,
        *(list(registros) if registros is not None else _registros_por_defecto(filas)),
        *reparaciones,
    ]
    if adopcion is not None:
        bloque.append(adopcion)
    valor = _hash(bloque)
    return [linea.replace("`hash: `", f"`hash: {valor}`") for linea in bloque]


def _reparacion(version: int, version_previa: int, identificador: str, operacion: str,
                ordinal_token: int = 1, esperado_previo: Optional[str] = None,
                pertinencia_previa: Optional[str] = None, campos: Optional[str] = None,
                evidencia_previa: Optional[str] = None,
                comando_previo: Optional[str] = None) -> Tuple[str, str]:
    token = f"{version}:{identificador}:{operacion}:a{ordinal_token}"
    partes = [
        f"- reparación: `version_previa: {version_previa}`", f"`id: {identificador}`",
        f"`operación: {operacion}`", f"`token: {token}`",
    ]
    if esperado_previo is not None:
        partes.append(f"`esperado_previo_sha256: {_sha(esperado_previo)}`")
    if pertinencia_previa is not None:
        partes.append(f"`pertinencia_previa_sha256: {_sha(pertinencia_previa)}`")
    if campos is not None:
        partes.append(f"`campos: {campos}`")
    if evidencia_previa is not None:
        partes.append(f"`evidencia_previa_sha256: {_sha(evidencia_previa)}`")
    if comando_previo is not None:
        partes.append(f"`comando_previo_sha256: {_sha(comando_previo)}`")
    return token, " · ".join(partes)


def _adopcion(version: int, version_previa: int, estado: str = "final",
              reutilizado: str = "ninguno", ajustado: str = "ninguno",
              actualizado: str = "ninguno", ordinal_token: int = 1) -> Tuple[str, str]:
    token = f"{version}:adopción-pertinencia:a{ordinal_token}"
    linea = (
        f"- adopción: `version_previa: {version_previa}` · `perfil: pertinencia-v1` · "
        f"`baseline_reutilizado: {reutilizado}` · `proyeccion_ajustada: {ajustado}` · "
        f"`baseline_actualizado: {actualizado}` · `estado: {estado}` · `token: {token}`"
    )
    return token, linea


def _aprobacion(token: str, hash_candidata: str, check_id: Optional[str] = None,
                version: Optional[int] = None, ordinal: Optional[int] = None,
                paso: str = "aprobar-reparación", actor: str = "usuario",
                extras: Sequence[str] = ()) -> str:
    partes = [
        f"- `paso: {paso}`", f"`actor: {actor}`", f"`token: {token}`",
        f"`hash: {hash_candidata}`", "`timestamp: 2026-01-01T00:01:00Z`",
    ]
    if check_id is not None:
        partes.append(f"`checkId: {check_id}`")
    if version is not None:
        partes.append(f"`contract_version: {version}`")
    if ordinal is not None:
        partes.append(f"`verification_defect_ordinal: {ordinal}`")
    partes.extend(extras)
    return " · ".join(partes)


def _congelar() -> str:
    return "- `paso: congelar` · `actor: conductor` · `timestamp: 2026-01-01T00:00:30Z`"


def _envoltura(predicado: str, proyector: str, cuerpo: Optional[str] = None) -> str:
    return shlex.join(["sh", "-c", cuerpo or MODULO.PROJECTION_WRAPPER_BODY,
                       "sh", predicado, proyector])


def _escribir(tmp: Path, bloques: Sequence[Sequence[str]], log_texto: str) -> Tuple[Path, Path]:
    contrato = tmp / "contrato.md"
    contrato.write_text(
        "\n".join("\n".join(bloque) for bloque in bloques) + "\n", encoding=ENCODING)
    log = tmp / "aprobaciones.md"
    log.write_text(log_texto, encoding=ENCODING)
    return contrato, log


def _ejecutar(script: Path, contrato: Path, log: Path, fase: str) -> subprocess.CompletedProcess:
    entorno = dict(os.environ)
    entorno["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(script), str(contrato), str(log), fase],
        capture_output=True, text=True, encoding=ENCODING, check=False, env=entorno,
    )


def _comprobar(tmp: Path, bloques: Sequence[Sequence[str]], log_texto: str, fase: str,
               codigo: int, contiene: Optional[str] = None,
               stderr_exacto: Optional[str] = None) -> subprocess.CompletedProcess:
    contrato, log = _escribir(tmp, bloques, log_texto)
    antes = _instantanea(tmp)
    resultado = _ejecutar(SCRIPT, contrato, log, fase)
    assert resultado.returncode == codigo, resultado.stderr
    assert resultado.stdout == ""
    assert "Traceback" not in resultado.stderr
    if stderr_exacto is not None:
        assert resultado.stderr == stderr_exacto
    elif contiene is not None:
        assert contiene in resultado.stderr
    elif codigo == 0:
        assert resultado.stderr == ""
    assert _instantanea(tmp) == antes
    return resultado


def _base() -> List[str]:
    return _version(1, None, [_fila()], [_pertinencia()])


def _legado(fila: Optional[str] = None, registros: Optional[Sequence[str]] = None) -> List[str]:
    return _version(1, None, [fila or _fila()], [], registros=registros)


def _adicion() -> Tuple[List[str], List[str], str]:
    v1 = _base()
    token, reparacion = _reparacion(2, 1, "B", "cobertura-agregada")
    v2 = _version(2, v1, [_fila(), _fila("B", "hace bar")],
                  [_pertinencia(), _pertinencia("B", "subafirmación Y")], [reparacion])
    return v1, v2, token


def _esperado(previa: Sequence[str], version: int, previo: str, nuevo: str,
              ordinal_token: int = 1) -> Tuple[List[str], str]:
    token, reparacion = _reparacion(
        version, version - 1, "A", "esperado-corregido",
        ordinal_token=ordinal_token, esperado_previo=previo)
    bloque = _version(version, previa, [_fila(esperado=nuevo)], [_pertinencia()], [reparacion])
    return bloque, token


def _verificacion(previa: Sequence[str], version: int, comando_previo: str,
                  comando_nuevo: str, ordinal_token: int = 1,
                  pertinencia: Optional[str] = None,
                  registros: Optional[Sequence[str]] = None) -> Tuple[List[str], str]:
    token, reparacion = _reparacion(
        version, version - 1, "A", "verificacion-corregida",
        ordinal_token=ordinal_token, campos="comando", comando_previo=comando_previo)
    bloque = _version(
        version, previa, [_fila(comando=comando_nuevo, baseline="RED")],
        [pertinencia or _pertinencia()], [reparacion], registros=registros)
    return bloque, token


def _caso(numero: int, tmp: Path) -> None:
    if numero in {1, 2, 3, 4, 5, 6}:
        v1, v2, token = _adicion()
        if numero == 1:
            _comprobar(tmp, [v1, v2], "", "candidate", 0)
        elif numero == 2:
            _comprobar(tmp, [v1, v2], "", "final", 1, "sin aprobación")
        elif numero in {3, 6}:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)) + "\n" + _congelar(),
                       "final", 0)
        elif numero == 4:
            log = _aprobacion(token, _hash(v2)) + "\n" + _congelar() + "\n# reevaluación\n"
            _comprobar(tmp, [v1, v2], log, "final", 0)
        else:
            _comprobar(tmp, [v1, v2], _congelar() + "\n" + _aprobacion(token, _hash(v2)),
                       "final", 1, "aprobación posterior al primer congelamiento")
        return
    if numero == 7:
        v1, _v2, token = _adicion()
        extra_token, extra = _reparacion(2, 1, "B", "esperado-corregido", esperado_previo="GREEN")
        cobertura = _reparacion(2, 1, "B", "cobertura-agregada")[1]
        v2 = _version(2, v1, [_fila(), _fila("B", "hace bar")],
                      [_pertinencia(), _pertinencia("B", "subafirmación Y")], [cobertura, extra])
        log = _aprobacion(token, _hash(v2)) + "\n" + _aprobacion(extra_token, _hash(v2))
        _comprobar(tmp, [v1, v2], log, "final", 1, "sin diferencia")
        return
    if numero == 8:
        v1 = _version(1, None, [_fila(), _fila("B")],
                      [_pertinencia(), _pertinencia("B")])
        v2 = _version(2, v1, [_fila()], [_pertinencia()])
        _comprobar(tmp, [v1, v2], "", "final", 1, "desaparecen ID B")
        return
    if numero == 9:
        v1 = _base()
        v2 = _version(2, v1, [_fila(requisito="hace otra cosa")], [_pertinencia()])
        _comprobar(tmp, [v1, v2], "", "final", 1, "Requisito de A cambia")
        return
    if numero in {10, 11}:
        v1 = _base()
        v2, token = _esperado(v1, 2, "GREEN", "PASS")
        if numero == 10:
            _comprobar(tmp, [v1, v2], "", "final", 1, "sin aprobación")
        else:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 0)
            v1 = _version(
                1, None, [_fila(esperado="GREEN", baseline="RED")], [_pertinencia()],
                registros=[_registro("A", "exit 1; ordinary=1")])
            token, reparacion = _reparacion(
                2, 1, "A", "esperado-corregido", esperado_previo="GREEN")
            v2 = _version(
                2, v1, [_fila(esperado="PASS", baseline="GREEN_ALREADY")], [_pertinencia()],
                [reparacion],
                registros=[_registro("A", "exit 0; ordinary=0", "already_satisfied")])
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 0)
        return
    if numero == 12:
        v1 = _base()
        candidata_1, token_1 = _esperado(v1, 2, "GREEN", "PASS", 1)
        candidata_2, token_2 = _esperado(v1, 2, "GREEN", "PASS", 2)
        log = (_congelar() + "\n" +
               _aprobacion(token_1, _hash(candidata_1), "A", 2, 1) + "\n" +
               _aprobacion(token_2, _hash(candidata_2), "A", 2, 1))
        _comprobar(tmp, [v1, candidata_2], log, "final", 0)
        _comprobar(tmp, [v1, candidata_2],
                   _congelar() + "\n" + _aprobacion(token_1, _hash(candidata_1), "A", 2, 1),
                   "final", 1, "sin aprobación")
        return
    if numero in {13, 14}:
        v1 = _base()
        v2, token_2 = _esperado(v1, 2, "GREEN", "PASS")
        v3, token_3 = _esperado(v2, 3, "PASS", "OK")
        aprobaciones = [
            _congelar(), _aprobacion(token_2, _hash(v2), "A", 2, 1),
            _aprobacion(token_3, _hash(v3), "A", 3, 2),
        ]
        if numero == 13:
            _comprobar(tmp, [v1, v2, v3], "\n".join(aprobaciones), "final", 0)
        else:
            v4, token_4 = _esperado(v3, 4, "OK", "DONE")
            aprobaciones.append(_aprobacion(token_4, _hash(v4), "A", 4, 3))
            _comprobar(tmp, [v1, v2, v3, v4], "\n".join(aprobaciones), "final", 1,
                       "presupuesto de VERIFICATION_DEFECT agotado para A")
        return
    if numero == 15:
        v1 = _base()
        candidata_1, token_1 = _esperado(v1, 2, "GREEN", "PASS", 1)
        v2, token_2 = _esperado(v1, 2, "GREEN", "PASS", 2)
        v3, token_3 = _esperado(v2, 3, "PASS", "OK")
        log = "\n".join([
            _congelar(), _aprobacion(token_1, _hash(candidata_1), "A", 2, 1),
            _aprobacion(token_2, _hash(v2), "A", 2, 1),
            _aprobacion(token_3, _hash(v3), "A", 3, 2),
        ])
        _comprobar(tmp, [v1, v2, v3], log, "final", 0)
        return
    if numero in {16, 17, 18, 19, 21, 23}:
        comando_1 = "python3 -c 'print(1)'"
        v1 = _version(1, None, [_fila(comando=comando_1, baseline="RED")], [_pertinencia()])
        v2, token_2 = _verificacion(v1, 2, comando_1, "python3 -c 'print(2)'")
        if numero == 16:
            clasificacion = ("- `paso: clasificar-falla` · `actor: conductor` · "
                             "`timestamp: 2026-01-01T00:00:40Z` · `checkId: A` · "
                             "`clase: VERIFICATION_DEFECT` · `consumedRound: no` · "
                             "`evidencia: comando defectuoso` · `delta: abc123` · `fix_round: 0` · "
                             "`contract_version: 2` · `verification_defect_ordinal: 1`")
            log = "\n".join([_congelar(), clasificacion,
                              _aprobacion(token_2, _hash(v2), "A", 2, 1)])
            _comprobar(tmp, [v1, v2], log, "final", 0)
        elif numero == 17:
            v3, token_3 = _verificacion(
                v2, 3, "python3 -c 'print(2)'", "python3 -c 'print(3)'")
            log = "\n".join([
                _congelar(), _aprobacion(token_2, _hash(v2), "A", 2, 1),
                _aprobacion(token_3, _hash(v3), "A", 3, 2),
            ])
            _comprobar(tmp, [v1, v2, v3], log, "final", 0)
        elif numero == 18:
            log = _congelar() + "\n" + _aprobacion(token_2, _hash(v2), "B", 2, 1)
            _comprobar(tmp, [v1, v2], log, "final", 1,
                       "aprobación post-congelamiento sin par de defecto coherente")
        elif numero == 19:
            v1 = _version(1, None,
                          [_fila(comando=comando_1, baseline="RED"),
                           _fila("B", comando=comando_1, baseline="RED")],
                          [_pertinencia(), _pertinencia("B")])
            token_2, reparacion = _reparacion(
                2, 1, "A", "verificacion-corregida", campos="comando",
                comando_previo=comando_1)
            filas = [_fila(comando="python3 -c 'print(2)'", baseline="RED"),
                     _fila("B", comando="python3 -c 'print(2)'", baseline="RED")]
            v2 = _version(2, v1, filas, [_pertinencia(), _pertinencia("B")], [reparacion])
            log = _congelar() + "\n" + _aprobacion(token_2, _hash(v2), "A", 2, 1)
            _comprobar(tmp, [v1, v2], log, "final", 1,
                       "Evidencia/Comando de B cambia sin verificacion-corregida único")
        elif numero == 21:
            _comprobar(tmp, [v1, v2], "", "final", 1, "sin aprobación")
        else:
            v3, token_3 = _verificacion(
                v2, 3, "python3 -c 'print(2)'", "python3 -c 'print(3)'")
            v4, token_4 = _verificacion(
                v3, 4, "python3 -c 'print(3)'", "python3 -c 'print(4)'")
            log = "\n".join([
                _congelar(), _aprobacion(token_2, _hash(v2), "A", 2, 1),
                _aprobacion(token_3, _hash(v3), "A", 3, 2),
                _aprobacion(token_4, _hash(v4), "A", 4, 3),
            ])
            _comprobar(tmp, [v1, v2, v3, v4], log, "final", 1,
                       "presupuesto de VERIFICATION_DEFECT agotado para A")
        return
    if numero == 20:
        v1 = _base()
        token, reparacion = _reparacion(2, 1, "A", "verificacion-corregida",
                                        campos="comando", comando_previo="python3 -c 'print(1)'")
        v2 = _version(2, v1, [_fila()], [_pertinencia()], [reparacion])
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1, "sin diferencia")
        token_huerfano = "2:A:verificacion-corregida:a1"
        _comprobar(tmp, [v1], _aprobacion(token_huerfano, _hash(v1)), "final", 1,
                   "aprobación sin reparación o adopción")
        return
    if numero == 22:
        comando = "python3 -c 'print(1)'"
        v1 = _version(1, None, [_fila(comando=comando, baseline="RED")], [_pertinencia()])
        v2, token = _verificacion(v1, 2, comando, "python3 -c 'print(2)'")
        for campos in ((None, 2, 1), ("A", None, 1), ("A", 2, None)):
            log = _congelar() + "\n" + _aprobacion(token, _hash(v2), *campos)
            _comprobar(tmp, [v1, v2], log, "final", 1, "par de VERIFICATION_DEFECT incompleto")
        return
    if numero == 24:
        v1 = _version(1, None, [_fila()], [])
        _comprobar(tmp, [v1], "", "final", 1, "paridad de pertinencia inválida")
        pert = _pertinencia()
        v1 = _version(1, None, [_fila()], [pert, pert])
        _comprobar(tmp, [v1], "", "final", 1, "pertinencia con ID duplicado")
        return
    if numero == 25:
        v1 = _version(1, None, [_fila()], [_pertinencia(autoridad="X · Y")])
        _comprobar(tmp, [v1], "", "final", 1, "paridad de pertinencia inválida")
        return
    if numero == 26:
        sin_tipo = ("- pertinencia: `id: A` · `autoridad: X` · `relación: no-aplica` · "
                    "`baseline_fundamento: ordinario`")
        v1 = _version(1, None, [_fila()], [sin_tipo])
        _comprobar(tmp, [v1], "", "final", 1, "forma u orden de campos inválido")
        v1 = _version(1, None, [_fila()], [_pertinencia(tipo="desconocido")])
        _comprobar(tmp, [v1], "", "final", 1, "baseline_tipo inválido")
        return
    if numero == 27:
        sin_fundamento = ("- pertinencia: `id: A` · `autoridad: X` · `relación: no-aplica` · "
                          "`baseline_tipo: otro`")
        v1 = _version(1, None, [_fila()], [sin_fundamento])
        _comprobar(tmp, [v1], "", "final", 1, "forma u orden de campos inválido")
        v1 = _version(1, None, [_fila()], [_pertinencia(fundamento="")])
        _comprobar(tmp, [v1], "", "final", 1, "valor inválido en baseline_fundamento")
        return
    if numero == 28:
        v1 = _version(1, None, [_fila(baseline="RED")], [_pertinencia(tipo="otro")],
                      registros=[_registro("A", "exit 1; failures=2")])
        _comprobar(tmp, [v1], "", "final", 1, "observado reservado")
        v1 = _version(1, None, [_fila(baseline="GREEN_ALREADY")],
                      [_pertinencia(tipo="fallos-conteo")],
                      registros=[_registro("A", "exit 0; ordinary=0", "already_satisfied")])
        _comprobar(tmp, [v1], "", "final", 1, "no es fallos-conteo")
        return
    if numero == 29:
        v1 = _version(1, None, [_fila(baseline="RED")], [_pertinencia(tipo="otro")],
                      registros=[_registro("A", "exit 1; 7")])
        _comprobar(tmp, [v1], "", "final", 0)
        return
    if numero == 30:
        for estado in ("BLOCKED", "NOT_APPLICABLE"):
            v1 = _version(1, None, [_fila(baseline=estado)], [_pertinencia()],
                          registros=[_registro("A", justificacion=(
                              "no aplica" if estado == "NOT_APPLICABLE" else None))])
            _comprobar(tmp, [v1], "", "final", 0)
        return
    if numero == 31:
        v1 = _base()
        token, reparacion = _reparacion(2, 1, "B", "esperado-corregido",
                                        esperado_previo="GREEN")
        v2 = _version(2, v1, [_fila(esperado="PASS")], [_pertinencia()], [reparacion])
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "Esperado de A cambia sin esperado-corregido único")
        token, reparacion = _reparacion(2, 9, "A", "esperado-corregido",
                                        esperado_previo="GREEN")
        v2 = _version(2, v1, [_fila(esperado="PASS")], [_pertinencia()], [reparacion])
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "version_previa inválida")
        return
    if numero in {32, 33}:
        v1 = _base()
        if numero == 32:
            v2, token = _esperado(v1, 2, "GREEN", "PASS")
        else:
            pert_nueva = _pertinencia(autoridad="subafirmación Z")
            token, reparacion = _reparacion(
                2, 1, "A", "pertinencia-corregida", pertinencia_previa=_pertinencia())
            v2 = _version(2, v1, [_fila()], [pert_nueva], [reparacion])
        log = _congelar() + "\n" + _aprobacion(token, _hash(v2))
        _comprobar(tmp, [v1, v2], log, "final", 1,
                   "aprobación post-congelamiento sin par de defecto coherente")
        return
    if numero == 34:
        v1 = _base()
        _comprobar(tmp, [v1], "", "intermedia", 2, stderr_exacto=MODULO.USO + "\n")
        contrato, _log = _escribir(tmp, [v1], "")
        log_ausente = tmp / "ausente.md"
        antes = _instantanea(tmp)
        resultado = _ejecutar(SCRIPT, contrato, log_ausente, "final")
        assert resultado.returncode == 1 and resultado.stdout == ""
        assert resultado.stderr == "GUARD:approval-log-inaccesible\n"
        assert _instantanea(tmp) == antes
        dependencias = tmp / "dependencias"
        dependencias.mkdir()
        copia = dependencias / SCRIPT.name
        shutil.copyfile(SCRIPT, copia)
        contrato_copia, log_copia = _escribir(dependencias, [v1], "")
        antes = _instantanea(dependencias)
        resultado = _ejecutar(copia, contrato_copia, log_copia, "final")
        assert resultado.returncode == 99
        assert resultado.stderr == "ARNES:contrato-invariantes dependencia _tabla.py no cargable\n"
        assert "Traceback" not in resultado.stderr and _instantanea(dependencias) == antes
        shutil.copyfile(SCRIPT.with_name("_tabla.py"), dependencias / "_tabla.py")
        antes = _instantanea(dependencias)
        resultado = _ejecutar(copia, contrato_copia, log_copia, "final")
        assert resultado.returncode == 99
        assert resultado.stderr == (
            "ARNES:contrato-invariantes dependencia contrato-cadena.py no cargable\n")
        assert "Traceback" not in resultado.stderr and _instantanea(dependencias) == antes
        return
    if numero == 35:
        v1 = _legado()
        _comprobar(tmp, [v1], "", "final", 1, "versión vigente legado sin adopción")
        return
    if numero in {36, 37, 39, 40, 41}:
        v1 = _legado()
        estado = "intermedia" if numero in {37, 40} else "final"
        token, adopcion = _adopcion(2, 1, estado=estado)
        v2 = _version(2, v1, [_fila()], [_pertinencia()], adopcion=adopcion)
        if numero == 36:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 0)
        elif numero == 37:
            _comprobar(tmp, [v1, v2], "", "candidate", 0)
        elif numero == 39:
            _comprobar(tmp, [v1, v2], "", "final", 1, "sin aprobación")
        elif numero == 40:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                       "una adopción intermedia no admite fase final")
        else:
            log = _congelar() + "\n" + _aprobacion(token, _hash(v2))
            _comprobar(tmp, [v1, v2], log, "final", 0)
        return
    if numero == 38:
        v1 = _legado()
        token_adopcion, adopcion = _adopcion(2, 1, estado="intermedia")
        pert_intermedia = _pertinencia(autoridad="subafirmación incompleta")
        v2 = _version(2, v1, [_fila()], [pert_intermedia], adopcion=adopcion)
        token_e, reparacion_e = _reparacion(
            3, 2, "A", "esperado-corregido", esperado_previo="GREEN")
        token_p, reparacion_p = _reparacion(
            3, 2, "A", "pertinencia-corregida", pertinencia_previa=pert_intermedia)
        v3 = _version(3, v2, [_fila(esperado="PASS")], [_pertinencia()],
                      [reparacion_e, reparacion_p])
        log = "\n".join([
            _congelar(), _aprobacion(token_adopcion, _hash(v2)),
            _aprobacion(token_e, _hash(v3), "A", 3, 1),
            _aprobacion(token_p, _hash(v3), "A", 3, 1),
        ])
        _comprobar(tmp, [v1, v2, v3], log, "final", 0)
        return
    if numero in {42, 43, 44, 46}:
        if numero == 42:
            _comprobar_procedimiento_cinco_mediciones()
            _comprobar_wrapper_documentado()
        predicado = "printf 'raw\\n'; exit 7"
        proyector = "cat >/dev/null; printf 'diagnóstico\\n' >&2; printf 'failures=2\\n'"
        fila_1 = _fila(comando=predicado, baseline="RED")
        v1 = _legado(fila_1, [_registro("A", "exit 7; raw")])
        cuerpo = MODULO.PROJECTION_WRAPPER_BODY
        predicado_nuevo = predicado
        if numero == 44:
            predicado_nuevo = "printf 'otro\\n'; exit 7"
        if numero == 46:
            cuerpo += "; :"
        comando = _envoltura(predicado_nuevo, proyector, cuerpo)
        token, adopcion = _adopcion(2, 1, ajustado="A")
        v2 = _version(
            2, v1, [_fila(comando=comando, baseline="RED")],
            [_pertinencia(tipo="fallos-conteo", fundamento="conteo de fallos preexistentes")],
            adopcion=adopcion, registros=[_registro("A", "exit 7; failures=2")])
        if numero in {42, 43}:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 0)
            if numero == 43:
                resultado = subprocess.run(
                    comando, shell=True, executable="/bin/sh", capture_output=True,
                    text=True, encoding=ENCODING, check=False)
                assert resultado.returncode == 7 and resultado.stdout == "raw\nfailures=2\n"
                assert resultado.stderr == ""
        elif numero == 44:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                       "no conserva el predicado previo")
        else:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                       "cuerpo canónico inválido")
        return
    if numero == 45:
        v1 = _version(1, None, [_fila(comando="printf uno | cat")], [_pertinencia()])
        _comprobar(tmp, [v1], "", "final", 1, "dialecto de tabla inválido")
        return
    if numero in {47, 48, 49, 50}:
        fila_1 = _fila(baseline="RED")
        v1 = _legado(fila_1, [_registro("A", "exit 1; failures=2")])
        estado = "intermedia" if numero == 50 else "final"
        token, adopcion = _adopcion(2, 1, estado=estado, actualizado="A")
        if numero == 48:
            baseline, registro = "BLOCKED", _registro("A")
        else:
            baseline = "GREEN_ALREADY"
            adjudicacion = None if numero == 49 else (
                "weak_check" if numero == 50 else "already_satisfied")
            registro = _registro("A", "exit 0; failures=0", adjudicacion)
        v2 = _version(
            2, v1, [_fila(baseline=baseline)],
            [_pertinencia(tipo="fallos-conteo", fundamento="conteo de fallos preexistentes")],
            adopcion=adopcion, registros=[registro])
        log = _aprobacion(token, _hash(v2))
        if numero == 47:
            _comprobar(tmp, [v1, v2], log, "final", 0)
            token, adopcion = _adopcion(2, 1, actualizado="A")
            sin_cambio = _version(
                2, v1, [_fila(baseline="RED")],
                [_pertinencia(tipo="fallos-conteo", fundamento="conteo de fallos preexistentes")],
                adopcion=adopcion, registros=[_registro("A", "exit 1; failures=2")])
            _comprobar(tmp, [v1, sin_cambio], _aprobacion(token, _hash(sin_cambio)), "final", 1,
                       "baseline_actualizado sin cambio")
        elif numero == 48:
            _comprobar(tmp, [v1, v2], log, "final", 1, "baseline_actualizado inválido")
            token, adopcion = _adopcion(2, 1, actualizado="A")
            no_aplicable = _version(
                2, v1, [_fila(baseline="NOT_APPLICABLE")],
                [_pertinencia(tipo="fallos-conteo", fundamento="conteo de fallos preexistentes")],
                adopcion=adopcion,
                registros=[_registro("A", justificacion="la medición no aplica")])
            _comprobar(tmp, [v1, no_aplicable], _aprobacion(token, _hash(no_aplicable)), "final", 1,
                       "baseline_actualizado inválido")
        elif numero == 49:
            _comprobar(tmp, [v1, v2], log, "final", 1, "sin adjudicación")
        else:
            _comprobar(tmp, [v1, v2], log, "candidate", 0)
            _comprobar(tmp, [v1, v2], log, "final", 1,
                       "una adopción intermedia no admite fase final")
        return
    if numero == 51:
        v1 = _version(
            1, None, [_fila(baseline="GREEN_ALREADY")],
            [_pertinencia(tipo="fallos-conteo", fundamento="conteo de fallos preexistentes")],
            registros=[_registro("A", "exit 0; failures=0", "weak_check")])
        _comprobar(tmp, [v1], "", "candidate", 1, "weak_check fuera de adopción intermedia")
        return
    if numero == 52:
        v1 = _legado()
        token, adopcion = _adopcion(2, 1)
        v2 = _version(2, v1, [_fila(requisito="mutado")], [_pertinencia()], adopcion=adopcion)
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "cambia una columna semántica protegida")
        token, adopcion = _adopcion(2, 1)
        v2 = _version(2, v1, [_fila(baseline="RED")], [_pertinencia()], adopcion=adopcion)
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "Baseline cambia fuera de baseline_actualizado")
        token, adopcion = _adopcion(2, 1)
        v2 = _version(2, v1, [_fila(comando="python3 -c 'print(2)'")],
                      [_pertinencia()], adopcion=adopcion)
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "comando cambia fuera de proyeccion_ajustada")
        token, adopcion = _adopcion(2, 1, ajustado="A")
        v2 = _version(2, v1, [_fila(comando=_envoltura(
            "python3 -c 'print(1)'", "printf 'failures=0\\n'"))],
            [_pertinencia(tipo="otro")], adopcion=adopcion)
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "proyeccion_ajustada exige baseline fallos-*")
        return
    if numero == 53:
        registro_1 = _registro("A", justificacion="la evidencia no tiene baseline ejecutable")
        v1 = _legado(registros=[registro_1])
        token, adopcion = _adopcion(2, 1, reutilizado="A")
        registro_2 = _registro(
            "A", justificacion="la evidencia no tiene baseline ejecutable",
            timestamp="2026-01-01T00:02:00Z")
        v2 = _version(2, v1, [_fila()], [_pertinencia()], adopcion=adopcion,
                      registros=[registro_2])
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "baseline_reutilizado inválido")
        return
    if numero == 54:
        v1 = _legado(_fila(baseline="RED"), [_registro("A", "exit 1; failures=2")])
        token, adopcion = _adopcion(2, 1, reutilizado="A")
        v2 = _version(
            2, v1, [_fila(baseline="RED")],
            [_pertinencia(tipo="fallos-conteo", fundamento="conteo de fallos preexistentes")],
            adopcion=adopcion, registros=[_registro("A", "exit 1; failures=2")])
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                   "baseline_reutilizado inválido")
        return
    if numero == 55:
        v1 = _base()
        v2, token = _esperado(v1, 2, "GREEN", "PASS")
        extras = ("`objeto: contrato-integracion:v2`", "`resultado: consumado`",
                  "`detalle: reparación aprobada`")
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2), extras=extras), "final", 0)
        return
    if numero == 56:
        v1 = _base()
        evento = _aprobacion(
            "2:A:esperado-corregido:a1", _hash(v1), paso="adoptar-estado-contrato",
            actor="orquestador",
            extras=("`objeto: contrato-integracion:v1`", "`resultado: consumado`"))
        _comprobar(tmp, [v1], evento, "final", 0)
        v2, _token = _esperado(v1, 2, "GREEN", "PASS")
        _comprobar(tmp, [v1, v2], evento, "final", 1, "sin aprobación")
        return
    if numero == 57:
        v1 = _base()
        candidata_1, token_1 = _esperado(v1, 2, "GREEN", "PASS", 1)
        candidata_2, token_2 = _esperado(v1, 2, "GREEN", "PASS", 2)
        log = "\n".join([
            _congelar(), _aprobacion(token_1, _hash(candidata_1), "A", 2, 1),
            _aprobacion(token_2, _hash(candidata_2), "A", 2, 1),
        ])
        _comprobar(tmp, [v1, candidata_2], log, "final", 0)
        return
    if numero == 58:
        v1 = _base()
        candidata_1, token_1 = _esperado(v1, 2, "GREEN", "PASS", 1)
        candidata_2, token_2 = _esperado(v1, 2, "GREEN", "PASS", 2)
        log = "\n".join([
            _congelar(), _aprobacion(token_1, _hash(candidata_1), "A", 2, 1),
            _aprobacion(token_2, _hash(candidata_2), "A", 2, 2),
        ])
        _comprobar(tmp, [v1, candidata_2], log, "final", 1,
                   "el par (A, 2) usa dos ordinales")
        return
    if numero in {59, 60}:
        v1 = _base()
        pert_nueva = _pertinencia(autoridad="subafirmación Z")
        token, reparacion = _reparacion(
            2, 1, "A", "pertinencia-corregida", pertinencia_previa=_pertinencia())
        v2 = _version(2, v1, [_fila()], [pert_nueva], [] if numero == 59 else [reparacion])
        if numero == 59:
            _comprobar(tmp, [v1, v2], "", "final", 1,
                       "pertinencia de A cambia sin pertinencia-corregida único")
        else:
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 0)
        return
    if numero == 61:
        v1 = _legado()
        token, adopcion = _adopcion(2, 1)
        v2 = _version(2, v1, [_fila()], [_pertinencia()], adopcion=adopcion)
        extras = ("`objeto: contrato-integracion:v2`", "`resultado: consumado`",
                  "`detalle: adopción legado`")
        _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2), extras=extras), "final", 0)
        return
    if numero == 62:
        v1 = _base()
        pert_nueva = _pertinencia(autoridad="subafirmación Z")
        token_e, reparacion_e = _reparacion(
            2, 1, "A", "esperado-corregido", esperado_previo="GREEN")
        token_p, reparacion_p = _reparacion(
            2, 1, "A", "pertinencia-corregida", pertinencia_previa=_pertinencia())
        v2 = _version(2, v1, [_fila(esperado="PASS")], [pert_nueva],
                      [reparacion_e, reparacion_p])
        log = "\n".join([
            _congelar(), _aprobacion(token_e, _hash(v2), "A", 2, 1),
            _aprobacion(token_p, _hash(v2), "A", 2, 1),
        ])
        _comprobar(tmp, [v1, v2], log, "final", 0)
        return
    if numero == 63:
        v1 = _base()
        token_1, reparacion_1 = _reparacion(
            2, 1, "A", "esperado-corregido", esperado_previo="GREEN")
        token_2, reparacion_2 = _reparacion(
            2, 1, "A", "esperado-corregido", ordinal_token=2, esperado_previo="GREEN")
        v2 = _version(2, v1, [_fila(esperado="PASS")], [_pertinencia()],
                      [reparacion_1, reparacion_2])
        log = _aprobacion(token_1, _hash(v2)) + "\n" + _aprobacion(token_2, _hash(v2))
        _comprobar(tmp, [v1, v2], log, "final", 1, "registro duplicado")
        return
    if numero in {64, 65}:
        predicado = "printf 'raw\\n'; exit 7"
        proyector_1 = "cat >/dev/null; printf 'failures=2\\n'"
        proyector_2 = "cat >/dev/null; printf 'failures=1\\n'"
        comando_1 = _envoltura(predicado, proyector_1)
        pert = _pertinencia(tipo="fallos-conteo", fundamento="conteo de fallos preexistentes")
        v1 = _version(1, None, [_fila(comando=comando_1, baseline="RED")], [pert],
                      registros=[_registro("A", "exit 7; failures=2")])
        comando_2 = _envoltura(predicado, proyector_2)
        if numero == 64:
            v2, token = _verificacion(v1, 2, comando_1, comando_2, pertinencia=pert,
                                      registros=[_registro("A", "exit 7; failures=1")])
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 0)
        else:
            cambiado = _envoltura("printf 'cambio\\n'; exit 7", proyector_2)
            v2, token = _verificacion(v1, 2, comando_1, cambiado, pertinencia=pert,
                                      registros=[_registro("A", "exit 7; failures=1")])
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                       "no conserva el predicado previo")
            anidado = _envoltura(comando_1, proyector_2)
            v2, token = _verificacion(v1, 2, comando_1, anidado, pertinencia=pert,
                                      registros=[_registro("A", "exit 7; failures=1")])
            _comprobar(tmp, [v1, v2], _aprobacion(token, _hash(v2)), "final", 1,
                       "envoltura de proyección anidada")
        return
    raise AssertionError(f"caso sin constructor: {numero}")


NOMBRES = (
    "adicion-candidate-sin-aprobacion", "adicion-final-sin-aprobacion",
    "adicion-aprobada-antes-freeze", "adicion-reevaluada-despues",
    "adicion-aprobada-despues-freeze", "cobertura-agregada-exclusiva",
    "cobertura-agregada-con-operacion-extra", "id-retirado", "requisito-cambiado",
    "esperado-sin-aprobacion", "esperado-aprobado", "version-resellada",
    "dos-versiones-defecto", "tercera-version-design-gap", "reaprobacion-sin-doble-consumo",
    "verificacion-inline-post-freeze", "dos-verificaciones-aprobadas",
    "verificacion-aprobada-para-otro-id", "dos-ids-un-registro",
    "verificacion-sin-diferencia", "verificacion-sin-aprobacion",
    "aprobacion-defecto-incompleta", "tercera-verificacion-design-gap",
    "pertinencia-ausente-o-duplicada", "pertinencia-caracter-estructural",
    "baseline-tipo-ausente-o-invalido", "baseline-fundamento-ausente-o-vacio",
    "baseline-tipo-proyeccion-incongruente", "baseline-otro-entero",
    "blocked-o-na-sin-observado", "reparacion-id-o-version-ajenos",
    "esperado-post-freeze-sin-par", "pertinencia-post-freeze-sin-par", "fase-invalida",
    "legado-sin-adopcion", "adopcion-final-aprobada", "adopcion-intermedia-candidate",
    "adopcion-intermedia-reparada", "adopcion-sin-aprobacion",
    "adopcion-intermedia-final", "adopcion-post-freeze-sin-presupuesto",
    "adopcion-proyeccion-ajustada", "wrapper-preserva-codigo",
    "wrapper-predicado-ajeno", "comando-con-barra", "wrapper-cuerpo-no-canonico",
    "adopcion-baseline-actualizado", "baseline-actualizado-blocked",
    "baseline-green-sin-adjudicacion", "weak-check-intermedia",
    "weak-check-fuera-intermedia", "adopcion-altera-campos",
    "baseline-reutilizado-incongruente", "baseline-fallos-reutilizado",
    "evento-orquestador-aprobacion", "evento-adoptar-no-aprueba",
    "resellado-conserva-ordinal-defecto", "resellado-cambia-ordinal-defecto",
    "pertinencia-cambia-sin-registro", "pertinencia-corregida-aprobada",
    "adopcion-integracion-sin-par", "dos-operaciones-un-consumo",
    "operacion-duplicada", "reparacion-mecanica-proyector",
    "reparacion-mecanica-altera-predicado",
)


def _ids(*rangos: Tuple[int, int]) -> FrozenSet[str]:
    return frozenset(
        "contrato-invariantes/ci-{0:03d}".format(numero)
        for inicio, fin in rangos for numero in range(inicio, fin + 1)
    )


EXPECTED_IDS_BY_AC = {
    "AC-2": _ids((24, 30), (35, 38), (42, 42), (47, 53)),
    "AC-3": _ids((1, 12), (35, 42), (44, 44), (52, 52), (59, 59), (64, 65)),
    "AC-4": _ids((6, 7), (10, 12), (17, 21), (31, 31), (38, 38), (42, 42),
                     (52, 52), (57, 60), (62, 65)),
    "AC-5": _ids((3, 7), (10, 23), (31, 33), (35, 42), (55, 55), (57, 63)),
    "AC-6": _ids((5, 5), (12, 17), (21, 23), (32, 33), (41, 41), (55, 58), (61, 63)),
    "AC-8": _ids((42, 42), (47, 47), (53, 54)),
    "AC-9": _ids((42, 46), (48, 48), (54, 54), (64, 65)),
    "AC-10": _ids((48, 48), (54, 54)),
    "AC-11": _ids((1, 2), (21, 21), (34, 34), (37, 37), (40, 40)),
    "AC-14": _ids((28, 28), (30, 30), (35, 42), (47, 54), (61, 61)),
}


class Definicion(NamedTuple):
    identidad: str
    nombre: str
    constructor: Constructor
    resultado: str
    tags: Tuple[str, ...]


DEFINICIONES: List[Definicion] = []
CASOS: List[Caso] = []
for _numero, _nombre in enumerate(NOMBRES, 1):
    _identidad = "contrato-invariantes/ci-{0:03d}".format(_numero)
    _tags = tuple(ac for ac, ids in EXPECTED_IDS_BY_AC.items() if _identidad in ids)

    def _constructor(tmp: Path, numero: int = _numero) -> None:
        _caso(numero, tmp)

    _resultado = "aceptación o rechazo y diagnóstico definidos por AC-13"
    _definicion = Definicion(_identidad, _nombre, _constructor, _resultado, _tags)
    DEFINICIONES.append(_definicion)

    def _test_funcion(_contexto: Optional[object], definicion: Definicion = _definicion) -> None:
        with tempfile.TemporaryDirectory(prefix="contrato-invariantes-v2-") as temporal:
            definicion.constructor(Path(temporal))

    _test_funcion.__name__ = "test_contrato_invariantes_ci_{0:03d}".format(_numero)
    _test_funcion.__doc__ = f"{_identidad}: {_nombre}."
    setattr(_test_funcion, "_builder", _constructor)
    setattr(_test_funcion, "_expected", _resultado)
    setattr(_test_funcion, "_tags", _tags)
    globals()[_test_funcion.__name__] = _test_funcion
    CASOS.append((_identidad, "contrato-invariantes-v1", _test_funcion))


def _validar_corpus() -> None:
    identidades = [identidad for identidad, _grupo, _funcion in CASOS]
    esperadas = ["contrato-invariantes/ci-{0:03d}".format(n) for n in range(1, 66)]
    assert identidades == esperadas
    assert len(NOMBRES) == len(DEFINICIONES) == len(set(NOMBRES)) == 65
    assert len(identidades) == len(set(identidades)) == 65
    assert len({id(definicion.constructor) for definicion in DEFINICIONES}) == 65
    union = set().union(*EXPECTED_IDS_BY_AC.values())
    assert union == set(identidades)
    for definicion in DEFINICIONES:
        esperados = {ac for ac, ids in EXPECTED_IDS_BY_AC.items() if definicion.identidad in ids}
        assert set(definicion.tags) == esperados and definicion.tags


def verificar_ac(ac: str) -> int:
    """Valida el mapa externo y ejecuta la selección cerrada de un criterio."""
    _validar_corpus()
    if ac not in EXPECTED_IDS_BY_AC:
        print(f"{ac}: 0/0 casos ok")
        return 1
    observados = {definicion.identidad for definicion in DEFINICIONES if ac in definicion.tags}
    if observados != EXPECTED_IDS_BY_AC[ac]:
        print(f"{ac}: mapa de identidades divergente")
        return 1
    seleccionados = [(identidad, funcion) for identidad, _grupo, funcion in CASOS
                     if identidad in EXPECTED_IDS_BY_AC[ac]]
    fallos = 0
    for identidad, funcion in seleccionados:
        try:
            funcion(None)
        except Exception as error:
            fallos += 1
            print(f"{identidad}: ERROR {type(error).__name__}: {error}")
    total = len(seleccionados)
    print(f"{ac}: {total - fallos}/{total} casos ok")
    return 1 if fallos or total == 0 else 0
