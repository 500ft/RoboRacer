# RoboRacer — trustworthy mast-evaluation sprint

## Separate CAD phase — added 2026-09-06

Individual mechanical work orders now live in [CAD_PLAN.md](CAD_PLAN.md), with their own authoritative [CAD_TASKS.csv](CAD_TASKS.csv). They are additional, unexecuted work outside this original 30-hour integrity sprint. Existing physical-readiness and publication gates remain open until their actual evidence arrives.

Prepared 2026-09-05. Six workload days, **30 focused hours**, not unattended calendar execution. Scope: reviewer-reproducible mast analysis software and an honest hardware-pending handoff; no physical-validation claim.

## A. Identity and outcome

Canonical sprint checkout: `/Users/redhose/Developer/research-sprints/2026-09-05/RoboRacer`; remote `https://github.com/500ft/RoboRacer.git`; branch `sprint/evidence-integrity-20260905`; base `bea803741ab91c8d1e782064666d97f302dbb9d9`. Initial tree clean. This dedicated worktree leaves the original checkout untouched. No commit, push, fabrication, spending, or outreach is included in this batch.

Publication-state update (2026-09-06): the owner authorized local commits, branch
pushes, and pull requests for this sprint. This does not authorize deployment,
research publication, outreach, spending, or any blocked physical/data action.

Outcome: an evaluator that cannot call an incomplete, non-finite, synthetic, nominal-reference-only, or untraceable campaign physical validation. A reviewer can replay the original defect and counterexamples, inspect corrected classifications, and rerun CI entry points. This does not establish mast compliance, impact resistance, modal behavior, or vehicle performance.

## B. Verified baseline and gaps

- **Verified:** Python 3.11.8 on macOS 14.7.3 arm64; five portable entry points in [CI](../.github/workflows/ci.yml) exit 0 locally. CI specifies Python 3.10; local execution is not that pinned environment or the Docker build. [Recorded commands and selected outputs](../evidence/sprint-2026-09-05/baseline.md).
- **Reproduced failure RR-1:** one x-axis, one cycle, forces 4 and 20 N produces `VALIDATED`, without an as-built artifact. [Evaluator](../experiments/mast_physical_validation.py) contradicts the [frozen protocol](specs/mast-physical-validation/design.md). Complete reproduction is in the baseline evidence.
- **Verified:** the evaluator uses nominal constants for the as-built comparison and does not enforce the complete trial matrix or finite values. Instrument adequacy is a standalone helper, not a verdict prerequisite.
- **Verified RR-3:** [mechanical design](design/16_mechanical_design_analysis.md) says design-only/no fabrication while the later protocol describes a conditional physical campaign. Reconcile status without claiming hardware exists.
- **Reported, outside this sprint:** independent-plant control performance (RR-2). Keep simulation findings scoped; do not add controller experiments to this budget.

## C. Deliverables and critical path

Must-have: fail-closed inputs/matrix; traceable axis-specific reference/campaign contract; honest synthetic classification; adversarial regression evidence; actual CLI exercise; aligned protocol/status; review packet. Existing numerical R², hysteresis, uncertainty, and ±15% thresholds stay fixed. A prospective input-schema clarification can distinguish nominal load labels from measured forces without changing numerical acceptance thresholds.

Owner preparation: obtain released drawing/inspection, as-built FEA, calibrated instruments and uncertainty/zero-check records, plus safe fixture access before any physical use. Agent prepares a checklist; Owner/External supply and approve evidence. Neither availability nor approval is currently verified.

Critical path: RR-S01 → RR-S03 → RR-S04 → RR-S05 → RR-S07 → RR-S08 → RR-S10. Owner hardware readiness RR-S02 is independent of software and **blocks physical campaigns only**. RR-S09 requests independent review only if the Owner supplies an authorized reviewer; preparing a request is not sending it.

## D. Workload allocation

| Day | Hours | Primary deliverable |
|---|---:|---|
| 1 | 5 | Baseline, bounded contract, owner-readiness checklist |
| 2 | 5 | Red/green matrix and numeric-input corrections |
| 3 | 6 | Provenance-aware API/CLI and reconciled documentation |
| 4 | 4 | Portable verification and candidate/source manifest |
| 5 | 6 | Frozen-candidate developer challenge cases and disposition |
| 6 | 4 | Review feedback if available and partial review packet |
| **Total** | **30** | Software-verifiable integrity improvements; hardware pending |

## E. Daily tasks

The [CSV ledger](SPRINT_TASKS.csv) is the only task-status authority. Paths marked **new** did not exist at baseline. Estimates are planning effort, not claimed elapsed work.

### Day 1 — 5 h

1. **RR-S01, P0, Agent, 2 h, no dependencies.** Inspect `experiments/mast_physical_validation.py`, its test, `docs/specs/mast-physical-validation/design.md`, `.github/workflows/ci.yml`, `requirements-{item11-regression,report}.txt`. Run the five baseline commands below; record identity, runtime, statuses and complete incomplete-matrix reproduction. Deliver **new** `evidence/sprint-2026-09-05/baseline.md`. Done when another reviewer can run the same reproduction at base and see the false verdict.
2. **RR-S02, P1, Owner, 1 h, no dependencies.** Review **new** `docs/specs/mast-physical-validation/campaign-readiness.md` and provide availability/authorization for drawings, as-built metrology, FEA, calibration, force/displacement instruments, fixture and reviewer. Agent drafts checklist only. Done when owner readiness is recorded; otherwise blocked with explicit inputs, no invented hardware dates.
3. **RR-S03, P0, Agent, 2 h, depends RR-S01.** Write this roadmap/CSV/progress/review index (**new**) and prospective contract amendment to existing design. Require both x/y, ≥3 complete cycles each, five nominal targets with measured-force values, complete load/unload pairing, finite positive inputs, checksummed evidence and source revision, calibration/uncertainty records. Synthetic evidence must be labeled and never emit physical `VALIDATED`. Done when contract is written before code and numerical gates unchanged.

