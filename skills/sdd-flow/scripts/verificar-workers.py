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
import tempfile
import subprocess
import shutil
import os
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
DEFAULTS = {
    "explore": (("opus", "alto"), ("gpt-5.6-sol", "alto")),
    "counter-plan": (("opus", "alto"), ("gpt-5.6-sol", "alto")),
    "investigate": (("opus", "muy_alto"), ("gpt-5.6-sol", "muy_alto")),
    "debate": (("opus", "alto"), ("gpt-5.6-sol", "alto")),
    "design-review": (("opus", "muy_alto"), ("gpt-5.6-sol", "muy_alto")),
    "implement": (("sonnet", "medio"), ("gpt-5.6-terra", "medio")),
    "refute": (("opus", "alto"), ("gpt-5.6-sol", "alto")),
    "pr": (("opus", "alto"), ("gpt-5.6-sol", "alto")),
}

REGIONES_DESIGN = (
    "cr-ronda1-posix", "cr-ronda1-ps", "cr-resume-posix", "cr-resume-ps",
    "cr-viac-r1-posix", "cr-viac-r1-ps", "cr-viac-resume-posix",
    "cr-viac-resume-ps", "cr-latencia-sync", "cr-latencia-background",
    "cr-seed-posix", "cr-seed-ps",
)
REGIONES_COEX = (
    "coex-directa-posix", "coex-directa-ps", "coex-latencia-posix", "coex-latencia-ps",
    "coex-fanout-posix-codex", "coex-fanout-posix-claude",
    "coex-fanout-ps-codex", "coex-fanout-ps-claude",
)
REGIONES_IMPLEMENT = (
    "ci-wb-posix", "ci-wb-ps", "ci-wb-resume", "ci-wb-resume-ps",
    "ci-wc-lanzamiento", "ci-wc-fix", "prfb-codex",
)
REGIONES_BBCR = ("bbcr-viab-posix", "bbcr-viab-ps", "bbcr-viac-posix", "bbcr-viac-ps")
MATRIZ_ESPERADA = frozenset(
    [(r, "design-review", "design-review") for r in REGIONES_DESIGN]
    + [(r, rol, rol) for r in REGIONES_COEX for rol in ("explore", "counter-plan", "investigate", "debate")]
    + [(r, "implement", "implement") for r in REGIONES_IMPLEMENT]
    + [(r, rol, rol) for r in REGIONES_BBCR for rol in ("pr", "refute")]
)


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
    corpus: Optional[Callable[[], str]] = None

    def texto_base(self) -> str:
        """Corpus que el autotest muta para este modo. Un modo que leyera archivos por su cuenta
        sería inmutable: su mutante existiría y no podría ponerlo rojo nunca."""
        return self.corpus() if self.corpus is not None else corpus_verde_real()


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


def tabla_tras(texto: str, ancla: str) -> list[list[str]]:
    """Devuelve la primera tabla contigua posterior a un ancla única."""
    if texto.count(ancla) != 1:
        return []
    lineas: list[str] = []
    iniciada = False
    for linea in texto.split(ancla, 1)[1].splitlines():
        if linea.strip().startswith("|"):
            iniciada = True
            lineas.append(linea)
        elif iniciada:
            break
    return parsear_tabla_pipe_con_escape("\n".join(lineas))


def celdas_literales(fila: list[str]) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(re.findall(r"`([^`]+)`", celda)) for celda in fila)


def controles_de_frases(texto: str, reglas: dict[str, tuple[str, ...]]) -> list[Chequeo]:
    observado = norm(texto)
    return [
        control(hoja, all(norm(frase) in observado for frase in frases),
                "cláusula presente", f"falta una cláusula: {frases}")
        for hoja, frases in reglas.items()
    ]


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


def seccion_workers(texto: str, titulo: str) -> str:
    sede = extraer_seccion(texto, "Esquema de `.specify/workers.yml`", 2) or ""
    return extraer_seccion(sede, titulo, 3) or ""


def verificar_3(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "Matriz de defaults y delta de inicialización")
    filas = tabla_tras(seccion, "dieciséis perfiles siguientes:")
    observados = {}
    for fila in filas[1:]:
        literales_fila = celdas_literales(fila)
        if len(fila) == 3 and all(literales_fila):
            observados[literales_fila[0][0]] = (literales_fila[1], literales_fila[2])
    defaults_ok = observados == DEFAULTS
    delta_ok = len(tabla_tras(seccion, "El delta usa tres columnas")) == 5 and all(
        frase in norm(seccion) for frase in ("muestra el archivo completo", "delta de abajo")
    )
    return [
        control("V3.muestra-defaults", defaults_ok, "los dieciséis defaults exactos", "la matriz de defaults difiere"),
        control("V3.muestra-delta", delta_ok, "preview con delta completo", "falta el delta en el preview"),
        *controles_de_frases(seccion, {
            "V3.pide-confirmacion": ("solo tras una confirmación explícita",),
            "V3.no-pisa-archivo-valido": ("ya existe y es válido", "sin sobrescribirlo"),
        }),
    ]


def verificar_4(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "Matriz de defaults y delta de inicialización")
    filas = tabla_tras(seccion, "El delta usa tres columnas")
    cabecera, datos = (filas[0], filas[1:]) if filas else ([], [])
    tres_ok = len(cabecera) == 3 and [norm(c) for c in cabecera] == [
        "region, ruta y familia", "procedencia y valor anterior", "perfil nuevo y cambio conocido"
    ]
    reglas = (
        ("V4.procedencia", "procedencia:"),
        ("V4.valor-anterior-o-indeterminado", "valor anterior:"),
        ("V4.perfil-nuevo", "perfil nuevo:"),
        ("V4.cambio-conocido", "cambio conocido:"),
    )
    return [
        control("V4.tres-columnas", tres_ok and len(datos) == 4, "tres columnas y cuatro baselines", "forma de la tabla incorrecta"),
        *[control(hoja, bool(datos) and all(frase in norm(" ".join(f)) for f in datos),
                  f"{frase} presente en cada baseline", f"falta {frase} en una fila") for hoja, frase in reglas],
    ]


