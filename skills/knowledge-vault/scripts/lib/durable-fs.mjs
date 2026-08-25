/**
 * Capa de I/O inyectable y etiquetada (AC-7, AC-25b) — plan §4.
 *
 * **Toda** operación de disco pasa por acá con un *label*. Eso compra tres cosas
 * que no se consiguen de otro modo:
 *
 * 1. **Inyección de fallos por label** (`failAt`): el test hace fallar exactamente
 *    `publish.rename` y comprueba en qué estado quedaron origen, destino, journal
 *    y staging.
 * 2. **Inyección de caídas** (`crashAt` + `checkpoint`): simula que el proceso
 *    muere justo después de una transición durable. El test **reejecuta el verbo**
 *    sobre el árbol resultante, sin matar procesos de verdad.
 * 3. **Recorder de la secuencia completa**: el oracle del **orden**, no solo del
 *    disparo. Que el receipt se escriba antes de publicar (paso 8 antes del 15)
 *    no se puede verificar mirando el árbol final — hay que mirar la traza.
 *
 * Dos decisiones que son garantías, no detalles:
 *
 * - **`removeEmptyDir` es una primitiva propia, no recursiva, que falla ante
 *   `ENOTEMPTY`.** Entre clasificar un directorio como vacío y borrarlo puede
 *   aparecer contenido, y un `rmTree` lo eliminaría en silencio.
 * - **`fsync` es fail-closed.** Si la plataforma no lo soporta, se levanta el
 *   error en vez de seguir: no se reporta una durabilidad que no se puede
 *   sostener (R8 del plan).
 */

import { isUtf8 } from 'node:buffer';
import { createHash, randomBytes } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

export class DurableFsError extends Error {
  constructor(code, message, { path: target = null, cause = null } = {}) {
    super(message, cause === null ? undefined : { cause });
    this.name = 'DurableFsError';
    this.code = code;
    this.path = target;
  }
}

/**
 * Caída simulada. **No es un error de I/O**: representa que el proceso dejó de
 * existir, así que ningún `catch` del motor debe tragársela. Los bloques de
 * captura del motor tienen que reenviarla usando `isInjectedCrash`.
 */
export class InjectedCrash extends Error {
  constructor(label) {
    super(`caída inyectada en ${label}`);
    this.name = 'InjectedCrash';
    this.label = label;
  }
}

export function isInjectedCrash(error) {
  return error instanceof InjectedCrash;
}

// ── Recorder ──────────────────────────────────────────────────────────────────

/**
 * Traza ordenada de todas las llamadas. El `seq` se asigna **al invocar**, no al
 * terminar, para que el orden sea el de invocación aunque algo corra en paralelo.
 */
export class Recorder {
  #entries = [];
  #next = 0;

