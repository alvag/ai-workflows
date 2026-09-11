"""Parse the restricted orchestration YAML dialect without external dependencies.

FRONTERA DE PRUEBA — tres unidades comparten este pasaje.

``delivery_modulo`` — clase: veredicto; dirección: admite-de-mas. Un retorno autoriza a afirmar
que el helper existe, carga, declara versión 1 y expone los cuatro símbolos requeridos. NO detecta
que sus firmas o su comportamiento respeten el contrato.

``validar_assessment`` — clase: veredicto; dirección: admite-de-mas. Un retorno autoriza a afirmar
que cada fila recibida tiene forma, identidad, enums y evidencia válidos. NO detecta cobertura de
scopes, fold, biyección ni igualdad con manifest o planes; eso pertenece a cada consumidor.

``parsear_perfil_manifest`` — clase: evidencia; dirección: admite-de-mas y rechaza-de-mas. Conserva
raíces del perfil, todas las claves del assessment y, de cada repo, el marcador más
path/complexity/risk. NO clasifica sintaxis YAML general, campos históricos de repo ni semántica
entre carriers; puede admitir texto que un parser YAML rechazaría y rechazar YAML válido fuera de
las formas que sí posee.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

__all__ = [
    "AssessmentError", "DeliveryDependency", "delivery_modulo", "parsear_perfil_manifest",
    "parsear_valor_yaml", "plegar_riesgo", "validar_assessment",
]

ASSESSMENT_FIELDS = {
    "scope", "urgency", "complexity", "risk", "evidence", "provenance", "confidence",
}


class AssessmentError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DeliveryDependency(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


def delivery_modulo():
    """Load the versioned sdd-flow delivery contract for orchestrator guards."""
    path = Path(__file__).resolve().parents[2] / "sdd-flow" / "scripts" / "delivery_profile.py"
    if not path.is_file():
        raise DeliveryDependency("ausente")
    try:
        spec = importlib.util.spec_from_file_location("_delivery_profile_orchestrator", path)
        if spec is None or spec.loader is None:
            raise DeliveryDependency("incompatible")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except DeliveryDependency:
        raise
    except Exception as error:
        raise DeliveryDependency("incompatible") from error
    required = (
        "parse_plan_frontmatter", "read_plan_frontmatter", "resolve_delivery_pair",
        "DeliveryProfileError",
    )
    if (getattr(module, "DELIVERY_PROFILE_CONTRACT_VERSION", None) != 1
            or not all(hasattr(module, symbol) for symbol in required)):
        raise DeliveryDependency("incompatible")
    return module


def _escalar(valor: str) -> str:
    valor = valor.strip()
    if valor.startswith(("\"", "'")):
        cierre = valor.find(valor[0], 1)
        if cierre >= 0:
            valor = valor[: cierre + 1]
    else:
        comentario = re.search(r"[ \t]#", valor)
        if comentario:
            valor = valor[: comentario.start()]
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] in {"\"", "'"} and valor[-1] == valor[0]:
        valor = valor[1:-1]
    return valor.strip()


def parsear_valor_yaml(valor: str) -> str | list[str]:
    """Return a restricted YAML scalar or comma-separated inline list."""
    limpio = valor.strip()
    if not limpio.startswith(("\"", "'")):
        comentario = re.search(r"[ \t]#", limpio)
        if comentario:
            limpio = limpio[: comentario.start()].strip()
    if limpio.startswith("[") and limpio.endswith("]"):
        cuerpo = limpio[1:-1].strip()
        if not cuerpo:
            return []
        return [item for parte in cuerpo.split(",") if (item := _escalar(parte))]
    return _escalar(limpio)


def validar_assessment(rows: Sequence[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """Validate assessment row semantics independently of each consumer's coverage policy."""
    scopes: Dict[str, Dict[str, object]] = {}
    for row in rows:
        values = row["values"]
        duplicates = row["duplicates"]
        if duplicates:
            raise AssessmentError("assessment-clave-duplicada", ", ".join(sorted(duplicates)))
        if set(values) != ASSESSMENT_FIELDS:
            raise AssessmentError(
                "assessment-forma-invalida",
                f"scope={values.get('scope', '')} trae {sorted(values)}",
            )
        scope = values["scope"]
        if not isinstance(scope, str) or not (scope in {"global", "integration"}
                                              or scope.startswith("repo:")):
            raise AssessmentError("assessment-scope-invalido", str(scope))
        if scope in scopes:
            raise AssessmentError("assessment-scope-duplicado", scope)
        if not isinstance(values["urgency"], str) or values["urgency"] not in {
                "high", "normal", "unknown"}:
            raise AssessmentError("assessment-urgency-invalida", str(values["urgency"]))
        if not isinstance(values["complexity"], str) or values["complexity"] not in {
                "trivial", "normal", "complex"}:
            raise AssessmentError("complejidad-desconocida", str(values["complexity"]))
        if not isinstance(values["risk"], str) or values["risk"] not in {
                "low", "high", "unknown"}:
            raise AssessmentError("riesgo-desconocido", str(values["risk"]))
        evidence = values["evidence"]
        if not isinstance(evidence, list):
            raise AssessmentError("assessment-forma-invalida", f"evidence no es lista en {scope}")
        if not evidence:
            raise AssessmentError("assessment-evidence-vacia", scope)
        provenance = values["provenance"]
        if not isinstance(provenance, str) or not re.fullmatch(
                r"user|tracker:[^\s]+|repo:.+:[0-9]+|inference:.+", provenance):
            raise AssessmentError("assessment-provenance-invalida", str(provenance))
        if not isinstance(values["confidence"], str) or values["confidence"] not in {
                "high", "medium", "low"}:
            raise AssessmentError("assessment-confidence-invalida", str(values["confidence"]))
        scopes[scope] = values
    return scopes


