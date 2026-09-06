# RoboRacer — individual CAD tasks

Prepared 2026-09-06. **Planning only: no CAD model, drawing, fabrication, calibration or physical result was produced by this amendment.**

[CAD_TASKS.csv](CAD_TASKS.csv) is the sole status ledger for this new CAD phase. The earlier [SPRINT_TASKS.csv](SPRINT_TASKS.csv) remains the authority for the separate 30-hour evidence-integrity sprint; its estimates and achieved software evidence are unchanged. This plan expands mechanical work orders, not publication or test permission. Scope tiers are in [scope.md](specs/cad-development/scope.md).

## Verified reason for the work

The mechanical study explicitly says parametric mast/deck CAD and as-built dimensions remain pending. Its ideal tube FEA does not define the real clamp or mount needed by the registered physical comparison.

Inspected source documents:

- [docs/design/16_mechanical_design_analysis.md](design/16_mechanical_design_analysis.md)
- [docs/specs/mast-physical-validation/design.md](specs/mast-physical-validation/design.md)
- [docs/specs/mast-physical-validation/campaign-readiness.md](specs/mast-physical-validation/campaign-readiness.md)

## Outcome and boundaries

A reviewer can reopen editable, version-pinned geometry; regenerate neutral STEP exports; understand the assembly, critical fits and measurement datums; and distinguish design assumptions from inspected hardware. STL is only a manufacturing derivative where appropriate, not the sole editable master. For hosted CAD retain a version-specific share reference and authorized portable source/export archive; record tool/version and export settings. Do not require a particular commercial tool before checking access.

**Entry decision:** Owner supplies selected chassis/deck/LiDAR interfaces, actual fabrication route and static-fixture instrument availability. As-built FEA and calibrated instruments remain separate prerequisites for physical testing.

**Excluded:** No fabricated mast or new physical/modal-validation claim. Do not replace the registered two-axis matrix, ±15% comparison band or instrument-count gate. Simulator-derived maneuver loads remain model-derived, not measured vehicle telemetry.

Agent owns document preparation and modeling once inputs exist; Owner owns actual component/access choices and review authority; External fabricators/operators own quotes, manufacture and facility approval. No approval, purchase, fabrication booking, IP disclosure of third-party drawings, or test run is completed by checking in this plan. Unknown critical dimensions block fabrication; conceptual placeholders must be visible and cannot become as-built evidence.

## Focused-hour allocation

The initial CAD phase is **24 estimated focused hours**, additional to the earlier software sprint. All hardware work in this phase remains subject to the entry decision. These are estimates, not recorded work. Each day is a workload bucket after its prerequisites, not a calendar promise; quotes, calibration and facility lead times are not compressed into CAD hours.

| Workload day | Hours | Ordered tasks |
| --- | ---: | --- |
| 1 | 4 | RR-CAD-01 → RR-CAD-02 |
| 2 | 5 | RR-CAD-03 |
| 3 | 5 | RR-CAD-04 |
| 4 | 4 | RR-CAD-05 |
| 5 | 3 | RR-CAD-06 |
| 6 | 3 | RR-CAD-07 |

Critical path follows the explicit task dependencies below: input register → owner decisions → parts/fixtures → release review. Independent branches may proceed after their shared inputs close.

## Individual work orders

All output paths below are **proposed NEW deliverables**, not existing artifacts. Current task state appears only in the CSV; the headings below define acceptance, not completion.

### RR-CAD-01 — Reconcile mast/deck inputs and load-case provenance

- Owner: Agent; priority: P1; estimate: 2 h; workload day: 1.
- Dependencies: none; source inspection is available now.
- Scope: initial CAD phase, subject to its input/owner gate.
- Proposed deliverables: `cad/roboracer/design-inputs.md; cad/roboracer/parameters.csv`.
- Done when: Retain selected 100 mm length, 20 mm OD, 1.5 mm wall baseline as a design choice, not an inspected specimen. Record 0.175 kg tip-package mass basis, chassis/model wheelbase distinction, load provenance and missing bolt/optical-center dimensions.
- Verification and evidence to retain: Trace inputs to mechanical study and reference outputs; identify assumptions separately from vendor dimensions and physical measurements.

### RR-CAD-02 — Approve mechanical interfaces and manufacture/metrology route

- Owner: Owner; priority: P1; estimate: 2 h; workload day: 1.
- Dependencies: RR-CAD-01.
- Scope: initial CAD phase, subject to its input/owner gate.
- Proposed deliverables: `cad/roboracer/owner-inputs.md`.
- Done when: Supply fit-critical chassis/deck, LiDAR/bracket and clamp details; select stock/process and fabricator, cost/lead-time quote, displacement/force instruments and safe static fixture access. Preparation is not a fabrication booking.
- Verification and evidence to retain: Record actual drawing references, interface measurements and tooling resolution against campaign-readiness.md.

### RR-CAD-03 — Model component deck and packaging layout

