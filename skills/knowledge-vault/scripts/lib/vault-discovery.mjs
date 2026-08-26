/**
 * Descubrir vaults candidatos cuando el proyecto no declara ninguno.
 *
 * `kv` **no tiene registro global** —esa es la decisión que hace que cada
 * proyecto apunte a su propio vault sin ningún archivo central— y de ahí se
 * sigue el problema que este módulo resuelve: en un proyecto nuevo no hay dónde
 * mirar, así que `archive` falla con `NO_VAULT` y quien lo invoca tiene que
 * saber de memoria dónde está su vault. Descubrir **no es** registrar: se mira
 * el disco en el momento y no se persiste nada.
 *
 * ## Por qué la clasificación no puede ser por ubicación
 *
 * La tentación es listar `~/vaults/*` y ofrecer lo que haya. Medido sobre un
 * home real, eso ofrece un vault de **Obsidian ajeno** —un directorio con
 * `.obsidian/` que la persona usa para otra cosa— y aceptarlo tiene consecuencia:
 * `ensureVaultRepo` le hace `git init` antes de que ninguna otra guarda mire, y
 * un archivado sobre un directorio limpio lo convertiría en vault de `kv`.
 *
 * Por eso se clasifica por **marca estructural**, que es lo que un vault de `kv`
 * tiene y un vault de notas no: `.kv/`, o el par `index.md` + `projects/`. Sobre
 * ese mismo home el criterio encontró el único vault real y descartó el ajeno.
 *
 * ## La poda, y su disparador
 *
 * Recorrer un home entero es caro y toca directorios que no pueden contener un
 * vault. La poda es una **lista cerrada**: nombres que empiezan con `.` —un vault
 * no es oculto, y así se evitan `.git`, `.Trash` y las caches— más `node_modules`,
 * `Library` y `Applications`. El disparador para tocarla es que aparezca una
 * ubicación convencional de vaults dentro de algo que hoy se poda; no se agregan
 * nombres por sospecha.
 *
 * Un directorio ilegible —permisos, típicamente `~/Library` en macOS— se saltea
 * sin fallar: el descubrimiento es una ayuda, y abortarlo entero porque una rama
 * del home no se deja mirar lo volvería inservible justo donde más se necesita.
 */

import path from 'node:path';

/** Las cuatro clases. Enum cerrado: quien consume ramifica sobre estos valores. */
export const CLASES = Object.freeze({
  KV: 'vault-kv',
  OBSIDIAN: 'obsidian-ajeno',
  VACIO: 'vacio',
  OTRO: 'otro',
});

/** Nombres que nunca se recorren. Lista cerrada; su disparador está arriba. */
const PODADOS = new Set(['node_modules', 'Library', 'Applications']);

function seRecorre(nombre) {
  return !nombre.startsWith('.') && !PODADOS.has(nombre);
}

/**
 * Lista los **nombres** de un directorio, o `null` si no se deja mirar.
 *
 * `readDirNames` no devuelve strings sino `{name, bytes}` por entrada —conserva
 * los bytes originales para que un nombre que no sobrevive el ida y vuelta UTF-8
 * detenga la operación en vez de colapsar con otro—, así que acá se proyecta el
 * nombre y se pierde adrede esa distinción: este módulo clasifica directorios,
 * no copia archivos, y ningún nombre suyo termina en una ruta de destino.
 */
async function nombresDe(fs, dir, label) {
  try {
    return (await fs.readDirNames(dir, label)).map(({ name }) => name);
  } catch {
    return null;
  }
}

async function esDirectorio(fs, target, label) {
  try {
    const info = await fs.lstat(target, label);
    return info !== null && info.isDirectory();
  } catch {
    return false;
  }
}

/**
 * Clasifica un directorio por su marca estructural.
 *
 * `.kv/` es la marca fuerte: sólo la escribe esta skill. El par
 * `index.md` + `projects/` es la de un vault anterior a `.kv`, y se conserva
 * porque un vault que nunca declaró identidad ni retiró nada no tiene `.kv/`.
 *
 * @returns {Promise<{clase: string, nombres: string[]|null}>}
 */
