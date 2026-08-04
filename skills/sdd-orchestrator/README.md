# sdd-orchestrator

Skill de **Spec-Driven Development multi-repo**. Coordina un cambio con un objetivo común que se reparte entre varios repos git ubicados bajo una carpeta contenedora (típicamente una carpeta que **no** es un repo git, p. ej. un `backend/` con microservicios).

Es una capa de **orquestación sobre `sdd-flow`**: no reimplementa el ciclo SDD. Arma la spec madre y reparte el trabajo, pero la implementación de cada repo la ejecuta `sdd-flow` por delegación. `sdd-orchestrator` nunca modifica `sdd-flow`.

## Qué hace

1. **Diseño centralizado (con gates):** consolida el objetivo, detecta y te propone los repos involucrados (tú confirmas), escribe una `master-spec.md` con criterios de aceptación globales y los contratos entre servicios, y reparte el trabajo en un sub-plan por repo (con dependencias declarables). Paras en cada gate.
2. **Ejecución paralela (delegada):** lanza un agente por repo que corre `/sdd-flow implement` en su `.plans/<id>/`. Cada repo crea su rama, implementa, corre tests/build, verifica sus AC y **frena antes de commitear**. Respeta dependencias (DAG) y aísla los fallos en cascada. Opcional: **modo inline** ("ejecuta `<repo>` acá" o `execution_mode: inline` en el manifest) para ejecutar un repo en la propia sesión del orquestador, de a uno — útil con un solo repo elegible o para seguir la implementación de cerca.
3. **Cierre centralizado (tú al mando):** reporte consolidado y luego revisión + commit + push por repo, controlado por ti.

## Cuándo usarla

- Un **mismo objetivo** cruza **2 o más repos** bajo una carpeta contenedora (microservicios relacionados).

## Cuándo NO usarla

- **Un solo repo:** usa `sdd-flow` directamente.
- **Cambios heterogéneos** sin objetivo común (sería un "batch runner", no el caso de esta skill).
- Necesitas coordinar el **deploy/release** entre servicios: queda fuera de alcance (la skill llega hasta commit/push por repo).

## Requisitos

- **`sdd-flow` instalada** en el entorno (dependencia dura: el orquestador delega en ella).
- Una **carpeta contenedora** con ≥2 repos git como subdirectorios.
- Capacidad de **subagentes en paralelo** en el entorno (recomendado; mejora mucho el fan-out). Sin ella, el orquestador serializa.

## Instalación

Copia la carpeta `sdd-orchestrator/` al directorio de skills de tu entorno (junto a `sdd-flow/`):

```
<skills>/
├─ sdd-flow/
└─ sdd-orchestrator/
   ├─ SKILL.md
   ├─ reference.md
   └─ README.md
```

## Uso

Parado en la carpeta contenedora (p. ej. `backend/`):

```
/sdd-orchestrator
```

Luego, en lenguaje natural: describe el objetivo y los servicios que crees que toca (y, si quieres, un prefijo de rama para toda la orquestación: "con prefijo de rama feature/"). El flujo:

1. Te propone los repos involucrados → confirmas.
2. Escribe la `master-spec.md` → la apruebas (GATE).
3. Reparte en sub-planes por repo → los apruebas (GATE).
4. Implementa en paralelo, frenando antes de commitear.
5. Cierras tú: revisión + commit (con el mecanismo inline de `sdd-flow`) + push por repo.
6. Cuando confirmas que todo está probado: "archiva `<id>`" mueve la orquestación a `.sdd/archived/<id>/` (sale del listado y libera los locks). Para cancelar una a medias: "aborta `<id>`" (pausa o descarta por repo, y archiva el manifest).

> **Prefijo de rama:** el prefijo de la orquestación aplica a todos los repos, salvo que un repo tenga su propio `branch_prefix` en `.specify/config.yml` (ese gana, p. ej. por su CI/CD). Sin prefijo, cada repo usa el semántico.

> **Config por repo (opcional):** cada repo puede inicializarse con `/sdd-flow init` (parado en el repo) para fijar su `.specify/config.yml` (stack, test/build, `branch_prefix`). Eso hace el reparto más determinista, pero no es obligatorio: sin config, el orquestador autodetecta cada repo.

Para retomar una orquestación a medias: `/sdd-orchestrator` y "retoma `<id>`" (o "¿en qué quedé?" para listar las activas).

### Varias features a la vez

Cada feature usa su propio `<id>`, así que conviven sin pisarse. Si dos features tocan el **mismo** repo, un **lock cooperativo** lo detecta y te ofrece esperar, pausar la otra, o excluir ese repo. Los repos no compartidos siguen en paralelo.

## Contrato de verificación y AC de integración

Cada `plan.md` por repo hereda el **contrato de verificación** de `sdd-flow` —el mismo esquema, por
puntero, sin plantilla propia—.

Los AC `[integration]` no viven en el contrato de ningún repo: viven en un **contrato de integración**
propio del orquestador, y el contrato de cada repo los referencia en solo-lectura. Es la forma
contractual de la regla que ya regía: ninguna integración se da por cumplida en un repo.

Ese contrato cubre además el trabajo que no pertenece a ningún repo —lo que hay que cerrar antes de
repartir, y lo que solo tiene sentido con todos los servicios arriba—, que el `manifest.yml` declara
como `orchestration_tasks`. Cada una de esas tareas tiene ahí su fila donde probar el cierre, cubra
un AC de integración o sea auxiliar; y como el conjunto de filas de un contrato no admite altas
posteriores, nace entero y temprano:

- El contrato de integración cubre el cierre de toda tarea y se congela en la Fase 1.

El mismo gate que habilita ese congelamiento vuelve a correr al abrir la Fase 3, esta vez para
revalidar la versión vigente antes de ejecutar ninguna evidencia; y la agregación final **no puede
dar verde** con filas ausentes o bloqueadas.

Nada de eso se lee del estado final. Un repo que se despacha, un gate que se cierra, un lock que se
libera: cada intento deja rastro propio.

- La orquestación registra sus transiciones en una bitácora local.

El `manifest.yml` dice en qué estado quedó cada cosa; la bitácora, los intentos de moverlo —quién,
cuándo y con qué resultado—, incluidos los rechazados. De ahí sale, entre otras cosas, si la
evidencia de una tarea sigue fresca en el momento de cerrarla.

El detalle —los campos de una tarea, la forma de un evento, las precondiciones de un cierre— vive en
`SKILL.md` y `reference.md`; acá va el mapa.

## Artefactos (todos locales, no se trackean)

- `<contenedora>/.sdd/<id>/master-spec.md` y `manifest.yml` — la capa de orquestación.
- `<repo>/.plans/<id>/` — un flujo `sdd-flow` normal y autónomo por repo.
