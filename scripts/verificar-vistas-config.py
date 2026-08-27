#!/usr/bin/env python3
"""Verifica que las vistas copiables de config sigan siendo fieles a sus dueños.

Este repo documenta la config de las skills SDD con un modelo dueño → vista: cada skill es
dueña del enum, la descripción y el valor de sus propias claves; `sdd-flow/config-ejemplo.md`
y `sdd-orchestrator/manifest-ejemplo.md` son vistas ensambladas de esos dueños, pensadas para
copiar. Ante discrepancia manda el dueño — pero nada impedía que una vista se desincronizara en
silencio (alguien cambia un default en un dueño y la vista queda mintiendo). Este script cierra
esa brecha con seis chequeos: conjunto de claves, tokens de enum, valores, marcas
`[def]`/`[ej]`/`[obl]`, comillas en `on`/`off` y colisión de claves de primer nivel al normalizar
guion medio a guion bajo.

Uso: python3 scripts/verificar-vistas-config.py
Exit 0 si los seis chequeos pasan; 1 si alguno falla (detalle impreso por chequeo).

Requiere python3 + PyYAML. Sin otras dependencias.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------------------------
# Rutas y headings de los dueños y las vistas.
# ---------------------------------------------------------------------------------------------

SDD_FLOW_REF = REPO / "skills/sdd-flow/reference.md"
SDD_FLOW_ESQUEMA = r"Esquema de `\.specify/config\.yml`"

SDD_FLOW_SKILL = REPO / "skills/sdd-flow/SKILL.md"
SDD_FLOW_SKILL_ESQUEMA = r"Adaptación al proyecto"

CROSS_REVIEW_SKILL = REPO / "skills/cross-review/SKILL.md"
CO_EXPLORE_SKILL = REPO / "skills/co-explore/SKILL.md"
CROSS_IMPLEMENT_SKILL = REPO / "skills/cross-implement/SKILL.md"
CONFIG_HEADING = r"Configuración"

CONFIG_EJEMPLO = REPO / "skills/sdd-flow/config-ejemplo.md"
CONFIG_EJEMPLO_HEADING = r"Ejemplo de `\.specify/config\.yml`"

SDD_ORCH_REF = REPO / "skills/sdd-orchestrator/reference.md"
SDD_ORCH_ESQUEMA = r"Esquema de `manifest\.yml`"

MANIFEST_EJEMPLO = REPO / "skills/sdd-orchestrator/manifest-ejemplo.md"
MANIFEST_EJEMPLO_HEADING = r"Ejemplo de `manifest\.yml`"

# La quinta sede (AC-1 de sede-config-vault): dueña de `knowledge-vault.path_vault`, la única
# clave del config con guion medio.
KNOWLEDGE_VAULT_REF = REPO / "skills/knowledge-vault/reference.md"
KNOWLEDGE_VAULT_REF_HEADING = r"La capa de configuración"

KNOWLEDGE_VAULT_SKILL = REPO / "skills/knowledge-vault/SKILL.md"
KNOWLEDGE_VAULT_SKILL_HEADING = r"El primer uso en un proyecto"

# Las 5 claves de ESTADO DE CORRIDA del esquema de manifest.yml (no son config, no viven en
# manifest-ejemplo.md).
CLAVES_ESTADO_CORRIDA = {"id", "created_at", "master_spec", "repos", "orchestration_tasks"}

# El registro de sedes activas de sede-config-vault (AC-1): (ruta, ancla, rol, extraccion),
# rol ∈ {"dueno", "consumidora", "vista"} · extraccion ∈ {"bloque", "prosa", "linea"}.
SEDES_CONFIG = [
    (SDD_FLOW_REF, SDD_FLOW_ESQUEMA, "dueno", "bloque"),
    (SDD_FLOW_SKILL, SDD_FLOW_SKILL_ESQUEMA, "consumidora", "bloque"),
    (CONFIG_EJEMPLO, CONFIG_EJEMPLO_HEADING, "vista", "linea"),
    (KNOWLEDGE_VAULT_REF, KNOWLEDGE_VAULT_REF_HEADING, "dueno", "bloque"),
    (KNOWLEDGE_VAULT_SKILL, KNOWLEDGE_VAULT_SKILL_HEADING, "consumidora", "prosa"),
]

# DUENOS_CONFIG se deriva de SEDES_CONFIG para la parte que le compete (los dueños del vault, que
# antes de este flujo no estaban) y conserva los tres dueños ajenos al vault que ya tenía: no son
# parte del registro de sedes de AC-1 (que es específico de la colisión vault_archive/knowledge-
# vault), así que desincronizarían la cardinalidad exacta de ese registro si se sumaran ahí.
DUENOS_CONFIG = [(ruta, ancla) for ruta, ancla, rol, _ in SEDES_CONFIG if rol == "dueno"] + [
    (CROSS_REVIEW_SKILL, CONFIG_HEADING),
    (CO_EXPLORE_SKILL, CONFIG_HEADING),
    (CROSS_IMPLEMENT_SKILL, CONFIG_HEADING),
]

# ---------------------------------------------------------------------------------------------
# Primitivas portadas de .plans/init-config-ejemplo/guardas/comun.sh (yamlblock/claves/enums).
# Ese archivo describe por qué el parser vive en python3+PyYAML y no en POSIX puro: el
# predicado es sobre la ESTRUCTURA de un bloque YAML y los tokens de sus comentarios, no sobre
# prosa. Están probadas por 21 mutantes en esa rama; se portan tal cual, sin reinventarlas.
# ---------------------------------------------------------------------------------------------

SEPS = ("—", "→", ". ", "; ", " - ")
_LINEA_CLAVE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_-]*):(.*)$")
_MARCA_RE = re.compile(r"\[(def|ej|obl)\]")


class FuenteIlegible(Exception):
    """La sede no produjo un bloque YAML legible. `causa` nombra por qué, entre
    "archivo ausente" · "heading ausente" · "bloque vacío"."""

    def __init__(self, ruta: Path, causa: str):
        self.ruta = ruta
        self.causa = causa
        super().__init__(f"{ruta}: {causa}")


def bloque_yaml(ruta: Path, heading: str) -> str:
    """Primer fence ```yaml bajo el heading que matchea `heading` (regex). Puerto de
    yamlblock() de comun.sh. Levanta `FuenteIlegible` en vez de devolver cadena vacía: el
    archivo ausente, el heading ausente y el bloque vacío son fallas silenciosas si se
    confunden con "nada que auditar"."""
    if not ruta.is_file():
        raise FuenteIlegible(ruta, "archivo ausente")
    on = fence = False
    lineas: list[str] = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
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
    if not on:
        raise FuenteIlegible(ruta, "heading ausente")
    texto = "\n".join(lineas)
    if not texto.strip():
        raise FuenteIlegible(ruta, "bloque vacío")
    return texto


def _walk_claves(nodo, prefijo=""):
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            p = f"{prefijo}{k}"
            if isinstance(v, dict):
                yield from _walk_claves(v, p + ".")
            else:
                yield p


def _cargar_yaml(ruta: Path, heading: str):
    texto = bloque_yaml(ruta, heading)
    try:
        return yaml.safe_load(texto) or {}
    except yaml.YAMLError as e:
        print(f"YAML inválido en {ruta} → {heading!r}: {e}", file=sys.stderr)
        return None


def claves(ruta: Path, heading: str) -> set[str]:
    """Una clave hoja punteada por cada hoja del bloque. Puerto de claves() de comun.sh."""
    datos = _cargar_yaml(ruta, heading)
    if datos is None:
        return set()
    return set(_walk_claves(datos))


def valores(ruta: Path, heading: str) -> dict[str, str]:
    """Como claves(), pero retiene el valor de cada hoja. Canonicalizado con json.dumps para
    que el estilo flow (`{a: 1}`) o block de YAML no genere falsos positivos de comparación."""
    datos = _cargar_yaml(ruta, heading)
    if datos is None:
        return {}
    salida: dict[str, str] = {}

    def walk(nodo, prefijo=""):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                p = f"{prefijo}{k}"
                if isinstance(v, dict):
                    walk(v, p + ".")
                else:
                    # default=str: alcanza a `created_at` (estado de corrida, no config), que
                    # PyYAML resuelve a datetime y json no serializa por su cuenta.
                    salida[p] = json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)

    walk(datos)
    return salida


def _lineas_con_ruta(texto: str):
    """Recorre las líneas de un bloque YAML calculando, para cada línea que declara una clave,
    su ruta punteada por indentación (mismo criterio que claves()/valores(): dos claves con el
    mismo nombre de hoja a distinta profundidad no colapsan). Yield (ruta, resto-tras-':')."""
    pila: list[tuple[int, str]] = []
    for linea in texto.split("\n"):
        m = _LINEA_CLAVE.match(linea)
        if not m:
            continue
        indent, clave, resto = len(m.group(1)), m.group(2), m.group(3)
        while pila and pila[-1][0] >= indent:
            pila.pop()
        ruta = ".".join([k for _, k in pila] + [clave])
        pila.append((indent, clave))
        yield ruta, resto


def _recortar_cabecera(comentario: str) -> str:
    """Dado el texto de un comentario, recorta un prefijo explicativo ("explicación: tok1 |
    ...") y corta la cola en el primer separador de nivel 0 (fuera de paréntesis) de SEPS.
    Puerto de la normalización de enums() en comun.sh."""
    bpos = [i for i in (comentario.find("("), comentario.find("|")) if i != -1]
    b = min(bpos) if bpos else len(comentario)
    j = comentario[:b].rfind(": ")
    if j != -1:
        comentario = comentario[j + 2:]
    profundidad, corte, i = 0, len(comentario), 0
    while i < len(comentario):
        c = comentario[i]
        if c == "(":
            profundidad += 1
        elif c == ")":
            profundidad = max(0, profundidad - 1)
        elif profundidad == 0 and comentario.startswith(SEPS, i):
            corte = i
            break
        i += 1
    return comentario[:corte]


def enums(ruta: Path, heading: str) -> dict[str, tuple[str, ...]]:
    """"clave puntuada" -> tupla ordenada de tokens, por cada clave cuyo comentario declara un
    enum (con '|'). Puerto de enums() de comun.sh."""
    texto = bloque_yaml(ruta, heading)
    salida: dict[str, tuple[str, ...]] = {}
    for ruta_clave, resto in _lineas_con_ruta(texto):
        cm = re.search(r"#\s*(.+)$", resto)
        if not cm:
            continue
        cabecera = _recortar_cabecera(cm.group(1))
        if "|" not in cabecera:
            continue
        toks = []
        for t in cabecera.split("|"):
            t = re.sub(r"\([^)]*\)", "", t).strip().strip("`").strip("'\"")
            if t:
                toks.append(t)
        if toks:
            salida[ruta_clave] = tuple(sorted(set(toks)))
    return salida