def verificar_5(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "Matriz `(región, ruta) → rol`")
    filas = tabla_tras(seccion, "`ruta` identifica el uso lógico")
    observada = {
        tuple(lits[0] for lits in celdas_literales(fila))
        for fila in filas[1:] if len(fila) == 3 and all(len(lits) == 1 for lits in celdas_literales(fila))
    }
    faltan, sobran = MATRIZ_ESPERADA - observada, observada - MATRIZ_ESPERADA
    fuentes = tuple(REPO / ruta for ruta in (
        "skills/cross-review/reference.md", "skills/co-explore/reference.md",
        "skills/cross-implement/reference.md", "skills/bitbucket-code-review/reference.md",
        "skills/sdd-pr-feedback/reference.md",
    ))
    regiones_esperadas = {region for region, _, _ in MATRIZ_ESPERADA}
    if all(ruta.exists() for ruta in fuentes):
        regiones_arbol = {
            region for ruta in fuentes
            for region, _ in re.findall(r"despacho:inicio:([^:]+):(claude|codex)", leer_texto(ruta))
        }
    else:
        regiones_arbol = regiones_esperadas  # corpus portable: el árbol no viaja con la sede
    identidad_ok = not faltan and not sobran and regiones_arbol == regiones_esperadas
    return [
        control("V5.identidad-region-ruta", identidad_ok, "identidad exacta contra las regiones marcadas", f"regiones árbol={sorted(regiones_arbol)}"),
        control("V5.sin-faltantes", not faltan, "sin rutas faltantes", f"faltan: {sorted(faltan)}"),
        control("V5.sin-sobrantes", not sobran, "sin rutas sobrantes", f"sobran: {sorted(sobran)}"),
        control("V5.ocho-roles-con-ruta", {rol for _, _, rol in observada} == ROLES and "los ocho roles tienen" in norm(seccion),
                "los ocho roles tienen ruta", "la cobertura de roles no es exacta"),
    ]


def verificar_6(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "El literal de herencia")
    filas = tabla_tras(seccion, "materializa por familia y por campo:")
    datos = {frozenset(literales(fila[0] + fila[1])): norm(fila[2]) for fila in filas[1:] if len(fila) == 3}
    return [
        control("V6.claude-model-cableado", frozenset(("claude", "model")) in datos and all(x in datos[frozenset(("claude", "model"))] for x in ("modelo cableado", "opus", "sonnet")),
                "modelo Claude cableado por ruta", "la resolución de claude/model difiere"),
        control("V6.claude-effort-sin-flag", frozenset(("claude", "effort")) in datos and all(
            frase in datos[frozenset(("claude", "effort"))] for frase in ("ningun flag", "--effort")
        ),
                "claude/effort omite el flag", "claude/effort no conserva la omisión"),
        control("V6.codex-config-personal", frozenset(("codex", "model", "effort")) in datos and "raiz del config personal" in datos[frozenset(("codex", "model", "effort"))],
                "Codex toma ambos campos del config personal", "la resolución de Codex difiere"),
    ]


def verificar_9(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "Momentos de resolución y valores inválidos")
    filas = tabla_tras(seccion, "Cada momento tiene un observable y una autoridad propios:")
    datos = {norm(f[0]): (norm(f[1]), norm(f[2])) for f in filas[1:] if len(f) == 3}
    momentos = {"lanzamiento", "resume propio", "resume de seed"}
    observable_ok = set(datos) == momentos and all(
        frase in datos[m][0] for m, frase in {
            "lanzamiento": "perfil vigente del rol resuelto y enviado al proceso",
            "resume propio": "perfil persistido por el lanzamiento de esa misma corrida",
            "resume de seed": "perfil persistido por la sesion de origen",
        }.items()
    )
    autoridad_ok = set(datos) == momentos and "cadena de resolucion" in datos["lanzamiento"][1] and all(
        "perfil congelado" in datos[m][1] and "nunca el archivo vigente" in datos[m][1]
        for m in ("resume propio", "resume de seed")
    )
    return [
        control("V9.tres-momentos", set(datos) == momentos, "tres momentos exactos", f"momentos: {sorted(datos)}"),
        control("V9.observable-por-momento", observable_ok, "observable propio por momento", "falta un observable"),
        control("V9.autoridad-por-momento", autoridad_ok, "autoridad propia por momento", "falta o difiere una autoridad"),
    ]


def verificar_12(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "Momentos de resolución y valores inválidos")
    return controles_de_frases(seccion, {
        "V12.casos-del-enum": ("esfuerzo fuera del enum", "rol o familia desconocidos", "parámetro no admitido", "schema_version` desconocida", "YAML ilegible", "forma histórica de perfiles"),
        "V12.detiene-antes-de-despachar": ("se detiene antes de despachar",),
        "V12.nombra-valor": ("nombra el valor inválido",),
        "V12.nombra-ruta": ("la ruta del archivo",),
        "V12.sugiere-correccion": ("sugiere una corrección concreta",),
    })


def verificar_13(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "Momentos de resolución y valores inválidos")
    return controles_de_frases(seccion, {
        "V13.avisa": ("el aviso incluye",),
        "V13.reintenta-una-vez": ("se reintenta una sola vez", "no existe un tercer intento"),
        "V13.conserva-campo-valido": ("se conserva el otro campo válido",),
        "V13.segunda-falla-unavailable": ("segundo intento falla", "UNAVAILABLE"),
        "V13.datos-del-aviso": ("rol, familia, valor solicitado y valor efectivo",),
        "V13.congela-perfil-exitoso": ("perfil del intento exitoso queda congelado",),
        "V13.prohibe-sustitucion-del-conductor": ("prohibido sustituir", "valor del conductor"),
    })


