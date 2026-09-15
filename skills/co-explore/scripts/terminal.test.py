#!/usr/bin/env python3
"""Arnes externo por mutacion para el adaptador de terminales."""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


RAIZ = Path(__file__).resolve().parent
ORIGINAL = RAIZ / "terminal.py"
# La unidad que se copia es la SEDE de la skill, no `scripts/`: hay autotests que cotejan el
# adaptador contra `reference.md`, su hermano. Copiando solo `scripts/` ese archivo no viaja, el
# autotest muere con FileNotFoundError y el arnes lee ese exit 1 como si el mutante hubiera
# enrojecido la fila. Un rojo por la razon equivocada acredita cobertura que no existe.
SEDE = RAIZ.parent


@dataclass(frozen=True)
class Mutante:
    nombre: str
    fila: str
    autotest: str | None
    antes: str | None = None
    despues: str | None = None


# Los nombres conservan cada alternativa declarada en "Mutantes de v1".
MUTANTES = (
    Mutante("quitar-caso-plataforma", "V1", None),
    Mutante("consentimiento-opcional", "V2", None),
    Mutante("verbo-sin-fila", "V3", None),
    Mutante("ausencia-oferta", "V4", "retomado", 'ofertas=0, causa=causa, recuperado=recuperado,', 'ofertas=1, causa=causa, recuperado=recuperado,'),
    Mutante("rancia-resuelve", "V4", "retomado", '    if estado != "resuelve":', '    if estado in ("ausente", "inconsultable"):'),
    Mutante("degradar-sin-causa", "V4", "retomado", 'causa=causa, recuperado=recuperado,', 'causa=None, recuperado=recuperado,'),
    Mutante("adopcion-ajena", "V4", "retomado", '        if propietario.get("sesion") != args.sesion and _en_vuelo(corrida) and not args.consentimiento:', '        if False:'),
    Mutante("esperar-antes-segundo-lanzar", "V5", "orden", '        pendientes = sorted({x.get("panel") for x in entradas if x.get("efecto") == "crear"} - lanzados)', '        pendientes = []'),
    Mutante("segundo-split-conductor", "V6", "layout", '["herdr", "pane", "split", args.desde', '["herdr", "pane", "split", "conductor"'),
    Mutante("nombre-solicitado", "V7", "renombrar", "leido = _nombre(dato)", "leido = None"),
    Mutante("omision-aplicada", "V8", "omision", 'aplicado=False, nombre_leido=leido', 'aplicado=True, nombre_leido=leido'),
    Mutante("motivo-omision-vacio", "V8", "omision", 'return emitir(0, "renombrar", "afirmativo", "orca",', 'return emitir(1, "renombrar", "adverso", "orca",'),
    Mutante("perfil-sin-campo-invocacion", "V9", "perfil", 'flags = [familia, "--model", str(perfil["modelo"]["valor"])]', 'flags = [familia]'),
    Mutante("efectivo-observable", "V9", "perfil", 'return flags + (["-c", "model_reasoning_effort=" + esfuerzo]', 'return [familia, "--effective-observable"] + (["-c", "model_reasoning_effort=" + esfuerzo]'),
    Mutante("encargo-inline", "V10", "encargo", "len(\" \".join(comando).encode()) < 4096", "len(\" \".join(comando).encode()) < 0"),
    Mutante("firma-pipeline-hermano", "V11", "cosecha", "args.indice, args.detalle, args.familia", "args.indice, args.base, args.familia"),
    Mutante("reinterpretar-codigo-pipeline", "V11", "cosecha", 'return 0, "validador", pasos[-1] and "", pasos', 'return 1, "validador", pasos[-1] and "", pasos'),
    Mutante("acuse-sin-asentar-lote", "V11", "cosecha", 'for mensaje in lote: _asentar(args.corrida, {"efecto": "buzon"', 'for mensaje in lote[:1]: _asentar(args.corrida, {"efecto": "buzon"'),
    Mutante("worker-sin-clasificacion", "V12", "ciclo", '"clasificacion":"un-solo-uso"', '"clasificacion":""'),
    Mutante("cerrar-conductor", "V12", "ciclo", '["orca", "terminal", "close", "--terminal", args.panel, "--json"]', '["orca", "terminal", "close", "--terminal", "conductor", "--json"]'),
    # Nacidos de la revision del PR #267. Ligan cada arreglo a la prueba que lo protege.
    Mutante("cese-por-codigo-de-release", "V14", "ciclo",
            'if estado_terminal != "released":', 'if False:'),
    Mutante("cierre-no-asentado", "V12", "ciclo",
            '\n    if acreditado and args.corrida:', '\n    if False and args.corrida:'),
    Mutante("terminalidad-por-existencia", "V18", "estados",
            'if presente and cierre:', 'if presente:'),
    Mutante("retoma-lee-json", "V4", "retomado",
            'transporte = _bloque_retomado(args.retomar, "transporte")', 'transporte = _leer_json(args.retomar).get("transporte")'),
    # `lanzar-conductor` se retiro tras medir que ninguna superficie de Orca sostiene el acuse
    # (Parte 37). Lo que queda que proteger no es una comprobacion sino el rechazo mismo: que no
    # transfiera, y que no consulte —consultar insinuaria que alguna respuesta podria cambiarlo—.
    Mutante("transfiere-igual", "V13", "mudanza",
            'return emitir(1, "lanzar-conductor", "adverso", args.plataforma, causa="mecanica-no-obtenida",',
            'return emitir(0, "lanzar-conductor", "afirmativo", args.plataforma, causa="mecanica-no-obtenida",'),
    Mutante("conductor-nulo-sin-declarar", "V13", "mudanza",
            '"conductor": "declarado-en-ledger-local" if vigente else "no-registrado"', '"conductor": "declarado-en-ledger-local"'),
    Mutante("ledger-local-como-autoridad", "V13", "mudanza",
            '"conductor": "declarado-en-ledger-local" if vigente', '"conductor": "ledger" if vigente'),
    Mutante("ledger-ilegible-revienta", "V13", "mudanza",
            '            except json.JSONDecodeError as error:', '            except ZeroDivisionError as error:'),
    Mutante("linea-no-objeto-pasa", "V13", "mudanza",
            '            if not isinstance(dato, dict):', '            if False:'),
    # Misma mutacion que `ledger-ilegible-revienta`, adjudicada por OTRO autotest: eso es lo que
    # prueba que el lector alcanza a un segundo consumidor real. `cosechar` no lo es —no llama a
    # `_ledger`—, y usarlo daba una asercion vacua.
    Mutante("lector-no-alcanza-la-retoma", "V4", "retomado",
            'raise LedgerIlegible("linea %d: %s" % (numero, error)) from error',
            'entradas.append({}) if False else None'),
    Mutante("consulta-la-plataforma", "V13", "mudanza",
            '    vigente = _conductor_vigente(_ledger(args.corrida))',
            '    _consultar(["orca", "orchestration", "worker-show", "--dispatch", str(args.dispatch), "--json"])\n    vigente = _conductor_vigente(_ledger(args.corrida))'),
    Mutante("fallback-cese-no-comprobable", "V14", "cese", "acreditado = medido and not residuales and args.modo == \"liquidar\"", "acreditado = args.modo == \"liquidar\""),
    Mutante("residuales-no-enumerados", "V14", "cese", 'cese_acreditado=acreditado, clasificacion="un-solo-uso", residuales_propios=len(residuales), reutilizacion="sin-reuso", metodo="pane-close"', 'cese_acreditado=True, clasificacion="un-solo-uso", residuales_propios=len(residuales), reutilizacion="sin-reuso", metodo="pane-close"'),
    Mutante("ablandar-afirmacion-permisos", "V15", None), Mutante("omitir-hecho-permisos", "V15", None),
    Mutante("afirmacion-sin-evidencia", "V16", None), Mutante("divergencia-sin-evidencia", "V17", None),
    Mutante("bloqueado-no-acreditado", "V18", "estados", 'estado, autoridad = ("terminado-vivo" if vivo else "terminado"), "artefacto"', 'estado, autoridad = "muerto", "liveness"'),
    Mutante("lifecycle-con-autoridad", "V18", "estados", 'estado, autoridad = "trabajando", "liveness"', 'estado, autoridad = "muerto", "lifecycle"'),
    Mutante("transporte-en-dos-sedes", "V19", None), Mutante("transporte-inventado", "V19", None),
    Mutante("ramas-perfil-distinto", "V20", None),
    Mutante("no-releer-encargo", "V21", "intervencion", "actual = hashlib.sha256(Path(args.encargo).read_bytes()).hexdigest()", "actual = args.hash_encargo"),
    Mutante("sin-hash-encargo-leido", "V21", "intervencion", 'etapa="digest", veredicto="rechazado"', 'etapa="pipeline", veredicto="rechazado"'),
    Mutante("comparar-declarado-consigo", "V21", "intervencion", "if declarado is None or declarado != args.hash_encargo:", "if False:"),
    Mutante("no-observable-no-declarado", "V21", None),
    Mutante("invocacion-cruda-documento", "V22", "determinismo", 'orden=f"worker-{ordinal}"', 'orden=f"worker-{ordinal + 1}"'),
    # recupera BIEN y ademas barre la otra plataforma: cumple la mitad de AC-23 y viola el criterio.
    Mutante("recuperar-invocando-detector", "V23", "persistencia", '    estado, _ = _identidad_registrada(recuperado["plataforma"])', '    estado_identidad("HERDR_PANE_ID", ["herdr", "pane", "list"], _panes)\n    estado, _ = _identidad_registrada(recuperado["plataforma"])'),
    Mutante("oferta-sin-punto", "V24", None), Mutante("consentimiento-sin-digest", "V24", None),
    Mutante("contribuyente-ajeno", "V25", None), Mutante("sedes-origen-distinto", "V25", None),
    Mutante("derivado-sin-modo-falla", "V26", None),
)


