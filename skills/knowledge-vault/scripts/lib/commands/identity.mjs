/**
 * El verbo `identity`: declarar de qué repositorio se está hablando.
 *
 * La ruta dentro del vault sale de un identificador del repositorio, y **no se
 * deriva**: se declara. Derivarlo del nombre del directorio parecía suficiente
 * con un solo repositorio, y el propio módulo de identidad ya advertía que ese
 * nombre no es identidad. Con N repositorios en N máquinas deja de serlo del
 * todo: dos clones que se llamen `api` en dos computadoras comparten sitio en el
 * vault, y un retiro decidiría sobre el flujo equivocado.
 *
 * ## Las dos banderas son un gate, no dos modos
 *
 * `--propose` mira las señales del repositorio y **propone** un identificador,
 * sin escribir nada. `--declare <id>` escribe el que le pasen. Son
 * **excluyentes** a propósito, y es la misma forma que tiene el retiro con
 * `--dry-run` y `--approve-digest`: entre las dos hay una persona que lee la
 * propuesta y **tipea** el identificador. Un solo comando que propusiera y
 * declarara de una eliminaría esa confirmación sin que ninguna bandera lo
 * delatara.
 *
 * ## Por qué el vault y no la configuración del proyecto
 *
 * Porque la configuración es **local** y no viaja entre clones: el mismo
 * repositorio tendría otra identidad en cada máquina, que es exactamente el
 * problema que esto viene a resolver. El registro vive versionado en el vault,
 * junto a las señales que respaldan cada entrada.
 */

import { ContractError } from '../contracts.mjs';
import path from 'node:path';

import {
  deriveStem,
  normalizarRemoto,
  parseRegistroIdentidades,
  proponerIdentidadRepo,
  serializarRegistroIdentidades,
} from '../identity.mjs';
import { discoverRepoRootFromDir, resolveVaultRootWithDefault } from '../config.mjs';
import { commitFlow, ensureVaultRepo, senalesDelRepositorio } from '../vault-git.mjs';
import {
  PROJECTS_DIRNAME,
  readIdentitiesFile,
  resolveIdentitiesPath,
  writeIdentitiesFile,
} from '../vault-store.mjs';

export const ESTADOS = Object.freeze({
  PROPUESTA: 'IDENTITY_PROPOSED',
  DECLARADA: 'IDENTITY_DECLARED',
  YA_DECLARADA: 'IDENTITY_ALREADY_DECLARED',
});

/** Las señales por las que dos entradas son el mismo repositorio. */
const mismoRepo = (entrada, senales) =>
  (senales.commitRaiz !== null && entrada.commitRaiz === senales.commitRaiz) ||
  (senales.remoto !== null && normalizarRemoto(entrada.remoto) === normalizarRemoto(senales.remoto));

