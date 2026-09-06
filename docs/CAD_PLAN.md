# RoboRacer — revised CAD work orders

Amended 2026-09-06 after source review. Planning only: no CAD, fixture, fabrication or calibration result exists from this amendment.

**MERGE BLOCKED — owner decision pending.** The earlier public-planning cleanup has not been explicitly reversed. This draft PR keeps ledgers on its unmerged branch for review; it does not authorize them on main. See [CAD_REVIEW_DISPOSITION.md](CAD_REVIEW_DISPOSITION.md). Removing details from the current tree does not erase previous public commits.

[CAD_TASKS.csv](CAD_TASKS.csv) is the sole CAD status ledger. [SPRINT_TASKS.csv](SPRINT_TASKS.csv) remains byte-preserved for the earlier integrity sprint. [Scope tiers](specs/cad-development/scope.md) and [reproduction checks](CAD_PLAN_CHECKS.md) describe this amendment, not physical validation.

## Verified source context

The mechanical study explicitly says parametric mast/deck CAD and as-built dimensions remain pending. Its ideal tube FEA does not define the real clamp or mount needed by the registered physical comparison.

Inspected source documents:

- [docs/design/16_mechanical_design_analysis.md](design/16_mechanical_design_analysis.md)
- [docs/specs/mast-physical-validation/design.md](specs/mast-physical-validation/design.md)
- [docs/specs/mast-physical-validation/campaign-readiness.md](specs/mast-physical-validation/campaign-readiness.md)


## Revised finish line and priority

Mast/root-clamp and metrology fixture first; deck packaging is deferred. New fixture-readiness design conditions are prospective, not claimed as part of the July freeze. Existing verdict thresholds stay unchanged.

## Tool and verification decision

**Selected design approach:** CadQuery code-CAD for parameterized families and neutral STEP verification; Onshape for hand-modeled fixtures with confirmed owner account/access. No Onshape automation, credentials or paid access is assumed. Agent owns code-CAD generators/tests; Owner or an authorized CAD operator owns interactive Onshape work. Lack of Onshape access blocks only affected fixture modeling and requires a documented alternative, not the entire parameter pipeline.

The dedicated tooling task budgets environment locking and CI setup. Pin actual Python/CadQuery/OCP versions only after a clean isolated install plus STEP export/reimport smoke test. No version, environment or geometry CI is claimed tested today. CadQuery's official [installation](https://cadquery.readthedocs.io/en/stable/installation.html) and [STEP import/export](https://cadquery.readthedocs.io/en/stable/importexport.html) docs establish the chosen workflow, not a completed build.

Required future automated sequence: read reviewed parameters.csv → reject invalid/missing dimensions and units → regenerate native geometry → export STEP → reimport into a fresh process → calculate geometric metrics → assert against predeclared tolerances. Geometry acceptance uses numeric JSON plus source/export identity; retain screenshots only for explanatory views. A golden image or a hash is not a geometry test. Tests include analytic nominal cases, registered bounds and invalid cases; expected values cannot be copied from the candidate's own output. CAD geometry tests do not validate physical stiffness, safety or fatigue.

Proposed commands (files DO NOT exist yet): `python cad/generate.py --parameters <registered-parameters.csv> --output <temporary-output>`; `python -m pytest cad/tests -q`. The tooling task must replace placeholders with actual checked-in defaults and wire CI before a model task can close.

## Rebaselined allocation

**23 estimated hours in the prioritized phase; 5 estimated hours parked.** This supersedes the previous CAD allocation, not the original 30-hour software sprint. Only tasks marked todo are executable now; blocked/parked estimates are not scheduled work. Owner decisions, fabrication lead times and external calibration do not shrink into focused hours.

| Workload day | Hours | Order |
| --- | ---: | --- |
| 1 | 4 | RR-CAD-01 → RR-CAD-02 |
| 2 | 3 | RR-CAD-08 |
| 3 | 5 | RR-CAD-04 |
| 4 | 5 | RR-CAD-05 |
| 5 | 3 | RR-CAD-06 |
| 6 | 3 | RR-CAD-07 |

## Individual work orders

IDs retain continuity with the first PR. New IDs represent split inputs, tooling or release tasks; display order is execution priority rather than numerical ID order. Proposed deliverables below are NEW, not present artifacts. Current status exists only in CAD_TASKS.csv.

### RR-CAD-01 — Reconcile mast/deck inputs and load-case provenance

- Owner: Agent; priority: P1; estimate: 2 h; day: 1.
- Dependencies: none.
- Proposed output: `NEW cad/roboracer/design-inputs.md; cad/roboracer/parameters.csv`.
- Done when: Retain selected 100 mm length, 20 mm OD, 1.5 mm wall baseline as a design choice, not an inspected specimen. Record 0.175 kg tip-package mass basis, chassis/model wheelbase distinction, load provenance and missing bolt/optical-center dimensions.
- Verification/evidence: Trace inputs to mechanical study and reference outputs; identify assumptions separately from vendor dimensions and physical measurements.

### RR-CAD-02 — Approve mechanical interfaces and manufacture/metrology route

- Owner: Owner; priority: P1; estimate: 2 h; day: 1.
- Dependencies: RR-CAD-01.
- Proposed output: `NEW cad/roboracer/owner-inputs.md`.
- Done when: Approve stock, mast/root-clamp/fastener and load-height interfaces, fabrication/inspection route, calibrated force instrument and tip/root indicators, bench access and actual lead-time quote. Confirm only the deck-side clamp mating datum; full chassis/deck packaging is not a prerequisite.
- Verification/evidence: Record actual drawing references, interface measurements and tooling resolution against campaign-readiness.md.

### RR-CAD-08 — Establish code-CAD regeneration and CI geometry tests

