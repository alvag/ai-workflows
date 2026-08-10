# Fixtures del documento de contrato

Corpus sintético de los modos `--contrato`, `--ejes` y `--capacidades` de
`scripts/verificar-matriz-despachos.py`. **El documento de contrato del repositorio todavía no
existe:** lo escriben las tasks que lo materializan, y estos archivos congelan la **forma** que
tendrá que cumplir. El orden es el principio del flujo —un modo se construye contra fixtures
sintéticos y se aplica sobre el artefacto real en otra task—, porque al revés el parser hereda la
interpretación de quien escribió el texto y los dos pasan de acuerdo entre sí aunque ambos estén mal.

## Qué hay

| Archivo | Qué es |
|---|---|
| `conforme/contrato.md` | el documento **conforme** de los tres modos, con sus siete secciones |
| `conforme/fuentes/propuesta-doctrinal.md` | documento fuente sintético: dos correcciones lo citan y su texto **está** ahí |
| `conforme/fuentes/exploracion-previa.md` | el **segundo** documento fuente, sin el cual «la citaste mal» y «no la dijo nadie» serían indistinguibles |

Los tres tienen que pasar. Sin casos positivos, un validador que rechace toda entrada satisface
todos los mutantes y su autotest cierra en verde sin haber aceptado jamás un documento válido.

## La forma congelada

Cada sección es un encabezado y una **tabla Markdown** con columnas fijas. Es tabular y no prosa a
propósito: un predicado que rasca prosa se endurece hasta aceptar lo que el autor escribió, y una
tabla se lee igual la escriba quien la escriba. Los encabezados se comparan **normalizados**, así que
`afirmación anterior` y `afirmacion anterior` son la misma columna.

| Sección (slug) | Columnas | Modo que la lee |
|---|---|---|
| `alcance-comprometido` | `tramo`, `estado` | `--contrato` |
| `correcciones` | `id`, `afirmación anterior`, `afirmación corregida`, `evidencia`, `supersesión`, `documento fuente` | `--contrato` |
| `decisiones-diferidas` | `id`, `decisión`, `estado`, `fase de destino` | `--contrato` |
| `eje-ciclo-de-vida-operativo` | `literal`, `tipo`, `sede`, `significado` | `--ejes` |
| `eje-validez-del-reporte-entregado` | ídem | `--ejes` |
| `eje-resultado-semantico` | ídem | `--ejes` |
| `capacidades-de-plataforma` | `afirmación`, `marca`, `versión`, `motivo` | `--capacidades` |

Una celda vacía se escribe `—`, y eso es un valor declarado y no una ausencia interpretada: sin la
marca, cada consumidor elegiría la suya.

## Lo sintético y lo normativo

**El alcance, las correcciones, las decisiones diferidas y las afirmaciones de plataforma son
sintéticos.** Los documentos fuente no existen en el árbol real, y las capacidades hablan de
`herramienta-sintetica` y de `interprete-beta`: un fixture copiado del documento real haría que el
modo y el dato acordaran entre sí.

**Los tres ejes son la excepción, y por un motivo.** La propiedad que esa sección ejerce es la
igualdad exacta contra `INVENTARIO_DE_EJES`, así que con literales inventados no probaría nada. Sus
dieciséis filas son las normativas, y `--autotest-ejes` comprueba en su preludio que el fixture no
haya divergido del inventario.

## El puntero por literal es la única defensa contra un inventario inventado

Los mutantes impiden que el **verificador** sea laxo. No impiden que el **inventario** sea inventado:
esta task y la que escribe el documento podrían acordar tres enums separados pero fabricados y cerrar
las dos su fila. Contra eso hay una sola defensa: cada literal declara una sede **real de `skills/`
que ya existe hoy**, y el preludio la resuelve contra el árbol y exige que el literal aparezca ahí.

