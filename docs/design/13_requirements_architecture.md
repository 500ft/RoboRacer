# 13 — Vehicle Requirements and System Architecture

**Status: TEMPLATE / TODO.** This is the first artifact of the design-only Vehicle Design Package. **Design-only: no fabrication.** Complete this file **before** 14/15/16 — part selection and FEA depend on the requirements and architecture fixed here. Dependency order: **13 → 14 → 15 → 16**.

**Traceability rule:** every requirement that has a number must trace back to either (a) the validated simulation envelope (experiments 4-6, `reports/`) or (b) an explicitly stated external constraint. Mark anything not yet pinned `[confirm]`.

---

## 1. Purpose and Scope

> TEMPLATE. State what the car must do: a 1/10-scale autonomous racer that runs the **existing** ROS2 sysID / identification / control stack unchanged, so the simulation results in this repo transfer to a real platform. Design-only deliverable; physical build + bring-up is the deferred milestone (item 17).

## 2. Requirements Table (skeleton)

> TEMPLATE. Fill every row. "Source / trace" must point at a file or a stated constraint; replace `[confirm]` with a real value from the run outputs or a datasheet.

| ID | Requirement | Target / range | Source / trace | Verification | Status |
| --- | --- | --- | --- | --- | --- |
| R-01 | Top speed | `[confirm]` m/s — must cover the sim operating speed | LQR operating speed **8.33095 m/s** (`reports/lqr_controller.md`); max speed per `summarize_run` `max_speed_mps` after rerun | Bench + telemetry | TODO |
| R-02 | Steering angle range | ≥ max command steer used in sim | `max_abs_command_steer_rad` ≈ 0.200 rad (pure pursuit, `reports/controller_comparison.md`); saturation case 0.419 rad (`reports/failure_mode_fmea.md`) | Servo spec + bench sweep | TODO |
| R-03 | Steering rate | ≥ controller steering-rate limit | Steering-rate constraint pulled from shared model params (`reports/mpc_controller.md`); extract exact value from `gym/roboracer` model params `[confirm]` | Servo slew bench | TODO |
| R-04 | Wheelbase (geometry lock) | **0.3302 m** | `WHEELBASE_M = 0.15875 + 0.17145` in `gym/roboracer/closed_loop.py` | CAD + measured | TODO |
| R-05 | Longitudinal accel envelope | `[confirm]` m/s² | `max_abs_long_accel_mps2` from `summarize_run` after `run_all.sh` rerun (see item 16 note) | Telemetry | TODO |
| R-06 | Lateral accel envelope | `[confirm]` m/s² | `max_abs_lat_accel_mps2` from `summarize_run` after rerun — **governs the item-16 LiDAR-mast load case** | Telemetry | TODO |
| R-07 | Sensor payload | LiDAR + IMU + wheel/motor encoders | item 15; must emit `/ego_racecar/odom`, `/drive` | Topic echo | TODO |
| R-08 | Onboard compute | Real-time at 100 Hz; headroom over MPC p95 | MPC **p95 1.32644 ms** (`reports/mpc_controller.md`) | Loop-timing bench | TODO |
| R-09 | Endurance / runtime | `[confirm]` min at race power | item 15 power budget | Battery draw test | TODO |
| R-10 | Scale / class | 1/10 RC class | item 14 platform decision | — | TODO |
| R-11 | Mass budget (total + per subsystem) | `[confirm]` kg | item 16 mass & CG budget | Scale | TODO |
| R-12 | Update-rate guarantee | 100 Hz control loop, zero-order hold | All controller reports (`dt = 0.002 s`, 100 Hz ZOH) | Loop-timing bench | TODO |

## 3. System Block Diagram (description)

> TEMPLATE. Replace with an actual diagram (e.g. Excalidraw export to `docs/design/figures/`). Describe the chain:

```
[ LiDAR ]        [ IMU ]        [ wheel/motor encoders ]
     \              |                    /
      \             |                   /
        ----> [ Onboard compute (Jetson-class) ] ----> ROS2 stack
                       |  publishes /ego_racecar/odom
                       |  subscribes /drive
                       v
              [ ESC + drive motor ]     [ steering servo ]
                       \                       /
                        ----> [ Chassis / drivetrain ] ----
                                       ^
                              [ Battery + power distribution ]  (item 15)
```

Sensing → Compute → Actuation → Power. The compute node must run the existing identification/control pipeline unmodified; the only contract with the rest of the repo is the topic interface in Section 4.

## 4. Interface Contract to Existing Software

> TEMPLATE. The architecture must preserve the topics the current pipeline already consumes/produces so the sim-validated stack runs unchanged on a future build:
- Odometry/state out: **`/ego_racecar/odom`**
- Drive command in: **`/drive`**
- Optional enrichment (achieved steering / slip): `/f1tenth/internal_state` (see top-level `README.md`).

## 5. Open Questions / `[confirm]`

> TEMPLATE. List every `[confirm]` above plus: target race environment, budget ceiling, and whether the build milestone (item 17) is committed.
