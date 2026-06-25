# 16 — Mechanical Design and Analysis (CAD / FEA Centerpiece)

**Status: IN PROGRESS.** This is the MechE centerpiece of the portfolio and **absorbs the old item 10 (LiDAR mast package)**. **Design-only: no fabrication.** The author does the CAD and FEA. **The LiDAR-mast analysis is substantially complete on ASSUMED placeholder masses/geometry:** hand calc (both load cases, §3.1), a frequency-fix design revision (§3.2, the baseline failed the modal guard band and was redesigned), and a real gmsh + CalculiX FEA validating it within ±15% (§4, §6). The mass/CG budget (§2) and tolerance stack (§7) still wait on the item-15 LiDAR lock; everything mast-related must be re-run once the real LiDAR mass + optical-center height are fixed.

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

### 3.2 Design revision — frequency fix (REQUIRED: the baseline FAILS modal)

The §3.1 baseline **passes strength but fails the modal guard band** (`f1 = 163.8 Hz < 200 Hz`). A design sweep over mast geometry and material was run to find a configuration that clears `f1 ≥ 200 Hz` with comfortable margin while keeping the crash-case yield safety factor acceptable. Reproduce with `python experiments/mast_hand_calc.py`; raw output in `runs/mast_hand_calc/design_sweep.txt`.

**Sweep space:** length `L ∈ {0.12 … 0.08} m`, outer diameter `OD ∈ {16 … 25} mm`, wall `t ∈ {1.0, 1.5, 2.0} mm`, material ∈ {6061-T6 aluminum, CFRP}. For every candidate the sweep recomputes `f1 = (1/2π)·√(3EI/(L³·m_eff))` with `m_eff = m_tip + 0.23·m_mast`, and the **governing crash-case** stress/SF.

> **CFRP alternative (clearly-stated assumed properties):** a roll-wrapped/pultruded carbon-fiber tube, axial modulus depends strongly on layup (≈ 70–130 GPa); the sweep assumes **E = 100 GPa, ρ = 1600 kg/m³**. CFRP is **anisotropic with no single tensile yield**, so a "yield SF" is not strictly defined — it is screened only against a **conservative 600 MPa bending allowable** (well below ultimate ≈ 1.5–2 GPa). **Aluminum remains the recommended baseline** because its yield is well-defined; CFRP is the lighter upgrade path if mast mass ever becomes binding.

**Recommended revised mast:** **6061-T6 aluminum, L = 100 mm, OD = 20 mm, wall t = 1.5 mm (stock).** This uses **both** stiffness levers (modestly shorter `L`, larger `OD`), keeps the stock 1.5 mm wall and the well-defined-yield aluminum, and only trims `L` by 20 mm (preserving the LiDAR optical-center height / sightline over the compute stack) — most of the stiffness budget is spent on diameter.

| Quantity | **Baseline (FAILS)** | **Recommended (PASSES)** |
| --- | ---: | ---: |
| Geometry | L=120 mm, OD=16 mm, t=1.5 mm | **L=100 mm, OD=20 mm, t=1.5 mm** |
| Material | 6061-T6 Al | 6061-T6 Al |
| Section `I` | 1815 mm⁴ | **3754 mm⁴** (×2.07) |
| `k = 3EI/L³` | 2.17×10⁵ N/m | **7.76×10⁵ N/m** (×3.58) |
| **`f1` (Rayleigh)** | **163.8 Hz → FAIL** (< 200) | **309.3 Hz → PASS** (1.55× the 200 Hz guard; 3.1× the 100 Hz control rate) |
| Crash-case `σ` | 77.8 MPa | **39.2 MPa** |
| **Crash-case SF** vs yield | 3.55 (PASS) | **7.04 (PASS)** |
| Crash tip deflection | 0.678 mm | 0.190 mm |
| Mast self-mass | 22.1 g | 23.5 g (**+1.4 g**) |

