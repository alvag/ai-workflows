"""Contrato dirigido del perfil de entrega compartido por las dos skills SDD."""

from __future__ import annotations

import ast
import importlib.util
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "skills" / "sdd-flow" / "scripts" / "delivery_profile.py"
POLICY = ROOT / "skills" / "sdd-flow" / "delivery-profile.md"
FLOW_SKILL = ROOT / "skills" / "sdd-flow" / "SKILL.md"
FLOW_REFERENCE = ROOT / "skills" / "sdd-flow" / "reference.md"
ORCHESTRATOR_SKILL = ROOT / "skills" / "sdd-orchestrator" / "SKILL.md"
ORCHESTRATOR_REFERENCE = ROOT / "skills" / "sdd-orchestrator" / "reference.md"
TESTS_README = ROOT / "tests" / "README.md"
Case = Tuple[str, str, Callable[[Optional[object]], None]]
GROUP = "delivery-profile"

# Closed registry by design: it proves the five known consumers, but cannot discover a new
# semantic consumer that was not added here. T3a/T4a/T5 wire these paths; T6 makes the checks
# structural and mutation-sensitive.
CONSUMERS = {
    "sdd-flow:promotion": ROOT / "skills" / "sdd-flow" / "scripts" / "promocion-tasks-ready.py",
    "sdd-flow:fingerprints": ROOT / "skills" / "sdd-flow" / "scripts" / "huellas-secuencia.py",
    "orchestrator:model": ROOT / "skills" / "sdd-orchestrator" / "scripts" / "orchestration-model.py",
    "orchestrator:state": ROOT / "skills" / "sdd-orchestrator" / "scripts" / "orchestration-state.py",
    "orchestrator:integration": ROOT / "skills" / "sdd-orchestrator" / "scripts" / "integracion-ownership.py",
}

EXPECTED_HELPER_CALLS = {
    "sdd-flow:promotion": {"parse_plan_frontmatter", "resolve_delivery_pair"},
    "sdd-flow:fingerprints": {"parse_plan_frontmatter"},
    "orchestrator:model": {"read_plan_frontmatter", "resolve_delivery_pair"},
    "orchestrator:state": {"read_plan_frontmatter", "resolve_delivery_pair"},
    "orchestrator:integration": {"read_plan_frontmatter", "resolve_delivery_pair"},
}


def _consumer_wiring_errors(name: str, source: str) -> list[str]:
    tree = ast.parse(source)
    errors = []
    parents = {id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    helper_calls = [
        node for node in calls
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "parse_plan_frontmatter", "read_plan_frontmatter", "resolve_delivery_pair",
        }
    ]
    present = {node.func.attr for node in helper_calls}
    missing = EXPECTED_HELPER_CALLS[name] - present
    if missing:
        errors.append("missing helper calls: " + ", ".join(sorted(missing)))

    if name == "sdd-flow:promotion":
        imported = any(
            isinstance(node, ast.Import)
            and any(alias.name == "delivery_profile" and alias.asname == "_delivery_profile"
                    for alias in node.names)
            for node in ast.walk(tree)
        )
        if not imported:
            errors.append("missing plain delivery_profile import")
    elif name == "sdd-flow:fingerprints":
        has_path_loader = any(
            isinstance(node.func, ast.Attribute) and node.func.attr == "spec_from_file_location"
            for node in calls
        ) and any(
            isinstance(node, ast.Constant) and node.value == "delivery_profile.py"
            for node in ast.walk(tree)
        )
        if not has_path_loader:
            errors.append("missing path loader")
        if not any(isinstance(node.func, ast.Name) and node.func.id == "_delivery_modulo"
                   for node in calls):
            errors.append("path loader is never called")
        module_names = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "module_from_spec"
            for target in node.targets if isinstance(target, ast.Name)
        }
        returned_names = {
            node.value.id for node in ast.walk(tree)
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)
        }
        if not module_names & returned_names:
            errors.append("path loader returns a constant or unrelated value")
    else:
        shared_import = any(
            isinstance(node, ast.ImportFrom) and node.module == "_yaml"
            and any(alias.name == "delivery_modulo" for alias in node.names)
            for node in ast.walk(tree)
        )
        if not shared_import:
            errors.append("missing shared path loader import")
        if not any(isinstance(node.func, ast.Name) and node.func.id == "delivery_modulo"
                   for node in calls):
            errors.append("shared path loader is never called")

    for call in helper_calls:
        call_name = call.func.attr
        if (name == "sdd-flow:promotion" and call_name == "resolve_delivery_pair"):
            continue
        if isinstance(parents.get(id(call)), ast.Expr):
            errors.append(f"ignored helper result: {call_name}")
    if name == "sdd-flow:fingerprints" and not any(
            isinstance(parents.get(id(call)), ast.Attribute)
            and parents[id(call)].attr == "raw_lines" for call in helper_calls):
        errors.append("parsed frontmatter raw_lines are not consumed")
    return errors


def _assert_consumer_wiring(name: str, source: str) -> None:
    errors = _consumer_wiring_errors(name, source)
    assert not errors, f"{name}: {'; '.join(errors)}"


def _helper():
    spec = importlib.util.spec_from_file_location("delivery_profile_under_test", HELPER)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _expect_code(module, code: str, call: Callable[[], object]) -> None:
    try:
        call()
    except module.DeliveryProfileError as error:
        assert error.code == code, f"expected {code}, got {error.code}: {error}"
        return
    raise AssertionError(f"expected DeliveryProfileError({code})")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.index(marker) + len(marker)
    match = re.search(r"^## ", text[start:], re.MULTILINE)
    return text[start:] if match is None else text[start:start + match.start()]


