"""Predicado: comprueba que SKILL y reference enseñen la misma cadena de producción, verificación,
ownership y recuperación, incluidas la proyección bloqueada y la rotación de secuencia."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple


USO = "USO:verify-ejecuta sdd_flow_skill sdd_flow_reference"


# Veinte identidades cerradas. El valor indica en qué sede debe aparecer cada marcador.
IDENTIDADES: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "documentos-canonicos": ("ambos", ("Producción del contrato de verificación",)),
    "cargar-ausente": ("skill", ("**CARGAR**",)),
    "identificar-presente": ("skill-ausente", ("**IDENTIFICAR**",)),
    "revert-ausente": ("skill", ("revert-to-confirm",)),
    "puntero-produccion-ausente": (
        "ambos", ("contrato-invariantes.py", "candidate", "final",
                  "`final` precede a congelar")),
    "medicion-directa-blocked-ausente": ("ambos", ("CROSS_IMPLEMENT_PROJECTION_BLOCKED",)),
    "verify-ownership-ausente": ("ambos", ("ownership-presupuesto.py",)),
    "agotamiento-entorno-ausente": ("ambos", ("ENVIRONMENT_FAILURE", "DESIGN_GAP")),
    "recuperacion-rotacion-ausente": ("ambos", ("rotation-pending", "rotation-completed")),
    "rotation-pending-disjunta": ("ambos", ("terminal:abandoned", "A ausente")),
    "rotation-pending-autoridad-paquete": ("ambos", ("archive_package", "incoming | outgoing")),
    "rotation-pending-resultado-cerrado": ("ambos", ("rollback-pending", "rotation-completed")),
    "rotation-pending-tupla-completa": ("ambos", ("pre-refresh", "post-refresh", "conflict:package")),
    "rotation-completed-autoridad-git": ("ambos", ("base_anchor", "pending-delta.patch")),
    "rotation-pending-propuesta-autorizada": ("ambos", ("RecoveryProposal.rotation_steps",)),
    "rotation-pending-cadena-sucesora": ("ambos", ("plan-refresh", "ledger-rotation")),
    "rotation-gate-acotado": ("ambos", ("gate de recuperación", "camino continuo")),
    "rotation-particion-minima": ("ambos", ("partición `rotación`", "seis casos")),
    "reinicio-explicitamente-aprobado": ("ambos", ("aprobar-reparación", "reiniciar")),
    "rollback-pending-particion-minima": ("ambos", ("reinicio post-rollback", "tres casos")),
}


def main() -> int:
    if len(sys.argv) != 3:
        print(USO, file=sys.stderr)
        return 2
    try:
        skill = Path(sys.argv[1]).read_text(encoding="utf-8")
        reference = Path(sys.argv[2]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print("GUARD:verify-solo-ejecuta documentos canónicos inaccesibles", file=sys.stderr)
        return 1
    if len(IDENTIDADES) != 20 or len(set(IDENTIDADES)) != 20:
        print("GUARD:verify-solo-ejecuta tabla interna distinta de veinte", file=sys.stderr)
        return 1
    errores = []
    for identidad, (sede, marcadores) in IDENTIDADES.items():
        if sede == "skill-ausente":
            if any(marcador in skill for marcador in marcadores):
                errores.append(identidad)
            continue
        textos = (skill, reference) if sede == "ambos" else (skill,)
        if any(any(marcador not in texto for marcador in marcadores) for texto in textos):
            errores.append(identidad)
    if errores:
        print("GUARD:verify-solo-ejecuta faltan marcadores: " + ", ".join(errores), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
