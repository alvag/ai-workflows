/**
 * Golden fixtures de la serialización canónica (AC-8).
 *
 * Cada entrada trae el valor, los **bytes canónicos escritos a mano** y su digest.
 * El digest **no** se calculó con este código: sale de `shasum -a 256` sobre el
 * campo `canonical`, así que el fixture es un oráculo independiente del módulo que
 * verifica. Si la canonicalización cambia, esto falla — que es el punto.
 *
 * **Todo carácter no ASCII de los datos va escrito con escapes `\u`, sin
 * excepción.** No es cosmético: un editor o una herramienta que normalice el
 * archivo al guardarlo convertiría el path NFD en su forma NFC, y el par NFC/NFD
 * —lo único que prueba que ninguna tabla Unicode participa del digest— se volvería
 * dos copias del mismo caso: verde y sin valor.
 */

const HASH_A = '0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f9';
const HASH_B = '1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a';
const HASH_C = '2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b';
const IDENTITY = 'manual:2f1c0a9e-4b6d-4a1e-9c3f-8d0e5a7b2c14';
const SOURCE_ID = 'demo-0123456789ab/abc-1';

export const GOLDEN = [
  {
    name: 'manifest-minimo',
    why: 'orden de claves por punto de codigo, en el objeto raiz y en cada archivo',
    value: {
      schema: 'kv-manifest/1',
      source_id: SOURCE_ID,
      repo_identity: IDENTITY,
      files: [{ path: 'plan.md', type: 'file', size: 12, sha256: HASH_A }],
    },
    canonical:
      `{"files":[{"path":"plan.md","sha256":"${HASH_A}","size":12,"type":"file"}],` +
      `"repo_identity":"${IDENTITY}","schema":"kv-manifest/1","source_id":"${SOURCE_ID}"}`,
    digest: 'bdcd6fe649bf6347a7ae14a9f5a15dfc55ada145807a28df76acc6bf120fe7e1',
  },

  {
    name: 'orden-por-punto-de-codigo',
    why: 'U+FF21 va antes que U+1F600 por punto de codigo; comparar unidades UTF-16 los invertiria',
    value: {
      schema: 'kv-source-inventory/1',
      files: [
        { path: '\uff21.md', type: 'file', size: 1, sha256: HASH_B },
        { path: '\u{1f600}.md', type: 'file', size: 2, sha256: HASH_C },
      ],
    },
    canonical:
      `{"files":[{"path":"\uff21.md","sha256":"${HASH_B}","size":1,"type":"file"},` +
      `{"path":"\u{1f600}.md","sha256":"${HASH_C}","size":2,"type":"file"}],` +
      '"schema":"kv-source-inventory/1"}',
    digest: '26b790ab285918433487f0dcdeed9ee525229eabce026dda20fb3d73a14f7c3d',
  },

  {
    name: 'escapes-minimos',
    why: 'solo se escapan la comilla doble, la barra invertida y C0 (U+0000..U+001F)',
    value: {
      schema: 'kv-manifest/1',
      source_id: SOURCE_ID,
      repo_identity: IDENTITY,
      files: [{ path: 'a"b\\c\n\t\u007f/d.md', type: 'file', size: 3, sha256: HASH_A }],
    },
    // En el esperado, U+007F va como caracter real: DEL **no** es C0 y sale literal.
    // La barra `/` tampoco se escapa.
    canonical:
      `{"files":[{"path":"a\\"b\\\\c\\u000a\\u0009\u007f/d.md","sha256":"${HASH_A}","size":3,"type":"file"}],` +
      `"repo_identity":"${IDENTITY}","schema":"kv-manifest/1","source_id":"${SOURCE_ID}"}`,
    digest: '3b1a9e227112a46d01d83abfff150dcf6ce25bbdef98adc84c20144b7c23ffd0',
  },

  {
    name: 'enteros-limite',
    why: 'cero y MAX_SAFE_INTEGER en decimal ASCII, sin exponente',
    value: {
      schema: 'kv-source-inventory/1',
      files: [
        { path: 'grande.bin', type: 'file', size: 9007199254740991, sha256: HASH_B },
        { path: 'vacio.txt', type: 'file', size: 0, sha256: HASH_C },
      ],
    },
    canonical:
      `{"files":[{"path":"grande.bin","sha256":"${HASH_B}","size":9007199254740991,"type":"file"},` +
      `{"path":"vacio.txt","sha256":"${HASH_C}","size":0,"type":"file"}],` +
      '"schema":"kv-source-inventory/1"}',
    digest: 'e95f82f8b344617971f109374d07792d12686609c7b9e6f19ca547f3abd39a47',
  },

  {
    name: 'nfc',
    why: 'mitad NFC del par: caf + U+00E9 + .md',
    value: {
      schema: 'kv-manifest/1',
      source_id: SOURCE_ID,
      repo_identity: IDENTITY,
      files: [{ path: 'caf\u00e9.md', type: 'file', size: 4, sha256: HASH_A }],
    },
    canonical:
      `{"files":[{"path":"caf\u00e9.md","sha256":"${HASH_A}","size":4,"type":"file"}],` +
      `"repo_identity":"${IDENTITY}","schema":"kv-manifest/1","source_id":"${SOURCE_ID}"}`,
    digest: 'f85735735dbea3d685a4c21ade979c5b17de812bfaad2684ecd94f5603f45af7',
  },

  {
    name: 'nfd',
    why: 'mitad NFD: cafe + U+0301 + .md. Mismo arbol logico, bytes distintos, digest distinto (AC-5)',
    value: {
      schema: 'kv-manifest/1',
      source_id: SOURCE_ID,
      repo_identity: IDENTITY,
      files: [{ path: 'cafe\u0301.md', type: 'file', size: 4, sha256: HASH_A }],
    },
    canonical:
      `{"files":[{"path":"cafe\u0301.md","sha256":"${HASH_A}","size":4,"type":"file"}],` +
      `"repo_identity":"${IDENTITY}","schema":"kv-manifest/1","source_id":"${SOURCE_ID}"}`,
    digest: '853069aa679c4502959fbb74a594fdbc9e0e26a00194f0acbf274c31656c6e72',
  },

  // ── Formas `v2` del desacople del consumidor ──────────────────────────────
  // Los tres digests salen de `shasum -a 256` sobre el campo `canonical`, nunca
  // de este código. Es la única defensa contra el riesgo que no da señal: si una
  // forma canónica estuviera mal, un golden REGENERADO reproduciría el error y
  // pasaría en verde.

  {
    name: 'seleccion-particion-total',
    why: 'reason es null si y solo si la decision es include; entries ordenado por path',
    value: {
      schema: 'kv-selection/1',
      source_fingerprint: HASH_B,
      entries: [
        { path: 'plan.md', decision: 'include', reason: null },
        { path: 'prompt.txt', decision: 'omit', reason: 'regla 2: prompt' },
      ],
    },
    canonical:
      '{"entries":[{"decision":"include","path":"plan.md","reason":null},' +
      '{"decision":"omit","path":"prompt.txt","reason":"regla 2: prompt"}],' +
      `"schema":"kv-selection/1","source_fingerprint":"${HASH_B}"}`,
    digest: 'c89c8b38d91533b7df7bc497f2317695c8911497bfe379e992d59d035340ca00',
  },

  {
    name: 'inventario-v2-con-directorio-vacio',
    why: 'directories entra al fingerprint y no lleva size ni sha256: no tiene bytes que hashear',
    value: {
      schema: 'kv-source-inventory/2',
      files: [{ path: 'plan.md', type: 'file', size: 12, sha256: HASH_A }],
      directories: [{ path: 'vacio', type: 'directory' }],
    },
    canonical:
      '{"directories":[{"path":"vacio","type":"directory"}],' +
      `"files":[{"path":"plan.md","sha256":"${HASH_A}","size":12,"type":"file"}],` +
      '"schema":"kv-source-inventory/2"}',
    digest: '94c6db5d6092612baf86f7a28ae07178fa582a436de8c610d8605d0215ce7e47',
  },

  {
    name: 'intento-v2',
    why: 'completeness reemplaza a precondition, y en el inventario reason reemplaza a rule',
    value: {
      schema: 'kv-attempt/2',
      command: 'archive',
      source_id: SOURCE_ID,
      repo_identity: IDENTITY,
      revision_id: HASH_A,
      source_fingerprint: HASH_B,
      selection_digest: HASH_C,
      completeness: { provenance: 'verified', predicate: 'plan.md:status=done', observed_value: 'done' },
      inventory: [
        { path: 'plan.md', type: 'file', size: 12, sha256: HASH_A, disposition: 'included', reason: null },
      ],
    },
    canonical:
      '{"command":"archive","completeness":{"observed_value":"done",' +
      '"predicate":"plan.md:status=done","provenance":"verified"},' +
      `"inventory":[{"disposition":"included","path":"plan.md","reason":null,"sha256":"${HASH_A}",` +
      '"size":12,"type":"file"}],' +
      `"repo_identity":"${IDENTITY}","revision_id":"${HASH_A}","schema":"kv-attempt/2",` +
      `"selection_digest":"${HASH_C}","source_fingerprint":"${HASH_B}","source_id":"${SOURCE_ID}"}`,
    digest: '56c0cbc436df4b66a361ccc9f44e48f4da81c45cc9ec83e5652e5b51b09c411c',
  },

  {
    name: 'intento-v2-forzado',
    why: 'un forzado registra CONTRA QUÉ valor se forzó: es lo único que lo explica',
    value: {
      schema: 'kv-attempt/2',
      command: 'archive',
      source_id: SOURCE_ID,
      repo_identity: IDENTITY,
      revision_id: HASH_A,
      source_fingerprint: HASH_B,
      selection_digest: HASH_C,
      completeness: { provenance: 'forced', predicate: 'plan.md:status=done', observed_value: 'wip' },
      inventory: [
        { path: 'plan.md', type: 'file', size: 12, sha256: HASH_A, disposition: 'included', reason: null },
      ],
    },
    canonical:
      '{"command":"archive","completeness":{"observed_value":"wip",' +
      '"predicate":"plan.md:status=done","provenance":"forced"},' +
      `"inventory":[{"disposition":"included","path":"plan.md","reason":null,"sha256":"${HASH_A}",` +
      '"size":12,"type":"file"}],' +
      `"repo_identity":"${IDENTITY}","revision_id":"${HASH_A}","schema":"kv-attempt/2",` +
      `"selection_digest":"${HASH_C}","source_fingerprint":"${HASH_B}","source_id":"${SOURCE_ID}"}`,
    digest: 'df6cd9e4ca38fffd2d57355723dea4cf63f5da367978455605947fe821bc14f8',
  },
];