def _table(text: str, heading: str, expected_headers: Tuple[str, ...]) -> list[dict[str, str]]:
    section = _section(text, heading)
    lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    assert len(lines) >= 3, f"{heading} must contain a non-empty Markdown table"

    def cells(line: str) -> list[str]:
        assert line.endswith("|"), f"unterminated table row in {heading}"
        return [cell.strip() for cell in line[1:-1].split("|")]

    headers = cells(lines[0])
    assert tuple(headers) == expected_headers, (heading, headers)
    separator = cells(lines[1])
    assert len(separator) == len(headers)
    assert all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator)
    rows = []
    for line in lines[2:]:
        values = cells(line)
        assert len(values) == len(headers), (heading, values)
        rows.append(dict(zip(headers, values)))
    return rows


def _marked_block(text: str, name: str) -> str:
    start = f"<!-- {name}:start -->"
    end = f"<!-- {name}:end -->"
    assert text.count(start) == 1 and text.count(end) == 1, name
    return text.split(start, 1)[1].split(end, 1)[0]


def _description_block(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith("description:")]
    assert len(starts) == 1, "frontmatter must contain one top-level description"
    start = starts[0]
    end = start + 1
    while end < len(lines) and lines[end].startswith((" ", "\t")):
        end += 1
    return "\n".join(lines[start:end]).rstrip("\n") + "\n"


def test_profile_contract(_ctx: Optional[object] = None) -> None:
    """The helper parses strict frontmatter and rejects malformed profile carriers."""
    module = _helper()
    assert module.DELIVERY_PROFILE_CONTRACT_VERSION == 1
    assert module.DELIVERY_PROFILES == frozenset({"standard", "expedited"})
    assert module.RISKS == frozenset({"low", "high", "unknown"})
    assert module.COMPLEXITIES == frozenset({"trivial", "normal", "complex"})

    for newline in ("\n", "\r\n", "\r"):
        parsed = module.parse_plan_frontmatter(
            newline.join(("---", "complexity: normal", "delivery_profile: expedited", "risk: low", "---", "body"))
        )
        assert parsed.raw_lines == (
            "complexity: normal", "delivery_profile: expedited", "risk: low")
        assert parsed.body_lines == ("body",)
        assert parsed.fields["risk"] == ("low",)
        assert module.resolve_delivery_pair(parsed.fields, "normal") == module.DeliveryPair(
            profile="expedited", risk="low", legacy=False)
        try:
            parsed.fields["risk"] = ("high",)
        except TypeError:
            pass
        else:
            raise AssertionError("frontmatter fields must be immutable")

    template = _section(_read(FLOW_SKILL), "Paso `plan` → GATE"); fenced = "\n".join(line[3:] if line.startswith("   ") else line for line in template.split("```yaml\n", 1)[1].split("\n```", 1)[0].splitlines())
    documented = module.parse_plan_frontmatter(fenced); assert module.resolve_delivery_pair(documented.fields, documented.fields["complexity"][0]) == module.DeliveryPair(profile="standard", risk="low", legacy=False)

    _expect_code(module, "header-ausente", lambda: module.parse_plan_frontmatter("body\n"))
    spaced_delimiters = module.parse_plan_frontmatter("--- \na: b\n--- \nbody\n")
    assert spaced_delimiters.fields["a"] == ("b",) and spaced_delimiters.body_lines == ("body", "")
    _expect_code(module, "header-mal-cerrado", lambda: module.parse_plan_frontmatter("---\na: b\n--\n"))

    duplicate = module.parse_plan_frontmatter(
        "---\ncomplexity: normal\ndelivery_profile: standard\ndelivery_profile : expedited\nrisk: low\n---\n")
    _expect_code(module, "clave-duplicada", lambda: module.resolve_delivery_pair(duplicate.fields, "normal"))
    _expect_code(module, "par-parcial", lambda: module.resolve_delivery_pair({"delivery_profile": ("standard",)}, "normal"))
    _expect_code(module, "perfil-desconocido", lambda: module.resolve_delivery_pair(
        {"delivery_profile": ("fast",), "risk": ("low",)}, "normal"))
    _expect_code(module, "riesgo-desconocido", lambda: module.resolve_delivery_pair(
        {"delivery_profile": ("standard",), "risk": ("tiny",)}, "normal"))
    _expect_code(module, "complejidad-desconocida", lambda: module.resolve_delivery_pair({}, "huge"))
    _expect_code(module, "complejidad-desconocida", lambda: module.resolve_delivery_pair(
        {"delivery_profile": ("standard",), "risk": ("low",)}, ""))
    spaced = module.parse_plan_frontmatter(
        "---\ncomplexity: normal\ndelivery_profile : expedited\nrisk : low\n---\n")
    assert module.resolve_delivery_pair(spaced.fields, "normal").profile == "expedited"
    quoted = module.parse_plan_frontmatter(
        "---\ncomplexity: normal\ndelivery_profile: \"expedited\"\nrisk: 'low'\n---\n")
    assert module.resolve_delivery_pair(quoted.fields, "normal").profile == "expedited"
    assert module.resolve_delivery_pair(
        {"delivery_profile": ("expedited",), "risk": ("low",)}, None).profile == "expedited"
    legacy = module.resolve_delivery_pair({}, "")
    assert legacy == module.DeliveryPair(profile="standard", risk=None, legacy=True)

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "plan.md"
        path.write_bytes(b"---\nrisk: \xff\n---\n")
        _expect_code(module, "archivo-ilegible", lambda: module.read_plan_frontmatter(path))

    print("PROFILE_CONTRACT_OK")