### Day 2 — 5 h

1. **RR-S04, P0, Agent, 5 h, depends RR-S03.** In existing `experiments/test_mast_physical_validation.py`, add failing regressions for incomplete matrices, missing pairs, invalid axes/cycles/directions/forces, duplicates, NaN/infinity, and zero-displacement edge cases. Correct existing evaluator minimally. Deliver red/green logs under **new** evidence directory. Command: `python experiments/test_mast_physical_validation.py`. Done when original bug is rejected, complete positive synthetic fixtures retain numerical behavior, invalid inputs have controlled outcomes, and no threshold is relaxed.

### Day 3 — 6 h

1. **RR-S05, P0, Agent, 3 h, depends RR-S04.** Add a versioned campaign/reference input to the existing evaluator and tests. Enforce complete provenance fields, artifact SHA-256 correspondence, axis-specific as-built reference, positive resolution plus ≥20 predicted counts, and uncertainty linkage. Reject missing nominal-only or inconsistent references. Deliver a contract documented in existing design and **new** readiness checklist. Done when forged/missing/hash-mismatched artifacts cannot earn validation and synthetic fixtures cannot be called measured evidence. Checksums establish identity, not authenticity of experiments.
2. **RR-S06, P1, Agent, 3 h, depends RR-S05.** Exercise actual CLI with temporary synthetic files and malformed/missing campaign inputs; record JSON and exit behavior. Update existing README, mechanical design status, protocol reproduction command and test report. Deliver **new** CLI/evidence logs. Done when missing new prerequisite fails with useful text, old command cannot silently validate, and documentation says conditional physical work rather than contradictory commitments.

### Day 4 — 4 h

1. **RR-S07, P0, Agent, 4 h, depends RR-S06.** Rerun the five CI entry points, `python -m py_compile experiments/mast_physical_validation.py experiments/test_mast_physical_validation.py`, and `git diff --check`. Record candidate SHA-256 inventory (**new** `evidence/sprint-2026-09-05/candidate.json`) and CLI outputs. No typecheck/linter configured; compile and whitespace checks supplement, not replace, CI tests. Docker workflow is separate and must remain unverified unless executed. Done when checks pass and candidate identity is frozen before selecting further challenge inputs.

### Day 5 — 6 h

1. **RR-S08, P1, Agent, 6 h, depends RR-S07.** Freeze a small developer evaluation selection protocol before inspecting outcomes: perturbed per-axis reference, ≥4 complete cycles, approximate measured target forces, near-threshold instrumentation, missing calibration file, and stale checksum. Retain expected judgments before candidate outputs, with input generator revision/hashes. Add separate cases beyond the red/green training set. Deliver **new** `evaluation.md` and logs. Done when observed outcomes and disagreements are recorded; if a case informs a fix, relabel it development and freeze a revised candidate. This is a developer spot check, not independent validation or a general error-rate estimate.

### Day 6 — 4 h

1. **RR-S09, P1, External, 2 h, depends RR-S08.** Owner supplies reviewer and authorization to share. Provide ready-to-send request in review index. Reviewer checks one rejection, reference provenance and one nominal numerical case. Done only with actual written feedback; otherwise explicit pending, no assumed outreach or invented reviewer.
2. **RR-S10, P0, Agent, 2 h, depends RR-S08.** Final tests, ledger/progress/state update and **new** `docs/REVIEW_READY.md` with source/artifact identity, reproductions, intended API changes, incomplete work and at most three remaining priorities. Done when a reviewable software candidate exists; call handoff partial while physical/external evidence is absent.

## Exact baseline/final commands

Run from repository root (dependencies already import successfully locally):

```bash
PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py
PYTHONPATH=gym python experiments/test_bag_evidence.py
PYTHONPATH=gym python experiments/validate_item11.py
PYTHONPATH=gym python experiments/test_mast_physical_validation.py
PYTHONPATH=gym python experiments/test_final_report.py
python -m py_compile experiments/mast_physical_validation.py experiments/test_mast_physical_validation.py
git diff --check
```

## F. Overrun, uncertainty and review criteria

Cut new experiment automation, additional controller studies and optional Docker regeneration before cutting numeric validity, complete pairing, reference provenance or honest evidence labeling. Missing hardware is not a software blocker and cannot be compressed into the sprint. Optional Day 7 adds **up to 4 h** solely for reviewer-driven corrections or environment reproduction, only after an explicit scope update; default remains 30 h.

Software can verify presence, consistency and content hashes, not truthfulness of supplied measurements. A registered manifest is not evidence of physical testing. Candidate freeze and checksums do not establish held-out independence. Any physical dataset requires Owner approval and a separate prospective campaign; never reuse synthetic fixtures as physical evidence.

## G. Resume

Read [ledger](SPRINT_TASKS.csv), [progress](SPRINT_PROGRESS.md), then `git status --short --branch` before edits. First implementation action after plan presentation: add the RR-S04 failing incomplete-matrix and numeric-input regressions. Review packet: [REVIEW_READY.md](REVIEW_READY.md).
