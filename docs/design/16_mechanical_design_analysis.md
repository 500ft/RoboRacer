# 16 — Mechanical Design and Analysis (CAD / FEA Centerpiece)

**Status: TEMPLATE / TODO.** This is the MechE centerpiece of the portfolio and **absorbs the old item 10 (LiDAR mast package)**. **Design-only: no fabrication.** The author does the CAD and FEA.

**Dependency order — do NOT do FEA first.** This file is **last**: **13 → 14 → 15 → 16**. The FEA must run on the **real geometry** locked in item 14 (wheelbase 0.3302 m, deck layout) and the **real masses** chosen in item 15 (LiDAR mass + optical-center height, compute, battery). An FEA built before those exist would be analyzing a fictional part. Do not start the mesh until items 13-15 are filled.

**Load-case philosophy — replace the placeholder 4g.** The old item-10 spec used an arbitrary **4g** load. **Do not use 4g.** The governing *maneuvering* case is **derived from this project's own telemetry**:

```
F_lateral, governing = m_LiDAR_tip × a_lat,peak × SF
```

where `a_lat,peak` is the **measured peak lateral acceleration** from the ride-quality race metrics added in commit `9e603d0` — `max_abs_lat_accel_mps2` from `summarize_run` / `race_and_report` in `gym/roboracer/closed_loop.py` — `m_LiDAR_tip` is the LiDAR tip mass from item 15, and `SF` is a stated safety factor. A **separate crash / drop case** is analyzed independently (it is not a steady maneuvering load and should not be blended into the maneuvering case).

> **`[confirm]` — peak lateral acceleration is not yet available as a clean number.** The lateral/longitudinal-accel summary columns (`max_abs_lat_accel_mps2`, `max_abs_long_accel_mps2`, lat-jerk) were added to `summarize_run` in commit `9e603d0` but **do not populate the committed controller-comparison run outputs yet** — the commit note states they "populate on the next `run_all.sh` rerun in the gym==0.19.0 env." The only existing closed-loop telemetry with accel columns (`runs/first_lap/telemetry.csv`) contains **raw scripted-lap / collision spikes** (max |a_y| ≈ 78 m/s², max |a_x| ≈ 801 m/s²) that are physically implausible as a clean ride-quality figure and **must not be used as the load case**. Action: rerun `RUN_FULL_MPC=1 ./run_all.sh`, read `max_abs_lat_accel_mps2` from a clean completed lap, and insert it below.

---

## 1. Inputs from Items 13-15 (fill before analysis)

| Input | Value | Source |
| --- | ---: | --- |
| Wheelbase (geometry) | 0.3302 m | item 14 / `closed_loop.py` |
| LiDAR tip mass `m_LiDAR_tip` | `[confirm]` kg | item 15 |
| LiDAR optical-center height above deck | `[confirm]` m | item 15 (moment arm) |
| Peak lateral accel `a_lat,peak` | `[confirm]` m/s² (from `max_abs_lat_accel_mps2`, clean lap, after rerun) | `summarize_run`, `gym/roboracer/closed_loop.py` |
| Peak longitudinal accel | `[confirm]` m/s² (`max_abs_long_accel_mps2`) | `summarize_run` |
| Safety factor `SF` (maneuvering) | `[confirm]` (state and justify, e.g. 2.0) | design choice |
| Crash/drop case | `[confirm]` (e.g. drop height, or impact deceleration) | design choice, separate from maneuvering |
| Mast material | `[confirm]` (E, σ_yield, ρ) | datasheet |

## 2. Mass and CG Budget (template)

> TEMPLATE. Tabulate every mounted mass (chassis plate, sensor deck, LiDAR, IMU, compute, battery, motor, servo, wiring) with position; compute total mass and CG. Total mass traces to R-11; CG height matters for the lateral load and for any rollover discussion.

| Item | Mass (kg) | x (m) | y (m) | z (m) | Source |
| --- | ---: | ---: | ---: | ---: | --- |
| Chassis plate | `[confirm]` | | | | item 14 / CAD |
| Sensor deck | `[confirm]` | | | | CAD |
| LiDAR | `[confirm]` | | | | item 15 |
| Compute | `[confirm]` | | | | item 15 |
| Battery | `[confirm]` | | | | item 15 |
| Motor + ESC | `[confirm]` | | | | item 14 |
| Servo | `[confirm]` | | | | item 14 |
| **Total / CG** | `[confirm]` | | | | derived |

## 3. LiDAR Mast — Free-Body Diagram + Hand Calculation (REQUIRED)

> TEMPLATE / TODO. Required deliverable: a labeled FBD of the mast as a cantilever with the LiDAR mass at the tip, loaded by `F_lateral, governing = m_LiDAR_tip × a_lat,peak × SF` applied at the optical-center height (moment arm). Hand-calc bending stress and tip deflection from beam theory:
- Bending moment at root: `M = F_lateral × h_arm`
- Max bending stress: `σ = M·c / I`
- Tip deflection: `δ = F_lateral·L³ / (3·E·I)`