def marcas(ruta: Path, heading: str, hojas: set[str]) -> dict[str, list[str]]:
    """"clave hoja" -> lista de marcas [def]/[ej]/[obl] encontradas en su PROPIA línea. Solo
    mira líneas cuya ruta está en `hojas`: una línea de padre marcada no puede compensar a una
    hoja sin marca, porque nunca se le atribuye a esa hoja."""
    texto = bloque_yaml(ruta, heading)
    salida: dict[str, list[str]] = {}
    for ruta_clave, resto in _lineas_con_ruta(texto):
        if ruta_clave not in hojas:
            continue
        cm = re.search(r"#(.*)$", resto)
        comentario = cm.group(1) if cm else ""
        salida[ruta_clave] = _MARCA_RE.findall(comentario)
    return salida


# ---------------------------------------------------------------------------------------------
# Checks 1-2: conjunto de claves y enums.
# ---------------------------------------------------------------------------------------------


def _union_claves(fuentes) -> set[str]:
    resultado: set[str] = set()
    for ruta, heading in fuentes:
        resultado |= claves(ruta, heading)
    return resultado


def _comparar_conjuntos(nombre: str, esperado: set[str], real: set[str], etq_esp: str, etq_real: str):
    if not esperado and not real:
        return False, "nada que comparar (ambos conjuntos están vacíos)"
    if not real:
        return False, f"{etq_real} no declara ninguna clave — nada que comparar, no un éxito"
    solo_esp = sorted(esperado - real)
    solo_real = sorted(real - esperado)
    if not solo_esp and not solo_real:
        return True, f"{len(real)} claves, {etq_real} == {etq_esp}"
    detalle = []
    if solo_esp:
        detalle.append(f"solo en {etq_esp}: {', '.join(solo_esp)}")
    if solo_real:
        detalle.append(f"solo en {etq_real}: {', '.join(solo_real)}")
    return False, " | ".join(detalle)


