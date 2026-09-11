# Sprint progress — RoboRacer

## 2026-09-11 — evidence-gap correction

The [current correction](COMPLETION_RECONCILIATION.md) supersedes any interpretation that earlier preparation closed a physical, approval, or source-review gate. Work is on `fix/evidence-gaps-20260911` from current renamed main; historical entries below retain their original dates and PR snapshots. The original day-3 and presentation PRs are now merged, but this correction is a new reviewable change, not an asserted merge or publication.

Each omitted or incomplete recommendation is accounted for separately in the current correction and existing task ledgers. No owner signature, measurement, PI conversation, imagery judgment, disclosure approval or independent review was fabricated. Exact tests, scope and next inputs are linked from the correction record; actual delivery state is established by its PR.

## Day-3 work — 2026-09-09

Delivery update: the preparation was committed as 500ft and pushed; [day-3 PR](https://github.com/500ft/RoboRacer/pull/14) is open against main. Initial implementation source: `b1a3120bce422a8bbd334c2006b04533a6632a8a` (later review/documentation commits are visible in the PR). This supersedes the pre-push stopping state below. Original day-1/day-2 PRs are merged; this new PR is not merged. Resume from the named unresolved project gates in [DAY3_PLAN.md](DAY3_PLAN.md), not from the already completed push step.

Both reviewed PR layers merged into main; new work starts from `44491a62d4418294d14143466c757010b1694ba4` on `task/day-three-20260909`. Six request-sheet tests cover exact pending-row coverage, future rows, invalid units, a filled pending value, duplicates and snapshot drift. 28 CAD tests pass. The failed 174.7 Hz baseline is distinguished from the selected nominal 285.5 Hz FE result; static acceptance is not repurposed as a modal verdict.

The [evidence record](../evidence/task-day3-2026-09-09/README.md) contains checks and limits. Work is locally verified and not yet recorded here as pushed/merged. Current edits belong to this task; original checkouts were preserved. Next: finish verification, commit the bounded change and open the new PR; preserve all stated external gates.

## Hosted tooling acceptance — 2026-09-09

RR-CAD-08 is now **done**: hosted geometry and existing CI passed for source
`8cefd74f15af71f95125d4fc15f62331d52ee795`. The uploaded STEP was downloaded, hash-checked,
reimported and checked for one solid and contracted volume. See
[hosted checks and artifact identity](../evidence/review-2026-09-09/hosted-verification.json). This supersedes the
intermediate in-progress statements below. Owner/physical gates remain open.


## 2026-09-09 — adversarial CAD review amendment

The original day-2 completion statement below was premature: a proposed workflow
is not running CI. RR-CAD-08 is now `in_progress` pending a green hosted CAD job.
The workflow is installed and existing CI also targets day-1 stack bases. Current
authentication includes workflow permission; the old restriction is historical.

Baseline 11 CAD tests passed. Eleven regression cases then failed on the
original implementation: nonfinite numeric inputs, populated pending/blank states,
duplicate parameter rows, three unchecked dependency versions, and two undetected
STEP round-trip metric changes. Minimal fixes produce 22 passing CAD tests.
The direct-package constraints are not a platform/transitive build lock.
See [review evidence](../evidence/review-2026-09-09/README.md).
Owner gates, recorded dimensions, registered thresholds, original model exports,
and the historical sprint ledger are unchanged. No fabrication or measurement.
Next action: push the amended PR, observe both hosted jobs, then close only the
tooling task if its installed geometry job passes.

## 2026-09-09 — RR-CAD-08 code-CAD regeneration and geometry tests (historical initial handoff)

Completed the day-2 CAD tooling task. CadQuery is installed in an isolated environment and
pinned in [`cad/requirements.lock`](../cad/requirements.lock) only after a STEP export/reimport
smoke test. [`cad/generate.py`](../cad/generate.py) regenerates the `mast_tube` family from
the registered parameters and refuses anything missing, pending, mis-united or invalid;
[11 tests](../cad/tests/test_geometry.py) hold it to [`cad/contract.json`](../cad/contract.json)
and prove failure on every bad-input class the task names. Geometry CI is shipped as an
appliable patch under `ci-proposed/` because the PR token lacks workflow scope. No CAD model of a
fixture, no physical part and no owner approval; owner gates are unchanged. Sole status is in
[CAD_TASKS.csv](CAD_TASKS.csv). [Verification](../evidence/task-2026-09-09/README.md).
Branch `task/priority-two-20260909`, stacked on the day-1 branch.
Next check: `python -m pytest cad/tests -q`.

## 2026-09-08 — RR-CAD-01 input register

Completed the existing highest-priority ready CAD-input task; its sole status is
in [CAD_TASKS.csv](CAD_TASKS.csv), not a duplicate sprint row. Historical sprint
CSV remains byte-preserved. [Inputs](../cad/roboracer/design-inputs.md) and
[verification](../evidence/task-2026-09-08/README.md) distinguish design/vendor
values from unavailable fit/measurement inputs. No CAD model, physical test or
owner approval. RR-CAD-08 is now ready for a later software tooling task; owner
interface approval still blocks real geometry acceptance and fabrication.
Branch `task/priority-one-20260908`; PR records committed/pushed identity.
Next check: `python experiments/test_cad_inputs.py`.

## 2026-09-06 — Reviewer-driven CAD amendment

This entry supersedes the earlier CAD allocation and readiness wording. The same CAD PR is now draft, pending the owner planning-ledger placement decision. [Review disposition](CAD_REVIEW_DISPOSITION.md) records that block; [CAD_PLAN.md](CAD_PLAN.md) and [CAD_TASKS.csv](CAD_TASKS.csv) contain revised priorities, separate tooling estimates and explicit parked work. No CAD model or new measurement was produced. Original integrity-sprint tasks/evidence remain unchanged. Next work is limited to active input-register tasks and unresolved owner decisions, not the parked portfolio-wide CAD program.

## 2026-09-06 — CAD task amendment

Added [individual CAD work orders](CAD_PLAN.md) and [CAD_TASKS.csv](CAD_TASKS.csv), separating component modeling, fixtures, inspection and release deliverables. This is planning only: no CAD or physical task is complete. The original sprint ledger and evidence are unchanged. CAD branch: `plan/cad-tasks-20260906`; the PR supplies the committed source identity. Next CAD action: the first input-register task in the CAD ledger; owner-gated successors remain blocked. Verification of this amendment is recorded in [CAD_PLAN_CHECKS.md](CAD_PLAN_CHECKS.md).

## 2026-09-05 — baseline and plan

Read root AGENTS and execute-and-test/quality-gates skills. No repo-local AGENTS found. Dedicated clean worktree branch `sprint/evidence-integrity-20260905`, base `bea803741ab91c8d1e782064666d97f302dbb9d9`; original checkout untouched. Python 3.11.8 macOS arm64.

Five CI commands passed before changes. Original incomplete-matrix defect reproduced exactly (`VALIDATED`, four rows, one axis). Additional dynamics-loader and replay-metric scripts also passed; these are supplementary, not the canonical five checks. No hardware or Docker execution occurred. Selected baseline output and complete reproduction recorded in [baseline](../evidence/sprint-2026-09-05/baseline.md).

Saved 30-hour roadmap, authoritative CSV and partial review index. Plan presentation precedes implementation. No behavior changed at this point. Only new sprint records are dirty; no commits/pushes. Owner hardware/readiness and independent review pending. Next: prospective contract amendment, then RR-S04 failing tests after parent confirms plan has been presented.

## 2026-09-06 — corrected candidate and reproducible developer evaluation

Resumed the saved branch/ledger, rather than restarting the sprint. Plan was
presented before GO and behavioral changes. Source base remains
`bea803741ab91c8d1e782064666d97f302dbb9d9`; branch
`sprint/evidence-integrity-20260905`. Original checkout was not modified.

The first regression run failed with 25 failing subcases: incomplete matrices,
invalid/non-finite cells and uncertainty, and missing reference still accepted.
Retained [red-matrix.log](../evidence/sprint-2026-09-05/red-matrix.log). After
implementation, two additional red regressions exposed stale provenance reuse
and an impossible circular reference-commit contract; the reference-artifact
commit now lives in campaign metadata, separately from the model-source commit.
Retained [red-provenance.log](../evidence/sprint-2026-09-05/red-provenance.log).

Current behavior enforces complete matrix and pairing, preserves measured
forces with explicit nominal labels, rejects non-finite inputs, uses checked
axis-specific reference values, checks campaign/calibration/uncertainty and
file/source identities, and rereads provenance at verdict time. Synthetic
fixtures return simulated labels; a missing campaign is inconclusive and the
CLI requires `--campaign`. No July numerical threshold was relaxed. Physical
scope language is now conditional; no apparatus or result was invented.

Compile and whitespace checks plus the five portable CI entry points pass.
Mast suite: 20 tests; final report: 6 tests. Actual CLI integration is tested,
including the intentional old-command migration error. Full outputs in
[green-portable.log](../evidence/sprint-2026-09-05/green-portable.log).

Runtime inspection initially raised `PackageNotFoundError: numba` when looking
up all package metadata in one comprehension. A safe inventory clarified:
NumPy 2.1.1, SciPy 1.15.2, pandas 2.2.3, PyYAML 6.0.2, rosbags 0.11.3,
ReportLab 4.5.1, pypdf 6.12.2; numba distribution metadata unavailable. This
was a diagnostic inventory failure, not a failing product test. Python 3.11.8
portable checks are **not** a reproduction of pinned Python 3.10 CI or the
Docker/full legacy Gym environment. No dependency versions were changed.

Candidate/source hashes were recorded before first execution of six
predeclared developer spot-check cases. **6/6** matched their prior expected
judgments; no exclusions or follow-on source fixes occurred. Replay:
`python evidence/sprint-2026-09-05/evaluate_candidate.py`. Candidate hash
verification is built into the runner. Inputs are synthetic, developer-selected
and related to the regression requirements: not independent/held-out empirical
validation. [Provenance and outcomes](../evidence/sprint-2026-09-05/evaluation.md).

At handoff, tracked modifications are README, mechanical design status,
physical protocol/test report, evaluator and its tests; new sprint documents,
readiness checklist and evidence directory remain untracked. No commits,
pushes, outreach, purchases, fabrication or physical tests occurred. Planning
estimates total 30 h; task completion does not claim 30 actual hours elapsed.

Next command for a reviewer: `python evidence/sprint-2026-09-05/evaluate_candidate.py`,
then the five commands in [REVIEW_READY.md](REVIEW_READY.md). Next owner action:
complete RR-S02 readiness and nominate/authorize an independent reviewer for
RR-S09. These are external blockers, not grounds to improvise a physical result.
