"""Core guarantees for the deterministic simulation and validation rules."""

import unittest

from api.schemas.simulation import SimulationRequest
from app.simulation_engine import ScenarioError
from app.simulation_engine import get_data
from app.simulation_engine import simulate


def scenario(*items: tuple[str, str | None]) -> SimulationRequest:
    return SimulationRequest.model_validate(
        {
            'decisions': [
                {'measure_id': measure_id, 'district_id': district_id}
                for measure_id, district_id in items
            ],
        },
    )


class SimulationTests(unittest.TestCase):
    def test_github_baseline_and_catalogue(self) -> None:
        data = get_data()
        self.assertEqual(data.baseline_score, 52.56)
        self.assertEqual(len(data.districts), 5)
        self.assertEqual(len(data.measures), 14)

    def test_valid_result_is_reproducible_and_uses_synergies(self) -> None:
        decisions = (
            ('M1', 'Нура'),
            ('M2', None),
            ('M7', 'Нура'),
            ('M10', 'Есиль'),
            ('M12', None),
        )
        first = simulate(scenario(*decisions))
        reverse = simulate(scenario(*reversed(decisions)))
        self.assertEqual(first.score, 55.74)
        self.assertEqual(first.score, reverse.score)
        self.assertEqual(first.spent, 90)
        self.assertEqual(first.critical_pairs_before, 2)
        self.assertEqual(first.critical_pairs_after, 1)
        self.assertEqual(len(first.activated_synergies), 2)

    def test_budget_overrun_is_rejected(self) -> None:
        request = scenario(
            ('M3', 'Есиль'),
            ('M5', 'Сарыарка'),
            ('M7', 'Нура'),
            ('M8', 'Алматы'),
            ('M13', 'Байконур'),
        )
        with self.assertRaises(ScenarioError) as raised:
            simulate(request)
        self.assertEqual(raised.exception.code, 'over_budget')

    def test_global_incompatibility_is_rejected(self) -> None:
        request = scenario(
            ('M1', 'Нура'),
            ('M3', 'Есиль'),
            ('M9', 'Байконур'),
            ('M10', 'Есиль'),
            ('M12', None),
        )
        with self.assertRaises(ScenarioError) as raised:
            simulate(request)
        self.assertEqual(raised.exception.code, 'incompatible')

    def test_same_district_incompatibility_is_rejected(self) -> None:
        request = scenario(
            ('M4', 'Нура'),
            ('M7', 'Нура'),
            ('M1', 'Есиль'),
            ('M10', 'Сарыарка'),
            ('M12', None),
        )
        with self.assertRaises(ScenarioError) as raised:
            simulate(request)
        self.assertEqual(raised.exception.code, 'incompatible')

    def test_city_measure_cannot_target_one_district(self) -> None:
        request = scenario(
            ('M1', 'Нура'),
            ('M2', 'Нура'),
            ('M7', 'Нура'),
            ('M10', 'Есиль'),
            ('M12', None),
        )
        with self.assertRaises(ScenarioError) as raised:
            simulate(request)
        self.assertEqual(raised.exception.code, 'city_scope')


if __name__ == '__main__':
    unittest.main()
