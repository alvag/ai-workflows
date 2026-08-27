/**
 * T5 — las cuatro identidades (AC-1, AC-2, AC-2b, AC-2c, AC-4).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';

import {
  FLOW_ID_RE,
  IdentityError,
  REPO_SLUG_RE,
  assertFlowId,
  assertRepoSlug,
  buildSourceInventoryV2,
  computeSourceFingerprint,
  deriveFlowId,
  deriveStem,
  normalizarRemoto,
  parseRegistroIdentidades,
  proponerIdentidadRepo,
  resolverIdentidadRepo,
  serializarRegistroIdentidades,
} from '../../../skills/knowledge-vault/scripts/lib/identity.mjs';
import { GOLDEN } from './fixtures/canonical-golden.mjs';

/** Por punto de código: un NUL crudo volvería binario este archivo para git. */
const NUL = String.fromCodePoint(0);

const HASH_A = '0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f9';

function rejects(fn, code) {
  assert.throws(fn, (err) => {
    assert.ok(err instanceof IdentityError, `se esperaba IdentityError, llegó ${err?.name}`);
    assert.equal(err.code, code);
    return true;
  });
}

// ── Segmentos (AC-2, AC-3) ────────────────────────────────────────────────────

test('acepta segmentos canónicos', () => {
  for (const slug of ['a', 'ab', 'mi-repo-0123456789ab', 'a1', '9x9']) {
    assert.equal(assertRepoSlug(slug), slug);
  }
  for (const flow of ['a', 'abc-123', 'pqtch-546', 'v1.2.3', 'a_b.c-d', 'x'.repeat(128)]) {
    assert.equal(assertFlowId(flow), flow);
  }
});

test('rechaza cada clase de segmento inválido', () => {
  const slugsInvalidos = [
    '', 'A', 'Mi-Repo', 'a/b', 'a\\b', 'a:b', 'a b', '-a', 'a-', 'a.b', 'a_b',
    'x'.repeat(64), 'ñ', NUL, `a${NUL}b`,
  ];
  for (const slug of slugsInvalidos) {
    rejects(() => assertRepoSlug(slug), 'INVALID_REPO_SLUG');
  }

  const flowsInvalidos = [
    '', 'A', 'ABC-1', 'a/b', 'a\\b', 'a:b', 'a b', '-a', 'a-', '.a', 'a.',
    'a..b', '..', 'x'.repeat(129), 'ñ',
  ];
  for (const flow of flowsInvalidos) {
    rejects(() => assertFlowId(flow), 'INVALID_FLOW_ID');
  }
});

test('el flow-id prohíbe `..` en cualquier posición', () => {
  assert.ok(!FLOW_ID_RE.test('a..b'));
  assert.ok(!FLOW_ID_RE.test('..abc'));
  assert.ok(!FLOW_ID_RE.test('abc..'));
  assert.ok(FLOW_ID_RE.test('a.b.c'));
});

test('los patrones acotan la longitud', () => {
  assert.ok(REPO_SLUG_RE.test('a'.repeat(63)));
  assert.ok(!REPO_SLUG_RE.test('a'.repeat(64)));
  assert.ok(FLOW_ID_RE.test('a'.repeat(128)));
  assert.ok(!FLOW_ID_RE.test('a'.repeat(129)));
});

// ── Derivación del flow-id: rechaza, no transforma (AC-3) ─────────────────────

test('el flow-id debe ya ser canónico: `A`/`a` y `ª`/`a` se rechazan', () => {
  assert.equal(deriveFlowId('pqtch-546'), 'pqtch-546');

  // Transformar antes de validar haría converger estos tres al mismo flow-id, y
  // AC-2c no lo detectaría: comparten `repo_identity`. Dos flujos distintos
  // quedarían mezclados como revisiones de una sola fuente.
  rejects(() => deriveFlowId('PQTCH-546'), 'INVALID_FLOW_ID');
  rejects(() => deriveFlowId('ª-546'), 'INVALID_FLOW_ID');
  rejects(() => deriveFlowId('Abc'), 'INVALID_FLOW_ID');
});

// Esta guarda decía `assert.throws(..., /--flow-id/)`: acreditaba una instrucción
// hacia un flag que ningún verbo implementa, y el reintento devolvía el error
// idéntico byte por byte. Ahora se verifica la salida que sí existe.
test('el error nombra la acción que existe, y no un flag inexistente', () => {
  const capturar = (valor) => {
    try { deriveFlowId(valor); return null; } catch (error) { return error; }
  };

  const error = capturar('PQTCH-925');
  assert.equal(error.code, 'INVALID_FLOW_ID');
  assert.doesNotMatch(error.message, /--flow-id/);
  assert.match(error.message, /a-z0-9\._-/);          // el dominio, no "kebab-case"
  assert.match(error.message, /renombrar el directorio de origen/);
  assert.match(error.message, /por ejemplo "pqtch-925"/);
});

