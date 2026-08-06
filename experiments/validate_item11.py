#!/usr/bin/env python
"""ROS-free regression validator for committed item 11 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_CORETYPE", "Haswell")

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.identification import identify_from_telemetry, metric_dict

EVIDENCE = REPO_ROOT / "evidence" / "item11"
TELEMETRY = EVIDENCE / "telemetry" / "enriched_bridge.csv"
UPSTREAM_TELEMETRY = EVIDENCE / "telemetry" / "upstream_gym_ros.csv"
TOLERANCES = EVIDENCE / "metrics" / "regression_tolerances.json"
METRICS = [
    "fitted_C_Sf",
    "fitted_C_Sr",
    "jacobian_condition_number",
    "raw_jacobian_condition_number",
    "parameter_correlation",
    "heldout_rollout_yaw_rate_rmse",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_metrics() -> dict[str, float]:
    frame = pd.read_csv(TELEMETRY)
    identified = identify_from_telemetry(frame, repo_root=REPO_ROOT)
    if not all(identified.acceptance_checks.values()):
        raise ValueError(f"enriched identification gates failed: {identified.acceptance_checks}")
    duration = float(
        identified.validation_trace["time_s"].iloc[-1]
        - identified.validation_trace["time_s"].iloc[0]
    )
    if duration < 5.5:
        raise ValueError(f"held-out duration is too short: {duration}")
    values = metric_dict(identified.metrics)
    return {name: values[name] for name in METRICS}


def validate_contracts(config: dict[str, object]) -> None:
    enriched_meta = json.loads((EVIDENCE / "metrics" / "enriched_conversion_metadata.json").read_text())
    upstream_meta = json.loads((EVIDENCE / "metrics" / "upstream_conversion_metadata.json").read_text())
    preflight = json.loads((EVIDENCE / "metrics" / "enriched_preflight.json").read_text())
    if not preflight["passed"]:
        raise ValueError("saved enriched preflight did not pass")
    if enriched_meta["steer_rad_source"] != "internal_state" or not enriched_meta["collision_observed"]:
        raise ValueError("enriched source contract is invalid")
    if upstream_meta["steer_rad_source"] != "command_proxy" or upstream_meta["collision_observed"]:
        raise ValueError("upstream source contract is invalid")
    if set(upstream_meta["topic_types"]) != {"/ego_racecar/odom", "/drive"}:
        raise ValueError("upstream evidence must contain only odometry and drive topics")
    if not {
        "/ego_racecar/odom",
        "/drive",
        "/f1tenth/collision",
        "/f1tenth/internal_state",
    }.issubset(enriched_meta["topic_types"]):
        raise ValueError("enriched evidence is missing required topics")
    for name, metadata in (("enriched", enriched_meta), ("upstream", upstream_meta)):
        if float(metadata["required_topic_overlap_s"]) < 19.0:
            raise ValueError(f"{name} overlap gate failed")
        rtf = float(metadata["real_time_factor"])
        if not 0.97 <= rtf <= 1.03:
            raise ValueError(f"{name} RTF gate failed: {rtf}")
    enriched_diagnostics = enriched_meta["topic_diagnostics"]
    if float(enriched_diagnostics["/f1tenth/internal_state"]["observed_rate_hz"]) < 80.0:
        raise ValueError("enriched internal-state rate gate failed")
    for quality_name in ("enriched_quality.csv", "upstream_quality.csv"):
        quality = pd.read_csv(EVIDENCE / "metrics" / quality_name)
        passed = quality["pass"].astype(str).str.lower().map({"true": True, "false": False})
        if passed.isna().any() or not bool(passed.all()):
            raise ValueError(f"saved quality checks failed: {quality_name}")
    hashes = config["telemetry_sha256"]
    if sha256_file(TELEMETRY) != hashes["enriched"]:
        raise ValueError("enriched telemetry hash mismatch")
    if sha256_file(UPSTREAM_TELEMETRY) != hashes["upstream"]:
        raise ValueError("upstream telemetry hash mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--emit-json", action="store_true")
    args = parser.parse_args()
    values = compute_metrics()
    if args.emit_json:
        print(json.dumps(values, sort_keys=True))
        return 0
    config = json.loads(TOLERANCES.read_text())
    validate_contracts(config)
    baseline = config["baseline"]
    for name, value in values.items():
        if args.strict:
            tolerance = float(config["absolute_tolerance"][name])
        else:
            tolerance = max(1e-12, 1e-6 * max(1.0, abs(float(baseline[name]))))
        if abs(value - float(baseline[name])) > tolerance:
            raise ValueError(
                f"{name} drifted: value={value}, baseline={baseline[name]}, tolerance={tolerance}"
            )
    print(f"Item 11 offline regression: PASS ({'strict' if args.strict else 'portable'} mode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