def test_profile_eligibility(_ctx: Optional[object] = None) -> None:
    """Expedited is eligible only for trivial or normal changes with low risk."""
    module = _helper()
    for complexity in ("trivial", "normal"):
        fields = {"delivery_profile": ("expedited",), "risk": ("low",)}
        assert module.resolve_delivery_pair(fields, complexity).profile == "expedited"
    for complexity, risk in (("complex", "low"), ("normal", "high"), ("normal", "unknown")):
        fields = {"delivery_profile": ("expedited",), "risk": (risk,)}
        _expect_code(module, "expedited-inelegible", lambda f=fields, c=complexity: module.resolve_delivery_pair(f, c))
    standard = {"delivery_profile": ("standard",), "risk": ("unknown",)}
    assert module.resolve_delivery_pair(standard, "complex").legacy is False
    print("PROFILE_ELIGIBILITY_OK")


def test_delivery_assessment_sdd_flow(_ctx: Optional[object] = None) -> None:
    """The repo flow evaluates all dimensions and persists the post-analysis risk."""
    policy = _read(POLICY)
    assessment = _table(
        policy,
        "2. Evaluación universal de entrega",
        ("Campo", "Valores admitidos", "Evidencia obligatoria", "Autoridad"),
    )
    assert {row["Campo"] for row in assessment} == {
        "urgency", "complexity", "risk", "evidence", "provenance", "confidence"
    }
    flow = _marked_block(_read(FLOW_SKILL), "delivery-profile-assessment")
    for token in ("gather-context", "analyze", "post-análisis", "elección humana"):
        assert token in flow


def test_delivery_assessment_orchestrator(_ctx: Optional[object] = None) -> None:
    """The orchestrator evaluates integration and every repository before fan-out."""
    carrier_tokens = (
        "`delivery_profile` y `risk` globales entre la raíz del manifest y todos los planes",
        "`complexity` y `risk` locales entre cada fila `repo:<path>` del assessment y su repo del manifest",
        "`complexity` local también entre esa fila y su plan",
        "El plan conserva el `risk` global; no copia el riesgo local",
    )

    def carriers_are_explicit(text: str) -> bool:
        return all(token in text for token in carrier_tokens) and (
            "igualdad de `delivery_profile`, `risk` y `complexity` entre evaluación" not in text)

    orchestrator = _read(ORCHESTRATOR_SKILL)
    block = _marked_block(orchestrator, "delivery-profile-assessment")
    for token in ("global", "integration", "repo:<path>", "elección humana", "antes de co-explore"):
        assert token in block
    resume = " ".join(_marked_block(
        orchestrator, "delivery-profile-resume-orchestrator").split())
    for token in ("manifest puede existir desde `1.2`", "sin `master-spec.md`", "retomar `1.2`",
                  "retoma de `co-explore`", "con `master-spec.md` y sin ningún plan",
                  "retomar `1.3` desde su punto 3", "perfil materializado decide",
                  "solo con al menos un plan"):
        assert token in resume
    assert "lo escribe el paso 2 de **`1.4`**" not in resume
    policy = " ".join(_section(_read(POLICY), "8. Orquestación all-or-nothing").split())
    assert carriers_are_explicit(policy)
    assert not carriers_are_explicit(policy.replace(carrier_tokens[-1], "El plan copia el riesgo local", 1))


def test_delivery_assessment(_ctx: Optional[object] = None) -> None:
    """Both skills expose the universal, auditable assessment contract."""
    test_delivery_assessment_sdd_flow(_ctx)
    test_delivery_assessment_orchestrator(_ctx)
    print("DELIVERY_ASSESSMENT_OK")


