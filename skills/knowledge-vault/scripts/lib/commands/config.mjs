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
import { ConfigError, resolveVaultRoot } from '../config.mjs';
import { ContractError } from '../contracts.mjs';

async function leerSiExiste(fs, ruta, label) {
  try {
    return (await fs.readFile(ruta, label)).toString('utf8');
  } catch (error) {
    if (error?.code === 'ENOENT' || error?.cause?.code === 'ENOENT') return null;
    throw error;
  }
}

export async function configCommand({ fs, flags, homeDir = null, label = 'config' }) {
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
  // y lejos de su causa.
  const root = resolveVaultRoot(flags['set-root'], homeDir, 'set-root');
  // `upsertPathVault` devuelve `{ text, changed }`: inserta o reemplaza **por
  // líneas**, para no reescribirle el formato al archivo de otro.
  const { text } = upsertPathVault(previo ?? '', flags['set-root']);
  await fs.mkdir(path.dirname(resuelto), `${label}.mkdir`, { recursive: true });
  await fs.writeFileAtomic(resuelto, Buffer.from(text, 'utf8'), `${label}.write`);
  return { status: 'VAULT_SET', configPath: resuelto, root };
}
