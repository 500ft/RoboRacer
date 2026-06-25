# FEA Toolchain Setup — LiDAR Mast (item 16)

**Status: WORKING / TESTED.** The full mesh → solve → modal pipeline ran on this
machine on 2026-06-25 and validated the hand calc (see results at the bottom and
in `runs/mast_fea/fea_summary.txt`). This file records the exact, tested commands
to stand the toolchain up from scratch and the workflow the pipeline uses.

The pipeline is `experiments/mast_fea.py` (geometry → mesh → static + modal →
compare-to-hand-calc). It validates `experiments/mast_hand_calc.py`.

---

## Toolchain (what actually ran)

| Role | Tool | Version | Where it lives |
| --- | --- | --- | --- |
| Mesher (Python API) | **gmsh** | 4.15.2 | conda **base** env (`~/ENTER`) |
| Solver | **CalculiX `ccx`** | 2.23 | conda env **`fea`** (`~/ENTER/envs/fea/bin/ccx`) |
| Orchestration | conda | 24.11.3 | — |

The mesher and the solver live in **two different conda environments** on this
machine (gmsh in `base`, ccx in `fea`). `mast_fea.py` therefore meshes with gmsh
in-process (run it from the `base`/gmsh env) and **shells out** to the `ccx`
binary. The binary path is auto-detected; override it with the `CCX` env var.

> Why two envs: `gmsh` installs cleanly as a Python wheel into the existing
> `base` env; `calculix` is a compiled binary distributed via conda-forge and is
> cleanest in its own env so it cannot perturb the simulation/ROS envs.

---

## Exact stand-up commands (tested, copy-paste)

These are the commands that were actually run to enable the path. On a fresh
machine with Miniconda/Anaconda already installed:

```bash
# 1) Mesher: gmsh Python API into the env you run the pipeline from (here: base).
pip install gmsh                      # -> gmsh 4.15.2 (macosx_arm64 wheel, ~36 MB)

# 2) Solver: CalculiX ccx into a dedicated conda env from conda-forge.
conda create -y -n fea -c conda-forge calculix     # -> calculix 2.23

# 3) Sanity-check both are present.
python -c "import gmsh; gmsh.initialize(); print('gmsh', gmsh.option.getString('General.Version')); gmsh.finalize()"
~/ENTER/envs/fea/bin/ccx -v          # -> 'This is Version 2.23'
```

Notes / gotchas that were hit and resolved:

- **conda-forge has `calculix` for osx-arm64** (`calculix 2.21 … 2.23`); no
  Docker image is needed. `brew` does **not** have a `calculix-ccx` formula.
- **gmsh ↔ CalculiX C3D10 node order differs.** gmsh's second-order tet
  (element type 11) lists the 6 mid-edge nodes in the order
  `(0-1, 1-2, 2-0, 0-3, 2-3, 1-3)`, but CalculiX C3D10 expects the **last two
  edge nodes swapped**: `(0-1, 1-2, 2-0, 0-3, 1-3, 2-3)`. Feeding gmsh order
  straight into ccx triggers a flood of `*ERROR in e_c3d: nonpositive jacobian`.
  `mast_fea.py` applies the permutation `(0,1,2,3,4,5,6,7,9,8)` in the `.inp`
  writer (`_GMSH_TO_CCX_C3D10`). This is the single most important integration
  detail.
- **Point load → singularity.** A transverse load on a single tip node produces
  a ~1.2 GPa nodal spike that is a mesh artifact, not real stress. The pipeline
  distributes the crash force over **all tip-ring nodes** and compares stress on
  a **mid-span gauge ring** (away from the fixed root and the load), plus the
  global tip deflection — those are the fair beam-theory comparisons.

### Running the pipeline

```bash
# From the repo root, with the gmsh (base) env active:
conda activate base                  # gmsh lives here
export CCX=~/ENTER/envs/fea/bin/ccx  # optional; auto-detected if omitted
python experiments/mast_fea.py
```

Outputs land in `runs/mast_fea/` (`fea_summary.txt`, `*.dat`, `*.ccx.log` are
kept in git; the multi-MB `*.inp` / `*.frd` mesh+result binaries are git-ignored
and regenerable).

---

## Workflow the pipeline implements (mesh → ccx → static + modal)

1. **Geometry (gmsh OCC):** hollow tube = outer cylinder − inner cylinder, axis
   +z, root plane at z=0, free tip at z=L. Recommended geometry: L=100 mm,
   OD=20 mm, wall t=1.5 mm, 6061-T6 (E=68.9 GPa, ν=0.33, ρ=2700).
2. **Mesh:** quadratic tetrahedra (C3D10), element size ≈ 1.2 mm
   (≈ OD/16, resolves the 1.5 mm wall). ~58 k nodes / ~29 k elements.
3. **Static deck (`mast_static.inp`):** root `*BOUNDARY NROOT,1,3` (ENCASTRE);
   `*STATIC`; `*CLOAD` of the crash design force F = 50 g × 0.20 kg × SF 1.5 =
   147.2 N distributed over the tip-ring node set. Requests `*EL FILE S` /
   `*NODE FILE U`. → max von Mises (gauge + global) and tip deflection.
4. **Modal deck (`mast_modal.inp`):** root ENCASTRE + a CalculiX `*ELEMENT,
   TYPE=MASS` carrying the 0.20 kg LiDAR tip mass at the tip-center node;
   `*FREQUENCY` step extracting 6 modes → first natural frequency.
5. **Compare:** parse `.dat` (eigenfreqs, tip displacement) and `.frd` (nodal
   stress → von Mises). Acceptance: FEA within **±15 %** of the hand calc on
   f1, tip deflection, and the mid-span gauge stress.

---

## Result of the validated run (2026-06-25)

Recommended mast (L=100 mm, OD=20 mm, t=1.5 mm, 6061-T6); mesh 58 232 nodes /
28 985 C3D10; crash load 147.2 N distributed over 474 tip-ring nodes:

| Quantity | Hand calc | FEA | Δ% | Within ±15%? |
| --- | ---: | ---: | ---: | --- |
| 1st natural frequency `f1` | 309.3 Hz | **267.4 Hz** | −13.6 % | **OK** |
| Tip deflection (crash) | 0.190 mm | 0.201 mm | +5.9 % | **OK** |
| Mid-span gauge stress (crash) | 19.6 MPa | 19.8 MPa | +1.3 % | **OK** |

First six FE modes: 267.4, 282.3, 944.5, 3655, 4233, 8008 Hz. Modes 1–2 are the
two ~degenerate orthogonal bending modes of the axisymmetric tube (the small
split is mesh asymmetry). The global **peak** von Mises (47.8 MPa) sits at the
fixed-root re-entrant corner — a stress-concentration/mesh singularity, **not** a
valid `M·c/I` comparison; that is why the gauge ring and tip deflection are used.

**Interpretation.** The Rayleigh tip-mass hand calc slightly **over**-predicts
stiffness (it assumes a perfectly rigid root and pure Euler–Bernoulli bending,
neglecting shear and root flexibility), so the 3-D FE frequency lands ~14 %
lower — the expected direction and magnitude. Crucially, the **FE f1 = 267 Hz
still clears the ≥ 200 Hz guard band (1.34×)**, so the frequency-fix
recommendation holds under the higher-fidelity model.
