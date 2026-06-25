# 15 — Sensor, Compute, and Power Package

**Status: IN PROGRESS — LiDAR + mast tip mass LOCKED; IMU / compute / power still TEMPLATE.** Depends on **13** (requirements) and **14** (platform/geometry). Shares the build with **16** (mechanical). **Design-only: no fabrication.** Dependency order: **13 → 14 → 15 → 16**.

**Hard contract:** the selected sensors must produce the topics the existing pipeline already consumes — **`/ego_racecar/odom`** and **`/drive`** — so the sim-validated identification/control stack runs unchanged. Optional enrichment topic for achieved steering / slip: `/f1tenth/internal_state` (see top-level `README.md`).

---

## 1. Sensor Suite → Topic Mapping

> **LiDAR row LOCKED** (see §1.1). IMU / encoder rows still TEMPLATE — choose parts; every row must terminate in a topic the pipeline reads.

| Sensor | Part | Quantity it provides | ROS2 topic it feeds | Notes |
| --- | --- | --- | --- | --- |
| 2D LiDAR | **Hokuyo UST-10LX** (LOCKED) | scan → localization → pose | `/scan` (`sensor_msgs/LaserScan`) → localization (e.g. particle filter) → **`/ego_racecar/odom`** | **Mass 130 g [datasheet]** → firmed mast tip mass 0.175 kg, item 16 §1.1 / §3 |
| IMU | `[confirm]` | yaw rate, accel | fuses into odom / EKF | Section 5 EKF state uses yaw_rate; accel columns feed ride-quality metrics |
| Wheel / motor encoders | `[confirm]` | speed | fuses into **`/ego_racecar/odom`** | Provides `speed_mps` analog used throughout sim |
| Drive command sink | ESC + servo (item 14) | consumes commands | subscribes **`/drive`** | Closes the loop |

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

## 2. Compute Sizing (template)

> TEMPLATE. Size against R-08 / R-12: the controller loop runs at **100 Hz** (10 ms period) and the heaviest measured controller is MPC at **p95 solve time 1.32644 ms**, mean 1.0739 ms, with rare spikes to ~36.8 ms (`reports/mpc_controller.md`). Compute must hold the 100 Hz loop with comfortable headroom and tolerate the spike behavior (watchdog / dedicated QP solver noted as deployment mitigation).

| Quantity | Value | Source |
| --- | ---: | --- |
| Control loop rate | 100 Hz (10 ms budget) | all controller reports |
| MPC p95 solve time | 1.32644 ms | `reports/mpc_controller.md` |
| MPC mean solve time | 1.0739 ms | `reports/mpc_controller.md` |
| MPC max solve time (spike) | ~36.8073 ms | `reports/mpc_controller.md` — exceeds one 10 ms period |
| Candidate compute | Jetson-class `[confirm exact module]` | R-08 |
| Headroom target | `[confirm]` (e.g. p95 < 25% of 10 ms budget) | design choice |

> Honest note: the p95 fits 100 Hz on the dev machine, but the max solve time already breaks a single control period. A deployment build should use a dedicated QP solver, watchdog timing, or a shorter horizon (per the MPC report). Compute selection should not assume the SciPy/SLSQP timing is the final timing.

## 3. Power Budget (template)

> TEMPLATE. Build the load list, then size the battery for R-09 runtime.

| Load | Nominal current | Peak current | Voltage | Source |
| --- | --- | --- | --- | --- |
| Drive motor + ESC | `[confirm]` A | `[confirm]` A | `[confirm]` V | item 14 sizing |
| Compute (Jetson-class) | `[confirm]` A | `[confirm]` A | `[confirm]` V | datasheet |
| LiDAR (Hokuyo UST-10LX, LOCKED) | **0.30 A** (≈ 3.6 W) | 0.7 A in-rush | **12 V** | Hokuyo UST-10LX datasheet |
| IMU + encoders + logic | `[confirm]` A | — | `[confirm]` V | datasheet |
| **Total** | `[confirm]` | `[confirm]` | — | sum |

| Battery quantity | Value | Method |
| --- | ---: | --- |
| Pack chemistry / config | `[confirm]` (e.g. 3S/4S LiPo) | choice |
| Pack capacity | `[confirm]` mAh | from total current × R-09 runtime |
| Estimated runtime | `[confirm]` min | capacity / average draw |

## 4. Wiring / Power-Distribution Diagram

> TEMPLATE. Replace with a diagram (export to `docs/design/figures/`): battery → power distribution (regulators for compute / logic / sensors, direct high-current path to ESC) → loads. Note fusing and a master cutoff.

## 5. Open Questions / `[confirm]`

> **RESOLVED:** 2D LiDAR part number (**Hokuyo UST-10LX**), LiDAR mass (**130 g, datasheet**), firmed mast tip mass (**0.175 kg**), and optical-center height (**≈ 0.100 m**, = recommended mast length) — all locked and fed to item 16. LiDAR power (12 V, 0.30 A / ≈ 3.6 W) recorded in §3.
>
> **STILL OPEN (`[confirm]`):** IMU and wheel/motor-encoder part numbers; compute module (Jetson-class) selection and its current draw; full load-list currents for drive motor + ESC and logic rail; battery chemistry/config, capacity, and runtime sizing against R-09.
