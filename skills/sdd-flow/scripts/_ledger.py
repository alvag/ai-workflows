"""Lector dirigido del dialecto del ledger de secuencia y del recibo de partición.

No es un analizador general del formato: reconoce exactamente las construcciones que esos dos
documentos usan y **falla cerrado** ante cualquier otra. La frontera de lo que valida está escrita en
`reference.md` → "La receta de serialización de las huellas" → "La frontera de la validación
dirigida": presencia y forma condicionadas por un campo declarado del propio documento entran;
legalidad de una transición y hechos del mundo quedan fuera.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class LecturaInvalida(Exception):
    """El documento no admite cálculo: forma desconocida, tipo distinto o cardinalidad inválida."""


# El único indicador de escalar de bloque admitido. Los demás cambian qué bytes produce el valor,
# así que aceptarlos en silencio movería el digest sin que nada lo señale.
CHOMPING_ADMITIDO = "|-"
CHOMPING_RECHAZADOS = ("|", "|+", ">", ">-", ">+")

# Cada cutpoint pertenece a **su** máquina: C1-C8 a la de bloques, C8-C12 a la de cierre, y solo C8
# está en las dos porque es el único que permite el handoff. Validar contra el rango completo aceptaba
# `closure-machine/C1` y `block-machine/C12`.
CUTPOINTS_POR_MAQUINA = {
    "block-machine": tuple(f"C{n}" for n in range(1, 9)),
    "closure-machine": tuple(f"C{n}" for n in range(8, 13)),
    "inline-machine": ("inline-active", "inline-ready-to-close", "inline-terminal"),
}
CUTPOINTS_BLOQUE = tuple(f"C{n}" for n in range(1, 13))
CUTPOINTS_INLINE = ("inline-active", "inline-ready-to-close", "inline-terminal")
MAQUINAS = ("block-machine", "closure-machine", "inline-machine")
TERMINALES = ("active", "suspended", "completed", "rolled_back", "abandoned")
HUELLA = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA = re.compile(r"^[0-9a-f]{40}$")


# --------------------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------------------

def _sangria(linea: str) -> int:
    if "\t" in linea[: len(linea) - len(linea.lstrip(" \t"))]:
        raise LecturaInvalida("sangría con tabulador: el dialecto solo admite espacios")
    return len(linea) - len(linea.lstrip(" "))


def _escalar(bruto: str) -> Any:
    valor = bruto.strip()
    if valor == "" or valor == "null" or valor == "~":
        return None
    if valor in ("true", "false"):
        return valor == "true"
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        interior = valor[1:-1]
        if valor[0] in interior:
            raise LecturaInvalida(f"comilla sin escapar dentro de un escalar: {valor}")
        return interior
    if re.fullmatch(r"-?\d+", valor):
        return int(valor)
    if valor.startswith(("[", "{")):
        return _flujo(valor)
    if valor.startswith(("&", "*", "!", "?")):
        raise LecturaInvalida(f"construcción no admitida por el lector dirigido: {valor}")
    return valor


def _flujo(bruto: str) -> Any:
    """Colecciones en línea. Solo el mapa `{k: v, k: v}` y la lista `[a, b]`, sin anidarlas."""
    cuerpo = bruto.strip()
    if cuerpo.startswith("{") and cuerpo.endswith("}"):
        interior = cuerpo[1:-1].strip()
        if not interior:
            return {}
        mapa: Dict[str, Any] = {}
        for parte in interior.split(","):
            if ":" not in parte:
                raise LecturaInvalida(f"entrada de mapa en línea sin clave: {parte.strip()}")
            clave, _, valor = parte.partition(":")
            clave = clave.strip()
            if clave in mapa:
                raise LecturaInvalida(f"clave repetida en un mapa en línea: {clave}")
            if valor.strip().startswith(("{", "[")):
                raise LecturaInvalida("colección en línea anidada: el dialecto no la usa")
            mapa[clave] = _escalar(valor)
        return mapa
    if cuerpo.startswith("[") and cuerpo.endswith("]"):
        interior = cuerpo[1:-1].strip()
        if not interior:
            return []
        return [_escalar(p) for p in interior.split(",")]
    raise LecturaInvalida(f"colección en línea mal cerrada: {cuerpo}")


def _valor_de_bloque(lineas: List[str], indice: int, indicador: str) -> Tuple[str, int]:
    """Desangra el escalar de bloque, normaliza los saltos y **come el salto final**."""
    if indicador != CHOMPING_ADMITIDO:
        raise LecturaInvalida(
            f"indicador de escalar de bloque no admitido: {indicador!r}; solo {CHOMPING_ADMITIDO!r}")
    cuerpo: List[str] = []
    sangria: Optional[int] = None
    while indice < len(lineas):
        linea = lineas[indice]
        if linea.strip() == "":
            cuerpo.append("")
            indice += 1
            continue
        actual = _sangria(linea)
        if sangria is None:
            sangria = actual
        if actual < sangria:
            break
        cuerpo.append(linea[sangria:])
        indice += 1
    while cuerpo and cuerpo[-1] == "":
        cuerpo.pop()
    return "\n".join(cuerpo), indice


def _bloque(lineas: List[str], indice: int, sangria: int) -> Tuple[Any, int]:
    if indice >= len(lineas):
        return None, indice
    contenido = lineas[indice].strip()
    if contenido.startswith("- "):
        return _lista(lineas, indice, sangria)
    return _mapa(lineas, indice, sangria)


def _lista(lineas: List[str], indice: int, sangria: int) -> Tuple[List[Any], int]:
    salida: List[Any] = []
    while indice < len(lineas):
        linea = lineas[indice]
        if linea.strip() == "":
            indice += 1
            continue
        actual = _sangria(linea)
        if actual < sangria:
            break
        if actual > sangria:
            raise LecturaInvalida(f"sangría inesperada en una lista, línea {indice + 1}")
        contenido = linea.strip()
        if not contenido.startswith("- "):
            break
        resto = contenido[2:]
        if ":" in resto and not resto.startswith(("{", "[")):
            # `- clave: valor` abre un mapa cuya primera clave vive en la línea del guion.
            interno = [" " * (sangria + 2) + resto] + lineas[indice + 1 :]
            elemento, consumidas = _mapa(interno, 0, sangria + 2)
            salida.append(elemento)
            indice = indice + 1 + (consumidas - 1)
        else:
            salida.append(_escalar(resto))
            indice += 1
    return salida, indice


def _mapa(lineas: List[str], indice: int, sangria: int) -> Tuple[Dict[str, Any], int]:
    salida: Dict[str, Any] = {}
    while indice < len(lineas):
        linea = lineas[indice]
        if linea.strip() == "":
            indice += 1
            continue
        actual = _sangria(linea)
        if actual < sangria:
            break
        if actual > sangria:
            raise LecturaInvalida(f"sangría inesperada en un mapa, línea {indice + 1}")
        contenido = linea.strip()
        if contenido.startswith("#"):
            indice += 1
            continue
        if contenido.startswith("- "):
            break
        if ":" not in contenido:
            raise LecturaInvalida(f"línea sin clave, línea {indice + 1}: {contenido}")
        clave, _, bruto = contenido.partition(":")
        clave = clave.strip()
        if not clave:
            raise LecturaInvalida(f"clave vacía, línea {indice + 1}")
        if clave in salida:
            raise LecturaInvalida(f"clave repetida en el mismo objeto: {clave}")
        bruto = bruto.strip()
        if bruto in CHOMPING_RECHAZADOS or bruto == CHOMPING_ADMITIDO:
            valor, indice = _valor_de_bloque(lineas, indice + 1, bruto)
            salida[clave] = valor
            continue
        if bruto == "":
            hijo, siguiente = _bloque(lineas, indice + 1, _sangria_hija(lineas, indice + 1, actual))
            salida[clave] = hijo
            indice = siguiente
            continue
        salida[clave] = _escalar(bruto)
        indice += 1
    return salida, indice


def _sangria_hija(lineas: List[str], indice: int, padre: int) -> int:
    for linea in lineas[indice:]:
        if linea.strip() == "":
            continue
        actual = _sangria(linea)
        if actual <= padre:
            return padre + 2
        return actual
    return padre + 2


def leer(texto: str) -> Dict[str, Any]:
    """Proyecta el documento a un mapa. Falla cerrado ante cualquier forma que el dialecto no use."""
    if not isinstance(texto, str):
        raise LecturaInvalida("la entrada del lector no es texto")
    lineas = [l for l in texto.replace("\r\n", "\n").split("\n")]
    # Los comentarios se descartan **dentro del parseo de mapas**, nunca sobre el texto entero: un
    # escalar de bloque puede contener líneas que empiezan con almohadilla y son parte del valor.
    # Filtrarlas acá hacía que dos parches distintos produjeran el mismo digest.
    # Solo **al inicio**, y por la misma razón que el comentario de arriba da para los comentarios:
    # un escalar de bloque puede contener una línea `---` que es parte del valor. `delta.material`
    # guarda un parche, y un parche sobre un archivo con frontmatter lleva `---` como línea de
    # contexto, así que barrer el texto entero rechazaba un ledger válido y le impedía recalcular su
    # digest. Un segundo documento más abajo no se escapa: sus líneas no las consume `_mapa` y caen
    # en la guarda de contenido sobrante.
    for linea in lineas:
        desnuda = linea.strip()
        if not desnuda or desnuda.startswith("#"):
            continue
        if desnuda in ("---", "..."):
            raise LecturaInvalida(
                "marcador de documento: el dialecto no admite múltiples documentos")
        break
    documento, consumidas = _mapa(lineas, 0, 0)
    if not isinstance(documento, dict) or not documento:
        raise LecturaInvalida("el documento no es un mapa no vacío")
    sobrante = [l for l in lineas[consumidas:] if l.strip() and not l.strip().startswith("#")]
    if sobrante:
        # Ignorarlo admitía un ledger válido seguido de cualquier cosa: el documento entero tiene que
        # consumirse, o no es el dialecto que este lector declara reconocer.
        raise LecturaInvalida(
            f"contenido no consumido a partir de la línea {consumidas + 1}: {sobrante[0][:50]}")
    return documento


# --------------------------------------------------------------------------------------
# Validación dirigida
# --------------------------------------------------------------------------------------

def _cerrado(objeto: Any, claves: Tuple[str, ...], donde: str, faltas: List[str],
             opcionales: Tuple[str, ...] = ()) -> bool:
    if not isinstance(objeto, dict):
        faltas.append(f"{donde}: se esperaba un objeto y vino {type(objeto).__name__}")
        return False
    sobran = set(objeto) - set(claves) - set(opcionales)
    if sobran:
        faltas.append(f"{donde}: claves no declaradas: {', '.join(sorted(sobran))}")
    faltan = set(claves) - set(objeto)
    if faltan:
        faltas.append(f"{donde}: claves ausentes: {', '.join(sorted(faltan))}")
    return not sobran and not faltan


def _huella(valor: Any, donde: str, faltas: List[str]) -> None:
    if not isinstance(valor, str) or not HUELLA.match(valor):
        faltas.append(f"{donde}: no tiene la forma sha256 seguida de 64 dígitos en minúscula")


def _recibo(documento: Dict[str, Any], legado: bool, faltas: List[str]) -> None:
    # El legado conserva lo que el contrato anterior sí declaraba y relaja solo lo que no estaba
    # definido: el cierre de la raíz y los tipos no declarados.
    if legado:
        for clave in ("tasks_fingerprint", "blocks"):
            if clave not in documento:
                faltas.append(f"recibo: clave ausente bajo el esquema legado: {clave}")
    else:
        _cerrado(documento, ("tasks_fingerprint", "blocks"), "recibo", faltas)
        _huella(documento.get("tasks_fingerprint"), "recibo.tasks_fingerprint", faltas)
    bloques = documento.get("blocks")
    if not isinstance(bloques, list) or not bloques:
        faltas.append("recibo.blocks: se esperaba una lista no vacía en su orden aprobado")
        return
    vistos = set()
    for orden, bloque in enumerate(bloques, start=1):
        donde = f"recibo.blocks[{orden}]"
        if not isinstance(bloque, dict):
            faltas.append(f"{donde}: se esperaba un objeto")
            continue
        if legado:
            for clave in ("block_id", "task_ids", "work_commit"):
                if clave not in bloque:
                    faltas.append(f"{donde}: clave ausente bajo el esquema legado: {clave}")
        else:
            _cerrado(bloque, ("block_id", "task_ids", "work_commit"), donde, faltas)
        identidad = bloque.get("block_id")
        if not legado and (not isinstance(identidad, str) or not identidad):
            faltas.append(f"{donde}.block_id: se esperaba una cadena no vacía")
        elif identidad is None:
            faltas.append(f"{donde}.block_id: identidad ausente")
        elif isinstance(identidad, (list, dict)):
            # Relajar el tipo bajo el legado no puede significar aceptar algo que no se puede
            # comparar: una identidad no hashable rompía el conjunto con un error sin capturar.
            faltas.append(f"{donde}.block_id: la identidad tiene que ser comparable, no una colección")
        elif identidad in vistos:
            # La unicidad de block_id la declaraba el contrato anterior, así que rige también en
            # el esquema legado: aflojarla volvería válido lo que ya se rechazaba.
            faltas.append(f"{donde}.block_id: identidad repetida en el recibo: {identidad}")
        else:
            vistos.add(identidad)
        # Bajo el esquema legado se relaja **solo lo que el contrato anterior no declaraba**: los
        # tipos de los elementos de `task_ids` y el formato de `work_commit`. Lo que sí declaraba
        # —`blocks` como lista en su orden aprobado y la unicidad de `block_id`— sigue rigiendo, o
        # aflojar volvería válido lo que ese contrato ya rechazaba.
        tareas = bloque.get("task_ids")
        if legado:
            if not isinstance(tareas, list) or not tareas:
                faltas.append(f"{donde}.task_ids: se esperaba una lista no vacía")
        else:
            if not isinstance(tareas, list) or not tareas or not all(isinstance(t, str) for t in tareas):
                faltas.append(f"{donde}.task_ids: se esperaba una lista no vacía de cadenas")
            commit = bloque.get("work_commit")
            if commit is not None and not (isinstance(commit, str) and SHA.match(commit)):
                faltas.append(f"{donde}.work_commit: se esperaba nulo o el SHA completo del commit")


def _ledger(documento: Dict[str, Any], faltas: List[str]) -> None:
    version = documento.get("schema_version")
    if isinstance(version, bool) or version != 1:
        faltas.append("ledger.schema_version: solo se interpreta la versión 1")
        return
    _cerrado(documento, ("schema_version", "sequence", "transitions", "effect_events", "result"),
             "ledger", faltas)
    secuencia = documento.get("sequence")
    if not isinstance(secuencia, dict):
        faltas.append("ledger.sequence: se esperaba un objeto")
        return
    modo = secuencia.get("mode")
    if modo not in ("blocks", "inline"):
        faltas.append("ledger.sequence.mode: se esperaba blocks o inline")
        return
    obligatorias = ("sequence_id", "mode", "base_anchor", "coverage_fingerprint", "delta", "cursor",
                    "terminal")
    opcionales = ("join_state",) + (("receipt_ref",) if modo == "blocks" else ())
    _cerrado(secuencia, obligatorias, "ledger.sequence", faltas, opcionales)
    if modo == "blocks" and "receipt_ref" not in secuencia:
        faltas.append("ledger.sequence.receipt_ref: obligatorio en el modo blocks")
    if modo == "inline" and "receipt_ref" in secuencia:
        faltas.append("ledger.sequence.receipt_ref: prohibido en el modo inline")
    if not isinstance(secuencia.get("sequence_id"), str) or not secuencia.get("sequence_id"):
        faltas.append("ledger.sequence.sequence_id: se esperaba una cadena no vacía")
    ancla = secuencia.get("base_anchor")
    if not isinstance(ancla, str) or not SHA.match(ancla):
        faltas.append("ledger.sequence.base_anchor: se esperaba el SHA completo")
    _huella(secuencia.get("coverage_fingerprint"), "ledger.sequence.coverage_fingerprint", faltas)
    delta = secuencia.get("delta")
    if _cerrado(delta, ("algorithm", "digest", "material"), "ledger.sequence.delta", faltas):
        if delta.get("algorithm") != "sha256":
            faltas.append("ledger.sequence.delta.algorithm: se esperaba sha256")
        _huella(delta.get("digest"), "ledger.sequence.delta.digest", faltas)
        if not isinstance(delta.get("material"), str):
            faltas.append("ledger.sequence.delta.material: se esperaba una cadena, vacía o el patch")
    cursor = secuencia.get("cursor")
    if _cerrado(cursor, ("machine", "cutpoint"), "ledger.sequence.cursor", faltas):
        maquina, corte = cursor.get("machine"), cursor.get("cutpoint")
        if maquina not in MAQUINAS:
            faltas.append("ledger.sequence.cursor.machine: máquina desconocida")
        elif modo == "inline" and maquina != "inline-machine":
            faltas.append("ledger.sequence.cursor.machine: inline solo admite inline-machine")
        elif modo == "blocks" and maquina == "inline-machine":
            faltas.append("ledger.sequence.cursor.machine: blocks no admite inline-machine")
        admitidos = CUTPOINTS_POR_MAQUINA.get(maquina, ())
        if corte not in admitidos:
            faltas.append(f"ledger.sequence.cursor.cutpoint: {corte!r} no pertenece a {maquina!r}")
    if secuencia.get("terminal") not in TERMINALES:
        faltas.append("ledger.sequence.terminal: valor fuera del enum")
    for clave in ("transitions", "effect_events"):
        if not isinstance(documento.get(clave), list):
            faltas.append(f"ledger.{clave}: se esperaba una lista")
    resultado = documento.get("result")
    if _cerrado(resultado, ("status", "closed_at"), "ledger.result", faltas):
        if resultado.get("status") not in TERMINALES:
            faltas.append("ledger.result.status: valor fuera del enum")
        elif resultado.get("status") != secuencia.get("terminal"):
            faltas.append("ledger.result.status: no coincide con sequence.terminal")
        cerrado_en = resultado.get("closed_at")
        # `suspended` es continuable: vuelve a diseño. Solo los tres terminales que no continúan
        # exigen fecha de cierre.
        continuable = resultado.get("status") in ("active", "suspended")
        if continuable and cerrado_en is not None:
            faltas.append("ledger.result.closed_at: debe ser nulo mientras la secuencia está activa")
        if not continuable and not isinstance(cerrado_en, str):
            faltas.append("ledger.result.closed_at: obligatorio en un terminal no continuable")


def validar(documento: Dict[str, Any], esquema: str) -> List[str]:
    """Devuelve las violaciones estructurales. Lista vacía significa que admite cálculo."""
    if esquema not in ("legado", "v1", "ledger"):
        raise LecturaInvalida(f"esquema desconocido: {esquema!r}")
    if not isinstance(documento, dict):
        raise LecturaInvalida("el documento a validar no es un mapa")
    faltas: List[str] = []
    if esquema == "ledger":
        _ledger(documento, faltas)
    else:
        _recibo(documento, esquema == "legado", faltas)
    return faltas
