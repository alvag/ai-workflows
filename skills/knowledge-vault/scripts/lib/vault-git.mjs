/**
 * El vault como repositorio Git propio.
 *
 * El módulo de identidad del árbol de origen **no commitea**: sólo derivaba la
 * identidad de un repo desde su remoto. Así que sin esto AC-13 no tiene
 * mecanismo, y por eso el módulo es nuevo y no rescatado.
 *
 * **Que el vault esté versionado y que sea su propio repositorio son dos cosas
 * distintas.** Si su raíz cae dentro de otro repositorio, `git add` desde ahí
 * stagea contra el de afuera y el vault entero termina commiteado dentro del
 * proyecto de alguien más. De ahí la comparación contra `--show-toplevel`: no
 * alcanza con que `git` responda, tiene que responder **exactamente** la raíz del
 * vault. Un vault anidado se rechaza; inicializar un repositorio adentro de otro
 * sería peor, porque el problema se vuelve invisible.
 *
 * El chequeo de árbol sucio corre **antes de comprometer el archivado**: para
 * entonces la recuperación acotada de staging del flujo actual ya barrió lo
 * propio, y encontrar un cambio ajeno después sería tarde, porque el commit se
 * lo llevaría puesto.
 */

import { execFile, spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';

const ejecutar = promisify(execFile);

export class VaultGitError extends Error {
  constructor(code, message, { path: target = null, detail = null } = {}) {
    super(message);
    this.name = 'VaultGitError';
    this.code = code;
    this.path = target;
    this.detail = detail;
  }
}

async function git(vaultRoot, args, { config = [] } = {}) {
  return ejecutar('git', ['-C', vaultRoot, ...config, ...args]);
}

async function gitWithInput(vaultRoot, args, input = '') {
  return new Promise((resolve, reject) => {
    const child = spawn('git', ['-C', vaultRoot, ...args], { stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    let inputError = null;
    child.stdin.on('error', (error) => { inputError = error; });
    child.once('error', reject);
    child.once('close', (code) => {
      if (inputError !== null && code === 0) reject(inputError);
      else resolve({ code, stdout, stderr });
    });
    child.stdin.end(input);
  });
}

const splitNul = (value) => value.split('\0').filter((entry) => entry.length > 0);

function statusPaths(stdout) {
  const records = splitNul(stdout);
  const paths = [];
  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    const status = record.slice(0, 2);
    paths.push({ status, path: record.slice(3) });
    if (/[RC]/.test(status)) index += 1;
  }
  return paths;
}

const covers = (requested, observed) => observed === requested || observed.startsWith(`${requested}/`);

function coveredRoutes(observedPaths) {
  const covered = new Set();
  for (const observed of observedPaths) {
    covered.add(observed);
    for (let cut = observed.lastIndexOf('/'); cut >= 0; cut = observed.lastIndexOf('/', cut - 1)) {
      covered.add(observed.slice(0, cut));
    }
  }
  return covered;
}

/** `--show-toplevel` resuelto, o `null` si el directorio no está bajo ningún repositorio. */
async function toplevel(vaultRoot) {
  try {
    const { stdout } = await git(vaultRoot, ['rev-parse', '--show-toplevel']);
    return await fs.realpath(stdout.trim());
  } catch {
    return null;
  }
}

/**
 * Lo que un vault recién creado necesita ignorar, y **nada más**.
 *
 * Los dos patrones son la causa medida de que un vault se ensucie solo: Obsidian
 * escribe su configuración al abrirlo y macOS deja `.DS_Store` al navegar sus
 * carpetas. Cualquiera de las dos deja el árbol con cambios ajenos, y el
 * archivado se niega a commitear encima de trabajo de otro: el resultado es un
 * flujo que no se puede archivar por un archivo que nadie escribió a propósito.
 *
 * **Dos y ninguno más.** En un almacén cuyo punto es la procedencia verificada,
 * cada patrón de exclusión es un lugar donde algo puede desaparecer sin que nadie
 * lo note. Estos dos se ganaron el lugar con un caso reproducido; el siguiente
 * tendrá que ganárselo igual.
 *
 * Lo que esto **no** cubre, y conviene saberlo: hacer clic en un `[[enlace]]` no
 * resuelto crea una nota vacía en la raíz del vault, y esa nota es un `.md`
 * legítimo que ningún patrón puede distinguir de un documento real. Se borra a
 * mano.
 */
const IGNORADOS = `# Lo escribe knowledge-vault al crear el vault. Obsidian y macOS ensucian el
# árbol solos, y el archivado se niega a commitear encima de cambios ajenos.
.obsidian/
.DS_Store
`;

/**
 * Siembra el `.gitignore` de un vault **recién creado** y lo commitea.
 *
 * Va en el mismo acto que el `git init` y no en cada corrida: reponerlo sobre un
 * vault existente pisaría una decisión del usuario que borró o editó el suyo. Por
 * lo mismo, un `.gitignore` que ya existe **no se toca** — el directorio pudo ser
 * un repositorio de notas antes de ser un vault.
 *
 * **Se commitea acá y no se deja suelto**, y esa es la parte que no es opcional:
 * `commitFlow` stagea rutas explícitas del flujo en curso, así que un `.gitignore`
 * sin commitear quedaría como cambio ajeno para siempre y bloquearía el primer
 * archivado — exactamente el problema que este archivo viene a evitar.
 */
async function sembrarGitignore(raiz) {
  const destino = path.join(raiz, '.gitignore');
  try {
    await fs.access(destino);
    return; // ya existe: es del usuario, no se toca
  } catch {
    // no existe, se siembra
  }
  await fs.writeFile(destino, IGNORADOS, 'utf8');
  await ejecutar('git', ['-C', raiz, 'add', '--', '.gitignore']);
  await ejecutar('git', ['-C', raiz, ...(await identidad(raiz)),
                         'commit', '-q', '-m', 'siembra el .gitignore del vault']);
}

/**
 * Deja el vault como repositorio Git cuya raíz es exactamente la del vault.
 *
 * Idempotente: sobre un vault ya inicializado no toca nada.
 */
export async function ensureVaultRepo(vaultRoot) {
  const raiz = await fs.realpath(vaultRoot);
  const actual = await toplevel(vaultRoot);

  if (actual !== null && actual !== raiz) {
    throw new VaultGitError(
      'VAULT_NESTED_IN_REPO',
      `la raíz del vault ${JSON.stringify(raiz)} cae dentro del repositorio ${JSON.stringify(actual)}: ` +
        'un vault anidado se commitearía contra el repositorio de afuera',
      { path: raiz, detail: { toplevel: actual } },
    );
  }
  if (actual === null) {
    await ejecutar('git', ['init', '-q', raiz]);
    await sembrarGitignore(raiz);
  }

  const verificado = await toplevel(vaultRoot);
  if (verificado !== raiz) {
    throw new VaultGitError(
      'VAULT_TOPLEVEL_MISMATCH',
      `la raíz de repositorio quedó en ${JSON.stringify(verificado)} y no en ${JSON.stringify(raiz)}`,
      { path: raiz },
    );
  }
  return raiz;
}

/**
 * Falla si el vault tiene cambios **ajenos** sin commitear. Corre después de que
 * la recuperación acotada de staging del flujo actual ya barrió lo propio, y
 * antes de comprometer el archivado.
 *
 * El invariante no es "el árbol está impoluto" sino "el commit del archivado no
 * se va a llevar puesto trabajo de otro". La diferencia importa y costó un
 * defecto: una corrida que muere entre la publicación y el commit deja en el
 * vault exactamente los archivos de ese archivado, sin commitear. Con la versión
 * estricta, ese estado —que es el que AC-6 manda reconstruir— bloqueaba todo
 * reintento, y el flujo quedaba copiado e imposible de completar.
 *
 * `allowed` son las rutas del archivado en curso, relativas a la raíz del vault.
 *
 * **`--untracked-files=all` no es un detalle de formato.** Sin él, `git status`
 * **colapsa** un directorio sin trackear a su ancestro más alto: en un vault
 * donde `projects/` todavía no está trackeado, la frontera recién publicada se
 * reporta como un solo `?? projects/`. Esa ruta es **ancestro** de la ruta
 * propia, no descendiente, así que el predicado de abajo devuelve `false` y el
 * residuo de la propia herramienta se lee como trabajo de una persona — dejando
 * el reintento bloqueado justo en el estado que esta función existe para dejar
 * reconstruir. Pedir el listado completo lo resuelve sin tocar el predicado, que
 * es lo que importa: ampliarlo para aceptar ancestros habría tapado también el
 * residuo de **otros** flujos del mismo proyecto, que sí es ajeno.
 *
 * `anclaEnHead` hace el otro `status` de este módulo y **no** necesita la
 * bandera: consulta rutas explícitas y solo se llega a él si `ls-tree` ya las
 * encontró en `HEAD`, o sea trackeadas, y el colapso es de untracked.
 */
export async function assertVaultClean(vaultRoot, allowed = []) {
  const { stdout } = await git(vaultRoot, [
    '--literal-pathspecs',
    'status',
    '--porcelain=v1',
    '-z',
    '--untracked-files=all',
  ]);
  const own = (target) => allowed.some((candidate) => covers(candidate, target));
  const dirty = statusPaths(stdout).filter((entry) => !own(entry.path));
  if (dirty.length > 0) {
    throw new VaultGitError(
      'VAULT_DIRTY',
      `el vault tiene ${dirty.length} cambio(s) ajeno(s) sin commitear y el archivado se los llevaría puestos`,
      { path: vaultRoot, detail: dirty.map((entry) => `${entry.status} ${entry.path}`) },
    );
  }
}

/** Identidad de respaldo, sólo si el repositorio no tiene una configurada. */
async function identidad(vaultRoot) {
  for (const clave of ['user.name', 'user.email']) {
    try {
      const { stdout } = await git(vaultRoot, ['config', '--get', clave]);
      if (stdout.trim().length === 0) throw new Error('vacío');
    } catch {
      return ['-c', 'user.name=knowledge-vault', '-c', 'user.email=knowledge-vault@localhost'];
    }
  }
  return [];
}

/**
 * Commitea **sólo** las rutas dadas, con un asunto que nombra el flujo.
 *
 * El asunto lo nombra porque es la única forma de responder "¿este flujo llegó al
 * vault?" mirando la historia, que es lo que AC-13 comprueba.
 *
 * @returns {Promise<{committed: boolean, subject: string}>}
 */
export async function commitFlow({ vaultRoot, flowId, paths, subject = null }) {
  if (!Array.isArray(paths) || paths.length === 0) {
    throw new VaultGitError('NOTHING_TO_STAGE', `commitFlow para ${flowId} no recibió rutas`);
  }
  // El índice distingue archivos ya trackeados de destinos nuevos: `git add`
  // rechaza un archivo trackeado bajo un directorio que pasó a estar ignorado,
  // mientras que `git add -u` lo actualiza sin abrir la puerta a un destino nuevo
  // ignorado. Los pathspecs viajan por stdin NUL para no crecer con argv.
  const requested = [...new Set(paths)];
  const index = await gitWithInput(vaultRoot, ['ls-files', '--cached', '-z']);
  if (index.code !== 0) {
    throw new VaultGitError('GIT_LS_FILES_FAILED', `git ls-files falló: ${index.stderr.trim()}`);
  }
  const indexedPaths = splitNul(index.stdout);
  const tracked = new Set(indexedPaths);
  const trackedPrefixes = coveredRoutes(indexedPaths);
  // Un directorio mixto debe pasar por las dos fases: -u toma cambios en los
  // archivos trackeados y add incorpora archivos nuevos bajo ese mismo prefijo.
  // Las rutas documentales exactas no se solapan, pero commitFlow acepta prefijos.
  const updatePaths = requested.filter((route) => trackedPrefixes.has(route));
  const newPaths = requested.filter((route) => !tracked.has(route));
  const stage = async (routes, update) => {
    if (routes.length === 0) return;
    const result = await gitWithInput(vaultRoot, [
      '--literal-pathspecs', 'add', ...(update ? ['-u'] : []),
      '--pathspec-from-file=-', '--pathspec-file-nul',
    ], `${routes.join('\0')}\0`);
    if (result.code !== 0) {
      throw new VaultGitError('GIT_ADD_FAILED', `git add falló: ${result.stderr.trim()}`);
    }
  };
  await stage(updatePaths, true);
  await stage(newPaths, false);

  const staged = await gitWithInput(vaultRoot, ['diff', '--cached', '--name-only']);
  if (staged.code !== 0) {
    throw new VaultGitError('GIT_DIFF_FAILED', `git diff --cached falló: ${staged.stderr.trim()}`);
  }
  // El asunto es parametrizable porque el vault registra **dos** actos distintos
  // sobre el mismo flujo: archivarlo y retirarlo. Compartir el asunto los haría
  // indistinguibles en la historia, que es donde alguien va a buscarlos.
  const asunto = subject ?? `archiva ${flowId}`;
  if (staged.stdout.trim().length === 0) return { committed: false, subject: asunto };

  await git(vaultRoot, ['commit', '-q', '-m', asunto], { config: await identidad(vaultRoot) });
  const { stdout: sha } = await git(vaultRoot, ['rev-parse', 'HEAD']);
  return { committed: true, subject: asunto, commit: sha.trim() };
}

/** El `HEAD` del vault, o `null` si todavía no hay ningún commit. */
export async function headDelVault(vaultRoot) {
  try {
    const { stdout } = await git(vaultRoot, ['rev-parse', 'HEAD']);
    return stdout.trim();
  } catch {
    return null;
  }
}

/**
 * Las señales por las que un repositorio se reconoce, **observadas**.
 *
 * Ninguna es la identidad: la identidad se declara y se confirma. Estas son lo
 * que se coteja contra el registro del vault, y por eso las dos que sirven
 * —remoto y commit raíz— son las que sobreviven a un clon en otra máquina,
 * mientras que la ruta y el nombre del directorio viajan sólo como respaldo.
 *
 * Un repositorio sin remoto, o sin ningún commit, devuelve `null` en esa señal en
 * vez de fallar: quien resuelve decide si con lo que queda alcanza.
 */
export async function senalesDelRepositorio(repoRoot) {
  const leer = async (args) => {
    try {
      const { stdout } = await git(repoRoot, args);
      const valor = stdout.trim().split('\n')[0];
      return valor.length === 0 ? null : valor;
    } catch {
      return null;
    }
  };
  return {
    remoto: await leer(['remote', 'get-url', 'origin']),
    commitRaiz: await leer(['rev-list', '--max-parents=0', 'HEAD']),
    rutaObservada: repoRoot,
    nombreDirectorio: path.basename(repoRoot),
  };
}

/**
 * ¿Cuáles de estas rutas están cubiertas por un archivo presente en el índice?
 *
 * El índice decide si una ruta está trackeada, no el árbol de trabajo: un
 * archivo agregado con `git add` pero sin commitear ya bloquea un borrado
 * destructivo, y `ls-tree HEAD` no lo vería porque todavía no hay commit.
 *
 * @param {string} vaultRoot
 * @param {string[]} rutas relativas a `vaultRoot`; archivos o directorios
 * @returns {Promise<string[]>} el subconjunto de `rutas` cubierto por el índice
 */
export async function rutasTrackeadas(vaultRoot, rutas) {
  const requested = [...new Set(rutas)];
  if (requested.length === 0) return [];
  const { stdout } = await git(vaultRoot, [
    '--literal-pathspecs', 'ls-files', '--cached', '-z', '--', ...requested,
  ]);
  const indexedCovered = coveredRoutes(splitNul(stdout));
  return requested.filter((route) => indexedCovered.has(route));
}

/**
 * ¿Estas rutas concretas están en `HEAD` y limpias?
 *
 * Es la cuarta postcondición del archivado, y reemplaza a la pregunta anterior
 * —"¿hay algún commit cuyo asunto nombre este flujo?"—, que comparaba **asuntos
 * por subcadena**. Esa comparación no puede autorizar un borrado: el commit
 * exacto pudo revertirse, y su asunto sigue en la historia mientras el contenido
 * ya no está. Peor todavía, un asunto ajeno que contenga el id como subcadena la
 * satisface sin que exista un solo byte del flujo.
 *
 * Se le pregunta al **árbol**, que es lo que el retiro va a destruir. Dos
 * condiciones, y las dos hacen falta: que las rutas estén en `HEAD` —commiteadas,
 * no sólo escritas— y que el árbol de trabajo no tenga cambios sobre ellas —lo
 * commiteado es lo que hay—.
 *
 * @param {string} vaultRoot
 * @param {string[]} rutas relativas a `vaultRoot`; archivos o directorios
 * @param {{scanPaths: string[], ignoreIndex?: boolean}} options; prefijos de
 * consulta obligatorios y acotados, que cubren todas las rutas exactas
 * @returns {Promise<boolean>}
 */
export async function rutasNoAncladas(vaultRoot, rutas, { scanPaths, ignoreIndex = false } = {}) {
  if (!Array.isArray(rutas)) {
    throw new VaultGitError('INVALID_PATHS', 'rutasNoAncladas espera una lista de rutas');
  }
  if (!Array.isArray(scanPaths)) {
    throw new VaultGitError('INVALID_SCAN_PATHS', 'rutasNoAncladas exige prefijos de consulta');
  }
  const requested = [...new Set(rutas)];
  if (requested.length === 0) return { missing: [], dirty: [], ignored: [] };
  const scan = [...new Set(scanPaths)];
  if (requested.some((route) => !scan.some((prefix) => covers(prefix, route)))) {
    throw new VaultGitError('INVALID_SCAN_PATHS', 'el prefijo de consulta no cubre todas las rutas exactas');
  }

  let headPaths = [];
  if (await headDelVault(vaultRoot) !== null) {
    const result = await gitWithInput(vaultRoot, [
      '--literal-pathspecs',
      'ls-tree',
      '-r',
      '--name-only',
      '-z',
      'HEAD',
      '--',
      ...scan,
    ]);
    if (result.code !== 0) {
      throw new VaultGitError('GIT_LS_TREE_FAILED', `git ls-tree falló: ${result.stderr.trim()}`);
    }
    headPaths = splitNul(result.stdout);
  }

  const result = await gitWithInput(vaultRoot, [
    '--literal-pathspecs',
    'status',
    '--porcelain=v1',
    '-z',
    '--untracked-files=all',
    '--',
    ...scan,
  ]);
  if (result.code !== 0) {
    throw new VaultGitError('GIT_STATUS_FAILED', `git status falló: ${result.stderr.trim()}`);
  }
  const dirtyPaths = statusPaths(result.stdout).map((entry) => entry.path);

  const ignoredResult = await gitWithInput(
    vaultRoot,
    ['check-ignore', ...(ignoreIndex ? ['--no-index'] : []), '-z', '--stdin'],
    `${requested.join('\0')}\0`,
  );
  if (ignoredResult.code !== 0 && ignoredResult.code !== 1) {
    throw new VaultGitError(
      'GIT_CHECK_IGNORE_FAILED',
      `git check-ignore falló con código ${ignoredResult.code}: ${ignoredResult.stderr.trim()}`,
      { path: vaultRoot },
    );
  }
  const ignoredPaths = ignoredResult.code === 0 ? splitNul(ignoredResult.stdout) : [];

  const headCovered = coveredRoutes(headPaths);
  const dirtyCovered = coveredRoutes(dirtyPaths);
  const ignoredCovered = coveredRoutes(ignoredPaths);
  return {
    missing: requested.filter((route) => !headCovered.has(route)),
    dirty: requested.filter((route) => dirtyCovered.has(route)),
    ignored: requested.filter((route) => ignoredCovered.has(route)),
  };
}

export async function inspectManifestAuthority(vaultRoot, manifestPath) {
  const absolute = path.isAbsolute(manifestPath)
    ? manifestPath
    : path.join(vaultRoot, ...manifestPath.split('/'));
  const relative = path.relative(vaultRoot, absolute).split(path.sep).join('/');
  if (relative === '' || relative === '..' || relative.startsWith('../')) {
    throw new VaultGitError(
      'MANIFEST_OUTSIDE_VAULT',
      `el manifiesto ${JSON.stringify(manifestPath)} no está contenido en el vault`,
      { path: manifestPath },
    );
  }

  const info = await fs.lstat(absolute).catch((error) => {
    if (error?.code === 'ENOENT') return null;
    throw error;
  });
  const diagnostics = await rutasNoAncladas(vaultRoot, [relative], {
    scanPaths: [relative], ignoreIndex: true,
  });
  // La ausencia física no implica ausencia de autoridad: una ruta versionada
  // eliminada del working tree sigue siendo un manifiesto sucio y debe bloquear.
  const exists = info !== null || diagnostics.missing.length === 0;
  return {
    exists,
    anchored: info?.isFile() === true && diagnostics.missing.length === 0,
    dirty: diagnostics.dirty.length > 0,
    ignored: diagnostics.ignored.length > 0,
  };
}

export async function anclaEnHead(vaultRoot, rutas, options = {}) {
  if (!Array.isArray(rutas) || rutas.length === 0) {
    throw new VaultGitError('NOTHING_TO_ANCHOR', 'anclaEnHead no recibió rutas que anclar');
  }
  const diagnostics = await rutasNoAncladas(vaultRoot, rutas, options);
  return diagnostics.missing.length === 0 && diagnostics.dirty.length === 0 && diagnostics.ignored.length === 0;
}
