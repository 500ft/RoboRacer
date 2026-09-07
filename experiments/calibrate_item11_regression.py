#!/usr/bin/env python
"""Calibrate strict item 11 tolerances from fresh validator processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = REPO_ROOT / "evidence" / "item11"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Reproducibility floors, relative to max(1, |baseline|), derived from the numerics that
# define each metric rather than from repeats on one machine. Same-machine repeats observe
# zero spread, so the previous 100-ULP floor (2.2e-14 relative) became the gate and failed
# on GitHub runners with a 242-ULP (3.9e-14 relative) shift of fitted_C_Sr that is not a
# regression:
# - fitted coefficients: least_squares stops at xtol=ftol=gtol=1e-13 on log-parameters, so
#   the converged value is only defined to ~1e-13 relative; a different BLAS/SIMD path moves
#   it within that band. Floor = 1e3 x xtol = 1e-10 (10^4 below the 1e-6 meaning ceiling).
# - Jacobian-derived diagnostics: result.jac is a 2-point finite difference with ~sqrt(eps)
#   (~1e-8) accuracy; a 1e-8 cross-interpreter spread was already observed. Floor = 1e-7.
# - held-out RMSE (~3e-10) is a rounding residue of the RK4 rollout on model-generated
#   telemetry; it is gated as an upper bound in validate_item11.py, not as an equality.
RELATIVE_FLOOR = {
    "fitted_C_Sf": 1e-10,
    "fitted_C_Sr": 1e-10,
    "jacobian_condition_number": 1e-7,
    "raw_jacobian_condition_number": 1e-7,
    "parameter_correlation": 1e-7,
    "heldout_rollout_yaw_rate_rmse": 1e-10,
}
UPPER_BOUND = {"heldout_rollout_yaw_rate_rmse": 1e-8}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument(
        "--comparison-python",
        action="append",
        default=[],
        help="Additional Python executable whose observed outputs contribute to tolerance calibration.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EVIDENCE / "metrics" / "regression_tolerances.json",
    )
    args = parser.parse_args()
    runs = []
    interpreters = [sys.executable, *args.comparison_python]
    for interpreter in interpreters:
        for _ in range(args.repeats):
            output = subprocess.check_output(
                [interpreter, str(REPO_ROOT / "experiments" / "validate_item11.py"), "--emit-json"],
                cwd=REPO_ROOT,
                text=True,
            )
            runs.append(json.loads(output))
    names = sorted(runs[0])
    baseline = {name: float(np.mean([run[name] for run in runs])) for name in names}
    tolerance = {}
    for name in names:
        values = np.array([run[name] for run in runs], dtype=float)
        observed_range = float(np.ptp(values))
        scale = max(1.0, abs(baseline[name]))
        tolerance[name] = max(5.0 * observed_range, RELATIVE_FLOOR[name] * scale)
    for name in ("fitted_C_Sf", "fitted_C_Sr"):
        if tolerance[name] / abs(baseline[name]) > 1e-6:
            raise ValueError(f"calibrated coefficient tolerance is too wide: {name}")
    interpreter_versions = [
        subprocess.check_output([interpreter, "--version"], text=True, stderr=subprocess.STDOUT).strip()
        for interpreter in interpreters
    ]
    payload = {
        "repeats_per_interpreter": args.repeats,
        "interpreter_versions": interpreter_versions,
        "baseline": baseline,
        "absolute_tolerance": tolerance,
        "relative_floor": RELATIVE_FLOOR,
        "upper_bound": UPPER_BOUND,
        "telemetry_sha256": {
            "enriched": sha256(EVIDENCE / "telemetry" / "enriched_bridge.csv"),
            "upstream": sha256(EVIDENCE / "telemetry" / "upstream_gym_ros.csv"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