**Why it works (stiffness rises far faster than mass).** Because the 0.20 kg tip mass dominates `m_eff` (mast self-mass ≈ 0.02 kg), `m_eff` is nearly constant and `f1 ≈ √(3EI/L³)`. The two levers attack `k = 3EI/L³` directly:
- **Shorter `L`:** `k ∝ L⁻³`, so 120→100 mm raises `k` by `(120/100)³ = 1.73×` (`f1 ∝ L⁻¹·⁵`) at essentially **zero mass cost**.
- **Larger `OD`:** for a thin wall `I ∝ OD³·t`, so 16→20 mm raises `I` by `2.07×`, while the extra material it adds to `m_eff` is second-order (tip mass dominates).

Together they lift `k` by `3.58×` and `f1` from 163.8 → 309.3 Hz. The same geometry change **also lowers** the crash stress (more `I` ⇒ less `M·c/I`), so the fix is **monotonic in both checks** — strength margin actually improves (SF 3.55 → 7.04). The same 100 mm/20 mm tube in CFRP would reach ≈ 375 Hz at ≈ 14 g, but aluminum is kept for its defined yield.

**Hand sanity-check of the recommended `f1`:** `I = π/64·(20⁴−17⁴) = 3754 mm⁴`; `k = 3·68.9e9·3.754e-9/0.1³ = 7.76×10⁵ N/m`; `m_eff = 0.200 + 0.23·0.0235 = 0.2054 kg`; `f1 = (1/2π)·√(7.76e5/0.2054) = 309.3 Hz`. ✔ matches the sweep.

> **FEA status — RAN and VALIDATED (not install-pending).** The gmsh + CalculiX toolchain was stood up (gmsh 4.15.2 mesher in the conda `base` env; CalculiX 2.23 `ccx` solver in a conda `fea` env) and a 3-D FEA of the **recommended** geometry was run via `experiments/mast_fea.py`. **FEA agrees with the hand calc within ±15 %** on all three headline metrics, and the higher-fidelity **FE first frequency (267.4 Hz) still clears the ≥ 200 Hz guard** (1.34×). Stand-up commands and the full workflow are in **`docs/design/FEA_SETUP.md`**; results in `runs/mast_fea/fea_summary.txt`. See §4 and §6.

## 4. Static FEA vs Hand Calc (REQUIRED)

> **DONE for the recommended geometry (§3.2).** Static FEA was run on the recommended mast (L=100 mm, OD=20 mm, t=1.5 mm, 6061-T6) with the **crash** load (147.2 N) and a fixed (ENCASTRE) root, via `experiments/mast_fea.py` (gmsh C3D10 mesh → CalculiX `ccx`). The crash load is **distributed over the tip-ring nodes** (a single-node point load creates a non-physical ~1.2 GPa nodal singularity); stress is compared on a **mid-span gauge ring** (away from the fixed root and the load) where elementary `M·c/I` applies, plus the global tip deflection. Mesh: 58 232 nodes / 28 985 quadratic tets, element size ≈ 1.2 mm. Raw results in `runs/mast_fea/fea_summary.txt`; toolchain in `docs/design/FEA_SETUP.md`.

| Quantity | Hand calc | FEA | Δ% | Within ±15%? |
| --- | ---: | ---: | ---: | --- |
| Tip deflection (crash) | 0.190 mm | 0.201 mm | +5.9% | **YES** |
| Mid-span gauge stress (crash) | 19.6 MPa | 19.8 MPa | +1.3% | **YES** |

> The fixed-root **peak** von Mises (47.8 MPa) is a re-entrant-corner stress concentration / mesh singularity, **not** a valid `M·c/I` comparison — which is exactly why the §5 mesh-convergence metric and the comparison above use a defined gauge region and the global deflection, not the peak nodal stress. Tip deflection (+5.9%) and gauge stress (+1.3%) both fall well inside the ±15% band, so the static hand calc is validated.

## 5. Mesh Convergence (REQUIRED, <5%)

> TEMPLATE / TODO. Refine the mesh over ≥3 levels and track peak stress on a **defined gauge region** (away from singular re-entrant corners — pick a fillet flank or a mid-span section so the metric converges instead of chasing a singularity). **Acceptance: <5% change in the gauge-region stress between the two finest meshes.**

