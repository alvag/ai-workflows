#!/usr/bin/env node
/**
 * El ejecutable. **Sin lógica**: cablea el filesystem durable, el home y `argv`,
 * corre el verbo y traduce el resultado a salida y código de salida.
 *
 * Todo lo que decida algo vive en `lib/`, para que se pueda probar sin lanzar un
 * proceso.
 */

import { homedir } from 'node:os';

import { runCli } from './lib/cli.mjs';
import { archiveCommand } from './lib/commands/archive.mjs';
import { configCommand } from './lib/commands/config.mjs';
import { indexCommand } from './lib/commands/index.mjs';
import { migrateCommand } from './lib/commands/migrate.mjs';
import { retireCommand } from './lib/commands/retire.mjs';
import { DurableFs } from './lib/durable-fs.mjs';

const comandos = {
  archive: archiveCommand,
  migrate: migrateCommand,
  index: indexCommand,
  config: configCommand,
  retire: retireCommand,
};

const resultado = await runCli({
  argv: process.argv.slice(2),
  comandos,
  fs: new DurableFs(),
  cwd: process.cwd(),
  homeDir: homedir(),
});

process.stdout.write(`${JSON.stringify(resultado, null, 2)}\n`);
process.exit(resultado.exitCode);
