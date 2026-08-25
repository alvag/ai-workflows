/**
 * Resolución de la raíz del vault, fail-closed (AC-31 a AC-34c) — plan §3.4.
 *
 * **Una sola respuesta a "dónde está el vault"**: la raíz declarada. Entra por
 * `--vault-root` (la forma primitiva, que no lee nada) o por `--config` (la
 * sección `knowledge-vault:` de un YAML cuya ruta se recibe). Las dos son
 * excluyentes y no hay precedencia entre ellas: una regla menos que recordar.
 *
 * Acá vivían cuatro formas de responder lo mismo —flag de nombre, marcador
 * `.kv-vault`, `remote_routes` y `path_routes` sobre un registro en
 * `~/.config/kv/config.json`—. Se retiraron: cuatro caminos hacia el mismo dato
 * son cuatro lugares donde puede estar mal, y ninguno ayudaba a crear la
 * configuración la primera vez.
 *
 * **El CLI nunca elige un destino alternativo** (AC-34b): resuelve, o falla
 * nombrando por qué. El fallback lo decide el consumidor al reconocer el estado.
 *
 * Los tres estados no se solapan, y la distinción no es cosmética:
 *
 * | Estado | Cuándo | ¿Degradable? |
 * |---|---|---|
 * | `NO_VAULT`               | No se declaró raíz, el config no existe, o no declara `path_vault` | sí |
 * | `CONFIG_INVALID`         | El config existe pero su forma no se puede leer sin adivinar | **no** (AC-34c) |
 * | `VAULT_ROOT_UNAVAILABLE` | Resolvió, pero la raíz no existe, no es directorio o no es escribible | sí |
 *
 * Degradar ante un archivo roto esconde el error del usuario; degradar ante un
 * vault que todavía no configuró es legítimo.
 *
 * **Sin override por variable de entorno y sin lecturas de `process`**: el home
 * lo inyecta el wrapper y la ruta del config la elige quien invoca.
 */

import { constants } from 'node:fs';
import { readdir, realpath } from 'node:fs/promises';
import path from 'node:path';

import { ConfigYamlError, readPathVault } from './config-yaml.mjs';
import { isInjectedCrash } from './durable-fs.mjs';

export class ConfigError extends Error {
  constructor(code, message, { path: target = null, detail = null } = {}) {
    super(message);
    this.name = 'ConfigError';
    this.code = code;
    this.path = target;
    this.detail = detail;
  }
}

