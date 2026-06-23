# 14 — Chassis, Drivetrain, and Actuator Selection

**Status: TEMPLATE / TODO.** Depends on **13** (requirements/architecture). Feeds **15** (sensor/compute/power) and **16** (mechanical design + FEA, which needs the real geometry and real masses fixed here). **Design-only: no fabrication.** Dependency order: **13 → 14 → 15 → 16**.

**Geometry lock:** the rolling platform must reproduce the identified model geometry, in particular **wheelbase = 0.3302 m** (`WHEELBASE_M = 0.15875 + 0.17145` in `gym/roboracer/closed_loop.py`). Any deviation must be documented with its effect on the identified `C_Sf` / `C_Sr` (Section 5).

---

## 1. Platform Decision

> TEMPLATE. Decide: standard 1/10-scale RC class (F1TENTH/RoboRacer-style build on a commercial chassis) **vs** custom chassis. State rationale against R-04 (wheelbase), R-01 (speed), R-10 (scale), R-11 (mass). Default expectation for this portfolio: 1/10 RC class to stay compatible with the F1TENTH/RoboRacer ecosystem, with a custom sensor deck (item 16) on top.

| Option | Pros | Cons | Wheelbase fit to 0.3302 m | Decision |
| --- | --- | --- | --- | --- |
| 1/10 RC class (commercial) | Ecosystem parts, known geometry, fast | Fixed geometry may not be exactly 0.3302 m | `[confirm]` stock wheelbase vs 0.3302 m | TODO |
| Custom chassis | Exact geometry, exact mounting | More design/build effort, more risk | Set to 0.3302 m by design | TODO |

## 2. Geometry (locked)

| Parameter | Value | Source |
| --- | ---: | --- |
| Wheelbase | **0.3302 m** | `WHEELBASE_M` in `gym/roboracer/closed_loop.py` |
| lf (front axle → CG) | 0.15875 m `[confirm — confirm this is lf, not just the first summand]` | `closed_loop.py` `0.15875 + 0.17145` |
| lr (CG → rear axle) | 0.17145 m `[confirm]` | `closed_loop.py` |
| Track width | `[confirm]` | item 13 / chosen platform |

> TEMPLATE. If the chosen commercial platform's wheelbase differs, document the delta and propagate it: a wheelbase change alters the slip/yaw relationship the identified `C_Sf`/`C_Sr` were fit to, so either (a) re-identify on the new geometry or (b) bound the modeling error.

## 3. Drivetrain — Motor / ESC Sizing (template)

> TEMPLATE. Size against R-01 (top speed) and R-05 (longitudinal accel envelope). Pull the speed target from `reports/lqr_controller.md` (operating speed 8.33095 m/s) and the accel target from `max_abs_long_accel_mps2` (`summarize_run`, after `run_all.sh` rerun — `[confirm]`).

| Quantity | Symbol | Value | Source / method |
| --- | --- | --- | --- |
| Target top speed | v_max | `[confirm]` m/s | R-01 |
| Wheel diameter | d_w | `[confirm]` m | platform |
| Required wheel RPM at v_max | n_w | compute = v_max / (π·d_w) · 60 | derived |
| Gear ratio | G | `[confirm]` | platform |
| Motor Kv / type | — | `[confirm]` | datasheet |
| Peak tractive force for R-05 accel | F = m·a | `[confirm]` N | mass (R-11) × `max_abs_long_accel_mps2` |
| ESC continuous / burst current | — | `[confirm]` A | datasheet vs F |

## 4. Steering Servo Sizing (template)

> TEMPLATE. Size against R-02 (steering angle range) and R-03 (steering rate). The servo must cover the steering command range exercised in sim and slew at least as fast as the controller steering-rate limit.

| Quantity | Value | Source |
| --- | ---: | --- |
| Required steering angle range | ≥ ±0.419 rad at the road wheel `[confirm linkage ratio]` | saturation case 0.419 rad (`reports/failure_mode_fmea.md`); nominal max command ≈ 0.200 rad (`reports/controller_comparison.md`) |
| Required steering rate | ≥ model steering-rate limit | `gym/roboracer` model params (`[confirm]` exact value) |
| Servo torque | `[confirm]` kg·cm | steering load estimate |
| Servo transit time | `[confirm]` s/60° → convert to rad/s and compare to rate limit | datasheet |

## 5. Geometry-Deviation Impact on Identified Parameters

> TEMPLATE. If geometry deviates from 0.3302 m or the chosen tires differ, state the expected effect on `C_Sf`/`C_Sr` and the plan to re-validate (re-run the SysID excitation + held-out validation from `reports/dynamic_parameter_identification.md` on the real platform). Until then, the sim `C_Sf = 4.718`, `C_Sr = 5.4562` are **not** assumed to hold on hardware.

## 6. Open Questions / `[confirm]`

> TEMPLATE. List the platform choice, stock wheelbase, gear ratio, wheel diameter, servo torque/rate, and the exact model steering-rate limit.
