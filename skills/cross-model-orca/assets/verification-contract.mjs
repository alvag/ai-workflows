import { Buffer } from 'node:buffer';

export const MAX_CONTRACT_BYTES = 1024 * 1024;

const COLUMNS = [
  'ID',
  'Requirement',
  'Evidence',
  'Command/observation',
  'Expected',
  'Baseline',
];
const EVIDENCE_TYPES = new Set(['test', 'build', 'inspección', 'manual']);
const BASELINE_STATES = new Set(['RED', 'GREEN_ALREADY', 'NOT_APPLICABLE', 'BLOCKED']);
const SLUG_PATTERN = /^[a-z0-9-]{1,64}$/;
const VERSION_PATTERN = /^## v([1-9][0-9]*)$/;
const ISO_8601_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const ADJUDICATION_MARKER = ' · adjudicación: ';
const JUSTIFICATION_MARKER = ' · justificación: ';

function fail(message, lineNumber) {
  const suffix = lineNumber === undefined ? '' : ` (línea ${lineNumber})`;
  throw new Error(`${message}${suffix}.`);
}

function skipBlank(lines, start) {
  let index = start;
  while (index < lines.length && lines[index].trim() === '') index++;
  return index;
}

function assertSlug(value, label, lineNumber) {
  if (!SLUG_PATTERN.test(value)) {
    fail(`${label} debe ser un slug de 1 a 64 caracteres [a-z0-9-]`, lineNumber);
  }
}

function parseTableCells(line, lineNumber) {
  const trimmed = line.trim();
  if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) {
    fail('La fila de tabla debe empezar y terminar con |', lineNumber);
  }
  const pieces = trimmed.split('|');
  if (pieces.length !== COLUMNS.length + 2) {
    fail('La fila de tabla contiene un pipe en una celda o un número de columnas inválido', lineNumber);
  }
  return pieces.slice(1, -1).map((cell) => cell.trim());
}

function assertExactColumns(cells, lineNumber) {
  if (cells.some((cell, index) => cell !== COLUMNS[index])) {
    fail(`La tabla debe usar exactamente las columnas ${COLUMNS.join(' · ')}`, lineNumber);
  }
}

function assertSeparator(cells, lineNumber) {
  if (cells.some((cell) => cell !== '---')) {
    fail('El separador de la tabla debe contener --- en sus seis columnas', lineNumber);
  }
}

function parseRow(line, lineNumber) {
  const cells = parseTableCells(line, lineNumber);
  if (cells.some((cell) => cell.length === 0)) {
    fail('Las celdas de la tabla no pueden estar vacías', lineNumber);
  }
  const [id, requirement, evidence, commandOrObservation, expected, baseline] = cells;
  assertSlug(id, 'El ID de fila', lineNumber);
  if (!EVIDENCE_TYPES.has(evidence)) {
    fail(`Evidence inválido: ${evidence}`, lineNumber);
  }
  if (!BASELINE_STATES.has(baseline)) {
    fail(`Baseline inválido: ${baseline}`, lineNumber);
  }
  return {
    id,
    requirement,
    evidence,
    commandOrObservation,
    expected,
    baseline,
  };
}

function takeSuffixValue(rest) {
  const suffixIndexes = [
    rest.indexOf(ADJUDICATION_MARKER),
    rest.indexOf(JUSTIFICATION_MARKER),
  ].filter((index) => index >= 0);
  if (suffixIndexes.length === 0) return { value: rest, rest: '' };
  const nextIndex = Math.min(...suffixIndexes);
  return {
    value: rest.slice(0, nextIndex),
    rest: rest.slice(nextIndex),
  };
}