def verificar_14(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "Momentos de resolución y valores inválidos")
    return controles_de_frases(seccion, {
        "V14.rama-con-diagnostico": ("diagnóstico del proveedor entrega una corrección", "la incorpora textualmente"),
        "V14.rama-sin-correccion-fiable": ("no hay una corrección fiable disponible",),
    })


def verificar_27(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "La cadena de resolución del perfil")
    historica = tabla_tras(seccion, "El valor histórico concreto del escalón 4")
    observada = {tuple(norm(c.replace("`", "")) for c in fila) for fila in historica[1:]}
    historico_ok = observada == {
        ("claude, rutas de juicio", "modelo opus cableado por la receta", "ningun flag; default del cli"),
        ("claude, rutas de implementacion", "modelo sonnet cableado por la receta", "ningun flag; default del cli"),
        ("codex, salvo bbcr-viab-posix, bbcr-viab-ps y prfb-codex", "raiz del config personal", "raiz del config personal"),
        ("codex, bbcr-viab-posix, bbcr-viab-ps y prfb-codex", "default del cli", "default del cli"),
    }
    return [
        *controles_de_frases(seccion, {
            "V27.sin-archivo": ("Sin archivo confirmado",),
            "V27.sin-override": ("sin override aplicable",),
            "V27.sin-congelado": ("sin perfil congelado",),
            "V27.alcance-embebido": ("invocaciones standalone", "rutas embebidas"),
            "V27.prohibe-escritura": ("Ninguna skill escribe `.specify/workers.yml`", "solo el paso `init`"),
        }),
        control("V27.valor-historico", historico_ok, "valor histórico concreto por vía", "la tabla histórica está incompleta"),
    ]


def verificar_28(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "La cadena de resolución del perfil")
    return controles_de_frases(seccion, {
        "V28.raiz-efectiva": ("raíz Git del directorio de trabajo", "Rige exclusivamente"),
        "V28.sin-consulta-ascendente": ("no se consulta un árbol padre o principal",),
        "V28.sin-fusion": ("no se fusionan archivos de dos raíces",),
    })


def verificar_29(texto: str) -> list[Chequeo]:
    seccion = seccion_workers(texto, "La cadena de resolución del perfil")
    escalones = tabla_tras(seccion, "Cada campo baja por separado")
    autoridades = {f[0].strip("` "): norm(f[1]) for f in escalones[1:] if len(f) == 3}
    cuatro_ok = autoridades == {
        "1": "perfil congelado de la sesion", "2": "override conversacional",
        "3": "archivo de la raiz efectiva", "4": "resolucion anterior",
    }
    estados = tabla_tras(seccion, "Descontado el estado terminal del archivo inválido")
    seis_ok = len(estados) == 7 and {tuple(norm(c) for c in f[:3]) for f in estados[1:]} == {
        ("reanudada", "cualquiera", "cualquiera"), ("fresca", "total", "cualquiera"),
        ("fresca", "parcial", "si"), ("fresca", "parcial", "no"),
        ("fresca", "no", "si"), ("fresca", "no", "no"),
    }
    return [
        control("V29.cuatro-escalones", cuatro_ok, "cuatro escalones exactos", f"escalones: {autoridades}"),
        *controles_de_frases(seccion, {
            "V29.por-campo": ("Cada campo baja por separado", "La resolución es por campo"),
            "V29.registro-de-origen": ("registra, por separado para `model` y `effort`, el número del escalón de origen",),
        }),
        control("V29.seis-estados", seis_ok, "seis estados exactos", "la tabla no contiene los seis estados"),
    ]


SEDES_REGIONES = (
    "skills/cross-review/reference.md",
    "skills/co-explore/reference.md",
    "skills/cross-implement/reference.md",
    "skills/bitbucket-code-review/reference.md",
    "skills/sdd-pr-feedback/reference.md",
)
# Rutas de reanudación: su autoridad es el perfil congelado (escalón 1), no el archivo.
REGIONES_RESUME = {
    "cr-resume-posix", "cr-resume-ps", "cr-seed-posix", "cr-seed-ps",
    "cr-viac-resume-posix", "cr-viac-resume-ps",
    "ci-wb-resume", "ci-wb-resume-ps", "ci-wc-fix",
}
# Las tres que históricamente no reinyectaban: su escalón 4 es el default del CLI.
SIN_REINYECCION_IDS = {"bbcr-viab-posix", "bbcr-viab-ps", "prfb-codex"}


def corpus_regiones() -> str:
    """Las 31 regiones marcadas, concatenadas. Es el corpus mutable de V8."""
    partes = []
    for sede in SEDES_REGIONES:
        texto = leer_texto(REPO / sede)
        for hallado in re.finditer(
            r"despacho:inicio:([a-z0-9-]+):(claude|codex) -->(.*?)<!-- despacho:fin:\1", texto, re.S
        ):
            partes.append(f"@@R {hallado.group(1)} {hallado.group(2)}@@\n{hallado.group(3)}")
    return "\n".join(partes)


def _es_powershell(region: str) -> bool:
    return region.endswith("-ps") or "-ps-" in region