  begin(op, label, paths) {
    const entry = { seq: this.#next++, op, label, paths, outcome: 'pending', error: null };
    this.#entries.push(entry);
    return entry;
  }

  get entries() {
    return [...this.#entries];
  }

  /** Labels en orden de invocación. La traza golden se compara contra esto. */
  labels() {
    return this.#entries.map((e) => e.label);
  }

  ops() {
    return this.#entries.map((e) => `${e.op}:${e.label}`);
  }

  /** Solo lo que efectivamente ocurrió, para snapshots de "cero escrituras". */
  succeeded() {
    return this.#entries.filter((e) => e.outcome === 'ok');
  }

  find(label) {
    return this.#entries.filter((e) => e.label === label);
  }

  indexOf(label) {
    return this.#entries.findIndex((e) => e.label === label);
  }

  /** ¿`primero` ocurrió antes que `segundo`? Ambos deben existir. */
  happenedBefore(primero, segundo) {
    const a = this.indexOf(primero);
    const b = this.indexOf(segundo);
    if (a === -1) throw new Error(`la traza no contiene ${primero}`);
    if (b === -1) throw new Error(`la traza no contiene ${segundo}`);
    return a < b;
  }

  reset() {
    this.#entries = [];
    this.#next = 0;
  }
}

// ── Reglas de inyección ───────────────────────────────────────────────────────

/**
 * Normaliza una regla. Formas aceptadas:
 *   'publish.rename'
 *   { label, code, message, nth, partial }
 *   (call) => Error | null
 */
function normalizeRules(spec) {
  if (spec === null || spec === undefined) return [];
  const lista = Array.isArray(spec) ? spec : [spec];
  return lista.map((regla) => {
    if (typeof regla === 'function') return { predicate: regla };
    if (typeof regla === 'string') return { label: regla, nth: 1, hits: 0 };
    return { nth: 1, hits: 0, ...regla };
  });
}

/**
 * Raíces dentro de las cuales una instancia puede destruir.
 *
 * `null` significa **sin contención declarada**, que es lo que usa todo el
 * camino que no destruye fuera del vault y no tiene por qué declararlo. Una
 * lista **vacía** significa "no puede destruir nada", y no es lo mismo: quien
 * destruye lo declara, y declarar cero es una declaración.
 */
function normalizeDestructiveRoots(spec) {
  if (spec === null || spec === undefined) return null;
  const lista = Array.isArray(spec) ? spec : [spec];
  return lista.map((raiz) => path.resolve(raiz));
}

function matchRule(rules, op, label, paths) {
  for (const rule of rules) {
    if (rule.predicate !== undefined) {
      // El predicado recibe también las rutas: sin ellas no se puede expresar
      // un fallo que depende de **dónde** ocurre, como el `EXDEV` que solo pega
      // cuando el destino está en otro volumen y no cuando es un hermano.
      const error = rule.predicate({ op, label, paths });
      if (error) return { rule, error };
      continue;
    }
    if (rule.label !== label) continue;
    rule.hits += 1;
    if (rule.hits !== rule.nth) continue;
    const error = new DurableFsError(
      rule.code ?? 'EIO',
      rule.message ?? `fallo inyectado en ${label}`,
    );
    error.injected = true;
    return { rule, error };
  }
  return null;
}

// ── DurableFs ─────────────────────────────────────────────────────────────────

export class DurableFs {
  #rules;
  #crashRules;
  #recorder;
  #destructiveRoots;

  constructor({ failAt = null, crashAt = null, recorder = null, destructiveRoots = null } = {}) {
    this.#rules = normalizeRules(failAt);
    this.#crashRules = normalizeRules(crashAt);
    this.#recorder = recorder ?? new Recorder();
    this.#destructiveRoots = normalizeDestructiveRoots(destructiveRoots);
  }

  get recorder() {
    return this.#recorder;
  }

  /** Envuelve una operación: etiqueta, registra, e inyecta si corresponde. */
  async #run(op, label, paths, action) {
    if (typeof label !== 'string' || label.length === 0) {
      throw new DurableFsError('MISSING_LABEL', `la operación ${op} necesita un label`);
    }
    const entry = this.#recorder.begin(op, label, paths);

    const crash = matchRule(this.#crashRules, op, label, paths);
    if (crash !== null) {
      entry.outcome = 'crash';
      throw new InjectedCrash(label);
    }

    const inyectado = matchRule(this.#rules, op, label, paths);
    // `partial` deja que la operación produzca su efecto a medias antes de
    // fallar: es lo que hace realista el borrado interrumpido de un remanente.
    if (inyectado !== null && inyectado.rule.partial === undefined) {
      entry.outcome = 'failed';
      entry.error = inyectado.error;
      throw inyectado.error;
    }

    try {
      const resultado = await action(inyectado?.rule ?? null);
      if (inyectado !== null) {
        entry.outcome = 'failed';
        entry.error = inyectado.error;
        throw inyectado.error;
      }
      entry.outcome = 'ok';
      return resultado;
    } catch (error) {
      if (entry.outcome === 'pending') {
        entry.outcome = 'failed';
        entry.error = error;
      }
      throw error;
    }
  }

  /**
   * Punto de caída. Se llama **después de cada transición durable**; sin regla
   * configurada es un no-op, pero queda en la traza como marca de orden.
   */
  checkpoint(label) {
    const entry = this.#recorder.begin('checkpoint', label, []);
    const crash = matchRule(this.#crashRules, 'checkpoint', label, []);
    if (crash !== null) {
      entry.outcome = 'crash';
      throw new InjectedCrash(label);
    }
    entry.outcome = 'ok';
  }

  // ── Primitivas ──────────────────────────────────────────────────────────────
  /**
   * Declara las raíces destructivas de esta instancia, una sola vez.
   *
   * Existe porque quien construye el `DurableFs` —el CLI— no sabe todavía sobre
   * qué se va a destruir: eso lo resuelve el verbo, después de leer la config y
   * la matriz de rutas. Declarar es un acto explícito y **irrepetible**: un
   * segundo intento con otras raíces es un error, no una ampliación, porque
   * ampliar la contención en caliente la vuelve decorativa.
   */
  declararRaicesDestructivas(raices) {
    const nuevas = normalizeDestructiveRoots(raices);
    if (this.#destructiveRoots !== null) {
      const iguales = this.#destructiveRoots.length === nuevas.length &&
        this.#destructiveRoots.every((r, i) => r === nuevas[i]);
      if (iguales) return this;
      throw new DurableFsError(
        'ROOTS_ALREADY_DECLARED',
        'las raíces destructivas ya estaban declaradas y no se amplían en caliente',
        { path: nuevas.join(', ') },
      );
    }
    this.#destructiveRoots = nuevas;
    return this;
  }

  /**
   * Contención de las primitivas destructivas, **inmediatamente antes** de que
   * toquen el disco.
   *
   * Es el complemento en runtime de la guarda estática de la suite. Esa guarda
   * reconoce nombres de variables en llamadas directas, así que un alias
   * (`const borrar = fs.rmTree.bind(fs)`) o un helper intermedio que reciba la
   * ruta por parámetro la evaden sin esfuerzo. Acá no hay a quién engañar: se
   * mira la ruta que llegó, venga de donde venga.
   *
   * La comprobación es **léxica** sobre la ruta normalizada, y `path.relative`
   * en vez de `startsWith` porque un hermano con prefijo común —`/tmp/kv-1`
   * contra `/tmp/kv-12`— es exactamente el escape que hay que atajar. Un enlace
   * simbólico intermedio que apunte fuera de la raíz no lo caza esto: eso lo
   * rechaza la matriz de rutas del objetivo, antes de que una ruta así llegue.
   */
  #assertContenido(op, targets) {
    if (this.#destructiveRoots === null) return;
    for (const target of targets) {
      const abs = path.resolve(target);
      const dentro = this.#destructiveRoots.some((raiz) => {
        const rel = path.relative(raiz, abs);
        return rel === '' || (!path.isAbsolute(rel) && rel !== '..' && !rel.startsWith(`..${path.sep}`));
      });
      if (dentro) continue;
      throw new DurableFsError(
        'OUT_OF_BOUNDS',
        `${op} sobre una ruta fuera de las raíces declaradas: ${abs}`,
        { path: abs },
      );
    }
  }


  async mkdir(target, label, { recursive = false } = {}) {
    return this.#run('mkdir', label, [target], () => fs.mkdir(target, { recursive }));
  }

  /**
   * Creación **exclusiva** con su contenido. Falla con `EEXIST` si ya existe.
   *
   * El plan lista `openExclusive` como primitiva; acá crea y escribe en una sola
   * llamada para que no exista ningún byte escrito fuera de un label — que es
   * justamente lo que esta capa garantiza.
   */
  async openExclusive(target, bytes, label) {
    return this.#run('openExclusive', label, [target], async () => {
      const handle = await fs.open(target, 'wx');
      try {
        await handle.writeFile(bytes);
      } finally {
        await handle.close();
      }
      return bytes.length;
    });
  }

