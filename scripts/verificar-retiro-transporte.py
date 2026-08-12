#!/usr/bin/env python3
"""Verifica el **retiro de la vía de transporte de multiplexor** del ecosistema de skills.

Un modo por criterio de aceptación del flujo de retiro. El router se declara entero desde la primera
task y la verificación final los recorre todos: no puede cerrar con un modo que no exista.

    --ausencia      # AC-1  · implementado
    --clave         # AC-2  · implementado
    --adaptadores   # AC-3  · implementado
    --drenaje       # AC-14b · implementado
    --vocabulario   # AC-12  · implementado
    --docs          # AC-16  · implementado
    --vias          # AC-15  · implementado

    --autotest      # control positivo + mutantes sobre corpus sintéticos, no sobre el árbol real

Exit 0 si el modo pasa · 1 si hay hallazgos, listados en stdout · 2 si la invocación es inválida.

Seis reglas de diseño, heredadas del plan y de las tasks:

1. **Sin `grep`/`awk`/`sed`.** En esta máquina `grep` es ugrep y difiere de BSD grep en regex con
   anclas internas: el mismo patrón devolvió 1 y 0. Todo el parseo es Python + stdlib. `subprocess`
   se usa solo para `git ls-files` y `git status`.
2. **Este archivo no puede contener los términos que busca.** Un predicado versionado que escribiera
   literales los términos prohibidos se encontraría a sí mismo, y el criterio que exige cero
   coincidencias **sin lista de excepciones** sería imposible de satisfacer. Por eso los términos se
   arman por concatenación de fragmentos (`_A + _B`) y nunca aparecen enteros en el fuente. La
   alternativa —una excepción por ruta— abriría la puerta a que mañana algo más se esconda acá.
   Por la misma razón, al nombrar lo retirado se dice **"la vía retirada"** o **"el transporte de
   multiplexor"**, nunca su nombre propio.
3. **La entrada es el árbol candidato, no `git ls-files` a secas.** Medido: un archivo nuevo sin
   stage **no aparece** en `git ls-files`, y un archivo borrado del working tree pero aún en el
   índice **sí aparece**. Sin corregirlo, este mismo verificador se escaparía de su propio predicado
   y el modo de adaptadores nunca podría ponerse verde. El modelo es:

       árbol candidato = git ls-files − (bajas de este cambio) + (altas de este cambio no ignoradas)

   Las altas y las bajas salen del **manifiesto declarado** de más abajo, derivado de las rutas que
   las tasks de este cambio dicen tocar; `git status --porcelain -z -uall` se usa solo para
   **filtrar** contra él. A `git status` a secas no se le puede preguntar: el working tree puede
   tener suciedad ajena, y una baja ajena excluiría un archivo que todavía hay que inspeccionar
   mientras que un untracked ajeno daría un rojo falso.
4. **Expectativas por conjunto exacto: sobra tanto como falta.** La allowlist del modo `--clave` se
   comprueba en las dos direcciones —una aparición de más se rechaza, y una garantía declarada sin
   realización también—, porque un conteo no prueba un conjunto. Y cada garantía se cuenta **sola**:
   empaquetar varias bajo un contador compartido deja que borrar una la satisfaga otra.
5. **La allowlist permite construcciones, no archivos ni claves.** Lo que sobrevive es el *campo*
   `transport` —del sobre, por intento y del manifest de corrida—, nunca la *clave de configuración*.
   Por eso las construcciones prohibidas se rechazan **estén donde estén**, incluso dentro de una sede
   permitida: si el chequeo se apagara ahí, cualquier sede de la allowlist sería un escondite. Y las
   sedes se anclan a la sección y construcción concreta, nunca al archivo entero: un archivo de 1.400
   líneas declarado como sede permitida no ejerce la dirección "nada de más".
6. **Un árbol vacío nunca es verde, y `--autotest` es lo que lo prueba.** Un predicado de ausencia que
   no lee nada pasa por vacuidad: `git` ausente, una raíz equivocada o un `ls-files` que falla darían
   exit 0 con cero hallazgos. Por eso el árbol candidato se construye mirando el código de salida de
   `git` y fallando si queda vacío. Y por eso existe `--autotest`: sin un **control positivo** —un
   corpus donde el retiro está completo y todos los modos implementados dan verde— los mutantes no
   prueban nada,
   porque un verificador que fallara siempre los detectaría todos igual.

Uso: python3 scripts/verificar-retiro-transporte.py --ausencia | --clave | --adaptadores |
     --drenaje | --vocabulario | --docs | --vias | --autotest
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHANGE_BASE_COMMIT = "2ed62dd"

# ---------------------------------------------------------------------------
# Fragmentos. Ver regla 2 del docstring: ninguno de los términos buscados puede
# quedar entero en este fuente, así que se arman en runtime desde estas piezas.
# `_NOM` es el nombre propio de la herramienta externa; `_ALO` es el recipiente
# de terminal donde esa vía alojaba al worker.
# ---------------------------------------------------------------------------
_A, _B = "her", "dr"
_C, _D = "pa", "ne"
_NOM = _A + _B
_ALO = _C + _D

# La evidencia medida no es prosa del repositorio, y `--ausencia` no puede distinguirlas con un
# `grep`. Este modo existe para que el repo no REFERENCIE la vía retirada; una transcripción literal
# de una sesión que la nombró es un DATO capturado —la sesión dijo lo que dijo— y sus bytes son el
# `bundle_sha256` de esa corrida: editarla invalida el bundle y reabre el congelamiento del acta.
#
# La exclusión es por PREFIJO DE DIRECTORIO, terminado en `/` a propósito: `scripts/corridas-fase-0/`
# no alcanza a `scripts/corridas-fase-0-otra/`, así que un directorio de nombre parecido sigue
# escaneándose. Y se INFORMA en cada corrida: una exclusión silenciosa convierte «no hay rastro» en
# «no miré ahí», que es la misma frase con el sentido opuesto.
EVIDENCIA_EXCLUIDA = (
    "scripts/corridas-fase-0/",
    # La evidencia sellada del oráculo de la Fase 0.5. Uno de los veintiún flujos que el
    # detector leyó es el que retiró esta misma vía, así que su transcripción la nombra en
    # cada comando que corrió. Sus bytes están hasheados en `oraculo-evidencia/manifest.json`
    # y la procedencia del oráculo apunta a esa identidad: depurarla invalida el sello y
    # reabre el congelamiento, igual que en el caso de arriba.
    "scripts/oraculo-evidencia/",
)


# Un IDENTIFICADOR del corpus no es una REFERENCIA a la vía. Los manifiestos congelados de la Fase
# 0.5 enumeran la población de `.plans/`, y siete de esos directorios llevan el término en su
# nombre: son hechos del árbol, no prosa del repositorio. Omitirlos falsificaría el corpus —excluir
# los flujos incómodos es exactamente lo que su predicado de elegibilidad existe para impedir— y
# editarlos invalidaría el sello que los congela.
#
# El criterio es de FORMA y no de existencia, a propósito: `.plans/` no viaja en un clon, así que un
# predicado que preguntara «¿existe el directorio?» daría rojo en cualquier clon fresco. Un término
# queda exento cuando cae dentro de una cadena JSON —en un archivo `.json`— cuyo contenido COMPLETO
# es un identificador de ruta del corpus: sin espacios, y con el segmento `archived/`, su forma
# aplanada `archived__`, o el prefijo `.plans/`.
#
# Las cuatro formas que el corpus tiene hoy, y que este predicado describe:
#   "flujo": "archived/<slug>"                          · la terna y la exclusión
#   "archived/<slug>"                                   · el elemento suelto del snapshot
#   "ruta": ".plans/archived/<slug>/spec.md"            · la ruta canónica del artefacto sellado
#   "evidencia": "salidas/archived__<slug>.jsonl"       · la referencia a la salida cruda
#
# Lo que NO queda exento, y cada uno tiene su mutante: el término suelto en prosa; el término como
# valor de un token sin ruta (`"transport": "<término>"`); una ruta fuera del corpus
# (`skills/.../transporte-<término>.md`); un valor con espacios, aunque esté entrecomillado; y el
# término en el PATH del archivo, que se escanea aparte y nunca se exime.
PATRON_CADENA_JSON = re.compile(r'"([^"\\]*)"')
PATRON_IDENTIDAD_CORPUS = re.compile(r"^(?:\.plans/[^ ]*|[^ ]*archived(?:/|__)[^ ]*)$")


def tramos_de_identidad(rel: str, linea: str) -> list[tuple[int, int]]:
    """Los tramos de la línea que son identificadores del corpus. Vacío fuera de un `.json`."""
    if not rel.endswith(".json"):
        return []
    return [m.span(1) for m in PATRON_CADENA_JSON.finditer(linea)
            if PATRON_IDENTIDAD_CORPUS.match(m.group(1))]


def ocurrencias_reportables(rel: str, linea: str, patron: "re.Pattern") -> int:
    """Cuántas veces el patrón cae FUERA de todo identificador del corpus."""
    tramos = tramos_de_identidad(rel, linea)
    return sum(1 for m in patron.finditer(linea)
               if not any(a <= m.start() and m.end() <= b for a, b in tramos))


def es_evidencia_capturada(rel: str) -> bool:
    return any(rel.startswith(prefijo) for prefijo in EVIDENCIA_EXCLUIDA)


# Los siete términos del criterio de ausencia, con el nombre por el que se informan.
TERMINOS = [
    ("nombre-de-la-herramienta", re.compile(re.escape(_NOM), re.I)),
    ("alojamiento-como-palabra", re.compile(r"\b" + _ALO + r"s?\b", re.I)),
    ("variable-de-entorno", re.compile(re.escape(_NOM.upper() + "_ENV"))),
    ("extension-del-scope", re.compile(re.escape("scope." + _NOM), re.I)),
    ("constante-de-mapeo", re.compile(re.escape("MAPEO_" + _NOM.upper()))),
    ("causa-de-degradacion", re.compile(re.escape("transport_" + "fall" + "back"))),
    ("nombre-del-adaptador", re.compile(re.escape("transporte-" + _NOM), re.I)),
]

ADAPTADOR = "transporte-" + _NOM + ".md"
ADAPTADORES = [f"skills/{s}/{ADAPTADOR}" for s in ("co-explore", "cross-review", "cross-implement")]

# Los tres documentos versionados cuyo TEMA es la vía retirada: depurar un documento de su propio
# asunto no deja documento, así que se eliminan enteros.
DOCS_ELIMINADOS = [
    f"docs/superpowers/experiments/2026-08-01-{_NOM}-como-transporte.md",
    f"docs/superpowers/experiments/2026-08-02-{_NOM}-transporte-sintesis.md",
    f"docs/superpowers/specs/2026-07-23-{_NOM}-cli-cross-model-ideas.md",
]
DOCS_DEPURADOS = [
    "docs/superpowers/specs/2026-07-30-portacion-cli-first-cross-model.md",
    "docs/superpowers/plans/2026-08-03-init-y-config-ejemplo.md",
]
REF_BASE_DOCS_TEMPORAL = "refs/tags/verificador-docs-base"

# El fixture del par POSIX/PowerShell cuyo nombre ancla la partición de casing al valor retirado.
FIXTURE_RETIRADO = (f"scripts/paridad-casos/manifest-valido/fixtures/"
                    f"transport-{_NOM.upper()}/manifest.json")

# --- Manifiesto declarado de este cambio (regla 3 del docstring) ------------
# BAJAS: rutas que las tasks de este cambio eliminan del árbol.
BAJAS = [*ADAPTADORES, *DOCS_ELIMINADOS, FIXTURE_RETIRADO]
# ALTAS: rutas que las tasks de este cambio agregan. Se admite comodín solo donde el nombre final lo
# fija una task posterior —el fixture re-anclado—, y acotado al directorio del par afectado para que
# un untracked ajeno no entre por la ventana.
ALTAS = [
    "scripts/verificar-retiro-transporte.py",
    "scripts/baseline-sobre-en-vuelo.md",
    "scripts/paridad-casos/manifest-valido/fixtures/*/manifest.json",
]

# --- Modo --clave -----------------------------------------------------------
CONTRATO = "corridas-en-vuelo.md"
SEDE_CONTRATO = "<contrato>"
REFERENCIA_MANIFEST = "skills/cross-review/reference.md"
SEDE_PAR = "<par:manifest-valido>"

# Las tres construcciones específicas de la clave de configuración retirada. NO se busca la
# subcadena `transport`: capturaría toda la prosa en español con "transporte" y volvería el criterio
# imposible de pasar. Se rechazan **en cualquier sede**, permitida o no (regla 5 del docstring): la
# allowlist habilita el *campo*, y ninguna de estas tres construcciones es el campo.
#
# La clave YAML se distingue del campo por el **quoting**: una clave de `.specify/config.yml` va sin
# comillas (`transport: cli-exec`), mientras que el campo del manifest y el del sobre viven en JSON y
# van siempre entre comillas dobles (`"transport": "cli-exec"`). Sin ese lookahead, el ejemplo JSON
# del manifest —que la allowlist ampara— daría un rojo falso.
CONSTRUCCIONES = [
    ("clave-de-config", re.compile(r"cross_model[^\n]*?\btransport\b")),
    ("clave-yaml-al-inicio-de-linea",
     re.compile(r"""^[ \t]*(?:[-*+][ \t]+)?(?!")["'`]?transport["'`]?[ \t]*:""")),
    ("clave-del-mapa-overrides", re.compile(r"overrides[^\n]*?\btransport\b")),
]
# El símbolo suelto, con frontera de palabra: `transport` sí, "transporte"/"transportes" no.
SIMBOLO = re.compile(r"\btransport\b")

# Dónde PUEDE aparecer el símbolo suelto. Son sedes **semánticas**, no archivos: el contrato está
# replicado en siete skills y las siete copias se normalizan a `<contrato>`, y los dos sabores del par
# POSIX/PowerShell colapsan al mismo par. Ninguna entrada nombra un archivo entero: la sede es
# `<ruta o alias>§<heading>`, así que la dirección "nada de más" se ejerce también dentro del archivo
# más grande, donde el símbolo aparece once veces y solo cuatro construcciones sobreviven.
SEDES_PERMITIDAS = (
    f"{SEDE_CONTRATO}§Los campos del sobre",
    f"{SEDE_CONTRATO}§Los campos por intento",
    f"{SEDE_CONTRATO}§Varios workers en una corrida",
    f"{REFERENCIA_MANIFEST}§El archivo",
    f"{REFERENCIA_MANIFEST}§Los campos",
    f"{REFERENCIA_MANIFEST}§Las causas de la indisponibilidad, y la que no lo es",
    SEDE_PAR,
)

# Las garantías que la allowlist obliga a conservar, **una comprobación por garantía**. La primera
# entrada de la allowlist del criterio son tres cosas —el campo raíz, su regla de derivación y el
# valor `mixto`—, y bajo un contador compartido borrar dos de ellas seguía dando verde por la tercera.
# Cada fila lleva su sede exacta (o `None` si no la fija) y el patrón que la realiza.
GARANTIAS = [
    ("A1a", "campo `transport` en la raíz del sobre",
     f"{SEDE_CONTRATO}§Los campos del sobre", re.compile(r"^\s*\|\s*`transport`\s*\|")),
    ("A1b", "la regla de derivación del `transport` raíz, fuera de la fila de la tabla",
     f"{SEDE_CONTRATO}§Los campos del sobre",
     re.compile(r"^(?!\s*\|)[^\n]*\btransport\b[^\n]*deriv", re.I)),
    ("A1c", "el valor `mixto` para cuando los intentos vigentes difieren",
     f"{SEDE_CONTRATO}§Los campos del sobre", re.compile(r"\bmixto\b")),
    ("A2", "campo `transport` por intento",
     f"{SEDE_CONTRATO}§Los campos por intento", re.compile(r"^\s*\|\s*`transport`\s*\|")),
    ("A4", "campo `transport` del manifest de corrida y su enum",
     f"{REFERENCIA_MANIFEST}§Los campos", re.compile(r"^\s*\|\s*`transport`\s*\|")),
]
SECCION_FUENTES = "Fuente por transporte"
VIAS_SUPERVIVIENTES = ["subagent", "cli-exec", "cli-resume"]
CASOS_MANIFEST = "scripts/paridad-casos/manifest-valido/casos.json"
FIXTURES_MANIFEST = "scripts/paridad-casos/manifest-valido/fixtures"

# El bloque de config del orquestador desaparece entero: sin la clave retirada queda versionando una
# estructura vacía. Se mira la declaración del bloque, no cada mención en prosa.
BLOQUE_CONFIG = re.compile(r"^[ \t]*cross_model[ \t]*:")
SEDES_BLOQUE_CONFIG = [
    "skills/sdd-orchestrator/reference.md",
    "skills/sdd-orchestrator/manifest-ejemplo.md",
]

# --- Modo --vias -----------------------------------------------------------
# Cada construcción es (ruta, sede semántica, forma informada, texto exacto). La cardinalidad no se
# transcribe: se deriva de CHANGE_BASE_COMMIT y se exige igual en el árbol actual. Mantener la sede
# separada evita que una realización agregada en otro lugar compense una pérdida parcial.
_PREFERENCIA_VIAS = (
    ("skills/cross-review/reference.md", "Descubrir el revisor · tabla",
     "fila Claude→Codex con Vía A (preferida)",
     "| Claude | Codex | ¿Existe el subagente `codex:codex-rescue` (plugin codex)? Si no, "
     "¿`command -v codex`? | Vía A (preferida) o Vía B |"),
    ("skills/cross-review/reference.md", "Vía A",
     "heading Vía A — subagente preferido",
     "### Vía A — subagente `codex:codex-rescue` (preferida en Claude Code)"),
    ("skills/bitbucket-code-review/reference.md", "Vía A",
     "heading Vía A — subagente preferido",
     "#### Vía A — subagente `codex:codex-rescue` (preferida en Claude Code, revisor Codex)"),
)

_DESCUBRIMIENTO_VIAS = (
    ("skills/cross-review/reference.md", "Descubrir el revisor · tabla y nota PowerShell",
     "`command -v codex` + `Get-Command codex -ErrorAction SilentlyContinue`",
     "| Claude | Codex | ¿Existe el subagente `codex:codex-rescue` (plugin codex)? Si no, "
     "¿`command -v codex`? | Vía A (preferida) o Vía B |\n"
     "| GPT/Codex | Claude | ¿`command -v claude`? | Vía C |\n\n"
     "> **En PowerShell** la detección de binarios es "
     "`Get-Command codex -ErrorAction SilentlyContinue`"),
    ("skills/cross-implement/reference.md", "Descubrir el implementador · tabla",
     "filas W-B/W-C con detección POSIX y PowerShell",
     "| Claude | Codex | `command -v codex` (PowerShell: "
     "`Get-Command codex -ErrorAction SilentlyContinue`) | Vía W-B (workspace-write) |\n"
     "| GPT/Codex | Claude | `command -v claude` | Vía W-C (permisos path-scoped) |"),
    ("skills/co-explore/reference.md", "Descubrir el revisor · puntero",
     "puntero al algoritmo canónico de descubrimiento",
     "**Puntero.** El algoritmo canónico de descubrimiento del explorador —identificar la familia\n"
     "del autor y elegir el explorador de la otra familia— vive en "
     "`cross-review/reference.md` →\n\"Descubrir el revisor\"."),
    ("skills/bitbucket-code-review/reference.md", "Descubrir · paso 3",
     "detección POSIX/PowerShell de los revisores CLI",
     "Codex o Claude real). Detección de binarios: `command -v codex`/`command -v claude` "
     "(POSIX) o\n`Get-Command codex -ErrorAction SilentlyContinue` (PowerShell)."),
    ("CLAUDE.md", "Cross-model delegation",
     "regla de detección POSIX/PowerShell",
     "- **Detección de binario:** POSIX `command -v codex` · PowerShell "
     "`Get-Command codex -ErrorAction SilentlyContinue`."),
)

_AISLAMIENTO_EXEC_VIAS = (
    ("skills/cross-review/reference.md", "Vía B · ronda 1 POSIX",
     "`set -- exec … -s read-only`",
     "set -- exec --ignore-user-config --disable hooks --disable apps --disable plugins \\\n"
     "       -s read-only -C <working_dir> --skip-git-repo-check --json \\"),
    ("skills/cross-review/reference.md", "Vía B · ronda 1 PowerShell",
     "`$CodexArgs = @('exec', … '-s','read-only', …)`",
     "$CodexArgs = @('exec','--ignore-user-config','--disable','hooks','--disable','apps',\n"
     "               '--disable','plugins','-s','read-only','-C','<working_dir>',"),
    ("skills/co-explore/reference.md", "Descubrir el revisor · POSIX",
     "`set -- exec … -s read-only`",
     "set -- exec --ignore-user-config --disable hooks --disable apps --disable plugins \\\n"
     "       -s read-only -C <working_dir> --skip-git-repo-check --json \\"),
    ("skills/co-explore/reference.md", "Descubrir el revisor · PowerShell",
     "`$CodexArgs = @('exec', … '-s','read-only', …)`",
     "$CodexArgs = @('exec','--ignore-user-config','--disable','hooks','--disable','apps',\n"
     "               '--disable','plugins','-s','read-only','-C','<working_dir>',"),
    ("skills/co-explore/reference.md", "Fan-out dual · POSIX",
     "`codex exec … -s read-only`",
     "codex exec --ignore-user-config --disable hooks --disable apps --disable plugins \\\n"
     "      -s read-only -C <working_dir> --skip-git-repo-check --json \\"),
)

_AISLAMIENTO_RESUME_VIAS = (
    ("skills/cross-review/reference.md", "Vía B · rondas siguientes POSIX",
     "`set -- exec resume … -c sandbox_mode=read-only`",
     "  set -- exec resume \"$SESSION_ID\" --ignore-user-config \\\n"
     "         --disable hooks --disable apps --disable plugins \\\n"
     "         -c sandbox_mode=read-only --skip-git-repo-check \\"),
    ("skills/cross-review/reference.md", "Vía B · rondas siguientes PowerShell",
     "`@('exec','resume', … 'sandbox_mode=read-only', …)`",
     "  $CodexArgs = @('exec','resume',$SessionId,'--ignore-user-config','--disable','hooks',\n"
     "                 '--disable','apps','--disable','plugins','-c','sandbox_mode=read-only',"),
    ("skills/cross-review/reference.md", "Resume del seed · POSIX",
     "`set -- exec resume … -c sandbox_mode=read-only`",
     "set -- exec resume \"$SESSION_ID\" --ignore-user-config \\\n"
     "       --disable hooks --disable apps --disable plugins \\\n"
     "       -c sandbox_mode=read-only --skip-git-repo-check --json \\"),
    ("skills/cross-review/reference.md", "Resume del seed · PowerShell",
     "`@('exec','resume', … 'sandbox_mode=read-only', …)`",
     "$CodexArgs = @('exec','resume',$Seed.session_id,'--ignore-user-config','--disable','hooks',\n"
     "               '--disable','apps','--disable','plugins','-c','sandbox_mode=read-only',"),
)

_WORKSPACE_EXEC_VIAS = (
    ("skills/cross-implement/reference.md", "Vías de invocación · regla 1",
     "escritura acotada y prohibición explícita de bypass",
     "1. **Escritura acotada por construcción, nunca por confianza**: sandbox `workspace-write` "
     "en\n   Codex, permisos path-scoped en Claude. **Nunca** `--yolo` /\n"
     "   `--dangerously-bypass-approvals-and-sandbox` / "
     "`--dangerously-skip-permissions` /\n   `acceptEdits` sin scoping"),
    ("skills/cross-implement/reference.md", "Vía W-B · lanzamiento POSIX",
     "`codex exec -s workspace-write`",
     "  codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json \\\n"
     "    --output-last-message <scratch>/report.txt - < <scratch>/prompt.txt \\"),
    ("skills/cross-implement/reference.md", "Vía W-B · lanzamiento PowerShell",
     "`Get-Content -Raw … | codex exec -s workspace-write`",
     "  Get-Content -Raw <scratch>\\prompt.txt |\n"
     "    codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json `"),
    ("skills/cross-implement/reference.md", "Vía W-C · lanzamiento",
     "`--permission-mode default` + Edit/Write path-scoped",
     "  ( cd <working_dir> && claude -p --safe-mode --model sonnet "
     "--permission-mode default \\\n"
     "      --allowedTools='Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)' \\\n"
     "      --session-id \"$SESSION_ID\""),
)

