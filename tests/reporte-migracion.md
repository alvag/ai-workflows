# Reporte de migración: snapshot dual

El commit `5e4098dcc2d7c6ba4568b584ade64de36330b4a0` sella el árbol irrepetible donde coexisten el arnés histórico, su corpus y los 37 ports.
El tag anotado `migracion/snapshot-dual` lo ancla fuera de la historia de entrega. Su publicación pertenece a T22.

- Base histórica: `5013b4589d5b6429f9705539268eb0d8ac7ae3fc`
- Árbol sellado: `39faa047a6318d1d89eb23fa53717c13665ecbbd`
- Pares comparados: **397**
- Divergencias: **0**
- Fixtures de `contrato-cadena`: **11**, con **17** hashes declarados recalculados

## Hashes de las implementaciones

| Matriz | Implementación vieja | Implementación nueva |
|---|---|---|
| `clarificacion-completa` | `sha256:649223a144fa1380256ce9685510e4e845abe5f410f776d9685e9cc77909e0e9` | `sha256:b49744ff5fd7192d39d7ee3db3c93be4c91c57b23f2d4e2b08bea6df921f6339` |
| `cobertura-ac-fila` | `sha256:0297c22811b7d6dcffb63e3443f036e3255a89bbbd3bd89261ea6afa68d6c0e6` | `sha256:128047ee211a936ef7f201b786d43702726344c80dd8a16734b3d5ffe3e5f082` |
| `contrato-baseline` | `sha256:ab2053287e19cf1549d2fc1c7150c6840e215b52e500856eb98bebfa784e94ce` | `sha256:2fc91725c18e18aa0814523c180d9b7a030124d676960110ed1271117e3bfc7a` |
| `contrato-cadena` | `sha256:4c58f33a967b0565d86bec020e08af7a5e0621993db67c449a2710845ea218ed` | `sha256:b12627169fb6d51bb40568295ae418440e3ec1002986e0e315c49d317a095ac5` |
| `contrato-cobertura` | `sha256:0be415d3ef3891e7836cedfe19984e2ee1b812968046d177e092ee6233567891` | `sha256:aeff20f0b7a467afc4389b26b92a8570645ed0d76b10a806741a86483a81a8a0` |
| `contrato-esquema` | `sha256:56a65cf4120dfd4e7949edefcfd79328946945f566988985b522a4ecde5b7143` | `sha256:2e84e540ce4c8b96b1b4051395a478154d09288c443c786a6ddaf003fedbdab3` |
| `contrato-invariantes` | `sha256:4ab5d04fe206d0bf884a4449444305d7272c62d03e3facee5e4816c8f897f85b` | `sha256:b9a5043887f7615baeb80737aae888975bac03e447fa3505df8775bd80a1ba87` |
| `cuarto-estado-consumidores` | `sha256:791162751c32f922f88b1297716450a54b7d3ae9f151e265ef1a7ff3277e8646` | `sha256:3b2e7098d953db0ca9a08c39e245adbc1c054322a70fe56d34c7d7c5f4772ee4` |
| `gate-blocked` | `sha256:8ef6d6d7dde322208d12aa3299811243e0eca990ff3477fc245da6c574bca63e` | `sha256:cc28b2ba4d3ba8ecb2577e199f663572ddd5020f822d7692c5edc0e174c649b4` |
| `gate-congelado` | `sha256:00824a75394afc718d2c77533360cf496d1f0cf5bbabc1af2efc7b00080ec74d` | `sha256:6f9ffe83b0de98d4c6baf99e5a05d14b91b8f1e49cf2ab90bf10cd9d64dac1f2` |
| `gate-fase-3` | `sha256:01c6586706d3a6a518fae9a81a0cef6ceb329168be4ba78f270a1294720ee056` | `sha256:2a5828b847dff052ae187a1ee1fe1326d604b6667f4a16ee4763003ce5685d8c` |
| `gate-modo-directo` | `sha256:901ed227d2e0e17c0d4294409168ea27c7aaafa96cd2b0a0cee9ccb93088dca7` | `sha256:00c1984ebea601fe47b62cf37058b543ef95d324c77956908a5b5786d6763be5` |
| `identidades-reintento` | `sha256:43305d71409c453557725eb63306b094df275fb3ffc1c6b5b36fd7f0441d2655` | `sha256:8362313efdd1e771f11475a73c6993eedf9c586a1c5d575b4777b30c071922f6` |
| `integracion-ownership` | `sha256:ea99f9f96098c37015f41eca6154551d25e75b6b7cc5d95f53e0a02fc614bb2f` | `sha256:74eec57912d2776de7c7b067e23bc41d8b5857fdc1954e5c0525ecc4e793f06a` |
| `manifest-resumen` | `sha256:f2c54c85e2d2a7bde8d3fd374b92689b50d7b2117bcc138a7031394624fdd27a` | `sha256:d24e50d9d5f8a5ee693ce1c80a17d026c8c10bc600c44f8a2131aadf83b6bf8a` |
| `manifest-valido` | `sha256:afba043073fdb13d92c4e5f622b930a57987b68a59c1cd2aebcf08cd89edd5b0` | `sha256:f06237186a16a16629d56160740710d1e9b064006b27b57e2af0be1d0f36cc16` |
| `materializacion-contrato` | `sha256:e438069a86ca77b8d7ca1eb65642c3d31e33c8f9031fa868e78d22cae63261a1` | `sha256:071c1aa4de4a12b82511ddb3e083591669da173c5b562713421a38a44f9bb81f` |
| `metaindice` | `sha256:eecdd56ef8221bcd34df9b5835358d2a47e326f4cd9eb3c5df857431e5a781c1` | `sha256:fa022b27e790336099a292196bbcb96e1d137cf1ecc5a048c1e65934e4a56489` |
| `orchestration-contract` | `sha256:1f9e1c7da3a6845ae74b55d490a3c5d2733e7605a8e6947a6b09afd274d46568` | `sha256:3adb25dfebf5161860a3ea88ffa5cd13989295d1d597da9a3d73ccf298eab0ee` |
| `orchestration-model` | `sha256:c014ae5e7c511639cbfec44eb6f6ad9e287aa0c7a05087daeec1583e58d4ee1f` | `sha256:1a3b21d7bba0a3ace600ec97f889dc937c6d13c67418b90c71b14b58094136e0` |
| `orchestration-state` | `sha256:65344302c07113d81f5353af5d35e2875f1e77bd1864ebb7b329f0d1a5de9dd6` | `sha256:4bcf0206a09ba5b8d3a26e3e93c3e6ec4754a9001af3bf740b5f7a0b777fdcf8` |
| `ownership-log` | `sha256:4365eeaee786df8303e5cf51401c075c7618a419f260d54ae8ee942fd9fab96c` | `sha256:ad0a45bc988f26531330fe998095c02028c73a6bde9949e1ce172f49813f0852` |
| `ownership-presupuesto` | `sha256:a767516058c81598544ff1c8d8328f9b25fcbd9bd663ee6277a89112470349c2` | `sha256:f37c994f4c80426cec8930d537b14ce0a1e4d70eedb3c0790d7b43a4026ce2d0` |
| `paquete-versionado` | `sha256:edef5814dbb8e80793b6391449ec3442255896485587658efe4a218ded9da87b` | `sha256:57496f4a3efb2959121f53b912b9c89df325da801991c255d0d0d28e41bba165` |
| `recovery-bloquea` | `sha256:71cf1ccedc7280ed733ead40817397b3c719a6651d8c7e21673f7ac3caf14fa8` | `sha256:b5ef326da8cba99c3e80d697324dcc841c8a1257dcd56b4a56ff866ada9d1429` |
| `resolver-antes-de-preguntar` | `sha256:0577964f7a342477a9ce977cbe20e97788268d0cf3afed4d66b266e0194413aa` | `sha256:55c6becb01c6369eebd93492e5404451ac53a1f89ed7be3754bc328958071a83` |
| `split-paginado` | `sha256:b91d95aa10633a1b4e434598250fd2c528736008161bf36d097e6210da7a1d4a` | `sha256:0e522b71738c64e6caf4baedff3d26c42baafd131450ebafa5cc5d052d2e2447` |
| `takeover-reglas` | `sha256:09d736f757ec217a395a21faa900fbe3e47aca74e14f1a83cc1e649357e34b95` | `sha256:46504f0352470788040d5fdfbbb83e60d03ba61816816eb9a3ba7b26a23ffd3d` |
| `validador-paginado` | `sha256:0dc4578bb352c1de717dd20262c6b5d37f44c15d14a00e447e250ba481b5c72d` | `sha256:bbc40b4cb1fb032b6ffbaa58b60aa471a9ab66f9fc5ff7b59b2f81fc19805a9b` |
| `verify-ejecuta` | `sha256:465a6474aa5675892c25f51e4f40e14957ace9df3dcf98351d1814ff6e8924f8` | `sha256:f8b38a809c2dc725bef60f3bb1574d553696ea39d6221a74adff1401b14671b0` |

## Evidencia recalculable

El bloque JSON registra los 397 IDs y las observaciones vieja y nueva por sus cinco dimensiones. Los bytes normalizados de stdout y artefactos se sellan con SHA-256; eventos, clase y código exacto quedan explícitos.

