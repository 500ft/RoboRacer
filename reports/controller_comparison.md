# Controller Comparison

## Objective

Compare tuned pure pursuit, LQR, and MPC under the same map, integration timestep, and 100 Hz controller update rate.

## Results

| controller | case | completed_lap | collision | lap_time_s | rms_cte_m | max_abs_cte_m | steering_effort_rad | mean_abs_command_steer_rad | max_abs_command_steer_rad | mpc_p95_solve_time_s | mpc_meets_100hz_budget | mpc_meets_50hz_budget |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pure_pursuit | selected_baseline | True | False | 38.042 | 0.157892 | 0.403062 | 8.19853 | 0.0399022 | 0.200099 |  |  |  |
| lqr | nominal | True | False | 38.064 | 0.178628 | 0.497708 | 8.98777 | 0.0425835 | 0.220906 |  |  |  |
| mpc | nominal | True | False | 37.86 | 0.169238 | 0.47665 | 8.6771 | 0.0407755 | 0.213303 | 0.00132644 | True | True |

## Notes

- Pure pursuit is the selected baseline from `reports/pure_pursuit_sweep.md`.
- LQR is the nominal case from `reports/lqr_controller.md`.
- MPC is the nominal constrained SLSQP controller from `reports/mpc_controller.md`.
- MPC runtime fields are only meaningful for the MPC row.