def test_preset_overrides(_ctx: Optional[object] = None) -> None:
    """The expedited preset resolves auto values while concrete overrides win."""
    def assert_contract(policy: str, flow: str, orchestrator: str) -> None:
        rows = _table(
            policy,
            "4. Preset, overrides, degradación y revocación",
            ("Capa", "Auto expedito", "Override concreto", "Resultado insuficiente"),
        )
        by_layer = {row["Capa"]: row for row in rows}
        assert by_layer["co-explore explore"]["Auto expedito"] == '"on"'
        assert by_layer["counter-plan"]["Auto expedito"] == '"off"'
        assert by_layer["cross-review"]["Auto expedito"] == '"on"'
        assert by_layer["implementación"]["Auto expedito"] == "inline"
        assert "ask" in by_layer["implementación"]["Override concreto"]
        for layer in ("co-explore explore", "cross-review"):
            result = by_layer[layer]["Resultado insuficiente"]
            for token in ('"off"', "desactiva la capa", "revoca expedited a standard"):
                assert token in result, (layer, token)
        normalized_policy = " ".join(policy.split())
        for token in ("supresión de duplicados", "evidencia upstream", "conserva el par global"):
            assert token in normalized_policy
        counter_result = by_layer["counter-plan"]["Resultado insuficiente"]
        for token in ('"on"', "revoca expedited a standard", "spec aprobada"):
            assert token in counter_result

        router = _marked_block(flow, "delivery-profile-preset")
        for token in ("same_family", "single_voice", "FALLO_DE_MAPA", "ronda completada",
                      '`co_explore.mode: "off"`', '`cross_review.mode: "off"`'):
            assert token in router
        review_callers = (
            _section(flow, "Revisión cross-model (segunda opinión, opcional)"),
            _section(orchestrator, "Revisión cross-model (segunda opinión, opcional)"),
        )
        for caller in review_callers:
            normalized = " ".join(caller.split())
            assert ('Un override raíz `cross_review.mode: "off"` desactiva la capa. '
                    'Con perfil `expedited`, revocarlo a `standard`' in normalized)
        for caller in (
            _section(flow, "Co-exploración cross-model (opcional)"),
            _section(orchestrator, "Co-exploración cross-model (opcional)"),
        ):
            normalized = " ".join(caller.split())
            assert ('Un override raíz `co_explore.mode: "off"` desactiva la capa. '
                    'Con perfil `expedited`, revocarlo a `standard`' in normalized)
            for token in ('counter-plan: "on"', "revocar `expedited` a `standard`",
                          "spec aprobada", "ejecutar `counter-plan`"):
                assert token in normalized

    policy = _read(POLICY)
    flow = _read(FLOW_SKILL)
    orchestrator = _read(ORCHESTRATOR_SKILL)
    assert_contract(policy, flow, orchestrator)
    mutants = (
        (policy.replace("revoca expedited a standard", "conserva expedited", 1), flow,
         orchestrator),
        (policy, flow.replace("revocar `expedited` a `standard`", "conservar `expedited`", 1),
         orchestrator),
        (policy, flow, orchestrator.replace(
            "revocar `expedited` a `standard`", "conservar `expedited`", 1)),
        (policy.replace(
            '"off" desactiva la capa y revoca expedited a standard',
            '"off" desactiva la capa y conserva expedited', 1), flow, orchestrator),
        (policy, flow.replace(
            '`expedited`, revocarlo a `standard` antes del siguiente gate',
            '`expedited`, conservarlo antes del siguiente gate', 1), orchestrator),
        (policy, flow.replace(
            '`expedited`, revocarlo a `standard` antes de escribir la spec',
            '`expedited`, conservarlo antes de escribir la spec', 1), orchestrator),
        (policy, flow, orchestrator.replace(
            '`expedited`, revocarlo a `standard` y restaurar los gates separados',
            '`expedited`, conservarlo y mantener los gates combinados', 1)),
        (policy, flow, orchestrator.replace(
            '`expedited`, revocarlo a `standard` antes de escribir `master-spec.md`',
            '`expedited`, conservarlo antes de escribir `master-spec.md`', 1)),
    )
    for mutant in mutants:
        try:
            assert_contract(*mutant)
        except AssertionError:
            continue
        raise AssertionError("counter-plan authority mutant survived")
    print("PRESET_OVERRIDES_OK")


def test_cross_review_lifecycle(_ctx: Optional[object] = None) -> None:
    """Expedited review keeps separate typed runs and the configured finite batch."""
    rows = _table(
        _read(POLICY),
        "6. Estabilidad de cross-review y corrección upstream",
        ("Resultado", "Rondas completadas", "Aplicaciones pendientes", "Acción llamadora"),
    )
    assert {row["Resultado"] for row in rows} == {"APPROVED", "REVISE", "UNAVAILABLE"}
    section = _section(_read(POLICY), "6. Estabilidad de cross-review y corrección upstream")
    for token in ("corrida de spec", "corrida de plan", "tasks como contexto", "tanda finita", "seguir hasta APPROVED"):
        assert token in section
    flow = _read(FLOW_SKILL)
    _marked_block(flow, "delivery-profile-review")
    flow_review = _section(flow, "Revisión cross-model (segunda opinión, opcional)")
    orchestrator_review = _section(
        _read(ORCHESTRATOR_SKILL), "Revisión cross-model (segunda opinión, opcional)")
    for caller, block in (("sdd-flow", flow_review), ("sdd-orchestrator", orchestrator_review)):
        assert "perfil efectivo es `expedited`" in block, caller
        assert "revocarlo a `standard`" in block, caller
    print("CROSS_REVIEW_LIFECYCLE_OK")


