"""Planning-source consistency checks, not physical or CAD validation."""
import csv
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CadInputTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / 'cad/roboracer/parameters.csv').open(newline='') as handle:
            self.rows = list(csv.DictReader(handle))
        self.by_id = {row['parameter']: row for row in self.rows}

    def value(self, key):
        return float(self.by_id[key]['value'])

    def test_source_and_unknown_contract(self):
        self.assertTrue(self.rows)
        self.assertEqual(len(self.rows), len(self.by_id))
        for row in self.rows:
            with self.subTest(parameter=row['parameter']):
                self.assertNotIn(None, row)
                self.assertTrue((ROOT / row['source']).is_file())
                self.assertTrue(row['release_requirement'])
                self.assertIn(row['unit'], {'mm', 'm', 'N', 'kg', '1', 'm/s^2', 'N/mm^2', 'kg/m^3'})
                self.assertIn(row['evidence_state'], {'pending', 'design_choice', 'model_assumption', 'reported_vendor_nominal', 'committed_simulation', 'protocol'})
                if row['evidence_state'] == 'pending':
                    self.assertEqual(row['value'], '')
                else:
                    self.assertTrue(math.isfinite(float(row['value'])))
                    self.assertGreater(float(row['value']), 0)

    def test_nominal_beam_and_mass_budget(self):
        od, wall, length = (self.value(k) for k in ('mast_outer_diameter', 'mast_wall_thickness', 'mast_length'))
        inner = od - 2 * wall
        self.assertGreater(inner, 0)
        moment = math.pi * (od**4 - inner**4) / 64
        stiffness = 3 * self.value('youngs_modulus') * moment / length**3
        self.assertAlmostEqual(stiffness, 775.9836594264038)
        mass = self.value('density') * math.pi * (od**2 - inner**2) / 4 * length * 1e-9
        # Annulus: (20^2 - 17^2) * 100 / 4 = 2775, so m = 0.0074925*pi kg.
        self.assertAlmostEqual(mass, 0.0074925 * math.pi, places=12)
        self.assertAlmostEqual(sum(self.value(k) for k in ('tip_body_mass', 'tip_bracket_mass', 'tip_cable_mass')), self.value('tip_total_mass'))
        self.assertEqual(self.by_id['actual_load_height']['evidence_state'], 'pending')

    def test_load_provenance_and_distinct_wheelbases(self):
        summary = json.loads((ROOT / 'runs/ride_quality_baseline/summary.json').read_text())
        self.assertTrue(summary['completed_lap'])
        self.assertFalse(summary['collision'])
        self.assertEqual(self.value('clean_sim_peak_lateral_accel'), summary['max_abs_lat_accel_mps2'])
        self.assertEqual([self.value(f'force_target_{i}') for i in range(1, 6)], [4, 8, 12, 16, 20])
        self.assertNotEqual(self.value('model_wheelbase'), self.value('selected_chassis_wheelbase'))


if __name__ == '__main__':
    unittest.main()
