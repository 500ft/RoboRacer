# LiDAR Mast Physical Compliance Validation — Frozen Protocol

Protocol frozen: 2026-07-17
Hardware status: not yet fabricated or measured

## Claim and scope

The experiment tests whether the **as-built lateral compliance** of the
100 mm-long, 20 mm-OD, 1.5 mm-wall 6061-T6 LiDAR mast agrees with the as-built
finite-element prediction. Compliance is displacement divided by force, in
mm/N. The test does not validate stress, fatigue life, vehicle vibration, or
on-track perception.

The committed nominal references are 0.166 mm hand calculation and 0.176 mm
FEA at 128.76 N, or 0.001289 and 0.001367 mm/N respectively. CAD and as-built
dimensions must be used to regenerate the comparison before the verdict.

## Fabrication dependency

Node 11B sits between CAD and testing. The fabrication traveler records the
released drawing revision, 6061-T6 stock certificate or seller specification,
cut/print/machine process, clamp and fastener configuration, and lead time.
Inspect and record mast length, OD, wall thickness, clamp engagement, load
height, and the two test axes. Nominal dimensions cannot substitute for the
as-built inspection.

## Instrumentation and measurability

- Displacement: indicator with 0.001 mm resolution or better, rigidly supported
  from a reference independent of the mast fixture.
- Force: calibrated 1–2 kg load cell with calibration masses spanning the test
  range; use approximately 4, 8, 12, 16, and 20 N.
- Fixture motion: a separate indicator/reference reading at the mast root or an
  equivalent blank-fixture control, saved as `fixture_mm` for every row.
- Video/photo: show the clamp, force line, indicator contact, load-cell axis,
  and both tested directions.

At 20 N the nominal FEA predicts about 0.0273 mm. A 0.01 mm indicator provides
only 2.7 counts and is rejected. A 0.001 mm indicator provides about 27 counts
and clears the preregistered 20-count measurability screen.

## Trial matrix and raw data

Test both orthogonal axes. For each axis, record at least three complete
load/unload cycles at all five force levels. Do not discard a cycle after
viewing it; append an exclusion flag and reason if the protocol was visibly
violated. Use the committed CSV schema:

```text
axis,cycle,direction,force_n,tip_mm,fixture_mm
```

Calibrate force and displacement before the test. Repeat the zero check after
each axis and document drift. Record ambient temperature, clamp torque or
tightening method, drawing revision, instrument IDs, calibration date, and
operator.

## Frozen verdict

The analyzer subtracts `fixture_mm`, fits compliance with a free intercept, and
computes R² and paired load/unload hysteresis. Verdicts are:

- **INCONCLUSIVE** if R² < 0.99 on either axis, hysteresis >5% of full-scale
  displacement, fixture motion is absent, or relative expanded uncertainty
  U95 >10%.
- **VALIDATED** if all quality gates pass and each measured as-built compliance
  is within ±15% of the as-built FEA prediction.
- **DISCREPANCY** if all quality gates pass but either axis differs from the
  as-built FEA prediction by more than 15%.

One root-cause investigation and one fully documented retest are allowed. The
thresholds do not move after data is visible.

## Reproduction

```bash
python experiments/mast_physical_validation.py \
  runs/mast_physical_validation/raw.csv \
  --relative-u95 0.08 \
  --output runs/mast_physical_validation/verdict.json

python experiments/test_mast_physical_validation.py
```
