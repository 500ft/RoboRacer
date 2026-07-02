# 16 — Mechanical Design and Analysis (CAD / FEA Centerpiece)

**Status: IN PROGRESS.** This is the MechE centerpiece of the portfolio and **absorbs the old item 10 (LiDAR mast package)**. **Design-only: no fabrication.** The author does the CAD and FEA. **The LiDAR-mast analysis is complete on the FIRMED item-15 tip mass:** the LiDAR is now locked (**Hokuyo UST-10LX, 130 g datasheet → mast tip mass 0.175 kg**, item 15 §1.1–§1.2), and the hand calc (§3.1), frequency-fix design revision (§3.2), and gmsh + CalculiX FEA (§4, §6) have all been **re-run on the firmed 0.175 kg mass** (validated within ±15%). The lighter real LiDAR (0.175 vs the old 0.20 kg placeholder) **raised** the frequency margin and improved the strength SF. The mass/CG budget (§2) and tolerance stack (§7) still wait on the remaining item-15 picks (compute, battery, IMU).

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
| LiDAR tip mass `m_LiDAR_tip` | **0.175 kg** (Hokuyo UST-10LX 0.130 kg datasheet + 0.030 kg bracket + 0.015 kg cable) | **item 15 §1.2 (LOCKED)** |
| LiDAR optical-center height above deck | **0.100 m** (= recommended mast length `L`, §3.2) | item 15 §1.2 (moment arm) |
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

> Values below are for the **recommended (frequency-fix) geometry** (§3.2; L=100 mm, OD=20 mm, t=1.5 mm 6061-T6) with the **firmed 0.175 kg** tip mass. The **crash case governs strength** (50 g) and is tabulated here; the maneuvering case (2 g) is far milder (σ ≈ 3.0 MPa). Full both-case numbers are in §3.1.

| Quantity | Symbol | Value (crash, recommended geom.) | Note |
| --- | --- | ---: | --- |
| Governing crash force | F | **128.8 N** | = m_LiDAR_tip × 50 g × SF_crash (0.175 kg × 490 m/s² × 1.5); **a_lat,peak = 19.4 m/s² known**; m_LiDAR_tip **firmed 0.175 kg** (item 15) |
| Moment arm | h_arm | **0.100 m** | optical-center height = mast length |
| Root bending moment | M | **15.45 N·m** | F × h_arm |
| Section modulus / I, c | — | **I = 3754 mm⁴, c = 10.0 mm** | recommended OD=20 mm tube |
| Hand-calc max stress | σ_hand | **34.3 MPa** | M·c/I (crash, root) |
| Hand-calc tip deflection | δ_hand | **0.166 mm** | F·L³/(3EI) (crash) |
| Margin vs yield | — | **8.05** | σ_yield / σ_hand (crash; PASS ≥ 1.5) |

### 3.1 Hand calculation (analytical baseline)

> Closed-form baseline, re-run on the **firmed item-15 tip mass**. The mast is
> modeled as a **thin-walled 6061-T6 aluminum cantilever tube**, fixed at the
> deck (root) with the LiDAR mass lumped at the free tip (moment arm = full
> length). Reproduce with `experiments/mast_hand_calc.py`; raw output is in
> `runs/mast_hand_calc/summary.txt`. **The tip mass is now FIRMED at 0.175 kg**
> (item 15 §1.2: Hokuyo UST-10LX 0.130 kg datasheet + 0.030 kg bracket + 0.015 kg
> cable); geometry and material remain engineering choices (labelled ASSUMED).
> The measured `a_lat,peak = 19.4 m/s²` is a non-assumed input. **The firmed
> 0.175 kg is lighter than the prior 0.20 kg placeholder, so f1 rose and stress
> fell — verified below.**

**Assumptions block (all ASSUMED unless noted):**

