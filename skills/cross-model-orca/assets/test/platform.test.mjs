// Tests de platform.mjs: rutas de configuración por familia, preflight de Node y
// resolución del install root. Cada test que toca variables de entorno las restaura
// en un `finally` para no filtrar estado a los tests siguientes.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import os from 'node:os';
import { configDir, isWindows, assertNode, resolveInstallRoot } from '../lib/platform.mjs';

test('configDir("codex") sin CODEX_HOME devuelve ruta absoluta terminada en .codex', () => {
  const original = process.env.CODEX_HOME;
  delete process.env.CODEX_HOME;
  try {
    const dir = configDir('codex');
    assert.equal(path.isAbsolute(dir), true);
    assert.equal(dir, path.join(os.homedir(), '.codex'));
  } finally {
    if (original === undefined) delete process.env.CODEX_HOME;
    else process.env.CODEX_HOME = original;
  }
});

test('configDir("codex") respeta CODEX_HOME cuando está seteada (caso Orca)', () => {
  const original = process.env.CODEX_HOME;
  const orcaRuntimeHome = path.join(os.homedir(), 'Library/Application Support/orca/codex-runtime-home/home');
  process.env.CODEX_HOME = orcaRuntimeHome;
  try {
    const dir = configDir('codex');
    assert.equal(dir, orcaRuntimeHome);
  } finally {
    if (original === undefined) delete process.env.CODEX_HOME;
    else process.env.CODEX_HOME = original;
  }
});

test('configDir("claude") sin CLAUDE_CONFIG_DIR devuelve ruta absoluta terminada en .claude', () => {
  const original = process.env.CLAUDE_CONFIG_DIR;
  delete process.env.CLAUDE_CONFIG_DIR;
  try {
    const dir = configDir('claude');
    assert.equal(path.isAbsolute(dir), true);
    assert.equal(dir, path.join(os.homedir(), '.claude'));
  } finally {
    if (original === undefined) delete process.env.CLAUDE_CONFIG_DIR;
    else process.env.CLAUDE_CONFIG_DIR = original;
  }
});

test('configDir("claude") respeta CLAUDE_CONFIG_DIR cuando está seteada', () => {
  const original = process.env.CLAUDE_CONFIG_DIR;
  const customDir = '/tmp/custom-claude-config';
  process.env.CLAUDE_CONFIG_DIR = customDir;
  try {
    const dir = configDir('claude');
    assert.equal(dir, customDir);
  } finally {
    if (original === undefined) delete process.env.CLAUDE_CONFIG_DIR;
    else process.env.CLAUDE_CONFIG_DIR = original;
  }
});

test('configDir con familia desconocida lanza Error', () => {
  assert.throws(() => configDir('gpt'), /Error/);
});

test('isWindows refleja process.platform', () => {
  assert.equal(isWindows(), process.platform === 'win32');
});

test('assertNode no lanza cuando la major actual cumple el mínimo', () => {
  const currentMajor = Number(process.versions.node.split('.')[0]);
  assert.doesNotThrow(() => assertNode(currentMajor));
  assert.doesNotThrow(() => assertNode(1));
});

test('assertNode lanza Error con un mínimo imposible', () => {
  assert.throws(() => assertNode(999), /Node/);
});

test('resolveInstallRoot lanza si CROSS_MODEL_ORCA no está seteada', () => {
  const original = process.env.CROSS_MODEL_ORCA;
  delete process.env.CROSS_MODEL_ORCA;
  try {
    assert.throws(() => resolveInstallRoot(), /CROSS_MODEL_ORCA/);
  } finally {
    if (original === undefined) delete process.env.CROSS_MODEL_ORCA;
    else process.env.CROSS_MODEL_ORCA = original;
  }
});

test('resolveInstallRoot devuelve CROSS_MODEL_ORCA cuando está seteada', () => {
  const original = process.env.CROSS_MODEL_ORCA;
  const customRoot = '/tmp/cross-model-orca-assets';
  process.env.CROSS_MODEL_ORCA = customRoot;
  try {
    assert.equal(resolveInstallRoot(), customRoot);
  } finally {
    if (original === undefined) delete process.env.CROSS_MODEL_ORCA;
    else process.env.CROSS_MODEL_ORCA = original;
  }
});
