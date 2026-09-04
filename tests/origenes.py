"""Procedencia cerrada de los tests contra el inventario de migracion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Set, Tuple


ENCODING = "utf-8"
TESTS_DIR = Path(__file__).resolve().parent
INVENTORY = TESTS_DIR / "inventario-bloques.md"
SECTION_TARGETS = "## 1. Nombres base y destino propuesto"
SECTION_CASES = "## 4. Pares matriz/caso"
Origin = Tuple[str, str]


@dataclass(frozen=True)
class CoverageTargets:
    guards: frozenset[str]
    infrastructure: frozenset[str]
    cases: frozenset[str]
    guards_by_skill: Dict[str, frozenset[str]]

    @property
    def inventory(self) -> frozenset[Origin]:
        return frozenset(
            {("guard", name) for name in self.guards}
            | {("infrastructure", name) for name in self.infrastructure}
        )

    @property
    def migrated_cases(self) -> frozenset[Origin]:
        return frozenset(("case", identity) for identity in self.cases)

    @property
    def all(self) -> frozenset[Origin]:
        return self.inventory | self.migrated_cases


def _section(text: str, title: str) -> str:
    if text.count(title) != 1:
        raise ValueError("inventory section is missing or duplicated: " + title)
    tail = text.split(title, 1)[1]
    return tail.split("\n## ", 1)[0]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) < 2 or not value.startswith("`") or not value.endswith("`"):
        raise ValueError("expected an inline-code inventory value: " + value)
    return value[1:-1]


def read_targets(path: Path = INVENTORY) -> CoverageTargets:
    text = path.read_text(encoding=ENCODING)
    guards: Set[str] = set()
    infrastructure: Set[str] = set()
    by_skill: Dict[str, Set[str]] = {}
    for line in _section(text, SECTION_TARGETS).splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        name, classification, destination = (
            _unquote(cells[0]), cells[2], _unquote(cells[3]))
        if classification == "guarda":
            guards.add(name)
            parts = Path(destination).parts
            if len(parts) < 3 or parts[0] != "skills":
                raise ValueError("guard outside a skill: " + name)
            by_skill.setdefault(parts[1], set()).add(name)
        elif classification == "infraestructura de tests":
            infrastructure.add(name)

    cases = set()
    for line in _section(text, SECTION_CASES).splitlines():
        if line.startswith("| `"):
            cases.add(_unquote(line[2:].split(" | ", 1)[0]))
    if len(guards) != 37 or len(infrastructure) != 1 or len(cases) != 397:
        raise ValueError(
            "unexpected coverage cardinality: guards={0}, infrastructure={1}, cases={2}".format(
                len(guards), len(infrastructure), len(cases)))
    return CoverageTargets(
        guards=frozenset(guards),
        infrastructure=frozenset(infrastructure),
        cases=frozenset(cases),
        guards_by_skill={key: frozenset(value) for key, value in by_skill.items()},
    )


ORIGEN_SIN_MIGRACION: frozenset = frozenset({("guard", "apertura")})
"""Origen que se declara cuando un caso NO deriva de ninguna migracion.

Existe porque `validate_coverage` exige un origen a todo caso y rechaza como huerfano al que no
lo tiene. El literal ya vivia sin nombre en tres `return` de `origins_for`; esos se conservan como
estan, y nombrarlo aca no los migra. El costo esta aceptado y escrito: infla nominalmente la
cobertura de una guarda que ya esta cubierta por su propio caso, asi que no oculta ningun hueco.
"""


def origins_for(identifier: str, group: str,
                targets: CoverageTargets) -> frozenset[Origin]:
    if identifier.startswith("escenario:"):
        return frozenset({("case", identifier.split(":", 1)[1])})
    for prefix in ("firma:", "mutante-v24:"):
        if identifier.startswith(prefix):
            return frozenset({("guard", identifier.split(":", 1)[1])})
    if group == "fixtures-orquestacion-v12":
        return frozenset({("infrastructure", "fixtures-orquestacion")})
    if identifier.startswith("runtime-v4:"):
        skill = identifier.split(":", 2)[1]
        return frozenset(("guard", name)
                         for name in targets.guards_by_skill.get(skill, frozenset()))
    if group == "runtime-v5":
        return frozenset({("guard", "apertura")})
    if group == "sedes-config-vault":
        return frozenset({("guard", "apertura")})
    if group == "huellas-secuencia":
        # No deriva de ninguna migracion: nace con la receta de serializacion de las huellas. No se
        # reutiliza un grupo existente, que le atribuiria un flujo historico ajeno, ni entra al
        # inventario, porque `origins_for` solo lee sus secciones 1 y 4 y una fila en la 7 no crearia
        # un origen valido.
        return ORIGEN_SIN_MIGRACION
    if group in {"dimensiones", "normalizaciones"}:
        return frozenset({("case", "contrato-cadena/positivo")})
    if identifier in {"cobertura-v14:tres-direcciones", "entrypoint-v20:ids"}:
        return frozenset({("guard", "apertura")})
    if identifier in {"acta-ref-invalido", "write-report-destino"}:
        return ORIGEN_SIN_MIGRACION
    return frozenset()


def validate_coverage(cases: Iterable[Tuple[str, str, object]],
                      targets: CoverageTargets) -> None:
    entries = list(cases)
    identifiers = {identifier for identifier, _group, _function in entries}
    expected_case_ids = {"escenario:" + identity for identity in targets.cases}
    missing_case_tests = sorted(expected_case_ids - identifiers)
    if missing_case_tests:
        raise ValueError("migrated cases without their test: " + ", ".join(missing_case_tests))

    covered: Set[Origin] = set()
    orphan_tests = []
    invalid_origins: Set[Origin] = set()
    for identifier, group, _function in entries:
        origins = origins_for(identifier, group, targets)
        if not origins:
            orphan_tests.append(identifier)
            continue
        invalid_origins.update(origins - targets.all)
        covered.update(origins)
    if orphan_tests:
        raise ValueError("tests without origin: " + ", ".join(sorted(orphan_tests)))
    if invalid_origins:
        raise ValueError("tests with an unknown origin: " + repr(sorted(invalid_origins)))

    missing_inventory = sorted(targets.inventory - covered)
    if missing_inventory:
        raise ValueError("inventory rows without a test: " + repr(missing_inventory))
