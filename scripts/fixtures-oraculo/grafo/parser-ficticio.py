"""Parser ficticio del fixture: importa dos ayudantes versionados del repo.

Existe para ejercer el mecanismo `import_estatico` del gate precommit. El parser real solo importa
`re`, `sys` y `pathlib`, así que su grafo dentro del repo es vacío y esa rama no se ejercería nunca.
"""
import ayudante
from ayudante_dos import algo

__all__ = ["ayudante", "algo"]