_WORKSPACE_RESUME_VIAS = (
    ("skills/cross-implement/reference.md", "Vía W-B · fix round POSIX",
     "`codex exec resume … sandbox_mode=workspace-write`",
     "  codex exec resume \"$SESSION_ID\" -c sandbox_mode=\"workspace-write\" "
     "--skip-git-repo-check --json \\\n"
     "    --output-last-message <scratch>/report.txt - < <scratch>/fix-rN.txt \\"),
    ("skills/cross-implement/reference.md", "Vía W-B · fix round PowerShell",
     "pipe + `$SessionId` con override `workspace-write`",
     "  En **PowerShell**: mismo patrón que la Vía B de cross-review (pipe + `$SessionId` con "
     "guard),\n  cambiando el valor del override a `workspace-write`."),
    ("skills/cross-implement/reference.md", "Vía W-C · fix round",
     "`--permission-mode default` + Edit/Write path-scoped + `--resume`",
     "  ( cd <working_dir> && claude -p --safe-mode --model sonnet "
     "--permission-mode default \\\n"
     "      --allowedTools='Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)' \\\n"
     "      --resume \"$SESSION_ID\""),
)

_RESUME_VIAS = (
    ("skills/cross-review/reference.md", "Vía B · comprobación de flags",
     "`codex exec resume --help`",
     "Verificado contra `codex exec resume --help`"),
    ("skills/cross-review/reference.md", "Vía B y seed · POSIX",
     "`set -- exec resume \"$SESSION_ID\" --ignore-user-config`",
     "set -- exec resume \"$SESSION_ID\" --ignore-user-config \\"),
    ("skills/cross-review/reference.md", "Vía B · PowerShell",
     "`@('exec','resume',$SessionId, …)`",
     "$CodexArgs = @('exec','resume',$SessionId,"),
    ("skills/cross-review/reference.md", "Seed · PowerShell",
     "`@('exec','resume',$Seed.session_id, …)`",
     "$CodexArgs = @('exec','resume',$Seed.session_id,"),
    ("skills/cross-review/reference.md", "Resume entre rondas · resumen",
     "`codex exec resume <thread_id>` + sandbox read-only",
     "Vía B: `codex exec resume <thread_id>\n  -c sandbox_mode=\"read-only\"`"),
    ("skills/cross-implement/reference.md", "Vía W-B · fix round",
     "`codex exec resume \"$SESSION_ID\"` + sandbox workspace-write",
     "codex exec resume \"$SESSION_ID\" -c sandbox_mode=\"workspace-write\""),
    ("CLAUDE.md", "Cross-model delegation",
     "regla de resume con sandbox workspace-write",
     "resume con `codex exec resume \"$SESSION_ID\" -c sandbox_mode=\"workspace-write\" ...`"),
)

