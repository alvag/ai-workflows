# Contrato sintético de ejecución

**Este documento no es el contrato del repositorio.** Es el fixture **conforme** de los ocho modos
de `scripts/verificar-matriz-despachos.py` que leen el documento de contrato —`--contrato`, `--ejes`,
`--capacidades`, `--perfil-schema`, `--perfil-precedencia`, `--roles`, `--diversidad` y
`--defectos`—: congela la **forma** que el contrato real tendrá que cumplir, y se escribe antes que
él a propósito. Al revés, el parser heredaría la interpretación de quien escribió el texto y los dos
pasarían de acuerdo entre sí aunque ambos estuvieran mal.

Su alcance, sus correcciones y sus decisiones diferidas son **sintéticos**, y sus documentos fuente
viven en `fuentes/`. También lo son el contenedor de perfiles, los escenarios de precedencia, los
intentos de la política de diversidad y las sedes de los campos de rol.

Hay tres excepciones declaradas, y las tres por el mismo motivo: donde la propiedad que la sección
ejerce es la **igualdad exacta contra un inventario congelado**, un dato inventado no probaría nada.
Son los **tres ejes** —con sus literales y sus punteros normativos—, las **cinco familias de rol**
—apuntadas a la tabla del roadmap— y el **mapa de las trece asignaciones** junto con las
**identidades de los seis defectos mínimos**.

## Alcance comprometido

| tramo | estado |
|---|---|
| Fases 0-4 | comprometido |
| Fases 5-7 | condicionado a las métricas de las anteriores |

## Correcciones

Cada fila reemplaza una afirmación que vive en el documento de la última columna. La cláusula de
supersesión nombra ese documento: sin nombrarlo, «este contrato prevalece» no dice sobre qué.

| id | afirmación anterior | afirmación corregida | evidencia | supersesión | documento fuente |
|---|---|---|---|---|---|
| C-01 | La revisión de artefactos sintéticos no tiene dueño declarado en el ecosistema de ejemplo. | La revisión de artefactos sintéticos tiene dueño declarado: la skill de revisión del corpus de ejemplo. | La skill de revisión del corpus declara el artefacto entre sus entradas admitidas. | Este contrato prevalece sobre `propuesta-doctrinal.md` en este punto. | fuentes/propuesta-doctrinal.md |
| C-02 | Un archivo de política de invocación sintética queda definido por su extensión. | Un archivo de política de invocación sintética queda definido por su ubicación y su clave de habilitación, no por su extensión. | Dos archivos con la misma extensión y distinta ubicación reciben trato distinto en el corpus. | Este contrato prevalece sobre `exploracion-previa.md` en este punto. | fuentes/exploracion-previa.md |
| C-03 | El despacho sintético de la familia beta corre siempre en primer plano. | El despacho sintético de la familia beta corre en segundo plano cuando el presupuesto de espera supera el tope conversacional. | El corpus de escenarios registra dos despachos beta en segundo plano. | Este contrato prevalece sobre `propuesta-doctrinal.md` en este punto. | fuentes/propuesta-doctrinal.md |

## Decisiones diferidas

Ninguna se resuelve acá: quedan **íntegramente diferidas**, cada una con la fase que la va a tomar.

| id | decisión | estado | fase de destino |
|---|---|---|---|
| D-01 | Si el arbitraje sintético lo ejerce el conductor o un tercero. | diferida | Fase 3 |
| D-02 | Con qué granularidad se mide el presupuesto sintético de espera. | diferida | Fase 5 |

## Los tres ejes

Tres preguntas distintas sobre una misma corrida delegada, con **vocabularios separados**. Nombrarlas
y separarlas es el aporte de este contrato; los literales salen de sedes que ya existen, y cada uno
declara la suya.

Cada literal se escribe **con su namespace** —`<eje>.<literal>`—: sin él, el mismo token citado en
otra sección no dice de qué eje es, que es exactamente la fusión que estas tres tablas existen para
impedir.

### Eje: ciclo de vida operativo

Qué pasó con la corrida **como proceso**, con independencia de lo que haya entregado.

