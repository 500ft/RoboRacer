# 14 — Chassis, Drivetrain, and Actuator Selection

**Status: PLATFORM + DRIVETRAIN LOCKED (2026-07-07).** Platform = **Traxxas Slash 4x4 VXL (TRA68086-4)** — the RoboRacer restricted-class baseline chassis (item 13 §2.1 R-13). Feeds **15** (sensor/compute/power) and **16** (mechanical design + FEA). **Design-only: no fabrication.** Dependency order: **13 → 14 → 15 → 16**.

**Geometry lock:** the rolling platform must reproduce the identified model geometry, in particular **wheelbase = 0.3302 m** (`WHEELBASE_M = 0.15875 + 0.17145` in `gym/roboracer/closed_loop.py`). Any deviation must be documented with its effect on the identified `C_Sf` / `C_Sr` (Section 5).

---

## 1. Platform Decision — Traxxas Slash 4x4 VXL (TRA68086-4)

**DECIDED: standard 1/10 RC class, Traxxas Slash 4x4 VXL RTR (TRA68086-4), with a custom sensor deck (item 16) on top.** The custom-chassis option is rejected.

| Option | Pros | Cons | Wheelbase fit to 0.3302 m | Decision |
| --- | --- | --- | --- | --- |
| **Slash 4x4 VXL (TRA68086-4)** | **Restricted-class baseline chassis by name (R-13)**; ecosystem parts; the documented F1TENTH/RoboRacer reference build; ships with the rules-ceiling motor (Velineon 3500) and a usable servo | Fixed geometry: wheelbase 0.324 m ≠ 0.3302 m (−1.9%) | 0.324 m stock (**deviation documented, §2/§5**) | **SELECTED** |
| Custom chassis | Exact 0.3302 m geometry | More design/build effort and risk; **not a named restricted-class baseline — would face the 15% dimensional-window inspection instead of automatic legality**; forfeits ecosystem spares | Exact by design | rejected |