| Parameter | Value | Basis |
| --- | ---: | --- |
| Mast length `L` (= moment arm `h_arm`) | 0.120 m | ASSUMED — short mast, tip at free end (conservative lever) |
| Tube OD | 16.0 mm | ASSUMED — stock aluminum tube |
| Wall thickness `t` | 1.50 mm | ASSUMED → ID 13.0 mm |
| Section: `I` = π/64·(OD⁴−ID⁴), `c` = OD/2 | I = 1.815×10⁻⁹ m⁴ (1815 mm⁴), c = 8.0 mm | derived |
| Material | 6061-T6 Al: E = 68.9 GPa, σ_yield = 276 MPa, ρ = 2700 kg/m³ | ASSUMED — carbon tube is the lighter/stiffer alternative but anisotropic with no single yield; Al is the conservative baseline |
| Tip mass `m_tip` | **0.175 kg** | **FIRMED (item 15 §1.2)** — Hokuyo UST-10LX 0.130 kg [datasheet] + 0.030 kg bracket + 0.015 kg cable |
| Maneuver accel `a_lat,peak` | 19.4 m/s² (≈ 2.0 g) | **MEASURED** — clean lap, `runs/ride_quality_baseline` |
| Crash shock | 50 g = 490 m/s² | ASSUMED — stated half-sine-equivalent survival shock; bounds a low-speed bench drop and deliberately governs strength over the ~2 g maneuvering case |
| Safety factors | SF_maneuver = 2.0, SF_crash = 1.5 | ASSUMED — 2.0 on yield for the repeated maneuvering load; 1.5 on top of the already-inflated 50 g crash |

**Results — both load cases** (cantilever, tip point load `F = m_tip·a·SF`, fixed root):

_Baseline geometry (L=120 mm, OD=16 mm, t=1.5 mm), firmed 0.175 kg tip:_

| Quantity | Maneuvering (2 g, SF 2.0) | Crash (50 g, SF 1.5) |
| --- | ---: | ---: |
| Tip force `F` | 6.79 N | 128.76 N |
| Root moment `M = F·L` | 0.815 N·m | 15.45 N·m |
| Max bending stress `σ = M·c/I` | 3.59 MPa | 68.10 MPa |
| Tip deflection `δ = F·L³/(3EI)` | 0.031 mm | 0.593 mm |
| Yield margin `σ_yield/σ` | **76.9** (PASS, ≥2.0) | **4.05** (PASS, ≥1.5) |

The **crash case governs strength** (σ ≈ 68 MPa vs 4 MPa); both clear yield with margin. Stress is modest because a 16 mm tube is over-stiff in bending for these loads — strength is not the binding constraint. (The firmed 0.175 kg tip lowered the crash stress from the 0.20 kg-placeholder 77.8 → 68.1 MPa, lifting the crash SF 3.55 → 4.05.)

**First natural frequency** (load-independent; Rayleigh tip-mass model):

| Quantity | Value |
| --- | ---: |
| `k_eff = 3EI/L³` | 2.171×10⁵ N/m |
| `m_eff = m_tip + 0.23·m_mast` (m_mast = 22.1 g) | 180.1 g |
| `f1 = (1/2π)·√(k_eff/m_eff)` | **174.7 Hz** |

**Acceptance criterion:** `f1` must clear the **100 Hz control update rate** and a plausible low-hundreds-Hz motor/drivetrain excitation band by a factor of 2, i.e. **f1 ≥ 200 Hz**. **Result: 174.7 Hz → FAIL.** The lighter firmed tip mass raised the baseline f1 from 163.8 (0.20 kg placeholder) to 174.7 Hz, but it **still lands inside the 2× guard band** (clears 100 Hz at 1.7×), so the slender-tube baseline remains unacceptable. **Action: stiffen — shorter `L`, larger OD/wall, or a carbon tube — and re-check before accepting the mast.** This is exactly the kind of binding constraint the modal analysis (Section 6) is meant to catch.

> **This `3.1` hand calc is the analytical ground truth the Section 4 static FEA (and Section 6 modal) must reproduce within ~10–15% (away from stress concentrations) before the detailed-geometry FEA is trusted.**