function parseBaselineRecord(line, lineNumber) {
  const trimmed = line.trim();
  const revisionMarker = ': revision `';
  const revisionStart = trimmed.indexOf(revisionMarker, 2);
  if (!trimmed.startsWith('- ') || revisionStart === -1) {
    fail('El registro de baseline debe usar "- <id>: revision `<sha>` · <ISO-8601> · resultado: <resultado>"', lineNumber);
  }

  const id = trimmed.slice(2, revisionStart);
  assertSlug(id, 'El ID del registro de baseline', lineNumber);
  const revisionValueStart = revisionStart + revisionMarker.length;
  const revisionEnd = trimmed.indexOf('`', revisionValueStart);
  if (revisionEnd === -1) fail('La revisión del baseline debe cerrarse con `', lineNumber);
  const revision = trimmed.slice(revisionValueStart, revisionEnd);
  if (revision.length === 0 || revision.includes('|')) {
    fail('La revisión del baseline debe ser no vacía y no contener pipes', lineNumber);
  }

  const timestampMarker = ' · ';
  if (!trimmed.startsWith(timestampMarker, revisionEnd + 1)) {
    fail('El registro de baseline no contiene el separador previo al timestamp', lineNumber);
  }
  const timestampStart = revisionEnd + 1 + timestampMarker.length;
  const resultMarker = ' · resultado: ';
  const resultStartMarker = trimmed.indexOf(resultMarker, timestampStart);
  if (resultStartMarker === -1) {
    fail('El registro de baseline no contiene "resultado:"', lineNumber);
  }
  const timestamp = trimmed.slice(timestampStart, resultStartMarker);
  if (!ISO_8601_PATTERN.test(timestamp) || Number.isNaN(Date.parse(timestamp))) {
    fail(`Timestamp de baseline inválido: ${timestamp}`, lineNumber);
  }

  let rest = trimmed.slice(resultStartMarker + resultMarker.length);
  const firstAdjudication = rest.indexOf(ADJUDICATION_MARKER);
  const firstJustification = rest.indexOf(JUSTIFICATION_MARKER);
  const suffixIndexes = [firstAdjudication, firstJustification].filter((index) => index >= 0);
  const firstSuffix = suffixIndexes.length === 0 ? -1 : Math.min(...suffixIndexes);
  const result = firstSuffix === -1 ? rest : rest.slice(0, firstSuffix);
  rest = firstSuffix === -1 ? '' : rest.slice(firstSuffix);
  if (result.length === 0 || result.includes('|')) {
    fail('El resultado del baseline debe ser no vacío y no contener pipes', lineNumber);
  }

  let adjudication = null;
  let justification = null;
  while (rest.length > 0) {
    if (rest.startsWith(ADJUDICATION_MARKER)) {
      if (adjudication !== null) fail('El registro de baseline duplica la adjudicación', lineNumber);
      const taken = takeSuffixValue(rest.slice(ADJUDICATION_MARKER.length));
      adjudication = taken.value;
      rest = taken.rest;
      continue;
    }
    if (rest.startsWith(JUSTIFICATION_MARKER)) {
      if (justification !== null) fail('El registro de baseline duplica la justificación', lineNumber);
      const taken = takeSuffixValue(rest.slice(JUSTIFICATION_MARKER.length));
      justification = taken.value;
      rest = taken.rest;
      continue;
    }
    fail('El registro de baseline contiene un sufijo desconocido', lineNumber);
  }

  if (adjudication !== null) {
    const prefix = 'already_satisfied — ';
    if (!adjudication.startsWith(prefix) || adjudication.slice(prefix.length).trim() === '') {
      fail('La única adjudicación final admitida es already_satisfied con una nota', lineNumber);
    }
  }
  if (justification !== null && justification.trim() === '') {
    fail('La justificación de NOT_APPLICABLE no puede estar vacía', lineNumber);
  }

  return {
    id,
    revision,
    timestamp,
    result,
    adjudication,
    justification,
  };
}

