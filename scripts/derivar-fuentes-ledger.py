#!/usr/bin/env python3
"""Deriva el conjunto de candidatos de las CUATRO fuentes cerradas, y las ternas del manifest.

`--ledger` del instrumento exige este archivo por `--fuentes` y no lo descubre él mismo: descubrir
sobre el mismo árbol que se valida sería contarlo sobre sí mismo. Por eso la derivación vive acá,
aparte, y su salida es un artefacto derivado que se regenera cuando cambia cualquiera de las fuentes.

Las cuatro fuentes y de dónde sale cada una:

  anomalias_del_runner        `scripts/journal-anomalias-fase-0/`  · un candidato por anomalía
  fallos_de_fixtures          `scripts/recibos-autotest-fase-0/`   · un candidato por modo y caso
  adjudicaciones_de_cohorte   `scripts/preregistro-fase-0.json`    · un candidato por adjudicación
  reportes_de_implementacion  `.plans/instrumento-y-baseline/work/defectos-descubiertos.json`

**Una fuente vacía es un conjunto vacío, no un error** — pero la diferencia entre «no produjo
candidatos» y «no existe» se INFORMA, porque las dos dan cero y solo una es una medición. Un
directorio que nunca se creó es un punto de emisión que falta, y eso es un dato del flujo.

Uso:
    python3 scripts/derivar-fuentes-ledger.py                     # a stdout
    python3 scripts/derivar-fuentes-ledger.py --salida <ruta>     # a un archivo
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent

DIR_ANOMALIAS = RAIZ / "scripts/journal-anomalias-fase-0"
DIR_RECIBOS_AUTOTEST = RAIZ / "scripts/recibos-autotest-fase-0"
RUTA_PREREGISTRO = RAIZ / "scripts/preregistro-fase-0.json"
RUTA_DEFECTOS = RAIZ / ".plans/instrumento-y-baseline/work/defectos-descubiertos.json"
RUTA_MANIFEST = RAIZ / "scripts/manifest-despachos-fase-0.json"


def _json(ruta: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(ruta.read_text(encoding="utf-8")), None
    except OSError as e:
        return None, f"no se pudo leer {ruta}: {e}"
    except json.JSONDecodeError as e:
        return None, f"{ruta} no es JSON válido: {e}"


def de_anomalias_del_runner() -> tuple[list[dict], str]:
    """Un candidato por anomalía. El schema del journal no cuenta: es el contrato, no un registro."""
    if not DIR_ANOMALIAS.is_dir():
        return [], "el directorio no existe: el punto de emisión nunca se creó"
    registros = sorted(p for p in DIR_ANOMALIAS.glob("*.json")
                       if not p.name.endswith(".schema.json"))
    if not registros:
        return [], ("el directorio existe con su schema y sin ningún registro: el runner no emitió "
                    "ninguna anomalía en las 13 corridas")
    candidatos = []
    for ruta in registros:
        datos, error = _json(ruta)
        if error:
            candidatos.append({"candidate_id": f"anomalia-ilegible-{ruta.stem}", "detalle": error})
            continue
        for anomalia in datos.get("anomalias") or []:
            candidatos.append({"candidate_id": anomalia.get("candidate_id"),
                               "detalle": anomalia.get("detalle")})
    return candidatos, f"{len(registros)} registros"


def de_fallos_de_fixtures() -> tuple[list[dict], str]:
    """Un candidato por modo y caso. Identidad `<modo>·<caso>`, fuera del namespace de bundles."""
    if not DIR_RECIBOS_AUTOTEST.is_dir():
        return [], "el directorio no existe: el punto de emisión nunca se creó"
    recibos = sorted(DIR_RECIBOS_AUTOTEST.glob("*.json"))
    candidatos = []
    for ruta in recibos:
        datos, error = _json(ruta)
        if error:
            candidatos.append({"candidate_id": f"recibo-ilegible-{ruta.stem}", "detalle": error})
            continue
        for fallo in datos.get("fallos") or []:
            candidatos.append({
                "candidate_id": f"fixture-{fallo.get('modo')}-{fallo.get('caso')}",
                "detalle": fallo.get("detalle")})
    return candidatos, f"{len(recibos)} recibos"


def de_adjudicaciones_de_cohorte() -> tuple[list[dict], str]:
    """Las adjudicaciones que el pre-registro congeló. Solo el pre-registro: la comparación
    acta → pre-registro prueba transcripción exacta, no reconcilia dos fuentes."""
    if not RUTA_PREREGISTRO.exists():
        return [], "el pre-registro no existe"
    datos, error = _json(RUTA_PREREGISTRO)
    if error:
        return [], error
    candidatos = [{"candidate_id": a.get("candidate_id"), "detalle": a.get("motivo")}
                  for a in (datos.get("adjudicaciones") or [])
                  if isinstance(a, dict) and a.get("candidate_id")]
    return candidatos, ("sin adjudicaciones con `candidate_id`: el acta congelada no declara "
                        "ninguna" if not candidatos else f"{len(candidatos)} adjudicaciones")


def de_reportes_de_implementacion() -> tuple[list[dict], str]:
    if not RUTA_DEFECTOS.exists():
        return [], "no existe la consolidación de defectos descubiertos"
    datos, error = _json(RUTA_DEFECTOS)
    if error:
        return [], error
    candidatos = [{"candidate_id": c.get("candidate_id"), "detalle": c.get("descripcion")}
                  for c in (datos.get("candidatos") or [])]
    return candidatos, f"{len(candidatos)} candidatos"


FUENTES = (
    ("anomalias_del_runner", de_anomalias_del_runner),
    ("fallos_de_fixtures", de_fallos_de_fixtures),
    ("adjudicaciones_de_cohorte", de_adjudicaciones_de_cohorte),
    ("reportes_de_implementacion", de_reportes_de_implementacion),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--salida", metavar="<ruta>", default=None,
                        help="dónde escribir el JSON derivado; por omisión, stdout")
    args = parser.parse_args()

    fuentes: dict[str, list[dict]] = {}
    notas: dict[str, str] = {}
    for nombre, derivar in FUENTES:
        candidatos, nota = derivar()
        fuentes[nombre] = candidatos
        notas[nombre] = nota

    manifest, error = _json(RUTA_MANIFEST)
    if error:
        print(f"FALLA  manifest de despachos: {error}", file=sys.stderr)
        return 1
    despachos = [{"task": d.get("task"), "actor": d.get("actor"), "intento": d.get("intento")}
                 for d in (manifest.get("despachos") or [])]

    documento = {
        "que_declara": "El conjunto de candidatos derivado de las cuatro fuentes cerradas y las "
                       "ternas del manifest de despachos. Derivado, no escrito: lo produce "
                       "`scripts/derivar-fuentes-ledger.py` leyendo las fuentes reales, y se "
                       "regenera cuando cualquiera cambia.",
        "x-estado-de-cada-fuente": notas,
        "fuentes": fuentes,
        "despachos": despachos,
    }
    texto = json.dumps(documento, indent=2, ensure_ascii=False) + "\n"
    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")
        total = sum(len(v) for v in fuentes.values())
        print(f"OK  {args.salida} · {total} candidatos en 4 fuentes · {len(despachos)} despachos")
        for nombre, nota in notas.items():
            print(f"    {nombre}: {len(fuentes[nombre])} — {nota}")
    else:
        sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