def check1_config():
    duenos = _union_claves(DUENOS_CONFIG)
    vista = claves(CONFIG_EJEMPLO, CONFIG_EJEMPLO_HEADING)
    return _comparar_conjuntos(
        "config-ejemplo.md", duenos, vista, f"unión de los {len(DUENOS_CONFIG)} dueños", "la vista"
    )


def check1_manifest():
    esquema = claves(SDD_ORCH_REF, SDD_ORCH_ESQUEMA)
    if not esquema:
        return False, "no se pudo leer el esquema de manifest.yml — nada que comparar"
    config_keys = esquema - CLAVES_ESTADO_CORRIDA
    vista = claves(MANIFEST_EJEMPLO, MANIFEST_EJEMPLO_HEADING)
    return _comparar_conjuntos(
        "manifest-ejemplo.md", config_keys, vista,
        f"esquema de manifest.yml ({len(esquema)} hojas) menos las "
        f"{len(esquema & CLAVES_ESTADO_CORRIDA)} de estado de corrida", "la vista",
    )


def _union_enums(fuentes) -> dict[str, tuple[str, ...]]:
    resultado: dict[str, tuple[str, ...]] = {}
    for ruta, heading in fuentes:
        resultado.update(enums(ruta, heading))
    return resultado


def _comparar_enums(enums_duenos: dict, enums_vista: dict, *, exigir_cobertura: bool):
    """exigir_cobertura=True (config-ejemplo.md): toda clave con enum en el dueño debe
    reaparecer con el MISMO enum en la vista (comparación por unión). exigir_cobertura=False
    (manifest-ejemplo.md): la vista usa un subconjunto por diseño, se compara solo la
    intersección — pero un enum de la vista sin ningún dueño que lo respalde sigue siendo un
    fallo en ambos casos."""
    claves_d, claves_v = set(enums_duenos), set(enums_vista)
    huerfanas = sorted(claves_v - claves_d)
    comunes = sorted(claves_d & claves_v)
    faltan = sorted(claves_d - claves_v) if exigir_cobertura else []

    if not comunes and not huerfanas and not faltan:
        return False, "nada que comparar (ningún enum declarado en ninguno de los dos lados)"
    if not comunes and not huerfanas:
        return False, "la vista no declara ningún enum — nada que comparar, no un éxito"

    difs = [k for k in comunes if enums_duenos[k] != enums_vista[k]]
    problemas = []
    for k in difs[:5]:
        problemas.append(f"{k}: dueño={list(enums_duenos[k])} vista={list(enums_vista[k])}")
    if huerfanas:
        problemas.append(f"vista declara enum sin dueño que lo respalde: {', '.join(huerfanas)}")
    if faltan:
        problemas.append(f"dueño declara enum que la vista no repite: {', '.join(faltan)}")
    if problemas:
        return False, " | ".join(problemas)
    return True, f"{len(comunes)} claves con enum comparadas, 0 discrepancias"


