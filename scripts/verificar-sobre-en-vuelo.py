#!/usr/bin/env python3
"""Verifica el contrato del **sobre de corrida delegada en vuelo** (flujo `hilo-workers-en-vuelo`).

Un modo por fila de la tabla `## Verification` del plan — veinte en total, `--ac 1` … `--ac 17`
con sus variantes `1b`/`2b`/`3b` — más `--sincronizar` (genera las seis copias desde la fuente),
`--validar-baseline` (comprueba el bloque `#### Baseline de vN` versionado bajo `scripts/`) y
`--autotest` (control positivo sobre un corpus verde temporal, y después un mutante por vez).

Tres reglas de diseño, heredadas del plan y de las tasks:

1. **Sin `grep`/`awk`/`sed`.** En esta máquina `grep` es ugrep 7.5.0 y difiere de BSD grep en regex
   con anclas internas: el mismo patrón devolvió 1 y 0. Todo el parseo es Python + stdlib.
   `subprocess` se usa solo para `git show` y para invocar las guardas del repo en `--ac 16`.
2. **Expectativas declarativas por conjunto exacto: sobra tanto como falta.** Un conteo no prueba un
   conjunto, y una coincidencia parcial no prueba una tupla fila→valor.
3. **El congelamiento original se levantó para retirar el transporte de multiplexor.** La migración
   in-place conserva los modos y versiona su nueva identidad como baseline `v2`; cualquier cambio
   posterior vuelve a exigir una versión nueva y el `sha256` de los bytes vigentes.

Formato que este verificador espera de los artefactos que lee (lo fija él, porque es quien mide):

- **Conjuntos de campos** (`### Los campos del sobre`, etc.): una fila de tabla —o, si la sección no
  tiene tabla, un ítem de lista sin indentar— por campo, con el nombre del campo entre backticks al
  principio. Si hay tabla en la sección, manda la tabla.
- **Sub-esquemas**: forma canónica `nombre = {a, b, c}`, en una línea.
- **Tablas de vocabulario cerrado** (outcomes, fuente por transporte, precedencia): la primera celda
  nombra la fila; alguna de las celdas siguientes lleva el valor del enum, preferentemente entre
  backticks.
- **Baseline** (`#### Baseline de vN`): tabla con columnas `ID | commit | sha256 | timestamp |
  estado | adjudicación`, un registro por fila de `## Verification`, en el mismo orden y sin rangos.

Uso: python3 scripts/verificar-sobre-en-vuelo.py --ac 1 | --autotest | --sincronizar | …
Exit 0 si el modo pasa, 1 si falla, 2 si la invocación es inválida.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHANGE_BASE_COMMIT = "2ed62dd"
BASELINE_PATH = "scripts/baseline-sobre-en-vuelo.md"
CONMUTACION_LOCK = ".cross-model/conmutacion.lock"

SKILLS = [
    "bitbucket-code-review",
    "co-explore",
    "cross-implement",
    "cross-review",
    "sdd-flow",
    "sdd-orchestrator",
    "sdd-pr-feedback",
]
CONTRATO_FUENTE = "skills/cross-review/corridas-en-vuelo.md"
CONTRATO = "corridas-en-vuelo.md"
COPIAS = [f"skills/{s}/{CONTRATO}" for s in SKILLS]

# La sede que rechaza el estado persistido (AC-1). Su conservación textual se comprueba en
# `--ac 1b` y la ausencia de reglas locales de retiro en `--ac 2`.
SEDES_RECHAZO = [
    "skills/co-explore/reference.md",
]
READMES = [f"skills/{s}/README.md" for s in
           ("co-explore", "cross-review", "cross-implement", "bitbucket-code-review")]

CAMPOS_RAIZ = {"run_id", "skill", "mode", "owner", "parent", "children", "descendants_summary",
               "workers", "scope", "transport", "harvest_pending", "proxima_accion",
               "manifest_seed", "manifest_first_dispatch_at"}
CAMPOS_WORKER = {"name", "family", "write", "attempts"}
CAMPOS_INTENTO = {"attempt_id", "transport", "output", "process_ref", "wait_budget", "harvested"}
SUBESQUEMAS = {
    "wait_budget": {"deadline", "limite", "consumidos"},
    "process_ref": {"tipo", "referencia", "evidencia_de_frescura", "autoridad"},
}

TRANSICIONES = {"nace", "relee", "cosecha", "retira"}
# Outcome de la espera → efecto del enum. `corte_presupuesto` deja el sobre activo porque "vencer el
# deadline nunca retira el sobre" (AC-2); `error` es un terminal comprobado y por eso habilita
# evaluar el retiro; la cancelación se parte en dos tuplas condicionales (AC-11).
ENUM_OUTCOME = ("habilita_evaluar_retiro", "sigue_activo", "recovery-required")
OUTCOMES = [
    (("resultado_entregado",), "habilita_evaluar_retiro"),
    (("corte_presupuesto",), "sigue_activo"),
    (("error",), "habilita_evaluar_retiro"),
    (("cancelacion", "cese_confirmado"), "habilita_evaluar_retiro"),
    (("cancelacion", "cese_incierto"), "recovery-required"),
]
ENUM_FUENTE = ("archivo+proceso", "archivo", "proceso", "ninguna")
FUENTES = [
    (("subagent",), "ninguna"),
    (("cli-exec",), "archivo+proceso"),
    (("cli-resume",), "archivo+proceso"),
]
ENUM_PRECEDENCIA = ("cosechar", "clasificar_error", "informar_activo", "esperar_cleanup")
PRECEDENCIA = [
    (("d1",), "cosechar", ["proceso activo", "artefacto completo"]),
    (("d2",), "clasificar_error", ["proceso terminado"]),
    (("d3",), "informar_activo", ["deadline"]),
    (("d4",), "esperar_cleanup", ["cleanup"]),
]

# Los once puntos de despacho del inventario del plan, por skill, con la señal que los identifica.
PUNTOS_DESPACHO = {
    "co-explore": {"fan-out dual": ["fan-out dual"], "debate": ["debate"]},
    "cross-review": {"revisor por ronda": ["revisor por ronda"]},
    "cross-implement": {"implementador inicial": ["implementador inicial"],
                        "fix loop": ["fix loop"]},
    "sdd-flow": {"exploración en analyze": ["analyze"],
                 "revisión final de diff": ["revision final"]},
    "sdd-orchestrator": {"fan-out por repo": ["fan-out por repo"]},
    "sdd-pr-feedback": {"implement delegado": ["implement delegado"]},
    "bitbucket-code-review": {"panel de revisores": ["panel de revisores"],
                              "validador adversarial": ["validador adversarial"]},
}

# Frases que, sobrevivientes en la sede de rechazo, dejarían una regla local de retiro compitiendo con
# las tres condiciones del contrato (T11 paso 4).
RETIRO_LOCAL_PROHIBIDO = ["la unica salida", "transferencia de ownership quedo fuera"]

# Construcciones operativas que deben sobrevivir en su sección concreta. La matriz se contrasta
# contra CHANGE_BASE_COMMIT para impedir que se autoajuste a un borrado del árbol vigente.
#
# El cuarto elemento es OPCIONAL y solo aparece cuando la construcción **se dijo con otras palabras**
# entre el commit base y hoy: entonces el anclaje se comprueba con esa redacción histórica y la
# presencia con la vigente. No es una alternancia —una sola redacción satisface cada lado, no
# cualquiera de las dos—, y por eso sigue siendo imposible autoajustar la matriz a un borrado: la
# construcción tiene que existir en los dos commits, cada uno con su forma. Sin el cuarto elemento,
# ambos lados usan el mismo requisito, que es el caso normal.
CONSERVAR = {
    "skills/co-explore/reference.md": [
        ("orden posterior a la retoma", "Truncado previo al dispatch",
         [["corre despues", "decision de retoma", "nunca al entrar"]]),
        ("limpieza previa al lanzamiento", "Truncado previo al dispatch",
         [["formas de cierre", "temporales", "recien despues", "lanza"]]),
        # Las dos de abajo cambiaron de referente al retirarse el transporte de multiplexor: el
        # descriptor de esa vía pasó a ser el sobre genérico, y "propio vivo" —que venía del recurso
        # de esa vía— pasó a ser el intento que todavía puede escribir. La garantía es la misma.
        ("sobre incluido en la limpieza", "Truncado previo al dispatch",
         [["sobre de corrida", "conjunto evaluado", "antes de redespachar"]],
         [["descriptor", "conjunto truncado", "redespacho", "antes de lanzar"]]),
        ("recurso vivo reserva sus rutas", "Truncado previo al dispatch",
         [["intento anterior", "bloquea", "truncado", "redespacho", "rutas"]],
         [["propio vivo", "bloquea", "truncado", "redespacho", "rutas"]]),
    ],
}

# Dueños y vistas de la config del repo (AC-15). La primera vista refleja la unión de sus cuatro
# dueños; la segunda refleja su dueño menos las claves de estado de corrida.
DUENOS_CONFIG = [
    ("skills/sdd-flow/reference.md", r"Esquema de `\.specify/config\.yml`"),
    ("skills/cross-review/SKILL.md", r"Configuración"),
    ("skills/co-explore/SKILL.md", r"Configuración"),
    ("skills/cross-implement/SKILL.md", r"Configuración"),
]
VISTA_CONFIG = ("skills/sdd-flow/config-ejemplo.md", r"Ejemplo de `\.specify/config\.yml`")
DUENO_MANIFEST = ("skills/sdd-orchestrator/reference.md", r"Esquema de `manifest\.yml`")
VISTA_MANIFEST = ("skills/sdd-orchestrator/manifest-ejemplo.md", r"Ejemplo de `manifest\.yml`")
SUPERFICIES_CONFIG = DUENOS_CONFIG + [VISTA_CONFIG, DUENO_MANIFEST, VISTA_MANIFEST]
_VISTAS_SPEC = spec_from_file_location("verificar_vistas_config",
                                       REPO / "scripts/verificar-vistas-config.py")
if _VISTAS_SPEC is None or _VISTAS_SPEC.loader is None:
    raise ImportError("no se pudo importar scripts/verificar-vistas-config.py")
_VISTAS_CONFIG = module_from_spec(_VISTAS_SPEC)
_VISTAS_SPEC.loader.exec_module(_VISTAS_CONFIG)
CLAVES_ESTADO_CORRIDA = _VISTAS_CONFIG.CLAVES_ESTADO_CORRIDA

GUARDAS = [
    ["python3", "scripts/verificar-vistas-config.py"],
    ["python3", "-m", "tests"],
]

ESTADOS_BASELINE = {"RED", "GREEN", "GREEN_ALREADY"}

# ---------------------------------------------------------------------------------------------
# Parser común: normalización, secciones, tablas, declaraciones, formas canónicas.
# ---------------------------------------------------------------------------------------------

_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+\.)\s+(.*)$")
_BACKTICK = re.compile(r"`([^`\n]+)`")


def norm(texto: str) -> str:
    """Minúsculas, sin diacríticos, sin énfasis markdown ni backticks, con la puntuación de
    enumeración convertida en espacio y los espacios colapsados."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    for ch in "`*·—–…":
        texto = texto.replace(ch, " ")
    return re.sub(r"\s+", " ", texto).strip().lower()


def leer(raiz: Path, rel: str) -> str | None:
    ruta = raiz / rel
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def seccion(texto: str, titulo: str) -> str | None:
    """Cuerpo del primer encabezado cuyo texto normalizado contiene `titulo`, hasta el próximo
    encabezado de nivel menor o igual."""
    objetivo = norm(titulo)
    lineas = texto.split("\n")
    inicio = nivel = None
    for i, linea in enumerate(lineas):
        m = re.match(r"^(#+)\s+(.*)$", linea)
        if not m:
            continue
        if inicio is None:
            if objetivo in norm(m.group(2)):
                inicio, nivel = i, len(m.group(1))
            continue
        if len(m.group(1)) <= nivel:
            return "\n".join(lineas[inicio + 1:i])
    return None if inicio is None else "\n".join(lineas[inicio + 1:])


def seccion_exacta(texto: str, titulo: str) -> str | None:
    """Como `seccion`, pero exige igualdad del encabezado para no confundir comentarios de código."""
    objetivo = norm(titulo)
    lineas = texto.split("\n")
    inicio = nivel = None
    for i, linea in enumerate(lineas):
        m = re.match(r"^(#+)\s+(.*)$", linea)
        if not m:
            continue
        if inicio is None:
            if norm(m.group(2)) == objetivo:
                inicio, nivel = i, len(m.group(1))
            continue
        if len(m.group(1)) <= nivel:
            return "\n".join(lineas[inicio + 1:i])
    return None if inicio is None else "\n".join(lineas[inicio + 1:])


def tablas(texto: str) -> list[list[list[str]]]:
    """Toda tabla markdown del texto, como lista de filas de celdas (encabezado incluido, fila
    separadora descartada)."""
    salida, actual = [], []
    for linea in texto.split("\n"):
        s = linea.strip()
        if s.startswith("|") and s.count("|") >= 2:
            celdas = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in celdas if c):
                actual.append(celdas)
            continue
        if actual:
            salida.append(actual)
            actual = []
    if actual:
        salida.append(actual)
    return [t for t in salida if len(t) >= 2]


def declaraciones(texto: str) -> list[str]:
    """Una entrada por elemento declarado: las filas del cuerpo de las tablas si el texto tiene
    alguna, y si no los ítems de lista sin indentar (con sus líneas de continuación)."""
    tabs = tablas(texto)
    if tabs:
        return [" | ".join(fila) for t in tabs for fila in t[1:]]
    items, actual = [], None
    for linea in texto.split("\n"):
        m = _ITEM.match(linea)
        if m and not m.group(1):
            if actual is not None:
                items.append(actual)
            actual = m.group(2)
        elif actual is not None:
            if not linea.strip():
                items.append(actual)
                actual = None
            elif not _ITEM.match(linea):
                actual += " " + linea.strip()
            else:
                items.append(actual)
                actual = None
    if actual is not None:
        items.append(actual)
    return items


def nombre_declarado(declaracion: str) -> str | None:
    """Primer token entre backticks de una declaración, que es como se nombra un campo."""
    m = _BACKTICK.search(declaracion)
    if not m:
        return None
    tok = m.group(1).strip().strip(".,;:")
    return tok if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\[\])?", tok) else None


def conjunto_canonico(texto: str, nombre: str) -> list[str] | None:
    """Elementos de la forma canónica `nombre = {a, b, c}`, en orden de aparición."""
    m = re.search(rf"{re.escape(nombre)}\s*=\s*\{{([^}}]*)\}}", texto.replace("`", ""))
    if not m:
        return None
    return [p.strip() for p in m.group(1).split(",") if p.strip()]


def valor_enum(celdas: list[str], enum: tuple[str, ...]) -> str | None:
    """Valor del enum que declara una fila. Prefiere los tokens entre backticks; si no hay, cae a
    subcadena, quedándose con el token más largo (para que `archivo+proceso` no se lea `archivo`)."""
    tokens = {t.strip() for c in celdas for t in _BACKTICK.findall(c)}
    encontrados = [v for v in enum if v in tokens]
    if not encontrados:
        texto = norm(" ".join(celdas))
        encontrados = [v for v in enum if norm(v) in texto]
        encontrados = [v for v in encontrados
                       if not any(v != o and norm(v) in norm(o) for o in encontrados)]
    return encontrados[0] if len(encontrados) == 1 else None


