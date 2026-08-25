import test from 'node:test';
import assert from 'node:assert/strict';

import { ConfigYamlError, emitQuoted, locateSection, readPathVault, upsertPathVault } from '../../../skills/knowledge-vault/scripts/lib/config-yaml.mjs';

const rechaza = (texto, motivo) =>
  assert.throws(
    () => locateSection(texto),
    (e) => {
      assert.ok(e instanceof ConfigYamlError, `se esperaba ConfigYamlError, llegó ${e?.name}`);
      assert.equal(e.code, 'CONFIG_INVALID');
      return true;
    },
    motivo,
  );

test('la sección ausente se reporta, no falla', () => {
  const r = locateSection('stack: node\ntracker: jira\n');
  assert.equal(r.present, false);
  assert.equal(r.keyLine, null);
  assert.equal(r.valueLine, null);
  assert.equal(r.eol, '\n');
});

test('localiza la sección y su clave, con la indentación de las hermanas', () => {
  const r = locateSection('stack: node\nknowledge-vault:\n  retention: 90\n  path_vault: "/v"\n');
  assert.equal(r.present, true);
  assert.equal(r.keyLine, 1);
  assert.equal(r.childIndent, '  ');
  assert.equal(r.valueLine, 3);
});

test('la sección sin la clave interna deja valueLine en null', () => {
  const r = locateSection('knowledge-vault:\n  retention: 90\n');
  assert.equal(r.present, true);
  assert.equal(r.valueLine, null);
  assert.equal(r.childIndent, '  ');
});

test('un comentario entre la clave y sus hijas es legítimo y no confunde la indentación', () => {
  const r = locateSection('knowledge-vault:\n  # el vault de cocha\n  retention: 90\n');
  assert.equal(r.present, true);
  assert.equal(r.childIndent, '  ');
});

test('un comentario con indentación distinta a la de sus hermanas no fija childIndent', () => {
  // Este caso, a diferencia del anterior, distingue el comentario de su primera
  // hermana real: si el comentario fijara la indentación, childIndent quedaría en
  // 4 espacios en vez de los 2 que usa `path_vault`.
  const r = locateSection('knowledge-vault:\n    # comentario más indentado que sus hermanas\n  path_vault: "/v"\n');
  assert.equal(r.present, true);
  assert.equal(r.childIndent, '  ');
});

test('CRLF se detecta y se reporta como terminador dominante', () => {
  const r = locateSection('stack: node\r\nknowledge-vault:\r\n  path_vault: "/v"\r\n');
  assert.equal(r.eol, '\r\n');
  assert.equal(r.valueLine, 2);
});

test('el BOM se detecta y no rompe la primera clave', () => {
  const r = locateSection('\ufeffknowledge-vault:\n  path_vault: "/v"\n');
  assert.equal(r.bom, true);
  assert.equal(r.keyLine, 0);
});

// ── Los nueve rechazos ──────────────────────────────────────────────────────

test('los nueve rechazos son CONFIG_INVALID', () => {
  rechaza('knowledge-vault:\n  a: 1\nknowledge-vault:\n  b: 2\n', 'clave duplicada');
  rechaza('"knowledge-vault":\n  a: 1\nknowledge-vault:\n  b: 2\n', 'clave citada equivalente');
  rechaza("'knowledge-vault':\n  a: 1\nknowledge-vault:\n  b: 2\n", 'clave citada simple');
  rechaza('knowledge-vault: algo\n', 'escalar en la misma línea');
  rechaza('knowledge-vault: {path_vault: /v}\n', 'mapa en forma de flujo');
  rechaza('knowledge-vault:\n  path_vault: /a\n  path_vault: /b\n', 'path_vault duplicado');
  rechaza('otra:\n  knowledge-vault:\n    path_vault: /v\n', 'la sección está indentada');
  rechaza('knowledge-vault:\n\tpath_vault: /v\n', 'tabulador en la indentación');
  rechaza('---\na: 1\n---\nknowledge-vault:\n  path_vault: /v\n', 'documento múltiple');
  rechaza('...\nknowledge-vault:\n  path_vault: /v\n', 'marcador de fin de documento');
});

test('una clave citada SOLA, sin duplicado, también se rechaza', () => {
  // No se puede insertar dentro con seguridad ni tratarla como ausente: tratarla
  // como ausente anexaría un bloque que YAML consideraría duplicado.
  rechaza('"knowledge-vault":\n  path_vault: "/v"\n', 'clave citada única');
});

