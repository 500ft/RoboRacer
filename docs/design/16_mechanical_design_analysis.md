# 16 — Mechanical Design and Analysis (CAD / FEA Centerpiece)

**Status: TEMPLATE / TODO.** This is the MechE centerpiece of the portfolio and **absorbs the old item 10 (LiDAR mast package)**. **Design-only: no fabrication.** The author does the CAD and FEA.

**Dependency order — do NOT do FEA first.** This file is **last**: **13 → 14 → 15 → 16**. The FEA must run on the **real geometry** locked in item 14 (wheelbase 0.3302 m, deck layout) and the **real masses** chosen in item 15 (LiDAR mass + optical-center height, compute, battery). An FEA built before those exist would be analyzing a fictional part. Do not start the mesh until items 13-15 are filled.

**Load-case philosophy — replace the placeholder 4g.** The old item-10 spec used an arbitrary **4g** load. **Do not use 4g.** The governing *maneuvering* case is **derived from this project's own telemetry**:

```
F_lateral, governing = m_LiDAR_tip × a_lat,peak × SF
```

where `a_lat,peak` is the **measured peak lateral acceleration** from the ride-quality race metrics added in commit `9e603d0` — `max_abs_lat_accel_mps2` from `summarize_run` / `race_and_report` in `gym/roboracer/closed_loop.py` — `m_LiDAR_tip` is the LiDAR tip mass from item 15, and `SF` is a stated safety factor. A **separate crash / drop case** is analyzed independently (it is not a steady maneuvering load and should not be blended into the maneuvering case).

> **Peak lateral acceleration — measured from a clean completed lap.** `a_lat,peak = 19.4 m/s²` (≈ 2.0 g), the `max_abs_lat_accel_mps2` reported by `summarize_run` for a **clean completed lap** (`completed_lap == True`, `collision == False`) of the **tuned pure-pursuit baseline** (lookahead 1.2 m, velocity gain 1.2 — the single `selected_baseline == True` row in `runs/pure_pursuit_sweep/results.csv`). Conditions: **RK4 integrator, `dt = 0.002 s`, controller at 100 Hz**, `examples/example_map`; lap time 38.04 s, mean speed 8.33 m/s. Companion figures from the same lap: `mean_abs_lat_accel_mps2 = 5.78`, `max_abs_long_accel_mps2 = 9.51`, `rms_lat_jerk_mps3 = 22.1`. Reproduce with `experiments/ride_quality_baseline.py`; the run is committed to `runs/ride_quality_baseline/` (`summary.json` + per-step `telemetry.csv`). The discarded `runs/first_lap/telemetry.csv` figures (max |a_y| ≈ 78 m/s², max |a_x| ≈ 801 m/s²) are **raw scripted-lap / collision spikes** and were deliberately **not** used.

---

## 1. Inputs from Items 13-15 (fill before analysis)

| Input | Value | Source |
| --- | ---: | --- |
| Wheelbase (geometry) | 0.3302 m | item 14 / `closed_loop.py` |
| LiDAR tip mass `m_LiDAR_tip` | `[confirm]` kg | item 15 |
| LiDAR optical-center height above deck | `[confirm]` m | item 15 (moment arm) |
| Peak lateral accel `a_lat,peak` | **19.4 m/s²** (≈ 2.0 g; `max_abs_lat_accel_mps2`, clean completed lap, pure-pursuit baseline, RK4 `dt = 0.002 s`, 100 Hz) | `summarize_run`, `gym/roboracer/closed_loop.py`; `runs/ride_quality_baseline/summary.json` |
| Peak longitudinal accel | **9.51 m/s²** (`max_abs_long_accel_mps2`, same clean lap) | `summarize_run`; `runs/ride_quality_baseline/summary.json` |
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
| Governing lateral force | F | `[confirm]` N | = m_LiDAR_tip × a_lat,peak × SF, with **a_lat,peak = 19.4 m/s² known** (clean lap); m_LiDAR_tip (item 15) and SF still to set |
| Moment arm | h_arm | `[confirm]` m | optical-center height |
| Root bending moment | M | `[confirm]` N·m | F × h_arm |
| Section modulus / I, c | — | `[confirm]` | from CAD section |
| Hand-calc max stress | σ_hand | `[confirm]` MPa | M·c/I |
| Hand-calc tip deflection | δ_hand | `[confirm]` mm | F·L³/(3EI) |
| Margin vs yield | — | `[confirm]` | σ_yield / σ_hand |

### 3.1 Hand calculation (analytical baseline)

