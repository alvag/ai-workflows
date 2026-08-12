"""Parser ficticio que carga por `importlib`: mecanismo fuera del modelo declarado.

La clausura de su grafo no es demostrable por análisis estático general, así que el gate **aborta**
en vez de pasar en silencio. Es el límite del quinto proxy, ejercido.
"""
import importlib


def cargar(nombre):
    return importlib.import_module(nombre)