_POSIX_EXEC_VIAS = (
    ("skills/cross-review/reference.md", "Vía B · ronda 1",
     "`codex \"$@\" < <ruta/al/prompt-r1.txt>`",
     "set -- exec --ignore-user-config --disable hooks --disable apps --disable plugins \\\n"
     "       -s read-only -C <working_dir> --skip-git-repo-check --json \\\n"
     "       --output-last-message <ruta/al/veredicto.txt>\n"
     "[ -n \"$MODEL\" ]  && set -- \"$@\" -m \"$MODEL\"\n"
     "[ -n \"$EFFORT\" ] && set -- \"$@\" -c \"model_reasoning_effort=$EFFORT\"\n"
     "set -- \"$@\" -\ncodex \"$@\" < <ruta/al/prompt-r1.txt>"),
    ("skills/cross-implement/reference.md", "Vía W-B · lanzamiento",
     "`codex exec … < <scratch>/prompt.txt`",
     "  codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json \\\n"
     "    --output-last-message <scratch>/report.txt - < <scratch>/prompt.txt \\"),
    ("skills/co-explore/reference.md", "Descubrir el revisor · lanzamiento",
     "`codex \"$@\" < co-explore/scratch/prompt.txt`",
     "set -- exec --ignore-user-config --disable hooks --disable apps --disable plugins \\\n"
     "       -s read-only -C <working_dir> --skip-git-repo-check --json \\\n"
     "       --output-last-message co-explore/scratch/explorer.out\n"
     "[ -n \"$MODEL\" ]  && set -- \"$@\" -m \"$MODEL\"\n"
     "[ -n \"$EFFORT\" ] && set -- \"$@\" -c \"model_reasoning_effort=$EFFORT\"\n"
     "set -- \"$@\" -\ncodex \"$@\" < co-explore/scratch/prompt.txt"),
    ("skills/co-explore/reference.md", "Fan-out dual · lanzamiento",
     "`codex exec … < \"$S/prompt-$M-codex-worker.txt\"`",
     "codex exec --ignore-user-config --disable hooks --disable apps --disable plugins \\\n"
     "      -s read-only -C <working_dir> --skip-git-repo-check --json \\\n"
     "      --output-last-message \"$S/raw-$M-codex-worker.md\" \\\n"
     "      ${MODEL:+-m} ${MODEL:+\"$MODEL\"} - \\\n"
     "    < \"$S/prompt-$M-codex-worker.txt\""),
    ("skills/bitbucket-code-review/reference.md", "Vía B · lanzamiento",
     "`codex exec … < <raíz-repo>/.pr-review/<id>/prompt.txt`",
     "codex exec -s read-only -C <dir-código> --skip-git-repo-check \\\n"
     "  --output-last-message <raíz-repo>/.pr-review/<id>/codex-verdict.txt - "
     "< <raíz-repo>/.pr-review/<id>/prompt.txt"),
    ("CLAUDE.md", "Cross-model delegation",
     "regla POSIX `< prompt.txt`",
     "POSIX pasa el prompt por `< prompt.txt`"),
)

_POWERSHELL_EXEC_VIAS = (
    ("skills/cross-review/reference.md", "Vía B · ronda 1",
     "`Get-Content -Raw … | & codex @CodexArgs`",
     "$CodexArgs = @('exec','--ignore-user-config','--disable','hooks','--disable','apps',\n"
     "               '--disable','plugins','-s','read-only','-C','<working_dir>',\n"
     "               '--skip-git-repo-check','--json','--output-last-message',"
     "'<ruta\\al\\veredicto.txt>')\n"
     "if ($Model)  { $CodexArgs += @('-m', $Model) }\n"
     "if ($Effort) { $CodexArgs += @('-c', \"model_reasoning_effort=$Effort\") }\n"
     "$CodexArgs += '-'\nGet-Content -Raw <ruta\\al\\prompt-r1.txt> |\n"
     "  & codex @CodexArgs"),
    ("skills/cross-implement/reference.md", "Vía W-B · lanzamiento",
     "`Get-Content -Raw … | codex exec`",
     "  Get-Content -Raw <scratch>\\prompt.txt |\n"
     "    codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json `"),
    ("skills/co-explore/reference.md", "Descubrir el revisor · lanzamiento",
     "`Start-Process codex -RedirectStandardInput …prompt.txt`",
     "$proc = Start-Process -FilePath codex -NoNewWindow -PassThru `\n"
     "  -RedirectStandardInput  co-explore\\scratch\\prompt.txt `"),
    ("skills/co-explore/reference.md", "Fan-out dual · lanzamiento",
     "`Start-Process codex -RedirectStandardInput …worker.txt`",
     "$pCodex = Start-Process -FilePath codex -NoNewWindow -PassThru `\n"
     "  -RedirectStandardInput  \"$S\\prompt-$M-codex-worker.txt\" `"),
    ("skills/bitbucket-code-review/reference.md", "Vía B · lanzamiento",
     "`Get-Content -Raw … | codex exec`",
     "Get-Content -Raw <raíz-repo>\\.pr-review\\<id>\\prompt.txt |\n"
     "  codex exec -s read-only -C <dir-código> --skip-git-repo-check `"),
    ("CLAUDE.md", "Cross-model delegation",
     "regla PowerShell `Get-Content -Raw prompt.txt | codex exec … -`",
     "`Get-Content -Raw prompt.txt | codex exec ... -`"),
)

_POSIX_RESUME_VIAS = (
    ("skills/cross-review/reference.md", "Vía B · rondas siguientes",
     "`codex \"$@\" < <ruta/al/delta-rN.txt>`",
     "  set -- exec resume \"$SESSION_ID\" --ignore-user-config \\\n"
     "         --disable hooks --disable apps --disable plugins \\\n"
     "         -c sandbox_mode=read-only --skip-git-repo-check \\\n"
     "         --output-last-message <ruta/veredicto.txt>\n"
     "  [ -n \"$MODEL\" ]  && set -- \"$@\" -m \"$MODEL\"\n"
     "  [ -n \"$EFFORT\" ] && set -- \"$@\" -c \"model_reasoning_effort=$EFFORT\"\n"
     "  set -- \"$@\" -\n  codex \"$@\" < <ruta/al/delta-rN.txt>"),
    ("skills/cross-review/reference.md", "Resume del seed",
     "`codex \"$@\" < <ruta/al/prompt-r1.txt>`",
     "set -- exec resume \"$SESSION_ID\" --ignore-user-config \\\n"
     "       --disable hooks --disable apps --disable plugins \\\n"
     "       -c sandbox_mode=read-only --skip-git-repo-check --json \\\n"
     "       --output-last-message <ruta/al/veredicto.txt>\n"
     "[ -n \"$MODEL\" ]  && set -- \"$@\" -m \"$MODEL\"\n"
     "[ -n \"$EFFORT\" ] && set -- \"$@\" -c \"model_reasoning_effort=$EFFORT\"\n"
     "set -- \"$@\" -\ncodex \"$@\" < <ruta/al/prompt-r1.txt>"),
    ("skills/cross-implement/reference.md", "Vía W-B · fix round",
     "`codex exec resume … < <scratch>/fix-rN.txt`",
     "  codex exec resume \"$SESSION_ID\" -c sandbox_mode=\"workspace-write\" "
     "--skip-git-repo-check --json \\\n"
     "    --output-last-message <scratch>/report.txt - < <scratch>/fix-rN.txt \\"),
)

_POWERSHELL_RESUME_VIAS = (
    ("skills/cross-review/reference.md", "Vía B · rondas siguientes",
     "`Get-Content -Raw …delta-rN.txt | & codex @CodexArgs`",
     "  $CodexArgs = @('exec','resume',$SessionId,'--ignore-user-config','--disable','hooks',\n"
     "                 '--disable','apps','--disable','plugins','-c','sandbox_mode=read-only',\n"
     "                 '--skip-git-repo-check','--output-last-message',"
     "'<ruta\\veredicto.txt>')\n"
     "  if ($Model)  { $CodexArgs += @('-m', $Model) }\n"
     "  if ($Effort) { $CodexArgs += @('-c', \"model_reasoning_effort=$Effort\") }\n"
     "  $CodexArgs += '-'\n  Get-Content -Raw <ruta\\al\\delta-rN.txt> |\n"
     "    & codex @CodexArgs"),
    ("skills/cross-review/reference.md", "Resume del seed",
     "`Get-Content -Raw …prompt-r1.txt | & codex @CodexArgs`",
     "$CodexArgs = @('exec','resume',$Seed.session_id,'--ignore-user-config','--disable','hooks',\n"
     "               '--disable','apps','--disable','plugins','-c','sandbox_mode=read-only',\n"
     "               '--skip-git-repo-check','--json',\n"
     "               '--output-last-message','<ruta\\al\\veredicto.txt>')\n"
     "if ($Seed.model)  { $CodexArgs += @('-m', $Seed.model) }\n"
     "if ($Seed.effort) { $CodexArgs += @('-c', "
     "\"model_reasoning_effort=$($Seed.effort)\") }\n"
     "$CodexArgs += '-'\nGet-Content -Raw <ruta\\al\\prompt-r1.txt> |\n"
     "  & codex @CodexArgs"),
    ("skills/cross-implement/reference.md", "Vía W-B · fix round",
     "declaración PowerShell: pipe + `$SessionId` y override workspace-write",
     "  En **PowerShell**: mismo patrón que la Vía B de cross-review (pipe + `$SessionId` con "
     "guard),\n  cambiando el valor del override a `workspace-write`."),
)

GARANTIAS_VIAS = (
    "preferencia-revision",
    "descubrimiento-cli",
    "aislamiento-read-only",
    "workspace-write-acotado",
    "resume-cli",
    "comando-posix",
    "comando-powershell",
)
MATRIZ_VIAS = {
    "subagent": {"preferencia-revision": _PREFERENCIA_VIAS},
    "cli-exec": {
        "descubrimiento-cli": _DESCUBRIMIENTO_VIAS,
        "aislamiento-read-only": _AISLAMIENTO_EXEC_VIAS,
        "workspace-write-acotado": _WORKSPACE_EXEC_VIAS,
        "comando-posix": _POSIX_EXEC_VIAS,
        "comando-powershell": _POWERSHELL_EXEC_VIAS,
    },
    "cli-resume": {
        "descubrimiento-cli": _DESCUBRIMIENTO_VIAS,
        "aislamiento-read-only": _AISLAMIENTO_RESUME_VIAS,
        "workspace-write-acotado": _WORKSPACE_RESUME_VIAS,
        "resume-cli": _RESUME_VIAS,
        "comando-posix": _POSIX_RESUME_VIAS,
        "comando-powershell": _POWERSHELL_RESUME_VIAS,
    },
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).casefold().strip()


# Índice normalizado de las sedes permitidas. La comparación es **exacta**, nunca por prefijo: un
# `startswith("<archivo>§")` volvería permitido el archivo entero y la dirección "nada de más"
# dejaría de ejercerse justo en la entrada más grande.
_SEDES_NORM = {norm(s): s for s in SEDES_PERMITIDAS}


def sede_canonica(sede: str) -> str | None:
    """La sede permitida que le corresponde, o `None` si no hay ninguna."""
    return _SEDES_NORM.get(norm(sede))


class ArbolInvalido(RuntimeError):
    """El árbol candidato no se pudo construir, o quedó vacío.

    Nunca puede terminar en verde: un predicado de ausencia sobre cero archivos pasa por vacuidad, y
    entonces `git` ausente, una `--raiz` equivocada o un `ls-files` que falla se leerían como "no hay
    rastros". Es exactamente el falso verde que esta excepción existe para convertir en rojo.
    """


def _git(raiz: Path, *args: str) -> str:
    """stdout de `git`, o `ArbolInvalido` si el binario falta o el comando no termina en 0."""
    try:
        r = subprocess.run(["git", *args], cwd=str(raiz), capture_output=True, text=True,
                           check=False)
    except (OSError, FileNotFoundError) as e:
        raise ArbolInvalido(f"no se pudo ejecutar `git {' '.join(args)}` en {raiz}: {e}") from e
    if r.returncode != 0:
        detalle = (r.stderr or r.stdout).strip().splitlines()
        raise ArbolInvalido(f"`git {' '.join(args)}` terminó en {r.returncode} en {raiz}"
                            + (f" — {detalle[0][:160]}" if detalle else ""))
    return r.stdout


def rastreados(raiz: Path) -> list[str]:
    return [p for p in _git(raiz, "ls-files", "-z").split("\0") if p]


def estado_working_tree(raiz: Path) -> tuple[set[str], set[str]]:
    """(borrados, agregados) según `git status --porcelain -z -uall`.

    `-uall` es necesario porque el porcelain por defecto colapsa un directorio untracked en una sola
    entrada terminada en `/`, y entonces un archivo nuevo dentro de él no sería visible. Los
    ignorados no aparecen sin `--ignored`, que es justo lo que se quiere: las altas son "no
    ignoradas" por construcción.
    """
    campos = _git(raiz, "status", "--porcelain", "-z", "-uall").split("\0")
    borrados: set[str] = set()
    agregados: set[str] = set()
    i = 0
    while i < len(campos):
        entrada = campos[i]
        i += 1
        if not entrada or len(entrada) < 4:
            continue
        xy, ruta = entrada[:2], entrada[3:]
        if xy[0] in ("R", "C"):
            origen = campos[i] if i < len(campos) else ""
            i += 1
            if origen:
                borrados.add(origen)
            agregados.add(ruta)
        elif xy == "??":
            agregados.add(ruta)
        elif "D" in xy:
            borrados.add(ruta)
        elif "A" in xy:
            agregados.add(ruta)
    return borrados, agregados


def arbol_candidato(raiz: Path) -> tuple[list[str], set[str], set[str]]:
    """git ls-files − bajas declaradas y efectivas + altas declaradas y efectivas.

    Levanta `ArbolInvalido` si `git` falla o si el resultado queda vacío: ver regla 6 del docstring.
    """
    base = rastreados(raiz)
    borrados, agregados = estado_working_tree(raiz)
    bajas = {p for p in BAJAS if p in borrados}
    altas = {p for p in agregados if any(fnmatch.fnmatch(p, pat) for pat in ALTAS)}
    en_base = set(base)
    candidato = [p for p in base if p not in bajas]
    candidato += sorted(a for a in altas if a not in en_base)
    candidato = sorted(set(candidato))
    if not candidato:
        raise ArbolInvalido(
            f"el árbol candidato quedó vacío en {raiz}: sobre cero archivos cualquier predicado de "
            f"ausencia pasa por vacuidad, así que el modo falla en vez de dar verde")
    return candidato, bajas, altas


