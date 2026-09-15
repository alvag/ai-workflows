"""Predicado: valida pertinencia, baseline y transiciones direccionales del contrato; conserva ID y
Requisito, liga cada diferencia a una operación y aprobación únicas, aplica fase y presupuesto,
y restringe la adopción legado y la envoltura de proyección canónica."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Dict, Iterable, List, Optional, Set, Tuple


USO = "USO:contrato-invariantes contract approval_log phase(candidate/final)"
ENCODING = "utf-8"
OPERACIONES = (
    "cobertura-agregada", "esperado-corregido", "pertinencia-corregida",
    "verificacion-corregida",
)
PERTINENCIA_ORDEN = (
    "id", "autoridad", "relación", "baseline_tipo", "baseline_fundamento",
)
BASELINE_TIPOS = {"fallos-conjunto", "fallos-listado", "fallos-conteo", "otro"}
EVIDENCIAS_EJECUTABLES = {"test", "build", "inspección"}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
TOKEN_RE = re.compile(r"(.+):a([1-9][0-9]*)")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")
PROYECCION_CONTEO_RE = re.compile(r"exit -?[0-9]+; failures=[0-9]+")
PROYECCION_CONJUNTO_RE = re.compile(r"exit -?[0-9]+; count=[0-9]+;sha256=[0-9a-f]{64}")

# Única autoridad de los bytes de la envoltura POSIX. Recibe el predicado en $1 y el proyector en
# $2; emite la salida completa seguida por la proyección, conserva el código del predicado y reserva
# una única pareja para fallos del transporte. No usa tuberías ni alternancia de shell.
PROJECTION_WRAPPER_BODY = (
    "p=$(mktemp); o=$(mktemp); l=$(mktemp); "
    "trap 'rm -f \"$p\" \"$o\" \"$l\"' EXIT HUP INT TERM; "
    "if ! test -n \"$p\"; then printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "if ! test -n \"$o\"; then printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "if ! test -n \"$l\"; then printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "sh -c \"$1\" >\"$p\" 2>&1; rc=$?; sh -c \"$2\" <\"$p\" >\"$o\" 2>\"$l\"; prc=$?; "
    "if [ \"$prc\" -ne 0 ]; then cat \"$l\" >&2; "
    "printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "exec 3<\"$o\"; IFS= read -r line <&3; first=$?; IFS= read -r extra <&3; second=$?; "
    "printf '%s\\n' \"$line\" >\"$l\"; cmp -s \"$l\" \"$o\"; same=$?; "
    "grep -Eq '^failures=[0-9]+$' \"$l\"; count=$?; "
    "grep -Eq '^count=[0-9]+;sha256=[0-9a-f]{64}$' \"$l\"; listed=$?; "
    "if [ \"$first\" -ne 0 ]; then printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "if [ \"$second\" -eq 0 ]; then printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "if [ \"$same\" -ne 0 ]; then printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "if [ \"$count\" -ne 0 ] && [ \"$listed\" -ne 0 ]; then "
    "printf '%s\\n' CROSS_IMPLEMENT_PROJECTION_BLOCKED; exit 125; fi; "
    "cat \"$p\"; cat \"$o\"; exit \"$rc\""
)


class Linea:
    def __init__(self, valores: Dict[str, str], orden: Tuple[str, ...], numero: int,
                 texto: str) -> None:
        self.valores = valores
        self.orden = orden
        self.numero = numero
        self.texto = texto


class Fila:
    def __init__(self, requisito: str, evidencia: str, comando: str, esperado: str,
                 baseline: str) -> None:
        self.requisito = requisito
        self.evidencia = evidencia
        self.comando = comando
        self.esperado = esperado
        self.baseline = baseline


class Version:
    def __init__(self, numero: int, bloque: List[str], filas: Dict[str, Fila],
                 pertinencias: Dict[str, Linea], reparaciones: List[Linea],
                 adopciones: List[Linea], registros: Dict[str, Linea]) -> None:
        self.numero = numero
        self.bloque = bloque
        self.filas = filas
        self.pertinencias = pertinencias
        self.reparaciones = reparaciones
        self.adopciones = adopciones
        self.registros = registros


def _cargar_dependencia(nombre_archivo: str, nombre_modulo: str) -> ModuleType:
    ruta = Path(__file__).resolve().with_name(nombre_archivo)
    especificacion = importlib.util.spec_from_file_location(nombre_modulo, ruta)
    if especificacion is None or especificacion.loader is None:
        raise RuntimeError(f"no se pudo crear el cargador de {ruta}")
    modulo = importlib.util.module_from_spec(especificacion)
    try:
        especificacion.loader.exec_module(modulo)
    except Exception as error:
        raise RuntimeError(f"no se pudo cargar {ruta}: {error}") from error
    return modulo


def _hash_bloque(bloque: List[str]) -> str:
    canon = [re.sub(r"`hash: [^`]*`", "`hash: `", linea).rstrip() for linea in bloque]
    while canon and canon[-1] == "":
        canon.pop()
    return hashlib.sha256(("\n".join(canon) + "\n").encode(ENCODING)).hexdigest()


def _sha(valor: str) -> str:
    return hashlib.sha256(valor.encode(ENCODING)).hexdigest()


def _linea_campos(texto: str, prefijo: str, numero: int) -> Optional[Linea]:
    if not texto.startswith(prefijo):
        return None
    piezas = texto[len(prefijo):].split(" · ")
    valores: Dict[str, str] = {}
    orden: List[str] = []
    for pieza in piezas:
        coincidencia = re.fullmatch(r"`([^`:]+): ([^`]*)`", pieza)
        if coincidencia is None or coincidencia.group(1) in valores:
            return Linea({}, (), numero, texto)
        clave, valor = coincidencia.groups()
        valores[clave] = valor
        orden.append(clave)
    return Linea(valores, tuple(orden), numero, texto)


def campos_linea(texto: str, prefijo: str = "- ") -> Dict[str, str]:
    """Lee una línea completa con la misma gramática estricta que el contrato."""
    lectura = _linea_campos(texto.strip(), prefijo, 0)
    if lectura is None or not _campos_validos(lectura, lectura.orden, "línea", []):
        return {}
    return dict(lectura.valores)


def operacion_token(token: str) -> Optional[str]:
    """Extrae la operación de un token de reparación con ordinal canónico."""
    coincidencia = TOKEN_RE.fullmatch(token)
    if coincidencia is None:
        return None
    prefijo = coincidencia.group(1)
    version_e_id, separador, operacion = prefijo.rpartition(":")
    version, separador_id, identificador = version_e_id.partition(":")
    if (not separador or not separador_id or not identificador
            or re.fullmatch(r"[1-9][0-9]*", version) is None
            or operacion not in OPERACIONES):
        return None
    return operacion


def _extraer(lineas: Iterable[str], prefijo: str) -> List[Linea]:
    resultado: List[Linea] = []
    for numero, linea in enumerate(lineas, 1):
        limpia = linea.strip()
        if limpia.startswith(prefijo):
            resultado.append(_linea_campos(limpia, prefijo, numero) or Linea({}, (), numero, limpia))
    return resultado


def parsear_reparaciones(texto: str) -> List[Tuple[int, Dict[str, str]]]:
    """Devuelve registros de reparación usando la frontera canónica de versiones."""
    cadena = _cargar_dependencia(
        "contrato-cadena.py", "cross_implement_contrato_invariantes_cadena_publica")
    resultado: List[Tuple[int, Dict[str, str]]] = []
    for numero, bloque in cadena.versiones(texto):
        for linea in _extraer(bloque[1:], "- reparación: "):
            resultado.append((numero, dict(linea.valores)))
    return resultado


def _parsear_versiones(texto: str, cadena: ModuleType, tabla: ModuleType) -> List[Version]:
    resultado: List[Version] = []
    for numero, bloque in cadena.versiones(texto):
        filas = {
            fila[0]: Fila(fila[1], fila[2], fila[3], fila[4], fila[5])
            for fila in tabla.parsear_tabla_pipe("\n".join(bloque[1:]))
            if len(fila) == 6 and fila[0] != "ID"
        }
        pertinencias_lista = _extraer(bloque[1:], "- pertinencia: ")
        pertinencias = {
            linea.valores.get("id", f"__malformada_{linea.numero}"): linea
            for linea in pertinencias_lista
        }
        registros_lista = [
            linea for linea in _extraer(bloque[1:], "- ")
            if linea.texto.startswith("- `id: ")
        ]
        registros = {
            linea.valores.get("id", f"__malformado_{linea.numero}"): linea
            for linea in registros_lista
        }
        resultado.append(Version(
            numero, bloque, filas, pertinencias,
            _extraer(bloque[1:], "- reparación: "),
            _extraer(bloque[1:], "- adopción: "), registros,
        ))
    return resultado


def _campos_validos(linea: Linea, orden: Tuple[str, ...], contexto: str,
                    errores: List[str]) -> bool:
    if linea.orden != orden:
        errores.append(f"{contexto}: forma u orden de campos inválido")
        return False
    for clave, valor in linea.valores.items():
        if not valor or "`" in valor or "·" in valor or CONTROL_RE.search(valor):
            errores.append(f"{contexto}: valor inválido en {clave}")
            return False
    return True


def _lista_ids(valor: str, contexto: str, errores: List[str]) -> Set[str]:
    if valor == "ninguno":
        return set()
    partes = valor.split(",")
    if any(not parte or parte.strip() != parte for parte in partes):
        errores.append(f"{contexto}: lista de ID mal formada")
        return set()
    if partes != sorted(set(partes), key=lambda item: item.encode(ENCODING)):
        errores.append(f"{contexto}: lista de ID no es única y canónica")
    return set(partes)


def _timestamp_valido(valor: str) -> bool:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", valor) is None:
        return False
    try:
        datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validar_pertinencias(version: Version, obligatorias: bool, errores: List[str]) -> None:
    if not obligatorias and not version.pertinencias:
        return
    ids_filas = set(version.filas)
    ids_pertinencia = set(version.pertinencias)
    if ids_filas != ids_pertinencia:
        errores.append(
            f"v{version.numero}: paridad de pertinencia inválida; "
            f"faltan={sorted(ids_filas - ids_pertinencia)}, "
            f"sobran={sorted(ids_pertinencia - ids_filas)}")
    if len(version.pertinencias) != len(_extraer(version.bloque[1:], "- pertinencia: ")):
        errores.append(f"v{version.numero}: pertinencia con ID duplicado")
    for identificador, linea in version.pertinencias.items():
        if not _campos_validos(linea, PERTINENCIA_ORDEN,
                               f"v{version.numero}: pertinencia de {identificador}", errores):
            continue
        if linea.valores["baseline_tipo"] not in BASELINE_TIPOS:
            errores.append(f"v{version.numero}: pertinencia de {identificador} con baseline_tipo inválido")


def _validar_baseline(version: Version, fase: str, adopcion: Optional[Linea],
                      errores: List[str]) -> None:
    for identificador, fila in version.filas.items():
        pertinencia = version.pertinencias.get(identificador)
        if pertinencia is None or not pertinencia.valores or fila.baseline not in {"RED", "GREEN_ALREADY"}:
            continue
        registro = version.registros.get(identificador)
        if registro is None or not registro.valores:
            errores.append(f"v{version.numero}: baseline de {identificador} sin registro")
            continue
        observado = registro.valores.get("observado", "")
        tipo = pertinencia.valores.get("baseline_tipo", "")
        if tipo == "fallos-conteo" and PROYECCION_CONTEO_RE.fullmatch(observado) is None:
            errores.append(f"v{version.numero}: observado de {identificador} no es fallos-conteo")
        elif tipo in {"fallos-conjunto", "fallos-listado"} and \
                PROYECCION_CONJUNTO_RE.fullmatch(observado) is None:
            errores.append(f"v{version.numero}: observado de {identificador} no es fallos-conjunto/listado")
        elif tipo == "otro" and (PROYECCION_CONTEO_RE.fullmatch(observado) is not None or
                                  PROYECCION_CONJUNTO_RE.fullmatch(observado) is not None):
            errores.append(f"v{version.numero}: observado reservado usado por baseline_tipo otro")
        if tipo.startswith("fallos-") and fila.evidencia not in EVIDENCIAS_EJECUTABLES:
            errores.append(f"v{version.numero}: baseline {tipo} de {identificador} no es ejecutable")
        if fila.baseline == "GREEN_ALREADY":
            adjudicacion = registro.valores.get("adjudicación", "")
            intermedia = (adopcion is not None and adopcion.valores.get("estado") == "intermedia"
                          and fase == "candidate")
            if adjudicacion == "weak_check" and not intermedia:
                errores.append(f"v{version.numero}: weak_check fuera de adopción intermedia candidate")
            elif adjudicacion not in {"already_satisfied", "weak_check"}:
                errores.append(f"v{version.numero}: GREEN_ALREADY de {identificador} sin adjudicación")


def _validar_token(token: str, prefijo: str, contexto: str, errores: List[str]) -> None:
    coincidencia = TOKEN_RE.fullmatch(token)
    if coincidencia is None or coincidencia.group(1) != prefijo:
        errores.append(f"{contexto}: token inválido")


def _validar_aprobaciones(aprobaciones: List[Linea], errores: List[str]) -> None:
    tokens = [linea.valores.get("token", "") for linea in aprobaciones]
    repetidos = sorted({token for token in tokens if token and tokens.count(token) > 1})
    if repetidos:
        errores.append("approval_log: token duplicado: " + ", ".join(repetidos))
    for linea in aprobaciones:
        contexto = f"approval_log línea {linea.numero}"
        obligatorios = ("paso", "actor", "token", "hash", "timestamp")
        if any(not linea.valores.get(clave) for clave in obligatorios):
            errores.append(f"{contexto}: aprobación incompleta")
            continue
        if linea.valores["paso"] != "aprobar-reparación" or linea.valores["actor"] != "usuario":
            errores.append(f"{contexto}: paso o actor inválido")
        if SHA256_RE.fullmatch(linea.valores["hash"]) is None:
            errores.append(f"{contexto}: hash inválido")
        if not _timestamp_valido(linea.valores["timestamp"]):
            errores.append(f"{contexto}: timestamp inválido")
    por_prefijo: Dict[str, List[int]] = {}
    for linea in aprobaciones:
        coincidencia = TOKEN_RE.fullmatch(linea.valores.get("token", ""))
        if coincidencia is not None:
            por_prefijo.setdefault(coincidencia.group(1), []).append(int(coincidencia.group(2)))
    for prefijo, ordinales in por_prefijo.items():
        if ordinales != list(range(1, len(ordinales) + 1)):
            errores.append(f"approval_log: ordinales de token no consecutivos para {prefijo}")


def _aprobacion_para(aprobaciones: List[Linea], token: str, hash_candidata: str,
                    contexto: str, requerida: bool, errores: List[str]) -> Optional[Linea]:
    candidatas = [linea for linea in aprobaciones if linea.valores.get("token") == token]
    if not candidatas:
        if requerida:
            errores.append(f"{contexto}: sin aprobación para el token {token}")
        return None
    if len(candidatas) != 1:
        errores.append(f"{contexto}: aprobación no única para el token {token}")
        return None
    aprobacion = candidatas[0]
    if aprobacion.valores.get("hash") != hash_candidata:
        errores.append(f"{contexto}: aprobación con hash distinto de la versión candidata")
    return aprobacion


def _orden_reparacion(operacion: str, campos: str = "") -> Tuple[str, ...]:
    base = ("version_previa", "id", "operación", "token")
    if operacion == "esperado-corregido":
        return base + ("esperado_previo_sha256",)
    if operacion == "pertinencia-corregida":
        return base + ("pertinencia_previa_sha256",)
    if operacion == "verificacion-corregida":
        huellas: Tuple[str, ...] = ()
        if campos in {"evidencia", "evidencia+comando"}:
            huellas += ("evidencia_previa_sha256",)
        if campos in {"comando", "evidencia+comando"}:
            huellas += ("comando_previo_sha256",)
        return base + ("campos",) + huellas
    return base


def _envoltura(comando: str) -> Tuple[Optional[Tuple[str, str]], Optional[str]]:
    try:
        argumentos = shlex.split(comando, posix=True)
    except ValueError:
        return None, "sintaxis POSIX inválida"
    if len(argumentos) != 6 or argumentos[0:2] != ["sh", "-c"] or argumentos[3] != "sh":
        return None, "aridad o argumentos fijos inválidos"
    if argumentos[2] != PROJECTION_WRAPPER_BODY:
        return None, "cuerpo canónico inválido"
    return (argumentos[4], argumentos[5]), None


def _validar_envoltura(nueva: str, previa: str, contexto: str,
                       errores: List[str]) -> None:
    envoltura_nueva, error = _envoltura(nueva)
    if error is not None or envoltura_nueva is None:
        errores.append(f"{contexto}: envoltura de proyección {error}")
        return
    predicado_nuevo, _proyector_nuevo = envoltura_nueva
    envoltura_previa, _ = _envoltura(previa)
    predicado_previo = envoltura_previa[0] if envoltura_previa is not None else previa
    if _envoltura(predicado_nuevo)[0] is not None:
        errores.append(f"{contexto}: envoltura de proyección anidada")
    elif predicado_nuevo != predicado_previo:
        errores.append(f"{contexto}: la envoltura no conserva el predicado previo")


def _validar_dialecto(version: Version, errores: List[str]) -> None:
    for numero, linea in enumerate(version.bloque[1:], 2):
        limpia = linea.strip()
        if not limpia.startswith("|") or limpia == "|---|---|---|---|---|---|" or \
                limpia.startswith("| ID |"):
            continue
        if limpia.count("|") != 7:
            errores.append(
                f"v{version.numero} línea {numero}: dialecto de tabla inválido; "
                "una celda contiene barra vertical")


def _validar_pares_defecto(aprobaciones: List[Linea], errores: List[str]) -> None:
    por_id: Dict[str, Dict[int, int]] = {}
    for aprobacion in aprobaciones:
        valores = aprobacion.valores
        presentes = [clave in valores for clave in
                     ("checkId", "contract_version", "verification_defect_ordinal")]
        if any(presentes) and not all(presentes):
            errores.append(f"approval_log línea {aprobacion.numero}: par de VERIFICATION_DEFECT incompleto")
            continue
        if not all(presentes):
            continue
        try:
            version = int(valores["contract_version"])
            ordinal = int(valores["verification_defect_ordinal"])
        except ValueError:
            errores.append(f"approval_log línea {aprobacion.numero}: versión u ordinal no numérico")
            continue
        if version < 1 or ordinal < 1:
            errores.append(f"approval_log línea {aprobacion.numero}: versión u ordinal no positivo")
            continue
        versiones = por_id.setdefault(valores["checkId"], {})
        previo = versiones.setdefault(version, ordinal)
        if previo != ordinal:
            errores.append(f"approval_log: el par ({valores['checkId']}, {version}) usa dos ordinales")
    for identificador, versiones in por_id.items():
        ordinales = [versiones[version] for version in sorted(versiones)]
        if ordinales != list(range(1, len(ordinales) + 1)):
            errores.append(f"approval_log: ordinales de VERIFICATION_DEFECT no consecutivos para {identificador}")
        if len(versiones) > 2:
            errores.append(f"approval_log: presupuesto de VERIFICATION_DEFECT agotado para {identificador}")


def _validar_adopcion(anterior: Version, actual: Version, adopcion: Linea,
                      aprobaciones: List[Linea], requiere_aprobacion: bool,
                      fase: str, errores: List[str]) -> None:
    orden = (
        "version_previa", "perfil", "baseline_reutilizado", "proyeccion_ajustada",
        "baseline_actualizado", "estado", "token",
    )
    contexto = f"v{actual.numero}: adopción"
    if not _campos_validos(adopcion, orden, contexto, errores):
        return
    valores = adopcion.valores
    if valores["version_previa"] != str(anterior.numero) or valores["perfil"] != "pertinencia-v1":
        errores.append(f"{contexto}: versión previa o perfil inválido")
    if valores["estado"] not in {"final", "intermedia"}:
        errores.append(f"{contexto}: estado inválido")
    if fase == "final" and valores["estado"] != "final":
        errores.append(f"{contexto}: una adopción intermedia no admite fase final")
    _validar_token(valores["token"], f"{actual.numero}:adopción-pertinencia", contexto, errores)
    aprobacion = _aprobacion_para(aprobaciones, valores["token"], _hash_bloque(actual.bloque),
                                  contexto, requiere_aprobacion, errores)
    if aprobacion is not None and any(clave in aprobacion.valores for clave in
                                     ("checkId", "contract_version", "verification_defect_ordinal")):
        errores.append(f"{contexto}: la aprobación de adopción no lleva par de defecto")
    reutilizados = _lista_ids(valores["baseline_reutilizado"], contexto, errores)
    ajustados = _lista_ids(valores["proyeccion_ajustada"], contexto, errores)
    actualizados = _lista_ids(valores["baseline_actualizado"], contexto, errores)
    if set(anterior.filas) != set(actual.filas):
        errores.append(f"{contexto}: la adopción no conserva el conjunto de ID")
    for identificador in sorted(set(anterior.filas) & set(actual.filas)):
        previa, nueva = anterior.filas[identificador], actual.filas[identificador]
        if (previa.requisito, previa.evidencia, previa.esperado) != \
                (nueva.requisito, nueva.evidencia, nueva.esperado):
            errores.append(f"{contexto}: cambia una columna semántica protegida de {identificador}")
        pertinencia = actual.pertinencias.get(identificador)
        tipo = pertinencia.valores.get("baseline_tipo", "") if pertinencia else ""
        if identificador in reutilizados:
            previo_registro = anterior.registros.get(identificador)
            nuevo_registro = actual.registros.get(identificador)
            if tipo != "otro" or previa.baseline != nueva.baseline or \
                    previo_registro is None or nuevo_registro is None or \
                    previo_registro.texto != nuevo_registro.texto:
                errores.append(f"{contexto}: baseline_reutilizado inválido para {identificador}")
        if previa.comando != nueva.comando:
            if identificador not in ajustados:
                errores.append(f"{contexto}: comando cambia fuera de proyeccion_ajustada para {identificador}")
            elif tipo not in {"fallos-conteo", "fallos-conjunto", "fallos-listado"}:
                errores.append(f"{contexto}: proyeccion_ajustada exige baseline fallos-* para {identificador}")
            else:
                _validar_envoltura(nueva.comando, previa.comando,
                                   f"{contexto}: {identificador}", errores)
        elif identificador in ajustados:
            errores.append(f"{contexto}: proyeccion_ajustada sin cambio para {identificador}")
        if previa.baseline != nueva.baseline and identificador not in actualizados:
            errores.append(f"{contexto}: Baseline cambia fuera de baseline_actualizado para {identificador}")
        if identificador in actualizados and (tipo not in {"fallos-conteo", "fallos-conjunto", "fallos-listado"}
                                               or nueva.baseline not in {"RED", "GREEN_ALREADY"}
                                               or identificador not in actual.registros):
            errores.append(f"{contexto}: baseline_actualizado inválido para {identificador}")
        elif identificador in actualizados and previa.baseline == nueva.baseline:
            errores.append(f"{contexto}: baseline_actualizado sin cambio para {identificador}")
    for conjunto, nombre in ((reutilizados, "baseline_reutilizado"),
                             (ajustados, "proyeccion_ajustada"),
                             (actualizados, "baseline_actualizado")):
        sobran = conjunto - set(actual.filas)
        if sobran:
            errores.append(f"{contexto}: {nombre} refiere ID inexistentes {sorted(sobran)}")


def _validar_transicion(anterior: Version, actual: Version, aprobaciones: List[Linea],
                        requiere_aprobacion: bool, fase: str, primera_congelacion: Optional[int],
                        errores: List[str]) -> None:
    adopcion = actual.adopciones[0] if len(actual.adopciones) == 1 else None
    if len(actual.adopciones) > 1:
        errores.append(f"v{actual.numero}: más de una línea de adopción")
    es_legado = bool(anterior.filas) and not anterior.pertinencias
    if es_legado and adopcion is None:
        errores.append(f"v{actual.numero}: versión vigente legado sin adopción")
    if not es_legado and adopcion is not None:
        errores.append(f"v{actual.numero}: adopción fuera de una transición legado")
    if adopcion is not None:
        _validar_adopcion(anterior, actual, adopcion, aprobaciones,
                          requiere_aprobacion, fase, errores)
    registros: Dict[Tuple[str, str], List[Linea]] = {}
    for linea in actual.reparaciones:
        clave = (linea.valores.get("id", ""), linea.valores.get("operación", ""))
        registros.setdefault(clave, []).append(linea)
    consumidos: Set[Tuple[str, str]] = set()
    faltantes = sorted(set(anterior.filas) - set(actual.filas))
    if faltantes:
        errores.append(f"v{anterior.numero}->v{actual.numero}: desaparecen ID {', '.join(faltantes)}")
    nuevos = sorted(set(actual.filas) - set(anterior.filas))
    if adopcion is not None and nuevos:
        errores.append(f"v{actual.numero}: una adopción no puede agregar cobertura")
    for identificador in nuevos:
        clave = (identificador, "cobertura-agregada")
        candidatas = registros.get(clave, [])
        if len(candidatas) != 1:
            errores.append(f"v{actual.numero}: ID nuevo {identificador} sin cobertura-agregada única")
            continue
        consumidos.add(clave)
        registro = candidatas[0]
        contexto = f"v{actual.numero}: cobertura-agregada de {identificador}"
        _campos_validos(registro, _orden_reparacion("cobertura-agregada"), contexto, errores)
        if registro.valores.get("version_previa") != str(anterior.numero):
            errores.append(f"{contexto}: version_previa inválida")
        token = registro.valores.get("token", "")
        _validar_token(token, f"{actual.numero}:{identificador}:cobertura-agregada", contexto, errores)
        aprobacion = _aprobacion_para(aprobaciones, token, _hash_bloque(actual.bloque), contexto,
                                      requiere_aprobacion, errores)
        if aprobacion is not None and primera_congelacion is not None and aprobacion.numero > primera_congelacion:
            errores.append(f"{contexto}: aprobación posterior al primer congelamiento")
    for identificador in sorted(set(anterior.filas) & set(actual.filas)):
        previa, nueva = anterior.filas[identificador], actual.filas[identificador]
        if previa.requisito != nueva.requisito:
            errores.append(f"v{anterior.numero}->v{actual.numero}: Requisito de {identificador} cambia")
        diferencias: List[Tuple[str, str, Dict[str, str]]] = []
        if previa.esperado != nueva.esperado:
            diferencias.append(("esperado-corregido", "Esperado", {
                "esperado_previo_sha256": _sha(previa.esperado),
            }))
        pert_previa = anterior.pertinencias.get(identificador)
        pert_nueva = actual.pertinencias.get(identificador)
        if pert_previa is not None and pert_nueva is not None and pert_previa.texto != pert_nueva.texto:
            diferencias.append(("pertinencia-corregida", "pertinencia", {
                "pertinencia_previa_sha256": _sha(pert_previa.texto),
            }))
        evidencia_cambia = previa.evidencia != nueva.evidencia
        comando_cambia = previa.comando != nueva.comando
        ajustados = set()
        if adopcion is not None:
            ajustados = _lista_ids(adopcion.valores.get("proyeccion_ajustada", "ninguno"),
                                   f"v{actual.numero}: adopción", errores)
        if (evidencia_cambia or comando_cambia) and not (comando_cambia and identificador in ajustados):
            campos = ("evidencia+comando" if evidencia_cambia and comando_cambia
                      else "evidencia" if evidencia_cambia else "comando")
            huellas = {"campos": campos}
            if evidencia_cambia:
                huellas["evidencia_previa_sha256"] = _sha(previa.evidencia)
            if comando_cambia:
                huellas["comando_previo_sha256"] = _sha(previa.comando)
            diferencias.append(("verificacion-corregida", "Evidencia/Comando", huellas))
            if comando_cambia and _envoltura(previa.comando)[0] is not None:
                _validar_envoltura(nueva.comando, previa.comando,
                                   f"v{actual.numero}: verificacion-corregida de {identificador}",
                                   errores)
        for operacion, etiqueta, huellas in diferencias:
            clave = (identificador, operacion)
            candidatas = registros.get(clave, [])
            if len(candidatas) != 1:
                errores.append(f"v{actual.numero}: {etiqueta} de {identificador} cambia sin {operacion} único")
                continue
            consumidos.add(clave)
            registro = candidatas[0]
            contexto = f"v{actual.numero}: {operacion} de {identificador}"
            _campos_validos(registro, _orden_reparacion(
                operacion, huellas.get("campos", "")), contexto, errores)
            if registro.valores.get("version_previa") != str(anterior.numero):
                errores.append(f"{contexto}: version_previa inválida")
            token = registro.valores.get("token", "")
            _validar_token(token, f"{actual.numero}:{identificador}:{operacion}", contexto, errores)
            for clave_huella, valor in huellas.items():
                if registro.valores.get(clave_huella) != valor:
                    errores.append(f"{contexto}: {clave_huella} no coincide")
            aprobacion = _aprobacion_para(aprobaciones, token, _hash_bloque(actual.bloque),
                                          contexto, requiere_aprobacion, errores)
            if aprobacion is not None and primera_congelacion is not None and aprobacion.numero > primera_congelacion:
                valores = aprobacion.valores
                if valores.get("checkId") != identificador or \
                        valores.get("contract_version") != str(actual.numero) or \
                        not valores.get("verification_defect_ordinal"):
                    errores.append(f"{contexto}: aprobación post-congelamiento sin par de defecto coherente")
    for clave, candidatas in registros.items():
        identificador, operacion = clave
        if operacion not in OPERACIONES:
            errores.append(f"v{actual.numero}: operación fuera de enum para {identificador}")
        if len(candidatas) != 1:
            errores.append(f"v{actual.numero}: registro duplicado {operacion} de {identificador}")
        if clave not in consumidos:
            errores.append(f"v{actual.numero}: registro {operacion} de {identificador} sin diferencia")


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[3] not in {"candidate", "final"}:
        print(USO, file=sys.stderr)
        return 2
    contrato_ruta, log_ruta, fase = sys.argv[1:]
    try:
        contrato_texto = Path(contrato_ruta).read_text(encoding=ENCODING)
    except (OSError, UnicodeError):
        print("GUARD:contrato-inaccesible", file=sys.stderr)
        return 1
    try:
        log_texto = Path(log_ruta).read_text(encoding=ENCODING)
    except (OSError, UnicodeError):
        print("GUARD:approval-log-inaccesible", file=sys.stderr)
        return 1
    try:
        tabla = _cargar_dependencia("_tabla.py", "cross_implement_contrato_invariantes_tabla")
    except RuntimeError:
        print("ARNES:contrato-invariantes dependencia _tabla.py no cargable", file=sys.stderr)
        return 99
    try:
        cadena = _cargar_dependencia(
            "contrato-cadena.py", "cross_implement_contrato_invariantes_cadena")
    except RuntimeError:
        print("ARNES:contrato-invariantes dependencia contrato-cadena.py no cargable", file=sys.stderr)
        return 99
    versiones = _parsear_versiones(contrato_texto, cadena, tabla)
    if not versiones:
        print("GUARD:contrato-direccional sin versiones", file=sys.stderr)
        return 1
    errores: List[str] = []
    aprobaciones = [
        linea for linea in _extraer(log_texto.splitlines(), "- ")
        if linea.valores.get("paso") == "aprobar-reparación"
        or "`paso: aprobar-reparación`" in linea.texto
    ]
    _validar_aprobaciones(aprobaciones, errores)
    _validar_pares_defecto(aprobaciones, errores)
    congelaciones = [indice for indice, linea in enumerate(log_texto.splitlines(), 1)
                     if "`paso: congelar`" in linea]
    primera_congelacion = congelaciones[0] if congelaciones else None
    for indice, version in enumerate(versiones):
        _validar_dialecto(version, errores)
        _validar_pertinencias(version, indice == len(versiones) - 1 or bool(version.pertinencias), errores)
    vigente = versiones[-1]
    adopcion_vigente = vigente.adopciones[0] if len(vigente.adopciones) == 1 else None
    _validar_baseline(vigente, fase, adopcion_vigente, errores)
    for indice in range(1, len(versiones)):
        es_vigente = indice == len(versiones) - 1
        adopcion = versiones[indice].adopciones
        fase_transicion = fase if es_vigente else (
            "candidate" if len(adopcion) == 1 and
            adopcion[0].valores.get("estado") == "intermedia" else "final")
        _validar_transicion(
            versiones[indice - 1], versiones[indice], aprobaciones,
            not (es_vigente and fase == "candidate"), fase_transicion,
            primera_congelacion, errores,
        )
    prefijos_contrato = {
        TOKEN_RE.fullmatch(linea.valores.get("token", "")).group(1)
        for version in versiones
        for linea in version.reparaciones + version.adopciones
        if TOKEN_RE.fullmatch(linea.valores.get("token", "")) is not None
    }
    for aprobacion in aprobaciones:
        coincidencia = TOKEN_RE.fullmatch(aprobacion.valores.get("token", ""))
        if coincidencia is not None and coincidencia.group(1) not in prefijos_contrato:
            errores.append(
                f"approval_log línea {aprobacion.numero}: aprobación sin reparación o adopción")
    if len(versiones) == 1 and not vigente.pertinencias:
        errores.append(f"v{vigente.numero}: versión vigente legado sin adopción")
    if errores:
        for error in errores:
            print("GUARD:contrato-direccional " + error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