  async copyFile(source, target, label, { exclusive = true } = {}) {
    return this.#run('copyFile', label, [source, target], () =>
      fs.copyFile(source, target, exclusive ? fs.constants.COPYFILE_EXCL : 0),
    );
  }

  async writeFile(target, bytes, label) {
    return this.#run('writeFile', label, [target], () => fs.writeFile(target, bytes));
  }

  async readFile(target, label) {
    return this.#run('readFile', label, [target], () => fs.readFile(target));
  }

  /**
   * `sha256` y tamaño de un archivo, leyendo por bloques.
   *
   * No usa `readFile`: AC-21 obliga a hashear **también** los omitidos, y eso
   * incluye recorrer `node_modules` entero. Cargar cada archivo completo en
   * memoria sería innecesario cuando alcanza con un buffer fijo.
   *
   * El tamaño que devuelve es el **realmente leído**, no el de `lstat`: si el
   * archivo cambió entre una cosa y la otra, el valor honesto es el que se hasheó.
   */
  async hashFile(target, label) {
    return this.#run('hashFile', label, [target], async () => {
      const handle = await fs.open(target, 'r');
      try {
        const hash = createHash('sha256');
        const bloque = Buffer.allocUnsafe(64 * 1024);
        let size = 0;
        for (;;) {
          const { bytesRead } = await handle.read(bloque, 0, bloque.length, null);
          if (bytesRead === 0) break;
          hash.update(bloque.subarray(0, bytesRead));
          size += bytesRead;
        }
        return { sha256: hash.digest('hex'), size };
      } finally {
        await handle.close();
      }
    });
  }

  async fsyncFile(target, label) {
    return this.#run('fsyncFile', label, [target], () => syncPath(target, false));
  }

  async fsyncDir(target, label) {
    return this.#run('fsyncDir', label, [target], () => syncPath(target, true));
  }

  async rename(from, to, label) {
    // Las dos rutas: `from` desaparece de su sitio y `to` puede quedar pisado.
    this.#assertContenido('rename', [from, to]);
    return this.#run('rename', label, [from, to], () => fs.rename(from, to));
  }

  async unlink(target, label) {
    this.#assertContenido('unlink', [target]);
    return this.#run('unlink', label, [target], () => fs.unlink(target));
  }

  async rmTree(target, label) {
    this.#assertContenido('rmTree', [target]);
    return this.#run('rmTree', label, [target], async (rule) => {
      if (rule?.partial !== undefined) {
        // Borra un subconjunto **real** y después falla: es el escenario que
        // deja un remanente a medio borrar y obliga a `DELETE_STARTED` a
        // continuar sin recalcular el digest.
        const entradas = await fs.readdir(target);
        for (const nombre of entradas.slice(0, rule.partial)) {
          await fs.rm(path.join(target, nombre), { recursive: true, force: true });
        }
        return;
      }
      await fs.rm(target, { recursive: true, force: false });
    });
  }

  /**
   * Borra un directorio **vacío**, sin recursión. Falla con `ENOTEMPTY` si ganó
   * contenido entre la clasificación y el retiro.
   *
   * No se reutiliza `rmTree`: eliminaría ese contenido recursivamente, y sería
   * una pérdida de datos silenciosa.
   */
  async removeEmptyDir(target, label) {
    this.#assertContenido('removeEmptyDir', [target]);
    return this.#run('removeEmptyDir', label, [target], async () => {
      try {
        await fs.rmdir(target);
      } catch (error) {
        if (error.code === 'ENOTEMPTY' || error.code === 'EEXIST') {
          throw new DurableFsError(
            'ENOTEMPTY',
            `el directorio dejó de estar vacío: ${target}`,
            { path: target, cause: error },
          );
        }
        throw error;
      }
    });
  }

  /**
   * Sonda de permisos, **sin escribir nada**.
   *
   * No está en la lista de primitivas del plan §4 porque esa lista enumera las
   * que mutan o sincronizan. Comprobar que una raíz de vault es escribible tiene
   * que poder hacerse en `--dry-run`, que no escribe absolutamente nada (AC-49),
   * así que no sirve "probar creando un directorio". `access(W_OK)` es la única
   * consulta que respeta ACLs y usuario efectivo.
   */
  async access(target, mode, label) {
    return this.#run('access', label, [target], async () => {
      try {
        await fs.access(target, mode);
        return true;
      } catch {
        return false;
      }
    });
  }

  /**
   * `lstat`: **no sigue enlaces**. Es la que usa el escaneo del origen, donde un
   * symlink tiene que verse como symlink y abortar (AC-14).
   */
  async lstat(target, label) {
    return this.#run('lstat', label, [target], () => statOrNull(fs.lstat, target));
  }

  /**
   * `stat`: **sigue enlaces**. Solo para rutas que el usuario declaró como
   * destino —la raíz de un vault, por ejemplo—, donde apuntar a un enlace es
   * legítimo. Nunca para clasificar entradas del árbol de origen.
   */
  async stat(target, label) {
    return this.#run('stat', label, [target], () => statOrNull(fs.stat, target));
  }

  /**
   * Resuelve la ruta **real**: sigue cada enlace del trayecto hasta rutas
   * físicas. Solo sirve sobre rutas que existen; sobre una que quizá no exista,
   * `realpathExistingPrefix`.
   */
  async realpath(target, label) {
    return this.#run('realpath', label, [target], () => fs.realpath(target));
  }

  /**
   * La ruta canónica de algo que **puede no existir todavía**: resuelve el
   * ancestro más cercano que sí exista y le vuelve a pegar los segmentos que
   * faltan.
   *
   * Hace falta porque `path.resolve` es **léxico** —no mira el disco— y
   * `realpath` falla con `ENOENT` sobre la ruta entera si el último componente
   * no está. Entre las dos queda un hueco: una ruta cuyo *directorio* es un
   * enlace. Quien derive una identidad de una ruta sin pasar por acá —la clave
   * de un lock, el nombre de un temporal— va a tratar dos caminos al mismo
   * archivo como si fueran dos archivos.
   *
   * Un enlace **roto** se devuelve sin resolver, no falla: es la respuesta
   * honesta —esa es su ruta canónica— y deja que el llamador decida si un
   * destino ausente es un error suyo o no.
   */
  async realpathExistingPrefix(target, label) {
    let actual = path.resolve(target);
    const faltantes = [];

    for (;;) {
      try {
        const real = await this.realpath(actual, label);
        return faltantes.length === 0 ? real : path.join(real, ...faltantes.reverse());
      } catch (error) {
        if (!esRutaAusente(error)) throw error;
        const padre = path.dirname(actual);
        // Se agotó el ascenso sin encontrar nada que exista: no hay qué resolver.
        if (padre === actual) return path.resolve(target);
        faltantes.push(path.basename(actual));
        actual = padre;
      }
    }
  }

  /**
   * Lectura de nombres **congelada** (plan §3.2). Los tres pasos, en orden:
   *
   *   1. `readdir({ encoding: 'buffer' })` — nunca la variante que devuelve strings.
   *   2. `isUtf8()` sobre cada nombre; inválido → `UNSUPPORTED_SOURCE_ENTRY`.
   *   3. Decodificación **fatal**, conservando exactamente los bytes validados.
   *
   * Sin esto el decode normal de Node reemplaza las secuencias inválidas por
   * U+FFFD y dos nombres POSIX distintos colapsan en el mismo path.
   */
  async readDirNames(target, label) {
    return this.#run('readDirNames', label, [target], async () => {
      const buffers = await fs.readdir(target, { encoding: 'buffer' });
      return buffers.map((bytes) => decodeEntryName(bytes, target));
    });
  }

  /**
   * Escritura atómica durable: temporal → `fsync` → `rename` → `fsync` del padre.
   *
   * `uniqueTemp` agrega un sufijo **aleatorio** por invocación, no un contador: dos
   * instancias de `DurableFs` en el mismo proceso comparten `pid`, así que un
   * contador propio de cada instancia arrancaría ambas en el mismo valor y
   * produciría el mismo nombre. El `pid` se conserva en el sufijo solo por
   * trazabilidad —saber qué proceso dejó un temporal huérfano—, no por unicidad:
   * esa la da el componente aleatorio. El temporal fijo (sin `uniqueTemp`) alcanza
   * cuando hay un solo escritor, pero dos escrituras del **mismo** target lo
   * comparten y la segunda pisa el intermedio de la primera.
   *
   * `expectBytes` es la comparación previa a publicar: si el archivo en disco ya no
   * es el que se leyó, se aborta con `CONFLICT` en vez de destruir el cambio ajeno.
   * **No es atómico** —comparar y renombrar son dos operaciones— así que reduce la
   * ventana, no la cierra. Contra escritores cooperantes el mecanismo es el lock;
   * esto es contra el editor que nunca lo va a tomar.
   */
  async writeFileAtomic(target, bytes, label, { uniqueTemp = false, expectBytes = null } = {}) {
    const padre = path.dirname(target);
    const sufijo = uniqueTemp ? `.${process.pid}.${randomBytes(4).toString('hex')}` : '';
    const temporal = path.join(padre, atomicTempName(target, sufijo));

    await this.writeFile(temporal, bytes, `${label}.tmp`);
    await this.fsyncFile(temporal, `${label}.tmp.fsync`);

    if (expectBytes !== null) {
      const actual = await this.#leerParaComparar(target, `${label}.cas`);
      if (!actual.equals(expectBytes)) {
        await this.unlink(temporal, `${label}.tmp.unlink`);
        throw new DurableFsError(
          'CONFLICT',
          `${target} cambió en disco entre la lectura y la publicación; no se sobrescribe`,
          { path: target },
        );
      }
    }

    await this.rename(temporal, target, `${label}.rename`);
    await this.fsyncDir(padre, `${label}.fsync-dir`);
  }

  /** Los bytes actuales, o un buffer vacío si el archivo no existe. */
  async #leerParaComparar(target, label) {
    try {
      return await this.readFile(target, label);
    } catch (error) {
      if (error?.code === 'ENOENT' || error?.cause?.code === 'ENOENT') return Buffer.alloc(0);
      throw error;
    }
  }
}