> **First-pass closed-form baseline computed now**, ahead of the item-15 LiDAR
> selection, so the FEA has a number to be validated against. The mast is
> modeled as a **thin-walled 6061-T6 aluminum cantilever tube**, fixed at the
> deck (root) with the LiDAR mass lumped at the free tip (moment arm = full
> length). Reproduce with `experiments/mast_hand_calc.py`; raw output is in
> `runs/mast_hand_calc/summary.txt`. **All geometry/mass/material values are
> ASSUMED placeholders** (clearly labelled below) and must be re-run once item
> 15 locks the real LiDAR mass and optical-center height. The measured
> `a_lat,peak = 19.4 m/s²` is the only non-assumed input.

**Assumptions block (all ASSUMED unless noted):**

| Parameter | Value | Basis |
| --- | ---: | --- |
| Mast length `L` (= moment arm `h_arm`) | 0.120 m | ASSUMED — short mast, tip at free end (conservative lever) |
| Tube OD | 16.0 mm | ASSUMED — stock aluminum tube |
| Wall thickness `t` | 1.50 mm | ASSUMED → ID 13.0 mm |
| Section: `I` = π/64·(OD⁴−ID⁴), `c` = OD/2 | I = 1.815×10⁻⁹ m⁴ (1815 mm⁴), c = 8.0 mm | derived |
| Material | 6061-T6 Al: E = 68.9 GPa, σ_yield = 276 MPa, ρ = 2700 kg/m³ | ASSUMED — carbon tube is the lighter/stiffer alternative but anisotropic with no single yield; Al is the conservative baseline |
| Tip mass `m_tip` | 0.20 kg | ASSUMED — RPLIDAR-class 2D scanner + bracket |
| Maneuver accel `a_lat,peak` | 19.4 m/s² (≈ 2.0 g) | **MEASURED** — clean lap, `runs/ride_quality_baseline` |
| Crash shock | 50 g = 490 m/s² | ASSUMED — stated half-sine-equivalent survival shock; bounds a low-speed bench drop and deliberately governs strength over the ~2 g maneuvering case |
| Safety factors | SF_maneuver = 2.0, SF_crash = 1.5 | ASSUMED — 2.0 on yield for the repeated maneuvering load; 1.5 on top of the already-inflated 50 g crash |

**Results — both load cases** (cantilever, tip point load `F = m_tip·a·SF`, fixed root):

| Quantity | Maneuvering (2 g, SF 2.0) | Crash (50 g, SF 1.5) |
| --- | ---: | ---: |
| Tip force `F` | 7.76 N | 147.2 N |
| Root moment `M = F·L` | 0.931 N·m | 17.66 N·m |
| Max bending stress `σ = M·c/I` | 4.10 MPa | 77.83 MPa |
| Tip deflection `δ = F·L³/(3EI)` | 0.036 mm | 0.678 mm |
| Yield margin `σ_yield/σ` | **67.2** (PASS, ≥2.0) | **3.55** (PASS, ≥1.5) |

The **crash case governs strength** (σ ≈ 78 MPa vs 4 MPa); both clear yield with margin. Stress is modest because a 16 mm tube is over-stiff in bending for these loads — strength is not the binding constraint.

**First natural frequency** (load-independent; Rayleigh tip-mass model):

| Quantity | Value |
| --- | ---: |
| `k_eff = 3EI/L³` | 2.171×10⁵ N/m |
| `m_eff = m_tip + 0.23·m_mast` (m_mast = 22.1 g) | 205.1 g |
| `f1 = (1/2π)·√(k_eff/m_eff)` | **163.8 Hz** |

**Acceptance criterion:** `f1` must clear the **100 Hz control update rate** and a plausible low-hundreds-Hz motor/drivetrain excitation band by a factor of 2, i.e. **f1 ≥ 200 Hz**. **Result: 163.8 Hz → FAIL.** It clears 100 Hz (1.6×) but lands inside the 2× guard band, dominated by the heavy 0.20 kg tip mass on a slender tube. **Action: stiffen — shorter `L`, larger OD/wall, or a carbon tube — and re-check before accepting the mast.** This is exactly the kind of binding constraint the modal analysis (Section 6) is meant to catch.

> **This `3.1` hand calc is the analytical ground truth the Section 4 static FEA (and Section 6 modal) must reproduce within ~10–15% (away from stress concentrations) before the detailed-geometry FEA is trusted.**

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

- [ ] Inputs from items 13-15 filled (geometry, LiDAR mass + height; **clean peak lateral accel `a_lat,peak = 19.4 m/s²` DONE** — pure-pursuit baseline, clean lap, `runs/ride_quality_baseline/`)
- [ ] Mass & CG budget
- [ ] FBD + hand calc (maneuvering case derived from telemetry, NOT 4g)
- [ ] FBD + hand calc (separate crash/drop case)
- [ ] Static FEA vs hand calc (within stated band)
- [ ] Mesh convergence <5% on a defined gauge region
- [ ] Modal analysis with first-frequency clearance of motor band AND 100 Hz control rate
- [ ] Tolerance stack → LiDAR angular error
- [ ] Polished design page per part
