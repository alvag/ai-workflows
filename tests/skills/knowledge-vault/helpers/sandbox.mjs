/**
 * Sandbox obligatorio de tests (AC-55).
 *
 * Cada test crea **un solo** `mkdtemp` y deriva de esa raíz HOME, la configuración,
 * el state del usuario, los repos, los vaults, el staging y los destinos. Ninguna
 * prueba escribe fuera de ahí.
 *
 * La aserción de encierro resuelve symlinks antes de comparar. Una comparación
 * puramente léxica no alcanza: un enlace *dentro* del sandbox que apunte afuera
 * pasaría el chequeo, y este proyecto borra árboles del usuario.
 */

import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm, realpath, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

/**
 * Resuelve `p` a una ruta absoluta con los symlinks del prefijo *existente* ya
 * resueltos. Los segmentos que todavía no existen se vuelven a pegar tal cual.
 *
 * Hace falta porque una ruta observada puede no existir (un destino que se va a
 * crear) y `realpath` fallaría con `ENOENT` sobre la ruta entera.
 */
async function resolveExistingPrefix(target) {
  let current = path.resolve(target);
  const missing = [];

  for (;;) {
    try {
      const real = await realpath(current);
      return missing.length === 0 ? real : path.join(real, ...missing.reverse());
    } catch (err) {
      if (err.code !== 'ENOENT' && err.code !== 'ENOTDIR') throw err;
      const parent = path.dirname(current);
      // Se agotó el ascenso: nada del prefijo existe.
      if (parent === current) return path.resolve(target);
      missing.push(path.basename(current));
      current = parent;
    }
  }
}

/**
 * Encierro léxico sobre rutas ya resueltas. `path.relative` es lo correcto acá:
 * `startsWith` daría por bueno un hermano con prefijo común (`/tmp/kv-1` contra
 * `/tmp/kv-12`), que es exactamente el escape que esto tiene que atajar.
 */
function isLexicallyInside(root, candidate) {
  const rel = path.relative(root, candidate);
  if (rel === '') return true;
  if (path.isAbsolute(rel)) return false;
  return rel !== '..' && !rel.startsWith(`..${path.sep}`);
}

/**
 * Crea el sandbox. Si se le pasa el contexto `t` de `node:test`, registra la
 * limpieza automática; si no, el llamador es dueño de `cleanup()`.
 */
export async function createSandbox(t, { prefix = 'kv-test-' } = {}) {
  // `realpath` de entrada: en macOS `os.tmpdir()` es `/var/folders/...`, un symlink
  // a `/private/var/folders/...`. Sin esto, toda ruta observada parecería estar
  // fuera de la raíz.
  const root = await realpath(await mkdtemp(path.join(await realpath(tmpdir()), prefix)));

  const home = path.join(root, 'home');
  const configDir = path.join(home, '.config', 'kv');
  const configPath = path.join(configDir, 'config.json');
  const stateDir = path.join(home, '.local', 'state', 'kv');
  const locksDir = path.join(stateDir, 'locks');
  const reposDir = path.join(root, 'repos');
  const vaultsDir = path.join(root, 'vaults');
  const destDir = path.join(root, 'dest');
  const scratchDir = path.join(root, 'scratch');

  for (const dir of [configDir, locksDir, reposDir, vaultsDir, destDir, scratchDir]) {
    await mkdir(dir, { recursive: true });
  }

  const observedPaths = [];

  const sandbox = {
    root,
    home,
    configDir,
    configPath,
    stateDir,
    locksDir,
    reposDir,
    vaultsDir,
    destDir,
    scratchDir,

    /** Ruta dentro del sandbox. No crea nada. */
    path(...segments) {
      return path.join(root, ...segments);
    },

    /**
     * Entorno para procesos hijo. Solo `HOME` (y su equivalente en Windows):
     * `kv` resuelve su configuración desde el home y **no** acepta override por
     * variable de entorno, así que exportar `XDG_*` acá enmascararía esa
     * regresión en vez de detectarla.
     */
    env(extra = {}) {
      return { ...process.env, HOME: home, USERPROFILE: home, ...extra };
    },

    /** Registra una ruta observada para verificarla después. Devuelve la ruta. */
    observe(target, label = null) {
      observedPaths.push({ target, label });
      return target;
    },

    observed() {
      return observedPaths.map((entry) => entry.target);
    },

    /** Falla si `target` queda fuera de la raíz del sandbox. */
    async assertInside(target, label = null) {
      const resolved = await resolveExistingPrefix(target);
      if (isLexicallyInside(root, resolved)) return resolved;
      const where = label ? `${label} (${target})` : String(target);
      throw new assert.AssertionError({
        message: `ruta fuera del sandbox: ${where} → ${resolved} (raíz: ${root})`,
        actual: resolved,
        expected: root,
        operator: 'assertInside',
      });
    },

    /** Verifica de una sola vez todo lo registrado con `observe()`. */
    async assertAllObservedInside() {
      for (const { target, label } of observedPaths) {
        await sandbox.assertInside(target, label);
      }
      return observedPaths.length;
    },

    /**
     * Crea un árbol desde una especificación plana.
     * Clave terminada en `/` → directorio; cualquier otra → archivo con ese
     * contenido (string o Buffer).
     *
     * Cada clave se encierra dos veces: dentro del sandbox y dentro del propio
     * `base`. Lo segundo no es redundante — un `..` desde un `base` profundo
     * sigue cayendo dentro del sandbox y ensuciaría un árbol vecino sin que
     * ningún chequeo se queje.
     */
    async makeTree(base, spec) {
      const resolvedBase = await sandbox.assertInside(base, 'makeTree(base)');
      await mkdir(resolvedBase, { recursive: true });
      for (const [relative, content] of Object.entries(spec)) {
        const target = path.join(resolvedBase, relative);
        await sandbox.assertInside(target, `makeTree(${relative})`);
        if (!isLexicallyInside(resolvedBase, path.resolve(target))) {
          throw new assert.AssertionError({
            message: `makeTree(${relative}) escapa de su base: ${target} (base: ${resolvedBase})`,
            actual: target,
            expected: resolvedBase,
            operator: 'makeTree',
          });
        }
        if (relative.endsWith('/')) {
          await mkdir(target, { recursive: true });
          continue;
        }
        await mkdir(path.dirname(target), { recursive: true });
        await writeFile(target, content ?? '');
      }
      return resolvedBase;
    },

    /** Crea un symlink dentro del sandbox. El destino puede ser cualquiera. */
    async makeSymlink(linkPath, target, type = undefined) {
      await sandbox.assertInside(linkPath, 'makeSymlink(link)');
      await mkdir(path.dirname(linkPath), { recursive: true });
      await symlink(target, linkPath, type);
      return linkPath;
    },

    /**
     * Un repo **con `.git`**, como el de verdad.
     *
     * Antes alcanzaba con el directorio pelado porque `discoverRepoRoot` caía a
     * `.plans/` cuando no encontraba `.git`. Ese fallback se fue (AC-2): era la
     * última traza de SDD en la resolución de rutas. Un sandbox sin `.git` ahora
     * resuelve el repo en `.plans/`, que es correcto y no es lo que el test quiere
     * probar.
     */
    async makeRepo(name) {
      return sandbox.makeTree(path.join(reposDir, name), { '.git/HEAD': 'ref: refs/heads/main\n' });
    },

    async makeVault(name) {
      return sandbox.makeTree(path.join(vaultsDir, name), {});
    },

    async cleanup() {
      await rm(root, { recursive: true, force: true });
    },
  };

  if (t && typeof t.after === 'function') t.after(() => sandbox.cleanup());

  return sandbox;
}