### 3.2 Design revision — frequency fix (REQUIRED: the baseline FAILS modal)

The §3.1 baseline **passes strength but fails the modal guard band** (`f1 = 174.7 Hz < 200 Hz`, on the firmed 0.175 kg tip mass). A design sweep over mast geometry and material was run to find a configuration that clears `f1 ≥ 200 Hz` with comfortable margin while keeping the crash-case yield safety factor acceptable. Reproduce with `python experiments/mast_hand_calc.py`; raw output in `runs/mast_hand_calc/design_sweep.txt`.

**Sweep space:** length `L ∈ {0.12 … 0.08} m`, outer diameter `OD ∈ {16 … 25} mm`, wall `t ∈ {1.0, 1.5, 2.0} mm`, material ∈ {6061-T6 aluminum, CFRP}. For every candidate the sweep recomputes `f1 = (1/2π)·√(3EI/(L³·m_eff))` with `m_eff = m_tip + 0.23·m_mast`, and the **governing crash-case** stress/SF.

> **CFRP alternative (clearly-stated assumed properties):** a roll-wrapped/pultruded carbon-fiber tube, axial modulus depends strongly on layup (≈ 70–130 GPa); the sweep assumes **E = 100 GPa, ρ = 1600 kg/m³**. CFRP is **anisotropic with no single tensile yield**, so a "yield SF" is not strictly defined — it is screened only against a **conservative 600 MPa bending allowable** (well below ultimate ≈ 1.5–2 GPa). **Aluminum remains the recommended baseline** because its yield is well-defined; CFRP is the lighter upgrade path if mast mass ever becomes binding.

**Recommended revised mast:** **6061-T6 aluminum, L = 100 mm, OD = 20 mm, wall t = 1.5 mm (stock).** This uses **both** stiffness levers (modestly shorter `L`, larger `OD`), keeps the stock 1.5 mm wall and the well-defined-yield aluminum, and only trims `L` by 20 mm (preserving the LiDAR optical-center height / sightline over the compute stack) — most of the stiffness budget is spent on diameter.

| Quantity | **Baseline (FAILS)** | **Recommended (PASSES)** |
| --- | ---: | ---: |
| Geometry | L=120 mm, OD=16 mm, t=1.5 mm | **L=100 mm, OD=20 mm, t=1.5 mm** |
| Material | 6061-T6 Al | 6061-T6 Al |
| Section `I` | 1815 mm⁴ | **3754 mm⁴** (×2.07) |
| `k = 3EI/L³` | 2.17×10⁵ N/m | **7.76×10⁵ N/m** (×3.58) |
| **`f1` (Rayleigh, 0.175 kg tip)** | **174.7 Hz → FAIL** (< 200) | **330.1 Hz → PASS** (1.65× the 200 Hz guard; 3.3× the 100 Hz control rate) |
| Crash-case `σ` | 68.1 MPa | **34.3 MPa** |
| **Crash-case SF** vs yield | 4.05 (PASS) | **8.05 (PASS)** |
| Crash tip deflection | 0.593 mm | 0.166 mm |
| Mast self-mass | 22.1 g | 23.5 g (**+1.4 g**) |

**Why it works (stiffness rises far faster than mass).** Because the 0.175 kg tip mass dominates `m_eff` (mast self-mass ≈ 0.02 kg), `m_eff` is nearly constant and `f1 ≈ √(3EI/L³)`. The two levers attack `k = 3EI/L³` directly:
- **Shorter `L`:** `k ∝ L⁻³`, so 120→100 mm raises `k` by `(120/100)³ = 1.73×` (`f1 ∝ L⁻¹·⁵`) at essentially **zero mass cost**.
- **Larger `OD`:** for a thin wall `I ∝ OD³·t`, so 16→20 mm raises `I` by `2.07×`, while the extra material it adds to `m_eff` is second-order (tip mass dominates).