// ── Auxiliares ────────────────────────────────────────────────────────────────

/**
 * El nombre del temporal que `writeFileAtomic` usa para `target`.
 *
 * Prefijo propio y oculto: un temporal abandonado por una caída tiene que ser
 * reconocible como de `kv` y no confundirse con material del usuario ni con un
 * staging de publicación, que llevan sus propios prefijos.
 */
export function atomicTempName(target, sufijo = '') {
  return `.kv-tmp-${path.basename(target)}${sufijo}`;
}

/** La forma exacta del sufijo de `uniqueTemp`: `.<pid>.<4 bytes en hex>`. */
const UNIQUE_TEMP_SUFFIX_RE = /^\.\d+\.[0-9a-f]{8}$/;

/**
 * `true` si `name` es un temporal **con sufijo único** de los que
 * `writeFileAtomic` crea al escribir `target`.
 *
 * Existe para que quien barra huérfanos no rearme el patrón por su cuenta: el
 * nombre lo construye este módulo, y saberlo en dos lados haría que cambiar el
 * sufijo dejara el barrido sin barrer, en silencio. El temporal **sin** sufijo
 * queda fuera a propósito: no lo distingue de nada y borrarlo sería adivinar.
 */
export function isUniqueAtomicTempName(name, target) {
  const prefijo = atomicTempName(target);
  return name.startsWith(prefijo) && UNIQUE_TEMP_SUFFIX_RE.test(name.slice(prefijo.length));
}

