# Evidence-gap correction — 2026-09-11

Status: software/draft scope complete; physical acceptance and numerical freeze blocked. Implementation-only scope authorized; physical acceptance is not.
Base: `51b0e70b858a2839b6ce4a5c4a60987463a29dbf`, clean checkout.
Branch: `fix/evidence-gaps-20260911`. Authoritative task states remain in
`docs/CAD_TASKS.csv` and `docs/SPRINT_TASKS.csv`.

## Ordered implementation and acceptance

1. RR-CAD-09: write failing rejection controls, then implement the omitted
   `cad/roboracer/fixture-contract.json` and `cad/fixture_contract.py`.
   Require reviewed dimensions, datums, bolt coordinates, positive tolerances,
   source identity and independent access evidence before geometry comparison.
   Unknown inputs remain null/pending. Geometry match is not stiffness or
   commissioning acceptance. Test missing fields, unresolved inputs, nonfinite
   values, bad units/tolerances and out-of-tolerance reports.
2. RR-S11: write `docs/specs/mast-physical-validation/modal-preregistration.md`
   and a machine-readable DRAFT/BLOCKED freeze checklist with executable
   rejection controls. Numerical measurement/analysis/acceptance settings must
   be filled and reviewed against an inspection-linked as-built model before
   any modal acquisition. No modal ±15% band is authorized. The 174.7 Hz
   rejected baseline and selected 285.5 Hz nominal FE result remain distinct.
3. Run the existing gates plus new tests, record exact results and remaining
   owner actions, update authoritative ledgers, and commit only if green.

## Gates (discovered from CI)

No configured standalone typecheck or lint rung. Use Python compilation and
`git diff --check` for syntax/whitespace; do not claim static typing coverage.
CAD: `/Users/redhose/.claude-science/conda/envs/cadq/bin/python -m pytest cad/tests -q`.
Evidence: `PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py`,
`experiments/test_bag_evidence.py`, `experiments/validate_item11.py`,
`experiments/test_mast_physical_validation.py`, `experiments/test_cad_inputs.py`,
`experiments/test_final_report.py` (same prefix for each).
Presentation: `python tools/check_presentation.py . "Autonomous Racing Systems" autonomous-racing-systems`
and `python tools/test_presentation.py`.
Build: CAD regeneration/STEP roundtrip is covered by CAD suite; also regenerate
with `python cad/generate.py --parameters cad/roboracer/parameters.csv --output <tmp>`
using the CAD interpreter. No unrelated simulation/ROS deployment is required.

Baseline: CAD 28 passed (7 upstream deprecation warnings); physical analyzer
20 tests passed; `python cad/input_requests.py --check` consistent.
System Python 3.13 lacks pytest; use existing registered CAD environment, not
a dependency installation. Remaining evidence gates will be rerun at completion.

## Execution notes

Plan saved before implementation. Steps 1 and 2 implemented as bounded software/draft artifacts. Parent reran the final CAD suite: 66 passed. The real contract and numerical modal checklist remain DRAFT_BLOCKED. Detailed verified evidence is in `test-report.md`; authoritative task states remain in the existing ledgers.
