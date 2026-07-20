// Capa base de plataforma para el transporte cross-model vía Orca.
// Resuelve rutas de configuración por familia (Codex/Claude) y valida la versión
// de Node en la que corre el resto de los módulos (harvest-core, dispatch-adapter, etc.).
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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
 * Resuelve la raíz de instalación del transporte cross-model-orca (el directorio `assets`).
 * Por defecto se autolocaliza a partir de la propia ruta de este módulo (`platform.mjs` vive en
 * `<assets>/lib/`, así que `<assets>` es la carpeta abuela del archivo) — no depende de que nadie
 * setee una variable de entorno. La variable CROSS_MODEL_ORCA sigue soportada como **override
 * opcional**: si está seteada, se respeta tal cual (caso de correr los módulos desde una copia
 * distinta de su propio `assets`, ver install.md).
 * @returns {string} ruta absoluta a la raíz de instalación (`assets`).
 */
export function resolveInstallRoot() {
  const override = process.env.CROSS_MODEL_ORCA;
  if (override) {
    return override;
  }
  return path.dirname(path.dirname(fileURLToPath(import.meta.url)));
}
