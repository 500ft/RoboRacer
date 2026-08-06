#!/usr/bin/env python3
"""Regression tests for the preregistered mast compliance gate."""

from __future__ import annotations

import unittest

from mast_physical_validation import (
    FEA_COMPLIANCE_MM_PER_N,
    evaluate_rows,
    indicator_counts_at_load,
    indicator_is_adequate,
)


def synthetic_rows(scale=1.0, hysteresis_mm=0.0, nonlinear_mm=0.0):
    rows = []
    for axis in ("x", "y"):
        for cycle in range(1, 4):
            for direction in ("load", "unload"):
                for force_n in (4.0, 8.0, 12.0, 16.0, 20.0):
                    fixture_mm = 0.0001 * force_n
                    direction_offset = hysteresis_mm if direction == "unload" else 0.0
                    tip_mm = (
                        fixture_mm
                        + scale * FEA_COMPLIANCE_MM_PER_N * force_n
                        + direction_offset
                        + nonlinear_mm * (force_n / 20.0) ** 2
                    )
                    rows.append(
                        {
                            "axis": axis,
                            "cycle": cycle,
                            "direction": direction,
                            "force_n": force_n,
                            "tip_mm": tip_mm,
                            "fixture_mm": fixture_mm,
                        }
                    )
    return rows


class MastPhysicalValidationTests(unittest.TestCase):
    def test_indicator_resolution_precheck(self):
        self.assertAlmostEqual(indicator_counts_at_load(20.0, 0.01), 2.7338, places=3)
        self.assertFalse(indicator_is_adequate(20.0, 0.01))
        self.assertTrue(indicator_is_adequate(20.0, 0.001))

    def test_validated_when_quality_and_agreement_pass(self):
        verdict = evaluate_rows(synthetic_rows(), relative_u95=0.08)
        self.assertEqual(verdict.classification, "VALIDATED")
        self.assertEqual(len(verdict.axes), 2)
        for axis in verdict.axes:
            self.assertAlmostEqual(axis.compliance_mm_per_n, FEA_COMPLIANCE_MM_PER_N)
            self.assertGreaterEqual(axis.r_squared, 0.99)

    def test_discrepancy_when_clean_measurement_misses_fea_band(self):
        verdict = evaluate_rows(synthetic_rows(scale=1.20), relative_u95=0.08)
        self.assertEqual(verdict.classification, "DISCREPANCY")

    def test_inconclusive_when_uncertainty_is_too_large(self):
        verdict = evaluate_rows(synthetic_rows(), relative_u95=0.11)
        self.assertEqual(verdict.classification, "INCONCLUSIVE")

    def test_inconclusive_when_hysteresis_is_too_large(self):
        verdict = evaluate_rows(synthetic_rows(hysteresis_mm=0.003), relative_u95=0.08)
        self.assertEqual(verdict.classification, "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
