#!/usr/bin/env python
"""Item-16 §7: mounting tolerance stack -> LiDAR scan-plane tilt -> sightline check.

The UST-10LX scans a horizontal plane. Yaw misalignment is nulled in software
by the localization mount calibration, so the physical stack that matters is
the TILT (pitch/roll) of the optical plane: stacked interface tolerances tilt
the beam, and at range the beam either climbs over the track wall (up-tilt) or
grazes the floor and returns false obstacles (down-tilt).

Requirement (derived, both directions, at the UST-10LX guaranteed range):
    up-tilt   : beam height at R_MAX must stay below the wall top
                theta <= atan((H_WALL - H_OPT) / R_MAX)
    down-tilt : the floor-graze distance must stay beyond R_MAX
                theta <= atan(H_OPT / R_MAX)
The up-tilt bound governs (wall clearance above the optical center is smaller
than the height of the optical center above the floor).

Each contributor is labelled ASSUMED where it is an engineering-typical value
rather than a datasheet/spec number, following the item-15/16 convention. The
elastic tilt under the measured 2g maneuvering load is computed from the
validated FEA deflection (runs/mast_fea/fea_summary.txt) and included to show
it is negligible against the interface tolerances.

Run:  python experiments/mast_tolerance_stack.py
Output: runs/mast_tolerance_stack/summary.txt (+ stdout). Exit 0 only if the
as-calibrated stack passes; the as-assembled (blind) stack is reported either
way.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = REPO_ROOT / "runs" / "mast_tolerance_stack"

# --- Geometry (locked / assumed) --------------------------------------------
H_MAST = 0.100        # optical center above deck [m]     (item 15 §1.2, LOCKED)
H_DECK = 0.070        # deck above floor [m]              (ASSUMED 1/10-class chassis)
H_OPT = H_MAST + H_DECK
H_WALL = 0.30         # track wall height [m]             (ASSUMED, conservative vs
                      #                                    the common 0.33 m duct wall)
R_MAX = 10.0          # UST-10LX guaranteed range [m]     (datasheet)
R_PLAN = 5.0          # representative planning range [m]

# --- Tilt contributors [deg] --------------------------------------------------
# (source, value, basis)
CONTRIBUTORS = [
    ("Deck local flatness under 20 mm base", math.degrees(math.atan(0.10 / 20.0)),
     "ASSUMED 0.10 mm across the 20 mm base seat (machined/FR4-plate class)"),
    ("Mast base-to-tube squareness", 0.50,
     "ASSUMED FDM/printed-bracket perpendicularity, no post-machining"),
    ("Bolted-joint preload rocking allowance", 0.10,
     "clamped flat-on-flat; hole clearance goes to YAW (software-nulled), keep a tilt allowance"),
    ("LiDAR internal scan-plane-to-base", 0.25,
     "ASSUMED - UST-10LX datasheet does not spec scan-plane tilt; typical class"),
    ("LiDAR mounting datum", math.degrees(math.atan(0.10 / 40.0)),
     "ASSUMED 0.10 mm across the 40 mm bolt pattern"),
]

# Elastic tilt under the measured 2g maneuvering load, from the validated FEA:
# delta_crash = 0.176 mm at F_crash = 128.8 N (runs/mast_fea/fea_summary.txt);
# deflection is linear, tip slope of an end-loaded cantilever = 1.5*delta/L.
F_CRASH, DELTA_CRASH = 128.8, 0.176e-3
F_MANEUVER = 0.175 * 19.4                    # tip mass x measured a_lat,peak (no SF: sightline, not strength)
DELTA_MAN = DELTA_CRASH * F_MANEUVER / F_CRASH
ELASTIC_TILT_DEG = math.degrees(1.5 * DELTA_MAN / H_MAST)
CONTRIBUTORS.append(
    ("Elastic tilt @ 2g maneuvering (FEA-derived)", ELASTIC_TILT_DEG,
     f"delta = {DELTA_MAN*1e3:.4f} mm from the validated static FEA, scaled to F = {F_MANEUVER:.1f} N"))

# After the one-time scan-plane leveling procedure (shim the base; verify by
# scanning a wall at two distances and equalizing return heights), everything
# EXTERNAL to the LiDAR is nulled; the residual is the internal scan-plane
# spec plus the preload/thermal drift allowance and the elastic term.
CALIBRATED_RESIDUAL = ["LiDAR internal scan-plane-to-base",
                       "Bolted-joint preload rocking allowance",
                       "Elastic tilt @ 2g maneuvering (FEA-derived)"]


def main() -> int:
    theta_req_up = math.degrees(math.atan((H_WALL - H_OPT) / R_MAX))
    theta_req_dn = math.degrees(math.atan(H_OPT / R_MAX))
    theta_req = min(theta_req_up, theta_req_dn)

    worst = sum(v for _, v, _ in CONTRIBUTORS)
    rss = math.sqrt(sum(v * v for _, v, _ in CONTRIBUTORS))
    cal = [(n, v, b) for n, v, b in CONTRIBUTORS if n in CALIBRATED_RESIDUAL]
    worst_cal = sum(v for _, v, _ in cal)

    def beam_err(theta_deg: float, r: float) -> float:
        return r * math.tan(math.radians(theta_deg))

    lines = ["=" * 84,
             "TOLERANCE STACK -> LiDAR SCAN-PLANE TILT (item 16 par.7)",
             "=" * 84,
             f"  Optical center: {H_OPT:.3f} m above floor "
             f"({H_MAST:.3f} m mast [LOCKED] + {H_DECK:.3f} m deck [ASSUMED])",
             f"  Requirement (governing = up-tilt wall clearance at R = {R_MAX:.0f} m):"
             f"  theta <= {theta_req:.3f} deg",
             f"    (down-tilt floor-graze bound: {theta_req_dn:.3f} deg)",
             "",
             f"  {'contributor':<44}{'tilt [deg]':>11}",
             "  " + "-" * 80]
    for name, val, basis in CONTRIBUTORS:
        lines.append(f"  {name:<44}{val:>11.3f}   {basis}")
    lines += [
        "",
        f"  {'WORST-CASE sum (blind assembly)':<44}{worst:>11.3f}   "
        f"{'FAIL' if worst > theta_req else 'PASS'} vs {theta_req:.3f} deg",
        f"  {'RSS (blind assembly)':<44}{rss:>11.3f}   "
        f"{'FAIL' if rss > theta_req else 'PASS'} vs {theta_req:.3f} deg",
        f"  {'WORST-CASE after scan-plane leveling':<44}{worst_cal:>11.3f}   "
        f"{'FAIL' if worst_cal > theta_req else 'PASS'} vs {theta_req:.3f} deg",
        "",
        "  Beam-height error at range (RSS blind / calibrated worst):",
        f"    R = {R_PLAN:.0f} m : +-{beam_err(rss, R_PLAN)*100:.1f} cm / "
        f"+-{beam_err(worst_cal, R_PLAN)*100:.1f} cm",
        f"    R = {R_MAX:.0f} m : +-{beam_err(rss, R_MAX)*100:.1f} cm / "
        f"+-{beam_err(worst_cal, R_MAX)*100:.1f} cm",
        "",
        "  CONCLUSION: blind assembly FAILS worst-case (and the RSS pass has no",
        "  margin policy behind it), so the stack DERIVES an install requirement:",
        "  a one-time scan-plane leveling (shim the base; verify by scanning a",
        "  wall at two distances and equalizing return heights). The calibrated",
        "  residual passes the governing bound with >2x margin. The elastic term",
        "  is negligible (<0.01 deg): the stack is interface-dominated, which is",
        "  exactly why the procedure fixes it.",
        "=" * 84]

    report = "\n".join(lines)
    print(report)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "summary.txt").write_text(report + "\n")
    print(f"\n[written] {RUN_DIR / 'summary.txt'}")
    return 0 if worst_cal <= theta_req else 1


if __name__ == "__main__":
    sys.exit(main())
