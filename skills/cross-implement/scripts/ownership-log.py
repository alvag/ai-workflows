"""Predicado: valida las clasificaciones delegadas y las auxiliares inline u orquestadas, sus cuatro
campos comunes, el par prospectivo de VERIFICATION_DEFECT solo donde corresponde, la ronda cero de
clases no implementables y que un mismo delta de implementación no se fragmente entre rondas."""

from __future__ import annotations

import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


CLASES = {"IMPLEMENTATION_DEFECT", "VERIFICATION_DEFECT", "ENVIRONMENT_FAILURE", "DESIGN_GAP"}
GENERICO = re.compile(
    r"no cubrió|no cubrio|faltó manejar|falto manejar|no entendió|no entendio|"
    r"algún borde|algun borde|no quedó bien|no quedo bien", re.IGNORECASE)
_RUTA_CONTRATO = Path(__file__).resolve().with_name("contrato-invariantes.py")
try:
    _ESPECIFICACION = importlib.util.spec_from_file_location("ownership_log_contrato", _RUTA_CONTRATO)
    if _ESPECIFICACION is None or _ESPECIFICACION.loader is None:
        raise RuntimeError(f"no se pudo cargar {_RUTA_CONTRATO}")
    _CONTRATO = importlib.util.module_from_spec(_ESPECIFICACION)
    _ESPECIFICACION.loader.exec_module(_CONTRATO)
    if not callable(getattr(_CONTRATO, "campos_linea", None)):
        raise RuntimeError("API de campos ausente")
except Exception as error:
    print(f"ARNES:ownership-log dependencia contrato-invariantes.py no cargable: {error}",
          file=sys.stderr)
    raise SystemExit(99) from None


def valor(linea: str, campo: str) -> str:
    return _CONTRATO.campos_linea(linea).get(campo, "")


def lineas_ownership(texto: str) -> List[Tuple[int, str]]:
    resultado: List[Tuple[int, str]] = []
    dentro = False
    for indice, linea in enumerate(texto.splitlines()):
        if linea == "Ownership:":
            dentro = True
            continue
        if dentro and (linea.startswith("## ") or not linea.strip()):
            dentro = False
        if dentro and linea.startswith("- `checkId: "):
            resultado.append((indice, linea))
    return resultado


def clasificaciones(texto: str) -> List[Tuple[str, str]]:
    lineas = texto.splitlines()
    delegadas = {indice for indice, _linea in lineas_ownership(texto)}
    resultado: List[Tuple[str, str]] = []
    for indice, linea in enumerate(lineas):
        if indice in delegadas:
            resultado.append(("delegada", linea))
        elif "`paso: clasificar-falla`" in linea:
            resultado.append(("auxiliar", linea.strip()))
    return resultado


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:ownership-log log", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    entradas = clasificaciones(texto)
    rc = 0
    apariciones: Dict[str, int] = defaultdict(int)
    rondas: Dict[Tuple[str, int], int] = defaultdict(int)
    delta_rondas: Dict[str, Set[int]] = defaultdict(set)
    for forma, linea in entradas:
        check_id = valor(linea, "checkId")
        clase = valor(linea, "clase")
        consumida = valor(linea, "consumedRound")
        if not check_id or clase not in CLASES:
            print(f'GUARD:log-clasificacion {check_id or "sin-checkId"}: clase inválida "{clase}"',
                  file=sys.stderr)
            rc = 1
        if not valor(linea, "evidencia"):
            print(f"GUARD:log-clasificacion {check_id}: sin evidencia", file=sys.stderr)
            rc = 1
        esperado = "sí" if clase == "IMPLEMENTATION_DEFECT" else "no"
        if consumida != esperado:
            print(f'GUARD:log-clasificacion {check_id}: consumedRound="{consumida or "ausente"}" '
                  f'y la clase {clase} exige "{esperado}"', file=sys.stderr)
            rc = 1
        if forma == "delegada" and any(valor(linea, campo) for campo in
                                        ("contract_version", "verification_defect_ordinal")):
            print(f"GUARD:log-clasificacion {check_id}: la forma delegada no proyecta par de defecto",
                  file=sys.stderr)
            rc = 1
        if forma == "auxiliar":
            obligatorios = ("actor", "timestamp", "delta", "fix_round")
            if any(not valor(linea, campo) for campo in obligatorios):
                print(f"GUARD:log-clasificacion {check_id}: línea auxiliar incompleta", file=sys.stderr)
                rc = 1
            try:
                ronda = int(valor(linea, "fix_round"))
            except ValueError:
                ronda = -1
            if clase == "IMPLEMENTATION_DEFECT":
                if ronda < 1:
                    print(f"GUARD:log-clasificacion {check_id}: implementación sin ronda positiva",
                          file=sys.stderr)
                    rc = 1
                delta = valor(linea, "delta")
                rondas[(delta, ronda)] += 1
                delta_rondas[delta].add(ronda)
            elif ronda != 0:
                print(f"GUARD:log-clasificacion {check_id}: {clase} exige fix_round 0",
                      file=sys.stderr)
                rc = 1
            if clase == "VERIFICATION_DEFECT":
                if not valor(linea, "contract_version") or not valor(
                        linea, "verification_defect_ordinal"):
                    print(f"GUARD:log-clasificacion {check_id}: proyección de defecto incompleta",
                          file=sys.stderr)
                    rc = 1
        elif clase == "IMPLEMENTATION_DEFECT" and valor(linea, "delta"):
            try:
                ronda = int(valor(linea, "fix_round"))
            except ValueError:
                ronda = -1
            if ronda < 1:
                print(f"GUARD:log-clasificacion {check_id}: implementación sin ronda positiva",
                      file=sys.stderr)
                rc = 1
            delta = valor(linea, "delta")
            rondas[(delta, ronda)] += 1
            delta_rondas[delta].add(ronda)
        apariciones[check_id] += 1
        if apariciones[check_id] > 1:
            razon = valor(linea, "razón")
            if not razon:
                print(f"GUARD:razon-falsable {check_id}: aparición {apariciones[check_id]} sin razón registrada",
                      file=sys.stderr)
                rc = 1
            elif GENERICO.search(razon):
                print(f"GUARD:razon-falsable {check_id}: la razón no nombra un observable que la refute",
                      file=sys.stderr)
                rc = 1
    for (delta, ronda), cantidad in sorted(rondas.items()):
        if cantidad > 1:
            print(f"GUARD:delta-una-ronda {delta}: fix_round {ronda} aparece {cantidad} veces",
                  file=sys.stderr)
            rc = 1
    for delta, indices in sorted(delta_rondas.items()):
        if len(indices) > 1:
            print(f"GUARD:delta-una-ronda {delta}: repartido entre {len(indices)} rondas",
                  file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