Ninguna sede puede vivir fuera de `skills/`. Un literal que apuntara al documento de contrato —que no
existe—, a estos fixtures o a los artefactos del flujo coincidiría siempre consigo mismo, y el modo,
el inventario y su fila quedarían los tres verdes sin ninguna evidencia independiente. Es la misma
regla que gobierna las procedencias de la matriz, un grado más dura.

**`done` aparece en dos ejes y no es una fusión**, y es el caso que más se parece a un defecto sin
serlo: en el eje operativo es el marcador de cierre del crudo —«pertenece al transporte, no al
contenido», dice su sede— y en el semántico es el veredicto de una task delegada. Distinto tipo,
distinta sede, distinto significado. Es el control positivo de `--ejes`, y el bloque `E` muestra las
dos direcciones: con las declaraciones distintas pasa, y al volverlas idénticas se pone rojo.

## Lo que ejerce el conforme, y que no se puede editar sin perderlo

| Pieza | Qué ejerce |
|---|---|
| corrección `C-01` | la variante **riesgosa** del caso conforme: atribuida a la propuesta doctrinal **cuando esa propuesta sí contiene** la afirmación reemplazada. Un modo que rechazara toda atribución a la propuesta pasaría los dos mutantes de atribución y caería acá |
| correcciones `C-02` y `C-03` | dos fuentes distintas, sin las cuales `fuente_equivocada` y `afirmacion_inexistente_en_la_fuente` no se distinguen |
| decisiones `D-01` y `D-02` | **dos** decisiones diferidas, para que quitarle la fase a una sea un defecto **unitario** entre filas válidas |
| eje operativo, `done` | el literal compartido legítimo |
| capacidades | las **tres** marcas ejercidas, con dos dependientes: sin la segunda, quitarle la versión a una no sería unitario |
| capacidades, primera fila | una tubería escapada (`\|`) dentro de una celda, que ejerce el corte por `|` no escapado y su re-escape al mutar |

## Los mutantes no están acá, y es a propósito

Los cuarenta y siete mutantes de los tres modos se **generan** transformando el conforme celda a
celda —por coordenada (sección, clave de la fila, columna) y no por búsqueda de texto, porque dos
celdas con el mismo contenido son un caso real—. Guardarlos como archivos los volvería una
transcripción que quedaría vieja en cuanto el conforme cambiara, y una columna renombrada dejaría el
mutante pasando por otro motivo en vez de romperse.

Los tres que solo el inventario congelado puede ver son los de **alta, baja y sustitución dentro del
vocabulario correcto**: los tres pasan namespace, sede y resolución, y usan `sigue_activo` —un
literal **real** de la misma sede que el contrato deja deliberadamente fuera del eje—, así que no se
delatan por una sede inventada.

## Cómo se corren

```sh
python3 scripts/verificar-matriz-despachos.py --autotest-contrato     # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --autotest-ejes         # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --autotest-capacidades  # exit 0 sano
python3 scripts/verificar-matriz-despachos.py --ejes scripts/fixtures-contrato/conforme/contrato.md
python3 scripts/verificar-matriz-despachos.py --contrato scripts/fixtures-contrato/conforme/contrato.md \
    --raiz scripts/fixtures-contrato/conforme
python3 scripts/verificar-matriz-despachos.py --contrato   # exit 3 mientras el documento no exista
```

**`--contrato` y `--ejes` usan dos raíces distintas y no es un descuido.** Las fuentes de las
correcciones son sintéticas y viven en el corpus, así que `--contrato` recibe `--raiz` apuntando al
fixture; las sedes de los ejes son reales, así que `--ejes` corre contra el repositorio. Con un árbol
sintético, los punteros de los ejes probarían que el modo sabe leer una tabla y nada más.

**Exit 3 no es un fallo: es «no hay veredicto».** Mientras el documento de contrato no exista, los
tres modos de aplicación terminan con 3. Lo que no puede pasar —y el bloque `D` de los tres autotests
lo comprueba en las dos direcciones— es que una ausencia se lea como conformidad.