export async function clasificarDirectorio({ fs, dir, label = 'discovery.clasificar' }) {
  const nombres = await nombresDe(fs, dir, `${label}.readdir`);
  if (nombres === null) return { clase: CLASES.OTRO, nombres: null };

  const tiene = new Set(nombres);
  if (tiene.has('.kv') && (await esDirectorio(fs, path.join(dir, '.kv'), `${label}.kv`))) {
    return { clase: CLASES.KV, nombres };
  }
  if (tiene.has('index.md') && (await esDirectorio(fs, path.join(dir, 'projects'), `${label}.projects`))) {
    return { clase: CLASES.KV, nombres };
  }
  // `.DS_Store` no es contenido: un directorio que sólo lo tiene está vacío para
  // cualquier propósito, y es el estado normal de una carpeta que se abrió en el
  // explorador de archivos de macOS y nunca se usó.
  const sustantivos = nombres.filter((n) => n !== '.DS_Store' && n !== '.obsidian');

  // **`.obsidian/` solo no alcanza para declararlo ajeno**, y la distinción no es
  // cosmética: un vault de `kv` recién creado que alguien abrió en Obsidian antes
  // de archivar nada tiene exactamente esa forma, y rechazarlo sería un falso
  // positivo sobre el camino normal. Lo que lo vuelve ajeno es tener **notas**.
  if (
    tiene.has('.obsidian') &&
    sustantivos.some((n) => n.toLowerCase().endsWith('.md')) &&
    (await esDirectorio(fs, path.join(dir, '.obsidian'), `${label}.obsidian`))
  ) {
    return { clase: CLASES.OBSIDIAN, nombres };
  }
  return { clase: sustantivos.length === 0 ? CLASES.VACIO : CLASES.OTRO, nombres };
}

/** Cuántos proyectos y flujos tiene un vault de `kv`. Best-effort: nunca falla. */
async function evidenciaDe(fs, root, label) {
  const proyectosDir = path.join(root, 'projects');
  const proyectos = (await nombresDe(fs, proyectosDir, `${label}.projects`)) ?? [];
  const nombresProyecto = proyectos.filter((n) => !n.startsWith('.') && !n.endsWith('.md'));
  let flujos = 0;
  for (const p of nombresProyecto) {
    const sdd = (await nombresDe(fs, path.join(proyectosDir, p, 'sdd'), `${label}.sdd`)) ?? [];
    // El nodo de un flujo es `<flujo>.md` junto a su directorio `<flujo>/`; se
    // cuentan los `.md` para no contar cada flujo dos veces.
    flujos += sdd.filter((n) => n.endsWith('.md') && n !== 'index.md').length;
  }
  return { proyectos: nombresProyecto.length, flujos, nombresProyecto: nombresProyecto.sort() };
}

/**
 * Recorre las raíces hasta `maxDepth` y devuelve los candidatos ordenados por
 * ruta. No desciende dentro de un candidato: un vault no contiene otro.
 *
 * @param {object} args
 * @param {object} args.fs sistema de archivos inyectado
 * @param {string[]} args.raices desde dónde buscar
 * @param {number} args.maxDepth profundidad máxima, contando la raíz como 0
 * @returns {Promise<{candidatos: Array<{root: string, clase: string, evidencia: object|null}>}>}
 */
export async function descubrirVaults({ fs, raices, maxDepth = 3, label = 'discovery' }) {
  const candidatos = [];
  const vistos = new Set();
  let pendientes = [...new Set(raices.map((r) => path.resolve(r)))].map((dir) => ({ dir, profundidad: 0 }));

  while (pendientes.length > 0) {
    const siguiente = [];
    for (const { dir, profundidad } of pendientes) {
      if (vistos.has(dir)) continue;
      vistos.add(dir);

      const { clase, nombres } = await clasificarDirectorio({ fs, dir, label: `${label}.clasificar` });
      if (clase === CLASES.KV) {
        candidatos.push({ root: dir, clase, evidencia: await evidenciaDe(fs, dir, `${label}.evidencia`) });
        continue; // un vault no contiene otro
      }
      if (clase === CLASES.OBSIDIAN) {
        candidatos.push({ root: dir, clase, evidencia: null });
        continue;
      }
      if (nombres === null || profundidad >= maxDepth) continue;

      for (const nombre of nombres) {
        if (!seRecorre(nombre)) continue;
        const hijo = path.join(dir, nombre);
        if (await esDirectorio(fs, hijo, `${label}.hijo`)) {
          siguiente.push({ dir: hijo, profundidad: profundidad + 1 });
        }
      }
    }
    pendientes = siguiente;
  }

  candidatos.sort((a, b) => (a.root < b.root ? -1 : a.root > b.root ? 1 : 0));
  return { candidatos };
}