| Mesh level | Element size / count | Gauge-region stress | Δ% vs previous |
| --- | --- | ---: | ---: |
| Coarse | `[confirm]` | `[confirm]` | — |
| Medium | `[confirm]` | `[confirm]` | `[confirm]` |
| Fine | `[confirm]` | `[confirm]` | `[confirm]` (**must be <5%**) |

## 6. Modal Analysis (REQUIRED, with acceptance criterion)

> **DONE for the recommended geometry (§3.2).** Acceptance criterion: `f1` must clear the **100 Hz control update rate** AND a plausible low-hundreds-Hz motor/drivetrain excitation band by **≥ 2× ⇒ f1 ≥ 200 Hz**. A CalculiX `*FREQUENCY` modal solve was run on the recommended mast with the 0.20 kg LiDAR as a lumped `*MASS` element at the tip and a fixed root (`experiments/mast_fea.py`). **The baseline (163.8 Hz) FAILED this guard; the recommended geometry PASSES by both the hand calc (309.3 Hz) and the FEA (267.4 Hz).**

| Mode | Natural frequency (FEA) | Excitation source to clear | Margin | Pass? |
| --- | ---: | --- | --- | --- |
| 1st (bending) | **267.4 Hz** (hand calc 309.3 Hz, Δ −13.6%) | 100 Hz control rate; low-hundreds-Hz motor band | **1.34× the 200 Hz guard; 2.67× the 100 Hz rate** | **YES** |
| 2nd (bending, orthogonal) | 282.3 Hz | — | — | — |
| 3rd | 944.5 Hz | — | — | — |

> Modes 1–2 are the two ~degenerate orthogonal bending modes of the axisymmetric tube (the small 267→282 Hz split is mesh asymmetry). The FE `f1` lands ~14% below the Rayleigh hand calc because the closed-form model assumes a perfectly rigid root and pure Euler–Bernoulli bending (neglecting shear and root flexibility) and so slightly over-predicts stiffness — the expected direction and magnitude. **Even at the higher-fidelity 267.4 Hz the design clears the ≥ 200 Hz guard (1.34×)**, so the frequency fix is robust. Baseline-vs-recommended comparison and reasoning: §3.2.

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

## 9. Checklist

- [ ] Inputs from items 13-15 filled (geometry, LiDAR mass + height; **clean peak lateral accel `a_lat,peak = 19.4 m/s²` DONE** — pure-pursuit baseline, clean lap, `runs/ride_quality_baseline/`). LiDAR mass/height still ASSUMED pending item 15 lock.
- [ ] Mass & CG budget (depends on item 15 lock)
- [x] FBD + hand calc, maneuvering case derived from telemetry, NOT 4g (§3.1)
- [x] FBD + hand calc, separate crash/drop case (§3.1; crash governs strength)
- [x] **Design revision — frequency fix** (§3.2): baseline `f1=163.8 Hz` FAILED the ≥200 Hz guard; recommended **L=100 mm / OD=20 mm / t=1.5 mm 6061-T6** → `f1=309.3 Hz`, crash SF 7.04 (both PASS)
- [x] Static FEA vs hand calc within ±15% (§4): tip deflection +5.9%, gauge stress +1.3% (gmsh + CalculiX, recommended geometry)
- [ ] Mesh convergence <5% on a defined gauge region (gauge ring defined and used in §4; a formal ≥3-level refinement study still to run)
- [x] Modal analysis with first-frequency clearance of motor band AND 100 Hz control rate (§6): FE `f1=267.4 Hz` ≥ 200 Hz guard (1.34×)
- [ ] Tolerance stack → LiDAR angular error (depends on item 15 lock)
- [ ] Polished design page per part
- [x] **FEA toolchain stood up and tested** (gmsh 4.15.2 + CalculiX 2.23 `ccx`); commands in `docs/design/FEA_SETUP.md`, pipeline `experiments/mast_fea.py`
