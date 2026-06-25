#!/usr/bin/env python
"""LiDAR-mast FEA pipeline — geometry -> mesh -> static + modal -> compare.

Validates the analytical hand calc in ``experiments/mast_hand_calc.py`` against
a 3-D finite-element model of the RECOMMENDED mast geometry (the frequency-fix
revision: 6061-T6 aluminum, L = 100 mm, OD = 20 mm, wall t = 1.5 mm). The mast
is a thin-walled cantilever tube, fully fixed at the deck (root) plane, with the
LiDAR tip mass either lumped as a point mass at the free-end center (modal) or
applied as an equivalent transverse tip force (static crash case).

Toolchain (two conda envs on this machine):
  * MESH  : gmsh 4.15.2  (Python API; lives in the conda BASE env)
  * SOLVE : CalculiX 2.23 ``ccx``  (lives in conda env ``fea``)

Because the mesher and solver live in different envs, this script meshes with
gmsh in-process and shells out to the ``ccx`` binary (path auto-detected, or set
via the ``CCX`` environment variable). See ``docs/design/FEA_SETUP.md`` for the
exact, tested stand-up commands.

What it does:
  1. Build the recommended tube as an OCC solid in gmsh and mesh it with
     quadratic tetrahedra (C3D10).
  2. Write two CalculiX decks:
       - static : root ENCASTRE, transverse point load (crash F) at the tip
                  center node  -> max von Mises stress + tip deflection.
       - modal  : root ENCASTRE, a CalculiX point MASS element at the tip
                  center node  -> first natural frequency (FREQUENCY step).
  3. Run ccx on each, parse the .dat/.frd, and compare to the hand calc:
       sigma_max and tip deflection must agree within ~10-15% (away from the
       root stress concentration); f1 within ~10-15%.

Run (from the repo root, with the gmsh/base env active):
    python experiments/mast_fea.py
Outputs go to ``runs/mast_fea/`` (meshes, .inp decks, ccx output, summary).

NOTE ON FIDELITY: a tip POINT load on a thin tube produces a local stress
concentration at the loaded node that the elementary M*c/I hand calc does not
model; the fair comparison metric is the stress on a mid-span gauge ring (and
the global tip deflection), not the peak nodal stress at the load point or the
singular root corner. The script reports both and flags the gauge comparison.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = REPO_ROOT / "runs" / "mast_fea"

# ---------------------------------------------------------------------------
# RECOMMENDED geometry + material (must match mast_hand_calc.py recommendation)
# ---------------------------------------------------------------------------
L = 0.100                 # mast length [m]            (recommended)
OD = 20.0e-3              # outer diameter [m]         (recommended)
WALL_T = 1.5e-3          # wall thickness [m]          (recommended, stock)
ID = OD - 2.0 * WALL_T   # inner diameter [m]

E = 68.9e9               # Young's modulus [Pa]        (6061-T6)
NU = 0.33                # Poisson's ratio [-]         (6061-T6)
RHO = 2700.0             # density [kg/m^3]            (6061-T6)
SIGMA_YIELD = 276.0e6    # tensile yield [Pa]          (6061-T6)

M_TIP = 0.20             # LiDAR + bracket tip mass [kg]
G = 9.81
A_CRASH = 50.0 * G       # crash shock [m/s^2]
SF_CRASH = 1.5           # crash safety factor
F_CRASH = M_TIP * A_CRASH * SF_CRASH  # transverse tip design force [N]

MESH_SIZE = 1.2e-3       # target element size [m] (~OD/16; resolves the wall)

# --- Analytical targets (from the hand calc, recommended geometry) ----------
def _hand_targets() -> dict[str, float]:
    I = math.pi / 64.0 * (OD**4 - ID**4)
    A = math.pi / 4.0 * (OD**2 - ID**2)
    c = OD / 2.0
    m_mast = RHO * A * L
    k = 3.0 * E * I / L**3
    m_eff = M_TIP + 0.23 * m_mast
    f1 = 1.0 / (2.0 * math.pi) * math.sqrt(k / m_eff)
    sigma_root = F_CRASH * L * c / I          # M*c/I at the root
    delta_tip = F_CRASH * L**3 / (3.0 * E * I)
    return {
        "I": I, "A": A, "c": c, "m_mast": m_mast,
        "k": k, "m_eff": m_eff, "f1": f1,
        "sigma_root": sigma_root, "delta_tip": delta_tip,
    }


def find_ccx() -> str | None:
    """Locate the CalculiX ``ccx`` binary (env var, PATH, or the ``fea`` env)."""
    if os.environ.get("CCX"):
        return os.environ["CCX"]
    for name in ("ccx", "ccx_2.23", "CalculiX"):
        p = shutil.which(name)
        if p:
            return p
    # Conventional conda location used by FEA_SETUP.md.
    for guess in (
        Path.home() / "ENTER" / "envs" / "fea" / "bin" / "ccx",
        Path("/opt/conda/envs/fea/bin/ccx"),
    ):
        if guess.exists():
            return str(guess)
    return None


# ---------------------------------------------------------------------------
# MESH (gmsh)
# ---------------------------------------------------------------------------
@dataclass
class Mesh:
    nodes: dict[int, tuple[float, float, float]]   # 1-based node id -> xyz
    c3d10: list[tuple[int, ...]]                    # 10-node tet connectivity
    root_nodes: list[int]                           # nodes on the z=0 root plane
    tip_center_node: int                            # node nearest tube axis at z=L
    tip_nodes: list[int]                            # all nodes on the z=L tip plane
    gauge_nodes: list[int]                          # nodes in a mid-span gauge ring


def build_mesh(mesh_size: float = MESH_SIZE) -> Mesh:
    """Build the recommended tube solid in gmsh and mesh with C3D10 tets.

    Tube axis is +z; root plane at z=0, free tip at z=L. Returns the parsed
    mesh plus the root node set and the tip-center node for BCs/loads.
    """
    import gmsh  # imported lazily so the rest of the module loads without it

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.model.add("lidar_mast")

        # Hollow tube = outer cylinder minus inner cylinder (OCC booleans).
        r_o, r_i = OD / 2.0, ID / 2.0
        outer = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, L, r_o)
        inner = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, L, r_i)
        tube, _ = gmsh.model.occ.cut([(3, outer)], [(3, inner)])
        gmsh.model.occ.synchronize()

        # Quadratic tets, second-order (C3D10) for bending accuracy.
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 0)
        gmsh.model.mesh.generate(3)

        # --- nodes ---
        ntags, ncoords, _ = gmsh.model.mesh.getNodes()
        nodes: dict[int, tuple[float, float, float]] = {}
        for i, tag in enumerate(ntags):
            x, y, z = ncoords[3 * i], ncoords[3 * i + 1], ncoords[3 * i + 2]
            nodes[int(tag)] = (x, y, z)

        # --- 10-node tets (gmsh element type 11) ---
        c3d10: list[tuple[int, ...]] = []
        etypes, etags, enodes = gmsh.model.mesh.getElements(dim=3)
        for et, _tg, nd in zip(etypes, etags, enodes):
            if et == 11:  # 10-node second-order tetrahedron
                nn = 10
                for k in range(len(nd) // nn):
                    c3d10.append(tuple(int(x) for x in nd[k * nn:(k + 1) * nn]))
        if not c3d10:
            raise RuntimeError("no C3D10 tets generated — check ElementOrder")

        # --- node sets ---
        tol = mesh_size * 0.25
        root_nodes = [nid for nid, (x, y, z) in nodes.items() if abs(z) <= tol]
        # tip plane: all nodes at z=L (load is distributed over these); the
        # tip-center node (closest to the axis) carries the modal point mass.
        tip_pool = [(nid, x, y) for nid, (x, y, z) in nodes.items() if abs(z - L) <= tol]
        if not tip_pool:
            raise RuntimeError("no nodes found on the tip plane")
        tip_nodes = [t[0] for t in tip_pool]
        tip_center_node = min(tip_pool, key=lambda t: math.hypot(t[1], t[2]))[0]
        # mid-span gauge ring: a thin band of nodes around z = L/2 (away from
        # the fixed-root and loaded-tip stress concentrations) where the FE
        # bending stress is the fair apples-to-apples check vs M*c/I.
        zg = L / 2.0
        band = mesh_size * 0.6
        gauge_nodes = [nid for nid, (x, y, z) in nodes.items() if abs(z - zg) <= band]

        return Mesh(nodes=nodes, c3d10=c3d10,
                    root_nodes=sorted(root_nodes), tip_center_node=tip_center_node,
                    tip_nodes=sorted(tip_nodes), gauge_nodes=sorted(gauge_nodes))
    finally:
        gmsh.finalize()


# ---------------------------------------------------------------------------
# CalculiX deck writers
# ---------------------------------------------------------------------------
# gmsh second-order tet (type 11) lists 4 corners then 6 edge nodes in the
# order (0-1, 1-2, 2-0, 0-3, 2-3, 1-3). CalculiX C3D10 expects the last two
# edge nodes swapped -> (0-1, 1-2, 2-0, 0-3, 1-3, 2-3). Applying this
# permutation fixes the "nonpositive jacobian" rejection from ccx.
_GMSH_TO_CCX_C3D10 = (0, 1, 2, 3, 4, 5, 6, 7, 9, 8)


def _write_common(mesh: Mesh, f) -> None:
    f.write("*NODE, NSET=NALL\n")
    for nid in sorted(mesh.nodes):
        x, y, z = mesh.nodes[nid]
        f.write(f"{nid}, {x:.9e}, {y:.9e}, {z:.9e}\n")
    f.write("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
    for eid, conn in enumerate(mesh.c3d10, start=1):
        c = [conn[i] for i in _GMSH_TO_CCX_C3D10]
        f.write(f"{eid}, " + ", ".join(str(n) for n in c) + "\n")
    f.write("*NSET, NSET=NROOT\n")
    for i in range(0, len(mesh.root_nodes), 8):
        f.write(", ".join(str(n) for n in mesh.root_nodes[i:i + 8]) + ",\n")
    f.write("*NSET, NSET=NTIP\n")
    f.write(f"{mesh.tip_center_node}\n")
    f.write("*NSET, NSET=NTIPALL\n")
    for i in range(0, len(mesh.tip_nodes), 8):
        f.write(", ".join(str(n) for n in mesh.tip_nodes[i:i + 8]) + ",\n")
    if mesh.gauge_nodes:
        f.write("*NSET, NSET=NGAUGE\n")
        for i in range(0, len(mesh.gauge_nodes), 8):
            f.write(", ".join(str(n) for n in mesh.gauge_nodes[i:i + 8]) + ",\n")
    f.write("*MATERIAL, NAME=AL6061T6\n")
    f.write("*ELASTIC\n")
    f.write(f"{E:.6e}, {NU}\n")
    f.write("*DENSITY\n")
    f.write(f"{RHO:.6e}\n")
    f.write("*SOLID SECTION, ELSET=EALL, MATERIAL=AL6061T6\n")


def write_static_inp(mesh: Mesh, path: Path) -> None:
    """Static crash case: root ENCASTRE, transverse tip load distributed over
    the tip ring (avoids a single-node point-load stress singularity).

    The total crash design force F_CRASH is split equally across the tip-plane
    nodes. Tip deflection is reported at the tip-center node; stress is reported
    on a mid-span gauge ring (fair M*c/I comparison) and globally (peak).
    """
    f_per_node = F_CRASH / max(1, len(mesh.tip_nodes))
    with path.open("w") as f:
        _write_common(mesh, f)
        f.write("*STEP\n*STATIC\n")
        f.write("*BOUNDARY\n")
        f.write("NROOT, 1, 3\n")                         # fix all 3 DOF at root
        f.write("*CLOAD\n")
        f.write(f"NTIPALL, 1, {f_per_node:.6e}\n")       # +x load spread over tip ring
        f.write("*NODE PRINT, NSET=NTIP\nU\n")
        # Extrapolated nodal stresses to the .frd; the gauge-ring filter
        # (mid-span node set) is applied in parse_frd, away from concentrations.
        f.write("*EL FILE\nS\n*NODE FILE\nU\n")
        f.write("*END STEP\n")


def write_modal_inp(mesh: Mesh, path: Path) -> None:
    """Modal case: root ENCASTRE + a point MASS element at the tip center node.

    CalculiX MASS element: a one-node element whose *MASS card carries the
    lumped LiDAR tip mass. The FREQUENCY step then returns the bending modes of
    (tube + tip mass), directly comparable to the Rayleigh hand-calc f1.
    """
    mass_eid = len(mesh.c3d10) + 1
    with path.open("w") as f:
        _write_common(mesh, f)
        f.write("*ELEMENT, TYPE=MASS, ELSET=ETIPMASS\n")
        f.write(f"{mass_eid}, {mesh.tip_center_node}\n")
        f.write("*MASS, ELSET=ETIPMASS\n")
        f.write(f"{M_TIP:.6e}\n")
        f.write("*STEP\n*FREQUENCY\n")
        f.write("6\n")                                   # extract first 6 modes
        f.write("*BOUNDARY\n")
        f.write("NROOT, 1, 3\n")
        f.write("*NODE FILE\nU\n")
        f.write("*END STEP\n")


# ---------------------------------------------------------------------------
# Run ccx + parse
# ---------------------------------------------------------------------------
def run_ccx(ccx: str, job: Path) -> None:
    """Invoke ccx on a job (path WITHOUT the .inp suffix)."""
    res = subprocess.run(
        [ccx, job.name], cwd=str(job.parent),
        capture_output=True, text=True, timeout=600,
    )
    (job.parent / f"{job.name}.ccx.log").write_text(res.stdout + "\n" + res.stderr)
    if res.returncode != 0:
        raise RuntimeError(
            f"ccx failed (rc={res.returncode}) on {job.name}; see {job.name}.ccx.log\n"
            + res.stdout[-2000:] + res.stderr[-2000:]
        )


def parse_frd_vonmises(frd: Path, only: set[int] | None = None) -> float | None:
    """Max von Mises stress [Pa] from a CalculiX .frd STRESS block.

    .frd stores the 6 stress components (SXX SYY SZZ SXY SYZ SZX) per node in
    the -4 STRESS dataset. We reconstruct von Mises per node and take the max,
    optionally restricting to a node-id set ``only`` (e.g. the mid-span gauge
    ring) so the result is away from the load-point / root singularities.
    """
    if not frd.exists():
        return None
    text = frd.read_text().splitlines()
    in_stress = False
    vm_max = 0.0
    for ln in text:
        if ln.startswith(" -4") and "STRESS" in ln:
            in_stress = True
            continue
        if in_stress and ln.startswith(" -3"):
            in_stress = False
            continue
        if in_stress and ln.startswith(" -1"):
            # Fixed-width: node id (cols 4-13) then 6 values in 12-char fields.
            try:
                nid = int(ln[3:13])
                body = ln[13:]
                vals = [float(body[i:i + 12]) for i in range(0, 6 * 12, 12)]
            except (ValueError, IndexError):
                continue
            if only is not None and nid not in only:
                continue
            sxx, syy, szz, sxy, syz, szx = vals
            vm = math.sqrt(
                0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2)
            )
            vm_max = max(vm_max, vm)
    return vm_max if vm_max > 0 else None


def parse_dat_tip_disp(dat: Path) -> float | None:
    """Return the tip transverse displacement magnitude [m] from the .dat file."""
    if not dat.exists():
        return None
    lines = dat.read_text().splitlines()
    grab = False
    last = None
    for ln in lines:
        low = ln.lower()
        if "displacements" in low and "nodal" not in low:
            grab = True
            continue
        if grab:
            parts = ln.split()
            if len(parts) >= 4:
                try:
                    ux, uy, uz = float(parts[1]), float(parts[2]), float(parts[3])
                    last = math.sqrt(ux * ux + uy * uy + uz * uz)
                except ValueError:
                    pass
            elif last is not None:
                break
    return last


def parse_dat_eigenfreqs(dat: Path) -> list[float]:
    """Return natural frequencies [Hz] from a CalculiX FREQUENCY .dat block."""
    if not dat.exists():
        return []
    lines = dat.read_text().splitlines()
    freqs: list[float] = []
    grab = False
    for ln in lines:
        low = ln.lower()
        if "eigenvalue" in low:
            grab = True            # header line; data follows after sub-headers
            continue
        if grab:
            parts = ln.split()
            # CalculiX FREQUENCY data row has 5 numeric columns:
            #   mode#  eigenvalue  omega[rad/time]  freq[cycles/time=Hz]  imag
            # -> the frequency in Hz is column index 3.
            if len(parts) == 5:
                try:
                    int(parts[0])
                    freqs.append(float(parts[3]))
                    continue
                except ValueError:
                    pass
            # Stop once we hit a blank/non-data line AFTER collecting modes
            # (skips the 3-line sub-header, which has no leading integer).
            if freqs and (not parts or not parts[0].replace("-", "").isdigit()):
                break
    return freqs


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    tgt = _hand_targets()

    print("=" * 78)
    print("LiDAR-MAST FEA  (recommended geometry: L=100 mm, OD=20 mm, t=1.5 mm, 6061-T6)")
    print("=" * 78)
    print(f"  Hand-calc targets:  f1 = {tgt['f1']:.1f} Hz   "
          f"sigma_root(crash) = {tgt['sigma_root']/1e6:.1f} MPa   "
          f"delta_tip = {tgt['delta_tip']*1e3:.3f} mm")
    print(f"  Crash design load:  F = {F_CRASH:.1f} N (50 g x 0.20 kg x SF 1.5)")

    ccx = find_ccx()
    try:
        import gmsh  # noqa: F401
        have_gmsh = True
    except Exception:  # pragma: no cover - environment dependent
        have_gmsh = False

    print(f"  gmsh available : {have_gmsh}")
    print(f"  ccx  available : {bool(ccx)}  ({ccx or 'NOT FOUND'})")
    if not have_gmsh or not ccx:
        print("\n[install-pending] FEA toolchain incomplete. See docs/design/FEA_SETUP.md")
        print("  This stub is runnable; it will mesh + solve once gmsh and ccx exist.")
        return 2

    # 1) mesh
    print("\n[1/4] meshing (gmsh, C3D10) ...")
    mesh = build_mesh()
    n_nodes, n_elems = len(mesh.nodes), len(mesh.c3d10)
    print(f"      nodes={n_nodes}  C3D10={n_elems}  "
          f"root_nodes={len(mesh.root_nodes)}  tip_node={mesh.tip_center_node}")

    # 2) write decks
    static_inp = RUN_DIR / "mast_static.inp"
    modal_inp = RUN_DIR / "mast_modal.inp"
    write_static_inp(mesh, static_inp)
    write_modal_inp(mesh, modal_inp)
    print(f"[2/4] wrote decks: {static_inp.name}, {modal_inp.name}")

    # 3) solve
    print("[3/4] solving (ccx) ...")
    run_ccx(ccx, static_inp.with_suffix(""))
    run_ccx(ccx, modal_inp.with_suffix(""))

    # 4) parse + compare
    print("[4/4] parsing + comparing to hand calc ...")
    frd = RUN_DIR / "mast_static.frd"
    vm_peak = parse_frd_vonmises(frd)                       # global peak (w/ conc.)
    vm_gauge = parse_frd_vonmises(frd, only=set(mesh.gauge_nodes))
    tip_disp = parse_dat_tip_disp(RUN_DIR / "mast_static.dat")
    freqs = parse_dat_eigenfreqs(RUN_DIR / "mast_modal.dat")
    f1_fea = freqs[0] if freqs else None

    # Hand-calc bending stress AT THE GAUGE RING (z = L/2): M(L/2) = F*(L/2),
    # so sigma_gauge = (F*L/2)*c/I = half the root value. This is the fair
    # comparison for the mid-span FE gauge stress (no concentration there).
    sigma_gauge_hand = F_CRASH * (L / 2.0) * tgt["c"] / tgt["I"]

    def pct(a: float, b: float) -> float:
        return 100.0 * (a - b) / b

    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("FEA vs HAND CALC — recommended LiDAR mast")
    lines.append("=" * 78)
    lines.append(f"  Mesh: {n_nodes} nodes, {n_elems} C3D10 tets, size ~{MESH_SIZE*1e3:.1f} mm")
    lines.append(f"  BCs : root fully fixed (ENCASTRE); crash load F={F_CRASH:.1f} N "
                 f"distributed over {len(mesh.tip_nodes)} tip-ring nodes")
    lines.append("")
    lines.append(f"  {'quantity':<26}{'hand calc':>13}{'FEA':>13}{'delta %':>9}  band(+-15%)")
    lines.append("  " + "-" * 74)

    headline_ok = True
    if f1_fea is not None:
        d = pct(f1_fea, tgt["f1"])
        ok = "OK" if abs(d) <= 15.0 else "OUT"
        headline_ok &= abs(d) <= 15.0
        lines.append(f"  {'f1 (1st bending) [Hz]':<26}{tgt['f1']:>13.1f}{f1_fea:>13.1f}{d:>9.1f}  {ok}")
    else:
        headline_ok = False
        lines.append(f"  {'f1 (1st bending) [Hz]':<26}{tgt['f1']:>13.1f}{'(parse?)':>13}{'-':>9}  -")

    if tip_disp is not None:
        d = pct(tip_disp, tgt["delta_tip"])
        ok = "OK" if abs(d) <= 15.0 else "OUT"
        headline_ok &= abs(d) <= 15.0
        lines.append(f"  {'tip deflection [mm]':<26}{tgt['delta_tip']*1e3:>13.3f}"
                     f"{tip_disp*1e3:>13.3f}{d:>9.1f}  {ok}")
    else:
        headline_ok = False
        lines.append(f"  {'tip deflection [mm]':<26}{tgt['delta_tip']*1e3:>13.3f}"
                     f"{'(parse?)':>13}{'-':>9}  -")

    if vm_gauge is not None:
        d = pct(vm_gauge, sigma_gauge_hand)
        ok = "OK" if abs(d) <= 15.0 else "OUT"
        headline_ok &= abs(d) <= 15.0
        lines.append(f"  {'gauge stress [MPa]':<26}{sigma_gauge_hand/1e6:>13.1f}"
                     f"{vm_gauge/1e6:>13.1f}{d:>9.1f}  {ok}")
    else:
        lines.append(f"  {'gauge stress [MPa]':<26}{sigma_gauge_hand/1e6:>13.1f}"
                     f"{'(parse?)':>13}{'-':>9}  -")

    lines.append("")
    lines.append(f"  Reference: root M*c/I hand calc = {tgt['sigma_root']/1e6:.1f} MPa; "
                 f"FE global PEAK vonMises = "
                 f"{(vm_peak/1e6 if vm_peak else float('nan')):.1f} MPa")
    lines.append("    The PEAK sits at the fixed-root re-entrant corner (a stress")
    lines.append("    concentration / mesh singularity) — NOT a valid M*c/I comparison.")
    lines.append("    The mid-span GAUGE ring (above) and the global tip DEFLECTION are the")
    lines.append("    fair checks; both should land within +-15% of beam theory.")

    if freqs:
        lines.append("")
        lines.append("  First modes [Hz]: " + ", ".join(f"{x:.1f}" for x in freqs[:6]))
        lines.append("    (modes 1-2 are the two ~degenerate orthogonal bending modes of the")
        lines.append("     axisymmetric tube; the small split is mesh asymmetry.)")
    lines.append("=" * 78)

    report = "\n".join(lines)
    print("\n" + report)
    (RUN_DIR / "fea_summary.txt").write_text(report + "\n")
    print(f"\n[written] {RUN_DIR / 'fea_summary.txt'}")

    # Exit nonzero if the headline checks are missing or out of band.
    if f1_fea is None or tip_disp is None:
        return 3
    if not headline_ok:
        print("\n[WARN] an FEA headline metric is outside +-15% — investigate mesh/BCs.")
        return 1
    print("\n[OK] FEA agrees with the hand calc within +-15% on f1, tip deflection,")
    print("     and mid-span gauge stress. Hand calc validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
