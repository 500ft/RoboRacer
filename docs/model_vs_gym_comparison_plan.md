# Derived Model vs Gym Comparison Plan

## Objective

Test whether the derived kinematic bicycle model can replay the F1TENTH Gym trajectory when driven by the same logged control trace. This is the first model-structure validation step before sysID or dynamic-model comparison.

The first comparison is intentionally kinematic, not dynamic lateral-yaw. The kinematic model needs geometry and logged commands, while the dynamic lateral-yaw model requires cornering stiffness values that are not fitted yet.

## Inputs

| Input | Source | Use |
| --- | --- | --- |
| Gym trajectory | `runs/first_lap/telemetry.csv` | reference \(X, Y, \psi, v\) time history |
| Commanded speed | `command_speed_mps` | replay speed target or speed trace, depending on chosen replay mode |
| Commanded steering | `command_steer_rad` | kinematic steering input |
| Actual steering state | `steer_rad` | diagnostic alternative if command replay disagrees because of steering-rate limits |
| Initial state | first selected telemetry row | initialize \(X_0, Y_0, \psi_0, v_0\) |
| Geometry | `lf`, `lr` from `docs/parameter_inventory.md` | compute \(L = l_f + l_r\) |
| Timestep | telemetry `time_s` spacing | discrete propagation interval |

Default comparison case: use the RK4 first-lap telemetry and replay only the completed-lap segment. Euler collision telemetry remains a numerical-integrator diagnostic, not the primary model-validation target.

## Model Used

Use the kinematic bicycle model from `docs/vehicle_model.md`:

\[
x_k =
\begin{bmatrix}
X \\
Y \\
\psi \\
v
\end{bmatrix},
\qquad
u_k =
\begin{bmatrix}
a \\
\delta
\end{bmatrix}
\]

with:

\[
\dot{X} = v\cos(\psi + \beta)
\]

\[
\dot{Y} = v\sin(\psi + \beta)
\]

\[
\dot{\psi} = \frac{v}{l_r}\sin(\beta)
\]

\[
\dot{v} = a
\]

\[
\beta = \tan^{-1}\left(\frac{l_r}{l_f + l_r}\tan\delta\right)
\]

The first implementation should use logged telemetry to define the exact replay mode before comparing results. Recommended v1 replay mode: use logged `speed_mps` as the model speed state for pose propagation and logged `command_steer_rad` as steering input. A later variant may integrate \(\dot{v} = a\) using `accel_x_mps2`.

## Outputs and Metrics

The comparison should generate a report and plots only after the script exists in the next implementation step. The planned output directory is:

```text
runs/model_vs_gym_comparison/
reports/model_vs_gym_comparison.md
reports/figures/model_vs_gym_trajectory_error.png
reports/figures/model_vs_gym_state_errors.png
```

Compute sample-wise errors:

\[
e_X = X_{\mathrm{model}} - X_{\mathrm{gym}}
\]

\[
e_Y = Y_{\mathrm{model}} - Y_{\mathrm{gym}}
\]

\[
e_{\mathrm{pos}} = \sqrt{e_X^2 + e_Y^2}
\]

\[
e_\psi = \operatorname{wrap}(\psi_{\mathrm{model}} - \psi_{\mathrm{gym}})
\]

\[
e_v = v_{\mathrm{model}} - v_{\mathrm{gym}}
\]

Report at minimum:

- position RMSE
- maximum position error
- final position drift
- yaw RMSE
- maximum absolute yaw error
- speed RMSE when speed is integrated rather than directly replayed
- error vs speed, steering magnitude, and estimated lateral acceleration

## Acceptance Criteria

For v1, the comparison is a diagnostic gate, not a final vehicle-validation claim.

The kinematic replay is acceptable for proceeding to dynamic-model sysID if:

- low-speed / low-steering sections show bounded pose drift without an obvious sign or frame-convention error
- yaw error remains consistent with the steering convention in `docs/vehicle_model.md`
- the report identifies where error grows with speed, steering magnitude, or lateral acceleration
- the script reproduces the same metrics from the committed telemetry without manual intervention

Numerical thresholds should be set in the implementation PR after inspecting baseline error distributions, then recorded in the report before interpreting pass/fail results. Do not tune thresholds after seeing a desired conclusion.

## Outcome Interpretation

- If the kinematic model matches Gym within tolerance, treat the kinematic structure and replay mapping as validated enough to proceed to sysID for the dynamic model.
- If drift grows mainly with speed, steering magnitude, or lateral acceleration, treat it as expected evidence of missing tire dynamics. This is informative because the kinematic model intentionally ignores slip.
- If drift appears even at low speed and low steering, treat it as a likely derivation, sign-convention, replay, geometry, or telemetry-mapping bug that must be fixed before sysID.
- If command steering and actual steering produce materially different replay error, document the steering-rate-limit effect and choose the replay input explicitly.

## Known Limitations

- The kinematic model does not model lateral tire slip, load transfer, combined slip, actuator dynamics, or steering-rate limits.
- The first comparison does not estimate \(C_{\alpha f}\), \(C_{\alpha r}\), or \(I_z\).
- The first comparison uses existing first-lap telemetry rather than a new excitation designed for identification.
- Strong agreement over one lap does not prove physical model fidelity outside this operating envelope.

## Not In Scope

- Dynamic lateral-yaw model validation
- System identification
- LQR or MPC design
- ROS integration
- New controller tuning
- New simulation sweeps
- Additional plot polishing beyond the future comparison report outputs
