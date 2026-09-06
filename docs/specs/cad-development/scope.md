# RoboRacer — CAD adaptive scope

Date: 2026-09-06. Task definitions: [CAD_PLAN.md](../../CAD_PLAN.md); authoritative CAD state: [CAD_TASKS.csv](../../CAD_TASKS.csv).

## Must-have for the initial CAD deliverable

- RR-CAD-01: Reconcile mast/deck inputs and load-case provenance.
- RR-CAD-02: Approve mechanical interfaces and manufacture/metrology route.
- RR-CAD-03: Model component deck and packaging layout.
- RR-CAD-04: Model mast, root clamp and LiDAR bracket assembly.
- RR-CAD-05: Model two-axis loading and displacement-metrology fixture.
- RR-CAD-06: Prepare geometry-to-FEA and as-built inspection handoff.
- RR-CAD-07: Release fabrication pack and explanatory mechanical visuals.

“Must-have” applies only to this CAD package, not every paper or software milestone. Entry decision: Owner supplies selected chassis/deck/LiDAR interfaces, actual fabrication route and static-fixture instrument availability. As-built FEA and calibrated instruments remain separate prerequisites for physical testing.

## Nice-to-have after the package

- Additional presentation renders or animation, only after source/STEP/drawing reproduction succeeds; they add explanation, not test evidence.

## Maybe-later

- Physical manufacture and commissioning. Trigger: owner-reviewed drawings, actual fabrication quote/access, qualified facility approval and approved measurement protocol. Why wait: unresolved interfaces cannot support safe or interpretable tests.

## Out

- No fabricated mast or new physical/modal-validation claim. Do not replace the registered two-axis matrix, ±15% comparison band or instrument-count gate. Simulator-derived maneuver loads remain model-derived, not measured vehicle telemetry.

## Milestone watch

- Check owner-input records before moving from a parameterized concept to released fits.
- Check the CAD_TASKS.csv predecessor IDs and linked acceptance evidence before starting dependent geometry.
- Check source/export regeneration and inspection drawings before a fabrication-review decision.
- Check qualified apparatus/measurement approval separately before any physical claim or energized run.
