#!/usr/bin/env python3
# Gate the dynamic replay on its committed metrics, not on figure bytes.
#
# Why numbers and not pixels: reports/figures/dynamic_replay_*.png were reported during an
# audit as showing "content drift". They do not. runs/dynamic_model_replay/metrics.csv is
# committed, and a fresh run reproduces it to <= 8 ULPs -- 14 of 18 metrics byte-identical,
# worst relative difference 1.0e-15 against a double-precision epsilon of 2.2e-16. The
# pixel differences come from the renderer, so a byte comparison of the PNGs reports drift
# that does not exist and would bury drift that does.
#
# Run: PYTHONPATH=gym python experiments/test_replay_metrics.py

import csv
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
COMMITTED = REPO / "runs" / "dynamic_model_replay" / "metrics.csv"

# Wide enough for BLAS/summation-order reassociation across platforms, ~1e6 tighter than
# any change that would matter physically. The observed cross-run spread is 1e-15.
REL_TOL = 1e-9


def read_metrics(path: pathlib.Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["metric"]: float(row["value"]) for row in csv.DictReader(handle)}


def main() -> None:
    committed = read_metrics(COMMITTED)
    assert committed, f"no metrics found in {COMMITTED}"

    with tempfile.TemporaryDirectory() as tmp:
        # Regenerate into a scratch tree so the committed artifacts are never written.
        result = subprocess.run(
            [sys.executable, str(REPO / "experiments" / "dynamic_model_replay.py"),
             "--run-dir", tmp],
            cwd=REPO, capture_output=True, text=True,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stdout[-2000:] + result.stderr[-2000:])
            raise SystemExit(f"replay generator failed with rc={result.returncode}")
        fresh = read_metrics(pathlib.Path(tmp) / "metrics.csv")

    missing = sorted(set(committed) - set(fresh))
    assert not missing, f"metrics absent from the regenerated run: {missing}"
    added = sorted(set(fresh) - set(committed))
    assert not added, f"regenerated run produced metrics absent from the committed file: {added}"

    identical = 0
    worst_name, worst_rel = "", 0.0
    for name, want in committed.items():
        got = fresh[name]
        if got == want:
            identical += 1
            continue
        rel = abs(got - want) / max(abs(want), 1e-300)
        if rel > worst_rel:
            worst_name, worst_rel = name, rel
        assert rel <= REL_TOL, (
            f"{name} moved by {rel:.3e} relative ({want!r} -> {got!r}), "
            f"above the {REL_TOL:.0e} tolerance"
        )

    print(f"replay metrics OK: {len(committed)} metrics, {identical} byte-identical, "
          f"worst relative drift {worst_rel:.2e}"
          + (f" ({worst_name})" if worst_name else ""))


if __name__ == "__main__":
    main()