- Owner: Agent; priority: P1; estimate: 3 h; day: 2.
- Dependencies: RR-CAD-01.
- Proposed output: `NEW cad/requirements.lock; cad/generate.py; cad/tests/; .github/workflows/cad-geometry.yml`.
- Done when: Use CadQuery for parameter-driven families and neutral STEP checks, Onshape for hand-modeled fixtures after confirming account/access. Pin Python/CadQuery/OCP dependencies after a clean isolated install and export/reimport smoke test. Add geometry CI before accepting a parametric model; screenshots are supplementary, not acceptance.
- Verification/evidence: Proposed commands, NOT YET IMPLEMENTED: python cad/generate.py --parameters <registered-parameters.csv> --output <temporary-output>; python -m pytest cad/tests -q. Assert geometry metrics against a reviewed contract with declared tolerances; prove failure on an altered parameter, invalid dimensions, missing inputs and bad STEP. Retain version lock, numeric JSON and STEP outputs.

### RR-CAD-04 — Model mast, root clamp and LiDAR bracket assembly

- Owner: Agent; priority: P1; estimate: 5 h; day: 3.
- Dependencies: RR-CAD-02;RR-CAD-08.
- Proposed output: `NEW cad/roboracer/mast/ (source, STEP, joint details)`.
- Done when: Model finite clamp engagement, fasteners, actual load/optical-center height and both axis datums. Keep ideal beam reference separately named; document joint compliance assumptions and material/process.
- Verification/evidence: Generate tube/clamp geometry from parameters.csv, export/reimport STEP, and assert wall/section/volume/density-based mass/load height against analytic expectations and declared tolerances. Exercise bounds, invalid walls and unit errors in CI; inspect joint fits separately.

### RR-CAD-05 — Model two-axis loading and displacement-metrology fixture

- Owner: Agent; priority: P1; estimate: 5 h; day: 4.
- Dependencies: RR-CAD-02;RR-CAD-04.
- Proposed output: `NEW cad/roboracer/fixture/ (source, STEP, setup drawings)`.
- Done when: Require load-point translational fixture stiffness >=10x specimen stiffness on each axis (nominal approximately 7,760 N/mm for 776 N/mm tube). Provide independent root and tip stations, both 0.001 mm resolution or better, and a method to measure/bound root rotation. Fill/review force, tip, root, rotation, repeatability and reference error budget BEFORE acceptance. Fitted-compliance U95 must satisfy existing <=10% gate; preserve full matrix and >=20 counts at full scale.
- Verification/evidence: Reproduce docs/CAD_MEASUREMENT_CONTRACT.md arithmetic. Check modeled stiffness/lever arms and budget numerically; actual calibration and blank-fixture evidence remain external. A single root translation reading does not remove rotation.

### RR-CAD-06 — Prepare geometry-to-FEA and as-built inspection handoff

- Owner: Agent; priority: P1; estimate: 3 h; day: 5.
- Dependencies: RR-CAD-04;RR-CAD-05.
- Proposed output: `NEW cad/roboracer/analysis-export/ (STEP, boundary map, inspection sheet)`.
- Done when: Record critical length/OD/wall/clamp/load-height datums, material source, detailed-versus-ideal geometry differences and root constraints. As-built x/y predictions require later inspection and converged solver evidence; nominal CAD cannot fill those records. After fabrication/inspection, commit and push the axis-specific AS-BUILT prediction and inspection-linked reference BEFORE ANY campaign load is applied. reference_commit and model source_commit are separate; test_started_at follows both. Prepared nominal exports do not complete that freeze.
- Verification/evidence: Reopen exports and map each boundary/inspection dimension to the physical reference contract; retain unresolved measurements rather than assumed as-built values. Verify reference/model commits and hashes resolve and precede loading; retain unresolved as-built freeze as an external release gate.

### RR-CAD-07 — Release fabrication pack and explanatory mechanical visuals

- Owner: Agent; priority: P1; estimate: 3 h; day: 6.
- Dependencies: RR-CAD-04;RR-CAD-05;RR-CAD-06.
- Proposed output: `NEW cad/roboracer/release/ (BOM, drawings, exports, visual index)`.
- Done when: Release mast/clamp and metrology fixture only: source/STEP, toleranced drawings, inspection/FEA mapping, filled reviewed uncertainty budget and lead-time dependency. Full deck packaging is not required. Actual calibration and as-built pre-load freeze remain external gates, not completed work.
- Verification/evidence: Second reviewer reproduces export dimensions, mass/CG frame and fixture setup from pack; RR-S02 remains blocked until actual readiness records arrive.

### RR-CAD-03 — Model component deck and packaging layout

- Owner: Agent; priority: P2; estimate: 5 h; day: conditional.
- Dependencies: RR-CAD-07.
- Proposed output: `NEW cad/roboracer/deck/ (source, STEP, drawing)`.
- Done when: Place chassis datums, compute, batteries, LiDAR/mast and service clearances. Preserve documented transponder allocation; capture mass/CG coordinate frame and full steering/suspension envelopes where actual geometry is available.
- Verification/evidence: Check interface fits, sightline and wiring/service access; compare sourced component mass/CG budget and list uncertain rows.

## Stop and release rules

Do not equate prepared drawings with fabricated/inspected apparatus. Unknown fit-critical dimensions block manufacture. Owner/facility review, actual metrology and prospective reference freezes remain separate gates. No spending, manufacture, pressurization, rotor operation, flight, publication or new third-party drawing disclosure is authorized here.

If time overruns, cut decorative views and already-parked variants first. Keep reference controls, fit/clearance tests, source provenance, filled measurement budgets and pre-load model freeze. Update estimates explicitly rather than claiming blocked hours as progress. Every future public visual needs a source/version, problem explained and CAD-only label.
