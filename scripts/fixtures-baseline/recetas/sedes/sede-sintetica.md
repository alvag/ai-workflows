# Sede sintética del corpus de recetas

Existe para ejercer los dos extremos que AC-34 nombra —**cero** resultados y **múltiples**— sin
editar una skill real. Contra el árbol de verdad no se pueden fabricar: una skill con dos
invocaciones idénticas sería un cambio al repositorio, y una sin ninguna no probaría nada sobre la
receta que sí la tiene.

## Una sola invocación

```bash
codex exec -s read-only -C <unico> --skip-git-repo-check -
```

## Dos invocaciones que un patrón laxo confunde

La ambigüedad es el caso interesante: las dos líneas son invocaciones legítimas de puntos
distintos, y un selector que devuelva «la primera» produce un comando plausible y falso.

```bash
codex exec -s read-only -C <ambiguo-a> --skip-git-repo-check -
codex exec -s read-only -C <ambiguo-b> --skip-git-repo-check -
```
