# Bounded developer evaluation — selection recorded 2026-09-06

Purpose: challenge the software candidate with additional synthetic parameter
combinations after freezing its source hashes. This is **developer spot-check
evidence**, not held-out physical validation, independent review, or an estimate
of general accuracy. The same author designed the evaluator and cases. They
reuse the published synthetic fixture generator; their scenarios overlap the
development requirements. No claims of distributional independence are made.

Selection before inspecting outputs: take six deterministic boundary/usage
scenarios below, retain all cases, and inspect actual CLI exit/JSON. No random
selection or post-hoc exclusions. Generator and candidate hashes appear in
`candidate.json`; executable case construction will be saved as
`evaluate_candidate.py`. Expected judgments below precede its first run.

| ID | Input construction (all explicitly synthetic) | Expected judgment |
|---|---|---|
| E1 | Add complete cycle 4 to both axes; U95=0.099 | exit 0, SIMULATED_AGREEMENT; 80 rows total |
| E2 | Add complete cycle 4 only to x | exit 0, SIMULATED_AGREEMENT; x40/y30 rows |
| E3 | Add only one cell from cycle 4 | exit 2, incomplete matrix; no verdict JSON |
| E4 | Both reference/row slopes 0.00089 mm/N, resolution 0.0009 mm | exit 0, INCONCLUSIVE (19.78 predicted counts <20) |
| E5 | Add explicit nominal targets; measured load force +0.2 N and unload −0.2 N; response uses measured force | exit 0, SIMULATED_AGREEMENT |
| E6 | Alter raw CSV bytes after manifest hashing | exit 2, checksum mismatch; no verdict JSON |

Retain full CLI stdout/stderr, exit code, input CSV/campaign hashes and actual
classifications in `evaluation-results.json`. Also retain generator parameters
and source identity for reproducibility; temporary paths are not durable
artifacts. A replay regenerates inputs in a fresh temporary directory. All
input bodies are determined by the committed candidate fixture generator and
this runner, rather than claiming the checksums independently prove provenance.

If any outcome drives an implementation change, relabel all observed cases
development material, regenerate the candidate inventory, and do not call a
rerun independent evaluation. No hardware/general safety inference is permitted.

## Observed results — 2026-09-06

First run of `python evidence/sprint-2026-09-05/evaluate_candidate.py` exited 0.
All **6/6 predeclared developer judgments matched**: E1/E2/E5 simulated
agreement, E4 inconclusive, E3 incomplete-matrix error, E6 checksum error.
No cases were omitted and none informed a post-evaluation implementation fix.
Candidate hashes were checked before constructing cases; source stayed fixed.
Full actual CLI outputs, errors, input hashes and source/runner identities:
[evaluation-results.json](evaluation-results.json). Replay regenerates the
same input bytes at new temporary paths; those path changes are expected.

This confirms these six synthetic software cases only. It does not estimate
physical validation accuracy or substitute for a human reviewer.