def check2_config():
    duenos = _union_enums(DUENOS_CONFIG)
    vista = enums(CONFIG_EJEMPLO, CONFIG_EJEMPLO_HEADING)
    return _comparar_enums(duenos, vista, exigir_cobertura=True)


def check2_manifest():
    # Mismas fuentes que G2o de vista.sh: el propio esquema de manifest.yml (dueño de
    # branch_prefix/execution_mode/implement_mode) + los dueños hermanos, pero de sdd-flow solo
    # el subconjunto cross_model.* — su implement_mode incluye "ask", que no aplica a nivel
    # orquestador, y colaría un token que ningún manifest real declara.
    duenos = enums(SDD_ORCH_REF, SDD_ORCH_ESQUEMA)
    duenos.update(enums(CROSS_REVIEW_SKILL, CONFIG_HEADING))
    duenos.update(enums(CO_EXPLORE_SKILL, CONFIG_HEADING))
    for k, v in enums(SDD_FLOW_REF, SDD_FLOW_ESQUEMA).items():
        if k.startswith("cross_model."):
            duenos[k] = v
    vista = enums(MANIFEST_EJEMPLO, MANIFEST_EJEMPLO_HEADING)
    return _comparar_enums(duenos, vista, exigir_cobertura=False)


# ---------------------------------------------------------------------------------------------
# Check 3 (nuevo): valores.
# ---------------------------------------------------------------------------------------------