def cubre(texto_norm: str, requisito) -> bool:
    """requisito = lista de alternativas; cada alternativa, lista de subcadenas que deben estar
    todas presentes (AND dentro de la alternativa, OR entre alternativas)."""
    return any(all(norm(s) in texto_norm for s in alt) for alt in requisito)


# ---------------------------------------------------------------------------------------------
# Resultado de un chequeo y utilidades de comparación.
# ---------------------------------------------------------------------------------------------


class Ctx:
    """Acumulador de chequeos de un modo."""

    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.filas: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, nombre: str, detalle: str = "") -> bool:
        self.filas.append((bool(ok), nombre, detalle))
        return bool(ok)

    def texto(self, rel: str) -> str | None:
        t = leer(self.raiz, rel)
        if t is None:
            self.check(False, f"{rel}", "el archivo no existe")
        return t

    def seccion(self, rel: str, titulo: str) -> str | None:
        t = leer(self.raiz, rel)
        if t is None:
            self.check(False, f"{rel} → «{titulo}»", "el archivo no existe")
            return None
        s = seccion(t, titulo)
        if s is None:
            self.check(False, f"{rel} → «{titulo}»", "no existe el encabezado")
        return s

    def seccion_exacta(self, rel: str, titulo: str) -> str | None:
        t = leer(self.raiz, rel)
        if t is None:
            self.check(False, f"{rel} → «{titulo}»", "el archivo no existe")
            return None
        s = seccion_exacta(t, titulo)
        if s is None:
            self.check(False, f"{rel} → «{titulo}»", "no existe el encabezado exacto")
        return s

    def contrato(self) -> str | None:
        return self.texto(CONTRATO_FUENTE)

    def exigir(self, texto: str | None, etiqueta: str, requisitos: dict) -> None:
        """Cada requisito se busca **dentro de un mismo párrafo o bloque**, nunca contra el archivo
        entero: un README daba por declarada la independencia del manifest porque decía
        "verificación independiente" cuatro mil caracteres más arriba."""
        if texto is None:
            for nombre in requisitos:
                self.check(False, f"{etiqueta}: {nombre}", "no hay texto que leer")
            return
        bloques = [norm(b) for b in re.split(r"\n\s*\n", texto) if b.strip()]
        for nombre, req in requisitos.items():
            ok = any(cubre(b, req) for b in bloques)
            self.check(ok, f"{etiqueta}: {nombre}",
                       "" if ok else f"ningún párrafo cumple alguna de {req}")

    def conjunto(self, nombre: str, esperado: set, real: set) -> None:
        faltan, sobran = sorted(esperado - real), sorted(real - esperado)
        if not real:
            self.check(False, nombre, "no se declaró ningún elemento — nada que comparar")
            return
        detalle = []
        if faltan:
            detalle.append(f"faltan: {', '.join(faltan)}")
        if sobran:
            detalle.append(f"sobran: {', '.join(sobran)}")
        self.check(not detalle, f"{nombre} ({len(esperado)} exactos)",
                   " | ".join(detalle) if detalle else f"{len(real)}/{len(esperado)}")

    def tuplas(self, etiqueta: str, texto: str | None, esperadas, enum, extras=None,
               exhaustiva: bool = True) -> None:
        """Tabla de vocabulario cerrado: conjunto exacto de filas y valor exacto por fila.
        `exhaustiva=False` verifica solo las tuplas pedidas y no reclama por las demás filas —lo
        usa `--ac 11`, que mira dos de los cinco outcomes; el conjunto exacto lo cubre `--ac 2`."""
        if texto is None:
            self.check(False, etiqueta, "no hay sección que leer")
            return
        filas = [f for t in tablas(texto) for f in t[1:]]
        if not filas:
            self.check(False, etiqueta, "la sección no tiene ninguna tabla con filas")
            return
        usadas = set()
        for i, (claves, esperado) in enumerate(esperadas):
            cands = [j for j, f in enumerate(filas)
                     if all(norm(k) in norm(f[0]) for k in claves)]
            nombre = f"{etiqueta}: {' + '.join(claves)}"
            if not cands:
                self.check(False, nombre, "no hay ninguna fila que la declare")
                continue
            if len(cands) > 1:
                self.check(False, nombre, f"{len(cands)} filas la declaran (ambigua)")
                continue
            j = cands[0]
            usadas.add(j)
            leido = valor_enum(filas[j], enum)
            ok = leido == esperado
            self.check(ok, nombre, "" if ok else
                       f"efecto leído {leido!r}, esperado {esperado!r} (enum {list(enum)})")
            if extras and extras[i]:
                fn = norm(" ".join(filas[j]))
                faltan = [s for s in extras[i] if norm(s) not in fn]
                self.check(not faltan, f"{nombre} — combinación descrita",
                           "" if not faltan else f"la fila no menciona: {', '.join(faltan)}")
        if exhaustiva:
            huerfanas = [filas[j][0] for j in range(len(filas)) if j not in usadas]
            self.check(not huerfanas, f"{etiqueta}: sin filas sobrantes",
                       "" if not huerfanas else f"filas que no corresponden a ninguna clave "
                                                f"esperada: {', '.join(huerfanas[:5])}")

    def biyeccion(self, etiqueta: str, decls: list[str], senales: dict) -> bool:
        """Cada señal cubierta por al menos una declaración, cada declaración cubriendo al menos
        una señal, y tantas declaraciones como señales: conjunto exacto sobre prosa declarada."""
        cobertura = {k: [] for k in senales}
        sin_senal = []
        for d in decls:
            dn = norm(d)
            tocadas = [k for k, sig in senales.items() if all(norm(s) in dn for s in sig)]
            if tocadas:
                for k in tocadas:
                    cobertura[k].append(d)
            else:
                sin_senal.append(d)
        faltan = [k for k, v in cobertura.items() if not v]
        self.check(not faltan, f"{etiqueta}: cobertura",
                   "" if not faltan else f"sin declarar: {', '.join(faltan)}")
        self.check(not sin_senal, f"{etiqueta}: sin declaraciones sobrantes",
                   "" if not sin_senal else
                   f"{len(sin_senal)} sin correspondencia: {sin_senal[0][:70]}")
        self.check(len(decls) == len(senales), f"{etiqueta}: cardinalidad",
                   "" if len(decls) == len(senales) else
                   f"{len(decls)} declaraciones para {len(senales)} esperadas")
        return not faltan and not sin_senal and len(decls) == len(senales)


# ---------------------------------------------------------------------------------------------
# Modos por AC.
# ---------------------------------------------------------------------------------------------


def _campos(ctx: Ctx, titulo: str, esperado: set, etiqueta: str) -> None:
    s = ctx.seccion(CONTRATO_FUENTE, titulo)
    if s is None:
        return
    reales = {n for n in (nombre_declarado(d) for d in declaraciones(s)) if n}
    ctx.conjunto(etiqueta, esperado, {r.removesuffix("[]") for r in reales})


def ac_1(ctx: Ctx) -> None:
    """AC-1 — los conjuntos de campos y los sub-esquemas exactos."""
    _campos(ctx, "Los campos del sobre", CAMPOS_RAIZ, "campos raíz")
    _campos(ctx, "Los campos por worker", CAMPOS_WORKER, "campos por worker")
    _campos(ctx, "Los campos por intento", CAMPOS_INTENTO, "campos por intento")
    texto = ctx.contrato()
    if texto is None:
        return
    for nombre, esperado in SUBESQUEMAS.items():
        elems = conjunto_canonico(texto, nombre)
        if elems is None:
            ctx.check(False, f"sub-esquema {nombre}", f"falta la forma `{nombre} = {{…}}`")
            continue
        ctx.conjunto(f"sub-esquema {nombre}", esperado, set(elems))
    elems = conjunto_canonico(texto, "scope")
    if elems is None:
        ctx.check(False, "sub-esquema scope", "falta la forma `scope = {…}`")
    else:
        ctx.conjunto("sub-esquema scope", {"repo", "worktree"}, set(elems))
    ctx.exigir(texto, "derivación", {
        "`transport` raíz derivado (valor común de los intentos vigentes, o `mixto`)":
            [["transport", "deriv", "mixto", "vigente"]],
    })
    ctx.exigir(texto, "contrato de `proxima_accion`", {
        "campo raíz de tipo cadena": [["proxima_accion", "cadena", "raiz"]],
        "opcional; `null` y ausencia son casos válidos":
            [["proxima_accion", "opcional", "null", "ausencia", "valid"]],
        "escritor: conductor propietario":
            [["proxima_accion", "conductor propietario", "unico", "escribe"]],
        "lector: conductor al recuperar el control durante el barrido":
            [["recupera el control", "lee", "barrido"]],
        "transición al registro de cierre junto con el sobre":
            [["transfiere", "registro de cierre", "resto del sobre"]],
        "transición independiente de tombstone": [["transicion", "no depende", "tombstone"]],
        "recuperación `cli-exec` transfiere el campo al cierre":
            [["cli-exec", "transfiere", "proxima_accion", "registro de cierre"]],
    })


def ac_1b(ctx: Ctx) -> None:
    """AC-1 — no reconstruye estado semántico, cita su sede de rechazo y separa registros."""
    texto = ctx.contrato()
    ctx.exigir(texto, "contrato", {
        "declara que no reconstruye el estado semántico":
            [["no reconstruye", "estado semantico"], ["no", "reconstruir", "estado semantico"]],
        "sobre obligatorio e independiente de `cross_model.manifest.mode`":
            [["cross_model.manifest.mode", "independiente", "obligatorio"]],
    })
    if texto is not None:
        faltan = [s for s in SEDES_RECHAZO if norm(s) not in norm(texto)]
        ctx.check(not faltan, "contrato: cita la sede que rechaza el estado persistido",
                  "" if not faltan else f"no citadas: {', '.join(faltan)}")
        objetivo = ["sobre", "checkpoint durable", "bitacora"]
        ok = any(all(any(o in norm(f[0]) for f in t[1:]) for o in objetivo) and len(t[0]) >= 3
                 for t in tablas(texto))
        ctx.check(ok, "contrato: tabla de frontera de los tres registros",
                  "" if ok else "no hay una tabla con ≥3 columnas cuyas filas sean sobre, "
                                "checkpoint durable y bitácora")
    s = ctx.seccion("skills/cross-review/reference.md", "Manifest de corrida")
    ctx.exigir(s, "cross-review/reference.md → «Manifest de corrida»", {
        f"puntero a `{CONTRATO}`": [[CONTRATO]],
    })
    for rel in SEDES_RECHAZO:
        t = ctx.texto(rel)
        if t is None:
            continue
        tn = norm(t)
        ok = ("maquina de estados persistente, ni esquema formal, ni validador propio, ni "
              "versionado" in tn) and "estado persistido ya se rechazo por escrito" in tn
        ctx.check(ok, f"{rel}: conserva su cláusula de rechazo del estado persistido",
                  "" if ok else "la cláusula textual ya no está")


def ac_2(ctx: Ctx) -> None:
    """AC-2 — transiciones y outcomes por tupla, el orden del orquestador y el retiro sin rivales."""
    s = ctx.seccion(CONTRATO_FUENTE, "Transiciones del sobre")
    if s is not None:
        reales = set()
        for d in declaraciones(s):
            dn = norm(d)
            reales |= {t for t in TRANSICIONES if dn.startswith(t) or f"`{t}`" in d}
        ctx.conjunto("transiciones", TRANSICIONES, reales)
    ctx.tuplas("outcome de la espera", ctx.seccion(CONTRATO_FUENTE, "Outcome de la espera"),
               OUTCOMES, ENUM_OUTCOME)
    orq = ctx.texto("skills/sdd-orchestrator/SKILL.md")
    if orq is not None:
        ok = False
        for parrafo in re.split(r"\n\s*\n", orq):
            p = norm(parrafo)
            i, j, k = p.find("bitacora"), p.find("sobre"), p.find("despacho")
            if -1 < i < j < k:
                ok = True
                break
        ctx.check(ok, "sdd-orchestrator/SKILL.md: orden bitácora → sobre → despacho",
                  "" if ok else "ningún párrafo declara los tres en ese orden")
    ctx.exigir(ctx.seccion("skills/cross-review/reference.md", "Manifest de corrida"),
               "cross-review/reference.md → «Manifest de corrida»",
               {"relación de retiro con el manifest": [["se retira", "manifest"]]})
    for rel in SEDES_RECHAZO:
        t = ctx.texto(rel)
        if t is None:
            continue
        tn = norm(t)
        malas = [f for f in RETIRO_LOCAL_PROHIBIDO if f in tn]
        ctx.check(not malas, f"{rel}: sin regla local de retiro que compita con el contrato",
                  "" if not malas else f"sobrevive: {', '.join(repr(m) for m in malas)}")


def ac_2b(ctx: Ctx) -> None:
    """AC-2 — las tres condiciones del retiro, escritor único, nacimiento y adopción."""
    s = ctx.seccion(CONTRATO_FUENTE, "Condiciones del retiro")
    if s is not None:
        ctx.biyeccion("condiciones del retiro", declaraciones(s), {
            "terminal comprobado": ["terminal comprobado"],
            "artefacto validado o descartado": ["artefacto"],
            "sin recursos propios vivos o transferidos": ["recursos"],
        })
        ctx.exigir(s, "condiciones del retiro", {
            "las tres son simultáneas": [["simultane"], ["las tres"]],
            "transferencia a un registro de cierre": [["registro de cierre"]],
        })
    texto = ctx.contrato()
    ctx.exigir(texto, "contrato", {
        "un solo escritor: el creador": [["escritor", "creador"], ["un solo escritor"]],
        "quien encuentra un sobre ajeno lee e informa, nunca escribe":
            [["lee e informa", "nunca escribe"], ["nunca escribe"]],
        "publicación temporal + rename atómico": [["temporal", "rename atomico"]],
        "el barrido ignora los temporales": [["ignora", "temporal"]],
        "nacimiento sin reemplazo (falla si la ruta existe → otro run_id)":
            [["falla si la ruta existe", "run_id"], ["sin reemplazo", "run_id"]],
        "el sobre nace antes del despacho": [["antes del despacho"], ["antes de despachar"]],
        "`harvest_pending` impide una segunda cosecha":
            [["harvest_pending", "segunda cosecha"], ["harvest_pending", "una sola vez"]],
    })
    ctx.exigir(ctx.seccion(CONTRATO_FUENTE, "Adopción"), "contrato → «Adopción»", {
        "única transición ejecutable por otra sesión": [["unica transicion"]],
        "solo con autorización explícita del usuario en el momento":
            [["autorizacion explicita", "usuario"]],
        "registra sucesor, decisión y motivo": [["sucesor", "decision", "motivo"]],
    })


def ac_3(ctx: Ctx) -> None:
    """AC-3 — la agregación multi-worker y `descendants_summary`."""
    s = ctx.seccion(CONTRATO_FUENTE, "Varios workers en una corrida")
    ctx.exigir(s, "contrato → «Varios workers en una corrida»", {
        "punto 1 — identidad por worker": [["identidad", "worker"]],
        "punto 2 — fuente y precedencia por worker": [["fuente", "precedencia"]],
        "punto 3 — qué se informa y cómo se cosecha parcialmente":
            [["se informa", "cosecha parcial"], ["se informa", "parcialmente"]],
        "punto 4 — cuándo la corrida agregada deja de estar en vuelo":
            [["deja de estar en vuelo"]],
        "`descendants_summary`": [["descendants_summary"]],
    })


