# Streams grabados, uno por familia

**Grabados, no escritos.** Cada archivo es la salida literal de una corrida real del CLI de su
familia sobre el prompt «Responde exactamente con la palabra OK y nada mas.», con los argumentos de
aislamiento que el adaptador declara. Existen porque el adaptador de la familia **del conductor**
nunca se ejerce en una corrida productiva —el detector es siempre el de la familia opuesta— y el
que no se ejerce es justamente el que se pudre sin que nadie lo note.

| Archivo | Familia | CLI | Cosecha |
|---|---|---|---|
| `gpt-codex.stream.jsonl` | GPT/Codex | `codex-cli 0.147.0` | el último `item.type == agent_message` del stream JSONL |
| `claude.stream.json` | Claude | `Claude Code 2.1.229` | el campo `result` del objeto `type: result`, con `is_error: false` |

**La clave del stream de Codex es `item.type`, no `item.item_type`.** Un extractor que busque la
segunda devuelve «no hay mensaje» sobre una corrida que entregó bien.
