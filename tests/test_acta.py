"""Casos del acta sellada: la lectura por ref y el destino del CLI.

Nada de lo que hay acá recalcula evidencia ni lanza subprocesos: los casos son deterministas y
rápidos.

**Dónde corre cada uno, porque no es lo mismo.** El del ref usa un repositorio temporal propio y no
consulta el `migracion/acta-dual` real, así que no puede alterar el `.git` que comparten los
worktrees. El del destino corre casi entero en un directorio temporal, pero **dos de sus destinos
apuntan al `tests/` real a propósito**: son los que comprueban que el CLI rechaza escribir dentro
del corpus, y contra un `tests/` simulado no probarían esa propiedad. Esos dos se borran en un
`finally`.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import hashlib

from tests.migracion import (ENCODING, EVIDENCE_END, EVIDENCE_START, REPORT_BLOB, REPORT_TAG,
                             ROOT, _git, main, read_report)


Case = Tuple[str, str, Callable[[Optional[object]], None]]

# Un acta minima pero BIEN FORMADA: `_parsear` la acepta. Es lo que la vuelve un senuelo util —si
# `read_report` tuviera fallback a la ruta, encontraria esto y retornaria en vez de levantar.
SENUELO = "prosa previa\n{0}\n```json\n{{\"senuelo\": true}}\n```\n{1}\nprosa posterior\n".format(
    EVIDENCE_START, EVIDENCE_END)

_IDENTIDAD = ["-c", "user.email=acta@test", "-c", "user.name=acta"]


def _sembrar_blob_del_acta(raiz: Path) -> str:
    """Escribe en `raiz` el mismo blob que el acta sellada, y devuelve su OID."""
    contenido = _git(ROOT, ["cat-file", "blob", REPORT_TAG], text=False)
    assert contenido.returncode == 0, contenido.stderr
    sembrado = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=raiz,
                              input=contenido.stdout, capture_output=True)
    assert sembrado.returncode == 0, sembrado.stderr
    return sembrado.stdout.decode(ENCODING).strip()


def _crear_tag_hacia_otro_blob(raiz: Path, ref: str) -> None:
    """Deja en `raiz` un tag ANOTADO que alcanza un blob que no es el del acta."""
    ajeno = raiz / "ajeno.txt"
    ajeno.write_text("no soy el acta\n", encoding=ENCODING)
    blob = _git(raiz, ["hash-object", "-w", str(ajeno)])
    assert blob.returncode == 0, blob.stderr
    creado = _git(raiz, _IDENTIDAD + ["tag", "-a", "-m", "ajeno", ref, blob.stdout.strip()])
    assert creado.returncode == 0, creado.stderr


def _exigir_que_levante(ref: str, raiz: Path, fragmento: str, etiqueta: str) -> None:
    try:
        read_report(ref, raiz)
    except AssertionError as error:
        assert fragmento in str(error), "{0}: levanto por otra causa: {1}".format(etiqueta, error)
        return
    raise AssertionError("{0}: la lectura no levanto".format(etiqueta))


def test_acta_ref_invalido(_context: Optional[object]) -> None:
    """La lectura sale del tag y solo del tag, y el senuelo lo vuelve observable.

    El caso es NEGATIVO: pasa cuando `read_report` falla. Con el senuelo en la ruta retirada, un
    `read_report` con fallback retornaria en vez de levantar y este caso se pondria ROJO, que es
    como se delata. Sin el senuelo no discriminaria nada: con la ruta vacia el fallback falla por
    `FileNotFoundError` en vez de por el ref, la lectura levanta igual y el caso queda verde.
    """
    with tempfile.TemporaryDirectory(prefix="acta-ref-invalido-") as temporal:
        raiz = Path(temporal)
        iniciado = _git(raiz, ["init", "-q"])
        assert iniciado.returncode == 0, iniciado.stderr

        # 1 — ref ausente
        _exigir_que_levante("refs/tags/no-existe", raiz, "is absent", "ref ausente")

        # 2 — ref anotado hacia otro blob: cae por IDENTIDAD, no por ausencia
        _crear_tag_hacia_otro_blob(raiz, "refs/tags/acta-ajena")
        _exigir_que_levante("refs/tags/acta-ajena", raiz,
                            "does not reach the sealed blob", "ref hacia otro blob")

        # 3 — forma: un tag LIGERO al blob correcto, y el SHA del blob a pelo. Los dos alcanzan
        # el objeto esperado, asi que solo los distingue el tipo del ref: `rev-parse <ref>^{}`
        # desreferencia cualquier cosa y no discrimina la anotacion.
        oid = _sembrar_blob_del_acta(raiz)
        assert oid == REPORT_BLOB, "el blob sembrado no es el del acta: " + oid
        ligero = _git(raiz, ["tag", "acta-ligera", oid])
        assert ligero.returncode == 0, ligero.stderr
        _exigir_que_levante("acta-ligera", raiz, "is not an annotated tag", "tag ligero al blob correcto")
        _exigir_que_levante(oid, raiz, "is not an annotated tag", "SHA del blob a pelo")

        # 4 — senuelo: un acta legitima en la ruta retirada NO rescata la lectura
        destino = raiz / "tests" / "reporte-migracion.md"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(SENUELO, encoding=ENCODING)
        assert destino.is_file(), "el senuelo no quedo escrito: la rama no probaria nada"
        _exigir_que_levante("refs/tags/no-existe", raiz, "is absent", "senuelo con ref ausente")
        _exigir_que_levante("refs/tags/acta-ajena", raiz,
                            "does not reach the sealed blob", "senuelo con ref hacia otro blob")


def _exigir_rechazo(argv: List[str], excepciones, fragmento: str, etiqueta: str) -> None:
    """Exige que el CLI rechace `argv`. El rechazo propaga y el entrypoint sale distinto de cero."""
    try:
        main(argv)
    except excepciones as error:
        assert fragmento in str(error), "{0}: rechazo por otra causa: {1}".format(etiqueta, error)
        return
    raise AssertionError("{0}: el CLI no rechazo".format(etiqueta))


def test_write_report_destino(_context: Optional[object]) -> None:
    """El CLI exige destino, lo rechaza donde corresponde, nunca trunca, y escribe el acta exacta.

    Los destinos bajo `tests/` se borran SIEMPRE al salir, y no por prolijidad. Este caso se ejerce
    con `_rechazar_bajo_tests` neutralizado para comprobar que ese rechazo discrimina; sin el
    rechazo el CLI escribe ahi el acta entera, y un `git add -A` posterior la devolveria al corpus
    del que acaba de salir. Medido: aparecio un `tests/x.md` de 870 KB con el sha256 exacto del blob.
    """
    bajo_tests = [ROOT / "tests" / "x.md", ROOT / "scripts" / ".." / "tests" / "y.md"]
    try:
        _ejercer_destinos(bajo_tests)
    finally:
        for residuo in bajo_tests:
            residuo.resolve().unlink(missing_ok=True)


def _ejercer_destinos(bajo_tests: List[Path]) -> None:
    with tempfile.TemporaryDirectory(prefix="write-report-destino-") as temporal:
        fuera = Path(temporal)

        # (a) — sin destino explicito no escribe nada
        _exigir_rechazo(["--write-report", "--from-acta"], SystemExit, "2", "sin --output")

        # (b) — destino directo bajo tests/
        _exigir_rechazo(["--write-report", "--from-acta", "--output", str(bajo_tests[0])],
                        AssertionError, "falls under tests/", "destino bajo tests/")

        # (b) — escape lexical: NO empieza por tests/ y contiene "..", pero RESUELVE dentro.
        # Una comparacion lexical sobre el path crudo lo dejaria pasar; sobre el resuelto lo caza.
        escape = bajo_tests[1]
        assert not escape.is_relative_to(ROOT / "tests"), "el escape ya era lexicalmente interno"
        assert escape.resolve().is_relative_to(ROOT / "tests"), "el escape no resuelve dentro"
        _exigir_rechazo(["--write-report", "--from-acta", "--output", str(escape)],
                        AssertionError, "falls under tests/", "escape por ../tests/")

        # (d) — symlink. Las TRES condiciones: fuera de tests/, roto, y padre del destino existente.
        # Con cualquiera ausente el mutante de `_rechazar_symlink` seria equivalente.
        roto = fuera / "destino-inexistente.md"
        enlace = fuera / "enlace.md"
        enlace.symlink_to(roto)
        assert enlace.is_symlink() and not roto.exists() and fuera.is_dir(), "precondiciones del enlace"
        _exigir_rechazo(["--write-report", "--from-acta", "--output", str(enlace)],
                        AssertionError, "is a symlink", "symlink roto fuera de tests/")

        # (d) — destino existente: rechaza y NO trunca
        ya = fuera / "existente.md"
        ya.write_text("contenido previo", encoding=ENCODING)
        _exigir_rechazo(["--write-report", "--from-acta", "--output", str(ya)],
                        FileExistsError, "File exists", "destino ya existente")
        assert ya.read_text(encoding=ENCODING) == "contenido previo", "el rechazo truncó el destino"

        # (c) — el positivo: re-materializa el acta desde el tag y sale el blob EXACTO.
        # Re-materializa y no regenera: regenerar exige un arnes retirado el 2026-08-25.
        destino = fuera / "re-materializada.md"
        assert main(["--write-report", "--from-acta", "--output", str(destino)]) == 0
        blob = _git(ROOT, ["cat-file", "blob", REPORT_TAG], text=False)
        assert blob.returncode == 0, blob.stderr
        escrito = hashlib.sha256(destino.read_bytes()).hexdigest()
        assert escrito == hashlib.sha256(blob.stdout).hexdigest(), (
            "lo escrito no es el acta sellada: " + escrito)


CASOS: List[Case] = [
    ("acta-ref-invalido", "acta-sellada", test_acta_ref_invalido),
    ("write-report-destino", "acta-sellada", test_write_report_destino),
]
