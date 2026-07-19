# Instalación — `cross-model-orca`

Contrato de instalación del transporte cross-model vía Orca. Esta skill-librería aloja módulos
Node ejecutables (`assets/lib/*.mjs`); no hay build ni empaquetado, se ejecutan directo con
`node`.

## 1. Verificar Node ≥ 18

Los módulos usan sintaxis y APIs de `node:test` disponibles desde Node 18. Verificá la versión
instalada:

**POSIX (bash/zsh):**
```bash
node --version
```

**PowerShell:**
```powershell
node --version
```

Si la major es menor a 18, actualizá Node antes de continuar. `assertNode(18)` (en
`assets/lib/platform.mjs`) hace este mismo chequeo en runtime y lanza un error claro si no se
cumple.

## 2. Exportar `CROSS_MODEL_ORCA`

Los módulos resuelven su raíz de instalación desde la variable de entorno `CROSS_MODEL_ORCA`,
que debe apuntar a la ruta **absoluta** de `skills/cross-model-orca/assets` (dentro de este
repo, `ai-workflows`).

**POSIX (bash/zsh)** — reemplazá `<ruta-absoluta-del-repo>` por la ruta real del checkout:
```bash
export CROSS_MODEL_ORCA="<ruta-absoluta-del-repo>/skills/cross-model-orca/assets"
```

Ejemplo concreto en este entorno:
```bash
export CROSS_MODEL_ORCA="/Users/max/Personal/repos/ai-workflows/skills/cross-model-orca/assets"
```

**PowerShell** — reemplazá `<ruta-absoluta-del-repo>` por la ruta real del checkout:
```powershell
$env:CROSS_MODEL_ORCA = "<ruta-absoluta-del-repo>\skills\cross-model-orca\assets"
```

Para que quede seteada en toda sesión nueva, agregá el `export`/`$env:` a tu `~/.zshrc`,
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
> automatizado, confirmá el nombre del ejecutable contra la versión de `skills-ref` que
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