def leer(raiz: Path, rel: str) -> str | None:
    ruta = raiz / rel
    try:
        return ruta.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None


def sedes_por_linea(rel: str, texto: str) -> dict[int, str]:
    """Sede semántica de cada línea: `<ruta normalizada>§<heading>`, o `<par:nombre>` dentro de un
    bloque cercado que declare `# @bloque:`.

    Las siete copias del contrato colapsan a `<contrato>`, y los dos sabores del par —POSIX y
    PowerShell— colapsan al mismo par: la allowlist es de construcciones, no de archivos.
    """
    ruta_norm = SEDE_CONTRATO if Path(rel).name == CONTRATO else rel
    lineas = texto.splitlines()
    cerca = re.compile(r"^\s*(?:```|~~~)")
    nombre_bloque = re.compile(r"^#\s*@bloque:\s*(\S+)")
    resultado: dict[int, str] = {}
    heading = "(sin sección)"
    dentro = False
    bloque: str | None = None
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if cerca.match(linea):
            if dentro:
                dentro, bloque = False, None
            else:
                dentro, bloque = True, None
                j = i + 1
                while j < len(lineas) and not cerca.match(lineas[j]):
                    m = nombre_bloque.match(lineas[j])
                    if m:
                        bloque = m.group(1)
                    j += 1
            resultado[i + 1] = f"{ruta_norm}§{heading}"
        elif dentro:
            resultado[i + 1] = (f"<par:{re.sub(r'-ps$', '', bloque)}>" if bloque
                                else f"{ruta_norm}§{heading}")
        else:
            m = re.match(r"^(#{1,6})\s+(.+?)\s*$", linea)
            if m:
                heading = m.group(2)
            resultado[i + 1] = f"{ruta_norm}§{heading}"
        i += 1
    return resultado


class Reporte:
    """Acumula hallazgos y los imprime. Un hallazgo es una violación del criterio, no un aviso."""

    def __init__(self, modo: str) -> None:
        self.modo = modo
        self.hallazgos: list[str] = []
        self.notas: list[str] = []

    def hallazgo(self, texto: str) -> None:
        self.hallazgos.append(texto)

    def nota(self, texto: str) -> None:
        self.notas.append(texto)

    def cerrar(self) -> int:
        print(f"=== --{self.modo}")
        for n in self.notas:
            print(f"[nota ] {n}")
        for h in self.hallazgos:
            print(f"[FALLA] {h}")
        estado = "OK" if not self.hallazgos else "FALLA"
        print(f"RESULTADO: {estado}")
        print(f"hallazgos: {len(self.hallazgos)}")
        return 1 if self.hallazgos else 0


# ---------------------------------------------------------------------------
# --docs (AC-16)
# ---------------------------------------------------------------------------
def lineas_documentales(texto: str) -> list[str]:
    """Líneas fuera de fences Markdown, donde vive la estructura del documento."""
    resultado: list[str] = []
    cerca: tuple[str, int] | None = None
    for linea in texto.splitlines():
        marca = re.match(r"^\s*(`{3,}|~{3,})", linea)
        if marca:
            token = marca.group(1)
            if cerca is None:
                cerca = (token[0], len(token))
            elif token[0] == cerca[0] and len(token) >= cerca[1]:
                cerca = None
            continue
        if cerca is None:
            resultado.append(linea)
    return resultado


