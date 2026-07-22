// ENTRYPOINT CLI (guardless) del validador declarativo. Solo lee y valida;
// nunca ejecuta los comandos u observaciones contenidos en el contrato.
import fs from 'node:fs';
import {
  MAX_CONTRACT_BYTES,
  validateContract,
} from './verification-contract.mjs';

function readContract(filePath) {
  let stat;
  try {
    stat = fs.statSync(filePath);
  } catch (err) {
    throw new Error(`no se pudo acceder al contrato "${filePath}": ${err.message}`);
  }
  if (!stat.isFile()) throw new Error(`el contrato no es un archivo: ${filePath}.`);
  if (stat.size > MAX_CONTRACT_BYTES) throw new Error('el contrato excede el máximo de 1 MiB.');
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new Error(`no se pudo leer el contrato "${filePath}": ${err.message}`);
  }
}

function main() {
  const [command, filePath, ...extra] = process.argv.slice(2);
  if (command !== 'validate') {
    throw new Error(`operación desconocida: ${String(command)}; se esperaba validate.`);
  }
  if (!filePath) throw new Error('falta la ruta del contrato para validate.');
  if (extra.length > 0) throw new Error(`argumentos inesperados: ${extra.join(', ')}.`);
  const result = validateContract(readContract(filePath));
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

// Guardless a propósito: este módulo es solo entrypoint y nunca se importa.
try {
  main();
} catch (err) {
  process.stderr.write(`error: ${err && err.message}\n`);
  process.exitCode = 2;
}
