# Sprint progress — RoboRacer

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