def celdas_tabla(linea: str) -> list[str]:
    """Celdas Markdown; una barra escapada pertenece a la celda y no crea otra columna."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", linea.strip().strip("|"))]


def es_separador_tabla(celdas: list[str]) -> bool:
    return bool(celdas) and all(re.fullmatch(r":?-{3,}:?", c) for c in celdas)


def extraer_estructura_doc(texto: str) -> dict[str, object]:
    """Extrae solo la mitad inmutable: estructura, IDs, guardas y catálogo.

    El texto de los elementos no forma parte del oráculo: el retiro exige reescribir cómo se
    nombraban ciertos hechos. La presencia, nivel, cardinalidad e identificadores sí forman parte.
    """
    lineas = lineas_documentales(texto)
    niveles_headings: list[int] = []
    ids_headings: Counter[str] = Counter()
    for linea in lineas:
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", linea)
        if not m:
            continue
        niveles_headings.append(len(m.group(1)))
        titulo = m.group(2)
        numerado = re.match(r"^(\d+)\.\s", titulo)
        tarea = re.match(r"^Task\s+(\d+)\b", titulo, re.I)
        if numerado:
            ids_headings[f"entrada-{numerado.group(1)}"] += 1
        if tarea:
            ids_headings[f"task-{tarea.group(1)}"] += 1

    ids_tarea: Counter[str] = Counter()
    for m in re.finditer(r"\b(?:Task\s+(\d+)|Step\s+(\d+)|T(\d+))\b", texto, re.I):
        if m.group(1):
            ids_tarea[f"task-{m.group(1)}"] += 1
        elif m.group(2):
            ids_tarea[f"step-{m.group(2)}"] += 1
        else:
            ids_tarea[f"t-{m.group(3)}"] += 1

    ids_guardas = Counter(m.group(0).upper()
                          for m in re.finditer(r"\bG\d+o?\b", texto, re.I))

    bloques_tabla: list[list[list[str]]] = []
    bloque: list[list[str]] = []
    for linea in [*lineas, ""]:
        if linea.strip().startswith("|") and linea.strip().endswith("|"):
            bloque.append(celdas_tabla(linea))
            continue
        if bloque:
            bloques_tabla.append(bloque)
            bloque = []

    forma_catalogo: list[tuple[int, ...]] = []
    ids_catalogo: Counter[str] = Counter()
    for filas in bloques_tabla:
        separadores = [i for i, celdas in enumerate(filas) if es_separador_tabla(celdas)]
        if len(separadores) != 1:
            continue
        datos = filas[separadores[0] + 1:]
        forma_catalogo.append(tuple(len(celdas) for celdas in datos))
        for celdas in datos:
            if not celdas:
                continue
            primera = celdas[0]
            if re.fullmatch(r"\d+", primera):
                ids_catalogo[f"fila-{primera}"] += 1
                continue
            ruta = re.fullmatch(r"`([^`]+\.(?:md|sh|txt)(?::\d+)?)`", primera)
            if ruta:
                ids_catalogo[f"ruta-{ruta.group(1)}"] += 1

    return {
        "headings": tuple(niveles_headings),
        "ids-de-heading": ids_headings,
        "ids-de-tarea": ids_tarea,
        "guardas": ids_guardas,
        "entradas-de-catalogo": tuple(forma_catalogo),
        "ids-de-catalogo": ids_catalogo,
    }


def referencia_base_docs(raiz: Path) -> str:
    """Commit real, o la etiqueta privada que usa únicamente el corpus temporal del autotest."""
    if raiz.resolve() != REPO.resolve():
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", REF_BASE_DOCS_TEMPORAL],
                           cwd=str(raiz), capture_output=True, text=True, check=False)
        if r.returncode == 0:
            return REF_BASE_DOCS_TEMPORAL
    return CHANGE_BASE_COMMIT


def _diferencia_contadores(base: Counter, actual: Counter) -> str:
    faltan = list((base - actual).elements())
    sobran = list((actual - base).elements())
    return f"faltan={faltan[:8]} · sobran={sobran[:8]}"


def evaluar_docs(raiz: Path) -> Reporte:
    rep = Reporte("docs")
    presentes = [rel for rel in DOCS_ELIMINADOS if (raiz / rel).exists()]
    for rel in presentes:
        rep.hallazgo(f"{rel} · la ruta temática todavía existe")
    rep.nota(f"rutas temáticas ausentes: {len(DOCS_ELIMINADOS) - len(presentes)}/"
             f"{len(DOCS_ELIMINADOS)}")

    base_ref = referencia_base_docs(raiz)
    rep.nota("oráculo estructural: " + (CHANGE_BASE_COMMIT if base_ref == CHANGE_BASE_COMMIT
                                        else f"fixture temporal derivado de {CHANGE_BASE_COMMIT}"))
    for rel in DOCS_DEPURADOS:
        actual_texto = leer(raiz, rel)
        if actual_texto is None:
            rep.hallazgo(f"{rel} · documento depurado ausente o ilegible")
            continue
        try:
            base_texto = _git(raiz, "show", f"{base_ref}:{rel}")
        except ArbolInvalido as e:
            rep.hallazgo(f"{rel} · no se pudo leer el oráculo: {e}")
            continue
        base = extraer_estructura_doc(base_texto)
        actual = extraer_estructura_doc(actual_texto)
        elementos_base = (len(base["headings"])
                          + sum(base["ids-de-tarea"].values())
                          + sum(base["guardas"].values())
                          + sum(len(tabla) for tabla in base["entradas-de-catalogo"]))
        if elementos_base == 0:
            rep.hallazgo(f"{rel} · extracción del oráculo vino vacía: 0 elementos sumando "
                         "headings, IDs de tarea, guardas y entradas de catálogo")
        rep.nota(f"{rel}: headings={len(actual['headings'])} · "
                 f"ids-tarea={sum(actual['ids-de-tarea'].values())} · "
                 f"guardas={sum(actual['guardas'].values())} · "
                 f"entradas-catálogo={sum(len(t) for t in actual['entradas-de-catalogo'])}")
        for clase in base:
            esperado = base[clase]
            observado = actual[clase]
            if esperado == observado:
                continue
            if isinstance(esperado, Counter) and isinstance(observado, Counter):
                detalle = _diferencia_contadores(esperado, observado)
            else:
                detalle = f"base={esperado} · actual={observado}"
            rep.hallazgo(f"{rel} · {clase} no conservados · {detalle}")
    return rep


# ---------------------------------------------------------------------------
# --ausencia (AC-1)
# ---------------------------------------------------------------------------
def evaluar_ausencia(raiz: Path) -> Reporte:
    rep = Reporte("ausencia")
    try:
        candidato, bajas, altas = arbol_candidato(raiz)
    except ArbolInvalido as e:
        rep.hallazgo(str(e))
        return rep
    evidencia = [rel for rel in candidato if es_evidencia_capturada(rel)]
    candidato = [rel for rel in candidato if not es_evidencia_capturada(rel)]
    rep.nota(f"árbol candidato: {len(candidato)} archivos "
             f"(−{len(bajas)} bajas efectivas, +{len(altas)} altas efectivas)")
    if evidencia:
        rep.nota(f"evidencia capturada excluida del escaneo: {len(evidencia)} archivos bajo "
                 f"{', '.join(EVIDENCIA_EXCLUIDA)} — transcripción de sesiones medidas, no prosa "
                 f"del repositorio, y con sus bytes hasheados en el bundle de cada corrida")
    exentas = 0
    for rel in candidato:
        for etiqueta, patron in TERMINOS:
            if patron.search(rel):
                rep.hallazgo(f"{rel} · path · {etiqueta}")
        texto = leer(raiz, rel)
        if texto is None:
            rep.hallazgo(f"{rel} · ilegible: el predicado no puede afirmar ausencia sobre él")
            continue
        for n, linea in enumerate(texto.splitlines(), 1):
            for etiqueta, patron in TERMINOS:
                if ocurrencias_reportables(rel, linea, patron):
                    rep.hallazgo(f"{rel}:{n} · {etiqueta} · {linea.strip()[:110]}")
                elif patron.search(linea):
                    exentas += 1
    if exentas:
        rep.nota(f"identificadores del corpus exentos: {exentas} ocurrencias dentro de una cadena "
                 "JSON cuyo contenido completo es una ruta del corpus — nombran un flujo de "
                 "`.plans/`, no referencian la vía")
    return rep


# ---------------------------------------------------------------------------
# --clave (AC-2)
# ---------------------------------------------------------------------------
def filas_tabla_fuentes(texto: str) -> list[str]:
    """Los valores de enum de la primera columna de la tabla de fuentes por transporte."""
    dentro = False
    filas: list[str] = []
    for linea in texto.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", linea)
        if m:
            dentro = norm(m.group(2)) == norm(SECCION_FUENTES)
            continue
        if not dentro or not linea.strip().startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if not celdas:
            continue
        m2 = re.match(r"^`([^`]+)`$", celdas[0])
        if m2:
            filas.append(m2.group(1))
    return filas


def evaluar_clave(raiz: Path) -> Reporte:
    rep = Reporte("clave")
    try:
        candidato, _, _ = arbol_candidato(raiz)
    except ArbolInvalido as e:
        rep.hallazgo(str(e))
        return rep
    en_skills = [p for p in candidato if p.startswith("skills/")]
    rep.nota(f"alcance: {len(en_skills)} archivos rastreados bajo skills/")

    # (a) cero construcciones de la clave retirada, EN CUALQUIER SEDE (regla 5 del docstring).
    # (b) el símbolo suelto solo dentro de las sedes permitidas.
    # (c) cada garantía de la allowlist realizada al menos una vez, contada por separado.
    realizadas: dict[str, int] = {ident: 0 for ident, _, _, _ in GARANTIAS}
    en_sede: dict[str, int] = {s: 0 for s in SEDES_PERMITIDAS}
    for rel in en_skills:
        texto = leer(raiz, rel)
        if texto is None:
            rep.hallazgo(f"{rel} · ilegible")
            continue
        sedes = sedes_por_linea(rel, texto)
        for n, linea in enumerate(texto.splitlines(), 1):
            sede = sedes.get(n, rel)
            canonica = sede_canonica(sede)
            permitida = canonica is not None
            for etiqueta, patron in CONSTRUCCIONES:
                if patron.search(linea):
                    donde = "dentro de una sede permitida" if permitida else "fuera de la allowlist"
                    rep.hallazgo(f"{rel}:{n} · construcción `{etiqueta}` {donde} — la allowlist "
                                 f"permite el campo, no la clave de configuración · sede «{sede}» "
                                 f"· {linea.strip()[:100]}")
            if SIMBOLO.search(linea):
                if not permitida:
                    rep.hallazgo(f"{rel}:{n} · aparición del símbolo fuera de la allowlist "
                                 f"· sede «{sede}» · {linea.strip()[:90]}")
                else:
                    en_sede[canonica] += 1
            for ident, _, sede_esperada, patron in GARANTIAS:
                if sede_esperada is not None and norm(sede_esperada) != norm(sede):
                    continue
                if patron.search(linea):
                    realizadas[ident] += 1
    for ident, descripcion, _, _ in GARANTIAS:
        if realizadas[ident] == 0:
            rep.hallazgo(f"{ident} · garantía de la allowlist sin ninguna realización: "
                         f"{descripcion}")
    rep.nota("realizaciones por garantía: "
             + " · ".join(f"{i}={realizadas[i]}" for i, _, _, _ in GARANTIAS))
    rep.nota("símbolo por sede permitida: " + " · ".join(f"{s}={c}" for s, c in en_sede.items()))

    # A3 se comprueba por estructura: su tabla nombra las vías por valor de enum, no por el símbolo.
    copias = [p for p in en_skills if Path(p).name == CONTRATO]
    if not copias:
        rep.hallazgo("A3 · no hay ninguna copia del contrato en el árbol candidato")
    # Conjunto, no lista: reordenar las filas de la tabla no es una violación del criterio, y
    # compararlas por posición daría un rojo por un cambio editorial. Los duplicados se miran aparte,
    # porque un conjunto los colapsa y "sobra tanto como falta" también vale acá.
    esperado = set(VIAS_SUPERVIVIENTES)
    sobrantes: dict[str, list[str]] = {}
    for rel in copias:
        texto = leer(raiz, rel) or ""
        filas = filas_tabla_fuentes(texto)
        if set(filas) != esperado or len(filas) != len(set(filas)):
            sobrantes[rel] = filas
    if sobrantes:
        muestra = next(iter(sobrantes.values()))
        rep.hallazgo(f"A3 · la tabla de «{SECCION_FUENTES}» no lista exactamente "
                     f"{sorted(esperado)} (sin repetidos) en {len(sobrantes)}/{len(copias)} copias "
                     f"— por ejemplo {muestra}")

    # (c) el bloque de config del orquestador desaparece entero, no solo su clave.
    for rel in SEDES_BLOQUE_CONFIG:
        if rel not in en_skills:
            continue
        texto = leer(raiz, rel) or ""
        for n, linea in enumerate(texto.splitlines(), 1):
            if BLOQUE_CONFIG.match(linea):
                rep.hallazgo(f"{rel}:{n} · el bloque de config sigue declarado en el orquestador")
    return rep


# ---------------------------------------------------------------------------
# --adaptadores (AC-3)
# ---------------------------------------------------------------------------
def evaluar_adaptadores(raiz: Path) -> Reporte:
    rep = Reporte("adaptadores")
    # El árbol primero: si no se puede construir, las tres rutas "no existen" por vacuidad y el modo
    # daría verde diciendo justo lo contrario de lo que sabe.
    try:
        candidato, _, _ = arbol_candidato(raiz)
    except ArbolInvalido as e:
        rep.hallazgo(str(e))
        return rep
    for rel in ADAPTADORES:
        if (raiz / rel).exists():
            rep.hallazgo(f"{rel} · la ruta todavía existe")
    # La misma exclusión que `--ausencia`, por el mismo motivo: una transcripción capturada que
    # nombra al adaptador es un DATO, no una referencia del repositorio. Que este modo no la
    # aplicara era un hueco que solo la suerte mantenía cerrado —ninguna evidencia excluida había
    # nombrado al adaptador todavía—, y se abrió en cuanto una lo hizo.
    evidencia = [rel for rel in candidato if es_evidencia_capturada(rel)]
    candidato = [rel for rel in candidato if not es_evidencia_capturada(rel)]
    if evidencia:
        rep.nota(f"evidencia capturada excluida del escaneo: {len(evidencia)} archivos bajo "
                 f"{', '.join(EVIDENCIA_EXCLUIDA)} — transcripción de sesiones medidas, no prosa "
                 f"del repositorio, y con sus bytes hasheados en el sello de cada corrida")
    patron = dict(TERMINOS)["nombre-del-adaptador"]
    exentas = 0
    for rel in candidato:
        if patron.search(rel):
            rep.hallazgo(f"{rel} · path · referencia al adaptador")
        texto = leer(raiz, rel)
        if texto is None:
            rep.hallazgo(f"{rel} · ilegible")
            continue
        for n, linea in enumerate(texto.splitlines(), 1):
            if ocurrencias_reportables(rel, linea, patron):
                rep.hallazgo(f"{rel}:{n} · referencia al adaptador · {linea.strip()[:110]}")
            elif patron.search(linea):
                exentas += 1
    if exentas:
        rep.nota(f"identificadores del corpus exentos: {exentas} ocurrencias dentro de una cadena "
                 "JSON cuyo contenido completo es una ruta del corpus — nombran un flujo de "
                 "`.plans/`, no referencian el adaptador")
    rep.nota(f"las 3 rutas de adaptador resueltas contra {raiz} "
             f"(árbol candidato: {len(candidato)} archivos)")
    return rep


# ---------------------------------------------------------------------------
# --drenaje (AC-14b)
# ---------------------------------------------------------------------------
def evaluar_drenaje(sobres) -> tuple[bool, bool, set[str]]:
    """(permitir_retiro, permitir_relanzamiento, rutas_reservadas)"""
    rutas_reservadas: set[str] = set()
    retiro_bloqueado = False
    for sobre in sobres:
        if not isinstance(sobre, dict):
            continue
        intentos_vigentes: list[dict] = []
        workers = sobre.get("workers", [])
        if isinstance(workers, list):
            for worker in workers:
                if not isinstance(worker, dict):
                    continue
                intentos = worker.get("attempts", [])
                if not isinstance(intentos, list) or not intentos:
                    continue
                vigente = next((intento for intento in reversed(intentos)
                                 if isinstance(intento, dict)
                                 and intento.get("harvested") is False), None)
                if vigente is not None:
                    intentos_vigentes.append(vigente)
        usa_via_retirada = sobre.get("transport") == _NOM or any(
            intento.get("transport") == _NOM for intento in intentos_vigentes)
        if not usa_via_retirada:
            continue
        retiro_bloqueado = True
        for intento in intentos_vigentes:
            output = intento.get("output")
            if isinstance(output, str) and output:
                rutas_reservadas.add(output)
    permitir = not retiro_bloqueado
    return permitir, permitir, rutas_reservadas


def evaluar_drenaje_en_raiz(raiz: Path) -> Reporte:
    rep = Reporte("drenaje")
    directorio = raiz / ".cross-model" / "active"
    rutas = sorted(directorio.glob("**/*.json")) if directorio.is_dir() else []
    sobres: list[dict] = []
    for ruta in rutas:
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as e:
            rep.hallazgo(f"{ruta.relative_to(raiz)} · sobre ilegible: {e}")
            continue
        if not isinstance(datos, dict):
            rep.hallazgo(f"{ruta.relative_to(raiz)} · la raíz JSON no es un objeto")
            continue
        sobres.append(datos)
    permitir_retiro, permitir_relanzamiento, reservadas = evaluar_drenaje(sobres)
    rep.nota(f"barrido real: {len(rutas)} sobres JSON bajo .cross-model/active/")
    rep.nota(f"rutas reservadas: {len(reservadas)}")
    if not permitir_retiro:
        rep.hallazgo("precondición de drenaje incumplida: retiro bloqueado")
    if not permitir_relanzamiento:
        rep.hallazgo("relanzamiento bloqueado mientras el intento vigente pueda escribir")
    for ruta in sorted(reservadas):
        rep.hallazgo(f"ruta reservada: {ruta}")
    return rep


# ---------------------------------------------------------------------------
# --vocabulario (AC-12)
# ---------------------------------------------------------------------------
def cuerpo_marcado(texto: str, nombre: str) -> str | None:
    """Contenido entre los marcadores exactos de un bloque, sin incluirlos."""
    lineas = texto.splitlines()
    inicio = f"# @bloque:{nombre}"
    fin = f"# @fin:{nombre}"
    if lineas.count(inicio) != 1 or lineas.count(fin) != 1:
        return None
    i, j = lineas.index(inicio), lineas.index(fin)
    if j <= i:
        return None
    return "\n".join(lineas[i + 1:j])


def vocabulario_documental(texto: str) -> tuple[set[str], int]:
    """Enum de escritura en la fila `transport` de la sección «Los campos»."""
    sedes = sedes_por_linea(REFERENCIA_MANIFEST, texto)
    valores: set[str] = set()
    filas = 0
    sede_esperada = f"{REFERENCIA_MANIFEST}§Los campos"
    for n, linea in enumerate(texto.splitlines(), 1):
        if norm(sedes.get(n, "")) != norm(sede_esperada):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) < 2 or celdas[0] != "`transport`":
            continue
        filas += 1
        valores.update(re.findall(r"`([^`]+)`", celdas[1]))
    return valores, filas


def vocabulario_posix(cuerpo: str) -> tuple[set[str], int]:
    asignaciones = re.findall(r'^\s*trans="([^"]*)"', cuerpo, re.M)
    return {valor for asignacion in asignaciones for valor in asignacion.split()}, len(asignaciones)


def vocabulario_powershell(cuerpo: str) -> tuple[set[str], int]:
    asignaciones = re.findall(r"\$trans\s*=\s*@\(([^)]*)\)", cuerpo)
    return ({valor for asignacion in asignaciones
             for valor in re.findall(r"'([^']+)'", asignacion)}, len(asignaciones))


def evaluar_vocabulario(raiz: Path) -> Reporte:
    rep = Reporte("vocabulario")
    texto = leer(raiz, REFERENCIA_MANIFEST)
    if texto is None:
        rep.hallazgo(f"{REFERENCIA_MANIFEST} · ilegible")
        return rep

    esperado = set(VIAS_SUPERVIVIENTES)
    documental, filas = vocabulario_documental(texto)
    posix_cuerpo = cuerpo_marcado(texto, "manifest-valido")
    ps_cuerpo = cuerpo_marcado(texto, "manifest-valido-ps")
    if posix_cuerpo is None:
        rep.hallazgo("cuerpo POSIX `manifest-valido` ausente o con marcadores ambiguos")
        posix, asignaciones_posix = set(), 0
    else:
        posix, asignaciones_posix = vocabulario_posix(posix_cuerpo)
    if ps_cuerpo is None:
        rep.hallazgo("cuerpo PowerShell `manifest-valido-ps` ausente o con marcadores ambiguos")
        powershell, asignaciones_ps = set(), 0
    else:
        powershell, asignaciones_ps = vocabulario_powershell(ps_cuerpo)

    fuentes = (
        ("documental", documental, filas),
        ("POSIX", posix, asignaciones_posix),
        ("PowerShell", powershell, asignaciones_ps),
    )
    for nombre, observado, realizaciones in fuentes:
        rep.nota(f"{nombre}: {sorted(observado)} · realizaciones={realizaciones}")
        if observado != esperado:
            rep.hallazgo(f"vocabulario {nombre}: observado={sorted(observado)}; "
                         f"esperado={sorted(esperado)}")
        if realizaciones == 0:
            rep.hallazgo(f"vocabulario {nombre}: el lector no extrajo ninguna realización")

    datos_casos = leer(raiz, CASOS_MANIFEST)
    if datos_casos is None:
        rep.hallazgo(f"{CASOS_MANIFEST} · ilegible")
        return rep
    try:
        raiz_casos = json.loads(datos_casos)
    except json.JSONDecodeError as e:
        rep.hallazgo(f"{CASOS_MANIFEST} · JSON inválido: {e}")
        return rep
    casos = raiz_casos.get("casos", []) if isinstance(raiz_casos, dict) else []
    invalidos = [caso for caso in casos if isinstance(caso, dict)
                 and caso.get("nombre") == "transport-bogus"]
    if len(invalidos) != 1:
        rep.hallazgo("caso `transport-bogus`: se esperaba una única declaración")
        return rep
    caso = invalidos[0]
    contrato_caso = (caso.get("particion"), caso.get("clase_esperada"), caso.get("objetivo"),
                     caso.get("fixture"))
    esperado_caso = ("invalido", "rechazo", "valor-fuera-de-vocabulario", "transport-bogus")
    if contrato_caso != esperado_caso:
        rep.hallazgo(f"caso `transport-bogus`: contrato={contrato_caso}; "
                     f"esperado={esperado_caso}")
        return rep
    rel_fixture = f"{FIXTURES_MANIFEST}/{caso['fixture']}/manifest.json"
    texto_fixture = leer(raiz, rel_fixture)
    try:
        fixture = json.loads(texto_fixture) if texto_fixture is not None else None
    except json.JSONDecodeError as e:
        rep.hallazgo(f"{rel_fixture} · JSON inválido: {e}")
        return rep
    valor_invalido = fixture.get("transport") if isinstance(fixture, dict) else None
    if not isinstance(valor_invalido, str) or not valor_invalido or valor_invalido in esperado:
        rep.hallazgo(f"caso `transport-bogus`: el fixture no aporta un valor ajeno al vocabulario "
                     f"vigente (observado={valor_invalido!r})")
    else:
        rep.nota(f"caso `transport-bogus`: rechazo declarado para valor ajeno `{valor_invalido}`")
    return rep


# ---------------------------------------------------------------------------
# --vias (AC-15)
# ---------------------------------------------------------------------------
def _inventario_vias() -> tuple[set[str], set[str]]:
    vias = set(MATRIZ_VIAS)
    garantias = {garantia for celdas in MATRIZ_VIAS.values() for garantia in celdas}
    return vias, garantias


def evaluar_vias(raiz: Path) -> Reporte:
    rep = Reporte("vias")
    vias, garantias_presentes = _inventario_vias()
    esperado_vias = set(VIAS_SUPERVIVIENTES)
    esperado_garantias = set(GARANTIAS_VIAS)
    if not MATRIZ_VIAS or not vias or not garantias_presentes:
        rep.hallazgo("matriz vacía: ninguna vía o garantía aplicable fue declarada")
        return rep
    if vias != esperado_vias:
        rep.hallazgo(f"matriz de vías no cerrada: observado={sorted(vias)} · "
                     f"esperado={sorted(esperado_vias)}")
    if garantias_presentes != esperado_garantias:
        rep.hallazgo(f"matriz de garantías no cerrada: observado={sorted(garantias_presentes)} · "
                     f"esperado={sorted(esperado_garantias)}")

    base_ref = referencia_base_docs(raiz)
    rep.nota("matriz cerrada anclada a " + (CHANGE_BASE_COMMIT if base_ref == CHANGE_BASE_COMMIT
                                             else f"fixture temporal derivado de "
                                                  f"{CHANGE_BASE_COMMIT}"))
    actuales: dict[str, str | None] = {}
    bases: dict[str, str | None] = {}

    def textos(rel: str) -> tuple[str | None, str | None]:
        if rel not in actuales:
            actuales[rel] = leer(raiz, rel)
        if rel not in bases:
            try:
                bases[rel] = _git(raiz, "show", f"{base_ref}:{rel}")
            except ArbolInvalido as e:
                bases[rel] = None
                rep.hallazgo(f"{rel} · no se pudo leer el oráculo de vías: {e}")
        return bases[rel], actuales[rel]

    filas_aplicables = 0
    filas_no_aplica = 0
    for via in VIAS_SUPERVIVIENTES:
        celdas = MATRIZ_VIAS.get(via, {})
        for garantia in GARANTIAS_VIAS:
            construcciones = celdas.get(garantia)
            if construcciones is None:
                filas_no_aplica += 1
                rep.nota(f"{via} | {garantia} | N/A declarado")
                continue
            filas_aplicables += 1
            if not construcciones:
                rep.hallazgo(f"{via} | {garantia} · extracción declarada sin construcciones")
                continue
            total_base = 0
            total_actual = 0
            detalles: list[str] = []
            for rel, sede, forma, exacta in construcciones:
                base, actual = textos(rel)
                base_n = base.count(exacta) if base is not None else 0
                actual_n = actual.count(exacta) if actual is not None else 0
                total_base += base_n
                total_actual += actual_n
                detalles.append(f"{rel}§{sede} · {forma} · {base_n}→{actual_n}")
                if base_n == 0:
                    rep.hallazgo(f"{via} | {garantia} | {rel}§{sede} · extracción del oráculo "
                                 f"vino vacía para {forma}")
                if actual_n == 0:
                    rep.hallazgo(f"{via} | {garantia} | {rel}§{sede} · cero realizaciones "
                                 f"actuales de {forma}")
                if base_n != actual_n:
                    rep.hallazgo(f"{via} | {garantia} | {rel}§{sede} · cardinalidad "
                                 f"base={base_n} actual={actual_n} · {forma}")
            if total_base == 0:
                rep.hallazgo(f"{via} | {garantia} · extracción agregada del oráculo vino vacía")
            if total_actual == 0:
                rep.hallazgo(f"{via} | {garantia} · extracción agregada actual vino vacía")
            rep.nota(f"{via} | {garantia} | base={total_base} actual={total_actual} | "
                     + " ; ".join(detalles))
    if filas_aplicables == 0:
        rep.hallazgo("matriz vacía: cero filas de garantías aplicables")
    rep.nota(f"filas: aplicables={filas_aplicables} · N/A declaradas={filas_no_aplica}")
    return rep


def _agregar_fixture_vias(raiz: Path) -> None:
    """Materializa todas las construcciones de la matriz en el corpus sintético."""
    por_ruta: dict[str, list[str]] = {}
    vistos: set[tuple[str, str]] = set()
    for celdas in MATRIZ_VIAS.values():
        for construcciones in celdas.values():
            for rel, _, _, exacta in construcciones:
                clave = (rel, exacta)
                if clave in vistos:
                    continue
                vistos.add(clave)
                por_ruta.setdefault(rel, []).append(exacta)
    for rel, construcciones in por_ruta.items():
        ruta = raiz / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        previo = ruta.read_text(encoding="utf-8") if ruta.exists() else f"# Fixture de {rel}\n"
        ruta.write_text(previo.rstrip() + "\n\n" + "\n\n".join(construcciones) + "\n",
                        encoding="utf-8")


# ---------------------------------------------------------------------------
# --autotest (regla 6 del docstring)
#
# El corpus es sintético y vive en un temporal fuera del árbol: describe el estado **posterior** al
# retiro, con las cuatro construcciones que sobreviven y ninguna de las prohibidas. Los mutantes lo
# rompen de a uno. Los que necesitan los literales prohibidos los arman por concatenación desde los
# fragmentos de arriba, igual que el resto del archivo, y el temporal se borra al terminar.
# ---------------------------------------------------------------------------
SKILLS_CONTRATO = ("co-explore", "cross-review", "cross-implement", "sdd-flow", "sdd-orchestrator",
                   "sdd-pr-feedback", "bitbucket-code-review")

_CONTRATO_VERDE = """# Corridas delegadas en vuelo

