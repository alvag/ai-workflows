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
 * El chequeo de árbol sucio corre **antes de escribir**: encontrarlo después ya
 * es tarde, porque el commit del archivado se llevaría puestos los cambios ajenos.
 */

import { execFile } from 'node:child_process';
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
 * Falla si el vault tiene cambios **ajenos** sin commitear. Se llama antes de escribir.
 *
 * El invariante no es "el árbol está impoluto" sino "el commit del archivado no
 * se va a llevar puesto trabajo de otro". La diferencia importa y costó un
 * defecto: una corrida que muere entre la publicación y el commit deja en el
 * vault exactamente los archivos de ese archivado, sin commitear. Con la versión
 * estricta, ese estado —que es el que AC-6 manda reconstruir— bloqueaba todo
 * reintento, y el flujo quedaba copiado e imposible de completar.
 *
 * `allowed` son las rutas del archivado en curso, relativas a la raíz del vault.
 */
export async function assertVaultClean(vaultRoot, allowed = []) {
  const { stdout } = await git(vaultRoot, ['status', '--porcelain']);
  const propio = (ruta) => allowed.some((a) => ruta === a || ruta.startsWith(`${a}/`));
  const sucio = stdout
    .split('\n')
    .filter((l) => l.trim().length > 0)
    // El formato es `XY <ruta>`; un rename trae `origen -> destino` y se juzga
    // por el destino, que es lo que quedaría staged.
    .filter((l) => !propio(l.slice(3).split(' -> ').at(-1).replace(/^"|"$/g, '')));
  if (sucio.length > 0) {
    throw new VaultGitError(
      'VAULT_DIRTY',
      `el vault tiene ${sucio.length} cambio(s) ajeno(s) sin commitear y el archivado se los llevaría puestos`,
      { path: vaultRoot, detail: sucio },
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
  // `--` separa rutas de revisiones: sin él, una ruta que se parezca a un ref
  // haría que `git add` interprete otra cosa.
  await git(vaultRoot, ['add', '--', ...paths]);

  const { stdout: staged } = await git(vaultRoot, ['diff', '--cached', '--name-only']);
  // El asunto es parametrizable porque el vault registra **dos** actos distintos
  // sobre el mismo flujo: archivarlo y retirarlo. Compartir el asunto los haría
  // indistinguibles en la historia, que es donde alguien va a buscarlos.
  const asunto = subject ?? `archiva ${flowId}`;
  if (staged.trim().length === 0) return { committed: false, subject: asunto };

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
 * @returns {Promise<boolean>}
 */
export async function anclaEnHead(vaultRoot, rutas) {
  if (!Array.isArray(rutas) || rutas.length === 0) {
    throw new VaultGitError('NOTHING_TO_ANCHOR', 'anclaEnHead no recibió rutas que anclar');
  }
  for (const ruta of rutas) {
    let stdout;
    try {
      // `-r` para que un directorio se resuelva a sus blobs, y `--` para que una
      // ruta que se parezca a un ref no se lea como revisión.
      ({ stdout } = await git(vaultRoot, ['ls-tree', '-r', '--name-only', 'HEAD', '--', ruta]));
    } catch {
      // Un repositorio sin ningún commit: `HEAD` no resuelve.
      return false;
    }
    if (stdout.trim().length === 0) return false;
  }

  const { stdout: sucio } = await git(vaultRoot, ['status', '--porcelain', '--', ...rutas]);
  return sucio.trim().length === 0;
}
