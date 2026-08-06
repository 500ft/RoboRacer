# 15 — Sensor, Compute, and Power Package

**Status: PACKAGE LOCKED (2026-07-07) — LiDAR, IMU, odometry, compute, and power architecture all decided.** Depends on **13** (requirements) and **14** (platform/geometry). Shares the build with **16** (mechanical). **Design-only: no fabrication.** Dependency order: **13 → 14 → 15 → 16**.

**Hard contract:** the selected sensors must produce the topics the existing pipeline already consumes — **`/ego_racecar/odom`** and **`/drive`** — so the sim-validated identification/control stack runs unchanged. Optional enrichment topic for achieved steering / slip: `/f1tenth/internal_state` (see top-level `README.md`).

---

## 1. Sensor Suite → Topic Mapping

> **All rows LOCKED (2026-07-07).** Every row terminates in a topic the pipeline reads.

| Sensor | Part | Quantity it provides | ROS2 topic it feeds | Notes |
| --- | --- | --- | --- | --- |
| 2D LiDAR | **Hokuyo UST-10LX** (LOCKED) | scan → localization → pose | `/scan` (`sensor_msgs/LaserScan`) → localization (e.g. particle filter) → **`/ego_racecar/odom`** | **Mass 130 g [datasheet]** → firmed mast tip mass 0.175 kg, item 16 §1.1 / §3 |
| IMU | **VESC 6 MkVI onboard IMU** (LOCKED — 9-axis SPI IMU integrated on the ESC; MkIII–MkV shipped Bosch BMI160-class parts) | yaw rate, accel | VESC driver → `sensor_msgs/Imu` → fuses into odom / EKF | **Zero added mass/cost/wiring.** Risk flagged: the ESC sits on the sprung chassis near the motor — if bench vibration/EMI makes it noisy, fallback = Bosch BNO055-class breakout on the deck (≈ 3 g, I2C/USB), a drop-in at the EKF input. Section-5 EKF uses yaw_rate; accel feeds ride-quality metrics |
| Wheel / motor odometry | **VESC ERPM odometry** (LOCKED — sensorless BEMF electrical-RPM from the Velineon 3500, converted via pole count + gear ratio 11.82 + wheel dia 0.1095 m) | speed | `vesc_to_odom` (standard F1TENTH stack) → **`/ego_racecar/odom`** | Provides the `speed_mps` analog used throughout sim. Known limitation: sensorless ERPM is unreliable below ≈ 1 m/s (BEMF too small) — acceptable for racing, flagged for launch/standing-start behavior |
| Drive command sink | VESC 6 MkVI + Traxxas 2075 servo (item 14 §3–§4) | consumes commands | subscribes **`/drive`** | Closes the loop |

### 1.1 LiDAR selection — Hokuyo UST-10LX (LOCKED)

**Choice: Hokuyo UST-10LX 2D scanning laser rangefinder.** Rationale:

- **It is the canonical F1TENTH/RoboRacer sensor.** The official F1TENTH "Build" BOM specifies the Hokuyo UST-10LX (or the longer-range UST-20LX), so picking it keeps this design on the community-standard hardware/software path — the same `urg_node` driver, `/scan` topic, and localization stack the existing sim pipeline already targets.
- **Interface satisfies the hard contract.** The UST-10LX is a 100BASE-TX Ethernet device; the ROS 2 `urg_node` driver publishes `sensor_msgs/LaserScan` on **`/scan`**, which feeds localization → **`/ego_racecar/odom`** (the topic the identification/control stack consumes). No pipeline change.
- **Performance is appropriate for a 1/10-scale indoor track:** 270° field of view, 0.25° angular resolution, 0.06–10 m range, 40 Hz scan rate (25 ms) — comfortably faster than the 100 Hz control loop's need for fresh scans and well-matched to ~5 m hallway/track geometry.

| LiDAR datasheet quantity | Value | Source |
| --- | ---: | --- |
| **Mass** | **≈ 130 g** | **Hokuyo UST-10LX / UST-20LX specification sheet, "Mass: Approx. 130 g"** (same 130 g listed in the official F1TENTH BOM) |
| Interface | 100BASE-TX Ethernet | Hokuyo UST-10LX datasheet |
| ROS 2 driver / topic | `urg_node` → **`/scan`** (`sensor_msgs/LaserScan`) | F1TENTH software stack |
| Supply voltage | 12 V DC (10.8–12.0 V) | Hokuyo UST-10LX datasheet |
| Power draw | **≈ 3.6 W** typical (≈ 0.30 A @ 12 V); ≈ 8.4 W (0.7 A) max in-rush at startup | Hokuyo UST-10LX datasheet "Current consumption: 0.3 A (Rush current 0.7 A)" |
| Field of view / resolution | 270° / 0.25° (1080 steps) | Hokuyo UST-10LX datasheet |
| Detection range | 0.06–10 m | Hokuyo UST-10LX datasheet |
| Scan rate | 40 Hz (25 ms/scan) | Hokuyo UST-10LX datasheet |

