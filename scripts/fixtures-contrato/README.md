# Fixtures del documento de contrato

Corpus sintético de los ocho modos que leen el documento de contrato de
`scripts/verificar-matriz-despachos.py`: `--contrato`, `--ejes`, `--capacidades`, `--perfil-schema`,
`--perfil-precedencia`, `--roles`, `--diversidad` y `--defectos`. **El documento de contrato del repositorio todavía no
existe:** lo escriben las tasks que lo materializan, y estos archivos congelan la **forma** que
tendrá que cumplir. El orden es el principio del flujo —un modo se construye contra fixtures
sintéticos y se aplica sobre el artefacto real en otra task—, porque al revés el parser hereda la
interpretación de quien escribió el texto y los dos pasan de acuerdo entre sí aunque ambos estén mal.

## Qué hay

| Archivo | Qué es |
|---|---|
| `conforme/contrato.md` | el documento **conforme** de los ocho modos, con sus trece secciones |
| `conforme/fuentes/propuesta-doctrinal.md` | documento fuente sintético: dos correcciones lo citan y su texto **está** ahí |
| `conforme/fuentes/exploracion-previa.md` | el **segundo** documento fuente, sin el cual «la citaste mal» y «no la dijo nadie» serían indistinguibles |
| `conforme/fuentes/contratos-de-rol.md` | la **sede sintética** de las veinticuatro procedencias ancladas de la sección de roles: sin ella, los campos vigentes serían texto libre |

Los cuatro tienen que pasar. Sin casos positivos, un validador que rechace toda entrada satisface
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

### Las seis secciones que van en bloque `json` y no en tabla

| Sección (slug) | Qué declara | Modo que la lee |
|---|---|---|
| `schema-del-perfil-de-ejecucion` | el contenedor de perfiles entero | `--perfil-schema` |
| `precedencia-del-perfil-de-ejecucion` | los niveles, el default portable y el corpus de escenarios | `--perfil-precedencia` |
| `familias-de-rol` | las cinco familias, sus campos con estado y sus procedencias ancladas | `--roles` |
| `asignaciones-de-despacho` | el mapa de las trece asignaciones, con su autoridad por punto | `--roles` |
| `politica-de-diversidad` | los intentos con sus tres identidades, sus relaciones y la topología | `--diversidad` |
| `inventario-de-defectos` | los defectos con ubicación, naturaleza y fase | `--defectos` |

**El cambio de gramática es por la forma del dato, no por gusto.** Un contenedor de perfiles es un
árbol de tres niveles, una procedencia anclada tiene siete campos y un escenario de precedencia lleva
adentro una superficie de configuración entera. Aplanar eso en celdas obligaría a inventar una
gramática de celda —separadores, escapes, sub-claves— que ya existe y se llama JSON. El argumento que
sostiene las tablas —que un predicado que rasca prosa se endurece hasta aceptar lo que el autor
escribió— vale igual o más para un bloque estructurado.

## Lo sintético y lo normativo

**El alcance, las correcciones, las decisiones diferidas y las afirmaciones de plataforma son
sintéticos.** Los documentos fuente no existen en el árbol real, y las capacidades hablan de
`herramienta-sintetica` y de `interprete-beta`: un fixture copiado del documento real haría que el
modo y el dato acordaran entre sí. Lo mismo vale para el contenedor de perfiles, los escenarios de
precedencia, los intentos de la política de diversidad y las sedes de `contratos-de-rol.md`: lo que
ejercen es que el modo sepa resolver, no que esas frases sean las del ecosistema.

**Hay tres excepciones, y cada una por el mismo motivo.** Donde la propiedad que la sección ejerce es
la **igualdad exacta contra un inventario**, un fixture inventado no probaría nada:

- **los tres ejes**, con sus dieciséis filas comparadas contra `INVENTARIO_DE_EJES`;
- **las cinco familias de rol**, comparadas contra `FAMILIAS_DE_ROL` y apuntadas al roadmap;
- **el mapa de las trece asignaciones**, comparado contra `MAPA_DE_ASIGNACIONES`, y **los seis
  defectos**, comparados por identidad contra `DEFECTOS_MINIMOS`.

Los preludios de `--autotest-ejes` y `--autotest-roles` comprueban que el fixture no haya divergido
de su inventario: si divergiera, el control positivo estaría midiendo otra cosa que la que su fila
declara.

## El puntero por literal es la única defensa contra un inventario inventado

Los mutantes impiden que el **verificador** sea laxo. No impiden que el **inventario** sea inventado:
esta task y la que escribe el documento podrían acordar tres enums separados pero fabricados y cerrar
las dos su fila. Contra eso hay una sola defensa: cada literal declara una sede **real de `skills/`
que ya existe hoy**, y el preludio la resuelve contra el árbol y exige que el literal aparezca ahí.

Ninguna sede puede vivir fuera de `skills/`. Un literal que apuntara al documento de contrato —que no
existe—, a estos fixtures o a los artefactos del flujo coincidiría siempre consigo mismo, y el modo,
el inventario y su fila quedarían los tres verdes sin ninguna evidencia independiente. Es la misma
regla que gobierna las procedencias de la matriz, un grado más dura.

