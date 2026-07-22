# ADR: manifest caller-owned para corridas cross-model

Fecha: 2026-07-22
Estado: aceptado
Alcance: Fases 0 y 1 del programa cross-model

## Contexto

El kernel `cross-model-orca` conoce cada intento de transporte por separado, pero no observa la
invocación completa `desired → orca-session → fallback cli → effective`. Esa secuencia pertenece
al caller. Sin un registro caller-owned no se puede distinguir una corrida terminada de un proceso
muerto a mitad de camino ni medir fallback, duración y recovery sin inferencias.

Esta decisión agrega un protocolo behavior-neutral: documenta los contratos y crea un helper
independiente. No integra el manifest en las skills ni modifica kernel, harvest, contención, dedup,
recovery o exit codes.

## Decisión

### 1. Invariantes congelados

1. **Conductor autoritativo.** El conductor define el contrato, decide el estado final, revisa los
   artefactos y ejecuta la verificación. El secundario y el transporte aportan evidencia; no toman
   autoridad sobre el cierre.
2. **Un escritor por working tree.** Nunca se habilita un segundo intento de escritura si el cierre
   del escritor anterior no fue demostrado. `recovered: false` se conserva como dato del kernel y
   solo una resolución explícita puede desbloquear la FSM.
3. **Compatibilidad CLI/Orca.** `orca-session` y `cli` son transportes intercambiables del mismo
   workflow y se registran, en orden, dentro de un único `attempts[]` propiedad del caller. El
   manifest no cambia el contrato ni los exit codes de ninguno.

### 2. Schema v1 de `run.json`

`schemaVersion` vale el entero `1`. El manifest terminal tiene este field-set mínimo:

```json
{
  "schemaVersion": 1,
  "runId": "uuid-en-formato-slug",
  "workflow": "cross-implement",
  "mode": "implement",
  "role": "builder",
  "family": "claude",
  "model": null,
  "transport": {
    "desired": "auto",
    "effective": "cli",
    "fallbackUsed": true
  },
  "attempts": [
    {
      "transport": "orca-session",
      "access": "write",
      "startedAt": "2026-07-22T12:00:00.000Z",
      "finishedAt": "2026-07-22T12:00:01.000Z",
      "outcome": "failed",
      "code": 4,
      "recovered": true
    },
    {
      "transport": "cli",
      "access": "write",
      "startedAt": "2026-07-22T12:00:02.000Z",
      "finishedAt": "2026-07-22T12:00:03.000Z",
      "outcome": "completed",
      "code": 0
    }
  ],
  "timing": {
    "startedAt": "2026-07-22T12:00:00.000Z",
    "finishedAt": "2026-07-22T12:00:04.000Z",
    "durationMs": 4000
  },
  "outcome": {
    "status": "ready",
    "code": 0
  },
  "usage": {
    "inputTokens": null,
    "outputTokens": null,
    "costUsd": null,
    "source": "unavailable"
  },
  "artifacts": [
    {
      "kind": "report",
      "path": "result.md",
      "sha256": "hexadecimal-de-64-caracteres"
    }
  ],
  "ext": {
    "cross-implement": {
      "fixRounds": 1,
      "verificationReruns": 0,
      "triage": []
    }
  }
}
```

#### Identidad, enums y tipos

- Todo string core que funciona como identificador es un enum o un slug de 1 a 64 caracteres con
  patrón `[a-z0-9-]`. La regla incluye `runId`, `workflow`, `mode`, `role`, `family`, `kind`,
  `checkId` y `writerResolution.resolvedBy`.
- `workflow` v1 es `cross-implement`; `transport` es `orca-session | cli`;
  `transport.desired` es `auto | orca-session | cli`; `access` es `read-only | write`.
- `role` describe el rol del workflow. `access` describe la capacidad de seguridad del intento.
  Los guards de escritor dependen exclusivamente de `access`.
- `attempts[].outcome` es `completed | failed | aborted | unterminated` y
  `attempts[].code` es un entero no negativo o `null` cuando no hubo exit code observable.
- `attempts[].recovered`, si está presente, es booleano. Un attempt `write` con outcome
  `unterminated` debe declararlo explícitamente; no existe default silencioso.
- `outcome.status` es `ready | failed | aborted`; `outcome.code` es entero no negativo o `null`.
- `model` es `null` en v1: esta fase no instrumenta identidad efectiva del modelo.
- Los timestamps son ISO-8601 y `durationMs` es la diferencia no negativa entre inicio y cierre.
- El escritor v1 rechaza campos desconocidos en las estructuras recibidas. No existe ningún campo
  para prompt, razonamiento interno ni contenido libre.

#### `usage`