def ac_3b(ctx: Ctx) -> None:
    """AC-3 — un ancestro no cosecha ni retira sobres indirectos."""
    ctx.exigir(ctx.contrato(), "contrato", {
        "solo corridas directas": [["corridas directas"]],
        "un ancestro no cosecha ni retira sobres indirectos":
            [["ancestro", "cosech", "retir", "indirect"]],
    })


def ac_4(ctx: Ctx) -> None:
    """AC-4 — el archivo, la identidad compuesta y las tres topologías del barrido."""
    ctx.exigir(ctx.seccion(CONTRATO_FUENTE, "El archivo"), "contrato → «El archivo»", {
        "ruta `.cross-model/active/<skill>/<run_id>.json`":
            [[".cross-model/active/", "run_id", ".json"]],
        "identidad compuesta `(repo, skill, run_id)`": [["repo, skill, run_id"]],
    })
    s = ctx.seccion(CONTRATO_FUENTE, "El barrido de corridas activas")
    if s is not None:
        decls = declaraciones(s)
        for clave, etiqueta in (("repo unico", "repo único"), ("standalone", "skill standalone"),
                                ("multi-repo", "orquestación multi-repo")):
            cands = [d for d in decls if clave in norm(d)]
            ctx.check(bool(cands), f"topología {etiqueta}",
                      "" if cands else "no se declara")
            if cands:
                ok = any(cubre(norm(d), [["listar"], ["enumerar"], ["recorr"]]) for d in cands)
                ctx.check(ok, f"topología {etiqueta}: recorrido escrito",
                          "" if ok else "la declaración no dice cómo se recorre")
        sobrantes = [d for d in decls if not any(
            c in norm(d) for c in ("repo unico", "standalone", "multi-repo"))]
        ctx.check(not sobrantes, "topologías: sin filas sobrantes",
                  "" if not sobrantes else f"{len(sobrantes)}: {sobrantes[0][:70]}")
    ctx.exigir(s, "contrato → «El barrido de corridas activas»", {
        "el multi-repo enumera siempre todos los `.sdd/*/manifest.yml`":
            [["siempre", ".sdd/", "manifest.yml"]],
        "`children` es optimización, no la autoridad del recorrido":
            [["children", "optimizacion"]],
    })


def ac_5(ctx: Ctx) -> None:
    """AC-5 — el cierre del turno, las cuatro propiedades de la sonda y `wait_budget`."""
    ctx.exigir(ctx.seccion(CONTRATO_FUENTE, "El cierre del turno"),
               "contrato → «El cierre del turno»", {
                   "todo turno cierra informando el estado de la corrida":
                       [["todo turno", "informa"], ["cierra informando"]],
               })
    ctx.exigir(ctx.seccion(CONTRATO_FUENTE, "La sonda por turno"),
               "contrato → «La sonda por turno»", {
                   "propiedad 1 — no bloqueante": [["no bloqueante"]],
                   "propiedad 2 — una por turno": [["una por turno"], ["una sonda por turno"]],
                   "propiedad 3 — sin retry": [["sin retry"], ["sin reintento"]],
                   "propiedad 4 — no modifica deadline ni contador":
                       [["no modifica", "deadline", "contador"]],
                   "solo un poll real incrementa `consumidos`":
                       [["poll real", "consumidos"]],
               })
    texto = ctx.contrato()
    if texto is not None:
        elems = conjunto_canonico(texto, "wait_budget")
        if elems is None:
            ctx.check(False, "sub-esquema wait_budget", "falta la forma `wait_budget = {…}`")
        else:
            ctx.conjunto("sub-esquema wait_budget", SUBESQUEMAS["wait_budget"], set(elems))
        tn = norm(texto)
        ok = any(p in tn for p in ("consumidos <= limite", "consumidos ≤ limite",
                                   "consumidos nunca supera", "consumidos no supera"))
        ctx.check(ok, "invariante `consumidos ≤ limite`",
                  "" if ok else "no está escrita la invariante")


