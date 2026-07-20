# Checkpoint Windows — transporte `cross-model-orca`

> **Para el agente que corra esto en Windows (Claude Code o Codex):** este es un runbook
> ejecutable. Corre cada prueba en **PowerShell**, anota el resultado real (no el esperado) en la
> sección **"Resultados (Windows)"** del final, y al terminar actualiza el checkpoint de Windows en
> `skills/cross-model-orca/spikes/RESULTS.md` → sección "Fase 7 — validación y checkpoints" (de
> `[ ]` a `[x]` si todo pasa, o `[~]` parcial con lo que falló).

## Por qué este checkpoint

El artefacto Node del conductor y los perfiles de lanzamiento se desarrollaron y verificaron en
**macOS**. Windows tiene dos diferencias que **no se pudieron verificar** allá y son el objetivo real
de esta corrida:

1. **Rutas por plataforma** (`platform.mjs`): `%USERPROFILE%`, `CODEX_HOME`, `CLAUDE_CONFIG_DIR`,
   separadores `\`.
2. **Slug del transcript de Claude** en Windows: el locator arma
   `<CLAUDE_CONFIG_DIR>\projects\<slug>\<session-id>.jsonl`, donde `<slug>` = el `cwd` con **todo
   carácter no alfanumérico → `-`** (`slugifyCwd` en `assets/dispatch-adapter.mjs`). En Windows el
   `cwd` trae `C:\Users\...` (backslashes, dos puntos, letra de unidad). Hay que confirmar que ese
   slug **coincide con el nombre real** del directorio que Claude Code crea bajo `projects\`. En
   Fase 1 un slug mal computado fue un bug real (S1); en Windows el riesgo se repite con otra forma
   de path.

Lo demás (tests puros, comandos PowerShell) es confirmación de portabilidad.

## Prerrequisitos

- **Node ≥ 18** (`node --version`). Obligatorio para el artefacto.
- El repo clonado en la rama `feat/cross-model-real-sessions`, parado en la **raíz del repo**.
- **Opcional** (solo para las pruebas 3 y 6, que lanzan CLIs reales): Claude Code CLI y/o Codex CLI
  instalados. Sin ellos, esas dos pruebas se marcan **N/A** (no bloquean el checkpoint del artefacto).

---

## Prueba 1 — Suite de tests (obligatoria)

Ejercita `platform.mjs` (rutas por plataforma, `isWindows()`), `harvest-core.mjs`,
`harvest-from-transcript.mjs`, `dispatch-adapter.mjs` (con un `orcaRunner` falso) y el test de
parser >1 MB. En macOS: **82 pass, 0 fail**.

```powershell
node --version
# Node hace la expansión del glob; comillas para que PowerShell no lo toque:
node --test "skills/cross-model-orca/assets/test/*.test.mjs"
```

- **Esperado:** `tests 82` / `pass 82` / `fail 0`, salida limpia.
- Si PowerShell/Node no expanden el glob, pasa los archivos explícitos:
  ```powershell
  node --test (Get-ChildItem skills/cross-model-orca/assets/test/*.test.mjs | ForEach-Object FullName)
  ```
- **Ojo:** `node --test <directorio>` a secas **falla** en Node 24 (trata el dir como módulo). No es
  un test roto — usa el glob de archivos.

## Prueba 2 — Rutas de `platform.mjs` en Windows (incluye autolocalización)

**Asegúrate de que `CROSS_MODEL_ORCA` NO esté seteada** para esta prueba (así se ejercita la
autolocalización, que es el camino por defecto): `Remove-Item Env:\CROSS_MODEL_ORCA -ErrorAction SilentlyContinue`.

```powershell
Remove-Item Env:\CROSS_MODEL_ORCA -ErrorAction SilentlyContinue
node -e "import('./skills/cross-model-orca/assets/lib/platform.mjs').then(m => { console.log('isWindows =', m.isWindows()); console.log('codex   =', m.configDir('codex')); console.log('claude  =', m.configDir('claude')); console.log('install =', m.resolveInstallRoot()); })"
```

- **Esperado:** `isWindows = true`; `codex`/`claude` resuelven a rutas **con backslashes** bajo
  `%USERPROFILE%` (p. ej. `C:\Users\<vos>\.codex` y `C:\Users\<vos>\.claude`), **salvo** que
  `CODEX_HOME`/`CLAUDE_CONFIG_DIR` estén seteadas, en cuyo caso mandan esas.
- **`install` (autolocalización — la verificación Windows clave):** sin la var, `resolveInstallRoot()`
  debe devolver una ruta **válida de Windows** que termina en `...\cross-model-orca\assets` (con
  backslashes, con la letra de unidad `C:\...` bien formada). Es el camino `import.meta.url` →
  `fileURLToPath`; en Windows el módulo se sirve como `file:///C:/...`, y `fileURLToPath` lo traduce
  a `C:\...`. **Si sale malformado** (p. ej. con `/` en vez de `\`, o un `/C:/...` con barra
  inicial, o un error), es un **hallazgo** (la autolocalización no es Windows-safe) — anótalo.
- Confirma que la ruta existe:
  ```powershell
  node -e "import('./skills/cross-model-orca/assets/lib/platform.mjs').then(m => { const r = m.resolveInstallRoot(); console.log('existe launch:', require('fs').existsSync(r + '\\launch\\claude-readonly.settings.json')); })"
  ```
  **Esperado:** `existe launch: true`.
- Repite `configDir` con las env vars seteadas para confirmar que se respetan:
  ```powershell
  $env:CODEX_HOME = "C:\tmp\codex-home"; $env:CLAUDE_CONFIG_DIR = "C:\tmp\claude-cfg"
  node -e "import('./skills/cross-model-orca/assets/lib/platform.mjs').then(m => { console.log(m.configDir('codex')); console.log(m.configDir('claude')); })"
  Remove-Item Env:\CODEX_HOME, Env:\CLAUDE_CONFIG_DIR
  ```
  **Esperado:** las rutas ahora cuelgan de `C:\tmp\codex-home` / `C:\tmp\claude-cfg`.

## Prueba 3 — Slug real del transcript de Claude en Windows (la clave)

**Solo si Claude Code CLI está instalado.** Confirma que el slug que calcula el código coincide con
el nombre real del directorio que Claude crea.

1. Calcula el slug esperado para el `cwd` actual (misma fórmula que `slugifyCwd`):
   ```powershell
   $cwd = (Get-Location).Path
   $slug = ($cwd -replace '[^a-zA-Z0-9-]', '-')
   Write-Output "cwd  = $cwd"
   Write-Output "slug = $slug"
   ```
2. Lanza una sesión Claude **corta** con un `--session-id` fijo, parada en ese `cwd`:
   ```powershell
   $env:DISABLE_AUTOUPDATER = "1"
   $sid = "11111111-2222-3333-4444-555555555555"
   claude --tools "Read,Grep,Glob" --session-id $sid "responde exactamente OK" < $null
   ```
3. Busca el transcript real y compáralo con el slug calculado:
   ```powershell
   $base = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { "$env:USERPROFILE\.claude" }
   Get-ChildItem "$base\projects" -Directory | Where-Object Name -like "*$($slug.Substring([Math]::Max(0,$slug.Length-20)))*"
   Test-Path "$base\projects\$slug\$sid.jsonl"
   ```
   - **Esperado:** `Test-Path` devuelve `True` — el archivo `<slug>\<sid>.jsonl` existe con el slug
     que calcula el código. **Si es `False`**, anota el nombre REAL del directorio que Claude creó
     (de `Get-ChildItem`) y cómo difiere del `$slug` calculado: eso es un **hallazgo** (el locator de
     Claude en Windows necesita ajustar `slugifyCwd`), documéntalo con detalle.

## Prueba 4 — Preflight de Node (`assertNode`)

```powershell
node -e "import('./skills/cross-model-orca/assets/lib/platform.mjs').then(m => { try { m.assertNode(18); console.log('assertNode(18) OK'); } catch (e) { console.log('THROW:', e.message); } m.assertNode(999); })"
```

- **Esperado:** imprime `assertNode(18) OK` y luego **lanza** un error claro para `assertNode(999)`
  (Node no llega a la major 999). Confirma que el mensaje de error es legible en Windows.

## Prueba 5 — Comandos PowerShell de instalación / perfiles

Confirma que los bloques PowerShell de `install.md` y `assets/launch/profiles.md` corren en tu shell.

**Nota:** `CROSS_MODEL_ORCA` es **opcional** (el artefacto se autolocaliza — Prueba 2). El bloque de
abajo solo verifica que, **si** la seteas como override, apunta a algo válido; no es un paso
obligatorio de instalación.

```powershell
# Instalación (install.md): la variable es OPCIONAL (override). Si la seteas, debe apuntar al assets:
$env:CROSS_MODEL_ORCA = "$((Get-Location).Path)\skills\cross-model-orca\assets"
Write-Output $env:CROSS_MODEL_ORCA
Test-Path $env:CROSS_MODEL_ORCA
Remove-Item Env:\CROSS_MODEL_ORCA   # limpiar: el default es autolocalizar

# JSON de los settings parsea:
node -e "JSON.parse(require('fs').readFileSync('skills/cross-model-orca/assets/launch/claude-readonly.settings.json','utf8')); JSON.parse(require('fs').readFileSync('skills/cross-model-orca/assets/launch/claude-readonly.mcp.json','utf8')); JSON.parse(require('fs').readFileSync('skills/cross-model-orca/assets/launch/claude-write.settings.json','utf8')); console.log('settings JSON OK')"
```

- **Esperado:** la ruta de `CROSS_MODEL_ORCA` existe (`True`) y los tres JSON parsean.

## Prueba 6 — Endurecimiento opcional `CERO-MCP` en Windows

**Solo si Claude Code CLI está instalado.** Es la garantía del caso desatendido (fail-closed de MCP
por `--strict-mcp-config`). En macOS: allowlist vacío → responde `CERO-MCP`.

```powershell
$env:DISABLE_AUTOUPDATER = "1"
$empty = "$env:TEMP\cmo-empty-mcp.json"
'{"mcpServers":{}}' | Set-Content $empty
claude --tools "Read,Grep,Glob" --strict-mcp-config --mcp-config $empty --settings skills/cross-model-orca/assets/launch/claude-readonly.settings.json "Enumera EXACTAMENTE los nombres de tus herramientas que empiezan con mcp__, una por linea. Si no tienes ninguna responde CERO-MCP" < $null
```

- **Esperado:** `CERO-MCP`. (Confirma que `--strict-mcp-config` deja la sesión sin MCP del entorno
  también en Windows.)

## Prueba 7 — (Opcional) `-c features.apps=false` inline en Codex

**Solo si Codex CLI está instalado.**

```powershell
codex exec -c features.apps=false --strict-config --ephemeral --skip-git-repo-check -s read-only --disable hooks "responde OK" < $null
```

- **Esperado:** responde `OK` sin error de esquema (`--strict-config` valida el campo).

---

## Dónde documentar los resultados

1. **Completa la tabla de abajo** (en este mismo archivo) con lo que realmente pasó.
2. **Actualiza** `skills/cross-model-orca/spikes/RESULTS.md` → "Fase 7 — validación y checkpoints":
   marca el checkpoint **Windows** de `[ ]` a `[x]` (todo pasó) o `[~]` (parcial), con un resumen de
   1-2 líneas y el link mental a esta tabla.
3. Si la Prueba 3 (slug) falló, además **abre un hallazgo** claro: el `cwd` real, el slug calculado,
   el nombre real del directorio de Claude, y la corrección propuesta a `slugifyCwd` en
   `assets/dispatch-adapter.mjs` (sin implementarla si no te lo piden — es checkpoint, no fix).

## Resultados (Windows) — completar

| # | Prueba | Resultado | Evidencia / nota |
|---|--------|-----------|------------------|
| — | Entorno | | Node `___`, Windows `___`, Claude CLI `___`, Codex CLI `___` |
| 1 | Suite de tests | ⬜ pass / ⬜ fail | `tests __ / pass __ / fail __` |
| 2 | Rutas platform.mjs + autolocalización (install root) | ⬜ ok / ⬜ hallazgo | |
| 3 | Slug transcript Claude | ⬜ ok / ⬜ hallazgo / ⬜ N/A | slug calc: `___` · dir real: `___` |
| 4 | assertNode | ⬜ ok / ⬜ hallazgo | |
| 5 | Comandos PowerShell | ⬜ ok / ⬜ hallazgo | |
| 6 | CERO-MCP | ⬜ ok / ⬜ hallazgo / ⬜ N/A | |
| 7 | features.apps inline (Codex) | ⬜ ok / ⬜ hallazgo / ⬜ N/A | |

**Resumen / hallazgos:**

_(completar)_