def verificar_8(texto: str) -> list[Chequeo]:
    regiones = []
    for trozo in texto.split("@@R ")[1:]:
        cabecera, _, cuerpo = trozo.partition("@@\n")
        region, familia = cabecera.split()
        regiones.append((region, familia, cuerpo, _ejecutable(cuerpo)))

    def sin(predicado) -> list[str]:
        return [r for r, f, c, e in regiones if not predicado(r, f, c, e)]

    res: list[Chequeo] = []
    def tiene_model(r, f, c, e):
        if r in REGIONES_RESUME:
            return "ONGELADO" in c or "ongelado" in c or "scalón 1" in c
        return "PERFIL_MODEL" in e or "PerfilModel" in e

    def tiene_effort(r, f, c, e):
        if r in REGIONES_RESUME:
            return "ONGELADO" in c or "ongelado" in c or "scalón 1" in c
        return "PERFIL_EFFORT" in e or "PerfilEffort" in e
    mal = sin(tiene_model)
    res.append(control("V8.model-desde-perfil", not mal,
                       f"las {len(regiones)} regiones toman `model` del perfil",
                       f"no toman `model` del perfil: {mal}"))
    mal = sin(tiene_effort)
    res.append(control("V8.effort-desde-perfil", not mal,
                       f"las {len(regiones)} regiones toman `effort` del perfil",
                       f"no toman `effort` del perfil: {mal}"))

    claude = [x for x in regiones if x[1] == "claude"]
    mal = [r for r, f, c, e in claude if not re.search(r"\b(opus|sonnet)\b", c)]
    res.append(control("V8.heredado-claude-model-materializa", not mal and bool(claude),
                       "cada ruta Claude declara el modelo cableado que materializa `heredado`",
                       f"no declaran su modelo cableado: {mal}"))
    mal = [r for r, f, c, e in claude if "--effort" not in e]
    res.append(control("V8.heredado-claude-effort-omite", not mal and bool(claude),
                       "cada ruta Claude emite `--effort` solo cuando el perfil lo resuelve",
                       f"no contemplan la omisión del flag de esfuerzo: {mal}"))

    codex = [x for x in regiones if x[1] == "codex"]
    # `-m` como TOKEN, no como substring: "-m" está contenido en "--model", así que el predicado
    # ingenuo no puede ponerse rojo mientras la región mencione el flag largo en cualquier parte.
    flag_modelo = re.compile(r"(?<![\w-])-m(?![\w-])")
    mal = [r for r, f, c, e in codex if not flag_modelo.search(e)]
    res.append(control("V8.heredado-codex-model-materializa", not mal and bool(codex),
                       "cada ruta Codex emite el flag de modelo con el valor resuelto",
                       f"no emiten el flag de modelo: {mal}"))
    mal = [r for r, f, c, e in codex if "model_reasoning_effort" not in e]
    res.append(control("V8.heredado-codex-effort-materializa", not mal and bool(codex),
                       "cada ruta Codex emite `model_reasoning_effort` con el valor resuelto",
                       f"no emiten el esfuerzo: {mal}"))

    cableado = re.compile(r"--model[ ',]+(opus|sonnet)\b")
    mal = [r for r, f, c, e in regiones if cableado.search(e)]
    res.append(control("V8.sin-modelo-cableado", not mal,
                       "ninguna región deja un modelo cableado en su comando",
                       f"conservan un modelo cableado: {mal}"))

    posix = [x for x in regiones if not _es_powershell(x[0])]
    pwsh = [x for x in regiones if _es_powershell(x[0])]
    # La expansión PARTIDA es obligatoria: zsh no hace field splitting y `-m` viajaría pegado.
    parten = [x for x in posix if "${" in x[3] and ":+" in x[3]]
    mal = [r for r, f, c, e in parten if re.search(r"\$\{[A-Z_]+:\+-[a-z] ", e)]
    res.append(control("V8.forma-partida-posix", not mal,
                       f"las {len(parten)} regiones POSIX con expansión condicional la usan partida",
                       f"expansión sin partir (el flag viajaría pegado a su valor): {mal}"))
    def _compacto(texto: str) -> str:
        return re.sub(r"[ \t]+", " ", texto)

    mal = [r for r, f, c, e in pwsh
           if "Args = @(" not in _compacto(e) and "Args += @(" not in _compacto(e)]
    res.append(control("V8.forma-array-powershell", not mal and bool(pwsh),
                       f"las {len(pwsh)} regiones PowerShell construyen sus argumentos como array",
                       f"no usan array de argumentos: {mal}"))

    mal = [r for r, f, c, e in regiones if "cadena de resolución del perfil" not in c]
    res.append(control("V8.remite-a-la-cadena", not mal,
                       "las 31 remiten a la sede única de la cadena",
                       f"no remiten a la cadena: {mal}"))
    mal = [r for r, f, c, e in regiones
           if "scalón 4" not in c and "scalón 1" not in c and "ONGELADO" not in c]
    res.append(control("V8.escalon-4-declarado", not mal,
                       "cada región declara qué escalón la gobierna sin autoridad anterior",
                       f"no declaran su escalón: {mal}"))
    mal = [r for r, f, c, e in regiones
           if r in REGIONES_RESUME and "ONGELADO" not in c and "scalón 1" not in c]
    res.append(control("V8.resume-usa-congelado", not mal,
                       f"las {len(REGIONES_RESUME)} rutas de reanudación usan el perfil congelado",
                       f"una reanudación que no declara el congelado: {mal}"))

    # Ninguna región nombra el perfil de OTRA: eso sería compensar una ruta con la de al lado.
    ajenas = [r for r, f, c, e in regiones
              if any(otra in e for otra, _, _, _ in regiones if otra != r and len(otra) > 8)]
    res.append(control("V8.sin-compensacion-entre-rutas", not ajenas,
                       "ninguna región resuelve su perfil nombrando a otra",
                       f"regiones que nombran otra ruta en su comando: {ajenas}"))

    res.append(control("V8.cobertura-31-regiones", len(regiones) == 31,
                       f"se inspeccionaron las {len(regiones)} regiones marcadas del árbol",
                       f"se inspeccionaron {len(regiones)} regiones; se esperaban 31"))
    res.append(control("V8.cobertura-posix", len(posix) == 18,
                       f"las {len(posix)} regiones POSIX entran en la inspección",
                       f"{len(posix)} regiones POSIX; se esperaban 18"))
    res.append(control("V8.cobertura-powershell", len(pwsh) == 13,
                       f"las {len(pwsh)} regiones PowerShell entran en la inspección",
                       f"{len(pwsh)} regiones PowerShell; se esperaban 13"))
    return res