| literal | tipo | sede | significado |
|---|---|---|---|
| `ciclo_de_vida_operativo.resultado_entregado` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | la espera terminó con un resultado terminal que se puede adjudicar |
| `ciclo_de_vida_operativo.corte_presupuesto` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | venció el presupuesto de espera del conductor; la corrida sigue activa |
| `ciclo_de_vida_operativo.error` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | terminal comprobado de fallo: se sabe qué pasó y se puede adjudicar |
| `ciclo_de_vida_operativo.cancelacion` | outcome_de_espera | `skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera` | terminal por decisión, con su segundo componente de cese confirmado o incierto |
| `ciclo_de_vida_operativo.UNAVAILABLE` | terminal_sin_entrega | `skills/co-explore/reference.md#estados-del-worker` | el worker no respondió o no se pudo lanzar, así que no hay reporte que validar |
| `ciclo_de_vida_operativo.done` | marcador_de_cierre | `skills/co-explore/reference.md#senal-de-finalizacion` | el crudo cerró con su marcador de fin; pertenece al transporte y no al contenido |

### Eje: validez del reporte entregado

Dado que el worker **entregó** algo, si eso satisface el contrato de salida. El eje no se pronuncia
sobre el mérito de lo entregado: eso es el tercer eje.

| literal | tipo | sede | significado |
|---|---|---|---|
| `validez_del_reporte_entregado.READY` | clase_de_validez | `skills/co-explore/reference.md#estados-del-worker` | el reporte pasa todos los predicados del contrato de salida, sin excepciones |
| `validez_del_reporte_entregado.INVALID` | clase_de_validez | `skills/co-explore/reference.md#estados-del-worker` | respondió, y lo que entregó falla alguno de esos predicados |
| `validez_del_reporte_entregado.clarification-needed` | clase_de_validez | `skills/co-explore/reference.md#clarification-needed-el-cuarto-estado` | frenó ante una ambigüedad, entregó lo que alcanzó a mapear y adosó la pregunta |

### Eje: resultado semántico

Qué dice el trabajo entregado **sobre el objeto de la delegación**. Un reporte válido puede traer
cualquiera de estos valores, y uno inválido no trae ninguno.

| literal | tipo | sede | significado |
|---|---|---|---|
| `resultado_semantico.APPROVED` | veredicto_de_revision | `skills/cross-review/reference.md#veredicto-derivado` | el ledger no deja findings en estado no terminal: la revisión convergió |
| `resultado_semantico.REVISE` | veredicto_de_revision | `skills/cross-review/reference.md#veredicto-derivado` | queda al menos un finding sin resolver, o una disputa que abre el gate humano |
| `resultado_semantico.done` | estado_de_task | `skills/sdd-flow/reference.md#prompt-del-subagente-por-task` | el subagente delegado ejecutó la task tal como estaba escrita |
| `resultado_semantico.failed` | estado_de_task | `skills/sdd-flow/reference.md#prompt-del-subagente-por-task` | el subagente delegado se bloqueó y lo dice, en vez de improvisar otro enfoque |
| `resultado_semantico.verified` | estado_de_repo_delegado | `skills/sdd-orchestrator/reference.md#prompt-del-agente-delegado` | el agente delegado por repo dejó su parte verde y con sus AC cubiertos |
| `resultado_semantico.PARTIAL` | cierre_de_unidad | `skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo` | parte la hizo el implementador y parte la terminó el conductor por takeover |
| `resultado_semantico.BLOCKED` | cierre_de_unidad | `skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo` | la fila nunca se pudo medir, así que no tiene criterio de «hecho» |

**`done` aparece en dos ejes y no es una fusión.** En el primero es el marcador de cierre del crudo
—transporte, no contenido— y en el tercero es el veredicto de una task delegada. Distinto tipo,
distinta sede y distinto significado: el literal coincide y la cosa que nombra, no.

## Capacidades de plataforma

Toda afirmación de plataforma va marcada. `dependiente` registra **con qué versión** se comprobó;
`no_verificable` registra **por qué** el runtime no la expone, que es la forma correcta de tratarla y
no un defecto.

| afirmación | marca | versión | motivo |
|---|---|---|---|
| El corte por `\|` no escapado parte una fila de tabla igual en cualquier intérprete de Markdown del corpus. | portable | — | — |
| Un rename dentro del mismo directorio publica el archivo sin dejar ver un estado intermedio. | portable | — | — |
| `herramienta-sintetica exec` acepta acotar el sandbox a solo lectura con una bandera propia. | dependiente | herramienta-sintetica 3.12.0 | — |
| El intérprete sintético de la familia beta no admite redirección de entrada por `<` y exige tubería. | dependiente | interprete-beta 7.4 | — |
| El runtime sintético expone un identificador de proceso consultable para el worker delegado. | no_verificable | — | el harness del corpus no publica ningún identificador de proceso, así que la afirmación no se puede comprobar desde adentro |