Together they lift `k` by `3.58×` and `f1` from 174.7 → 330.1 Hz. The same geometry change **also lowers** the crash stress (more `I` ⇒ less `M·c/I`), so the fix is **monotonic in both checks** — strength margin actually improves (SF 4.05 → 8.05). The same 100 mm/20 mm tube in CFRP would reach ≈ 400 Hz at ≈ 14 g, but aluminum is kept for its defined yield.

**Hand sanity-check of the recommended `f1`:** `I = π/64·(20⁴−17⁴) = 3754 mm⁴`; `k = 3·68.9e9·3.754e-9/0.1³ = 7.76×10⁵ N/m`; `m_eff = 0.175 + 0.23·0.0235 = 0.1804 kg`; `f1 = (1/2π)·√(7.76e5/0.1804) = 330.1 Hz`. ✔ matches the sweep.

> **FEA status — RE-RUN on the firmed 0.175 kg tip mass and VALIDATED.** The gmsh + CalculiX toolchain (gmsh 4.15.2 mesher in the conda `base` env; CalculiX 2.23 `ccx` solver in a conda `fea` env) was re-run on the **recommended** geometry with the firmed mass via `experiments/mast_fea.py`. **FEA agrees with the hand calc within ±15 %** on all three headline metrics, and the higher-fidelity **FE first frequency (285.5 Hz, up from 267.4 Hz at the old 0.20 kg placeholder) still clears the ≥ 200 Hz guard** (1.43×). Stand-up commands and the full workflow are in **`docs/design/FEA_SETUP.md`**; results in `runs/mast_fea/fea_summary.txt`. See §4 and §6.

## 4. Static FEA vs Hand Calc (REQUIRED)

> **DONE for the recommended geometry (§3.2), re-run on the firmed 0.175 kg tip mass.** Static FEA was run on the recommended mast (L=100 mm, OD=20 mm, t=1.5 mm, 6061-T6) with the **crash** load (**128.8 N** = 0.175 kg × 50 g × 1.5) and a fixed (ENCASTRE) root, via `experiments/mast_fea.py` (gmsh C3D10 mesh → CalculiX `ccx`). The crash load is **distributed over the tip-ring nodes** (a single-node point load creates a non-physical nodal singularity); stress is compared on a **mid-span gauge ring** (away from the fixed root and the load) where elementary `M·c/I` applies, plus the global tip deflection. Mesh: 58 232 nodes / 28 985 quadratic tets, element size ≈ 1.2 mm. Raw results in `runs/mast_fea/fea_summary.txt`; toolchain in `docs/design/FEA_SETUP.md`.

| Quantity | Hand calc | FEA | Δ% | Within ±15%? |
| --- | ---: | ---: | ---: | --- |
| Tip deflection (crash) | 0.166 mm | 0.176 mm | +5.9% | **YES** |
| Mid-span gauge stress (crash) | 17.1 MPa | 17.4 MPa | +1.3% | **YES** |

> The fixed-root **peak** von Mises (41.9 MPa) is a re-entrant-corner stress concentration / mesh singularity, **not** a valid `M·c/I` comparison (root beam-theory `M·c/I` = 34.3 MPa) — which is exactly why the §5 mesh-convergence metric and the comparison above use a defined gauge region and the global deflection, not the peak nodal stress. Tip deflection (+5.9%) and gauge stress (+1.3%) both fall well inside the ±15% band, so the static hand calc is validated.

## 5. Mesh Convergence (REQUIRED, <5%)

> **DONE — PASS.** Three uniform refinements (~1.5× each) of the recommended mast, solved for the static crash case **and** the first bending mode via `python experiments/mast_fea.py --converge` (raw table: `runs/mast_fea/mesh_convergence.txt`). The gauge band is held **fixed** (z = L/2 ± 1.0 mm) across all levels so every mesh samples the same physical region — letting the band scale with element size would change the comparison region between levels and contaminate the convergence measure. Acceptance: <5% change in gauge stress (and tip deflection and f1) between the two finest meshes.