def test_jira_off_sequence(_ctx: Optional[object] = None) -> None:
    """Normal expedited without Jira has one atomic artifact gate."""
    rows = _table(
        _read(POLICY),
        "5. Secuencias por complejidad y Jira",
        ("Complejidad", "Perfil", "Jira", "Gates de artefactos", "Secuencia efectiva"),
    )
    keyed = {(r["Complejidad"], r["Perfil"], r["Jira"]): r for r in rows}
    assert keyed[("normal", "standard", '"off"')]["Gates de artefactos"] == "2"
    assert keyed[("normal", "expedited", '"off"')]["Gates de artefactos"] == "1"
    assert "atómico(spec+plan+tasks)" in keyed[("normal", "expedited", '"off"')]["Secuencia efectiva"]
    router = _marked_block(_read(FLOW_SKILL), "delivery-profile-router")
    normal_off = _marked_block(router, "normal-expedited-jira-off")
    assert normal_off.count("→ GATE") == 1
    assert all(token in normal_off for token in ("spec", "plan", "tasks"))
    create_branch = " ".join(_section(_read(FLOW_SKILL), "Paso `create-branch`").split())
    for token in ('normal + expedited + jira_approval: "off"', "spec estable",
                  "antes del gate atómico"):
        assert token in create_branch
    classifier = _read(FLOW_SKILL)
    classifier_rows = _table(
        classifier,
        "Clasificador de complejidad (escalado de gates)",
        ("Nivel", "Señales típicas", "`standard`", "`expedited` + Jira off",
         "`expedited` + Jira on", "Clarify"),
    )
    normal = next(row for row in classifier_rows if row["Nivel"] == "**Normal**")
    assert "**2 gates**" in normal["`standard`"]
    assert "**1 gate**" in normal["`expedited` + Jira off"]
    assert "**2 gates locales**" in normal["`expedited` + Jira on"]
    assert "espera externa" in normal["`expedited` + Jira on"]
    classifier_section = " ".join(
        re.sub(r"^\s*>\s?", "", line).strip()
        for line in _section(
            classifier, "Clasificador de complejidad (escalado de gates)").splitlines()
    )
    assert "contador base `standard`" in classifier_section
    assert 'normal + `expedited` + `jira_approval: "off"` lo reduce de 2 a 1' in classifier_section
    print("JIRA_OFF_SEQUENCE_OK")


def test_jira_on_sequence(_ctx: Optional[object] = None) -> None:
    """Jira approval remains external and precedes the combined plan/tasks gate."""
    rows = _table(
        _read(POLICY),
        "5. Secuencias por complejidad y Jira",
        ("Complejidad", "Perfil", "Jira", "Gates de artefactos", "Secuencia efectiva"),
    )
    row = next(r for r in rows if (r["Complejidad"], r["Perfil"], r["Jira"]) ==
               ("normal", "expedited", '"on"'))
    assert row["Gates de artefactos"] == "2"
    assert all(token in row["Secuencia efectiva"] for token in
               ("spec-local", "publicar", "espera-externa", "atómico(plan+tasks)"))
    router = _marked_block(_read(FLOW_SKILL), "normal-expedited-jira-on")
    assert router.index("aprobación externa de Jira") < router.index("plan")
    assert router.count("→ GATE") == 2
    print("JIRA_ON_SEQUENCE_OK")