Record the section (I, c), the numbers, and the margin against σ_yield. **This hand calc is the ground truth the FEA must match.** Also run the **crash/drop case** as a separate FBD/hand calc.

| Quantity | Symbol | Value | Note |
| --- | --- | ---: | --- |
| Governing lateral force | F | `[confirm]` N | = m_LiDAR_tip × a_lat,peak × SF |
| Moment arm | h_arm | `[confirm]` m | optical-center height |
| Root bending moment | M | `[confirm]` N·m | F × h_arm |
| Section modulus / I, c | — | `[confirm]` | from CAD section |
| Hand-calc max stress | σ_hand | `[confirm]` MPa | M·c/I |
| Hand-calc tip deflection | δ_hand | `[confirm]` mm | F·L³/(3EI) |
| Margin vs yield | — | `[confirm]` | σ_yield / σ_hand |

## 4. Static FEA vs Hand Calc (REQUIRED)

> TEMPLATE / TODO. Run static FEA on the real mast geometry with the same governing load and boundary condition (fixed root). **Acceptance: FEA peak stress agrees with the Section 3 hand calc** (state the % difference and an acceptance band, e.g. within ~10-15% away from stress concentrations). Report σ_FEA, δ_FEA, and the comparison. Repeat for the crash/drop case.

| Quantity | Hand calc | FEA | Δ% | Within band? |
| --- | ---: | ---: | ---: | --- |
| Max stress | `[confirm]` | `[confirm]` | `[confirm]` | TODO |
| Tip deflection | `[confirm]` | `[confirm]` | `[confirm]` | TODO |

## 5. Mesh Convergence (REQUIRED, <5%)

> TEMPLATE / TODO. Refine the mesh over ≥3 levels and track peak stress on a **defined gauge region** (away from singular re-entrant corners — pick a fillet flank or a mid-span section so the metric converges instead of chasing a singularity). **Acceptance: <5% change in the gauge-region stress between the two finest meshes.**

| Mesh level | Element size / count | Gauge-region stress | Δ% vs previous |
| --- | --- | ---: | ---: |
| Coarse | `[confirm]` | `[confirm]` | — |
| Medium | `[confirm]` | `[confirm]` | `[confirm]` |
| Fine | `[confirm]` | `[confirm]` | `[confirm]` (**must be <5%**) |

## 6. Modal Analysis (REQUIRED, with acceptance criterion)

> TEMPLATE / TODO. Compute the first several natural frequencies of the mast + LiDAR mass. **Acceptance criterion (state explicitly):** the **first natural frequency must be clear of both** (a) the chassis/motor/drivetrain excitation band **and** (b) the **control update rate of 100 Hz** (all controllers run at 100 Hz, `dt = 0.002 s`). State the separation margin (e.g. f1 ≥ 2× the highest excitation of concern, or a stated guard band around 100 Hz). If f1 lands near 100 Hz or the motor band, redesign (stiffen / add a rib / change section) — do not accept it.

| Mode | Natural frequency | Excitation source to clear | Margin | Pass? |
| --- | ---: | --- | --- | --- |
| 1st | `[confirm]` Hz | control rate 100 Hz; motor/drivetrain band `[confirm]` | `[confirm]` | TODO |
| 2nd | `[confirm]` Hz | — | — | — |

## 7. Tolerance Stack → LiDAR Angular Error (REQUIRED)

> TEMPLATE / TODO. Build the tolerance stack from the mounting interfaces (deck flatness, mast base squareness, fastener clearance, LiDAR mounting datum) to the **angular error of the LiDAR optical axis**. Convert the worst-case (and RSS) tilt into a scan-angle / range error at a representative distance, and state whether it is acceptable for the localization that feeds `/ego_racecar/odom`.

| Contributor | Tolerance | Angular contribution | Note |
| --- | --- | --- | --- |
| Deck flatness | `[confirm]` | `[confirm]` ° | |
| Mast base squareness | `[confirm]` | `[confirm]` ° | |
| Fastener clearance / fit | `[confirm]` | `[confirm]` ° | |
| LiDAR mounting datum | `[confirm]` | `[confirm]` ° | |
| **Worst-case sum / RSS** | — | `[confirm]` ° | → range error `[confirm]` mm at `[confirm]` m |

## 8. Design Page(s)

> TEMPLATE / TODO. One polished design page per major part (chassis plate, sensor deck, LiDAR mast): CAD render, key dimensions, governing load case + result, FEA contour, modal result, and the tolerance budget. Export figures to `docs/design/figures/`.

## 9. Checklist (none complete)

- [ ] Inputs from items 13-15 filled (geometry, LiDAR mass + height, **clean** peak lateral accel after `run_all.sh` rerun)
- [ ] Mass & CG budget
- [ ] FBD + hand calc (maneuvering case derived from telemetry, NOT 4g)
- [ ] FBD + hand calc (separate crash/drop case)
- [ ] Static FEA vs hand calc (within stated band)
- [ ] Mesh convergence <5% on a defined gauge region
- [ ] Modal analysis with first-frequency clearance of motor band AND 100 Hz control rate
- [ ] Tolerance stack → LiDAR angular error
- [ ] Polished design page per part