def _union_valores(fuentes):
    combinado: dict[str, str] = {}
    conflictos: list[str] = []
    for ruta, heading in fuentes:
        for k, v in valores(ruta, heading).items():
            if k in combinado and combinado[k] != v:
                conflictos.append(f"{k}: {combinado[k]} (otro dueño) vs {v} ({ruta.name})")
            else:
                combinado[k] = v
    return combinado, conflictos


def _comparar_valores(valores_duenos: dict, valores_vista: dict):
    claves_d, claves_v = set(valores_duenos), set(valores_vista)
    comunes = sorted(claves_d & claves_v)
    if not comunes:
        return False, "nada que comparar (0 claves en la intersección)"
    difs = [(k, valores_duenos[k], valores_vista[k]) for k in comunes if valores_duenos[k] != valores_vista[k]]
    notas = []
    solo_d, solo_v = sorted(claves_d - claves_v), sorted(claves_v - claves_d)
    if solo_d:
        notas.append(f"solo en dueño (sin comparar): {', '.join(solo_d)}")
    if solo_v:
        notas.append(f"solo en vista (sin comparar): {', '.join(solo_v)}")
    if difs:
        detalle = "; ".join(f"{k}: dueño={d} vista={v}" for k, d, v in difs[:5])
        msg = f"{len(difs)} discrepancias de {len(comunes)} claves comparadas — {detalle}"
        if notas:
            msg += " | " + " | ".join(notas)
        return False, msg
    msg = f"{len(comunes)} claves comparadas, 0 discrepancias"
    if notas:
        msg += " | " + " | ".join(notas)
    return True, msg


def check3_config():
    duenos, conflictos = _union_valores(DUENOS_CONFIG)
    if conflictos:
        return False, f"dueños en conflicto entre sí (ambigüedad, no comparable): {'; '.join(conflictos[:3])}"
    vista = valores(CONFIG_EJEMPLO, CONFIG_EJEMPLO_HEADING)
    return _comparar_valores(duenos, vista)


