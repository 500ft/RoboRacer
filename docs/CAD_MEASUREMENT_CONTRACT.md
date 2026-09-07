# Mast fixture-readiness contract — prospective amendment, 2026-09-06

This is a CAD/fixture design requirement added before physical testing. It is not an experimental result and does not change the numerical verdict in the [frozen protocol](specs/mast-physical-validation/design.md). RR-CAD-05 owns the fixture and filled error budget; RR-CAD-06 owns the geometry-to-reference handoff.

## Reproduced nominal scale

Using the mechanical study's assumed 6061-T6 E = 68,900 N/mm² and selected tube L = 100 mm, OD = 20 mm, ID = 17 mm:

- I = pi(OD^4 - ID^4)/64 = 3,754.154 mm^4.
- k = 3EI/L^3 = 775.984 N/mm; compliance = 1.288687 micrometres/N.
- A 4 N load gives 5.15475 micrometres in this ideal beam.
- Root rotation 50 microradians at a 100 mm lever produces 5 micrometres: almost the whole low-load signal.
- Proposed translational fixture-stiffness screen: >=10k = 7,759.84 N/mm at the load point on EACH axis. Recompute from reviewed specimen/as-built stiffness if it changes; this ratio does not constrain root rotation.

These are hand-model quantities, not new FEA or measured values. The protocol's separate nominal FEA compliance is 0.176/128.76 = 0.001367 mm/N. At 20 N it gives approximately 27.3 micrometres, sufficient for the existing 20-count full-scale screen at 0.001 mm resolution. That screen does NOT mean the 4 N point has 20 counts.

## Required fixture/instrument design acceptance

1. Document load-point fixture translational stiffness >=10 times specimen stiffness for x and y, with the constraints and force-line location used in the calculation. Physical commissioning must check the prediction; a rigid CAD solid is not stiffness evidence.
2. Provide independent tip AND root indicator stations, each 0.001 mm resolution or better, with fixed reference supports and recorded measurement directions.
3. Measure or bound root rotation independently: for example, a second spatially separated root observation with a measured baseline. A single root translation channel cannot observe rotation. Record station spacing, angular sensitivity and propagated uncertainty; do not silently treat subtraction of fixture_mm as a rotation correction.
4. Record a FILLED numerical error budget with actual instrument IDs/calibration, source status, units, distributions/standard uncertainties, sensitivities and covariance assumptions for force, tip, root translation, root rotation, repeatability and reference prediction. Blank or assumed-zero components block fixture acceptance.
5. Propagate through the actual fitted-compliance estimator across all five force levels, cycles and axes. Demonstrate the existing relative expanded U95 <=10% requirement, rather than using full-scale count resolution alone. If root rotation is not adequately bounded or fixture corrections change the observable/model, amend the protocol prospectively BEFORE loading; do not quietly alter evaluator semantics.

## Planning-only quantified example, not a filled measured budget

| Term | Known planning calculation | Still required before acceptance |
| --- | --- | --- |
| Tip quantization | At 1 micrometre step, uniform quantization standard uncertainty = 1/sqrt(12) = 0.289 micrometres | Actual calibration, hysteresis, contact-force and resolution records |
| Root quantization | Same 0.289 micrometres at 1 micrometre step | Actual root station calibration and motion geometry |
| Difference of independent readings | Combined standard uncertainty 0.408 micrometres; illustrative k=2 expansion 0.816 micrometres | Actual dependence/covariance, zero-drift and coverage justification |
| Low-load illustration | 0.816/5.155 = 15.8% of the 4 N ideal signal | Fitted-slope uncertainty, not pointwise relative uncertainty, governs the frozen gate |
| Root rotation | 50 microradians * 100 mm = 5 micrometres | Observed/bounded rotation and uncertainty; cannot be assumed absent |
| Force / repeatability / reference | Unavailable, not zero | Calibrations, repeated measurements, converged inspection-linked reference and propagated uncertainty |

The quantization example assumes independent uniform rounding; it is not a claim about actual calibrated instruments or proof the fitted slope will fail. It explains why the complete budget is required.

## Pre-load reference freeze

After fabrication and as-built inspection, commit and push axis-specific as-built model source and the inspection-linked reference artifact BEFORE ANY campaign load is applied. Record model source_commit and reference_commit separately; the campaign's test_started_at must follow them. Verify hashes and that the reference actually corresponds to inspected dimensions and boundary conditions. A nominal geometry export or an empty manifest does not satisfy this gate. Preserve the earlier reference if a discrepancy later motivates a new model.

## Reproduce the nominal arithmetic

Run from the repository root:

```sh
python - <<'PY'
import math
E, L, od, inner = 68900.0, 100.0, 20.0, 17.0
I = math.pi * (od**4 - inner**4) / 64
k = 3 * E * I / L**3
assert abs(k - 775.9836594264038) < 1e-9
assert abs(4000/k - 5.15474772104962) < 1e-9
assert abs(L * 50e-6 * 1000 - 5) < 1e-12
print({"k_n_per_mm": k, "minimum_fixture_n_per_mm": 10*k,
       "tip_at_4n_um": 4000/k, "root_50urad_um": L*50e-6*1000})
PY
```
