/**
 * El verbo `retire`: retirar del origen lo que ya está a salvo.
 *
 * Es el único verbo de la skill que destruye, y su forma entera está gobernada
 * por esa asimetría. Copiar mal se repara borrando el vault y volviendo a copiar;
 * borrar mal no se repara. De ahí las tres cosas que lo separan de los otros
 * cuatro:
 *
 * 1. **El ensayo es de primera clase, no un modo de depuración.** `--dry-run`
 *    recorre el camino completo sin una sola escritura, clasifica cada entrada
 *    entre a salvo y sin copia, y emite el digest que una persona va a aprobar.
 *    Sale con código **cero siempre**, incluso al encontrar discrepancias: un
 *    ensayo que falla por lo que encontró es un ensayo que no se puede leer.
 * 2. **El retiro real exige el digest como argumento.** No lo recalcula para sí
 *    mismo —eso sería aprobarse solo—: lo recibe y lo compara contra lo que
 *    vuelve a escanear. La implementación floja de este verbo, la que hay que
 *    poder rechazar, es exactamente la que computa su propio digest al ejecutar.
 * 3. **Dos digests, con dos alcances distintos.** El del **lote** cubre el
 *    conjunto de flujos y las precondiciones globales: si cambió, no se toca
 *    nada, porque lo que se aprobó era otra cosa. El de **cada flujo** cubre su
 *    propio árbol: si cambió, falla ese flujo y el lote sigue. Un solo digest
 *    obligaría a elegir entre abortar todo por un archivo ajeno o no detectar un
 *    cambio de alcance.
 *
 * **El ejecutor llega inyectado y por defecto no existe.** Mientras el módulo de
 * destrucción no esté instalado, el camino real se detiene con una precondición
 * en vez de fingir que hizo algo. No es un placeholder: es lo que mantiene el
 * árbol sin ninguna llamada destructiva hasta que la haya de verdad.
 */

import path from 'node:path';

import {
  assertObjetivoDestructivo,
  discoverRepoRootFromDir,
  resolveVaultRootWithDefault,
} from '../config.mjs';
import { digestOf } from '../canonical.mjs';
import { ContractError } from '../contracts.mjs';
import {
  parseRegistroIdentidades,
  resolverIdentidadRepo,
} from '../identity.mjs';
import { construirManifiesto, digestManifiesto } from '../manifest.mjs';
import {
  ejecutarRetiro,
  esNombreDeRemanente,
  flowIdDeRemanente,
  rutaDelManifiesto,
  rutaDelRemanente,
  RESULTADOS,
} from '../retire-execute.mjs';
import { assertContainedPath } from '../portable-path.mjs';
import { estaASalvo } from '../safety-probe.mjs';
import { isCopiable } from '../selection.mjs';
import { scanInventory } from '../tree.mjs';
import { headDelVault, senalesDelRepositorio } from '../vault-git.mjs';
import { readIdentitiesFile } from '../vault-store.mjs';

/** Estados propios del verbo. Los códigos los fija la tabla del contrato. */
export const ESTADOS = Object.freeze({
  DRY_RUN: 'DRY_RUN',
  BATCH_OK: 'BATCH_OK',
  BATCH_PARTIAL: 'BATCH_PARTIAL',
  BATCH_FAILED: 'BATCH_FAILED',
});

/**
 * El ejecutor por defecto. Es inyectable para que los tests puedan observar el
 * lote sin destruir, no para que el verbo pueda correr sin ejecutor: quien no lo
 * pasa obtiene el real.
 */
export const EJECUTOR_POR_DEFECTO = ejecutarRetiro;

function exigir(flags, nombre) {
  const valor = flags[nombre];
  if (typeof valor !== 'string' || valor.length === 0) {
    throw new ContractError('USAGE', `retire exige --${nombre}`);
  }
  return valor;
}

