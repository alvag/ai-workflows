"""Predicado: cuenta VERIFICATION_DEFECT solo por pares aprobados únicos y las demás clases por
aparición física; concilia proyecciones delegadas, inline y orquestadas sin doble lectura ni doble
consumo, y rechaza cualquier presupuesto excedido."""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


CLASES = {"IMPLEMENTATION_DEFECT", "VERIFICATION_DEFECT", "ENVIRONMENT_FAILURE", "DESIGN_GAP"}
_RUTA_CONTRATO = Path(__file__).resolve().with_name("contrato-invariantes.py")
try:
    _ESPECIFICACION = importlib.util.spec_from_file_location("ownership_presupuesto_contrato", _RUTA_CONTRATO)
    if _ESPECIFICACION is None or _ESPECIFICACION.loader is None:
        raise RuntimeError(f"no se pudo cargar {_RUTA_CONTRATO}")
    _CONTRATO = importlib.util.module_from_spec(_ESPECIFICACION)
    _ESPECIFICACION.loader.exec_module(_CONTRATO)
    if not callable(getattr(_CONTRATO, "campos_linea", None)):
        raise RuntimeError("API de campos ausente")
except Exception as error:
    print(f"ARNES:ownership-presupuesto dependencia contrato-invariantes.py no cargable: {error}",
          file=sys.stderr)
    raise SystemExit(99) from None


def _clasificaciones(texto: str) -> List[Tuple[str, str]]:
    resultado: List[Tuple[str, str]] = []
    dentro = False
    for linea in texto.splitlines():
        if linea == "Ownership:":
            dentro = True
            continue
        if dentro and (linea.startswith("## ") or not linea.strip()):
            dentro = False
        if (dentro and linea.startswith("- `checkId: ")) or \
                "`paso: clasificar-falla`" in linea:
            campos = _CONTRATO.campos_linea(linea)
            if not campos.get("checkId") or not campos.get("clase"):
                raise ValueError("clasificación inválida")
            resultado.append((campos["checkId"], campos["clase"]))
    return resultado


def _pares_aprobados(texto: str) -> List[Tuple[str, int, int]]:
    resultado: List[Tuple[str, int, int]] = []
    for linea in texto.splitlines():
        if "`paso: aprobar-reparación`" not in linea:
            continue
        campos = _CONTRATO.campos_linea(linea)
        if not campos:
            raise ValueError("aprobación malformada")
        check_id = campos.get("checkId", "")
        version = campos.get("contract_version", "")
        ordinal = campos.get("verification_defect_ordinal", "")
        if not any((check_id, version, ordinal)):
            continue
        if not all((check_id, version, ordinal)):
            raise ValueError("par de aprobación incompleto")
        try:
            resultado.append((check_id, int(version), int(ordinal)))
        except ValueError as error:
            raise ValueError("versión u ordinal de aprobación inválidos") from error
    return resultado


def main() -> int:
    if len(sys.argv) != 4:
        print("USO:ownership-presupuesto log approval_log max_fix_rounds", file=sys.stderr)
        return 2
    try:
        log_path = Path(sys.argv[1])
        approval_path = Path(sys.argv[2])
        max_fix_rounds = int(sys.argv[3])
        if max_fix_rounds < 0:
            raise ValueError("límite de rondas inválido")
    except ValueError as error:
        print(f"GUARD:presupuesto-por-check {error}", file=sys.stderr)
        return 1
    try:
        textos: Dict[Path, str] = {}
        for ruta in (log_path, approval_path):
            resuelta = ruta.resolve()
            if resuelta not in textos:
                textos[resuelta] = ruta.read_text(encoding="utf-8")
        log = textos[log_path.resolve()]
        approval_log = textos[approval_path.resolve()]
        pares = _pares_aprobados(approval_log)
    except (OSError, UnicodeError) as error:
        print(f"GUARD:presupuesto-por-check archivo ilegible: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"GUARD:presupuesto-por-check {error}", file=sys.stderr)
        return 1
    try:
        clasificaciones = _clasificaciones(log)
    except ValueError as error:
        print(f"GUARD:presupuesto-por-check {error}", file=sys.stderr)
        return 1
    excesos: List[str] = []
    fisicas = Counter(
        (check_id, clase) for check_id, clase in clasificaciones
        if clase in CLASES and clase != "VERIFICATION_DEFECT"
    )
    for (check_id, clase), cantidad in sorted(fisicas.items()):
        if clase == "IMPLEMENTATION_DEFECT":
            tope = max_fix_rounds
        elif clase == "DESIGN_GAP":
            tope = 1
        else:
            tope = 2
        if cantidad > tope:
            excesos.append(f"  {check_id} · {clase} · {cantidad} > {tope}")
    clases_verificacion = {check_id for check_id, clase in clasificaciones
                           if clase == "VERIFICATION_DEFECT"}
    por_id: Dict[str, Dict[int, Set[int]]] = defaultdict(lambda: defaultdict(set))
    for check_id, version, ordinal in pares:
        por_id[check_id][version].add(ordinal)
    for check_id, versiones in sorted(por_id.items()):
        if check_id not in clases_verificacion:
            excesos.append(f"  {check_id} · VERIFICATION_DEFECT · aprobación sin clasificación")
        if any(len(ordinales) != 1 for ordinales in versiones.values()):
            excesos.append(f"  {check_id} · VERIFICATION_DEFECT · ordinal divergente por par")
            continue
        ordinales = [next(iter(versiones[version])) for version in sorted(versiones)]
        if ordinales != list(range(1, len(ordinales) + 1)):
            excesos.append(f"  {check_id} · VERIFICATION_DEFECT · ordinales no consecutivos")
        if len(versiones) > 2:
            excesos.append(f"  {check_id} · VERIFICATION_DEFECT · {len(versiones)} > 2")
    if excesos:
        print("GUARD:presupuesto-por-check presupuesto excedido:", file=sys.stderr)
        print("\n".join(excesos), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