def ac_6(ctx: Ctx) -> None:
    """AC-6 — fuentes vigentes, `process_ref` y continuidad operativa anclada a su sección."""
    ctx.tuplas("fuente por transporte", ctx.seccion(CONTRATO_FUENTE, "Fuente por transporte"),
               FUENTES, ENUM_FUENTE)
    texto = ctx.contrato()
    if texto is not None:
        elems = conjunto_canonico(texto, "process_ref")
        if elems is None:
            ctx.check(False, "sub-esquema process_ref", "falta la forma `process_ref = {…}`")
        else:
            ctx.conjunto("sub-esquema process_ref", SUBESQUEMAS["process_ref"], set(elems))
    ctx.exigir(texto, "contrato", {
        "`process_ref` es `null` donde no hay proceso consultable":
            [["null", "no hay proceso"], ["null", "sin proceso"]],
        "ante frescura no comprobada el proceso es incierto y nunca se cancela":
            [["incierto", "nunca se cancela"]],
        "el subagente no tiene fuente consultable a mitad de vuelo":
            [["subagent", "no hay fuente consultable"]],
    })
    s = ctx.seccion_exacta("skills/co-explore/reference.md", "Truncado previo al dispatch")
    if s is not None:
        sn = norm(s)
        ok = (CONTRATO in s and "invariantes de recuperacion" in sn and
              cubre(sn, [["intento anterior", "rutas"]]))
        ctx.check(ok, "co-explore/reference.md: remite a las invariantes con el referente de rutas",
                  "" if ok else f"cita el contrato: {CONTRATO in s} · cita invariantes: "
                                f"{'invariantes de recuperacion' in sn} · refiere intento y rutas: "
                                f"{cubre(sn, [['intento anterior', 'rutas']])}")
    for rel, construcciones in CONSERVAR.items():
        try:
            base = subprocess.run(["git", "show", f"{CHANGE_BASE_COMMIT}:{rel}"], cwd=REPO,
                                  capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError as e:
            ctx.check(False, f"matriz CONSERVAR: {CHANGE_BASE_COMMIT}:{rel}",
                      e.stderr.strip()[:120])
            continue
        for nombre, titulo, requisito, *resto in construcciones:
            requisito_base = resto[0] if resto else requisito
            seccion_base = seccion_exacta(base, titulo)
            seccion_actual = ctx.seccion_exacta(rel, titulo)
            anclada = seccion_base is not None and cubre(norm(seccion_base), requisito_base)
            ctx.check(anclada, f"CONSERVAR anclado en {CHANGE_BASE_COMMIT}: {nombre}",
                      "" if anclada else f"la construcción no existe en «{titulo}» del commit base")
            presente = seccion_actual is not None and cubre(norm(seccion_actual), requisito)
            ctx.check(presente, f"{rel} → «{titulo}»: conserva {nombre}",
                      "" if presente else f"la construcción operativa no cumple {requisito}")


def ac_7(ctx: Ctx) -> None:
    """AC-7 — las cuatro discrepancias con su resolución."""
    ctx.tuplas("precedencia ante discrepancia",
               ctx.seccion(CONTRATO_FUENTE, "Precedencia ante discrepancia"),
               [(c, v) for c, v, _ in PRECEDENCIA], ENUM_PRECEDENCIA,
               extras=[e for _, _, e in PRECEDENCIA])
    ctx.exigir(ctx.contrato(), "contrato", {
        "`esperar_cleanup` ejecuta la transferencia al registro de cierre":
            [["esperar_cleanup", "transfer"], ["cleanup", "registro de cierre"]],
    })


def ac_8(ctx: Ctx) -> None:
    """AC-8 — el límite se declara y la salida no afirma ejecución."""
    ctx.exigir(ctx.seccion(CONTRATO_FUENTE, "El límite declarado"),
               "contrato → «El límite declarado»", {
                   "se declara en una línea en vez de simular una verificación":
                       [["una linea", "simular"]],
                   "la salida no afirma que el worker sigue ejecutándose":
                       [["no afirma", "ejecutandose"], ["no afirma", "sigue ejecutando"]],
               })


def ac_9(ctx: Ctx) -> None:
    """AC-9 — el sidecar del dato nuevo y sus siete obligaciones."""
    s = ctx.seccion(CONTRATO_FUENTE, "El dato nuevo del usuario")
    ctx.exigir(s, "contrato → «El dato nuevo del usuario»", {
        "ruta del sidecar `.cross-model/active/<skill>/<run_id>.datos.jsonl`":
            [[".cross-model/active/", ".datos.jsonl"]],
        "append-only": [["append-only"], ["append only"]],
    })
    if s is not None:
        # Conjunto exacto por forma canónica: contar tokens sueltos entre backticks mezclaría los
        # campos del sidecar con cualquier campo del sobre citado de paso.
        elems = conjunto_canonico(s, "datos.jsonl")
        if elems is None:
            ctx.check(False, "campos del sidecar",
                      "falta la forma `<run_id>.datos.jsonl = {origen, destinos, recibido_en, "
                      "disposicion}`")
        else:
            ctx.conjunto("campos del sidecar", {"origen", "destinos", "recibido_en", "disposicion"},
                         {e.removesuffix("[]") for e in elems})
        ctx.biyeccion("las siete obligaciones del dato nuevo", declaraciones(s), {
            "ronda siguiente por defecto": ["ronda siguiente", "por defecto"],
            "abortar solo por pedido explícito": ["abortar", "explicit"],
            "conjunto explícito de destinos, que puede ser vacío": ["destinos", "vacio"],
            "el sidecar con su origen": ["sidecar", "origen"],
            "nunca sobre el artefacto que el intento vigente ya consumió":
                ["nunca", "ya consumio"],
            "una sola pasada: `destinos: []` y sin consumo en esta corrida": ["una sola pasada"],
            "si la corrida termina antes: `no_consumido` y el sidecar sobrevive al retiro":
                ["no_consumido", "sobrevive"],
        })


def ac_10(ctx: Ctx) -> None:
    """AC-10 — el relanzamiento seguro y los intentos como entradas propias."""
    ctx.exigir(ctx.seccion(CONTRATO_FUENTE, "Relanzamiento seguro"),
               "contrato → «Relanzamiento seguro»", {
                   "condición 1 — cese confirmado del worker anterior": [["cese", "confirm"]],
                   "condición 2 — rutas exclusivas por intento": [["rutas exclusivas"]],
                   "condición 3 — escritor nuevo bloqueado mientras el anterior pueda tocar el árbol":
                       [["bloquead", "arbol"]],
                   "cada intento es una entrada nueva de `attempts[]`":
                       [["attempts", "entrada"]],
               })


def ac_11(ctx: Ctx) -> None:
    """AC-11 — `error` es outcome propio y la cancelación tiene sus dos tuplas condicionales."""
    s = ctx.seccion(CONTRATO_FUENTE, "Outcome de la espera")
    ctx.tuplas("outcome de la espera", s,
               [t for t in OUTCOMES if t[0][0] in ("error", "cancelacion")], ENUM_OUTCOME,
               exhaustiva=False)
    ctx.exigir(s, "contrato → «Outcome de la espera»", {
        "la cancelación es un terminal distinto del corte por presupuesto y del error":
            [["cancelacion", "corte_presupuesto", "error"]],
    })


def ac_12(ctx: Ctx) -> str:
    """AC-12 — los once puntos de despacho y el puntero normativo por skill."""
    puntos = punteros = 0
    for skill, esperados in PUNTOS_DESPACHO.items():
        rel = f"skills/{skill}/SKILL.md"
        s = ctx.seccion(rel, "Corridas delegadas en vuelo")
        if s is None:
            continue
        if ctx.check(CONTRATO in s, f"{skill}: puntero normativo a su copia local",
                     "" if CONTRATO in s else f"la sección no cita `{CONTRATO}`"):
            punteros += 1
        decls = [d for d in declaraciones(s) if CONTRATO not in d]
        if ctx.biyeccion(f"{skill}: puntos de despacho", decls, esperados):
            puntos += len(esperados)
    total = sum(len(v) for v in PUNTOS_DESPACHO.values())
    return f"{puntos}/{total} · {punteros}/{len(PUNTOS_DESPACHO)} punteros · sin faltantes ni sobrantes"


def ac_13(ctx: Ctx) -> str:
    """AC-13 — las siete copias byte-idénticas, el trigger de CLAUDE.md y los cuatro README."""
    fuente = leer(ctx.raiz, CONTRATO_FUENTE)
    identicas = 0
    if fuente is None:
        ctx.check(False, f"fuente {CONTRATO_FUENTE}", "no existe")
    else:
        h = hashlib.sha256(fuente.encode("utf-8")).hexdigest()
        for rel in COPIAS:
            otro = leer(ctx.raiz, rel)
            if otro is None:
                ctx.check(False, f"copia {rel}", "no existe")
                continue
            ok = hashlib.sha256(otro.encode("utf-8")).hexdigest() == h
            identicas += ok
            ctx.check(ok, f"copia {rel}", "" if ok else "diverge de la fuente (sha256 distinto)")
    ctx.exigir(ctx.texto("CLAUDE.md"), "CLAUDE.md", {
        f"trigger: tocar `{CONTRATO}` obliga a `--sincronizar` y `--ac 13`":
            [[CONTRATO, "--sincronizar", "--ac 13"]],
    })
    for rel in READMES:
        ctx.exigir(ctx.texto(rel), rel, {
            "nombra `.cross-model/active/`": [["active/"]],
            # "manifest.mode" + "no" daba verde con el texto actual, que dice justo lo contrario
            # ("apágalo con cross_model.manifest.mode"): la negación tiene que ser la frase.
            "declara que no lo apaga `cross_model.manifest.mode`":
                [["manifest.mode", "no lo apaga"], ["manifest.mode", "no se apaga"],
                 ["manifest.mode", "independiente"]],
            "advierte el riesgo de copias de versiones mezcladas, con su sede canónica":
                [["mezclad", "sede canonica"], ["mezclad", "primera linea"]],
        })
    return f"{identicas}/{len(COPIAS)} idénticas"


def ac_14(ctx: Ctx) -> None:
    """AC-14 — la tercera excepción de la regla 7 de `co-explore`, citada por `sdd-flow`."""
    texto = ctx.texto("skills/co-explore/SKILL.md")
    if texto is not None:
        bloque = None
        for parrafo in re.split(r"\n\s*\n", texto):
            if "excepciones acotadas" in norm(parrafo):
                bloque = parrafo
                break
        if bloque is None:
            ctx.check(False, "co-explore: lista de excepciones conversacionales",
                      "no se encontró el párrafo de «excepciones acotadas»")
        else:
            bn = norm(bloque)
            ctx.check("tres excepciones" in bn, "co-explore: la lista pasa a tres excepciones",
                      "" if "tres excepciones" in bn else f"sigue diciendo: {bloque.strip()[:80]}")
            ok = cubre(bn, [["corridas", "en vuelo"], ["corrida", "en vuelo"]])
            ctx.check(ok, "co-explore: la tercera excepción nombra el aviso de corridas en vuelo",
                      "" if ok else "la lista no menciona las corridas en vuelo")
    flow = ctx.texto("skills/sdd-flow/SKILL.md")
    if flow is not None:
        bloque = None
        for d in declaraciones(flow) + re.split(r"\n\s*\n", flow):
            if "no citan la co-exploracion" in norm(d):
                bloque = d
                break
        if bloque is None:
            ctx.check(False, "sdd-flow: exención conversacional",
                      "no se encontró «Los artefactos no citan la co-exploración»")
        else:
            bn = norm(bloque)
            faltan = [n for n, req in (
                ("cita a co-explore", [["co-explore"]]),
                ("nombra la excepción", [["excepcion"]]),
                ("nombra las corridas en vuelo", [["en vuelo"]]),
            ) if not cubre(bn, req)]
            ctx.check(not faltan, "sdd-flow: su exención cita la regla de `co-explore`",
                      "" if not faltan else f"falta: {', '.join(faltan)}")


def extraer_claves(texto: str, heading: str) -> tuple[set[str], str | None]:
    """Hojas punteadas del primer bloque YAML de la sección, o su causa de error."""
    import yaml

    nivel = None
    fence = False
    lineas: list[str] = []
    for linea in texto.splitlines():
        encabezado = re.match(r"^(#+)\s+(.*)$", linea)
        if nivel is None:
            if re.match(rf"^#+\s+{heading}(?:\s|$)", linea):
                nivel = len(encabezado.group(1)) if encabezado else 0
            continue
        if not fence:
            if encabezado:
                if re.match(rf"^#+\s+{heading}(?:\s|$)", linea):
                    nivel = len(encabezado.group(1))
                    continue
                break
            if re.match(r"^\s*```yaml(?:\s|$)", linea):
                fence = True
            continue
        if re.match(r"^\s*```", linea):
            break
        lineas.append(linea)
    if nivel is None:
        return set(), "heading ausente"
    if not fence:
        return set(), "bloque yaml ausente"
    try:
        datos = yaml.safe_load("\n".join(lineas))
    except yaml.YAMLError:
        return set(), "yaml inválido"
    if not isinstance(datos, dict):
        return set(), "raíz no es un mapa"
    salida: set[str] = set()

    def walk(nodo, prefijo=""):
        for k, v in nodo.items():
            p = f"{prefijo}{k}"
            walk(v, p + ".") if isinstance(v, dict) else salida.add(p)

    walk(datos)
    return salida, None


def incompletas(base: dict[str, set[str]], ahora: dict[str, set[str]]) -> \
        list[tuple[str, str, str]]:
    """Claves nuevas que no están completas en los dos extremos de su grupo."""
    salida: list[tuple[str, str, str]] = []

    def revisar(duenos: list[tuple[str, str]], vista: tuple[str, str],
                excluir: set[str]) -> None:
        rutas_dueno = [rel for rel, _ in duenos]
        rel_vista = vista[0]
        base_dueno = set().union(*(base[rel] for rel in rutas_dueno)) - excluir
        ahora_dueno = set().union(*(ahora[rel] for rel in rutas_dueno)) - excluir
        base_vista = base[rel_vista] - excluir
        ahora_vista = ahora[rel_vista] - excluir

        for clave in sorted((ahora_dueno - base_dueno) - ahora_vista):
            archivos = [rel for rel in rutas_dueno if clave in ahora[rel]]
            salida.append((clave, " o ".join(archivos), rel_vista))
        for clave in sorted((ahora_vista - base_vista) - ahora_dueno):
            salida.append((clave, " o ".join(rutas_dueno), rel_vista))

    revisar(DUENOS_CONFIG, VISTA_CONFIG, set())
    revisar([DUENO_MANIFEST], VISTA_MANIFEST, CLAVES_ESTADO_CORRIDA)
    return salida


def resolver_base(raiz: Path) -> tuple[str | None, str]:
    """Resuelve el merge-base con `main` y, como fallback, con `origin/main`."""
    errores = []
    for ref in ("main", "origin/main"):
        resultado = subprocess.run(["git", "merge-base", "HEAD", ref], cwd=raiz,
                                   capture_output=True, text=True)
        sha = resultado.stdout.strip()
        if resultado.returncode == 0 and sha:
            return sha, ref
        causa = resultado.stderr.strip() or resultado.stdout.strip() or f"exit {resultado.returncode}"
        errores.append(f"{ref}: {causa}")
    return None, "no se pudo determinar la base; " + " | ".join(errores)


def ac_15(ctx: Ctx) -> str:
    """AC-15 — las claves nuevas del diff de la rama están completas en dueño y vista.

    Sobre la rama base no hay sujeto: el merge-base es HEAD y el conjunto nuevo queda vacío.
    """
    sha_base, ref_base = resolver_base(ctx.raiz)
    if sha_base is None:
        ctx.check(False, "merge-base de la rama", ref_base)
        return "merge-base: no resuelto · pares nuevos evaluados: ?"

    base: dict[str, set[str]] = {}
    ahora: dict[str, set[str]] = {}
    for rel, heading in SUPERFICIES_CONFIG:
        try:
            viejo = subprocess.run(["git", "show", f"{sha_base}:{rel}"], cwd=ctx.raiz,
                                   capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError as e:
            ctx.check(False, f"git show {sha_base}:{rel}", e.stderr.strip()[:120])
            continue
        nuevo = leer(ctx.raiz, rel)
        if nuevo is None:
            ctx.check(False, rel, "el archivo ya no existe en el árbol")
            continue
        claves_base, error_base = extraer_claves(viejo, heading)
        claves_ahora, error_ahora = extraer_claves(nuevo, heading)
        if error_base:
            ctx.check(False, f"{rel} en merge-base {sha_base}", error_base)
        if error_ahora:
            ctx.check(False, rel, error_ahora)
        if error_base or error_ahora:
            continue
        base[rel] = claves_base
        ahora[rel] = claves_ahora

    resumen = f"merge-base {ref_base}={sha_base}"
    if len(base) != len(SUPERFICIES_CONFIG) or len(ahora) != len(SUPERFICIES_CONFIG):
        return f"{resumen} · pares nuevos evaluados: ?"

    fallas = incompletas(base, ahora)
    for clave, dueno, vista in fallas:
        ctx.check(False, f"clave incompleta `{clave}`", f"dueño: {dueno} · vista: {vista}")
    pares_nuevos = sum(len(ahora[rel] - base[rel]) for rel, _ in SUPERFICIES_CONFIG)
    ctx.check(not fallas, f"claves nuevas completas en dueño y vista ({pares_nuevos} pares)")
    return f"{resumen} · pares nuevos evaluados: {pares_nuevos}"


def _diagnosticos(salida: str, skill: str) -> set[str]:
    """Normaliza la salida de `skills-ref validate` a `skill|regla|mensaje`, para comparar por
    conjunto y no por conteo ni por coincidencia parcial."""
    out: set[str] = set()
    for linea in salida.splitlines():
        s = linea.strip()
        if not s.startswith("- "):
            continue
        cuerpo = s[2:].strip()
        regla, _, resto = cuerpo.partition(":")
        tokens = sorted(t.strip() for t in resto.split(",") if t.strip())
        out.add(f"{skill}|{norm(regla)}|{norm(' , '.join(tokens))}")
    return out


def _validar_skills_ref(ctx: Ctx) -> int:
    """Compara por skill `(returncode, diagnósticos)` contra el commit base del cambio."""
    if shutil.which("skills-ref") is None:
        ctx.check(False, "skills-ref", "el binario no está instalado — el predicado no es medible")
        return 1
    antes: dict[str, tuple[int, set[str]]] = {}
    ahora: dict[str, tuple[int, set[str]]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        try:
            listado = subprocess.run(["git", "ls-tree", "-r", "--name-only",
                                      CHANGE_BASE_COMMIT, "skills/"],
                                     cwd=REPO, capture_output=True, text=True,
                                     check=True).stdout.split()
        except subprocess.CalledProcessError as e:
            ctx.check(False, f"git ls-tree {CHANGE_BASE_COMMIT}", e.stderr.strip()[:120])
            return 1
        for rel in listado:
            blob = subprocess.run(["git", "show", f"{CHANGE_BASE_COMMIT}:{rel}"], cwd=REPO,
                                  capture_output=True, check=True).stdout
            destino = base / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(blob)
        for skill in SKILLS:
            viejo = base / "skills" / skill
            if not viejo.is_dir():
                ctx.check(False, f"skills-ref baseline: {skill}",
                          "la skill no existe en el commit base")
                continue
            r = subprocess.run(["skills-ref", "validate", str(viejo)], capture_output=True,
                               text=True)
            antes[skill] = (r.returncode, _diagnosticos(r.stdout + r.stderr, skill))
            nuevo = ctx.raiz / "skills" / skill
            r = subprocess.run(["skills-ref", "validate", str(nuevo)], capture_output=True,
                               text=True)
            ahora[skill] = (r.returncode, _diagnosticos(r.stdout + r.stderr, skill))
    fallos = 0
    for skill in SKILLS:
        if skill not in antes or skill not in ahora:
            fallos += 1
            continue
        rc_base, diagnosticos_base = antes[skill]
        rc_actual, diagnosticos_actuales = ahora[skill]
        conserva_exito = rc_base != 0 or rc_actual == 0
        fallos += not ctx.check(
            conserva_exito, f"skills-ref {skill}: un baseline exitoso sigue exitoso",
            "" if conserva_exito else f"rc base={rc_base} · rc actual={rc_actual}")
        nuevos = sorted(diagnosticos_actuales - diagnosticos_base)
        fallos += not ctx.check(
            not nuevos, f"skills-ref {skill}: diagnósticos actuales ⊆ baseline",
            "" if not nuevos else " | ".join(nuevos[:4]))
        salida_parseable = rc_actual == 0 or bool(diagnosticos_actuales)
        fallos += not ctx.check(
            salida_parseable, f"skills-ref {skill}: todo rc no cero produce diagnósticos parseables",
            "" if salida_parseable else f"rc={rc_actual} sin diagnósticos normalizados")
    return fallos


def ac_16(ctx: Ctx) -> str:
    """AC-16 — guardas del repo y pares `(returncode, diagnósticos)` sin regresión."""
    acumulado = 0
    for cmd in GUARDAS:
        r = subprocess.run(cmd, cwd=ctx.raiz, capture_output=True, text=True)
        acumulado += r.returncode
        ctx.check(r.returncode == 0, " ".join(cmd[1:]),
                  "" if r.returncode == 0 else f"rc={r.returncode}")
    fallos_skills_ref = _validar_skills_ref(ctx)
    return f"rc={acumulado} · fallos skills-ref: {fallos_skills_ref}"


def ac_17(ctx: Ctx) -> str:
    """AC-17 — autoridades frescas del manifest, carriers, productores y cierre idempotente."""
    contrato = ctx.seccion(CONTRATO_FUENTE, "Los campos del sobre")
    ctx.exigir(contrato, "carrier activo", {
        "par condicional e indivisible": [["manifest_seed", "manifest_first_dispatch_at", "condicional", "indivisible"]],
        "seed exacto, inmutable y anterior al preflight": [["antes", "preflight", "exactamente", "skill", "mode", "preflight_started_at", "families", "transport", "selection", "inmutable"]],
        "timestamp null y write-once antes de la primera tool call": [["manifest_first_dispatch_at", "null", "inmediatamente antes", "primera tool call", "una sola vez"]],
        "terminal sin worker conserva el fallback": [["ningun worker", "seleccionado", "ninguna via", "null", "workers[]", "none"]],
        "preflight con vía resuelta conserva la vía candidata": [["falla", "preflight", "via", "families", "manifest_seed.transport", "conserva"]],
        "modo off mantiene ausente el par": [["modo off", "ambos nodos", "ausentes", "no se vuelven", "retomar"], ["modo off", "ambos nodos", "ausentes", "no se vuelve", "retomar"]],
    })
    retiro = norm(ctx.seccion(CONTRATO_FUENTE, "Condiciones del retiro") or "")
    checkpoint_sin_manifest = bool(re.search(r"checkpoint intermedio[^.]*carrier[^.]*no materializa[^.]*manifest", retiro))
    terminal_resuelve_manifest = bool(re.search(r"outcome terminal[^.]*manifest[^.]*retiro terminal", retiro))
    ctx.check(checkpoint_sin_manifest and terminal_resuelve_manifest,
              "carrier canónico distingue checkpoint y retiro terminal",
              "" if checkpoint_sin_manifest and terminal_resuelve_manifest else "el retiro canónico no distingue la transferencia no terminal")

    checkpoint = ctx.seccion("skills/cross-review/reference.md", "Checkpoint durable")
    ctx.exigir(checkpoint, "checkpoint durable", {
        "igualdad estructural exacta con el sobre": [["manifest_seed", "exactamente", "diferencia de valor", "invalida"]],
        "timestamp write-once no usa reloj de rehidratación": [["manifest_first_dispatch_at", "null", "timestamp", "nunca", "rehidratacion"]],
        "off conserva ambos nodos ausentes": [["manifest deshabilitado", "dos nodos", "ausentes", "no se serializan"]],
        "resume rehidrata autoridades sin abrir otra corrida": [["resume", "rehidrata", "autoridades", "no se inicia otra"]],
    })

    manifest = ctx.seccion("skills/cross-review/reference.md", "Manifest de corrida")
    ctx.exigir(manifest, "objeto y ruta del manifest", {
        "run_id separa dos rutas del mismo segundo": [["mismo segundo", "run_id distintos", "no colisionan"]],
        "segundo cierre conserva bytes idénticos": [["segundo cierre", "bytes identicos"]],
        "manifest anterior ilegible es irrelevante": [["manifest anterior", "ilegible", "irrelevante"]],
        "runs nunca es fuente o plantilla": [[".cross-model/runs/ no se lee ni se copia como plantilla"]],
    })
    if manifest is not None:
        manifest_norm = norm(manifest)
        retry_consulta = bool(re.search(r"retry[^.]*consulta[^.]*existe", manifest_norm))
        existencia_idempotente = bool(re.search(
            r"si la ruta existe[^.]*sin abrir[^.]*validar[^.]*recalcular[^.]*reescribir",
            manifest_norm))
        retry_idempotente = retry_consulta and existencia_idempotente
        ctx.check(retry_idempotente,
                  "objeto y ruta del manifest: consulta existencia sin leer el cierre",
                  "" if retry_idempotente else
                  "el retry no liga existencia con no abrir, validar, recalcular ni reescribir")
        eexist_idempotente = bool(re.search(
            r"eexist[^.]*cierre[^.]*sin abrir[^.]*recalcular[^.]*reescribir",
            manifest_norm))
        ctx.check(eexist_idempotente, "objeto y ruta del manifest: EEXIST cierra sin recalcular",
                  "" if eexist_idempotente else
                  "EEXIST no está ligado al cierre sin abrir, recalcular ni reescribir")
        checkpoint_transfiere = bool(re.search(r"checkpoint intermedio[^.]*transfiere[^.]*carrier[^.]*no materializa[^.]*manifest", manifest_norm))
        ctx.check(checkpoint_transfiere, "checkpoint transfiere el carrier sin cerrar el manifest",
                  "" if checkpoint_transfiere else "el checkpoint no distingue transferencia de carrier y retiro terminal")
        sentinelas = re.search(
            r"corrida A.*?started_at:\s*([0-9TZ:+-]+).*?duration_s:\s*(\d+).*?"
            r"corrida B.*?started_at:\s*([0-9TZ:+-]+).*?duration_s:\s*(\d+)",
            manifest, re.IGNORECASE | re.DOTALL)
        distintos = bool(sentinelas and sentinelas.group(1) != sentinelas.group(3)
                         and sentinelas.group(2) != sentinelas.group(4))
        ctx.check(distintos, "sentinelas: timestamp y duración distintos entre A y B",
                  "" if distintos else "no se encontraron dos pares de sentinelas distintos")

    productores = {
        "co-explore": ("skills/co-explore/SKILL.md", ("completed", "map_failure")),
        "cross-review": ("skills/cross-review/SKILL.md", ("approved", "revise", "unavailable")),
        "cross-implement": ("skills/cross-implement/SKILL.md", ("implemented", "partial", "unavailable")),
        "bitbucket-code-review": ("skills/bitbucket-code-review/SKILL.md", ("published", "proposed", "unavailable")),
    }
    for productor, (rel, terminales) in productores.items():
        texto = ctx.texto(rel)
        ctx.exigir(texto, f"productor {productor}", {
            "secuencia selección a terminal": [["seleccion", "seed", "sobre", "preflight", "timestamp", "tool call", "terminal"]],
            "terminales proyectados desde autoridades frescas": [["manifest", "autoridad", *terminales], ["manifest", "manifest_authorities", *terminales], ["manifest", "manifest_seed", "manifest_first_dispatch_at", *terminales]],
            "preflight sin despacho usa null, inicio de preflight y none": [["preflight", "null", "preflight_started_at", "transport", "none"]],
            "preflight con vía resuelta no degrada a none": [["via", "resuelta", "preflight", "seed", "conserva", "no haya"]],
            "runs no es fuente": [[".cross-model/runs/", "no", "fuente"]],
        })
    return f"{len(productores)} productores · carriers, checkpoint, objeto/ruta y guardas"


# ---------------------------------------------------------------------------------------------
# Cerrojo de la conmutación destructiva.
# ---------------------------------------------------------------------------------------------


def _git_conmutacion_bytes(raiz: Path, *args: str) -> bytes:
    resultado = subprocess.run(
        ["git", "-C", str(raiz), *args], capture_output=True, check=False)
    if resultado.returncode != 0:
        detalle = (resultado.stderr.strip() or resultado.stdout.strip()).decode(
            "utf-8", errors="replace")
        raise RuntimeError(detalle or "git no pudo leer el estado de la conmutación")
    return resultado.stdout


def _git_conmutacion(raiz: Path, *args: str) -> str:
    return _git_conmutacion_bytes(raiz, *args).decode("utf-8").strip()


def _huella_estado_trabajo(raiz: Path) -> str:
    huella = hashlib.sha256()
    huella.update(_git_conmutacion_bytes(raiz, "diff", "--binary", "HEAD", "--"))
    no_seguidos = _git_conmutacion_bytes(
        raiz, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    for nombre_crudo in sorted(nombre for nombre in no_seguidos if nombre):
        nombre = os.fsdecode(nombre_crudo)
        ruta = raiz / nombre
        huella.update(b"\0untracked\0" + nombre_crudo + b"\0")
        if ruta.is_symlink():
            huella.update(b"symlink\0" + os.fsencode(os.readlink(ruta)))
        elif ruta.is_file():
            huella.update(b"file\0" + ruta.read_bytes())
        else:
            huella.update(b"other\0")
    return huella.hexdigest()


def _estado_conmutacion(raiz: Path) -> dict[str, str | int]:
    return {
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "commit": _git_conmutacion(raiz, "rev-parse", "HEAD"),
        "arbol": _git_conmutacion(raiz, "rev-parse", "HEAD^{tree}"),
        "estado_trabajo": _huella_estado_trabajo(raiz),
    }


def _corridas_activas(raiz: Path) -> list[str]:
    active = raiz / ".cross-model/active"
    if not active.is_dir():
        return []
    return sorted(
        ruta.relative_to(raiz).as_posix()
        for ruta in active.rglob("*.json")
        if ruta.is_file() and not ruta.name.endswith(".datos.jsonl")
    )


def liberar_conmutacion(raiz: Path, registro: dict[str, str | int],
                        completada: bool) -> tuple[bool, str]:
    """Libera tras completar; al abortar exige volver al commit y árbol registrados."""
    lock = raiz / CONMUTACION_LOCK
    if not lock.is_file():
        return False, "el cerrojo ya no existe"
    try:
        vigente = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"el cerrojo no se puede adjudicar: {exc}"
    if vigente != registro:
        return False, "el cerrojo pertenece a otro intento"
    if not completada:
        actual = _estado_conmutacion(raiz)
        for campo in ("commit", "arbol", "estado_trabajo"):
            if actual[campo] != registro[campo]:
                return False, "la reversión no restauró el commit y árbol registrados"
    lock.unlink()
    return True, "cerrojo liberado"


def tomar_conmutacion(raiz: Path) -> tuple[dict[str, str | int] | None, str]:
    """Toma con O_EXCL y, recién entonces, enumera las corridas delegadas activas."""
    lock = raiz / CONMUTACION_LOCK
    lock.parent.mkdir(parents=True, exist_ok=True)
    registro = _estado_conmutacion(raiz)
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return None, "conmutación en curso: el cerrojo ya existe y no se retira automáticamente"
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as salida:
            json.dump(registro, salida, ensure_ascii=False, sort_keys=True)
            salida.write("\n")
    except Exception:
        lock.unlink(missing_ok=True)
        raise

    activas = _corridas_activas(raiz)
    if activas:
        liberada, detalle = liberar_conmutacion(raiz, registro, completada=False)
        sufijo = "" if liberada else f"; {detalle}; el cerrojo queda tomado"
        return None, "corridas activas sin adjudicar: " + ", ".join(activas) + sufijo
    return registro, "cerrojo tomado; cero corridas activas; conmutación habilitada"


def _preparar_repo_conmutacion(raiz: Path) -> None:
    (raiz / ".gitignore").write_text(".cross-model/\n", encoding="utf-8")
    (raiz / "contenido.txt").write_text("estado inicial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(raiz), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(raiz), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(raiz), "-c", "user.name=conmutacion-test",
         "-c", "user.email=conmutacion-test@example.invalid", "commit", "-qm", "base"],
        check=True,
    )


def autotest_conmutacion() -> list[str]:
    fallas: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "repo"
        raiz.mkdir()
        _preparar_repo_conmutacion(raiz)
        contenido = raiz / "contenido.txt"
        contenido.write_text("estado previo\n", encoding="utf-8")
        active = raiz / ".cross-model/active/co-explore"
        active.mkdir(parents=True)
        (active / "sembrada.json").write_text("{}\n", encoding="utf-8")

        registro, detalle = tomar_conmutacion(raiz)
        if registro is not None or "corridas activas" not in detalle or (raiz / CONMUTACION_LOCK).exists():
            fallas.append("una corrida activa sembrada no rechazó limpiamente")
        (active / "sembrada.json").unlink()

        registro, detalle = tomar_conmutacion(raiz)
        lock = raiz / CONMUTACION_LOCK
        campos = set(json.loads(lock.read_text(encoding="utf-8"))) if lock.is_file() else set()
        if registro is None or not {"pid", "timestamp", "commit", "arbol"} <= campos:
            fallas.append("cero corridas no registró pid, timestamp, commit y árbol")
        elif not liberar_conmutacion(raiz, registro, completada=True)[0] or lock.exists():
            fallas.append("una conmutación completa no liberó el cerrojo")

        huerfano = {"pid": 999999, "timestamp": "2026-01-01T00:00:00Z",
                    "commit": "0" * 40, "arbol": "0" * 40, "estado_trabajo": "0" * 64}
        lock.write_text(json.dumps(huerfano) + "\n", encoding="utf-8")
        registro, detalle = tomar_conmutacion(raiz)
        if registro is not None or "no se retira automáticamente" not in detalle:
            fallas.append("un cerrojo huérfano no detuvo el gate")
        if json.loads(lock.read_text(encoding="utf-8")) != huerfano:
            fallas.append("el gate alteró un cerrojo huérfano")
        lock.unlink()

        with ThreadPoolExecutor(max_workers=2) as pool:
            intentos = list(pool.map(lambda _n: tomar_conmutacion(raiz), range(2)))
        ganadores = [registro for registro, _detalle in intentos if registro is not None]
        if len(ganadores) != 1:
            fallas.append(f"dos intentos concurrentes produjeron {len(ganadores)} ganadores")
        elif not liberar_conmutacion(raiz, ganadores[0], completada=True)[0]:
            fallas.append("no se pudo liberar el ganador concurrente")

        registro, _detalle = tomar_conmutacion(raiz)
        if registro is None:
            fallas.append("no se pudo preparar el caso de reversión")
        else:
            contenido.write_text("edición parcial\n", encoding="utf-8")
            if liberar_conmutacion(raiz, registro, completada=False)[0] or not lock.exists():
                fallas.append("una reversión incompleta liberó el cerrojo")
            contenido.write_text("estado previo\n", encoding="utf-8")
            if not liberar_conmutacion(raiz, registro, completada=False)[0] or lock.exists():
                fallas.append("una reversión completa no liberó el cerrojo")

    for rel in (
        "skills/co-explore/SKILL.md",
        "skills/cross-implement/SKILL.md",
        "skills/cross-review/SKILL.md",
        "skills/sdd-flow/SKILL.md",
        "skills/sdd-orchestrator/SKILL.md",
    ):
        texto = (REPO / rel).read_text(encoding="utf-8")
        if (".cross-model/conmutacion.lock" not in texto
                or "antes de crear o escribir el sobre" not in texto
                or "borrarlo automáticamente" not in texto):
            fallas.append(f"{rel} no consume el cerrojo antes del despacho")
    return fallas


# ---------------------------------------------------------------------------------------------
# Modos auxiliares: sincronizar y validar el baseline.
# ---------------------------------------------------------------------------------------------


def sincronizar(raiz: Path) -> int:
    fuente = raiz / CONTRATO_FUENTE
    if not fuente.is_file():
        print(f"FALLA — no existe la fuente {CONTRATO_FUENTE}")
        return 1
    datos = fuente.read_bytes()
    copiadas = 0
    for rel in COPIAS:
        destino = raiz / rel
        if destino == fuente:
            continue
        if not destino.parent.is_dir():
            print(f"FALLA — no existe el directorio {destino.parent}")
            return 1
        if not destino.is_file() or destino.read_bytes() != datos:
            destino.write_bytes(datos)
            copiadas += 1
    print(f"ok — {len(COPIAS)} copias sincronizadas desde {CONTRATO_FUENTE} "
          f"({copiadas} reescritas)")
    return 0


_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?([.,]\d+)?"
                  r"(Z|[+-]\d{2}:?\d{2})?$")


def validar_baseline(ctx: Ctx, comprobar_commit: bool = True) -> None:
    baseline = ctx.texto(BASELINE_PATH)
    if baseline is None:
        return
    tabla = seccion(baseline, "Verification")
    ids_tabla: list[str] = []
    for t in tablas(tabla or ""):
        for fila in t[1:]:
            m = re.fullmatch(r"V\d+", fila[0].strip().strip("`"))
            if m:
                ids_tabla.append(fila[0].strip().strip("`"))
        if ids_tabla:
            break
    ctx.check(len(ids_tabla) == 20, "la tabla de `## Verification` tiene veinte filas",
              "" if len(ids_tabla) == 20 else f"leídas {len(ids_tabla)}")
    versiones = sorted(int(m.group(1)) for m in
                       re.finditer(r"^#+\s*Baseline de v(\d+)", baseline, re.MULTILINE))
    if not versiones:
        ctx.check(False, "bloque `#### Baseline de vN`", f"no existe en {BASELINE_PATH}")
        return
    bloque = seccion(baseline, f"Baseline de v{versiones[-1]}")
    filas = [f for t in tablas(bloque or "") for f in t[1:]]
    if not filas:
        ctx.check(False, f"baseline v{versiones[-1]}", "el bloque no tiene tabla de registros")
        return
    ids = [f[0].strip().strip("`") for f in filas]
    malformados = [i for i in ids if not re.fullmatch(r"V\d+", i)]
    ctx.check(not malformados, "IDs sin rangos ni agrupaciones",
              "" if not malformados else f"IDs mal formados: {malformados[:4]}")
    ctx.check(len(ids) == len(set(ids)), "un registro por fila, sin duplicados",
              "" if len(ids) == len(set(ids)) else "hay IDs repetidos")
    ctx.check(ids == ids_tabla, "mismos IDs y mismo orden que la tabla",
              "" if ids == ids_tabla else f"baseline={ids[:5]}… tabla={ids_tabla[:5]}…")
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    commits = {f[1].strip().strip("`") for f in filas if len(f) > 2}
    shas = {f[2].strip().strip("`") for f in filas if len(f) > 2}
    commit = next(iter(commits)) if len(commits) == 1 else ""
    sha_registrado = next(iter(shas)) if len(shas) == 1 else ""
    ctx.check(len(commits) == 1 and bool(re.fullmatch(r"[0-9a-f]{7,40}", commit)),
              "un único commit Git válido en todo el baseline",
              "" if len(commits) == 1 else f"commits leídos: {sorted(commits)}")
    ctx.check(len(shas) == 1 and bool(re.fullmatch(r"[0-9a-f]{64}", sha_registrado)),
              "un único sha256 válido en todo el baseline",
              "" if len(shas) == 1 else f"sha256 leídos: {sorted(shas)}")
    problemas = []
    for fila in filas:
        ident = fila[0].strip()
        if len(fila) < 6:
            problemas.append(f"{ident}: registro incompleto")
            continue
        if fila[1].strip().strip("`") != commit:
            problemas.append(f"{ident}: commit distinto")
        if fila[2].strip().strip("`") != sha:
            problemas.append(f"{ident}: sha256 del verificador no coincide")
        if not any(_ISO.match(c.strip()) for c in fila):
            problemas.append(f"{ident}: sin timestamp ISO-8601")
        if not any(c.strip() in ESTADOS_BASELINE for c in fila):
            problemas.append(f"{ident}: sin estado de {sorted(ESTADOS_BASELINE)}")
    ctx.check(not problemas, "commit, sha256, timestamp y estado por registro",
              "" if not problemas else "; ".join(problemas[:5]))
    if comprobar_commit and commit and sha_registrado:
        resultado = subprocess.run(
            ["git", "-C", str(ctx.raiz), "show",
             f"{commit}:scripts/verificar-sobre-en-vuelo.py"],
            capture_output=True,
            check=False,
        )
        sha_commit = hashlib.sha256(resultado.stdout).hexdigest() if resultado.returncode == 0 else ""
        ctx.check(resultado.returncode == 0 and sha_commit == sha_registrado,
                  "el commit registrado contiene el verificador identificado por el sha256",
                  "" if resultado.returncode == 0 and sha_commit == sha_registrado else
                  (resultado.stderr.decode("utf-8", "replace").strip() or
                   f"git show produjo sha256 {sha_commit or 'vacío'}"))
    for objetivo in ("V18", "V19"):
        fila = next((f for f in filas if f[0].strip().strip("`") == objetivo), None)
        if fila is None:
            ctx.check(False, f"{objetivo}: adjudicación escrita", "no hay registro")
            continue
        resto = [c for c in fila[5:] if c.strip()]
        ctx.check(bool(resto), f"{objetivo}: adjudicación escrita",
                  "" if resto else "el registro no la trae")


# ---------------------------------------------------------------------------------------------
# Ejecución de un modo.
# ---------------------------------------------------------------------------------------------

MODOS = {
    "1": ("AC-1 · campos y sub-esquemas exactos", ac_1),
    "1b": ("AC-1 · no-estado-semántico, sede citada y frontera", ac_1b),
    "2": ("AC-2 · transiciones, outcomes y orden del orquestador", ac_2),
    "2b": ("AC-2 · retiro, escritor único, nacimiento y adopción", ac_2b),
    "3": ("AC-3 · agregación multi-worker", ac_3),
    "3b": ("AC-3 · el ancestro no cosecha ni retira", ac_3b),
    "4": ("AC-4 · archivo, identidad y barrido por topología", ac_4),
    "5": ("AC-5 · cierre del turno, sonda y wait_budget", ac_5),
    "6": ("AC-6 · fuentes vigentes, process_ref y continuidad operativa", ac_6),
    "7": ("AC-7 · precedencia ante discrepancia", ac_7),
    "8": ("AC-8 · el límite declarado", ac_8),
    "9": ("AC-9 · el sidecar del dato nuevo", ac_9),
    "10": ("AC-10 · relanzamiento seguro", ac_10),
    "11": ("AC-11 · la cancelación como terminal propio", ac_11),
    "12": ("AC-12 · los once puntos y los siete punteros", ac_12),
    "13": ("AC-13 · siete copias idénticas, trigger y README", ac_13),
    "14": ("AC-14 · la tercera excepción y su cita", ac_14),
    "15": ("AC-15 · claves nuevas del diff de la rama completas en dueño y vista", ac_15),
    "16": ("AC-16 · las guardas del repo sin regresión", ac_16),
    "17": ("AC-17 · autoridades frescas y cierre idempotente del manifest", ac_17),
}
FILAS = {"1": "V1", "1b": "V2", "2": "V3", "2b": "V4", "3": "V5", "3b": "V6", "4": "V7",
         "5": "V8", "6": "V9", "7": "V10", "8": "V11", "9": "V12", "10": "V13", "11": "V14",
         "12": "V15", "13": "V16", "14": "V17", "15": "V18", "16": "V19", "17": "V20"}


def correr(modo: str, raiz: Path, verboso: bool = True) -> tuple[int, str]:
    nombre, fn = MODOS[modo]
    ctx = Ctx(raiz)
    resumen = fn(ctx) or "ok"
    fallas = [f for f in ctx.filas if not f[0]]
    if verboso:
        print(f"=== {FILAS[modo]} · --ac {modo} — {nombre}")
        for ok, etiqueta, detalle in ctx.filas:
            print(f"[{'OK   ' if ok else 'FALLA'}] {etiqueta}" + (f": {detalle}" if detalle else ""))
    veredicto = resumen if not fallas else f"FALLA — {len(fallas)}/{len(ctx.filas)} chequeos"
    if verboso:
        print(veredicto)
    return (1 if fallas else 0), veredicto


# ---------------------------------------------------------------------------------------------
# Corpus verde del autotest. Es el control positivo: sin él, un verificador que falla siempre por
# archivo ausente daría "rojo" con todos los mutantes y parecería sano.
# ---------------------------------------------------------------------------------------------

CONTRATO_VERDE = """# Corridas delegadas en vuelo

**Sede canónica: `skills/cross-review/corridas-en-vuelo.md`.** Las otras seis son copias generadas.

El sobre son metadatos operativos y **no reconstruye el estado semántico** de la corrida. La sede
que rechaza el estado persistido —`skills/co-explore/reference.md`— sigue vigente.

El sobre es **obligatorio** e **independiente** de `cross_model.manifest.mode`: apagar el manifest no
apaga el sobre.

| registro | qué registra | vive mientras |
|---|---|---|
| sobre de corrida en vuelo | el trabajo delegado corriendo ahora | no se cumplen las tres condiciones |
| checkpoint durable | una revisión esperando decisión humana | el gate no se resolvió |
| bitácora del orquestador | el intento de cada transición | siempre: append-only |

Orden fijo: evento de intento → sobre → tool call del despacho.

### El archivo

`.cross-model/active/<skill>/<run_id>.json`. La identidad es `(repo, skill, run_id)`.

### Los campos del sobre

| campo | qué |
|---|---|
| `run_id` | sufijo corto de corrida |
| `skill` | identidad escalar de la skill |
| `mode` | modo operativo |
| `owner` | conductor propietario |
| `parent` | sobre padre |
| `children` | hijas, escritas por el padre |
| `descendants_summary` | resumen de la descendencia |
| `workers` | los workers directos |
| `scope` | `scope = {repo, worktree}` |
| `transport` | derivado |
| `harvest_pending` | marca explícita de cosecha pendiente |
| `proxima_accion` | próxima acción al recuperar el control |
| `manifest_seed` | seed inmutable del manifest habilitado |
| `manifest_first_dispatch_at` | timestamp write-once, inicialmente `null` |

`transport` raíz es el único campo **derivado**: el valor común de los intentos vigentes, o `mixto`.

`proxima_accion` es una **cadena opcional en la raíz**. `null` y la ausencia del campo son casos
**válidos**: significan "sin acción declarada". El **conductor propietario** es el **único** que la
**escribe**; cuando **recupera el control**, la **lee** durante el **barrido**. Al cerrar la corrida,
**transfiere** el campo al **registro de cierre** junto con el **resto del sobre**; esta **transición
no depende** de un **tombstone**. En una recuperación `cli-exec`, el conductor **transfiere**
`proxima_accion` del sobre activo al **registro de cierre** antes de retirarlo.

**El par del manifest es condicional e indivisible.** Antes de cualquier preflight, el sobre nace
con ambos nodos cuando el manifest está habilitado. `manifest_seed` contiene exactamente `skill`,
`mode`, `preflight_started_at`, `families`, `transport` y `selection`, y es inmutable.
`manifest_first_dispatch_at` nace en `null` y se fija una sola vez inmediatamente antes de la
primera tool call. Si ningún worker fue seleccionado o no se resolvió ninguna vía, queda `null`,
`workers[]` puede quedar vacío y el `transport` del seed usa `none`. Si un worker falla su preflight
después de resolver la vía, `families` y `manifest_seed.transport` conservan ese worker y esa vía.
En modo off ambos nodos permanecen ausentes; no se vuelven a leer ni inventar al retomar.

### Los campos por worker

| campo | qué |
|---|---|
| `name` | nombre del agente |
| `family` | familia |
| `write` | read-only o escritor |
| `attempts` | sus intentos |

### Los campos por intento

| campo | qué |
|---|---|
| `attempt_id` | identidad del intento |
| `transport` | la vía de este intento |
| `output` | ruta exclusiva de salida |
| `process_ref` | `process_ref = {tipo, referencia, evidencia_de_frescura, autoridad}`, `null` si no hay proceso consultable |
| `wait_budget` | `wait_budget = {deadline, limite, consumidos}`, con `consumidos <= limite` |
| `harvested` | si este intento ya se cosechó |

Ante frescura no comprobada el proceso se clasifica **incierto** y **nunca se cancela**.

### Varios workers en una corrida

La **identidad** es por worker; la **fuente** y la **precedencia** también son por worker. La regla
de agregación define qué **se informa**, cómo se hace la **cosecha parcial** y cuándo la corrida
agregada **deja de estar en vuelo**. Cada hija publica su `descendants_summary`.

Un conductor administra solo sus **corridas directas**: un **ancestro** no cosecha ni retira sobres
**indirectos**.

### Transiciones del sobre

| transición | qué pasa |
|---|---|
| `nace` | antes del despacho, nunca después |
| `relee` | al recuperar el control |
| `cosecha` | una sola vez |
| `retira` | solo con las tres condiciones |

El sobre **nace antes del despacho**. `harvest_pending` impide una **segunda cosecha**.

**Un solo escritor: el creador.** Quien encuentra un sobre ajeno **lee e informa** y **nunca
escribe**. Toda actualización se publica **temporal** en el mismo directorio + **rename atómico**, y
el barrido **ignora** los **temporales**. El nacimiento va **sin reemplazo**: **falla si la ruta
existe** y ante colisión se genera otro `run_id`.

### Outcome de la espera

| outcome | efecto |
|---|---|
| `resultado_entregado` | `habilita_evaluar_retiro` |
| `corte_presupuesto` | `sigue_activo` |
| `error` | `habilita_evaluar_retiro` |
| `(cancelacion, cese_confirmado)` | `habilita_evaluar_retiro` |
| `(cancelacion, cese_incierto)` | `recovery-required` |

La `cancelacion` es un terminal propio, distinto del `corte_presupuesto` y del `error`. Vencer el
deadline nunca retira el sobre.

### Condiciones del retiro

| condición | qué exige |
|---|---|
| terminal comprobado | uno de los outcomes terminales |
| artefacto validado o descartado | nada queda sin adjudicar |
| sin recursos propios vivos, o transferidos a un **registro de cierre** | propiedad y próxima acción transferidas |

Las tres son **simultáneas**.

Un checkpoint intermedio transfiere el carrier y no materializa el manifest. Solo un outcome
terminal resuelve el manifest antes del retiro terminal.

### Adopción

Es la **única transición** que otra sesión puede ejecutar, y solo con **autorización explícita** del
**usuario** en el momento. Registra **sucesor**, **decisión** y **motivo**.

### El barrido de corridas activas

| topología | dónde vive | recorrido |
|---|---|---|
| repo único | `<repo>/.cross-model/active/*/` | listar los subdirectorios por skill, ignorando temporales |
| skill standalone | `<working_dir>/.cross-model/active/*/` | listar los subdirectorios por skill |
| orquestación multi-repo | la carpeta contenedora | enumerar **siempre** todos los `.sdd/*/manifest.yml` y listar cada repo |

`children` es **optimización** del orden, nunca la autoridad del recorrido.

### El cierre del turno

Mientras haya una corrida registrada, **todo turno** del conductor cierra **informando** su estado.

### La sonda por turno

Es **no bloqueante**, **una por turno**, **sin retry**, y **no modifica** el `deadline` ni el
**contador** del transporte. Solo un **poll real** incrementa `consumidos`.

### Fuente por transporte

| transporte | fuente |
|---|---|
| `subagent` | `ninguna` — **no hay fuente consultable** a mitad de vuelo |
| `cli-exec` | `archivo+proceso` |
| `cli-resume` | `archivo+proceso` |

### Precedencia ante discrepancia

| caso | resolución |
|---|---|
| `D1` — proceso activo + artefacto completo | `cosechar` |
| `D2` — proceso terminado + artefacto ausente o inválido | `clasificar_error` |
| `D3` — deadline vencido + proceso incierto | `informar_activo` |
| `D4` — artefacto completo + cleanup pendiente | `esperar_cleanup` |

`esperar_cleanup` **ejecuta la transferencia** al **registro de cierre** y recién entonces habilita
evaluar el retiro.

### El límite declarado

Sin fuente consultable se declara el límite **en una línea** en vez de **simular** una verificación,
y la salida **no afirma** que el worker sigue **ejecutándose**.

### El dato nuevo del usuario

El destino es `.cross-model/active/<skill>/<run_id>.datos.jsonl`, **append-only**:
`<run_id>.datos.jsonl = {origen, destinos, recibido_en, disposicion}`.

| obligación | qué exige |
|---|---|
| ronda siguiente **por defecto** | el dato se consume en el despacho siguiente |
| abortar solo por pedido **explícito** | nunca por iniciativa del conductor |
| conjunto explícito de `destinos`, que puede ser **vacío** | siempre escrito |
| el sidecar registra su `origen` | quién lo aportó |
| **nunca** sobre el artefacto que el intento vigente **ya consumió** | append-only por construcción |
| en un despacho de **una sola pasada** no hay ronda siguiente | se informa que no habrá consumo |
| si la corrida termina antes, queda `no_consumido` y el sidecar **sobrevive** al retiro | lo lee el próximo despacho |

### Relanzamiento seguro

**Cese confirmado** del worker anterior; **rutas exclusivas** por intento; el escritor nuevo queda
**bloqueado** mientras el anterior pueda tocar el **árbol**. Cada intento es una **entrada** nueva de
`attempts[]`.
"""

_RECHAZO = ("Para los dos vale el mismo límite del ecosistema: no hay máquina de estados "
            "persistente, ni esquema formal, ni validador propio, ni versionado.\n"
            "Ese nivel de estado persistido ya se rechazó por escrito, y este ítem nunca se "
            "ejercitó.\n")

_SKILL_TPL = """---
name: {skill}
---

# {skill}

## Corridas delegadas en vuelo

Regla canónica: `corridas-en-vuelo.md`, hermano de este archivo.

{puntos}

## Otras reglas de la skill

{extra}
"""

_README_TPL = """# {skill}

Cada corrida deja su manifest en `.cross-model/runs/` y su sobre activo en `.cross-model/active/`.
El sobre **no** lo apaga `cross_model.manifest.mode`: es obligatorio e independiente de esa clave.

Riesgo de una instalación con copias de versiones **mezcladas**: la **sede canónica** va en la
primera línea de cada copia.
"""


def corpus_verde(raiz: Path) -> None:
    """Escribe un árbol mínimo pero completo que satisface los veinte modos de parser."""
    def manifiesto(terminales: str, autoridades: str) -> str:
        return ("La secuencia es selección → seed/sobre → preflight → timestamp write-once "
                f"→ primera tool call → terminal. El manifest proyecta {terminales} desde {autoridades}. "
                "Un preflight sin worker seleccionado o sin vía resuelta conserva `null` y usa "
                "`preflight_started_at`/`transport: none`. Si la vía estaba resuelta y falla el "
                "preflight, el seed conserva esa vía aunque no haya despacho. `.cross-model/runs/` "
                "nunca es fuente.")

    puntos = {
        "co-explore": ["- fan-out dual (`explore`/`counter-plan`/`investigate`)",
                       "- worker por ronda del modo `debate`"],
        "cross-review": ["- revisor por ronda, con resume"],
        "cross-implement": ["- implementador inicial", "- rondas del fix loop"],
        "sdd-flow": ["- subagente de exploración en `analyze`",
                     "- reviewer de la revisión final de diff"],
        "sdd-orchestrator": ["- fan-out por repo (Fase 2.3)"],
        "sdd-pr-feedback": ["- implement delegado sobre la Vía B"],
        "bitbucket-code-review": ["- panel de revisores externos",
                                  "- validador adversarial por hallazgo"],
    }
    manifiestos = {
        "co-explore": manifiesto("`completed` y `map_failure`", "esas autoridades"),
        "cross-review": manifiesto("`APPROVED`, `REVISE` y `UNAVAILABLE`", "`manifest_authorities`"),
        "cross-implement": manifiesto("`IMPLEMENTED`, `PARTIAL` y `UNAVAILABLE`", "esas autoridades"),
        "bitbucket-code-review": manifiesto("`PUBLISHED`, `PROPOSED` y `UNAVAILABLE`", "esas autoridades"),
    }
    extras = {
        "sdd-orchestrator": "El orden es fijo: **bitácora** → **sobre** → **despacho**.",
        "co-explore": ("**Tres excepciones acotadas, todas conversacionales.** La nota de límite, la "
                       "advertencia de una sola voz y el **aviso de corridas delegadas en vuelo**."),
        "sdd-flow": ("- **Los artefactos no citan la co-exploración.** El checkpoint conversacional "
                     "no está alcanzado: vale la **excepción** de `co-explore` que cubre el aviso "
                     "de corridas delegadas **en vuelo**."),
    }
    for skill in SKILLS:
        d = raiz / "skills" / skill
        d.mkdir(parents=True, exist_ok=True)
        extra = "\n\n".join(p for p in (extras.get(skill, ""), manifiestos.get(skill, "")) if p)
        (d / "SKILL.md").write_text(_SKILL_TPL.format(
            skill=skill, puntos="\n".join(puntos[skill]), extra=extra),
            encoding="utf-8")
    (raiz / CONTRATO_FUENTE).write_text(CONTRATO_VERDE, encoding="utf-8")
    sincronizar_silencioso(raiz)
    for rel in READMES:
        (raiz / rel).write_text(_README_TPL.format(skill=Path(rel).parent.name), encoding="utf-8")
    (raiz / "skills/co-explore/reference.md").write_text(
        "# co-explore — Referencia\n\n### Truncado previo al dispatch\n\n"
        "Antes de truncar y redespachar, leer `skills/cross-review/corridas-en-vuelo.md` → "
        "\"Invariantes de recuperación\". Esas reglas determinan cuándo el intento anterior dejó "
        "de reservar sus rutas y cuándo puede nacer el siguiente.\n\n"
        "Corre después de la decisión de retoma, nunca al entrar al modo.\n\n"
        "Al redespachar se vacían las dos formas de cierre y sus temporales; recién después se "
        "lanza.\n\n"
        "El sobre de corrida entra en el conjunto evaluado: antes de redespachar, el conductor lo "
        "relee, porque si sobrevive sin releerse conserva referencias obsoletas.\n\n"
        "Un intento anterior que aún puede escribir bloquea el truncado y el redespacho sobre esas "
        "rutas.\n\n"
        "### Glosario\n\nTruncado nombra la limpieza previa al lanzamiento.\n\n"
        "### El descriptor de corrida y su retiro\n\n" + _RECHAZO, encoding="utf-8")
    (raiz / "skills/cross-review/reference.md").write_text(
        "# cross-review — Referencia\n\n"
        "## Checkpoint durable\n\n"
        "El checkpoint conserva `manifest_seed` exactamente: una diferencia de valor frente al "
        "sobre invalida el descriptor. `manifest_first_dispatch_at` conserva `null` o el timestamp "
        "write-once, nunca un reloj de rehidratación. Con manifest deshabilitado los dos nodos "
        "permanecen ausentes y no se serializan. El `resume` rehidrata estas autoridades y no se "
        "inicia otra corrida.\n\n"
        "## Manifest de corrida\n\n"
        "El manifest registra la corrida terminada; su hermano activo es el sobre de "
        "`corridas-en-vuelo.md`, y **se retira** cuando el manifest se escribe. Dos corridas del "
        "mismo segundo usan `run_id` distintos y no colisionan. Un retry consulta si la ruta existe. "
        "Si la ruta existe, termina sin abrir, validar, recalcular ni reescribir. Si la creación "
        "pierde una carrera `EEXIST`, el cierre termina sin abrir, recalcular ni reescribir. Un segundo cierre conserva "
        "bytes idénticos. Un manifest anterior ilegible es irrelevante. `.cross-model/runs/` no se "
        "lee ni se copia como plantilla. Un checkpoint intermedio transfiere el carrier y no "
        "materializa el manifest.\n\n"
        "**Centinelas.** La corrida A usa `started_at: 2026-07-31T14:02:11Z` y `duration_s: 412`; "
        "la corrida B usa `started_at: 2026-08-01T09:00:03Z` y `duration_s: 7`.\n",
        encoding="utf-8")
    (raiz / "CLAUDE.md").write_text(
        "# CLAUDE.md\n\n- Si la skill toca `corridas-en-vuelo.md`, correr "
        "`python3 scripts/verificar-sobre-en-vuelo.py --sincronizar` y `--ac 13`.\n",
        encoding="utf-8")


def sincronizar_silencioso(raiz: Path) -> None:
    datos = (raiz / CONTRATO_FUENTE).read_bytes()
    for rel in COPIAS:
        destino = raiz / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)


REQUISITOS_BASELINE = {
    "1": "AC-1 — campos raíz, por worker y por intento, más sub-esquemas exactos",
    "1b": "AC-1 — no-estado semántico, sede de rechazo y frontera entre registros",
    "2": "AC-2 — transiciones, outcomes y orden del orquestador",
    "2b": "AC-2 — retiro, escritor único, nacimiento y adopción",
    "3": "AC-3 — agregación multi-worker y resumen de descendencia",
    "3b": "AC-3 — un ancestro no cosecha ni retira sobres indirectos",
    "4": "AC-4 — archivo, identidad y barrido por topología",
    "5": "AC-5 — cierre de turno, sonda y presupuesto de espera",
    "6": "AC-6 — fuentes vigentes, referencia de proceso y continuidad operativa",
    "7": "AC-7 — precedencia ante discrepancias",
    "8": "AC-8 — límite declarado sin afirmar ejecución",
    "9": "AC-9 — sidecar append-only para datos nuevos",
    "10": "AC-10 — relanzamiento seguro y rutas exclusivas",
    "11": "AC-11 — error y cancelación como terminales propios",
    "12": "AC-12 — once puntos de despacho y siete punteros locales",
    "13": "AC-13 — siete copias idénticas, trigger y README",
    "14": "AC-14 — tercera excepción y cita normativa",
    "15": "AC-15 — claves nuevas del diff de la rama completas en dueño y vista; en la rama base "
          "no hay sujeto",
    "16": "AC-16 — guardas del repo sin regresión",
    "17": "AC-17 — autoridades frescas, carriers y cierre idempotente del manifest",
}


BASELINE_TPL = """# Baseline normativo del sobre en vuelo

## Verification

| ID | Requisito | Comando | Esperado |
|---|---|---|---|
{filas}

### v3

Identidad: `({baseline_commit}, sha256 del verificador)`. Sucede a `v2`: el inventario de puntos de
despacho bajó de trece a once al retirarse el modo de implementación por task.

#### Baseline de v3

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
{registros}
"""


def corpus_baseline(raiz: Path, sha: str, commit: str = "0123456") -> None:
    filas = "\n".join(
        f"| {FILAS[m]} | {REQUISITOS_BASELINE[m]} | `--ac {m}` | ok |" for m in MODOS)
    registros = "\n".join(
        f"| {FILAS[m]} | {commit} | {sha} | 2026-08-06T10:00:00-05:00 | "
        f"{'GREEN_ALREADY' if m in ('15', '16') else 'RED'} | "
        f"{'no regresión: pasa por construcción' if m in ('15', '16') else '—'} |"
        for m in MODOS)
    destino = raiz / BASELINE_PATH
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(BASELINE_TPL.format(
        filas=filas, registros=registros, baseline_commit=commit), encoding="utf-8")


# Mutantes: (nombre, archivo relativo, viejo, nuevo, modo que debe fallar, señal en el mensaje).
MUTANTES = [
    ("clave faltante", CONTRATO_FUENTE, "| `owner` | conductor propietario |\n", "", "1", "owner"),
    ("clave sobrante", CONTRATO_FUENTE, "| `owner` | conductor propietario |",
     "| `owner` | conductor propietario |\n| `estado_semantico` | de más |", "1",
     "estado_semantico"),
    ("escritor de próxima acción roto", CONTRATO_FUENTE,
     "El **conductor propietario** es el **único** que la\n**escribe**;",
     "Cualquier conductor la escribe;", "1", "escritor"),
    ("lector de próxima acción roto", CONTRATO_FUENTE,
     "cuando **recupera el control**, la **lee** durante el **barrido**.",
     "El campo no se lee durante la recuperación.", "1", "lector"),
    ("transición de próxima acción rota", CONTRATO_FUENTE,
     "**transfiere** el campo al **registro de cierre** junto con el **resto del sobre**;",
     "descarta el campo al cerrar;", "1", "transición"),
    ("dependencia de próxima acción reintroducida", CONTRATO_FUENTE,
     "esta **transición\nno depende** de un **tombstone**.",
     "esta transición depende de un artefacto de cierre.", "1", "tombstone"),
    ("fila faltante", CONTRATO_FUENTE, "| `cli-resume` | `archivo+proceso` |\n", "", "6",
     "cli-resume"),
    ("fila sobrante", CONTRATO_FUENTE, "| `D4` — artefacto completo + cleanup pendiente | `esperar_cleanup` |",
     "| `D4` — artefacto completo + cleanup pendiente | `esperar_cleanup` |\n"
     "| `D5` — inventada | `cosechar` |", "7", "D5"),
    ("tupla intercambiada", CONTRATO_FUENTE,
     "| `D2` — proceso terminado + artefacto ausente o inválido | `clasificar_error` |",
     "| `D2` — proceso terminado + artefacto ausente o inválido | `cosechar` |", "7", "D2"),
    ("copia divergente", "skills/sdd-flow/corridas-en-vuelo.md", "# Corridas delegadas en vuelo",
     "# Corridas delegadas en vuelo (editada a mano)", "13", "sdd-flow"),
    ("puntero ausente", "skills/cross-implement/SKILL.md",
     "Regla canónica: `corridas-en-vuelo.md`, hermano de este archivo.", "", "12",
     "cross-implement"),
    ("cláusula de reporte por turno borrada", CONTRATO_FUENTE,
     "Mientras haya una corrida registrada, **todo turno** del conductor cierra **informando** su "
     "estado.", "El conductor sondea.", "5", "cierre del turno"),
    # Los dos siguientes cubren chequeos que ya estaban verdes en el árbol real —una construcción
    # operativa y la cláusula del README—: sin un mutante propio, ninguno se probó en rojo.
    ("orden operativo borrado, con el término presente en otra sección",
     "skills/co-explore/reference.md",
     "Corre después de la decisión de retoma, nunca al entrar al modo.",
     "El orden se decide al ejecutar.", "6", "orden posterior a la retoma"),
    ("cláusula de independencia del README borrada", "skills/cross-review/README.md",
     "El sobre **no** lo apaga `cross_model.manifest.mode`: es obligatorio e independiente de esa "
     "clave.", "Se apaga con `cross_model.manifest.mode`.", "13", "manifest.mode"),
    ("cláusula de rechazo del estado persistido borrada", "skills/co-explore/reference.md",
     "no hay máquina de estados persistente", "hay estado", "1b", "rechazo del estado persistido"),
    ("regla local de retiro reintroducida", "skills/co-explore/reference.md",
     "Ese nivel de estado persistido ya se rechazó por escrito",
     "La única salida se decide aquí; ese nivel ya se rechazó por escrito",
     "2", "la unica salida"),
    ("manifest: par off deja de estar ausente", CONTRATO_FUENTE,
     "En modo off ambos nodos permanecen ausentes; no se vuelven a leer",
     "En modo off ambos nodos se reconstruyen al cerrar; no se vuelven a leer", "17",
     "modo off mantiene ausente"),
    ("manifest: terminal sin worker pierde fallback", CONTRATO_FUENTE,
     "Si ningún worker fue seleccionado o no se resolvió ninguna vía, queda `null`,\n"
     "`workers[]` puede quedar vacío y el `transport` del seed usa `none`.",
     "Si ningún worker fue seleccionado, se inventa un lanzamiento.", "17",
     "terminal sin worker"),
    ("manifest: preflight con vía resuelta degrada a none", CONTRATO_FUENTE,
     "Si un worker falla su preflight\ndespués de resolver la vía, `families` y "
     "`manifest_seed.transport` conservan ese worker y esa vía.",
     "Si un worker falla su preflight después de resolver la vía, el seed cambia a `none`.", "17",
     "preflight con vía resuelta"),
    ("manifest: checkpoint acepta seed divergente", "skills/cross-review/reference.md",
     "una diferencia de valor frente al sobre invalida el descriptor",
     "una diferencia de valor frente al sobre se corrige al cerrar", "17", "igualdad estructural"),
    ("manifest: resume abre otra corrida", "skills/cross-review/reference.md",
     "El `resume` rehidrata estas autoridades y no se inicia otra corrida.",
     "El `resume` descarta estas autoridades e inicia otra corrida.", "17", "resume rehidrata"),
    ("manifest: sentinelas heredados", "skills/cross-review/reference.md",
     "la corrida B usa `started_at: 2026-08-01T09:00:03Z` y `duration_s: 7`",
     "la corrida B usa `started_at: 2026-07-31T14:02:11Z` y `duration_s: 412`", "17", "sentinelas"),
    ("manifest: rutas del mismo segundo colisionan", "skills/cross-review/reference.md",
     "mismo segundo usan `run_id` distintos y no colisionan",
     "mismo segundo colisionan aunque usen `run_id` distintos", "17", "dos rutas del mismo segundo"),
    ("manifest: retry abre cierre existente", "skills/cross-review/reference.md",
     "Si la ruta existe, termina sin abrir, validar, recalcular ni reescribir.",
     "Si la ruta existe, la abre, valida, recalcula y reescribe.", "17", "consulta existencia sin leer"),
    ("manifest: EEXIST deja de ser idempotente", "skills/cross-review/reference.md",
     "Si la creación pierde una carrera `EEXIST`, el cierre termina sin abrir, recalcular ni reescribir.",
     "Si la creación pierde una carrera `EEXIST`, recalcula y reemplaza el cierre.", "17", "EEXIST cierra"),
    ("manifest: segundo cierre cambia bytes", "skills/cross-review/reference.md",
     "Un segundo cierre conserva bytes idénticos.",
     "Un segundo cierre actualiza los bytes.", "17", "segundo cierre conserva bytes"),
    ("manifest: cierre previo ilegible bloquea", "skills/cross-review/reference.md",
     "Un manifest anterior ilegible es irrelevante.",
     "Un manifest anterior ilegible bloquea el cierre.", "17", "manifest anterior ilegible"),
    ("manifest: runs vuelve a ser plantilla", "skills/cross-review/reference.md",
     "`.cross-model/runs/` no se lee ni se copia como plantilla.",
     "`.cross-model/runs/` no se lee y se copia como plantilla.", "17", "runs nunca es fuente"),
    ("manifest: checkpoint se confunde con terminal", "skills/cross-review/reference.md", "Un checkpoint intermedio transfiere el carrier y no materializa el manifest.", "Un checkpoint intermedio materializa el manifest antes de transferir el carrier.", "17", "checkpoint transfiere el carrier"),
    ("manifest: carrier canónico cierra en checkpoint", CONTRATO_FUENTE, "Un checkpoint intermedio transfiere el carrier y no materializa el manifest.", "Un checkpoint intermedio materializa el manifest al transferir el carrier.", "17", "carrier canónico distingue checkpoint"),
    ("manifest: secuencia co-explore rota", "skills/co-explore/SKILL.md",
     "primera tool call → terminal. El manifest proyecta `completed`",
     "primera tool call. El manifest proyecta `completed`", "17", "productor co-explore: secuencia"),
    ("manifest: terminal cross-review omitido", "skills/cross-review/SKILL.md",
     "`APPROVED`, `REVISE` y `UNAVAILABLE`",
     "`APPROVED` y `REVISE`", "17", "productor cross-review: terminales"),
    ("manifest: fallback cross-implement roto", "skills/cross-implement/SKILL.md",
     "`preflight_started_at`/`transport: none`",
     "un timestamp terminal y transporte inventado", "17", "productor cross-implement: preflight"),
    ("manifest: bitbucket lee runs", "skills/bitbucket-code-review/SKILL.md",
     "`.cross-model/runs/` nunca es fuente.",
     "`.cross-model/runs/` es la plantilla del cierre.", "17", "productor bitbucket-code-review: runs"),
]


def _preparar_repo_config(raiz: Path) -> None:
    """Repo mínimo para ejercitar `--ac 15` contra el merge-base por su camino real."""
    sha_base, causa = resolver_base(REPO)
    if sha_base is None:
        raise RuntimeError(causa)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=raiz, check=True)
    for rel, _ in SUPERFICIES_CONFIG:
        contenido = subprocess.run(["git", "show", f"{sha_base}:{rel}"], cwd=REPO,
                                   capture_output=True, text=True, check=True).stdout
        destino = raiz / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    subprocess.run(["git", "add", "skills"], cwd=raiz, check=True)
    subprocess.run(["git", "-c", "user.name=Autotest", "-c", "user.email=autotest@example.invalid",
                    "commit", "-q", "-m", "base"], cwd=raiz, check=True)
    subprocess.run(["git", "switch", "-q", "-c", "feature"], cwd=raiz, check=True)
    for rel, _ in SUPERFICIES_CONFIG:
        destino = raiz / rel
        destino.write_text((REPO / rel).read_text(encoding="utf-8"), encoding="utf-8")


