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


class TapTestPreregTests(unittest.TestCase):
    """The modal preregistration is fail-closed: no band until every modal input is filled."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location('tap_test_prereg', ROOT / 'experiments/tap_test_prereg.py')
        cls.P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.P)

    def modal_rows(self):
        with (ROOT / 'cad/roboracer/modal-inputs.csv').open(newline='') as handle:
            return list(csv.DictReader(handle))

    def test_committed_document_is_current_and_band_refused(self):
        self.assertEqual(self.P.main(['--check']), 0)
        self.assertEqual(self.P.main(['--release']), 2)
        text = (ROOT / 'docs/specs/mast-modal-tap-test/preregistration.md').read_text()
        self.assertIn('band REFUSED', text)
        self.assertNotRegex(text, r'Band: \d')

    def test_modal_register_is_all_pending_with_no_values(self):
        rows = self.modal_rows()
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(parameter=row['parameter']):
                self.assertEqual(row['evidence_state'], 'pending')
                self.assertEqual(row['value'], '')
                self.assertIn(row['unit'], {'Hz', '1', 'kg', 's', 'mm'})
                self.assertTrue((ROOT / row['source']).is_file())

    def test_nominal_hand_f1_uses_repository_formula(self):
        reg = self.P._read(self.P.REGISTER)
        hand = self.P.nominal_hand_f1(reg)
        self.assertAlmostEqual(hand['f1_hz'], 330.07414641340273, places=9)
        self.assertAlmostEqual(hand['k_eff_n_per_m'], 775983.6594264036, places=6)
        self.assertAlmostEqual(self.P.committed_fea_f1(), 285.5)
        self.assertAlmostEqual(self.P.rejected_baseline_f1(), 174.7)

    def test_filled_register_yields_band_in_committed_form_positive_control(self):
        import tempfile
        rows = self.modal_rows()
        synthetic = {'as_built_f1_prediction': '300', 'model_discrepancy_tolerance_rel': '0.10',
                     'stiffness_rel_std_uncertainty': '0.04', 'modal_mass_rel_std_uncertainty': '0.03',
                     'accelerometer_installed_mass': '0.005', 'daq_sample_rate': '5000', 'record_duration': '2',
                     'excitation_location_from_root': '60', 'response_location_from_root': '95', 'taps_per_axis': '10'}
        for row in rows:
            row['value'], row['evidence_state'] = synthetic[row['parameter']], 'protocol'  # test-only numbers
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'modal.csv'
            with path.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            b = self.P.band(self.P._read(path))
        u_model = 0.5 * math.sqrt(0.04**2 + 0.03**2)
        u_res = 1 / (2 * 300 * math.sqrt(12))
        half = 0.10 + 2 * math.sqrt(u_model**2 + u_res**2)
        self.assertEqual(b['pending_inputs'], [])
        self.assertAlmostEqual(b['half_width_rel'], half)
        self.assertAlmostEqual(b['band_hz'][0], 300 * (1 - half))
        self.assertAlmostEqual(b['band_hz'][1], 300 * (1 + half))

    def test_pending_row_with_a_value_is_refused(self):
        import tempfile
        rows = self.modal_rows()
        rows[0]['value'] = '300'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'modal.csv'
            with path.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            with self.assertRaises(self.P.PreregInputError):
                self.P._read(path)


if __name__ == '__main__':
    unittest.main()
