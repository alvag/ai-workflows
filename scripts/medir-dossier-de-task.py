#!/usr/bin/env python3
"""Arma el dossier de cada task y mide su tamaño contra el paquete que hoy se manda leer.

**Falla ruidoso a propósito.** Un dossier incompleto se lee igual que uno completo, así que cada
pieza que la task cita y no se encuentra es un ERROR con nombre, nunca una omisión silenciosa. Ese
es el riesgo 7 de la propuesta —«un patrón ingenuo ya falló durante esta medición»— y se reprodujo
otra vez el 2026-08-12: un extractor de AC devolvió cero para una spec entera y el cero pasó por
respuesta.

Control positivo: antes de armar nada, extrae **todos** los AC que la spec declara y exige que
ninguno venga vacío. Sin eso, un extractor roto mide dossiers chiquitos y parece un éxito.
"""
import re
import sys
from pathlib import Path

# Las specs de este repo declaran los AC de CINCO formas distintas, medidas sobre los 21 flujos
# archivados. Un patrón que cubra menos devuelve cero para el resto — y cero es indistinguible de
# «no hay AC» si nadie lo mira:
#   - **AC-18:** …                                  (id + dos puntos)
#   - **AC-34** *(capacidad nueva)***:** …          (id + nota + dos puntos)
#   - **AC-1 — Selección de backend previa:** …     (id + raya + título + dos puntos)
#   - **AC-1 — Metadatos operativos, no estado.**   (id + raya + título + punto)
#   **AC-1** — No queda rastro de la vía…           (SIN viñeta)
# Lo invariante es: arranque de línea, viñeta opcional, `**`, el id, y **un delimitador de
# declaración** — `:`, el cierre `**`, o una raya—. El delimitador NO es cosmética: sin él, una línea
# de prosa en negrita como `**AC-24bis no es AC-24 repetido, y la diferencia importa.**` entra como
# declaración y el extractor termina con dos bloques para el mismo id, uno de ellos falso.
INICIO_DE_AC = re.compile(r"^(?:- )?\*\*(AC-\d+bis|AC-\d+)(?=\*\*|:| —|\s*\*\*?:)", re.M)
# El corte no puede ser «el próximo ítem de lista»: la forma sin viñeta nunca lo encontraría y se
# tragaría el resto del documento. Corta en la próxima declaración o en el próximo heading.
CUALQUIER_ITEM = re.compile(r"^(?:- )?\*\*(?:AC-\d+)|^#{1,6} ", re.M)
FILA_DE_CONTRATO = re.compile(r"^\| (V\d+[a-z]?) \|", re.M)
INICIO_DE_TASK = re.compile(r"^- \[[x ]\] \*\*(T\d+b?) —", re.M)
CAMPO = lambda n: re.compile(rf"^  - \*\*{n}:?\*?\*?:?\*?\*? ?(.*(?:\n(?:    |  [^-]).*)*)", re.M)


# El apéndice de fidelidad repite cada criterio heredado, **literal como venía del flujo padre**.
# Son declaraciones válidas y no vigentes: lo que la task tiene que leer es el criterio de las
# secciones de contenido. Medido en esta spec: 13 de 16 AC aparecen dos veces, y un diccionario por
# id se queda con el último — el del apéndice— sin decir nada. Para AC-27 eso cambia 4.409 bytes por
# 355. Por eso el corte es explícito y las declaraciones se cuentan.
CORTE_DE_APENDICE = re.compile(r"^## Ap[eé]ndice de fidelidad", re.M)


def bloques_por_id(texto: str, inicio: re.Pattern, fin: re.Pattern,
                   contar: dict[str, int] | None = None) -> dict[str, str]:
    """Cada bloque va desde su encabezado hasta el próximo ítem de primer nivel.

    Un id declarado dos veces NO se colapsa en silencio: se queda con la primera declaración —la
    vigente— y se registra en `contar` para que quien llame pueda reportarlo."""
    salida: dict[str, str] = {}
    for m in inicio.finditer(texto):
        ident = m.group(1)
        if contar is not None:
            contar[ident] = contar.get(ident, 0) + 1
        if ident in salida:
            continue
        siguiente = fin.search(texto, m.end())
        salida[ident] = texto[m.start():siguiente.start() if siguiente else len(texto)].strip()
    return salida