`usage.source` es `unavailable | provider`. Con `unavailable`, las tres métricas deben ser `null`.
Con `provider`, tokens son enteros no negativos y costo es un número no negativo. `estimated` no
es una fuente válida y una corrida nunca mezcla métricas reportadas con estimaciones.

#### `artifacts`

Cada entrada contiene exactamente `{kind, path}`. `path` es relativo al directorio del
manifest y debe apuntar a un archivo existente cuyo `realpath` permanezca dentro de ese directorio;
se rechazan rutas absolutas, escapes con `..` y symlinks hacia afuera. El helper calcula `sha256`
con `node:crypto` leyendo el archivo por bloques. El terminal guarda únicamente
`{kind, path, sha256}`, nunca el contenido.

#### `ext.cross-implement`

Los workflows no registrados se rechazan. El único schema v1 es:

```text
ext.cross-implement = {
  fixRounds: integer >= 0,
  verificationReruns: integer >= 0,
  triage: Array<{
    checkId: slug <= 64 [a-z0-9-],
    class: IMPLEMENTATION_DEFECT | VERIFICATION_DEFECT | ENVIRONMENT_FAILURE | DESIGN_GAP,
    consumedRound: boolean
  }>
}
```

No se admiten claves adicionales ni strings de texto libre. Parent/child runs y cualquier otro
workflow quedan fuera de v1.

#### Estado parcial y commit terminal

`start` crea `<runId>.partial.json` antes del primer intento. El partial contiene identidad,
`transport.desired`, `attempts`, solo `timing.startedAt`, usage inicial honesto y `ext`; nunca
contiene `transport.effective`, `transport.fallbackUsed`, `timing.finishedAt`, `durationMs`,
`outcome` terminal ni `artifacts` terminales.

Cada transición mutable relee el partial y lo reemplaza con `write tmp → rename`. `finish` valida
todo y construye el terminal completo en memoria; lo escribe en un temporal separado, publica
`<runId>.json` por rename y solo entonces elimina el partial. Por lo tanto:

- un partial sin terminal significa exactamente `incomplete`, nunca éxito;
- si terminal y partial coexisten por un crash entre rename y unlink, el terminal tiene
  precedencia;
- el terminal es inmutable;
- `finish` repetido es idempotente-limpiador: no reescribe el terminal y elimina el partial
  huérfano;
- `attempt-start`, `attempt-finish` y `resolve-writer` rechazan un `runId` terminal.

#### FSM de attempts y protección del escritor

- Solo puede existir un attempt abierto.
- Un attempt nuevo después de `completed` se rechaza.
- Se permiten retries del mismo transporte.
- `cli → orca-session` se rechaza; el único cambio de transporte permitido es
  `orca-session → cli`.
- `fallbackUsed` es `true` si y solo si existe un attempt `cli` posterior a un attempt
  `orca-session` no exitoso. El conteo de attempts no interviene.
- Un attempt `write` no exitoso con `recovered: false` bloquea tanto `attempt-start` como
  `finish`, sin importar si terminó `failed`, `aborted` o `unterminated`.
- Un `failed` de escritura sin campo `recovered` no bloquea: representa el caso donde el kernel no
  llegó a crear una sesión escritora.
- `resolve-writer` solo actúa sobre ese bloqueo y agrega
  `writerResolution: {resolvedBy, resolvedAt}`. Nunca modifica el `recovered: false` original.

#### Derivación normativa del cierre

| Cierre solicitado | `transport.effective` | `fallbackUsed` | `outcome.status` |
|---|---|---|---|
| Éxito en primer attempt | Transporte del `completed` | `false` | `ready` |
| Éxito tras fallo(s) | Transporte del `completed` | Regla por predecesor | `ready` |
| Todos los attempts sin éxito | `null` | Regla por predecesor | `failed` |
| Aborto con al menos un attempt cerrado | Transporte exitoso previo o `null` | Regla por predecesor | `aborted` |
| Cero attempts | `null` | `false` | Solo `aborted` |

`ready` sin attempt `completed`, `failed` con un attempt `completed` y cualquier cierre distinto
de `aborted` con cero attempts son combinaciones incoherentes y se rechazan. El `code` terminal
proviene del attempt exitoso cuando existe; en caso contrario, del último attempt, o `null` con
cero attempts.

### 3. Schema v1 del verification contract

El verification contract es declarativo, se congela antes del dispatch y conserva este formato:

```markdown
## Verification contract

schemaVersion: 1

| ID | Requirement | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| V1 | AC-1 | test | node --test path/to/test.mjs | exit 0 | RED |
```

Normas v1:

- cada fila enlaza un requisito con evidencia, un comando u observación reproducible, el resultado
  esperado y el baseline previo al dispatch;