def plegar_riesgo(scopes: Dict[str, Dict[str, object]], repo_paths: Sequence[str]) -> str:
    risks = [str(scopes["integration"]["risk"])] + [
        str(scopes[f"repo:{path}"]["risk"]) for path in repo_paths
    ]
    return "high" if "high" in risks else "unknown" if "unknown" in risks else "low"


def parsear_perfil_manifest(texto: str) -> Dict[str, object]:
    """Parse the shared profile boundary of the restricted manifest dialect.

    Owned root and field keys are plain scalars with canonical two/four-space indentation. Mapping
    key order is irrelevant. Every root ``repos`` occurrence is counted before its value form is
    interpreted. All assessment keys remain observable; repo evidence is limited to row markers and
    ``path``, ``complexity`` and ``risk``. Misindented owned evidence is recorded in ``*_invalid``;
    historical repo fields are deliberately left to the downstream parser.
    This function only preserves structural evidence; model and state retain their different
    completeness policies.
    """
    root: Dict[str, List[str]] = {"delivery_profile": [], "risk": []}
    assessment: List[Dict[str, object]] = []
    assessment_sections = 0
    assessment_invalid: List[str] = []
    repos: List[Dict[str, object]] = []
    repos_sections = 0
    repos_invalid: List[str] = []
    section = ""
    current: Optional[Dict[str, object]] = None

    def scalar(value: str) -> str:
        parsed = parsear_valor_yaml(value)
        return parsed if isinstance(parsed, str) else ""

    for line in texto.splitlines():
        if re.match(r"^\s*#", line):
            continue
        if re.match(r"^-(?:\s|$)", line) and section in {"assessment", "repos"}:
            target = assessment_invalid if section == "assessment" else repos_invalid
            target.append(line.strip())
            current = None
            continue
        if line and not line[0].isspace():
            root_scalar = re.match(r"^(delivery_profile|risk)\s*:\s*(.*)$", line)
            if root_scalar:
                root[root_scalar.group(1)].append(scalar(root_scalar.group(2)))
                section = ""
            elif match := re.fullmatch(r"delivery_assessment\s*:\s*(.*)", line):
                assessment_sections += 1
                value = match.group(1).strip()
                section = "assessment" if not value or value.startswith("#") else ""
                if section != "assessment": assessment_invalid.append(value)
            elif match := re.fullmatch(r"repos\s*:\s*(.*)", line):
                repos_sections += 1
                value = match.group(1).strip()
                section = "repos" if not value or value.startswith("#") else ""
                if section != "repos": repos_invalid.append(value)
            else:
                section = ""
            current = None
            continue
        if section == "assessment":
            start = re.match(r"^  -\s*(.*)$", line)
            if start:
                current = {"values": {}, "duplicates": set()}
                assessment.append(current)
                field = re.fullmatch(r"([^:\s][^:]*?)\s*:\s*(.*)", start.group(1))
            else:
                field = re.match(r"^    ([^:\s][^:]*?)\s*:\s*(.*)$", line)
            if current is not None and field:
                values = current["values"]
                if field.group(1) in values: current["duplicates"].add(field.group(1))
                else: values[field.group(1)] = parsear_valor_yaml(field.group(2))
            elif line.strip():
                assessment_invalid.append(line.strip())
            continue
        if section == "repos":
            start = re.match(r"^  -\s*(.*)$", line)
            if start:
                current = {"path": "", "complexity": [], "risk": [],
                           "duplicates": set(), "path_seen": False}
                repos.append(current)
                field = re.fullmatch(r"(path|complexity|risk)\s*:\s*(.*)", start.group(1))
            else:
                field = re.match(r"^    (path|complexity|risk)\s*:\s*(.*)$", line)
            if current is not None and field:
                key, value = field.group(1), field.group(2)
                if key == "path" and current["path_seen"]: current["duplicates"].add("path")
                elif key == "path": current["path_seen"], current["path"] = True, scalar(value)
                else: current[key].append(scalar(value))
            elif ((marker := re.match(r"^([ \t]*)-\s*", line))
                  and marker.group(1) != "  ") or re.match(
                    r"^\s*(path|complexity|risk)\s*:", line):
                repos_invalid.append(line.strip())
    return {"root": root, "assessment": assessment,
            "assessment_sections": assessment_sections,
            "assessment_invalid": assessment_invalid, "repos": repos,
            "repos_sections": repos_sections, "repos_invalid": repos_invalid}
