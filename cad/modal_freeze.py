"""Reject incomplete modal preregistration. Completeness is not a freeze or result."""
import argparse
import json
import math
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "docs/specs/mast-physical-validation/modal-freeze.json"
SETTINGS = {
    "sample_rate_hz", "record_duration_s", "frequency_resolution_hz",
    "analysis_low_hz", "analysis_high_hz", "antialias_passband_hz",
    "antialias_stopband_hz", "antialias_attenuation_db", "repeats_per_axis",
    "model_discrepancy_fraction", "max_relative_u95", "min_coherence",
    "max_repeatability_fraction", "max_sensor_mass_fraction",
}
RECORDS = {
    "specimen_and_drawing", "inspection_and_installed_mass", "model_source_commit",
    "inspection_linked_reference_commit", "instrument_ids_calibration_bandwidth",
    "excitation_response_coordinates_both_axes", "clamp_and_cable_configuration",
    "sensor_loading_correction", "timing_antialias_characterization",
    "uncertainty_budget", "mode_pairing_estimator_window_damping",
    "exclusions_quality_retest_rule", "threshold_rationale_and_reviewer",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value):
    require(type(value) in (int, float) and math.isfinite(value) and value > 0,
            "unresolved/nonpositive/nonfinite numerical input")


def check(document, schema_only=False):
    require(type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 1, "unsupported schema")
    require(document.get("status") in {"draft_blocked", "ready_for_human_freeze_review"}, "invalid status")
    for key, keys in (("settings", SETTINGS), ("records", RECORDS), ("reference_hz", {"x", "y"})):
        require(type(document.get(key)) is dict and set(document[key]) == keys, f"missing/extra {key}")
    for value in (*document["settings"].values(), *document["reference_hz"].values()):
        if value is not None or not schema_only:
            positive(value)
    if schema_only:
        return "DRAFT_BLOCKED" if document["status"] == "draft_blocked" else "SCHEMA_ONLY"
    require(document["status"] == "ready_for_human_freeze_review", "unresolved draft status")
    require(document.get("baseline_kind") == "as_built", "unresolved as-built baseline")
    for value in document["records"].values():
        require(isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {"pending", "unknown", "tbd"}, "unresolved evidence record")
    settings = document["settings"]
    require(type(settings["repeats_per_axis"]) is int and settings["repeats_per_axis"] >= 2, "repeatability requires integer repeated trials")
    for key in ("model_discrepancy_fraction", "max_relative_u95", "min_coherence", "max_repeatability_fraction", "max_sensor_mass_fraction"):
        require(settings[key] < 1, f"invalid fraction: {key}")
    require(settings["analysis_low_hz"] < settings["analysis_high_hz"] <= settings["antialias_passband_hz"] < settings["antialias_stopband_hz"] < settings["sample_rate_hz"] / 2,
            "incoherent analysis/antialias/Nyquist bands")
    require(math.isclose(settings["frequency_resolution_hz"], 1 / settings["record_duration_s"], rel_tol=1e-9), "resolution must equal 1/T; zero padding does not improve resolution")
    require(all(settings["analysis_low_hz"] < f < settings["analysis_high_hz"] for f in document["reference_hz"].values()), "as-built references outside analysis band")
    return "READY_FOR_HUMAN_FREEZE_REVIEW_ONLY"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT)
    parser.add_argument("--check-draft", action="store_true")
    args = parser.parse_args()
    try:
        print(check(json.loads(args.path.read_text()), schema_only=args.check_draft))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")


if __name__ == "__main__":
    main()
