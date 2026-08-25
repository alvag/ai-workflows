/**
 * Traduce `argv` a una llamada, y un error a un código de salida. Nada más.
 *
 * Los comandos se **inyectan**, así que el ruteo se puede probar sin tocar disco
 * ni git: lo que hay que verificar acá es qué invocación es válida y con qué
 * código sale cada fallo, no lo que hace cada verbo.
 */

import { ContractError, VERBS, exitCodeFor, isStatus } from './contracts.mjs';

/** Banderas sin valor: no se comen el argumento siguiente. */
const BOOLEANAS = new Set(['dry-run', 'propose']);

/**
 * @returns {{verb: string, flags: Record<string, string|true>}}
 */
export function parseArgv(argv) {
  const [verb, ...resto] = argv;
  if (verb === undefined || !VERBS.includes(verb)) {
    throw new ContractError(
      'USAGE',
      `verbo ${verb === undefined ? 'ausente' : JSON.stringify(verb)}; los verbos son ${VERBS.join(', ')}`,
    );
  }

  const flags = {};
  for (let i = 0; i < resto.length; i += 1) {
    const token = resto[i];
    if (!token.startsWith('--')) {
      throw new ContractError('USAGE', `argumento suelto ${JSON.stringify(token)}: todo entra por banderas largas`);
    }
    const nombre = token.slice(2);
    if (BOOLEANAS.has(nombre)) {
      flags[nombre] = true;
      continue;
    }
    const valor = resto[i + 1];
    if (valor === undefined || valor.startsWith('--')) {
      throw new ContractError('USAGE', `la bandera --${nombre} espera un valor`);
    }
    flags[nombre] = valor;
    i += 1;
  }
  return { verb, flags };
}

/**
 * Corre el verbo y devuelve su estado con el código de salida ya resuelto.
 *
 * Un error que trae un `code` de la tabla sale con **su** código; uno que no,
 * sale `INTERNAL_ERROR`. Traducir un error desconocido a un estado del contrato
 * sería peor que no traducirlo: le daría a quien automatiza una razón concreta
 * y falsa.
 */
export async function runCli({ argv, comandos, ...contexto }) {
  try {
    const { verb, flags } = parseArgv(argv);
    if (flags.config !== undefined && flags['vault-root'] !== undefined) {
      throw new ContractError(
        'USAGE',
        '--config y --vault-root son excluyentes: la raíz del vault se declara de una sola forma',
      );
    }
    const comando = comandos[verb];
    if (comando === undefined) {
      throw new ContractError('INTERNAL_ERROR', `el verbo ${verb} no tiene comando cableado`);
    }
    const resultado = await comando({ ...contexto, flags });
    return { ...resultado, exitCode: exitCodeFor(resultado.status) };
  } catch (error) {
    const status = isStatus(error?.code) ? error.code : 'INTERNAL_ERROR';
    return { status, exitCode: exitCodeFor(status), message: error?.message ?? String(error) };
  }
}
