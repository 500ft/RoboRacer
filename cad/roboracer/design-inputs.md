# Mast input reconciliation — RR-CAD-01

Prepared 2026-09-08. **Design inputs, not inspected hardware or a CAD model.**
The [parameter register](parameters.csv) records the selected tube, mass basis,
load provenance, model/chassis mismatch, fixture requirements and missing fits.
Blank numeric values mean pending, not zero. `reported_vendor_nominal` means
the existing study cites a vendor value; the vendor source was not independently
re-audited in this task. No row is a new physical measurement.

## What the next model should preserve

The chosen ideal tube is 100 mm long, 20 mm OD and 1.5 mm wall, not the earlier
120 mm / 16 mm rejected design. These are the constants in
[mast_fea.py](../../experiments/mast_fea.py), not an inspected specimen.
The 0.175 kg tip is 0.130 kg cited sensor body plus 0.030 kg bracket and 0.015 kg
cable allowances. Calling the configuration selected does not make either
allowance measured. Material properties are assumed 6061-T6 values pending
stock provenance and the later uncertainty review.

The [chassis decision](../../docs/design/14_chassis_drivetrain_actuators.md)
retains 0.3302 m for the identified simulator and separately reports 0.324 m
for the selected Slash chassis. Do not enlarge a bracket or change the physical
wheelbase to silently force model agreement. Deck packaging is parked; only
the clamp mating datum is required to advance the mast fixture.

## Three different load cases, not interchangeable

| Input | Provenance | Permitted use |
| --- | --- | --- |
| 19.436448595 m/s² lateral peak | [Committed clean simulated lap](../../runs/ride_quality_baseline/summary.json), 0.002 s RK4 step, no collision | Model maneuvering load; not measured vehicle acceleration |
| 128.75625 N = 0.175 × 50 × 9.81 × 1.5 | Assumed shock case in the FEA source | Nominal strength/compliance reference, not the bench test load |
| 4/8/12/16/20 N, both axes and ≥3 load/unload cycles | [Frozen physical protocol](../../docs/specs/mast-physical-validation/design.md) | Future calibrated static campaign after owner readiness |

The historical FEA reports 0.176 mm at the crash case. The physical protocol
uses its rounded 128.76 N reference divisor. These are nominal planning values;
do not populate an `as_built` campaign reference from this register.

## Derived planning sanity checks

For ID = OD − 2t = 17 mm, I = pi(OD⁴ − ID⁴)/64 = 3754.154 mm⁴.
With assumed E = 68900 N/mm², k = 3EI/L³ = 775.984 N/mm and tube mass is
0.023538 kg. Fixture translation stiffness must be at least 10k, approximately
7759.84 N/mm, on each axis. The 4 N ideal-beam signal is only 0.005155 mm.
Both indicator stations therefore retain the 0.001 mm-or-better requirement;
full-scale counts are not a complete uncertainty budget. A root rotation of
50 microradians at 100 mm causes 0.005 mm displacement and cannot be removed
by a single root translation reading. These calculations reproduce the
[fixture contract](../../docs/CAD_MEASUREMENT_CONTRACT.md), not measured stiffness.

## Owner handoff and limits

RR-CAD-02 needs exact stock and clamp/fastener drawings, engagement, bolt pattern,
optical-center/load-height datums, fabrication route/quote, calibrated force
and tip/root instruments, root-rotation observation baseline, and safe bench
access. The source register is complete with these explicit unknowns; those
unknowns still block model acceptance and fabrication. No geometry tooling,
manufacture, FEA rerun, physical validation or owner approval occurred.

After fabrication/inspection, axis-specific as-built source and reference
must be committed and pushed **before any campaign load**. Keep source_commit
and reference_commit separate. The filled reviewed uncertainty budget and
[campaign readiness](../../docs/specs/mast-physical-validation/campaign-readiness.md)
remain compulsory. The historical sprint accounting is unchanged.
