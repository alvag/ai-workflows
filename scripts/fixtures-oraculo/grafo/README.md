# El modelo de dependencias del gate precommit

Los **mecanismos soportados** son los cuatro que `pathset-parser.json` declara, y este directorio
existe para dejar escrito qué caso construye cada uno y cuál se ejerce hoy:

| Mecanismo | Caso construido | Estado hoy |
|---|---|---|
| `import_estatico` | un archivo nuevo del repo importado por el parser: `--autotest-gate-precommit` lo declara como dependencia y comprueba que dé **rojo** | ejercido sobre un pathset ficticio; el parser real solo importa stdlib |
| `import_dinamico_conocido` | `importlib` / `__import__` / `exec` / `eval` en un archivo del pathset | **aborta**: la clausura no es demostrable por análisis estático |
| `script_ejecutado` | un script del repo invocado por el parser | sin ocurrencia en el árbol |
| `archivo_de_configuracion_leido` | un archivo de configuración versionado que el parser lee | sin ocurrencia en el árbol |

**Un mecanismo fuera de esos cuatro aborta la validación**, nunca pasa en silencio. Es lo que
impide que el pathset crezca por un camino que nadie modeló y que el gate siga dando verde.

> El grafo del parser dentro del repo es **vacío** hoy: importa `re`, `sys` y `pathlib`. Los casos
> de arriba se ejercen sobre pathsets ficticios porque el real no los tiene — y ejercerlos igual es
> lo único que evita que la rama se pudra hasta el día en que haga falta.