## Schema del perfil de ejecución

El **contenedor completo** es obligatorio —versión, perfiles nombrados, asignaciones por rol, valor
por defecto y familias—; lo que lleva **lista blanca cerrada** es el objeto de parámetros de cada
perfil, que entrega al runtime el modelo y el esfuerzo de razonamiento y nada más. Son dos niveles
distintos: los componentes del contenedor viven **fuera** de ese objeto, así que la lista blanca no
los alcanza.

Una asignación elige qué perfil se resuelve. No transporta herramientas, aislamiento, permisos,
contrato de salida ni autoridad: una hoja capaz de alterar cualquiera de esos cinco convierte el
perfil en una superficie de elevación de privilegios, que es lo contrario de lo que declara.

```json
{
  "subagents": {
    "schema_version": 1,
    "profiles": {
      "economy": {
        "codex": {
          "model": "inherit",
          "reasoning": "low"
        },
        "claude": {
          "model": "inherit",
          "reasoning": "low"
        }
      },
      "balanced": {
        "codex": {
          "model": "inherit",
          "reasoning": "medium"
        },
        "claude": {
          "model": "inherit",
          "reasoning": "medium"
        }
      },
      "deep-review": {
        "codex": {
          "model": "inherit",
          "reasoning": "high"
        },
        "claude": {
          "model": "inherit",
          "reasoning": "high"
        }
      }
    },
    "bindings": {
      "default": "balanced",
      "roles": {
        "explorer": "economy",
        "investigator": "deep-review",
        "design-reviewer": "deep-review",
        "bounded-implementer": "balanced",
        "diff-reviewer": "deep-review"
      }
    }
  }
}
```

## Precedencia del perfil de ejecución

Los niveles se recorren en orden y el primero que resuelve gana. Los escenarios de abajo **no** son
ejemplos: son el corpus contra el que la precedencia se ejecuta, y cada uno declara qué tiene que
resolver.

Un perfil sin uso, una asignación a un perfil inexistente y una referencia rota resuelven
**inválidos**, no ignorados. La ausencia legítima resuelve al valor por defecto portable, y sus dos
escenarios van **por separado**: no es lo mismo un punto sin asignación habiendo superficie que un
punto sin superficie alguna, y un solo caso los confundiría.

