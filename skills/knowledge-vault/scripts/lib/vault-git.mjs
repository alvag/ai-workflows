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
  if (actual === null) await ejecutar('git', ['init', '-q', raiz]);

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
export async function commitFlow({ vaultRoot, flowId, paths }) {
  if (!Array.isArray(paths) || paths.length === 0) {
    throw new VaultGitError('NOTHING_TO_STAGE', `commitFlow para ${flowId} no recibió rutas`);
  }
  // `--` separa rutas de revisiones: sin él, una ruta que se parezca a un ref
  // haría que `git add` interprete otra cosa.
  await git(vaultRoot, ['add', '--', ...paths]);

  const { stdout: staged } = await git(vaultRoot, ['diff', '--cached', '--name-only']);
  const subject = `archiva ${flowId}`;
  if (staged.trim().length === 0) return { committed: false, subject };

  await git(vaultRoot, ['commit', '-q', '-m', subject], { config: await identidad(vaultRoot) });
  return { committed: true, subject };
}

/**
 * ¿La historia del vault tiene un commit que nombre este flujo?
 *
 * Es la cuarta postcondición del archivado. Se pregunta a la historia y no a un
 * registro propio: el registro podría afirmar que sí mientras el commit no existe.
 */
export async function hasFlowCommit(vaultRoot, flowId) {
  try {
    const { stdout } = await git(vaultRoot, ['log', '--format=%s']);
    return stdout.split('\n').some((asunto) => asunto.includes(flowId));
  } catch {
    // Un repositorio sin ningún commit: `git log` sale distinto de cero.
    return false;
  }
}