## Los campos del sobre

| campo | qué guarda |
|---|---|
| `owner` | el conductor propietario |
| `transport` | la vía por la que viaja la corrida, **derivada** de los intentos vigentes |
| `proxima_accion` | qué hacer al recuperar el control, o `null` |

**`transport` en la raíz es el único campo derivado del sobre.** Su valor no se escribe por decisión
propia: es el valor **común** a los intentos vigentes de todos los workers, o `mixto` cuando difieren.

## Los campos por intento

| campo | qué guarda |
|---|---|
| `worker` | quién corre este intento |
| `transport` | la vía por la que viaja **este** intento |

## Varios workers en una corrida

Dos workers pueden resolver a fuentes distintas al mismo tiempo, y el `transport` de la raíz vale
`mixto` justamente para no elegir una de las dos y mentir sobre la otra.

## Fuente por transporte

| vía | fuente | nota |
|---|---|---|
| `subagent` | `envelope` | la salida vuelve por el propio despacho |
| `cli-exec` | `archivo` | se cosecha del disco cuando el proceso termina |
| `cli-resume` | `archivo+proceso` | ídem, sobre una sesión reanudada |
"""

_REFERENCIA_VERDE = """# cross-review — Referencia

## El manifest de corrida

### El archivo

```json
{
  "skill": "co-explore",
  "mode": "explore",
  "transport": "cli-exec",
  "outcome": "completed"
}
```

### Los campos

| campo | qué guarda | fuente |
|---|---|---|
| `mode` | el modo de esta corrida | contrato de invocación |
| `transport` | la vía efectiva: `subagent` · `cli-exec` · `cli-resume` | vía resuelta al lanzar |

**`transport` es el del lanzamiento.** Una corrida que arranca con `cli-exec` y reanuda su sesión en
las rondas siguientes sigue siendo `cli-exec`.

### Las causas de la indisponibilidad, y la que no lo es

3. **`transport` guarda la vía que efectivamente corrió**, no la que se intentó.

### El vocabulario es prestado, nunca propio

Cada término ya existe en la skill que lo produce: el manifest los **serializa**, no los define.

### La suma por vocabulario

```sh
# @bloque:manifest-valido
trans="subagent cli-exec cli-resume"
for par in "transport:$trans"; do :; done
# @fin:manifest-valido
```

```powershell
# @bloque:manifest-valido-ps
$trans = @('subagent','cli-exec','cli-resume')
foreach ($par in @(@('transport',$trans))) { }
# @fin:manifest-valido-ps
```
"""

_ORQUESTADOR_VERDE = """# sdd-orchestrator — Referencia

## Esquema del manifest

```yaml
objetivo: retirar una vía
repos:
  - path: apps/web
    branch: feature/x
```
"""

_EJEMPLO_VERDE = """# manifest de ejemplo

```yaml
objetivo: ejemplo
repos:
  - path: apps/web
```
"""

_NOTA_VERDE = """# Nota

Documento de relleno del corpus: existe para que los mutantes tengan dónde escribir sin tocar el
contrato ni la referencia.
"""

_DOC_PORTACION_VERDE = """# Portación CLI-first

## Catálogo de ideas portables

### 1. Coordinador puro

Contenido vigente.

### 2. Contrato congelado

Contenido vigente.
"""

_DOC_PLAN_VERDE = """# Plan de ejemplo

## Estructura de archivos

| Archivo | Responsabilidad | Acción |
|---|---|---|
| `.plans/ejemplo/guardas/comun.sh` | primitivas compartidas | crear |
| `skills/sdd-flow/reference.md` | esquema | modificar |

### Task 1: Andamiaje

- [ ] **Step 1: Crear las primitivas**

Las guardas G1 y G2 deben quedar verdes.

### Task 2: Control por mutación

| # | Guarda | Mutación | Esperado |
|---|---|---|---|
| 1 | G1 | borrar una entrada | RED |
| 2 | G2 | cambiar un enum | RED |
"""


def corpus_verde(raiz: Path) -> None:
    """Escribe el árbol mínimo donde el retiro está completo: todos los modos implementados pasan."""
    for skill in SKILLS_CONTRATO:
        d = raiz / "skills" / skill
        d.mkdir(parents=True, exist_ok=True)
        (d / CONTRATO).write_text(_CONTRATO_VERDE, encoding="utf-8")
    (raiz / REFERENCIA_MANIFEST).write_text(_REFERENCIA_VERDE, encoding="utf-8")
    casos = raiz / CASOS_MANIFEST
    casos.parent.mkdir(parents=True, exist_ok=True)
    casos.write_text(json.dumps({"casos": [{
        "nombre": "transport-bogus",
        "particion": "invalido",
        "clase_esperada": "rechazo",
        "objetivo": "valor-fuera-de-vocabulario",
        "fixture": "transport-bogus",
    }]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fixture = raiz / FIXTURES_MANIFEST / "transport-bogus" / "manifest.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps({"transport": "bogus"}, indent=2) + "\n", encoding="utf-8")
    (raiz / "skills/sdd-orchestrator/reference.md").write_text(_ORQUESTADOR_VERDE, encoding="utf-8")
    (raiz / "skills/sdd-orchestrator/manifest-ejemplo.md").write_text(_EJEMPLO_VERDE,
                                                                     encoding="utf-8")
    (raiz / "docs").mkdir(parents=True, exist_ok=True)
    (raiz / "docs/nota.md").write_text(_NOTA_VERDE, encoding="utf-8")
    for rel, texto in zip(DOCS_DEPURADOS, (_DOC_PORTACION_VERDE, _DOC_PLAN_VERDE)):
        ruta = raiz / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8")
    _agregar_fixture_vias(raiz)


def _preparar_repo(raiz: Path) -> None:
    """`git init` + `add`: el árbol candidato se lee del índice, así que sin esto no hay entrada."""
    for args in (("init", "-q"), ("add", "-A", "-f")):
        subprocess.run(["git", *args], cwd=str(raiz), capture_output=True, text=True, check=True)


def _sellar_base_docs(raiz: Path) -> None:
    """Crea el oráculo privado del corpus antes de aplicar una mutación."""
    _preparar_repo(raiz)
    subprocess.run([
        "git", "-c", "user.name=Verifier", "-c", "user.email=verifier@example.invalid",
        "commit", "-qm", "docs base",
    ], cwd=str(raiz), capture_output=True, text=True, check=True)
    subprocess.run(["git", "update-ref", REF_BASE_DOCS_TEMPORAL, "HEAD"], cwd=str(raiz),
                   capture_output=True, text=True, check=True)


def _sustituir_en_contrato(viejo: str, nuevo: str):
    """Aplica la sustitución a las SIETE copias: mutar una sola deja las otras seis realizando la
    garantía, y el mutante daría verde por replicación en vez de por corrección."""
    def mutar(raiz: Path) -> None:
        for skill in SKILLS_CONTRATO:
            ruta = raiz / "skills" / skill / CONTRATO
            texto = ruta.read_text(encoding="utf-8")
            if viejo not in texto:
                raise AssertionError(f"mutación inaplicable: patrón ausente en {ruta}")
            ruta.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")
    return mutar


def _sustituir(rel: str, viejo: str, nuevo: str):
    def mutar(raiz: Path) -> None:
        ruta = raiz / rel
        texto = ruta.read_text(encoding="utf-8")
        if viejo not in texto:
            raise AssertionError(f"mutación inaplicable: patrón ausente en {rel}")
        ruta.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")
    return mutar


def _crear(rel: str, texto: str):
    def mutar(raiz: Path) -> None:
        destino = raiz / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return mutar


_RUTA_SOBRE_DRENAJE = ".cross-model/active/cross-review/drain-1.json"
_SOBRE_DRENAJE_TPL = """{{
  "run_id": "drain-1",
  "transport": "{transport}",
  "workers": [{{
    "name": "reviewer-a",
    "attempts": [{{
      "attempt_id": "a1",
      "transport": "{transport}",
      "output": "outputs/reviewer-a.json",
      "harvested": false
    }}]
  }}]
}}
"""


def _con_corpus(mutacion):
    def preparar(raiz: Path) -> None:
        corpus_verde(raiz)
        _sellar_base_docs(raiz)
        mutacion(raiz)
        _preparar_repo(raiz)
    return preparar


# Las tres construcciones prohibidas, inyectadas juntas DENTRO de una sede permitida. Es el falso
# verde confirmado: el chequeo estaba condicionado a que la sede no estuviera en la allowlist, así
# que cualquier sede permitida era un escondite para las tres.
_INYECCION = """
La clave `cross_model.transport` vuelve a nombrarse acá.