Las **cinco familias de rol** tienen la misma defensa contra otra sede: la tabla de
`docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md`. Y **ocho de las trece asignaciones** la tienen para su
variante, porque el roadmap la nombra. Las otras cinco no: ahí el puntero no existe, y por eso llevan
la marca `decision` y su justificación escrita. Un mapa que se declarara entero derivado del roadmap
estaría afirmando algo falso, y es el mutante `procedencia_no_coincide` el que lo caza.

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
| schema del perfil | la **frontera de los dos niveles**: sus cinco componentes se llaman `schema_version`, `profiles`, `bindings`, `default` y las familias, y ninguno está en la lista blanca. Un modo que aplicara la lista blanca al contenedor los rechazaría a todos y pasaría los seis mutantes de hoja |
| precedencia, `E-02` y `E-03` | los **dos** escenarios de ausencia legítima, por separado. `E-08` es el que más se les parece sin serlo: sin asignación para el rol, pero con valor por defecto en la superficie, así que resuelve por otro nivel |
| familias de rol, `diff-reviewer.scope` | la variante **riesgosa**: un campo `ausente` **sin puntero**. La ausencia declarada es legítima y no todo campo tiene a dónde apuntar; un modo que exigiera puntero a todo caería acá |
| familias de rol, `investigator.scope` | el cuarto estado, `propuesto`, con su fase de destino |
| diversidad, `I-03` | un resultado `same_family` **presente** y correctamente excluido del conteo: estar presente no es el defecto, contarlo sí |
| diversidad, `I-04` | el intento de una sola voz, sin el cual esa mitad de la regla de evidencia independiente no se ejerce |
| defectos | exactamente los **seis** mínimos, para que el séptimo del caso conforme muestre que el mínimo no cierra el conjunto |

## Lo que se congela de cada inventario, que no es lo mismo en todos

| Inventario | Cómo se congela | Por qué |
|---|---|---|
| los tres ejes | se **derivan**: puntero por literal a una sede real de `skills/` | el vocabulario ya existe; nombrarlo y separarlo es el aporte |
| las cinco **familias de rol** | se **derivan**: puntero por familia a la tabla del roadmap | están escritas ahí; si una se la hubiera inventado esta task, no habría sección donde encontrarla |
| el mapa **punto → variante** | se **decide y se escribe**: trece filas congeladas en el verificador | el roadmap mapea *skill → roles reusables*, no *punto → variante*. Medido: siete filas, 13 puntos y 12 menciones de rol, y en tres skills no cuadran. Construirlo es decidir, y cinco de las trece admitían más de una respuesta defendible con el mismo criterio |
| las ocho variantes con `puntero` | llevan además la carga de la prueba | el roadmap sí las nombra, así que el puntero se resuelve y tiene que contenerlas. Las otras cinco se marcan `decision` y llevan su justificación escrita |
| los **seis defectos** | su **identidad** se congela; su ubicación, naturaleza y fase, no | los nombra el criterio. Adjudicar dónde vive cada uno es de la task que materializa el inventario, y fijarlo acá le impondría una adjudicación que su task no tomó |

## Los mutantes no están acá, y es a propósito

Los mutantes de los ocho modos se **generan** transformando el conforme: los de las tres secciones
tabulares, celda a celda por coordenada (sección, clave de la fila, columna) y no por búsqueda de
texto, porque dos celdas con el mismo contenido son un caso real; los de las seis secciones
estructuradas, mutando el **dato** del bloque y volviéndolo a serializar, porque el corpus tiene
veinticuatro procedencias ancladas casi idénticas y un reemplazo textual tocaría la que no era.
Guardarlos como archivos los volvería una transcripción que quedaría vieja en cuanto el conforme
cambiara, y una columna renombrada dejaría el mutante pasando por otro motivo en vez de romperse.

Dos familias se generan **por elemento y no por categoría**: una por cada uno de los trece puntos de
despacho, que sustituye su variante por otra del mismo vocabulario —ninguno se delata por inventar un
token—, y una por cada una de las cinco clases que una hoja de perfil no puede alterar, **más una
sexta que no es ninguna de las cinco**: un tercer parámetro de runtime, que no eleva nada y aun así
no está en la lista blanca. Sin esa sexta, una lista de prohibidos pasaría por lista blanca.

Los tres que solo el inventario congelado puede ver son los de **alta, baja y sustitución dentro del
vocabulario correcto**: los tres pasan namespace, sede y resolución, y usan `sigue_activo` —un
literal **real** de la misma sede que el contrato deja deliberadamente fuera del eje—, así que no se
delatan por una sede inventada.

## Cómo se corren

```sh
for m in contrato ejes capacidades perfil-schema perfil-precedencia roles diversidad defectos; do
    python3 scripts/verificar-matriz-despachos.py --autotest-$m   # exit 0 sano, los ocho
done
python3 scripts/verificar-matriz-despachos.py --ejes scripts/fixtures-contrato/conforme/contrato.md
python3 scripts/verificar-matriz-despachos.py --contrato scripts/fixtures-contrato/conforme/contrato.md \
    --raiz scripts/fixtures-contrato/conforme
python3 scripts/verificar-matriz-despachos.py --roles scripts/fixtures-contrato/conforme/contrato.md \
    --raiz scripts/fixtures-contrato/conforme
python3 scripts/verificar-matriz-despachos.py --contrato   # exit 3 mientras el documento no exista
```

**Los modos usan raíces distintas y no es un descuido.** Las fuentes de las correcciones y las sedes
de los campos de rol son sintéticas y viven en el corpus, así que `--contrato` y `--roles` reciben
`--raiz` apuntando al fixture; las sedes de los ejes, los punteros de las cinco familias y los de las
ocho variantes son reales, así que se resuelven contra el repositorio —`--roles` usa `--arbol` para
eso, y por eso es el único que recibe las dos—. Con un árbol sintético, esos punteros probarían que
el modo sabe leer una tabla o un bloque y nada más.

**Exit 3 no es un fallo: es «no hay veredicto».** Mientras el documento de contrato no exista, los
ocho modos de aplicación terminan con 3. Lo que no puede pasar —y el bloque `D` de los tres autotests
lo comprueba en las dos direcciones— es que una ausencia se lea como conformidad.