def check3_manifest():
    # A diferencia de check3_config, el valor de referencia NO es la unión de los 4 dueños
    # nombrados en el modelo: cross-review/SKILL.md documenta su propio default de
    # `cross_review.artifacts` como [spec, plan, tasks] pero anota explícitamente, en el mismo
    # comentario, que sdd-orchestrator usa [master-spec, reparto] — un default distinto por
    # contexto, ya documentado, no una divergencia. El esquema de manifest.yml en
    # sdd-orchestrator/reference.md ya trae ese valor de contexto para las 11 claves (es la
    # misma fuente que sostiene el chequeo de claves G1o), así que es la única fuente de
    # verdad de VALOR para esta vista — evita mezclar un default genérico con el override de
    # contexto y producir un falso rojo sobre una vista que hoy es correcta.
    duenos_todos = valores(SDD_ORCH_REF, SDD_ORCH_ESQUEMA)
    duenos = {k: v for k, v in duenos_todos.items() if k not in CLAVES_ESTADO_CORRIDA}
    if not duenos:
        return False, "no se pudo leer el esquema de manifest.yml — nada que comparar"
    vista = valores(MANIFEST_EJEMPLO, MANIFEST_EJEMPLO_HEADING)
    return _comparar_valores(duenos, vista)


# ---------------------------------------------------------------------------------------------
# Check 4 (nuevo): marcas [def]/[ej]/[obl], una y solo una por HOJA (no por línea).
# ---------------------------------------------------------------------------------------------


def check4_marcas():
    total_hojas = 0
    problemas = []
    for ruta, heading, etiqueta in [
        (CONFIG_EJEMPLO, CONFIG_EJEMPLO_HEADING, "config-ejemplo.md"),
        (MANIFEST_EJEMPLO, MANIFEST_EJEMPLO_HEADING, "manifest-ejemplo.md"),
    ]:
        hojas = claves(ruta, heading)
        if not hojas:
            problemas.append(f"{etiqueta}: sin hojas — nada que verificar")
            continue
        por_hoja = marcas(ruta, heading, hojas)
        total_hojas += len(hojas)
        for h in sorted(hojas - set(por_hoja)):
            problemas.append(f"{etiqueta}:{h}: no se encontró su línea (0 marcas)")
        for h in sorted(por_hoja):
            n = len(por_hoja[h])
            if n != 1:
                problemas.append(f"{etiqueta}:{h}: {n} marcas {por_hoja[h]}")
    if total_hojas == 0:
        return False, "nada que comparar (0 hojas totales entre las dos vistas)"
    if problemas:
        return False, f"{total_hojas} hojas evaluadas — " + " | ".join(problemas[:8])
    return True, f"{total_hojas} hojas (config-ejemplo.md + manifest-ejemplo.md), cada una con exactamente 1 marca"


# ---------------------------------------------------------------------------------------------
# Check 5: comillas. Ningún .md bajo skills/ escribe on/off sin comillas, como valor o como
# token de un enum en un comentario. Barrido recursivo sobre TODO .md, no sobre nombres de
# archivo hardcodeados, y sobre CUALQUIER clave, no solo `mode`/`manifest.mode`.
# ---------------------------------------------------------------------------------------------

_ASIGNACION_ON_OFF = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_.]*:\s*(on|off)\s*(#.*)?$")


def _token_sin_comillas(tok: str) -> bool:
    t = tok.strip()
    t = re.sub(r"\([^)]*\)\s*$", "", t).strip()
    return t in ("on", "off")


def check5_comillas():
    base = REPO / "skills"
    archivos = sorted(base.rglob("*.md"))
    if not archivos:
        return False, "no se encontraron archivos .md bajo skills/ — nada que barrer"
    violaciones = []
    for archivo in archivos:
        for i, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), start=1):
            if _ASIGNACION_ON_OFF.match(linea):
                violaciones.append(f"{archivo.relative_to(REPO)}:{i}: valor sin comillas → {linea.strip()}")
                continue
            if "#" not in linea or "|" not in linea:
                continue
            cabecera = _recortar_cabecera(linea.split("#", 1)[1])
            if "|" not in cabecera:
                continue
            if any(_token_sin_comillas(t) for t in cabecera.split("|")):
                violaciones.append(f"{archivo.relative_to(REPO)}:{i}: enum sin comillas → {linea.strip()}")
    if violaciones:
        return False, f"{len(violaciones)} violaciones — " + " | ".join(violaciones[:5])
    return True, f"0 valores y 0 enums con on/off sin comillas en {len(archivos)} archivos .md bajo skills/"


