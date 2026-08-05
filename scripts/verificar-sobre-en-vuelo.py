#!/usr/bin/env python3
"""Verifica el contrato del **sobre de corrida delegada en vuelo** (flujo `hilo-workers-en-vuelo`).

Un modo por fila de la tabla `## Verification` del plan — diecinueve en total, `--ac 1` … `--ac 16`
con sus variantes `1b`/`2b`/`3b` — más `--sincronizar` (genera las seis copias desde la fuente),
`--validar-baseline` (comprueba el bloque `#### Baseline de vN` del plan) y `--autotest` (control
positivo sobre un corpus verde temporal, y después un mutante por vez).

Tres reglas de diseño, heredadas del plan y de las tasks:

1. **Sin `grep`/`awk`/`sed`.** En esta máquina `grep` es ugrep 7.5.0 y difiere de BSD grep en regex
   con anclas internas: el mismo patrón devolvió 1 y 0. Todo el parseo es Python + stdlib.
   `subprocess` se usa solo para `git show` y para invocar las guardas del repo en `--ac 16`.
2. **Expectativas declarativas por conjunto exacto: sobra tanto como falta.** Un conteo no prueba un
   conjunto, y una coincidencia parcial no prueba una tupla fila→valor.
3. **El verificador se congela tras la task 2.** Ningún modo se amplía después: su `sha256` entra al
   baseline y ampliarlo obliga a versionar el contrato a `v2`.

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
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE_COMMIT = "5f3ff18"

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

# Las cuatro sedes que rechazan el estado persistido (AC-1) — son exactamente los cuatro archivos
# que edita la T11, de ahí que su conservación textual se compruebe en `--ac 1b` y la ausencia de
# reglas locales de retiro en `--ac 2`.
SEDES_RECHAZO = [
    "skills/co-explore/reference.md",
    "skills/co-explore/transporte-herdr.md",
    "skills/cross-review/transporte-herdr.md",
    "skills/cross-implement/transporte-herdr.md",
]
ADAPTADORES = [
    "skills/co-explore/transporte-herdr.md",
    "skills/cross-review/transporte-herdr.md",
    "skills/cross-implement/transporte-herdr.md",
]
READMES = [f"skills/{s}/README.md" for s in
           ("co-explore", "cross-review", "cross-implement", "bitbucket-code-review")]

CAMPOS_RAIZ = {"run_id", "skill", "mode", "owner", "parent", "children", "descendants_summary",
               "workers", "scope", "transport", "harvest_pending"}
CAMPOS_WORKER = {"name", "family", "write", "attempts"}
CAMPOS_INTENTO = {"attempt_id", "transport", "output", "process_ref", "wait_budget", "harvested"}
SUBESQUEMAS = {
    "wait_budget": {"deadline", "limite", "consumidos"},
    "process_ref": {"tipo", "referencia", "evidencia_de_frescura", "autoridad"},
}
# Las doce correspondencias del descriptor Herdr: campo del descriptor → dónde vive en el sobre.
MAPEO_HERDR = [
    ("run id", "run_id"),
    ("skill", "skill"),
    ("modo", "mode"),
    ("transporte", "attempts"),
    ("nombres de agentes", "workers"),
    ("outputs esperados", "output"),
    ("deadline", "wait_budget"),
    ("gate pendiente", "harvest_pending"),
    ("panes propios", "scope.herdr"),
    ("prompt esperado", "scope.herdr"),
    ("estados terminales", "scope.herdr"),
    ("proxima accion", "scope.herdr"),
]

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
    (("herdr",), "archivo+proceso"),
]
ENUM_PRECEDENCIA = ("cosechar", "clasificar_error", "informar_activo", "esperar_cleanup")
PRECEDENCIA = [
    (("d1",), "cosechar", ["proceso activo", "artefacto completo"]),
    (("d2",), "clasificar_error", ["proceso terminado"]),
    (("d3",), "informar_activo", ["deadline"]),
    (("d4",), "esperar_cleanup", ["cleanup"]),
]

# Los trece puntos de despacho del inventario del plan, por skill, con la señal que los identifica.
PUNTOS_DESPACHO = {
    "co-explore": {"fan-out dual": ["fan-out dual"], "debate": ["debate"]},
    "cross-review": {"revisor por ronda": ["revisor por ronda"]},
    "cross-implement": {"implementador inicial": ["implementador inicial"],
                        "fix loop": ["fix loop"]},
    "sdd-flow": {"exploración en analyze": ["analyze"],
                 "implementer por task": ["implementer por task"],
                 "reviewer por task": ["reviewer por task"],
                 "revisión final de diff": ["revision final"]},
    "sdd-orchestrator": {"fan-out por repo": ["fan-out por repo"]},
    "sdd-pr-feedback": {"implement delegado": ["implement delegado"]},
    "bitbucket-code-review": {"panel de revisores": ["panel de revisores"],
                              "validador adversarial": ["validador adversarial"]},
}

# Frases que, sobrevivientes en las cuatro sedes, dejarían una regla local de retiro compitiendo con
# las tres condiciones del contrato (T11 paso 4).
RETIRO_LOCAL_PROHIBIDO = ["la unica salida", "transferencia de ownership quedo fuera"]

# Nombres de campo del descriptor lo bastante discriminantes como para delatar una enumeración local
# sobreviviente. Los que la T11 autoriza conservar —panes propios, truncado, cierre— no están acá.
CAMPOS_DESCRIPTOR_LOCAL = ["run id", "nombres de agentes", "prompt esperado", "outputs esperados",
                           "estados terminales", "gate pendiente"]

# Qué tiene que seguir presente en cada archivo que toca la T11: lo propio de panes, que remitir el
# resto al contrato no puede llevarse puesto. La matriz está MEDIDA sobre 5f3ff18 y congelada acá a
# propósito —"truncado" hoy no está en dos de los tres adaptadores—: un predicado que se recalculara
# contra el árbol vigente se autoajustaría a cualquier borrado y no podría ponerse rojo.
CONSERVAR = {
    "skills/co-explore/transporte-herdr.md": ["panes propios", "cierre"],
    "skills/cross-review/transporte-herdr.md": ["panes propios", "cierre"],
    "skills/cross-implement/transporte-herdr.md": ["panes propios", "truncad", "cierre"],
    "skills/co-explore/reference.md": ["panes propios", "truncad", "cierre"],
}

# Dueños y vistas de la config del repo (AC-15). Mismo modelo que verificar-vistas-config.py.
DUENOS_CONFIG = [
    ("skills/sdd-flow/reference.md", r"Esquema de `\.specify/config\.yml`"),
    ("skills/sdd-orchestrator/reference.md", r"Esquema de `manifest\.yml`"),
    ("skills/cross-review/SKILL.md", r"Configuración"),
    ("skills/co-explore/SKILL.md", r"Configuración"),
    ("skills/cross-implement/SKILL.md", r"Configuración"),
    ("skills/sdd-flow/config-ejemplo.md", r"Ejemplo de `\.specify/config\.yml`"),
    ("skills/sdd-orchestrator/manifest-ejemplo.md", r"Ejemplo de `manifest\.yml`"),
]

GUARDAS = [
    ["python3", "scripts/verificar-vistas-config.py"],
    ["python3", "scripts/verificar-paridad-powershell.py", "--auditar-catalogo"],
    ["python3", "scripts/verificar-paridad-powershell.py", "--auditar-matrices"],
] + [["python3", "scripts/verificar-paridad-powershell.py", f"--autotest-{n}"] for n in
     ("extractor", "escaner", "normalizacion", "clasificador", "comparador", "precedencia",
      "catalogo")]

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
    """AC-1 — los conjuntos de campos, los sub-esquemas y las doce correspondencias Herdr."""
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
        fijos = [e for e in elems if e in ("repo", "worktree")]
        ext = [e for e in elems if "extension" in norm(e) and "transporte" in norm(e)]
        ok = len(fijos) == 2 and len(ext) == 1 and len(elems) == 3
        ctx.check(ok, "sub-esquema scope",
                  "" if ok else f"esperado {{repo, worktree, extensión opcional por transporte}}, "
                                f"leído {elems}")
    ctx.exigir(texto, "derivación", {
        "`transport` raíz derivado (valor común de los intentos vigentes, o `mixto`)":
            [["transport", "deriv", "mixto", "vigente"]],
    })
    s = ctx.seccion(CONTRATO_FUENTE, "Mapeo del descriptor Herdr")
    if s is None:
        return
    filas = [f for t in tablas(s) for f in t[1:]]
    if not filas:
        ctx.check(False, "mapeo Herdr", "la sección no tiene tabla")
        return
    usadas, faltan = set(), []
    for campo, destino in MAPEO_HERDR:
        cands = [j for j, f in enumerate(filas) if norm(campo) in norm(f[0])]
        if not cands:
            faltan.append(f"{campo} (sin fila)")
            continue
        usadas.update(cands)
        if not any(norm(destino) in norm(" ".join(filas[j][1:])) for j in cands):
            faltan.append(f"{campo} → esperado {destino}")
    ctx.check(not faltan, "mapeo Herdr: las doce correspondencias",
              "" if not faltan else "; ".join(faltan))
    huerfanas = [filas[j][0] for j in range(len(filas)) if j not in usadas]
    ctx.check(not huerfanas, "mapeo Herdr: sin filas sobrantes",
              "" if not huerfanas else f"filas sin campo del descriptor: {', '.join(huerfanas)}")


def ac_1b(ctx: Ctx) -> None:
    """AC-1 — no reconstruye estado semántico, cita sus cuatro sedes, y la frontera de la T8."""
    texto = ctx.contrato()
    ctx.exigir(texto, "contrato", {
        "declara que no reconstruye el estado semántico":
            [["no reconstruye", "estado semantico"], ["no", "reconstruir", "estado semantico"]],
        "sobre obligatorio e independiente de `cross_model.manifest.mode`":
            [["cross_model.manifest.mode", "independiente", "obligatorio"]],
    })
    if texto is not None:
        faltan = [s for s in SEDES_RECHAZO if norm(s) not in norm(texto)]
        ctx.check(not faltan, "contrato: cita las cuatro sedes que rechazan el estado persistido",
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
    """AC-6 — fuente por transporte, `process_ref`, y el chequeo positivo de los adaptadores."""
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
    for rel in ADAPTADORES:
        s = seccion(leer(ctx.raiz, rel) or "", "Entradas y salidas")
        if s is None:
            ctx.check(False, f"{rel} → «Entradas y salidas»", "no existe la sección")
            continue
        sn = norm(s)
        ok = CONTRATO in s and "mapeo" in sn
        ctx.check(ok, f"{rel}: remite a la tabla de mapeo del contrato",
                  "" if ok else f"la sección no cita `{CONTRATO}` con su mapeo")
        quedan = [c for c in CAMPOS_DESCRIPTOR_LOCAL if norm(c) in sn]
        ctx.check(len(quedan) <= 1, f"{rel}: sin enumeración local de los doce campos",
                  "" if len(quedan) <= 1 else f"siguen enumerados: {', '.join(quedan)}")
    s = ctx.seccion("skills/co-explore/reference.md", "El descriptor de corrida y su retiro")
    if s is not None:
        sn = norm(s)
        # Un solo chequeo con las tres señales: por separado, "es el sobre" y "vía de panes" ya
        # están hoy y darían verde sin que la redeclaración haya ocurrido.
        ok = CONTRATO in s and cubre(sn, [["sobre", "via de panes"]])
        ctx.check(ok, "co-explore/reference.md: el descriptor redeclarado como el sobre por la vía "
                      f"de panes, con remisión a `{CONTRATO}`",
                  "" if ok else f"cita el contrato: {CONTRATO in s} · dice sobre + vía de panes: "
                                f"{cubre(sn, [['sobre', 'via de panes']])}")
        quedan = [c for c in CAMPOS_DESCRIPTOR_LOCAL if norm(c) in sn]
        ctx.check(len(quedan) <= 1, "co-explore/reference.md: sin definición local de campos",
                  "" if len(quedan) <= 1 else f"siguen definidos: {', '.join(quedan)}")
    for rel, terminos in CONSERVAR.items():
        t = leer(ctx.raiz, rel)
        if t is None:
            ctx.check(False, f"{rel}: conserva lo propio de panes", "el archivo no existe")
            continue
        faltan = [p for p in terminos if p not in norm(t)]
        ctx.check(not faltan, f"{rel}: conserva {', '.join(terminos)}",
                  "" if not faltan else f"ya no menciona: {', '.join(faltan)}")


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
    """AC-12 — los trece puntos de despacho y el puntero normativo por skill."""
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


def _claves_config(texto: str, heading: str) -> set[str]:
    """Hojas punteadas del primer bloque ```yaml bajo `heading`. Mismo criterio que
    verificar-vistas-config.py, del que este modo es la contraparte de no regresión."""
    import yaml
    on = fence = False
    lineas: list[str] = []
    for linea in texto.splitlines():
        if not on:
            if re.match(rf"^#+ {heading}", linea):
                on = True
            continue
        if not fence:
            if re.match(r"^\s*```yaml", linea):
                fence = True
            continue
        if re.match(r"^\s*```", linea):
            break
        lineas.append(linea)
    if not lineas:
        return set()
    try:
        datos = yaml.safe_load("\n".join(lineas)) or {}
    except yaml.YAMLError:
        return set()
    salida: set[str] = set()

    def walk(nodo, prefijo=""):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                p = f"{prefijo}{k}"
                walk(v, p + ".") if isinstance(v, dict) else salida.add(p)

    walk(datos)
    return salida


