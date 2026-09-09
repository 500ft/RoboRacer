# RR-CAD-08 verification — 2026-09-09

**Review amendment:** this is the original day-2 evidence snapshot, not the final
acceptance verdict. [Adversarial review](../review-2026-09-09/README.md) reproduced
admission/version/round-trip gaps and corrects the premature completion claim.
The CAD workflow is now installed; hosted verification is pending. The historical
exports below are preserved rather than silently regenerated under revised code.

Base: `04e3ee74a513575eaa9f0de90e3209ebef01e010` (head of the day-1 branch `task/priority-one-20260908`, PR #12). Candidate
identity is the containing PR head. No physical specimen, fabrication or measurement is
claimed; this task delivers tooling that regenerates and tests **model** geometry from the
registered parameters, carrying their evidence states through unchanged.

Deliverables: [`cad/generate.py`](../../cad/generate.py), [`cad/contract.json`](../../cad/contract.json),
[`cad/tests/test_geometry.py`](../../cad/tests/test_geometry.py), [`cad/requirements.lock`](../../cad/requirements.lock),
and the geometry CI as [`ci-proposed/cad-geometry-workflow.patch`](../../ci-proposed/cad-geometry-workflow.patch).
Authoritative status: [CAD_TASKS.csv](../../docs/CAD_TASKS.csv). The earlier sprint ledger is byte-preserved.

## Environment lock

Pinned after a clean isolated conda-forge install and a STEP export/reimport smoke test
(20 × 10 × 5 mm box: volume 1000.000000 → 1000.000000 mm³, relative difference 0):
Python 3.11.16, CadQuery 2.8.0, OCP 7.9.3.1, numpy 2.4.6.
`test_installed_versions_match_lock` fails if the running environment departs from the lock.

## Reproduction and observed evidence

Commands run from the repository root in the locked environment.

| Command | Observed result |
| --- | --- |
| `python cad/generate.py --parameters cad/roboracer/parameters.csv --output evidence/task-2026-09-09/cad-out` | exit 0, 2.2 s — `mast_tube: volume 8717.920 mm^3  mass 23.538 g  bbox [20.0, 20.0, 100.0]  -> evidence/task-2026-09-09/cad-out` |
| `python -m pytest cad/tests -q` | exit 0, 2.7 s — **11 passed** |
| `git apply --check ci-proposed/cad-geometry-workflow.patch` | exit 0 |
| embedded CAD ledger validator (docs/CAD_PLAN_CHECKS.md) | see below, run after this ledger edit |

## Geometry family: `mast_tube`

| metric | analytic (from register) | CadQuery solid | after STEP re-import |
| --- | ---: | ---: | ---: |
| volume, mm³ | 8717.919614 | 8717.919614 | 8717.919614 |
| bbox, mm | [20.0, 20.0, 100.0] | [20.0, 20.0, 100.0] | [20.0, 20.0, 100.0] |
| mass, g | 23.5384 | 23.5384 | 23.5384 |

Retained: [`cad-out/geometry.json`](cad-out/geometry.json) (all metrics, input evidence states,
file hashes, versions) and [`cad-out/mast_tube.step`](cad-out/mast_tube.step).

## Fail-closed behaviour proven by test

Altered parameter → contract assertion fails · invalid dimensions → `GeometryInputError` ·
missing register row → `GeometryInputError` · empty (pending) value → `GeometryInputError` ·
unit mismatch → `GeometryInputError` · truncated STEP → import/metric check raises ·
CLI on bad input → exit 2 with `REFUSED`.

## Not modelled, and why
- Every parameter this family needs is registered with a value; nothing was guessed.


Pending parameters in the register (6) are listed in `geometry.json`
and remain owner inputs. Passing this contract means the code regenerates the intended model;
it says nothing about an as-built part.