SIN_REINYECCION = {
    "bbcr-viab-posix": "skills/bitbucket-code-review/reference.md",
    "bbcr-viab-ps": "skills/bitbucket-code-review/reference.md",
    "prfb-codex": "skills/sdd-pr-feedback/reference.md",
}


def cuerpo_region(ruta: Path, region: str) -> str:
    texto = leer_texto(ruta)
    patron = r"despacho:inicio:%s:[a-z]+ -->(.*?)<!-- despacho:fin:%s" % (region, region)
    hallado = re.search(patron, texto, re.S)
    if hallado is None:
        raise MedicionDetenida(f"no existe la región {region} en {ruta}")
    return hallado.group(1)


def corpus_sin_reinyeccion() -> str:
    """Las tres regiones sin reinyección, concatenadas y delimitadas: es el corpus mutable de V10."""
    partes = [
        f"@@REGION {region}@@\n{cuerpo_region(REPO / ruta, region)}"
        for region, ruta in SIN_REINYECCION.items()
    ]
    return "\n".join(partes)


def _ejecutable(cuerpo: str) -> str:
    """Descarta comentarios y prosa: un texto que NOMBRA el literal no lo USA, y un control que no
    distingue las dos cosas queda verde con solo un comentario al lado."""
    return "\n".join(
        linea for linea in cuerpo.splitlines()
        if not linea.strip().startswith(("#", "**", ">"))
    )


def _usa_perfil(cuerpo: str) -> bool:
    vivo = _ejecutable(cuerpo)
    return ("PERFIL_MODEL" in vivo or "PerfilModel" in vivo) and (
        "PERFIL_EFFORT" in vivo or "PerfilEffort" in vivo
    )


