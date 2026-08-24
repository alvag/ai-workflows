"""Una identidad de test durable por cada escenario de paridad generado."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from tests.fabricas.escenarios import Escenario, load_catalog, read_inventory


Case = Tuple[str, str, Callable[[Optional[object]], None]]
INVENTORY: Dict[str, Escenario] = {
    scenario.identidad: scenario for scenario in read_inventory()
}
GENERATED = load_catalog()


def _make_test(scenario: Escenario) -> Callable[[Optional[object]], None]:
    def scenario_test(_context: Optional[object]) -> None:
        """El escenario reproduce su identidad matriz/caso y el hash de su matriz."""
        authoritative = INVENTORY[scenario.identidad]
        assert scenario == authoritative
        assert scenario.identidad == scenario.matriz + "/" + scenario.caso
        assert scenario.hash_matriz == authoritative.hash_matriz

    return scenario_test


CASOS: List[Case] = []
for index, generated in enumerate(GENERATED, 1):
    test = _make_test(generated)
    test.__name__ = "test_generated_scenario_{0:03d}".format(index)
    globals()[test.__name__] = test
    CASOS.append(("escenario:" + generated.identidad, "escenarios-generados", test))
