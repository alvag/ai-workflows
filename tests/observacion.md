# Contrato de observación

`tests/observacion.py` hereda el oracle de `scripts/verificar-paridad-powershell.py`. Conserva las
firmas de `Observacion`, `ejecutar` y `comparar`, incluido el `stderr`, la señal de `timeout` y el
`interprete` usado.

La comparación tiene cinco dimensiones independientes:

1. clase de resultado;
2. diagnósticos como multiconjunto de eventos, preservando multiplicidad y canal;
3. stdout normalizado;
4. rutas y contenido normalizado de artefactos;
5. código de salida exacto.

El orden de los diagnósticos no es contractual. Su multiplicidad, canal, prefijo y sensibilidad a
mayúsculas sí lo son. Stdout y el contenido de artefactos normalizan únicamente CRLF a LF, un BOM
inicial y espacios o tabuladores al final de cada línea. No normalizan orden, espacios internos,
nombres de artefacto ni mayúsculas.

Ante una divergencia entre variantes, POSIX es la variante fuente salvo una excepción escrita y
aprobada en el gate correspondiente.

## Desviación aprobada

La función heredada comparaba clase, eventos, stdout y artefactos, pero no observaba el código de
salida exacto. El oracle durable añade esa quinta dimensión para distinguir, por ejemplo, código
`2` de código `99` aunque ambos produzcan la misma clase. Esta es la única desviación respecto de la
función heredada.