```json
{
  "niveles": [
    "override_explicito_del_usuario",
    "asignacion_del_punto_de_despacho",
    "asignacion_por_rol_de_la_superficie",
    "valor_por_defecto_de_la_superficie",
    "perfil_default_portable",
    "default_de_la_sesion_o_plataforma"
  ],
  "default_portable": "balanced",
  "escenarios": [
    {
      "id": "E-01",
      "descripcion": "superficie con asignación para el rol pedido",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {
                "model": "inherit",
                "reasoning": "low"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "low"
              }
            },
            "balanced": {
              "codex": {
                "model": "inherit",
                "reasoning": "medium"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "medium"
              }
            }
          },
          "bindings": {
            "default": "balanced",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "economy",
        "nivel": "asignacion_por_rol_de_la_superficie"
      }
    },
    {
      "id": "E-02",
      "descripcion": "ausencia legítima (a): hay superficie de configuración y el punto no tiene asignación para su rol",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {
                "model": "inherit",
                "reasoning": "low"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "low"
              }
            }
          },
          "bindings": {
            "roles": {
              "investigator": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "balanced",
        "nivel": "perfil_default_portable",
        "causa": "sin_asignacion_para_el_rol"
      }
    },
    {
      "id": "E-03",
      "descripcion": "ausencia legítima (b): el punto no tiene superficie de configuración alguna",
      "rol": "explorer",
      "superficie": null,
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "balanced",
        "nivel": "perfil_default_portable",
        "causa": "sin_superficie_de_configuracion"
      }
    },
    {
      "id": "E-04",
      "descripcion": "un perfil declarado que ningún binding referencia",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {
                "model": "inherit",
                "reasoning": "low"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "low"
              }
            },
            "deep-review": {
              "codex": {
                "model": "inherit",
                "reasoning": "high"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "high"
              }
            }
          },
          "bindings": {
            "default": "economy",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "invalido",
        "causa": "perfil_sin_uso"
      }
    },
    {
      "id": "E-05",
      "descripcion": "una asignación que nombra un perfil que no existe",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {
                "model": "inherit",
                "reasoning": "low"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "low"
              }
            }
          },
          "bindings": {
            "default": "economy",
            "roles": {
              "explorer": "economy",
              "diff-reviewer": "turbo"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "invalido",
        "causa": "asignacion_a_perfil_inexistente"
      }
    },
    {
      "id": "E-06",
      "descripcion": "el valor por defecto de la superficie apunta a un perfil que no existe",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {
                "model": "inherit",
                "reasoning": "low"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "low"
              }
            }
          },
          "bindings": {
            "default": "no-existe",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "invalido",
        "causa": "referencia_rota"
      }
    },
    {
      "id": "E-07",
      "descripcion": "override explícito del usuario para la corrida",
      "rol": "explorer",
      "override": "deep-review",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "economy": {
              "codex": {
                "model": "inherit",
                "reasoning": "low"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "low"
              }
            },
            "deep-review": {
              "codex": {
                "model": "inherit",
                "reasoning": "high"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "high"
              }
            }
          },
          "bindings": {
            "default": "economy",
            "roles": {
              "explorer": "economy"
            }
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "deep-review",
        "nivel": "override_explicito_del_usuario"
      }
    },
    {
      "id": "E-08",
      "descripcion": "sin asignación para el rol, pero la superficie declara su valor por defecto: no es la ausencia legítima",
      "rol": "explorer",
      "superficie": {
        "subagents": {
          "schema_version": 1,
          "profiles": {
            "balanced": {
              "codex": {
                "model": "inherit",
                "reasoning": "medium"
              },
              "claude": {
                "model": "inherit",
                "reasoning": "medium"
              }
            }
          },
          "bindings": {
            "default": "balanced",
            "roles": {}
          }
        }
      },
      "resolucion_esperada": {
        "clase": "resuelto",
        "perfil": "balanced",
        "nivel": "valor_por_defecto_de_la_superficie"
      }
    }
  ]
}
```

## Familias de rol

Cada campo declara su **estado** —vigente en una sede normativa, observado en el comportamiento,
ausente, o propuesto para una fase futura—. Los declarados vigentes u observados están **anclados** y
se resuelven con el mismo verificador semántico que las hojas de la matriz: sustituir una entrada,
una salida o un scope por otro plausible hace que el valor resuelto deje de coincidir con el
declarado.

Un campo `ausente` declara su motivo y **no** lleva puntero: la ausencia declarada es legítima y no
todo campo tiene a dónde apuntar.

Las cinco familias **se derivan** de la tabla del roadmap, y cada una lleva su puntero normativo.

```json
{
  "familias": [
    {
      "familia": "explorer",
      "puntero": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "vigente",
          "valor": "paquete de contexto congelado y objetivo de mapeo, sin acceso a los mapas de los demás",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "explorer", "encabezado_de_columna": "entrada"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "salida": {
          "estado": "vigente",
          "valor": "índice compacto de hallazgos, con el detalle disponible bajo demanda",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "explorer", "encabezado_de_columna": "salida"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "scope": {
          "estado": "vigente",
          "valor": "lectura del árbol de trabajo; ninguna escritura",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "explorer", "encabezado_de_columna": "scope"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        }
      }
    },
    {
      "familia": "investigator",
      "puntero": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "vigente",
          "valor": "síntoma reproducible y las corridas previas que ya fallaron",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "investigator", "encabezado_de_columna": "entrada"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "salida": {
          "estado": "observado",
          "valor": "causas raíz rankeadas con su plan de verificación",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "investigator", "encabezado_de_columna": "salida"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "scope": {
          "estado": "propuesto",
          "fase": "Fase 2"
        }
      }
    },
    {
      "familia": "design-reviewer",
      "puntero": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "vigente",
          "valor": "el artefacto de diseño en revisión y el criterio contra el que se lo juzga",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "design-reviewer", "encabezado_de_columna": "entrada"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "salida": {
          "estado": "vigente",
          "valor": "findings con severidad y el veredicto derivado del ledger",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "design-reviewer", "encabezado_de_columna": "salida"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "scope": {
          "estado": "observado",
          "valor": "lectura del artefacto y del árbol que lo respalda",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "design-reviewer", "encabezado_de_columna": "scope"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        }
      }
    },
    {
      "familia": "bounded-implementer",
      "puntero": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "vigente",
          "valor": "un work order congelado, con su criterio de hecho y su alcance de archivos",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "bounded-implementer", "encabezado_de_columna": "entrada"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "salida": {
          "estado": "vigente",
          "valor": "el diff producido y el receipt de la corrida",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "bounded-implementer", "encabezado_de_columna": "salida"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "scope": {
          "estado": "vigente",
          "valor": "escritura acotada al working dir declarado por el work order",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "bounded-implementer", "encabezado_de_columna": "scope"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        }
      }
    },
    {
      "familia": "diff-reviewer",
      "puntero": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills",
      "campos": {
        "entrada": {
          "estado": "vigente",
          "valor": "el diff a revisar y el contrato que ese diff dice cumplir",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "diff-reviewer", "encabezado_de_columna": "entrada"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "salida": {
          "estado": "observado",
          "valor": "findings sobre el diff, cada uno con su ubicación",
          "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "diff-reviewer", "encabezado_de_columna": "salida"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        },
        "scope": {
          "estado": "ausente",
          "motivo": "ninguna sede del corpus declara hasta dónde llega la lectura de este revisor; se registra la ausencia en vez de inventarla"
        }
      }
    }
  ]
}
```