/**
 * Hijos **directos** que son directorios. Los archivos sueltos no se procesan.
 *
 * Los **remanentes se saltean**, y no es un detalle de presentación: un remanente
 * es un reclamo en curso o una destrucción autorizada del flujo que lleva su
 * nombre. Enumerarlo como si fuera un flujo más lo trataría como material del
 * usuario y lo mandaría a la sonda con un `flowId` que empieza con el prefijo
 * reservado. Quien lo adopta es la secuencia del flujo al que pertenece.
 */
async function objetivosDe({ fs, raiz, label }) {
  const entradas = await fs.readDirNames(raiz, `${label}.readdir`);
  const directorios = [];
  const sueltos = [];
  const remanentes = [];
  for (const { name } of entradas) {
    const abs = path.join(raiz, name);
    const info = await fs.lstat(abs, `${label}.lstat`);
    if (esNombreDeRemanente(name)) { remanentes.push(abs); continue; }
    if (info !== null && info.isDirectory()) directorios.push(abs);
    else sueltos.push(abs);
  }
  // Un remanente cuyo flujo ya no está en su ruta sigue necesitando que alguien
  // lo adopte: es un reclamo sin autorizar o una destrucción a medio terminar, y
  // si no entra al lote queda ahí para siempre. Entra por el **flujo** al que
  // pertenece, no por su propia ruta.
  for (const abs of remanentes) {
    const objetivo = path.join(raiz, flowIdDeRemanente(path.basename(abs)));
    if (!directorios.includes(objetivo)) directorios.push(objetivo);
  }
  directorios.sort();
  sueltos.sort();
  remanentes.sort();
  return { directorios, sueltos, remanentes };
}

/**
 * El plan del lote: qué se retiraría, con qué autoridad, y bajo qué digest.
 *
 * **No escribe.** Es el mismo recorrido que hace el retiro real, y por eso el
 * ensayo dice la verdad: no es una simulación aparte que pueda divergir.
 */
export async function planificarRetiro({ fs, vaultRoot, repoId, raiz, objetivos, repoRoot, label = 'retire' }) {
  const vaultCommit = await headDelVault(vaultRoot);
  if (vaultCommit === null) {
    throw new ContractError('PRECONDITION_NOT_MET', `el vault no tiene ningún commit: ${vaultRoot}`);
  }

  const flujos = [];
  for (const objetivo of objetivos) {
    const flowId = path.basename(objetivo);
    const entrada = { flowId, flowDir: objetivo, aSalvo: false, causa: null, manifiesto: null, digest: null };
    // Las dos señales durables, observadas **antes** de intentar nada: un flujo
    // sin copia verificable pero con remanente no es "nada que hacer", es una
    // secuencia a medio camino que hay que terminar o deshacer.
    const infoRemanente = await fs.lstat(rutaDelRemanente(raiz, flowId), `${label}.remanente.lstat`);
    entrada.hayRemanente = infoRemanente !== null && infoRemanente.isDirectory();
    entrada.hayManifiesto =
      (await fs.lstat(rutaDelManifiesto(vaultRoot, repoId, flowId), `${label}.manifiesto.lstat`)) !== null;
    try {
      await assertObjetivoDestructivo({ objetivo, raizDeclarada: raiz, vaultRoot, repoRoot });
      const sonda = await estaASalvo({ fs, vaultRoot, repoId, flowId, flowDir: objetivo });
      entrada.aSalvo = sonda.aSalvo;
      entrada.causa = sonda.causa;
      entrada.faltantes = sonda.faltantes;

      // El manifiesto se construye igual cuando NO está a salvo: es lo que el
      // ensayo tiene que mostrar —cuántos bytes se perderían— y sin él el
      // informe diría "no se puede" sin decir de qué se está hablando. Lo que
      // cambia es la clasificación: sin copia verificada, nada queda `a-salvo`.
      entrada.manifiesto = await construirManifiesto({
        fs,
        flowDir: objetivo,
        aSalvo: sonda.aSalvo ? await rutasASalvo({ fs, flowDir: objetivo, label }) : [],
        identidad: { repoId, flowId },
        vaultCommit,
        label: `${label}.manifest`,
      });
      entrada.digest = digestManifiesto(entrada.manifiesto);
    } catch (error) {
      entrada.causa = error.code ?? 'ERROR';
      entrada.error = error.message;
    }
    flujos.push(entrada);
  }

  // El digest del **lote**: el alcance y las precondiciones globales. Va sobre
  // los digests por flujo y no sobre sus manifiestos enteros, así que agregar o
  // quitar un flujo lo mueve tanto como cambiar el contenido de uno.
  const digestAlcance = digestOf({
    repoId,
    raiz: path.basename(raiz),
    vaultCommit,
    flujos: flujos.map((f) => ({ flowId: f.flowId, digest: f.digest ?? '', aSalvo: f.aSalvo })),
  });

  return { flujos, digestAlcance, vaultCommit };
}