def control_positivo(spec: str) -> list[str]:
    """Todos los AC declarados salen no vacíos. Es lo que caza al extractor que devuelve cero."""
    ids = INICIO_DE_AC.findall(spec)
    veces: dict[str, int] = {}
    bloques = bloques_por_id(spec, INICIO_DE_AC, CUALQUIER_ITEM, veces)
    fallas = []
    if not ids:
        return ["el extractor no encontró NINGÚN AC en la spec: el patrón no reconoce su formato"]
    for i in sorted(bloques):
        if not bloques[i] or len(bloques[i]) < 40:
            fallas.append(f"`{i}` se declara y su bloque salió vacío o trunco")
    # El corte del apéndice tiene que existir si hay duplicados, o el criterio de «la primera gana»
    # es una coincidencia de orden y no una regla.
    dup = {i: n for i, n in veces.items() if n > 1}
    if dup and not CORTE_DE_APENDICE.search(spec):
        fallas.append(f"{len(dup)} AC declarados más de una vez y la spec no tiene apéndice de "
                      f"fidelidad: la regla «la primera gana» no está fundada acá")
    corte = CORTE_DE_APENDICE.search(spec)
    for i in sorted(dup):
        pos = [m.start() for m in INICIO_DE_AC.finditer(spec) if m.group(1) == i]
        if corte and any(p < corte.start() for p in pos[1:]):
            fallas.append(f"`{i}` tiene una segunda declaración ANTES del apéndice: no es una copia "
                          f"de fidelidad y elegir la primera puede estar tomando la equivocada")
    print(f"  {len(dup)} AC con declaración repetida en el apéndice de fidelidad; "
          f"se toma la vigente")
    return fallas


def main() -> int:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1
                else ".plans/archived/instrumento-y-baseline")
    spec = (raiz / "spec.md").read_text(encoding="utf-8")
    plan = (raiz / "plan.md").read_text(encoding="utf-8")
    tasks = (raiz / "tasks.md").read_text(encoding="utf-8")
    paquete = sum(len(t.encode()) for t in (spec, plan, tasks))

    fallas = control_positivo(spec)
    ac = bloques_por_id(spec, INICIO_DE_AC, CUALQUIER_ITEM)
    print(f"control positivo: {len(ac)} AC extraídos"
          + (f" · {len(fallas)} FALLAS" if fallas else " · todos no vacíos"))
    for f in fallas:
        print(f"  FALLA {f}")
    if fallas:
        return 1

    filas = {m.group(1): plan[m.start():plan.find("\n", m.start())]
             for m in FILA_DE_CONTRATO.finditer(plan)}
    enfoque = plan[plan.find("## Enfoque"):plan.find("\n## ", plan.find("## Enfoque") + 5)]

    bloques_de_task = bloques_por_id(tasks, INICIO_DE_TASK, INICIO_DE_TASK)
    produce = {}
    for tid, cuerpo in bloques_de_task.items():
        m = CAMPO("Produce").search(cuerpo)
        if m:
            produce[tid] = m.group(0).strip()

    print(f"\npaquete que hoy se manda leer: {paquete:,} b · enfoque del plan: {len(enfoque.encode()):,} b\n")
    print(f"{'task':>5} {'dossier':>9} {'AC':>3} {'V':>3} {'cons':>5} {'reducción':>10}")
    print("-" * 42)
    total, problemas, medidos = 0, [], []
    for tid, cuerpo in bloques_de_task.items():
        piezas = [cuerpo, enfoque]
        m = CAMPO("AC").search(cuerpo)
        ids_ac = re.findall(r"AC-\d+bis|AC-\d+", m.group(1)) if m else []
        for i in ids_ac:
            if i not in ac:
                problemas.append(f"{tid} cita `{i}` y la spec no lo declara")
                continue
            piezas.append(ac[i])
        m = CAMPO("Verificar").search(cuerpo)
        ids_v = re.findall(r"V\d+[a-z]?", m.group(1)) if m else []
        for i in ids_v:
            if i not in filas:
                problemas.append(f"{tid} cita la fila `{i}` y el contrato no la tiene")
                continue
            piezas.append(filas[i])
        m = CAMPO("Consume").search(cuerpo)
        consumidas = sorted(set(re.findall(r"\bT\d+b?\b", m.group(1)))) if m else []
        for t in consumidas:
            if t in produce:
                piezas.append(produce[t])
        dossier = sum(len(p.encode()) for p in piezas)
        total += dossier
        medidos.append(dossier)
        print(f"{tid:>5} {dossier:>9,} {len(ids_ac):>3} {len(ids_v):>3} {len(consumidas):>5} "
              f"{paquete/dossier:>9.1f}x")

    print("-" * 42)
    n = len(medidos)
    if not n:
        print("FALLA  no se parseó ninguna task: el `tasks.md` de este flujo no usa el formato\n"
              "       `- [x] **T<n> — …`. Cero tasks no es un dossier chico, es un extractor que no\n"
              "       reconoce el artefacto — y sin este corte saldría por división por cero.")
        return 1
    print(f"{'':>5} {total//n:>9,} {'':>3} {'':>3} {'':>5} {paquete/(total/n):>9.1f}x  (promedio)")
    print(f"\nHoy   : {n} tasks x {paquete:,} b = {n*paquete/1e6:>6.1f} MB de ingesta")
    print(f"Dossier: la suma de los {n} dossiers = {total/1e6:>6.1f} MB")
    print(f"Peor caso (task más grande): {paquete/min(medidos):.1f}x · "
          f"mejor: {paquete/max(medidos):.1f}x")
    if problemas:
        print(f"\nREFERENCIAS QUE NO RESUELVEN — {len(problemas)}:")
        for p in problemas:
            print(f"  {p}")
        return 1
    print("\nTodas las referencias citadas resuelven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