def test_upstream_revocation(_ctx: Optional[object] = None) -> None:
    """Review outcome, rounds, and pending applications govern upstream stability."""
    rows = _table(
        _read(POLICY),
        "6. Estabilidad de cross-review y corrección upstream",
        ("Resultado", "Rondas completadas", "Aplicaciones pendientes", "Acción llamadora"),
    )
    actions = {(r["Resultado"], r["Rondas completadas"], r["Aplicaciones pendientes"]): r["Acción llamadora"]
               for r in rows}
    assert "habilitar dependientes" in actions[("APPROVED", ">=1", "0")]
    assert "revocar expedited" in actions[("REVISE", ">=1", "cualquiera")]
    assert "revocar expedited" in actions[("UNAVAILABLE", "0", "cualquiera")]
    assert "habilitar dependientes" in actions[("UNAVAILABLE", ">=1", "0")]
    assert "revocar expedited" in actions[("UNAVAILABLE", ">=1", ">0")]
    flow = _read(FLOW_SKILL)
    _marked_block(flow, "delivery-profile-review")
    co_explore = _section(flow, "Co-exploración cross-model (opcional)")
    assert "perfil efectivo es `expedited`" in co_explore
    assert "revocarlo a `standard`" in co_explore
    orchestrator = _read(ORCHESTRATOR_SKILL)

    def assert_orchestrator_caller(text: str) -> None:
        caller = " ".join(_marked_block(text, "delivery-profile-router").split())
        assert "finding material abierto" in caller
        for token in ("REVISE", "UNAVAILABLE", "aplicaciones pendientes", "APPROVED",
                      "no revocan"):
            assert token in caller
        assert "Un finding material o una corrección upstream revoca" not in caller

    assert_orchestrator_caller(orchestrator)
    mutant = orchestrator.replace("finding material abierto", "finding material", 1)
    try:
        assert_orchestrator_caller(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("open-finding revocation mutant survived")
    print("UPSTREAM_REVOCATION_OK")


def test_upstream_regeneration(_ctx: Optional[object] = None) -> None:
    """Upstream changes invalidate and re-review every dependent artifact."""
    section = _section(_read(POLICY), "6. Estabilidad de cross-review y corrección upstream")
    ordered = ("registrar arbitraje", "cerrar la corrida actual", "invalidar dependientes",
               "regenerar dependientes", "repetir evidencia afectada", "abrir una nueva corrida de revisión")
    positions = [section.index(token) for token in ordered]
    assert positions == sorted(positions)
    _marked_block(_read(FLOW_REFERENCE), "delivery-profile-regeneration")
    print("UPSTREAM_REGENERATION_OK")


def test_branch_preservation(_ctx: Optional[object] = None) -> None:
    """Returning to standard consumes the existing branch and preserves its base."""
    rows = _table(
        _read(POLICY),
        "7. Persistencia, resume y preservación de rama",
        ("Estado del carrier", "Autoridad", "Acción al retomar", "Tratamiento de rama"),
    )
    assert any("revocado" in row["Estado del carrier"] and
               "conservar rama y base" in row["Tratamiento de rama"] for row in rows)
    assert any("spec_approved_at: null" in row["Estado del carrier"] and
               "no volver a preguntar" in row["Acción al retomar"] for row in rows)
    assert any("heredado pre-plan" in row["Estado del carrier"] and
               "preguntar una vez" in row["Acción al retomar"] for row in rows)
    _marked_block(_read(FLOW_REFERENCE), "delivery-profile-resume")
    print("BRANCH_PRESERVATION_OK")


def test_persistence_resume(_ctx: Optional[object] = None) -> None:
    """Plan and handoff preserve authority, approval evidence, and legacy behavior."""
    flow = _read(FLOW_SKILL)
    reference = _read(FLOW_REFERENCE)
    resume = _marked_block(reference, "delivery-profile-resume")
    assert "rama existente no acredita" in resume
    assert "preguntar una vez" in resume
    assert "spec_approved_at: null" in resume
    assert "no volver a preguntar" in resume
    assert "header son autoridad" in resume
    assert "planned + expedited + normal" in resume
    assert "delivery_profile: standard" in flow and "risk: low" in flow
    assert flow.count("spec_approved_at: null") >= 1
    assert "Se escribe/actualiza en tres situaciones" in flow
    assert "Paso `create-branch`" in flow
    assert "si existe, la spec ya fue aprobada" not in flow
    assert "delivery_profile: standard" in reference and "risk: low" in reference
    readme = _read(ROOT / "skills" / "sdd-flow" / "README.md")
    handoff_line = next(line for line in readme.splitlines() if "├─ handoff.md" in line)
    assert "siempre en `create-branch`" in handoff_line
    skill_handoff_line = next(line for line in flow.splitlines() if "├─ handoff.md" in line)
    assert "siempre en `create-branch`" in skill_handoff_line
    print("PERSISTENCE_RESUME_OK")


def test_quality_permissions(_ctx: Optional[object] = None) -> None:
    """Every profile retains the quality floor and explicit external authorization."""
    section = " ".join(_section(_read(POLICY), "9. Piso de calidad y autorización externa").split())
    for token in ("búsqueda completa de antecedentes", "causa raíz antes de editar", "criterios de aceptación",
                  "pruebas enfocadas", "evidencia fresca", "revisión final del diff", "reversión",
                  "nunca silenciar", "rama", "commit", "push", "pull request", "merge",
                  "escritura externa", "risk: high", "risk: unknown"):
        assert token in section
    assert "permiso" in section and "no concede" in section
    flow = _read(FLOW_SKILL); _marked_block(flow, "delivery-profile-quality"); gate = next(line for line in flow.splitlines() if line.startswith("5. **Gate de revisión manual")); assert "Si `final_diff_review.mode` está `on`, o está `auto` y el flujo se ejecuta `inline` y es `complex` o tiene `risk: high | unknown`, ofrecer" in gate
    print("QUALITY_PERMISSIONS_OK")


def test_scenario_matrix(_ctx: Optional[object] = None) -> None:
    """The functional matrix covers positive, negative, legacy, and multi-repo cases."""
    rows = _table(
        _read(POLICY),
        "10. Matriz de escenarios y dry runs",
        ("Escenario", "Entrada", "Perfil esperado", "Observación obligatoria"),
    )
    names = {row["Escenario"] for row in rows}
    assert {"normal-low-jira-off", "normal-low-jira-on", "trivial-low", "complex-low",
            "normal-unknown", "legacy-dual-absence", "multi-repo-low",
            "multi-repo-one-high", "partial-carrier", "review-unavailable-zero-rounds"} <= names
    policy = _read(POLICY).lower()
    assert all(term not in policy for term in ("tiempo ahorrado", "duración transcurrida", "telemetría", "piloto"))
    _marked_block(_read(ORCHESTRATOR_SKILL), "delivery-profile-router")
    examples = _section(_read(ORCHESTRATOR_REFERENCE), "Ejemplos de `manifest.yml`")
    assert "E1-E3" in examples
    assert "legacy standard" in examples
    assert "ausencia dual" in examples
    assert "esquema vigente" in examples
    print("SCENARIO_MATRIX_OK")


def test_trivial_profile(_ctx: Optional[object] = None) -> None:
    """Trivial keeps its combined plan and one gate under either explicit profile."""
    rows = _table(
        _read(POLICY),
        "5. Secuencias por complejidad y Jira",
        ("Complejidad", "Perfil", "Jira", "Gates de artefactos", "Secuencia efectiva"),
    )
    trivial = [row for row in rows if row["Complejidad"] == "trivial"]
    assert {(row["Perfil"], row["Jira"], row["Gates de artefactos"]) for row in trivial} == {
        ("standard", '"off"', "1"), ("expedited", '"off"', "1")
    }
    sequences = {row["Perfil"]: row["Secuencia efectiva"] for row in trivial}
    assert sequences["standard"] == "plan-combinado(spec+plan+tasks) > gate-atómico"
    assert sequences["expedited"] == (
        "explore > plan-combinado(spec+plan+tasks) > cross-review > gate-atómico")
    section = _section(_read(POLICY), "5. Secuencias por complejidad y Jira")
    assert "recomendar standard porque no se reduce ningún gate de artefactos" in section
    assert "Jira requiere reclasificación explícita a normal" in section
    _marked_block(_read(FLOW_SKILL), "trivial-delivery-profile")
    template = _section(_read(FLOW_REFERENCE), "Plantilla de plan combinado (trivial)")
    fenced = template.split("```markdown\n", 1)[1].split("\n```", 1)[0]
    module = _helper()
    parsed = module.parse_plan_frontmatter(fenced)
    assert module.resolve_delivery_pair(parsed.fields, "trivial") == module.DeliveryPair(
        profile="standard", risk="low", legacy=False)
    print("TRIVIAL_PROFILE_OK")


def test_documented_view_counts(_ctx: Optional[object] = None) -> None:
    """Secondary prose reports the same current config-view totals as the canonical examples."""
    flow = _read(FLOW_SKILL); flow_reference = _read(FLOW_REFERENCE)
    orchestrator_reference = _read(ORCHESTRATOR_REFERENCE)
    tests_readme = _read(TESTS_README)
    assert "config admite **37 claves**" in flow
    assert all(token in flow_reference for token in ("dueño de las 23 claves", "Las 14 restantes", "37 juntas"))
    assert "Solo esas 13 claves" in orchestrator_reference
    assert "`id`, `created_at`, `master_spec`, `delivery_profile`, `risk`, `delivery_assessment`, `repos`, `orchestration_tasks`" in " ".join(orchestrator_reference.split())
    assert "562 casos ok" in tests_readme and "512 casos node ok" in tests_readme
    print("DOCUMENTED_VIEW_COUNTS_OK")


def test_review_checkpoint(_ctx: Optional[object] = None) -> None:
    """An open review is adjudicated or closed before a replacement run exists."""
    section = " ".join(_section(
        _read(POLICY), "6. Estabilidad de cross-review y corrección upstream").split())
    for token in ("mismo run_id", "conceder una tanda finita adicional", "rechazar aplicaciones",
                  "cambiar un criterio de aceptación", "cerrar la corrida actual"):
        assert token in section
    assert section.index("cerrar la corrida actual") < section.index("abrir una nueva corrida de revisión")
    _marked_block(_read(FLOW_REFERENCE), "delivery-profile-review-checkpoint")
    print("REVIEW_CHECKPOINT_OK")


def test_descriptions_unchanged(_ctx: Optional[object] = None) -> None:
    """Frontmatter descriptions remain byte-stable while body routers carry the profile."""
    expected = {
        FLOW_SKILL: "cd0088b8383e8b142e88f15d65529193bf8e799c269017553c8975ae58f0ff99",
        ORCHESTRATOR_SKILL:
            "e2eb2e126c07128afe87efc0cfaf8702ced2cf1594f8bd9b7793060e67548082",
    }
    for path, digest in expected.items():
        text = _read(path)
        description = _description_block(text)
        assert hashlib.sha256(description.encode("utf-8")).hexdigest() == digest
        assert "delivery_profile" not in description and "expedited" not in description
        router = _marked_block(text, "delivery-profile-router")
        assert "expedited" in router and "gate" in router.lower()
    print("DESCRIPTIONS_UNCHANGED_OK")


def test_sdd_flow_consumer_wiring(_ctx: Optional[object] = None) -> None:
    """Both local consumers must load, call, and consume the shared helper."""
    assert set(CONSUMERS) >= {"sdd-flow:promotion", "sdd-flow:fingerprints"}
    promotion = _read(CONSUMERS["sdd-flow:promotion"])
    fingerprints = _read(CONSUMERS["sdd-flow:fingerprints"])
    _assert_consumer_wiring("sdd-flow:promotion", promotion)
    _assert_consumer_wiring("sdd-flow:fingerprints", fingerprints)
    assert "import delivery_profile as _delivery_profile" in promotion
    assert "_delivery_profile.parse_plan_frontmatter" in promotion
    assert "_delivery_profile.resolve_delivery_pair" in promotion
    assert "def _delivery_modulo():" in fingerprints
    assert "spec_from_file_location" in fingerprints
    assert "modulo.parse_plan_frontmatter(texto).raw_lines" in fingerprints

    with tempfile.TemporaryDirectory(prefix="delivery-profile-consumers-") as directory:
        arena = Path(directory)
        (arena / "plan.md").write_text(
            "--- \nstatus: planned\ncomplexity: normal\n"
            "delivery_profile: standard\nrisk: low\ncontract_procedure: measured-v1\n"
            f"contract_frozen_version: 1\ncontract_frozen_hash: {'a' * 64}\n--- \n",
            encoding="utf-8",
        )
        (arena / "log.md").write_text("log\n", encoding="utf-8")
        (arena / "tasks.md").write_text(
            "- [ ] **T1 — sample** · cubre: AC-1\n  - **Por qué:** sample\n",
            encoding="utf-8",
        )
        fingerprints = subprocess.run(
            [sys.executable, str(CONSUMERS["sdd-flow:fingerprints"]), "calcular", "--huella",
             "coverage", "--fuente", "tasks.md", "--forma", "tasks", "--plan", "plan.md"],
            cwd=arena, capture_output=True, text=True, check=False)
        assert fingerprints.returncode == 0, fingerprints.stderr
        for name, helper_text in (("ausente", None), ("incompatible", "DELIVERY_PROFILE_CONTRACT_VERSION = 2\n")):
            for consumer, args, expected in (
                (CONSUMERS["sdd-flow:promotion"], ["plan.md", "log.md"],
                 f"ARNES:promocion-tasks-ready delivery-profile-helper-{name}"),
                (CONSUMERS["sdd-flow:fingerprints"],
                 ["calcular", "--huella", "coverage", "--fuente", "tasks.md",
                  "--forma", "tasks", "--plan", "plan.md"],
                 f"ARNES:huellas-secuencia delivery-profile-helper-{name}"),
            ):
                script_dir = arena / f"{consumer.stem}-{name}"
                script_dir.mkdir()
                copied = script_dir / consumer.name
                shutil.copy2(consumer, copied)
                if helper_text is not None:
                    (script_dir / "delivery_profile.py").write_text(helper_text, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(copied), *args], cwd=arena,
                    capture_output=True, text=True, check=False,
                )
                assert result.returncode == 99, (consumer, name, result.stderr)
                assert expected in result.stderr
                assert "Traceback" not in result.stderr

        invalid_cases = (
            ("status: tasks-ready\ncomplexity: normal\ndelivery_profile: expedited\n",
             2, "par-parcial"),
            ("status: planned\ncomplexity: normal\ndelivery_profile: expedited\nrisk: tiny\n",
             2, "riesgo-desconocido"),
            ("status: plan-approved\ncomplexity: complex\ndelivery_profile: expedited\nrisk: low\n",
             1, "expedited-inelegible"),
        )
        for header, code, diagnostic in invalid_cases:
            (arena / "plan.md").write_text(
                f"---\n{header}contract_procedure: measured-v1\n---\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(CONSUMERS["sdd-flow:promotion"]),
                 str(arena / "plan.md"), str(arena / "log.md")],
                capture_output=True, text=True, check=False,
            )
            assert result.returncode == code, result.stderr
            assert f"GUARD:promocion-tasks-ready {diagnostic}" in result.stderr
            assert "Traceback" not in result.stderr
    print("SDD_FLOW_CONSUMER_WIRING_OK")