// Plegado a minúsculas ASCII y nada más. `deriveStem` no sirve: borra `.` y `_`
// —que el dominio admite—, trunca a 48 y colapsa `---`, `..` y `''` en `repo`.
test('el candidato conserva la relación con la entrada', () => {
  const mensaje = (valor) => {
    try { deriveFlowId(valor); return ''; } catch (error) { return error.message; }
  };
  assert.match(mensaje('A_B.C'), /por ejemplo "a_b\.c"/);        // preserva `_` y `.`
  assert.match(mensaje('X'.repeat(60)), new RegExp(`por ejemplo "${'x'.repeat(60)}"`));
});

// Un candidato constante haría converger todos los nombres, reintroduciendo por
// la vía de la recomendación la colisión que justificó no normalizar.
test('sin candidato válido, la cláusula se omite en vez de inventarse', () => {
  for (const valor of ['ª-546', '---', '..', '', 123, null, undefined]) {
    let error;
    try { deriveFlowId(valor); } catch (capturado) { error = capturado; }
    assert.equal(error.code, 'INVALID_FLOW_ID', String(valor));
    assert.doesNotMatch(error.message, /por ejemplo/, String(valor));
    assert.match(error.message, /renombrar el directorio de origen/, String(valor));
  }
});

// ── repo-slug: stem legible + hash de identidad (AC-4) ────────────────────────

test('el stem pliega a ASCII, colapsa runs y recorta', () => {
  assert.equal(deriveStem('mi-repo'), 'mi-repo');
  assert.equal(deriveStem('Mi_Repo'), 'mi-repo');
  assert.equal(deriveStem('API v2 (nuevo)'), 'api-v2-nuevo');
  assert.equal(deriveStem('---raro---'), 'raro');
  assert.equal(deriveStem('a'.repeat(80)), 'a'.repeat(48));
});

// ── Los tres documentos y sus digests (AC-1) ──────────────────────────────────

/** Digest de una selección cualquiera: acá se lo trata como un valor opaco. */

// ── T8 — los constructores `v2`, anclados al golden escrito a mano ────────────

/**
 * El golden es un oráculo independiente: sus bytes y su digest salen de
 * `shasum -a 256`, no de este código. Comprobar que los constructores **producen
 * exactamente ese valor** es lo que impide que un cambio de forma se cuele con
 * los tests en verde, porque el digest ya está publicado en `plan.md` como forma
 * congelada (AC-37).
 */
const golden = (nombre) => GOLDEN.find((g) => g.name === nombre);

test('`buildSourceInventoryV2` produce el documento congelado, con los directorios vacíos', () => {
  const g = golden('inventario-v2-con-directorio-vacio');
  const construido = buildSourceInventoryV2({
    // Desordenados a propósito: el orden lo pone el constructor, no quien llama.
    files: [{ path: 'plan.md', type: 'file', size: 12, sha256: g.value.files[0].sha256 }],
    directories: [{ path: 'vacio' }],
  });

  assert.deepEqual(construido, g.value);
  assert.equal(computeSourceFingerprint(construido), g.digest);
});

test('un directorio vacío mueve el fingerprint: por eso entra al inventario (AC-23)', () => {
  const archivos = [{ path: 'plan.md', type: 'file', size: 12, sha256: HASH_A }];
  const sin = computeSourceFingerprint(buildSourceInventoryV2({ files: archivos, directories: [] }));
  const con = computeSourceFingerprint(buildSourceInventoryV2({ files: archivos, directories: [{ path: 'vacio' }] }));
  assert.notEqual(sin, con);
});

// ── La identidad **declarada** del repositorio (AC-13) ────────────────────────
//
// Lo que se prueba acá no es que la resolución "ande": es que **no elija**. Con
// N repositorios en N máquinas, dos clones que se llamen igual dejan de ser un
// caso teórico, y el modo de fallar barato —quedarse con el más parecido— es
// exactamente el que destruiría el flujo equivocado.

const REGISTRO_DOS = [
  { repoId: 'api-pagos', remoto: 'git@github.com:acme/api.git', commitRaiz: 'aaaa111', rutaObservada: '/home/ana/api' },
  { repoId: 'api-legacy', remoto: 'https://gitlab.com/otra/api.git', commitRaiz: 'bbbb222', rutaObservada: '/home/bruno/api' },
].map((e) => ({ ...e }));