| Mesh level | Element size / count | Gauge stress | Δ% | Tip defl. | Δ% | f1 | Δ% |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Coarse | 3.0 mm / 4 747 C3D10 | 17.38 MPa | — | 0.1772 mm | — | 290.6 Hz | — |
| Medium | 2.0 mm / 10 435 C3D10 | 17.50 MPa | +0.70% | 0.1751 mm | −1.15% | 289.6 Hz | −0.35% |
| Fine | 1.2 mm / 28 985 C3D10 | 17.48 MPa | **−0.15%** | 0.1757 mm | **+0.30%** | 285.5 Hz | **−1.42%** |

All three metrics move by <1.5% at the final refinement — an order of magnitude inside the 5% acceptance band, so the 1.2 mm production mesh used in §4/§6 is converged for the quantities being reported. (The global *peak* von Mises at the fixed-root corner is deliberately **not** tracked here: it sits on a re-entrant-corner singularity and diverges with refinement, which is exactly why the acceptance metric is defined on the gauge region.)

## 6. Modal Analysis (REQUIRED, with acceptance criterion)

> **DONE for the recommended geometry (§3.2), re-run on the firmed 0.175 kg tip mass.** Acceptance criterion: `f1` must clear the **100 Hz control update rate** AND a plausible low-hundreds-Hz motor/drivetrain excitation band by **≥ 2× ⇒ f1 ≥ 200 Hz**. A CalculiX `*FREQUENCY` modal solve was run on the recommended mast with the **0.175 kg** LiDAR (Hokuyo UST-10LX, item 15) as a lumped `*MASS` element at the tip and a fixed root (`experiments/mast_fea.py`). **The baseline (174.7 Hz) FAILED this guard; the recommended geometry PASSES by both the hand calc (330.1 Hz) and the FEA (285.5 Hz).**

| Mode | Natural frequency (FEA) | Excitation source to clear | Margin | Pass? |
| --- | ---: | --- | --- | --- |
| 1st (bending) | **285.5 Hz** (hand calc 330.1 Hz, Δ −13.5%) | 100 Hz control rate; low-hundreds-Hz motor band | **1.43× the 200 Hz guard; 2.86× the 100 Hz rate** | **YES** |
| 2nd (bending, orthogonal) | 301.3 Hz | — | — | — |
| 3rd | 1009.3 Hz | — | — | — |

> Modes 1–2 are the two ~degenerate orthogonal bending modes of the axisymmetric tube (the small 285→301 Hz split is mesh asymmetry). The FE `f1` lands ~14% below the Rayleigh hand calc because the closed-form model assumes a perfectly rigid root and pure Euler–Bernoulli bending (neglecting shear and root flexibility) and so slightly over-predicts stiffness — the expected direction and magnitude. **Even at the higher-fidelity 285.5 Hz the design clears the ≥ 200 Hz guard (1.43×)** — the lighter firmed LiDAR improved the FE margin from 1.34× (0.20 kg) to 1.43× — so the frequency fix is robust. Baseline-vs-recommended comparison and reasoning: §3.2.

## 7. Tolerance Stack → LiDAR Angular Error (REQUIRED)

> **DONE — with a derived install requirement.** `experiments/mast_tolerance_stack.py` (raw: `runs/mast_tolerance_stack/summary.txt`). The UST-10LX scans a horizontal plane, so yaw misalignment is nulled by the software mount calibration; the physical stack that matters is the **tilt** of the scan plane. The requirement is derived from the sightline, both directions, at the 10 m guaranteed range (optical center 0.170 m above floor = 0.100 m mast [LOCKED] + 0.070 m deck [ASSUMED]; wall 0.30 m [ASSUMED, conservative vs the common 0.33 m duct]): **governing bound = up-tilt wall clearance, θ ≤ 0.745°** (down-tilt floor-graze bound 0.974°).