def test_orchestrator_consumer_wiring(_ctx: Optional[object] = None) -> None:
    """All orchestrator consumers must load, call, and consume the shared helper."""
    assert len(CONSUMERS) == 5
    sources = {name: _read(path) for name, path in CONSUMERS.items()}
    for name in ("orchestrator:model", "orchestrator:state", "orchestrator:integration"):
        _assert_consumer_wiring(name, sources[name])

    mutants = (
        ("sdd-flow:promotion", sources["sdd-flow:promotion"].replace(
            "import delivery_profile as _delivery_profile", "import re as _delivery_profile", 1)),
        ("orchestrator:model", sources["orchestrator:model"].replace(
            "helper.read_plan_frontmatter(plan)", "helper.read_plan_frontmatter_missing(plan)")),
        ("orchestrator:state", sources["orchestrator:state"].replace(
            "parsed = helper.read_plan_frontmatter(path)",
            "helper.read_plan_frontmatter(path)\n    parsed = None", 1)),
        ("orchestrator:integration", sources["orchestrator:integration"].replace(
            "helper = delivery_modulo()", "helper = None", 1)),
        ("sdd-flow:fingerprints", sources["sdd-flow:fingerprints"].replace(
            "return list(modulo.parse_plan_frontmatter(texto).raw_lines)", "return []", 1)),
    )
    for name, mutant in mutants:
        try:
            _assert_consumer_wiring(name, mutant)
        except AssertionError:
            continue
        raise AssertionError(f"wiring mutant survived: {name}")
    print("ORCHESTRATOR_CONSUMER_WIRING_OK")