> **Lighter / cheaper alternative (noted, not selected): Slamtec RPLIDAR S2** (≈ 190 g incl. base; 360°, 30 m, 12 V, UART/USB → `rplidar_ros` → `/scan`) or the **RPLIDAR A2M12** (≈ 190 g). These are lower-cost and widely used on F1TENTH builds; their ~190 g body lands close to the Hokuyo-based tip mass below, so the structural conclusion is unchanged. The Hokuyo UST-10LX is kept as the baseline because it is the documented F1TENTH reference part with the cleanest Ethernet/`/scan` integration.

### 1.2 Firmed mast tip mass (input to item 16)

The LiDAR tip mass for the item-16 mast load case is now **firmed** from the selected part:

| Component | Mass | Basis |
| --- | ---: | --- |
| Hokuyo UST-10LX body | 0.130 kg | **datasheet** (≈ 130 g) |
| Mounting bracket + M3 fasteners | 0.030 kg | ASSUMED allowance (3D-printed / Al L-bracket + hardware; bench-typical for this sensor) |
| Tip-carried cable + connector | 0.015 kg | ASSUMED allowance (Ethernet pigtail + power lead run to the deck) |
| **Firmed mast tip mass `m_LiDAR_tip`** | **0.175 kg** | LiDAR + bracket + cable |

> This **0.175 kg** replaces the old **0.20 kg ASSUMED placeholder** in `experiments/mast_hand_calc.py` and `experiments/mast_fea.py`. Because it is **lighter**, it **raises** the mast's first natural frequency and **lowers** bending stress — a strict improvement on both the modal guard and the strength margin (verified: hand-calc recommended-geometry `f1` 309.3 → **330.1 Hz**; FE `f1` 267.4 → **285.5 Hz**; crash SF 7.04 → **8.05**). See item 16 §3.1–§3.2, §4, §6.
>
> **Optical-center height above deck** (the mast moment arm / sightline) is the recommended mast length: **`h_arm ≈ L = 0.100 m`** (item 16 §3.2 frequency-fix geometry). The mast was sized to keep this clearance over the compute stack while clearing the 200 Hz modal guard.

## 2. Compute Sizing — NVIDIA Jetson Orin NX 16 GB (LOCKED)

**DECIDED: NVIDIA Jetson Orin NX 16 GB module on a Seeed reComputer J401 carrier** (the reComputer J4012 configuration). Rationale: (a) rules place **no restriction** on compute as long as everything runs onboard (R-15) — Jetson family is the community-standard choice named in the rules commentary; (b) it is the current-generation part in the official RoboRacer build docs (successor to the Xavier NX the older docs list); (c) the J401 carrier accepts **9–19 V DC** input, so it runs directly off a 3S pack across its full discharge range (§3). Sized against R-08 / R-12:

| Quantity | Value | Source |
| --- | ---: | --- |
| Control loop rate | 100 Hz (10 ms budget) | all controller reports |
| MPC p95 solve time | 1.32644 ms | `reports/mpc_controller.md` |
| MPC mean solve time | 1.0739 ms | `reports/mpc_controller.md` |
| MPC max solve time (spike) | ~36.8073 ms | `reports/mpc_controller.md` — exceeds one 10 ms period |
| Selected compute | **Jetson Orin NX 16 GB + Seeed J401 carrier** (configurable 7–40 W power modes) | [seeedstudio.com reComputer J4012](https://www.seeedstudio.com/reComputer-J4012-p-5586.html); [J401 datasheet](https://files.seeedstudio.com/wiki/reComputer-J4012/Carrier-Board-J401/J401-datasheet.pdf) |
| Headroom target (R-08) | **p95 ≤ 25% of the 10 ms budget** (2.5 ms) — the dev-machine p95 of 1.33 ms already meets this; Orin NX must be re-benched | design choice |

> Honest note (unchanged): the p95 fits 100 Hz on the dev machine, but the max solve time already breaks a single control period. A deployment build should use a dedicated QP solver, watchdog timing, or a shorter horizon (per the MPC report). Compute selection does not assume the SciPy/SLSQP timing is final — the loop-timing bench on the Orin NX (R-08 verification) is what closes this.

> Honest note: the p95 fits 100 Hz on the dev machine, but the max solve time already breaks a single control period. A deployment build should use a dedicated QP solver, watchdog timing, or a shorter horizon (per the MPC report). Compute selection should not assume the SciPy/SLSQP timing is the final timing.

## 3. Power Budget — two-battery architecture (LOCKED)

**Architecture: two separate 3S packs.** Pack A (drive) feeds the VESC only; Pack B (compute/sensors) feeds the Jetson directly (9–19 V input accepts the full 3S swing of 9.0–12.6 V) and the LiDAR through a small 12 V regulator (the UST-10LX's 10.8–12.0 V window is narrower than a 3S swing, so it cannot run raw off the pack). This is the standard F1TENTH practice: it isolates the compute rail from ESC current transients/brownouts, and it is rules-clean — R-16 allows multiple batteries as long as at most one ≤ 4S pack drives the motor. Our *drive* pack is 3S, one class below the 4S ceiling: legal, matches the stock VXL platform rating, and the §-item-14 sizing shows 3S already covers the R-01/R-05 envelope — 4S would buy top speed the controllers never command.

| Load | Nominal | Peak | Voltage / rail | Source |
| --- | --- | --- | --- | --- |
| Drive motor + VESC 6 MkVI | ≈ 10 A race-average (**ASSUMED**, to be replaced by a VESC log) | ≈ 79 A at the R-05 accel transient (item 14 §3) | Pack A, 3S 11.1 V nominal | item 14 §3 sizing |
| Compute (Orin NX + J401) | ≈ 2.7 A (30 W system **ASSUMED**: 25 W max module mode + carrier overhead) | ≈ 3.6 A (40 W MAXN ceiling) | Pack B direct, 9.0–12.6 V | Seeed J4012 page (7–40 W modes); split module/carrier draw not published — bench-measure at bring-up |
| LiDAR (Hokuyo UST-10LX) | **0.30 A** (≈ 3.6 W) | 0.7 A in-rush | **12 V regulated** off Pack B | Hokuyo UST-10LX datasheet |
| Servo (Traxxas 2075) + logic | ≈ 1 A average (**ASSUMED**); stall transients higher | 3 A (**ASSUMED** stall) | VESC 5 V servo rail (stock wiring practice) | flag: verify the VESC servo-rail current limit at bench before trusting stall headroom |
| **Pack B total** | **≈ 3.4 A** | ≈ 4.3 A + in-rush | — | sum of compute + LiDAR + margin |

| Battery quantity | Value | Method |
| --- | ---: | --- |
| Pack A (drive) | **Traxxas 2872X — 3S 11.1 V, 5 000 mAh, 25 C, 376 g** | vendor spec ([traxxas.com 2872X](https://traxxas.com/2872x-5000-mah-111-volt-3-cell-lipo-battery)); 25 C ⇒ 125 A pack capability ≥ 79 A peak ✓ |
| Pack B (compute) | **Traxxas 2872X** (same part — one SKU, packs interchangeable) | same |
| Drive runtime | 5 Ah / 10 A ≈ **30 min** (**ASSUMED average draw**) ≥ R-09's 20 min ✓ | capacity / assumed race-average |
| Compute runtime | 5 Ah / 3.4 A ≈ **86 min** ≥ R-09 ✓ | capacity / load list |

## 4. Wiring / Power-Distribution Topology

> Topology (diagram export to `docs/design/figures/` is a CAD-stage deliverable):
>
> **Pack A (3S)** →(main fuse + master cutoff)→ **VESC 6 MkVI** → Velineon 3500; VESC 5 V rail → 2075 servo; VESC USB/UART → Jetson (drive commands in, ERPM/IMU out).
> **Pack B (3S)** →(fuse)→ **Jetson Orin NX / J401** (direct, 9–19 V input); →(12 V buck/boost regulator, ≈ 0.05 kg ASSUMED)→ **Hokuyo UST-10LX**; LiDAR Ethernet → Jetson.
>
> Both packs get inline fuses and a single master cutoff reachable without lifting the deck (also what a race marshal expects at inspection).

## 5. Open Questions

> **RESOLVED:** 2D LiDAR (**Hokuyo UST-10LX**, 130 g datasheet, tip mass 0.175 kg, optical height ≈ 0.100 m); IMU (**VESC 6 MkVI onboard**, BNO055-class fallback flagged); odometry (**VESC ERPM** via `vesc_to_odom`); compute (**Jetson Orin NX 16 GB + Seeed J401**, 7–40 W); power architecture (**two Traxxas 2872X 3S packs**, 12 V regulator for the LiDAR only) with runtimes clearing R-09.
>
> **STILL OPEN (bench, not catalog):** measured Jetson system draw in the selected power mode; VESC servo-rail current limit vs 2075 stall; VESC-IMU vibration noise (gates the BNO055 fallback); wiring-diagram figure export (CAD stage).
