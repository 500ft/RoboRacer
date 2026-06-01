# Parameter Inventory

## Purpose

This document tracks parameter values, sources, and status before model-vs-Gym comparison or system identification. Values should not be silently guessed. Unknown, unfitted, or experiment-dependent values are marked explicitly.

## Vehicle and Simulator Parameters

| Parameter | Symbol / code key | Value | Units | Source | Status |
| --- | --- | ---: | --- | --- | --- |
| Friction coefficient | `mu` | 1.0489 | unitless | default `F110Env.params` in `gym/f110_gym/envs/f110_env.py` | known default |
| Front cornering stiffness coefficient | `C_Sf` | 4.718 | TBD | default `F110Env.params` | known simulator default; not fitted |
| Rear cornering stiffness coefficient | `C_Sr` | 5.4562 | TBD | default `F110Env.params` | known simulator default; not fitted |
| Front axle distance from CG | `lf` | 0.15875 | m | default `F110Env.params` | known default |
| Rear axle distance from CG | `lr` | 0.17145 | m | default `F110Env.params` | known default |
| Wheelbase | `lf + lr` | 0.33020 | m | derived from default `lf` and `lr` | known derived default |
| CG height | `h` | 0.074 | m | default `F110Env.params` | known default |
| Vehicle mass | `m` | 3.74 | kg | default `F110Env.params` | known default |
| Yaw inertia | `I` / \(I_z\) | 0.04712 | kg m^2 | default `F110Env.params` | known default |
| Minimum steering angle | `s_min` | -0.4189 | rad | default `F110Env.params` | known default |
| Maximum steering angle | `s_max` | 0.4189 | rad | default `F110Env.params` | known default |
| Minimum steering velocity | `sv_min` | -3.2 | rad/s | default `F110Env.params` | known default |
| Maximum steering velocity | `sv_max` | 3.2 | rad/s | default `F110Env.params` | known default |
| Switching velocity | `v_switch` | 7.319 | m/s | default `F110Env.params` | known default |
| Maximum acceleration | `a_max` | 9.51 | m/s^2 | default `F110Env.params` | known default |
| Minimum velocity | `v_min` | -5.0 | m/s | default `F110Env.params` | known default |
| Maximum velocity | `v_max` | 20.0 | m/s | default `F110Env.params` | known default |
| Vehicle width | `width` | 0.31 | m | default `F110Env.params` | known default |
| Vehicle length | `length` | 0.58 | m | default `F110Env.params` | known default |

## Gym Nonlinear Single-Track Oracle Parameters

These parameters are the known default values used by the local F1TENTH Gym nonlinear single-track model. They are treated as oracle/reference parameters for dynamic replay, not as identified values. The default values are defined in `F110Env.params` in `gym/f110_gym/envs/f110_env.py`; the consuming nonlinear model is `vehicle_dynamics_st` in `gym/f110_gym/envs/dynamic_models.py`.

| Parameter | Symbol / code key | Value | Units | Source | Status | Used for |
| --- | --- | ---: | --- | --- | --- | --- |
| Friction coefficient | `mu` | 1.0489 | unitless | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | tire-force limits |
| Front cornering stiffness coefficient | `C_Sf` | 4.718 | Gym coefficient | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | front lateral force |
| Rear cornering stiffness coefficient | `C_Sr` | 5.4562 | Gym coefficient | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | rear lateral force |
| Front axle distance from CG | `lf` | 0.15875 | m | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | slip-angle geometry |
| Rear axle distance from CG | `lr` | 0.17145 | m | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | slip-angle geometry |
| CG height | `h` | 0.074 | m | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | load-transfer term in dynamic model |
| Vehicle mass | `m` | 3.74 | kg | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | force balance |
| Yaw inertia | `I` / \(I_z\) | 0.04712 | kg m^2 | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default, not fitted | yaw dynamics |
| Steering angle minimum | `s_min` | -0.4189 | rad | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | steering constraint |
| Steering angle maximum | `s_max` | 0.4189 | rad | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | steering constraint |
| Steering velocity minimum | `sv_min` | -3.2 | rad/s | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | input constraint |
| Steering velocity maximum | `sv_max` | 3.2 | rad/s | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | input constraint |
| Velocity minimum | `v_min` | -5.0 | m/s | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | speed constraint |
| Velocity maximum | `v_max` | 20.0 | m/s | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | speed constraint |
| Acceleration maximum | `a_max` | 9.51 | m/s^2 | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | acceleration constraint |
| Switching velocity | `v_switch` | 7.319 | m/s | `gym/f110_gym/envs/f110_env.py` default `F110Env.params` | known default | acceleration constraint / model behavior |

