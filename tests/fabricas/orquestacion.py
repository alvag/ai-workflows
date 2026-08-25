"""Fabrica escenarios de orquestacion con una sola mutacion logica por caso.

Las precedencias preservan un unico diagnostico: modelo (ubicacion, mapa, clave),
contrato (clases, cardinalidad, huerfanas) y estado (despacho, promocion,
evidencia y correspondencia evento-fila). Las salidas base se publican por
escritura directa; solo las ediciones historicamente realizadas por ``_fx_sed``
se publican mediante rename.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ENCODING = "utf-8"


def _defaults() -> Dict[str, object]:
    values: Dict[str, object] = {
        "BQ": "`", "ID": "notificaciones-v2", "OUTCOME": "", "RETRO": 0,
        "USA_C": 0, "REPARTO": 1, "SKILL_REVALIDA": 1, "V2": "",
        "FILA_HUERFANA": 0, "FILA_DUP": 0, "BIT_VACIA": 0, "BIT_EDIT": "",
        "LOCK": "", "TAREAS": "G1 C1 X1", "FILAS": "G1 C1 X1",
        "A_ST": "done", "B_ST": "done", "C_ST": "done",
        "A_PLANST": "", "B_PLANST": "", "C_PLANST": "",
        "A_SHA": "aaa1111", "B_SHA": "bbb2222", "C_SHA": "ccc3333",
        "A_LOCALBASE": "RED", "B_LOCALBASE": "RED", "C_LOCALBASE": "RED",
        "A_DESPACHO": "auto", "B_DESPACHO": "auto", "C_DESPACHO": "auto",
        "A_COVERS": "AC-1", "B_COVERS": "AC-2", "C_COVERS": "AC-5",
        "A_REFS": "AC-3=V-C1=ok AC-4=V-C1=ok",
        "B_REFS": "AC-3=V-C1=ok", "C_REFS": "",
    }
    tasks = {
        "G1": ("G1", "gate", "equipo-arquitectura", "done",
               "acordar el esquema del evento entre los dos equipos", "@empty@",
               "@empty@", "V-G1", "servicio-b", "@none@", "NOT_APPLICABLE",
               "acuerdo-evento=v3", "", "el acuerdo declara el esquema del evento"),
        "C1": ("C1", "closeout", "equipo-plataforma", "done",
               "correr el flujo end-to-end con los dos servicios desplegados", "G1",
               "AC-3, AC-4", "V-C1", "@none@",
               "AC-3=servicio-a,servicio-b;AC-4=servicio-a", "RED", "@none@",
               "servicio-a=aaa1111, servicio-b=bbb2222",
               "el receptor procesa el evento y responde 200"),
        "X1": ("X1", "closeout", "equipo-datos", "done",
               "archivar el acuerdo del evento en la wiki del equipo", "@empty@",
               "@empty@", "V-X1", "@none@", "@none@", "NOT_APPLICABLE",
               "wiki-acuerdo=v1", "", "el acuerdo quedó archivado en la wiki"),
        "D1": ("C1", "closeout", "equipo-redes", "done",
               "publicar el acuerdo en el catálogo interno", "@empty@", "@empty@",
               "V-D1", "@none@", "@none@", "NOT_APPLICABLE", "catalogo=v1", "",
               "el acuerdo figura en el catálogo"),
    }
    fields = ("ID", "PHASE", "OWNER", "ST", "WHAT", "DEPS", "COVERS", "DW",
              "BLOCKS", "PART", "BASE", "ANCLA", "SHAS", "ESPERADO")
    for task, row in tasks.items():
        for field, value in zip(fields, row):
            values[task + "_" + field] = value
        values[task + "_EVFILA"] = ""
        values[task + "_EVOBJ"] = ""
        values[task + "_OBSERVADO"] = row[-1]
        values[task + "_EVIDENCIA"] = "no" if task == "D1" else "si"
        values[task + "_CIERRE"] = "no" if task == "D1" else "auto"
    return values


def _reparto(v: Dict[str, object]) -> None:
    v.update(G1_ST="pending", C1_ST="pending", X1_ST="pending",
             A_ST="tasks-ready", B_ST="planned")


def _gate_cubre(v: Dict[str, object]) -> None:
    v.update(G1_COVERS="AC-3", G1_PART="AC-3=servicio-a,servicio-b",
             G1_SHAS="servicio-a=aaa1111, servicio-b=bbb2222", G1_ANCLA="@none@",
             C1_COVERS="AC-4", C1_PART="AC-4=servicio-a",
             C1_SHAS="servicio-a=aaa1111",
             A_REFS="AC-3=V-G1=ok AC-4=V-C1=ok", B_REFS="AC-3=V-G1=ok")


def _baseline_blocked(v: Dict[str, object]) -> None:
    v.update(A_LOCALBASE="BLOCKED", A_ST="tasks-ready", A_DESPACHO="rechazado",
             C1_ST="pending", X1_ST="pending")


def _lock(v: Dict[str, object]) -> None:
    v.update(G1_ST="blocked", C1_ST="pending", X1_ST="pending",
             A_ST="done", B_ST="planned")


def _retro(v: Dict[str, object]) -> None:
    v.update(RETRO=1, TAREAS="", FILAS="", A_REFS="", B_REFS="")


NO_CHANGES = {
    "MODELO_VALIDO", "PARTICIPACION_AUSENTE_SIN_INTEG", "CONTRATO_COMPLETO",
    "BASELINE_NOT_APPLICABLE", "REF_CLOSEOUT", "CIERRE_LEGITIMO",
    "BITACORA_TRANSICION_CONSUMADA", "FRESCURA_VALIDA_MULTIREPO",
    "FRESCURA_VALIDA_ANCLA_NO_CODIGO", "PRECEDENCIA_TODO_DONE",
}


def _aplicar_escenario(name: str, v: Dict[str, object]) -> bool:
    if name in NO_CHANGES:
        return True
    updates: Dict[str, Dict[str, object]] = {
        "PARTICIPACION_VACIA_SIN_INTEG": {"X1_PART": "@empty@"},
        "AC_INTEGRATION_HUERFANO": {"C1_COVERS": "AC-4", "C1_PART": "AC-4=servicio-a", "A_REFS": "AC-4=V-C1=ok", "B_REFS": ""},
        "AC_MAL_UBICADO_INTEG_EN_REPO": {"A_COVERS": "AC-1, AC-3"},
        "AC_MAL_UBICADO_LOCAL_EN_TAREA": {"C1_COVERS": "AC-3, AC-4, AC-1", "C1_PART": "AC-3=servicio-a,servicio-b;AC-4=servicio-a;AC-1=servicio-a"},
        "CARDINALIDAD_DOS_TAREAS": {"X1_COVERS": "AC-3", "X1_PART": "AC-3=servicio-a,servicio-b"},
        "CICLO": {"C1_DEPS": "G1, X1", "X1_DEPS": "C1"},
        "ID_DUPLICADO": {"TAREAS": "G1 C1 X1 D1"},
        "REF_MUERTA_DEPENDS": {"C1_DEPS": "G9"}, "REF_MUERTA_BLOCKS": {"G1_BLOCKS": "servicio-z"},
        "ENUM_PHASE": {"C1_PHASE": "cierre"}, "ENUM_STATUS": {"C1_ST": "pendiente"},
        "OWNER_AUSENTE": {"C1_OWNER": "@none@"}, "OWNER_VACIO": {"C1_OWNER": "@empty@"},
        "DONE_WHEN_AUSENTE": {"X1_DW": "@none@"}, "DONE_WHEN_VACIO": {"X1_DW": "@empty@"},
        "BLOCKS_EN_CLOSEOUT": {"C1_BLOCKS": "servicio-b"}, "GATE_DEPENDE_CLOSEOUT": {"G1_DEPS": "X1"},
        "PARTICIPACION_CLAVE_DUP": {"C1_PART": "AC-3=servicio-a,servicio-b;AC-3=servicio-a;AC-4=servicio-a"},
        "PARTICIPACION_REPO_INEXISTENTE": {"C1_PART": "AC-3=servicio-a,servicio-z;AC-4=servicio-a"},
        "PARTICIPACION_AC_NO_INTEG": {"C1_COVERS": "AC-3, AC-4, AC-7", "C1_PART": "AC-3=servicio-a,servicio-b;AC-4=servicio-a;AC-7=servicio-a"},
        "PARTICIPACION_AC_SIN_CLAVE": {"C1_PART": "AC-3=servicio-a,servicio-b"},
        "PARTICIPACION_CLAVE_EXTRA": {"C1_PART": "AC-3=servicio-a,servicio-b;AC-4=servicio-a;AC-9=servicio-b"},
        "PARTICIPACION_AUSENTE_CON_INTEG": {"C1_PART": "@none@"},
        "PARTICIPACION_VACIA_CON_INTEG": {"C1_PART": "@empty@"},
        "SOLO_GATES": {"FILAS": "G1"}, "SIN_AUXILIAR": {"FILAS": "G1 C1"},
        "CARDINALIDAD_TAREA_SIN_FILA": {"FILAS": "G1 X1"},
        "CARDINALIDAD_FILA_HUERFANA": {"FILA_HUERFANA": 1}, "CARDINALIDAD_DOS_FILAS": {"FILA_DUP": 1},
        "BASELINE_SIN_RESOLVER": {"X1_BASE": "TBD"}, "V2_AGREGA_ID": {"V2": "agrega"}, "V2_QUITA_ID": {"V2": "quita"},
        "CIERRE_LOCAL_PROHIBIDO": {"A_REFS": "AC-3=V-C1=local AC-4=V-C1=ok"},
        "CIERRE_LOCAL_NOT_APPLICABLE": {"A_REFS": "AC-3=V-C1=na AC-4=V-C1=ok"},
        "REF_ESPERADA_AUSENTE": {"A_REFS": "AC-3=V-C1=ok"},
        "REF_EN_NO_PARTICIPANTE": {"B_REFS": "AC-3=V-C1=ok AC-4=V-C1=ok"},
        "REF_CON_LITERAL_VIEJO": {"A_REFS": "AC-3=V-C1=viejo AC-4=V-C1=ok"},
        "REF_A_FILA_EQUIVOCADA": {"B_REFS": "AC-3=V-X1=ok"},
        "MIXTO_2P_1NP": {"USA_C": 1}, "FASE3_SIN_REVALIDAR": {"SKILL_REVALIDA": 0},
        "DONE_GATE_UNASSIGNED_SINAC": {"G1_OWNER": "UNASSIGNED"},
        "DONE_CLOSEOUT_UNASSIGNED_CONAC": {"C1_OWNER": "UNASSIGNED"},
        "DONE_CLOSEOUT_UNASSIGNED_SINAC": {"X1_OWNER": "UNASSIGNED"},
        "DEPS_INSATISFECHAS": {"X1_DEPS": "C1", "C1_ST": "in-progress"},
        "EVIDENCIA_OBSOLETA": {"C1_EVIDENCIA": "no"},
        "ESPERADO_FALLIDO": {"C1_OBSERVADO": "el receptor descarta el evento y responde 500"},
        "DONE_WHEN_DIVERGENTE": {"C1_DW": "V-C9"}, "DUENO_DUPLICADO": {"X1_OWNER": "equipo-plataforma"},
        "EVIDENCIA_DUPLICADA": {"X1_DW": "V-C1", "X1_EVFILA": "V-C1"},
        "FRESCURA_FILA_EQUIVOCADA": {"C1_EVFILA": "V-Z9"}, "FRESCURA_TAREA_EQUIVOCADA": {"C1_EVOBJ": "X1"},
        "FRESCURA_VERSION_ANTERIOR": {"V2": "igual"}, "FRESCURA_REPO_MOVIDO": {"B_SHA": "bbb9999"},
        "FRESCURA_REPO_AUSENTE": {"C1_SHAS": "servicio-a=aaa1111"},
        "FRESCURA_ANCLA_AUSENTE": {"G1_ANCLA": "@none@"}, "FRESCURA_ANCLA_OBSOLETA": {"G1_ANCLA": "acuerdo-evento=v2"},
        "BITACORA_AUSENTE": {"BIT_VACIA": 1}, "BITACORA_ID_DUPLICADO": {"BIT_EDIT": "id-duplicado"},
        "BITACORA_ORDEN_AMBIGUO": {"BIT_EDIT": "orden-ambiguo"}, "BITACORA_RESULTADO_INVALIDO": {"BIT_EDIT": "resultado-invalido"},
        "BITACORA_EXITO_SIN_EFECTO": {"X1_ST": "pending", "X1_CIERRE": "forzado"},
        "BITACORA_RECHAZO_CON_EFECTO": {"BIT_EDIT": "rechazo-con-efecto"},
        "BITACORA_TRANSICION_SIN_EVENTO": {"BIT_EDIT": "sin-evento"},
        "PRECEDENCIA_REPO_FAILED": {"A_ST": "failed"}, "PRECEDENCIA_REPO_BLOCKED": {"B_ST": "blocked"},
        "PRECEDENCIA_EN_CURSO": {"B_ST": "implementing"}, "PRECEDENCIA_INTEGRACION_PENDIENTE": {"C1_ST": "pending"},
        "PRECEDENCIA_FAILED_MAS_INTEG_PENDIENTE": {"A_ST": "failed", "C1_ST": "pending"},
        "PRECEDENCIA_FAILED_MAS_REPO_BLOCKED": {"A_ST": "failed", "B_ST": "blocked"},
        "PRECEDENCIA_EN_CURSO_MAS_INTEG_PENDIENTE": {"B_ST": "implementing", "C1_ST": "pending"},
        "ARCHIVE_CIERRE_PENDIENTE": {"OUTCOME": "archived", "C1_ST": "pending"},
        "ARCHIVE_VARIAS_PENDIENTES": {"OUTCOME": "archived", "REPARTO": 0, "G1_ST": "pending", "C1_ST": "pending", "X1_ST": "pending", "A_ST": "planned", "B_ST": "planned"},
    }
    if name in updates:
        v.update(updates[name])
        return True
    if name == "REF_GATE": _gate_cubre(v)
    elif name == "RETROCOMPAT": _retro(v)
    elif name in {"ASIGNACION_INICIAL", "GATE_ABIERTO_DESPACHO_RECHAZADO", "BITACORA_INTENTO_RECHAZADO"}: _reparto(v)
    elif name == "REPARTO_OWNER_UNASSIGNED": _reparto(v); v["C1_OWNER"] = "UNASSIGNED"
    elif name == "ASIGNACION_LIBRE_AUN_PLANNED": _reparto(v); v["A_ST"] = "planned"
    elif name == "ASIGNACION_BLOQUEADO_YA_READY": _reparto(v); v.update(B_ST="tasks-ready", B_DESPACHO="no")
    elif name == "DIVERGENCIA_MANIFEST_PLAN": _reparto(v); v["A_PLANST"] = "planned"
    elif name == "GATE_ABIERTO_REPO_PLANNED": _reparto(v); v["B_DESPACHO"] = "no"
    elif name == "GATE_ABIERTO_DESPACHO_EXITOSO": _reparto(v); v["B_ST"] = "implementing"
    elif name in {"GATE_CERRADO_REPO_READY", "PROMOCION_TRAS_GATE"}: _reparto(v); v.update(G1_ST="done", B_ST="implementing")
    elif name == "GATE_CERRADO_REPO_AUN_PLANNED": _reparto(v); v["G1_ST"] = "done"
    elif name == "GATE_CERRADO_SIN_DESPACHO": _reparto(v); v.update(G1_ST="done", B_ST="tasks-ready", B_DESPACHO="no")
    elif name == "BASELINE_BLOCKED_SIN_DESPACHO": _baseline_blocked(v)
    elif name == "DESPACHO_CON_BASELINE_BLOCKED": _baseline_blocked(v); v["A_ST"] = "implementing"
    elif name == "LOCK_LIBERADO_TRAS_DECISION": _lock(v); v["LOCK"] = "con-decision"
    elif name == "LOCK_LIBERACION_RECHAZADA_SIN_DECISION": _lock(v); v["LOCK"] = "rechazado"
    elif name == "LOCK_LIBERADO_SIN_DECISION": _lock(v); v["LOCK"] = "sin-decision"
    elif name == "DONE_GATE_UNASSIGNED_CONAC": _gate_cubre(v); v["G1_OWNER"] = "UNASSIGNED"
    elif name.startswith("BITACORA_EVENTO_SIN_"):
        v["BIT_EDIT"] = "sin-campo:" + name.removeprefix("BITACORA_EVENTO_SIN_").lower()
    elif name == "PRECEDENCIA_GATE_BLOCKED": _lock(v)
    elif name == "PRECEDENCIA_GATE_BLOCKED_MAS_EN_CURSO": _lock(v); v["A_ST"] = "implementing"
    elif name == "PRECEDENCIA_REPO_BLOCKED_MAS_GATE_BLOCKED": _lock(v); v["B_ST"] = "blocked"
    else: return False
    return True


class Factory:
    def __init__(self, root: Path, values: Dict[str, object]) -> None:
        self.root = root
        self.v = values
        self.identifier = str(values["ID"])
        self.base = root / ".sdd" / self.identifier
        self.manifest = self.base / "manifest.yml"
        self.spec = self.base / "master-spec.md"
        self.contract = self.base / "integracion.md"
        self.log = self.base / "bitacora.md"
        self.skill = root / "skill" / "SKILL.md"
        self.event_number = 0

    def get(self, prefix: str, field: str) -> str:
        return str(self.v[prefix + "_" + field])

    def repos(self) -> Tuple[str, ...]:
        return ("a", "b", "c") if self.v["USA_C"] == 1 else ("a", "b")

    @staticmethod
    def repo_path(repo: str) -> str:
        return {"a": "servicio-a", "b": "servicio-b", "c": "servicio-c"}[repo]

    @staticmethod
    def upper(repo: str) -> str:
        return repo.upper()

    def plan_path(self, repo: str) -> Path:
        return self.root / self.repo_path(repo) / ".plans" / self.identifier / "plan.md"

    @staticmethod
    def yaml_list(value: str) -> Optional[str]:
        if value == "@none@": return None
        if value == "@empty@": return "[]"
        return "[" + value + "]"

    def emit_manifest(self) -> str:
        lines = [f"id: {self.identifier}", f"master_spec: .sdd/{self.identifier}/master-spec.md", "created_at: 2026-06-03T09:00:00-03:00"]
        if self.v["OUTCOME"]: lines.append("outcome: " + str(self.v["OUTCOME"]))
        lines.append("repos:")
        for repo in self.repos():
            up, path = self.upper(repo), self.repo_path(repo)
            lines += [f"  - path: {path}", f"    branch: feature/{self.identifier}-{path}", f"    status: {self.get(up, 'ST')}", "    depends_on: []", f"    covers_ac: [{self.get(up, 'COVERS')}]" ]
        if not self.v["TAREAS"]: return "\n".join(lines) + "\n"
        lines.append("orchestration_tasks:")
        for task in str(self.v["TAREAS"]).split():
            lines += [f"  - id: {self.get(task, 'ID')}", f"    phase: {self.get(task, 'PHASE')}", f"    what: {self.get(task, 'WHAT')}"]
            owner = self.get(task, "OWNER")
            if owner == "@empty@": lines.append('    owner: ""')
            elif owner != "@none@": lines.append("    owner: " + owner)
            lines.append("    status: " + self.get(task, "ST"))
            for field, label in (("DEPS", "depends_on"), ("COVERS", "covers_ac")):
                value = self.yaml_list(self.get(task, field))
                if value is not None: lines.append(f"    {label}: {value}")
            done = self.get(task, "DW")
            if done == "@empty@": lines.append('    done_when: ""')
            elif done != "@none@": lines.append("    done_when: " + done)
            blocks = self.yaml_list(self.get(task, "BLOCKS"))
            if blocks is not None: lines.append("    blocks_repos: " + blocks)
            part = self.get(task, "PART")
            if part == "@empty@": lines.append("    participating_repos: {}")
            elif part != "@none@":
                lines.append("    participating_repos:")
                for pair in part.split(";"):
                    ac, repos = pair.split("=", 1)
                    lines.append(f"      {ac}: [{repos.replace(',', ', ')}]")
        return "\n".join(lines) + "\n"

    def emit_spec(self) -> str:
        lines = ["# Master Spec — notificaciones v2", "", "## Problema / Objetivo", "Publicar y consumir el evento de notificación entre los dos servicios.", "", "## Alcance", "- **Incluye:** el emisor, el receptor y el acuerdo del evento.", "- **No incluye:** los avisos por correo.", "", "## Criterios de aceptación", "- **AC-1 [repo-local]:** Given el emisor, When se crea una notificación, Then publica el evento.", "- **AC-2 [repo-local]:** Given el receptor, When llega el evento, Then lo procesa."]
        if self.v["USA_C"] == 1: lines.append("- **AC-5 [repo-local]:** Given el panel, When se consulta el histórico, Then lista las notificaciones.")
        if self.v["RETRO"] == 0: lines += ["- **AC-3 [integration]:** Given los dos servicios arriba, When se crea una notificación, Then el receptor la procesa y responde 200.", "- **AC-4 [integration]:** Given el acuerdo publicado, When se valida el esquema del evento, Then emisor y receptor coinciden."]
        lines += ["", "## Contratos entre servicios", "- **servicio-a expone:** evento `notificacion.creada {id, destinatario}`.", "- **servicio-b consume:** `notificacion.creada` desde el bus.", "", "## Anclas versionadas", "- `acuerdo-evento: v3`", "- `wiki-acuerdo: v1`", "- `catalogo: v1`", "", "## Reparto", "| AC | Repo(s) | Tipo |", "|---|---|---|", "| AC-1 | servicio-a | repo-local |", "| AC-2 | servicio-b | repo-local |"]
        if self.v["USA_C"] == 1: lines.append("| AC-5 | servicio-c | repo-local |")
        if self.v["RETRO"] == 0: lines += ["| AC-3 | servicio-a + servicio-b | integration |", "| AC-4 | servicio-a | integration |"]
        return "\n".join(lines) + "\n"

    def evidence(self, task: str) -> str:
        return "manual" if task == "C1" else "inspección"

    def command(self, task: str) -> str:
        if task == "C1": return "desplegar los dos servicios y publicar una notificación"
        if task == "G1": return '`grep -c "^evento:" acuerdo.md`'
        return "`grep -c acuerdo wiki.md`"

    def baseline_record(self, row_id: str, baseline: str) -> str:
        line = f"- `id: {row_id}` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00`"
        if baseline == "NOT_APPLICABLE": line += " · `justificación: la evidencia es un acuerdo entre equipos; no hay comando que ejecutar contra el código`"
        elif baseline == "GREEN_ALREADY": line += " · `adjudicación: already_satisfied`"
        return line

    def contract_version(self, version: str, tasks: str) -> str:
        lines = [f"## {version}", "", "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |", "|---|---|---|---|---|---|"]
        for task in tasks.split():
            if task == "Z9":
                lines.append("| V-Z9 | Z9 — revisar el tablero de la orquestación [—] | inspección | `grep -c tablero notas.md` | `1` | NOT_APPLICABLE |")
                continue
            covers = self.get(task, "COVERS")
            if covers in {"@empty@", "@none@"}: covers = "—"
            lines.append(f"| V-{self.get(task, 'ID')} | {self.get(task, 'ID')} — {self.get(task, 'WHAT')} [{covers}] | {self.evidence(task)} | {self.command(task)} | {self.get(task, 'ESPERADO')} | {self.get(task, 'BASE')} |")
            if self.v["FILA_DUP"] == 1 and task == "X1": lines.append(f"| V-X1-bis | X1 — {self.get('X1', 'WHAT')} [—] | inspección | `grep -c acuerdo wiki.md` | `1` | NOT_APPLICABLE |")
        if self.v["FILA_HUERFANA"] == 1: lines.append("| V-H9 | H9 — publicar el changelog de la orquestación [—] | inspección | `grep -c changelog notas.md` | `1` | NOT_APPLICABLE |")
        lines += ["", f"### Baseline de {version}", "`hash_previo:` · `hash: 9b1c04e2`", ""]
        for task in tasks.split():
            if task == "Z9": lines.append("- `id: V-Z9` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00` · `justificación: la fila mira un tablero que este cambio no produce`")
            else:
                lines.append(self.baseline_record("V-" + self.get(task, "ID"), self.get(task, "BASE")))
                if self.v["FILA_DUP"] == 1 and task == "X1": lines.append(self.baseline_record("V-X1-bis", "NOT_APPLICABLE"))
        if self.v["FILA_HUERFANA"] == 1: lines.append(self.baseline_record("V-H9", "NOT_APPLICABLE"))
        return "\n".join(lines) + "\n"

    def emit_contract(self) -> str:
        body = f"# Contrato de integración — {self.identifier}\n\n" + self.contract_version("v1", str(self.v["FILAS"]))
        if self.v["V2"]:
            tasks = str(self.v["FILAS"])
            if self.v["V2"] == "agrega": tasks += " Z9"
            elif self.v["V2"] == "quita": tasks = tasks.replace(" X1", "")
            body += "\n" + self.contract_version("v2", tasks)
        return body

    def timestamp(self) -> str:
        return f"2026-06-03T{10 + self.event_number // 60:02d}:{self.event_number % 60:02d}:00-03:00"

    def event(self, step: str, actor: str, obj: str, result: str, extra: Tuple[str, ...] = ()) -> str:
        self.event_number += 1
        fields = (("id", str(self.event_number)), ("paso", step), ("actor", actor), ("objeto", obj), ("resultado", result), ("timestamp", self.timestamp()))
        line = "- " + " · ".join(f"`{key}: {value}`" for key, value in fields)
        if extra: line += " · " + " · ".join("`" + item + "`" for item in extra)
        return line

    def evidence_event(self, task: str) -> str:
        obj = self.get(task, "EVOBJ") or self.get(task, "ID")
        actor = self.get(task, "OWNER")
        if actor in {"@none@", "@empty@", "UNASSIGNED"}: actor = "orquestador"
        row = self.get(task, "EVFILA") or "V-" + self.get(task, "ID")
        extra: List[str] = ["fila: " + row, "contrato: v1"]
        if self.get(task, "SHAS"): extra.append("sha: " + self.get(task, "SHAS"))
        anchor = self.get(task, "ANCLA")
        if anchor not in {"", "@none@"}: extra.append("ancla: " + anchor)
        extra.append("observado: " + self.get(task, "OBSERVADO"))
        return self.event("ejecutar-evidencia", actor, obj, "consumado", tuple(extra))

    def emit_log(self) -> str:
        if self.v["BIT_VACIA"] == 1: return ""
        lines = [f"# Bitácora de transiciones — {self.identifier}", ""]
        if self.v["REPARTO"] == 1:
            for repo in self.repos():
                path, status = self.repo_path(repo), self.get(self.upper(repo), "ST")
                lines.append(self.event("promover-repo", "orquestador", path, "rechazado" if status == "planned" else "consumado"))
            for repo in self.repos():
                up, path = self.upper(repo), self.repo_path(repo)
                status, dispatch = self.get(up, "ST"), self.get(up, "DESPACHO")
                if dispatch == "no": continue
                if dispatch in {"rechazado", "consumado"}: result = dispatch
                elif status == "tasks-ready": continue
                else: result = "rechazado" if status in {"planned", "blocked"} else "consumado"
                lines.append(self.event("despachar-repo", "orquestador", path, result))
        if self.v["LOCK"]:
            extra = ("decision: excluir-repo",) if self.v["LOCK"] == "con-decision" else ()
            result = "rechazado" if self.v["LOCK"] == "rechazado" else "consumado"
            lines.append(self.event("liberar-lock", "orquestador", "servicio-b", result, extra))
        for task in str(self.v["TAREAS"]).split():
            if self.get(task, "ST") != "done" and self.get(task, "CIERRE") != "forzado": continue
            if self.get(task, "CIERRE") == "no": continue
            if self.get(task, "EVIDENCIA") == "si": lines.append(self.evidence_event(task))
            lines.append(self.event("cerrar-tarea", "orquestador", self.get(task, "ID"), "consumado"))
        return "\n".join(lines) + "\n"

    def emit_plan(self, repo: str) -> str:
        up, path = self.upper(repo), self.repo_path(repo)
        status = self.get(up, "PLANST") or self.get(up, "ST")
        lines = ["---", f"id: {self.identifier}", f"repo: {path}", f"branch: feature/{self.identifier}-{path}", "base_commit: 0000000", f"head_sha: {self.get(up, 'SHA')}", f"status: {status}", "---", "", f"# Plan — {path} (parte de {self.identifier})", "", "## Verification", "", "### v1", "", "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |", "|---|---|---|---|---|---|", f"| V1 | {self.get(up, 'COVERS')} [repo-local] — el repo cumple su parte | test | `npm test` | 1 test, verde | {self.get(up, 'LOCALBASE')} |"]
        references = self.get(up, "REFS").split()
        for index, ref in enumerate(references, 2):
            ac, row, mode = ref.split("=")
            if mode == "local": line = f"| V{index} | {ac} [integration] — el repo lo verifica de su lado | test | `npm test -- integracion` | 1 test, verde | RED |"
            else:
                evidence = {"na": "NOT_APPLICABLE", "viejo": "N/A: Fase 3"}.get(mode, "N/A: orchestration-owned")
                line = f"| V{index} | {ac} [integration] — cerrado en el contrato de integración | {evidence} | ver {row} de integracion.md | se verifica en el contrato de integración | {evidence} |"
            lines.append(line)
        lines += ["", "#### Baseline de v1", "`hash_previo:` · `hash: 3c7f1ab0`", "", "- `id: V1` · `commit: 0000000` · `timestamp: 2026-06-03T09:20:00-03:00`"]
        for index, _ref in enumerate(references, 2): lines.append(f"- `id: V{index}` · `commit: 0000000` · `timestamp: 2026-06-03T09:20:00-03:00` · `justificación: la fila se cierra en el contrato de integración de la orquestación`")
        return "\n".join(lines) + "\n"

    def emit_skill(self) -> str:
        revalidation = "- La Fase 3 revalida la versión vigente del contrato antes de ejecutar evidencia." if self.v["SKILL_REVALIDA"] == 1 else "- Congelarlo **antes** de ejecutar la primera evidencia."
        return "\n".join(["# sdd-orchestrator", "", "## Fase 3 · Cierre (centralizada, el usuario al mando)", "", "- Gate de apertura del contrato de integración: el contrato pasa su gate antes de la primera evidencia.", revalidation, "- Una tabla de precedencia produce el estado agregado como `ESTADO:<valor>` y nunca oculta el más grave.", "- Cada ejecución de evidencia y cada cierre de tarea registra su intento en la bitácora antes de materializarse.", "", "| # | Estado agregado | Cuándo |", "|---|---|---|", "| 1 | `ESTADO:no-verificado:repo-failed` | algún repo quedó en `failed` |", "| 2 | `ESTADO:no-verificado:repo-blocked` | algún repo quedó en `blocked` |", "| 3 | `ESTADO:no-verificado:gate-blocked` | alguna tarea `gate` quedó en `blocked` |", "| 4 | `ESTADO:en-curso` | algún repo sigue en marcha |", "| 5 | `ESTADO:no-verificado:integracion-pendiente` | queda una tarea de orquestación sin cerrar |", "| 6 | `ESTADO:done` | todo cerrado |", "", "Una fila ausente, `BLOCKED` o `manual` pendiente produce no verificado.", ""])

    def emit_env(self) -> Tuple[str, str]:
        plans = [str(self.plan_path(repo)) for repo in self.repos()]
        shell = "\n".join([f'export repos="{" ".join(plans)}"', f'export manifest="{self.manifest}"', f'export master_spec="{self.spec}"', f'export contrato="{self.contract}"', f'export bitacora="{self.log}"', f'export skill_orq="{self.skill}"', ""])
        powershell = "$repos = @(" + ",".join("'" + plan + "'" for plan in plans) + ")\n" + "\n".join([f"$manifest = '{self.manifest}'", f"$master_spec = '{self.spec}'", f"$contrato = '{self.contract}'", f"$bitacora = '{self.log}'", f"$skill_orq = '{self.skill}'", ""])
        return shell, powershell

    def edit_log(self, text: str) -> str:
        edit = str(self.v["BIT_EDIT"])
        lines = text.splitlines(keepends=True)
        if edit in {"id-duplicado", "orden-ambiguo"} and lines:
            replacement = "1" if edit == "id-duplicado" else "ultimo"
            lines[-1] = re.sub(r"id: [0-9][0-9]*", "id: " + replacement, lines[-1], count=1)
        elif edit in {"resultado-invalido", "rechazo-con-efecto", "sin-evento"}:
            target = "C1" if edit == "resultado-invalido" else "X1"
            for index, line in enumerate(lines):
                if "cerrar-tarea" in line and "objeto: " + target in line:
                    if edit == "sin-evento": del lines[index]
                    else:
                        value = "ok" if edit == "resultado-invalido" else "rechazado"
                        lines[index] = line.replace("resultado: consumado", "resultado: " + value, 1)
                    break
        elif edit.startswith("sin-campo:"):
            field = edit.split(":", 1)[1]
            for index, line in enumerate(lines):
                if "cerrar-tarea" in line and "objeto: C1" in line:
                    if field == "id": lines[index] = re.sub(r"^- `id: [^`]*` · ", "- ", line)
                    else: lines[index] = re.sub(r" · `" + re.escape(field) + r": [^`]*`", "", line)
                    break
        return "".join(lines)

    def materialize(self) -> Tuple[Path, ...]:
        self.base.mkdir(parents=True, exist_ok=True)
        self.skill.parent.mkdir(parents=True, exist_ok=True)
        for repo in self.repos(): self.plan_path(repo).parent.mkdir(parents=True, exist_ok=True)
        outputs: List[Tuple[Path, str]] = [(self.manifest, self.emit_manifest()), (self.spec, self.emit_spec()), (self.contract, self.emit_contract()), (self.log, self.emit_log())]
        outputs += [(self.plan_path(repo), self.emit_plan(repo)) for repo in self.repos()]
        outputs.append((self.skill, self.emit_skill()))
        for path, body in outputs: _publish_direct(path, body)
        if self.v["BIT_EDIT"]: _publish_rename(self.log, self.edit_log(self.log.read_text(encoding=ENCODING)))
        shell, powershell = self.emit_env()
        _publish_direct(self.root / "env.sh", shell)
        _publish_direct(self.root / "env.ps1", powershell)
        return tuple(path for path, _body in outputs) + (self.root / "env.sh", self.root / "env.ps1")


def _publish_direct(path: Path, body: str) -> None:
    path.write_text(body, encoding=ENCODING)


def _publish_rename(path: Path, body: str) -> None:
    temporary = path.with_name(path.name + ".fxtmp")
    temporary.write_text(body, encoding=ENCODING)
    os.replace(temporary, path)


def materialize(scenario: str, root: Optional[Path] = None) -> Tuple[Path, ...]:
    values = _defaults()
    if not _aplicar_escenario(scenario, values):
        raise ValueError("escenario desconocido: " + scenario)
    return Factory(Path.cwd() if root is None else root, values).materialize()


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:fixtures-orquestacion scenario", file=sys.stderr)
        return 2
    try:
        materialize(sys.argv[1])
    except ValueError as exc:
        print("ARNES:" + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
