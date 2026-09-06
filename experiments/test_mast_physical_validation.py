#!/usr/bin/env python3
"""Regression tests for the preregistered mast compliance gate."""

from __future__ import annotations

import unittest
import math
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from mast_physical_validation import (
    FEA_COMPLIANCE_MM_PER_N,
    evaluate_rows,
    indicator_counts_at_load,
    indicator_is_adequate,
    load_campaign,
    read_csv,
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


def write_synthetic_campaign(root, rows=None, u95=0.08, compliances=None, resolution=0.001):
    """Create ONLY synthetic unit-test artifacts; never physical evidence."""
    rows = synthetic_rows() if rows is None else rows
    root = Path(root)
    raw = root / "raw.csv"
    with raw.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    identity = {"specimen_id": "SYNTHETIC-TEST-ONLY", "drawing_revision": "synthetic-v1",
                "evidence_kind": "synthetic"}
    inspection = dict(identity, length_mm=100, od_mm=20, wall_mm=1.5,
                      clamp_engagement_mm=10, load_height_mm=100)
    (root / "inspection.json").write_text(json.dumps(inspection))
    repo = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    reference = dict(identity, reference_kind="synthetic", source_commit=commit,
                     inspection_sha256=hashlib.sha256((root / "inspection.json").read_bytes()).hexdigest(),
                     boundary_conditions="synthetic fixed-root fixture", solver_version="synthetic-linear-v1",
                     model_revision="synthetic-linear-v1", compliance_mm_per_n=compliances or
                     {axis: FEA_COMPLIANCE_MM_PER_N for axis in ("x", "y")})
    calibration = {"evidence_kind": "synthetic", "force_instrument_id": "TEST-force",
                   "tip_instrument_id": "TEST-tip", "fixture_instrument_id": "TEST-fixture",
                   "calibration_date": "2026-09-04", "resolution_mm": resolution}
    uncertainty = dict(identity, relative_u95=u95, method="synthetic injected uncertainty",
                       reviewed_by="unit-test generator, not external reviewer",
                       components={key: "synthetic fixture input" for key in
                                   ("force", "tip", "fixture", "repeatability", "reference")})
    for name, content in (("reference", reference), ("calibration", calibration),
                          ("uncertainty", uncertainty)):
        (root / (name + ".json")).write_text(json.dumps(content))
    for name in ("zero_checks", "setup"):
        (root / (name + ".txt")).write_text("SYNTHETIC SOFTWARE TEST ONLY; no measurement")
    metadata = dict(identity, schema_version=1, operator="synthetic generator",
                    clamp_method="synthetic boundary", ambient_temperature_c=20,
                    test_date="2026-09-05", test_started_at="2026-09-05T12:00:00-04:00")
    for name in ("raw_csv", "reference", "inspection", "calibration", "uncertainty", "zero_checks", "setup"):
        filename = "raw.csv" if name == "raw_csv" else name + (".txt" if name in ("zero_checks", "setup") else ".json")
        metadata[name] = {"path": filename, "sha256": hashlib.sha256((root / filename).read_bytes()).hexdigest()}
    path = root / "campaign.json"
    path.write_text(json.dumps(metadata))
    return path, raw


def evaluate_synthetic(rows, u95=0.08, **kwargs):
    with tempfile.TemporaryDirectory() as directory:
        path, raw = write_synthetic_campaign(directory, rows, u95, **kwargs)
        return evaluate_rows(read_csv(raw), u95, load_campaign(path, raw))


class MastPhysicalValidationTests(unittest.TestCase):
    def test_rejects_audit_incomplete_matrix(self):
        rows = [row for row in synthetic_rows() if row["axis"] == "x"
                and row["cycle"] == 1 and row["force_n"] in (4.0, 20.0)]
        with self.assertRaises(ValueError):
            evaluate_rows(rows, 0.05)

    def test_rejects_missing_matrix_cells(self):
        full = synthetic_rows()
        for rows in (full[:-1], [r for r in full if r["axis"] == "x"],
                     [r for r in full if r["cycle"] < 3],
                     [r for r in full if r["direction"] == "load"],
                     [r for r in full if r["force_n"] != 12.0], full + [full[0]]):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                evaluate_rows(rows, 0.05)

    def test_rejects_invalid_cells(self):
        cases = {"axis": ("z", "", None), "cycle": (0, -1, 1.5, True, "nan"),
                 "direction": ("sideways", ""), "force_n": (0, -1, 19.0, math.nan, math.inf),
                 "tip_mm": (math.nan, math.inf, -math.inf),
                 "fixture_mm": (math.nan, math.inf, None)}
        for field, values in cases.items():
            for value in values:
                rows = synthetic_rows()
                rows[0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    evaluate_rows(rows, 0.05)

    def test_rejects_invalid_uncertainty(self):
        for value in (math.nan, math.inf, -math.inf, -0.01, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_rows(synthetic_rows(), value)

    def test_incomplete_reference_never_validates(self):
        verdict = evaluate_rows(synthetic_rows(), 0.05)
        self.assertEqual(verdict.classification, "INCONCLUSIVE")

    def test_indicator_resolution_precheck(self):
        self.assertAlmostEqual(indicator_counts_at_load(20.0, 0.01), 2.7338, places=3)
        self.assertFalse(indicator_is_adequate(20.0, 0.01))
        self.assertTrue(indicator_is_adequate(20.0, 0.001))

    def test_simulated_agreement_when_quality_and_agreement_pass(self):
        verdict = evaluate_synthetic(synthetic_rows())
        self.assertEqual(verdict.classification, "SIMULATED_AGREEMENT")
        self.assertEqual(verdict.evidence_kind, "synthetic")
        self.assertEqual(len(verdict.axes), 2)
        for axis in verdict.axes:
            self.assertAlmostEqual(axis.compliance_mm_per_n, FEA_COMPLIANCE_MM_PER_N)
            self.assertGreaterEqual(axis.r_squared, 0.99)

    def test_discrepancy_when_clean_measurement_misses_fea_band(self):
        verdict = evaluate_synthetic(synthetic_rows(scale=1.20))
        self.assertEqual(verdict.classification, "SIMULATED_DISCREPANCY")

    def test_inconclusive_when_uncertainty_is_too_large(self):
        verdict = evaluate_synthetic(synthetic_rows(), u95=0.11)
        self.assertEqual(verdict.classification, "INCONCLUSIVE")

    def test_inconclusive_when_hysteresis_is_too_large(self):
        verdict = evaluate_synthetic(synthetic_rows(hysteresis_mm=0.003))
        self.assertEqual(verdict.classification, "INCONCLUSIVE")

    def test_zero_or_negative_compliance_is_inconclusive_and_json_finite(self):
        for scale in (0, -1):
            verdict = evaluate_synthetic(synthetic_rows(scale=scale))
            self.assertEqual(verdict.classification, "INCONCLUSIVE")
            json.dumps(asdict(verdict), allow_nan=False)

    def test_per_axis_as_built_values_used_not_nominal_constant(self):
        rows = synthetic_rows()
        for row in rows:
            if row["axis"] == "y":
                row["tip_mm"] += FEA_COMPLIANCE_MM_PER_N * row["force_n"] * 0.3
        refs = {"x": FEA_COMPLIANCE_MM_PER_N, "y": FEA_COMPLIANCE_MM_PER_N * 1.3}
        verdict = evaluate_synthetic(rows, compliances=refs)
        self.assertEqual(verdict.classification, "SIMULATED_AGREEMENT")

    def test_instrumentation_gate_is_part_of_verdict(self):
        verdict = evaluate_synthetic(synthetic_rows(), resolution=0.01)
        self.assertEqual(verdict.classification, "INCONCLUSIVE")
        verdict = evaluate_synthetic(synthetic_rows(scale=0.5),
                                     compliances={a: FEA_COMPLIANCE_MM_PER_N * 0.5 for a in ("x", "y")})
        self.assertEqual(verdict.classification, "INCONCLUSIVE")

    def test_actual_forces_with_explicit_targets_remain_measured(self):
        rows = synthetic_rows()
        for row in rows:
            row["load_level_n"] = row["force_n"]
            row["force_n"] += 0.1 if row["direction"] == "load" else -0.1
            row["tip_mm"] = row["fixture_mm"] + FEA_COMPLIANCE_MM_PER_N * row["force_n"]
        self.assertEqual(evaluate_synthetic(rows).classification, "SIMULATED_AGREEMENT")

    def test_changed_rows_or_uncertainty_cannot_reuse_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            path, raw = write_synthetic_campaign(directory)
            campaign = load_campaign(path, raw)
            rows = read_csv(raw)
            with self.assertRaises(ValueError):
                evaluate_rows(rows, 0.01, campaign)
            rows[0]["tip_mm"] = "1.0"
            with self.assertRaises(ValueError):
                evaluate_rows(rows, 0.08, campaign)

    def test_changed_artifact_cannot_reuse_previously_loaded_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            path, raw = write_synthetic_campaign(directory)
            campaign = load_campaign(path, raw)
            (Path(directory) / "setup.txt").write_text("changed after loading")
            with self.assertRaises(ValueError):
                evaluate_rows(read_csv(raw), 0.08, campaign)

    def test_physical_reference_commit_is_separate_from_model_source_commit(self):
        # This is an explicitly MOCKED provenance check over synthetic inputs,
        # not a physical campaign or an independently authenticated measurement.
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=repo) as directory:
            path, raw = write_synthetic_campaign(directory)
            metadata = json.loads(path.read_text())
            metadata["evidence_kind"] = "physical"
            metadata["reference_commit"] = "a" * 40
            for name in ("reference", "inspection", "calibration", "uncertainty"):
                artifact = Path(directory) / metadata[name]["path"]
                record = json.loads(artifact.read_text())
                record["evidence_kind"] = "physical"
                if name == "reference":
                    record["reference_kind"] = "as_built"
                artifact.write_text(json.dumps(record))
            reference_path = Path(directory) / "reference.json"
            reference = json.loads(reference_path.read_text())
            reference["inspection_sha256"] = hashlib.sha256((Path(directory) / "inspection.json").read_bytes()).hexdigest()
            reference_path.write_text(json.dumps(reference))
            for name in ("reference", "inspection", "calibration", "uncertainty"):
                artifact = Path(directory) / metadata[name]["path"]
                metadata[name]["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            path.write_text(json.dumps(metadata))

            def mock_git(args, **kwargs):
                if args[1] == "cat-file":
                    return subprocess.CompletedProcess(args, 0, "commit\n", "")
                if args[1:4] == ["show", "-s", "--format=%cI"]:
                    return subprocess.CompletedProcess(args, 0, "2026-09-04T10:00:00-04:00\n", "")
                expected = "a" * 40 + ":" + reference_path.relative_to(repo).as_posix()
                self.assertEqual(args, ["git", "show", expected])
                return subprocess.CompletedProcess(args, 0, reference_path.read_bytes(), b"")

            with patch("mast_physical_validation.subprocess.run", side_effect=mock_git):
                campaign = load_campaign(path, raw)
                self.assertEqual(evaluate_rows(read_csv(raw), 0.08, campaign).classification, "VALIDATED")

    def test_campaign_requires_checked_artifacts(self):
        for key in ("raw_csv", "reference", "inspection", "calibration", "uncertainty", "zero_checks", "setup"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                path, raw = write_synthetic_campaign(directory)
                metadata = json.loads(path.read_text())
                artifact = Path(directory) / metadata[key]["path"]
                artifact.write_bytes(artifact.read_bytes() + b"changed")
                with self.assertRaises(ValueError):
                    load_campaign(path, raw)

    def test_invalid_reference_and_metadata_are_rejected(self):
        cases = [("reference", "reference_kind", "nominal"),
                 ("reference", "source_commit", "0" * 40),
                 ("reference", "specimen_id", "another-specimen"),
                 ("reference", "inspection_sha256", "0" * 64),
                 ("reference", "compliance_mm_per_n", {"x": math.inf, "y": 0.001}),
                 ("calibration", "resolution_mm", math.nan),
                 ("calibration", "calibration_date", "2026-10-01"),
                 ("calibration", "force_instrument_id", ""),
                 ("uncertainty", "components", {}), ("inspection", "wall_mm", 11)]
        for name, field, value in cases:
            with self.subTest(name=name, field=field), tempfile.TemporaryDirectory() as directory:
                path, raw = write_synthetic_campaign(directory)
                metadata = json.loads(path.read_text())
                artifact = Path(directory) / metadata[name]["path"]
                record = json.loads(artifact.read_text())
                record[field] = value
                artifact.write_text(json.dumps(record))
                metadata[name]["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
                path.write_text(json.dumps(metadata))
                with self.assertRaises(ValueError):
                    load_campaign(path, raw)

    def test_cli_missing_campaign_and_actual_synthetic_output(self):
        script = Path(__file__).with_name("mast_physical_validation.py")
        with tempfile.TemporaryDirectory() as directory:
            path, raw = write_synthetic_campaign(directory)
            missing = subprocess.run([sys.executable, str(script), str(raw), "--relative-u95", "0.08"],
                                     capture_output=True, text=True)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("--campaign", missing.stderr)
            valid = subprocess.run([sys.executable, str(script), str(raw), "--campaign", str(path)],
                                   capture_output=True, text=True)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertEqual(json.loads(valid.stdout)["classification"], "SIMULATED_AGREEMENT")
            (Path(directory) / "setup.txt").unlink()
            invalid = subprocess.run([sys.executable, str(script), str(raw), "--campaign", str(path)],
                                     capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)
            self.assertNotIn("Traceback", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
