# LiDAR Mast Physical Compliance Validation — Frozen Protocol

Protocol frozen: 2026-07-17
Hardware status: not yet fabricated or measured

## Prospective software-enforcement amendment — 2026-09-05

The July numerical gates below are unchanged. The original software did not
enforce its written trial matrix or as-built provenance. This amendment is
written before the correction and before any physical campaign; it is not a
retroactive claim that the July implementation was adequate.

Require axes `x` and `y`, positive integer cycle identifiers, at least three
complete cycles per axis, and exactly one load/unload row at each nominal
4/8/12/16/20 N target in every included cycle. Do not average away duplicate
rows or silently omit incomplete cycles. Optional `load_level_n` labels the
nominal target while `force_n` remains the measured force used for the fit;
without that column, only exact target forces identify a level. No force
rounding may create apparently complete data. Non-finite values, negative
force, invalid categories and missing fields are input errors, not results.
An explicit target label requires measured force strictly within that target's
nonoverlapping ±2 N bin. This is target identification, not an acceptable force
calibration error; actual force/calibration uncertainty still governs U95.
Opposite directions are paired by cycle and nominal target. Because actual
paired forces can differ, report hysteresis after adjusting their difference
using the fitted compliance; preserve measured forces for inspection. Each
direction must preserve increasing force across nominal targets.

The CLI will require a version-1 campaign JSON alongside raw CSV. It binds
the raw CSV hash, specimen/drawing identity, evidence kind (`physical` or
`synthetic`), axis-specific reference JSON, calibration, inspection,
uncertainty, zero-check and setup artifacts by SHA-256. Physical comparison
requires an `as_built` reference frozen in a resolvable Git commit before
the campaign. Reference and inspection must identify the same specimen and
drawing. Instrument IDs, calibration/test dates, resolution, temperature,
clamp method, operator and a reviewed uncertainty record are required.
Software checks record presence, consistency and identity, not authenticity
or scientific adequacy. A human must still review model/boundary conditions,
uncertainty propagation and calibration scope.

No campaign supplied to the Python API means `INCONCLUSIVE`; the CLI reports
a missing required argument. Synthetic evidence receives `SIMULATED_AGREEMENT`
or `SIMULATED_DISCREPANCY` and never physical `VALIDATED`. Missing physical
provenance and insufficient predicted indicator counts prevent validation.
The nominal constants remain useful for planning/synthetic controls only.

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
axis,cycle,direction,force_n,tip_mm,fixture_mm,load_level_n
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
  --campaign runs/mast_physical_validation/campaign.json \
  --output runs/mast_physical_validation/verdict.json

python experiments/test_mast_physical_validation.py
```

The physical input files above are **not yet present**. `--relative-u95`
remains an optional compatibility assertion matching the uncertainty record,
not an override. Missing/invalid inputs exit 2 with a CLI error. Every valid
analysis exits 0; automation must inspect JSON `classification`, never treat
exit 0 as a pass. Undefined fit/hysteresis values are JSON null.

### Campaign v1 file contract

The executable `write_synthetic_campaign` builder in
`experiments/test_mast_physical_validation.py` demonstrates a complete schema
using **synthetic-only** artifacts. It supplies no measured data. Owner must
complete the [readiness checklist](campaign-readiness.md) for physical use.

Campaign JSON: `schema_version: 1`, `evidence_kind` (`physical` or `synthetic`),
`specimen_id`, `drawing_revision`, `operator`, `clamp_method`, finite
`ambient_temperature_c`, ISO `test_date`; artifact objects `{path, sha256}`
for `raw_csv`, `reference`, `inspection`, `calibration`, `uncertainty`,
`zero_checks`, `setup`. Paths stay within the campaign directory; files must
be nonempty and their hashes match. CSV header duplicates and extra cells
without headers are rejected. No exclusions or duplicate averaging occurs.

- Reference JSON: matching specimen/drawing/evidence identity,
  `reference_kind` (`as_built` for physical, `synthetic` otherwise), resolvable
  full Git `source_commit` for model source, `model_revision`, `solver_version`,
  `boundary_conditions`, matching `inspection_sha256`, and positive finite
  `compliance_mm_per_n` for exactly `x` and `y`.
- Physical campaigns additionally require top-level `reference_commit` for
  the committed reference artifact and timezone-qualified `test_started_at`.
  The reference commit timestamp must precede test start. Reference and
  model-source commits are separate: a file cannot embed its own commit hash.
  Hashes/Git timestamps establish identity/order, not authenticated hardware
  measurements or externally witnessed preregistration.
- Inspection JSON: matching specimen/drawing/evidence identity, positive
  `length_mm`, `od_mm`, `wall_mm`, `clamp_engagement_mm`, `load_height_mm`, and
  consistent wall/OD. A human must verify these dimensions generated the FEA.
- Calibration JSON: matching `evidence_kind`, `force_instrument_id`,
  `tip_instrument_id`, `fixture_instrument_id`, ISO `calibration_date` no later
  than the test, and positive `resolution_mm` (the coarser of tip and fixture
  displacement resolution). Require ≤0.001 mm and ≥20 predicted counts on
  **each** axis, not only the nominal planning geometry.
- Uncertainty JSON: matching specimen/evidence identity, positive finite
  `relative_u95`, `method`, `reviewed_by`, and `components` descriptions for
  `force`, `tip`, `fixture`, `repeatability`, `reference`. Automated checks
  establish presence/linkage; human review must establish propagation and
  coverage. Zero-check/setup artifacts retain actual records/photos for that
  review; the software does not interpret their scientific adequacy.

Optional `load_level_n` labels nominal target, preserving measured `force_n`.
Legacy six-column CSV requires exact target forces. The public Python API
reloads provenance at evaluation and binds rows to the checked CSV. A missing
campaign is `INCONCLUSIVE`; changed/mismatched provenance is an error. Tests
with mocked Git history exercise physical-classification logic only, not
physical mast performance.
