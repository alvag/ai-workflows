// Capa base de plataforma para el transporte cross-model vía Orca.
// Resuelve rutas de configuración por familia (Codex/Claude) y valida la versión
// de Node en la que corre el resto de los módulos (harvest-core, dispatch-adapter, etc.).
import os from 'node:os';
import path from 'node:path';

/**
 * Directorio de configuración/datos de la familia indicada.
 * Respeta las variables de entorno cuando están seteadas: bajo Orca, por ejemplo,
 * CODEX_HOME apunta al runtime de Orca (no a ~/.codex), y hay que preferirla siempre.
 * @param {'codex'|'claude'} family
 * @returns {string} ruta absoluta al directorio de config/datos de la familia.
 */
export function configDir(family) {
  if (family === 'codex') {
    return process.env.CODEX_HOME
      ? path.resolve(process.env.CODEX_HOME)
      : path.join(os.homedir(), '.codex');
  }
  if (family === 'claude') {
    return process.env.CLAUDE_CONFIG_DIR
      ? path.resolve(process.env.CLAUDE_CONFIG_DIR)
      : path.join(os.homedir(), '.claude');
  }
  throw new Error(`Familia desconocida: "${family}". Los valores válidos son "codex" o "claude".`);
}

/** @returns {boolean} true si el proceso corre en Windows. */
export function isWindows() {
  return process.platform === 'win32';
}

/**
 * Verifica que la major de Node actual cumpla el mínimo requerido.
 * @param {number} minMajor major mínima requerida (p. ej. 18).
 * @throws {Error} si la major actual de Node es menor a `minMajor`.
 */
export function assertNode(minMajor) {
  const currentMajor = Number.parseInt(process.versions.node, 10);
  if (currentMajor < minMajor) {
    throw new Error(
      `Se requiere Node >= ${minMajor}. Versión actual: ${process.versions.node}. ` +
        'Actualiza Node antes de continuar (ver install.md).'
    );
  }
}

/**
 * Resuelve la raíz de instalación del transporte cross-model-orca a partir de la
 * variable de entorno CROSS_MODEL_ORCA.
 * @returns {string} el valor de CROSS_MODEL_ORCA.
 * @throws {Error} si la variable no está seteada.
 */
export function resolveInstallRoot() {
  const root = process.env.CROSS_MODEL_ORCA;
  if (!root) {
    throw new Error(
      'CROSS_MODEL_ORCA no está seteada. Exporta la variable apuntando a la ruta absoluta de ' +
        'skills/cross-model-orca/assets (ver install.md).'
    );
  }
  return root;
}