def verificar_10(texto: str) -> list[Chequeo]:
    cuerpos = {region: "" for region in SIN_REINYECCION}
    for trozo in texto.split("@@REGION ")[1:]:
        region, _, resto = trozo.partition("@@\n")
        cuerpos[region.strip()] = resto

    resultados = [
        control(
            f"V10.{region}", _usa_perfil(cuerpos[region]),
            "referencia el perfil en sus dos campos",
            "no referencia el perfil en los dos campos fuera de la prosa",
        )
        for region in SIN_REINYECCION
    ]
    resultados.append(control(
        "V10.ambos-campos", all(_usa_perfil(c) for c in cuerpos.values()),
        "las tres regiones usan modelo y esfuerzo",
        "alguna región omite uno de los dos campos",
    ))
    resultados.append(control(
        "V10.fallback-historico",
        all("default del CLI" in c for c in cuerpos.values()),
        "las tres declaran su fallback histórico: el default del CLI",
        "alguna no declara qué se conserva cuando la cadena no resuelve",
    ))
    return resultados


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
    "3": Modo("3", "V3", "inicialización de workers", (
        "V3.muestra-defaults", "V3.muestra-delta", "V3.pide-confirmacion",
        "V3.no-pisa-archivo-valido",
    ), verificar_3),
    "4": Modo("4", "V4", "delta contra las rutas vigentes", (
        "V4.tres-columnas", "V4.procedencia", "V4.valor-anterior-o-indeterminado",
        "V4.perfil-nuevo", "V4.cambio-conocido",
    ), verificar_4),
    "5": Modo("5", "V5", "matriz de rutas por rol", (
        "V5.identidad-region-ruta", "V5.sin-faltantes", "V5.sin-sobrantes",
        "V5.ocho-roles-con-ruta",
    ), verificar_5),
    "6": Modo("6", "V6", "literal de herencia", (
        "V6.claude-model-cableado", "V6.claude-effort-sin-flag", "V6.codex-config-personal",
    ), verificar_6),
    "8": Modo("8", "V8", "el perfil llega al comando de cada ruta", (
        "V8.model-desde-perfil",
        "V8.effort-desde-perfil",
        "V8.heredado-claude-model-materializa",
        "V8.heredado-claude-effort-omite",
        "V8.heredado-codex-model-materializa",
        "V8.heredado-codex-effort-materializa",
        "V8.sin-modelo-cableado",
        "V8.forma-partida-posix",
        "V8.forma-array-powershell",
        "V8.remite-a-la-cadena",
        "V8.escalon-4-declarado",
        "V8.resume-usa-congelado",
        "V8.sin-compensacion-entre-rutas",
        "V8.cobertura-31-regiones",
        "V8.cobertura-posix",
        "V8.cobertura-powershell",
    ), verificar_8, corpus_regiones),
    "10": Modo("10", "V10", "las tres rutas sin reinyección", (
        "V10.bbcr-viab-posix",
        "V10.bbcr-viab-ps",
        "V10.prfb-codex",
        "V10.ambos-campos",
        "V10.fallback-historico",
    ), verificar_10, corpus_sin_reinyeccion),
    "7": Modo("7", "V7", "enum portable de esfuerzo", (
        "V7.cinco-literales",
        "V7.traduccion-claude",
        "V7.traduccion-codex",
        "V7.identidad-entre-familias",
    ), verificar_7),
    "9": Modo("9", "V9", "momentos de resolución", (
        "V9.tres-momentos", "V9.observable-por-momento", "V9.autoridad-por-momento",
    ), verificar_9),
    "12": Modo("12", "V12", "valores inválidos por forma", (
        "V12.casos-del-enum", "V12.detiene-antes-de-despachar", "V12.nombra-valor",
        "V12.nombra-ruta", "V12.sugiere-correccion",
    ), verificar_12),
    "13": Modo("13", "V13", "rechazo del proveedor", (
        "V13.avisa", "V13.reintenta-una-vez", "V13.conserva-campo-valido",
        "V13.segunda-falla-unavailable", "V13.datos-del-aviso", "V13.congela-perfil-exitoso",
        "V13.prohibe-sustitucion-del-conductor",
    ), verificar_13),
    "14": Modo("14", "V14", "corrección del diagnóstico", (
        "V14.rama-con-diagnostico", "V14.rama-sin-correccion-fiable",
    ), verificar_14),
    "27": Modo("27", "V27", "resolución anterior", (
        "V27.sin-archivo", "V27.sin-override", "V27.sin-congelado", "V27.alcance-embebido",
        "V27.prohibe-escritura", "V27.valor-historico",
    ), verificar_27),
    "28": Modo("28", "V28", "raíz efectiva", (
        "V28.raiz-efectiva", "V28.sin-consulta-ascendente", "V28.sin-fusion",
    ), verificar_28),
    "29": Modo("29", "V29", "cadena por campo", (
        "V29.cuatro-escalones", "V29.por-campo", "V29.registro-de-origen",
        "V29.seis-estados",
    ), verificar_29),
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
    "V8.model-desde-perfil": mutar("V8.model-desde-perfil",
        'MODEL="${PERFIL_MODEL:-sonnet}"', 'MODEL="sonnet"'),
    "V8.effort-desde-perfil": mutar("V8.effort-desde-perfil",
        'EFFORT="$PERFIL_EFFORT"\n  set -- -p --safe-mode --model "$MODEL" --permission-mode default \\\n         \'--allowedTools=Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)\' \\\n         --session-id "$SESSION_ID"',
        'EFFORT="alto"\n  set -- -p --safe-mode --model "$MODEL" --permission-mode default \\\n         \'--allowedTools=Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)\' \\\n         --session-id "$SESSION_ID"'),
    "V8.heredado-claude-model-materializa": mutar("V8.heredado-claude-model-materializa",
        '`sonnet`,\n  # el modelo cableado de esta ruta de implementación, y ningún flag de esfuerzo.\n  MODEL="${PERFIL_MODEL:-sonnet}"',
        'el modelo por defecto del CLI.\n  MODEL="$PERFIL_MODEL"'),
    "V8.heredado-claude-effort-omite": mutar("V8.heredado-claude-effort-omite",
        '[ -n "$EFFORT" ] && set -- "$@" --effort "$EFFORT"\n  ( cd <working_dir> && claude "$@" \\\n      < <scratch>/prompt.txt )',
        '( cd <working_dir> && claude "$@" \\\n      < <scratch>/prompt.txt )'),
    "V8.heredado-codex-model-materializa": mutar("V8.heredado-codex-model-materializa",
        '  if ($Model)  { $ResumeArgs += @(\'-m\', $Model) }\n  if ($Effort) { $ResumeArgs += @(\'-c\', "model_reasoning_effort=$Effort") }',
        '  if ($Effort) { $ResumeArgs += @(\'-c\', "model_reasoning_effort=$Effort") }'),
    "V8.heredado-codex-effort-materializa": mutar("V8.heredado-codex-effort-materializa",
        '${PERFIL_EFFORT:+-c} ${PERFIL_EFFORT:+"model_reasoning_effort=$PERFIL_EFFORT"} ', ''),
    "V8.sin-modelo-cableado": mutar("V8.sin-modelo-cableado",
        'MODEL="${PERFIL_CONGELADO_MODEL:-sonnet}"', '--model sonnet'),
    "V8.forma-partida-posix": mutar("V8.forma-partida-posix",
        '${MODEL:+-m} ${MODEL:+"$MODEL"} \\', '${MODEL:+-m "$MODEL"} \\'),
    "V8.forma-array-powershell": mutar("V8.forma-array-powershell",
        "  $ClaudeArgs  = @('-p','--safe-mode','--model',$ModelClaude,'--permission-mode','default',\n                   '--allowedTools=Read,Grep,Glob','--session-id',$SessionId)\n  if ($PerfilEffort) { $ClaudeArgs += @('--effort', $PerfilEffort) }\n  Get-Content -Raw <raíz-repo>\\.pr-review\\<id>\\prompt.txt |\n    claude @ClaudeArgs `",
        '  $ClaudeArgs  = "-p --safe-mode --model $ModelClaude --session-id $SessionId"\n  Get-Content -Raw <raíz-repo>\\.pr-review\\<id>\\prompt.txt |\n    claude $ClaudeArgs `'),
    "V8.remite-a-la-cadena": mutar("V8.remite-a-la-cadena",
        '# Escalón 1 de la cadena de `sdd-flow/reference.md` → "La cadena de resolución del perfil": el seed\n# transporta el perfil CONGELADO —`model` y `effort` juntos— y es la autoridad de esta reanudación.\nSEED=',
        '# Escalón 1: el seed transporta el perfil congelado.\nSEED='),
    "V8.escalon-4-declarado": mutar("V8.escalon-4-declarado",
        "# Escalón 4 — el valor histórico CONCRETO de esta ruta es el **default del CLI**",
        "# El valor de esta ruta"),
    "V8.resume-usa-congelado": mutar("V8.resume-usa-congelado",
        '# Escalón 1 de la cadena de `sdd-flow/reference.md` → "La cadena de resolución del perfil":\n  # en una reanudación la autoridad es el perfil CONGELADO',
        '# Cadena de resolución del perfil: la autoridad es el archivo vigente'),
    "V8.sin-compensacion-entre-rutas": mutar("V8.sin-compensacion-entre-rutas",
        'SEED=<sesión que resuelva la matriz', 'SEED=coex-fanout-posix-codex <sesión que resuelva la matriz'),
    "V8.cobertura-31-regiones": mutar("V8.cobertura-31-regiones",
        '@@R prfb-codex codex@@',
        '@@OCULTA prfb-codex codex@@'),
    "V8.cobertura-posix": mutar("V8.cobertura-posix",
        '@@R cr-ronda1-posix codex@@',
        '@@R cr-ronda1-alt-ps codex@@'),
    "V8.cobertura-powershell": mutar("V8.cobertura-powershell",
        '@@R cr-ronda1-ps codex@@',
        '@@R cr-ronda1-alterna codex@@'),
    "V10.bbcr-viab-posix": mutar("V10.bbcr-viab-posix",
        'MODEL="$PERFIL_MODEL"', 'MODEL="opus"'),
    "V10.bbcr-viab-ps": mutar("V10.bbcr-viab-ps",
        "if ($PerfilModel)  { $CodexArgs += @('-m', $PerfilModel) }",
        "$CodexArgs += @('-m', 'gpt-5.6-sol')"),
    "V10.prfb-codex": mutar("V10.prfb-codex",
        '${PERFIL_MODEL:+-m} ${PERFIL_MODEL:+"$PERFIL_MODEL"}', "-m gpt-5.6-sol"),
    "V10.ambos-campos": mutar("V10.ambos-campos",
        'EFFORT="$PERFIL_EFFORT"', 'EFFORT="alto"'),
    "V10.fallback-historico": mutar("V10.fallback-historico",
        "el valor histórico CONCRETO de esta ruta es el **default del CLI**",
        "el valor de esta ruta se toma del config personal"),
    "V7.identidad-entre-familias": mutar("V7.identidad-entre-familias",
        "| `maximo` | `max` | `max` |",
        "| `maximo` | `max` | `maximum` |",
    ),
}

