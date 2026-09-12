"""Prospective modal readiness checks; no modal measurements are supplied."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("modal_freeze", ROOT / "cad/modal_freeze.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_draft_can_be_read_but_not_frozen():
    draft = json.loads(module.DEFAULT.read_text())
    assert module.check(draft, schema_only=True) == "DRAFT_BLOCKED"
    with pytest.raises(ValueError, match="unresolved"):
        module.check(draft)


def synthetic_complete():
    draft = json.loads(module.DEFAULT.read_text())
    draft["status"] = "ready_for_human_freeze_review"
    for key in draft["settings"]:
        draft["settings"][key] = 1.0
    draft["settings"].update(sample_rate_hz=4000.0, record_duration_s=4.0,
                             frequency_resolution_hz=0.25, analysis_low_hz=100.0,
                             analysis_high_hz=800.0, antialias_passband_hz=800.0,
                             antialias_stopband_hz=1500.0, repeats_per_axis=5,
                             model_discrepancy_fraction=0.12,
                             max_relative_u95=0.08, min_coherence=0.9,
                             max_repeatability_fraction=0.03,
                             max_sensor_mass_fraction=0.01)
    for key in draft["records"]:
        draft["records"][key] = "synthetic only, human review required"
    draft["baseline_kind"] = "as_built"
    draft["reference_hz"] = {"x": 290.0, "y": 292.0}
    return draft


def test_complete_synthetic_check_is_not_frozen_or_validated():
    assert module.check(synthetic_complete()) == "READY_FOR_HUMAN_FREEZE_REVIEW_ONLY"


@pytest.mark.parametrize("change", ["null", "nan", "bool", "missing", "record", "nominal", "axis", "nyquist", "resolution", "repeats", "fraction", "band"])
def test_unresolved_or_incoherent_freeze_inputs_rejected(change):
    draft = synthetic_complete()
    if change == "null": draft["settings"]["max_relative_u95"] = None
    if change == "nan": draft["settings"]["sample_rate_hz"] = float("nan")
    if change == "bool": draft["settings"]["record_duration_s"] = True
    if change == "missing": del draft["settings"]["model_discrepancy_fraction"]
    if change == "record": draft["records"]["uncertainty_budget"] = None
    if change == "nominal": draft["baseline_kind"] = "nominal"
    if change == "axis": draft["reference_hz"] = {"x": 290.0}
    if change == "nyquist": draft["settings"]["sample_rate_hz"] = 2000.0
    if change == "resolution": draft["settings"]["frequency_resolution_hz"] = 0.01
    if change == "repeats": draft["settings"]["repeats_per_axis"] = 2.5
    if change == "fraction": draft["settings"]["model_discrepancy_fraction"] = 1.1
    if change == "band": draft["settings"]["analysis_low_hz"] = 400.0
    with pytest.raises(ValueError): module.check(draft)


def test_cli_default_rejects_committed_draft():
    result = subprocess.run([sys.executable, str(ROOT / "cad/modal_freeze.py")], capture_output=True, text=True)
    assert result.returncode == 2
    assert "BLOCKED" in result.stderr
