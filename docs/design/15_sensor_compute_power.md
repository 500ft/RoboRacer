# 15 — Sensor, Compute, and Power Package

**Status: TEMPLATE / TODO.** Depends on **13** (requirements) and **14** (platform/geometry). Shares the build with **16** (mechanical). **Design-only: no fabrication.** Dependency order: **13 → 14 → 15 → 16**.

**Hard contract:** the selected sensors must produce the topics the existing pipeline already consumes — **`/ego_racecar/odom`** and **`/drive`** — so the sim-validated identification/control stack runs unchanged. Optional enrichment topic for achieved steering / slip: `/f1tenth/internal_state` (see top-level `README.md`).

---

## 1. Sensor Suite → Topic Mapping (template)

> TEMPLATE. Choose parts; every row must terminate in a topic the pipeline reads.

| Sensor | Candidate part | Quantity it provides | ROS2 topic it feeds | Notes |
| --- | --- | --- | --- | --- |
| 2D LiDAR | `[confirm]` (e.g. Hokuyo / RPLIDAR class) | scan → localization → pose | `/scan` → localization → **`/ego_racecar/odom`** | Mass + mounting height feed item 16 mast load case |
| IMU | `[confirm]` | yaw rate, accel | fuses into odom / EKF | Section 5 EKF state uses yaw_rate; accel columns feed ride-quality metrics |
| Wheel / motor encoders | `[confirm]` | speed | fuses into **`/ego_racecar/odom`** | Provides `speed_mps` analog used throughout sim |
| Drive command sink | ESC + servo (item 14) | consumes commands | subscribes **`/drive`** | Closes the loop |

> The LiDAR mass and its mounted tip height/CG are an **input to item 16** (the mast FEA load case). Record them here once the part is chosen: LiDAR mass `[confirm]` kg, sensor optical-center height above deck `[confirm]` m.

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
| LiDAR | `[confirm]` A | — | `[confirm]` V | datasheet |
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

> TEMPLATE. List LiDAR/IMU/encoder/compute part numbers, LiDAR mass + optical-center height (needed by item 16), full load list currents, and battery config.
