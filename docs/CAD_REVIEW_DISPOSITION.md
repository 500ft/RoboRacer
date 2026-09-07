# CAD review disposition — 2026-09-06

## Merge policy: pending owner decision

The reviewer supplied two blocking policy questions. The prior cleanup is verified in Git history for P-V, Drone, RoboRacer and Enclosure. This amendment does not silently reverse it. All five CAD PRs are draft; no merge is authorized until Owner records whether main admits planning ledgers or only reviewer-facing engineering contracts.

Current conservative disposition: keep task ledgers on the unmerged planning branch and remove the newly added README promotion. If Owner selects contracts-only, extract parameter/interface/inspection/verification contracts into a clean main-targeted change and keep task statuses outside main. Reconcile the prerequisite integrity PRs too; their sprint ledgers remain byte-preserved here, so merging those unchanged would reintroduce the same policy problem. No private repository was created and a public branch is not private storage.

## Accepted engineering amendments

Mast/root-clamp and metrology fixture first; deck packaging is deferred. New fixture-readiness design conditions are prospective, not claimed as part of the July freeze. Existing verdict thresholds stay unchanged.

Code-CAD/CI is now an explicit selected workflow and separately estimated task, not an already implemented test. Cross-ledger prerequisites are recorded in [CAD_DEPENDENCIES.json](CAD_DEPENDENCIES.json); the embedded validator checks references and prevents a task entering todo/in_progress/done with unverified prerequisites. Checks establish metadata consistency, not authentic external approval.

## Inputs and limits

The pasted review was available and checked against local files/current PR heads. The two artifact attachment links in the user message were not available as local files; their additional unpasted punch-list items have not been claimed reviewed. No CAD models or scientific measurements were made in this amendment.