test('un anchor dentro del bloque cae en el rechazo de la forma', () => {
  rechaza('knowledge-vault: &ancla\n', 'anchor como valor de la clave');
});

test('un anchor FUERA del bloque no molesta', () => {
  const r = locateSection('base: &ancla\n  x: 1\nknowledge-vault:\n  path_vault: "/v"\n');
  assert.equal(r.present, true);
  assert.equal(r.valueLine, 3);
});

test('el valor se emite SIEMPRE citado, incluso cuando no lo necesitaría', () => {
  // Una sola forma de emisión: sin rama que decidir, no hay rama que equivocar.
  assert.equal(emitQuoted('/vaults/cocha'), '"/vaults/cocha"');
});

test('los caracteres que rompen un escalar plano quedan contenidos por las comillas', () => {
  // Sin comillas, YAML leería `/vaults/proyecto` y el archivado iría a OTRO
  // directorio: es el peor caso del diseño.
  assert.equal(emitQuoted('/vaults/proyecto#1'), '"/vaults/proyecto#1"');
  assert.equal(emitQuoted('/vaults/a: b'), '"/vaults/a: b"');
  assert.equal(emitQuoted('/vaults/a  '), '"/vaults/a  "');
});

test('la barra invertida y la comilla doble se escapan', () => {
  assert.equal(emitQuoted('/vaults/a\\b'), '"/vaults/a\\\\b"');
  assert.equal(emitQuoted('/vaults/a"b'), '"/vaults/a\\"b"');
});

test('los caracteres de control se rechazan, no se escapan', () => {
  // Son citables en YAML, pero una ruta que los contiene es un error de tipeo o
  // una inyección. Aceptarlos no le sirve a nadie.
  for (const malo of ['/vaults/a\nb', '/vaults/a\rb', '/vaults/a\tb', '/vaults/a\u0000b']) {
    assert.throws(
      () => emitQuoted(malo),
      (e) => e instanceof ConfigYamlError && e.code === 'CONFIG_INVALID',
      `debía rechazar ${JSON.stringify(malo)}`,
    );
  }
});

test('el no-ASCII se conserva tal cual: UTF-8 es válido en un escalar citado', () => {
  assert.equal(emitQuoted('/vaults/proyectos-ñ/día'), '"/vaults/proyectos-ñ/día"');
});

test('round-trip: lo que se emite y se relee es byte a byte lo que entró', () => {
  for (const original of ['/v/a#1', '/v/a: b', '/v/a\\b', '/v/a"b', '/v/ñ', '/v/a  ']) {
    const emitido = emitQuoted(original);
    // Un escalar double-quoted de YAML con solo \\ y \" escapados es exactamente
    // un string JSON, así que JSON.parse es un lector fiel para esta forma.
    assert.equal(JSON.parse(emitido), original, `round-trip roto para ${JSON.stringify(original)}`);
  }
});

/**
 * LA ASERCIÓN CENTRAL DE TODO EL MÓDULO.
 *
 * Escrita como byte-identidad y NO como "el YAML parseado es equivalente": la
 * equivalencia semántica pasaría igual con los comentarios borrados y las claves
 * reordenadas, que es exactamente el fallo que este diseño existe para evitar.
 */
function assertSoloCambioLaLinea(antes, despues, { esperadas = 1 } = {}) {
  const a = antes.split('\n');
  const d = despues.split('\n');
  const distintas = [];
  for (let i = 0; i < Math.max(a.length, d.length); i += 1) {
    if (a[i] !== d[i]) distintas.push(i);
  }
  assert.equal(
    distintas.length,
    esperadas,
    `cambiaron ${distintas.length} líneas (${distintas.join(', ')}), se esperaban ${esperadas}`,
  );
}

const CONFIG_REAL = [
  'stack: node',
  'test_cmd: "npm test"',
  'tracker: jira',
  '',
  '# la revisión cross-model la quiero solo en cambios complejos',
  'cross_review:',
  '  mode: auto',
  '  execution: auto',
  '',
  'archive_target: vault',
  '',
].join('\n');

test('lectura: devuelve el valor citado sin sus comillas', () => {
  assert.equal(readPathVault('knowledge-vault:\n  path_vault: "/v/cocha"\n'), '/v/cocha');
});

test('lectura: acepta el valor plano que un humano escribió a mano', () => {
  assert.equal(readPathVault('knowledge-vault:\n  path_vault: /v/cocha\n'), '/v/cocha');
});

test('lectura: sin sección o sin clave devuelve null', () => {
  assert.equal(readPathVault('stack: node\n'), null);
  assert.equal(readPathVault('knowledge-vault:\n  retention: 90\n'), null);
});

