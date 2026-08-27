/**
 * Traduce `argv` a una llamada, y un error a un código de salida. Nada más.
 *
 * Los comandos se **inyectan**, así que el ruteo se puede probar sin tocar disco
 * ni git: lo que hay que verificar acá es qué invocación es válida y con qué
 * código sale cada fallo, no lo que hace cada verbo.
 */

import { ContractError, FLAGS_BY_VERB, VERBS, exitCodeFor, isStatus } from './contracts.mjs';

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
    // La fila del verbo es la **única** autoridad sobre qué banderas existen y de
    // qué forma. Aceptar cualquier nombre —que es lo que se hacía— vuelve el
    // reintento imposible indistinguible del correcto: la bandera se parsea, se
    // guarda y se descarta sin que nada avise.
    //
    // `Object.hasOwn` y no `nombre in fila` ni un acceso directo: aunque las filas
    // nacen sin prototipo, la pertenencia explícita es lo que impide que una
    // edición futura de `contracts.mjs` reabra el agujero de `--constructor`.
    if (!Object.hasOwn(FLAGS_BY_VERB[verb], nombre)) {
      // La fila es la lista completa de lo aceptado, así que nombrarla cuesta una
      // expresión y evita que un typo o una bandera movida de verbo terminen en
      // prueba y error. Es el mismo criterio que este PR aplica al renombre: un
      // error que dice qué no se puede sin decir qué sí, obliga a adivinar.
      const acepta = Object.keys(FLAGS_BY_VERB[verb]).map((f) => `--${f}`).join(', ');
      throw new ContractError(
        'USAGE',
        `el verbo ${verb} no acepta la bandera --${nombre}; acepta ${acepta || '(ninguna)'}`,
      );
    }
    // Repetir una bandera pisaba el valor anterior sin avisar, que es la misma
    // clase de descarte silencioso que la tabla cierra un renglón más arriba: con
    // `--from a --from b` se archivaba `b` y nada decía que se habían dado dos.
    // Ahora que la fila conoce cada nombre, detectarlo es una comparación.
    if (Object.hasOwn(flags, nombre)) {
      throw new ContractError('USAGE', `la bandera --${nombre} está repetida: se declara una sola vez`);
    }
    if (FLAGS_BY_VERB[verb][nombre] === 'booleana') {
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