<!-- evidencia-migracion:inicio -->
```json
{
  "evidence": {
    "chain": {
      "checked_hashes": 17,
      "corpus_path": "scripts/paridad-casos/contrato-cadena/fixtures",
      "fixture_count": 11,
      "fixtures": {
        "hash-alterado": {
          "port_exit": 1,
          "reported_hash_mismatches": [
            [
              1,
              "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
            ]
          ],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "1111111111111111111111111111111111111111111111111111111111111111",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": false,
              "previous_matches": true,
              "version": 1
            }
          ]
        },
        "hash-casing": {
          "port_exit": 1,
          "reported_hash_mismatches": [
            [
              1,
              "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
            ]
          ],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": false,
              "previous_matches": true,
              "version": 1
            }
          ]
        },
        "positivo": {
          "port_exit": 0,
          "reported_hash_mismatches": [],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            },
            {
              "calculated": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "declared": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "declared_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "expected_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "hash_matches": true,
              "previous_matches": true,
              "version": 2
            }
          ]
        },
        "previo-casing": {
          "port_exit": 1,
          "reported_hash_mismatches": [
            [
              2,
              "ad669f16bcb1e5e9e1719f11748a13c60ad22d769ebd2dd77f3537f12b3cf211"
            ]
          ],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            },
            {
              "calculated": "ad669f16bcb1e5e9e1719f11748a13c60ad22d769ebd2dd77f3537f12b3cf211",
              "declared": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "declared_previous": "",
              "expected_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "hash_matches": false,
              "previous_matches": false,
              "version": 2
            }
          ]
        },
        "previo-roto": {
          "port_exit": 1,
          "reported_hash_mismatches": [],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            },
            {
              "calculated": "018f4e9cc269cb553afc55cbc878f1f7065da44667925eaccbaed1642dc813ab",
              "declared": "018f4e9cc269cb553afc55cbc878f1f7065da44667925eaccbaed1642dc813ab",
              "declared_previous": "0000000000000000000000000000000000000000000000000000000000000000",
              "expected_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "hash_matches": true,
              "previous_matches": false,
              "version": 2
            }
          ]
        },
        "serie-impar": {
          "port_exit": 0,
          "reported_hash_mismatches": [],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            },
            {
              "calculated": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "declared": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "declared_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "expected_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "hash_matches": true,
              "previous_matches": true,
              "version": 2
            },
            {
              "calculated": "65075dbfe578ac8c9aab70e4897c2bedce312cde8982f4968496d7fe7a163bcf",
              "declared": "65075dbfe578ac8c9aab70e4897c2bedce312cde8982f4968496d7fe7a163bcf",
              "declared_previous": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "expected_previous": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "hash_matches": true,
              "previous_matches": true,
              "version": 3
            }
          ]
        },
        "serie-par": {
          "port_exit": 0,
          "reported_hash_mismatches": [],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            },
            {
              "calculated": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "declared": "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71",
              "declared_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "expected_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "hash_matches": true,
              "previous_matches": true,
              "version": 2
            }
          ]
        },
        "serie-singleton": {
          "port_exit": 0,
          "reported_hash_mismatches": [],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            }
          ]
        },
        "serie-vacia": {
          "port_exit": 0,
          "reported_hash_mismatches": [],
          "versions": []
        },
        "version-casing": {
          "port_exit": 0,
          "reported_hash_mismatches": [],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            }
          ]
        },
        "version-salteada": {
          "port_exit": 1,
          "reported_hash_mismatches": [],
          "versions": [
            {
              "calculated": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "declared_previous": "",
              "expected_previous": "",
              "hash_matches": true,
              "previous_matches": true,
              "version": 1
            },
            {
              "calculated": "a7b4216eab32ba7240e17e2083a50882314db6f786fdd82362a97c1a9998bc46",
              "declared": "a7b4216eab32ba7240e17e2083a50882314db6f786fdd82362a97c1a9998bc46",
              "declared_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "expected_previous": "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954",
              "hash_matches": true,
              "previous_matches": true,
              "version": 3
            }
          ]
        }
      }
    },
    "dual": {
      "cases": {
        "clarificacion-completa/campo-casing": {
          "new": {
            "artifacts": {
              "informe.md": "sha256:a7d50c9e0b3a135ce9d1480603b16b6b1154952dfbad47b2dd538587897f4625"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "impacto:"
                  ]
                ],
                "id": "campo-faltante"
              }
            ],
            "observation_sha256": "sha256:67c7a0d155aa40de641427c0b30ef494599795b3cd2bd53654e001489374ee17",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "informe.md": "sha256:a7d50c9e0b3a135ce9d1480603b16b6b1154952dfbad47b2dd538587897f4625"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "impacto:"
                  ]
                ],
                "id": "campo-faltante"
              }
            ],
            "observation_sha256": "sha256:67c7a0d155aa40de641427c0b30ef494599795b3cd2bd53654e001489374ee17",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "clarificacion-completa/campo-vacio": {
          "new": {
            "artifacts": {
              "informe.md": "sha256:6fb016f17b81e5fcb5c2efda10c3ba8a467f1e218a231fcd0a06c44a96d213b2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "impacto:"
                  ]
                ],
                "id": "campo-faltante"
              }
            ],
            "observation_sha256": "sha256:d5bff3888e402c6d7898368a804f9a6787e4b73d74338a3ea64fb89c651a8676",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "informe.md": "sha256:6fb016f17b81e5fcb5c2efda10c3ba8a467f1e218a231fcd0a06c44a96d213b2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "impacto:"
                  ]
                ],
                "id": "campo-faltante"
              }
            ],
            "observation_sha256": "sha256:d5bff3888e402c6d7898368a804f9a6787e4b73d74338a3ea64fb89c651a8676",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "clarificacion-completa/detalle-casing": {
          "new": {
            "artifacts": {
              "informe.md": "sha256:ee5f02626632f897e88fea166157a7cc4f5280209d9e752759aaa52f3a707e34"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:1b0b71003b7dc4518719ad734fee1115e9d6299f87d4eaf716ec3e1e0ec6e0da",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "informe.md": "sha256:ee5f02626632f897e88fea166157a7cc4f5280209d9e752759aaa52f3a707e34"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:1b0b71003b7dc4518719ad734fee1115e9d6299f87d4eaf716ec3e1e0ec6e0da",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "clarificacion-completa/indice-casing": {
          "new": {
            "artifacts": {
              "informe.md": "sha256:1498694e94e35629d605208132dc6ad75fcd7011bd19a3aec57d5b05a6ef1502"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-indice"
              }
            ],
            "observation_sha256": "sha256:63169f1cf1ea158023d4b96920eb19c402076b60d6ee246aaaea31a8cd6a3d44",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "informe.md": "sha256:1498694e94e35629d605208132dc6ad75fcd7011bd19a3aec57d5b05a6ef1502"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-indice"
              }
            ],
            "observation_sha256": "sha256:63169f1cf1ea158023d4b96920eb19c402076b60d6ee246aaaea31a8cd6a3d44",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "clarificacion-completa/positivo": {
          "new": {
            "artifacts": {
              "informe.md": "sha256:d6e054ad28df28b9e2c13b95100342be2f3cb9631aa81de10728c1f19dbe92c7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8cc2b1cf77adc3c29a9fd34204305ddf1c5df0b2bde67577c6f603b452bf7b77",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "informe.md": "sha256:d6e054ad28df28b9e2c13b95100342be2f3cb9631aa81de10728c1f19dbe92c7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8cc2b1cf77adc3c29a9fd34204305ddf1c5df0b2bde67577c6f603b452bf7b77",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "clarificacion-completa/sin-seccion-detalle": {
          "new": {
            "artifacts": {
              "informe.md": "sha256:d1fa02c5248075decfb6a4236ce13fba1f3d29c0a742085fe6955dcf4fde6ffe"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:e4272287f09a1459290817508b22530f2b50281a050501ffd7766940113f0000",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "informe.md": "sha256:d1fa02c5248075decfb6a4236ce13fba1f3d29c0a742085fe6955dcf4fde6ffe"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:e4272287f09a1459290817508b22530f2b50281a050501ffd7766940113f0000",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "clarificacion-completa/sin-seccion-indice": {
          "new": {
            "artifacts": {
              "informe.md": "sha256:5462158f4556177d9d5f99b62e8b7fdc47aa60b1b4a4c6e257bb4e319e160f5e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-indice"
              }
            ],
            "observation_sha256": "sha256:c865f41d1ea1d6ff7555c657620f22f16c926f708c528f70ebb9ffedaad0ac9d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "informe.md": "sha256:5462158f4556177d9d5f99b62e8b7fdc47aa60b1b4a4c6e257bb4e319e160f5e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-indice"
              }
            ],
            "observation_sha256": "sha256:c865f41d1ea1d6ff7555c657620f22f16c926f708c528f70ebb9ffedaad0ac9d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cobertura-ac-fila/ac-casing": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:7a5fc25bbfec2c56a9fb4fb692a8a9c3686705187c6cf662752c3e8e6b61189a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-1A"
                  ]
                ],
                "id": "fila-sin-ac"
              },
              {
                "fields": [
                  [
                    "entidades",
                    "AC-1a"
                  ]
                ],
                "id": "ac-sin-fila"
              }
            ],
            "observation_sha256": "sha256:66133176640e2a0057641a9ef200480629736c8e427c3562d29dfb9ad0c7be41",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:7a5fc25bbfec2c56a9fb4fb692a8a9c3686705187c6cf662752c3e8e6b61189a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-1A"
                  ]
                ],
                "id": "fila-sin-ac"
              },
              {
                "fields": [
                  [
                    "entidades",
                    "AC-1a"
                  ]
                ],
                "id": "ac-sin-fila"
              }
            ],
            "observation_sha256": "sha256:66133176640e2a0057641a9ef200480629736c8e427c3562d29dfb9ad0c7be41",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cobertura-ac-fila/ac-huerfano": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:c170f2ebfa73b1e066110b18b543e0aa99605ad3d495b71831cfec614eaecb6e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-2"
                  ]
                ],
                "id": "ac-sin-fila"
              }
            ],
            "observation_sha256": "sha256:4a46ce355cb2e3da712c323d6f72f478851a297f8394bfae69719b2f02110d85",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:c170f2ebfa73b1e066110b18b543e0aa99605ad3d495b71831cfec614eaecb6e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-2"
                  ]
                ],
                "id": "ac-sin-fila"
              }
            ],
            "observation_sha256": "sha256:4a46ce355cb2e3da712c323d6f72f478851a297f8394bfae69719b2f02110d85",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cobertura-ac-fila/fila-huerfana": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:bd155bdf04c174cfde5182c1f712c84948cabde90c6a37c1b5ee50b1488d4f14"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-9"
                  ]
                ],
                "id": "fila-sin-ac"
              }
            ],
            "observation_sha256": "sha256:1cd796afc25a4ca7b7f4f42a3990b8c3243acee471e013a787e68a12eb352115",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:bd155bdf04c174cfde5182c1f712c84948cabde90c6a37c1b5ee50b1488d4f14"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-9"
                  ]
                ],
                "id": "fila-sin-ac"
              }
            ],
            "observation_sha256": "sha256:1cd796afc25a4ca7b7f4f42a3990b8c3243acee471e013a787e68a12eb352115",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cobertura-ac-fila/multi-emision": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:a9f77ceb9894ead63e7226e3ddc1b57ab99393ca07854b6b58576f824641c2ed"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-2"
                  ]
                ],
                "id": "ac-sin-fila"
              },
              {
                "fields": [
                  [
                    "entidades",
                    "AC-9"
                  ]
                ],
                "id": "fila-sin-ac"
              }
            ],
            "observation_sha256": "sha256:46039a1c282265d80010a3d60352bba2ac484a9f4c469ff59fa8918e68ed8ad9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:a9f77ceb9894ead63e7226e3ddc1b57ab99393ca07854b6b58576f824641c2ed"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "AC-2"
                  ]
                ],
                "id": "ac-sin-fila"
              },
              {
                "fields": [
                  [
                    "entidades",
                    "AC-9"
                  ]
                ],
                "id": "fila-sin-ac"
              }
            ],
            "observation_sha256": "sha256:46039a1c282265d80010a3d60352bba2ac484a9f4c469ff59fa8918e68ed8ad9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cobertura-ac-fila/positivo": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:f1bb428eb26c96ef82ac400bd4808a3f7642df65acc2bb2e2beff171b57ac522"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6efc6f964cfa702196a31bb8353348b86d4504cb692c8c59bbbc3180dc9eb95c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:f1bb428eb26c96ef82ac400bd4808a3f7642df65acc2bb2e2beff171b57ac522"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6efc6f964cfa702196a31bb8353348b86d4504cb692c8c59bbbc3180dc9eb95c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/adjudicacion-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:1abcb22d4c1f920ac53761d612601236e06b7f5d11df2702d4e1d7ec26c106a1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "green-sin-adjudicacion"
              }
            ],
            "observation_sha256": "sha256:2331f8892eeea8e2c93b09f23f930dd04a9a48f87239871c28d547bfc22dbf85",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:1abcb22d4c1f920ac53761d612601236e06b7f5d11df2702d4e1d7ec26c106a1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "green-sin-adjudicacion"
              }
            ],
            "observation_sha256": "sha256:2331f8892eeea8e2c93b09f23f930dd04a9a48f87239871c28d547bfc22dbf85",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/campo-columna-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:2cfedc4ca71c9bf8c1775fb2158221a86b6e9fd54e61326ee254018085510816"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "campo-como-columna"
              }
            ],
            "observation_sha256": "sha256:a8544883378cff879ef10e4c397aff5147e1e880f156c7c1647fcfe14dda915d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:2cfedc4ca71c9bf8c1775fb2158221a86b6e9fd54e61326ee254018085510816"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "campo-como-columna"
              }
            ],
            "observation_sha256": "sha256:a8544883378cff879ef10e4c397aff5147e1e880f156c7c1647fcfe14dda915d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/campo-en-la-cabecera": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:4cf1c9277577c29e76679720d3740521fdd3b86d5b21be05eefc694c2ee52c02"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "campo-como-columna"
              }
            ],
            "observation_sha256": "sha256:8acca88d64b6bfd6d6c68b853e7ae604a979bd3997f97e79d6df4d9280929278",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:4cf1c9277577c29e76679720d3740521fdd3b86d5b21be05eefc694c2ee52c02"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "campo-como-columna"
              }
            ],
            "observation_sha256": "sha256:8acca88d64b6bfd6d6c68b853e7ae604a979bd3997f97e79d6df4d9280929278",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/commit-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:fd9ef2e1aa5f6eef5eac0850621f67c310c834826e92825057f0456e951c32f9"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "sin-commit"
              }
            ],
            "observation_sha256": "sha256:64b81b467a20451cfa1857af9ef6a0836d67d9275fd23758bd4b77e48f920db7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:fd9ef2e1aa5f6eef5eac0850621f67c310c834826e92825057f0456e951c32f9"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "sin-commit"
              }
            ],
            "observation_sha256": "sha256:64b81b467a20451cfa1857af9ef6a0836d67d9275fd23758bd4b77e48f920db7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/duplicado-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:278c9568b6f86181e70a99088dcd3b13f6b36c11676eecf6cc18ba11dabfc366"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "V1 v1"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:dbabacb4f72650e8cd63fd0afd928d5247a95e91710a66f3e2b6605d7ed69692",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:278c9568b6f86181e70a99088dcd3b13f6b36c11676eecf6cc18ba11dabfc366"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "V1 v1"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:dbabacb4f72650e8cd63fd0afd928d5247a95e91710a66f3e2b6605d7ed69692",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/duplicado-impar": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:171578fb6eb5c008e4d31ac745b594b7d92bb9a53518720f2316881e61f28e8e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "V1"
                  ]
                ],
                "id": "registro-duplicado"
              },
              {
                "fields": [
                  [
                    "registros",
                    "V1 V2"
                  ],
                  [
                    "tabla",
                    "V1 V2"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:8ad4eb0660c2e39b6c3e03820185aa688460d1c9620b62d9e7cdb92c571601fd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:171578fb6eb5c008e4d31ac745b594b7d92bb9a53518720f2316881e61f28e8e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "V1"
                  ]
                ],
                "id": "registro-duplicado"
              },
              {
                "fields": [
                  [
                    "registros",
                    "V1 V2"
                  ],
                  [
                    "tabla",
                    "V1 V2"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:8ad4eb0660c2e39b6c3e03820185aa688460d1c9620b62d9e7cdb92c571601fd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/duplicado-invalido": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:6afb7385312bf1539da3d26e98714e157cbe29416f0f140ea1f79b6846d6d881"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "V1"
                  ]
                ],
                "id": "registro-duplicado"
              },
              {
                "fields": [
                  [
                    "registros",
                    "V1"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:b24ba469be169648a32a1367b5f440ebcddab13f090baee7b30dee45d7fc098b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:6afb7385312bf1539da3d26e98714e157cbe29416f0f140ea1f79b6846d6d881"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "V1"
                  ]
                ],
                "id": "registro-duplicado"
              },
              {
                "fields": [
                  [
                    "registros",
                    "V1"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:b24ba469be169648a32a1367b5f440ebcddab13f090baee7b30dee45d7fc098b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/duplicado-par": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:cf517b113262554dcaadfdf53cc379cad2b464638b47da50d2982c08e05a66c1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6deb46aedb10f3816aa0052217d680da725443b73f638af00dc38287a804f3f0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:cf517b113262554dcaadfdf53cc379cad2b464638b47da50d2982c08e05a66c1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6deb46aedb10f3816aa0052217d680da725443b73f638af00dc38287a804f3f0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/duplicado-singleton": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:434e4a33f63037ba36d771a54b0df6f659cc85034809c320dba9e5e6cb8cf3d0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:acd7a2c6c5d7d2355f2fcb1b0bac57b66f385e137ae7849a67ecfd0ea14b1ea1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:434e4a33f63037ba36d771a54b0df6f659cc85034809c320dba9e5e6cb8cf3d0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:acd7a2c6c5d7d2355f2fcb1b0bac57b66f385e137ae7849a67ecfd0ea14b1ea1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/duplicado-vacio": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    ""
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:4770f10fd5165e6c60cced69fe17ff57f5aff1b47c4824aa05fd03837f1e4913",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    ""
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:4770f10fd5165e6c60cced69fe17ff57f5aff1b47c4824aa05fd03837f1e4913",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/green-sin-adjudicar": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:2005a2bb9951090ffa65b6b9844ac5dcd66bcb6481a85459ad57b6549172de5b"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "green-sin-adjudicacion"
              }
            ],
            "observation_sha256": "sha256:f9e78e267ee50bf1971ddb9f1d67d2ad1c192021ce3ba44cea00ee6a3e7c2634",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:2005a2bb9951090ffa65b6b9844ac5dcd66bcb6481a85459ad57b6549172de5b"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "green-sin-adjudicacion"
              }
            ],
            "observation_sha256": "sha256:f9e78e267ee50bf1971ddb9f1d67d2ad1c192021ce3ba44cea00ee6a3e7c2634",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/id-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:c890e455d492447c6adc697b7597ad6af2f079c2cbd023cb5885b6ea60112215"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "v1"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:a39fdfc01f4c13687819099c372cfe5aa70d22a710599d2b7abf66b1f967d98e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:c890e455d492447c6adc697b7597ad6af2f079c2cbd023cb5885b6ea60112215"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "v1"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:a39fdfc01f4c13687819099c372cfe5aa70d22a710599d2b7abf66b1f967d98e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/justificacion-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:6ed853b71e445c542c376e4da8a47ca2a19fca8d5b5d36742ee6cb8cc9865000"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "na-sin-justificacion"
              }
            ],
            "observation_sha256": "sha256:c8efc530a44fb12eac733b17283b17dcce9662f199cb31a6b1023714e6fcc06e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:6ed853b71e445c542c376e4da8a47ca2a19fca8d5b5d36742ee6cb8cc9865000"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "na-sin-justificacion"
              }
            ],
            "observation_sha256": "sha256:c8efc530a44fb12eac733b17283b17dcce9662f199cb31a6b1023714e6fcc06e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/na-sin-justificar": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:bf6ec7ac12dd669ea489e51a4de83a01e743cabcaf22c634b6ba4843b54f4160"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "na-sin-justificacion"
              }
            ],
            "observation_sha256": "sha256:6662b37926c02311e73bc8c9bc532cc52abbff73dc153d7944c934211073ed52",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:bf6ec7ac12dd669ea489e51a4de83a01e743cabcaf22c634b6ba4843b54f4160"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "na-sin-justificacion"
              }
            ],
            "observation_sha256": "sha256:6662b37926c02311e73bc8c9bc532cc52abbff73dc153d7944c934211073ed52",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/positivo": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:434e4a33f63037ba36d771a54b0df6f659cc85034809c320dba9e5e6cb8cf3d0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:acd7a2c6c5d7d2355f2fcb1b0bac57b66f385e137ae7849a67ecfd0ea14b1ea1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:434e4a33f63037ba36d771a54b0df6f659cc85034809c320dba9e5e6cb8cf3d0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:acd7a2c6c5d7d2355f2fcb1b0bac57b66f385e137ae7849a67ecfd0ea14b1ea1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/registro-de-mas": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:a6f26d4ce4a9d272a72fa07454a74f986c3c67adad9232bb0bc113c089abfa57"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "V1 V2"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:1b3de24915d544e351f66d17e3c544b069ecaf146279fcf4a5491fb37bab85bd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:a6f26d4ce4a9d272a72fa07454a74f986c3c67adad9232bb0bc113c089abfa57"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "V1 V2"
                  ],
                  [
                    "tabla",
                    "V1"
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:1b3de24915d544e351f66d17e3c544b069ecaf146279fcf4a5491fb37bab85bd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/registro-sin-commit": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:87dd9b3fd4068d83edd78a79759741359be060820b193a02f1a42288e01299b1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "sin-commit"
              }
            ],
            "observation_sha256": "sha256:5b6178f1070e7692659e2abe841d8fa7fe8ac752bed7c83f70ef3fb911340033",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:87dd9b3fd4068d83edd78a79759741359be060820b193a02f1a42288e01299b1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "sin-commit"
              }
            ],
            "observation_sha256": "sha256:5b6178f1070e7692659e2abe841d8fa7fe8ac752bed7c83f70ef3fb911340033",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/tabla-sin-filas": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:2e07912f392aedaf948e1ceaf09a6312c3d86776c729cf33bc3068404c14375e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "V1"
                  ],
                  [
                    "tabla",
                    ""
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:1795778c100b84d230349d490d4e75f93f85c9429e02f1ecfda079606796382f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:2e07912f392aedaf948e1ceaf09a6312c3d86776c729cf33bc3068404c14375e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "V1"
                  ],
                  [
                    "tabla",
                    ""
                  ]
                ],
                "id": "tabla-vs-registros"
              }
            ],
            "observation_sha256": "sha256:1795778c100b84d230349d490d4e75f93f85c9429e02f1ecfda079606796382f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/timestamp-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:9b0ee40e306f09745052fa31806bea792cf95338b4f956b2315228b03cc91fc2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "timestamp-no-iso"
              }
            ],
            "observation_sha256": "sha256:32ac68370fa58d94fec37ae86b871652c1d86bdbc525fa7fe682700cfca82e43",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:9b0ee40e306f09745052fa31806bea792cf95338b4f956b2315228b03cc91fc2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "timestamp-no-iso"
              }
            ],
            "observation_sha256": "sha256:32ac68370fa58d94fec37ae86b871652c1d86bdbc525fa7fe682700cfca82e43",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-baseline/timestamp-invalido": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:4472fb0e1f1c6e3c44a29f9ff939a87c6fadc08419d272ccb5d8e09d8a9489f2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "timestamp-no-iso"
              }
            ],
            "observation_sha256": "sha256:e267e34664036637e337c493cdd2f2df7ac2c2f61c76b54b467f9dd08a4c9357",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:4472fb0e1f1c6e3c44a29f9ff939a87c6fadc08419d272ccb5d8e09d8a9489f2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "id",
                    "V1"
                  ]
                ],
                "id": "timestamp-no-iso"
              }
            ],
            "observation_sha256": "sha256:e267e34664036637e337c493cdd2f2df7ac2c2f61c76b54b467f9dd08a4c9357",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/hash-alterado": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:0a684890c2fc32a79f2f6038b317a77dd3f5464d55d0198bd71d3d8937575141"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declarado",
                    "1111111111111111111111111111111111111111111111111111111111111111"
                  ],
                  [
                    "recalculado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "version",
                    "1"
                  ]
                ],
                "id": "hash-no-coincide"
              }
            ],
            "observation_sha256": "sha256:9e6b80726a911dd40a9433f601048b9626a9e8eed6033a6c496f560a63b20530",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:0a684890c2fc32a79f2f6038b317a77dd3f5464d55d0198bd71d3d8937575141"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declarado",
                    "1111111111111111111111111111111111111111111111111111111111111111"
                  ],
                  [
                    "recalculado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "version",
                    "1"
                  ]
                ],
                "id": "hash-no-coincide"
              }
            ],
            "observation_sha256": "sha256:9e6b80726a911dd40a9433f601048b9626a9e8eed6033a6c496f560a63b20530",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/hash-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:18c5b664cce4ba2d69ea7963254124f22285126783e034762cdb082f6b2596c7"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declarado",
                    "vacío"
                  ],
                  [
                    "recalculado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "version",
                    "1"
                  ]
                ],
                "id": "hash-no-coincide"
              }
            ],
            "observation_sha256": "sha256:26beaccff0c0dc2a7d22b17c3f065d4ebbcacb1b0830895c01eecb352eda6a11",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:18c5b664cce4ba2d69ea7963254124f22285126783e034762cdb082f6b2596c7"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declarado",
                    "vacío"
                  ],
                  [
                    "recalculado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "version",
                    "1"
                  ]
                ],
                "id": "hash-no-coincide"
              }
            ],
            "observation_sha256": "sha256:26beaccff0c0dc2a7d22b17c3f065d4ebbcacb1b0830895c01eecb352eda6a11",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/positivo": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:db3e34ad6ededbd507cfa8e1683834294051621777bc37165e01df6dedcf9e24"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c7aeaf76342cc390975dbf5693339f154397cbb575f975066fa45831f4715e3b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:db3e34ad6ededbd507cfa8e1683834294051621777bc37165e01df6dedcf9e24"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c7aeaf76342cc390975dbf5693339f154397cbb575f975066fa45831f4715e3b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/previo-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:45d9285cf291345975bb0dc065a31803f28cb0d702d9b34c30a620f4c62d657a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declarado",
                    "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71"
                  ],
                  [
                    "recalculado",
                    "ad669f16bcb1e5e9e1719f11748a13c60ad22d769ebd2dd77f3537f12b3cf211"
                  ],
                  [
                    "version",
                    "2"
                  ]
                ],
                "id": "hash-no-coincide"
              },
              {
                "fields": [
                  [
                    "esperado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "previo",
                    "vacío"
                  ],
                  [
                    "version",
                    "2"
                  ]
                ],
                "id": "hash-previo-no-encadena"
              }
            ],
            "observation_sha256": "sha256:5107478b266fcfbe023c6e6cfd54ddfce6923a0e2fa75855ea4ae79c65ecd6b2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:45d9285cf291345975bb0dc065a31803f28cb0d702d9b34c30a620f4c62d657a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declarado",
                    "ce9221a7b5afb3375a284e2aba5555798769b0beaf209820d4797969abe96e71"
                  ],
                  [
                    "recalculado",
                    "ad669f16bcb1e5e9e1719f11748a13c60ad22d769ebd2dd77f3537f12b3cf211"
                  ],
                  [
                    "version",
                    "2"
                  ]
                ],
                "id": "hash-no-coincide"
              },
              {
                "fields": [
                  [
                    "esperado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "previo",
                    "vacío"
                  ],
                  [
                    "version",
                    "2"
                  ]
                ],
                "id": "hash-previo-no-encadena"
              }
            ],
            "observation_sha256": "sha256:5107478b266fcfbe023c6e6cfd54ddfce6923a0e2fa75855ea4ae79c65ecd6b2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/previo-roto": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:896d649631491a80f11b3bba93acb6df91b0743b80a9dc54a893f95ee54464bf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "esperado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "previo",
                    "0000000000000000000000000000000000000000000000000000000000000000"
                  ],
                  [
                    "version",
                    "2"
                  ]
                ],
                "id": "hash-previo-no-encadena"
              }
            ],
            "observation_sha256": "sha256:a891edbebcc243a52a177d4013e2fa5893e7232a6214cf124073d23ee9de802d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:896d649631491a80f11b3bba93acb6df91b0743b80a9dc54a893f95ee54464bf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "esperado",
                    "a9bce48396b7cd5a648e52095670132e9c19da5bbb94f9a30659befcdb6b1954"
                  ],
                  [
                    "previo",
                    "0000000000000000000000000000000000000000000000000000000000000000"
                  ],
                  [
                    "version",
                    "2"
                  ]
                ],
                "id": "hash-previo-no-encadena"
              }
            ],
            "observation_sha256": "sha256:a891edbebcc243a52a177d4013e2fa5893e7232a6214cf124073d23ee9de802d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/serie-impar": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:ad8edd400a613f012f2832245b97dfb124907707e4cdc4eef5999b71d204cbc3"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:19c7e01192b82d902fe4c93957b58f55095859285d69bab53de531ba6707757c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:ad8edd400a613f012f2832245b97dfb124907707e4cdc4eef5999b71d204cbc3"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:19c7e01192b82d902fe4c93957b58f55095859285d69bab53de531ba6707757c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/serie-par": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:db3e34ad6ededbd507cfa8e1683834294051621777bc37165e01df6dedcf9e24"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c7aeaf76342cc390975dbf5693339f154397cbb575f975066fa45831f4715e3b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:db3e34ad6ededbd507cfa8e1683834294051621777bc37165e01df6dedcf9e24"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c7aeaf76342cc390975dbf5693339f154397cbb575f975066fa45831f4715e3b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/serie-singleton": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:38de3850f8e9f2b2d10a17725aed88a3f142db3dd216f12088b26b30fd2a3df9"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:455f7932b75ed5d321387f252263b3ab0df55d22a6a5c5aafae9eb3bf778d5b4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:38de3850f8e9f2b2d10a17725aed88a3f142db3dd216f12088b26b30fd2a3df9"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:455f7932b75ed5d321387f252263b3ab0df55d22a6a5c5aafae9eb3bf778d5b4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/serie-vacia": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:790ca15e345f046a5cab2629a2ac203fe9517a653d3b47bff095aecebebe637d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:571e980d8f01568fe18a20d7384d2951efde337dec39e758af0bdc1be8c6f88d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:790ca15e345f046a5cab2629a2ac203fe9517a653d3b47bff095aecebebe637d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:571e980d8f01568fe18a20d7384d2951efde337dec39e758af0bdc1be8c6f88d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/version-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:77ef3775de505d9174b43d14589b3d63ed985526b84ee3aceedbd1a2b04672d7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:dc2e29cbd9a05dbf5ab76097a669eb39b5d0796ce1db37b261c7f49fea87e05b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:77ef3775de505d9174b43d14589b3d63ed985526b84ee3aceedbd1a2b04672d7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:dc2e29cbd9a05dbf5ab76097a669eb39b5d0796ce1db37b261c7f49fea87e05b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cadena/version-salteada": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:a6fa721e46d4e10f8e004228e89f50eb130136c85ce43427e79fe88362285072"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "esperada",
                    "2"
                  ],
                  [
                    "vino",
                    "3"
                  ]
                ],
                "id": "versiones-no-consecutivas"
              }
            ],
            "observation_sha256": "sha256:5083044ca8617f8d41a923640d828c2e66faa94b25d89089a3bd4ea194659f09",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:a6fa721e46d4e10f8e004228e89f50eb130136c85ce43427e79fe88362285072"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "esperada",
                    "2"
                  ],
                  [
                    "vino",
                    "3"
                  ]
                ],
                "id": "versiones-no-consecutivas"
              }
            ],
            "observation_sha256": "sha256:5083044ca8617f8d41a923640d828c2e66faa94b25d89089a3bd4ea194659f09",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cobertura/case-mixto": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:becff4d3fc11e30fade5c69348c66c41cd2232c4c140eb1f094fe7e711d886d7",
              "reqs.txt": "sha256:e184bae4ce7b4bf189edbb464a79196fe005e9bbe677fdf83927cee359d6569d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "A C"
                  ]
                ],
                "id": "requisito-sin-fila"
              },
              {
                "fields": [
                  [
                    "entidades",
                    "B a"
                  ]
                ],
                "id": "fila-sin-requisito"
              }
            ],
            "observation_sha256": "sha256:3f2d8f2839d81e5b047e359ab42244b2bf23e7c65b52456374432389f5f077fa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:becff4d3fc11e30fade5c69348c66c41cd2232c4c140eb1f094fe7e711d886d7",
              "reqs.txt": "sha256:e184bae4ce7b4bf189edbb464a79196fe005e9bbe677fdf83927cee359d6569d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "A C"
                  ]
                ],
                "id": "requisito-sin-fila"
              },
              {
                "fields": [
                  [
                    "entidades",
                    "B a"
                  ]
                ],
                "id": "fila-sin-requisito"
              }
            ],
            "observation_sha256": "sha256:3f2d8f2839d81e5b047e359ab42244b2bf23e7c65b52456374432389f5f077fa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cobertura/fila-sin-requisito": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:a9b3b6abc56326a14c0f037e2a81c7a587bd861a956d1c7881f38a29a4c58018",
              "reqs.txt": "sha256:06f961b802bc46ee168555f066d28f4f0e9afdf3f88174c1ee6f9de004fc30a0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "Z"
                  ]
                ],
                "id": "fila-sin-requisito"
              }
            ],
            "observation_sha256": "sha256:a9d349d6ff55a5792fe23e85fead3c8696b18e628f717792b4264b88cf7f8a95",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:a9b3b6abc56326a14c0f037e2a81c7a587bd861a956d1c7881f38a29a4c58018",
              "reqs.txt": "sha256:06f961b802bc46ee168555f066d28f4f0e9afdf3f88174c1ee6f9de004fc30a0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "Z"
                  ]
                ],
                "id": "fila-sin-requisito"
              }
            ],
            "observation_sha256": "sha256:a9d349d6ff55a5792fe23e85fead3c8696b18e628f717792b4264b88cf7f8a95",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cobertura/positivo": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:d2bd813f113d6d5f57c466abd1bc96c098063687375690f76a7d7432133e26eb",
              "reqs.txt": "sha256:e184bae4ce7b4bf189edbb464a79196fe005e9bbe677fdf83927cee359d6569d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:edad66470f488114669221a5e8c50b6713efa68ccd0bc7a9abe59786b1a1f862",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:d2bd813f113d6d5f57c466abd1bc96c098063687375690f76a7d7432133e26eb",
              "reqs.txt": "sha256:e184bae4ce7b4bf189edbb464a79196fe005e9bbe677fdf83927cee359d6569d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:edad66470f488114669221a5e8c50b6713efa68ccd0bc7a9abe59786b1a1f862",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-cobertura/requisito-sin-fila": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:c9bcdc712acc5da4053b617c379ec8cac67a19e71a77e22f66f0b7ff7b449b4d",
              "reqs.txt": "sha256:e184bae4ce7b4bf189edbb464a79196fe005e9bbe677fdf83927cee359d6569d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "C"
                  ]
                ],
                "id": "requisito-sin-fila"
              }
            ],
            "observation_sha256": "sha256:70121423a8f19933cbda0581b773f4315189e4e58b35eb06d6c6fd58a0f2b8f8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:c9bcdc712acc5da4053b617c379ec8cac67a19e71a77e22f66f0b7ff7b449b4d",
              "reqs.txt": "sha256:e184bae4ce7b4bf189edbb464a79196fe005e9bbe677fdf83927cee359d6569d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "entidades",
                    "C"
                  ]
                ],
                "id": "requisito-sin-fila"
              }
            ],
            "observation_sha256": "sha256:70121423a8f19933cbda0581b773f4315189e4e58b35eb06d6c6fd58a0f2b8f8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/baseline-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:f0f28a50f3beec6cd1c39332b56d3a74ccf7636f27a22f7b98593705704d24c2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Baseline=red"
                  ]
                ],
                "id": "enum-baseline"
              }
            ],
            "observation_sha256": "sha256:d2bf855d08db8497a5b9d50fca855166800a71095f0ca5f52f1ccbd1550454d9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:f0f28a50f3beec6cd1c39332b56d3a74ccf7636f27a22f7b98593705704d24c2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Baseline=red"
                  ]
                ],
                "id": "enum-baseline"
              }
            ],
            "observation_sha256": "sha256:d2bf855d08db8497a5b9d50fca855166800a71095f0ca5f52f1ccbd1550454d9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/baseline-fuera-del-enum": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:53cff10d34969e36925dd406e439dc0aa6796674c6e8170deea9d1ca6c83c3fa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Baseline=AMARILLO"
                  ]
                ],
                "id": "enum-baseline"
              }
            ],
            "observation_sha256": "sha256:ba8881c2040dd27bff79f38ab385c38d633cf709a11ee6672f104368cf111742",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:53cff10d34969e36925dd406e439dc0aa6796674c6e8170deea9d1ca6c83c3fa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Baseline=AMARILLO"
                  ]
                ],
                "id": "enum-baseline"
              }
            ],
            "observation_sha256": "sha256:ba8881c2040dd27bff79f38ab385c38d633cf709a11ee6672f104368cf111742",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/cabecera-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:f7e0622233084ec2616e20fb83b68022d21589fcab59e80ccfc94ee52596fc40"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "id : Baseline=Baseline"
                  ]
                ],
                "id": "enum-baseline"
              },
              {
                "fields": [
                  [
                    "filas",
                    "id : Evidencia=Evidencia"
                  ]
                ],
                "id": "enum-evidencia"
              },
              {
                "fields": [],
                "id": "cabecera-no-normativa"
              }
            ],
            "observation_sha256": "sha256:05145c9d6c92a0c40f7857012ff6de1caeedfa2d5a3efcfe40707c910adcdf96",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:f7e0622233084ec2616e20fb83b68022d21589fcab59e80ccfc94ee52596fc40"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "id : Baseline=Baseline"
                  ]
                ],
                "id": "enum-baseline"
              },
              {
                "fields": [
                  [
                    "filas",
                    "id : Evidencia=Evidencia"
                  ]
                ],
                "id": "enum-evidencia"
              },
              {
                "fields": [],
                "id": "cabecera-no-normativa"
              }
            ],
            "observation_sha256": "sha256:05145c9d6c92a0c40f7857012ff6de1caeedfa2d5a3efcfe40707c910adcdf96",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/cabecera-distinta": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:6e649286147c33bb1e2f6d2699186b7ed6da7f89f88cb016484ae32124c73d30"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "cabecera-no-normativa"
              }
            ],
            "observation_sha256": "sha256:8b3cf780533a002a2ed5d768f37ac952ef0d63b4033b181aad6d5cbf0393f1bb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:6e649286147c33bb1e2f6d2699186b7ed6da7f89f88cb016484ae32124c73d30"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "cabecera-no-normativa"
              }
            ],
            "observation_sha256": "sha256:8b3cf780533a002a2ed5d768f37ac952ef0d63b4033b181aad6d5cbf0393f1bb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/cinco-columnas": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:67aa62ad7cc42a824f1c54097866cd52f884527129292162bc0fe761570c333f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : 5 columnas"
                  ]
                ],
                "id": "columnas-fuera-del-esquema"
              }
            ],
            "observation_sha256": "sha256:3a68e42550ec5737fbe61163f3e7bac53acc60bb42ab0016f18e8d7f411b7a2d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:67aa62ad7cc42a824f1c54097866cd52f884527129292162bc0fe761570c333f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : 5 columnas"
                  ]
                ],
                "id": "columnas-fuera-del-esquema"
              }
            ],
            "observation_sha256": "sha256:3a68e42550ec5737fbe61163f3e7bac53acc60bb42ab0016f18e8d7f411b7a2d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/evidencia-casing": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:15e80089e4c95582568cdb65dc2d9534e666e0440ad10e057f9b81bb89cde755"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Evidencia=Test"
                  ]
                ],
                "id": "enum-evidencia"
              }
            ],
            "observation_sha256": "sha256:f70af72f42f48f9aeeaf71b6ea62f2db4b6c3c1a1c6aa25955ada485e38d724e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:15e80089e4c95582568cdb65dc2d9534e666e0440ad10e057f9b81bb89cde755"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Evidencia=Test"
                  ]
                ],
                "id": "enum-evidencia"
              }
            ],
            "observation_sha256": "sha256:f70af72f42f48f9aeeaf71b6ea62f2db4b6c3c1a1c6aa25955ada485e38d724e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/evidencia-fuera-del-enum": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:d5d307d522020813e48c0a2ad73ffb98e0f6dde63461d077fbff84a5da141a43"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Evidencia=revisión"
                  ]
                ],
                "id": "enum-evidencia"
              }
            ],
            "observation_sha256": "sha256:ae44c55d88d285e7ea05abe3dbd44a7534bf5f407a9c2c8da30fcf5eafb7250b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:d5d307d522020813e48c0a2ad73ffb98e0f6dde63461d077fbff84a5da141a43"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : Evidencia=revisión"
                  ]
                ],
                "id": "enum-evidencia"
              }
            ],
            "observation_sha256": "sha256:ae44c55d88d285e7ea05abe3dbd44a7534bf5f407a9c2c8da30fcf5eafb7250b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/positivo": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:325d76a94b20cf768b927701e9c99d712f8185e6e8042b47d3ac9e62bb671eb4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f25eb3d8aebb62ade4a2328469c39f9d4ccf28edfbba186a57cc07a0c904e6f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:325d76a94b20cf768b927701e9c99d712f8185e6e8042b47d3ac9e62bb671eb4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f25eb3d8aebb62ade4a2328469c39f9d4ccf28edfbba186a57cc07a0c904e6f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/seis-columnas": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:2ca4fb9091454f35d794f31be73fe087a19ab793ed6f052eedf0e666b680c378"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4c554840768e95f060b1174b054c9191fde8bdae5788733e2a5314953eaa848f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:2ca4fb9091454f35d794f31be73fe087a19ab793ed6f052eedf0e666b680c378"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4c554840768e95f060b1174b054c9191fde8bdae5788733e2a5314953eaa848f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/sin-filas": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:2aca6c27a02e774274f04ec56e58b3f24749ed8b2170127e5ddbf8f00ef8edf9"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:36bfa5d6cf46d18ff1353d6b8f86c60c7d28e6163663e1ee9a3b45f199b770dc",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:2aca6c27a02e774274f04ec56e58b3f24749ed8b2170127e5ddbf8f00ef8edf9"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:36bfa5d6cf46d18ff1353d6b8f86c60c7d28e6163663e1ee9a3b45f199b770dc",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-esquema/una-sola-columna": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:805139eab49775b12ebc658c1bbd095a0bbef0107d2acf0cfafe54bf290ee5b0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : 1 columnas"
                  ]
                ],
                "id": "columnas-fuera-del-esquema"
              }
            ],
            "observation_sha256": "sha256:63b96cb7add2cec1946a29963640b8f5b5932ba5160bd64d6b51a336c974be62",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:805139eab49775b12ebc658c1bbd095a0bbef0107d2acf0cfafe54bf290ee5b0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1 : 1 columnas"
                  ]
                ],
                "id": "columnas-fuera-del-esquema"
              }
            ],
            "observation_sha256": "sha256:63b96cb7add2cec1946a29963640b8f5b5932ba5160bd64d6b51a336c974be62",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-invariantes/esperado-a-minuscula": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:5748df59f8545f3ca16fdfea1f2dae4b83dfd5c3293258dab44eb3534d7849cf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ],
                  [
                    "ids",
                    "A"
                  ]
                ],
                "id": "requisito-esperado-cambian"
              }
            ],
            "observation_sha256": "sha256:f746b4e4f943bbdf973d9d38e77ef1e867565beea40da4fc444766c376081a2c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:5748df59f8545f3ca16fdfea1f2dae4b83dfd5c3293258dab44eb3534d7849cf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ],
                  [
                    "ids",
                    "A"
                  ]
                ],
                "id": "requisito-esperado-cambian"
              }
            ],
            "observation_sha256": "sha256:f746b4e4f943bbdf973d9d38e77ef1e867565beea40da4fc444766c376081a2c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-invariantes/id-a-minuscula": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:e290544b265fefab0db796a6a61a8fdea127fd011f3b03c10e8287664e1adcd6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ]
                ],
                "id": "ids-cambian"
              }
            ],
            "observation_sha256": "sha256:7f83b7a6f6395610966ab4600bdfe3d1a12226554b719bae5c623dffa6251270",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:e290544b265fefab0db796a6a61a8fdea127fd011f3b03c10e8287664e1adcd6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ]
                ],
                "id": "ids-cambian"
              }
            ],
            "observation_sha256": "sha256:7f83b7a6f6395610966ab4600bdfe3d1a12226554b719bae5c623dffa6251270",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-invariantes/id-agregado": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:3c86121bf59bb552970c7b048e38fd10e01bc37311d67c1380c2c0d9be3903ef"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ]
                ],
                "id": "ids-cambian"
              }
            ],
            "observation_sha256": "sha256:8a4b4177d017575a34e3df2eaef50c70447edfbca7d1905e6cf39958b7340bc6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:3c86121bf59bb552970c7b048e38fd10e01bc37311d67c1380c2c0d9be3903ef"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ]
                ],
                "id": "ids-cambian"
              }
            ],
            "observation_sha256": "sha256:8a4b4177d017575a34e3df2eaef50c70447edfbca7d1905e6cf39958b7340bc6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-invariantes/positivo": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:09754c6939540b2b7e6cedda02570a5618a4b1898035eedc3db2c8ed8741b47a"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a89b0ed01b0f963ca81f83891355df2e136ec659cb0ef16b05a148c84f188e0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:09754c6939540b2b7e6cedda02570a5618a4b1898035eedc3db2c8ed8741b47a"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a89b0ed01b0f963ca81f83891355df2e136ec659cb0ef16b05a148c84f188e0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "contrato-invariantes/requisito-cambia": {
          "new": {
            "artifacts": {
              "contrato.md": "sha256:f00074d5fbd2ec9090b4988f922f32bb44fee5d36684a784879a6b1ec2133af0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ],
                  [
                    "ids",
                    "A"
                  ]
                ],
                "id": "requisito-esperado-cambian"
              }
            ],
            "observation_sha256": "sha256:7262de0be9ce4f0d904d452a53be7290f68a600eccb760799ae544cd1c4c2f98",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "contrato.md": "sha256:f00074d5fbd2ec9090b4988f922f32bb44fee5d36684a784879a6b1ec2133af0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "desde",
                    "1"
                  ],
                  [
                    "hasta",
                    "2"
                  ],
                  [
                    "ids",
                    "A"
                  ]
                ],
                "id": "requisito-esperado-cambian"
              }
            ],
            "observation_sha256": "sha256:7262de0be9ce4f0d904d452a53be7290f68a600eccb760799ae544cd1c4c2f98",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/degradacion-heading-casing": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:15dd8719cdd7a3d5d1830ffb905b4f993477904e00f5304d1b70e95b9ad80bf1",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "degradacion-skill"
              }
            ],
            "observation_sha256": "sha256:541a26e9233482a134279cbfa6f9adb8a1c93a715d95c4e7027d676a7b7c552d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:15dd8719cdd7a3d5d1830ffb905b4f993477904e00f5304d1b70e95b9ad80bf1",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "degradacion-skill"
              }
            ],
            "observation_sha256": "sha256:541a26e9233482a134279cbfa6f9adb8a1c93a715d95c4e7027d676a7b7c552d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/degradacion-skill-sin-estado": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:0b30f2df20132e82ecd4dfcefcc379e70670acd37c2b7fa461eab0826f7d5014",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "degradacion-skill"
              }
            ],
            "observation_sha256": "sha256:43582641b9fa058b44ca8be0c61010678a11e18977dfc7d738734318569024a2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:0b30f2df20132e82ecd4dfcefcc379e70670acd37c2b7fa461eab0826f7d5014",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "degradacion-skill"
              }
            ],
            "observation_sha256": "sha256:43582641b9fa058b44ca8be0c61010678a11e18977dfc7d738734318569024a2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/envelope-ref-heading-casing": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:920f526c8ba4f306376ff16d6123dc0850a6d154fa1e72148380884baf04f9d0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-ref"
              }
            ],
            "observation_sha256": "sha256:86d0e8db97d4aa883d01621f764827ff0193e1f940b7918e4239beb01a6c231c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:920f526c8ba4f306376ff16d6123dc0850a6d154fa1e72148380884baf04f9d0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-ref"
              }
            ],
            "observation_sha256": "sha256:86d0e8db97d4aa883d01621f764827ff0193e1f940b7918e4239beb01a6c231c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/envelope-ref-sin-estado": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:ecbf74a0885d436f88e12cec126b4db5797386a5b3078fe4f8f6f1e9f730d729"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-ref"
              }
            ],
            "observation_sha256": "sha256:d146131865313654bd8fbe02868ecf10c700158d0fc148db235331d5e4b214fe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:ecbf74a0885d436f88e12cec126b4db5797386a5b3078fe4f8f6f1e9f730d729"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-ref"
              }
            ],
            "observation_sha256": "sha256:d146131865313654bd8fbe02868ecf10c700158d0fc148db235331d5e4b214fe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/envelope-skill-estado-casing": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:0209024a58f3670c9c6e85df86f01cff96bd670f96e3f50e13010e692ed4a295",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-skill"
              }
            ],
            "observation_sha256": "sha256:fdd4cbbd0d1c6990003cb8ad52b9fa229043f4a41b05245e9d0bb369f2c6429e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:0209024a58f3670c9c6e85df86f01cff96bd670f96e3f50e13010e692ed4a295",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-skill"
              }
            ],
            "observation_sha256": "sha256:fdd4cbbd0d1c6990003cb8ad52b9fa229043f4a41b05245e9d0bb369f2c6429e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/envelope-skill-sin-estado": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:558829f072ec40a8f263deb5907a868b8ed7cd90421e26bae628b97836486a39",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-skill"
              }
            ],
            "observation_sha256": "sha256:6a0759ef76dbe340a45fc8d186ada6fb0bd56cdf29c64d5cb668ae8f27ce1163",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:558829f072ec40a8f263deb5907a868b8ed7cd90421e26bae628b97836486a39",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "envelope-skill"
              }
            ],
            "observation_sha256": "sha256:6a0759ef76dbe340a45fc8d186ada6fb0bd56cdf29c64d5cb668ae8f27ce1163",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/escalera-estado-casing": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:563747a4909665c42534bab7231994c264302f43f443905407fc4ca69a27277d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "escalera-ref"
              }
            ],
            "observation_sha256": "sha256:985b21dadb3fbad872992febafb712323679eef527ec3dbd9d997d904e96c2cb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:563747a4909665c42534bab7231994c264302f43f443905407fc4ca69a27277d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "escalera-ref"
              }
            ],
            "observation_sha256": "sha256:985b21dadb3fbad872992febafb712323679eef527ec3dbd9d997d904e96c2cb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/escalera-sin-estado": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:da1087b6ce98575203d64981e2706bc4d992bbff59ae8b094d5cf959ed50b45c"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "escalera-ref"
              }
            ],
            "observation_sha256": "sha256:4f030b670dd23cdcfbf6bd54f78cd240fcfa777e75248d25a137f8871fddf501",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:da1087b6ce98575203d64981e2706bc4d992bbff59ae8b094d5cf959ed50b45c"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "escalera-ref"
              }
            ],
            "observation_sha256": "sha256:4f030b670dd23cdcfbf6bd54f78cd240fcfa777e75248d25a137f8871fddf501",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "cuarto-estado-consumidores/positivo": {
          "new": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:a0374959d470013f7d3f57fc5ff3919dfb12b05a8c7b0f0cd950db4268942cb1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "SKILL.md": "sha256:cde5533432feea545769180118d424559e4e4b29c3b47f0a7178f694c485634c",
              "reference.md": "sha256:fdb1fdebb9207ca2dfbb8c9c77a92e03e3f39b1c38ba17e55e0b2709467ab3c3"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:a0374959d470013f7d3f57fc5ff3919dfb12b05a8c7b0f0cd950db4268942cb1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-blocked/blocked-al-despachar": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:7e52587ece74db5dd6f2bddae46ca70e2b007f0298e12788f102a0817b1cff6d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1"
                  ]
                ],
                "id": "blocked-y-despacha"
              }
            ],
            "observation_sha256": "sha256:ee037823fe4b6d8d9a102b84651626c1550babf779df462cf1de9919c48c2a58",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:7e52587ece74db5dd6f2bddae46ca70e2b007f0298e12788f102a0817b1cff6d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1"
                  ]
                ],
                "id": "blocked-y-despacha"
              }
            ],
            "observation_sha256": "sha256:ee037823fe4b6d8d9a102b84651626c1550babf779df462cf1de9919c48c2a58",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-blocked/blocked-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:29e824eeb0e2cbb3ebb32562a386183a181822d92780a5d09423e8bed0a84843"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4fa98e9475f1409a52301f80804bbf86a75ba09d9a2b4b4f46f95a3d8012b2e6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:29e824eeb0e2cbb3ebb32562a386183a181822d92780a5d09423e8bed0a84843"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4fa98e9475f1409a52301f80804bbf86a75ba09d9a2b4b4f46f95a3d8012b2e6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-blocked/justificacion-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:f311bd061eee701cf075e58645223d0d612290c4430940c0e288672648b1d7eb"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "- `id: V1` `justificación: NO HAY ENTORNO de CI`"
                  ]
                ],
                "id": "justificado-por-el-entorno"
              }
            ],
            "observation_sha256": "sha256:5ae0e16aa92793dd1b82ae394b0d69dc68bd5cdb87b14ee2ec7e91446b137f5a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:f311bd061eee701cf075e58645223d0d612290c4430940c0e288672648b1d7eb"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "- `id: V1` `justificación: NO HAY ENTORNO de CI`"
                  ]
                ],
                "id": "justificado-por-el-entorno"
              }
            ],
            "observation_sha256": "sha256:5ae0e16aa92793dd1b82ae394b0d69dc68bd5cdb87b14ee2ec7e91446b137f5a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-blocked/justificacion-por-entorno": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:2a7c553d24d5bf628d559479aaf439a218e3105d73a73746e0ff3ac0c30079eb"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "- `id: V1` `justificación: no hay entorno de CI`"
                  ]
                ],
                "id": "justificado-por-el-entorno"
              }
            ],
            "observation_sha256": "sha256:41c7f2536ca331e1c4cb7efacb8b82739477bb8d828db6057fa1c852bc2b9b0c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:2a7c553d24d5bf628d559479aaf439a218e3105d73a73746e0ff3ac0c30079eb"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "registros",
                    "- `id: V1` `justificación: no hay entorno de CI`"
                  ]
                ],
                "id": "justificado-por-el-entorno"
              }
            ],
            "observation_sha256": "sha256:41c7f2536ca331e1c4cb7efacb8b82739477bb8d828db6057fa1c852bc2b9b0c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-blocked/positivo": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:eb72c00bb99f80c43e377a90d1b4b101f0eda4a8e879fd95f1a48c4b0372c1c7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9287d1ef7a3be50bec87a6020f5c11513544e1c058710126e156e4d4eb0e80d8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:eb72c00bb99f80c43e377a90d1b4b101f0eda4a8e879fd95f1a48c4b0372c1c7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9287d1ef7a3be50bec87a6020f5c11513544e1c058710126e156e4d4eb0e80d8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/baseline-blocked": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:950ecd549d0de7b4b8f63ea6c2655c07094190f3f6f16a3a5ade3c0209534582"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1"
                  ]
                ],
                "id": "baseline-sin-resolver"
              }
            ],
            "observation_sha256": "sha256:d2bf250e4596c011c4a97d00fac5f2de43ce8db398c129da407b4b87cf8df0f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:950ecd549d0de7b4b8f63ea6c2655c07094190f3f6f16a3a5ade3c0209534582"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1"
                  ]
                ],
                "id": "baseline-sin-resolver"
              }
            ],
            "observation_sha256": "sha256:d2bf250e4596c011c4a97d00fac5f2de43ce8db398c129da407b4b87cf8df0f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/baseline-espacios": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:18e2ba98edd529ba6c91332ef6747ba6deb0719a0ca64c970556cfc3c0e19c02"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2956331542e29a1c8cd145653e62369630d454df0c59c2e2ce2c93d0f698af67",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:18e2ba98edd529ba6c91332ef6747ba6deb0719a0ca64c970556cfc3c0e19c02"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2956331542e29a1c8cd145653e62369630d454df0c59c2e2ce2c93d0f698af67",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/baseline-vacio": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:ca2b87b200eb15088868355e539dca92a2ca345de5b1f615182dc88fe0de7372"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1"
                  ]
                ],
                "id": "baseline-sin-resolver"
              }
            ],
            "observation_sha256": "sha256:14f4aaad545e175236d279dd1961978935076ed0d63f2cbb8e958483247590fe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:ca2b87b200eb15088868355e539dca92a2ca345de5b1f615182dc88fe0de7372"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "V1"
                  ]
                ],
                "id": "baseline-sin-resolver"
              }
            ],
            "observation_sha256": "sha256:14f4aaad545e175236d279dd1961978935076ed0d63f2cbb8e958483247590fe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/congelar-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:008459ca6fb404a302f7f4876095546fd4cc05746a0cd218fc0f006a4e794688",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "bitacora-sin-congelar"
              }
            ],
            "observation_sha256": "sha256:c136de0faadc77377a79fb476dde9c0646f0d2a61b0f0dd3e224eb9e94f6e1fc",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:008459ca6fb404a302f7f4876095546fd4cc05746a0cd218fc0f006a4e794688",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "bitacora-sin-congelar"
              }
            ],
            "observation_sha256": "sha256:c136de0faadc77377a79fb476dde9c0646f0d2a61b0f0dd3e224eb9e94f6e1fc",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/positivo": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1573ee9a879c3b9c1974a5cc43e6bb7c0b44ce308d559432bf9fe48e6a4fdb52",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1573ee9a879c3b9c1974a5cc43e6bb7c0b44ce308d559432bf9fe48e6a4fdb52",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/sin-congelar": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "bitacora-sin-congelar"
              }
            ],
            "observation_sha256": "sha256:61a3e21a87889bd2e6d23b719bac775ca7dd7f22eaa43a092bfb071645f79fac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:642f7e87ce9cfe7d436c4769dfb2068004001d80f492fa2120d8f557e4cd9ac9",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "bitacora-sin-congelar"
              }
            ],
            "observation_sha256": "sha256:61a3e21a87889bd2e6d23b719bac775ca7dd7f22eaa43a092bfb071645f79fac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/sin-version": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:60994e3a95fc6d39b3b1f082ceee6fc70c3ed2d2533e7ecd000e6d08bac34016"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-tabla"
              }
            ],
            "observation_sha256": "sha256:fd0455b1a3ee8b1b3cee34f9acb13f4b34984be7d3870a6cac4bd2bb171aa1f4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:60994e3a95fc6d39b3b1f082ceee6fc70c3ed2d2533e7ecd000e6d08bac34016"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-tabla"
              }
            ],
            "observation_sha256": "sha256:fd0455b1a3ee8b1b3cee34f9acb13f4b34984be7d3870a6cac4bd2bb171aa1f4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/tabla-impar": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:610e1920e26ced460f233b4c15118cc52722e7c18dd62e74aea780a1c28418d8"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2a082aa7c681feedd4d45f95d631f5d0366a4400979958ec766bf3a63c714077",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:610e1920e26ced460f233b4c15118cc52722e7c18dd62e74aea780a1c28418d8"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2a082aa7c681feedd4d45f95d631f5d0366a4400979958ec766bf3a63c714077",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/tabla-par": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:b0886464d088f44887040978064a59e2d2737936db89eec379463b44f88a9206"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cd0685a20e45cf08f7b2c3d80d7ff2d17c204ba8e110b5e420d1041ea59b1c0c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:b0886464d088f44887040978064a59e2d2737936db89eec379463b44f88a9206"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cd0685a20e45cf08f7b2c3d80d7ff2d17c204ba8e110b5e420d1041ea59b1c0c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/tabla-singleton": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1573ee9a879c3b9c1974a5cc43e6bb7c0b44ce308d559432bf9fe48e6a4fdb52",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:962b73cb7e01dc9993ac0d563ddb3f3f0e435552067b6c98ee79cd619e679e67"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1573ee9a879c3b9c1974a5cc43e6bb7c0b44ce308d559432bf9fe48e6a4fdb52",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/tabla-vacia": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:2e90479ddf684ba8b813e64a825c6f79f461defface5a6b793cfe31828f8e9ae"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-tabla"
              }
            ],
            "observation_sha256": "sha256:52a74d93c4565f66a271e8eb822fa05dcadb88abcae90b77ec1e1df0842a12d2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:2e90479ddf684ba8b813e64a825c6f79f461defface5a6b793cfe31828f8e9ae"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-tabla"
              }
            ],
            "observation_sha256": "sha256:52a74d93c4565f66a271e8eb822fa05dcadb88abcae90b77ec1e1df0842a12d2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-congelado/version-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:9dd73382fe45d6e39a6fec98840cda205de81824a201da1f25a86981a4c1f7e4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-tabla"
              }
            ],
            "observation_sha256": "sha256:3bbf50b03a22e5f63042cb37620d025d37fe02beae5b8e54ee0f60c471d051a0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0dcc2a2c4c827ce8cf62b824736739bd29ea6adbbedf32a31a81ce8d5932c644",
              "contrato.md": "sha256:9dd73382fe45d6e39a6fec98840cda205de81824a201da1f25a86981a4c1f7e4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-tabla"
              }
            ],
            "observation_sha256": "sha256:3bbf50b03a22e5f63042cb37620d025d37fe02beae5b8e54ee0f60c471d051a0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/archivo-inexistente": {
          "new": {
            "artifacts": {
              "otro.md": "sha256:68dab0877bec4208d4c4a501504b77d097b9fd258d74373819499dc651196979"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/skill.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:97b46b6cea3792025c34a284c1d2d444a8cd1fd464e79328289866d8181cf07e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "otro.md": "sha256:68dab0877bec4208d4c4a501504b77d097b9fd258d74373819499dc651196979"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/skill.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:97b46b6cea3792025c34a284c1d2d444a8cd1fd464e79328289866d8181cf07e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/congelado-casing": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:1ce4f0ed273d7331f1a7f471abbdc3f9ccb289e58521d0d60c149b78afee029f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4cb8fdb5914eb20164d6a936c5469355d896ff8696014a7b565035fef0e79af4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:1ce4f0ed273d7331f1a7f471abbdc3f9ccb289e58521d0d60c149b78afee029f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4cb8fdb5914eb20164d6a936c5469355d896ff8696014a7b565035fef0e79af4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/congelado-presente": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:9026be24bcf3903689078bd2f3453b8e8eca4d779223142c0d3fde7a6455173f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "no-revalida-version-vigente"
              }
            ],
            "observation_sha256": "sha256:be9cc136de3dec38dd6d574a199864ec5dde62dbb40f6f68fb62c27c89960a81",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:9026be24bcf3903689078bd2f3453b8e8eca4d779223142c0d3fde7a6455173f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "no-revalida-version-vigente"
              }
            ],
            "observation_sha256": "sha256:be9cc136de3dec38dd6d574a199864ec5dde62dbb40f6f68fb62c27c89960a81",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/gate-apertura-casing": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:41ed27f3e6cb3a4158083ab0f5f48410bf96da0e72d95f4108d0b25d33a23636"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-gate-de-apertura"
              }
            ],
            "observation_sha256": "sha256:b26634e2b6952fd1e65c8bc7bf859a2592a43452a15d607e6d97d871d410bb7b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:41ed27f3e6cb3a4158083ab0f5f48410bf96da0e72d95f4108d0b25d33a23636"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-gate-de-apertura"
              }
            ],
            "observation_sha256": "sha256:b26634e2b6952fd1e65c8bc7bf859a2592a43452a15d607e6d97d871d410bb7b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/no-verificado-casing": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:13b868bb4f01ae69c310f463b5b30b6b24df88b5dbf248c84d01b8979ab37547"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-veredicto-no-verificado"
              }
            ],
            "observation_sha256": "sha256:dc709f70ef69eb07ec401252183ff02206bf4d2640dc322268bba1fcfb097b34",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:13b868bb4f01ae69c310f463b5b30b6b24df88b5dbf248c84d01b8979ab37547"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-veredicto-no-verificado"
              }
            ],
            "observation_sha256": "sha256:dc709f70ef69eb07ec401252183ff02206bf4d2640dc322268bba1fcfb097b34",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/positivo": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:e6d37ed1b24c139b0711abb972fa8a706549f7ec6f7eb7e287487e61204d8994"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2e2bc4ff7a804676196e2a08d2cfbaa2a81d52b1ccdece1668b1d440db1e5202",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:e6d37ed1b24c139b0711abb972fa8a706549f7ec6f7eb7e287487e61204d8994"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2e2bc4ff7a804676196e2a08d2cfbaa2a81d52b1ccdece1668b1d440db1e5202",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/revalida-casing": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:483341631a7956cbdc3512f5e8d5e85aaa9d22d98b13c846a906dbaa30d84917"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "no-revalida-version-vigente"
              }
            ],
            "observation_sha256": "sha256:8fad8f0719d5cd77071d87f351f5cd4fb18d6473f076143053bbf4b867aa6043",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:483341631a7956cbdc3512f5e8d5e85aaa9d22d98b13c846a906dbaa30d84917"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "no-revalida-version-vigente"
              }
            ],
            "observation_sha256": "sha256:8fad8f0719d5cd77071d87f351f5cd4fb18d6473f076143053bbf4b867aa6043",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/sin-gate-apertura": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:a413df7ac0e5f98e42bce2cc3dad20f9418ebfcc2f0f9f727625c13f2f539ee2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-gate-de-apertura"
              }
            ],
            "observation_sha256": "sha256:edb2309bf75da831318818b4421d8239fd9b1bedbe937b3e65eb6af772f26198",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:a413df7ac0e5f98e42bce2cc3dad20f9418ebfcc2f0f9f727625c13f2f539ee2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-gate-de-apertura"
              }
            ],
            "observation_sha256": "sha256:edb2309bf75da831318818b4421d8239fd9b1bedbe937b3e65eb6af772f26198",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/sin-no-verificado": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:7fc18e767423b520da5a6b64bfb4bef8459fa57e80393398b1dc5e927d9df68e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-veredicto-no-verificado"
              }
            ],
            "observation_sha256": "sha256:44c94ed3ecdab7d1bf704280b9ecfefbd1c600d5cb3d5500c88bf7b4fa3bbc06",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:7fc18e767423b520da5a6b64bfb4bef8459fa57e80393398b1dc5e927d9df68e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-veredicto-no-verificado"
              }
            ],
            "observation_sha256": "sha256:44c94ed3ecdab7d1bf704280b9ecfefbd1c600d5cb3d5500c88bf7b4fa3bbc06",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-fase-3/sin-revalida": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:2f0f9e05796ee77a1e11205036e5c95cf1f3b774f331678f7d98216fba501967"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "no-revalida-version-vigente"
              }
            ],
            "observation_sha256": "sha256:703c861c65306d10f9f5fee18c528a3626b04a4426c5f3071247caf9ead7a756",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:2f0f9e05796ee77a1e11205036e5c95cf1f3b774f331678f7d98216fba501967"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "no-revalida-version-vigente"
              }
            ],
            "observation_sha256": "sha256:703c861c65306d10f9f5fee18c528a3626b04a4426c5f3071247caf9ead7a756",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/actor-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:d17b0dc18a1e3a1349045bce4b3b63ec988d2c3e3402ec85e9486ec1a5285b84"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actor",
                    "Conductor"
                  ],
                  [
                    "paso",
                    "derivar-tabla"
                  ]
                ],
                "id": "paso-de-otro-actor"
              }
            ],
            "observation_sha256": "sha256:bd426d8b207393372b493686befcf70782725f0f43aedc37456437f4d3d49432",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:d17b0dc18a1e3a1349045bce4b3b63ec988d2c3e3402ec85e9486ec1a5285b84"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actor",
                    "Conductor"
                  ],
                  [
                    "paso",
                    "derivar-tabla"
                  ]
                ],
                "id": "paso-de-otro-actor"
              }
            ],
            "observation_sha256": "sha256:bd426d8b207393372b493686befcf70782725f0f43aedc37456437f4d3d49432",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/despachar-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:24e5fe623e9389e01e034617dfab13b5733010a278596ca8552580b4b07aea2b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d5444a78fa9dd4a7f1a9d0bb418ab4323d0f99c38b8b0b2eec8c92b8bb24f103",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:24e5fe623e9389e01e034617dfab13b5733010a278596ca8552580b4b07aea2b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d5444a78fa9dd4a7f1a9d0bb418ab4323d0f99c38b8b0b2eec8c92b8bb24f103",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/despacho-sin-congelar": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:a3e44aa24546486906202c35d03eb49e28a118a85c64a4d59442e8013066b1d9"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "despacho-sin-congelar"
              },
              {
                "fields": [],
                "id": "kickoff-no-precede"
              }
            ],
            "observation_sha256": "sha256:638a00e6dba81ac0229d464947b060a557cd126f2bfa58d31a8f36538e861dd6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:a3e44aa24546486906202c35d03eb49e28a118a85c64a4d59442e8013066b1d9"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "despacho-sin-congelar"
              },
              {
                "fields": [],
                "id": "kickoff-no-precede"
              }
            ],
            "observation_sha256": "sha256:638a00e6dba81ac0229d464947b060a557cd126f2bfa58d31a8f36538e861dd6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/kickoff-tarde": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:59c29cd6b7fdbfe1c3d7e95eea2009aa1c924990689f1ddc1cf91995674eadfd"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "kickoff-no-precede"
              }
            ],
            "observation_sha256": "sha256:26edd519205a8a3f078b23e16ba660a02294bf3434d482db45969a4a50d2047d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:59c29cd6b7fdbfe1c3d7e95eea2009aa1c924990689f1ddc1cf91995674eadfd"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "kickoff-no-precede"
              }
            ],
            "observation_sha256": "sha256:26edd519205a8a3f078b23e16ba660a02294bf3434d482db45969a4a50d2047d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/orden-vs-timestamps": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:ac9ce3be974f27bd8c2514327502887ee58bf4cb9597013d07db0166e855666f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "orden-contradice-timestamps"
              }
            ],
            "observation_sha256": "sha256:11d693ab90b6c7ce37959709ec0c2e9fb6542b8df93846aa4b0d820cd93f7706",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:ac9ce3be974f27bd8c2514327502887ee58bf4cb9597013d07db0166e855666f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "orden-contradice-timestamps"
              }
            ],
            "observation_sha256": "sha256:11d693ab90b6c7ce37959709ec0c2e9fb6542b8df93846aa4b0d820cd93f7706",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/otro-actor": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:54e22ac8feb0dc0fbfef98791929793d03a4f692a53007673efcb0aecf85a72c"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actor",
                    "worker"
                  ],
                  [
                    "paso",
                    "derivar-tabla"
                  ]
                ],
                "id": "paso-de-otro-actor"
              }
            ],
            "observation_sha256": "sha256:29034f0da13b1637db8294ca3d4e49df9f7bb13666d0d6c3fd29ed167f7ad57a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:54e22ac8feb0dc0fbfef98791929793d03a4f692a53007673efcb0aecf85a72c"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actor",
                    "worker"
                  ],
                  [
                    "paso",
                    "derivar-tabla"
                  ]
                ],
                "id": "paso-de-otro-actor"
              }
            ],
            "observation_sha256": "sha256:29034f0da13b1637db8294ca3d4e49df9f7bb13666d0d6c3fd29ed167f7ad57a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/paso-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:a19d732e80f976ce23503420b6837ba4b949bbc4d1d2538f80370cbeb0cb2af6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "despacho-sin-congelar"
              },
              {
                "fields": [],
                "id": "kickoff-no-precede"
              }
            ],
            "observation_sha256": "sha256:83dfa60932eeacdc11e5b852ccc8fe7acaf8147eee591bfbf63be41f4b87b81e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:a19d732e80f976ce23503420b6837ba4b949bbc4d1d2538f80370cbeb0cb2af6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "despacho-sin-congelar"
              },
              {
                "fields": [],
                "id": "kickoff-no-precede"
              }
            ],
            "observation_sha256": "sha256:83dfa60932eeacdc11e5b852ccc8fe7acaf8147eee591bfbf63be41f4b87b81e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/positivo": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0ebe158dccd593c27e751bd0ffec0e89be60b4fd2cceaaddd6bb9c82ab0de0b2"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:a045766ad32a875867bc206bf230cea3cada8aef589b65656f9879541ef09c63",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0ebe158dccd593c27e751bd0ffec0e89be60b4fd2cceaaddd6bb9c82ab0de0b2"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:a045766ad32a875867bc206bf230cea3cada8aef589b65656f9879541ef09c63",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "gate-modo-directo/timestamp-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:3c6ecf72b55c75422672214eea81a6c06938194eab1371461caa7247bde0e233"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "orden-contradice-timestamps"
              }
            ],
            "observation_sha256": "sha256:b0b1a828b6343111cb18ecfddd43a8faa71dfd5711c9ed57d394681cefca77a4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:3c6ecf72b55c75422672214eea81a6c06938194eab1371461caa7247bde0e233"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "orden-contradice-timestamps"
              }
            ],
            "observation_sha256": "sha256:b0b1a828b6343111cb18ecfddd43a8faa71dfd5711c9ed57d394681cefca77a4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/identidad-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:c7439a6d9b87a71849432c0ba70586a343cee03667cb6c893fd3a60a8a421a6f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "identidades",
                    "FormatRepair"
                  ]
                ],
                "id": "identidad-desconocida"
              }
            ],
            "observation_sha256": "sha256:9041e51f4c1f3afe9d7bb9c45f9521a8a4132243b12a6532a9118c93ae546af9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:c7439a6d9b87a71849432c0ba70586a343cee03667cb6c893fd3a60a8a421a6f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "identidades",
                    "FormatRepair"
                  ]
                ],
                "id": "identidad-desconocida"
              }
            ],
            "observation_sha256": "sha256:9041e51f4c1f3afe9d7bb9c45f9521a8a4132243b12a6532a9118c93ae546af9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/identidad-inventada": {
          "new": {
            "artifacts": {
              "log.md": "sha256:8e04967cd1aa68a352a71e770e984528b6c542e1390d3cc658aabd7b82fc9778"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "identidades",
                    "retryAttempt"
                  ]
                ],
                "id": "identidad-desconocida"
              }
            ],
            "observation_sha256": "sha256:15d107a7cc664c72e50e9b31d8c0d0faff40e353c4141579bcb8610a1ee077fb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:8e04967cd1aa68a352a71e770e984528b6c542e1390d3cc658aabd7b82fc9778"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "identidades",
                    "retryAttempt"
                  ]
                ],
                "id": "identidad-desconocida"
              }
            ],
            "observation_sha256": "sha256:15d107a7cc664c72e50e9b31d8c0d0faff40e353c4141579bcb8610a1ee077fb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/mismos-ids-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:4926517ae61ecd4fbbdc182859583bb6f14a4641402dd1dce2082a7b025c1128"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "reparacion-sin-mismos-ids"
              }
            ],
            "observation_sha256": "sha256:a6d567e74569264861db2e24c262b366165d5fbdd01c0f5e51ee77c679833032",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:4926517ae61ecd4fbbdc182859583bb6f14a4641402dd1dce2082a7b025c1128"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "reparacion-sin-mismos-ids"
              }
            ],
            "observation_sha256": "sha256:a6d567e74569264861db2e24c262b366165d5fbdd01c0f5e51ee77c679833032",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/positivo": {
          "new": {
            "artifacts": {
              "log.md": "sha256:79f8fbaa00bdd3a7920ffc4945e95fa32f3412e51cf5171e19c17ad7811e6cea"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:876bcd06a38804937153f5bd91f5b71074052a6ca9d7eadf72f697ec423a55b0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:79f8fbaa00bdd3a7920ffc4945e95fa32f3412e51cf5171e19c17ad7811e6cea"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:876bcd06a38804937153f5bd91f5b71074052a6ca9d7eadf72f697ec423a55b0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/reparaciones-impar": {
          "new": {
            "artifacts": {
              "log.md": "sha256:a9187c857788beab3314be6d6f0d4eea496a08ce741eefecb22f3ce1d3feef57"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "3"
                  ]
                ],
                "id": "tope-reparaciones"
              }
            ],
            "observation_sha256": "sha256:76623faaf11561df9938b1cb1aa7f8801b385ad55ad7534e87c4fbd25ee1d75c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:a9187c857788beab3314be6d6f0d4eea496a08ce741eefecb22f3ce1d3feef57"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "3"
                  ]
                ],
                "id": "tope-reparaciones"
              }
            ],
            "observation_sha256": "sha256:76623faaf11561df9938b1cb1aa7f8801b385ad55ad7534e87c4fbd25ee1d75c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/reparaciones-par": {
          "new": {
            "artifacts": {
              "log.md": "sha256:2b4ee4d297e922c78368bd740ad35011d5f186f71fa5d7a38d8fd32d2e94a580"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "2"
                  ]
                ],
                "id": "tope-reparaciones"
              }
            ],
            "observation_sha256": "sha256:c2069aac85963461d9130f1c8ad7bcf2af6f310426be8642c1da2b6c144d9c32",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:2b4ee4d297e922c78368bd740ad35011d5f186f71fa5d7a38d8fd32d2e94a580"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "2"
                  ]
                ],
                "id": "tope-reparaciones"
              }
            ],
            "observation_sha256": "sha256:c2069aac85963461d9130f1c8ad7bcf2af6f310426be8642c1da2b6c144d9c32",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/reparaciones-singleton": {
          "new": {
            "artifacts": {
              "log.md": "sha256:359b4546e6d673a354ddfb98baf27c9f9eb1411a13c463fa4d018a7d6a18fad7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4400be8bfd2edfe252b72e5a1f88cb577d90d7a246713c7bd4f3f72f774cc2c2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:359b4546e6d673a354ddfb98baf27c9f9eb1411a13c463fa4d018a7d6a18fad7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4400be8bfd2edfe252b72e5a1f88cb577d90d7a246713c7bd4f3f72f774cc2c2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/reparaciones-vacio": {
          "new": {
            "artifacts": {
              "log.md": "sha256:6a7dbebd5d298538297cdd65745f02c6012283e9d0d8d86bfcd9e84884ae983b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f500f9db40c0c8d3c9168c097ac6bf0f63de0bf6996522ce706ad1c21b1c52c5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:6a7dbebd5d298538297cdd65745f02c6012283e9d0d8d86bfcd9e84884ae983b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f500f9db40c0c8d3c9168c097ac6bf0f63de0bf6996522ce706ad1c21b1c52c5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "identidades-reintento/sin-mismos-ids": {
          "new": {
            "artifacts": {
              "log.md": "sha256:3221584245dcab79f092a106ef4bfb2ac0fd8f8e2b4e8c294df1e81b89a27bd2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "reparacion-sin-mismos-ids"
              }
            ],
            "observation_sha256": "sha256:284aba24429f584c4a9d4f7247f73e1ef2b400675cd6d84c6f7ace0dc837fdfa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:3221584245dcab79f092a106ef4bfb2ac0fd8f8e2b4e8c294df1e81b89a27bd2"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "reparacion-sin-mismos-ids"
              }
            ],
            "observation_sha256": "sha256:284aba24429f584c4a9d4f7247f73e1ef2b400675cd6d84c6f7ace0dc837fdfa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/agregadores-vacio": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:0d7c71954c5a2ea72d504c0a59a6de90076537ee0e03b0cb26e44b2ef6f9cbd6",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7851a405cbe799ce8173351bd5be859a16003c7d65d1a293b7efdada172d5a0b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:0d7c71954c5a2ea72d504c0a59a6de90076537ee0e03b0cb26e44b2ef6f9cbd6",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7851a405cbe799ce8173351bd5be859a16003c7d65d1a293b7efdada172d5a0b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/archivo-inexistente-manifest": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.yml"
                  ]
                ],
                "id": "arnes-manifest-inexistente"
              }
            ],
            "observation_sha256": "sha256:ddde3c04c5d00d2322cd1a94c6d3cfca630061b40491f43b3f32e0819e8c027f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.yml"
                  ]
                ],
                "id": "arnes-manifest-inexistente"
              }
            ],
            "observation_sha256": "sha256:ddde3c04c5d00d2322cd1a94c6d3cfca630061b40491f43b3f32e0819e8c027f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/archivo-inexistente-plan": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:280fe6cbec23182ae90e7556504166877badb7aa1dad9729ef658d43876faa53",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:280fe6cbec23182ae90e7556504166877badb7aa1dad9729ef658d43876faa53",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/ausente-impar": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:df3652cf7be2e5245d38317bda53b29346dc4638db8f70a36f70755741c859ce",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api participa en AC-1, AC-2, AC-3 y no lo referencia"
                  ],
                  [
                    "hallazgo",
                    "referencia-esperada-ausente"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ac06a09e24aa70db44ae9dc0beabe79f5f934e05f15aefcbfaf1cdd4d87dade1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:df3652cf7be2e5245d38317bda53b29346dc4638db8f70a36f70755741c859ce",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api participa en AC-1, AC-2, AC-3 y no lo referencia"
                  ],
                  [
                    "hallazgo",
                    "referencia-esperada-ausente"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ac06a09e24aa70db44ae9dc0beabe79f5f934e05f15aefcbfaf1cdd4d87dade1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/ausente-par": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:892c5dd1955cdc6b6e36a30303f963b71473c067f01fcb1c9a087bacd55b7cfd",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api participa en AC-1, AC-2 y no lo referencia"
                  ],
                  [
                    "hallazgo",
                    "referencia-esperada-ausente"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:2978a30fb3f4e4c0de1bd69ea11e404823d13fe7c137f0a7c3a016caeb06b08d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:892c5dd1955cdc6b6e36a30303f963b71473c067f01fcb1c9a087bacd55b7cfd",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api participa en AC-1, AC-2 y no lo referencia"
                  ],
                  [
                    "hallazgo",
                    "referencia-esperada-ausente"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:2978a30fb3f4e4c0de1bd69ea11e404823d13fe7c137f0a7c3a016caeb06b08d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/ausente-singleton": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api participa en AC-1 y no lo referencia"
                  ],
                  [
                    "hallazgo",
                    "referencia-esperada-ausente"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:bc207ca98ba3079835221c8d954217abfc391194bef6675b4bd488af51784855",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:244b00754a94d92fe18b054fed6d9d1df87601a5dbb16953f157d345dfb4111b",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api participa en AC-1 y no lo referencia"
                  ],
                  [
                    "hallazgo",
                    "referencia-esperada-ausente"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:bc207ca98ba3079835221c8d954217abfc391194bef6675b4bd488af51784855",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/evidencia-local": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:e25fe654195cb231827da645423c64c31b64d9a1b90b9bf8d6c10d8770c460b2",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [pytest -k ac1] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ee5a5a33a10b544b3227a099721857649cb1736053a4458f469f637b6f64c0a6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:e25fe654195cb231827da645423c64c31b64d9a1b90b9bf8d6c10d8770c460b2",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [pytest -k ac1] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ee5a5a33a10b544b3227a099721857649cb1736053a4458f469f637b6f64c0a6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/fila-equivocada": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:4d7126931dd9f16a58679c439b2ac42e3c5651abf0b927291747dec49dbd8a30",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1 apuntando a [V-G9], y su fila autoritativa es V-G1"
                  ],
                  [
                    "hallazgo",
                    "referencia-a-fila-equivocada"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:27562880f4b7c876ee948889cbe3f52f19a88785de08a1b2ad42edc3201eb146",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:4d7126931dd9f16a58679c439b2ac42e3c5651abf0b927291747dec49dbd8a30",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1 apuntando a [V-G9], y su fila autoritativa es V-G1"
                  ],
                  [
                    "hallazgo",
                    "referencia-a-fila-equivocada"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:27562880f4b7c876ee948889cbe3f52f19a88785de08a1b2ad42edc3201eb146",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/fila-equivocada-casing": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:9f77899554e1546e56891e9f2c5fca9eab45c8630cd1cae4f409056e0391b753",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1 apuntando a [V-g1], y su fila autoritativa es V-G1"
                  ],
                  [
                    "hallazgo",
                    "referencia-a-fila-equivocada"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:d7d0825fd0196cfa1d26fb1dd8c8ec381ff0d8f2e42d1f1555111ef44a44f43d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:9f77899554e1546e56891e9f2c5fca9eab45c8630cd1cae4f409056e0391b753",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1 apuntando a [V-g1], y su fila autoritativa es V-G1"
                  ],
                  [
                    "hallazgo",
                    "referencia-a-fila-equivocada"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:d7d0825fd0196cfa1d26fb1dd8c8ec381ff0d8f2e42d1f1555111ef44a44f43d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/not-applicable": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:14bc21a42cb73774748a09431fe4dede1cbfbb132fc9bde6c9cb387759713141",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api marca NOT_APPLICABLE la fila de AC-1, que borraría una obligación global"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-not-applicable"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ed0f0139d48b0f3437027c2ab6fcbda7d606ebd655dbbb1af57afacfc0d03918",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:14bc21a42cb73774748a09431fe4dede1cbfbb132fc9bde6c9cb387759713141",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api marca NOT_APPLICABLE la fila de AC-1, que borraría una obligación global"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-not-applicable"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ed0f0139d48b0f3437027c2ab6fcbda7d606ebd655dbbb1af57afacfc0d03918",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/not-applicable-casing": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:56ddd29e66c930851fe207814eaeadec0e66ca28d25bebd4c022c8a029f1273f",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [not_applicable] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ce245c536a668e6430df300cce4a35acd5759a121f331ee973dda68332558a77",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:56ddd29e66c930851fe207814eaeadec0e66ca28d25bebd4c022c8a029f1273f",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [not_applicable] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:ce245c536a668e6430df300cce4a35acd5759a121f331ee973dda68332558a77",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/obsoleta-casing": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:ca001ce92467f8c1bfbdce400826419703f29b95e20ebd3fc979dc180f278e71",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [N/A: fase 3] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:5dc08752518783ee74e6249369bef8ad228a281d6d5c033b8fb83a14c6c927f2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:ca001ce92467f8c1bfbdce400826419703f29b95e20ebd3fc979dc180f278e71",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [N/A: fase 3] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:5dc08752518783ee74e6249369bef8ad228a281d6d5c033b8fb83a14c6c927f2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/obsoleta-fase-3": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:79f2be6e5ef1f109e15daeb7fa7811b4bef8832e8bbc4363f13f8c63dcb456f5",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1 con el literal viejo, que anuncia una fase y no un dueño"
                  ],
                  [
                    "hallazgo",
                    "referencia-obsoleta-fase-3"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:546bbdbb075554ff7b903e18492cf5da70648ac4a520b80063060af3f5e820f6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:79f2be6e5ef1f109e15daeb7fa7811b4bef8832e8bbc4363f13f8c63dcb456f5",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1 con el literal viejo, que anuncia una fase y no un dueño"
                  ],
                  [
                    "hallazgo",
                    "referencia-obsoleta-fase-3"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:546bbdbb075554ff7b903e18492cf5da70648ac4a520b80063060af3f5e820f6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/owned-casing": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:775e5c9b30e7e5d9d66fdf29f36046c767b57067a9b93cc8c9a48f91250780fa",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [N/A: Orchestration-Owned] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:1cc668e3f5accea6956d0a5671a68912c17ad9ae33de2cfd3fd10f003af4515f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:775e5c9b30e7e5d9d66fdf29f36046c767b57067a9b93cc8c9a48f91250780fa",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api cierra AC-1 de su lado: evidencia [N/A: Orchestration-Owned] y baseline [N/A: orchestration-owned]"
                  ],
                  [
                    "hallazgo",
                    "fila-integration-con-evidencia-local"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:1cc668e3f5accea6956d0a5671a68912c17ad9ae33de2cfd3fd10f003af4515f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/plan-sin-repo": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:041b5e6706aec67106d5cd12aefaf0a3f5998d9fe7f5de5a894eac763650ef19",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:041b5e6706aec67106d5cd12aefaf0a3f5998d9fe7f5de5a894eac763650ef19"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "arnes-plan-sin-repo"
              }
            ],
            "observation_sha256": "sha256:08e2d60cbffa6fc5ad673f4a130b0d96155c40a17ea6a9e9d96aa058c1a2216b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:041b5e6706aec67106d5cd12aefaf0a3f5998d9fe7f5de5a894eac763650ef19",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:041b5e6706aec67106d5cd12aefaf0a3f5998d9fe7f5de5a894eac763650ef19"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "arnes-plan-sin-repo"
              }
            ],
            "observation_sha256": "sha256:08e2d60cbffa6fc5ad673f4a130b0d96155c40a17ea6a9e9d96aa058c1a2216b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/positivo": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:eb31a1b1967ac8198f45e8753e0be7d38af08b639c977b14407dc0cc723cd154",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:de90f7aaee0d081d99dc869d8dd8f56dae390999b02a9c9cab8e60a15953ee4b",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:eb31a1b1967ac8198f45e8753e0be7d38af08b639c977b14407dc0cc723cd154",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/repo-casing": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:7af6483d57963eda327e49c20280d50c0f05e7bbe36b1aef2b49437afd9940d5",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:195ca5e852430d5c6c6294917b11009de4f98efe52f198d15bcbf4e4c92a3caf",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:7af6483d57963eda327e49c20280d50c0f05e7bbe36b1aef2b49437afd9940d5",
              "web-plan.md": "sha256:435da462f3f80cddba53ba3271fdd4906fa83f2967f6086f6caead801bbcac42"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:195ca5e852430d5c6c6294917b11009de4f98efe52f198d15bcbf4e4c92a3caf",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/sobrante-impar": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:105a3e99b9aa72d440964f15672acc173b9a46ac4a63b331ed378932f81173de",
              "manifest.yml": "sha256:113a872948daa55b3039333daeaf45bdf43f7c5ed78bc2718e1e2555b2174b35",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, AC-2, AC-3, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:f060661a0845ed6900767854133ee8ed3d501773306feba2890098b2df747063",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:105a3e99b9aa72d440964f15672acc173b9a46ac4a63b331ed378932f81173de",
              "manifest.yml": "sha256:113a872948daa55b3039333daeaf45bdf43f7c5ed78bc2718e1e2555b2174b35",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, AC-2, AC-3, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:f060661a0845ed6900767854133ee8ed3d501773306feba2890098b2df747063",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/sobrante-par": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:ae4d7de06bf90660a6c1f3f1f222255e5e0b4a77eee6170253073bd18177fb39",
              "manifest.yml": "sha256:b30137f7eab927addd0c60af1c0ff76a28b846401ee18298b5f38c449e20daae",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, AC-2, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:f6f77d779464a884b533536a32769b4d4eb546015a2d817db7870d62a0e584e7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:ae4d7de06bf90660a6c1f3f1f222255e5e0b4a77eee6170253073bd18177fb39",
              "manifest.yml": "sha256:b30137f7eab927addd0c60af1c0ff76a28b846401ee18298b5f38c449e20daae",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, AC-2, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:f6f77d779464a884b533536a32769b4d4eb546015a2d817db7870d62a0e584e7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "integracion-ownership/sobrante-singleton": {
          "new": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:0d7c71954c5a2ea72d504c0a59a6de90076537ee0e03b0cb26e44b2ef6f9cbd6",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:1acac2cfe621725f576644718a8d2910584a3275cd2284ae13faef8cbbffc5ec",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "api-plan.md": "sha256:fe836e229796405d9f5354355fd4c6242967e7521d36129a5ef2a6fa039058ba",
              "manifest.yml": "sha256:0d7c71954c5a2ea72d504c0a59a6de90076537ee0e03b0cb26e44b2ef6f9cbd6",
              "web-plan.md": "sha256:9217b977583042e07415021beacdc8923872634df423ddd0ef7f8b1c7c9a93d8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo api referencia AC-1, y participating_repos no lo declara participante"
                  ],
                  [
                    "hallazgo",
                    "referencia-en-repo-no-participante"
                  ],
                  [
                    "plan",
                    "{dir}/api-plan.md"
                  ]
                ],
                "id": "integracion"
              }
            ],
            "observation_sha256": "sha256:1acac2cfe621725f576644718a8d2910584a3275cd2284ae13faef8cbbffc5ec",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-resumen/agrupacion-case": {
          "new": {
            "artifacts": {
              "runs/a.json": "sha256:6e9fcd01a5660385e246b7b7ee5314d02125aeeb1fa1b69d51fefbe095a120ca",
              "runs/b.json": "sha256:53d66b2ef84550464323c6afa7e214959b37c96bf024fd545ba7cdda9164bc2d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:b04671f820ca920905404d56439e4182d9f073fbd5462c48be3d57e323d786d3",
            "stdout_sha256": "sha256:2c16538e833051080532bdc7a7b7dd5d06897f3876b8f001338feb99c0bbe33f"
          },
          "old": {
            "artifacts": {
              "runs/a.json": "sha256:6e9fcd01a5660385e246b7b7ee5314d02125aeeb1fa1b69d51fefbe095a120ca",
              "runs/b.json": "sha256:53d66b2ef84550464323c6afa7e214959b37c96bf024fd545ba7cdda9164bc2d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:b04671f820ca920905404d56439e4182d9f073fbd5462c48be3d57e323d786d3",
            "stdout_sha256": "sha256:2c16538e833051080532bdc7a7b7dd5d06897f3876b8f001338feb99c0bbe33f"
          }
        },
        "manifest-resumen/cardinalidad-impar": {
          "new": {
            "artifacts": {
              "runs/a.json": "sha256:78782015f0223acf9134435ed57deea140bd7f05c10eec05c8423a3a3345b185",
              "runs/b.json": "sha256:43688a0d99f2bfce26facf40e1a715523d0f8fb5ef81f4de62a50f7e234d985b",
              "runs/c.json": "sha256:c6fde3bb774196dd1af6b2b6acc8c450bf9b7b54569cebd9cb8c0c8c6c0986dc"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:80e7593ccf84a28e5458137f2745b8ad0ba0e493a56e5181fcd7881a1a81d6b8",
            "stdout_sha256": "sha256:e3663417ae835ff61d880ac3ea60557119ece0b2f4dad86fdd7f352c8e0cdeff"
          },
          "old": {
            "artifacts": {
              "runs/a.json": "sha256:78782015f0223acf9134435ed57deea140bd7f05c10eec05c8423a3a3345b185",
              "runs/b.json": "sha256:43688a0d99f2bfce26facf40e1a715523d0f8fb5ef81f4de62a50f7e234d985b",
              "runs/c.json": "sha256:c6fde3bb774196dd1af6b2b6acc8c450bf9b7b54569cebd9cb8c0c8c6c0986dc"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:80e7593ccf84a28e5458137f2745b8ad0ba0e493a56e5181fcd7881a1a81d6b8",
            "stdout_sha256": "sha256:e3663417ae835ff61d880ac3ea60557119ece0b2f4dad86fdd7f352c8e0cdeff"
          }
        },
        "manifest-resumen/cardinalidad-par": {
          "new": {
            "artifacts": {
              "runs/a.json": "sha256:78782015f0223acf9134435ed57deea140bd7f05c10eec05c8423a3a3345b185",
              "runs/b.json": "sha256:c6fde3bb774196dd1af6b2b6acc8c450bf9b7b54569cebd9cb8c0c8c6c0986dc"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:b26766c2145a31b4e0386735dce867d37947decd84da883298622a9dbaf87b68",
            "stdout_sha256": "sha256:6999351ef92da8cb71feaea93b4ea9562a4176dfe83d37180953dda2b2751b18"
          },
          "old": {
            "artifacts": {
              "runs/a.json": "sha256:78782015f0223acf9134435ed57deea140bd7f05c10eec05c8423a3a3345b185",
              "runs/b.json": "sha256:c6fde3bb774196dd1af6b2b6acc8c450bf9b7b54569cebd9cb8c0c8c6c0986dc"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:b26766c2145a31b4e0386735dce867d37947decd84da883298622a9dbaf87b68",
            "stdout_sha256": "sha256:6999351ef92da8cb71feaea93b4ea9562a4176dfe83d37180953dda2b2751b18"
          }
        },
        "manifest-resumen/positivo": {
          "new": {
            "artifacts": {
              "runs/a.json": "sha256:6e9fcd01a5660385e246b7b7ee5314d02125aeeb1fa1b69d51fefbe095a120ca",
              "runs/b.json": "sha256:de7b8a0076ee6a1ad2b1b454b4c74993d441e57680df031b68391612b5373861"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:38c523d125ffc4b0376ed5f600094b2b5e84a3a026df4707a334c8179826a370",
            "stdout_sha256": "sha256:dc37f6c011ec0fe7b65c4210f35a6af412530333bfd231c0bb2c91b8fd663cd2"
          },
          "old": {
            "artifacts": {
              "runs/a.json": "sha256:6e9fcd01a5660385e246b7b7ee5314d02125aeeb1fa1b69d51fefbe095a120ca",
              "runs/b.json": "sha256:de7b8a0076ee6a1ad2b1b454b4c74993d441e57680df031b68391612b5373861"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:38c523d125ffc4b0376ed5f600094b2b5e84a3a026df4707a334c8179826a370",
            "stdout_sha256": "sha256:dc37f6c011ec0fe7b65c4210f35a6af412530333bfd231c0bb2c91b8fd663cd2"
          }
        },
        "manifest-resumen/singleton": {
          "new": {
            "artifacts": {
              "runs/a.json": "sha256:a5eddf1e4d847f433536e233b66ecc34408b8af24ba8ba16fa3512ab670550c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3be2c450c5998e18d34ba652cb31ba039b386cdd3652e945096e6ae50c5782a1",
            "stdout_sha256": "sha256:7d0336949df8f3964ffee23de4325d1de9fc134e0df8b394edc276ea06aaeeed"
          },
          "old": {
            "artifacts": {
              "runs/a.json": "sha256:a5eddf1e4d847f433536e233b66ecc34408b8af24ba8ba16fa3512ab670550c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3be2c450c5998e18d34ba652cb31ba039b386cdd3652e945096e6ae50c5782a1",
            "stdout_sha256": "sha256:7d0336949df8f3964ffee23de4325d1de9fc134e0df8b394edc276ea06aaeeed"
          }
        },
        "manifest-resumen/skill-vacia": {
          "new": {
            "artifacts": {
              "runs/a.json": "sha256:c5f5cea3e48aac80c8e9643d3dc00810867cd549321cd2f586c967fd98f00428",
              "runs/b.json": "sha256:6e9fcd01a5660385e246b7b7ee5314d02125aeeb1fa1b69d51fefbe095a120ca"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:bdcf466632c9c89d0923b1c398ade539e555c3e274e5b24ff067c438be96e092",
            "stdout_sha256": "sha256:6f0b504a0b7e8e366413330ec682c66ec7762f08ba2aadb3aa14d539fee4e96b"
          },
          "old": {
            "artifacts": {
              "runs/a.json": "sha256:c5f5cea3e48aac80c8e9643d3dc00810867cd549321cd2f586c967fd98f00428",
              "runs/b.json": "sha256:6e9fcd01a5660385e246b7b7ee5314d02125aeeb1fa1b69d51fefbe095a120ca"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:bdcf466632c9c89d0923b1c398ade539e555c3e274e5b24ff067c438be96e092",
            "stdout_sha256": "sha256:6f0b504a0b7e8e366413330ec682c66ec7762f08ba2aadb3aa14d539fee4e96b"
          }
        },
        "manifest-resumen/vacio": {
          "new": {
            "artifacts": {
              "runs/.gitkeep": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6905d5abc9be26182f0bfd016f365fede8813bce00bb15f72e00a37ec493cf05",
            "stdout_sha256": "sha256:1a0e8e92f4a0049e4b682ca5d74b8391636c0f16696f57948b8d8607844b065d"
          },
          "old": {
            "artifacts": {
              "runs/.gitkeep": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6905d5abc9be26182f0bfd016f365fede8813bce00bb15f72e00a37ec493cf05",
            "stdout_sha256": "sha256:1a0e8e92f4a0049e4b682ca5d74b8391636c0f16696f57948b8d8607844b065d"
          }
        },
        "manifest-valido/campo-desconocido-casing": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:844e08d389c6a1e352dd891c16e90617ae8e24cfe54770d94585a9bb5668c48f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "Attempts"
                  ]
                ],
                "id": "clave-desconocida"
              }
            ],
            "observation_sha256": "sha256:03bc05369e6db4351618899e6e96a30a92b61133887ba5b47f281a8fbbb0c82e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:844e08d389c6a1e352dd891c16e90617ae8e24cfe54770d94585a9bb5668c48f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "Attempts"
                  ]
                ],
                "id": "clave-desconocida"
              }
            ],
            "observation_sha256": "sha256:03bc05369e6db4351618899e6e96a30a92b61133887ba5b47f281a8fbbb0c82e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/clave-desconocida": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:bf1bc77c8a944c1fdaecaa84c9af5bbc32ed42c6b3a6d97e90e8f7c1911289ec"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "extra"
                  ]
                ],
                "id": "clave-desconocida"
              }
            ],
            "observation_sha256": "sha256:45ff27fa8ab9289c113ebabe246196cabf3338dd8cf76f1e1f4fac29ebfe2479",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:bf1bc77c8a944c1fdaecaa84c9af5bbc32ed42c6b3a6d97e90e8f7c1911289ec"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "extra"
                  ]
                ],
                "id": "clave-desconocida"
              }
            ],
            "observation_sha256": "sha256:45ff27fa8ab9289c113ebabe246196cabf3338dd8cf76f1e1f4fac29ebfe2479",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/clave-requerida-duplicada": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:9e408a27f401ddf5f17de0c0f57137ee6ca23fb1d65e2a066c38e0ca34df85ac"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ]
                ],
                "id": "clave-duplicada"
              }
            ],
            "observation_sha256": "sha256:05234c6f1748d57ba687b158070afbfc88d9cd8af4c24f83a4081a43792a380b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:9e408a27f401ddf5f17de0c0f57137ee6ca23fb1d65e2a066c38e0ca34df85ac"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ]
                ],
                "id": "clave-duplicada"
              }
            ],
            "observation_sha256": "sha256:05234c6f1748d57ba687b158070afbfc88d9cd8af4c24f83a4081a43792a380b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/duration-decimal": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:2c80e7bb683d3547ce9752fffc4f29754d9f66204dd6a94be44800f1e9ee3fc8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "1.5"
                  ]
                ],
                "id": "duration-invalida"
              }
            ],
            "observation_sha256": "sha256:3131effe88863aab7f83b756ad191f59e2919c153677a664d6732697370c9798",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:2c80e7bb683d3547ce9752fffc4f29754d9f66204dd6a94be44800f1e9ee3fc8"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "1.5"
                  ]
                ],
                "id": "duration-invalida"
              }
            ],
            "observation_sha256": "sha256:3131effe88863aab7f83b756ad191f59e2919c153677a664d6732697370c9798",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/duration-leading-zero": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:4426184bd869ef44a84808f93494a91afd432c24d7d4b94d51e6fa61462b5303"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "json-invalido"
              }
            ],
            "observation_sha256": "sha256:6250a6e9e962ae1c2886be72d7a0d636c0699340a15405420caa3b4ac2ced27c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:4426184bd869ef44a84808f93494a91afd432c24d7d4b94d51e6fa61462b5303"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "json-invalido"
              }
            ],
            "observation_sha256": "sha256:6250a6e9e962ae1c2886be72d7a0d636c0699340a15405420caa3b4ac2ced27c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/duration-negativa": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:ddb6028a3f3a563fa544b73efec6b4dd81b4b95d70736270d07fafa86dd9ae82"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "-1"
                  ]
                ],
                "id": "duration-invalida"
              }
            ],
            "observation_sha256": "sha256:a44d7850750f46bc33f4c2ed0920d5b6f8ac4b6baaaa0f227e9001bd94123ca7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:ddb6028a3f3a563fa544b73efec6b4dd81b4b95d70736270d07fafa86dd9ae82"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "-1"
                  ]
                ],
                "id": "duration-invalida"
              }
            ],
            "observation_sha256": "sha256:a44d7850750f46bc33f4c2ed0920d5b6f8ac4b6baaaa0f227e9001bd94123ca7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/falta-selection": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:b305ff204bf024b7ee2526cfe4c4a813dcb05232174fcdbd7559db2940642b73"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ]
                ],
                "id": "falta-campo"
              }
            ],
            "observation_sha256": "sha256:0942ca3772762958ca19374d6ddf51708d7cea71e89bd54d76117cb4a3d2cd56",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:b305ff204bf024b7ee2526cfe4c4a813dcb05232174fcdbd7559db2940642b73"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ]
                ],
                "id": "falta-campo"
              }
            ],
            "observation_sha256": "sha256:0942ca3772762958ca19374d6ddf51708d7cea71e89bd54d76117cb4a3d2cd56",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/families-escalar": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:5c277279af85511872b426c6b47a238e236739b91bede60fb0d0913a56eee772"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "families-no-lista"
              }
            ],
            "observation_sha256": "sha256:36912f031e07bdd8fd7603f4548d3dc22b8ed6df083fae8355bce73ea9110769",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:5c277279af85511872b426c6b47a238e236739b91bede60fb0d0913a56eee772"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "families-no-lista"
              }
            ],
            "observation_sha256": "sha256:36912f031e07bdd8fd7603f4548d3dc22b8ed6df083fae8355bce73ea9110769",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/families-vacia-valida": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:ba9f2fbee1536470a68d2e8c764a8ef393d215a7f360f04f72774992742bae92"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2115fef75f9ac016552f1fa8f57864bed3fecc92e13cdff85484759d09b6493b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:ba9f2fbee1536470a68d2e8c764a8ef393d215a7f360f04f72774992742bae92"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2115fef75f9ac016552f1fa8f57864bed3fecc92e13cdff85484759d09b6493b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/family-casing": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:c58fba1e0a8142562249dc40f982037ec25d80e183bce6f9fbc3ae8b919cff55"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "familia",
                    "CODEX"
                  ]
                ],
                "id": "family-invalida"
              }
            ],
            "observation_sha256": "sha256:9c33d10ef0857588f61e5729e4f5cfdd38f9fe5729b961ed36ab05d3c07000df",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:c58fba1e0a8142562249dc40f982037ec25d80e183bce6f9fbc3ae8b919cff55"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "familia",
                    "CODEX"
                  ]
                ],
                "id": "family-invalida"
              }
            ],
            "observation_sha256": "sha256:9c33d10ef0857588f61e5729e4f5cfdd38f9fe5729b961ed36ab05d3c07000df",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/family-desconocida": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:ace0ff5dfd20c3245288c8ed4035b5905c4857f8ed41bbb227ca46347aab5bce"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "familia",
                    "gpt"
                  ]
                ],
                "id": "family-invalida"
              }
            ],
            "observation_sha256": "sha256:16a8d766924a2e38b6b27517402bbc51a987e39aed209bde1fb7726b41813b63",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:ace0ff5dfd20c3245288c8ed4035b5905c4857f8ed41bbb227ca46347aab5bce"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "familia",
                    "gpt"
                  ]
                ],
                "id": "family-invalida"
              }
            ],
            "observation_sha256": "sha256:16a8d766924a2e38b6b27517402bbc51a987e39aed209bde1fb7726b41813b63",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/family-no-string": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:c6312b5afc5ff1b5fb717774cc68eab25d4e4f747fb7b86958890d92e8069dbd"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "familia",
                    "<elemento no string>"
                  ]
                ],
                "id": "family-invalida"
              }
            ],
            "observation_sha256": "sha256:2d30cc0d2a3b5c3a43724bc8f54ab422c8f76023637d7484040ae8bbcd3a514e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:c6312b5afc5ff1b5fb717774cc68eab25d4e4f747fb7b86958890d92e8069dbd"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "familia",
                    "<elemento no string>"
                  ]
                ],
                "id": "family-invalida"
              }
            ],
            "observation_sha256": "sha256:2d30cc0d2a3b5c3a43724bc8f54ab422c8f76023637d7484040ae8bbcd3a514e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/json-sin-llave-raiz": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:42333e3e7578d90d0b1afc2b33ae81b587419612a1f9603ce86e48559c1d7319"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "json-invalido"
              }
            ],
            "observation_sha256": "sha256:aba32beaa3882f93bf8dc8081d125131cdaf9b28ccfb7874c0340166a3631fa8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:42333e3e7578d90d0b1afc2b33ae81b587419612a1f9603ce86e48559c1d7319"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "json-invalido"
              }
            ],
            "observation_sha256": "sha256:aba32beaa3882f93bf8dc8081d125131cdaf9b28ccfb7874c0340166a3631fa8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/mode-bogus": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:950ecab95dff9a55599a107266f179f0cf4bf61a8f362dc18f75f900a8d3247c"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "mode"
                  ],
                  [
                    "skill",
                    "cross-review"
                  ],
                  [
                    "valor",
                    "auto"
                  ]
                ],
                "id": "valor-fuera-de-vocabulario"
              }
            ],
            "observation_sha256": "sha256:cc0dfa11035a858557dfd6c63bae1fbdb88e379ec3f1f5c0a90f8afe855a0feb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:950ecab95dff9a55599a107266f179f0cf4bf61a8f362dc18f75f900a8d3247c"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "mode"
                  ],
                  [
                    "skill",
                    "cross-review"
                  ],
                  [
                    "valor",
                    "auto"
                  ]
                ],
                "id": "valor-fuera-de-vocabulario"
              }
            ],
            "observation_sha256": "sha256:cc0dfa11035a858557dfd6c63bae1fbdb88e379ec3f1f5c0a90f8afe855a0feb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/positivo": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:18e12a38ed6a69a4c4e500fd0c0180d4f38b53317fbb6583f64958c27270a59b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9d4adf63cf2f473def190b080fa2fdcef14c6a48c1455cb7c239c31bb2413f26",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:18e12a38ed6a69a4c4e500fd0c0180d4f38b53317fbb6583f64958c27270a59b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9d4adf63cf2f473def190b080fa2fdcef14c6a48c1455cb7c239c31bb2413f26",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/selection-USER-CHOICE": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:6a791646c2b6dc86c5df2ab148ddd541f8bebc3b471e3e957f97dd9d8ef421f0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ],
                  [
                    "skill",
                    "cross-review"
                  ],
                  [
                    "valor",
                    "USER_CHOICE"
                  ]
                ],
                "id": "valor-fuera-de-vocabulario"
              }
            ],
            "observation_sha256": "sha256:dd84f999db0d13c49024fce9bff8db5967ed4bee65cbbb1c316f03320d9a8158",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:6a791646c2b6dc86c5df2ab148ddd541f8bebc3b471e3e957f97dd9d8ef421f0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ],
                  [
                    "skill",
                    "cross-review"
                  ],
                  [
                    "valor",
                    "USER_CHOICE"
                  ]
                ],
                "id": "valor-fuera-de-vocabulario"
              }
            ],
            "observation_sha256": "sha256:dd84f999db0d13c49024fce9bff8db5967ed4bee65cbbb1c316f03320d9a8158",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/selection-bogus": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:51c26d4a271169248e06076f749a1428204357c1b4ce2124fbdc636ca1ad0c69"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ],
                  [
                    "skill",
                    "cross-review"
                  ],
                  [
                    "valor",
                    "bogus"
                  ]
                ],
                "id": "valor-fuera-de-vocabulario"
              }
            ],
            "observation_sha256": "sha256:72fdd3b36290d1128db5b23322a2d3a0a2fd96d9b2558a5264642bafd5788bc3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:51c26d4a271169248e06076f749a1428204357c1b4ce2124fbdc636ca1ad0c69"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "campo",
                    "selection"
                  ],
                  [
                    "skill",
                    "cross-review"
                  ],
                  [
                    "valor",
                    "bogus"
                  ]
                ],
                "id": "valor-fuera-de-vocabulario"
              }
            ],
            "observation_sha256": "sha256:72fdd3b36290d1128db5b23322a2d3a0a2fd96d9b2558a5264642bafd5788bc3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/skill-casing": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:a1e8a68061896eeab04d7b9b513573a739af81c24b550a55079e21e3acc2ecef"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "skill",
                    "Cross-Review"
                  ]
                ],
                "id": "skill-fuera-del-ecosistema"
              }
            ],
            "observation_sha256": "sha256:ab6c7a5caec118b7d3c80d870b2c29f10c0e00b31cc9870d92a0b33f767ab3ac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:a1e8a68061896eeab04d7b9b513573a739af81c24b550a55079e21e3acc2ecef"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "skill",
                    "Cross-Review"
                  ]
                ],
                "id": "skill-fuera-del-ecosistema"
              }
            ],
            "observation_sha256": "sha256:ab6c7a5caec118b7d3c80d870b2c29f10c0e00b31cc9870d92a0b33f767ab3ac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/skill-desconocida": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:39bcd3af04fdc218320fcb33493e38388150d5e5bb10d9cfbabb8207852ea815"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "skill",
                    "bogus"
                  ]
                ],
                "id": "skill-fuera-del-ecosistema"
              }
            ],
            "observation_sha256": "sha256:94c4a11ea880d27db3ec6ff1b05aecf17e55c9b76debffd968b7e6533fc7becd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:39bcd3af04fdc218320fcb33493e38388150d5e5bb10d9cfbabb8207852ea815"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "skill",
                    "bogus"
                  ]
                ],
                "id": "skill-fuera-del-ecosistema"
              }
            ],
            "observation_sha256": "sha256:94c4a11ea880d27db3ec6ff1b05aecf17e55c9b76debffd968b7e6533fc7becd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/started-at-fecha-imposible": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:78ef410d35214ec96d30856bb0f62afc02b4180c2a9fa62ea4c15f7b6317ffbf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "2026-99-99T99:99:99Z"
                  ]
                ],
                "id": "started-at-invalido"
              }
            ],
            "observation_sha256": "sha256:01cca317896593dcac7b9f54f2ec17edbc49d3aea367d7786463457b9394ec82",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:78ef410d35214ec96d30856bb0f62afc02b4180c2a9fa62ea4c15f7b6317ffbf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "2026-99-99T99:99:99Z"
                  ]
                ],
                "id": "started-at-invalido"
              }
            ],
            "observation_sha256": "sha256:01cca317896593dcac7b9f54f2ec17edbc49d3aea367d7786463457b9394ec82",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/started-at-no-utc": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:7f1b5b424e092280045c45c43bc8cc0e05dcbf5edb6402ab9a84b8e80db1db25"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "2026-08-04T07:00:00-03:00"
                  ]
                ],
                "id": "started-at-invalido"
              }
            ],
            "observation_sha256": "sha256:ac1e73b6dcc13657fc1c32b3f75389675e9551b489ee63adca1e9c7355cafa70",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:7f1b5b424e092280045c45c43bc8cc0e05dcbf5edb6402ab9a84b8e80db1db25"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "2026-08-04T07:00:00-03:00"
                  ]
                ],
                "id": "started-at-invalido"
              }
            ],
            "observation_sha256": "sha256:ac1e73b6dcc13657fc1c32b3f75389675e9551b489ee63adca1e9c7355cafa70",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/started-at-z-minuscula": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:81e9e29a840620f9fc4e8c95c332f983c431a403724ca6976c0721796e9d618d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "2026-08-04T10:00:00z"
                  ]
                ],
                "id": "started-at-invalido"
              }
            ],
            "observation_sha256": "sha256:0d5d6dc90d21b9841305c11db4a1ed774525ff02f83a09a7409274c8c54c4282",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:81e9e29a840620f9fc4e8c95c332f983c431a403724ca6976c0721796e9d618d"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "valor",
                    "2026-08-04T10:00:00z"
                  ]
                ],
                "id": "started-at-invalido"
              }
            ],
            "observation_sha256": "sha256:0d5d6dc90d21b9841305c11db4a1ed774525ff02f83a09a7409274c8c54c4282",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "manifest-valido/transport-none": {
          "new": {
            "artifacts": {
              "manifest.json": "sha256:1110e8dd075a4636388ad3e773f6713949f417c7a7544377c73067e26f3b54c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:5ff0c01b75d7c6f25cb5eb703d3947ffe4a5da997019cd687db3e4f470836b36",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "manifest.json": "sha256:1110e8dd075a4636388ad3e773f6713949f417c7a7544377c73067e26f3b54c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:5ff0c01b75d7c6f25cb5eb703d3947ffe4a5da997019cd687db3e4f470836b36",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "materializacion-contrato/cabecera-casing": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:46cae6c745194bdd17830af43b7b200ee84ae58898eb99cc8b2af40cc584f3f3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "cabecera-ausente"
              }
            ],
            "observation_sha256": "sha256:75e3af2673a41172eea5fe04f9ce4f2a32a646b7ddca40e0a61b14dc9efb93a6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:46cae6c745194bdd17830af43b7b200ee84ae58898eb99cc8b2af40cc584f3f3"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "cabecera-ausente"
              }
            ],
            "observation_sha256": "sha256:75e3af2673a41172eea5fe04f9ce4f2a32a646b7ddca40e0a61b14dc9efb93a6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "materializacion-contrato/dialecto-casing": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:b93d833ff4801264f5d4def9d8b6d54a9985ab7bd829f44884028140bd8fb2d6"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c798b641d5e8139c05f499989991cab1735f61825d398d32ec2b3045f35ed64f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:b93d833ff4801264f5d4def9d8b6d54a9985ab7bd829f44884028140bd8fb2d6"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c798b641d5e8139c05f499989991cab1735f61825d398d32ec2b3045f35ed64f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "materializacion-contrato/dialecto-propio": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:25e6319ba987214cb31544e3afb8ae15214cec0b08ec555be3f7e1afd86dea67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "ID Otra cosa"
                  ]
                ],
                "id": "otro-esquema"
              }
            ],
            "observation_sha256": "sha256:7cb722caa3df128fe75f06e2d88806d392f5050da39291666513c5e146bd2129",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:25e6319ba987214cb31544e3afb8ae15214cec0b08ec555be3f7e1afd86dea67"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "filas",
                    "ID Otra cosa"
                  ]
                ],
                "id": "otro-esquema"
              }
            ],
            "observation_sha256": "sha256:7cb722caa3df128fe75f06e2d88806d392f5050da39291666513c5e146bd2129",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "materializacion-contrato/positivo": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:882ad0f4e6158b332509b725548ad9efc78b4f2da9c00d42799348c215be76c1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:495b08d2b84fb2498786152f840db9113747dff35bcbedb4a62336ebdf2c3b5f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:882ad0f4e6158b332509b725548ad9efc78b4f2da9c00d42799348c215be76c1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:495b08d2b84fb2498786152f840db9113747dff35bcbedb4a62336ebdf2c3b5f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "materializacion-contrato/sin-cabecera": {
          "new": {
            "artifacts": {
              "plan.md": "sha256:c109aeb34ecec22b234b8bb78d42db06c3a4ea021d9b3e780aae24c9429b2af1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "cabecera-ausente"
              }
            ],
            "observation_sha256": "sha256:36bca552a505bf2cb68d17b7d8e769727a2a6f46eb73ce716fce1ee04b3b93c7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "plan.md": "sha256:c109aeb34ecec22b234b8bb78d42db06c3a4ea021d9b3e780aae24c9429b2af1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "cabecera-ausente"
              }
            ],
            "observation_sha256": "sha256:36bca552a505bf2cb68d17b7d8e769727a2a6f46eb73ce716fce1ee04b3b93c7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/conteo-impar": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:8ed5c0d5e1739eb3e3f2c16a97cb80cc2429fff617ac73468cc9f0c596a8cff1",
              "salida.md": "sha256:306ff9c2948dec2660999c72f42f487452a4cacddff77be594ba6feb31d701ce"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declara",
                    "2"
                  ],
                  [
                    "real",
                    "3"
                  ],
                  [
                    "ruta",
                    "salida-p01.md"
                  ]
                ],
                "id": "conteo-por-pagina"
              }
            ],
            "observation_sha256": "sha256:05fdbf6c0dc809f7498b56079c21ad74053f9dfa27699bfca7e901a2c79f0dcd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:8ed5c0d5e1739eb3e3f2c16a97cb80cc2429fff617ac73468cc9f0c596a8cff1",
              "salida.md": "sha256:306ff9c2948dec2660999c72f42f487452a4cacddff77be594ba6feb31d701ce"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "declara",
                    "2"
                  ],
                  [
                    "real",
                    "3"
                  ],
                  [
                    "ruta",
                    "salida-p01.md"
                  ]
                ],
                "id": "conteo-por-pagina"
              }
            ],
            "observation_sha256": "sha256:05fdbf6c0dc809f7498b56079c21ad74053f9dfa27699bfca7e901a2c79f0dcd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/conteo-par": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a82cd26ca0cae0201d3d1de81bc8fff88e6308d0838bad02e0ca7d44cecef31",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a82cd26ca0cae0201d3d1de81bc8fff88e6308d0838bad02e0ca7d44cecef31",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/conteo-singleton": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:aed7e61ecfed231fab92d85181e60a3f819ddd9611bc1b6fce31396fd974dd35",
              "salida.md": "sha256:e00029999a976b63766b25d1118a2dda3390b1e8b327b5964c9d20134be94482"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:438c7f295dc0e4ae6c4bb8a968c1c2cc0f4715bdabed7cfef9c91ebf7bfe244c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:aed7e61ecfed231fab92d85181e60a3f819ddd9611bc1b6fce31396fd974dd35",
              "salida.md": "sha256:e00029999a976b63766b25d1118a2dda3390b1e8b327b5964c9d20134be94482"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:438c7f295dc0e4ae6c4bb8a968c1c2cc0f4715bdabed7cfef9c91ebf7bfe244c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/conteo-vacio": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:efcec193de9cfbb8d964e62bd9732e14cd13beb1f45f8dffdce505f7b1382999",
              "salida.md": "sha256:7d5b2604c99aa2ec412bbc27ce5256ea7f2411d7e75b61696c2cfa3057be5d8e"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4e86d638a9708e283688df888efc01fec45fcbde6297ae0884df9e6c74b1488d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:efcec193de9cfbb8d964e62bd9732e14cd13beb1f45f8dffdce505f7b1382999",
              "salida.md": "sha256:7d5b2604c99aa2ec412bbc27ce5256ea7f2411d7e75b61696c2cfa3057be5d8e"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4e86d638a9708e283688df888efc01fec45fcbde6297ae0884df9e6c74b1488d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/duplicado-casing": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:abbdfeafa6be53cff56124b7146c48709c6b155379ceb55c9ad6631560f15842"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f30a958741df11dfedf05cd91e75f82e300fcb99b9f38d941bb87cc018cc6db1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:abbdfeafa6be53cff56124b7146c48709c6b155379ceb55c9ad6631560f15842"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f30a958741df11dfedf05cd91e75f82e300fcb99b9f38d941bb87cc018cc6db1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/duplicados-impar": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:35609ed9fb0e588f434979aed3ef42a876c616c16b8b1f3b933d42e2fcf88826"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-duplicada"
              }
            ],
            "observation_sha256": "sha256:b2747af71b6ec69cf3db875a848c1a7475a266254b4ae2d1005847eca2f0798d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:35609ed9fb0e588f434979aed3ef42a876c616c16b8b1f3b933d42e2fcf88826"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-duplicada"
              }
            ],
            "observation_sha256": "sha256:b2747af71b6ec69cf3db875a848c1a7475a266254b4ae2d1005847eca2f0798d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/duplicados-par": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e9df7cecaf94fb2d4d42aaa9087d06e02c8354d6956c1dfc7f7670a56e944eb0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-duplicada"
              }
            ],
            "observation_sha256": "sha256:2e85509148c15c1ff9ee41cd07249ea21d1f1ead3f3f4d73071d1e11cf4670c8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e9df7cecaf94fb2d4d42aaa9087d06e02c8354d6956c1dfc7f7670a56e944eb0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-duplicada"
              }
            ],
            "observation_sha256": "sha256:2e85509148c15c1ff9ee41cd07249ea21d1f1ead3f3f4d73071d1e11cf4670c8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/duplicados-singleton": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a82cd26ca0cae0201d3d1de81bc8fff88e6308d0838bad02e0ca7d44cecef31",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a82cd26ca0cae0201d3d1de81bc8fff88e6308d0838bad02e0ca7d44cecef31",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/duplicados-vacio": {
          "new": {
            "artifacts": {
              "salida.md": "sha256:6b289726aecbeb88fcde7a684dd0bce41cf8de50921cb768c5be148c9b042f76"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1623a79d2ee92822f42677744c28a370c656723be5bbb494456c17a9e9302aa2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida.md": "sha256:6b289726aecbeb88fcde7a684dd0bce41cf8de50921cb768c5be148c9b042f76"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1623a79d2ee92822f42677744c28a370c656723be5bbb494456c17a9e9302aa2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/huerfana-casing": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:90c470f7575c34ebcd6cea322380177af56e8bf658cfdc01a53cd5326802bdd4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-huerfana"
              }
            ],
            "observation_sha256": "sha256:b93b03f4f4ef25f59a982ecde41d57a1de429a86d4b3f639b1e55b576ec9fe9a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:90c470f7575c34ebcd6cea322380177af56e8bf658cfdc01a53cd5326802bdd4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-huerfana"
              }
            ],
            "observation_sha256": "sha256:b93b03f4f4ef25f59a982ecde41d57a1de429a86d4b3f639b1e55b576ec9fe9a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/ids-casing": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e8fcb231dcd6a54a97f2074dbfcedfc8fee81aadc77150b4eaf723f2201bdaef"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "meta",
                    "E1 e2"
                  ],
                  [
                    "paginas",
                    "E1 E2"
                  ]
                ],
                "id": "ids-meta-vs-paginas"
              }
            ],
            "observation_sha256": "sha256:84b2fb5ae284d3b3c0235eac14b1a0a85fdfebd13919e8ed7e81161ad3a555f1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e8fcb231dcd6a54a97f2074dbfcedfc8fee81aadc77150b4eaf723f2201bdaef"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "meta",
                    "E1 e2"
                  ],
                  [
                    "paginas",
                    "E1 E2"
                  ]
                ],
                "id": "ids-meta-vs-paginas"
              }
            ],
            "observation_sha256": "sha256:84b2fb5ae284d3b3c0235eac14b1a0a85fdfebd13919e8ed7e81161ad3a555f1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/ids-no-coinciden": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:2195a475763a76679f3d9e1f855893753543f26d1611d5e1f19dfe3d345f4a79"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "meta",
                    "E1 E9"
                  ],
                  [
                    "paginas",
                    "E1 E2"
                  ]
                ],
                "id": "ids-meta-vs-paginas"
              }
            ],
            "observation_sha256": "sha256:6aa2ef3a806e9dd1ebf798bb8bc7dee00a74b0ede71bdbab8b0460452fd09c05",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:2195a475763a76679f3d9e1f855893753543f26d1611d5e1f19dfe3d345f4a79"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "meta",
                    "E1 E9"
                  ],
                  [
                    "paginas",
                    "E1 E2"
                  ]
                ],
                "id": "ids-meta-vs-paginas"
              }
            ],
            "observation_sha256": "sha256:6aa2ef3a806e9dd1ebf798bb8bc7dee00a74b0ede71bdbab8b0460452fd09c05",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/pagina-en-disco-no-listada": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida-p02.md": "sha256:10b0a735893dd4fe5afc950f496c241d64d4386a1f4811fe2fb9754d0c8720a7",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p02.md"
                  ]
                ],
                "id": "pagina-huerfana"
              }
            ],
            "observation_sha256": "sha256:b93a7cc75aee331979b95dc80af569bab9db831209e6d36cfecd9cf8d20c640b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida-p02.md": "sha256:10b0a735893dd4fe5afc950f496c241d64d4386a1f4811fe2fb9754d0c8720a7",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p02.md"
                  ]
                ],
                "id": "pagina-huerfana"
              }
            ],
            "observation_sha256": "sha256:b93a7cc75aee331979b95dc80af569bab9db831209e6d36cfecd9cf8d20c640b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/positivo": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a82cd26ca0cae0201d3d1de81bc8fff88e6308d0838bad02e0ca7d44cecef31",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1a82cd26ca0cae0201d3d1de81bc8fff88e6308d0838bad02e0ca7d44cecef31",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/ruta-duplicada": {
          "new": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e9df7cecaf94fb2d4d42aaa9087d06e02c8354d6956c1dfc7f7670a56e944eb0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-duplicada"
              }
            ],
            "observation_sha256": "sha256:2e85509148c15c1ff9ee41cd07249ea21d1f1ead3f3f4d73071d1e11cf4670c8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida-p01.md": "sha256:a39472718d5130b9d45dc1914eb3016588dba39f65c22c51bd278e527bea44e8",
              "salida.md": "sha256:e9df7cecaf94fb2d4d42aaa9087d06e02c8354d6956c1dfc7f7670a56e944eb0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "rutas",
                    "salida-p01.md"
                  ]
                ],
                "id": "pagina-duplicada"
              }
            ],
            "observation_sha256": "sha256:2e85509148c15c1ff9ee41cd07249ea21d1f1ead3f3f4d73071d1e11cf4670c8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/ruta-inexistente": {
          "new": {
            "artifacts": {
              "salida.md": "sha256:065e665b3381883fdfb260946d09c154ac4d0caf60acec30535af46270402789"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ruta",
                    "salida-p09.md"
                  ]
                ],
                "id": "pagina-declarada-no-existe"
              }
            ],
            "observation_sha256": "sha256:e821ff6c9968b08077d1f834c156120a78b9673b665d675f9041bde5da0c3f29",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "salida.md": "sha256:065e665b3381883fdfb260946d09c154ac4d0caf60acec30535af46270402789"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ruta",
                    "salida-p09.md"
                  ]
                ],
                "id": "pagina-declarada-no-existe"
              }
            ],
            "observation_sha256": "sha256:e821ff6c9968b08077d1f834c156120a78b9673b665d675f9041bde5da0c3f29",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "metaindice/sin-metaindice": {
          "new": {
            "artifacts": {
              "otro.md": "sha256:6a3a8bba10fe08ea8ba42722c74af4e0e60cd1fcdfab0737a39e75d9e743c886"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "metaindice-ausente"
              }
            ],
            "observation_sha256": "sha256:d12163d19cbb672b5a8b91910b103d3926c9441747f4d8aaacaec53cd7de4b50",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "otro.md": "sha256:6a3a8bba10fe08ea8ba42722c74af4e0e60cd1fcdfab0737a39e75d9e743c886"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "metaindice-ausente"
              }
            ],
            "observation_sha256": "sha256:d12163d19cbb672b5a8b91910b103d3926c9441747f4d8aaacaec53cd7de4b50",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/archivo-inexistente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:6a2e5094d10edb67d05bc980aac5c02e43e91d1122add15bb0ccd10b9d9d00ff",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:6a2e5094d10edb67d05bc980aac5c02e43e91d1122add15bb0ccd10b9d9d00ff",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/baseline-casing": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:5540bb0c7bc4d71e70212aa0728875ba8f618bf1b9478f0a0ce8252845c62461",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 de v1 declara baseline [red], fuera de {RED, GREEN_ALREADY, NOT_APPLICABLE, BLOCKED}"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "baseline-sin-resolver"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:c7d433e8ad9e0734186d4eea32993ddcd25608244f12400d4d315a9dd2ec76d3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:5540bb0c7bc4d71e70212aa0728875ba8f618bf1b9478f0a0ce8252845c62461",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 de v1 declara baseline [red], fuera de {RED, GREEN_ALREADY, NOT_APPLICABLE, BLOCKED}"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "baseline-sin-resolver"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:c7d433e8ad9e0734186d4eea32993ddcd25608244f12400d4d315a9dd2ec76d3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/baseline-not-applicable": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/baseline-sin-resolver": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6fef8126e927c0542fec02f5eb895e5730493de58091f77d83eb5803aa10eb05",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-X1 de v1 declara baseline [TBD], fuera de {RED, GREEN_ALREADY, NOT_APPLICABLE, BLOCKED}"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "baseline-sin-resolver"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:77f6c7191b80c2bd2188dfeead216ec8ad0af48986cc238b04820cfa78f44482",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6fef8126e927c0542fec02f5eb895e5730493de58091f77d83eb5803aa10eb05",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-X1 de v1 declara baseline [TBD], fuera de {RED, GREEN_ALREADY, NOT_APPLICABLE, BLOCKED}"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "baseline-sin-resolver"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:77f6c7191b80c2bd2188dfeead216ec8ad0af48986cc238b04820cfa78f44482",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/cardinalidad-dos-filas": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:a7fb6b25adefe81ce523fbef46c8045ef290999dcc80a2d1cb7f5b64339e2f7c",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 tiene 2 filas en v1: V-X1, V-X1-bis"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "tarea-con-dos-filas"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:bfe83b83ade43f658446f551a9b2da4d17a4cd82dc3718e72028a2c088179895",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:a7fb6b25adefe81ce523fbef46c8045ef290999dcc80a2d1cb7f5b64339e2f7c",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 tiene 2 filas en v1: V-X1, V-X1-bis"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "tarea-con-dos-filas"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:bfe83b83ade43f658446f551a9b2da4d17a4cd82dc3718e72028a2c088179895",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/cardinalidad-fila-huerfana": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:30c475dba8e6e57d91a3af279e4fd6366c839a4fd5f40c5ca8913ecbb4088daa",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-H9 de v1 no cierra ninguna orchestration_task"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "fila-sin-tarea"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:bedd9980a97f9255e21e99095e0bbbc55b14ef149d738263c0efa999f2ab683f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:30c475dba8e6e57d91a3af279e4fd6366c839a4fd5f40c5ca8913ecbb4088daa",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-H9 de v1 no cierra ninguna orchestration_task"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "fila-sin-tarea"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:bedd9980a97f9255e21e99095e0bbbc55b14ef149d738263c0efa999f2ab683f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/cardinalidad-tarea-sin-fila": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:478d42d94e06cdf6c381382cb99c443229d727380dda093b9b0f595c7c7e7934",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 no tiene fila en v1 (done_when: V-C1)"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "tarea-sin-fila"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:36ba9281806cb75e51c41db2af9aa79a8e70c21ed20d1a77bd244e9492d15c87",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:478d42d94e06cdf6c381382cb99c443229d727380dda093b9b0f595c7c7e7934",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 no tiene fila en v1 (done_when: V-C1)"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "tarea-sin-fila"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:36ba9281806cb75e51c41db2af9aa79a8e70c21ed20d1a77bd244e9492d15c87",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/id-casing": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:dd18a3f7e48e4577300e559cb83b6cc0a94b4fe3dc67b85b6367ab7054fc1fd4",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v2 estrena la fila V-c1, que v1 no declara"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "id-agregado-entre-versiones"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:206a1ecb2fa1a7065e4808232c7072836518b0c407e377082bf8c092cb4ebb29",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:dd18a3f7e48e4577300e559cb83b6cc0a94b4fe3dc67b85b6367ab7054fc1fd4",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v2 estrena la fila V-c1, que v1 no declara"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "id-agregado-entre-versiones"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:206a1ecb2fa1a7065e4808232c7072836518b0c407e377082bf8c092cb4ebb29",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/mixto-2p-1np": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:80a06b2485b22d7efefb96036a564ae35fdab0c1f878063e3dc319e9debbb2f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a06ce0e22a3cc48360b4d4af961828cb27addc41cf422921f8cda0f18e8296ae",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:83ed5ea126481fa405d3cb0855df8394506893c02c76e282cf1d1677f02c35a6",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "servicio-c/.plans/notificaciones-v2/plan.md": "sha256:b3fdd62766ad81147f1927c9154e22d620ae42925dfbbd479e1b85978c19d4e7",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cbc4f177d1ebc1a55cbf66a65c1b44dffcc1890cfd8a9ad2a04ef7f8f6ee9872",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:80a06b2485b22d7efefb96036a564ae35fdab0c1f878063e3dc319e9debbb2f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a06ce0e22a3cc48360b4d4af961828cb27addc41cf422921f8cda0f18e8296ae",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:83ed5ea126481fa405d3cb0855df8394506893c02c76e282cf1d1677f02c35a6",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "servicio-c/.plans/notificaciones-v2/plan.md": "sha256:b3fdd62766ad81147f1927c9154e22d620ae42925dfbbd479e1b85978c19d4e7",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cbc4f177d1ebc1a55cbf66a65c1b44dffcc1890cfd8a9ad2a04ef7f8f6ee9872",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/positivo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/retrocompat": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:f79d67311399b08d0e3a6846b2f3227f6bafcc01772b038ee2471c48338193ae",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8e52ffaf7220553bfed82c963f367484950b89f38e5690c9ad2b3f0c0384768f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:766d03dc461dcbb8732fc4fc23c3846ce60b77281bd6b670319d9fb41edf8459",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:91db5c1c24ec64677017d796869218b94762104540f963e99e15a91b4f3ad190",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b5d4ee128380226aa949f5209fa646e03d2b78f41c5f9c87e4e0371065b82381",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c007db8a60a04417a9fab82d1cedfc7e2488eae8fc3e3ec74d9d5a2b89896d9e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:f79d67311399b08d0e3a6846b2f3227f6bafcc01772b038ee2471c48338193ae",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8e52ffaf7220553bfed82c963f367484950b89f38e5690c9ad2b3f0c0384768f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:766d03dc461dcbb8732fc4fc23c3846ce60b77281bd6b670319d9fb41edf8459",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:91db5c1c24ec64677017d796869218b94762104540f963e99e15a91b4f3ad190",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b5d4ee128380226aa949f5209fa646e03d2b78f41c5f9c87e4e0371065b82381",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c007db8a60a04417a9fab82d1cedfc7e2488eae8fc3e3ec74d9d5a2b89896d9e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/sin-auxiliar": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8d939196a160adbbd6d8777f3f672b79158a5d2ec979867e52b13a85a6e32251",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v1 no aloja el cierre de ninguna tarea auxiliar; sin fila: X1"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "fila-auxiliar-ausente"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:bf98102f3f87c4d798ccf25bc97de1deb725c110e7c5b2d2835ee08a5dd4485f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8d939196a160adbbd6d8777f3f672b79158a5d2ec979867e52b13a85a6e32251",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v1 no aloja el cierre de ninguna tarea auxiliar; sin fila: X1"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "fila-auxiliar-ausente"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:bf98102f3f87c4d798ccf25bc97de1deb725c110e7c5b2d2835ee08a5dd4485f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/solo-gates": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:b144218d868aacc30aa1b3b6c3ae9eeb07883e0f00c7f3f00c7b54fdbca6fba8",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v1 no aloja el cierre de ninguna tarea phase=closeout; sin fila: C1, X1"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "fila-closeout-ausente"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:3959a321e9006707bde9108bc7441cf537945d73450325af917756a0b92a5ce1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:b144218d868aacc30aa1b3b6c3ae9eeb07883e0f00c7f3f00c7b54fdbca6fba8",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v1 no aloja el cierre de ninguna tarea phase=closeout; sin fila: C1, X1"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "fila-closeout-ausente"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:3959a321e9006707bde9108bc7441cf537945d73450325af917756a0b92a5ce1",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/v2-agrega-id": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:2c0c175345ad02e69755ebabaa3f4a872249abe6bd6e39c20a3c72c9ab8231fe",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v2 estrena la fila V-Z9, que v1 no declara"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "id-agregado-entre-versiones"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:fbf1f69184b6dd3ac4917805fa2869078dfb5e1a947eeb6c46c38ae1eb28ad0a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:2c0c175345ad02e69755ebabaa3f4a872249abe6bd6e39c20a3c72c9ab8231fe",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v2 estrena la fila V-Z9, que v1 no declara"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "id-agregado-entre-versiones"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:fbf1f69184b6dd3ac4917805fa2869078dfb5e1a947eeb6c46c38ae1eb28ad0a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-contract/v2-quita-id": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:1dc8e02b6de0d280deb7476a0e33ff4a24d737d24768ac9c082fff6f677ac30f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v2 no lleva la fila V-X1, que v1 declara"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "id-quitado-entre-versiones"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:e2084046b9fb413bae97227a5c12c8c52f93400f71ae3ab40966d30f55ac70b6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:1dc8e02b6de0d280deb7476a0e33ff4a24d737d24768ac9c082fff6f677ac30f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "v2 no lleva la fila V-X1, que v1 declara"
                  ],
                  [
                    "contrato",
                    "{dir}/.sdd/notificaciones-v2/integracion.md"
                  ],
                  [
                    "hallazgo",
                    "id-quitado-entre-versiones"
                  ]
                ],
                "id": "contract"
              }
            ],
            "observation_sha256": "sha256:e2084046b9fb413bae97227a5c12c8c52f93400f71ae3ab40966d30f55ac70b6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/ac-integration-huerfano": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:9227146d70134bbd36d2098333c37367a309c321c15c25200cab27049eaac3f0",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:40773eebe0dc21383aff8b4d027e86b0a584a083fb159a58ae317c168bc9fe1b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:ff3491826e01f46a43fd2b7b0e7ac1d95ba7d0e66d18f2de2803d5c1a2e7e92f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "ninguna orchestration_task cubre AC-3"
                  ],
                  [
                    "detalle",
                    "AC-3"
                  ],
                  [
                    "hallazgo",
                    "ac-integration-huerfano"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f9b3f35fb45fcc93b7504589d1702e3fa3331d6b3a9d6653c962064971063783",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:9227146d70134bbd36d2098333c37367a309c321c15c25200cab27049eaac3f0",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:40773eebe0dc21383aff8b4d027e86b0a584a083fb159a58ae317c168bc9fe1b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:ff3491826e01f46a43fd2b7b0e7ac1d95ba7d0e66d18f2de2803d5c1a2e7e92f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "ninguna orchestration_task cubre AC-3"
                  ],
                  [
                    "detalle",
                    "AC-3"
                  ],
                  [
                    "hallazgo",
                    "ac-integration-huerfano"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f9b3f35fb45fcc93b7504589d1702e3fa3331d6b3a9d6653c962064971063783",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/ac-mal-ubicado-integ-en-repo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:366ae7b2f226cba3c888f5b2732648c2d62c0028c86fab51f45d15feb13de9ac",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:700d49315c862b47ac965cf70bd3e31eedf184239fe77acf3b98d6cf85c78817",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a declara AC-3, que la master-spec etiqueta [integration]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "integration-en-covers_ac-de-repo"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:311f1c2c78f40ebbe4dec780cc7564371c7c12faba91e70c90ef55f02703d1cf",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:366ae7b2f226cba3c888f5b2732648c2d62c0028c86fab51f45d15feb13de9ac",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:700d49315c862b47ac965cf70bd3e31eedf184239fe77acf3b98d6cf85c78817",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a declara AC-3, que la master-spec etiqueta [integration]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "integration-en-covers_ac-de-repo"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:311f1c2c78f40ebbe4dec780cc7564371c7c12faba91e70c90ef55f02703d1cf",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/ac-mal-ubicado-local-en-tarea": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:fa2e45f1b2cba0e0a5d98991229c99d9f8619812a89beff73d277156d47686f7",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:204b11bb1eea3dda923ec207fe4c184a88a844f98aaa6a887f9682d812066dd3",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara AC-1, que la master-spec etiqueta [repo-local]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-local-en-covers_ac-de-tarea"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f56f8c45c2800e680b58d31b3815beb18c39ef79fcfb4b12b84eeaf9f5269196",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:fa2e45f1b2cba0e0a5d98991229c99d9f8619812a89beff73d277156d47686f7",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:204b11bb1eea3dda923ec207fe4c184a88a844f98aaa6a887f9682d812066dd3",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara AC-1, que la master-spec etiqueta [repo-local]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-local-en-covers_ac-de-tarea"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f56f8c45c2800e680b58d31b3815beb18c39ef79fcfb4b12b84eeaf9f5269196",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/archivo-inexistente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:6a2e5094d10edb67d05bc980aac5c02e43e91d1122add15bb0ccd10b9d9d00ff",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-archivo-inexistente"
              }
            ],
            "observation_sha256": "sha256:6a2e5094d10edb67d05bc980aac5c02e43e91d1122add15bb0ccd10b9d9d00ff",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/blocks-en-closeout": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2bc8fbdf416825fc5b7695dcb21e54a60372b546ed19b85527cfb5c36e112725",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 es phase=closeout y declara blocks_repos: [servicio-b]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "blocks_repos-en-closeout"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:bc070f1ac18a6f757d59dc3daf63e27eb39fb31b113eae99d335d8082876a9a5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2bc8fbdf416825fc5b7695dcb21e54a60372b546ed19b85527cfb5c36e112725",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 es phase=closeout y declara blocks_repos: [servicio-b]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "blocks_repos-en-closeout"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:bc070f1ac18a6f757d59dc3daf63e27eb39fb31b113eae99d335d8082876a9a5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/cardinalidad-dos-tareas": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:993b098a7877f1c7c49550c152d9a8043c00f6f1f69a017bf3ef72df64024c44",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:d590bba0da8c9b4d57414b9af7d43c40c0b128400c922bdfedc7c891efeb1d76",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "AC-3 lo cubren 2 tareas de cierre: C1, X1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ac-cubierto-por-dos-tareas"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9ae6ca8291f08f743267f010bcb332fa6b17643b987095c9c141ebb88f8e3990",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:993b098a7877f1c7c49550c152d9a8043c00f6f1f69a017bf3ef72df64024c44",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:d590bba0da8c9b4d57414b9af7d43c40c0b128400c922bdfedc7c891efeb1d76",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "AC-3 lo cubren 2 tareas de cierre: C1, X1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ac-cubierto-por-dos-tareas"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9ae6ca8291f08f743267f010bcb332fa6b17643b987095c9c141ebb88f8e3990",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-blocks": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1e2053428e8c5aa30d4bb5117daa07584ac020fd1c8b43091424fdceac34ee0d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 bloquea SERVICIO-B, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "blocks_repos-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:2836e09b9b2a75ab910799484b23c52753bc04bd61be91269b358eb6c11e0f04",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1e2053428e8c5aa30d4bb5117daa07584ac020fd1c8b43091424fdceac34ee0d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 bloquea SERVICIO-B, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "blocks_repos-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:2836e09b9b2a75ab910799484b23c52753bc04bd61be91269b358eb6c11e0f04",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-covers-ac": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3074d5b94f6e74e3c94a1bfe46ce1c06502bc412741b04f673d49b119db0c41d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "ninguna orchestration_task cubre AC-4"
                  ],
                  [
                    "detalle",
                    "AC-4"
                  ],
                  [
                    "hallazgo",
                    "ac-integration-huerfano"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:fde4fe89e3727575328441c1df6310acc44a41671da93998cfebffea32bba7db",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3074d5b94f6e74e3c94a1bfe46ce1c06502bc412741b04f673d49b119db0c41d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "ninguna orchestration_task cubre AC-4"
                  ],
                  [
                    "detalle",
                    "AC-4"
                  ],
                  [
                    "hallazgo",
                    "ac-integration-huerfano"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:fde4fe89e3727575328441c1df6310acc44a41671da93998cfebffea32bba7db",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-depends-on": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a7756a2a28e22d21bc4eeb09b5e849dfb12b1989243bf45339a498b5242ccb5a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 depende de g1, que ninguna orchestration_task declara"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "depends_on-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f208ef4977f68f17d45614437c60c26387543922e6e5de787779aaf22a23163e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a7756a2a28e22d21bc4eeb09b5e849dfb12b1989243bf45339a498b5242ccb5a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 depende de g1, que ninguna orchestration_task declara"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "depends_on-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f208ef4977f68f17d45614437c60c26387543922e6e5de787779aaf22a23163e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-id": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0a1c22035ac01caac9d6f51fe67e48fb678761b62d9796ea8351b412eb1edb09",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c737f8b4c5d0fb509d772b37f4c26c260da39762cb8c2e4103dafd46210e52b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0a1c22035ac01caac9d6f51fe67e48fb678761b62d9796ea8351b412eb1edb09",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c737f8b4c5d0fb509d772b37f4c26c260da39762cb8c2e4103dafd46210e52b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-part-clave": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0c9af9f8d6fd7937b04e2bef4670327c4c6bb67285263bb638ecbc6f7d400638",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara la clave ac-4, que no está en su covers_ac [AC-3, AC-4]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-clave-ajena"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:005e2532a56fc8473725db4fb988e70852fedf49bd1f356a72ea77fc12d01b35",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0c9af9f8d6fd7937b04e2bef4670327c4c6bb67285263bb638ecbc6f7d400638",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara la clave ac-4, que no está en su covers_ac [AC-3, AC-4]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-clave-ajena"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:005e2532a56fc8473725db4fb988e70852fedf49bd1f356a72ea77fc12d01b35",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-part-repo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:36e230ef4dc743d70c22558a1811b2a9afca58cc2528c56be0f94b4a6870dc7a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-4 de la tarea C1 nombra Servicio-A, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-repo-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:23a7745095100d347fef2d5390ad158451f85aead235d8ecfecea8eec6ef6095",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:36e230ef4dc743d70c22558a1811b2a9afca58cc2528c56be0f94b4a6870dc7a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-4 de la tarea C1 nombra Servicio-A, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-repo-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:23a7745095100d347fef2d5390ad158451f85aead235d8ecfecea8eec6ef6095",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-phase": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8c8f2a96eb5fb85dabd3f279f803bf77887e6356f7b5422da86aae12dcdba05b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 declara phase=[Gate], fuera de {gate, closeout}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "phase-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:6c4d06c5fed599ec46c4f7c76a286de4e52c7ddd8cbdcc7e1b3741779b8b860c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8c8f2a96eb5fb85dabd3f279f803bf77887e6356f7b5422da86aae12dcdba05b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 declara phase=[Gate], fuera de {gate, closeout}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "phase-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:6c4d06c5fed599ec46c4f7c76a286de4e52c7ddd8cbdcc7e1b3741779b8b860c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-status": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:d22162869343ebc002919a06437a035d81de1e567146a344ea7126f67dae7a63",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara status=[Done], fuera de {pending, in-progress, done, blocked}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "status-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0aee9cbbf5ebb76d4918d150dbae64eb27e8207446dbaef2e681b9304e6a672d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:d22162869343ebc002919a06437a035d81de1e567146a344ea7126f67dae7a63",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara status=[Done], fuera de {pending, in-progress, done, blocked}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "status-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0aee9cbbf5ebb76d4918d150dbae64eb27e8207446dbaef2e681b9304e6a672d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/casing-tag-ac": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:8a466cb37e2dfa85ad35a4e80fe611ccd1cf9440264bd9a5dda29fdb628fb3b9",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-4 de la tarea C1 no es un AC [integration] de la master-spec"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ac-no-integration"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:2b09b951309c6853e18849bfb62e33cf385edcf8c9ca8d9dc255bdaeb2974d1e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:8a466cb37e2dfa85ad35a4e80fe611ccd1cf9440264bd9a5dda29fdb628fb3b9",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-4 de la tarea C1 no es un AC [integration] de la master-spec"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ac-no-integration"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:2b09b951309c6853e18849bfb62e33cf385edcf8c9ca8d9dc255bdaeb2974d1e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/ciclo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:dbefc825eab46924688d188cb8be530955ba6a343707cc956820f72107bac294",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "estas tareas no llegan a ejecutarse nunca: C1, X1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ciclo-en-depends_on"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0c490537ce75f9ed43e090dbacd015458a956bd66f0bea7826d8a5b670fe8991",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:dbefc825eab46924688d188cb8be530955ba6a343707cc956820f72107bac294",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "estas tareas no llegan a ejecutarse nunca: C1, X1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ciclo-en-depends_on"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0c490537ce75f9ed43e090dbacd015458a956bd66f0bea7826d8a5b670fe8991",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/done-when-ausente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:b0e837891635d3e3ae01df42fcb8147b6f09c1cc573455a7abb3048cddd79be7",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 no declara done_when"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "done_when-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:48c7993be82cc76f01c61980a6d3589871d3e93ebadea762792e7fdec8ea69a7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:b0e837891635d3e3ae01df42fcb8147b6f09c1cc573455a7abb3048cddd79be7",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 no declara done_when"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "done_when-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:48c7993be82cc76f01c61980a6d3589871d3e93ebadea762792e7fdec8ea69a7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/done-when-vacio": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:500d8f1554b691f5f794628121bd97702cb3398aa18b045126178ccf7c02141d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 declara done_when vacío"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "done_when-vacio"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:17f2306f3253f29c9591b8b37d7637f31b5593464897c1b343fcaf04571b0ee6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:500d8f1554b691f5f794628121bd97702cb3398aa18b045126178ccf7c02141d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 declara done_when vacío"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "done_when-vacio"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:17f2306f3253f29c9591b8b37d7637f31b5593464897c1b343fcaf04571b0ee6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/enum-phase": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:6145c9221fa756ed9be9e3376a334e076cb6795a086a960c388f91ea266c1144",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara phase=[cierre], fuera de {gate, closeout}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "phase-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:ec90d02697af875d8b9667c165a868551c31fca98e5c311cf0ff9c5141ac09f4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:6145c9221fa756ed9be9e3376a334e076cb6795a086a960c388f91ea266c1144",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara phase=[cierre], fuera de {gate, closeout}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "phase-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:ec90d02697af875d8b9667c165a868551c31fca98e5c311cf0ff9c5141ac09f4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/enum-status": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:efe2fd85ee67883405c0137d8d91b2655084adbc88f32687cdc933f1af851b0b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara status=[pendiente], fuera de {pending, in-progress, done, blocked}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "status-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0864acf1ab08cedd1fd8d2c961f9156072ae858149d9776b2591190eccd2cbb3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:efe2fd85ee67883405c0137d8d91b2655084adbc88f32687cdc933f1af851b0b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara status=[pendiente], fuera de {pending, in-progress, done, blocked}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "status-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0864acf1ab08cedd1fd8d2c961f9156072ae858149d9776b2591190eccd2cbb3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/gate-depende-closeout": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:98b233c22a020cc07f2d48b8c50e9ff96f69a63089ddd8513f5303a19e9401ba",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el gate G1 depende de X1, que es phase=closeout"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "gate-depende-de-closeout"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:98bf13346e02486f9b934897796d0a9661f2cd6425d8efc296783d5192be3564",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:98b233c22a020cc07f2d48b8c50e9ff96f69a63089ddd8513f5303a19e9401ba",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el gate G1 depende de X1, que es phase=closeout"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "gate-depende-de-closeout"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:98bf13346e02486f9b934897796d0a9661f2cd6425d8efc296783d5192be3564",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/id-duplicado": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:f208be51cf68c3241128b030279a44e65814bdce220234755da01fcbc7df798d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el id C1 abre 2 entradas de orchestration_tasks"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "id-duplicado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9e726d92643177d1e08c29ee9335c018792b32fcd8f912ac62847d51253cd050",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:f208be51cf68c3241128b030279a44e65814bdce220234755da01fcbc7df798d",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el id C1 abre 2 entradas de orchestration_tasks"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "id-duplicado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9e726d92643177d1e08c29ee9335c018792b32fcd8f912ac62847d51253cd050",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/mixto-2p-1np": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:80a06b2485b22d7efefb96036a564ae35fdab0c1f878063e3dc319e9debbb2f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a06ce0e22a3cc48360b4d4af961828cb27addc41cf422921f8cda0f18e8296ae",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:83ed5ea126481fa405d3cb0855df8394506893c02c76e282cf1d1677f02c35a6",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "servicio-c/.plans/notificaciones-v2/plan.md": "sha256:b3fdd62766ad81147f1927c9154e22d620ae42925dfbbd479e1b85978c19d4e7",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cbc4f177d1ebc1a55cbf66a65c1b44dffcc1890cfd8a9ad2a04ef7f8f6ee9872",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:80a06b2485b22d7efefb96036a564ae35fdab0c1f878063e3dc319e9debbb2f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a06ce0e22a3cc48360b4d4af961828cb27addc41cf422921f8cda0f18e8296ae",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:83ed5ea126481fa405d3cb0855df8394506893c02c76e282cf1d1677f02c35a6",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "servicio-c/.plans/notificaciones-v2/plan.md": "sha256:b3fdd62766ad81147f1927c9154e22d620ae42925dfbbd479e1b85978c19d4e7",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cbc4f177d1ebc1a55cbf66a65c1b44dffcc1890cfd8a9ad2a04ef7f8f6ee9872",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/modelo-valido": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/owner-ausente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3fe464214129f62c810e5414ffcffa50179cd7b32ab82c5847e05231a284550",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1c8e54ef0ad336485ac99cea35baa78c4383c68ac5589f9ff22073b32b3657b2",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 no declara owner"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "owner-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9cb4fe2f846451ecca098a328efdc41a4d83fdeb80a8c5dfa8c9cbc3f7968943",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3fe464214129f62c810e5414ffcffa50179cd7b32ab82c5847e05231a284550",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1c8e54ef0ad336485ac99cea35baa78c4383c68ac5589f9ff22073b32b3657b2",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 no declara owner"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "owner-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9cb4fe2f846451ecca098a328efdc41a4d83fdeb80a8c5dfa8c9cbc3f7968943",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/owner-vacio": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3fe464214129f62c810e5414ffcffa50179cd7b32ab82c5847e05231a284550",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7fec88bfaa0c425dc54ba0ec9e0dd8138d95f9b722ac00f20a2a46cb859d3393",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara owner vacío"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "owner-vacio"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0be4e1b58ce1c4eabaae0a04ed3d8c17f7d740ffe623feeed622a41b555e2045",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3fe464214129f62c810e5414ffcffa50179cd7b32ab82c5847e05231a284550",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7fec88bfaa0c425dc54ba0ec9e0dd8138d95f9b722ac00f20a2a46cb859d3393",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara owner vacío"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "owner-vacio"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:0be4e1b58ce1c4eabaae0a04ed3d8c17f7d740ffe623feeed622a41b555e2045",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-ac-no-integ": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:884214c69dca46455b3c65e1d8a83807c129dc7ec2759d1591b2d4f8dc3f5390",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2eebe0a515edd7ac209e6a3b9bcf0813c27651b3714501866932ccaccb92a9ef",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-7 de la tarea C1 no es un AC [integration] de la master-spec"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ac-no-integration"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:4c0a8a1a5f0eccedb3f6d228262de8ea78493f132e0b822c106a7862f02fd9d6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:884214c69dca46455b3c65e1d8a83807c129dc7ec2759d1591b2d4f8dc3f5390",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2eebe0a515edd7ac209e6a3b9bcf0813c27651b3714501866932ccaccb92a9ef",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-7 de la tarea C1 no es un AC [integration] de la master-spec"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ac-no-integration"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:4c0a8a1a5f0eccedb3f6d228262de8ea78493f132e0b822c106a7862f02fd9d6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-ac-sin-clave": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:b46bf801730662cdd41840c22a24c755cb287d9c90776347d4f6ba5fa8e6fe3b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cubre AC-4 y no le declara clave en participating_repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ac-sin-clave"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:cd820fe97bb2f2f6b2041db54c677daa172ed7f2b7423e67215612f64fb89cc8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:b46bf801730662cdd41840c22a24c755cb287d9c90776347d4f6ba5fa8e6fe3b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cubre AC-4 y no le declara clave en participating_repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ac-sin-clave"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:cd820fe97bb2f2f6b2041db54c677daa172ed7f2b7423e67215612f64fb89cc8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-ausente-con-integ": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:43a90f80722b5ce57bde33bffacf7672ef9b22730acd91abaa88b395193988f0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cubre [AC-3, AC-4] y no declara participating_repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ausente-con-covers_ac"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:3843ec512357a498dd6e0ca73fe51d0a6244e01c2b6446385ae2d4aa707c43b8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:43a90f80722b5ce57bde33bffacf7672ef9b22730acd91abaa88b395193988f0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cubre [AC-3, AC-4] y no declara participating_repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-ausente-con-covers_ac"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:3843ec512357a498dd6e0ca73fe51d0a6244e01c2b6446385ae2d4aa707c43b8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-ausente-sin-integ": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e5f422777bdc0e595da6730f2b2b003a723c7d49bf832f5cd6c58f5c596ae109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-clave-dup": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:d293e71d3f94ceddda997fb03a7cd1f17609737d3cc058f5ec52b211f40b0df4",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 repite la clave AC-3 en participating_repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-clave-duplicada"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:ea7fc5d786618279780e8cb47be0e7249ca1e3497647efb893d642d63b6ccc13",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:d293e71d3f94ceddda997fb03a7cd1f17609737d3cc058f5ec52b211f40b0df4",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 repite la clave AC-3 en participating_repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-clave-duplicada"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:ea7fc5d786618279780e8cb47be0e7249ca1e3497647efb893d642d63b6ccc13",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-clave-extra": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1c2e0ddb673a4ddd0f5afafa9ec3fb797f890bf25f55c3c00288777cc9e316d5",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara la clave AC-9, que no está en su covers_ac [AC-3, AC-4]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-clave-ajena"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f392bab7fd1148d8fc8c790d59ccfaa9e6c816bd402aefdcf7a1bc6e20a83fc9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1c2e0ddb673a4ddd0f5afafa9ec3fb797f890bf25f55c3c00288777cc9e316d5",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 declara la clave AC-9, que no está en su covers_ac [AC-3, AC-4]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-clave-ajena"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:f392bab7fd1148d8fc8c790d59ccfaa9e6c816bd402aefdcf7a1bc6e20a83fc9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-repo-inexistente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:ce5299a33b12c075be1dc2ecef95f9216b0f26eb07d018f7d2df173294518c86",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-3 de la tarea C1 nombra servicio-z, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-repo-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:6b8c79d0d07bbe56b70e41fa62833c962b1f6e5dbcd204a4fbb4bfe4c79372c5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:ce5299a33b12c075be1dc2ecef95f9216b0f26eb07d018f7d2df173294518c86",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la clave AC-3 de la tarea C1 nombra servicio-z, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-repo-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:6b8c79d0d07bbe56b70e41fa62833c962b1f6e5dbcd204a4fbb4bfe4c79372c5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-vacia-con-integ": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:6e9e229fbea85ebb53d0ec92267b6340ebd7aa184780677c3982cb12534ec99a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cubre [AC-3, AC-4] con participating_repos vacío"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-vacia-con-covers_ac"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9c1c39c7979075ce01fbfb6d97e2791e106c642046ad319fe321a16f690da54d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:6e9e229fbea85ebb53d0ec92267b6340ebd7aa184780677c3982cb12534ec99a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cubre [AC-3, AC-4] con participating_repos vacío"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "participacion-vacia-con-covers_ac"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:9c1c39c7979075ce01fbfb6d97e2791e106c642046ad319fe321a16f690da54d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/participacion-vacia-sin-integ": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3ad055e0535c880d3d19015f9e2484051770a42ef0f07d32a379a512419c424c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:999e9ababdf6162ba857e70d66ce285d8942220e8b394f7af36abb0d4962defe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3ad055e0535c880d3d19015f9e2484051770a42ef0f07d32a379a512419c424c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:999e9ababdf6162ba857e70d66ce285d8942220e8b394f7af36abb0d4962defe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/ref-muerta-blocks": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1a438f491867b0f22d9fbaaceb2bd784505f1a041a13459e99338d0db9d4e809",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 bloquea servicio-z, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "blocks_repos-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:6def4658999b805993f2b1df69fe6d1e800df8be8dd4a3ddaff9dd5dbe79f308",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:1a438f491867b0f22d9fbaaceb2bd784505f1a041a13459e99338d0db9d4e809",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 bloquea servicio-z, que no es un path de repos"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "blocks_repos-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:6def4658999b805993f2b1df69fe6d1e800df8be8dd4a3ddaff9dd5dbe79f308",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/ref-muerta-depends": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8e3966671c19125cd622a3b238df8d40c9d2af201ac70517f5dd8fa964c1e710",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 depende de G9, que ninguna orchestration_task declara"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "depends_on-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:efbe3d93d8a571e5e7ee76ba926ea13bfc8c492957c8a97414682228e4909d43",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8e3966671c19125cd622a3b238df8d40c9d2af201ac70517f5dd8fa964c1e710",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 depende de G9, que ninguna orchestration_task declara"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "depends_on-inexistente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "model"
              }
            ],
            "observation_sha256": "sha256:efbe3d93d8a571e5e7ee76ba926ea13bfc8c492957c8a97414682228e4909d43",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-model/retrocompat": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:f79d67311399b08d0e3a6846b2f3227f6bafcc01772b038ee2471c48338193ae",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8e52ffaf7220553bfed82c963f367484950b89f38e5690c9ad2b3f0c0384768f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:766d03dc461dcbb8732fc4fc23c3846ce60b77281bd6b670319d9fb41edf8459",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:91db5c1c24ec64677017d796869218b94762104540f963e99e15a91b4f3ad190",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b5d4ee128380226aa949f5209fa646e03d2b78f41c5f9c87e4e0371065b82381",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c007db8a60a04417a9fab82d1cedfc7e2488eae8fc3e3ec74d9d5a2b89896d9e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:f79d67311399b08d0e3a6846b2f3227f6bafcc01772b038ee2471c48338193ae",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8e52ffaf7220553bfed82c963f367484950b89f38e5690c9ad2b3f0c0384768f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:766d03dc461dcbb8732fc4fc23c3846ce60b77281bd6b670319d9fb41edf8459",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:91db5c1c24ec64677017d796869218b94762104540f963e99e15a91b4f3ad190",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b5d4ee128380226aa949f5209fa646e03d2b78f41c5f9c87e4e0371065b82381",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:c007db8a60a04417a9fab82d1cedfc7e2488eae8fc3e3ec74d9d5a2b89896d9e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/archive-cierre-pendiente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:190acfcde4f0605e3e3a34edc2f8bdac7e2bacaad2bb06dcc429b826610db72f",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "quedan 1 orchestration_tasks fuera de done: C1"
                  ],
                  [
                    "detalle",
                    "C1"
                  ],
                  [
                    "hallazgo",
                    "archive-con-tareas-pendientes"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:6cd0faa81175278fb659f12600af2b7152da698e3e05b4ac72b7135d95511b90",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:190acfcde4f0605e3e3a34edc2f8bdac7e2bacaad2bb06dcc429b826610db72f",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "quedan 1 orchestration_tasks fuera de done: C1"
                  ],
                  [
                    "detalle",
                    "C1"
                  ],
                  [
                    "hallazgo",
                    "archive-con-tareas-pendientes"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:6cd0faa81175278fb659f12600af2b7152da698e3e05b4ac72b7135d95511b90",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/archive-varias-pendientes": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e5fe8cc4d88d3b9a7ef0ab450b78b23eae16c8a40b81d1a3cd640ccb70effbff",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:88b8b5dfa50e91f98acc344ad2a1fb0feb702d4e5e317d42b253461ae85365a1",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6d72356369ce3722b30339c3c020ec610f7e362956a849de26d310f49062e22f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "quedan 3 orchestration_tasks fuera de done: G1, C1, X1"
                  ],
                  [
                    "detalle",
                    "C1 G1 X1"
                  ],
                  [
                    "hallazgo",
                    "archive-con-tareas-pendientes"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:e53448a0f7661097dfa4fc9b9d6af37b115da124f20f052aa43544ea1ade276f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e5fe8cc4d88d3b9a7ef0ab450b78b23eae16c8a40b81d1a3cd640ccb70effbff",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:88b8b5dfa50e91f98acc344ad2a1fb0feb702d4e5e317d42b253461ae85365a1",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6d72356369ce3722b30339c3c020ec610f7e362956a849de26d310f49062e22f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "quedan 3 orchestration_tasks fuera de done: G1, C1, X1"
                  ],
                  [
                    "detalle",
                    "C1 G1 X1"
                  ],
                  [
                    "hallazgo",
                    "archive-con-tareas-pendientes"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:e53448a0f7661097dfa4fc9b9d6af37b115da124f20f052aa43544ea1ade276f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/archivo-inexistente-artefacto": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-artefacto-inexistente"
              }
            ],
            "observation_sha256": "sha256:d096ee64cdac5b1b97f903691ef4fe8a4fa135deee5f867253d7d3f0ff5eb957",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-artefacto-inexistente"
              }
            ],
            "observation_sha256": "sha256:d096ee64cdac5b1b97f903691ef4fe8a4fa135deee5f867253d7d3f0ff5eb957",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/archivo-inexistente-plan": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-plan-inexistente"
              }
            ],
            "observation_sha256": "sha256:a778867d89f72a7833789c917e41de7ca9a9d960b80a2a754c05e58fa0adb09d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "fallo",
            "code": 99,
            "events": [
              {
                "fields": [
                  [
                    "archivo",
                    "{dir}/NO-EXISTE.md"
                  ]
                ],
                "id": "arnes-plan-inexistente"
              }
            ],
            "observation_sha256": "sha256:a778867d89f72a7833789c917e41de7ca9a9d960b80a2a754c05e58fa0adb09d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/asignacion-bloqueado-ya-ready": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:3d6671e2d36edae2c7919ac7537588256c33596628bd316da467baf245b61e9d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:31006a6f852eee031597d8c4e2f292a9e8b42a57e026a31d41cade6e369badbd",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:fae641a107e7e1cdfed6428a572253c008029eb706dcd48841069b5478441e7c",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b está en tasks-ready con 1 gate(s) fuera de done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-bloqueado-promovido"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:6d681d9ce78cda259444a6e3f103a66e06a1cfe6fa6b78c25ed61c85b0f16788",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:3d6671e2d36edae2c7919ac7537588256c33596628bd316da467baf245b61e9d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:31006a6f852eee031597d8c4e2f292a9e8b42a57e026a31d41cade6e369badbd",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:fae641a107e7e1cdfed6428a572253c008029eb706dcd48841069b5478441e7c",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b está en tasks-ready con 1 gate(s) fuera de done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-bloqueado-promovido"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:6d681d9ce78cda259444a6e3f103a66e06a1cfe6fa6b78c25ed61c85b0f16788",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/asignacion-inicial": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0c47b02dc7c489956352f073425b2d6c6940baeda81605a0f81e1c451123610b",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0c47b02dc7c489956352f073425b2d6c6940baeda81605a0f81e1c451123610b",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/asignacion-libre-aun-planned": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:99ed7f121bba85304790e8cec4743f83ff82aca77006b92fe114f594d5ab4849",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:34dc324137a6a1d23055207c6f5b2b228f25bbcceba99f12f3f4b83bf4a84cd3",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6d72356369ce3722b30339c3c020ec610f7e362956a849de26d310f49062e22f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a sigue en planned y ninguna tarea gate lo retiene"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-libre-sin-promover"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:bb1460732117f8037c06ee9406da6fd7306abd080015200ca61df4df0a27404e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:99ed7f121bba85304790e8cec4743f83ff82aca77006b92fe114f594d5ab4849",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:34dc324137a6a1d23055207c6f5b2b228f25bbcceba99f12f3f4b83bf4a84cd3",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6d72356369ce3722b30339c3c020ec610f7e362956a849de26d310f49062e22f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a sigue en planned y ninguna tarea gate lo retiene"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-libre-sin-promover"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:bb1460732117f8037c06ee9406da6fd7306abd080015200ca61df4df0a27404e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/baseline-blocked-sin-despacho": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0867b6bd3bd736852abdd6c3b00c7f4549f576cd98371e957ac5766fdacee703",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8b20f5cac8fd268b27a3186f6c131781fac1f6bd16e166f00ed0628c5770d3e1",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:a519e60f53a5a71f5056631b8d71ed1882e84774c3df3c40bc092f81708f12e3",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:910c11f82abfb898c329a5999f9d6a8c8e56d7a28266c04e023b52b55a510962",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0867b6bd3bd736852abdd6c3b00c7f4549f576cd98371e957ac5766fdacee703",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8b20f5cac8fd268b27a3186f6c131781fac1f6bd16e166f00ed0628c5770d3e1",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:a519e60f53a5a71f5056631b8d71ed1882e84774c3df3c40bc092f81708f12e3",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:910c11f82abfb898c329a5999f9d6a8c8e56d7a28266c04e023b52b55a510962",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/bitacora-ausente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "no hay bitácora que leer en {dir}/.sdd/notificaciones-v2/bitacora.md"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "bitacora-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:1517f464f5a34c6b5bfaa2ebf48b1dc3e04837d625a1c23a32f52eccdd3c16a9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "no hay bitácora que leer en {dir}/.sdd/notificaciones-v2/bitacora.md"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "bitacora-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:1517f464f5a34c6b5bfaa2ebf48b1dc3e04837d625a1c23a32f52eccdd3c16a9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-evento-sin-actor": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0d97693e0e859cf1bc344b61cccf614998551a56c13066342464ca2471cf0dbf",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara actor"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-actor"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:3179cce8f3b19c493d20c1808e1590486e55ab57235dfe9b1adbc594de21c891",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0d97693e0e859cf1bc344b61cccf614998551a56c13066342464ca2471cf0dbf",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara actor"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-actor"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:3179cce8f3b19c493d20c1808e1590486e55ab57235dfe9b1adbc594de21c891",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-evento-sin-id": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ccdbd32eb44bbf35f66566f0c10a0bd71dbceac797a4186ba1b159d0d499db4d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara id"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-id"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:5e4e732bf8651b3fd5a15b7b20851c8d9a5ea3fbe29cd52536748813ff1e3096",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ccdbd32eb44bbf35f66566f0c10a0bd71dbceac797a4186ba1b159d0d499db4d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara id"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-id"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:5e4e732bf8651b3fd5a15b7b20851c8d9a5ea3fbe29cd52536748813ff1e3096",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-evento-sin-objeto": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0c880491c252f04a6e90c7111e8d806250f7222576dd81377997d50d4f548f12",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara objeto"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-objeto"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:0aa44e0aa5559155eceb4dd534b3479d4c848d88f74f3a70e1dfa7edde551beb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0c880491c252f04a6e90c7111e8d806250f7222576dd81377997d50d4f548f12",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara objeto"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-objeto"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:0aa44e0aa5559155eceb4dd534b3479d4c848d88f74f3a70e1dfa7edde551beb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-evento-sin-paso": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:6d353f1a28fe1cbbb38e5b4a4a69f56926d00ec224c9ec8844c241b887a9d515",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara paso"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-paso"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:7f982e45ae48958ff136f192df8930011b026d9999d85fd35c4ab6c9f11d26d6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:6d353f1a28fe1cbbb38e5b4a4a69f56926d00ec224c9ec8844c241b887a9d515",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara paso"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-paso"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:7f982e45ae48958ff136f192df8930011b026d9999d85fd35c4ab6c9f11d26d6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-evento-sin-resultado": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:238750b85023d744b3c4c5a928f7bade771c63546b4b857aa93a55a1bc30f697",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara resultado"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-resultado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:ba1bb740ef8710c3b7ddfa1c230c685374344566e5f64aec4477a3169f636077",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:238750b85023d744b3c4c5a928f7bade771c63546b4b857aa93a55a1bc30f697",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara resultado"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-resultado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:ba1bb740ef8710c3b7ddfa1c230c685374344566e5f64aec4477a3169f636077",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-evento-sin-timestamp": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:3bf5787183a09cef3099853f7f78f2726896e48fdaa0fface148a027141c8c12",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara timestamp"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-timestamp"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:5bc6151308ba463a48b0ddf4d8d7d8d578ce5ee11a026abdf4fa175600b8843a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:3bf5787183a09cef3099853f7f78f2726896e48fdaa0fface148a027141c8c12",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8º de la bitácora no declara timestamp"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-sin-timestamp"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:5bc6151308ba463a48b0ddf4d8d7d8d578ce5ee11a026abdf4fa175600b8843a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-exito-sin-efecto": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:63a02a4f34224198d082c9662ce59873b9a8e7de852b981e114c62551b411a38",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 10 consumó cerrar-tarea sobre X1 y su estado no cambió"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "exito-sin-transicion"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:a0cfb7dc47bc10f604b2eacc2e5a0b4f14218be5f6f0fb7e0bcccbb6218d0bb8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:63a02a4f34224198d082c9662ce59873b9a8e7de852b981e114c62551b411a38",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 10 consumó cerrar-tarea sobre X1 y su estado no cambió"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "exito-sin-transicion"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:a0cfb7dc47bc10f604b2eacc2e5a0b4f14218be5f6f0fb7e0bcccbb6218d0bb8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-id-duplicado": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a17de3be2ca1cc73f2d82ad77229a6f1e46256fce8e89941a994ba59a4706019",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el id 1 abre 2 eventos de la bitácora"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-id-duplicado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:4980496145d90bba6468843703fd4eafb7a321d1e6c7f95cd5b3f017888ff91c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a17de3be2ca1cc73f2d82ad77229a6f1e46256fce8e89941a994ba59a4706019",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el id 1 abre 2 eventos de la bitácora"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evento-id-duplicado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:4980496145d90bba6468843703fd4eafb7a321d1e6c7f95cd5b3f017888ff91c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-intento-rechazado": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0c47b02dc7c489956352f073425b2d6c6940baeda81605a0f81e1c451123610b",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0c47b02dc7c489956352f073425b2d6c6940baeda81605a0f81e1c451123610b",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/bitacora-orden-ambiguo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:046f905a0186b73d5a27a5409290d31822c00d48051055611a7013e6c700f183",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento con id [ultimo] no lleva un entero comparable"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "orden-no-determinable"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:24c9dc25d5af8769e267b1306209c5fc71f2b7de99583866d78d593ac6259dfa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:046f905a0186b73d5a27a5409290d31822c00d48051055611a7013e6c700f183",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento con id [ultimo] no lleva un entero comparable"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "orden-no-determinable"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:24c9dc25d5af8769e267b1306209c5fc71f2b7de99583866d78d593ac6259dfa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-rechazo-con-efecto": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:76ba09fe15b241acd87dd80c6add340142f422794d3c8a52e8be843e288256c7",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 10 rechazó cerrar-tarea sobre X1 y su estado cambió igual"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "rechazo-con-transicion"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:23c79ece884362216e3fbada9cfcd6e8f8d6b57806a7bc9d86ae37c62133fe9b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:76ba09fe15b241acd87dd80c6add340142f422794d3c8a52e8be843e288256c7",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 10 rechazó cerrar-tarea sobre X1 y su estado cambió igual"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "rechazo-con-transicion"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:23c79ece884362216e3fbada9cfcd6e8f8d6b57806a7bc9d86ae37c62133fe9b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-resultado-invalido": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:fc5da77b81720b8c711af21e9440d94084090df53575adb40eabc7096a8b04f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8 declara resultado=[ok], fuera de {consumado, rechazado}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "resultado-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:730e95e34f1874563f644ff9a605d56ba3ea70f846575ac94919a1efb27ba0ec",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:fc5da77b81720b8c711af21e9440d94084090df53575adb40eabc7096a8b04f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 8 declara resultado=[ok], fuera de {consumado, rechazado}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "resultado-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:730e95e34f1874563f644ff9a605d56ba3ea70f846575ac94919a1efb27ba0ec",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/bitacora-transicion-consumada": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "orchestration-state/bitacora-transicion-sin-evento": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:b5c8c965759850e8efb03b482230b6f5ba0b7e6ceed7a53ba634a7a16185623a",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 está en done y ningún evento cerrar-tarea la consumó"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "transicion-sin-evento"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:309d9e5db7a594d65a3c82391ced85cf3e2deb991a0096f4e5e00b59b3113226",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:b5c8c965759850e8efb03b482230b6f5ba0b7e6ceed7a53ba634a7a16185623a",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 está en done y ningún evento cerrar-tarea la consumó"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "transicion-sin-evento"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:309d9e5db7a594d65a3c82391ced85cf3e2deb991a0096f4e5e00b59b3113226",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-ancla": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:446dc120cf04a56392bcdedd016e1d7a789d454adc7a370c2cb9a876f6c80282",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 midió acuerdo-evento en V3 y la vigente es v3"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ancla-versionada-obsoleta"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:cc6fd2e3d21f0608e641b5ee76dcf967df92ffd912703e0af8006cefe7cdda01",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:446dc120cf04a56392bcdedd016e1d7a789d454adc7a370c2cb9a876f6c80282",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 midió acuerdo-evento en V3 y la vigente es v3"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ancla-versionada-obsoleta"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:cc6fd2e3d21f0608e641b5ee76dcf967df92ffd912703e0af8006cefe7cdda01",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-contrato": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:d71fc8a96b0be78f9fbf03c0edf21562946af30ad45c3db87bae10716e6abe01",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-G1 se midió contra el contrato V1 y la versión vigente es v1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-version-anterior"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:ebcb23a185510c75ce642ee656ca794ce88398befa05e8326004822ed7035f15",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:d71fc8a96b0be78f9fbf03c0edf21562946af30ad45c3db87bae10716e6abe01",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-G1 se midió contra el contrato V1 y la versión vigente es v1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-version-anterior"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:ebcb23a185510c75ce642ee656ca794ce88398befa05e8326004822ed7035f15",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-fila": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:9ed98f2a1f3832367445dabb24cf3d3c0ee3a9b98abf6cf455e54113d11c8fb8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cierra con V-C1 y su evidencia ejecutó v-c1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-otra-fila"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:1c700fa26e3b9e2d418cb27d03ba4ca219df1f9fa6b6b1a5f8d92f4f39ae4517",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:9ed98f2a1f3832367445dabb24cf3d3c0ee3a9b98abf6cf455e54113d11c8fb8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cierra con V-C1 y su evidencia ejecutó v-c1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-otra-fila"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:1c700fa26e3b9e2d418cb27d03ba4ca219df1f9fa6b6b1a5f8d92f4f39ae4517",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-objeto": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ff87224345518d830d2c4322a7d82112a59a5667de3b74dda69871792e2c5fc3",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 3 consumó despachar-repo sobre SERVICIO-A y su estado no cambió"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "exito-sin-transicion"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:651f2543bf6a31dd114c392e6ca176529242c6f3ba4abf554a68349b8448a32b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ff87224345518d830d2c4322a7d82112a59a5667de3b74dda69871792e2c5fc3",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 3 consumó despachar-repo sobre SERVICIO-A y su estado no cambió"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "exito-sin-transicion"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:651f2543bf6a31dd114c392e6ca176529242c6f3ba4abf554a68349b8448a32b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-owner": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3472f43d4bda167b2f2ae633ba7b573ffc926dff2dcd3b56bde0fc07b89f1e1e",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:ed3d40b06184cd1ffd7923f3de9c04c8f7e31a6ed582f23549ea254992443c26",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3472f43d4bda167b2f2ae633ba7b573ffc926dff2dcd3b56bde0fc07b89f1e1e",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:ed3d40b06184cd1ffd7923f3de9c04c8f7e31a6ed582f23549ea254992443c26",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "orchestration-state/casing-paso": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:031365219f872e81a44c5327661979e9ffe4d9f549721576bed363816d9006f6",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a está en done y ningún evento promover-repo lo consumó"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "transicion-sin-evento"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:bc2ea92fea0c8e3cac0d2d384325a301eba5ef3e1549fdf4c5ea572618bc94dd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:031365219f872e81a44c5327661979e9ffe4d9f549721576bed363816d9006f6",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a está en done y ningún evento promover-repo lo consumó"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "transicion-sin-evento"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:bc2ea92fea0c8e3cac0d2d384325a301eba5ef3e1549fdf4c5ea572618bc94dd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-resultado": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:c581e073a2bf8c7e267f4230e5e12a23190ad34b70021b09bc0c42a13a3dff21",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 1 declara resultado=[Consumado], fuera de {consumado, rechazado}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "resultado-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:3bec65166dc3ba9aabb288b9c0dd0caf2ce21e9a98035f0efbb2194ae4be1abe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:c581e073a2bf8c7e267f4230e5e12a23190ad34b70021b09bc0c42a13a3dff21",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 1 declara resultado=[Consumado], fuera de {consumado, rechazado}"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "resultado-fuera-de-enum"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:3bec65166dc3ba9aabb288b9c0dd0caf2ce21e9a98035f0efbb2194ae4be1abe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-sha": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:78feaea965211d69f907de0b15779d3fa2a3d65e5bf22c6de5c6411a6a4ec26f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 midió servicio-a en AAA1111 y su plan.md declara aaa1111"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-cambiado-tras-medir"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:e25ac27bffb8a894b947336f566870dd327ee6d81b23392a1cacb50ae02ea1c5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:78feaea965211d69f907de0b15779d3fa2a3d65e5bf22c6de5c6411a6a4ec26f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 midió servicio-a en AAA1111 y su plan.md declara aaa1111"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-cambiado-tras-medir"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:e25ac27bffb8a894b947336f566870dd327ee6d81b23392a1cacb50ae02ea1c5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/casing-status-repo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2e9280eb371a8af9bd27b4f2db7a27108fcef75278684dab0485d8b0d371edc6",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a vale Done en el manifest y done en su plan.md"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "manifest-y-plan-divergen"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:3d1264058e2eb36f9c1818fd926b86f7320d6f479c58bcf2af5f0a03b376105b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2e9280eb371a8af9bd27b4f2db7a27108fcef75278684dab0485d8b0d371edc6",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a vale Done en el manifest y done en su plan.md"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "manifest-y-plan-divergen"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:3d1264058e2eb36f9c1818fd926b86f7320d6f479c58bcf2af5f0a03b376105b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/cierre-legitimo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "orchestration-state/deps-insatisfechas": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:999c27dd317d1a3b9ec1a9231914c515161afd687097431ef16f518cff1eb168",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 cerró con C1 fuera de done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "depends_on-insatisfecho"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:ab7feadd21d5637764739ee8df9d0bbaa90a5c1684a0ec9abc179e9f89f323b0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:999c27dd317d1a3b9ec1a9231914c515161afd687097431ef16f518cff1eb168",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 cerró con C1 fuera de done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "depends_on-insatisfecho"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:ab7feadd21d5637764739ee8df9d0bbaa90a5c1684a0ec9abc179e9f89f323b0",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/despacho-con-baseline-blocked": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0867b6bd3bd736852abdd6c3b00c7f4549f576cd98371e957ac5766fdacee703",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:32b7829f1b28ae85d9a410a86fa8c7838ae8eb2291872fcc8f8d3d72df0d9e23",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6c8b0de134678762b04b3003980b56eb5bcfcd9979d88fb4fe91c1dd85f79727",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a está en implementing con una fila de baseline BLOCKED en su contrato local"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "despacho-con-baseline-blocked"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:978bb905048191c1d67e55efdefeac969997513b8b42d75ca0c28335c9747abe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0867b6bd3bd736852abdd6c3b00c7f4549f576cd98371e957ac5766fdacee703",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:32b7829f1b28ae85d9a410a86fa8c7838ae8eb2291872fcc8f8d3d72df0d9e23",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6c8b0de134678762b04b3003980b56eb5bcfcd9979d88fb4fe91c1dd85f79727",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a está en implementing con una fila de baseline BLOCKED en su contrato local"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "despacho-con-baseline-blocked"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:978bb905048191c1d67e55efdefeac969997513b8b42d75ca0c28335c9747abe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/divergencia-manifest-plan": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6d72356369ce3722b30339c3c020ec610f7e362956a849de26d310f49062e22f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a vale tasks-ready en el manifest y planned en su plan.md"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "manifest-y-plan-divergen"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:5546f7c67067a7b30e8001ac19aa6123e0f56cbb3b25308723c4879c981e7c0b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:6d72356369ce3722b30339c3c020ec610f7e362956a849de26d310f49062e22f",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-a vale tasks-ready en el manifest y planned en su plan.md"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "manifest-y-plan-divergen"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:5546f7c67067a7b30e8001ac19aa6123e0f56cbb3b25308723c4879c981e7c0b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/done-closeout-unassigned-conac": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3fe464214129f62c810e5414ffcffa50179cd7b32ab82c5847e05231a284550",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:c843f91f3ea2494fb8f9577379d1ede62778dd1aba1d051b5b063b40c6c25501",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 (phase=closeout) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:676355e2e66fc72be593d081a8fbbfa001ab7b0bc24f0af157116efae59be776",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:e3fe464214129f62c810e5414ffcffa50179cd7b32ab82c5847e05231a284550",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:c843f91f3ea2494fb8f9577379d1ede62778dd1aba1d051b5b063b40c6c25501",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 (phase=closeout) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:676355e2e66fc72be593d081a8fbbfa001ab7b0bc24f0af157116efae59be776",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/done-closeout-unassigned-sinac": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:86b10b0667f5cf8737d146beb0c68dddcc04a3a0838817d910bf6967f311b92d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:adcc12b4588ee226fd1a97a68f514f6f8a42f477df5e184da0d94ad0c84644d6",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 (phase=closeout) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:75b93c66af08d472c61547ac5df86fb73349bf8d6c71c85b937ac28fdf59d988",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:86b10b0667f5cf8737d146beb0c68dddcc04a3a0838817d910bf6967f311b92d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:adcc12b4588ee226fd1a97a68f514f6f8a42f477df5e184da0d94ad0c84644d6",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea X1 (phase=closeout) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:75b93c66af08d472c61547ac5df86fb73349bf8d6c71c85b937ac28fdf59d988",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/done-gate-unassigned-conac": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:2cb51afe4587009c06c5e6ee54cd53a745e8d4e74a06e142e7afcc3a6dcb757d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:b0fcf4e5d68d56a803488e2a590d925f67d8ec375f06cc93aa5d90ff549bc4ee",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:63b6e09135960116ef8b904382245f71b6145fe1fc5cfc9b9bd063a54b49be21",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:1ea3cdef778c806b3ae2694d9a190cf1ffadaa5283d9d6df4a3f20536245a687",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:6f3a3ed282d9fa5dec908fd87f528a8b94868a4a83563296716338f45dde6874",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 (phase=gate) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:67a4d577f3982a16cd6e4c5522ef002f3d3fedca53c9a6d6da3547677390b9df",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:2cb51afe4587009c06c5e6ee54cd53a745e8d4e74a06e142e7afcc3a6dcb757d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:b0fcf4e5d68d56a803488e2a590d925f67d8ec375f06cc93aa5d90ff549bc4ee",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:63b6e09135960116ef8b904382245f71b6145fe1fc5cfc9b9bd063a54b49be21",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:1ea3cdef778c806b3ae2694d9a190cf1ffadaa5283d9d6df4a3f20536245a687",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:6f3a3ed282d9fa5dec908fd87f528a8b94868a4a83563296716338f45dde6874",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 (phase=gate) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:67a4d577f3982a16cd6e4c5522ef002f3d3fedca53c9a6d6da3547677390b9df",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/done-gate-unassigned-sinac": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ec2a394f103221b8f63a1e5338aabe61e2f841f74b4e0105e749e2e0cbe04ca8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:421a6de33091448d53f203848d990e6fd221d8e3a16056aa2facf2b2ddcd09da",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 (phase=gate) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:c47bdc1f29399a72330a571888e544b12a4a676d4ee3039653d1051d71184226",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ec2a394f103221b8f63a1e5338aabe61e2f841f74b4e0105e749e2e0cbe04ca8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:421a6de33091448d53f203848d990e6fd221d8e3a16056aa2facf2b2ddcd09da",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 (phase=gate) cerró con owner UNASSIGNED"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "cierre-con-owner-unassigned"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:c47bdc1f29399a72330a571888e544b12a4a676d4ee3039653d1051d71184226",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/done-when-divergente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:f904aa28bcf01e85f76901d1ae009c71fbf15a6592d070e0164c01cc6b586922",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cierra en la fila V-C1 y su done_when dice V-C9"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "done_when-no-referencia-su-fila"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:a56c260f4f548e347dc17cb8c3d8f7c0c6508e62f6d77012c464a805dc9f4a27",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:f904aa28bcf01e85f76901d1ae009c71fbf15a6592d070e0164c01cc6b586922",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cierra en la fila V-C1 y su done_when dice V-C9"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "done_when-no-referencia-su-fila"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:a56c260f4f548e347dc17cb8c3d8f7c0c6508e62f6d77012c464a805dc9f4a27",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/dueno-duplicado": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:64b5df1aeb9c18738a97aed13c33d8cb4eaf91abc83f80935e971921dccd0053",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:19234c41d4515c9c5adf0944b48fb6d52005c9537c5c75d5d126e8c8b9f43749",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "las tareas C1 y X1 declaran el mismo owner equipo-plataforma"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "dueno-duplicado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:a12bb8194db6a8c5db5f63db930acb0b6953a21781df0b19191c16bed5fef028",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:64b5df1aeb9c18738a97aed13c33d8cb4eaf91abc83f80935e971921dccd0053",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:19234c41d4515c9c5adf0944b48fb6d52005c9537c5c75d5d126e8c8b9f43749",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "las tareas C1 y X1 declaran el mismo owner equipo-plataforma"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "dueno-duplicado"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:a12bb8194db6a8c5db5f63db930acb0b6953a21781df0b19191c16bed5fef028",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/esperado-fallido": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:249ca54920549dd58da11db9d59787bd8247ebc664638d67221896f79319411e",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 esperaba [el receptor procesa el evento y responde 200] y observó [el receptor descarta el evento y responde 500]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "esperado-no-satisfecho"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:1874f9884acb6306398d81c0283e05f18aa8812533b36f8ab28f4c14d1bebe04",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:249ca54920549dd58da11db9d59787bd8247ebc664638d67221896f79319411e",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 esperaba [el receptor procesa el evento y responde 200] y observó [el receptor descarta el evento y responde 500]"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "esperado-no-satisfecho"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:1874f9884acb6306398d81c0283e05f18aa8812533b36f8ab28f4c14d1bebe04",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/evidencia-duplicada": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ebba53ac1721e751efd8422d8fad70069effb09f510340c60cb33e91304d92c4",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3b9fc3e731fec91e3a4fc592a053273704305f747c12142b9302387f12f0e0a2",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 la ejecutan 2 eventos de tareas distintas"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-duplicada"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:30e7546b08c15cbfe57967a483988353a0a6a2ece37c061d282a8841fd00752a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:ebba53ac1721e751efd8422d8fad70069effb09f510340c60cb33e91304d92c4",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:3b9fc3e731fec91e3a4fc592a053273704305f747c12142b9302387f12f0e0a2",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 la ejecutan 2 eventos de tareas distintas"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-duplicada"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:30e7546b08c15cbfe57967a483988353a0a6a2ece37c061d282a8841fd00752a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/evidencia-obsoleta": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:9bf723e826f985115311f0e1194f1ced4776cb9db06ead2f1e4cd903793d2320",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cerró sin ningún evento ejecutar-evidencia de su fila V-C1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-obsoleta"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:12a036aae7c02fc40334b8e157bf4901b8ff9ca16729e6d6f6681b7e0e457bdc",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:9bf723e826f985115311f0e1194f1ced4776cb9db06ead2f1e4cd903793d2320",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cerró sin ningún evento ejecutar-evidencia de su fila V-C1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-obsoleta"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:12a036aae7c02fc40334b8e157bf4901b8ff9ca16729e6d6f6681b7e0e457bdc",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/frescura-ancla-ausente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:9c57ddd4637726d84184f43108ebba1482db9b0e1a6d5f60f67ca5bc0e146827",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 no participa ningún repo y su evidencia no declara ancla versionada"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ancla-versionada-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:6e41b39d63ca999de27d5ba8c5d08be220496b8ba0df77e22e4385777c012cfa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:9c57ddd4637726d84184f43108ebba1482db9b0e1a6d5f60f67ca5bc0e146827",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 no participa ningún repo y su evidencia no declara ancla versionada"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ancla-versionada-ausente"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:6e41b39d63ca999de27d5ba8c5d08be220496b8ba0df77e22e4385777c012cfa",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/frescura-ancla-obsoleta": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:1e0aab7d0d8df57af9e9c8756efca7c8b4b551081837d74b5de5d87ed2ecd0d3",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 midió acuerdo-evento en v2 y la vigente es v3"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ancla-versionada-obsoleta"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:bc2b05104d0f6b32fe16eb3f9958e390fa590c661bcb90d8c72047a9afd78a20",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:1e0aab7d0d8df57af9e9c8756efca7c8b4b551081837d74b5de5d87ed2ecd0d3",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea G1 midió acuerdo-evento en v2 y la vigente es v3"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "ancla-versionada-obsoleta"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:bc2b05104d0f6b32fe16eb3f9958e390fa590c661bcb90d8c72047a9afd78a20",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/frescura-fila-equivocada": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:89b4702e026c95192bd6b284405f664f2bb50badc51618746347044b4542ea1c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cierra con V-C1 y su evidencia ejecutó V-Z9"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-otra-fila"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:306c4c6b59329ddb433e8d360ff353469708f8eeaa376e5c2c9a6d2e7b1b7adf",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:89b4702e026c95192bd6b284405f664f2bb50badc51618746347044b4542ea1c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 cierra con V-C1 y su evidencia ejecutó V-Z9"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-otra-fila"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:306c4c6b59329ddb433e8d360ff353469708f8eeaa376e5c2c9a6d2e7b1b7adf",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/frescura-repo-ausente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:416e399062ae92e8fdbc68e7ade2b9df656a9ab278ea9124f75c8feb025b7f5d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 participa servicio-b y su evidencia no lo mide"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-relevante-sin-sha"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:7bb6a26bbc5b6d8db9b6b61c3ddf3c7bd8c557f187be12ef7fa4e23ab1c42c8c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:416e399062ae92e8fdbc68e7ade2b9df656a9ab278ea9124f75c8feb025b7f5d",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 participa servicio-b y su evidencia no lo mide"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-relevante-sin-sha"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:7bb6a26bbc5b6d8db9b6b61c3ddf3c7bd8c557f187be12ef7fa4e23ab1c42c8c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/frescura-repo-movido": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:af11cc03be5095e186de2c4844230d492d0600c747d7063c00bcd05deb393874",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 midió servicio-b en bbb2222 y su plan.md declara bbb9999"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-cambiado-tras-medir"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:62cdacf67eee90c7caad8036a95b09b6581c7db20f44da28a1fe0bb4001384ad",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:af11cc03be5095e186de2c4844230d492d0600c747d7063c00bcd05deb393874",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la tarea C1 midió servicio-b en bbb2222 y su plan.md declara bbb9999"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "repo-cambiado-tras-medir"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:62cdacf67eee90c7caad8036a95b09b6581c7db20f44da28a1fe0bb4001384ad",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/frescura-tarea-equivocada": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:53f1a16fc6f829546023319d947a0954f26875c9ee1c60009f5487f00a6ca5b0",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 de C1 la ejecutó un evento con objeto X1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-otra-tarea"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:cfbc7ab8bc002ce2edd528635761b2fe3f625d6c750af007c5a388b734cb8ee6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:53f1a16fc6f829546023319d947a0954f26875c9ee1c60009f5487f00a6ca5b0",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-C1 de C1 la ejecutó un evento con objeto X1"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-otra-tarea"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:cfbc7ab8bc002ce2edd528635761b2fe3f625d6c750af007c5a388b734cb8ee6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/frescura-valida-ancla-no-codigo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "orchestration-state/frescura-valida-multirepo": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "orchestration-state/frescura-version-anterior": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:2f9f3acdf6e8ac778424eef2a679e2f3a2195daaf0c4814afb53a76b369f5095",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-G1 se midió contra el contrato v1 y la versión vigente es v2"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-version-anterior"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:7f63de7a0cfd8bf055599e025e1d56fc2958d656f47edcbce886c27b3e7efdd4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:2f9f3acdf6e8ac778424eef2a679e2f3a2195daaf0c4814afb53a76b369f5095",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "la fila V-G1 se midió contra el contrato v1 y la versión vigente es v2"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "evidencia-de-version-anterior"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:7f63de7a0cfd8bf055599e025e1d56fc2958d656f47edcbce886c27b3e7efdd4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/gate-abierto-despacho-exitoso": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a32290e247ce709cad5be05f8dd29703c5ae7efbc1d1118e9e17b349b068b5c8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:6396ea2aed3e266c5b9206df77c8febcd0ef56d2457e0b9fcf59cb116190cf9a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b se despachó con 1 gate(s) fuera de done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "despacho-exitoso-con-gate-abierto"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:eab3cfa8cbd8bf76d52d4cde7e0cfe6b4878766bc87f01d1598b5e3e4c0d9180",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a32290e247ce709cad5be05f8dd29703c5ae7efbc1d1118e9e17b349b068b5c8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:6396ea2aed3e266c5b9206df77c8febcd0ef56d2457e0b9fcf59cb116190cf9a",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b se despachó con 1 gate(s) fuera de done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "despacho-exitoso-con-gate-abierto"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:eab3cfa8cbd8bf76d52d4cde7e0cfe6b4878766bc87f01d1598b5e3e4c0d9180",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/gate-abierto-despacho-rechazado": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0c47b02dc7c489956352f073425b2d6c6940baeda81605a0f81e1c451123610b",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0c47b02dc7c489956352f073425b2d6c6940baeda81605a0f81e1c451123610b",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/gate-abierto-repo-planned": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:2675cd557c54400419723e01477436b34d7b1afab0a8639ec27cdc300ad02f62",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:98793faab5ada790887db4856cd4f31a154aeb0cd4020ef2b7328f65b9ca16f0",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:2675cd557c54400419723e01477436b34d7b1afab0a8639ec27cdc300ad02f62",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8feca33d8658615f2f717686da160059169c98efe24bc1500dbb05835cf02ed0",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:98793faab5ada790887db4856cd4f31a154aeb0cd4020ef2b7328f65b9ca16f0",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/gate-cerrado-repo-aun-planned": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:edc14fb92cbc11adb1a009eca462ae4f25cb271fff14fd4e8c1b5856b999dbf5",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7c235dd0702025db1ba5cd4bfa2067fa5377b62e7083593940185a2624c746fe",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b sigue en planned con sus 1 gate(s) en done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "gate-cerrado-sin-promover"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:8a7a5e9acb16714fb0e2a30886c5d414005c2638ab841bfa5f016a87bec4f726",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:edc14fb92cbc11adb1a009eca462ae4f25cb271fff14fd4e8c1b5856b999dbf5",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7c235dd0702025db1ba5cd4bfa2067fa5377b62e7083593940185a2624c746fe",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b sigue en planned con sus 1 gate(s) en done"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "gate-cerrado-sin-promover"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:8a7a5e9acb16714fb0e2a30886c5d414005c2638ab841bfa5f016a87bec4f726",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/gate-cerrado-repo-ready": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:43af7477f42a7cb3f79de77f1da42fc5fb5369b6080d913999b91ba5cfbf4c39",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7810886a0cf10d634ed68337b095023ddbdff3c1f4b8615fa69e48c71cb78d6c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6c903738f621e8199327ef5b3a2c9702e54c715e0fde62821f50fbf2a91b62a5",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:43af7477f42a7cb3f79de77f1da42fc5fb5369b6080d913999b91ba5cfbf4c39",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7810886a0cf10d634ed68337b095023ddbdff3c1f4b8615fa69e48c71cb78d6c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6c903738f621e8199327ef5b3a2c9702e54c715e0fde62821f50fbf2a91b62a5",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/gate-cerrado-sin-despacho": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:087a41d880beff163e3bb6e28b1990c8f041c5d7168b292f4956bd85ce9f3d74",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0a4dc9f7003c15fa92003e05a7cf7d6eae2fe234925a0561f09a6ecd0109d086",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:fae641a107e7e1cdfed6428a572253c008029eb706dcd48841069b5478441e7c",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b se promovió al cerrar su gate y nunca se despachó"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "gate-cerrado-sin-despachar"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:2386ce2b89e275c22e379029346414e730f0ce146c5f850a8d9cec1374149e82",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:087a41d880beff163e3bb6e28b1990c8f041c5d7168b292f4956bd85ce9f3d74",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0a4dc9f7003c15fa92003e05a7cf7d6eae2fe234925a0561f09a6ecd0109d086",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:fae641a107e7e1cdfed6428a572253c008029eb706dcd48841069b5478441e7c",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el repo servicio-b se promovió al cerrar su gate y nunca se despachó"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "gate-cerrado-sin-despachar"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:2386ce2b89e275c22e379029346414e730f0ce146c5f850a8d9cec1374149e82",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/lock-liberacion-rechazada-sin-decision": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:4a1873c84bbfaaec1b0ccb55c672b435c00c8a11c37004bf831677493b322ae9",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6b2abc1b424f7a44ceb3c6e796ab3692bff43d0b32c9b347d34a5ec01b7766e2",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:4a1873c84bbfaaec1b0ccb55c672b435c00c8a11c37004bf831677493b322ae9",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6b2abc1b424f7a44ceb3c6e796ab3692bff43d0b32c9b347d34a5ec01b7766e2",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          }
        },
        "orchestration-state/lock-liberado-sin-decision": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a9051aab80aada714f98c66b3fd59d1a28130901d278b6dffe4b855455d0d004",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 5 liberó el lock de servicio-b sin una decisión registrada antes"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "liberacion-de-lock-sin-decision"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:8b34379bca2af74e3399d2d18b01108c4fd6dfac86ceafb209f6fab73a5f60e6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a9051aab80aada714f98c66b3fd59d1a28130901d278b6dffe4b855455d0d004",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "contexto",
                    "el evento 5 liberó el lock de servicio-b sin una decisión registrada antes"
                  ],
                  [
                    "detalle",
                    ""
                  ],
                  [
                    "hallazgo",
                    "liberacion-de-lock-sin-decision"
                  ],
                  [
                    "manifest",
                    "{dir}/.sdd/notificaciones-v2/manifest.yml"
                  ]
                ],
                "id": "state"
              }
            ],
            "observation_sha256": "sha256:8b34379bca2af74e3399d2d18b01108c4fd6dfac86ceafb209f6fab73a5f60e6",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "orchestration-state/lock-liberado-tras-decision": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:8929b253edb4090f2514557dd5c47e09a1ea0c6ac300ae6faeb05583c8d9c447",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cf6dc457c111e18f78ccb747b6344678297f7d7729dc3e4f4e592a0160f1deb5",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:8929b253edb4090f2514557dd5c47e09a1ea0c6ac300ae6faeb05583c8d9c447",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cf6dc457c111e18f78ccb747b6344678297f7d7729dc3e4f4e592a0160f1deb5",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          }
        },
        "orchestration-state/mixto-2p-1np": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:80a06b2485b22d7efefb96036a564ae35fdab0c1f878063e3dc319e9debbb2f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a06ce0e22a3cc48360b4d4af961828cb27addc41cf422921f8cda0f18e8296ae",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:83ed5ea126481fa405d3cb0855df8394506893c02c76e282cf1d1677f02c35a6",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "servicio-c/.plans/notificaciones-v2/plan.md": "sha256:b3fdd62766ad81147f1927c9154e22d620ae42925dfbbd479e1b85978c19d4e7",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d89a87037f4094e3dfac479ba4a91f8fbbd77a3cb1c4d63dfb9a4a9560635203",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:80a06b2485b22d7efefb96036a564ae35fdab0c1f878063e3dc319e9debbb2f8",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a06ce0e22a3cc48360b4d4af961828cb27addc41cf422921f8cda0f18e8296ae",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:83ed5ea126481fa405d3cb0855df8394506893c02c76e282cf1d1677f02c35a6",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "servicio-c/.plans/notificaciones-v2/plan.md": "sha256:b3fdd62766ad81147f1927c9154e22d620ae42925dfbbd479e1b85978c19d4e7",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d89a87037f4094e3dfac479ba4a91f8fbbd77a3cb1c4d63dfb9a4a9560635203",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "orchestration-state/precedencia-en-curso": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2716a52df41b0cda3ba17863d2e5ad9d956a49567bb6d9f9e05d39091977ddb4",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7daa5197037ee537f94c6b4e1543aaf9fb109037be3d7fd43e0f2209b57fb8d9",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:2716a52df41b0cda3ba17863d2e5ad9d956a49567bb6d9f9e05d39091977ddb4",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7daa5197037ee537f94c6b4e1543aaf9fb109037be3d7fd43e0f2209b57fb8d9",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/precedencia-en-curso-mas-integ-pendiente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a55a8640ff1484df73a14ca5589ba8da33622f46dce7dd726bce83f4f5415dd9",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9708fa9a69d2031b00a3bbc8301b139360701bae443344a2adfb89f5cbfce0e8",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:a55a8640ff1484df73a14ca5589ba8da33622f46dce7dd726bce83f4f5415dd9",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9708fa9a69d2031b00a3bbc8301b139360701bae443344a2adfb89f5cbfce0e8",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/precedencia-failed-mas-integ-pendiente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:f34b26f927c23826922c628054d4f4dca79d557fd5f5e0632f2b2b998e838ce3",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:967adf8b0ff7922e4cd44902bd40fc9f4f9e8f69f23564a5964b8da70352bd68",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e4ea3d28edf67822dbbd345c5e26f38d6a1a009a29f13d0a404949b5e1c298cc",
            "stdout_sha256": "sha256:f0251aafe0e429fc4e5ba36d3d0020fba7b6d3233f873fc85b2b489f37b26257"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:f34b26f927c23826922c628054d4f4dca79d557fd5f5e0632f2b2b998e838ce3",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:967adf8b0ff7922e4cd44902bd40fc9f4f9e8f69f23564a5964b8da70352bd68",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e4ea3d28edf67822dbbd345c5e26f38d6a1a009a29f13d0a404949b5e1c298cc",
            "stdout_sha256": "sha256:f0251aafe0e429fc4e5ba36d3d0020fba7b6d3233f873fc85b2b489f37b26257"
          }
        },
        "orchestration-state/precedencia-failed-mas-repo-blocked": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:40c47074f3d1129958d7c0a64be821f15eb6c81593246aa356ee3d35f3b3f50f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0d452490be1aa8f945fb05f9b23c2294029186761921613cd592cd78fa7fdefc",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:967adf8b0ff7922e4cd44902bd40fc9f4f9e8f69f23564a5964b8da70352bd68",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:cdda88ce202d05a7517aea0311eaac1b2207c79a3b226b39724b1faac2e872df",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f49ce60528260345ecf549b18f529924745fdaa9c9d3e3e857a594268cb5f5dd",
            "stdout_sha256": "sha256:f0251aafe0e429fc4e5ba36d3d0020fba7b6d3233f873fc85b2b489f37b26257"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:40c47074f3d1129958d7c0a64be821f15eb6c81593246aa356ee3d35f3b3f50f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:0d452490be1aa8f945fb05f9b23c2294029186761921613cd592cd78fa7fdefc",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:967adf8b0ff7922e4cd44902bd40fc9f4f9e8f69f23564a5964b8da70352bd68",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:cdda88ce202d05a7517aea0311eaac1b2207c79a3b226b39724b1faac2e872df",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f49ce60528260345ecf549b18f529924745fdaa9c9d3e3e857a594268cb5f5dd",
            "stdout_sha256": "sha256:f0251aafe0e429fc4e5ba36d3d0020fba7b6d3233f873fc85b2b489f37b26257"
          }
        },
        "orchestration-state/precedencia-gate-blocked": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0bb9271d55fe4d98d66834906d153978dcce165dfa233f01bd5f5d56ce0edf1f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:5492c68a70487634770e0b2afa4ee1b6e0d9e9f12b2eede245798cca3fa4d1cb",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0bb9271d55fe4d98d66834906d153978dcce165dfa233f01bd5f5d56ce0edf1f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:673012bac13740fd89e28755f6989561869c22ddc54c24772ff59775e96c669b",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:5492c68a70487634770e0b2afa4ee1b6e0d9e9f12b2eede245798cca3fa4d1cb",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          }
        },
        "orchestration-state/precedencia-gate-blocked-mas-en-curso": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0bb9271d55fe4d98d66834906d153978dcce165dfa233f01bd5f5d56ce0edf1f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8b0d3504a752bc7e232643f34617956bb72499a36b81b7bf5abcdf2873794f86",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b00e72fc7dc742c8233b6382355a6c7c122e47992c4f00ae924f31e837768145",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7464a8b0f473c93186695b4372cca2c3090e046238a5e8d4f4ad9417c30c5a77",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:0bb9271d55fe4d98d66834906d153978dcce165dfa233f01bd5f5d56ce0edf1f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:8b0d3504a752bc7e232643f34617956bb72499a36b81b7bf5abcdf2873794f86",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b00e72fc7dc742c8233b6382355a6c7c122e47992c4f00ae924f31e837768145",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7464a8b0f473c93186695b4372cca2c3090e046238a5e8d4f4ad9417c30c5a77",
            "stdout_sha256": "sha256:b9ef9685f727026b9bdb70b7f70ae3fc42dbfb2cb278e6d56c8e9e2f8914d79c"
          }
        },
        "orchestration-state/precedencia-integracion-pendiente": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:613bd1b68dbd99f45845cbb386ec480e78b9dad804a35669d1ba69ee057172a2",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1ab63f61c5702f5f496657c1b2011bd4b3f8f511508ec6ede33cc441cbc0e5fe",
            "stdout_sha256": "sha256:c4389643dbf6546762ff49bf27fc4035485882ea00369692213b26fd77120da3"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:a4c9b5b6abe092bbb18a2a61430332bb2cd529cdf2bc86552bd75cd5beb9188c",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:613bd1b68dbd99f45845cbb386ec480e78b9dad804a35669d1ba69ee057172a2",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1ab63f61c5702f5f496657c1b2011bd4b3f8f511508ec6ede33cc441cbc0e5fe",
            "stdout_sha256": "sha256:c4389643dbf6546762ff49bf27fc4035485882ea00369692213b26fd77120da3"
          }
        },
        "orchestration-state/precedencia-repo-blocked": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:40c47074f3d1129958d7c0a64be821f15eb6c81593246aa356ee3d35f3b3f50f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:787530fe23ab7edf605623097407bae7bd9e171dab1aa4c5b471aae4ccf66026",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:cdda88ce202d05a7517aea0311eaac1b2207c79a3b226b39724b1faac2e872df",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3e81535c397498cb5f27c8be9ec67e9b26ecc2ee41bd78122c285704cc722661",
            "stdout_sha256": "sha256:64511cd64eec17c66ca41f6728ad5148c13b6382869e9895439e1ff45ee9dbeb"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:40c47074f3d1129958d7c0a64be821f15eb6c81593246aa356ee3d35f3b3f50f",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:787530fe23ab7edf605623097407bae7bd9e171dab1aa4c5b471aae4ccf66026",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:cdda88ce202d05a7517aea0311eaac1b2207c79a3b226b39724b1faac2e872df",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3e81535c397498cb5f27c8be9ec67e9b26ecc2ee41bd78122c285704cc722661",
            "stdout_sha256": "sha256:64511cd64eec17c66ca41f6728ad5148c13b6382869e9895439e1ff45ee9dbeb"
          }
        },
        "orchestration-state/precedencia-repo-blocked-mas-gate-blocked": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:cf1a21bd3be9ac1e3ad51c8e24dce71f127911be93c20268584ec07d1f49fcc3",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:43d2e28de7c39e4ce25573c4690b56e9646bbfedc4c57bfdc4f874972793e420",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:cdda88ce202d05a7517aea0311eaac1b2207c79a3b226b39724b1faac2e872df",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:549160080eac5e51981a5dc4a19e631174163e54d52e17814e278bb3f5965f52",
            "stdout_sha256": "sha256:64511cd64eec17c66ca41f6728ad5148c13b6382869e9895439e1ff45ee9dbeb"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:cf1a21bd3be9ac1e3ad51c8e24dce71f127911be93c20268584ec07d1f49fcc3",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:43d2e28de7c39e4ce25573c4690b56e9646bbfedc4c57bfdc4f874972793e420",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:cdda88ce202d05a7517aea0311eaac1b2207c79a3b226b39724b1faac2e872df",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:549160080eac5e51981a5dc4a19e631174163e54d52e17814e278bb3f5965f52",
            "stdout_sha256": "sha256:64511cd64eec17c66ca41f6728ad5148c13b6382869e9895439e1ff45ee9dbeb"
          }
        },
        "orchestration-state/precedencia-repo-failed": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:36bded11a84448f23677d6add649f100e05590aee69aa839be2bbaf7d0deaf82",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:967adf8b0ff7922e4cd44902bd40fc9f4f9e8f69f23564a5964b8da70352bd68",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f298b3f06dcaa464d164ef2a7afa51415f03ec59c72d4998c5eaf2c6ae3875d4",
            "stdout_sha256": "sha256:f0251aafe0e429fc4e5ba36d3d0020fba7b6d3233f873fc85b2b489f37b26257"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:36bded11a84448f23677d6add649f100e05590aee69aa839be2bbaf7d0deaf82",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:967adf8b0ff7922e4cd44902bd40fc9f4f9e8f69f23564a5964b8da70352bd68",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f298b3f06dcaa464d164ef2a7afa51415f03ec59c72d4998c5eaf2c6ae3875d4",
            "stdout_sha256": "sha256:f0251aafe0e429fc4e5ba36d3d0020fba7b6d3233f873fc85b2b489f37b26257"
          }
        },
        "orchestration-state/precedencia-todo-done": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:639b32c98474a7e6d054869a3bc3d245d48a0a4389c4e700242d3a82a9bbe441",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:33e66d9f71fafa4781366a9924d980a16da4db736a2725174edfd1387b46665c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:2753092f4af9aa12f88fddc2bac3d6f7a69b56b3a0d155dd051cfebe132e9b11",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:bac313a90da0dd99d61cce11d01dbf54f5bc049077f89ab58521916a12e2c0b1",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8dc0dd52d4b8c3d8ceb3601d90abceb12b059566bebd89e8a1cc37044cbb6faa",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "orchestration-state/promocion-tras-gate": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:43af7477f42a7cb3f79de77f1da42fc5fb5369b6080d913999b91ba5cfbf4c39",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7810886a0cf10d634ed68337b095023ddbdff3c1f4b8615fa69e48c71cb78d6c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6c903738f621e8199327ef5b3a2c9702e54c715e0fde62821f50fbf2a91b62a5",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:43af7477f42a7cb3f79de77f1da42fc5fb5369b6080d913999b91ba5cfbf4c39",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:7810886a0cf10d634ed68337b095023ddbdff3c1f4b8615fa69e48c71cb78d6c",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:ac173727e80225fc63ba9dc6d1e890bab14555f75a62557773dff67e8db9425e",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6c903738f621e8199327ef5b3a2c9702e54c715e0fde62821f50fbf2a91b62a5",
            "stdout_sha256": "sha256:373f863b8ac9d9ed50d35175f04038a2f8d696816d9d13594fbbcdf5e7506434"
          }
        },
        "orchestration-state/reparto-owner-unassigned": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:e7e1cdebb9bdedd167b5002a8a4363a6f4c3ef8120aed681fa935ce1fbb380fa",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7ba0a6ad958737bcf3674d535f98924f72d834b34eae136ebdf81e6251dfb258",
            "stdout_sha256": "sha256:8f9d9dcf21957604159af3355b7332eeb1a418d584cb0dfcac5fa201469c25a9"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:357d3e80b5822ddda77db50550d8d56a9aa69bd2da98e6b06584f50a1b437043",
              ".sdd/notificaciones-v2/integracion.md": "sha256:6d127d5e42f127c36060b2b63af1a6c710ed3579114043b6e5df3ca81101b39e",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:e7e1cdebb9bdedd167b5002a8a4363a6f4c3ef8120aed681fa935ce1fbb380fa",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:1886554807958b581db61589e003275703d83a3c527a90a66630f3dcd3ee196b",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:927a932fb8b79d6234528dca42ee19191e8ac19dc801347e4ab53adfb5ce9b87",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:e8a42b3fbfaea426eb3a0ff6100098115b81e2defec12e8064588677b06b415f",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:7ba0a6ad958737bcf3674d535f98924f72d834b34eae136ebdf81e6251dfb258",
            "stdout_sha256": "sha256:8f9d9dcf21957604159af3355b7332eeb1a418d584cb0dfcac5fa201469c25a9"
          }
        },
        "orchestration-state/retrocompat": {
          "new": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:f79d67311399b08d0e3a6846b2f3227f6bafcc01772b038ee2471c48338193ae",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8e52ffaf7220553bfed82c963f367484950b89f38e5690c9ad2b3f0c0384768f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:766d03dc461dcbb8732fc4fc23c3846ce60b77281bd6b670319d9fb41edf8459",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:91db5c1c24ec64677017d796869218b94762104540f963e99e15a91b4f3ad190",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b5d4ee128380226aa949f5209fa646e03d2b78f41c5f9c87e4e0371065b82381",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2bf2b66112394225944f9d97c531194c49040485799b6ea5c2ed72f28aa584f4",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          },
          "old": {
            "artifacts": {
              ".sdd/notificaciones-v2/bitacora.md": "sha256:f79d67311399b08d0e3a6846b2f3227f6bafcc01772b038ee2471c48338193ae",
              ".sdd/notificaciones-v2/integracion.md": "sha256:8e52ffaf7220553bfed82c963f367484950b89f38e5690c9ad2b3f0c0384768f",
              ".sdd/notificaciones-v2/manifest.yml": "sha256:766d03dc461dcbb8732fc4fc23c3846ce60b77281bd6b670319d9fb41edf8459",
              ".sdd/notificaciones-v2/master-spec.md": "sha256:91db5c1c24ec64677017d796869218b94762104540f963e99e15a91b4f3ad190",
              "servicio-a/.plans/notificaciones-v2/plan.md": "sha256:b5d4ee128380226aa949f5209fa646e03d2b78f41c5f9c87e4e0371065b82381",
              "servicio-b/.plans/notificaciones-v2/plan.md": "sha256:d3ea3767c1148dcbd43a10222d2e2870fdd8e25048c14e6d3e1f01387e44a746",
              "skill/SKILL.md": "sha256:eda3b5542493a2ac1a66c0bafde2fe88276026395781a7797547aff24ee28e54"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:2bf2b66112394225944f9d97c531194c49040485799b6ea5c2ed72f28aa584f4",
            "stdout_sha256": "sha256:491d4a20831a2adfb0a9470835e9f69926827ddc611969b58a59340f49ffc5a1"
          }
        },
        "ownership-log/checkid-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:4c40e0e19adb4107329ab7fc5f57ef032475347603f30c9857928da99b352bad"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:798c8ed764a3b91d7894c00e9bf6c6eed444d31650486048fc2b05fa6f6ae18c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:4c40e0e19adb4107329ab7fc5f57ef032475347603f30c9857928da99b352bad"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:798c8ed764a3b91d7894c00e9bf6c6eed444d31650486048fc2b05fa6f6ae18c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/clase-bogus": {
          "new": {
            "artifacts": {
              "log.md": "sha256:f0f3295a0ad8192c809f16652b208814e9a55e5ee753c3295fb5f440fcf8c391"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "BOGUS"
                  ]
                ],
                "id": "clase-invalida"
              }
            ],
            "observation_sha256": "sha256:378cc5a1ab7a565f3e4a498dcb242c5235def6fde8b715b70b5f551cf71c2dbe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:f0f3295a0ad8192c809f16652b208814e9a55e5ee753c3295fb5f440fcf8c391"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "BOGUS"
                  ]
                ],
                "id": "clase-invalida"
              }
            ],
            "observation_sha256": "sha256:378cc5a1ab7a565f3e4a498dcb242c5235def6fde8b715b70b5f551cf71c2dbe",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/clase-minuscula": {
          "new": {
            "artifacts": {
              "log.md": "sha256:b00893580639abffbba625cc9b053bd7cba8cda1e7255c914ca4c2fe010ec3aa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "verification_defect"
                  ]
                ],
                "id": "clase-invalida"
              }
            ],
            "observation_sha256": "sha256:9cbed99f159b2f1fa4e5ed93fdd2e63ef43b1d80096cf8ad3897e2877a84ed40",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:b00893580639abffbba625cc9b053bd7cba8cda1e7255c914ca4c2fe010ec3aa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "verification_defect"
                  ]
                ],
                "id": "clase-invalida"
              }
            ],
            "observation_sha256": "sha256:9cbed99f159b2f1fa4e5ed93fdd2e63ef43b1d80096cf8ad3897e2877a84ed40",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/consumed-round-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:0606637d9e32d339f68e52fdc95725d4115450cd9e3fbb90ffd62a2f5401e8d7"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "IMPLEMENTATION_DEFECT"
                  ],
                  [
                    "cr",
                    "Sí"
                  ],
                  [
                    "esp",
                    "sí"
                  ]
                ],
                "id": "consumed-round-incoherente"
              }
            ],
            "observation_sha256": "sha256:463686c20a550f9a0634de3923b7e8449c30614dca7f994e84e0208a5052027e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:0606637d9e32d339f68e52fdc95725d4115450cd9e3fbb90ffd62a2f5401e8d7"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "IMPLEMENTATION_DEFECT"
                  ],
                  [
                    "cr",
                    "Sí"
                  ],
                  [
                    "esp",
                    "sí"
                  ]
                ],
                "id": "consumed-round-incoherente"
              }
            ],
            "observation_sha256": "sha256:463686c20a550f9a0634de3923b7e8449c30614dca7f994e84e0208a5052027e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/consumed-round-incoherente": {
          "new": {
            "artifacts": {
              "log.md": "sha256:277cc0db0725a564b190a6846f155e25526942e61cfaeab25a8c03dd0d735cc4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "IMPLEMENTATION_DEFECT"
                  ],
                  [
                    "cr",
                    "no"
                  ],
                  [
                    "esp",
                    "sí"
                  ]
                ],
                "id": "consumed-round-incoherente"
              }
            ],
            "observation_sha256": "sha256:0988301d17f6f00872805207ab5722ff281d5816ec7d3837c3920b3747d86b85",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:277cc0db0725a564b190a6846f155e25526942e61cfaeab25a8c03dd0d735cc4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "clase",
                    "IMPLEMENTATION_DEFECT"
                  ],
                  [
                    "cr",
                    "no"
                  ],
                  [
                    "esp",
                    "sí"
                  ]
                ],
                "id": "consumed-round-incoherente"
              }
            ],
            "observation_sha256": "sha256:0988301d17f6f00872805207ab5722ff281d5816ec7d3837c3920b3747d86b85",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/delta-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:4826c8db9a63b3d5949a6a1f083bc82022a3e23ea6fe78797dac79e95fb7deff"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8b7f46bbe4d78ca84aa9d5827a4478d7b00ff022ee4fcf1131420775418bd116",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:4826c8db9a63b3d5949a6a1f083bc82022a3e23ea6fe78797dac79e95fb7deff"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:8b7f46bbe4d78ca84aa9d5827a4478d7b00ff022ee4fcf1131420775418bd116",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/delta-en-dos-rondas": {
          "new": {
            "artifacts": {
              "log.md": "sha256:cb52dd148e68a8c09b53883420428cb14da326e7daf4f2469ce3d811a4c81a0a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "deltas",
                    "D1 en 2 rondas"
                  ]
                ],
                "id": "delta-una-ronda"
              }
            ],
            "observation_sha256": "sha256:3f026d8f7d0142196a690be28c5527082d6a675960711c8ce5e0040cbec0df4b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:cb52dd148e68a8c09b53883420428cb14da326e7daf4f2469ce3d811a4c81a0a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "deltas",
                    "D1 en 2 rondas"
                  ]
                ],
                "id": "delta-una-ronda"
              }
            ],
            "observation_sha256": "sha256:3f026d8f7d0142196a690be28c5527082d6a675960711c8ce5e0040cbec0df4b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/delta-impar": {
          "new": {
            "artifacts": {
              "log.md": "sha256:8eb1177ae7b9556451371ce1ede2e8ba0c55e3f2875d90c52192b96cb959b05a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "deltas",
                    "D1 en 3 rondas"
                  ]
                ],
                "id": "delta-una-ronda"
              }
            ],
            "observation_sha256": "sha256:195833f35224af551b065367a1e63428eda3bb339317f05a17df0de6ed19a583",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:8eb1177ae7b9556451371ce1ede2e8ba0c55e3f2875d90c52192b96cb959b05a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "deltas",
                    "D1 en 3 rondas"
                  ]
                ],
                "id": "delta-una-ronda"
              }
            ],
            "observation_sha256": "sha256:195833f35224af551b065367a1e63428eda3bb339317f05a17df0de6ed19a583",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/delta-par": {
          "new": {
            "artifacts": {
              "log.md": "sha256:3b4b7654d9d8dc5da2592eaa62d124835c44b7d8d1ad574fb21398093be04534"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0dfac645efd4953f365942c365b951598122bcd8a68a86013bd1bb5469b41981",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:3b4b7654d9d8dc5da2592eaa62d124835c44b7d8d1ad574fb21398093be04534"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:0dfac645efd4953f365942c365b951598122bcd8a68a86013bd1bb5469b41981",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/delta-singleton": {
          "new": {
            "artifacts": {
              "log.md": "sha256:e4557cfabe7aa2bf4eba314114e3d93d1a93f67e399d32619f7579035692ad09"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c1a86bd7205a7defc5b1cc6b8938b43edf45ee69e9565b9a8142a8ee72cb20f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:e4557cfabe7aa2bf4eba314114e3d93d1a93f67e399d32619f7579035692ad09"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c1a86bd7205a7defc5b1cc6b8938b43edf45ee69e9565b9a8142a8ee72cb20f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/delta-vacio": {
          "new": {
            "artifacts": {
              "log.md": "sha256:9b890bc868c74120e8b79e953c7c26f0a018a5eb87b71177d08649f0b6bd8635"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f14460da3264bd197139c50739769147f2c0f4e29badfcbf356d8759989bab2b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:9b890bc868c74120e8b79e953c7c26f0a018a5eb87b71177d08649f0b6bd8635"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f14460da3264bd197139c50739769147f2c0f4e29badfcbf356d8759989bab2b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/evidencia-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:14849844fc18e2ac8a36b91dabdbae2ad6b8cef723dcc98d8ec9d169e1f00420"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "sin-evidencia"
              }
            ],
            "observation_sha256": "sha256:be369c4b754b296990b4376b97dd538f00e38c8ce567d113494db3f697bcbce9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:14849844fc18e2ac8a36b91dabdbae2ad6b8cef723dcc98d8ec9d169e1f00420"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "sin-evidencia"
              }
            ],
            "observation_sha256": "sha256:be369c4b754b296990b4376b97dd538f00e38c8ce567d113494db3f697bcbce9",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/positivo": {
          "new": {
            "artifacts": {
              "log.md": "sha256:e4557cfabe7aa2bf4eba314114e3d93d1a93f67e399d32619f7579035692ad09"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c1a86bd7205a7defc5b1cc6b8938b43edf45ee69e9565b9a8142a8ee72cb20f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:e4557cfabe7aa2bf4eba314114e3d93d1a93f67e399d32619f7579035692ad09"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c1a86bd7205a7defc5b1cc6b8938b43edf45ee69e9565b9a8142a8ee72cb20f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/razon-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:fcf8ec5bba1e839c369031a631f17555cec82bead14d68121914980c8291e05b"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "n",
                    "2"
                  ]
                ],
                "id": "razon-ausente"
              }
            ],
            "observation_sha256": "sha256:5da8e6c8478da89e8e256170da25eb293b8a6732c8f3e5e629128edbda5ac83a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:fcf8ec5bba1e839c369031a631f17555cec82bead14d68121914980c8291e05b"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "n",
                    "2"
                  ]
                ],
                "id": "razon-ausente"
              }
            ],
            "observation_sha256": "sha256:5da8e6c8478da89e8e256170da25eb293b8a6732c8f3e5e629128edbda5ac83a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/razon-generica": {
          "new": {
            "artifacts": {
              "log.md": "sha256:84e051b3b48af35121c63f8d5976add3e2122a66a15e172bb236741c9ff5ffd6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "razon-no-falsable"
              }
            ],
            "observation_sha256": "sha256:6e59118b62244dce9c5207735dad78f0b1fda5cdaf11c98b9c2b362148262676",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:84e051b3b48af35121c63f8d5976add3e2122a66a15e172bb236741c9ff5ffd6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "razon-no-falsable"
              }
            ],
            "observation_sha256": "sha256:6e59118b62244dce9c5207735dad78f0b1fda5cdaf11c98b9c2b362148262676",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/razon-generica-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:a89865b6509b663881fba609180f77c66ee796cd8345a04147e038915acf13eb"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "razon-no-falsable"
              }
            ],
            "observation_sha256": "sha256:36d351019a7897ed95390e0c8381c40141716095f2f078e631fa6f74bcdce662",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:a89865b6509b663881fba609180f77c66ee796cd8345a04147e038915acf13eb"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "razon-no-falsable"
              }
            ],
            "observation_sha256": "sha256:36d351019a7897ed95390e0c8381c40141716095f2f078e631fa6f74bcdce662",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/razon-impar": {
          "new": {
            "artifacts": {
              "log.md": "sha256:65ab8cc54d203b9d1abe396d63f3b53604ded2f9596b04693847c6d0d863686a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "n",
                    "3"
                  ]
                ],
                "id": "razon-ausente"
              }
            ],
            "observation_sha256": "sha256:b14e6493a990d551ef6128dea80504c3d61777db3fcdb3da3bb1cdec7d31fbac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:65ab8cc54d203b9d1abe396d63f3b53604ded2f9596b04693847c6d0d863686a"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "n",
                    "3"
                  ]
                ],
                "id": "razon-ausente"
              }
            ],
            "observation_sha256": "sha256:b14e6493a990d551ef6128dea80504c3d61777db3fcdb3da3bb1cdec7d31fbac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/razon-par": {
          "new": {
            "artifacts": {
              "log.md": "sha256:0799f8f37e518ab5678b07f8623e66f21ad97ea3cb1f3ce3293014c5cec0ceef"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1d729210d08cb4aa1809e4e2af4f9a85afba5576e7d3fa19e82d5a014823c59c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:0799f8f37e518ab5678b07f8623e66f21ad97ea3cb1f3ce3293014c5cec0ceef"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1d729210d08cb4aa1809e4e2af4f9a85afba5576e7d3fa19e82d5a014823c59c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/razon-singleton": {
          "new": {
            "artifacts": {
              "log.md": "sha256:e4557cfabe7aa2bf4eba314114e3d93d1a93f67e399d32619f7579035692ad09"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c1a86bd7205a7defc5b1cc6b8938b43edf45ee69e9565b9a8142a8ee72cb20f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:e4557cfabe7aa2bf4eba314114e3d93d1a93f67e399d32619f7579035692ad09"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3c1a86bd7205a7defc5b1cc6b8938b43edf45ee69e9565b9a8142a8ee72cb20f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/razon-vacio": {
          "new": {
            "artifacts": {
              "log.md": "sha256:64fb5cba00837762309f8c20da67c7a7cb29d63f4916c8d95728d44ca414c4c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e6cb6c156e74d96e937f022eb760a47959b54482c1459cd4313acad26c872838",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:64fb5cba00837762309f8c20da67c7a7cb29d63f4916c8d95728d44ca414c4c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e6cb6c156e74d96e937f022eb760a47959b54482c1459cd4313acad26c872838",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/segunda-sin-razon": {
          "new": {
            "artifacts": {
              "log.md": "sha256:521e4ca37b5a8ec1887a6a9fc021b3f84c96e616603531b5130501de3d5b5ce6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "n",
                    "2"
                  ]
                ],
                "id": "razon-ausente"
              }
            ],
            "observation_sha256": "sha256:b3881a78c02db0878ec7e4dd169f0c5a2783d7f972931cd1dbe855b2f9caea53",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:521e4ca37b5a8ec1887a6a9fc021b3f84c96e616603531b5130501de3d5b5ce6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ],
                  [
                    "n",
                    "2"
                  ]
                ],
                "id": "razon-ausente"
              }
            ],
            "observation_sha256": "sha256:b3881a78c02db0878ec7e4dd169f0c5a2783d7f972931cd1dbe855b2f9caea53",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-log/sin-campo-evidencia": {
          "new": {
            "artifacts": {
              "log.md": "sha256:6d4a2ca7634ad45e949e8bda4f471d752c00810d05f5235b8b7e47ed73b85dce"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "sin-evidencia"
              }
            ],
            "observation_sha256": "sha256:d237e2669adb4406b0985b0d6c69a0bea3b8614a101e809d4f0f945812dc89e8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:6d4a2ca7634ad45e949e8bda4f471d752c00810d05f5235b8b7e47ed73b85dce"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "check",
                    "V1"
                  ]
                ],
                "id": "sin-evidencia"
              }
            ],
            "observation_sha256": "sha256:d237e2669adb4406b0985b0d6c69a0bea3b8614a101e809d4f0f945812dc89e8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-presupuesto/cardinalidad-impar": {
          "new": {
            "artifacts": {
              "log.md": "sha256:7a4bea6b5c98b547eae10ccc575e2824244e35ab7118cb0a656637073aa241ed"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "excesos",
                    "V1 · VERIFICATION_DEFECT · 3 > 2"
                  ]
                ],
                "id": "presupuesto-excedido"
              }
            ],
            "observation_sha256": "sha256:e0fc2ebc53a0fdf018e5df46ad15e18ce83c1aa72a98afd8fa2c43d77a467376",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:7a4bea6b5c98b547eae10ccc575e2824244e35ab7118cb0a656637073aa241ed"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "excesos",
                    "V1 · VERIFICATION_DEFECT · 3 > 2"
                  ]
                ],
                "id": "presupuesto-excedido"
              }
            ],
            "observation_sha256": "sha256:e0fc2ebc53a0fdf018e5df46ad15e18ce83c1aa72a98afd8fa2c43d77a467376",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-presupuesto/cardinalidad-par": {
          "new": {
            "artifacts": {
              "log.md": "sha256:423dbdd818ea6f0369cfad5b232bb02629a155b38e7dbfe9256ecc78bc48c110"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6f4223fc0b78c8ecce46cf592710ce9edc1619e63a91bd94bd4b3edd3f510b8b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:423dbdd818ea6f0369cfad5b232bb02629a155b38e7dbfe9256ecc78bc48c110"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6f4223fc0b78c8ecce46cf592710ce9edc1619e63a91bd94bd4b3edd3f510b8b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-presupuesto/clase-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:06d214720e184e87d87a5f04ee234af674e5c09d831f96cc28b71d52d7e18f2f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3e70c19a0886f4b325868100b5ca873f1c0188d8139cd6ebabe1e16bd894de2c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:06d214720e184e87d87a5f04ee234af674e5c09d831f96cc28b71d52d7e18f2f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:3e70c19a0886f4b325868100b5ca873f1c0188d8139cd6ebabe1e16bd894de2c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-presupuesto/design-gap-repetido": {
          "new": {
            "artifacts": {
              "log.md": "sha256:e9aecbf4be046db893c1c2b6b0f8a0474a13b481d9bad444600815f40d40ad3e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "excesos",
                    "V1 · DESIGN_GAP · 2 > 1"
                  ]
                ],
                "id": "presupuesto-excedido"
              }
            ],
            "observation_sha256": "sha256:06cfeed92dc0f1b314f109750cb1681e706f9adc44010fa0e4d5aecedfa689dd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:e9aecbf4be046db893c1c2b6b0f8a0474a13b481d9bad444600815f40d40ad3e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "excesos",
                    "V1 · DESIGN_GAP · 2 > 1"
                  ]
                ],
                "id": "presupuesto-excedido"
              }
            ],
            "observation_sha256": "sha256:06cfeed92dc0f1b314f109750cb1681e706f9adc44010fa0e4d5aecedfa689dd",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-presupuesto/positivo": {
          "new": {
            "artifacts": {
              "log.md": "sha256:9d959165999a2f66b0fa437853b46fb8832952e96dc41a6ed1e2279667111822"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:97325fb5b6dd491542329601378e64382786f67a99daab6bb53aef2f1bf71d79",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:9d959165999a2f66b0fa437853b46fb8832952e96dc41a6ed1e2279667111822"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:97325fb5b6dd491542329601378e64382786f67a99daab6bb53aef2f1bf71d79",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-presupuesto/singleton": {
          "new": {
            "artifacts": {
              "log.md": "sha256:9b890bc868c74120e8b79e953c7c26f0a018a5eb87b71177d08649f0b6bd8635"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f14460da3264bd197139c50739769147f2c0f4e29badfcbf356d8759989bab2b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:9b890bc868c74120e8b79e953c7c26f0a018a5eb87b71177d08649f0b6bd8635"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f14460da3264bd197139c50739769147f2c0f4e29badfcbf356d8759989bab2b",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "ownership-presupuesto/vacio": {
          "new": {
            "artifacts": {
              "log.md": "sha256:64fb5cba00837762309f8c20da67c7a7cb29d63f4916c8d95728d44ca414c4c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e6cb6c156e74d96e937f022eb760a47959b54482c1459cd4313acad26c872838",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:64fb5cba00837762309f8c20da67c7a7cb29d63f4916c8d95728d44ca414c4c0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:e6cb6c156e74d96e937f022eb760a47959b54482c1459cd4313acad26c872838",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/hash-casing": {
          "new": {
            "artifacts": {
              "scratch/paquete-demo-v1.txt": "sha256:590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actual",
                    "590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
                  ],
                  [
                    "esperado",
                    "590423528A8F5265B54A107BCBE6EBEB0A95F082ABFB8A48D95D74789A8C64F1"
                  ]
                ],
                "id": "paquete-inmutable"
              }
            ],
            "observation_sha256": "sha256:3f35cd8af88720b62d857695acb87a2ae320a23d73730b418ade896ad486f7d2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/paquete-demo-v1.txt": "sha256:590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actual",
                    "590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
                  ],
                  [
                    "esperado",
                    "590423528A8F5265B54A107BCBE6EBEB0A95F082ABFB8A48D95D74789A8C64F1"
                  ]
                ],
                "id": "paquete-inmutable"
              }
            ],
            "observation_sha256": "sha256:3f35cd8af88720b62d857695acb87a2ae320a23d73730b418ade896ad486f7d2",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/paquete-modificado": {
          "new": {
            "artifacts": {
              "scratch/paquete-demo-v1.txt": "sha256:590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actual",
                    "590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
                  ],
                  [
                    "esperado",
                    "1111111111111111111111111111111111111111111111111111111111111111"
                  ]
                ],
                "id": "paquete-inmutable"
              }
            ],
            "observation_sha256": "sha256:9019a49916c2deea710fa150eaa21bcd105cccd8ef15a27239d667c02015bf01",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/paquete-demo-v1.txt": "sha256:590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "actual",
                    "590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
                  ],
                  [
                    "esperado",
                    "1111111111111111111111111111111111111111111111111111111111111111"
                  ]
                ],
                "id": "paquete-inmutable"
              }
            ],
            "observation_sha256": "sha256:9019a49916c2deea710fa150eaa21bcd105cccd8ef15a27239d667c02015bf01",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/positivo": {
          "new": {
            "artifacts": {
              "scratch/paquete-demo-v1.txt": "sha256:590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:037d0fa4428d61387dc8f2372be3cacaa5198f7f522b2bfb73b999e5b1d437de",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/paquete-demo-v1.txt": "sha256:590423528a8f5265b54a107bcbe6ebeb0a95f082abfb8a48d95d74789a8c64f1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:037d0fa4428d61387dc8f2372be3cacaa5198f7f522b2bfb73b999e5b1d437de",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/redespacho-0": {
          "new": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:b677320c8f0e6acdee86f67e7b61eb31d52ad4dd3ffc60f031f6c5c47e3dad8f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:bb4730fcb0f5b0c092e237336defabf59f19c76ddaec133e1a8622b26692353c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:b677320c8f0e6acdee86f67e7b61eb31d52ad4dd3ffc60f031f6c5c47e3dad8f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:bb4730fcb0f5b0c092e237336defabf59f19c76ddaec133e1a8622b26692353c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/redespacho-1": {
          "new": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:b677320c8f0e6acdee86f67e7b61eb31d52ad4dd3ffc60f031f6c5c47e3dad8f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "1"
                  ]
                ],
                "id": "truncado-alcanza-versiones"
              }
            ],
            "observation_sha256": "sha256:33c50a73722a9715f53fa8fef38635c6f65e1a8f72a3556b28aaa8440b5d4361",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:b677320c8f0e6acdee86f67e7b61eb31d52ad4dd3ffc60f031f6c5c47e3dad8f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "1"
                  ]
                ],
                "id": "truncado-alcanza-versiones"
              }
            ],
            "observation_sha256": "sha256:33c50a73722a9715f53fa8fef38635c6f65e1a8f72a3556b28aaa8440b5d4361",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/truncado-impar": {
          "new": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7",
              "scratch/paquete-demo-v3.txt": "sha256:0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f",
              "scratch/paquete-demo-v4.txt": "sha256:a3a5e715f0cc574a73c3f9bebb6bc24f32ffd5b67b387244c2c909da779a1478"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "3"
                  ]
                ],
                "id": "truncado-alcanza-versiones"
              }
            ],
            "observation_sha256": "sha256:0120d1bad706bd82ba96c9ec237f98dda582fd15d0d344c3d03fbc1019659396",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7",
              "scratch/paquete-demo-v3.txt": "sha256:0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f",
              "scratch/paquete-demo-v4.txt": "sha256:a3a5e715f0cc574a73c3f9bebb6bc24f32ffd5b67b387244c2c909da779a1478"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "3"
                  ]
                ],
                "id": "truncado-alcanza-versiones"
              }
            ],
            "observation_sha256": "sha256:0120d1bad706bd82ba96c9ec237f98dda582fd15d0d344c3d03fbc1019659396",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/truncado-par": {
          "new": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7",
              "scratch/paquete-demo-v3.txt": "sha256:0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "2"
                  ]
                ],
                "id": "truncado-alcanza-versiones"
              }
            ],
            "observation_sha256": "sha256:bbe5e9bd692a7f8fcab8ff81eee122cbce2f8ad2b2d35e90b7756b79f9460406",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/paquete-demo-v2.txt": "sha256:87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7",
              "scratch/paquete-demo-v3.txt": "sha256:0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "cuantas",
                    "2"
                  ]
                ],
                "id": "truncado-alcanza-versiones"
              }
            ],
            "observation_sha256": "sha256:bbe5e9bd692a7f8fcab8ff81eee122cbce2f8ad2b2d35e90b7756b79f9460406",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "paquete-versionado/truncado-vacio": {
          "new": {
            "artifacts": {
              "scratch/.gitkeep": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:74f67017a8b13b663b32f95fc053e65ac17759f04093dd272adad4c3df1d97ac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "scratch/.gitkeep": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:74f67017a8b13b663b32f95fc053e65ac17759f04093dd272adad4c3df1d97ac",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "recovery-bloquea/dos-reintentos": {
          "new": {
            "artifacts": {
              "log.md": "sha256:46a7f00e5fbcb577d1e8c0c593f3edacbcc945fe509f8ecd92d5fed13953cd87"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `transportAttempt: 2` 3: - `semanticAttempt: 2`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:d91b23ae0c4b7b06878752e0a4e04549ed39c57b7f686aa441eca63768d6d97f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:46a7f00e5fbcb577d1e8c0c593f3edacbcc945fe509f8ecd92d5fed13953cd87"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `transportAttempt: 2` 3: - `semanticAttempt: 2`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:d91b23ae0c4b7b06878752e0a4e04549ed39c57b7f686aa441eca63768d6d97f",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "recovery-bloquea/positivo": {
          "new": {
            "artifacts": {
              "log.md": "sha256:9c69960d690ff552af6eb3a185c39f07f294f7a86fb2fca1bd3a258f727deddf"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:5c36618d665746d3c1745b1705c917516ed21ec5ee2e017e958eb2e9afffbae3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:9c69960d690ff552af6eb3a185c39f07f294f7a86fb2fca1bd3a258f727deddf"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:5c36618d665746d3c1745b1705c917516ed21ec5ee2e017e958eb2e9afffbae3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "recovery-bloquea/recovery-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:d10fe19292220006834e6b933627d475cda332976f997ac3af76afcf19fed084"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9e5e3002b443c3cb3d0825fab601b78cf450471de2e107aaf1953e7334f7c432",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:d10fe19292220006834e6b933627d475cda332976f997ac3af76afcf19fed084"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9e5e3002b443c3cb3d0825fab601b78cf450471de2e107aaf1953e7334f7c432",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "recovery-bloquea/reintento-antes-de-resolver": {
          "new": {
            "artifacts": {
              "log.md": "sha256:8f7626bc313b4d60141a8cb44b4e6df262049dc9ef276c624d80b5fb95d2bebf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `semanticAttempt: 2`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:b0806e8a8122bc70ca60a2b5f4d48c211d7d6381a7c0eaee26a74d1ffb941f4c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:8f7626bc313b4d60141a8cb44b4e6df262049dc9ef276c624d80b5fb95d2bebf"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `semanticAttempt: 2`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:b0806e8a8122bc70ca60a2b5f4d48c211d7d6381a7c0eaee26a74d1ffb941f4c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "recovery-bloquea/sin-reintentos": {
          "new": {
            "artifacts": {
              "log.md": "sha256:406947af306a4b15cc2247499a5e905021b65360111abfab93dbbf53c8ce171b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:51e7d48e6d6c55e8bceeb03c65734aff6f5241a1daec9a74f7f386cc02adea93",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:406947af306a4b15cc2247499a5e905021b65360111abfab93dbbf53c8ce171b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:51e7d48e6d6c55e8bceeb03c65734aff6f5241a1daec9a74f7f386cc02adea93",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "recovery-bloquea/tres-reintentos": {
          "new": {
            "artifacts": {
              "log.md": "sha256:7afdbd42b5d5bec6e5c6e5f861a6f0cab89bfd5531d47cd71c434e29cb8c1773"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `transportAttempt: 2` 3: - `semanticAttempt: 2` 4: - `transportAttempt: 3`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:5a1b323b491d43ab5685a12acfd924c980333b7dbc0a217237e91ae95238ee28",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:7afdbd42b5d5bec6e5c6e5f861a6f0cab89bfd5531d47cd71c434e29cb8c1773"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `transportAttempt: 2` 3: - `semanticAttempt: 2` 4: - `transportAttempt: 3`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:5a1b323b491d43ab5685a12acfd924c980333b7dbc0a217237e91ae95238ee28",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "recovery-bloquea/un-reintento": {
          "new": {
            "artifacts": {
              "log.md": "sha256:95b3ca122a86d2a38de91434368e69c538d094461afca46d3ca25c5218de614e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `transportAttempt: 2`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:d55a3b160ce6dd89d88a78ee14a893a89a2be1d11e732c4329ba9bbfbb0a9728",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:95b3ca122a86d2a38de91434368e69c538d094461afca46d3ca25c5218de614e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "2: - `transportAttempt: 2`"
                  ]
                ],
                "id": "reintento-con-recurso-abierto"
              }
            ],
            "observation_sha256": "sha256:d55a3b160ce6dd89d88a78ee14a893a89a2be1d11e732c4329ba9bbfbb0a9728",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "resolver-antes-de-preguntar/escalar-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:f80adad6e4e79d08b9918846c592442082646ab2c6ecc38a3658a8aa833246e0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4346631ca4bc0feef146829ea25829e01cb5eb1110c83c3f5b2b477697d0cd82",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:f80adad6e4e79d08b9918846c592442082646ab2c6ecc38a3658a8aa833246e0"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:4346631ca4bc0feef146829ea25829e01cb5eb1110c83c3f5b2b477697d0cd82",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "resolver-antes-de-preguntar/paso-casing": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:f46d46491b945367d406ca4faf6478c220a3f0fc2b2013768a9e769c692cab82"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "paso",
                    "buscar-en-repo"
                  ]
                ],
                "id": "escalo-sin-registrar"
              }
            ],
            "observation_sha256": "sha256:ef8809632a33d4f20563b1ad955cd3232631edc39d986c0cf384bec402fec2a5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:f46d46491b945367d406ca4faf6478c220a3f0fc2b2013768a9e769c692cab82"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "paso",
                    "buscar-en-repo"
                  ]
                ],
                "id": "escalo-sin-registrar"
              }
            ],
            "observation_sha256": "sha256:ef8809632a33d4f20563b1ad955cd3232631edc39d986c0cf384bec402fec2a5",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "resolver-antes-de-preguntar/paso-despues": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:0b7d2e5854691d028cd7fb2d3fe7138390653d945ab699a6f1ad804f4df5780f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "paso",
                    "buscar-en-repo"
                  ]
                ],
                "id": "paso-despues-de-escalar"
              }
            ],
            "observation_sha256": "sha256:91329352073ffbdf94e55382ad1fcf3356463ccac3d13f1a20db4fdce69f5c71",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:0b7d2e5854691d028cd7fb2d3fe7138390653d945ab699a6f1ad804f4df5780f"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "paso",
                    "buscar-en-repo"
                  ]
                ],
                "id": "paso-despues-de-escalar"
              }
            ],
            "observation_sha256": "sha256:91329352073ffbdf94e55382ad1fcf3356463ccac3d13f1a20db4fdce69f5c71",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "resolver-antes-de-preguntar/positivo": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:8c0f623bc5ac19fed50b52a76a456f18aedc8a048d9e39506eb994c96c90d5f6"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f2cfb733666c1ca41d7d653b52ff8b9515f7a53f4cdbc86d8afc21d493406109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:8c0f623bc5ac19fed50b52a76a456f18aedc8a048d9e39506eb994c96c90d5f6"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:f2cfb733666c1ca41d7d653b52ff8b9515f7a53f4cdbc86d8afc21d493406109",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "resolver-antes-de-preguntar/sin-registrar-paso": {
          "new": {
            "artifacts": {
              "bitacora.md": "sha256:6abe02e551e4705e7386525a7393cab68a1e7910577ad7a760e903878bc30f2e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "paso",
                    "buscar-en-repo"
                  ]
                ],
                "id": "escalo-sin-registrar"
              }
            ],
            "observation_sha256": "sha256:82c4016e2a9d329350a613682ba3bbdba563ae39a90aca00cf4a4a1fbad7faf4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "bitacora.md": "sha256:6abe02e551e4705e7386525a7393cab68a1e7910577ad7a760e903878bc30f2e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "paso",
                    "buscar-en-repo"
                  ]
                ],
                "id": "escalo-sin-registrar"
              }
            ],
            "observation_sha256": "sha256:82c4016e2a9d329350a613682ba3bbdba563ae39a90aca00cf4a4a1fbad7faf4",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "split-paginado/paginas-desiguales": {
          "new": {
            "artifacts": {
              "detail-salida.md": "sha256:f0f4a1dd24f9bf4bee6c03b316cd7d31256c70de891e020dd5e144c6872accdd",
              "raw.md": "sha256:e10974f76f961266865b914845037d4d4d0c0f520e6b43412ad100030c544548",
              "salida-p01.md": "sha256:f7c4ce27cdbe7e60eafdd7dd5abfbf09ce7116448dcafa2f58fb161184d9a302",
              "salida-p02.md": "sha256:64a8598b40efecce88afff83ee1a4b2df6272fa76a6d6340198344be3a3f3d3c",
              "salida.md": "sha256:ff180b20398ecfbfda150bdd3651315cf761583113268c1faf6b4d49f5f305eb"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:ee48df2fab021764d1778e22b2f7fdf1568a33d69513ee5674782beb710fa2ff",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail-salida.md": "sha256:f0f4a1dd24f9bf4bee6c03b316cd7d31256c70de891e020dd5e144c6872accdd",
              "raw.md": "sha256:e10974f76f961266865b914845037d4d4d0c0f520e6b43412ad100030c544548",
              "salida-p01.md": "sha256:f7c4ce27cdbe7e60eafdd7dd5abfbf09ce7116448dcafa2f58fb161184d9a302",
              "salida-p02.md": "sha256:64a8598b40efecce88afff83ee1a4b2df6272fa76a6d6340198344be3a3f3d3c",
              "salida.md": "sha256:ff180b20398ecfbfda150bdd3651315cf761583113268c1faf6b4d49f5f305eb"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:ee48df2fab021764d1778e22b2f7fdf1568a33d69513ee5674782beb710fa2ff",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "split-paginado/positivo": {
          "new": {
            "artifacts": {
              "detail-salida.md": "sha256:be2747467867df8ed9578485180d6ec0c034709b89b5a5efe96fc8bf2b1fa974",
              "raw.md": "sha256:82b5ae179bb3ababcfeecb64545a5565eda5b2f24f93e917d537c4152ee22d0e",
              "salida-p01.md": "sha256:f7c4ce27cdbe7e60eafdd7dd5abfbf09ce7116448dcafa2f58fb161184d9a302",
              "salida-p02.md": "sha256:d957a16fcd52f96221bf5c72670009297b4f9086dc32a66956b88fcfe2cff2bf",
              "salida.md": "sha256:f9b405c11f2f67eb634070cb41250167124f00c42e5dc34a8f164edaff3a256c"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:a69bd06628c5661bd407c5233cffb0e0ef5df72845c84c240a3a001caf8d6736",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail-salida.md": "sha256:be2747467867df8ed9578485180d6ec0c034709b89b5a5efe96fc8bf2b1fa974",
              "raw.md": "sha256:82b5ae179bb3ababcfeecb64545a5565eda5b2f24f93e917d537c4152ee22d0e",
              "salida-p01.md": "sha256:f7c4ce27cdbe7e60eafdd7dd5abfbf09ce7116448dcafa2f58fb161184d9a302",
              "salida-p02.md": "sha256:d957a16fcd52f96221bf5c72670009297b4f9086dc32a66956b88fcfe2cff2bf",
              "salida.md": "sha256:f9b405c11f2f67eb634070cb41250167124f00c42e5dc34a8f164edaff3a256c"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:a69bd06628c5661bd407c5233cffb0e0ef5df72845c84c240a3a001caf8d6736",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "split-paginado/residuo-detectable": {
          "new": {
            "artifacts": {
              "detail-salida.md": "sha256:be2747467867df8ed9578485180d6ec0c034709b89b5a5efe96fc8bf2b1fa974",
              "raw.md": "sha256:82b5ae179bb3ababcfeecb64545a5565eda5b2f24f93e917d537c4152ee22d0e",
              "salida-p01.md": "sha256:e51eae29fa11673d6530c042c1c818b539c1f2086d04c698f3aec48d9cba3d77",
              "salida-p02.md": "sha256:57d23a682666152caa98ce300b1f5484dfa3d6d7b99c2a1c716c2c5b6fdbbc93",
              "salida.md": "sha256:51101d6c773de1c9c6df38f8c840b661afe0d7e8fab8e89c33f77932e8fe9c28"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:833ebeae5d92dc6ec315bb64edad4195d7712ad8791c3dd6d3d0e713d7837e8a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail-salida.md": "sha256:be2747467867df8ed9578485180d6ec0c034709b89b5a5efe96fc8bf2b1fa974",
              "raw.md": "sha256:82b5ae179bb3ababcfeecb64545a5565eda5b2f24f93e917d537c4152ee22d0e",
              "salida-p01.md": "sha256:e51eae29fa11673d6530c042c1c818b539c1f2086d04c698f3aec48d9cba3d77",
              "salida-p02.md": "sha256:57d23a682666152caa98ce300b1f5484dfa3d6d7b99c2a1c716c2c5b6fdbbc93",
              "salida.md": "sha256:51101d6c773de1c9c6df38f8c840b661afe0d7e8fab8e89c33f77932e8fe9c28"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:833ebeae5d92dc6ec315bb64edad4195d7712ad8791c3dd6d3d0e713d7837e8a",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "split-paginado/seccion-minuscula": {
          "new": {
            "artifacts": {
              "raw.md": "sha256:171ab1366b0b87aaa5fdffa73afe7525769321e2d8e6c3c1a1bf560cb51f03fa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:e4d8a30f66d5e5ee15bbec70168dd381d12d86211f27091397062027c288d540",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "raw.md": "sha256:171ab1366b0b87aaa5fdffa73afe7525769321e2d8e6c3c1a1bf560cb51f03fa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:e4d8a30f66d5e5ee15bbec70168dd381d12d86211f27091397062027c288d540",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "split-paginado/sin-detalle": {
          "new": {
            "artifacts": {
              "raw.md": "sha256:d5c96704bd55c065ca3dd7b495a9b7b99d172c5d08941179bbf27b0c8ea0b9da"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:2c12e5474bb9da5c5ce5747dee40a98b90f2661e0307f92f0e0c686727954bf8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "raw.md": "sha256:d5c96704bd55c065ca3dd7b495a9b7b99d172c5d08941179bbf27b0c8ea0b9da"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "sin-detalle"
              }
            ],
            "observation_sha256": "sha256:2c12e5474bb9da5c5ce5747dee40a98b90f2661e0307f92f0e0c686727954bf8",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "split-paginado/singleton": {
          "new": {
            "artifacts": {
              "detail-salida.md": "sha256:1f56615d745b284c69683d25faf93b87a90f29a72cb9752d7e9e8331452a839f",
              "raw.md": "sha256:87f2bc5ea0291eb83cefe9ea3b76ccbebd7d96a222d59f5208275336af0ceff2",
              "salida-p01.md": "sha256:52325b333aba17f0a9b06aca4a8179433e76ba7e2951e0e4b3a3d4e538fbd140",
              "salida.md": "sha256:e00029999a976b63766b25d1118a2dda3390b1e8b327b5964c9d20134be94482"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:43dc8db80a9c6a825e07128406b38720e03bca58286005c54771802a92ca5285",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail-salida.md": "sha256:1f56615d745b284c69683d25faf93b87a90f29a72cb9752d7e9e8331452a839f",
              "raw.md": "sha256:87f2bc5ea0291eb83cefe9ea3b76ccbebd7d96a222d59f5208275336af0ceff2",
              "salida-p01.md": "sha256:52325b333aba17f0a9b06aca4a8179433e76ba7e2951e0e4b3a3d4e538fbd140",
              "salida.md": "sha256:e00029999a976b63766b25d1118a2dda3390b1e8b327b5964c9d20134be94482"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:43dc8db80a9c6a825e07128406b38720e03bca58286005c54771802a92ca5285",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "split-paginado/vacio": {
          "new": {
            "artifacts": {
              "detail-salida.md": "sha256:1f56615d745b284c69683d25faf93b87a90f29a72cb9752d7e9e8331452a839f",
              "raw.md": "sha256:20ac1c71e424cacd9d5cadb4a9961afb30d6651ed8843c8794d66012f107c81c",
              "salida.md": "sha256:6b289726aecbeb88fcde7a684dd0bce41cf8de50921cb768c5be148c9b042f76"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d66b973b949182665a55bd478ae7e72fd4b286ad6bb51601a1cce8f6131eda3e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail-salida.md": "sha256:1f56615d745b284c69683d25faf93b87a90f29a72cb9752d7e9e8331452a839f",
              "raw.md": "sha256:20ac1c71e424cacd9d5cadb4a9961afb30d6651ed8843c8794d66012f107c81c",
              "salida.md": "sha256:6b289726aecbeb88fcde7a684dd0bce41cf8de50921cb768c5be148c9b042f76"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d66b973b949182665a55bd478ae7e72fd4b286ad6bb51601a1cce8f6131eda3e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "takeover-reglas/contrato-cambia-en-takeover": {
          "new": {
            "artifacts": {
              "log.md": "sha256:4735760fa6abb4bb1a7d8ad016ff4dc62aaf7941b76185d686fdcb48f5026edc"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "antes",
                    "v1"
                  ],
                  [
                    "durante",
                    "v2"
                  ]
                ],
                "id": "takeover-no-ablanda"
              }
            ],
            "observation_sha256": "sha256:83868059970033061b5ec417aa579be7064fa3f808b03e4efcf604a6da3ad182",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:4735760fa6abb4bb1a7d8ad016ff4dc62aaf7941b76185d686fdcb48f5026edc"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "antes",
                    "v1"
                  ],
                  [
                    "durante",
                    "v2"
                  ]
                ],
                "id": "takeover-no-ablanda"
              }
            ],
            "observation_sha256": "sha256:83868059970033061b5ec417aa579be7064fa3f808b03e4efcf604a6da3ad182",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "takeover-reglas/contrato-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:f8dfa1b358ecb3b657c7da6b5d35181b17e519042a94dc4bc83e6473bf21aa7d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cf61625fae9c7a512683800f160a128beb89a3c911a1f5fab7652a545f23a2be",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:f8dfa1b358ecb3b657c7da6b5d35181b17e519042a94dc4bc83e6473bf21aa7d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:cf61625fae9c7a512683800f160a128beb89a3c911a1f5fab7652a545f23a2be",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "takeover-reglas/design-gap-casing": {
          "new": {
            "artifacts": {
              "log.md": "sha256:08bbc9a21a3d9ffb3bd8963e8cc3c8c84775b99d9129199cb3df57c8f3571546"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9b32d3ea9710e17e8a2c0af728353e5c9e6899c12d51a5b618f4b6706455d98d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:08bbc9a21a3d9ffb3bd8963e8cc3c8c84775b99d9129199cb3df57c8f3571546"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:9b32d3ea9710e17e8a2c0af728353e5c9e6899c12d51a5b618f4b6706455d98d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "takeover-reglas/positivo": {
          "new": {
            "artifacts": {
              "log.md": "sha256:7f7b7c3fc10f88bacf853a552fb354a55ad27d445b07fb050c6dc99f7f11f3e7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:51cc1ed43d4f09c5ba5b0adb38679d97cac74c6db1863da8d6e08a557be99450",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:7f7b7c3fc10f88bacf853a552fb354a55ad27d445b07fb050c6dc99f7f11f3e7"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:51cc1ed43d4f09c5ba5b0adb38679d97cac74c6db1863da8d6e08a557be99450",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "takeover-reglas/trabajo-despues-del-gap": {
          "new": {
            "artifacts": {
              "log.md": "sha256:996c1084838d49fb62ef57708dac0d558202f88bb2579d4cc4ebd3989a0c79f6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "6: ## Ronda 2"
                  ]
                ],
                "id": "design-gap-corta-takeover"
              }
            ],
            "observation_sha256": "sha256:027abd9b99fdf456fb8bff6a69d40cd762f3f3776d74ca507932e3ff0ae220fb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "log.md": "sha256:996c1084838d49fb62ef57708dac0d558202f88bb2579d4cc4ebd3989a0c79f6"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "lineas",
                    "6: ## Ronda 2"
                  ]
                ],
                "id": "design-gap-corta-takeover"
              }
            ],
            "observation_sha256": "sha256:027abd9b99fdf456fb8bff6a69d40cd762f3f3776d74ca507932e3ff0ae220fb",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/desarrollo-casing": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:6e3bfb13e3b95c37ec61929237a57de7e116e9237e85884655707273a685af8c",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "ABC-A-DEF-002"
                  ]
                ],
                "id": "desarrollo-sin-entrada"
              },
              {
                "fields": [
                  [
                    "ids",
                    "abc-a-def-002"
                  ]
                ],
                "id": "indexado-sin-desarrollo"
              }
            ],
            "observation_sha256": "sha256:c71f7c728ea11d6c91922010c3145536cb6ce0fa93feea943ad463f55890c6f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:6e3bfb13e3b95c37ec61929237a57de7e116e9237e85884655707273a685af8c",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "ABC-A-DEF-002"
                  ]
                ],
                "id": "desarrollo-sin-entrada"
              },
              {
                "fields": [
                  [
                    "ids",
                    "abc-a-def-002"
                  ]
                ],
                "id": "indexado-sin-desarrollo"
              }
            ],
            "observation_sha256": "sha256:c71f7c728ea11d6c91922010c3145536cb6ce0fa93feea943ad463f55890c6f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/entrada-casing": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:2a363af710401e0ebd686ceafbea56ce957661ff13c9d1dd2b7bac77d3958712",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida.md": "sha256:5d82d2037480d87c2dd3af150d30a9d3f5923d3e0e5f897fbd4f06f874ee43fa"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:acfedafd38b06b2a74e949ed5f6c357a18d31911da1f77fdeb3a2ba3d622ed20",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:2a363af710401e0ebd686ceafbea56ce957661ff13c9d1dd2b7bac77d3958712",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida.md": "sha256:5d82d2037480d87c2dd3af150d30a9d3f5923d3e0e5f897fbd4f06f874ee43fa"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:acfedafd38b06b2a74e949ed5f6c357a18d31911da1f77fdeb3a2ba3d622ed20",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/positivo": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:01e20e83d3af8ea9fc140c8eb802068e5dec66b8fbeccb47b9e47e2d815afec8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:ce9b3e173e60b39eede1627017ace7937d50cbab3f8668b9bbe9c9a51fc2715d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:01e20e83d3af8ea9fc140c8eb802068e5dec66b8fbeccb47b9e47e2d815afec8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:ce9b3e173e60b39eede1627017ace7937d50cbab3f8668b9bbe9c9a51fc2715d",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/sin-desarrollo": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:0b22111538e30679cf318355320d93673d0a5dc06ae113c70205d0a9778f6e75",
              "salida-p01.md": "sha256:01e20e83d3af8ea9fc140c8eb802068e5dec66b8fbeccb47b9e47e2d815afec8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "ABC-A-DEF-002"
                  ]
                ],
                "id": "indexado-sin-desarrollo"
              }
            ],
            "observation_sha256": "sha256:61f50323bba0152143a39d26f92b117436e64f0c6a04fe4ba23afc92d5a3f78c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:0b22111538e30679cf318355320d93673d0a5dc06ae113c70205d0a9778f6e75",
              "salida-p01.md": "sha256:01e20e83d3af8ea9fc140c8eb802068e5dec66b8fbeccb47b9e47e2d815afec8",
              "salida.md": "sha256:e149a6245313df6c32903b57c5bde0ae61da3e5f718df287cb60c59aa19cf6b4"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "ABC-A-DEF-002"
                  ]
                ],
                "id": "indexado-sin-desarrollo"
              }
            ],
            "observation_sha256": "sha256:61f50323bba0152143a39d26f92b117436e64f0c6a04fe4ba23afc92d5a3f78c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/sin-entrada": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida.md": "sha256:5d82d2037480d87c2dd3af150d30a9d3f5923d3e0e5f897fbd4f06f874ee43fa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "ABC-A-DEF-002"
                  ]
                ],
                "id": "desarrollo-sin-entrada"
              }
            ],
            "observation_sha256": "sha256:705494f2c3ef61e061b007b61fc5fb26cb2bd3eb6a34ba4e9a0bebe5dbadef26",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida.md": "sha256:5d82d2037480d87c2dd3af150d30a9d3f5923d3e0e5f897fbd4f06f874ee43fa"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [
                  [
                    "ids",
                    "ABC-A-DEF-002"
                  ]
                ],
                "id": "desarrollo-sin-entrada"
              }
            ],
            "observation_sha256": "sha256:705494f2c3ef61e061b007b61fc5fb26cb2bd3eb6a34ba4e9a0bebe5dbadef26",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/union-impar": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:fd62ad45200165e8d3962c5025712b92f0ac9562556ce54d62e2c3aacea546c8",
              "salida-p01.md": "sha256:01e20e83d3af8ea9fc140c8eb802068e5dec66b8fbeccb47b9e47e2d815afec8",
              "salida-p02.md": "sha256:f53169600fd9fe87ee772c9fb279bd58664fc2a1fcde97d51589bea2c2e4c0c0",
              "salida.md": "sha256:37f8f121f45cd5122e0e2360c45e94c0d7dbfd0adf7b08e31c2e5760a40b75e1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:104046edb75aec1b57fdb3fef0f4c3b36d828d2255942ef190933da189e9f40e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:fd62ad45200165e8d3962c5025712b92f0ac9562556ce54d62e2c3aacea546c8",
              "salida-p01.md": "sha256:01e20e83d3af8ea9fc140c8eb802068e5dec66b8fbeccb47b9e47e2d815afec8",
              "salida-p02.md": "sha256:f53169600fd9fe87ee772c9fb279bd58664fc2a1fcde97d51589bea2c2e4c0c0",
              "salida.md": "sha256:37f8f121f45cd5122e0e2360c45e94c0d7dbfd0adf7b08e31c2e5760a40b75e1"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:104046edb75aec1b57fdb3fef0f4c3b36d828d2255942ef190933da189e9f40e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/union-par": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida-p02.md": "sha256:d71dee7ab7efc53d3544fa55a0999b8a0ef491e241a780e5e614f0a09d5c6959",
              "salida.md": "sha256:470c01634cf767976cd26fb322972e35bcf006173ee76faa83c10f042a4a2f2b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6408fe63d9d681a1477a51320f82fdb8e3aae2c331bbf29be4c49a1211026971",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:437a5f80d94d23c6d976bc38363e35e6289c94b044f7ee4edbf3b3dae8ce6d49",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida-p02.md": "sha256:d71dee7ab7efc53d3544fa55a0999b8a0ef491e241a780e5e614f0a09d5c6959",
              "salida.md": "sha256:470c01634cf767976cd26fb322972e35bcf006173ee76faa83c10f042a4a2f2b"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:6408fe63d9d681a1477a51320f82fdb8e3aae2c331bbf29be4c49a1211026971",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/union-singleton": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:0b22111538e30679cf318355320d93673d0a5dc06ae113c70205d0a9778f6e75",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida.md": "sha256:5d82d2037480d87c2dd3af150d30a9d3f5923d3e0e5f897fbd4f06f874ee43fa"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1952eed4bf3a7089f660b241fd7bfdbf71df7dbed1d494fdb0b8a6efc7fd7a68",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:0b22111538e30679cf318355320d93673d0a5dc06ae113c70205d0a9778f6e75",
              "salida-p01.md": "sha256:ac1b447c5b4f116ef4ae6a6ddb243119e5e8daa8d3282a59b8a12a7257e26f7d",
              "salida.md": "sha256:5d82d2037480d87c2dd3af150d30a9d3f5923d3e0e5f897fbd4f06f874ee43fa"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:1952eed4bf3a7089f660b241fd7bfdbf71df7dbed1d494fdb0b8a6efc7fd7a68",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "validador-paginado/union-vacia": {
          "new": {
            "artifacts": {
              "detail.md": "sha256:01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
              "salida-p01.md": "sha256:efcec193de9cfbb8d964e62bd9732e14cd13beb1f45f8dffdce505f7b1382999",
              "salida.md": "sha256:7d5b2604c99aa2ec412bbc27ce5256ea7f2411d7e75b61696c2cfa3057be5d8e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "union-vacia"
              }
            ],
            "observation_sha256": "sha256:7800a22a73346d774040d3d26abd2c380f16c6e4457284b7b6ea0c419614be7e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "detail.md": "sha256:01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
              "salida-p01.md": "sha256:efcec193de9cfbb8d964e62bd9732e14cd13beb1f45f8dffdce505f7b1382999",
              "salida.md": "sha256:7d5b2604c99aa2ec412bbc27ce5256ea7f2411d7e75b61696c2cfa3057be5d8e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "union-vacia"
              }
            ],
            "observation_sha256": "sha256:7800a22a73346d774040d3d26abd2c380f16c6e4457284b7b6ea0c419614be7e",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "verify-ejecuta/cargar-minuscula": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:6174744f1b78e0bccec8f05a9f0fe188c7713e76c06f91af011daed7f854f264"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-no-carga"
              }
            ],
            "observation_sha256": "sha256:84936c347a3d25fd727397a386ed86993e8621712de6a02e5801d26b537ec5d7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:6174744f1b78e0bccec8f05a9f0fe188c7713e76c06f91af011daed7f854f264"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-no-carga"
              }
            ],
            "observation_sha256": "sha256:84936c347a3d25fd727397a386ed86993e8621712de6a02e5801d26b537ec5d7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "verify-ejecuta/con-identificar": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:c0587a28cd3665e053c2bfb6a8e319ad9ca1a21791911b39d4fc39771e5f8c4b"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-sigue-identificando"
              }
            ],
            "observation_sha256": "sha256:9c1730dec6420319215b033e1df5a892c35c28befb2f5ee242a4eb49666aef21",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:c0587a28cd3665e053c2bfb6a8e319ad9ca1a21791911b39d4fc39771e5f8c4b"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-sigue-identificando"
              }
            ],
            "observation_sha256": "sha256:9c1730dec6420319215b033e1df5a892c35c28befb2f5ee242a4eb49666aef21",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "verify-ejecuta/identificar-minuscula": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:784e6080a706b705a0476b816206f8aad8c793ba0a6749332c5819c80177a88d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d1f7816c090fc29aec044a3edc4bb92f0b10fc85940d11de7f4f896a8ffa6952",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:784e6080a706b705a0476b816206f8aad8c793ba0a6749332c5819c80177a88d"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:d1f7816c090fc29aec044a3edc4bb92f0b10fc85940d11de7f4f896a8ffa6952",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "verify-ejecuta/positivo": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:0d440cbf1521c7ff3f4ff8376cadeb4a8cd8319d8738b77da33864031b5bad0f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:b0b81ab935262f58840867d53c8eb6e0639ff17ddd9a833cfd6b2b69c78bd693",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:0d440cbf1521c7ff3f4ff8376cadeb4a8cd8319d8738b77da33864031b5bad0f"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:b0b81ab935262f58840867d53c8eb6e0639ff17ddd9a833cfd6b2b69c78bd693",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "verify-ejecuta/revert-mayuscula": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:ae39368cb54fc74d63dfa1ae74c9e0ba82f1793f60269fa89598d390b6c6382c"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:206889f5271e4474044ec4cc7bcff4780989cd50be0b733f1f3a353b506918d3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:ae39368cb54fc74d63dfa1ae74c9e0ba82f1793f60269fa89598d390b6c6382c"
            },
            "class": "aceptacion",
            "code": 0,
            "events": [],
            "observation_sha256": "sha256:206889f5271e4474044ec4cc7bcff4780989cd50be0b733f1f3a353b506918d3",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "verify-ejecuta/sin-cargar": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:930817bf9ff0ff6aaa81731858479accbffffd78591b1051a8f639724c783d0e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-no-carga"
              }
            ],
            "observation_sha256": "sha256:8e497235f2f2968ad36223bf92466cc2471d71f249e08ded0a27e2bafce0f72c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:930817bf9ff0ff6aaa81731858479accbffffd78591b1051a8f639724c783d0e"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-no-carga"
              }
            ],
            "observation_sha256": "sha256:8e497235f2f2968ad36223bf92466cc2471d71f249e08ded0a27e2bafce0f72c",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        },
        "verify-ejecuta/sin-revert": {
          "new": {
            "artifacts": {
              "skill.md": "sha256:205c7cdb232dc16dc86f20d0092aec7feb685e44cbe0dbbd82eaef4bc1b3d5a0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-perdio-revert"
              }
            ],
            "observation_sha256": "sha256:e9f64e6e7d03356921a9728cdfb9b41f6499ee317b8e891fdd04ba12c50d53f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          },
          "old": {
            "artifacts": {
              "skill.md": "sha256:205c7cdb232dc16dc86f20d0092aec7feb685e44cbe0dbbd82eaef4bc1b3d5a0"
            },
            "class": "rechazo",
            "code": 1,
            "events": [
              {
                "fields": [],
                "id": "verify-perdio-revert"
              }
            ],
            "observation_sha256": "sha256:e9f64e6e7d03356921a9728cdfb9b41f6499ee317b8e891fdd04ba12c50d53f7",
            "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
          }
        }
      },
      "compared": 397,
      "divergences": [],
      "implementations": {
        "clarificacion-completa": {
          "new_path": "skills/co-explore/scripts/clarificacion-completa.py",
          "new_sha256": "sha256:b49744ff5fd7192d39d7ee3db3c93be4c91c57b23f2d4e2b08bea6df921f6339",
          "old_path": "skills/co-explore/reference.md#@bloque:clarificacion-completa",
          "old_sha256": "sha256:649223a144fa1380256ce9685510e4e845abe5f410f776d9685e9cc77909e0e9"
        },
        "cobertura-ac-fila": {
          "new_path": "skills/sdd-flow/scripts/cobertura-ac-fila.py",
          "new_sha256": "sha256:128047ee211a936ef7f201b786d43702726344c80dd8a16734b3d5ffe3e5f082",
          "old_path": "skills/sdd-flow/reference.md#@bloque:cobertura-ac-fila",
          "old_sha256": "sha256:0297c22811b7d6dcffb63e3443f036e3255a89bbbd3bd89261ea6afa68d6c0e6"
        },
        "contrato-baseline": {
          "new_path": "skills/cross-implement/scripts/contrato-baseline.py",
          "new_sha256": "sha256:2fc91725c18e18aa0814523c180d9b7a030124d676960110ed1271117e3bfc7a",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:contrato-baseline",
          "old_sha256": "sha256:ab2053287e19cf1549d2fc1c7150c6840e215b52e500856eb98bebfa784e94ce"
        },
        "contrato-cadena": {
          "new_path": "skills/cross-implement/scripts/contrato-cadena.py",
          "new_sha256": "sha256:b12627169fb6d51bb40568295ae418440e3ec1002986e0e315c49d317a095ac5",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:contrato-cadena",
          "old_sha256": "sha256:4c58f33a967b0565d86bec020e08af7a5e0621993db67c449a2710845ea218ed"
        },
        "contrato-cobertura": {
          "new_path": "skills/cross-implement/scripts/contrato-cobertura.py",
          "new_sha256": "sha256:aeff20f0b7a467afc4389b26b92a8570645ed0d76b10a806741a86483a81a8a0",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:contrato-cobertura",
          "old_sha256": "sha256:0be415d3ef3891e7836cedfe19984e2ee1b812968046d177e092ee6233567891"
        },
        "contrato-esquema": {
          "new_path": "skills/cross-implement/scripts/contrato-esquema.py",
          "new_sha256": "sha256:2e84e540ce4c8b96b1b4051395a478154d09288c443c786a6ddaf003fedbdab3",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:contrato-esquema",
          "old_sha256": "sha256:56a65cf4120dfd4e7949edefcfd79328946945f566988985b522a4ecde5b7143"
        },
        "contrato-invariantes": {
          "new_path": "skills/cross-implement/scripts/contrato-invariantes.py",
          "new_sha256": "sha256:b9a5043887f7615baeb80737aae888975bac03e447fa3505df8775bd80a1ba87",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:contrato-invariantes",
          "old_sha256": "sha256:4ab5d04fe206d0bf884a4449444305d7272c62d03e3facee5e4816c8f897f85b"
        },
        "cuarto-estado-consumidores": {
          "new_path": "skills/co-explore/scripts/cuarto-estado-consumidores.py",
          "new_sha256": "sha256:3b2e7098d953db0ca9a08c39e245adbc1c054322a70fe56d34c7d7c5f4772ee4",
          "old_path": "skills/co-explore/reference.md#@bloque:cuarto-estado-consumidores",
          "old_sha256": "sha256:791162751c32f922f88b1297716450a54b7d3ae9f151e265ef1a7ff3277e8646"
        },
        "gate-blocked": {
          "new_path": "skills/cross-implement/scripts/gate-blocked.py",
          "new_sha256": "sha256:cc28b2ba4d3ba8ecb2577e199f663572ddd5020f822d7692c5edc0e174c649b4",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:gate-blocked",
          "old_sha256": "sha256:8ef6d6d7dde322208d12aa3299811243e0eca990ff3477fc245da6c574bca63e"
        },
        "gate-congelado": {
          "new_path": "skills/cross-implement/scripts/gate-congelado.py",
          "new_sha256": "sha256:6f9ffe83b0de98d4c6baf99e5a05d14b91b8f1e49cf2ab90bf10cd9d64dac1f2",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:gate-congelado",
          "old_sha256": "sha256:00824a75394afc718d2c77533360cf496d1f0cf5bbabc1af2efc7b00080ec74d"
        },
        "gate-fase-3": {
          "new_path": "skills/sdd-orchestrator/scripts/gate-fase-3.py",
          "new_sha256": "sha256:2a5828b847dff052ae187a1ee1fe1326d604b6667f4a16ee4763003ce5685d8c",
          "old_path": "skills/sdd-orchestrator/reference.md#@bloque:gate-fase-3",
          "old_sha256": "sha256:01c6586706d3a6a518fae9a81a0cef6ceb329168be4ba78f270a1294720ee056"
        },
        "gate-modo-directo": {
          "new_path": "skills/cross-implement/scripts/gate-modo-directo.py",
          "new_sha256": "sha256:00c1984ebea601fe47b62cf37058b543ef95d324c77956908a5b5786d6763be5",
          "old_path": "skills/cross-implement/contrato-verificacion.md#@bloque:gate-modo-directo",
          "old_sha256": "sha256:901ed227d2e0e17c0d4294409168ea27c7aaafa96cd2b0a0cee9ccb93088dca7"
        },
        "identidades-reintento": {
          "new_path": "skills/co-explore/scripts/identidades-reintento.py",
          "new_sha256": "sha256:8362313efdd1e771f11475a73c6993eedf9c586a1c5d575b4777b30c071922f6",
          "old_path": "skills/co-explore/reference.md#@bloque:identidades-reintento",
          "old_sha256": "sha256:43305d71409c453557725eb63306b094df275fb3ffc1c6b5b36fd7f0441d2655"
        },
        "integracion-ownership": {
          "new_path": "skills/sdd-orchestrator/scripts/integracion-ownership.py",
          "new_sha256": "sha256:74eec57912d2776de7c7b067e23bc41d8b5857fdc1954e5c0525ecc4e793f06a",
          "old_path": "skills/sdd-orchestrator/reference.md#@bloque:integracion-ownership",
          "old_sha256": "sha256:ea99f9f96098c37015f41eca6154551d25e75b6b7cc5d95f53e0a02fc614bb2f"
        },
        "manifest-resumen": {
          "new_path": "skills/cross-review/scripts/manifest-resumen.py",
          "new_sha256": "sha256:d24e50d9d5f8a5ee693ce1c80a17d026c8c10bc600c44f8a2131aadf83b6bf8a",
          "old_path": "skills/cross-review/reference.md#@bloque:manifest-resumen",
          "old_sha256": "sha256:f2c54c85e2d2a7bde8d3fd374b92689b50d7b2117bcc138a7031394624fdd27a"
        },
        "manifest-valido": {
          "new_path": "skills/cross-review/scripts/manifest-valido.py",
          "new_sha256": "sha256:f06237186a16a16629d56160740710d1e9b064006b27b57e2af0be1d0f36cc16",
          "old_path": "skills/cross-review/reference.md#@bloque:manifest-valido",
          "old_sha256": "sha256:afba043073fdb13d92c4e5f622b930a57987b68a59c1cd2aebcf08cd89edd5b0"
        },
        "materializacion-contrato": {
          "new_path": "skills/sdd-flow/scripts/materializacion-contrato.py",
          "new_sha256": "sha256:071c1aa4de4a12b82511ddb3e083591669da173c5b562713421a38a44f9bb81f",
          "old_path": "skills/sdd-flow/reference.md#@bloque:materializacion-contrato",
          "old_sha256": "sha256:e438069a86ca77b8d7ca1eb65642c3d31e33c8f9031fa868e78d22cae63261a1"
        },
        "metaindice": {
          "new_path": "skills/co-explore/scripts/metaindice.py",
          "new_sha256": "sha256:fa022b27e790336099a292196bbcb96e1d137cf1ecc5a048c1e65934e4a56489",
          "old_path": "skills/co-explore/reference.md#@bloque:metaindice",
          "old_sha256": "sha256:eecdd56ef8221bcd34df9b5835358d2a47e326f4cd9eb3c5df857431e5a781c1"
        },
        "orchestration-contract": {
          "new_path": "skills/sdd-orchestrator/scripts/orchestration-contract.py",
          "new_sha256": "sha256:3adb25dfebf5161860a3ea88ffa5cd13989295d1d597da9a3d73ccf298eab0ee",
          "old_path": "skills/sdd-orchestrator/reference.md#@bloque:orchestration-contract",
          "old_sha256": "sha256:1f9e1c7da3a6845ae74b55d490a3c5d2733e7605a8e6947a6b09afd274d46568"
        },
        "orchestration-model": {
          "new_path": "skills/sdd-orchestrator/scripts/orchestration-model.py",
          "new_sha256": "sha256:1a3b21d7bba0a3ace600ec97f889dc937c6d13c67418b90c71b14b58094136e0",
          "old_path": "skills/sdd-orchestrator/reference.md#@bloque:orchestration-model",
          "old_sha256": "sha256:c014ae5e7c511639cbfec44eb6f6ad9e287aa0c7a05087daeec1583e58d4ee1f"
        },
        "orchestration-state": {
          "new_path": "skills/sdd-orchestrator/scripts/orchestration-state.py",
          "new_sha256": "sha256:4bcf0206a09ba5b8d3a26e3e93c3e6ec4754a9001af3bf740b5f7a0b777fdcf8",
          "old_path": "skills/sdd-orchestrator/reference.md#@bloque:orchestration-state",
          "old_sha256": "sha256:65344302c07113d81f5353af5d35e2875f1e77bd1864ebb7b329f0d1a5de9dd6"
        },
        "ownership-log": {
          "new_path": "skills/cross-implement/scripts/ownership-log.py",
          "new_sha256": "sha256:ad0a45bc988f26531330fe998095c02028c73a6bde9949e1ce172f49813f0852",
          "old_path": "skills/cross-implement/ownership.md#@bloque:ownership-log",
          "old_sha256": "sha256:4365eeaee786df8303e5cf51401c075c7618a419f260d54ae8ee942fd9fab96c"
        },
        "ownership-presupuesto": {
          "new_path": "skills/cross-implement/scripts/ownership-presupuesto.py",
          "new_sha256": "sha256:f37c994f4c80426cec8930d537b14ce0a1e4d70eedb3c0790d7b43a4026ce2d0",
          "old_path": "skills/cross-implement/ownership.md#@bloque:ownership-presupuesto",
          "old_sha256": "sha256:a767516058c81598544ff1c8d8328f9b25fcbd9bd663ee6277a89112470349c2"
        },
        "paquete-versionado": {
          "new_path": "skills/co-explore/scripts/paquete-versionado.py",
          "new_sha256": "sha256:57496f4a3efb2959121f53b912b9c89df325da801991c255d0d0d28e41bba165",
          "old_path": "skills/co-explore/reference.md#@bloque:paquete-versionado",
          "old_sha256": "sha256:edef5814dbb8e80793b6391449ec3442255896485587658efe4a218ded9da87b"
        },
        "recovery-bloquea": {
          "new_path": "skills/co-explore/scripts/recovery-bloquea.py",
          "new_sha256": "sha256:b5ef326da8cba99c3e80d697324dcc841c8a1257dcd56b4a56ff866ada9d1429",
          "old_path": "skills/co-explore/reference.md#@bloque:recovery-bloquea",
          "old_sha256": "sha256:71cf1ccedc7280ed733ead40817397b3c719a6651d8c7e21673f7ac3caf14fa8"
        },
        "resolver-antes-de-preguntar": {
          "new_path": "skills/co-explore/scripts/resolver-antes-de-preguntar.py",
          "new_sha256": "sha256:55c6becb01c6369eebd93492e5404451ac53a1f89ed7be3754bc328958071a83",
          "old_path": "skills/co-explore/reference.md#@bloque:resolver-antes-de-preguntar",
          "old_sha256": "sha256:0577964f7a342477a9ce977cbe20e97788268d0cf3afed4d66b266e0194413aa"
        },
        "split-paginado": {
          "new_path": "skills/co-explore/scripts/split-paginado.py",
          "new_sha256": "sha256:0e522b71738c64e6caf4baedff3d26c42baafd131450ebafa5cc5d052d2e2447",
          "old_path": "skills/co-explore/reference.md#@bloque:split-paginado",
          "old_sha256": "sha256:b91d95aa10633a1b4e434598250fd2c528736008161bf36d097e6210da7a1d4a"
        },
        "takeover-reglas": {
          "new_path": "skills/cross-implement/scripts/takeover-reglas.py",
          "new_sha256": "sha256:46504f0352470788040d5fdfbbb83e60d03ba61816816eb9a3ba7b26a23ffd3d",
          "old_path": "skills/cross-implement/ownership.md#@bloque:takeover-reglas",
          "old_sha256": "sha256:09d736f757ec217a395a21faa900fbe3e47aca74e14f1a83cc1e649357e34b95"
        },
        "validador-paginado": {
          "new_path": "skills/co-explore/scripts/validador-paginado.py",
          "new_sha256": "sha256:bbc40b4cb1fb032b6ffbaa58b60aa471a9ab66f9fc5ff7b59b2f81fc19805a9b",
          "old_path": "skills/co-explore/reference.md#@bloque:validador-paginado",
          "old_sha256": "sha256:0dc4578bb352c1de717dd20262c6b5d37f44c15d14a00e447e250ba481b5c72d"
        },
        "verify-ejecuta": {
          "new_path": "skills/sdd-flow/scripts/verify-ejecuta.py",
          "new_sha256": "sha256:f8b38a809c2dc725bef60f3bb1574d553696ea39d6221a74adff1401b14671b0",
          "old_path": "skills/sdd-flow/reference.md#@bloque:verify-ejecuta",
          "old_sha256": "sha256:465a6474aa5675892c25f51e4f40e14957ace9df3dcf98351d1814ff6e8924f8"
        }
      }
    }
  },
  "snapshot": {
    "base_commit": "5013b4589d5b6429f9705539268eb0d8ac7ae3fc",
    "commit": "5e4098dcc2d7c6ba4568b584ade64de36330b4a0",
    "tag": "migracion/snapshot-dual",
    "tree": "39faa047a6318d1d89eb23fa53717c13665ecbbd"
  }
}
```
<!-- evidencia-migracion:fin -->