test('caso 1 — archivo vacío: se crea solo la sección', () => {
  const { text, changed } = upsertPathVault('', '/v/cocha');
  assert.equal(changed, true);
  assert.equal(text, 'knowledge-vault:\n  path_vault: "/v/cocha"\n');
});

test('caso 2 — sin la sección: se anexa al final y NADA más cambia', () => {
  const { text, changed } = upsertPathVault(CONFIG_REAL, '/v/cocha');
  assert.equal(changed, true);
  assert.ok(text.startsWith(CONFIG_REAL), 'el original tiene que sobrevivir como prefijo exacto');
  assert.ok(text.endsWith('knowledge-vault:\n  path_vault: "/v/cocha"\n'));
  // El comentario del usuario y las comillas de test_cmd siguen ahí.
  assert.ok(text.includes('# la revisión cross-model la quiero solo en cambios complejos'));
  assert.ok(text.includes('test_cmd: "npm test"'));
});

test('caso 3 — sección sin la clave: se inserta como primera hija, con la indentación hermana', () => {
  const antes = 'stack: node\nknowledge-vault:\n    retention: 90\n';
  const { text } = upsertPathVault(antes, '/v/cocha');
  assert.equal(text, 'stack: node\nknowledge-vault:\n    path_vault: "/v/cocha"\n    retention: 90\n');
  // 3 y no 1: assertSoloCambioLaLinea compara por índice, y una inserción corre
  // todas las líneas siguientes una posición. Con 4 líneas en "antes" e inserción
  // en el índice 2, difieren los índices 2, 3 y 4. La aserción fuerte de este caso
  // es el assert.equal de arriba, que compara el archivo completo; este conteo es
  // un chequeo secundario y ruidoso frente a una inserción (a diferencia del caso
  // 4, un reemplazo in-place, donde sí vale por sí solo y da 1).
  assertSoloCambioLaLinea(antes, text, { esperadas: 3 });
});

test('caso 3 — sin hermanas, la indentación por defecto es de dos espacios', () => {
  const { text } = upsertPathVault('knowledge-vault:\n', '/v/cocha');
  assert.equal(text, 'knowledge-vault:\n  path_vault: "/v/cocha"\n');
});

test('caso 4 — la clave ya está: se reemplaza SOLO el valor de esa línea', () => {
  const antes = [
    'stack: node',
    '',
    'knowledge-vault:',
    '  # el vault del trabajo',
    '  path_vault: "/v/viejo"',
    '  retention: 90',
    '',
  ].join('\n');
  const { text, changed } = upsertPathVault(antes, '/v/nuevo');
  assert.equal(changed, true);
  assertSoloCambioLaLinea(antes, text, { esperadas: 1 });
  assert.ok(text.includes('  path_vault: "/v/nuevo"'));
  assert.ok(text.includes('  # el vault del trabajo'), 'el comentario tiene que sobrevivir');
  assert.ok(text.includes('  retention: 90'));
});

test('idempotencia: el mismo valor no reescribe nada', () => {
  const antes = 'knowledge-vault:\n  path_vault: "/v/cocha"\n';
  const { text, changed } = upsertPathVault(antes, '/v/cocha');
  assert.equal(changed, false);
  assert.equal(text, antes);
});

test('CRLF: se emite el terminador dominante del archivo', () => {
  const { text } = upsertPathVault('stack: node\r\nknowledge-vault:\r\n', '/v/cocha');
  assert.equal(text, 'stack: node\r\nknowledge-vault:\r\n  path_vault: "/v/cocha"\r\n');
});

test('el BOM sobrevive al frente', () => {
  const { text } = upsertPathVault('\ufeffstack: node\n', '/v/cocha');
  assert.ok(text.startsWith('\ufeff'));
  assert.ok(text.includes('knowledge-vault:\n  path_vault: "/v/cocha"\n'));
});

test('un archivo sin salto final recibe uno antes de la sección anexada', () => {
  const { text } = upsertPathVault('stack: node', '/v/cocha');
  assert.equal(text, 'stack: node\nknowledge-vault:\n  path_vault: "/v/cocha"\n');
});

test('round-trip completo: lo que se escribe se relee igual', () => {
  for (const root of ['/v/a#1', '/v/a: b', '/v/a"b', '/v/ñ']) {
    const { text } = upsertPathVault(CONFIG_REAL, root);
    assert.equal(readPathVault(text), root, `round-trip roto para ${JSON.stringify(root)}`);
  }
});