```yaml
transport: cli-exec
```

En el mapa `overrides` del handoff: `transport: null`.
"""

# Controles positivos adicionales: variantes del corpus que **siguen** siendo el estado retirado y
# por lo tanto deben quedar verdes. Van acá porque un mutante no las cubre: lo que estas variantes
# cazan es el rojo falso —el verificador rechazando algo legítimo—, y esa clase de defecto no se
# detecta agregando otro rojo, solo agregando un verde que tenga que seguir siéndolo.
VARIANTES_VERDES = [
    ("tabla de fuentes reordenada",
     _sustituir_en_contrato(
         "| `subagent` | `envelope` | la salida vuelve por el propio despacho |\n"
         "| `cli-exec` | `archivo` | se cosecha del disco cuando el proceso termina |\n"
         "| `cli-resume` | `archivo+proceso` | ídem, sobre una sesión reanudada |",
         "| `cli-resume` | `archivo+proceso` | ídem, sobre una sesión reanudada |\n"
         "| `cli-exec` | `archivo` | se cosecha del disco cuando el proceso termina |\n"
         "| `subagent` | `envelope` | la salida vuelve por el propio despacho |")),
    ("ejemplo JSON del sobre con el campo entre comillas",
     _sustituir_en_contrato("## Los campos por intento",
                            '```json\n{\n  "transport": "cli-exec"\n}\n```\n\n'
                            "## Los campos por intento")),
    ("intento activo por una vía vigente",
     _crear(_RUTA_SOBRE_DRENAJE, _SOBRE_DRENAJE_TPL.format(transport="cli-exec"))),
    # Ejerce la exclusión de evidencia, **una variante por prefijo**. Sin ellas la exclusión sería
    # código muerto: una que ningún caso atraviesa daría verde por no aplicarse nunca, y el verde
    # parecería cobertura. Se derivan de `EVIDENCIA_EXCLUIDA` y no se escriben a mano, así que un
    # prefijo agregado sin control es imposible — que es como entró el segundo.
    *[(f"la vía y el adaptador nombrados dentro de una transcripción capturada bajo {prefijo}",
       _crear(prefijo + "corrida/salida-del-worker.txt",
              "El worker corrió `" + _NOM + "-native-audit` leyendo `transporte-" + _NOM
              + ".md` y devolvió su reporte.\n"))
      for prefijo in EVIDENCIA_EXCLUIDA],
    # Ejercen el criterio de identidad del corpus, **una variante por forma real**. Sin ellas el
    # criterio sería un agujero que ningún caso atraviesa: daría verde por no aplicarse nunca.
    ("identificador del corpus como valor de campo",
     _crear("scripts/manifiesto-de-corpus.json",
            '{\n  "flujo": "archived/' + _NOM + '-transporte-skills"\n}\n')),
    ("identificador del corpus como ruta canónica de artefacto",
     _crear("scripts/manifiesto-de-rutas.json",
            '{\n  "ruta": ".plans/archived/' + _NOM + '-transporte-skills/spec.md"\n}\n')),
    ("identificador del corpus en su forma aplanada, y con el adaptador dentro",
     _crear("scripts/manifiesto-de-evidencia.json",
            '{\n  "evidencia": "salidas/archived__transporte-' + _NOM + '-flujo.jsonl"\n}\n')),
]

MUTANTES = [
    # El simétrico de las variantes de identidad: cada forma que el criterio NO exime, con su
    # mutante. Sin ellos, aflojar el predicado —quitarle el ancla al corpus, admitir espacios,
    # extenderlo fuera de los `.json`— abriría un agujero que ningún caso vería.
    ("término como valor de un token sin ruta del corpus", ["ausencia"],
     ["nombre-de-la-herramienta", "config-suelta.json"],
     _con_corpus(_crear("scripts/config-suelta.json",
                        '{\n  "transport": "' + _NOM + '"\n}\n'))),
    ("término en una ruta fuera del corpus", ["ausencia", "adaptadores"],
     ["rutas-ajenas.json"],
     _con_corpus(_crear("scripts/rutas-ajenas.json",
                        '{\n  "ruta": "skills/co-explore/transporte-' + _NOM + '.md"\n}\n'))),
    ("término en prosa dentro de un valor JSON entrecomillado", ["ausencia"],
     ["nombre-de-la-herramienta", "motivos.json"],
     _con_corpus(_crear("scripts/motivos.json",
                        '{\n  "motivo": "el ' + _NOM + ' quedó retirado"\n}\n'))),
    ("el mismo identificador del corpus, pero fuera de un `.json`", ["ausencia"],
     ["nombre-de-la-herramienta", "nota-suelta.md"],
     _con_corpus(_crear("docs/nota-suelta.md",
                        '"archived/' + _NOM + '-transporte-skills"\n'))),
    ("término de la vía reintroducido en el contenido", ["ausencia"],
     ["nombre-de-la-herramienta"],
     _con_corpus(_sustituir("docs/nota.md", "Documento de relleno",
                            "La vía retirada se llamaba " + _NOM + ". Documento de relleno"))),
    ("término de la vía en el path de un archivo nuevo", ["ausencia"],
     ["· path ·", "alojamiento-como-palabra"],
     _con_corpus(_crear(f"docs/{_ALO}s-propios.md", "# Nota suelta\n"))),
    # El simétrico de las variantes verdes: la exclusión es por prefijo terminado en `/`, así que un
    # directorio de nombre parecido NO queda exento. Sin estos mutantes, cambiar el prefijo por un
    # `in` o quitarle la barra abriría un agujero que ningún caso vería. También se derivan, y
    # cubren **los dos** modos que ahora aplican la exclusión: un arreglo que la agregara a uno
    # solo dejaría el otro escaneando lo que el primero exime.
    *[(f"la vía nombrada en un directorio parecido a {prefijo}", ["ausencia"],
       ["nombre-de-la-herramienta", prefijo.rstrip("/").rsplit("/", 1)[-1] + "-otra"],
       _con_corpus(_crear(prefijo.rstrip("/") + "-otra/salida.txt",
                          "Reporte suelto sobre " + _NOM + ".\n")))
      for prefijo in EVIDENCIA_EXCLUIDA],
    *[(f"el adaptador nombrado en un directorio parecido a {prefijo}", ["adaptadores"],
       ["referencia al adaptador", prefijo.rstrip("/").rsplit("/", 1)[-1] + "-otra"],
       _con_corpus(_crear(prefijo.rstrip("/") + "-otra/adaptador.txt",
                          "Reporte suelto sobre `transporte-" + _NOM + ".md`.\n")))
      for prefijo in EVIDENCIA_EXCLUIDA],
    ("construcción prohibida dentro de una sede permitida", ["clave"],
     ["clave-de-config", "clave-yaml-al-inicio-de-linea", "clave-del-mapa-overrides",
      "dentro de una sede permitida"],
     _con_corpus(_sustituir_en_contrato("## Los campos por intento",
                                        _INYECCION + "\n## Los campos por intento"))),
    ("símbolo suelto fuera de toda sede permitida", ["clave"],
     ["fuera de la allowlist", "Fuente por transporte"],
     _con_corpus(_sustituir_en_contrato("| `subagent` | `envelope` |",
                                        "El campo `transport` de la fila.\n\n"
                                        "| `subagent` | `envelope` |"))),
    ("campo `transport` de la raíz borrado", ["clave"], ["A1a"],
     _con_corpus(_sustituir_en_contrato(
         "| `transport` | la vía por la que viaja la corrida, **derivada** de los intentos "
         "vigentes |\n", ""))),
    ("regla de derivación borrada, con la fila de la tabla intacta", ["clave"], ["A1b"],
     _con_corpus(_sustituir_en_contrato(
         "**`transport` en la raíz es el único campo derivado del sobre.** Su valor no se escribe "
         "por decisión\npropia: es el valor **común** a los intentos vigentes de todos los workers, "
         "o `mixto` cuando difieren.",
         # Conserva `mixto` a propósito: si la mutación se llevara las dos garantías, el rojo no
         # probaría que A1b se cuenta sola, que es justo lo que este mutante existe para probar.
         "El sobre se escribe entero de una vez, y el valor es `mixto` si difieren."))),
    ("valor `mixto` borrado de la regla, con la regla intacta", ["clave"], ["A1c"],
     _con_corpus(_sustituir_en_contrato(", o `mixto` cuando difieren", ""))),
    ("campo `transport` por intento borrado", ["clave"], ["A2"],
     _con_corpus(_sustituir_en_contrato(
         "| `transport` | la vía por la que viaja **este** intento |\n", ""))),
    ("campo del manifest de corrida borrado de su tabla", ["clave"], ["A4"],
     _con_corpus(_sustituir(
         REFERENCIA_MANIFEST,
         "| `transport` | la vía efectiva: `subagent` · `cli-exec` · `cli-resume` | vía resuelta al "
         "lanzar |\n", ""))),
    ("valor ausente en un solo lector de vocabulario", ["vocabulario"],
     ["documental", "cli-resume"],
     _con_corpus(_sustituir(
         REFERENCIA_MANIFEST,
         "| `transport` | la vía efectiva: `subagent` · `cli-exec` · `cli-resume` | vía resuelta al "
         "lanzar |",
         "| `transport` | la vía efectiva: `subagent` · `cli-exec` | vía resuelta al lanzar |"))),
    ("símbolo en otra sección del archivo más grande", ["clave"],
     ["fuera de la allowlist", "El vocabulario es prestado"],
     _con_corpus(_sustituir(REFERENCIA_MANIFEST,
                            "Cada término ya existe en la skill que lo produce",
                            "El valor de `transport` se toma prestado, y cada término ya existe en "
                            "la skill que lo produce"))),
    ("fila de más en la tabla de fuentes", ["clave"], ["Fuente por transporte"],
     _con_corpus(_sustituir_en_contrato("| `cli-resume` | `archivo+proceso` |",
                                        "| `cli-resume` | `archivo+proceso` |\n"
                                        "| `via-inventada` | `archivo` |"))),
    # La comparación por conjunto ignora repetidos, así que "sobra tanto como falta" necesita su
    # propio mutante: sin él, duplicar una fila pasaría por el conjunto sin que nada se ponga rojo.
    ("fila repetida en la tabla de fuentes", ["clave"], ["Fuente por transporte"],
     _con_corpus(_sustituir_en_contrato(
         "| `cli-exec` | `archivo` | se cosecha del disco cuando el proceso termina |",
         "| `cli-exec` | `archivo` | se cosecha del disco cuando el proceso termina |\n"
         "| `cli-exec` | `archivo` | repetida |"))),
    ("bloque de config reintroducido en el orquestador", ["clave"], ["bloque de config"],
     _con_corpus(_sustituir("skills/sdd-orchestrator/reference.md", "objetivo: retirar una vía",
                            "cross_model:\n  manifest: on\nobjetivo: retirar una vía"))),
    ("ruta de adaptador de vuelta en el árbol", ["adaptadores"], ["la ruta todavía existe"],
     _con_corpus(_crear(ADAPTADORES[0], "# Adaptador\n"))),
    ("referencia al adaptador en el contenido de otro archivo", ["adaptadores"],
     ["referencia al adaptador"],
     _con_corpus(_sustituir("docs/nota.md", "# Nota",
                            "# Nota\n\nVer `skills/cross-review/" + ADAPTADOR + "`."))),
    ("intento activo por la vía retirada", ["drenaje"],
     ["retiro bloqueado", "relanzamiento bloqueado", "outputs/reviewer-a.json"],
     _con_corpus(_crear(_RUTA_SOBRE_DRENAJE,
                        _SOBRE_DRENAJE_TPL.format(transport=_NOM)))),
    # Los dos falsos verdes de la construcción del árbol: sin ellos, `git` ausente o una raíz vacía
    # devolvían exit 0 con "árbol candidato: 0 archivos" en los tres modos.
    ("git ausente: la raíz no es un repositorio", ["ausencia", "clave", "adaptadores"],
     ["ls-files"], corpus_verde),
    ("árbol candidato vacío: repositorio sin ningún archivo",
     ["ausencia", "clave", "adaptadores"], ["vacío"], _preparar_repo),
]


def autotest_drenaje() -> list[str]:
    fallas: list[str] = []
    print("\n=== Drenaje: controles negativo y positivo sobre el mismo sobre efímero")
    with tempfile.TemporaryDirectory() as tmp:
        temporal = Path(tmp)
        ruta = temporal / "sobre.json"

        fixture_negativo = _SOBRE_DRENAJE_TPL.format(transport=_NOM)
        esperado_negativo = (False, False, {"outputs/reviewer-a.json"})
        ruta.write_text(fixture_negativo, encoding="utf-8")
        digest_antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
        observado_negativo = evaluar_drenaje([json.loads(ruta.read_text(encoding="utf-8"))])
        digest_despues = hashlib.sha256(ruta.read_bytes()).hexdigest()
        negativo_ok = observado_negativo == esperado_negativo
        inmutable_negativo = digest_antes == digest_despues
        print(f"[{'OK   ' if negativo_ok else 'FALLA'}] control negativo: "
              f"observado={observado_negativo}")
        print(f"[{'OK   ' if inmutable_negativo else 'FALLA'}] digest del corpus negativo: "
              f"{'sin cambios' if inmutable_negativo else 'CAMBIÓ'}")
        if not negativo_ok:
            fallas.append(f"drenaje negativo: esperado={esperado_negativo}, "
                          f"observado={observado_negativo}")
        if not inmutable_negativo:
            fallas.append("drenaje negativo: la evaluación modificó el corpus")

        fixture_positivo = _SOBRE_DRENAJE_TPL.format(transport="cli-exec")
        esperado_positivo = (True, True, set())
        ruta.write_text(fixture_positivo, encoding="utf-8")
        digest_antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
        observado_positivo = evaluar_drenaje([json.loads(ruta.read_text(encoding="utf-8"))])
        digest_despues = hashlib.sha256(ruta.read_bytes()).hexdigest()
        positivo_ok = observado_positivo == esperado_positivo
        inmutable_positivo = digest_antes == digest_despues
        print(f"[{'OK   ' if positivo_ok else 'FALLA'}] control positivo: "
              f"observado={observado_positivo}")
        print(f"[{'OK   ' if inmutable_positivo else 'FALLA'}] digest del corpus positivo: "
              f"{'sin cambios' if inmutable_positivo else 'CAMBIÓ'}")
        if not positivo_ok:
            fallas.append(f"drenaje positivo: esperado={esperado_positivo}, "
                          f"observado={observado_positivo}")
        if not inmutable_positivo:
            fallas.append("drenaje positivo: la evaluación modificó el corpus")
    eliminado = not temporal.exists()
    print(f"[{'OK   ' if eliminado else 'FALLA'}] temporal eliminado")
    if not eliminado:
        fallas.append(f"drenaje: el temporal sobrevivió en {temporal}")
    return fallas


def _sanear_para_fixture(texto: str) -> str:
    """Quita del contenido histórico los términos vedados antes de escribirlo en el temporal."""
    for _, patron in TERMINOS:
        texto = patron.sub("vía-retirada", texto)
    return texto


def autotest_docs() -> list[str]:
    """Borra una entrada ajena en una copia, exige rojo y comprueba la restauración."""
    fallas: list[str] = []
    print("\n=== Documentación: mutante reversible sobre una copia temporal")
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "copia"
        raiz.mkdir()
        actuales: dict[str, str] = {}
        for rel in DOCS_DEPURADOS:
            actual = leer(REPO, rel)
            if actual is None:
                fallas.append(f"documentación: no se pudo copiar {rel}")
                continue
            actuales[rel] = actual
            try:
                base = _git(REPO, "show", f"{CHANGE_BASE_COMMIT}:{rel}")
            except ArbolInvalido as e:
                fallas.append(f"documentación: no se pudo leer el oráculo de {rel}: {e}")
                continue
            ruta = raiz / rel
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(_sanear_para_fixture(base), encoding="utf-8")
        if len(actuales) == len(DOCS_DEPURADOS):
            _sellar_base_docs(raiz)
            for rel, texto in actuales.items():
                (raiz / rel).write_text(texto, encoding="utf-8")
            _preparar_repo(raiz)

            rel_mutado = DOCS_DEPURADOS[1]
            ruta_mutada = raiz / rel_mutado
            original = ruta_mutada.read_text(encoding="utf-8")
            aguja = ".plans/init-config-ejemplo/guardas/comun.sh"
            entradas = [linea for linea in original.splitlines()
                        if linea.startswith("|") and aguja in linea]
            if len(entradas) != 1:
                fallas.append(f"documentación: entrada mutante ambigua ({len(entradas)})")
            else:
                entrada = entradas[0]
                mutado = original.replace(entrada + "\n", "", 1)
                ruta_mutada.write_text(mutado, encoding="utf-8")
                comando = [sys.executable, str(Path(__file__).resolve()),
                           "--raiz", str(raiz), "--docs"]
                rojo = subprocess.run(comando, capture_output=True, text=True, check=False)
                print(f"entrada borrada: `{aguja}`")
                print("--- salida con la mutación")
                print(rojo.stdout.rstrip())
                print(f"exit_code: {rojo.returncode}")
                senales = ("entradas-de-catalogo no conservados", aguja)
                if rojo.returncode != 1 or any(s not in rojo.stdout for s in senales):
                    fallas.append("documentación: el mutante no falló por la entrada borrada")

                ruta_mutada.write_text(original, encoding="utf-8")
                restaurado = subprocess.run(comando, capture_output=True, text=True, check=False)
                print("--- salida restaurada")
                print(restaurado.stdout.rstrip())
                print(f"exit_code: {restaurado.returncode}")
                if restaurado.returncode != 0:
                    fallas.append("documentación: la copia restaurada no volvió a verde")
    eliminado = not raiz.exists()
    print(f"[{'OK   ' if eliminado else 'FALLA'}] temporal eliminado")
    if not eliminado:
        fallas.append(f"documentación: el temporal sobrevivió en {raiz}")
    return fallas


def autotest_docs_vacuidad() -> list[str]:
    """Neutraliza las cuatro dimensiones en ambos lados y exige que el oráculo vacío sea rojo."""
    fallas: list[str] = []
    print("\n=== Documentación: mutante de extracción vacía sobre un corpus temporal")
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "vacio"
        raiz.mkdir()
        neutralizado = "Contenido sin estructura documental extraíble.\n"
        for rel in DOCS_DEPURADOS:
            ruta = raiz / rel
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(neutralizado, encoding="utf-8")
        _sellar_base_docs(raiz)
        _preparar_repo(raiz)
        comando = [sys.executable, str(Path(__file__).resolve()),
                   "--raiz", str(raiz), "--docs"]
        rojo = subprocess.run(comando, capture_output=True, text=True, check=False)
        print("neutralización: headings, IDs de tarea, guardas y entradas de catálogo del "
              "oráculo y del actual")
        print("--- salida con la neutralización")
        print(rojo.stdout.rstrip())
        print(f"exit_code: {rojo.returncode}")
        senales = [f"{rel} · extracción del oráculo vino vacía" for rel in DOCS_DEPURADOS]
        if rojo.returncode != 1 or any(s not in rojo.stdout for s in senales):
            fallas.append("documentación: el oráculo vacío no produjo un hallazgo por documento")
    eliminado = not raiz.exists()
    print(f"[{'OK   ' if eliminado else 'FALLA'}] temporal vacío eliminado")
    if not eliminado:
        fallas.append(f"documentación: el temporal vacío sobrevivió en {raiz}")
    return fallas


def autotest_vias() -> list[str]:
    """Elimina una realización en una copia, exige rojo y descarta la copia al restaurar."""
    fallas: list[str] = []
    print("\n=== Vías: mutante reversible sobre una copia temporal")
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "copia"
        raiz.mkdir()
        rutas = sorted({rel for celdas in MATRIZ_VIAS.values()
                        for construcciones in celdas.values()
                        for rel, _, _, _ in construcciones})
        actuales: dict[str, str] = {}
        for rel in rutas:
            actual = leer(REPO, rel)
            if actual is None:
                fallas.append(f"vías: no se pudo copiar {rel}")
                continue
            actuales[rel] = actual
            try:
                base = _git(REPO, "show", f"{CHANGE_BASE_COMMIT}:{rel}")
            except ArbolInvalido as e:
                fallas.append(f"vías: no se pudo leer el oráculo de {rel}: {e}")
                continue
            ruta = raiz / rel
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(_sanear_para_fixture(base), encoding="utf-8")
        if len(actuales) == len(rutas):
            _sellar_base_docs(raiz)
            for rel, texto in actuales.items():
                (raiz / rel).write_text(_sanear_para_fixture(texto), encoding="utf-8")
            _preparar_repo(raiz)

            rel_mutado, sede, _, aguja = _PREFERENCIA_VIAS[-1]
            ruta_mutada = raiz / rel_mutado
            original = ruta_mutada.read_text(encoding="utf-8")
            if original.count(aguja) != 1:
                fallas.append(f"vías: garantía mutante ambigua ({original.count(aguja)})")
            else:
                mutado = original.replace(aguja + "\n", "", 1)
                if mutado == original:
                    mutado = original.replace(aguja, "", 1)
                ruta_mutada.write_text(mutado, encoding="utf-8")
                comando = [sys.executable, str(Path(__file__).resolve()),
                           "--raiz", str(raiz), "--vias"]
                rojo = subprocess.run(comando, capture_output=True, text=True, check=False)
                print("garantía eliminada: `preferencia-revision`")
                print(f"sede: `{rel_mutado}§{sede}`")
                print("--- salida con la mutación")
                print(rojo.stdout.rstrip())
                print(f"exit_code: {rojo.returncode}")
                senales = ("subagent | preferencia-revision", rel_mutado,
                           "cardinalidad base=1 actual=0")
                if rojo.returncode != 1 or any(s not in rojo.stdout for s in senales):
                    fallas.append("vías: el mutante no falló por la preferencia eliminada")

                ruta_mutada.write_text(original, encoding="utf-8")
                restaurado = subprocess.run(comando, capture_output=True, text=True, check=False)
                print("--- salida restaurada")
                print(restaurado.stdout.rstrip())
                print(f"exit_code: {restaurado.returncode}")
                if restaurado.returncode != 0:
                    fallas.append("vías: la copia restaurada no volvió a verde")
    eliminado = not raiz.exists()
    print(f"[{'OK   ' if eliminado else 'FALLA'}] temporal de vías eliminado")
    if not eliminado:
        fallas.append(f"vías: el temporal sobrevivió en {raiz}")
    return fallas


def autotest() -> int:
    fallas: list[str] = []
    print("=== Control positivo: corpus sintético con el retiro ya completo")
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "verde"
        raiz.mkdir()
        corpus_verde(raiz)
        _sellar_base_docs(raiz)
        _preparar_repo(raiz)
        for modo, evaluar in EVALUADORES.items():
            rep = evaluar(raiz)
            ok = not rep.hallazgos
            print(f"[{'OK   ' if ok else 'FALLA'}] --{modo}: {len(rep.hallazgos)} hallazgos")
            for h in rep.hallazgos[:6]:
                print(f"          {h}")
            if not ok:
                fallas.append(f"corpus verde: --{modo} → {len(rep.hallazgos)} hallazgos")
    fallas.extend(autotest_drenaje())
    fallas.extend(autotest_docs())
    fallas.extend(autotest_docs_vacuidad())
    fallas.extend(autotest_vias())
    for nombre, variante in VARIANTES_VERDES:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp) / "variante"
            raiz.mkdir()
            corpus_verde(raiz)
            _sellar_base_docs(raiz)
            variante(raiz)
            _preparar_repo(raiz)
            malos = {m: e(raiz).hallazgos for m, e in EVALUADORES.items()}
            malos = {m: h for m, h in malos.items() if h}
            print(f"[{'OK   ' if not malos else 'FALLA'}] variante verde · {nombre}: "
                  + ("sin hallazgos" if not malos
                     else " · ".join(f"--{m}: {h[0]}" for m, h in malos.items())))
            if malos:
                fallas.append(f"variante verde «{nombre}»: {list(malos)}")
    if fallas:
        print("\nRESULTADO: FALLA — sin control positivo los mutantes no prueban nada: un "
              "verificador que fallara siempre los detectaría todos igual.")
        for f in fallas:
            print(f"  - {f}")
        return 1

    print("\n=== Mutantes, uno por vez — cada uno rojo por su propio motivo")
    for nombre, modos, senales, preparar in MUTANTES:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp) / "mutante"
            raiz.mkdir()
            try:
                preparar(raiz)
            except AssertionError as e:
                print(f"[FALLA] {nombre}: {e}")
                fallas.append(f"{nombre}: {e}")
                continue
            for modo in modos:
                rep = EVALUADORES[modo](raiz)
                mensaje = norm(" ".join(rep.hallazgos))
                faltan = [s for s in senales if norm(s) not in mensaje]
                ok = bool(rep.hallazgos) and not faltan
                detalle = (f"{len(rep.hallazgos)} hallazgos · señales presentes" if ok else
                           f"{len(rep.hallazgos)} hallazgos · señales AUSENTES {faltan}")
                print(f"[{'OK   ' if ok else 'FALLA'}] {nombre} → --{modo}: {detalle}")
                if not ok:
                    for h in rep.hallazgos[:4]:
                        print(f"          {h}")
                    fallas.append(f"{nombre} → --{modo}: no falló por su motivo ({faltan})")

    print()
    if fallas:
        print("RESULTADO: FALLA")
        for f in fallas:
            print(f"  - {f}")
        return 1
    corridas = sum(len(m[1]) for m in MUTANTES)
    print(f"RESULTADO: OK — control positivo sobre los {len(EVALUADORES)} modos implementados, "
          f"{len(VARIANTES_VERDES)} variantes que deben seguir verdes, {len(MUTANTES)} mutantes "
          f"en {corridas} corridas, 1 mutante reversible de documentación, 1 mutante de vacuidad "
          f"y 1 mutante reversible de vías")
    return 0


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
EVALUADORES = {
    "ausencia": evaluar_ausencia,
    "clave": evaluar_clave,
    "adaptadores": evaluar_adaptadores,
    "drenaje": evaluar_drenaje_en_raiz,
    "vocabulario": evaluar_vocabulario,
    "docs": evaluar_docs,
    "vias": evaluar_vias,
}
MODOS = {nombre: (lambda raiz, f=f: f(raiz).cerrar()) for nombre, f in EVALUADORES.items()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--raiz", type=Path, default=REPO, help="raíz del árbol a verificar")
    p.add_argument("--ausencia", action="store_true", help="AC-1 · sin rastro de la vía retirada")
    p.add_argument("--clave", action="store_true", help="AC-2 · sin remanentes de la clave")
    p.add_argument("--adaptadores", action="store_true", help="AC-3 · los 3 adaptadores no existen")
    p.add_argument("--drenaje", action="store_true", help="AC-14b · precondición de drenaje")
    p.add_argument("--vocabulario", action="store_true", help="AC-12 · igualdad de vocabularios")
    p.add_argument("--docs", action="store_true", help="AC-16 · estructura documental conservada")
    p.add_argument("--vias", action="store_true", help="AC-15 · garantías por vía conservadas")
    p.add_argument("--autotest", action="store_true",
                   help="control positivo sobre un corpus sintético y después los mutantes")
    args = p.parse_args()

    elegidos = [m for m in (*MODOS, "autotest") if getattr(args, m)]
    if len(elegidos) != 1:
        p.error("elegí exactamente uno de --"
                + " / --".join((*MODOS, "autotest")))
    modo = elegidos[0]
    if modo == "autotest":
        return autotest()
    return MODOS[modo](args.raiz.resolve())


if __name__ == "__main__":
    sys.exit(main())