# ---------------------------------------------------------------------------------------------
# Check 6 (nuevo): colisión de claves de primer nivel al normalizar guion medio a guion bajo.
# `knowledge-vault` es la única clave del config con guion medio; sin este check nada impide que
# vuelva a coexistir con una homógrafa en guion bajo (el defecto que motivó sede-config-vault).
# ---------------------------------------------------------------------------------------------

def _fuentes_colision(sedes_config=None) -> list[tuple[Path, str]]:
    """Las sedes de `SEDES_CONFIG` con bloque YAML extraíble. La extracción "prosa" (la
    instrucción consumidora del vault) no tiene fence: `bloque_yaml` levantaría "bloque vacío"
    sobre ella, así que se filtra por tipo de extracción en vez de llamar `bloque_yaml` sobre
    las cinco sedes por igual."""
    if sedes_config is None:
        sedes_config = SEDES_CONFIG
    return [(ruta, ancla) for ruta, ancla, _rol, extraccion in sedes_config if extraccion != "prosa"]


def _claves_nivel1(ruta: Path, heading: str) -> set[str]:
    datos = _cargar_yaml(ruta, heading)
    if not isinstance(datos, dict):
        return set()
    return set(datos.keys())


def _normalizar_guion(clave: str) -> str:
    return clave.replace("-", "_")


def check6_colision(sedes_config=None):
    claves_n1: set[str] = set()
    for ruta, heading in _fuentes_colision(sedes_config):
        claves_n1 |= _claves_nivel1(ruta, heading)
    if not claves_n1:
        return False, "nada que comparar (0 claves de primer nivel entre las sedes activas)"
    por_normal: dict[str, set[str]] = {}
    for clave in claves_n1:
        por_normal.setdefault(_normalizar_guion(clave), set()).add(clave)
    colisiones = {norm: nombres for norm, nombres in por_normal.items() if len(nombres) > 1}
    if colisiones:
        detalle = "; ".join(
            f"{norm}: {', '.join(sorted(nombres))}" for norm, nombres in sorted(colisiones.items())
        )
        return False, f"{len(colisiones)} colisión(es) al normalizar guion medio→bajo — {detalle}"
    return True, f"{len(claves_n1)} claves de primer nivel, 0 colisiones al normalizar guion medio→bajo"


# ---------------------------------------------------------------------------------------------


def main() -> int:
    checks = [
        ("1a", "Claves — config-ejemplo.md", check1_config),
        ("1b", "Claves — manifest-ejemplo.md", check1_manifest),
        ("2a", "Enums — config-ejemplo.md (unión)", check2_config),
        ("2b", "Enums — manifest-ejemplo.md (intersección)", check2_manifest),
        ("3a", "Valores — config-ejemplo.md", check3_config),
        ("3b", "Valores — manifest-ejemplo.md", check3_manifest),
        ("4 ", "Marcas [def]/[ej]/[obl]", check4_marcas),
        ("5 ", "Comillas en on/off", check5_comillas),
        ("6 ", "Colisión de claves de primer nivel (guion medio→bajo)", check6_colision),
    ]
    ok_total = True
    for id_, nombre, fn in checks:
        try:
            ok, msg = fn()
        except FuenteIlegible as e:
            ok, msg = False, str(e)
        ok_total = ok_total and ok
        estado = "OK   " if ok else "FALLA"
        print(f"[{id_}] {estado} {nombre}: {msg}")
    print()
    if ok_total:
        print("RESULTADO: OK — las vistas son fieles a sus dueños")
        return 0
    print("RESULTADO: FALLA — ver detalle arriba")
    return 1


if __name__ == "__main__":
    sys.exit(main())
