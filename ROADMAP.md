# Roadmap — RoboRacer / F1TENTH Modeling

_Last updated: 2026-06-23 · Horizon: 8 weeks (through ~2026-08-23)_

## Role in the portfolio

**Primary flagship — serves both tracks.** This is the single artifact that
proves research-grade work (system identification with held-out validation) AND
deployable robotics engineering (controls + ROS 2). It is the highest-priority
project of the summer.

## Where it is now (strong)

- Kinematic + dynamic bicycle model derived and documented.
- **System ID with held-out validation at 100% VAF** (recovered Gym's nonlinear
  `C_Sf`/`C_Sr`).
- Controllers implemented and benchmarked: pure pursuit, LQR, constrained MPC
  (reports in `reports/`).
- EKF state estimation; failure-mode FMEA; ROS 2 sidecar with a
  rosbag->telemetry bridge validated against known plant coefficients.
- CI green; ~16k lines Python; reproducible-from-scripts discipline.

## The gap to close

The project currently reads as **controls + software, simulation only.** Two
moves convert it into an undeniable mechatronics flagship:

1. A **mechanical engineering artifact** (proves FEA / hand-calc ability — the
   exact thing a controls-heavy repo is missing for a MechE resume).
2. **Physical-hardware validation** of the SysID pipeline (kills the "sim-only"
   objection), if a real car is reachable.

## Milestones

- [ ] **Wks 1-2 — Close the controls story:** finish the pure-pursuit lookahead
      sweep and a single clean PP vs LQR vs MPC comparison table + figure; tick
      the remaining boxes in `Things to Complete/` items 1, 2, 6, 7.
- [ ] **Wks 3-4 — Mechanical package (item 11, highest leverage):** LiDAR-mast
      lateral load (4g case) -> FBD -> hand calc -> static FEA -> mesh
      convergence (<5% stress change) -> modal (first natural frequency) ->
      tolerance stack on LiDAR angular error. One clean mechanical design page.
- [ ] **Wks 5-6 — Physical validation (stretch):** acquire one excitation
      dataset on a real RoboRacer/F1TENTH car (NYU lab or club), run the SysID
      pipeline, report held-out validation on real telemetry.
- [ ] **Wks 7-8 — Final report (item 12):** 10-20 page technical report, every
      figure reproducible from scripts, simulator vs derived-model results kept
      distinct, failures explained (not just successes).

## Portfolio statement

> Identified a nonlinear vehicle-dynamics model from telemetry with held-out
> validation (100% VAF); designed and benchmarked pure-pursuit, LQR, and
> constrained-MPC controllers; built a ROS 2 telemetry bridge; and delivered a
> mechanical FEA package (FBD, hand calc, FEA, mesh convergence, modal) for the
> sensor mast.
