# Instalación — `cross-model-orca`

Contrato de instalación del transporte cross-model vía Orca. Esta skill-librería aloja módulos
Node ejecutables (`assets/lib/*.mjs`); no hay build ni empaquetado, se ejecutan directo con
`node`.

## 1. Verificar Node ≥ 18

Los módulos usan sintaxis y APIs de `node:test` disponibles desde Node 18. Verifica la versión
instalada:

**POSIX (bash/zsh):**
```bash
node --version
```

**PowerShell:**
```powershell
node --version
```

Si la major es menor a 18, actualiza Node antes de continuar. `assertNode(18)` (en
`assets/lib/platform.mjs`) hace este mismo chequeo en runtime y lanza un error claro si no se
cumple.

## 2. Exportar `CROSS_MODEL_ORCA`

Los módulos resuelven su raíz de instalación desde la variable de entorno `CROSS_MODEL_ORCA`,
que debe apuntar a la ruta **absoluta** de `skills/cross-model-orca/assets` (dentro de este
repo, `ai-workflows`).

**POSIX (bash/zsh)** — reemplaza `<ruta-absoluta-del-repo>` por la ruta real del checkout:
```bash
export CROSS_MODEL_ORCA="<ruta-absoluta-del-repo>/skills/cross-model-orca/assets"
```

Ejemplo concreto en este entorno:
```bash
export CROSS_MODEL_ORCA="/Users/max/Personal/repos/ai-workflows/skills/cross-model-orca/assets"
```

**PowerShell** — reemplaza `<ruta-absoluta-del-repo>` por la ruta real del checkout:
```powershell
$env:CROSS_MODEL_ORCA = "<ruta-absoluta-del-repo>\skills\cross-model-orca\assets"
```

Para que quede seteada en toda sesión nueva, agrega el `export`/`$env:` a tu `~/.zshrc`,
`~/.bashrc` o perfil de PowerShell (`$PROFILE`), según corresponda.

## 3. Instalación reproducible de `skills-ref`

`skills-ref` es el validador de formato de skills del repo oficial
[`agentskills/agentskills`](https://github.com/agentskills/agentskills) (carpeta
`skills-ref/` del monorepo). **Es un paquete Python** (no Node) publicado en PyPI como
[`skills-ref`](https://pypi.org/project/skills-ref/); esta skill-librería no depende de él en
runtime, solo se usa como checkpoint manual de validación al autorear/editar skills.

**Comando verificado (2026-07-19) — vía `uv`, sin instalar nada de forma persistente:**

**POSIX (bash/zsh):**
```bash
uvx --from skills-ref agentskills validate ./skills/cross-model-orca
```

**PowerShell:**
```powershell
uvx --from skills-ref agentskills validate ./skills/cross-model-orca
```

> **Atención — discrepancia confirmada, requiere reconfirmar en cada actualización del
> paquete:** el `README.md` del repo oficial documenta el ejecutable como `skills-ref`
> (`skills-ref validate path/to/skill`), pero la versión publicada en PyPI al momento de
> escribir esto (`skills-ref` 0.1.1) expone el ejecutable con el nombre **`agentskills`**, no
> `skills-ref`. Se verificó en vivo: `uvx skills-ref ...` falla con
> *"An executable named `skills-ref` is not provided by package `skills-ref`"* y sugiere
> `uvx --from skills-ref agentskills`. Antes de depender de este comando en un pipeline
> automatizado, confirma el nombre del ejecutable contra la versión de `skills-ref` que
> tengas instalada (`agentskills --version` o `skills-ref --version`, según corresponda).

**Alternativa con `pip` (entorno virtual, en vez de `uv`):**

**POSIX (bash/zsh):**
```bash
python3 -m venv .venv-skills-ref
source .venv-skills-ref/bin/activate
pip install skills-ref
agentskills validate ./skills/cross-model-orca
```

**PowerShell:**
```powershell
python -m venv .venv-skills-ref
.venv-skills-ref\Scripts\Activate.ps1
pip install skills-ref
agentskills validate ./skills/cross-model-orca
```

### Fallback si `skills-ref`/`agentskills` no se puede instalar

Si no hay Python disponible o la instalación falla (sin conectividad a PyPI, política de la
máquina, etc.), **saltear la validación automática de formato** y dejarla como **checkpoint
manual**: antes de dar por buena una skill nueva o editada, revisar a mano contra
[`agentskills.io/specification`](https://agentskills.io/specification) que `SKILL.md` tenga
`name`/`description` válidos, que `description` no supere 1024 caracteres y que la estructura de
carpeta (`SKILL.md` + `reference.md` + `README.md`) sea la esperada. Documentar en el PR que la
validación fue manual (sin `skills-ref`) cuando corresponda.

## 4. API key de `context7` para el allowlist read-only

El Claude secundario read-only se lanza con `--strict-mcp-config --mcp-config
assets/launch/claude-readonly.mcp.json` (gate primario de MCP; ver `assets/launch/mcp-inventory.md`
→ "Dos gates"). Ese allowlist declara `context7` (documentación de librerías, solo lectura) con la
API key como **placeholder** (`REEMPLAZA_POR_TU_API_KEY_DE_CONTEXT7`) — **el repo no lleva una key
real**.

Antes de despachar un secundario read-only que use `context7`, pon tu key. Dos opciones (no
edites el archivo trackeado en el checkout: dejaría el árbol sucio y arriesga commitear la key):

- **Recomendado — copia a una ruta runtime con la key puesta** (mismo patrón que los perfiles de
  Codex en `$CODEX_HOME`), y apunta `--mcp-config` a esa copia:

  **POSIX (bash/zsh):**
  ```bash
  mkdir -p "$HOME/.cross-model-orca-state/launch"
  sed 's/REEMPLAZA_POR_TU_API_KEY_DE_CONTEXT7/'"$CONTEXT7_API_KEY"'/' \
    skills/cross-model-orca/assets/launch/claude-readonly.mcp.json \
    > "$HOME/.cross-model-orca-state/launch/claude-readonly.mcp.json"
  ```

  **PowerShell:**
  ```powershell
  New-Item -ItemType Directory -Force "$HOME/.cross-model-orca-state/launch" | Out-Null
  (Get-Content -Raw skills/cross-model-orca/assets/launch/claude-readonly.mcp.json) `
    -replace 'REEMPLAZA_POR_TU_API_KEY_DE_CONTEXT7', $env:CONTEXT7_API_KEY |
    Set-Content "$HOME/.cross-model-orca-state/launch/claude-readonly.mcp.json"
  ```

- **Si no quieres `context7` en el secundario:** deja el allowlist con `{"mcpServers": {}}` (cero
  MCP; el secundario explora con `Read`/`Grep`/`Glob`). Es el default más fail-closed.

> No pusimos la key vía `${CONTEXT7_API_KEY}` en el archivo porque no se pudo confirmar que el
> `--mcp-config` de Claude 2.1.214 expanda variables de entorno (el probe quedó inconcluso por el
> cold-start de `context7` en modo `-p`). La sustitución explícita de arriba es determinística.
> Si en tu entorno confirmas que la expansión de `${VAR}` funciona, puedes usarla en su lugar.
