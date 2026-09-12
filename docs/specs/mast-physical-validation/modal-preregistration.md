# Mast tap-test preregistration — DRAFT / BLOCKED

Prepared 2026-09-11, before acquisition. This corrects the previously deferred
protocol artifact; it is **not frozen**, permission to test, or modal evidence.
The authoritative task is RR-S11 in `docs/SPRINT_TASKS.csv`. Static compliance
remains governed solely by [design.md](design.md); its ±15% agreement and U95
≤10% do not become modal thresholds.

## Target and observable

Estimate the first installed bending mode on both transverse axes and compare
with inspection-linked as-built modal predictions using the same root restraint,
sensor/bracket/accelerometer mass and moving cable configuration. The
[rejected 174.7 Hz baseline](../../design/16_mechanical_design_analysis.md) is not
the selected design. [Selected nominal FEA](../../../runs/mast_fea/fea_summary.txt)
is 285.5 Hz (second mode 301.3 Hz); the selected hand estimate is 330.1 Hz.
These are model outputs, not an as-built center for an acceptance interval.
The existing 200 Hz guard is a separate design screen, not demonstrated
separation from measured motor excitation. No ±15% band about either nominal
frequency is preregistered here.

## Prospective experiment, to be finalized before any tap acquisition

1. Finish static fixture/inspection readiness first. Record specimen/drawing,
   clamp engagement/torque, effective length, installed force-free configuration,
   body/bracket/cable and accelerometer masses, instrument serial numbers,
   calibration and mounting. Document the sensor thermal/mounting arrangement;
   the unmodeled heat-sink plate must not be silently added to moving mass.
2. Select and record excitation and response coordinates/directions for x and y.
   Excite away from the fixed-root node, observe near the tip, and verify mode
   observability/cross-axis coupling. Quantify accelerometer and cable loading;
   compare an inspection-linked model of the instrumented assembly, or freeze
   a justified correction and its uncertainty before data exists.
3. Prefer an instrumented impulse and synchronized force/acceleration channels
   so FRF/coherence quality can be assessed. If only response-only decay is
   available, amend this draft prospectively with a suitable estimator and
   replacement quality checks; do not fabricate coherence from response alone.
4. Fix sampling, analog anti-aliasing, record duration, trigger/pretrigger,
   excitation amplitude/linearity screen, repeats per axis, windows, detrending,
   estimator/version, frequency search band, mode-pairing and damping method.
   Retain all raw channels, including double hits, clipping and poor decays;
   apply only prior exclusion rules with reasons. Do not pick a favorable peak.
5. Freeze model/reference sources separately from protocol commit, before
   acquisition. Preserve raw files and instrument timing metadata, SHA-256
   artifacts, actual start time, zero checks and setup photos. Commit and push
   the reviewed protocol and as-built reference before tapping. Independent
   review of acquisition readiness and provenance is still required.

## Numerical freeze checklist — every blank is a blocker

Fill [modal-freeze.json](modal-freeze.json), with reviewed source records:

- As-built predicted frequencies for **x and y**, specimen/drawing and inspected
  dimensions/mass linkage; model-source and reference commits must resolve and
  predate acquisition. Neither 174.7 nor 285.5 is copied in as a measured baseline.
- Sample rate (Hz), record duration (s), true bin spacing Δf = 1/T (Hz), search
  band, analog passband/stopband (Hz), stopband attenuation (dB), channel timing
  accuracy and sensor/DAQ calibrated bandwidth. Nyquist alone is insufficient;
  review attenuation against measured noise and possible out-of-band excitation.
- Integer repeat count per axis, excitation amplitude/linearity and clipping
  limits, minimum coherence, maximum repeatability fraction, allowed sensor
  mass-loading fraction and the correction method. The checker requires at
  least two repeats for repeatability to exist; this is not an approved count.
- A filled numerical uncertainty budget for frequency estimate/resolution,
  timing, repeatability, calibration, mode identification, sensor/cable loading,
  root flexibility and reference-model inputs. State units, distributions,
  standard uncertainties, sensitivities, covariance, coverage factor and U95.
  For an initial approximation, f ∝ √(k/m), so independent relative standard
  uncertainty is 0.5√[(u_k/k)²+(u_m/m)²]; this is not the full installed budget.
- Separately set the maximum relative measurement U95 and model-discrepancy
  tolerance, both numerically justified by the above budget and intended claim.
  Freeze the interval/guard-band decision rule and inclusivity at boundaries,
  treatment of the 200 Hz screen, quality failures, and at most one documented
  root-cause/retest cycle. Quality failure is INCONCLUSIVE, not model agreement.
  Adequate quality plus disagreement must remain reportable as DISCREPANCY.

No numerical acceptance values are supplied because calibration, as-built
baseline and modal uncertainty are unresolved. The selected nominal frequency
alone cannot justify a physical pass interval.

## Executable boundary and reproduction

```sh
python cad/modal_freeze.py --check-draft
python cad/modal_freeze.py
```

First command prints `DRAFT_BLOCKED` (exit 0 means valid draft structure only).
Default command exits 2 with `BLOCKED` on the committed unresolved fields.
Even a fully populated synthetic checklist yields only
`READY_FOR_HUMAN_FREEZE_REVIEW_ONLY`. This helper checks completeness and basic
numeric coherence, **not** calibration authenticity, artifact hashes/history,
budget adequacy, scientific validity or a final experiment verdict. Human
review must inspect actual linked records, approve every numerical choice,
verify commit/hash chronology and freeze the analysis code before acquisition.
No modal analyzer or frozen acceptance protocol is claimed implemented.