def reemplazar_uno(texto: str, antes: str, despues: str) -> str | None:
    if texto.count(antes) != 1:
        return None
    return texto.replace(antes, despues, 1)


def ejecutar(ruta: Path, autotest: str) -> subprocess.CompletedProcess[str]:
    # El adaptador se ejecuta como proceso; este arnes nunca lo importa.
    return subprocess.run(
        [sys.executable, str(ruta), f"--autotest-{autotest}"],
        capture_output=True,
        text=True,
        check=False,
    )


def copia_mutada(mutante: Mutante, temporal: Path) -> Path | None:
    destino = temporal / mutante.nombre
    shutil.copytree(SEDE, destino)
    ruta = destino / "scripts" / "terminal.py"
    texto = ruta.read_text(encoding="utf-8")
    mutado = reemplazar_uno(texto, mutante.antes or "", mutante.despues or "")
    if mutado is None:
        return None
    ruta.write_text(mutado, encoding="utf-8")
    return ruta


def control_propio() -> bool:
    """Un reemplazo ausente debe ser rojo y nunca cobertura."""
    return reemplazar_uno(ORIGINAL.read_text(encoding="utf-8"), "texto-que-no-existe", "x") is None


def traza_determinista(temporal: Path) -> bool:
    """Sombrea PATH y compara las operaciones observables de dos procesos."""
    binario = temporal / "bin"
    binario.mkdir()
    registro = temporal / "traza.jsonl"
    programa = '''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["TERMINAL_TEST_LOG"], "a", encoding="utf-8") as archivo:
    archivo.write(json.dumps([os.path.basename(sys.argv[0])] + args) + "\\n")
if os.path.basename(sys.argv[0]) == "herdr":
    print(json.dumps({"result": {"panes": [{"pane_id": "h"}]}}))
else:
    print(json.dumps({"result": {"terminals": [{"handle": "o"}]}}))
'''
    for nombre in ("herdr", "orca"):
        ruta = binario / nombre
        ruta.write_text(programa, encoding="utf-8")
        ruta.chmod(0o755)
    entorno = os.environ | {
        "PATH": str(binario) + os.pathsep + os.environ["PATH"],
        "TERMINAL_TEST_LOG": str(registro),
        "HERDR_PANE_ID": "h",
        "ORCA_TERMINAL_HANDLE": "o",
    }
    resultados = [subprocess.run([sys.executable, str(ORIGINAL), "detectar"], env=entorno, capture_output=True, text=True) for _ in range(2)]
    filas = [json.loads(linea) for linea in registro.read_text(encoding="utf-8").splitlines()]
    mitad = len(filas) // 2
    return (
        len(filas) == 4
        and filas[:mitad] == filas[mitad:]
        and all(resultado.stdout for resultado in resultados)
        and resultados[0].stdout == resultados[1].stdout
    )