Rationale against the requirements: R-13 (this is the named legal chassis — TRA74054 / TRA6804R / TRA68086 are all permitted; the Platinum TRA6804R is the low-CG variant and remains a drop-in alternative), R-01 (60+ mph capability ≫ 8.33 m/s operating point), R-10 (1/10 scale), R-11 (2.64 kg rolling mass leaves ≈ 1.9 kg for deck + sensors + compute + batteries within the 4.5 kg budget). Vendor spec: [traxxas.com 68086-4](https://traxxas.com/68086-4-110-slash-4x4-vxl-brushless-short-course-truck-w-tqi).

## 2. Geometry

| Parameter | Value | Source |
| --- | ---: | --- |
| Wheelbase (model target) | **0.3302 m** | `WHEELBASE_M` in `gym/roboracer/closed_loop.py` |
| Wheelbase (platform, stock) | **0.324 m** (12.75 in) | Traxxas 68086-4 vendor spec |
| Wheelbase deviation | **−6.2 mm (−1.9%)** | derived — see §5 for the modeling consequence |
| lf (front axle → CG) | 0.15875 m | `s_max`-companion params in `gym/roboracer/dynamics.py` (`"lf": 0.15875`) — confirmed it is lf, not just the first summand |
| lr (CG → rear axle) | 0.17145 m | `gym/roboracer/dynamics.py` (`"lr": 0.17145`) |
| Track (front = rear, overall) | 0.296 m (11.65 in) | Traxxas 68086-4 vendor spec; **rules window 238–341 mm ✓** |
| Overall length | 0.568 m (22.36 in) | vendor spec; **rules window 454–654 mm ✓** |
| Ground clearance | 0.072 m | vendor spec — sets the deck underside datum for CAD |
| Tire diameter | **0.1095 m** (4.31 in) | vendor spec — used in §3 sizing |

> **Deviation handling (binding rule):** the −1.9% wheelbase delta (and any CG shift from the deck build) alters the slip/yaw relationship the identified `C_Sf`/`C_Sr` were fit to. Per §5, the sim coefficients are **not** carried to hardware; the platform gets its own excitation + held-out identification (the pipeline already exists and is validated). The 0.3302 m figure remains the *model* geometry for all sim work.

### 2.1 Chassis modifications (baseline → build)

Per the standard F1TENTH/RoboRacer build ([docs](https://f1tenth.readthedocs.io/en/foxy_test/getting_started/build_car/bom.html)): remove the body shell + rear spoiler mounts, remove the stock VXL-3s ESC and receiver (replaced by VESC + Jetson, §3 / item 15), keep motor + servo + drivetrain stock, add the laser-cut platform deck on standoffs. The deck is the item-16 CAD centerpiece and must reserve the R-14 transponder bay (≥ 8 × 12 cm, front half, clear above).

## 3. Drivetrain — Motor / ESC Sizing

**Motor: stock Velineon 3500 (brushless, 3500 kV, sensorless)** — kept deliberately: it is the restricted-class spec **ceiling** (R-17), so it is both legal and the maximum allowed. **ESC: VESC 6 MkVI** replaces the stock VXL-3s — required for the software stack (`/drive` → duty/current control, ERPM odometry out) and is standard on F1TENTH/RoboRacer builds. Rules allow custom ESCs with no restriction.

| Quantity | Symbol | Value | Source / method |
| --- | --- | --- | --- |
| Sizing speed (design point) | v | 10 m/s (covers R-01's 8.33 m/s with margin) | design choice |
| Wheel diameter | d_w | 0.1095 m | vendor spec (§2) |
| Wheel speed at 10 m/s | n_w | 10 / (π·0.1095) · 60 = **1 744 rpm** | derived |
| Overall drive ratio (stock) | G | **11.82** | vendor spec |
| Motor speed at 10 m/s | n_m | 1 744 × 11.82 = **20 600 rpm** | derived |
| Motor no-load speed on 3S | n_0 | 3 500 kV × 11.1 V = **38 850 rpm** | datasheet kV × pack nominal |
| Operating point | n_m/n_0 | **0.53** — comfortably inside the usable band | derived; sanity: stock truck is rated 60+ mph on higher cells |
| Peak tractive force for R-05 | F = m·a | 4.42 kg × 9.51 m/s² = **42.0 N** | R-11 mass estimate (item 16 §2) × R-05 |
| Wheel torque at F | T_w | 42.0 × 0.0548 = **2.30 N·m** | derived |
| Motor torque (÷G, ÷η=0.9 driveline **ASSUMED**) | T_m | 2.30 / 11.82 / 0.9 = **0.216 N·m** | derived |
| Motor torque constant | K_t = 60/(2π·kV) | **2.73 mN·m/A** | derived from kV |
| Peak phase current at T_m | I | 0.216 / 0.00273 ≈ **79 A** (transient, at the accel peak) | derived |
| ESC continuous / burst | — | **80 A / 120 A** (mount/airflow dependent) | VESC 6 MkVI vendor spec ([trampaboards.com](https://trampaboards.com/vesc-6-mkvi--the-amazing-trampa-vesc-6-mkvi--gives-maximum-power-original-p-27536.html)) |

> **Margin statement:** the R-05 peak-accel current (~79 A) sits at the VESC's 80 A continuous rating but is a **transient** (the clean-lap accel peak, not a sustained draw); the 120 A burst rating covers it with 1.5×. Honest caveat: the 79 A figure ignores motor efficiency losses and uses an assumed 90% driveline efficiency — it is an estimate for sizing, to be replaced by a measured VESC current log at bring-up (item 17).

## 4. Steering Servo — stock Traxxas 2075

**DECIDED: keep the stock 2075 digital waterproof servo** shipped in the TRA68086-4. Checked against R-02/R-03:

| Quantity | Value | Source |
| --- | ---: | --- |
| Required steering angle range (R-02) | ≥ ±0.4189 rad at the road wheel | model `s_max` (`gym/roboracer/dynamics.py`) |
| Stock coverage of R-02 | ±0.4189 rad = ±24° — inside the stock Slash steering envelope (this is the servo/linkage the chassis ships with) | chassis-stock capability; **verify exact road-wheel sweep at CAD/bench** |
| Required steering rate (R-03) | ≥ 3.2 rad/s at the road wheel | model `sv_max` (`gym/roboracer/dynamics.py`) |
| Servo slew (datasheet) | 0.16 s/60° ⇒ **6.5 rad/s** → **2.0× over R-03** | Traxxas 2075 spec ([traxxas.com](https://traxxas.com/2075-digital-waterproof-servo)) |
| Servo torque (datasheet) | 125 oz·in = **9.0 kg·cm = 0.88 N·m** | Traxxas 2075 spec |
| Torque adequacy | screened by comparable hardware: this exact servo steers this exact chassis at higher speeds than R-01 in stock form | comparable-hardware check; no separate kingpin-load calc performed (**stated screen, not a calc**) |

> Linkage ratio note: the rate/torque comparison assumes ≈1:1 servo-horn-to-road-wheel over the small-angle range used in racing (nominal commands ≈ 0.2 rad). The exact nonlinear linkage ratio comes out of the item-16 CAD; the 2.0× rate margin absorbs plausible ratio penalties.

## 5. Geometry-Deviation Impact on Identified Parameters

**Standing rule (unchanged, now with the concrete numbers):** the platform deviates from the identified model in wheelbase (0.324 vs 0.3302 m, −1.9%) and mass (≈ 4.42 vs 3.74 kg, **+18%** — item 16 §2), and the real tires differ from the sim tire model entirely. Therefore the sim `C_Sf = 4.718`, `C_Sr = 5.4562` are **not** assumed to hold on hardware. The transfer plan is the one this repo was built to execute: run the SysID excitation on the vehicle, fit, and accept only on held-out replay (`reports/dynamic_parameter_identification.md` procedure), with the robustness limits from `reports/parameter_id_robustness.md` (latency is the dominant failure path — budget the sensing chain accordingly). The mass deviation also propagates into the §3 tractive sizing (already computed at 4.42 kg).

## 6. Open Questions

> **RESOLVED (2026-07-07):** platform (TRA68086-4), stock wheelbase (0.324 m) + delta handling, gear ratio (11.82), wheel diameter (0.1095 m), servo rate margin (2.0×), exact steering-rate limit (3.2 rad/s from `dynamics.py`).
>
> **STILL OPEN (CAD/bench, not catalog):** exact road-wheel steering sweep and linkage ratio (item-16 CAD); measured VESC current at the accel peak (item 17 bring-up); whether to move to the low-CG Platinum chassis (TRA6804R) if the item-16 CG budget wants it.