- `Baseline` es exactamente `RED | GREEN_ALREADY | NOT_APPLICABLE | BLOCKED`;
- un baseline verde no demuestra el cambio: el conductor lo adjudica por separado;
- el implementador no modifica el contrato congelado;
- el conductor repite la evidencia final y conserva autoridad sobre el resultado;
- el schema define formato, no obliga a generar un gate ejecutable.

### 4. Política de evolución aditiva

El cabo “v1.x” queda resuelto sin versión menor numérica:

- `schemaVersion` permanece en `1` para adiciones compatibles;
- todo lector v1 debe aplicar **must-ignore** a campos desconocidos y leer únicamente los que
  comprende;
- se prohíben lectores que exijan un field-set cerrado para consumir manifests de la misma major;
- el helper escritor v1 sigue validando estrictamente sus propias entradas para impedir contenido
  no tipado; esa disciplina de escritura no contradice la tolerancia de lectura;
- agregar un campo opcional, una nueva procedencia tipada o un schema `ext.<workflow>` registrado es
  aditivo y no incrementa `schemaVersion`;
- eliminar o renombrar campos, cambiar tipos/semántica, volver obligatorio un campo nuevo o alterar
  una derivación existente es breaking y exige incrementar `schemaVersion`.

Así, “compatible con v1” significa que un lector que conoce el field-set aquí definido puede
extraerlo con la misma semántica aunque el documento contenga adiciones posteriores.

### 5. Matriz normativa de procedencia

| Ruta | Procedencia normativa | Condición |
|---|---|---|
| `schemaVersion` | Helper caller-owned | Siempre |
| `runId` | `crypto.randomUUID()` del helper | Siempre |
| `workflow`, `mode`, `role`, `family` | Caller, validados por schema | Siempre |
| `model` | `null` por falta de instrumentación | v1 |
| `transport.desired` | Política elegida por el caller | Siempre |
| `attempts[].transport`, `attempts[].access` | Caller al iniciar el intento | Siempre |
| `attempts[].startedAt`, `attempts[].finishedAt` | Reloj del helper | Siempre |
| `attempts[].outcome` | Clasificación explícita del caller sobre el resultado observado | Siempre |
| `attempts[].code` | Campo `code` del JSON del kernel | Si `transport = orca-session` |
| `attempts[].code` | Exit code del proceso | Si `transport = cli` |
| `attempts[].code` | `null` | Si no hubo exit code observable |
| `attempts[].recovered` | Campo `recovered` del JSON del kernel | Si `transport = orca-session` y el kernel lo reportó |
| `attempts[].writerResolution.*` | Intervención explícita del caller/humano + reloj del helper | Solo tras `recovered: false` |
| `transport.effective` | Derivado por el helper del attempt `completed` | Al cerrar |
| `transport.fallbackUsed` | Derivado por predecesor `orca-session` no exitoso antes de `cli` | Al cerrar |
| `timing.*` | Reloj del helper; duración por diferencia | Siempre |
| `outcome.status` | Solicitud del caller validada contra attempts | Al cerrar |
| `outcome.code` | Derivado del attempt exitoso o del último attempt | Al cerrar |
| `usage.*` | Provider o ausencia declarada por `usage.source` | Por corrida |
| `artifacts[].kind`, `artifacts[].path` | Caller | Al cerrar |
| `artifacts[].sha256` | Bytes del archivo calculados con `node:crypto` | Al cerrar |
| `ext.cross-implement.*` | Caller, validado contra schema enumerado | Workflow `cross-implement` |

Solo `usage` lleva `source` por corrida porque su procedencia puede variar. Si otra métrica adquiere
procedencia variable, su campo `source` se agrega de manera aditiva; no se duplica procedencia fija
en cada manifest.

### 6. Baseline de la suite

- Fecha: **2026-07-22**.
- Comando desde la raíz: `node --test skills/cross-model-orca/assets/test/*.test.mjs`.
- Runner antes de agregar los tests del manifest: **tests 103 · pass 103 · fail 0 · cancelled 0 ·
  skipped 0 · todo 0**.
- Exit code: **0**.

Este conteo es el baseline de regresión. Los tests agregados por esta decisión se suman; no
reemplazan ni reinterpretan los 103 preexistentes.

## Consecuencias

- Un crash deja evidencia incompleta honesta y nunca un falso éxito.
- El fallback completo se vuelve observable sin modificar el transporte.
- La protección de doble escritor queda anclada en el dato `recovered` del kernel y en una
  intervención separada, auditable.
- El schema evita transportar prompts o razonamiento, pero exige registrar schemas nuevos antes de
  ampliar `ext`.
- La integración real en `cross-implement`, el uso operativo del verification contract, lifecycle
  events, artifact protocol completo, perfiles y otros workflows quedan para fases posteriores.
