"""Genera escenarios durables de paridad desde el inventario autoritativo."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


ENCODING = "utf-8"
TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = TESTS_DIR.parent
INVENTORY_PATH = TESTS_DIR / "inventario-bloques.md"
CATALOG_PATH = TESTS_DIR / "casos" / "escenarios.jsonl"
SECTION_TITLE = "## 4. Pares matriz/caso"
EXPECTED_SCENARIOS = 397


@dataclass(frozen=True)
class Escenario:
    identidad: str
    matriz: str
    caso: str
    hash_matriz: str
    fixture: str
    entradas: Dict[str, str]
    reemplazos: Tuple[Dict[str, str], ...]
    clase_esperada: str
    particion: str
    precondicion: str

    def serialized(self) -> Dict[str, object]:
        value = asdict(self)
        value["reemplazos"] = list(self.reemplazos)
        return value


def _unquote_code(value: str) -> str:
    if len(value) < 2 or not value.startswith("`") or not value.endswith("`"):
        raise ValueError("expected an inline-code inventory value")
    return value[1:-1]


def _parse_fixture(value: str) -> Tuple[str, Dict[str, str], Tuple[Dict[str, str], ...]]:
    try:
        fixture, payload = value.split("; entradas=", 1)
    except ValueError as exc:
        raise ValueError("scenario row does not declare entradas") from exc

    if "; reemplazos=" in payload:
        inputs_text, replacements_text = payload.split("; reemplazos=", 1)
        replacements_value = json.loads(replacements_text)
    else:
        inputs_text = payload
        replacements_value = []
    inputs_value = json.loads(inputs_text)

    if not isinstance(inputs_value, dict) or not all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in inputs_value.items()):
        raise ValueError("entradas must be an object of strings")
    if not isinstance(replacements_value, list):
        raise ValueError("reemplazos must be a list")
    replacements: List[Dict[str, str]] = []
    for replacement in replacements_value:
        if not isinstance(replacement, dict) or set(replacement) != {
                "archivo", "buscar", "reemplazar"}:
            raise ValueError("each replacement must declare archivo, buscar and reemplazar")
        if not all(isinstance(item, str) for item in replacement.values()):
            raise ValueError("replacement values must be strings")
        replacements.append(replacement)
    return fixture, inputs_value, tuple(replacements)


def _parse_observation(value: str) -> Tuple[str, str]:
    prefix = "clase="
    separator = "; partición="
    if not value.startswith(prefix) or separator not in value:
        raise ValueError("scenario row has an invalid base observation")
    expected_class, partition = value[len(prefix):].split(separator, 1)
    if not expected_class or not partition:
        raise ValueError("scenario row has an incomplete base observation")
    return expected_class, partition


def _parse_row(line: str) -> Escenario:
    columns = line[2:-2].split(" | ", 4)
    if len(columns) != 5:
        raise ValueError("scenario row does not have five columns")

    identity = _unquote_code(columns[0])
    if identity.count("/") != 1:
        raise ValueError("scenario identity must be the matrix/case pair")
    matrix, case = identity.split("/", 1)
    matrix_hash = _unquote_code(columns[1])
    if not matrix_hash.startswith("sha256:") or len(matrix_hash) != 71:
        raise ValueError("scenario row has an invalid matrix SHA-256")
    try:
        int(matrix_hash[7:], 16)
    except ValueError as exc:
        raise ValueError("scenario row has a non-hexadecimal matrix SHA-256") from exc

    fixture, inputs, replacements = _parse_fixture(columns[2])
    expected_class, partition = _parse_observation(columns[3])
    return Escenario(
        identidad=identity,
        matriz=matrix,
        caso=case,
        hash_matriz=matrix_hash,
        fixture=fixture,
        entradas=inputs,
        reemplazos=replacements,
        clase_esperada=expected_class,
        particion=partition,
        precondicion=columns[4],
    )


def read_inventory(path: Path = INVENTORY_PATH) -> Tuple[Escenario, ...]:
    """Read the 397 authoritative matrix/case rows without consulting the old matrices."""
    scenarios: List[Escenario] = []
    identities = set()
    in_section = False
    for line in path.read_text(encoding=ENCODING).splitlines():
        if line == SECTION_TITLE:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.startswith("| `"):
            continue
        scenario = _parse_row(line)
        if scenario.identidad in identities:
            raise ValueError("duplicate scenario identity: " + scenario.identidad)
        identities.add(scenario.identidad)
        scenarios.append(scenario)

    if len(scenarios) != EXPECTED_SCENARIOS:
        raise ValueError(
            "expected {0} scenarios, found {1}".format(EXPECTED_SCENARIOS, len(scenarios)))
    return tuple(scenarios)


def _verify_source_hashes(scenarios: Iterable[Escenario]) -> None:
    hashes: Dict[str, str] = {}
    for scenario in scenarios:
        previous = hashes.setdefault(scenario.matriz, scenario.hash_matriz)
        if previous != scenario.hash_matriz:
            raise ValueError("matrix has more than one inventory hash: " + scenario.matriz)

    for matrix, expected in hashes.items():
        source = REPO_DIR / "scripts" / "paridad-casos" / matrix / "casos.json"
        # The digest covers the original bytes, so this is intentionally a binary read.
        actual = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(
                "matrix hash mismatch for {0}: expected {1}, found {2}".format(
                    matrix, expected, actual))


def write_catalog(path: Path = CATALOG_PATH) -> Tuple[Escenario, ...]:
    """Generate one JSON Lines scenario per authoritative matrix/case identity."""
    scenarios = read_inventory()
    _verify_source_hashes(scenarios)
    body = "".join(
        json.dumps(scenario.serialized(), ensure_ascii=False, sort_keys=True) + "\n"
        for scenario in scenarios
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding=ENCODING)
    return scenarios


def load_catalog(path: Path = CATALOG_PATH) -> Tuple[Escenario, ...]:
    """Load the generated catalog without depending on the corpus that will be retired."""
    scenarios: List[Escenario] = []
    for line_number, line in enumerate(path.read_text(encoding=ENCODING).splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("catalog line {0} is not an object".format(line_number))
        replacements = value.get("reemplazos")
        if not isinstance(replacements, list):
            raise ValueError("catalog line {0} has invalid replacements".format(line_number))
        value["reemplazos"] = tuple(replacements)
        scenarios.append(Escenario(**value))
    if len(scenarios) != EXPECTED_SCENARIOS:
        raise ValueError(
            "expected {0} catalog scenarios, found {1}".format(
                EXPECTED_SCENARIOS, len(scenarios)))
    return tuple(scenarios)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args(argv)
    if not args.generate:
        parser.error("--generate is required")
    scenarios = write_catalog()
    print("generated {0} scenarios in {1}".format(len(scenarios), CATALOG_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