- Owner: Agent; priority: P1; estimate: 5 h; workload day: 2.
- Dependencies: RR-CAD-02.
- Scope: initial CAD phase, subject to its input/owner gate.
- Proposed deliverables: `cad/roboracer/deck/ (source, STEP, drawing)`.
- Done when: Place chassis datums, compute, batteries, LiDAR/mast and service clearances. Preserve documented transponder allocation; capture mass/CG coordinate frame and full steering/suspension envelopes where actual geometry is available.
- Verification and evidence to retain: Check interface fits, sightline and wiring/service access; compare sourced component mass/CG budget and list uncertain rows.

### RR-CAD-04 — Model mast, root clamp and LiDAR bracket assembly

- Owner: Agent; priority: P1; estimate: 5 h; workload day: 3.
- Dependencies: RR-CAD-02, RR-CAD-03.
- Scope: initial CAD phase, subject to its input/owner gate.
- Proposed deliverables: `cad/roboracer/mast/ (source, STEP, joint details)`.
- Done when: Model finite clamp engagement, fasteners, actual load/optical-center height and both axis datums. Keep ideal beam reference separately named; document joint compliance assumptions and material/process.
- Verification and evidence to retain: Inspect worst-case tolerance stack and assembly interference; compare actual section/lever arm to ideal tube model before reusing any FEA result.

### RR-CAD-05 — Model two-axis loading and displacement-metrology fixture

- Owner: Agent; priority: P1; estimate: 4 h; workload day: 4.
- Dependencies: RR-CAD-02, RR-CAD-04.
- Scope: initial CAD phase, subject to its input/owner gate.
- Proposed deliverables: `cad/roboracer/fixture/ (source, STEP, setup drawings)`.
- Done when: Define force line, independent tip/root indicator mounts, orthogonal loading and clamp-rotation observation. Support the existing five-target three-cycle per-axis protocol and at least 20 predicted displacement counts without adding fixture compliance to specimen stiffness.
- Verification and evidence to retain: Review ~4/8/12/16/20 N access and indicator travel/resolution; retain fixture motion/rotation error budget and safety review requirements.

### RR-CAD-06 — Prepare geometry-to-FEA and as-built inspection handoff

- Owner: Agent; priority: P1; estimate: 3 h; workload day: 5.
- Dependencies: RR-CAD-04, RR-CAD-05.
- Scope: initial CAD phase, subject to its input/owner gate.
- Proposed deliverables: `cad/roboracer/analysis-export/ (STEP, boundary map, inspection sheet)`.
- Done when: Record critical length/OD/wall/clamp/load-height datums, material source, detailed-versus-ideal geometry differences and root constraints. As-built x/y predictions require later inspection and converged solver evidence; nominal CAD cannot fill those records.
- Verification and evidence to retain: Reopen exports and map each boundary/inspection dimension to the physical reference contract; retain unresolved measurements rather than assumed as-built values.

### RR-CAD-07 — Release fabrication pack and explanatory mechanical visuals

- Owner: Agent; priority: P1; estimate: 3 h; workload day: 6.
- Dependencies: RR-CAD-03, RR-CAD-04, RR-CAD-05, RR-CAD-06.
- Scope: initial CAD phase, subject to its input/owner gate.
- Proposed deliverables: `cad/roboracer/release/ (BOM, drawings, exports, visual index)`.
- Done when: Deliver editable source/version, STEP, toleranced fabrication drawings, assembly/exploded and fixture views, inspection checklist and fabrication lead-time dependency. Label design revisions as modeled, never validated.
- Verification and evidence to retain: Second reviewer reproduces export dimensions, mass/CG frame and fixture setup from pack; RR-S02 remains blocked until actual readiness records arrive.

## Release review and overrun rule

Every release includes an assembly/exploded view, a critical section/detail view and a measurement/inspection setup view. Captions identify the question illustrated, source revision, dimensions/units and **CAD prediction—not measured** state; cite vendor/hand-calculation references actually used. Render quality is not evidence of fit or performance.

Before marking a CAD task done, attach real source/export identities, regeneration instructions and the corresponding acceptance evidence in CAD_TASKS.csv. A second AI pass is a development check, not independent human or laboratory validation. Retain failed fits and unresolved assumptions; do not silently tune experimental geometry after observing confirmation data.

If the phase overruns, postpone decorative renders, optional variants and mechanism extensions first. Do not remove required fits, safety interfaces, reference controls, source traceability or measurement access. Fabrication-release review, apparatus commissioning and physical evaluation remain separate future actions; updated geometry may require a new prospective analysis/reference freeze. Preparing drawings does not close an existing physical-readiness or publication blocker.

## PR review scope

This amendment changes task planning and navigation only. It is stacked on the open evidence-integrity PR so its diff excludes earlier fixes. No software behavior or frozen scientific threshold is changed. Review task dependencies and claim boundaries now; actual CAD acceptance is assessed when those artifacts exist.
