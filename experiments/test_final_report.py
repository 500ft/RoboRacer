#!/usr/bin/env python3
"""Closure tests for the item-12 design-review report."""

from __future__ import annotations

import csv
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "final_report.md"
BUILD_SCRIPT = ROOT / "scripts" / "build_final_report.py"
TOLERANCE_RUN = ROOT / "runs" / "mast_tolerance_stack" / "summary.txt"


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class FinalReportTests(unittest.TestCase):
    def test_report_has_no_unresolved_markers(self) -> None:
        text = REPORT.read_text(encoding="utf-8")
        marker = re.compile(
            r"\bTODO\b|\bTBD\b|\[confirm\]|\bTEMPLATE\b|\bPLACEHOLDER\b",
            re.IGNORECASE,
        )
        self.assertIsNone(marker.search(text))

    def test_mechanical_headlines_trace_to_committed_artifacts(self) -> None:
        self.assertTrue(
            TOLERANCE_RUN.exists(),
            "the tolerance script must persist the run output cited by the report",
        )
        report = REPORT.read_text(encoding="utf-8")
        sources = {
            "runs/mast_hand_calc/summary.txt": ("174.7", "128.76"),
            "runs/mast_hand_calc/design_sweep.txt": ("330.1", "8.05"),
            "runs/mast_fea/fea_summary.txt": ("285.5", "17.4", "0.176"),
            "runs/mast_fea/mesh_convergence.txt": ("-0.15", "0.30", "-1.42"),
            "runs/mast_tolerance_stack/summary.txt": ("1.284", "0.354", "0.138"),
            "docs/design/16_mechanical_design_analysis.md": ("4.42", "4.5"),
        }
        for source_path, values in sources.items():
            source = read(source_path)
            self.assertIn(source_path, report)
            for value in values:
                with self.subTest(source=source_path, value=value):
                    self.assertIn(value, source)
                    self.assertIn(value, report)

    def test_simulation_headlines_trace_to_committed_artifacts(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        literal_sources = {
            "runs/ride_quality_baseline/summary.json": ("19.436", "9.51"),
            "reports/integrator_convergence.md": (
                "0.0020",
                "0.0133307",
                "0.176077",
                "0.277026",
            ),
            "reports/model_vs_gym_comparison.md": ("66.7991", "0.999"),
            "runs/failure_mode_fmea/results.csv": ("1.484", "0.053", "0.706"),
            "runs/parameter_id_robustness/metrics.csv": ("0.440", "0.892"),
        }
        for source_path, values in literal_sources.items():
            source = read(source_path)
            self.assertIn(source_path, report)
            for value in values:
                with self.subTest(source=source_path, value=value):
                    self.assertIn(value, source)
                    self.assertIn(value, report)

        controller_path = "runs/controller_comparison/results.csv"
        with (ROOT / controller_path).open(newline="", encoding="utf-8") as handle:
            controllers = {
                row["controller"]: row for row in csv.DictReader(handle)
            }
        controller_claims = {
            "pure_pursuit": f"{float(controllers['pure_pursuit']['rms_cte_m']):.6f}",
            "lqr": f"{float(controllers['lqr']['rms_cte_m']):.6f}",
            "mpc": f"{float(controllers['mpc']['rms_cte_m']):.6f}",
        }
        self.assertIn(controller_path, report)
        for controller, value in controller_claims.items():
            with self.subTest(source=controller_path, controller=controller):
                self.assertIn(value, report)

        mpc_path = "runs/mpc_controller/results.csv"
        with (ROOT / mpc_path).open(newline="", encoding="utf-8") as handle:
            mpc = next(csv.DictReader(handle))
        mpc_claims = (
            f"{float(mpc['mpc_p95_solve_time_s']) * 1000:.5f}",
            f"{float(mpc['mpc_max_solve_time_s']) * 1000:.3f}",
        )
        self.assertIn(mpc_path, report)
        for value in mpc_claims:
            with self.subTest(source=mpc_path, value=value):
                self.assertIn(value, report)

        ekf_path = "runs/ekf_study/summary.csv"
        with (ROOT / ekf_path).open(newline="", encoding="utf-8") as handle:
            ekf_rows = list(csv.DictReader(handle))
        clean_dead_reckoning = next(
            row
            for row in ekf_rows
            if row["scenario"] == "clean_measurements"
            and row["estimator"] == "dead_reckoning"
        )
        dropout_ekf = next(
            row
            for row in ekf_rows
            if row["scenario"] == "dropout_3s" and row["estimator"] == "ekf"
        )
        ekf_claims = (
            f"{float(clean_dead_reckoning['position_rmse_m']):.2f}",
            f"{float(dropout_ekf['position_rmse_m']):.6f}",
            f"{float(dropout_ekf['max_position_error_m']):.5f}",
        )
        self.assertIn(ekf_path, report)
        for value in ekf_claims:
            with self.subTest(source=ekf_path, value=value):
                self.assertIn(value, report)

    def test_physical_gate_is_registered_and_pending(self) -> None:
        report = REPORT.read_text(encoding="utf-8").lower()
        self.assertIn("experiment registered", report)
        self.assertIn("campaign scheduled", report)
        self.assertIn("measurement pending", report)
        self.assertIn("+/-15%", report)
        self.assertIn("does not validate stress", report)

    def test_local_report_references_exist(self) -> None:
        text = REPORT.read_text(encoding="utf-8")
        references = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
        for reference in references:
            if "://" in reference or reference.startswith("#"):
                continue
            target = (REPORT.parent / reference.split("#", 1)[0]).resolve()
            with self.subTest(reference=reference):
                self.assertTrue(target.exists(), f"missing local reference: {reference}")

    def test_report_builds_review_length_pdf(self) -> None:
        self.assertTrue(BUILD_SCRIPT.exists(), "report build script is missing")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.pdf"
            subprocess.run(
                [
                    "python3",
                    str(BUILD_SCRIPT),
                    "--input",
                    str(REPORT),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
            )
            reader = PdfReader(output)
            self.assertGreaterEqual(len(reader.pages), 10)
            self.assertLessEqual(len(reader.pages), 20)
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            for heading in (
                "Requirements and Verification",
                "Mechanical Design and Analysis",
                "Physical Compliance Gate",
                "Traceability and Reproduction",
            ):
                self.assertIn(heading, extracted)


if __name__ == "__main__":
    unittest.main()