| Contributor | Tolerance | Angular contribution | Note |
| --- | --- | ---: | --- |
| Deck local flatness (20 mm base seat) | 0.10 mm / 20 mm | 0.286° | ASSUMED, machined/FR4-plate class |
| Mast base-to-tube squareness | — | 0.500° | ASSUMED FDM-bracket class, no post-machining |
| Bolted-joint preload rocking | — | 0.100° | clearance goes to yaw (software-nulled); tilt allowance kept |
| LiDAR internal scan-plane-to-base | — | 0.250° | ASSUMED — datasheet does not spec it |
| LiDAR mounting datum | 0.10 mm / 40 mm | 0.143° | ASSUMED bolt-pattern flatness |
| Elastic tilt @ 2g maneuvering | FEA-derived | 0.004° | negligible — stack is interface-dominated |
| **Worst-case sum (blind assembly)** | — | **1.284°** | **FAIL** vs 0.745° |
| **RSS (blind assembly)** | — | **0.652°** | passes, but with no margin policy behind it |
| **Worst-case after scan-plane leveling** | — | **0.354°** | **PASS**, >2× margin |

Beam-height error: ±5.7 cm (RSS, blind) / ±3.1 cm (calibrated worst) at 5 m; ±11.4 / ±6.2 cm at 10 m.

**Derived requirement:** blind assembly fails worst-case, so the build gains a one-time **scan-plane leveling step** — shim the mast base, verify by scanning a wall at two distances and equalizing return heights. That nulls every contributor external to the LiDAR; the calibrated residual (internal spec + preload drift + elastic) passes the governing bound with >2× margin. This is the same pattern as the §3.2 frequency fix: the analysis exists to catch the failure and convert it into a cheap requirement before anything is built.

## 8. Design Page(s)

> TEMPLATE / TODO. One polished design page per major part (chassis plate, sensor deck, LiDAR mast): CAD render, key dimensions, governing load case + result, FEA contour, modal result, and the tolerance budget. Export figures to `docs/design/figures/`.

## 9. Checklist

- [x] Inputs from items 13-15 filled (geometry; **LiDAR mass + height LOCKED** — Hokuyo UST-10LX, 0.130 kg datasheet → tip mass 0.175 kg, h_arm = 0.100 m, item 15 §1.2; **clean peak lateral accel `a_lat,peak = 19.4 m/s²` DONE** — pure-pursuit baseline, clean lap, `runs/ride_quality_baseline/`). Compute/battery/IMU masses still pending for the §2 budget.
- [ ] Mass & CG budget (depends on remaining item-15 compute/battery picks)
- [x] FBD + hand calc, maneuvering case derived from telemetry, NOT 4g (§3.1)
- [x] FBD + hand calc, separate crash/drop case (§3.1; crash governs strength)
- [x] **Design revision — frequency fix** (§3.2): baseline `f1=174.7 Hz` (firmed 0.175 kg tip) FAILED the ≥200 Hz guard; recommended **L=100 mm / OD=20 mm / t=1.5 mm 6061-T6** → `f1=330.1 Hz`, crash SF 8.05 (both PASS)
- [x] Static FEA vs hand calc within ±15% (§4): tip deflection +5.9%, gauge stress +1.3% (gmsh + CalculiX, recommended geometry, firmed mass)
- [ ] Mesh convergence <5% on a defined gauge region (gauge ring defined and used in §4; a formal ≥3-level refinement study still to run)
- [x] Modal analysis with first-frequency clearance of motor band AND 100 Hz control rate (§6): FE `f1=285.5 Hz` ≥ 200 Hz guard (1.43×)
- [ ] Tolerance stack → LiDAR angular error (depends on item 15 lock)
- [ ] Polished design page per part
- [x] **FEA toolchain stood up and tested** (gmsh 4.15.2 + CalculiX 2.23 `ccx`); commands in `docs/design/FEA_SETUP.md`, pipeline `experiments/mast_fea.py`