/**
 * "Esta ruta no está" — incluyendo `ENOTDIR`, que es lo que responde el sistema
 * cuando un componente intermedio existe pero no es un directorio.
 */
function esRutaAusente(error) {
  const code = error?.code ?? error?.cause?.code;
  return code === 'ENOENT' || code === 'ENOTDIR';
}

async function statOrNull(fn, target) {
  try {
    return await fn(target);
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return null;
    throw error;
  }
}

/** Errno que significan "esta plataforma no lo soporta", no "esto falló". */
const OPEN_UNSUPPORTED = ['EISDIR', 'EPERM', 'EACCES'];
const SYNC_UNSUPPORTED = ['EINVAL', 'EPERM', 'ENOTSUP', 'EBADF'];

/**
 * Traduce un error de `open`/`fsync` al fallo cerrado de R8.
 *
 * Se exporta y vive aparte para poder probarse con errores sintéticos: en una
 * plataforma que **sí** soporta `fsync` de directorios no hay forma de provocar
 * el caso real, y probarlo inyectando ya el `FSYNC_UNSUPPORTED` sería probar el
 * inyector en vez de esta traducción.
 */
export function classifyFsyncError(error, target, { stage }) {
  const noSoportado = stage === 'open' ? OPEN_UNSUPPORTED : SYNC_UNSUPPORTED;
  if (!noSoportado.includes(error.code)) return error;
  return new DurableFsError(
    'FSYNC_UNSUPPORTED',
    `esta plataforma no soporta fsync sobre ${target}`,
    { path: target, cause: error },
  );
}