def ac_15(ctx: Ctx) -> str:
    """AC-15 — ninguna clave de configuración nueva respecto de `5f3ff18`."""
    antes: set[str] = set()
    ahora: set[str] = set()
    for rel, heading in DUENOS_CONFIG:
        try:
            viejo = subprocess.run(["git", "show", f"{BASE_COMMIT}:{rel}"], cwd=REPO,
                                   capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError as e:
            ctx.check(False, f"git show {BASE_COMMIT}:{rel}", e.stderr.strip()[:120])
            continue
        nuevo = leer(ctx.raiz, rel)
        if nuevo is None:
            ctx.check(False, rel, "el archivo ya no existe en el árbol")
            continue
        antes |= {f"{rel}:{k}" for k in _claves_config(viejo, heading)}
        ahora |= {f"{rel}:{k}" for k in _claves_config(nuevo, heading)}
    if not antes:
        ctx.check(False, "claves de config en el commit base", "no se leyó ninguna — nada que "
                                                               "comparar, no un éxito")
        return "nuevas: ?"
    nuevas = sorted(ahora - antes)
    ctx.check(not nuevas, f"claves nuevas ({len(antes)} en {BASE_COMMIT}, {len(ahora)} ahora)",
              "" if not nuevas else ", ".join(nuevas))
    return f"nuevas: {len(nuevas)}"


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
    """`skills-ref validate` sobre el árbol contra un baseline generado en el momento desde
    `git show 5f3ff18:` — sin leer ningún snapshot en disco."""
    if shutil.which("skills-ref") is None:
        ctx.check(False, "skills-ref", "el binario no está instalado — el predicado no es medible")
        return 1
    antes: set[str] = set()
    ahora: set[str] = set()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        try:
            listado = subprocess.run(["git", "ls-tree", "-r", "--name-only", BASE_COMMIT, "skills/"],
                                     cwd=REPO, capture_output=True, text=True,
                                     check=True).stdout.split()
        except subprocess.CalledProcessError as e:
            ctx.check(False, f"git ls-tree {BASE_COMMIT}", e.stderr.strip()[:120])
            return 1
        for rel in listado:
            blob = subprocess.run(["git", "show", f"{BASE_COMMIT}:{rel}"], cwd=REPO,
                                  capture_output=True, check=True).stdout
            destino = base / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(blob)
        for skill in SKILLS:
            viejo = base / "skills" / skill
            if viejo.is_dir():
                r = subprocess.run(["skills-ref", "validate", str(viejo)], capture_output=True,
                                   text=True)
                antes |= _diagnosticos(r.stdout + r.stderr, skill)
            nuevo = ctx.raiz / "skills" / skill
            r = subprocess.run(["skills-ref", "validate", str(nuevo)], capture_output=True,
                               text=True)
            ahora |= _diagnosticos(r.stdout + r.stderr, skill)
    nuevos = sorted(ahora - antes)
    ctx.check(not nuevos, f"skills-ref: diagnósticos_actuales − diagnósticos_{BASE_COMMIT} = ∅ "
                          f"({len(antes)} en base, {len(ahora)} ahora)",
              "" if not nuevos else " | ".join(nuevos[:4]))
    return len(nuevos)


def ac_16(ctx: Ctx) -> str:
    """AC-16 — las guardas del repo con `rc` acumulado y `skills-ref` sin diagnósticos nuevos."""
    acumulado = 0
    for cmd in GUARDAS:
        r = subprocess.run(cmd, cwd=ctx.raiz, capture_output=True, text=True)
        acumulado += r.returncode
        ctx.check(r.returncode == 0, " ".join(cmd[1:]),
                  "" if r.returncode == 0 else f"rc={r.returncode}")
    nuevos = _validar_skills_ref(ctx)
    return f"rc={acumulado} · nuevos: {nuevos}"


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


def validar_baseline(ctx: Ctx) -> None:
    plan = ctx.texto(".plans/hilo-workers-en-vuelo/plan.md")
    if plan is None:
        return
    tabla = seccion(plan, "Verification")
    ids_tabla: list[str] = []
    for t in tablas(tabla or ""):
        for fila in t[1:]:
            m = re.fullmatch(r"V\d+", fila[0].strip().strip("`"))
            if m:
                ids_tabla.append(fila[0].strip().strip("`"))
        if ids_tabla:
            break
    ctx.check(len(ids_tabla) == 19, "la tabla de `## Verification` tiene diecinueve filas",
              "" if len(ids_tabla) == 19 else f"leídas {len(ids_tabla)}")
    versiones = sorted(int(m.group(1)) for m in re.finditer(r"^#+\s*Baseline de v(\d+)", plan,
                                                            re.MULTILINE))
    if not versiones:
        ctx.check(False, "bloque `#### Baseline de vN`", "no existe en el plan")
        return
    bloque = seccion(plan, f"Baseline de v{versiones[-1]}")
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
    sha = hashlib.sha256((REPO / "scripts/verificar-sobre-en-vuelo.py").read_bytes()).hexdigest()
    problemas = []
    for fila in filas:
        campos = " | ".join(fila)
        ident = fila[0].strip()
        if BASE_COMMIT not in campos:
            problemas.append(f"{ident}: sin commit {BASE_COMMIT}")
        if sha not in campos.replace(" ", ""):
            problemas.append(f"{ident}: sha256 del verificador no coincide")
        if not any(_ISO.match(c.strip()) for c in fila):
            problemas.append(f"{ident}: sin timestamp ISO-8601")
        if not any(c.strip() in ESTADOS_BASELINE for c in fila):
            problemas.append(f"{ident}: sin estado de {sorted(ESTADOS_BASELINE)}")
    ctx.check(not problemas, "commit, sha256, timestamp y estado por registro",
              "" if not problemas else "; ".join(problemas[:5]))
    for objetivo in ("V18", "V19"):
        fila = next((f for f in filas if f[0].strip().strip("`") == objetivo), None)
        if fila is None:
            ctx.check(False, f"{objetivo}: adjudicación escrita", "no hay registro")
            continue
        resto = [c for c in fila[1:] if c.strip() and not _ISO.match(c.strip())
                 and c.strip() not in ESTADOS_BASELINE and BASE_COMMIT not in c and sha not in c]
        ctx.check(bool(resto), f"{objetivo}: adjudicación escrita",
                  "" if resto else "el registro no la trae")


# ---------------------------------------------------------------------------------------------
# Ejecución de un modo.
# ---------------------------------------------------------------------------------------------

MODOS = {
    "1": ("AC-1 · campos, sub-esquemas y mapeo Herdr", ac_1),
    "1b": ("AC-1 · no-estado-semántico, sedes citadas y frontera", ac_1b),
    "2": ("AC-2 · transiciones, outcomes y orden del orquestador", ac_2),
    "2b": ("AC-2 · retiro, escritor único, nacimiento y adopción", ac_2b),
    "3": ("AC-3 · agregación multi-worker", ac_3),
    "3b": ("AC-3 · el ancestro no cosecha ni retira", ac_3b),
    "4": ("AC-4 · archivo, identidad y barrido por topología", ac_4),
    "5": ("AC-5 · cierre del turno, sonda y wait_budget", ac_5),
    "6": ("AC-6 · fuente por transporte, process_ref y adaptadores", ac_6),
    "7": ("AC-7 · precedencia ante discrepancia", ac_7),
    "8": ("AC-8 · el límite declarado", ac_8),
    "9": ("AC-9 · el sidecar del dato nuevo", ac_9),
    "10": ("AC-10 · relanzamiento seguro", ac_10),
    "11": ("AC-11 · la cancelación como terminal propio", ac_11),
    "12": ("AC-12 · los trece puntos y los siete punteros", ac_12),
    "13": ("AC-13 · siete copias idénticas, trigger y README", ac_13),
    "14": ("AC-14 · la tercera excepción y su cita", ac_14),
    "15": ("AC-15 · ninguna clave de configuración nueva", ac_15),
    "16": ("AC-16 · las guardas del repo sin regresión", ac_16),
}
FILAS = {"1": "V1", "1b": "V2", "2": "V3", "2b": "V4", "3": "V5", "3b": "V6", "4": "V7",
         "5": "V8", "6": "V9", "7": "V10", "8": "V11", "9": "V12", "10": "V13", "11": "V14",
         "12": "V15", "13": "V16", "14": "V17", "15": "V18", "16": "V19"}


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

El sobre son metadatos operativos y **no reconstruye el estado semántico** de la corrida. Las cuatro
sedes que rechazan el estado persistido —`skills/co-explore/reference.md`,
`skills/co-explore/transporte-herdr.md`, `skills/cross-review/transporte-herdr.md` y
`skills/cross-implement/transporte-herdr.md`— siguen vigentes.

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
| `scope` | `scope = {repo, worktree, extensión opcional por transporte}` |
| `transport` | derivado |
| `harvest_pending` | marca explícita de cosecha pendiente |

`transport` raíz es el único campo **derivado**: el valor común de los intentos vigentes, o `mixto`.

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

### Mapeo del descriptor Herdr

| campo del descriptor | dónde vive |
|---|---|
| run ID · skill · modo | `run_id` · `skill` · `mode` |
| transporte | `workers[].attempts[].transport` |
| nombres de agentes | `workers[].name` |
| outputs esperados · deadline | `workers[].attempts[].output` · `workers[].attempts[].wait_budget` |
| gate pendiente | `harvest_pending` |
| panes propios · prompt esperado · estados terminales · próxima acción | `scope.herdr` |

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
| `herdr` | `archivo+proceso`, con la autoridad en el archivo |

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

_ADAPTADOR = """# {skill} — transporte por panes (adaptador)

## Entradas y salidas

Qué campos del sobre escribe esta skill: la correspondencia completa está en el **mapeo** del
contrato (`corridas-en-vuelo.md` → "Mapeo del descriptor Herdr"), y no se duplica acá.

**Panes propios**, truncado previo al dispatch y autorización de cierre siguen siendo propios de
panes. {rechazo}
"""

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
    """Escribe un árbol mínimo pero completo que satisface los diecisiete modos de parser."""
    puntos = {
        "co-explore": ["- fan-out dual (`explore`/`counter-plan`/`investigate`)",
                       "- worker por ronda del modo `debate`"],
        "cross-review": ["- revisor por ronda, con resume"],
        "cross-implement": ["- implementador inicial", "- rondas del fix loop"],
        "sdd-flow": ["- subagente de exploración en `analyze`", "- implementer por task",
                     "- reviewer por task", "- reviewer de la revisión final de diff"],
        "sdd-orchestrator": ["- fan-out por repo (Fase 2.3)"],
        "sdd-pr-feedback": ["- implement delegado sobre la Vía B"],
        "bitbucket-code-review": ["- panel de revisores externos",
                                  "- validador adversarial por hallazgo"],
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
        (d / "SKILL.md").write_text(_SKILL_TPL.format(
            skill=skill, puntos="\n".join(puntos[skill]), extra=extras.get(skill, "")),
            encoding="utf-8")
    (raiz / CONTRATO_FUENTE).write_text(CONTRATO_VERDE, encoding="utf-8")
    sincronizar_silencioso(raiz)
    for rel in READMES:
        (raiz / rel).write_text(_README_TPL.format(skill=Path(rel).parent.name), encoding="utf-8")
    for rel in ADAPTADORES:
        (raiz / rel).write_text(_ADAPTADOR.format(skill=Path(rel).parent.name, rechazo=_RECHAZO),
                                encoding="utf-8")
    (raiz / "skills/co-explore/reference.md").write_text(
        "# co-explore — Referencia\n\n### El descriptor de corrida y su retiro\n\n"
        "El descriptor **es** el sobre de corrida en vuelo por la **vía de panes**: campos, "
        "transiciones y retiro viven en `corridas-en-vuelo.md`. Acá quedan los **panes propios**, el "
        "truncado y la autorización de cierre.\n\n" + _RECHAZO, encoding="utf-8")
    (raiz / "skills/cross-review/reference.md").write_text(
        "# cross-review — Referencia\n\n## Manifest de corrida\n\nEl manifest registra la corrida "
        "terminada; su hermano activo es el sobre de `corridas-en-vuelo.md`, y **se retira** cuando "
        "el manifest se escribe.\n", encoding="utf-8")
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


BASELINE_TPL = """# Plan

## Verification

| ID | Requisito | Comando | Esperado |
|---|---|---|---|
{filas}

### v1

#### Baseline de v1

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
{registros}
"""


def corpus_baseline(raiz: Path, sha: str) -> None:
    filas = "\n".join(f"| {FILAS[m]} | AC-{m} | `--ac {m}` | ok |" for m in MODOS)
    registros = "\n".join(
        f"| {FILAS[m]} | {BASE_COMMIT} | {sha} | 2026-08-05T10:00:00-05:00 | "
        f"{'GREEN_ALREADY' if m in ('15', '16') else 'RED'} | "
        f"{'no regresión: pasa por construcción' if m in ('15', '16') else '—'} |"
        for m in MODOS)
    destino = raiz / ".plans/hilo-workers-en-vuelo/plan.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(BASELINE_TPL.format(filas=filas, registros=registros), encoding="utf-8")


# Mutantes: (nombre, archivo relativo, viejo, nuevo, modo que debe fallar, señal en el mensaje).
MUTANTES = [
    ("clave faltante", CONTRATO_FUENTE, "| `owner` | conductor propietario |\n", "", "1", "owner"),
    ("clave sobrante", CONTRATO_FUENTE, "| `owner` | conductor propietario |",
     "| `owner` | conductor propietario |\n| `estado_semantico` | de más |", "1",
     "estado_semantico"),
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
    # Los dos siguientes cubren chequeos que ya estaban verdes en el árbol real —conservación de lo
    # propio de panes y la cláusula del README—: sin un mutante propio, ninguno se probó en rojo.
    ("conservación de panes propios borrada", "skills/cross-implement/transporte-herdr.md",
     "**Panes propios**, truncado", "El truncado", "6", "panes propios"),
    ("cláusula de independencia del README borrada", "skills/cross-review/README.md",
     "El sobre **no** lo apaga `cross_model.manifest.mode`: es obligatorio e independiente de esa "
     "clave.", "Se apaga con `cross_model.manifest.mode`.", "13", "manifest.mode"),
    ("cláusula de rechazo del estado persistido borrada", "skills/co-explore/transporte-herdr.md",
     "no hay máquina de estados persistente", "hay estado", "1b", "rechazo del estado persistido"),
    ("regla local de retiro reintroducida", "skills/cross-review/transporte-herdr.md",
     "autorización de cierre siguen siendo", "autorización de cierre y la única salida siguen "
     "siendo", "2", "la unica salida"),
]


def autotest() -> int:
    print("=== Control positivo: corpus verde completo")
    fallas = []
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
        validar_baseline(ctx)
        malas = [f for f in ctx.filas if not f[0]]
        print(f"[{'OK   ' if not malas else 'FALLA'}] --validar-baseline: "
              f"{'ok' if not malas else malas}")
        if malas:
            fallas.append(f"corpus verde: --validar-baseline → {malas}")
    print("(--ac 15 y --ac 16 quedan fuera del corpus: no leen artefactos, sino git y las guardas "
          "del repo; su control positivo es el árbol real, donde V18 y V19 están verdes.)")
    if fallas:
        print("\nRESULTADO: FALLA — el control positivo no cierra; los mutantes no probarían nada")
        for f in fallas:
            print(f"  - {f}")
        return 1

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
        validar_baseline(ctx)
        malas = [f for f in ctx.filas if not f[0]]
        mensaje = " ".join(f"{e}: {d}" for _, e, d in malas)
        ok = bool(malas) and "sha256" in mensaje
        print(f"[{'OK   ' if ok else 'FALLA'}] sha256 del verificador desalineado → "
              f"--validar-baseline: {len(malas)} en rojo")
        if not ok:
            fallas.append(f"baseline con sha ajeno: no falló por su motivo — {mensaje[:200]}")

    print()
    if fallas:
        print("RESULTADO: FALLA")
        for f in fallas:
            print(f"  - {f}")
        return 1
    print(f"RESULTADO: OK — control positivo sobre {len(MODOS) - 2} modos y "
          f"{len(MUTANTES) + 1} mutantes, cada uno rojo por su motivo")
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
