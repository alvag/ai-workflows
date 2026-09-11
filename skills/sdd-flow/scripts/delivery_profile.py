"""Contrato mecánico compartido del perfil de entrega de SDD."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import FrozenSet, Mapping, Optional, Sequence, Tuple


DELIVERY_PROFILE_CONTRACT_VERSION: int = 1
DELIVERY_PROFILES: FrozenSet[str] = frozenset({"standard", "expedited"})
RISKS: FrozenSet[str] = frozenset({"low", "high", "unknown"})
COMPLEXITIES: FrozenSet[str] = frozenset({"trivial", "normal", "complex"})


@dataclass(frozen=True)
class PlanFrontmatter:
    raw_lines: Tuple[str, ...]
    body_lines: Tuple[str, ...]
    fields: Mapping[str, Tuple[str, ...]]


@dataclass(frozen=True)
class DeliveryPair:
    profile: str
    risk: Optional[str]
    legacy: bool


class DeliveryProfileError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> None:
    raise DeliveryProfileError(code, message)


def _scalar(value: str) -> str:
    value = value.strip()
    if value.startswith(("\"", "'")):
        closing = value.find(value[0], 1)
        if closing >= 0:
            value = value[: closing + 1]
    else:
        comment = next((index for index, char in enumerate(value)
                        if char == "#" and (index == 0 or value[index - 1].isspace())), len(value))
        value = value[:comment].rstrip()
    if len(value) >= 2 and value[0] in {"\"", "'"} and value[-1] == value[0]:
        value = value[1:-1]
    return value.strip()


def parse_plan_frontmatter(text: str) -> PlanFrontmatter:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if not lines or lines[0].strip() != "---":
        _fail("header-ausente", "el plan no abre con el delimitador ---")

    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), -1)
    if end < 0:
        _fail("header-mal-cerrado", "el frontmatter no cierra con el delimitador ---")

    raw_lines = tuple(lines[1:end])
    collected: dict[str, list[str]] = {}
    for line in raw_lines:
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.rstrip()
        if not key or not key.replace("_", "a").replace("-", "a").isalnum():
            continue
        collected.setdefault(key, []).append(_scalar(value))
    fields = MappingProxyType({key: tuple(values) for key, values in collected.items()})
    return PlanFrontmatter(raw_lines=raw_lines, body_lines=tuple(lines[end + 1:]), fields=fields)


def read_plan_frontmatter(path: Path) -> PlanFrontmatter:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        _fail("archivo-ilegible", f"el plan no se pudo leer como UTF-8: {error}")
    return parse_plan_frontmatter(text)


def resolve_delivery_pair(fields: Mapping[str, Sequence[str]], complexity: Optional[str]) -> DeliveryPair:
    for key in ("complexity", "delivery_profile", "risk"):
        values = fields.get(key, ())
        if len(values) > 1:
            _fail("clave-duplicada", f"la clave {key} está duplicada")

    profile_values = fields.get("delivery_profile", ())
    risk_values = fields.get("risk", ())
    has_profile = len(profile_values) == 1
    has_risk = len(risk_values) == 1

    if not has_profile and not has_risk and not complexity:
        return DeliveryPair(profile="standard", risk=None, legacy=True)
    if complexity is not None and complexity not in COMPLEXITIES:
        _fail("complejidad-desconocida", f"la complejidad {complexity!r} no pertenece al contrato")
    if not has_profile and not has_risk:
        return DeliveryPair(profile="standard", risk=None, legacy=True)
    if has_profile != has_risk:
        _fail("par-parcial", "delivery_profile y risk deben declararse juntos")

    profile = profile_values[0]
    risk = risk_values[0]
    if profile not in DELIVERY_PROFILES:
        _fail("perfil-desconocido", f"delivery_profile {profile!r} no pertenece al contrato")
    if risk not in RISKS:
        _fail("riesgo-desconocido", f"risk {risk!r} no pertenece al contrato")
    if profile == "expedited" and (risk != "low" or (complexity is not None
                                                       and complexity not in {"trivial", "normal"})):
        _fail(
            "expedited-inelegible",
            "expedited exige risk low y, cuando aplica, complexity trivial|normal",
        )
    return DeliveryPair(profile=profile, risk=risk, legacy=False)
