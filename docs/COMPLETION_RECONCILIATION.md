# RoboRacer completion reconciliation — 2026-09-11

This corrects the omission of the fixture geometry contract as a distinct deliverable. Task states are in CAD_TASKS.csv and SPRINT_TASKS.csv.

| Recommendation | Implemented here | Still not completed |
| --- | --- | --- |
| Fixture geometry contract | [JSON contract](../cad/roboracer/fixture-contract.json), [comparator](../cad/fixture_contract.py), [regression tests](../cad/tests/test_fixture_contract.py) | Populated reviewed geometry, actual fixture CAD/STEP, fabrication and metrology acceptance |
| Tap-test protocol artifact | [Draft procedure](specs/mast-physical-validation/modal-preregistration.md), [freeze fields](specs/mast-physical-validation/modal-freeze.json), [completeness checker](../cad/modal_freeze.py) | Numerical freeze, authenticated calibration/reference review and acquisition |
| Modal target | Rejected 174.7 Hz and selected nominal 285.5 Hz explicitly distinguished | Inspection-linked as-built x/y references and justified pass band |
| Owner measurement sitting | [Pending input sheet](../cad/roboracer/input-requests.csv) and [fixture preparation](../cad/roboracer/fixture-preparation.md) | Actual dimensions, instrument uncertainties, stiffness/rotation evidence and approval |
| Physical validation | Existing static analyzer unchanged | No physical static or modal campaign result |

A structurally valid draft returns DRAFT_BLOCKED, not permission to fabricate or test. The fixture comparison is only a comparison of supplied CAD observations to reviewed targets; it does not extract a new STEP model or authenticate the input records. The modal checker can at most return READY_FOR_HUMAN_FREEZE_REVIEW_ONLY. It is not an implemented modal analyzer or frozen experiment.

## Smallest next owner input

Identify the specimen/fabrication route and provide the generated register's actual dimensions, datums, sensor/mass arrangement and calibration/uncertainty records. Resolve root restraint and indicator placement first. Then populate and review the fixture targets. After actual geometry and instrument uncertainty exist, derive both as-built modal references and the numerical discrepancy/quality decision rule, commit and push the approved protocol before loading/tapping.

Keep the static ±15% agreement criterion separate. It cannot supply an arbitrary band about 174.7 Hz or 285.5 Hz. Missing calibration, root motion or as-built evidence remains a blocker, not a nominal value.

## Reproduce

```sh
python cad/fixture_contract.py --check-draft
python cad/fixture_contract.py
python cad/modal_freeze.py --check-draft
python cad/modal_freeze.py
```

Draft checks exit 0; strict commands exit 2 on the committed missing inputs. Full CAD/evidence checks are recorded in [correction test report](specs/evidence-gap-correction/test-report.md). No physical input, model output, or original numerical threshold was changed.