/** Las rutas copiables del flujo, que son las que el vault tiene a salvo. */
async function rutasASalvo({ fs, flowDir, label }) {
  const inventario = await scanInventory({ fs, root: flowDir, label: `${label}.copiables` });
  return inventario.files.filter((e) => isCopiable(e.path)).map((e) => e.path);
}

/**
 * El complemento exacto de lo que `archive` seleccionaría, leído del manifiesto
 * ya construido —no se reescanea el árbol—. `null` cuando la medición falló:
 * un conjunto vacío mentiría "no quedó nada afuera".
 */
function proyectarOmitidos(manifiesto) {
  if (manifiesto === null) return null;
  return manifiesto.inventario
    .filter((entrada) => !isCopiable(entrada.path))
    .map((entrada) => {
      assertContainedPath(entrada.path, 'omitidos');
      return { path: entrada.path, size: entrada.size, sha256: entrada.sha256 };
    });
}

export async function retireCommand({
  fs,
  flags,
  homeDir = null,
  label = 'retire',
  ejecutor = EJECUTOR_POR_DEFECTO,
}) {
  // Ensayar y retirar en la **misma** invocación es la forma exacta que tiene un
  // guion de eliminar el gate: corre el ensayo, se copia el digest y lo pasa. Se
  // rechaza acá, mecánicamente, en vez de pedírselo a quien escriba el guion.
  if (flags['dry-run'] === true && flags['approve-digest'] !== undefined) {
    throw new ContractError(
      'USAGE',
      '--dry-run y --approve-digest son excluyentes: el ensayo se presenta a una persona y el retiro real es un acto separado',
    );
  }
  const raiz = path.resolve(exigir(flags, 'root'));
  const repoRoot = await discoverRepoRootFromDir({ fs, dir: raiz, label: `${label}.repo` });
  const { root: vaultRoot } = await resolveVaultRootWithDefault({
    fs,
    configPath: flags.config ?? null,
    vaultRoot: flags['vault-root'] ?? null,
    repoRoot,
    homeDir,
    label: `${label}.config`,
  });

  // La identidad **declarada**, no la derivada del nombre del directorio. Una
  // resolución ambigua detiene: es la única señal de que dos repositorios
  // distintos comparten sitio en el vault.
  const registro = parseRegistroIdentidades(await readIdentitiesFile({ fs, vaultRoot, label: `${label}.ident` }));
  const { repoId } = resolverIdentidadRepo({
    registro,
    senales: await senalesDelRepositorio(repoRoot),
  });

  const { directorios, sueltos } = await objetivosDe({ fs, raiz, label });
  const objetivos = flags.from === undefined
    ? directorios
    : [path.resolve(flags.from)];

  const plan = await planificarRetiro({ fs, vaultRoot, repoId, raiz, objetivos, repoRoot, label });
  // El modo dirigido —ensayo **y** `--from` a la vez— es el único que expone
  // `omitidos`: el lote agregado y el retiro real no lo llevan.
  const modoDirigido = flags['dry-run'] === true && flags.from !== undefined;
  // Los sueltos no se procesan y se **nombran**: decir que la raíz quedó vacía
  // cuando no lo está es peor que no decir nada.
  const informe = {
    repoId,
    raiz,
    vaultRoot,
    vaultCommit: plan.vaultCommit,
    digest: plan.digestAlcance,
    flujos: plan.flujos.map(({ manifiesto, ...resto }) => {
      const entrada = { ...resto, bytes: manifiesto?.bytes ?? null };
      return modoDirigido ? { ...entrada, omitidos: proyectarOmitidos(manifiesto) } : entrada;
    }),
    remanentesNoProcesados: sueltos,
  };

  if (flags['dry-run'] === true) {
    // Cero **siempre**: el ensayo informa, no juzga.
    return { status: ESTADOS.DRY_RUN, informe };
  }

  const aprobado = flags['approve-digest'];
  if (typeof aprobado !== 'string' || aprobado.length === 0) {
    throw new ContractError(
      'USAGE',
      'retire sin --dry-run exige --approve-digest: el digest lo aprueba una persona sobre un ensayo, no el propio comando',
    );
  }
  if (aprobado !== plan.digestAlcance) {
    // El lote entero, antes de tocar nada: lo que se aprobó era otro alcance.
    throw new ContractError(
      'PRECONDITION_NOT_MET',
      `el digest aprobado no describe este lote: aprobado ${aprobado}, medido ${plan.digestAlcance}`,
      { detail: { aprobado, medido: plan.digestAlcance } },
    );
  }

  // La contención en runtime, declarada **acá**: quien construye el `DurableFs`
  // —el CLI— no sabe sobre qué se va a destruir hasta que el verbo resuelve la
  // config y la matriz de rutas. Sin esta línea el mecanismo existe y no protege
  // nada, que es la peor de las dos formas de no tenerlo.
  //
  // **Dos raíces, no una.** La de archivados es la obvia; el vault entra porque
  // la publicación atómica del manifiesto renombra su temporal sobre el destino,
  // y `rename` es una primitiva destructiva —el origen del renombrado
  // desaparece—. Declarar sólo la de archivados haría fallar el propio
  // manifiesto, y la salida barata —sacar `rename` de la contención— dejaría sin
  // cubrir justamente el reclamo, que es un renombrado sobre el origen.
  if (typeof fs.declararRaicesDestructivas === 'function') {
    fs.declararRaicesDestructivas([raiz, vaultRoot]);
  }

  const resultados = [];
  for (const flujo of plan.flujos) {
    // No está a salvo y **tampoco** hay secuencia a medio camino: no hay nada
    // que ejecutar, y reclamarlo para verificar lo que ya sabemos que falla
    // sería renombrar el origen de un flujo que no se va a retirar.
    if (!flujo.aSalvo && !flujo.hayRemanente && !flujo.hayManifiesto) {
      resultados.push({ flowId: flujo.flowId, estado: 'FALLO', causa: flujo.causa });
      continue;
    }
    try {
      resultados.push(await ejecutor({ fs, vaultRoot, repoId, raiz, flujo, label }));
    } catch (error) {
      // Un fallo individual no se lleva puesto el lote: la verificación por
      // flujo continúa con los demás. Lo que sí falla cerrado son las
      // precondiciones **globales**, y esas ya se comprobaron arriba.
      resultados.push({ flowId: flujo.flowId, estado: 'FALLO', causa: error.code ?? 'ERROR', error: error.message });
    }
  }

  return { status: estadoDelLote(resultados), informe: { ...informe, resultados } };
}

/**
 * Los tres estados del lote.
 *
 * `BATCH_OK` incluye el **lote vacío** y el lote cuyos objetivos ya estaban todos
 * retirados: ninguno de los dos es un fallo, son ausencia de trabajo. Tratarlos
 * como error haría que un cierre idempotente saliera distinto de cero cada vez
 * que no queda nada por hacer.
 */
export function estadoDelLote(resultados) {
  const fallidos = resultados.filter((r) => r.estado === 'FALLO').length;
  const retirados = resultados.filter((r) => r.estado === RESULTADOS.RETIRADO).length;
  if (fallidos === 0) return ESTADOS.BATCH_OK;
  return retirados > 0 ? ESTADOS.BATCH_PARTIAL : ESTADOS.BATCH_FAILED;
}
