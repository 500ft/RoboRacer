# CAD review disposition — 2026-09-06

## Merge policy: pending owner decision

The reviewer supplied two blocking policy questions. The prior cleanup is verified in Git history for P-V, Drone, RoboRacer and Enclosure. This amendment does not silently reverse it. All five CAD PRs are draft; no merge is authorized until Owner records whether main admits planning ledgers or only reviewer-facing engineering contracts.

Current conservative disposition: keep task ledgers on the unmerged planning branch and remove the newly added README promotion. If Owner selects contracts-only, extract parameter/interface/inspection/verification contracts into a clean main-targeted change and keep task statuses outside main. Reconcile the prerequisite integrity PRs too; their sprint ledgers remain byte-preserved here, so merging those unchanged would reintroduce the same policy problem. No private repository was created and a public branch is not private storage.

## Accepted engineering amendments

Mast/root-clamp and metrology fixture first; deck packaging is deferred. New fixture-readiness design conditions are prospective, not claimed as part of the July freeze. Existing verdict thresholds stay unchanged.

Code-CAD/CI is now an explicit selected workflow and separately estimated task, not an already implemented test. Cross-ledger prerequisites are recorded in [CAD_DEPENDENCIES.json](CAD_DEPENDENCIES.json); the embedded validator checks references and prevents a task entering todo/in_progress/done with unverified prerequisites. Checks establish metadata consistency, not authentic external approval.

## Inputs and limits

The pasted review was available and checked against local files/current PR heads. The two artifact attachment links in the user message were not available as local files; their additional unpasted punch-list items have not been claimed reviewed. No CAD models or scientific measurements were made in this amendment.


## 2026-09-12 — fixture-contract reconciliation (sprint task 4)

Two implementations of the fixture geometry contract were written independently on 2026-09-11
and touched the same four files: **PR #17** (`fix/evidence-gaps-20260911`, merged to `main`) and
**PR #16** (`audit/fixture-contract-tap-prereg-20260911`, open, conflicting).

| | PR #17 (main) | PR #16 |
|---|---|---|
| model | reviewed-target schema + observation comparator (`--check-draft`, `--geometry`) | clauses derived from `parameters.csv` + release gate (`--check`, `--release`) |
| what it catches | CAD observations outside reviewed tolerances | contract disagreeing with the register; pending inputs presented as filled |
| what it lacks | nothing binds the null targets to the register | no observation comparison; no reviewed tolerances |
| tests | 6 (parametrised → 23) | 8 |

**Decision: one file, one checker, both halves kept.** `cad/roboracer/fixture-contract.json` keeps
#17's schema as the authoritative committed contract (it is merged and referenced by RR-CAD-09,
`COMPLETION_RECONCILIATION.md` and `fixture-preparation.md`). #16's register engine is folded into
the same checker as a `derived_from_register` section: `--refresh` regenerates it, `--check` fails
when it is stale, and `--release` refuses (exit 2) unless the review fields and every target are
filled **and** no derived clause is pending. #17's modes are byte-for-byte unchanged. Tests: all of
#17's kept, #16's ported onto the merged schema (33 pass), including a new control showing that
filling only the review fields still refuses on the five pending register rows.

**Disposition of PR #16: closed as superseded, not merged.** Its contract half is now on `main`
through this reconciliation. Its second half — `experiments/tap_test_prereg.py`,
`docs/specs/mast-modal-tap-test/preregistration.md`, `cad/roboracer/modal-inputs.csv` — is **not
carried**: it deletes #17's `docs/specs/mast-physical-validation/modal-preregistration.md` and
`modal-freeze.json`, and the sprint plan keeps the numerical modal freeze as a separate item
(RR-S11). Whether the tap-test generator should regenerate #17's modal document is a separate
decision, recorded as open under RR-S11; nothing about the modal target (285.5 Hz FEA / 330.1 Hz
hand, not the rejected 174.7 Hz baseline) changes here.

Verification: `python cad/fixture_contract.py --check` current; `--release` REFUSED with 16
named blockers; `--check-draft` DRAFT_BLOCKED; `pytest cad/tests/test_fixture_contract.py` 33
passed. `test_geometry.py` needs the pinned CadQuery environment and is unaffected.
