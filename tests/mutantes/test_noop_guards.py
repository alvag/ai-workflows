"""Un mutante no-op ejecutable por cada guarda de la tabla de firmas."""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from tests.casos.test_firmas import FIRMAS, Firma, _argumentos_genericos


ENCODING = "utf-8"
Case = Tuple[str, str, Callable[[Optional[object]], None]]


def _mutate_main(firma: Firma, destination: Path) -> Firma:
    scripts = destination / "scripts"
    shutil.copytree(firma.archivo.parent, scripts)
    target = scripts / firma.archivo.name
    source = target.read_text(encoding=ENCODING)
    tree = ast.parse(source, filename=str(target))
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(functions) != 1 or not functions[0].body:
        raise AssertionError("main no es mutable de forma univoca: " + firma.nombre)
    original = functions[0]
    lines = source.splitlines(keepends=True)
    lines[original.body[0].lineno - 1:original.end_lineno] = ["    return 0\n"]
    mutated_source = "".join(lines)
    mutated_tree = ast.parse(mutated_source, filename=str(target))
    mutated = next(node for node in mutated_tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "main")
    assert ast.dump(original.args) == ast.dump(mutated.args)
    assert ast.dump(original.returns) == ast.dump(mutated.returns)
    assert len(mutated.body) == 1 and isinstance(mutated.body[0], ast.Return)
    compile(mutated_source, str(target), "exec", dont_inherit=True)
    target.write_text(mutated_source, encoding=ENCODING)
    return replace(firma, archivo=target)


def _assert_arity_behavior(firma: Firma, cwd: Path) -> None:
    arguments = _argumentos_genericos(firma)
    missing = arguments[:firma.aridad - 1]
    result = subprocess.run(
        [sys.executable, str(firma.archivo)] + missing,
        cwd=str(cwd), capture_output=True, text=True, encoding=ENCODING, check=False,
    )
    assert result.returncode == firma.codigo_aridad
    assert result.stdout == ""
    assert result.stderr == firma.mensaje_aridad + "\n"


def _kill_noop_mutant(firma: Firma) -> None:
    with tempfile.TemporaryDirectory(prefix="mutante-v24-") as temporary:
        root = Path(temporary)
        mutant = _mutate_main(firma, root)
        try:
            _assert_arity_behavior(mutant, root)
        except AssertionError:
            return
        raise AssertionError("el mutante no-op sobrevivio: " + firma.nombre)


def _make_test(firma: Firma) -> Callable[[Optional[object]], None]:
    def test_mutant(_context: Optional[object]) -> None:
        """El no-op conserva la firma pero rompe el comportamiento de invocacion."""
        _kill_noop_mutant(firma)

    test_mutant.__doc__ = "Mutante no-op conductual de {0}.".format(firma.nombre)
    return test_mutant


CASOS: List[Case] = []
for index, inventoried_signature in enumerate(FIRMAS, 1):
    test = _make_test(inventoried_signature)
    test.__name__ = "test_noop_guard_{0:02d}".format(index)
    globals()[test.__name__] = test
    CASOS.append(("mutante-v24:" + inventoried_signature.nombre,
                  "mutantes-noop-v24", test))
