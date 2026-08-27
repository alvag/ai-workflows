/**
 * El verbo `config`: leer y escribir `path_vault` en el config del proyecto.
 *
 * `kv` **no tiene un archivo de configuración propio**. Escribe en el que ya usa
 * el consumidor —para un repositorio con flujos SDD, `.specify/config.yml`— bajo
 * una sección `knowledge-vault:` que nadie más toca. Eso es lo que hace que cada
 * proyecto apunte a su propio vault sin ningún registro global, y lo que obliga a
 * que la escritura sea **por líneas** y no reserializando: el archivo es de otro,
 * y volver a emitirlo con un serializador le reescribiría el formato entero.
 */

import path from 'node:path';

import { readPathVault, upsertPathVault } from '../config-yaml.mjs';
import { ConfigError, assertRootUsable, resolveVaultRoot } from '../config.mjs';
import { ContractError } from '../contracts.mjs';
import { CLASES, descubrirVaults } from '../vault-discovery.mjs';

async function leerSiExiste(fs, ruta, label) {
  try {
    return (await fs.readFile(ruta, label)).toString('utf8');
  } catch (error) {
    if (error?.code === 'ENOENT' || error?.cause?.code === 'ENOENT') return null;
    throw error;
  }
}

export async function configCommand({ fs, flags, homeDir = null, label = 'config' }) {
  if (flags.discover === true) {
    // `--set-root` quedaba parseada y descartada en silencio: quien corría
    // `config --discover --set-root <ruta>` obtenía exit 0 y un listado, y creía
    // que la raíz había quedado declarada cuando no se escribió nada. Es la misma
    // clase que el parser ya cierra para las banderas que ningún verbo declara —
    // acá el nombre es legal para el verbo y lo que no existe es la combinación—,
    // y con peor consecuencia, porque la bandera descartada expresa una escritura.
    //
    // `--config` **no** entra en esta exclusión, y la diferencia no es de grado:
    // que el descubrimiento lo ignore es una decisión tomada y verificada —
    // "discover no escribe nada: descubrir no es configurar"—, así que rechazarlo
    // rompería un uso legítimo. `--set-root` no tiene esa guarda porque nadie
    // decidió que se ignorara: simplemente se perdía.
    if (flags['set-root'] !== undefined) {
      throw new ContractError(
        'USAGE',
        '--discover y --set-root son excluyentes: el descubrimiento solo mira el disco, '
          + 'así que no declara ninguna raíz; para fijarla, corré `config --config <ruta> '
          + '--set-root <raíz>` con lo que el descubrimiento haya sugerido',
      );
    }
    return descubrir({ fs, flags, homeDir, label });
  }

  const configPath = flags.config;
  if (typeof configPath !== 'string' || configPath.length === 0) {
    throw new ContractError('USAGE', 'config exige --config con una ruta');
  }
  const resuelto = path.resolve(configPath);
  const previo = await leerSiExiste(fs, resuelto, `${label}.read`);

  if (flags['set-root'] === undefined) {
    if (previo === null) {
      throw new ConfigError('NO_VAULT', `el config ${resuelto} no existe`, { path: resuelto });
    }
    const declarado = readPathVault(previo);
    if (declarado === null) {
      throw new ConfigError('NO_VAULT', `el config ${resuelto} no declara path_vault`, { path: resuelto });
    }
    return { status: 'VAULT_CONFIGURED', configPath: resuelto, root: declarado };
  }

  // Se valida **antes** de escribir: dejar en el config una raíz que después no
  // resuelve convierte un error de tipeo en un fallo que aparece mucho más tarde
  // y lejos de su causa. `resolveVaultRoot` sólo resuelve la **forma** —expande
  // `~`, absolutiza—, así que durante un tiempo la promesa de este comentario no
  // se cumplía: una ruta mal tipeada se escribía sin chistar y reaparecía en el
  // `archive` siguiente como un `INTERNAL_ERROR` genérico, lejos de su causa
  // igual que si no se validara nada. `assertRootUsable` es lo que la cumple:
  // comprueba que exista, sea directorio, sea escribible y no sea el vault de
  // notas de otro.
  const root = resolveVaultRoot(flags['set-root'], homeDir, 'set-root');
  await assertRootUsable({ fs, root, label: `${label}.usable` });
  // `upsertPathVault` devuelve `{ text, changed }`: inserta o reemplaza **por
  // líneas**, para no reescribirle el formato al archivo de otro.
  const { text } = upsertPathVault(previo ?? '', flags['set-root']);
  await fs.mkdir(path.dirname(resuelto), `${label}.mkdir`, { recursive: true });
  await fs.writeFileAtomic(resuelto, Buffer.from(text, 'utf8'), `${label}.write`);
  return { status: 'VAULT_SET', configPath: resuelto, root };
}

/**
 * `config --discover`: qué vaults hay en el disco, clasificados.
 *
 * Existe porque `kv` no tiene registro global, y esa decisión —cada proyecto
 * apunta al suyo, sin archivo central— deja un hueco concreto en el primer uso:
 * `NO_VAULT` dice que falta declarar la raíz y no hay dónde averiguar cuál es.
 *
 * **Sale 0 siempre, incluso sin candidatos**, por la misma razón que el ensayo de
 * `retire`: un descubrimiento que falla por lo que encontró es un descubrimiento
 * que no se puede leer. Cero candidatos es un resultado legítimo —hay que crear
 * el vault— y no un error.
 *
 * **No escribe nada.** Quien elige es una persona, y persistir la elección es el
 * otro modo de este mismo verbo (`--set-root`).
 */
async function descubrir({ fs, flags, homeDir, label }) {
  const declarado = flags['search-root'];
  const raices = typeof declarado === 'string' && declarado.length > 0 ? [declarado] : homeDir === null ? [] : [homeDir];
  if (raices.length === 0) {
    throw new ContractError('USAGE', 'discover exige --search-root cuando no hay home resoluble');
  }

  const { candidatos } = await descubrirVaults({ fs, raices, label: `${label}.discover` });
  const vaults = candidatos.filter((c) => c.clase === CLASES.KV);
  const ajenos = candidatos.filter((c) => c.clase === CLASES.OBSIDIAN);
  const nuevos = candidatos.filter((c) => c.clase === CLASES.VACIO);

  // La sugerencia es del comando y no de quien lo lee, para que dos agentes no
  // elijan distinto sobre la misma evidencia: con un solo vault, ese; con varios,
  // ninguna, porque desempatar por número de flujos elegiría por tamaño una
  // pregunta que es de propósito.
  const sugerido = vaults.length === 1 ? vaults[0].root : null;

  return {
    status: 'VAULTS_DISCOVERED',
    buscadoEn: raices,
    sugerido,
    vaults,
    // Directorios con la forma de un vault nuevo: `.obsidian/` y ninguna nota.
    // **Se ofrecen**, y por eso viajan enteros y no como rutas planas: quien elige
    // necesita poder distinguirlos de un vault con conocimiento adentro, y ahí es
    // donde `evidencia: null` dice lo que hay que decir. Sin esta cubeta, el único
    // candidato que busca quien todavía no tiene vault era el único invisible.
    // La lista se emite siempre: vacía es un resultado, no una ausencia.
    nuevos,
    // Se informan **sin** sugerirlos: son la trampa que este verbo existe para no
    // pisar, y callarlos dejaría a quien busca preguntándose por qué su carpeta
    // de notas no aparece.
    ajenos: ajenos.map((c) => c.root),
  };
}