def main() -> int:
    base = [m for m in MUTANTES if m.autotest]
    pendientes = [m for m in MUTANTES if not m.autotest]
    errores: list[str] = []
    aplicados: list[str] = []

    if not control_propio():
        errores.append("control-propio: un mutante no aplicado fue cubierto")
    else:
        print("CONTROL rojo: mutante no aplicado no cuenta como cubierto")

    with tempfile.TemporaryDirectory(prefix="terminal-mutacion-") as nombre:
        temporal = Path(nombre)
        if not traza_determinista(temporal):
            errores.append("traza: PATH sombreado no produjo dos secuencias identicas")
        else:
            print("TRAZA verde: dos procesos registraron la misma secuencia")
        for mutante in base:
            ruta = copia_mutada(mutante, temporal)
            if ruta is None:
                errores.append(f"{mutante.nombre} ({mutante.fila}): no aplicado")
                continue
            resultado = ejecutar(ruta, mutante.autotest or "")
            if resultado.returncode == 0:
                errores.append(f"{mutante.nombre} ({mutante.fila}): no enrojecio {mutante.fila}")
                continue
            aplicados.append(f"{mutante.nombre} -> {mutante.fila}")
            print(f"ROJO {mutante.fila}: {mutante.nombre}")

    for mutante in pendientes:
        print(f"PENDIENTE {mutante.fila}: {mutante.nombre}")
    for error in errores:
        print(f"ERROR: {error}", file=sys.stderr)
    print(f"RESUMEN aplicados={len(aplicados)} pendientes={len(pendientes)} errores={len(errores)}")
    return 0 if not errores else 1


if __name__ == "__main__":
    sys.exit(main())
