"""Corpus de vectores de las huellas del ledger, corrido contra la ruta productiva.

El corpus vive **fuera** del código que lo consume y sus digests se derivaron a mano desde la
definición normativa, sin importar ni ejecutar el productor. Este módulo lo carga e invoca el
ejecutable real, y agrega lo que el corpus por sí solo no puede probar: que sustituir la función de
digest por una constante pone el runner completo en rojo. Seleccionar un caso *llamado* «mutante» no
sustituye nada y admite una implementación que devuelva el código esperado solo para ese nombre.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable, List, Optional, Tuple

RAIZ = Path(__file__).resolve().parents[2]
EJECUTABLE = RAIZ / "skills" / "sdd-flow" / "scripts" / "huellas-secuencia.py"
CORPUS = RAIZ / "tests" / "vectores-huellas"
Case = Tuple[str, str, Callable[[Optional[object]], None]]
GRUPO = "huellas-secuencia"


def _productor():
    especificacion = importlib.util.spec_from_file_location("huellas_secuencia_bajo_prueba",
                                                            EJECUTABLE)
    if especificacion is None or especificacion.loader is None:
        raise AssertionError(f"no se pudo cargar {EJECUTABLE}")
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def _manifiesto() -> List[dict]:
    return _productor()._manifiesto(str(CORPUS))


def test_corpus_completo(_ctx: Optional[object] = None) -> None:
    """Todos los vectores del corpus rinden contra la ruta productiva."""
    codigo, lineas = _productor().verificar_vectores(str(CORPUS), None)
    fallas = [l for l in lineas if l.startswith("FALLA")]
    assert codigo == 0, "vectores que no rinden: " + "; ".join(fallas)
    declarados = (CORPUS / "obligatorios.txt").read_text(encoding="utf-8").split("\n")
    esperados = len([d for d in declarados if d.strip() and not d.startswith("#")])
    # Contra la matriz cerrada declarada, no contra un número transcrito que envejece solo.
    assert len(lineas) == esperados, f"el corpus corrió {len(lineas)} de {esperados} vectores"


def test_manifiesto_declara_su_procedencia(_ctx: Optional[object] = None) -> None:
    """Cada vector con digest declara el mecanismo independiente con el que se obtuvo."""
    sin_mecanismo = [f["id"] for f in _manifiesto()
                     if f["digest"] != "-" and "sin importar el productor" not in f["mecanismo"]]
    assert not sin_mecanismo, f"vectores con digest y sin mecanismo declarado: {sin_mecanismo}"


def test_seleccion_vacia_no_es_exito(_ctx: Optional[object] = None) -> None:
    """Un selector que no casa nada da «no medible», no un verde por vacuidad."""
    productor = _productor()
    try:
        productor.verificar_vectores(str(CORPUS), "prefijo-que-no-existe-")
    except productor.NoMedible:
        return
    raise AssertionError("una selección vacía tiene que fallar, no rendir por no tener vectores")


def test_cada_grupo_rinde_por_separado(_ctx: Optional[object] = None) -> None:
    """La selección por prefijo rinde grupo por grupo, que es como el contrato la invoca."""
    productor = _productor()
    prefijos: List[str] = []
    for fila in _manifiesto():
        prefijo = fila["id"].split("-", 1)[0] + "-"
        if prefijo not in prefijos:
            prefijos.append(prefijo)
    assert len(prefijos) >= 7, f"el corpus solo tiene {len(prefijos)} grupos"
    for prefijo in prefijos:
        codigo, lineas = productor.verificar_vectores(str(CORPUS), prefijo)
        fallas = [l for l in lineas if l.startswith("FALLA")]
        assert codigo == 0, f"el grupo {prefijo} no rinde: " + "; ".join(fallas)
        assert lineas, f"el grupo {prefijo} quedó sin vectores seleccionados"


def test_mutante_digest_constante(_ctx: Optional[object] = None) -> None:
    """Sustituir la función de digest por una constante pone el runner **completo** en rojo.

    Es lo que el corpus solo no puede probar: sin este caso, una implementación que devolviera
    siempre el mismo valor pasaría todas las relaciones de igualdad y solo fallaría las de
    diferencia, y ni siquiera eso si el corpus no tuviera ninguna.
    """
    productor = _productor()
    original = productor._digest
    productor._digest = lambda _preimage: "sha256:" + "0" * 64
    try:
        codigo, lineas = productor.verificar_vectores(str(CORPUS), None)
    finally:
        productor._digest = original
    assert codigo != 0, "el runner quedó verde con la función de digest sustituida por una constante"
    fallas = [l for l in lineas if l.startswith("FALLA")]
    assert len(fallas) >= 10, (
        f"con el digest constante solo {len(fallas)} vectores se pusieron rojos; el corpus no "
        "discrimina lo suficiente")


def test_mutante_sin_recorte_de_espacios(_ctx: Optional[object] = None) -> None:
    """Dejar de recortar los espacios finales de un valor mueve la huella de tareas.

    Es el segundo mutante y ataca la canonicalización, no el hash: la clarification aprobada fija que
    la huella de tareas recorta esos espacios y la del delta no, así que una implementación que los
    conservara en las dos rompería la igualdad entre gemelos.
    """
    productor = _productor()
    original = productor._escapar
    productor._escapar = lambda valor: valor.replace("\\", "\\\\").replace("\t", "\\t")
    try:
        codigo, _lineas = productor.verificar_vectores(str(CORPUS), "tasks-")
    finally:
        productor._escapar = original
    assert codigo != 0, "el corpus quedó verde sin recortar los espacios finales de cada valor"


# El barrido **deriva** sus objetivos del propio lector con el AST: toda `raise LecturaInvalida` y
# todo `faltas.append` es un sitio explícito de diagnóstico. Lo que enumera y lo que no, en el
# docstring de `_sitios_de_guarda`: no es «las guardas del lector», es sus rechazos declarados. Una lista escrita a mano se lee como cobertura y no lo
# es — la anterior mutaba ocho anclas de cincuenta y tres sitios, y las que no nombraba quedaban
# verdes por vacuidad sin que nada lo dijera.
#
# Y el veredicto es la **salida completa**, no el código de salida: si dos guardas disparan sobre el
# mismo vector, anular una deja la otra y el código no cambia, así que una guarda ejercitada se
# contaba como no ejercitada. Comparar la salida discrimina por causa.
SOBREVIVIENTES_DECLARADOS = {
    # Del dialecto del lector: el corpus alimenta documentos bien formados para ejercitar el
    # esquema, así que la forma del dialecto queda sin ejercitar. Fallan cerrado en `leer()`, antes
    # de que se calcule ninguna huella, y son alcanzables: lo que falta es el vector, no la guarda.
    "sangría con tabulador": "dialecto",
    "comilla sin escapar": "dialecto",
    "construcción no admitida": "dialecto",
    "entrada de mapa en línea sin clave": "dialecto",
    "clave repetida en un mapa en línea": "dialecto",
    "colección en línea anidada": "dialecto",
    "colección en línea mal cerrada": "dialecto",
    "sangría inesperada en una lista": "dialecto",
    "sangría inesperada en un mapa": "dialecto",
    "línea sin clave, línea": "dialecto",
    "clave vacía, línea": "dialecto",
    "marcador de documento": "dialecto",
    "el documento no es un mapa no vacío": "dialecto",
    # Alcanzable por la API de `validar()` y **no** por la ruta productiva: la discriminación
    # recibo/ledger del ejecutable exige `tasks_fingerprint` **y** `blocks`, así que un recibo al que
    # le falte una se detiene antes, en la ambigüedad, y ningún vector del corpus llega hasta acá.
    # Se declaró «inalcanzable» a secas, que afirmaba de más: lo es para el corpus, no para la API.
    "recibo: clave ausente bajo el esquema legado": "api-interna",
    # Guardas de la API interna: `validar` solo la invoca el ejecutable, siempre con un nombre de
    # esquema del enum y con el mapa que `leer` ya devolvió. No hay entrada del corpus que las alcance.
    "la entrada del lector no es texto": "api-interna",
    # `_leer` siempre devuelve `str`, así que ninguna entrada del corpus puede llegar acá con otra
    # cosa: solo un llamador directo de `leer()`. Estaba declarada como «dialecto», que afirmaba que
    # existía un vector posible, y no lo hay.
    "esquema desconocido": "api-interna",
    "el documento a validar no es un mapa": "api-interna",
}


def _sitios_de_guarda(fuente: str):
    """Los **sitios explícitos de diagnóstico** del lector, derivados del árbol sintáctico.

    El alcance está acotado a propósito y hay que decirlo, porque el número que produce este barrido
    invita a leerlo como «las guardas del lector» a secas: enumera `raise LecturaInvalida` y
    `faltas.append`, que son los rechazos que se nombran. **No** ve una guarda semántica escrita como
    un `break`, un `return` o la elección de una rama, y por construcción no puede ver una guarda
    **ausente**. Es cobertura de los rechazos declarados, no de la corrección del lector.
    """
    import ast
    sitios = []
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Raise):
            invocada = getattr(getattr(nodo.exc, "func", None), "id", None)
            if invocada == "LecturaInvalida":
                sitios.append((nodo.lineno, nodo.end_lineno))
        elif isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Call):
            f = nodo.value.func
            if (isinstance(f, ast.Attribute) and f.attr == "append"
                    and isinstance(f.value, ast.Name) and f.value.id == "faltas"):
                sitios.append((nodo.lineno, nodo.end_lineno))
    return sorted(sitios)


def test_cada_guarda_del_lector_la_caza_el_corpus(_ctx: Optional[object] = None) -> None:
    """Ninguna guarda del lector puede anularse sin que la salida del corpus cambie.

    Las que sobreviven tienen que ser **exactamente** las declaradas, en las dos direcciones: una
    guarda nueva sin vector aparece sola, y una declarada que alguien cubra obliga a sacarla de la
    lista en vez de dejarla como excusa vencida.
    """
    import shutil
    import subprocess
    import tempfile

    lector_real = RAIZ / "skills" / "sdd-flow" / "scripts" / "_ledger.py"
    fuente = lector_real.read_text(encoding="utf-8")
    lineas = fuente.split("\n")
    sitios = _sitios_de_guarda(fuente)
    assert len(sitios) >= 50, f"solo se derivaron {len(sitios)} sitios de guarda del lector"

    # Cada fragmento declarado tiene que nombrar **un** sitio: si deja de ser único o desaparece,
    # la lista está describiendo un lector que ya no existe.
    # El texto de un sitio es su **sentencia entera**, no su primera línea: partir un `raise` en
    # dos por longitud dejaba el mensaje fuera de la clave y el fragmento declarado casaba cero
    # sitios. La clave no puede depender de cómo se formateó el código que vigila.
    textos = [" ".join(l.strip() for l in lineas[ini - 1:fin]) for ini, fin in sitios]
    for fragmento in SOBREVIVIENTES_DECLARADOS:
        casan = [t for t in textos if fragmento in t]
        assert len(casan) == 1, f"el fragmento declarado {fragmento!r} casa {len(casan)} sitios"

    raiz = tempfile.mkdtemp()
    try:
        shutil.copytree(RAIZ / "skills", Path(raiz) / "skills")
        shutil.copytree(CORPUS, Path(raiz) / "tests" / "vectores-huellas")
        lector = Path(raiz) / "skills" / "sdd-flow" / "scripts" / "_ledger.py"
        orden = ["python3", "skills/sdd-flow/scripts/huellas-secuencia.py", "verificar-vectores",
                 "--corpus", "tests/vectores-huellas"]
        base = subprocess.run(orden, cwd=raiz, capture_output=True)
        assert base.returncode == 0, "el corpus no está verde antes de mutar nada"

        sobreviven = []
        for (ini, fin), texto in zip(sitios, textos):
            sangria = len(lineas[ini - 1]) - len(lineas[ini - 1].lstrip())
            lector.write_text("\n".join(lineas[:ini - 1] + [" " * sangria + "pass"] + lineas[fin:]),
                              encoding="utf-8")
            if subprocess.run(orden, cwd=raiz, capture_output=True).stdout == base.stdout:
                sobreviven.append(texto)
        lector.write_text(fuente, encoding="utf-8")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    declarados = set(SOBREVIVIENTES_DECLARADOS)
    sin_declarar = [t for t in sobreviven if not any(f in t for f in declarados)]
    ya_cubiertos = [f for f in declarados if not any(f in t for t in sobreviven)]
    assert not sin_declarar, ("guardas que ningún vector ejercita y que nadie declaró: "
                              + "; ".join(sin_declarar))
    assert not ya_cubiertos, ("declaradas como no ejercitadas pero el corpus ya las caza; sacarlas "
                              "de la lista: " + "; ".join(ya_cubiertos))


def test_infraestructura_del_referenciado_da_corpus_incompleto(_ctx: Optional[object] = None) -> None:
    """Si falla la entrada del vector **referenciado**, el runner da 3 y no 1.

    Un vector que no se puede correr no es un vector que no rinde, y la rama del referenciado es la
    que no tenía cómo ejercitarse: no puede ser un vector del corpus, porque un corpus incompleto lo
    pone en rojo por definición. Sin este caso, la corrección que propaga el centinela quedaba
    escrita y sin nadie que la mirara.
    """
    import shutil
    import subprocess
    import tempfile

    productor = _productor()
    # Se elige la pareja desde el manifiesto y no por su nombre: un identificador transcrito envejece
    # con el corpus y dejaría el caso apuntando a un vector que ya no existe.
    por_id = {f["id"]: f for f in _manifiesto()}
    pareja = next((f, por_id[f["relacion"].split(":", 1)[1]])
                  for f in por_id.values()
                  if f["relacion"].startswith(("igual-a:", "difiere-de:"))
                  and f["entrada"] != por_id[f["relacion"].split(":", 1)[1]]["entrada"])
    referencia, referenciado = pareja

    raiz = tempfile.mkdtemp()
    try:
        corpus = Path(raiz) / "vectores-huellas"
        shutil.copytree(CORPUS, corpus)
        (corpus / referenciado["entrada"]).unlink()
        completo = subprocess.run(
            ["python3", str(EJECUTABLE), "verificar-vectores", "--corpus", str(corpus),
             "--caso", referencia["id"]], capture_output=True, text=True)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    assert completo.returncode == 3, (
        f"con la entrada de {referenciado['id']} ausente el runner devolvió "
        f"{completo.returncode}, y el contrato promete 3 para corpus incompleto")
    assert referenciado["id"] in (completo.stdout + completo.stderr), (
        "el runner no nombra el vector referenciado cuya infraestructura falló")


PROMOCION = RAIZ / "skills" / "sdd-flow" / "scripts" / "promocion-tasks-ready.py"
# El hash canónico del bloque de abajo, calculado por `contrato-cadena.py` sobre sus bytes. Un valor
# distinto no es «otro hash»: es un contrato cuya huella declarada no identifica a su contenido.
HASH_CANONICO = "bd3a154d6c9e3149aa6797ce77c5ceb975c0295a3a2eacc0f257b6b28021b7d8"


def _plan_con_hash(destino: Path, valor: str) -> Path:
    """Un plan que llega al gate de congelamiento, con el `hash` que se le indique."""
    (destino / "plan.md").write_text(
        "---\nstatus: planned\ncomplexity: normal\ncontract_procedure: measured-v1\n---\n"
        "contenido\n## v1\n\n`hash_previo:` · `hash: " + valor + "`\n", encoding="utf-8")
    (destino / "log.md").write_text(
        "- `paso: congelar` · `actor: conductor` · `timestamp: 2026-08-24T12:00:00Z`\n",
        encoding="utf-8")
    return destino / "plan.md"


def test_congelar_exige_una_cadena_valida(_ctx: Optional[object] = None) -> None:
    """Congelar un contrato cuyo `hash` no corresponde a sus bytes falla cerrado y no muta el plan.

    Es el **control positivo** de esa validación, y sin él la guarda entra salteada: revertirla dejaba
    la suite entera, los veinte modos y el corpus en verde mientras el defecto volvía completo. Un
    plan con el hash canónico pasa con y sin validación, así que la mitad que discrimina es esta.
    """
    import shutil
    import subprocess
    import tempfile

    for valor, codigo, claves, etiqueta in ((HASH_CANONICO, 0, 2, "canónico"),
                                            ("a" * 64, 1, 0, "que no corresponde")):
        arena = Path(tempfile.mkdtemp())
        try:
            plan = _plan_con_hash(arena, valor)
            corrida = subprocess.run(
                ["python3", str(PROMOCION), str(plan), str(arena / "log.md")],
                capture_output=True, text=True)
            texto = plan.read_text(encoding="utf-8")
            congeladas = [l for l in texto.split("\n") if l.startswith("contract_frozen")]
            assert corrida.returncode == codigo, (
                f"con un hash {etiqueta} se esperaba {codigo} y vino {corrida.returncode}: "
                + (corrida.stdout + corrida.stderr).strip()[:120])
            assert len(congeladas) == claves, (
                f"con un hash {etiqueta} se esperaban {claves} claves congeladas y hay "
                f"{len(congeladas)}")
            if codigo != 0:
                # El plan queda **intacto**: una promoción que no congela tampoco promueve.
                assert "status: planned" in texto, "el plan se promovió pese a no congelar"
                assert "recalculado" in corrida.stderr, (
                    "el diagnóstico del validador no llega al conductor: "
                    + corrida.stderr.strip()[:100])
        finally:
            shutil.rmtree(arena, ignore_errors=True)


CASOS: List[Case] = [
    ("huellas:corpus-completo", GRUPO, test_corpus_completo),
    ("huellas:procedencia-del-manifiesto", GRUPO, test_manifiesto_declara_su_procedencia),
    ("huellas:seleccion-vacia", GRUPO, test_seleccion_vacia_no_es_exito),
    ("huellas:mutante-digest-constante", GRUPO, test_mutante_digest_constante),
    ("huellas:mutante-sin-recorte", GRUPO, test_mutante_sin_recorte_de_espacios),
    ("huellas:grupos-del-corpus", GRUPO, test_cada_grupo_rinde_por_separado),
    ("huellas:barrido-de-guardas", GRUPO, test_cada_guarda_del_lector_la_caza_el_corpus),
    ("huellas:infra-del-referenciado", GRUPO, test_infraestructura_del_referenciado_da_corpus_incompleto),
    ("huellas:congelar-exige-cadena", GRUPO, test_congelar_exige_una_cadena_valida),
]