/**
 * `fsync` fail-closed. Si la plataforma no lo soporta se levanta el error en vez
 * de seguir: reportar una durabilidad que no se puede sostener es peor que
 * fallar (R8 del plan).
 */
async function syncPath(target, isDirectory) {
  let handle;
  try {
    handle = await fs.open(target, 'r');
  } catch (error) {
    // Esta rama solo dispara en Windows: en POSIX abrir un directorio en modo
    // lectura funciona. La suite la cubre por `classifyFsyncError` con errores
    // sintéticos, no de punta a punta — es el R6 del plan, que declara que
    // Windows no se valida en vez de afirmar que sí.
    throw isDirectory ? classifyFsyncError(error, target, { stage: 'open' }) : error;
  }
  try {
    await handle.sync();
  } catch (error) {
    throw classifyFsyncError(error, target, { stage: 'sync' });
  } finally {
    await handle.close();
  }
}

/** Valida y decodifica un nombre de entrada, comprobando el ida y vuelta exacto. */
export function decodeEntryName(bytes, dirPath = null) {
  if (!isUtf8(bytes)) {
    throw new DurableFsError(
      'UNSUPPORTED_SOURCE_ENTRY',
      `nombre de archivo con bytes que no son UTF-8 válido en ${dirPath ?? '(desconocido)'}`,
      { path: dirPath },
    );
  }

  let name;
  try {
    name = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch (error) {
    throw new DurableFsError(
      'UNSUPPORTED_SOURCE_ENTRY',
      `nombre de archivo indecodificable en ${dirPath ?? '(desconocido)'}`,
      { path: dirPath, cause: error },
    );
  }

  // `ignoreBOM: true` conserva un U+FEFF inicial: con el default el decoder lo
  // consumiría y el nombre perdería bytes en silencio.
  //
  // La comprobación de ida y vuelta es **redundante** con las dos de arriba: hoy
  // no hay entrada que las pase y falle acá. Se conserva igual porque es la única
  // que sigue siendo válida si alguien cambia las opciones del decoder, y cuesta
  // una comparación de buffers.
  if (!Buffer.from(name, 'utf8').equals(bytes)) {
    throw new DurableFsError(
      'UNSUPPORTED_SOURCE_ENTRY',
      `el nombre no sobrevive el ida y vuelta UTF-8 en ${dirPath ?? '(desconocido)'}`,
      { path: dirPath },
    );
  }

  return { name, bytes };
}
