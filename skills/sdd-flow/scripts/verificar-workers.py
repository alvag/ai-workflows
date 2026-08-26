#!/usr/bin/env python3
"""Verifica el contrato de perfiles de worker por rol.

Interfaz:
  --ac <n>                         ejecuta un modo registrado
  --autotest --hojas <ruta>        prueba la biyección entre hojas, controles y mutantes
  --listar                         lista los modos registrados y sus hojas

Códigos de salida: 0 pasa, 1 falla, 2 invocación inválida y 3 medición detenida.
El código 3 no expresa un veredicto sobre el modo solicitado.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from _tabla import parsear_tabla_pipe


REPO = Path(__file__).resolve().parents[3]
REFERENCE = REPO / "skills/sdd-flow/reference.md"

ROLES = {
    "explore",
    "counter-plan",
    "investigate",
    "debate",
    "design-review",
    "implement",
    "refute",
    "pr",
}
FAMILIAS = {"claude", "codex"}
CAMPOS = {"model", "effort"}
TRADUCCIONES = {
    "bajo": "low",
    "medio": "medium",
    "alto": "high",
    "muy_alto": "xhigh",
    "maximo": "max",
}


class MedicionDetenida(RuntimeError):
    """La evidencia necesaria no se pudo leer; no hay veredicto."""


@dataclass(frozen=True)
class Chequeo:
    hoja: str
    ok: bool
    detalle: str


@dataclass(frozen=True)
class Modo:
    ac: str
    fila: str
    nombre: str
    controles: tuple[str, ...]
    ejecutar: Callable[[str], list[Chequeo]]


@dataclass(frozen=True)
class Mutante:
    hoja: str
    patron: str
    reemplazo: str

    def aplicar(self, texto: str) -> str:
        return reemplazar_unico(texto, self.patron, self.reemplazo)


def norm(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def leer_texto(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8")
    except OSError as exc:
        raise MedicionDetenida(f"no se pudo leer {ruta}: {exc}") from exc


def extraer_seccion(texto: str, titulo: str, nivel: int) -> str | None:
    lineas = texto.splitlines()
    inicio = None
    for indice, linea in enumerate(lineas):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", linea)
        if m and len(m.group(1)) == nivel and m.group(2) == titulo:
            inicio = indice
            break
    if inicio is None:
        return None
    fin = len(lineas)
    for indice in range(inicio + 1, len(lineas)):
        m = re.match(r"^(#{1,6})\s+", lineas[indice])
        if m and len(m.group(1)) <= nivel:
            fin = indice
            break
    return "\n".join(lineas[inicio:fin])


def extraer_yaml(texto: str) -> str | None:
    m = re.search(r"^```yaml\s*$\n(.*?)\n^```\s*$", texto, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else None


def parsear_yaml_restringido(texto: str) -> tuple[dict[str, object], str | None]:
    """Parsea el subconjunto de YAML usado por el esquema: mapas y escalares."""
    raiz: dict[str, object] = {}
    pila: list[tuple[int, dict[str, object]]] = [(-1, raiz)]
    for numero, linea in enumerate(texto.splitlines(), start=1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        if "\t" in linea:
            return {}, f"línea {numero}: tabulación no admitida"
        indentacion = len(linea) - len(linea.lstrip(" "))
        if indentacion % 2:
            return {}, f"línea {numero}: indentación impar"
        m = re.match(r"^\s*([A-Za-z0-9_-]+):(?:\s*(.*?))?\s*$", linea)
        if not m:
            return {}, f"línea {numero}: forma no admitida"
        clave, valor = m.group(1), (m.group(2) or "").strip()
        if " #" in valor:
            valor = valor.split(" #", 1)[0].rstrip()
        while pila and indentacion <= pila[-1][0]:
            pila.pop()
        if not pila:
            return {}, f"línea {numero}: indentación sin padre"
        padre = pila[-1][1]
        if clave in padre:
            return {}, f"línea {numero}: clave duplicada {clave}"
        if valor:
            if valor.isdigit():
                padre[clave] = int(valor)
            else:
                padre[clave] = valor.strip("'\"")
        else:
            nodo: dict[str, object] = {}
            padre[clave] = nodo
            pila.append((indentacion, nodo))
    return raiz, None


def parsear_tabla_pipe_con_escape(texto: str) -> list[list[str]]:
    r"""Versión acotada que trata ``\|`` como contenido de una celda."""
    filas: list[list[str]] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not (linea.startswith("|") and linea.endswith("|")):
            continue
        celdas: list[str] = []
        actual: list[str] = []
        indice = 1
        limite = len(linea) - 1
        while indice < limite:
            caracter = linea[indice]
            if caracter == "\\" and indice + 1 < limite and linea[indice + 1] == "|":
                actual.append("|")
                indice += 2
                continue
            if caracter == "|":
                celdas.append("".join(actual).strip())
                actual = []
            else:
                actual.append(caracter)
            indice += 1
        celdas.append("".join(actual).strip())
        if celdas and all(celda and set(celda) <= {"-", ":"} for celda in celdas):
            continue
        filas.append(celdas)
    return filas


def literales(celda: str) -> set[str]:
    return set(re.findall(r"`([^`]+)`", celda))


def control(hoja: str, ok: bool, detalle_ok: str, detalle_falla: str) -> Chequeo:
    return Chequeo(hoja, ok, detalle_ok if ok else detalle_falla)


def verificar_1(texto: str) -> list[Chequeo]:
    seccion = extraer_seccion(texto, "Esquema de `.specify/workers.yml`", 2)
    bloque = extraer_yaml(seccion or "")
    datos, error = parsear_yaml_restringido(bloque) if bloque is not None else ({}, "bloque YAML ausente")
    roles = datos.get("roles") if isinstance(datos.get("roles"), dict) else {}

    version_ok = error is None and datos.get("schema_version") == 1
    roles_ok = error is None and set(roles) == ROLES
    familias_ok = roles_ok and all(
        isinstance(roles[rol], dict) and set(roles[rol]) == FAMILIAS for rol in ROLES
    )
    campos_ok = familias_ok and all(
        isinstance(roles[rol][familia], dict) and set(roles[rol][familia]) == CAMPOS
        for rol in ROLES for familia in FAMILIAS
    )

    claves = extraer_seccion(seccion or "", "Claves admitidas", 3)
    filas = parsear_tabla_pipe_con_escape(claves or "")
    tabla: dict[str, set[str]] = {}
    for fila in filas:
        if len(fila) == 2 and norm(fila[0]) != "nivel":
            tabla[norm(fila[0].strip("`"))] = literales(fila[1])
    tabla_esperada = {
        "raiz": {"schema_version", "roles"},
        "roles": ROLES,
        "cada rol": FAMILIAS,
        "cada familia": CAMPOS,
    }
    cierre_textual = "ninguna otra clave" in norm(seccion or "") and "ningun nivel" in norm(seccion or "")
    cierre_ok = error is None and set(datos) == {"schema_version", "roles"} and tabla == tabla_esperada and cierre_textual

    causa = error or "la estructura no coincide con el esquema cerrado"
    return [
        control("V1.schema-version", version_ok, "schema_version: 1", causa),
        control("V1.ocho-roles", roles_ok, "los ocho roles exactos", f"roles observados: {sorted(roles)}"),
        control("V1.dos-familias-por-rol", familias_ok, "claude y codex en cada rol", causa),
        control("V1.dos-campos-por-familia", campos_ok, "model y effort en cada familia", causa),
        control("V1.cierre-sin-claves-extra", cierre_ok, "lista blanca cerrada en todos los niveles", causa),
    ]


def verificar_2(texto: str) -> list[Chequeo]:
    seccion = extraer_seccion(texto, "Esquema de `.specify/workers.yml`", 2) or ""
    historica = extraer_seccion(seccion, "Forma histórica descartada", 3) or ""
    normalizada = norm(historica)
    forma_ok = all(frase in normalizada for frase in (
        "sustituye la forma historica",
        "perfiles nombrados con indireccion por asignaciones",
    ))
    motivo_ok = all(frase in normalizada for frase in (
        "lista blanca cerrada",
        "model",
        "effort",
        "misma garantia",
        "herramientas",
        "permisos",
        "autoridad",
        "maquinaria de la indireccion",
    ))
    return [
        control("V2.forma-historica-nombrada", forma_ok, "forma histórica nombrada y sustituida", "falta nombrar la forma histórica completa"),
        control("V2.motivo-del-descarte", motivo_ok, "motivo y garantía equivalente declarados", "falta el motivo normativo del descarte"),
    ]


def verificar_7(texto: str) -> list[Chequeo]:
    seccion = extraer_seccion(texto, "Esquema de `.specify/workers.yml`", 2) or ""
    enum = extraer_seccion(seccion, "Enum portable de esfuerzo", 3) or ""
    filas = [fila for fila in parsear_tabla_pipe(enum) if len(fila) == 3]
    datos = [fila for fila in filas if fila[0].strip().strip("`") != "Portable"]
    limpias = [[celda.strip().strip("`") for celda in fila] for fila in datos]
    por_literal = {fila[0]: fila for fila in limpias}
    cinco_ok = len(limpias) == 5 and set(por_literal) == set(TRADUCCIONES)
    claude_ok = cinco_ok and all(por_literal[k][1] == v for k, v in TRADUCCIONES.items())
    codex_ok = cinco_ok and all(por_literal[k][2] == v for k, v in TRADUCCIONES.items())
    identidad_ok = cinco_ok and all(fila[1] == fila[2] for fila in limpias)
    return [
        control("V7.cinco-literales", cinco_ok, "cinco literales exactos", f"literales observados: {sorted(por_literal)}"),
        control("V7.traduccion-claude", claude_ok, "traducción de Claude exacta", "la columna de Claude difiere"),
        control("V7.traduccion-codex", codex_ok, "traducción de Codex exacta", "la columna de Codex difiere"),
        control("V7.identidad-entre-familias", identidad_ok, "ambas familias traducen al mismo valor", "las traducciones difieren entre familias"),
    ]


MODOS = {
    "1": Modo("1", "V1", "esquema cerrado", (
        "V1.schema-version",
        "V1.ocho-roles",
        "V1.dos-familias-por-rol",
        "V1.dos-campos-por-familia",
        "V1.cierre-sin-claves-extra",
    ), verificar_1),
    "2": Modo("2", "V2", "descarte de la forma histórica", (
        "V2.forma-historica-nombrada",
        "V2.motivo-del-descarte",
    ), verificar_2),
    "7": Modo("7", "V7", "enum portable de esfuerzo", (
        "V7.cinco-literales",
        "V7.traduccion-claude",
        "V7.traduccion-codex",
        "V7.identidad-entre-familias",
    ), verificar_7),
}


def reemplazar_unico(texto: str, viejo: str, nuevo: str) -> str:
    if texto.count(viejo) != 1:
        raise ValueError(f"el patrón del mutante aparece {texto.count(viejo)} veces")
    return texto.replace(viejo, nuevo, 1)


def mutar(hoja: str, patron: str, reemplazo: str) -> Mutante:
    return Mutante(hoja, patron, reemplazo)


MUTANTES = {
    "V1.schema-version": mutar("V1.schema-version", "schema_version: 1\nroles:", "schema_version: 2\nroles:"),
    "V1.ocho-roles": mutar("V1.ocho-roles",
        "  refute:\n    claude:\n      model: opus\n      effort: alto\n    codex:\n      model: gpt-5.6-sol\n      effort: alto\n",
        "",
    ),
    "V1.dos-familias-por-rol": mutar("V1.dos-familias-por-rol",
        "  pr:\n    claude:\n      model: opus\n      effort: alto\n    codex:\n      model: gpt-5.6-sol\n      effort: alto\n",
        "  pr:\n    claude:\n      model: opus\n      effort: alto\n",
    ),
    "V1.dos-campos-por-familia": mutar("V1.dos-campos-por-familia",
        "  pr:\n    claude:\n      model: opus\n      effort: alto\n    codex:\n      model: gpt-5.6-sol\n      effort: alto\n",
        "  pr:\n    claude:\n      model: opus\n      effort: alto\n    codex:\n      model: gpt-5.6-sol\n",
    ),
    "V1.cierre-sin-claves-extra": mutar("V1.cierre-sin-claves-extra",
        "schema_version: 1\nroles:",
        "schema_version: 1\nextra: true\nroles:",
    ),
    "V2.forma-historica-nombrada": mutar("V2.forma-historica-nombrada",
        "sustituye la forma histórica de perfiles nombrados con indirección por asignaciones",
        "sustituye la configuración anterior",
    ),
    "V2.motivo-del-descarte": mutar("V2.motivo-del-descarte",
        "No se adopta esa forma porque la lista blanca cerrada de `model` y `effort` aporta la misma\n"
        "garantía: una asignación no puede transportar herramientas, permisos ni autoridad, sin la maquinaria\n"
        "de la indirección. La forma directa conserva esa frontera sin perfiles intermedios ni referencias que\n"
        "resolver.",
        "No se adopta esa forma por preferencia editorial.",
    ),
    "V7.cinco-literales": mutar("V7.cinco-literales", "| `bajo` | `low` | `low` |\n", ""),
    "V7.traduccion-claude": mutar("V7.traduccion-claude",
        "| `medio` | `medium` | `medium` |",
        "| `medio` | `middle` | `medium` |",
    ),
    "V7.traduccion-codex": mutar("V7.traduccion-codex",
        "| `alto` | `high` | `high` |",
        "| `alto` | `high` | `higher` |",
    ),
    "V7.identidad-entre-familias": mutar("V7.identidad-entre-familias",
        "| `maximo` | `max` | `max` |",
        "| `maximo` | `max` | `maximum` |",
    ),
}


def inventario_hojas(ruta: Path) -> tuple[list[str], str | None]:
    texto = leer_texto(ruta)
    seccion = extraer_seccion(texto, "Hojas normativas de v1", 4)
    if seccion is None:
        raise MedicionDetenida(f"no existe la sección #### Hojas normativas de v1 en {ruta}")
    prefijos = tuple(f"{modo.fila}." for modo in MODOS.values())
    hojas = [hoja for hoja in re.findall(r"`(V\d+\.[^`]+)`", seccion) if hoja.startswith(prefijos)]
    duplicadas = sorted({hoja for hoja in hojas if hojas.count(hoja) > 1})
    return hojas, ", ".join(duplicadas) if duplicadas else None


def corpus_verde_real() -> str:
    texto = leer_texto(REFERENCE)
    seccion = extraer_seccion(texto, "Esquema de `.specify/workers.yml`", 2)
    if seccion is None:
        raise MedicionDetenida(
            f"no existe la sección ## Esquema de `.specify/workers.yml` en {REFERENCE}"
        )
    return seccion


def evaluar_consistencia_interna() -> tuple[int, list[str]]:
    lineas = ["=== Autotest estructural de workers"]
    controles_lista = [hoja for modo in MODOS.values() for hoja in modo.controles]
    mutantes_lista = [mutante.hoja for mutante in MUTANTES.values()]
    controles = set(controles_lista)
    mutantes = set(mutantes_lista)
    controles_duplicados = sorted({hoja for hoja in controles_lista if controles_lista.count(hoja) > 1})
    mutantes_duplicados = sorted({hoja for hoja in mutantes_lista if mutantes_lista.count(hoja) > 1})
    claves_desalineadas = sorted(
        clave for clave, mutante in MUTANTES.items() if clave != mutante.hoja
    )
    biyeccion_ok = (
        not controles_duplicados
        and not mutantes_duplicados
        and not claves_desalineadas
        and controles == mutantes
    )
    lineas.append(
        f"[{'OK   ' if biyeccion_ok else 'FALLA'}] biyección interna por hoja: "
        f"controles={len(controles)} mutantes={len(mutantes)}"
    )
    if controles_duplicados:
        lineas.append(f"[FALLA] controles duplicados: {controles_duplicados}")
    if mutantes_duplicados:
        lineas.append(f"[FALLA] mutantes duplicados: {mutantes_duplicados}")
    if claves_desalineadas:
        lineas.append(f"[FALLA] claves de mutante desalineadas: {claves_desalineadas}")
    if controles != mutantes:
        lineas.append(
            f"[FALLA] controles sin mutante={sorted(controles - mutantes)} "
            f"mutantes sin control={sorted(mutantes - controles)}"
        )
    if not biyeccion_ok:
        lineas.append("RESULTADO ESTRUCTURAL: FALLA — controles y mutantes no son biyectivos")
        return 1, lineas

    try:
        corpus = corpus_verde_real()
    except MedicionDetenida as exc:
        return 3, lineas + [f"MEDICIÓN DETENIDA — {exc}; no hay veredicto."]

    fallas: list[str] = []
    for modo in MODOS.values():
        resultados = modo.ejecutar(corpus)
        ids = tuple(resultado.hoja for resultado in resultados)
        ok = ids == modo.controles and all(resultado.ok for resultado in resultados)
        lineas.append(
            f"[{'OK   ' if ok else 'FALLA'}] control positivo --ac {modo.ac}: "
            f"{sum(resultado.ok for resultado in resultados)}/{len(resultados)} controles verdes"
        )
        if not ok:
            fallas.append(f"control positivo --ac {modo.ac}")

    for hoja in sorted(controles, key=lambda valor: (int(valor.split(".", 1)[0][1:]), valor)):
        mutante = MUTANTES[hoja]
        modo = next(m for m in MODOS.values() if hoja in m.controles)
        apariciones = corpus.count(mutante.patron)
        if apariciones != 1:
            lineas.append(
                f"[FALLA] {hoja} → aplicabilidad: el patrón aparece {apariciones} veces; se exige 1"
            )
            fallas.append(hoja)
            continue
        try:
            texto_mutado = mutante.aplicar(corpus)
            resultados = modo.ejecutar(texto_mutado)
        except ValueError as exc:
            lineas.append(f"[FALLA] {hoja} → el mutante no se pudo aplicar: {exc}")
            fallas.append(hoja)
            continue
        rojos = [resultado.hoja for resultado in resultados if not resultado.ok]
        ok = hoja in rojos
        lineas.append(
            f"[{'OK   ' if ok else 'FALLA'}] {hoja} → controles en rojo: "
            f"{', '.join(rojos) if rojos else 'ninguno'}"
        )
        if not ok:
            fallas.append(hoja)

    if fallas:
        lineas.append("RESULTADO ESTRUCTURAL: FALLA — " + ", ".join(fallas))
        return 1, lineas
    lineas.append(
        f"RESULTADO ESTRUCTURAL: OK — {len(MODOS)} modos, {len(controles)} hojas y "
        f"{len(MUTANTES)} mutantes; cada hoja puso rojo su control"
    )
    return 0, lineas


def evaluar_autotest(ruta_hojas: Path) -> tuple[int, list[str]]:
    lineas = [f"=== Autotest de workers · hojas: {ruta_hojas}"]
    try:
        inventario_lista, duplicadas = inventario_hojas(ruta_hojas)
    except MedicionDetenida as exc:
        return 3, lineas + [f"MEDICIÓN DETENIDA — {exc}; no hay veredicto."]

    inventario = set(inventario_lista)
    controles = {hoja for modo in MODOS.values() for hoja in modo.controles}
    mutantes = {mutante.hoja for mutante in MUTANTES.values()}
    if duplicadas:
        lineas.append(f"[FALLA] hojas duplicadas en el inventario: {duplicadas}")
    biyeccion_ok = not duplicadas and inventario == controles == mutantes
    lineas.append(
        f"[{'OK   ' if biyeccion_ok else 'FALLA'}] biyección contra el inventario: "
        f"inventario={len(inventario)} controles={len(controles)} mutantes={len(mutantes)}"
    )
    if not biyeccion_ok:
        universo = inventario | controles | mutantes
        for nombre, conjunto in (
            ("inventario", inventario),
            ("controles", controles),
            ("mutantes", mutantes),
        ):
            faltan = sorted(universo - conjunto)
            sobran = sorted(conjunto - (inventario & controles & mutantes))
            if faltan or sobran:
                lineas.append(f"[FALLA] {nombre}: faltan={faltan} sobran={sobran}")
        lineas.append("RESULTADO: FALLA — inventario, controles y mutantes no son iguales")
        return 1, lineas

    estado_estructural, lineas_estructurales = evaluar_consistencia_interna()
    lineas.extend(lineas_estructurales)
    if estado_estructural == 3:
        lineas.append("MEDICIÓN DETENIDA — el autotest estructural no produjo un veredicto")
        return 3, lineas
    if estado_estructural == 1:
        lineas.append("RESULTADO: FALLA — el autotest estructural no está en verde")
        return 1, lineas
    lineas.append(
        f"RESULTADO: OK — inventario completo para {len(MODOS)} modos y {len(inventario)} hojas"
    )
    return 0, lineas


def ejecutar_modo(modo: Modo) -> int:
    estado_autotest, lineas_autotest = evaluar_consistencia_interna()
    if estado_autotest != 0:
        detalle = lineas_autotest[-1] if lineas_autotest else "autotest sin salida"
        print(
            f"MEDICIÓN DETENIDA — el autotest estructural no está en verde: {detalle}. "
            f"No es un veredicto de {modo.fila}."
        )
        return 3
    try:
        texto = leer_texto(REFERENCE)
    except MedicionDetenida as exc:
        print(f"MEDICIÓN DETENIDA — {exc}. No es un veredicto de {modo.fila}.")
        return 3
    resultados = modo.ejecutar(texto)
    print(f"=== {modo.fila} · --ac {modo.ac} — {modo.nombre}")
    for resultado in resultados:
        print(f"[{'OK   ' if resultado.ok else 'FALLA'}] {resultado.hoja}: {resultado.detalle}")
    fallas = [resultado for resultado in resultados if not resultado.ok]
    print(
        f"RESULTADO: {'OK' if not fallas else 'FALLA'} — "
        f"{len(resultados) - len(fallas)}/{len(resultados)} controles verdes"
    )
    return 1 if fallas else 0


def listar() -> int:
    for modo in MODOS.values():
        print(f"AC {modo.ac} · {modo.fila} — {modo.nombre}")
        for hoja in modo.controles:
            print(f"  - {hoja}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ac", metavar="N", help="ejecuta el modo del AC N")
    parser.add_argument("--autotest", action="store_true", help="ejercita controles y mutantes")
    parser.add_argument("--listar", action="store_true", help="lista los modos y sus hojas")
    parser.add_argument("--hojas", type=Path, help="plan que contiene #### Hojas normativas de v1")
    args = parser.parse_args()

    elegidos = sum((args.ac is not None, args.autotest, args.listar))
    if elegidos != 1:
        parser.error("elige exactamente uno de --ac, --autotest o --listar")
    if args.ac is not None and args.ac not in MODOS:
        parser.error(f"AC no registrado: {args.ac}; valores válidos: {', '.join(MODOS)}")
    if args.autotest and args.hojas is None:
        parser.error("--autotest exige --hojas <ruta-del-plan>")
    if not args.autotest and args.hojas is not None:
        parser.error("--hojas solo se admite con --autotest")
    if args.autotest:
        estado, lineas = evaluar_autotest(args.hojas)
        print("\n".join(lineas))
        return estado
    if args.listar:
        return listar()
    return ejecutar_modo(MODOS[args.ac])


if __name__ == "__main__":
    sys.exit(main())