MUTANTES.update({
    "V3.muestra-defaults": mutar("V3.muestra-defaults",
        "| `implement` | `sonnet` / `medio` | `gpt-5.6-terra` / `medio` |",
        "| `implement` | `sonnet` / `medio` | `gpt-5.6-sol` / `medio` |"),
    "V3.muestra-delta": mutar("V3.muestra-delta", "y el delta de abajo antes de escribir", "antes de escribir"),
    "V3.pide-confirmacion": mutar("V3.pide-confirmacion", "solo tras una confirmación explícita", "sin confirmación"),
    "V3.no-pisa-archivo-valido": mutar("V3.no-pisa-archivo-valido", "lo\nconserva sin sobrescribirlo", "lo sobrescribe"),
    "V4.tres-columnas": mutar("V4.tres-columnas",
        "| Región, ruta y familia | Procedencia y valor anterior | Perfil nuevo y cambio conocido |",
        "| Región y familia | Procedencia y valor anterior | Perfil nuevo y cambio conocido |"),
    "V4.procedencia": mutar("V4.procedencia",
        "procedencia: modelo cableado por la receta y default del CLI; valor anterior: `sonnet`",
        "origen omitido; valor anterior: `sonnet`"),
    "V4.valor-anterior-o-indeterminado": mutar("V4.valor-anterior-o-indeterminado",
        "procedencia: reinyección de la raíz del config personal; valor anterior: modelo y esfuerzo `indeterminado`",
        "procedencia: reinyección de la raíz del config personal"),
    "V4.perfil-nuevo": mutar("V4.perfil-nuevo",
        "perfil nuevo: `pr` y `refute`", "resultado: `pr` y `refute`"),
    "V4.cambio-conocido": mutar("V4.cambio-conocido",
        "`investigate` y `design-review` → `opus` / `muy_alto`; cambio conocido: modelo no cambia, esfuerzo indeterminado",
        "`investigate` y `design-review` → `opus` / `muy_alto`; cambio no declarado"),
    "V5.identidad-region-ruta": mutar("V5.identidad-region-ruta",
        "| `cr-ronda1-posix` | `design-review` | `design-review` |",
        "| `cr-ronda1-posix` | `design-review` | `implement` |"),
    "V5.sin-faltantes": mutar("V5.sin-faltantes",
        "| `cr-ronda1-ps` | `design-review` | `design-review` |\n", ""),
    "V5.sin-sobrantes": mutar("V5.sin-sobrantes",
        "| `prfb-codex` | `implement` | `implement` |",
        "| `prfb-codex` | `implement` | `implement` |\n| `ruta-inexistente` | `implement` | `implement` |"),
    "V5.ocho-roles-con-ruta": mutar("V5.ocho-roles-con-ruta",
        "Los ocho roles tienen al menos una ruta", "Los roles aparecen en la matriz"),
    "V6.claude-model-cableado": mutar("V6.claude-model-cableado",
        "el modelo cableado de esa ruta: `opus` en las doce regiones de juicio y `sonnet` en las dos de implementación",
        "el default del CLI"),
    "V6.claude-effort-sin-flag": mutar("V6.claude-effort-sin-flag",
        "ningún flag `--effort`; rige el default del CLI", "el flag `--effort alto`"),
    "V6.codex-config-personal": mutar("V6.codex-config-personal",
        "el valor de la raíz del config personal del usuario", "el default del CLI"),
    "V9.tres-momentos": mutar("V9.tres-momentos",
        "| resume de seed | perfil persistido por la sesión de origen, aunque difiera del perfil vigente del rol | perfil congelado de la sesión de origen; nunca el archivo vigente |\n", ""),
    "V9.observable-por-momento": mutar("V9.observable-por-momento",
        "perfil vigente del rol resuelto y enviado al proceso", "perfil observado"),
    "V9.autoridad-por-momento": mutar("V9.autoridad-por-momento",
        "perfil congelado de la sesión; nunca el archivo vigente",
        "el archivo vigente"),
    "V12.casos-del-enum": mutar("V12.casos-del-enum",
        "esfuerzo fuera del enum; rol o familia desconocidos; parámetro no",
        "esfuerzo fuera del enum; parámetro no"),
    "V12.detiene-antes-de-despachar": mutar("V12.detiene-antes-de-despachar",
        "La validación local se detiene antes de despachar", "La validación local continúa el despacho"),
    "V12.nombra-valor": mutar("V12.nombra-valor", "nombra el valor inválido", "nombra el error"),
    "V12.nombra-ruta": mutar("V12.nombra-ruta", "la ruta del archivo", "el archivo"),
    "V12.sugiere-correccion": mutar("V12.sugiere-correccion",
        "sugiere una corrección concreta", "solicita reintentar"),
    "V13.avisa": mutar("V13.avisa", "el aviso incluye rol", "el registro incluye rol"),
    "V13.reintenta-una-vez": mutar("V13.reintenta-una-vez",
        "Se reintenta una sola vez", "Se reintenta hasta que funcione"),
    "V13.conserva-campo-valido": mutar("V13.conserva-campo-valido",
        "se conserva el otro campo válido", "se omiten ambos campos"),
    "V13.segunda-falla-unavailable": mutar("V13.segunda-falla-unavailable",
        "Si el segundo intento falla, el worker queda `UNAVAILABLE`",
        "Si el segundo intento falla, se vuelve a intentar"),
    "V13.datos-del-aviso": mutar("V13.datos-del-aviso",
        "rol,\nfamilia, valor solicitado y valor efectivo", "familia y valor efectivo"),
    "V13.congela-perfil-exitoso": mutar("V13.congela-perfil-exitoso",
        "El perfil del intento exitoso queda congelado", "El perfil se vuelve a resolver"),
    "V13.prohibe-sustitucion-del-conductor": mutar("V13.prohibe-sustitucion-del-conductor",
        "Está prohibido sustituir el campo rechazado por el valor del conductor",
        "El conductor sustituye el campo rechazado"),
    "V14.rama-con-diagnostico": mutar("V14.rama-con-diagnostico",
        "diagnóstico del proveedor entrega una corrección, la incorpora\ntextualmente",
        "diagnóstico del proveedor entrega una corrección, la omite"),
    "V14.rama-sin-correccion-fiable": mutar("V14.rama-sin-correccion-fiable",
        "declara expresamente que no hay una corrección fiable disponible",
        "omite la corrección"),
    "V27.sin-archivo": mutar("V27.sin-archivo", "Sin archivo confirmado, sin override", "Con archivo confirmado, sin override"),
    "V27.sin-override": mutar("V27.sin-override", "sin override aplicable y sin perfil", "con override aplicable y sin perfil"),
    "V27.sin-congelado": mutar("V27.sin-congelado", "sin perfil congelado, una ruta fresca", "con perfil congelado, una ruta fresca"),
    "V27.alcance-embebido": mutar("V27.alcance-embebido",
        "invocaciones standalone como rutas embebidas", "invocaciones standalone"),
    "V27.prohibe-escritura": mutar("V27.prohibe-escritura",
        "Ninguna skill escribe `.specify/workers.yml`", "Cada skill puede escribir `.specify/workers.yml`"),
    "V27.valor-historico": mutar("V27.valor-historico",
        "| Codex, `bbcr-viab-posix`, `bbcr-viab-ps` y `prfb-codex` | default del CLI | default del CLI |",
        "| Codex, `bbcr-viab-posix`, `bbcr-viab-ps` y `prfb-codex` | valor nuevo | valor nuevo |"),
    "V28.raiz-efectiva": mutar("V28.raiz-efectiva",
        "raíz Git del directorio de trabajo de la corrida", "raíz del árbol principal"),
    "V28.sin-consulta-ascendente": mutar("V28.sin-consulta-ascendente",
        "no se consulta un árbol padre o principal", "se consulta el árbol principal"),
    "V28.sin-fusion": mutar("V28.sin-fusion",
        "no se fusionan archivos de dos\nraíces", "se fusionan archivos de dos raíces"),
    "V29.cuatro-escalones": mutar("V29.cuatro-escalones",
        "| 4 | resolución anterior | solo el campo que ningún escalón anterior resolvió; rige en corridas standalone y embebidas |",
        "| 4 | defaults globales | completa el perfil |"),
    "V29.por-campo": mutar("V29.por-campo", "Cada campo baja por separado", "El perfil baja como unidad"),
    "V29.registro-de-origen": mutar("V29.registro-de-origen",
        "registra, por separado para `model` y `effort`, el número del escalón de origen",
        "registra el perfil resuelto"),
    "V29.seis-estados": mutar("V29.seis-estados",
        "| fresca | no | no | resolución anterior en ambos campos |\n", ""),
})