def _indices_bloque_config(texto: str, heading: str) -> tuple[int, int]:
    """Índices del fence YAML completo de una superficie usada por los mutantes."""
    lineas = texto.splitlines(keepends=True)
    nivel = inicio = None
    for i, linea in enumerate(lineas):
        encabezado = re.match(r"^(#+)\s+(.*)$", linea)
        if nivel is None:
            if re.match(rf"^#+\s+{heading}(?:\s|$)", linea):
                nivel = len(encabezado.group(1)) if encabezado else 0
            continue
        if inicio is None:
            if encabezado:
                if re.match(rf"^#+\s+{heading}(?:\s|$)", linea):
                    nivel = len(encabezado.group(1))
                    continue
                break
            if re.match(r"^\s*```yaml(?:\s|$)", linea):
                inicio = i
            continue
        if re.match(r"^\s*```", linea):
            return inicio, i
    raise ValueError(f"no se encontró el bloque YAML de {heading}")


def _reemplazar_bloque_config(texto: str, heading: str, contenido: str) -> str:
    lineas = texto.splitlines(keepends=True)
    inicio, fin = _indices_bloque_config(texto, heading)
    return "".join(lineas[:inicio + 1]) + contenido.rstrip("\n") + "\n" + "".join(lineas[fin:])


