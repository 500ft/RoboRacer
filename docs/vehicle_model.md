# Vehicle Model Derivation

## Purpose and Scope

This document defines the vehicle-model structure used for later F1TENTH Gym comparison and parameter-identification work. It is a derivation document only: it does not fit vehicle parameters, tune a controller, run a new simulation, or claim physical model fidelity.

The kinematic bicycle model describes planar pose evolution using position, heading, speed, acceleration, and steering angle. The dynamic bicycle model below is a lateral-yaw perturbation model at constant longitudinal speed. Its states are lateral velocity and yaw rate. It is not a full pose propagation model and does not estimate tire parameters.

## Coordinate Frames and Sign Convention

- Inertial/global frame: fixed map frame used for vehicle position \(X, Y\).
- Vehicle/body frame: frame attached to the vehicle center of gravity, with positive body \(x\) forward and positive body \(y\) to the left.
- Positive yaw angle \(\psi\): counterclockwise rotation from the global \(X\)-axis to the vehicle body \(x\)-axis.
- Positive yaw rate \(r = \dot{\psi}\): counterclockwise yaw.
- Positive lateral velocity \(v_y\): velocity in the positive body \(y\) direction.
- Positive steering angle \(\delta\): front wheel steered toward positive body \(y\).

For the dynamic model, the front and rear slip angles are defined as:

\[
\alpha_f = \delta - \frac{v_y + l_f r}{v_x}
\]

\[
\alpha_r = -\frac{v_y - l_r r}{v_x}
\]

The linear lateral tire-force convention is:

\[
F_{yf} = C_{\alpha f}\alpha_f
\]

\[
F_{yr} = C_{\alpha r}\alpha_r
\]

where \(C_{\alpha f} > 0\) and \(C_{\alpha r} > 0\). With this convention, a positive slip angle produces a positive lateral tire force.

## Notation and Parameters

| Symbol | Meaning | Units |
| --- | --- | --- |
| \(X, Y\) | vehicle center-of-gravity position in the global frame | m |
| \(\psi\) | vehicle yaw angle | rad |
| \(v\) | scalar speed in the kinematic model | m/s |
| \(v_x\) | body-frame longitudinal velocity | m/s |
| \(v_y\) | body-frame lateral velocity | m/s |
| \(r\) | yaw rate | rad/s |
| \(a\) | longitudinal acceleration input | m/s\(^2\) |
| \(\delta\) | front steering angle input | rad |
| \(m\) | vehicle mass | kg |
| \(I_z\) | yaw moment of inertia about the vertical axis | kg m\(^2\) |
| \(l_f\) | distance from center of gravity to front axle | m |
| \(l_r\) | distance from center of gravity to rear axle | m |
| \(L = l_f + l_r\) | wheelbase | m |
| \(C_{\alpha f}\) | front cornering stiffness | N/rad |
| \(C_{\alpha r}\) | rear cornering stiffness | N/rad |

## Modeling Assumptions

- Motion is planar.
- Roll, pitch, suspension, and load-transfer dynamics are ignored.
- Tire slip angles are small enough for linear tire forces.
- Tire saturation and combined slip are ignored.
- The lateral-yaw dynamic model is linearized at constant \(v_x = v_{x0} > 0\).
- Longitudinal acceleration is omitted from the lateral-yaw linear model because the operating point assumes constant longitudinal speed.

## Kinematic Bicycle Model

The kinematic model uses pose and scalar speed as the state:

\[
x_k =
\begin{bmatrix}
X \\
Y \\
\psi \\
v
\end{bmatrix}
\]

with input:

\[
u_k =
\begin{bmatrix}
a \\
\delta
\end{bmatrix}
\]

The slip-free kinematic bicycle equations are:

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

where:

\[
\beta = \tan^{-1}\left(\frac{l_r}{l_f + l_r}\tan\delta\right)
\]

This model is appropriate for low-slip pose propagation. It does not represent lateral tire-force dynamics.

## Dynamic Bicycle Model With Linear Tires

The dynamic bicycle model uses lateral velocity and yaw rate as the state:

\[
x_d =
\begin{bmatrix}
v_y \\
r
\end{bmatrix}
\]

with steering input:

\[
u_d = \delta
\]

The model is derived at constant longitudinal speed:

\[
v_x = v_{x0} > 0
\]

The lateral force balance is:

\[
m(\dot{v}_y + v_x r) = F_{yf} + F_{yr}
\]

The yaw moment balance is:

\[
I_z\dot{r} = l_f F_{yf} - l_r F_{yr}
\]

Substituting the stated slip-angle and tire-force convention gives:

\[
\dot{v}_y
=
-\frac{C_{\alpha f} + C_{\alpha r}}{m v_x}v_y
+
\left(
\frac{-l_f C_{\alpha f} + l_r C_{\alpha r}}{m v_x}
- v_x
\right)r
+
\frac{C_{\alpha f}}{m}\delta
\]

\[
\dot{r}
=
\frac{-l_f C_{\alpha f} + l_r C_{\alpha r}}{I_z v_x}v_y
-
\frac{l_f^2 C_{\alpha f} + l_r^2 C_{\alpha r}}{I_z v_x}r
+
\frac{l_f C_{\alpha f}}{I_z}\delta
\]

## Linearization and Continuous-Time State-Space Form

The lateral-yaw model is already linear in \(v_y\), \(r\), and \(\delta\) after assuming constant \(v_x = v_{x0}\) and linear tire forces. The continuous-time perturbation model is:

\[
\dot{x}_d = A x_d + B u_d
\]

with:

\[
A =
\begin{bmatrix}
-\frac{C_{\alpha f} + C_{\alpha r}}{m v_{x0}}
&
\frac{-l_f C_{\alpha f} + l_r C_{\alpha r}}{m v_{x0}} - v_{x0}
\\
\frac{-l_f C_{\alpha f} + l_r C_{\alpha r}}{I_z v_{x0}}
&
-\frac{l_f^2 C_{\alpha f} + l_r^2 C_{\alpha r}}{I_z v_{x0}}
\end{bmatrix}
\]

\[
B =
\begin{bmatrix}
\frac{C_{\alpha f}}{m}
\\
\frac{l_f C_{\alpha f}}{I_z}
\end{bmatrix}
\]

These signs follow directly from the slip-angle and tire-force convention stated above. A different slip-angle convention requires re-deriving the matrix signs.

## Controllability

For the two-state dynamic model, the controllability matrix is:

\[
\mathcal{C} =
\begin{bmatrix}
B & AB
\end{bmatrix}
\]

The model is controllable when:

\[
\operatorname{rank}(\mathcal{C}) = 2
\]

Equivalently, for this two-state system:

\[
\det(\mathcal{C})
=
\frac{C_{\alpha f}^2}
{I_z^2 m^2 v_{x0}}
\left[
I_z C_{\alpha r}(l_f + l_r)
- m C_{\alpha r}l_f l_r(l_f + l_r)
+ m^2 l_f^2 v_{x0}^2
\right]
\neq 0
\]

This rank condition assumes physically meaningful parameters:

\[
C_{\alpha f} > 0,\quad C_{\alpha r} > 0,\quad m > 0,\quad I_z > 0,\quad v_{x0} > 0
\]

and nondegenerate vehicle geometry with positive axle distances. Degenerate parameter choices, such as zero front cornering stiffness, or special parameter-speed cancellations that make \(\det(\mathcal{C}) = 0\), reduce rank and are outside a controllable operating-point claim.

## Observability

Use the measurement model:

\[
y =
\begin{bmatrix}
v_y \\
r
\end{bmatrix}
\]

Then:

\[
C = I_2,\qquad D = 0
\]

The observability matrix is:

\[
\mathcal{O} =
\begin{bmatrix}
C \\
CA
\end{bmatrix}
\]

Because \(C = I_2\), the two-state lateral-yaw model is trivially observable:

\[
\operatorname{rank}(\mathcal{O}) = 2
\]

This observability claim applies only to \(x_d = [v_y,\ r]^T\). It does not claim observability of a larger path-tracking or full-pose state from the same measurements.

## Discrete-Time Form

For a zero-order-hold discretization with steering held constant over one timestep, the discrete-time model is:

\[
x_d[k + 1] = A_d x_d[k] + B_d u_d[k]
\]

where:

\[
A_d = e^{A\Delta t}
\]

\[
B_d = \int_0^{\Delta t} e^{A\tau}B\,d\tau
\]

The zero-order-hold assumption matches the intended simulator interpretation that the steering command is held constant over the integration interval.

The RK4 convergence study in `reports/integrator_convergence.md` selected the numerical simulation timestep:

\[
\Delta t_{\mathrm{conv}} = 0.002~\mathrm{s}
\]

This timestep is a convergence-selected discretization choice. It is not a fitted vehicle parameter and does not prove physical model fidelity.

## What This Derivation Does Not Claim

This document derives model structure only. It does not identify:

\[
C_{\alpha f},\quad C_{\alpha r},\quad m,\quad I_z,\quad l_f,\quad l_r
\]

Later system-identification work must estimate or validate parameter values before using this model for quantitative prediction, LQR design, MPC design, or simulator-vs-derived-model claims.