def test_consumer_wiring(_ctx: Optional[object] = None) -> None:
    """The closed five-consumer registry stays green through both focused subsets."""
    test_sdd_flow_consumer_wiring(_ctx)
    test_orchestrator_consumer_wiring(_ctx)
    print("CONSUMER_WIRING_OK")


CASOS: list[Case] = [
    ("delivery-profile:contract", GROUP, test_profile_contract),
    ("delivery-profile:eligibility", GROUP, test_profile_eligibility),
    ("delivery-profile:assessment-flow", GROUP, test_delivery_assessment_sdd_flow),
    ("delivery-profile:assessment-orchestrator", GROUP, test_delivery_assessment_orchestrator),
    ("delivery-profile:assessment", GROUP, test_delivery_assessment),
    ("delivery-profile:preset", GROUP, test_preset_overrides),
    ("delivery-profile:review-lifecycle", GROUP, test_cross_review_lifecycle),
    ("delivery-profile:jira-off", GROUP, test_jira_off_sequence),
    ("delivery-profile:jira-on", GROUP, test_jira_on_sequence),
    ("delivery-profile:upstream-revocation", GROUP, test_upstream_revocation),
    ("delivery-profile:upstream-regeneration", GROUP, test_upstream_regeneration),
    ("delivery-profile:branch-preservation", GROUP, test_branch_preservation),
    ("delivery-profile:persistence-resume", GROUP, test_persistence_resume),
    ("delivery-profile:quality-permissions", GROUP, test_quality_permissions),
    ("delivery-profile:scenario-matrix", GROUP, test_scenario_matrix),
    ("delivery-profile:trivial", GROUP, test_trivial_profile),
    ("delivery-profile:view-counts", GROUP, test_documented_view_counts),
    ("delivery-profile:review-checkpoint", GROUP, test_review_checkpoint),
    ("delivery-profile:descriptions-unchanged", GROUP, test_descriptions_unchanged),
    ("delivery-profile:wiring-sdd-flow", GROUP, test_sdd_flow_consumer_wiring),
    ("delivery-profile:wiring-orchestrator", GROUP, test_orchestrator_consumer_wiring),
    ("delivery-profile:wiring-all", GROUP, test_consumer_wiring),
]
