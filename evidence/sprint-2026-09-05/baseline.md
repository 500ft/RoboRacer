# Baseline — captured 2026-09-05 before behavior changes

Working directory `/Users/redhose/Developer/research-sprints/2026-09-05/RoboRacer`; remote `https://github.com/500ft/RoboRacer.git`; branch `sprint/evidence-integrity-20260905`; HEAD `bea803741ab91c8d1e782064666d97f302dbb9d9`; tree initially clean. Python 3.11.8; macOS-14.7.3-arm64-arm-64bit. CI declares Python 3.10, so this is portable local execution, not reproduction of the pinned Docker environment.

## Commands and selected original outputs

Each command run from the directory above, with prefix `PYTHONPATH=gym`:

| Command | Exit | Selected stdout/stderr |
|---|---:|---|
| `python experiments/test_rosbag_to_telemetry.py` | 0 | `rosbag_to_telemetry synthetic tests passed` |
| `python experiments/test_bag_evidence.py` | 0 | `Verified bag evidence: synthetic`; `bag evidence tests passed` |
| `python experiments/validate_item11.py` | 0 | `Item 11 offline regression: PASS (portable mode)` |
| `python experiments/test_mast_physical_validation.py` | 0 | `Ran 5 tests in 0.001s`; `OK` |
| `python experiments/test_final_report.py` | 0 | `Ran 6 tests in 1.307s`; `OK` |

Outputs are selected excerpts, not full transcripts. Dynamics loader and replay-metrics supplementary commands also exited 0 (`Dynamics loader regression: PASS`; `18 metrics, 18 byte-identical, worst relative drift 0.00e+00`). No dependency installation was required. No new physical dataset exists.

## Reproduced RR-1 defect

Exact command at base (one x-axis cycle, two loads, complete pairing at only those two loads):

```bash
PYTHONPATH=experiments python -c 'from mast_physical_validation import evaluate_rows,FEA_COMPLIANCE_MM_PER_N as c; rows=[dict(axis="x",cycle=1,direction=d,force_n=f,tip_mm=c*f,fixture_mm=0) for d in ("load","unload") for f in (4,20)]; print(evaluate_rows(rows,0.05))'
```

Exit 0, output:

```text
Verdict(classification='VALIDATED', reasons=['all quality gates pass and compliance is within 15% of as-built FEA'], relative_u95=0.05, fixture_subtracted=True, axes=[AxisMetrics(axis='x', rows=4, compliance_mm_per_n=0.0013668841255048152, intercept_mm=0.0, r_squared=1.0, hysteresis_fraction=0.0, fea_relative_error=0.0)])
```

Expected under written protocol: no validation; x/y and ≥3 complete cycles with five loads are required, and no as-built comparison evidence is supplied. This synthetic input is development evidence only.