### Nonlinear Model State and Input Convention

The nonlinear single-track model uses the state order:

\[
x =
\begin{bmatrix}
X & Y & \delta & v & \psi & r & \beta
\end{bmatrix}^T
\]

where \(X,Y\) are global position, \(\delta\) is steering angle, \(v\) is speed, \(\psi\) is yaw angle, \(r\) is yaw rate, and \(\beta\) is slip angle at the vehicle center.

The input order is:

\[
u =
\begin{bmatrix}
\dot{\delta} & a_x
\end{bmatrix}^T
\]

where \(\dot{\delta}\) is steering velocity and \(a_x\) is longitudinal acceleration. `vehicle_dynamics_st` applies steering, velocity, and acceleration constraints internally through `steering_constraint` and `accl_constraints`; replay code should call the same function rather than duplicating those limits externally.

## Experiment and Controller Parameters

| Parameter | Symbol / code key | Value | Units | Source | Status |
| --- | --- | ---: | --- | --- | --- |
| First-run timestep | `timestep` | 0.01 | s | `experiments/run_scripted_lap.py` environment creation | known first-run setting |
| RK4 convergence timestep | \(\Delta t_{\mathrm{conv}}\) | 0.0020 | s | `reports/integrator_convergence.md` | selected numerical timestep |
| First-run lookahead | `tlad` | 0.82461887897713965 | m | `WORK_PARAMS` in `experiments/run_scripted_lap.py` | known experiment setting |
| First-run velocity gain | `vgain` | 1.375 | unitless | `WORK_PARAMS` in `experiments/run_scripted_lap.py` | known experiment setting |
| First-run mass candidate | `mass` | 3.463388126201571 | kg | `WORK_PARAMS` in `experiments/run_scripted_lap.py` | recorded candidate; not passed to Gym in current first-lap run |
| First-run front axle candidate | `lf` | 0.15597534362552312 | m | `WORK_PARAMS` in `experiments/run_scripted_lap.py` | recorded candidate; not passed to Gym in current first-lap run |
| Config mass lower bound | `mass_min` | 3.0 | kg | `examples/config_example_map.yaml` | config bound |
| Config mass upper bound | `mass_max` | 4.0 | kg | `examples/config_example_map.yaml` | config bound |
| Config front axle lower bound | `lf_min` | 0.147 | m | `examples/config_example_map.yaml` | config bound |
| Config front axle upper bound | `lf_max` | 0.170 | m | `examples/config_example_map.yaml` | config bound |
| Config lookahead lower bound | `tlad_min` | 0.2 | m | `examples/config_example_map.yaml` | config bound |
| Config lookahead upper bound | `tlad_max` | 5.0 | m | `examples/config_example_map.yaml` | config bound |
| Config velocity-gain lower bound | `vgain_min` | 0.5 | unitless | `examples/config_example_map.yaml` | config bound |
| Config velocity-gain upper bound | `vgain_max` | 1.5 | unitless | `examples/config_example_map.yaml` | config bound |

## Model Parameters Not Yet Identified

| Parameter | Symbol | Value | Units | Source | Status |
| --- | --- | --- | --- | --- | --- |
| Front physical cornering stiffness | \(C_{\alpha f}\) | TBD | N/rad | future sysID | not fitted |
| Rear physical cornering stiffness | \(C_{\alpha r}\) | TBD | N/rad | future sysID | not fitted |
| Dynamic-model operating speed | \(v_{x0}\) | TBD | m/s | future operating-point selection | TBD |
| Kinematic replay initial state | \(X_0, Y_0, \psi_0, v_0\) | TBD | mixed | first row of selected Gym telemetry | TBD |

## Interpretation Rules

- Simulator defaults are valid references to what F1TENTH Gym uses when `params` is not supplied.
- Config bounds are not fitted parameter values.
- `C_Sf` and `C_Sr` are simulator parameters, but the derived model's physical cornering stiffnesses \(C_{\alpha f}\) and \(C_{\alpha r}\) remain not fitted.
- The selected `0.0020 s` timestep is a numerical convergence result, not a vehicle parameter and not evidence of physical model accuracy.
- Any parameter used in a future report must cite one of: simulator default, config bound, measured geometry, selected numerical setting, or fitted sysID result.
