# 13 — Vehicle Requirements and System Architecture

**Status: REQUIREMENTS LOCKED (2026-07-07).** Numeric targets are filled from the validated simulation envelope and the official RoboRacer competition rules; the platform/part decisions they feed are locked in items 14–15. **Design-only: no fabrication.** Dependency order: **13 → 14 → 15 → 16**.

**Competition context (new external constraint set):** the design now targets **RoboRacer restricted-class legality** in addition to reproducing the sim geometry. Rules source: the official ruleset ([github.com/f1tenth/roboracer_rules](https://github.com/f1tenth/roboracer_rules), Oct-2024 revision) — see §2.1. Restricted class is a test of algorithms: hardware must match the baseline BOM profile, all computation onboard, no unauthorized mechanical advantage (violations → disqualification or reclassification to Open Class at inspection).

**Traceability rule:** every requirement that has a number must trace back to either (a) the validated simulation envelope (experiments 4-6, `reports/`) or (b) an explicitly stated external constraint. Mark anything not yet pinned `[confirm]`.

---

## 1. Purpose and Scope

A 1/10-scale autonomous racer that (a) runs the **existing** ROS2 sysID / identification / control stack unchanged (topic contract in §4), so the simulation results in this repo transfer to a real platform, and (b) is **legal in the RoboRacer restricted class** (§2.1), so the same vehicle can enter official competition without hardware rework. Design-only deliverable; physical build + bring-up is the deferred milestone (item 17).

## 2. Requirements Table

> Numeric targets trace to (a) the validated simulation envelope (`reports/`, `runs/`, `gym/roboracer/dynamics.py`) or (b) the competition ruleset (§2.1). Values marked **ASSUMED** are design choices, stated as such.

| ID | Requirement | Target / range | Source / trace | Verification | Status |
| --- | --- | --- | --- | --- | --- |
| R-01 | Top speed | **≥ 8.33 m/s** (sim operating speed); platform capability 26.8+ m/s (60+ mph) is a ceiling, not a target | LQR operating speed **8.33095 m/s** (`reports/lqr_controller.md`); Slash 4x4 VXL vendor spec (item 14 §3) | Bench + telemetry | **SET** |
| R-02 | Steering angle range | **≥ ±0.4189 rad** at the road wheel | model `s_max = 0.4189` (`gym/roboracer/dynamics.py`); saturation case 0.419 rad (`reports/failure_mode_fmea.md`); nominal max command ≈ 0.200 rad (`reports/controller_comparison.md`) | Servo spec + bench sweep | **SET** |
| R-03 | Steering rate | **≥ 3.2 rad/s** at the road wheel | model `sv_max = 3.2` (`gym/roboracer/dynamics.py`) — the constraint enforced by the MPC (`reports/mpc_controller.md`) | Servo slew bench (item 14 §4: stock servo gives ≈ 6.5 rad/s, 2.0×) | **SET** |
| R-04 | Wheelbase (geometry lock) | **0.3302 m** target; chosen platform is 0.324 m (**−1.9% deviation, documented — item 14 §2**) | `WHEELBASE_M = 0.15875 + 0.17145` in `gym/roboracer/closed_loop.py` | CAD + measured | **SET (with deviation)** |
| R-05 | Longitudinal accel envelope | **9.51 m/s²** | `max_abs_long_accel_mps2 = 9.51` on the clean baseline lap (`runs/ride_quality_baseline/summary.json`); equals the model accel cap `a_max = 9.51` (`dynamics.py`) — the lap saturates the cap | Telemetry | **SET** |
| R-06 | Lateral accel envelope | **19.4 m/s²** (≈ 2.0 g) | `max_abs_lat_accel_mps2`, clean baseline lap (`runs/ride_quality_baseline/summary.json`) — **governs the item-16 LiDAR-mast load case** | Telemetry | **SET** |
| R-07 | Sensor payload | LiDAR + IMU + wheel/motor odometry | item 15 §1 (all rows now locked); must emit `/ego_racecar/odom`, `/drive` | Topic echo | **SET** |
| R-08 | Onboard compute | Real-time at 100 Hz; headroom target p95 ≤ 25% of the 10 ms budget | MPC **p95 1.32644 ms** (`reports/mpc_controller.md`); onboard-only is also a **rule** (§2.1 R-15) | Loop-timing bench | **SET** |
| R-09 | Endurance / runtime | **≥ 20 min** per battery set at race power (**ASSUMED** design target — typical race-session length) | item 15 §3 power budget (predicts ≥ 30 min drive, ≈ 86 min compute) | Battery draw test | **SET (ASSUMED)** |
| R-10 | Scale / class | 1/10 RC class, restricted-class-legal | item 14 §1 platform decision; §2.1 | Inspection checklist | **SET** |
| R-11 | Mass budget (total + per subsystem) | **≤ 4.5 kg** ready-to-race; current bottom-up estimate 4.42 kg (item 16 §2). Sim identified-model mass is `m = 3.74 kg` (`dynamics.py`) — the **+18% deviation is flagged**, see item 14 §5 | item 16 §2 mass & CG budget | Scale | **SET (deviation flagged)** |
| R-12 | Update-rate guarantee | 100 Hz control loop, zero-order hold | All controller reports (`dt = 0.002 s`, 100 Hz ZOH) | Loop-timing bench | **SET** |

### 2.1 Competition constraints (RoboRacer restricted class)

> Source: official ruleset, [github.com/f1tenth/roboracer_rules](https://github.com/f1tenth/roboracer_rules) (Oct-2024 revision). These are **external constraints** — rows below are requirements on this design, with compliance status of the item-14/15 picks.

| ID | Rule | Constraint | Our compliance | Status |
| --- | --- | --- | --- | --- |
| R-13 | Baseline chassis | 1:10 Traxxas Slash 4x4 (TRA74054, TRA6804R, TRA68086) or alternative within the dimensional window: width 238–341 mm, length 454–654 mm; 4WD or 2WD | **TRA68086-4** selected (item 14 §1): width 296 mm ✓, length 568 mm ✓ | **PASS** |
| R-14 | Transponder bay | Designated spot on the **front half** of the car, **≥ 8 × 12 cm**, easily accessible, **nothing on top of it** | Reserved keep-out zone in the deck layout — **direct input to the item-16 deck CAD** (§ deck layout) | **DESIGN RULE → CAD** |
| R-15 | Onboard computation | All path planning and sensor processing onboard; no remote-server offloading | Jetson Orin NX onboard (item 15 §2); Wi-Fi used for dev/telemetry only | **PASS** |
| R-16 | Drive power | Drive motor powered by at most **one battery rated ≤ 4S** (capacity unlimited; extra batteries allowed for other loads) | Drive = one 3S pack; separate 3S pack for compute (item 15 §3) | **PASS** |
| R-17 | Motor | **Single** brushless DC motor driving the wheels; spec ceiling = Velineon 3500 or lower-rated equivalent | Stock **Velineon 3500** — the ceiling part itself (item 14 §3) | **PASS** |
| R-18 | LiDAR | Spec ceiling: Hokuyo UST-10LX baseline per the Oct-2024 rules text (repo ruleset states UST-30LX as ceiling — either way our part is at/below it) | **Hokuyo UST-10LX** (item 15 §1.1, LOCKED) | **PASS** |
| R-19 | Prohibited equipment | No indoor-GPS sensors; no equipment manipulating the race environment or providing external track information | None used | **PASS** |
| R-20 | Head-to-head addenda | Soft bumpers ≥ 5 cm of soft material front + rear; LiDAR-perceivable marker ≥ 12 × 12 cm at every horizontal plane 10–30 cm above ground | Bumper + marker are **CAD work items** (item 16 deck/bumper layout), head-to-head events only | **DESIGN RULE → CAD** |

> **Inspection note:** every vehicle passes a physical inspection before competing; non-conforming hardware → disqualification or Open Class. The restricted class is a test of algorithms — unauthorized hardware for mechanical advantage is forbidden. This is *favorable* to this project: the validated sim/controls stack is the differentiator the class rewards.

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

## 5. Open Questions

> **RESOLVED (2026-07-07):** all numeric requirement targets (R-01…R-12) are set from the sim envelope + `dynamics.py` model params; competition constraints captured as R-13…R-20 from the official ruleset.
>
> **STILL OPEN:** target race environment (indoor track assumed — matches the UST-10LX 10 m range rationale); budget ceiling for the build milestone; whether item 17 (physical build) is committed — currently a deferred milestone. R-14/R-20 are geometry rules that close in the item-16 CAD, not here.