def inventario_hojas(ruta: Path) -> tuple[list[str], str | None]:
    texto = leer_texto(ruta)
    seccion = extraer_seccion(texto, "Hojas normativas de v1", 4)
    if seccion is None:
        raise MedicionDetenida(f"no existe la sección #### Hojas normativas de v1 en {ruta}")
    prefijos = tuple(f"{modo.fila}." for modo in MODOS.values())
    # Solo las LÍNEAS DE DECLARACIÓN (`- **Vn** — ...`). Grepear la sección entera captura además las
    # menciones en prosa —una nota que explica que una hoja se partió en dos, por ejemplo— y las suma
    # al inventario como si fueran hojas: el mismo defecto de medir la mención en vez de la
    # declaración.
    declaradas = [
        linea for linea in seccion.splitlines()
        if re.match(r"^\s*[-*]\s+\*\*V\d+\*\*\s+—", linea)
    ]
    hojas = [
        hoja for linea in declaradas
        for hoja in re.findall(r"`(V\d+\.[^`]+)`", linea)
        if hoja.startswith(prefijos)
    ]
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
        corpus_por_modo = {clave: modo.texto_base() for clave, modo in MODOS.items()}
    except MedicionDetenida as exc:
        return 3, lineas + [f"MEDICIÓN DETENIDA — {exc}; no hay veredicto."]

    fallas: list[str] = []
    for clave, modo in MODOS.items():
        resultados = modo.ejecutar(corpus_por_modo[clave])
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
        clave = next(k for k, m in MODOS.items() if hoja in m.controles)
        modo = MODOS[clave]
        corpus = corpus_por_modo[clave]
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
        # el corpus DEL MODO, no el reference.md por defecto: V8 y V10 miran otras sedes, y pasarles
        # el corpus equivocado los deja en rojo por leer el archivo que no les toca
        texto = modo.texto_base()
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