export async function identityCommand({ fs, flags, cwd = process.cwd(), homeDir = null, label = 'identity' }) {
  const proponer = flags.propose === true;
  const declarado = flags.declare;

  if (proponer && declarado !== undefined) {
    throw new ContractError(
      'USAGE',
      '--propose y --declare son excluyentes: entre la propuesta y la declaración va una persona',
    );
  }
  if (!proponer && (typeof declarado !== 'string' || declarado.length === 0)) {
    throw new ContractError('USAGE', 'identity exige --propose o --declare <id>');
  }

  const repoRoot = await discoverRepoRootFromDir({ fs, dir: cwd, label: `${label}.repo` });
  const senales = await senalesDelRepositorio(repoRoot);
  if (senales.remoto === null && senales.commitRaiz === null) {
    throw new ContractError(
      'AMBIGUOUS_IDENTITY',
      `${repoRoot} no tiene remoto ni ningún commit: sin una señal observable no se puede declarar ` +
        'de qué repositorio se habla, y el nombre del directorio no es una señal',
    );
  }

  if (proponer) {
    // No toca el vault: proponer es leer el repositorio y nada más.
    const propuesta = proponerIdentidadRepo(senales);
    return { status: ESTADOS.PROPUESTA, propuesta: propuesta.repoId, origen: propuesta.origen, senales };
  }

  const { root: vaultRoot } = await resolveVaultRootWithDefault({
    fs,
    configPath: flags.config ?? null,
    vaultRoot: flags['vault-root'] ?? null,
    repoRoot,
    homeDir,
    label: `${label}.config`,
  });

  // Antes de escribir un byte: el registro tiene que quedar **versionado**, y un
  // vault que todavía no es repositorio deja la escritura hecha y el commit sin
  // hacer. Medido: sin esto, la primera declaración sobre un vault nuevo escribe
  // el TSV, falla al commitear y devuelve un error que no dice que ya escribió.
  await ensureVaultRepo(vaultRoot);

  const registro = parseRegistroIdentidades(await readIdentitiesFile({ fs, vaultRoot, label: `${label}.read` }));
  const compatibles = registro.filter((e) => mismoRepo(e, senales));
  const ids = [...new Set(compatibles.map((e) => e.repoId))];

  // Ya declarado con **este** identificador: es un no-op, no un error. Declarar
  // dos veces tiene que poder correrse sin pensar.
  if (ids.length === 1 && ids[0] === declarado) {
    return { status: ESTADOS.YA_DECLARADA, repoId: declarado, vaultRoot };
  }
  // Ya declarado con **otro**: eso no se resuelve escribiendo encima. Un mismo
  // repositorio con dos identidades es la ambigüedad que el diseño prohíbe, y
  // adivinar cuál vale sería decidir sobre qué flujos se pueden destruir.
  if (ids.length > 0) {
    throw new ContractError(
      'AMBIGUOUS_IDENTITY',
      `este repositorio ya está declarado como ${ids.join(', ')}: declarar ${JSON.stringify(declarado)} ` +
        'lo dejaría con dos identidades. Corregí el registro a mano si el cambio es deliberado',
      { detail: { declarado, existentes: ids } },
    );
  }
  // El identificador ya lo usa **otro** repositorio: compartirían sitio en el
  // vault, que es el problema entero.
  const ajeno = registro.find((e) => e.repoId === declarado);
  if (ajeno !== undefined) {
    throw new ContractError(
      'AMBIGUOUS_IDENTITY',
      `${JSON.stringify(declarado)} ya identifica a otro repositorio (${ajeno.remoto || ajeno.rutaObservada}): ` +
        'dos repositorios con el mismo identificador comparten ruta dentro del vault',
      { detail: { declarado, ajeno } },
    );
  }

  // Declarar un identificador distinto del derivado **huerfana** lo que ya está
  // archivado: `archive` escribió bajo el derivado y desde acá en adelante todo
  // —copiar y retirar— usaría el declarado. Los flujos viejos quedarían en una
  // ruta que ningún verbo vuelve a mirar, y `retire` los reportaría a todos como
  // no-a-salvo sin decir por qué.
  const derivado = deriveStem(path.basename(repoRoot));
  if (declarado !== derivado) {
    const yaArchivado = path.join(vaultRoot, PROJECTS_DIRNAME, derivado);
    if ((await fs.lstat(yaArchivado, `${label}.derivado.lstat`)) !== null) {
      throw new ContractError(
        'AMBIGUOUS_IDENTITY',
        `el vault ya tiene material bajo ${JSON.stringify(derivado)}, que es el identificador que ` +
          `se venía derivando de este repositorio. Declarar ${JSON.stringify(declarado)} lo dejaría ` +
          `en una ruta que ningún verbo vuelve a mirar. Declará ${JSON.stringify(derivado)}, o mové ` +
          'ese directorio a mano antes de cambiar de identificador',
        { path: yaArchivado, detail: { declarado, derivado } },
      );
    }
  }

  const entrada = {
    repoId: declarado,
    remoto: senales.remoto ?? '',
    commitRaiz: senales.commitRaiz ?? '',
    rutaObservada: senales.rutaObservada,
  };
  await writeIdentitiesFile({
    fs, vaultRoot, texto: serializarRegistroIdentidades([...registro, entrada]), label: `${label}.write`,
  });

  // Versionado, como el resto del vault: el registro tiene que viajar entre
  // clones, y un archivo sin commitear no viaja.
  const { committed } = await commitFlow({
    vaultRoot,
    flowId: declarado,
    paths: [resolveIdentitiesPath(vaultRoot).slice(vaultRoot.length + 1)],
    subject: `declara la identidad de ${declarado}`,
  });
  if (!committed) {
    throw new ContractError(
      'PRECONDITION_NOT_MET',
      `el registro de identidades no produjo commit: ${declarado} quedaría declarado sólo en esta máquina`,
    );
  }
  return { status: ESTADOS.DECLARADA, repoId: declarado, vaultRoot, senales };
}