def _inyectar_clave_config(texto: str, heading: str, clave: str) -> str:
    lineas = texto.splitlines(keepends=True)
    inicio, _ = _indices_bloque_config(texto, heading)
    lineas.insert(inicio + 1, f"{clave}: true\n")
    return "".join(lineas)


def _retirar_bloque_config(texto: str, heading: str) -> str:
    lineas = texto.splitlines(keepends=True)
    inicio, fin = _indices_bloque_config(texto, heading)
    return "".join(lineas[:inicio] + lineas[fin + 1:])


def _correr_ac15_temporal(raiz: Path) -> tuple[int, str]:
    resultado = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--ac", "15",
                                "--raiz", str(raiz)], capture_output=True, text=True)
    return resultado.returncode, resultado.stdout + resultado.stderr


def autotest() -> int:
    print("=== Gate de conmutación: drenaje, exclusión y recuperación")
    fallas = autotest_conmutacion()
    print(f"[{'OK   ' if not fallas else 'FALLA'}] protocolo de conmutación: "
          f"{'ok' if not fallas else '; '.join(fallas)}")

    print("=== Control positivo: corpus verde completo")
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "verde"
        raiz.mkdir()
        corpus_verde(raiz)
        corpus_baseline(raiz, hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        modos_parser = [m for m in MODOS if m not in ("15", "16")]
        for modo in modos_parser:
            rc, veredicto = correr(modo, raiz, verboso=False)
            print(f"[{'OK   ' if rc == 0 else 'FALLA'}] --ac {modo}: {veredicto}")
            if rc:
                fallas.append(f"corpus verde: --ac {modo} → {veredicto}")
                correr(modo, raiz, verboso=True)
        ctx = Ctx(raiz)
        validar_baseline(ctx, comprobar_commit=False)
        malas = [f for f in ctx.filas if not f[0]]
        print(f"[{'OK   ' if not malas else 'FALLA'}] --validar-baseline: "
              f"{'ok' if not malas else malas}")
        if malas:
            fallas.append(f"corpus verde: --validar-baseline → {malas}")
    print("(--ac 15 se prueba abajo por integración contra repos temporales; --ac 16 queda fuera "
          "del corpus porque ejecuta las guardas del repo.)")
    if fallas:
        print("\nRESULTADO: FALLA — el control positivo no cierra; los mutantes no probarían nada")
        for f in fallas:
            print(f"  - {f}")
        return 1

    print("\n=== --ac 15 por integración: control negativo y mutante")

    def cambiar_heading(texto: str) -> str:
        return texto.replace("## Esquema de `.specify/config.yml`",
                             "## Encabezado retirado por el autotest", 1)

    def sembrar_retiro(raiz: Path) -> None:
        """Deja una clave NUEVA y completa en dueño y vista, para que el retiro tenga sujeto.

        No se usa una clave real del repo —antes era `cross_model.families`— porque eso ata el
        autotest de la guarda al contenido de un flujo concreto: sobre una rama sin esa clave el
        caso no se puede construir, y la guarda queda sin poder probarse por una razón que nada
        tiene que ver con la guarda. El sujeto tiene que ser NUEVO respecto del merge-base: el
        predicado solo mira las claves nuevas, así que retirar una preexistente no probaría nada.
        """
        for rel, heading in (DUENOS_CONFIG[0], VISTA_CONFIG):
            ruta = raiz / rel
            ruta.write_text(
                _inyectar_clave_config(ruta.read_text(encoding="utf-8"), heading,
                                       "autotest_retiro"),
                encoding="utf-8")

    def retirar_sembrada(texto: str) -> str:
        patron = "autotest_retiro: true\n"
        if patron not in texto:
            raise ValueError("la clave sembrada no está en el dueño")
        return texto.replace(patron, "", 1)

    casos_config = [
        ("solo-en-dueno", DUENOS_CONFIG[0],
         lambda texto: _inyectar_clave_config(texto, DUENOS_CONFIG[0][1],
                                               "autotest_solo_dueno"),
         ("autotest_solo_dueno", DUENOS_CONFIG[0][0], VISTA_CONFIG[0])),
        ("solo-en-vista", VISTA_CONFIG,
         lambda texto: _inyectar_clave_config(texto, VISTA_CONFIG[1],
                                               "autotest_solo_vista"),
         ("autotest_solo_vista", DUENOS_CONFIG[0][0], VISTA_CONFIG[0])),
        ("retiro-de-dueno", DUENOS_CONFIG[0], retirar_sembrada,
         ("autotest_retiro", DUENOS_CONFIG[0][0], VISTA_CONFIG[0]), sembrar_retiro),
        ("extractor-sin-heading", DUENOS_CONFIG[0], cambiar_heading,
         (DUENOS_CONFIG[0][0], "heading ausente")),
        ("extractor-sin-fence", DUENOS_CONFIG[1],
         lambda texto: _retirar_bloque_config(texto, DUENOS_CONFIG[1][1]),
         (DUENOS_CONFIG[1][0], "bloque yaml ausente")),
        ("extractor-yaml-invalido", DUENOS_CONFIG[2],
         lambda texto: _reemplazar_bloque_config(texto, DUENOS_CONFIG[2][1], "clave: ["),
         (DUENOS_CONFIG[2][0], "yaml inválido")),
        ("extractor-raiz-no-dict", DUENOS_CONFIG[3],
         lambda texto: _reemplazar_bloque_config(texto, DUENOS_CONFIG[3][1], "- valor"),
         (DUENOS_CONFIG[3][0], "raíz no es un mapa")),
        ("extractor-bloque-posterior", DUENOS_CONFIG[0],
         lambda texto: _retirar_bloque_config(texto, DUENOS_CONFIG[0][1]),
         (DUENOS_CONFIG[0][0], "bloque yaml ausente")),
    ]
    for nombre, superficie, mutar, senales, *resto in casos_config:
        sembrar = resto[0] if resto else None
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp) / "repo"
            raiz.mkdir()
            try:
                _preparar_repo_config(raiz)
                if sembrar is not None:
                    sembrar(raiz)
                rc_verde, salida_verde = _correr_ac15_temporal(raiz)
                ruta = raiz / superficie[0]
                ruta.write_text(mutar(ruta.read_text(encoding="utf-8")), encoding="utf-8")
                rc_rojo, salida_roja = _correr_ac15_temporal(raiz)
            except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as e:
                fallas.append(f"{nombre}: no se pudo construir el caso — {e}")
                print(f"[FALLA] {nombre}: no se pudo construir el caso — {e}")
                continue
            diagnostico = norm(salida_roja)
            ok = rc_verde == 0 and rc_rojo != 0 and all(norm(s) in diagnostico for s in senales)
            print(f"[{'OK   ' if ok else 'FALLA'}] {nombre}: sin mutante "
                  f"{'verde' if rc_verde == 0 else 'ROJO'} · con mutante "
                  f"{'rojo por su causa' if rc_rojo != 0 and all(norm(s) in diagnostico for s in senales) else 'sin la señal esperada'}")
            if not ok:
                fallas.append(f"{nombre}: verde rc={rc_verde}; mutante rc={rc_rojo}; "
                              f"señales={senales}; salida={salida_roja[:300]!r}; "
                              f"control={salida_verde[:160]!r}")

    print("\n=== Mutantes, uno por vez")
    for nombre, rel, viejo, nuevo, modo, senal in MUTANTES:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp) / "mutante"
            raiz.mkdir()
            corpus_verde(raiz)
            ruta = raiz / rel
            texto = ruta.read_text(encoding="utf-8")
            if viejo not in texto:
                fallas.append(f"{nombre}: el texto a mutar no está en {rel}")
                print(f"[FALLA] {nombre}: no se pudo aplicar (patrón ausente en {rel})")
                continue
            ruta.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")
            if rel == CONTRATO_FUENTE:
                sincronizar_silencioso(raiz)  # aislar el efecto: si no, --ac 13 también caería
            ctx = Ctx(raiz)
            resumen = MODOS[modo][1](ctx) or "ok"
            malas = [f for f in ctx.filas if not f[0]]
            mensaje = " ".join(f"{e}: {d}" for _, e, d in malas)
            ok = bool(malas) and norm(senal) in norm(mensaje)
            print(f"[{'OK   ' if ok else 'FALLA'}] {nombre} → --ac {modo}: "
                  f"{len(malas)} chequeos en rojo" + (f" · señal «{senal}» presente" if ok else
                                                      f" · señal «{senal}» AUSENTE ({resumen})"))
            if not ok:
                fallas.append(f"{nombre}: --ac {modo} no falló por su motivo — {mensaje[:200]}")

    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "baseline"
        raiz.mkdir()
        corpus_verde(raiz)
        corpus_baseline(raiz, "0" * 64)
        ctx = Ctx(raiz)
        validar_baseline(ctx, comprobar_commit=False)
        malas = [f for f in ctx.filas if not f[0]]
        mensaje = " ".join(f"{e}: {d}" for _, e, d in malas)
        ok = bool(malas) and "sha256" in mensaje
        print(f"[{'OK   ' if ok else 'FALLA'}] sha256 del verificador desalineado → "
              f"--validar-baseline: {len(malas)} en rojo")
        if not ok:
            fallas.append(f"baseline con sha ajeno: no falló por su motivo — {mensaje[:200]}")

    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "baseline-git"
        raiz.mkdir()
        corpus_verde(raiz)
        verificador = raiz / "scripts/verificar-sobre-en-vuelo.py"
        verificador.parent.mkdir(parents=True, exist_ok=True)
        verificador.write_text("# verificador anterior\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(raiz), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(raiz), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(raiz), "-c", "user.name=baseline-test",
             "-c", "user.email=baseline-test@example.invalid", "commit", "-qm", "anterior"],
            check=True,
        )
        commit_anterior = subprocess.run(
            ["git", "-C", str(raiz), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        verificador.write_bytes(Path(__file__).read_bytes())
        subprocess.run(["git", "-C", str(raiz), "add", str(verificador)], check=True)
        subprocess.run(
            ["git", "-C", str(raiz), "-c", "user.name=baseline-test",
             "-c", "user.email=baseline-test@example.invalid", "commit", "-qm", "vigente"],
            check=True,
        )
        commit_vigente = subprocess.run(
            ["git", "-C", str(raiz), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        sha_vigente = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        corpus_baseline(raiz, sha_vigente, commit_vigente)
        ctx = Ctx(raiz)
        validar_baseline(ctx)
        malas = [f for f in ctx.filas if not f[0]]
        print(f"[{'OK   ' if not malas else 'FALLA'}] commit y sha256 ligados por git show")
        if malas:
            fallas.append(f"baseline ligado al commit vigente quedó rojo — {malas[:2]}")

        corpus_baseline(raiz, sha_vigente, commit_anterior)
        ctx = Ctx(raiz)
        validar_baseline(ctx)
        malas = [f for f in ctx.filas if not f[0]]
        mensaje = " ".join(f"{e}: {d}" for _, e, d in malas)
        ok = bool(malas) and "commit registrado contiene" in mensaje
        print(f"[{'OK   ' if ok else 'FALLA'}] commit con bytes ajenos queda rojo por git show")
        if not ok:
            fallas.append(f"baseline ligado a commit ajeno no falló por su motivo — {mensaje[:200]}")

    print()
    if fallas:
        print("RESULTADO: FALLA")
        for f in fallas:
            print(f"  - {f}")
        return 1
    print(f"RESULTADO: OK — control positivo sobre {len(MODOS) - 1} modos y "
          f"{len(MUTANTES) + len(casos_config) + 3} mutantes, cada uno rojo por su motivo")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ac", choices=list(MODOS), metavar="N",
                   help="modo de verificación: " + " ".join(MODOS))
    p.add_argument("--raiz", type=Path, default=REPO, help="raíz del árbol a verificar")
    p.add_argument("--sincronizar", action="store_true",
                   help="copia la fuente del contrato a las otras seis skills")
    p.add_argument("--validar-baseline", action="store_true",
                   help="valida el bloque `#### Baseline de vN` del plan")
    p.add_argument("--autotest", action="store_true",
                   help="control positivo sobre un corpus verde y después los mutantes")
    args = p.parse_args()
    elegidos = [bool(args.ac), args.sincronizar, args.validar_baseline, args.autotest]
    if sum(elegidos) != 1:
        p.error("elegí exactamente uno de --ac / --sincronizar / --validar-baseline / --autotest")
    if args.autotest:
        return autotest()
    if args.sincronizar:
        return sincronizar(args.raiz)
    if args.validar_baseline:
        ctx = Ctx(args.raiz)
        validar_baseline(ctx)
        print("=== --validar-baseline")
        for ok, etiqueta, detalle in ctx.filas:
            print(f"[{'OK   ' if ok else 'FALLA'}] {etiqueta}" + (f": {detalle}" if detalle else ""))
        fallas = [f for f in ctx.filas if not f[0]]
        print("ok" if not fallas else f"FALLA — {len(fallas)}/{len(ctx.filas)} chequeos")
        return 1 if fallas else 0
    return correr(args.ac, args.raiz)[0]


if __name__ == "__main__":
    sys.exit(main())
