#!/usr/bin/env python3
"""Replay six declared developer cases, never a physical validation campaign."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
from test_mast_physical_validation import (  # noqa: E402
    FEA_COMPLIANCE_MM_PER_N,
    synthetic_rows,
    write_synthetic_campaign,
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    candidate = json.loads(Path(__file__).with_name("candidate.json").read_text())
    for filename, expected in candidate["files"].items():
        if sha(ROOT / filename) != expected:
            raise SystemExit("Candidate changed: " + filename + "; rebaseline before evaluation")
    expected = {
        "E1": (0, "SIMULATED_AGREEMENT"),
        "E2": (0, "SIMULATED_AGREEMENT"),
        "E3": (2, None),
        "E4": (0, "INCONCLUSIVE"),
        "E5": (0, "SIMULATED_AGREEMENT"),
        "E6": (2, None),
    }
    results = []
    for identifier, (expected_exit, expected_classification) in expected.items():
        rows = synthetic_rows()
        options = {}
        if identifier in ("E1", "E2", "E3"):
            extra = [dict(row, cycle=4) for row in rows if row["cycle"] == 1]
            if identifier == "E2":
                extra = [row for row in extra if row["axis"] == "x"]
            if identifier == "E3":
                extra = extra[:1]
            rows += extra
            if identifier == "E1":
                options["u95"] = 0.099
        elif identifier == "E4":
            rows = synthetic_rows(scale=0.00089 / FEA_COMPLIANCE_MM_PER_N)
            options = {"compliances": {axis: 0.00089 for axis in ("x", "y")}, "resolution": 0.0009}
        elif identifier == "E5":
            for row in rows:
                row["load_level_n"] = row["force_n"]
                row["force_n"] += 0.2 if row["direction"] == "load" else -0.2
                row["tip_mm"] = row["fixture_mm"] + FEA_COMPLIANCE_MM_PER_N * row["force_n"]
        with tempfile.TemporaryDirectory(prefix="rr-developer-evaluation-") as directory:
            campaign, raw = write_synthetic_campaign(directory, rows, **options)
            if identifier == "E6":
                # Bytes change after hashing. No missing output is interpreted
                # as a zero-error result; this must be a controlled input error.
                raw.write_bytes(raw.read_bytes() + b"\n")
            command = [sys.executable, str(ROOT / "experiments/mast_physical_validation.py"),
                       str(raw), "--campaign", str(campaign)]
            process = subprocess.run(command, capture_output=True, text=True, check=False)
            payload = json.loads(process.stdout) if process.returncode == 0 else None
            classification = payload["classification"] if payload else None
            results.append({
                "id": identifier,
                "evidence_kind": "synthetic developer spot check",
                "expected_exit": expected_exit,
                "expected_classification": expected_classification,
                "observed_exit": process.returncode,
                "observed_classification": classification,
                "matches_predeclared_judgment": process.returncode == expected_exit and classification == expected_classification,
                "rows": len(rows),
                "raw_csv_sha256": sha(raw),
                "campaign_sha256": sha(campaign),
                "command": command,
                "stdout": process.stdout,
                "stderr": process.stderr,
            })
    print(json.dumps({"candidate": candidate, "runner_sha256": sha(Path(__file__)),
                      "selection": "six predeclared developer cases; no exclusions",
                      "limitations": "synthetic fixtures; developer-selected; not independent or physical validation",
                      "results": results}, indent=2, allow_nan=False))
    return 0 if all(item["matches_predeclared_judgment"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
