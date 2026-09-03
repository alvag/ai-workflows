"""Productor de las tres huellas del ledger de secuencia y del recibo de partición.

Compila fuentes a preimages y emite o compara; **no** es un runtime del ledger: no interpreta la
máquina de estados y no muta ningún archivo del repositorio.

La sede normativa de qué bytes produce cada huella es `reference.md` → "La receta de serialización de
las huellas". Ante una discrepancia entre esa prosa y este archivo, **manda el ejecutable**, y un
cambio semántico de lo que produce exige una versión nueva de receta.

Códigos de salida, iguales en los cuatro subcomandos:

    0  éxito
    1  no coincide, o algún vector no rinde
    2  invocación mal formada
    3  no medible: el documento no admite cálculo, o el corpus falta o está incompleto
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

OK, DIFIERE, USO, NO_MEDIBLE = 0, 1, 2, 3

PREFIJOS = {
    "tasks": "sdd-flow/tasks-fingerprint/1",
    "coverage": "sdd-flow/coverage-fingerprint/1",
    "delta": "sdd-flow/delta-digest/1",
}

# Lista cerrada y su orden fijo. Una clave desconocida dentro de una unidad falla cerrado: la lista
# es lo que haría invisible un campo nuevo, y ese es el costo que esta elección paga.
CLAVES = ("id", "cubre", "titulo", "por-que", "archivos", "seam", "produce", "consume", "pasos",
          "verificar")
ETIQUETAS = {
    "por qué": "por-que", "por que": "por-que", "archivos": "archivos", "seam": "seam",
    "produce": "produce", "consume": "consume", "pasos": "pasos", "verificar": "verificar",
}
MULTIVALOR = ("cubre", "archivos", "consume", "verificar")


class NoMedible(Exception):
    """El documento no admite cálculo. Se traduce al código 3, nunca al 2."""


def _ledger_modulo():
    ruta = Path(__file__).resolve().parent / "_ledger.py"
    especificacion = importlib.util.spec_from_file_location("_ledger_huellas", ruta)
    if especificacion is None or especificacion.loader is None:
        raise NoMedible("no se pudo cargar el lector dirigido")
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


# --------------------------------------------------------------------------------------
# Gramática de extracción
# --------------------------------------------------------------------------------------

def _fuera_de_cercas(lineas: Sequence[str]) -> List[bool]:
    """Un encabezado dentro de una cerca de código no delimita nada."""
    fuera, dentro = [], False
    for linea in lineas:
        if linea.lstrip().startswith("```"):
            dentro = not dentro
            fuera.append(False)
            continue
        fuera.append(not dentro)
    return fuera


def slug(titulo: str) -> str:
    """ASCII en minúscula; corridas fuera de a-z0-9 a un guion; sin guiones en los extremos."""
    bajo = "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in titulo.strip())
    return re.sub(r"[^a-z0-9]+", "-", bajo).strip("-")


def _escapar(valor: str) -> str:
    """La única sede del recorte de espacios de un valor, y de los tres escapes cerrados.

    Una sola sede es lo que permite que un mutante la sustituya y que el corpus lo cace; repartido
    entre la extracción y la serialización, un mutante aplicado en una mitad queda verde por la otra.
    """
    return valor.strip().replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def _es_task(linea: str) -> Optional[re.Match]:
    return re.match(r"^\s*-\s*\[[ xX]\]\s*(.*)$", linea)


def _titulo_y_cubre(resto: str) -> Tuple[str, str, str]:
    """De la línea del checkbox saca identificador, título y cobertura, en las dos formas."""
    cuerpo = resto.strip()
    cubre = ""
    if "· cubre:" in cuerpo:
        cuerpo, _, cubre = cuerpo.partition("· cubre:")
    cuerpo = cuerpo.strip().strip("*").strip()
    match = re.match(r"^(T[0-9A-Za-z]+)\s*—\s*(.*)$", cuerpo)
    if not match:
        raise NoMedible(f"bloque de task sin identificador reconocible: {resto.strip()[:60]}")
    return match.group(1), match.group(2).strip().strip("*").strip(), cubre.strip()


def _campos_de_task(cuerpo: Sequence[str]) -> Dict[str, List[str]]:
    campos: Dict[str, List[str]] = {}
    clave_actual: Optional[str] = None
    for linea in cuerpo:
        etiqueta = re.match(r"^\s*-\s*\*\*(.+?):\*\*\s*(.*)$", linea)
        if etiqueta:
            nombre = etiqueta.group(1).strip().lower()
            if nombre not in ETIQUETAS:
                raise NoMedible(f"clave desconocida en una unidad: {etiqueta.group(1).strip()}")
            clave_actual = ETIQUETAS[nombre]
            valor = etiqueta.group(2)
            campos.setdefault(clave_actual, [])
            if valor.strip():
                campos[clave_actual].append(valor)
            continue
        paso = re.match(r"^\s+\d+\.\s+(.*)$", linea)
        if paso and clave_actual == "pasos":
            campos["pasos"].append(paso.group(1))
            continue
        if re.match(r"^\s*-\s+\S", linea):
            # Descartarla en silencio daba la misma huella a dos tareas con restricciones distintas,
            # que es exactamente lo que AC-6 prohíbe.
            raise NoMedible(f"viñeta no reconocida dentro de una unidad: {linea.strip()[:50]}")
        if linea.strip() and clave_actual and campos.get(clave_actual):
            campos[clave_actual][-1] = campos[clave_actual][-1] + " " + linea.strip()
    return campos


def _unidad(etiqueta: str, identificador: str, cuerpo: str) -> str:
    octetos = len(cuerpo.encode("utf-8"))
    return f"{etiqueta}\t{identificador}\t{octetos}\n{cuerpo}"


def _cuerpo_de_task(identificador: str, titulo: str, cubre: str,
                    campos: Dict[str, List[str]]) -> str:
    valores: Dict[str, List[str]] = {"id": [identificador], "titulo": [titulo]}
    if cubre:
        valores["cubre"] = [p.strip() for p in cubre.split(",") if p.strip()]
    for clave, crudos in campos.items():
        if not crudos:
            continue
        if clave in MULTIVALOR:
            partes: List[str] = []
            for crudo in crudos:
                partes.extend(p.strip() for p in crudo.split(";") if p.strip())
            valores[clave] = partes
        else:
            valores[clave] = list(crudos)
    lineas: List[str] = []
    for clave in CLAVES:
        for ordinal, valor in enumerate(valores.get(clave, []), start=1):
            lineas.append(f"{clave}\t{ordinal}\t{_escapar(valor)}\n")
    return "".join(lineas)


def _lineas_del_alcance(texto: str, forma: str) -> List[str]:
    """Las líneas donde vive el alcance, según la forma. Una sola vía para las dos huellas."""
    if forma not in ("tasks", "embebida"):
        raise ValueError(f"forma desconocida: {forma!r}")
    lineas = texto.replace("\r\n", "\n").split("\n")
    if forma == "tasks":
        return lineas
    libres = _fuera_de_cercas(lineas)
    marco = [i for i, l in enumerate(lineas) if libres[i] and re.match(r"^##\s+Tasks\s*$", l)]
    if not marco:
        raise NoMedible("la forma embebida exige una sección `## Tasks` en el plan")
    resto = [i for i, l in enumerate(lineas)
             if i > marco[0] and libres[i] and re.match(r"^##\s+\S", l)]
    return lineas[marco[0] + 1:min(resto) if resto else len(lineas)]


def _seccion_de_autorrevision(lineas: List[str], encabezados: List[int]) -> set:
    """Los índices que caen dentro de la sección de autorrevisión, encabezado incluido.

    Sede **única** de la exclusión: mientras vivía dentro del lazo de globales, un checkbox de task
    dentro de esa sección entraba igual a la huella, así que la exclusión que AC-6 pide era parcial.
    """
    for inicio in encabezados:
        if not lineas[inicio].lstrip("#").strip().lower().startswith("self-review"):
            continue
        siguientes = [i for i in encabezados if i > inicio]
        return set(range(inicio, min(siguientes) if siguientes else len(lineas)))
    return set()


def _indices_de_task(lineas: List[str], fuera: List[bool]):
    """Las tasks del alcance, ya sin la sección de autorrevisión, y los encabezados que delimitan.

    **Sede única** de esa exclusión, y por eso las dos huellas la comparten. Mientras cada una
    enumeraba las tasks por su cuenta, una task dentro de `## Self-review` salía de la huella de
    tareas y entraba a la de cobertura: dos huellas afirmando alcances distintos del mismo documento,
    que es justo lo que ninguna de las dos puede hacer.
    """
    encabezados = [i for i, l in enumerate(lineas)
                   if fuera[i] and re.match(r"^##\s+\S", l)]
    excluidas = _seccion_de_autorrevision(lineas, encabezados)
    indices = [i for i, l in enumerate(lineas)
               if fuera[i] and _es_task(l) and i not in excluidas]
    return indices, encabezados, excluidas


def unidades(texto: str, forma: str = "tasks") -> List[str]:
    """Las unidades del alcance, en **orden documental**: por su posición en la fuente.

    Los bloques globales son secciones de `tasks.md`. En la forma **embebida** las tareas viven
    dentro del plan, cuyas secciones son suyas y no del alcance, así que ahí no hay globales: leerlos
    metería el plan entero en la huella. La forma se declara y no se infiere.
    """
    lineas = _lineas_del_alcance(texto, forma)
    fuera = _fuera_de_cercas(lineas)
    vistos = set()

    # AC-6 excluye la **sección** de autorrevisión, no solo su encabezado, y la exclusión vive en
    # `_indices_de_task`. `encabezados` NO se filtra: sigue delimitando el cuerpo de la sección
    # anterior, y filtrarlo le borraba su frontera y esa sección se tragaba la autorrevisión entera.
    indices, encabezados, excluidas = _indices_de_task(lineas, fuera)
    # Orden **documental**: las unidades se emiten por su posición en la fuente, no todas las tasks
    # y después todos los globales. Agruparlas por tipo era una divergencia con la definición.
    por_posicion: List[Tuple[int, str]] = []
    for inicio in indices:
        siguientes = [i for i in indices if i > inicio] + [i for i in encabezados if i > inicio]
        fin = min(siguientes) if siguientes else len(lineas)
        identificador, titulo, cubre = _titulo_y_cubre(_es_task(lineas[inicio]).group(1))
        if identificador in vistos:
            raise NoMedible(f"identificador de task duplicado: {identificador}")
        vistos.add(identificador)
        campos = _campos_de_task(lineas[inicio + 1:fin])
        por_posicion.append((inicio, _unidad("task", identificador,
                                             _cuerpo_de_task(identificador, titulo, cubre, campos))))
    if not por_posicion:
        raise NoMedible("alcance vacío: ninguna task en la fuente")

    if forma == "embebida":
        return [u for _, u in sorted(por_posicion)]
    slugs = set()
    for inicio in encabezados:
        if inicio in excluidas:
            continue
        titulo = lineas[inicio].lstrip("#").strip()
        identificador = slug(titulo)
        if not identificador:
            raise NoMedible(f"bloque global sin identificador tras el slug: {titulo[:60]}")
        if identificador in slugs:
            raise NoMedible(f"slug de bloque global duplicado: {identificador}")
        slugs.add(identificador)
        siguientes = [i for i in encabezados if i > inicio]
        fin = min(siguientes) if siguientes else len(lineas)
        cuerpo = lineas[inicio + 1:fin]
        while cuerpo and cuerpo[-1].strip() == "":
            cuerpo.pop()
        por_posicion.append((inicio, _unidad("global", identificador,
                                             "".join(l + "\n" for l in cuerpo))))
    return [u for _, u in sorted(por_posicion)]


# --------------------------------------------------------------------------------------
# Las tres huellas
# --------------------------------------------------------------------------------------

def _digest(preimage: str) -> str:
    return "sha256:" + hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def preimage_tasks(texto: str, forma: str = "tasks") -> str:
    return PREFIJOS["tasks"] + "\n" + "".join(unidades(texto, forma))


def preimage_coverage(texto: str, plan: str, forma: str = "tasks") -> str:
    """Dos fuentes: `texto` trae el alcance y `plan` las claves congeladas del contrato.

    Confundirlas produce una huella sobre alcance vacío que igual parece válida, porque el `plan.md`
    de un flujo no trivial no contiene ninguna task.
    """
    # El alcance sale de la **misma enumeración** que la huella de tareas, no de una paralela:
    # ignorar `--forma` acá tomaba checkboxes de cualquier parte del plan, y enumerar por separado
    # metía a la cobertura las tasks de la sección de autorrevisión que la otra huella excluye.
    lineas = _lineas_del_alcance(texto, forma)
    fuera = _fuera_de_cercas(lineas)
    identificadores: List[str] = []
    for indice in _indices_de_task(lineas, fuera)[0]:
        identificador = _titulo_y_cubre(_es_task(lineas[indice]).group(1))[0]
        if identificador in identificadores:
            # La misma fuente falla cerrado al calcular la huella de tareas; aceptarla acá dejaba
            # dos alcances distintos con la misma cobertura.
            raise NoMedible(f"identificador de task duplicado en el alcance: {identificador}")
        identificadores.append(identificador)
    # Un alcance vacío **no** falla: su cuerpo es solo la línea del contrato. Lo dicen la prosa
    # normativa y la matriz congelada de vectores, y el código decía lo contrario.
    huella = ""
    for linea in _header(plan):
        campo = re.match(r"^contract_frozen_hash:\s*([0-9a-f]{64})\s*$", linea)
        if campo:
            huella = campo.group(1)
            break
    if huella and not any(re.match(r"^contract_frozen_version:\s*\d+\s*$", l) for l in _header(plan)):
        raise NoMedible("contract_frozen_hash sin su contract_frozen_version: las dos claves se "
                        "congelan en el mismo acto")
    if not huella:
        declarada = any(l.startswith("contract_frozen_hash:") for l in _header(plan))
        raise NoMedible("contract_frozen_hash presente pero mal formado: la cadena del contrato no "
                        "produjo un digest válido" if declarada else
                        "no hay contract_frozen_hash en el header: contrato ausente o no congelado")
    cuerpo = "".join(i + "\n" for i in identificadores) + f"contrato\t{huella}\n"
    return PREFIJOS["coverage"] + "\n" + cuerpo


def preimage_delta(material: str) -> str:
    return PREFIJOS["delta"] + "\n" + material


def calcular(huella: str, fuente: Optional[str], material: Optional[str],
             documento: Optional[str], plan: Optional[str] = None,
             forma: str = "tasks") -> str:
    if huella == "tasks":
        return _digest(preimage_tasks(_leer(fuente), forma))
    if huella == "coverage":
        return _digest(preimage_coverage(_leer(fuente), _leer(plan), forma))
    if material is not None:
        # El material suelto se toma como **valor lógico**, igual que el escalar de bloque: se le
        # come un único salto final si lo tiene. Sin esto, el digest de la creación no coincidía con
        # el recálculo posterior desde el ledger, que es la comparación que el contrato ordena.
        # `|-` recorta **todos** los saltos finales, no uno: alinear el material suelto con esa
        # semántica es lo que hace que el digest de la creación coincida con el del recálculo.
        return _digest(preimage_delta(_leer(material).rstrip("\n")))
    ledger = _ledger_modulo()
    try:
        objeto = ledger.leer(_leer(documento))
    except ledger.LecturaInvalida as error:
        raise NoMedible(str(error))
    # Una sola vía para las dos formas que el contrato admite: el escalar de bloque con el patch
    # durable, y la cadena vacía pre-handoff. El lector ya rechaza un chomping distinto del
    # declarado, así que esa guarda no se pierde por venir por acá.
    # AC-17: no se calcula sobre un documento que el esquema ya rechazaría. Sin esto, un ledger
    # con una clave desconocida producía huella y salía 0.
    faltas = ledger.validar(objeto, "ledger")
    if faltas:
        raise NoMedible("el documento no admite cálculo: " + "; ".join(faltas[:3]))
    valor = objeto.get("sequence", {}).get("delta", {}).get("material")
    if valor is None:
        raise NoMedible("el documento no tiene sequence.delta.material")
    if not isinstance(valor, str):
        raise NoMedible("sequence.delta.material no es una cadena")
    return _digest(preimage_delta(valor))


def _header(texto: str) -> List[str]:
    """Las líneas del frontmatter del plan, y nada más.

    Buscar una clave congelada en todo el documento aceptaba una que viviera en el cuerpo —en una
    tabla, en un ejemplo, en la prosa que la explica— y no en el header, que es su sede declarada.
    """
    lineas = texto.replace("\r\n", "\n").split("\n")
    if not lineas or lineas[0].strip() != "---":
        return []
    salida: List[str] = []
    for linea in lineas[1:]:
        if linea.strip() == "---":
            return salida
        salida.append(linea)
    return []


def _leer(ruta: Optional[str]) -> str:
    if ruta is None:
        raise NoMedible("la fuente no fue declarada")
    camino = Path(ruta)
    if not camino.is_file():
        raise NoMedible(f"la fuente no existe: {ruta}")
    try:
        return camino.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise NoMedible(f"la fuente no se pudo leer: {error}")


# --------------------------------------------------------------------------------------
# Validación
# --------------------------------------------------------------------------------------

def _regimen(plan: Optional[str]) -> str:
    """El marcador vive en el header del plan y no en el recibo: por eso `--plan` es obligatorio."""
    for linea in _header(_leer(plan)):
        campo = re.match(r"^huellas_receta:\s*(\S+)\s*$", linea)
        if campo:
            if campo.group(1) != "v1":
                raise NoMedible(f"huellas_receta con un valor no soportado: {campo.group(1)}")
            return "v1"
        if linea.strip() == "---" and linea is not None:
            continue
    return "legado"


def validar(documento: str, plan: Optional[str]) -> List[str]:
    ledger = _ledger_modulo()
    texto = _leer(documento)
    try:
        objeto = ledger.leer(texto)
    except ledger.LecturaInvalida as error:
        raise NoMedible(str(error))
    # Discriminar por la ausencia de una sola clave era frágil: la raíz del recibo legado es abierta,
    # así que uno antiguo con un `schema_version` de más se leía como ledger y dejaba de ser válido.
    parece_ledger = "sequence" in objeto and "schema_version" in objeto
    parece_recibo = "tasks_fingerprint" in objeto and "blocks" in objeto
    if parece_ledger == parece_recibo:
        raise NoMedible("el documento no es reconociblemente un recibo ni un ledger: un recibo lleva "
                        "tasks_fingerprint y blocks, un ledger lleva schema_version y sequence")
    es_recibo = parece_recibo
    if es_recibo and plan is None:
        raise ValueError("validar un recibo exige --plan: el marcador de régimen vive en el plan")
    esquema = _regimen(plan) if es_recibo else "ledger"
    try:
        return ledger.validar(objeto, esquema)
    except ledger.LecturaInvalida as error:
        raise NoMedible(str(error))


# --------------------------------------------------------------------------------------
# Vectores
# --------------------------------------------------------------------------------------

def _huella_del_arbol(raiz: str) -> str:
    """Huella del contenido del corpus, para comprobar que una invocación no lo mutó."""
    acumulado = hashlib.sha256()
    for ruta in sorted(Path(raiz).rglob("*")):
        # El bytecode que el intérprete genera al importar no lo escribe este ejecutable.
        if "__pycache__" in ruta.parts:
            continue
        if ruta.is_file():
            acumulado.update(str(ruta.relative_to(raiz)).encode("utf-8"))
            acumulado.update(ruta.read_bytes())
    return acumulado.hexdigest()


def _manifiesto(corpus: str) -> List[Dict[str, str]]:
    ruta = Path(corpus) / "manifiesto.tsv"
    if not ruta.is_file():
        raise NoMedible(f"el corpus no tiene manifiesto: {ruta}")
    filas: List[Dict[str, str]] = []
    cabecera: Optional[List[str]] = None
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").split("\n"), start=1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        campos = linea.split("\t")
        if cabecera is None:
            cabecera = [c.strip() for c in campos]
            continue
        if len(campos) != len(cabecera):
            raise NoMedible(f"fila {numero} del manifiesto con {len(campos)} campos, "
                            f"se esperaban {len(cabecera)}")
        filas.append(dict(zip(cabecera, (c.strip() for c in campos))))
    if not filas:
        raise NoMedible("el manifiesto del corpus está vacío")
    # La matriz es **cerrada**: el corpus declara sus identificadores obligatorios aparte, y el
    # manifiesto tiene que estar en biyección con esa lista. Sin esto, el runner declaraba
    # obligatorio solo lo que el manifiesto trajera.
    declarados = Path(corpus) / "obligatorios.txt"
    if not declarados.is_file():
        raise NoMedible(f"el corpus no declara su matriz cerrada: {declarados}")
    esperados = {l.strip() for l in declarados.read_text(encoding="utf-8").split("\n")
                 if l.strip() and not l.startswith("#")}
    for fila in filas:
        # `preimage_hex` es el registro auditable de los bytes canónicos esperados. Si nadie lo
        # consume, se puede corromper entero sin que el corpus cambie de color.
        hx, dg = fila.get("preimage_hex", "-"), fila.get("digest", "-")
        if hx == "-" or dg == "-":
            continue
        try:
            calculado = "sha256:" + hashlib.sha256(bytes.fromhex(hx)).hexdigest()
        except ValueError:
            raise NoMedible(f"{fila['id']}: preimage_hex no es hexadecimal válido")
        if calculado != dg:
            raise NoMedible(f"{fila['id']}: el digest declarado no es el de su preimage_hex")
    ids = [f["id"] for f in filas]
    if len(ids) != len(set(ids)):
        repetidos = sorted({i for i in ids if ids.count(i) > 1})
        raise NoMedible(f"el manifiesto repite identificadores: {repetidos}")
    presentes = set(ids)
    if presentes != esperados:
        faltan, sobran = sorted(esperados - presentes), sorted(presentes - esperados)
        raise NoMedible(f"la matriz cerrada no coincide; faltan {faltan}, sobran {sobran}")
    return filas


def verificar_vectores(corpus: str, caso: Optional[str]) -> Tuple[int, List[str]]:
    filas = _manifiesto(corpus)
    seleccion = [f for f in filas if caso is None or f["id"].startswith(caso)]
    if not seleccion:
        raise NoMedible(f"la selección quedó vacía para el prefijo {caso!r}")
    por_id = {f["id"]: f for f in filas}
    lineas: List[str] = []
    infra: List[str] = []
    fallos = 0
    for fila in seleccion:
        obtenido, detalle = _rendir(corpus, fila)
        esperado, relacion = fila["digest"], fila["relacion"]
        if obtenido is INFRA:
            rinde, visto = False, f"INFRAESTRUCTURA: {detalle}"
            infra.append(f"{fila['id']}: {detalle}")
        elif relacion == "falla-cerrado":
            rinde = obtenido is None
            visto = detalle if obtenido is None else "no falló"
        elif relacion == "admite":
            rinde = obtenido == "admite"
            visto = obtenido if obtenido is not None else detalle
        elif relacion == "difiere-de-declarado":
            rinde = obtenido is not None and obtenido != esperado
            visto = f"{obtenido} contra el declarado {esperado}"
        elif relacion.startswith("codigo:"):
            rinde = obtenido == relacion.split(":", 1)[1]
            visto = f"código {obtenido}"
        elif relacion.startswith(("difiere-de:", "igual-a:")):
            otro = por_id.get(relacion.split(":", 1)[1])
            if otro is None:
                raise NoMedible(f"{fila['id']}: la relación nombra un vector que no está en el corpus")
            contra, detalle_otro = _rendir(corpus, otro)
            if contra is INFRA:
                # Compararlo como valor dejaba el vector verde por un fallo del corpus, y no
                # registrarlo devolvía 1 en vez del 3 que el contrato promete para corpus incompleto.
                rinde, visto = False, f"INFRAESTRUCTURA del referenciado: {detalle_otro}"
                infra.append(f"{fila['id']} → {otro['id']}: {detalle_otro}")
            else:
                hay = obtenido is not None and contra is not None
                rinde = hay and ((obtenido != contra) if relacion.startswith("difiere") else
                                 (obtenido == contra))
                # Y si el vector declara su propio digest golden, tiene que cumplirlo además de la
                # relación: sin esto, cualquier digest distinto pasaba un `difiere-de`.
                if rinde and esperado != "-" and obtenido != esperado:
                    rinde, visto = False, f"{obtenido} no es su golden declarado {esperado}"
                else:
                    visto = f"{obtenido} contra {contra}"
        else:
            rinde = obtenido == esperado
            visto = obtenido if obtenido is not None else detalle
        fallos += not rinde
        lineas.append(f"{'ok ' if rinde else 'FALLA'} {fila['id']} {relacion} {visto}")
    if infra:
        # Corpus ausente o incompleto es `3`, no `1`: un vector que no se puede correr no es un
        # vector que no rinde.
        raise NoMedible("el corpus está incompleto: " + "; ".join(infra[:3]))
    return (OK if fallos == 0 else DIFIERE), lineas


SEPARADOR_SUSTITUCION = "|=>"
# Centinela de fallo de infraestructura del corpus, distinto del fallo declarado de un vector.
INFRA = object()


def _con_sustitucion(entrada: str, sustitucion: str) -> str:
    """Aplica la sustitución declarada del vector sobre una copia en memoria de su base.

    Es lo que evita que cada mutación de un campo cueste una copia entera del fixture. El anclaje
    tiene que aparecer **exactamente una vez**: si la base cambia y el ancla desaparece o se duplica,
    el vector falla nombrándose, en vez de mutar algo distinto de lo que declara.
    """
    texto = _leer(entrada)
    # Varias sustituciones se encadenan con `;;`: hay invariantes del documento que exigen mover dos
    # campos a la vez, y partirlas en dos vectores probaría un documento que el contrato rechaza.
    for parte in sustitucion.split(";;"):
        if SEPARADOR_SUSTITUCION not in parte:
            raise NoMedible(f"sustitución mal formada, falta {SEPARADOR_SUSTITUCION!r}")
        viejo, _, nuevo = parte.partition(SEPARADOR_SUSTITUCION)
        viejo, nuevo = viejo.replace("\\n", "\n"), nuevo.replace("\\n", "\n")
        if texto.count(viejo) != 1:
            raise NoMedible(f"el ancla de la sustitución aparece {texto.count(viejo)} veces, "
                            "se esperaba exactamente una")
        texto = texto.replace(viejo, nuevo)
    return texto


def _rendir(corpus: str, fila: Dict[str, str]) -> Tuple[Optional[str], str]:
    entrada = str(Path(corpus) / fila["entrada"])
    sustitucion = fila.get("sustitucion") or "-"
    temporal: Optional[Path] = None
    # Un vector cuya ENTRADA no existe, o cuya sustitución no se puede aplicar, no rinde su fallo
    # declarado: falla la infraestructura del corpus. Confundirlos dejaba pasar en verde a los trece
    # vectores `falla-cerrado` con solo borrarles el archivo.
    if not Path(entrada).is_file():
        return INFRA, f"la entrada del vector no existe: {fila['entrada']}"
    if sustitucion != "-":
        try:
            contenido = _con_sustitucion(entrada, sustitucion)
        except NoMedible as error:
            return INFRA, f"la sustitución no se pudo aplicar: {error}"[:80]
        # **Fuera del repositorio**: el ejecutable declara que no muta ningún archivo suyo, y un
        # temporal dentro del corpus lo contradice y puede dejar residuos si el proceso muere.
        import tempfile
        descriptor, ruta = tempfile.mkstemp(prefix="vector-huellas.", suffix=Path(entrada).suffix)
        temporal = Path(ruta)
        with open(descriptor, "w", encoding="utf-8") as archivo:
            archivo.write(contenido)
        entrada = str(temporal)
    try:
        return _rendir_entrada(corpus, fila, entrada)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def _rendir_entrada(corpus: str, fila: Dict[str, str], entrada: str) -> Tuple[Optional[str], str]:
    try:
        if fila["huella"] == "codigos":
            # Los argumentos del vector nombran archivos del corpus; resolverlos contra el cwd haría
            # que el mismo vector rindiera distinto según desde dónde se lo invoque.
            argv = [str(Path(corpus) / a) if a.startswith("entradas/") else a
                    for a in _leer(entrada).split("\n") if a]
            # La promesa es «no muta ningún archivo del repositorio», así que se vigilan las dos
            # superficies que una invocación podría tocar: el corpus y la sede de los scripts.
            vigiladas = [corpus, str(Path(__file__).resolve().parent)]
            antes = [_huella_del_arbol(v) for v in vigiladas]
            codigo = main(argv)
            for ruta, previa in zip(vigiladas, antes):
                if _huella_del_arbol(ruta) != previa:
                    return None, f"hubo mutación en {ruta}"
            return str(codigo), ""
        if fila["huella"] == "delta":
            # El contrato admite las dos formas del material: el escalar de bloque del ledger y el
            # material suelto de la creación, cuando el ledger todavía no existe.
            if entrada.endswith(".yml"):
                obtenido = calcular("delta", None, None, entrada)
            else:
                obtenido = calcular("delta", None, entrada, None)
        elif fila["huella"] == "esquema":
            plan = str(Path(corpus) / fila["plan"]) if fila.get("plan") else None
            faltas = validar(entrada, plan)
            return (None, "; ".join(faltas)[:80]) if faltas else ("admite", "")
        else:
            plan = str(Path(corpus) / fila["plan"]) if fila.get("plan") else None
            obtenido = calcular(fila["huella"], entrada, None, None, plan,
                                fila.get("forma") or "tasks")
        return obtenido, ""
    except NoMedible as error:
        return None, str(error)[:80]


# --------------------------------------------------------------------------------------
# Interfaz de línea de comandos
# --------------------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="huellas-secuencia", add_help=True)
    subs = parser.add_subparsers(dest="subcomando", required=True)
    for nombre in ("calcular", "comparar"):
        sub = subs.add_parser(nombre)
        sub.add_argument("--huella", required=True, choices=("tasks", "coverage", "delta"))
        sub.add_argument("--fuente")
        sub.add_argument("--material")
        sub.add_argument("--documento")
        sub.add_argument("--plan")
        # Sin default: la forma **se declara y no se infiere**, y un default silencioso es
        # lo que dejó a las cuatro invocaciones de cobertura omitiéndola sin que nada lo
        # dijera. `_fuentes` la exige donde decide el alcance.
        sub.add_argument("--forma", choices=("tasks", "embebida"))
        if nombre == "comparar":
            sub.add_argument("--esperado", required=True)
    val = subs.add_parser("validar")
    val.add_argument("--documento", required=True)
    val.add_argument("--plan")
    vec = subs.add_parser("verificar-vectores")
    vec.add_argument("--corpus", required=True)
    vec.add_argument("--caso")
    return parser


def _fuentes(args: argparse.Namespace) -> None:
    if args.huella in ("tasks", "coverage") and args.forma is None:
        raise ValueError("--forma es obligatoria con --huella tasks o coverage: "
                         "la forma decide el alcance y no se infiere")
    if args.huella == "delta":
        if (args.material is None) == (args.documento is None):
            raise ValueError("delta toma --material o --documento, exactamente uno de los dos")
        if args.fuente is not None:
            raise ValueError("delta no toma --fuente")
    else:
        if args.fuente is None:
            raise ValueError(f"{args.huella} exige --fuente")
        if args.material is not None or args.documento is not None:
            raise ValueError(f"{args.huella} no toma --material ni --documento")
        # El alcance y las claves congeladas viven en archivos distintos salvo en un flujo trivial.
        if args.huella == "coverage" and args.plan is None:
            raise ValueError("coverage exige --plan además de --fuente: el alcance y las claves "
                             "congeladas son dos fuentes")
        if args.huella == "tasks" and args.plan is not None:
            raise ValueError("tasks no toma --plan")


def main(argv: Sequence[str]) -> int:
    try:
        args = _parser().parse_args(list(argv))
    except SystemExit:
        return USO
    try:
        if args.subcomando in ("calcular", "comparar"):
            _fuentes(args)
            valor = calcular(args.huella, args.fuente, args.material, args.documento, args.plan,
                             args.forma)
            if args.subcomando == "calcular":
                print(valor)
                return OK
            print(valor)
            if valor == args.esperado:
                return OK
            print(f"no coincide: esperado {args.esperado}", file=sys.stderr)
            return DIFIERE
        if args.subcomando == "validar":
            faltas = validar(args.documento, args.plan)
            if not faltas:
                print("admite cálculo")
                return OK
            for falta in faltas:
                print(falta, file=sys.stderr)
            return NO_MEDIBLE
        codigo, lineas = verificar_vectores(args.corpus, args.caso)
        for linea in lineas:
            print(linea)
        return codigo
    except ValueError as error:
        print(f"USO: {error}", file=sys.stderr)
        return USO
    except NoMedible as error:
        print(f"NO MEDIBLE: {error}", file=sys.stderr)
        return NO_MEDIBLE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
