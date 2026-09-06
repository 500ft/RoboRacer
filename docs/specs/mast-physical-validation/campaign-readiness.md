# Mast campaign readiness — prepared, not completed

Prospective CAD review amendment (2026-09-06): apply the [fixture-readiness contract](../../CAD_MEASUREMENT_CONTRACT.md), including >=10x translational stiffness, matched-resolution root/tip stations, root-rotation observability and a filled reviewed error budget. These are newly specified design conditions, not a retroactive change to the frozen verdict. As-built prediction/reference commits must be pushed before campaign loading.

CAD dependencies are now explicit in [CAD_PLAN.md](../../CAD_PLAN.md) and [CAD_TASKS.csv](../../CAD_TASKS.csv): deck/mast geometry, clamp and fixture design, inspection/FEA handoff and fabrication drawings. Their completion alone does not close RR-S02: fabrication, as-built inspection, converged reference predictions and instrument calibration still require real records.

Prepared 2026-09-05. No apparatus, measurement, instrument calibration, fabrication booking, reviewer contact, or as-built FEA is asserted by this checklist. Owner must supply actual records; Agent prepares analysis only. Physical readiness is RR-S02 in the [authoritative ledger](../../SPRINT_TASKS.csv).

Before a physical campaign, obtain and review:

- Released drawing revision and specimen identity; material provenance and fabrication traveler.
- Measured length, OD, wall, clamp engagement, load height, axis datums and uncertainty. Do not replace inspection with the nominal tube used in `experiments/mast_fea.py`.
- Versioned as-built x/y compliance predictions with solver inputs, boundary conditions, mesh convergence and inspection linkage. Commit the reviewed reference before the campaign; source commit and hashes identify it, not its scientific validity.
- 0.001 mm or better displacement resolution; calibrated force measurement spanning approximately 4/8/12/16/20 N; independent fixture-motion measurement. Verify ≥20 predicted counts per axis before testing.
- Instrument IDs, calibration dates/records, ambient temperature, clamp tightening method, force and displacement calibrations, before/after zero checks and a written uncertainty budget including force, tip, fixture, repeatability, and reference uncertainty.
- An approved safe static-load fixture and operator; setup photos showing force line, tip/root indicator supports and orthogonal axes. Evaluate root rotation separately if simple fixture translation subtraction is inadequate.
- Both orthogonal axes; ≥3 complete load/unload cycles each; five nominal targets per direction; retain raw measured force and displacement. Exclusions must retain source rows and written reasons, never silently discard a bad cycle.
- Owner approval to use and disclose measurements and an external reviewer if available. Preparing this checklist does not authorize fabrication, purchases, outreach, or public disclosure.

If unavailable, keep the project a model-based design study with a conditional physical protocol. Do not rush fabrication or reduce the trial matrix to fit the six-day software sprint.
