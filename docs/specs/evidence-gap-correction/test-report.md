# Fixture and modal correction — test report

Date: 2026-09-11. Base: `51b0e70b858a2839b6ce4a5c4a60987463a29dbf`. Branch: `fix/evidence-gaps-20260911`.

## Reconciliation

The missing fixture-contract artifact is now implemented separately from the still-blocked physical fixture. The modal protocol now exists as a draft with explicit missing numerical fields; it is not a frozen tap-test acceptance band. See [complete item matrix](../../COMPLETION_RECONCILIATION.md). RR-CAD-09 and RR-S11 cover the software/draft only; RR-CAD-02/04/05/06/07, RR-S12 and RR-S13 remain blocked.

## Verification observed by parent

- Existing CAD suite plus new fixture/modal controls: **66 passed**, seven upstream Pyparsing deprecation warnings. Command: `/Users/redhose/.claude-science/conda/envs/cadq/bin/python -m pytest cad/tests -q`.
- `PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py`: exit 0, synthetic converter tests pass.
- `PYTHONPATH=gym python experiments/test_bag_evidence.py`: exit 0, synthetic evidence tests pass.
- `PYTHONPATH=gym python experiments/validate_item11.py`: exit 0, portable offline regression pass.
- `PYTHONPATH=gym python experiments/test_mast_physical_validation.py`: 20 tests, exit 0.
- `python experiments/test_cad_inputs.py`: 3 tests, exit 0.
- `PYTHONPATH=gym python experiments/test_final_report.py`: 6 tests, exit 0.
- `python cad/fixture_contract.py --check-draft`: DRAFT_BLOCKED, exit 0 for valid draft structure.
- `python cad/fixture_contract.py`: BLOCKED, exit 2 for missing geometry.
- `python cad/modal_freeze.py --check-draft`: DRAFT_BLOCKED, exit 0 for valid draft structure.
- `python cad/modal_freeze.py`: BLOCKED, exit 2 for unresolved numeric inputs.

The assigned worker reported test-first missing-implementation failures; the parent independently inspected source and reran the final suite/CLI gates. No independent human review is claimed. No configured standalone typechecker/linter exists; compilation, whitespace, existing CI and CAD export/reimport tests are the applicable checks.

## Acceptance and limits

New controls reject missing/invalid dimensions, datums, units, tolerances, bolt coordinates, malformed tube volume, unresolved modal references, nonfinite/bool numeric values, invalid frequency/anti-alias bands and missing uncertainty records. Synthetic matching geometry only returns MODEL_GEOMETRY_MATCH_ONLY; a populated synthetic modal document at most returns READY_FOR_HUMAN_FREEZE_REVIEW_ONLY.

Neither helper authenticates source metadata or extracts fixture measurements from a real STEP. No fixture model, approved numerical band, modal-result analyzer, calibration, tap acquisition or physical comparison was completed. Existing nominal mast exports, original static criteria and measurement registers remain unchanged. Expanded CAD workflow paths ensure future modal checklist changes trigger the CAD test job.
