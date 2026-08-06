# Dynamic Parameter Identification

## Objective

Estimate nonlinear single-track coefficients `C_Sf` and `C_Sr` from ROS-backed enriched Gym bridge telemetry with native achieved steering, then require an independent held-out replay to pass.

## Method

The fitter uses the logged internal states and achieved/reconstructed inputs from `evidence/item11/telemetry/enriched_bridge.csv`. Only intervals starting at `speed_mps >= 0.75` are used, excluding Gym's low-speed kinematic fallback. The first 70% of usable intervals are training data; the final 30% are held out chronologically.

For each training interval, the measured state at row `k` is propagated one RK4 step through `vehicle_dynamics_st`. The achieved finite-difference inputs stored on row `k+1` are applied over interval `k -> k+1`. Bounded nonlinear least squares minimizes normalized yaw-rate and slip-angle one-step residuals. The held-out rollout starts once from the measured split state and then propagates recursively without state resets.

## Identified Parameters

| Parameter | Identified | Known Gym oracle | Relative error |
| --- | ---: | ---: | ---: |
| `C_Sf` | 4.718000001 | 4.718000000 | 2.736e-10 |
| `C_Sr` | 5.456200007 | 5.456200000 | 1.249e-09 |

The oracle comparison is a controlled simulator-recovery check, not physical-vehicle validation.

## Held-Out Validation

Validation status: **passed**

| Metric | Value |
| --- | ---: |
| Held-out rollout yaw-rate RMSE | 2.986152e-10 rad/s |
| Held-out rollout yaw-rate NRMSE | 5.271253e-10 of measured range |
| Held-out rollout yaw-rate VAF | 100.000000000% |
| Held-out rollout slip-angle RMSE | 2.851398e-10 rad |
| Held-out rollout slip-angle NRMSE | 1.015066e-08 of measured range |
| Held-out rollout slip-angle VAF | 100.000000000% |
| Held-out rollout yaw RMSE | 2.857363e-10 rad |
| Held-out rollout position RMSE | 5.998214e-10 m |
| Normalized residual Jacobian condition number | 1.339308 |
| Raw physical Jacobian condition number | 2.949016 |
| `C_Sf`-`C_Sr` parameter correlation | 0.090755 |
| Sensitivity-column cosine | -0.090755 |

Acceptance checks:

| Check | Pass |
| --- | --- |
| oracle_recovery | True |
| heldout_yaw_rate | True |
| heldout_slip_angle | True |
| heldout_yaw | True |
| heldout_normalized_fit | True |
| heldout_variance_accounted_for | True |
| identifiability | True |
| parameter_correlation | True |

## Figures

![Dynamic parameter fit](figures/enriched_ros_fit.png)

![Held-out residuals](figures/enriched_ros_residuals.png)

## Interpretation

The held-out validation demonstrates that the identified coefficients reproduce the nonlinear lateral-yaw state evolution for a frequency regime not used during fitting. The low Jacobian condition number indicates that the selected excitation distinguishes the two fitted coefficients for this controlled dataset.

This result validates the identification pipeline for the stated source. It does not establish that the same coefficients apply to a physical RoboRacer vehicle.

## Scope Gate

No LQR, MPC, or controller tuning is performed here. Controller design remains blocked until an identified model passes held-out validation. This Gym identification passes that gate for simulator work; physical-vehicle controller work still requires identification and held-out validation from real RoboRacer data.