function validateBaseline(rows, baseline, version) {
  const rowById = new Map(rows.map((row) => [row.id, row]));
  const seen = new Set();

  for (let index = 0; index < baseline.length; index++) {
    const record = baseline[index];
    const row = rowById.get(record.id);
    if (!row) fail(`El baseline de v${version} registra el ID ${record.id} sin una fila`);
    if (seen.has(record.id)) fail(`El baseline de v${version} duplica el ID ${record.id}`);
    seen.add(record.id);
    if (record.id !== rows[index]?.id) {
      fail(`El baseline de v${version} debe conservar el mismo orden de IDs que la tabla`);
    }
    if (row.baseline === 'GREEN_ALREADY') {
      if (record.adjudication === null) {
        fail(`La fila GREEN_ALREADY ${record.id} exige adjudicación: already_satisfied`);
      }
    } else if (record.adjudication !== null) {
      fail(`La adjudicación de ${record.id} no es coherente con Baseline ${row.baseline}`);
    }
    if (row.baseline === 'NOT_APPLICABLE') {
      if (record.justification === null) {
        fail(`La fila NOT_APPLICABLE ${record.id} exige justificación`);
      }
    } else if (record.justification !== null) {
      fail(`La justificación de ${record.id} no es coherente con Baseline ${row.baseline}`);
    }
    record.state = row.baseline;
  }

  const missing = rows.filter((row) => !seen.has(row.id)).map((row) => row.id);
  if (missing.length > 0) {
    fail(`El baseline de v${version} no registra los IDs: ${missing.join(', ')}`);
  }
  if (baseline.length !== rows.length) {
    fail(`El baseline de v${version} debe tener exactamente un registro por fila`);
  }
}

function validateStableIds(versions) {
  const expected = new Set(versions[0].rows.map((row) => row.id));
  for (const version of versions.slice(1)) {
    const actual = new Set(version.rows.map((row) => row.id));
    const changed = actual.size !== expected.size || [...expected].some((id) => !actual.has(id));
    if (changed) fail(`v${version.version} cambia el conjunto estable de IDs del contrato`);
  }
}

export function parseContract(markdown) {
  if (typeof markdown !== 'string') throw new Error('El contrato debe recibirse como texto.');
  if (Buffer.byteLength(markdown, 'utf8') > MAX_CONTRACT_BYTES) {
    throw new Error('El contrato excede el máximo de 1 MiB.');
  }

  const lines = markdown.split(/\r?\n/);
  let index = skipBlank(lines, 0);
  if (!/^# Verification contract — \S.*$/.test(lines[index]?.trim() ?? '')) {
    fail('Falta el título canónico "# Verification contract — <id>"', index + 1);
  }
  index = skipBlank(lines, index + 1);
  if (lines[index]?.trim() !== 'schemaVersion: 1') {
    fail('schemaVersion: 1 debe aparecer antes de la primera versión', index + 1);
  }
  index = skipBlank(lines, index + 1);

  const versions = [];
  while (index < lines.length) {
    const versionMatch = VERSION_PATTERN.exec(lines[index].trim());
    if (!versionMatch) fail('Se esperaba una sección consecutiva ## vN', index + 1);
    const version = Number(versionMatch[1]);
    if (version !== versions.length + 1) {
      fail(`Las versiones deben ser consecutivas desde v1; se encontró v${version}`, index + 1);
    }
    index = skipBlank(lines, index + 1);

    const header = parseTableCells(lines[index] ?? '', index + 1);
    assertExactColumns(header, index + 1);
    index++;
    const separator = parseTableCells(lines[index] ?? '', index + 1);
    assertSeparator(separator, index + 1);
    index++;

    const rows = [];
    const rowIds = new Set();
    while (index < lines.length && lines[index].trim().startsWith('|')) {
      const row = parseRow(lines[index], index + 1);
      if (rowIds.has(row.id)) fail(`La tabla de v${version} duplica el ID ${row.id}`, index + 1);
      rowIds.add(row.id);
      rows.push(row);
      index++;
    }
    if (rows.length === 0) fail(`La tabla de v${version} debe contener al menos una fila`);

    index = skipBlank(lines, index);
    if (lines[index]?.trim() !== '### Baseline') {
      fail(`Falta el bloque ### Baseline de v${version}`, index + 1);
    }
    index = skipBlank(lines, index + 1);

    const baseline = [];
    while (index < lines.length && lines[index].trim().startsWith('- ')) {
      baseline.push(parseBaselineRecord(lines[index], index + 1));
      index++;
    }
    validateBaseline(rows, baseline, version);
    versions.push({ version, rows, baseline });
    index = skipBlank(lines, index);
  }

  if (versions.length === 0) fail('El contrato debe contener al menos la versión v1');
  validateStableIds(versions);
  return { versions };
}

export function validateContract(markdown) {
  const { versions } = parseContract(markdown);
  return { ok: true, versions: versions.length };
}