## Asignaciones de despacho

El mapa punto → familia → variante de los trece puntos. **No se deriva de ninguna fuente:** el
roadmap mapea *skill → roles reusables*, no *punto → variante*. Construirlo es decidir, y por eso
cada fila declara su procedencia: `puntero` cuando el roadmap nombra la variante —y entonces el
puntero se resuelve y tiene que contenerla—, `decision` cuando la asignación se tomó acá, y entonces
lleva su justificación.

La **autoridad final va por punto y variante**, no por familia de rol. Y dos variantes cuyo
resultado hoy tiene forma distinta no comparten declaración de salida.

```json
{
  "asignaciones": [
    {
      "punto": "co-explore · fan-out dual",
      "familia": "explorer / investigator",
      "variante": "fan-out en modos explore y counter-plan; root-cause en modo investigate",
      "procedencia": "decision",
      "forma_de_resultado": "mapa_comparable",
      "declaracion_de_salida": "salida.mapa-comparable",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor arbitra entre los dos mapas y no produce uno propio",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "co-explore · fan-out dual", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "justificacion": "la skill lista tres roles para dos puntos; el fan-out sirve a familias distintas según el modo, así que la asignación es condicionada y no única"
    },
    {
      "punto": "co-explore · debate",
      "familia": "design-reviewer",
      "variante": "decision-debate",
      "procedencia": "puntero",
      "forma_de_resultado": "postura_con_recomendacion",
      "declaracion_de_salida": "salida.postura",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor es voz y decide tras leer la postura",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "co-explore · debate", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "cross-review · revisor por ronda",
      "familia": "design-reviewer",
      "variante": "artifact-review",
      "procedencia": "puntero",
      "forma_de_resultado": "veredicto_de_revision",
      "declaracion_de_salida": "salida.veredicto",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor adjudica cada finding y el gate humano cierra",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "cross-review · revisor por ronda", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "cross-implement · implementador inicial",
      "familia": "bounded-implementer",
      "variante": "work-order",
      "procedencia": "puntero",
      "forma_de_resultado": "diff_con_receipt",
      "declaracion_de_salida": "salida.diff",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor revisa el diff como un PR ajeno y es quien commitea",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "cross-implement · implementador inicial", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "cross-implement · fix loop",
      "familia": "bounded-implementer",
      "variante": "fix-round",
      "procedencia": "decision",
      "forma_de_resultado": "diff_con_receipt",
      "declaracion_de_salida": "salida.diff",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor corre la prueba él mismo y decide si hay otra ronda",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "cross-implement · fix loop", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "justificacion": "el roadmap dice «después diff-reviewer», pero ese revisor es el conductor, que no es un punto de despacho delegado; lo que se despacha en el fix loop es el implementador corrigiendo contra el mismo work order"
    },
    {
      "punto": "sdd-flow · analyze",
      "familia": "explorer",
      "variante": "codebase-survey",
      "procedencia": "decision",
      "forma_de_resultado": "mapa_para_un_plan",
      "declaracion_de_salida": "salida.mapa-de-analyze",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor escribe el plan con lo que el survey haya encontrado",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "sdd-flow · analyze", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "justificacion": "el roadmap asigna la familia pero ninguna variante; se separa del fan-out de co-explore porque el contrato de salida difiere: analyze alimenta un plan y el fan-out produce mapas destinados a compararse"
    },
    {
      "punto": "sdd-flow · implementer por task",
      "familia": "bounded-implementer",
      "variante": "task",
      "procedencia": "puntero",
      "forma_de_resultado": "diff_con_receipt",
      "declaracion_de_salida": "salida.diff",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor cierra la task tras leer su reporte y su diff",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "sdd-flow · implementer por task", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "sdd-flow · reviewer por task",
      "familia": "diff-reviewer",
      "variante": "task",
      "procedencia": "decision",
      "forma_de_resultado": "findings_sobre_un_diff",
      "declaracion_de_salida": "salida.findings",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor adjudica los findings de la task",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "sdd-flow · reviewer por task", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "justificacion": "el roadmap agrupa los dos revisores de la skill bajo un solo diff-reviewer sin variantes que los distingan"
    },
    {
      "punto": "sdd-flow · revisión final",
      "familia": "diff-reviewer",
      "variante": "final",
      "procedencia": "decision",
      "forma_de_resultado": "findings_sobre_un_diff",
      "declaracion_de_salida": "salida.findings",
      "autoridad": {
        "estado": "vigente",
        "valor": "el gate humano cierra el flujo con los findings agregados a la vista",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "sdd-flow · revisión final", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "justificacion": "mismo motivo que el reviewer por task, y la diferencia es real: uno ve el diff de una task y el otro el diff agregado de todas"
    },
    {
      "punto": "sdd-orchestrator · fan-out por repo",
      "familia": "bounded-implementer",
      "variante": "repo-runner",
      "procedencia": "puntero",
      "forma_de_resultado": "repo_verificado",
      "declaracion_de_salida": "salida.repo",
      "autoridad": {
        "estado": "vigente",
        "valor": "el orquestador consolida y ningún worker cierra el objetivo madre",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "sdd-orchestrator · fan-out por repo", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "sdd-pr-feedback · implement delegado",
      "familia": "bounded-implementer",
      "variante": "work-order",
      "procedencia": "puntero",
      "forma_de_resultado": "diff_con_receipt",
      "declaracion_de_salida": "salida.diff",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor responde el comentario del PR y decide si se resuelve",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "sdd-pr-feedback · implement delegado", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "bitbucket-code-review · panel",
      "familia": "diff-reviewer",
      "variante": "review",
      "procedencia": "puntero",
      "forma_de_resultado": "findings_sobre_un_diff",
      "declaracion_de_salida": "salida.findings",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor consolida el panel en una sola conclusión",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "bitbucket-code-review · panel", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    },
    {
      "punto": "bitbucket-code-review · validador adversarial",
      "familia": "diff-reviewer",
      "variante": "refute",
      "procedencia": "puntero",
      "forma_de_resultado": "refutacion_de_finding",
      "declaracion_de_salida": "salida.refutacion",
      "autoridad": {
        "estado": "vigente",
        "valor": "el conductor decide si la refutación tumba el finding",
        "procedencia": {"sede": "fuentes/contratos-de-rol.md", "tipo_de_sede": "fila_de_tabla_markdown", "selector": {"clave_primera_celda": "bitbucket-code-review · validador adversarial", "encabezado_de_columna": "autoridad final"}, "cardinalidad": {"tipo": "exactamente_una"}, "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
      },
      "puntero_variante": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#1-que-significa-soportado-por-las-siete-skills"
    }
  ]
}
```