test('[AC-13] resuelve por el commit raíz, no por la ruta ni por el nombre', () => {
  const r = resolverIdentidadRepo({
    registro: REGISTRO_DOS,
    // La ruta observada es la del OTRO repositorio a propósito: si la resolución
    // la mirara, devolvería `api-legacy`.
    senales: { commitRaiz: 'aaaa111', rutaObservada: '/home/bruno/api', nombreDirectorio: 'api' },
  });
  assert.equal(r.repoId, 'api-pagos');
});

test('[AC-13] dos clones con el mismo nombre de directorio no colisionan', () => {
  const a = resolverIdentidadRepo({ registro: REGISTRO_DOS, senales: { remoto: 'git@github.com:acme/api.git' } });
  const b = resolverIdentidadRepo({ registro: REGISTRO_DOS, senales: { remoto: 'https://gitlab.com/otra/api.git' } });
  assert.equal(a.repoId, 'api-pagos');
  assert.equal(b.repoId, 'api-legacy');
  // Y el derivado de hoy los mandaría a los dos al mismo sitio del vault.
  assert.equal(deriveStem('api'), deriveStem('api'));
});

test('[AC-13] sin identidad declarada la operación se detiene', () => {
  rejects(
    () => resolverIdentidadRepo({ registro: REGISTRO_DOS, senales: { commitRaiz: 'cccc333' } }),
    'AMBIGUOUS_IDENTITY',
  );
  // Y con registro vacío también: "todavía nadie lo declaró" no autoriza nada.
  rejects(() => resolverIdentidadRepo({ registro: [], senales: { commitRaiz: 'aaaa111' } }), 'AMBIGUOUS_IDENTITY');
});

test('[AC-13] dos identidades compatibles detienen en vez de elegir por proximidad', () => {
  const registro = [
    ...REGISTRO_DOS,
    { repoId: 'api-fork', remoto: 'git@github.com:acme/api.git', commitRaiz: 'dddd444', rutaObservada: '/home/ana/fork' },
  ];
  assert.throws(
    () => resolverIdentidadRepo({ registro, senales: { remoto: 'git@github.com:acme/api.git' } }),
    (err) => {
      assert.equal(err.code, 'AMBIGUOUS_IDENTITY');
      assert.deepEqual(err.detail.candidatos.sort(), ['api-fork', 'api-pagos']);
      return true;
    },
  );
});

test('[AC-13] sin ninguna señal de identidad se detiene: la ruta no es una señal', () => {
  rejects(
    () => resolverIdentidadRepo({ registro: REGISTRO_DOS, senales: { rutaObservada: '/home/ana/api', nombreDirectorio: 'api' } }),
    'AMBIGUOUS_IDENTITY',
  );
});

test('[AC-13] el remoto se compara sin protocolo, credenciales ni sufijo', () => {
  const formas = [
    'git@github.com:acme/api.git',
    'https://github.com/acme/api.git',
    'ssh://git@github.com/acme/api',
    'https://usuario@github.com/acme/api/',
  ];
  const normalizadas = new Set(formas.map(normalizarRemoto));
  assert.deepEqual([...normalizadas], ['github.com/acme/api']);
  for (const forma of formas) {
    assert.equal(resolverIdentidadRepo({ registro: REGISTRO_DOS, senales: { remoto: forma } }).repoId, 'api-pagos');
  }
});

test('[AC-13] la propuesta sale del remoto y, sin remoto, del directorio', () => {
  assert.deepEqual(
    proponerIdentidadRepo({ remoto: 'git@github.com:acme/API v2.git', nombreDirectorio: 'otro' }),
    { repoId: 'api-v2', origen: 'remoto' },
  );
  assert.deepEqual(
    proponerIdentidadRepo({ nombreDirectorio: 'Mi_Repo' }),
    { repoId: 'mi-repo', origen: 'directorio' },
  );
});

test('[AC-13] el registro va y vuelve sin perder ni inventar campos', () => {
  const texto = serializarRegistroIdentidades(REGISTRO_DOS);
  assert.deepEqual(parseRegistroIdentidades(texto), REGISTRO_DOS);
  assert.deepEqual(parseRegistroIdentidades('# comentario\n\n'), []);
  rejects(() => parseRegistroIdentidades('solo-un-campo\n'), 'REGISTRO_ILEGIBLE');
  rejects(
    () => serializarRegistroIdentidades([{ repoId: 'a\tb', remoto: '', commitRaiz: '', rutaObservada: '' }]),
    'CAMPO_INVALIDO',
  );
});
