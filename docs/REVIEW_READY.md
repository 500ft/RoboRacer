# RoboRacer sprint review index — software candidate, partial project handoff

Updated 2026-09-06. [Roadmap](SPRINT_ROADMAP.md), [authoritative ledger](SPRINT_TASKS.csv),
[progress and runtime inventory](SPRINT_PROGRESS.md).

## Identity and scope

Canonical worktree `/Users/redhose/Developer/research-sprints/2026-09-05/RoboRacer`;
remote `https://github.com/500ft/RoboRacer.git`; branch
`sprint/evidence-integrity-20260905`; base
`bea803741ab91c8d1e782064666d97f302dbb9d9`; final commit is this packet's
containing commit (reported in the PR; not self-embedded).
[Candidate/source SHA-256 inventory](../evidence/sprint-2026-09-05/candidate.json)
identifies the exact evaluator, regression fixture generator, protocol and
public status corrections. No release, deployment, or container build occurred.
The delivery route is the repository's Python CLI, exercised as a consumer
subprocess—not a published package. Original checkout is untouched.

## Deliverables and evidence

| Deliverable | Acceptance evidence |
|---|---|
| Reproduced original false validation | [Complete baseline input/output](../evidence/sprint-2026-09-05/baseline.md); [25 failing subcases before correction](../evidence/sprint-2026-09-05/red-matrix.log) |
| Complete matrix/numeric validity and per-axis comparison | [Evaluator](../experiments/mast_physical_validation.py), [20 regression tests](../experiments/test_mast_physical_validation.py), [green checks](../evidence/sprint-2026-09-05/green-portable.log) |
| Campaign/reference identity and honest synthetic labels | [Two red provenance regressions](../evidence/sprint-2026-09-05/red-provenance.log), [schema and CLI contract](specs/mast-physical-validation/design.md) |
| Consumer CLI and boundary behavior | [Six complete CLI outputs and input hashes](../evidence/sprint-2026-09-05/evaluation-results.json); [selection, prior judgments and limitations](../evidence/sprint-2026-09-05/evaluation.md) |
| Consistent conditional physical scope | [Mechanical status](design/16_mechanical_design_analysis.md), [Owner readiness checklist](specs/mast-physical-validation/campaign-readiness.md), [test report](specs/mast-physical-validation/test-report.md) |

The original incomplete four-row input now raises a controlled input error,
not `VALIDATED`. A complete dataset without a campaign is `INCONCLUSIVE`, with
no nominal reference passed off as as-built FEA. Checked synthetic agreement
is `SIMULATED_AGREEMENT`; the physical `VALIDATED` branch is tested only using
**mocked Git history and synthetic test input**, not physical measurements.

## Reproduce

The primary agent independently reran the delegated software checks on2026-09-06:
[actual rerun record](../evidence/sprint-2026-09-05/parent-verification.json).
This is additional software verification, not independent human or physical validation.

From the worktree root (observed exits all 0 unless stated):

```bash
python -m py_compile experiments/mast_physical_validation.py experiments/test_mast_physical_validation.py
git diff --check
PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py
PYTHONPATH=gym python experiments/test_bag_evidence.py
PYTHONPATH=gym python experiments/validate_item11.py
PYTHONPATH=gym python experiments/test_mast_physical_validation.py
PYTHONPATH=gym python experiments/test_final_report.py
python evidence/sprint-2026-09-05/evaluate_candidate.py
```

The five portable CI checks pass locally; mast tests 20, report tests 6.
Evaluation runner exits 0 after comparing actual CLI outcomes to all six
predeclared judgments: E1/E2/E5 simulated agreement, E4 inconclusive, E3/E6
input error **exit 2**. Full original stdout/stderr and statuses are retained.
The runner refuses changed candidate hashes. A rerun uses new temporary
paths, not new inputs. No post-evaluation source fixes occurred.

Local runtime is Python 3.11.8 macOS arm64 with versions recorded in progress;
it is not CI's pinned Python 3.10 or Docker environment. No typechecker or
linter is configured; compile/whitespace checks supplement the existing
tests. Full legacy Gym regeneration, Docker image build/run and physical
campaigns were not executed. Do not interpret portable success as those results.

### Intentional API/CLI changes

- CLI now requires `--campaign`; old bare CSV/`--relative-u95` invocation exits
  2 and points to the missing argument. Optional `--relative-u95` must match
  the campaign uncertainty record; it cannot replace that evidence.
- Python `evaluate_rows(rows, relative_u95, campaign=None)` remains callable
  without provenance for inspection, but cannot return validation. Supplied
  campaigns must load through `load_campaign` and are rechecked at evaluation.
- Invalid/non-finite/incomplete inputs raise `ValueError` or a controlled CLI
  error rather than being fitted. Undefined R²/hysteresis is JSON null, never
  a nonstandard Infinity/NaN result. Numerical thresholds are unchanged.
- Optional CSV `load_level_n` records nominal targets separately from measured
  force. Exact target forces retain six-column compatibility. All valid CLI
  analyses exit 0, even inconclusive/discrepant; inspect classification.

## Evaluation meaning and incomplete work

All evaluation inputs are synthetic, developer-selected and related to the
development requirements. Six matches demonstrate these cases, not general
accuracy, independent validation or real mast stiffness. Checksums prove file
identity, not truthful measurement or scientifically adequate uncertainty.

Remaining priorities (no external action represented as completed):

1. **RR-S02 blocked:** Owner supplies approved fixture/instruments, calibration,
   as-built CAD/inspection and FEA plus actual campaign records before physical
   use. Human review must assess boundary conditions, fixture rotation, zero
   checks and uncertainty propagation; file presence alone cannot do that.
2. **RR-S09 blocked:** Owner nominates/authorizes an independent reviewer; no
   outreach sent and no feedback received. Pinned Docker/legacy regeneration
   remains an explicit unexecuted follow-up if deployment there is required.
3. **RR-2 deferred:** independently challenged controls results (changed plant,
   friction, speed/delay/observability) are outside this integrity sprint.

Résumé/project wording supported now: “Hardened a LiDAR-mast compliance
analysis workflow to enforce complete paired experiments and traceable
references, with reproducible adversarial checks separating simulation from
physical validation.” Do not add a measured-compliance or impact-survival claim.

## Ready-to-send review request — not sent

“Review RoboRacer against docs/SPRINT_ROADMAP.md. Repository: /Users/redhose/Developer/research-sprints/2026-09-05/RoboRacer. Base commit: bea803741ab91c8d1e782064666d97f302dbb9d9. Final commit: PR head (see GitHub PR). Review index: docs/REVIEW_READY.md. Incomplete work: Owner-confirmed physical readiness and actual measurements; independent review; pinned Docker/legacy-environment verification. Reproduce the changed behaviors and counterexamples, rerun appropriate checks, and assess the code and evidence independently. Review first; make further changes only if requested.”