## Política de diversidad

Por intento se registran las **tres identidades** —quien conduce, quien escribió el artefacto en
juego y el trabajo delegado— y las **relaciones** entre ellas. La topología agregada de la corrida se
**deriva** de esos registros: está escrita abajo para que se pueda leer, y el verificador la
recalcula en vez de creerle.

Un resultado cuenta como **evidencia independiente** solo cuando el trabajo delegado es de otra
familia que quien escribió el artefacto que juzga, y la corrida no fue de una sola voz. Un resultado
`same_family` puede estar presente sin ser un defecto; contarlo como independiente sí lo es.

```json
{
  "familias": [
    "claude",
    "codex"
  ],
  "intentos": [
    {
      "id": "I-01",
      "conductor": "claude",
      "autor_del_artefacto": "claude",
      "worker": "codex",
      "relaciones": {"worker_vs_conductor": "cross_family", "worker_vs_autor": "cross_family"},
      "cuenta_como_evidencia_independiente": true
    },
    {
      "id": "I-02",
      "conductor": "claude",
      "autor_del_artefacto": "codex",
      "worker": "claude",
      "relaciones": {"worker_vs_conductor": "same_family", "worker_vs_autor": "cross_family"},
      "cuenta_como_evidencia_independiente": true
    },
    {
      "id": "I-03",
      "conductor": "claude",
      "autor_del_artefacto": "codex",
      "worker": "codex",
      "relaciones": {"worker_vs_conductor": "cross_family", "worker_vs_autor": "same_family"},
      "cuenta_como_evidencia_independiente": false
    },
    {
      "id": "I-04",
      "conductor": "claude",
      "autor_del_artefacto": "claude",
      "worker": "claude",
      "relaciones": {"worker_vs_conductor": "same_family", "worker_vs_autor": "same_family"},
      "cuenta_como_evidencia_independiente": false
    }
  ],
  "topologia": {"intentos": 4, "single_voice": 1, "cross_vs_conductor": 2, "cross_vs_autor": 2, "evidencia_independiente": 2, "familias_presentes": ["claude", "codex"]}
}
```

