# Vehicle Model Derivation

## Purpose

This document defines the vehicle model basis for later Gym-vs-derived-model comparison and parameter-identification work. It is not a fitted model result yet.

## Coordinate Frames and Notation

- Inertial/global frame: fixed map frame used by F1TENTH Gym for position.
- Vehicle/body frame: frame attached to the vehicle, with the x-axis forward and y-axis lateral.
- \(x, y\): vehicle position in the global frame.
- \(\psi\): yaw angle from the global x-axis to the vehicle heading.
- \(v_x\): longitudinal velocity in the vehicle body frame.
- \(v_y\): lateral velocity in the vehicle body frame.
- \(r = \dot{\psi}\): yaw rate.
- \(\delta\): front steering angle input.
- \(a\): longitudinal acceleration input, or an equivalent speed-tracking command in simulator experiments.

## Parameters

- \(m\): vehicle mass.
- \(I_z\): yaw moment of inertia about the vertical axis.
- \(l_f\): distance from center of gravity to front axle.
- \(l_r\): distance from center of gravity to rear axle.
- \(L = l_f + l_r\): wheelbase.
- \(C_{\alpha f}\): front cornering stiffness.
- \(C_{\alpha r}\): rear cornering stiffness.

## Assumptions

- Motion is planar.
- Roll and pitch dynamics are ignored.
- Load transfer is ignored in the first model.
- Slip angles are small for the linear dynamic bicycle model.
- \(v_x\) is constant or slowly varying for linearization.
- Tire saturation is ignored in the first linear model.

## Kinematic Bicycle Model

Use state:

\[
\mathbf{x}
=
\begin{bmatrix}
x \\
y \\
\psi \\
v
\end{bmatrix}
\]

Use input:

\[
\mathbf{u}
=
\begin{bmatrix}
a \\
\delta
\end{bmatrix}
\]

The kinematic bicycle equations are:

\[
\dot{x} = v\cos(\psi + \beta)
\]

\[
\dot{y} = v\sin(\psi + \beta)
\]

\[
\dot{\psi} = \frac{v}{l_r}\sin(\beta)
\]

\[
\dot{v} = a
\]

with:

\[
\beta = \tan^{-1}\left(\frac{l_r}{l_f + l_r}\tan\delta\right)
\]

This model is useful for low-slip trajectory propagation and as the first derived-model comparison against Gym.

## Dynamic Bicycle Model With Linear Tires

At fixed \(v_x\), use lateral-yaw state:

\[
\mathbf{x}
=
\begin{bmatrix}
v_y \\
r
\end{bmatrix}
\]

with steering input \(\delta\).

Slip angles:

\[
\alpha_f
=
\delta
-
\frac{v_y + l_f r}{v_x}
\]

\[
\alpha_r
=
-
\frac{v_y - l_r r}{v_x}
\]

Linear tire forces:

\[
F_{yf} = C_{\alpha f}\alpha_f
\]

\[
F_{yr} = C_{\alpha r}\alpha_r
\]

Lateral dynamics:

\[
m(\dot{v}_y + v_x r)
=
F_{yf} + F_{yr}
\]

Yaw dynamics:

\[
I_z\dot{r}
=
l_f F_{yf} - l_r F_{yr}
\]

Substituting the linear tire forces gives:

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

State-space form:

\[
\dot{\mathbf{x}} = A\mathbf{x} + B\delta
\]

where:

\[
A =
\begin{bmatrix}
-\frac{C_{\alpha f} + C_{\alpha r}}{m v_x}
&
\frac{-l_f C_{\alpha f} + l_r C_{\alpha r}}{m v_x} - v_x
\\
\frac{-l_f C_{\alpha f} + l_r C_{\alpha r}}{I_z v_x}
&
-\frac{l_f^2 C_{\alpha f} + l_r^2 C_{\alpha r}}{I_z v_x}
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

## Discrete-Time Form

The continuous-time model will be discretized using the RK4 timestep selected by the integrator convergence study.

Until that experiment is complete:

\[
\Delta t = \Delta t_{\mathrm{conv}}
\]

where \(\Delta t_{\mathrm{conv}}\) is selected in `reports/integrator_convergence.md` using the predeclared pairwise refinement-change criterion.

## Future SysID Use

The later sysID experiment will excite the simulator using prescribed steering inputs, record response data, and fit a subset of the dynamic bicycle model parameters. Candidate fitted parameters include:

\[
C_{\alpha f},\quad C_{\alpha r},\quad I_z
\]

This document defines the model basis only. It does not claim fitted parameter values yet.