/** `$VAR`, `${VAR}` y `%VAR%`: una raíz no interpola nada. */
const VARIABLE_RE = /\$\{?[A-Za-z_]|%[A-Za-z_][A-Za-z0-9_]*%/;

/**
 * `<home>/.local/state/kv` — donde viven los locks por fuente.
 *
 * Es lo único que `kv` sigue derivando del home: estado efímero de máquina, no
 * algo que el usuario edite ni que tenga sentido sincronizar entre equipos. La
 * configuración ya no vive ahí — se recibe por `--config`.
 */
export function stateDirFor(homeDir) {
  return path.join(homeDir, '.local', 'state', 'kv');
}

function invalid(message, detail = null) {
  return new ConfigError('CONFIG_INVALID', message, { detail });
}

/**
 * Expande `~/…` y valida que la raíz sea utilizable como ruta literal.
 *
 * `origen` nombra de dónde salió el valor —`path_vault`, `vault-root`— y solo
 * alimenta el mensaje: quien lo lee tiene que saber **qué corregir**.
 */
export function resolveVaultRoot(rawRoot, homeDir, origen) {
  if (typeof rawRoot !== 'string' || rawRoot.length === 0) {
    throw invalid(`${JSON.stringify(origen)} no declara una raíz`);
  }
  if (VARIABLE_RE.test(rawRoot)) {
    throw invalid(`la raíz de ${JSON.stringify(origen)} no puede llevar variables: ${rawRoot}`);
  }

  let expandido = rawRoot;
  if (rawRoot === '~') expandido = homeDir;
  else if (rawRoot.startsWith('~/')) expandido = path.join(homeDir, rawRoot.slice(2));
  else if (rawRoot.startsWith('~')) {
    throw invalid(`la raíz de ${JSON.stringify(origen)} usa una forma de ~ no soportada: ${rawRoot}`);
  }

  if (expandido.split(/[/\\]/).includes('..')) {
    throw invalid(`la raíz de ${JSON.stringify(origen)} no puede llevar '..': ${rawRoot}`);
  }
  if (!path.isAbsolute(expandido)) {
    throw invalid(`la raíz de ${JSON.stringify(origen)} debe ser absoluta o empezar en ~/: ${rawRoot}`);
  }
  return expandido;
}

/**
 * El repo es el ancestro más cercano con `.git`; si no hay ninguno, el padre del
 * origen.
 *
 * Ya no alimenta ninguna resolución de vault —ese registro se retiró—, pero sigue
 * siendo la raíz contra la que se derivan el slug legible y el alcance de
 * `doctor`. El nombre del directorio **no es identidad** (AC-4): solo alimenta el
 * tramo legible del slug.
 *
 * `from` no tiene por qué existir: `restore` lo llama sobre un destino que
 * todavía no está creado, y el recorrido sube igual hasta encontrar el repo.
 */
export async function discoverRepoRoot({ fs, from, label = 'config.repo' }) {
  const { root } = path.parse(from);
  let dir = path.dirname(from);

  for (;;) {
    if ((await fs.lstat(path.join(dir, '.git'), label)) !== null) return dir;
    if (dir === root) break;
    dir = path.dirname(dir);
  }
  // Sin `.git` en ningún ancestro, el padre del origen. **No se busca `.plans/`**:
  // era la última traza de SDD en la resolución de rutas de esta skill (AC-2), y
  // conocer esa convención hacía que el repo descubierto dependiera de cómo
  // organiza sus carpetas un consumidor en particular.
  return path.dirname(from);
}

// ── Resolución ────────────────────────────────────────────────────────────────

/**
 * La raíz usable, o el estado que dice por qué no.
 *
 * `homeDir` solo se usa para expandir un `~/` que el usuario haya escrito en su
 * config; **no hay ningún archivo que `kv` busque en el home**. Se inyecta, como
 * en todo `lib/`: este módulo no lee el ambiente.
 */
export async function resolveVaultRootFrom({
  fs,
  configPath = null,
  vaultRoot = null,
  homeDir = null,
  label = 'config.resolve',
}) {
  // Redundante con la tabla congelada de `contracts.mjs`, y a propósito: los
  // comandos no son los únicos que llaman acá, y "cuál de las dos manda" no tiene
  // una respuesta que valga la pena inventar.
  if (vaultRoot !== null && configPath !== null) {
    throw invalid('--config y --vault-root son excluyentes: la raíz del vault se declara de una sola forma');
  }

  if (vaultRoot !== null) {
    const root = resolveVaultRoot(vaultRoot, homeDeclarado(vaultRoot, homeDir), 'vault-root');
    await assertRootUsable({ fs, root, label });
    return { root, source: 'flag' };
  }

  if (configPath === null) {
    throw new ConfigError('NO_VAULT', 'no se declaró la raíz del vault: falta --config o --vault-root');
  }

  const resuelto = path.resolve(configPath);
  let bytes;
  try {
    bytes = await fs.readFile(resuelto, `${label}.read`);
  } catch (error) {
    // Un config ausente es la ausencia de configuración, no un archivo roto: es
    // el estado que habilita que el consumidor pregunte y configure.
    if (error?.code === 'ENOENT' || error?.cause?.code === 'ENOENT') {
      throw new ConfigError('NO_VAULT', `el config ${resuelto} no existe`, { path: resuelto });
    }
    if (isInvalidConfigPathError(error)) {
      throw new ConfigError('CONFIG_INVALID', `no se puede leer ${resuelto}: ${error.message}`, { path: resuelto });
    }
    throw error;
  }

  const declarado = readDeclaredRoot(bytes, resuelto);
  if (declarado === null) {
    throw new ConfigError('NO_VAULT', `el config ${resuelto} no declara path_vault`, { path: resuelto });
  }

  const root = resolveVaultRoot(declarado, homeDeclarado(declarado, homeDir), 'path_vault');
  await assertRootUsable({ fs, root, label });
  return { root, source: 'config' };
}

/**
 * Los errores de lectura que son afirmaciones sobre **la ruta que eligió quien
 * invoca**, no fallos del motor: `--config` apuntando a un directorio, a algo
 * bajo un no-directorio, o a un bucle de enlaces.
 *
 * Vive acá y no en cada lector porque los dos que existen —este módulo y el verbo
 * `config`— tienen que coincidir: la misma ruta no puede salir `CONFIG_INVALID`
 * de `kv config` y `INTERNAL_ERROR` de `kv archive`. Dejarlos propagar crudos era
 * exactamente ese accidente, y T7 ya lo había corregido de un solo lado.
 */
export function isInvalidConfigPathError(error) {
  const codigo = error?.code ?? error?.cause?.code;
  return codigo === 'EISDIR' || codigo === 'ENOTDIR' || codigo === 'ELOOP';
}

/**
 * La raíz que el config declara, o `null` si no declara ninguna.
 *
 * **Vacío o solo espacios cuenta como no declarada.** Una raíz en blanco no es una
 * ruta, y tratarla como tal produciría un destino que el usuario no eligió.
 *
 * Es el único lector del `path_vault` de un archivo ya leído, compartido con el
 * verbo `config`: son la misma pregunta —"¿qué raíz declara este config?"— y dos
 * copias tendrían que coincidir para siempre en tres cosas a la vez (la
 * decodificación, las nueve formas que se rechazan y qué cuenta como vacío).
 */
export function readDeclaredRoot(bytes, target) {
  let texto;
  try {
    texto = new TextDecoder('utf-8', { fatal: true, ignoreBOM: false }).decode(bytes);
  } catch {
    throw new ConfigError('CONFIG_INVALID', `${target} no es UTF-8 válido`, { path: target });
  }

  let declarado;
  try {
    declarado = readPathVault(texto);
  } catch (error) {
    // Las nueve formas ambiguas que `config-yaml.mjs` rechaza. Adivinar cuál de
    // dos secciones manda cambiaría el destino del archivado en silencio.
    if (error instanceof ConfigYamlError) {
      throw new ConfigError('CONFIG_INVALID', error.message, { path: target });
    }
    throw error;
  }

  return declarado === null || declarado.trim().length === 0 ? null : declarado;
}

/**
 * El home con el que expandir un `~`, o el rechazo explicando que falta.
 *
 * `lib/` no lee `process.env` por su cuenta, así que un `~` sin home inyectado no
 * se puede resolver. Se dice por qué en vez de dejar que `path.join` falle con un
 * `undefined` y el fallo salga como un error interno del programa.
 */
function homeDeclarado(raw, homeDir) {
  if (typeof homeDir === 'string' && homeDir.length > 0) return homeDir;
  if (typeof raw !== 'string' || !raw.startsWith('~')) return null;
  throw invalid(
    `no se puede expandir el ~ de ${JSON.stringify(raw)}: esta invocación no declara un directorio home`,
  );
}

/**
 * La raíz tiene que existir, ser un directorio y ser escribible. **Todo** lo que
 * impida comprobarlo cae al mismo estado —`VAULT_ROOT_UNAVAILABLE`— porque el
 * consumidor actúa igual ante todos: puede degradar.
 *
 * Corre en los **dos** caminos, no solo en el del config: una raíz escrita a mano
 * en `--vault-root` se equivoca tanto como una leída de un archivo, y dejarla
 * pasar convertiría un destino inexistente en un `ENOENT` a mitad de la copia.
 *
 * `stat` y no `lstat`: la raíz la declara el usuario, y apuntarla a un enlace
 * hacia un volumen externo es legítimo. La prohibición de symlinks de AC-14 es
 * sobre el árbol de **origen**, no sobre el destino que el usuario eligió.
 */
async function assertRootUsable({ fs, root, label }) {
  const noUsable = (motivo) =>
    new ConfigError('VAULT_ROOT_UNAVAILABLE', `la raíz del vault ${motivo}: ${root}`, { path: root });

  // `fs.stat` solo absorbe "esta ruta no está" (`ENOENT`/`ENOTDIR`); un `ELOOP` o
  // un `EACCES` sobre un ancestro salen crudos. Dejarlos propagar los volvía
  // `INTERNAL_ERROR`, y con eso **un vault en un volumen sin permisos —el caso
  // degradable por antonomasia— se volvía no degradable**: el consumidor no puede
  // reinvocar en local ante un fallo interno. No poder mirar la raíz es
  // exactamente "la raíz no está disponible", que es lo que este estado nombra.
  let info;
  try {
    info = await fs.stat(root, `${label}.stat`);
  } catch (error) {
    // Una caída inyectada no es un fallo de la raíz: el proceso dejó de existir, y
    // convertirla en un estado del contrato sería mentir sobre lo que pasó.
    if (isInjectedCrash(error)) throw error;
    throw noUsable(`no se puede inspeccionar (${error?.code ?? error?.message ?? 'motivo desconocido'})`);
  }

  if (info === null) throw noUsable('no existe');
  if (!info.isDirectory()) throw noUsable('no es un directorio');
  if (!(await fs.access(root, constants.W_OK, `${label}.access`))) throw noUsable('no es escribible');
}

// ── La matriz de rutas (AC-15) ────────────────────────────────────────────────

/** `hijo` está dentro de `padre`, o es el mismo. Sobre rutas ya resueltas. */
function contiene(padre, hijo) {
  if (padre === hijo) return true;
  const prefijo = padre.endsWith(path.sep) ? padre : padre + path.sep;
  return hijo.startsWith(prefijo);
}

/**
 * Las dos condiciones que hay que exigir antes de operar, y **sólo** esas dos.
 *
 * El criterio ingenuo —"que ninguna de las rutas se solape con otra"— bloquea el
 * archivado entero: el directorio de un flujo vive dentro del repositorio por
 * construcción. Lo que importa es distinto:
 *
 *   1. el **vault** es disjunto del repositorio y de la raíz de archivados, en
 *      las dos direcciones. Si viviera adentro, archivar se copiaría a sí mismo
 *      y cada corrida crecería sobre la anterior;
 *   2. el **flujo** es hijo **directo** de la raíz de archivados, así que el
 *      tramo `<flujo>` de la ruta de destino es un solo segmento.
 *
 * Se compara sobre rutas **resueltas**: un vault que es un enlace simbólico al
 * repositorio no comparte un solo carácter de prefijo con él y sin embargo es el
 * mismo directorio.
 *
 * @returns {Promise<{vaultRoot:string, repoRoot:string, archivedRoot:string, flowDir:string}>}
 *   las cuatro rutas ya resueltas, para que el llamador no vuelva a resolverlas.
 */
export async function assertPathMatrix({ vaultRoot, repoRoot, archivedRoot, flowDir }) {
  const entradas = { vaultRoot, repoRoot, archivedRoot, flowDir };
  const resueltas = {};
  for (const [nombre, valor] of Object.entries(entradas)) {
    if (typeof valor !== 'string' || valor.length === 0) {
      throw invalid(`la matriz de rutas exige ${nombre}`);
    }
    try {
      resueltas[nombre] = await realpath(valor);
    } catch (error) {
      throw invalid(`no se puede resolver ${nombre}: ${error.message}`, { path: valor });
    }
  }
  const { vaultRoot: v, repoRoot: r, archivedRoot: a, flowDir: f } = resueltas;

  for (const [nombre, otra] of [['el repositorio', r], ['la raíz de archivados', a]]) {
    if (contiene(v, otra) || contiene(otra, v)) {
      throw invalid(
        `el vault y ${nombre} no son disjuntos: ${JSON.stringify(v)} contra ${JSON.stringify(otra)}`,
        { vault: v, otra },
      );
    }
  }
  if (path.dirname(f) !== a) {
    throw invalid(
      `el flujo no es hijo directo de la raíz de archivados: ${JSON.stringify(f)} bajo ${JSON.stringify(a)}`,
      { flowDir: f, archivedRoot: a },
    );
  }
  return resueltas;
}

/**
 * La matriz de rutas de un objetivo **destructivo** (AC-9).
 *
 * La de arriba vale para copiar, y para copiar alcanza. Para borrar hace falta
 * acotar el **objetivo**, y hay una trampa concreta en el camino barato: derivar
 * la raíz del propio objetivo —`raiz = dirname(objetivo)`— vuelve la condición de
 * hijo directo **tautológica**. Siempre se cumple, nunca detecta nada, y el
 * borrado queda autorizado sobre cualquier ruta del disco. Por eso el flujo y su
 * raíz llegan por **parámetros distintos**, y quien invoca declara los dos.
 *
 * Además el objetivo no puede **contener un repositorio Git**. Un `.plans/` con
 * un submódulo, un worktree o un clon adentro es material de alguien más, y el
 * vault no tiene ninguna copia de él: la frontera verificada cubre `.md` de la
 * raíz del flujo, nada de esto. Las tres formas se rechazan porque las tres son
 * un repositorio y sólo una se ve como directorio:
 *
 * | Forma | Cómo se reconoce |
 * |---|---|
 * | clon normal | `.git/` es un directorio |
 * | árbol de trabajo enlazado o submódulo | `.git` es un **archivo** con `gitdir:` |
 * | repositorio desnudo | no hay `.git`, pero sí `HEAD`, `objects/` y `refs/` |
 *
 * Y un **error de permisos durante la búsqueda detiene**. Leerlo como ausencia
 * —"no pude entrar, así que no hay nada"— es exactamente cómo un borrado se come
 * un repositorio que no llegó a ver.
 *
 * @param {object} args
 * @param {string} args.objetivo el directorio que se va a destruir
 * @param {string} args.raizDeclarada la raíz de archivados, **declarada aparte**
 * @param {string} args.vaultRoot
 * @param {string} args.repoRoot
 * @returns {Promise<{objetivo:string, raizDeclarada:string, vaultRoot:string, repoRoot:string}>}
 */
export async function assertObjetivoDestructivo({ objetivo, raizDeclarada, vaultRoot, repoRoot }) {
  const entradas = { objetivo, raizDeclarada, vaultRoot, repoRoot };
  const resueltas = {};
  for (const [nombre, valor] of Object.entries(entradas)) {
    if (typeof valor !== 'string' || valor.length === 0) {
      throw invalid(`la matriz destructiva exige ${nombre}`);
    }
    try {
      resueltas[nombre] = await realpath(valor);
    } catch (error) {
      // Un objetivo que ya no está no es un caso benigno: significa que alguien
      // más lo movió entre la aprobación y el borrado.
      throw invalid(`no se puede resolver ${nombre}: ${error.message}`, { path: valor });
    }
  }
  const { objetivo: o, raizDeclarada: a, vaultRoot: v, repoRoot: r } = resueltas;

  if (contiene(o, v) || contiene(v, o)) {
    throw invalid(
      `el objetivo y el vault no son disjuntos: ${JSON.stringify(o)} contra ${JSON.stringify(v)}`,
      { objetivo: o, vaultRoot: v },
    );
  }
  if (o === r) {
    throw invalid(`el objetivo es la raíz del repositorio: ${JSON.stringify(o)}`, { objetivo: o });
  }
  if (o === a) {
    throw invalid(
      `el objetivo es la propia raíz de archivados, no un flujo: ${JSON.stringify(o)}`,
      { objetivo: o, raizDeclarada: a },
    );
  }
  if (path.dirname(o) !== a) {
    throw invalid(
      `el objetivo no es hijo directo de la raíz declarada: ${JSON.stringify(o)} bajo ${JSON.stringify(a)}`,
      { objetivo: o, raizDeclarada: a },
    );
  }

  const repositorio = await buscarRepositorio(o);
  if (repositorio !== null) {
    throw invalid(
      `el objetivo contiene un repositorio Git (${repositorio.forma}): ${JSON.stringify(repositorio.path)}`,
      { objetivo: o, ...repositorio },
    );
  }
  return resueltas;
}

/** Las tres formas de un repositorio, o `null`. Un error de permisos **detiene**. */
async function buscarRepositorio(raiz) {
  let entradas;
  try {
    entradas = await readdir(raiz, { withFileTypes: true });
  } catch (error) {
    throw invalid(
      `no se puede enumerar ${JSON.stringify(raiz)} para descartar repositorios: ${error.message}`,
      { path: raiz, code: error.code },
    );
  }

  const nombres = new Set(entradas.map((e) => e.name));
  if (nombres.has('HEAD') && nombres.has('objects') && nombres.has('refs')) {
    return { forma: 'repositorio desnudo', path: raiz };
  }
  for (const entrada of entradas) {
    const abs = path.join(raiz, entrada.name);
    if (entrada.name === '.git') {
      return { forma: entrada.isDirectory() ? 'clon' : 'árbol de trabajo enlazado', path: abs };
    }
    // Sin seguir enlaces: un symlink no se recorre, y tampoco se destruye a
    // través suyo — el borrado quita el enlace, no su destino.
    if (!entrada.isDirectory()) continue;
    const adentro = await buscarRepositorio(abs);
    if (adentro !== null) return adentro;
  }
  return null;
}

// ── E1: la raíz por defecto sale del config del proyecto ──────────────────────

/** Dónde vive el config de un proyecto, relativo a su raíz. */
export const CONFIG_RELPATH = path.join('.specify', 'config.yml');

/**
 * La raíz del repositorio que contiene `dir`.
 *
 * `discoverRepoRoot` recibe una ruta **de archivo** y arranca por su directorio
 * padre, así que pasarle un directorio se saltearía ese mismo directorio. El
 * ancla es un nombre que no existe: sirve sólo para que `dirname` devuelva `dir`.
 */
export async function discoverRepoRootFromDir({ fs, dir, label = 'config.repo' }) {
  return discoverRepoRoot({ fs, from: path.join(dir, '.kv-ancla'), label });
}

/**
 * Resuelve la raíz del vault, cayendo al config del proyecto si no se declaró.
 *
 * Las dos formas explícitas siguen mandando y siguen siendo excluyentes. Lo que
 * agrega esto es el tercer caso —ninguna de las dos— que antes era un error:
 * `<raíz del repo>/.specify/config.yml`. Como ese archivo es **por proyecto**,
 * un repositorio archiva en un vault y otro en otro sin nada global y sin cargar
 * la ruta en cada invocación.
 */
export async function resolveVaultRootWithDefault({
  fs,
  configPath = null,
  vaultRoot = null,
  repoRoot,
  homeDir = null,
  label = 'config.resolve',
}) {
  if (vaultRoot !== null || configPath !== null) {
    return resolveVaultRootFrom({ fs, configPath, vaultRoot, homeDir, label });
  }
  const porDefecto = path.join(repoRoot, CONFIG_RELPATH);
  const resuelto = await resolveVaultRootFrom({ fs, configPath: porDefecto, homeDir, label });
  return { ...resuelto, source: 'config-por-defecto' };
}