## Inventario de defectos

Los defectos ya verificados, cada uno con ubicación, naturaleza y fase de corrección. El mínimo son
**seis y se comparan por identidad**: sustituir uno por otro conservando el total es exactamente lo
que un conteo no ve. Puede contener más y no menos.

Sus **identidades** son las que nombra el criterio; su ubicación, su naturaleza y su fase son
**sintéticas**, porque adjudicar dónde vive cada defecto es trabajo de la task que materializa el
inventario, y congelarlas acá le impondría una adjudicación que su task no tomó.

```json
{
  "defectos": [
    {
      "id": "instruccion-del-repositorio-contra-guarda",
      "descripcion": "la instrucción del repositorio que contradice el estado de una guarda",
      "ubicacion": "sintetico/instrucciones-del-corpus.md#estado-de-las-guardas",
      "naturaleza": "documental: la instrucción y el estado real de la guarda dicen cosas distintas, y quien la lee la aplica al revés",
      "fase": "Fase 0"
    },
    {
      "id": "conteo-de-skills-del-manifest",
      "descripcion": "la discrepancia entre el número declarado de skills del manifest y su tabla",
      "ubicacion": "sintetico/manifest-del-corpus.md#tabla-de-skills",
      "naturaleza": "documental: el total en prosa y la cantidad de filas de la tabla no coinciden",
      "fase": "Fase 0"
    },
    {
      "id": "frontera-que-nombra-skill-inexistente",
      "descripcion": "la regla de fronteras que nombra una skill inexistente",
      "ubicacion": "sintetico/instrucciones-del-corpus.md#fronteras-entre-skills",
      "naturaleza": "documental: la frontera reparte trabajo a un nombre que no tiene skill detrás, así que ese trabajo no tiene dueño",
      "fase": "Fase 0"
    },
    {
      "id": "registro-historico-rechazado-por-su-guarda",
      "descripcion": "los archivos del registro histórico que su propia guarda rechaza",
      "ubicacion": "sintetico/registro-del-corpus.md#entradas-adjudicadas",
      "naturaleza": "instrumental: la guarda que valida el registro pone en rojo entradas que el propio registro contiene",
      "fase": "Fase 1"
    },
    {
      "id": "familia-dura-con-override-explicito",
      "descripcion": "la regla de familia declarada dura que a la vez admite override explícito",
      "ubicacion": "sintetico/politica-del-corpus.md#regla-de-familia",
      "naturaleza": "doctrinal: la regla se declara innegociable y su propio texto describe cómo negociarla",
      "fase": "Fase 2"
    },
    {
      "id": "sede-del-fan-out-vs-prompt",
      "descripcion": "la divergencia entre la sede del fan-out por repo y el prompt con que ese fan-out despacha",
      "ubicacion": "sintetico/orquestador-del-corpus.md#fan-out-por-repo",
      "naturaleza": "instrumental: la sede declara un contrato y el prompt despacha con otro, así que el worker cumple el que nadie declaró",
      "fase": "Fase 1"
    }
  ]
}
```
