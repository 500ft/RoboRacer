#!/usr/bin/env python
"""LiDAR-mast hand calculation — analytical baseline for the item-16 FEA.

Models the LiDAR mast (item 15 / item 16 of the design package) as a
thin-walled cantilever tube, fixed at the deck (root) with the LiDAR mass
lumped at the free tip. Computes, for two load cases, the root bending
moment, peak bending stress, tip deflection, and yield safety factor, plus
the load-independent first natural frequency (Rayleigh tip-mass model).

This is the ANALYTICAL GROUND TRUTH that the static FEA in
docs/design/16_mechanical_design_analysis.md (Section 4) must reproduce
within ~10-15% (away from stress concentrations) before the
detailed-geometry FEA is trusted.

Units: strict SI throughout (m, kg, s, N, Pa). Printed values are converted
to engineering units (mm, MPa, Hz) only at the print boundary. numpy + stdlib
only; no FEA dependencies.

Run:
    python experiments/mast_hand_calc.py
Output is also written to runs/mast_hand_calc/summary.txt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = REPO_ROOT / "runs" / "mast_hand_calc"

# ----------------------------------------------------------------------------
# ASSUMPTIONS — every value below is an explicit design assumption. The LiDAR
# (item 15) is NOT yet selected, so tip mass, mast length, and section are
# placeholders chosen to be representative and conservative. Each is labelled
# ASSUMED with a short rationale; change these in one place when item 15 locks.
# ----------------------------------------------------------------------------

# --- Geometry (ASSUMED) ---
# Short mast so the optical center clears the chassis/compute stack without a
# tall, whippy cantilever. 0.12 m is a typical sensor-deck-to-optical-center
# height for a 1/10-scale car; the moment arm h_arm == L here because the tip
# mass sits at the free end (conservative: full length is the lever).
L = 0.12                 # mast length / moment arm [m]  (ASSUMED)
OD = 16.0e-3             # tube outer diameter [m]       (ASSUMED, 16 mm)
WALL_T = 1.5e-3          # tube wall thickness [m]        (ASSUMED, 1.5 mm)
ID = OD - 2.0 * WALL_T   # tube inner diameter [m]        (derived)

# --- Material (ASSUMED): 6061-T6 aluminum ---
# Common, weldable, cheap stock tube; properties are textbook handbook values.
# Carbon-fiber tube is the lighter, stiffer alternative (E roughly 70-130 GPa
# axial depending on layup, rho roughly 1600 kg/m^3) but is anisotropic and
# has no single sigma_yield; aluminum is the conservative, well-defined choice
# for a hand-calc baseline. See note printed at the end.
E = 68.9e9               # Young's modulus [Pa]           (ASSUMED, 6061-T6)
SIGMA_YIELD = 276.0e6    # tensile yield strength [Pa]    (ASSUMED, 6061-T6)
RHO = 2700.0             # density [kg/m^3]               (ASSUMED, 6061-T6)

# --- Tip mass (ASSUMED) ---
# RPLIDAR-class 2D scanner (e.g. A1/A2-class) plus a light mounting bracket.
# A bare RPLIDAR A2 is ~0.19 kg; round up to 0.20 kg to cover the bracket.
M_TIP = 0.20             # lumped LiDAR + bracket mass at tip [kg] (ASSUMED)

# --- Load environment ---
# Maneuvering peak lateral acceleration is NOT assumed — it is measured from a
# clean completed lap (item 16, runs/ride_quality_baseline). Treated as known.
A_LAT_PEAK = 19.4        # peak lateral accel [m/s^2] (~2.0 g; MEASURED, clean lap)
G = 9.81                 # standard gravity [m/s^2]

# --- Safety factors (ASSUMED, stated) ---
# Maneuvering: SF=2.0 on yield. The maneuvering load is a repeated/quasi-static
# inertial load with modeling uncertainty (tip mass, section, mounting fixity),
# so a 2x margin on yield is a conventional, defensible choice.
SF_MANEUVER = 2.0        # safety factor, maneuvering case (ASSUMED)
# Crash: the load is a one-off survival event; we already inflate it with a
# large g-shock (below), so we accept a smaller explicit SF of 1.5 on top.
SF_CRASH = 1.5           # safety factor, crash case (ASSUMED)

# --- Crash/drop case (ASSUMED, justified) ---
# A 1/10 car striking a wall or tipping onto the mast subjects the tip mass to
# a transient deceleration. Rather than guess a contact stiffness / stop
# distance (which sets the true peak g and is highly uncertain), we adopt a
# stated, conservative half-sine-equivalent shock of 50 g applied to the tip
# mass. 50 g is a common ruggedized-electronics shock-survival level and
# bounds a low-speed bench drop of this small mass; it is deliberately well
# above the ~2 g maneuvering case so the crash governs the strength check.
A_CRASH_G = 50.0         # crash shock [g] (ASSUMED, stated survival level)
A_CRASH = A_CRASH_G * G  # crash shock [m/s^2]

# --- Modal acceptance band (stated) ---
CONTROL_RATE_HZ = 100.0  # all controllers run at 100 Hz (dt = 0.002 s)
# Acceptance: f1 must clear the 100 Hz control update rate with a guard factor
# and also clear a plausible brushless-motor/drivetrain excitation band. A
# 1/10 sensored BLDC at racing RPM produces electrical/commutation excitation
# in the low-hundreds of Hz; we require f1 to sit at least a factor of 2 above
# 100 Hz (>=200 Hz) so the structure is stiff relative to the control loop and
# the dominant low-frequency excitation, avoiding resonant amplification of
# the scan platform.
F1_MIN_HZ = 2.0 * CONTROL_RATE_HZ  # acceptance threshold [Hz] = 200 Hz


@dataclass
class SectionProps:
    """Geometric properties of the thin-walled circular tube section."""

    area: float          # cross-sectional (material) area A [m^2]
    I: float             # second moment of area about bending axis [m^4]
    c: float             # extreme-fiber distance = OD/2 [m]
    mass_per_len: float  # distributed self-mass per unit length [kg/m]
    mast_mass: float     # total mast self-mass [kg]


def section_properties(od: float, idia: float, length: float, rho: float) -> SectionProps:
    """Hollow circular tube: A, I, c, and self-mass.

    I = pi/64 * (OD^4 - ID^4)  (annulus second moment of area)
    A = pi/4  * (OD^2 - ID^2)
    """
    area = math.pi / 4.0 * (od**2 - idia**2)
    I = math.pi / 64.0 * (od**4 - idia**4)
    c = od / 2.0
    mass_per_len = rho * area
    mast_mass = mass_per_len * length
    return SectionProps(area=area, I=I, c=c, mass_per_len=mass_per_len, mast_mass=mast_mass)


@dataclass
class CantileverResult:
    """Beam response for one load case."""

    label: str
    accel: float    # applied acceleration [m/s^2]
    sf: float       # safety factor multiplier applied to the inertial load
    force: float    # design tip force F [N]
    moment: float   # root bending moment M = F*L [N*m]
    sigma: float    # peak bending stress sigma = M*c/I [Pa]
    delta: float    # tip deflection delta = F*L^3/(3 E I) [m]
    sf_yield: float # realized margin = sigma_yield / sigma [-]


def evaluate_load_case(
    label: str,
    accel: float,
    sf: float,
    sec: SectionProps,
    *,
    length: float,
    E: float,
    sigma_yield: float,
    m_tip: float,
) -> CantileverResult:
    """Linear-elastic cantilever with a transverse point load F at the tip.

    Design tip force already includes the safety factor:
        F = m_tip * accel * SF
    The mast self-weight is intentionally NOT added to the transverse load:
    its inertial contribution is distributed and small relative to the tip
    mass, and lumping it at the tip would be unconservative for the moment.
    (It IS accounted for in the modal effective mass below.)
    """
    F = m_tip * accel * sf
    M = F * length
    sigma = M * sec.c / sec.I
    delta = F * length**3 / (3.0 * E * sec.I)
    sf_yield = sigma_yield / sigma
    return CantileverResult(
        label=label, accel=accel, sf=sf, force=F, moment=M,
        sigma=sigma, delta=delta, sf_yield=sf_yield,
    )


def first_natural_frequency(sec: SectionProps, *, length: float, E: float, m_tip: float) -> tuple[float, float, float]:
    """First bending mode via the Rayleigh tip-mass approximation.

    Tip-loaded cantilever stiffness:  k_eff = 3 E I / L^3
    Effective modal mass:             m_eff = m_tip + 0.23 * m_mast
        (0.23 is the standard Rayleigh equivalent fraction of a uniform
         cantilever's distributed mass lumped at the tip.)
    f1 = (1 / 2pi) * sqrt(k_eff / m_eff)

    Returns (f1 [Hz], k_eff [N/m], m_eff [kg]).
    """
    k_eff = 3.0 * E * sec.I / length**3
    m_eff = m_tip + 0.23 * sec.mast_mass
    f1 = (1.0 / (2.0 * math.pi)) * math.sqrt(k_eff / m_eff)
    return f1, k_eff, m_eff


# ----------------------------------------------------------------------------
# DESIGN SWEEP — frequency fix
# ----------------------------------------------------------------------------
# The baseline (L=0.12 m, OD=16 mm, t=1.5 mm, 6061-T6) PASSES strength but
# FAILS the modal guard band: f1 = 163.8 Hz < 200 Hz. The sweep below searches
# mast geometry (length L, outer diameter OD, wall t) and material to find
# configurations that clear f1 >= 200 Hz with comfortable margin while keeping
# the crash-case yield safety factor acceptable.
#
# WHY shortening L and growing OD work (and why they win over adding mass):
#   k_eff = 3 E I / L^3,  I = (pi/64)(OD^4 - ID^4) ~ (pi/8) R^3 t  (thin wall)
#   f1 = (1/2pi) sqrt(k_eff / m_eff),  m_eff = m_tip + 0.23 m_mast
#   The 0.20 kg tip mass dominates m_eff (mast self-mass ~0.02 kg), so m_eff
#   is nearly constant and f1 ~ sqrt(k_eff) = sqrt(3 E I / L^3).
#     - Length:  k ∝ L^-3, so f1 ∝ L^-1.5. A 0.12 -> 0.10 m cut is a 1.73x
#       stiffness gain (1.32x in f1) for a TINY mass change.
#     - Diameter: I ∝ OD^3·t (thin wall), while the added material the larger
#       tube contributes to m_eff is second-order (tip mass dominates). So OD
#       buys stiffness far faster than it adds effective mass.
#   Both levers raise k_eff much faster than m_eff, so f1 climbs.

# --- CFRP alternative material (ASSUMED, clearly stated) ---
# A pultruded / roll-wrapped carbon-fiber tube. Axial modulus depends heavily
# on layup; standard-modulus unidirectional-dominant tube is ~70-130 GPa. We
# take E_CFRP = 100 GPa as a representative mid-range axial value and
# rho_CFRP = 1600 kg/m^3. CFRP is ANISOTROPIC and has NO single tensile yield
# point, so a "yield SF" is not strictly defined; for screening we compare its
# peak bending stress against a CONSERVATIVE allowable of 600 MPa (typical
# design allowable, well below ultimate ~1.5-2 GPa) purely as a sanity bound.
# Aluminum remains the recommended baseline because its yield is well-defined.
E_CFRP = 100.0e9          # CFRP axial Young's modulus [Pa] (ASSUMED, mid-range)
RHO_CFRP = 1600.0         # CFRP density [kg/m^3]           (ASSUMED)
SIGMA_ALLOW_CFRP = 600.0e6  # CFRP conservative bending allowable [Pa] (ASSUMED)

# Comfortable-margin target: aim ~1.5x above the 200 Hz guard (i.e. ~3x the
# 100 Hz control rate) so the design sits well clear of the acceptance
# threshold AND of any low-hundreds-Hz motor band, not on the knife-edge.
F1_TARGET_HZ = 1.5 * F1_MIN_HZ  # = 300 Hz aspirational margin


@dataclass
class SweepCandidate:
    """One mast configuration evaluated by the design sweep."""

    material: str        # "6061-T6" or "CFRP"
    length: float        # L [m]
    od: float            # OD [m]
    wall: float          # t [m]
    E: float             # Young's modulus [Pa]
    rho: float           # density [kg/m^3]
    sigma_limit: float   # yield (Al) or conservative allowable (CFRP) [Pa]
    I: float             # section second moment [m^4]
    mast_mass: float     # mast self-mass [kg]
    f1: float            # first natural frequency [Hz]
    sigma_crash: float   # crash-case peak bending stress [Pa]
    sf_crash: float      # crash-case strength margin sigma_limit/sigma_crash
    delta_crash: float   # crash-case tip deflection [m]

    @property
    def f1_pass(self) -> bool:
        return self.f1 >= F1_MIN_HZ

    @property
    def strength_pass(self) -> bool:
        # Require the crash case to clear its stated SF (1.5) on the limit.
        return self.sf_crash >= SF_CRASH


def evaluate_candidate(
    material: str, length: float, od: float, wall: float,
    E: float, rho: float, sigma_limit: float,
) -> SweepCandidate:
    """Compute f1 and the (governing) crash-case strength for one geometry."""
    idia = od - 2.0 * wall
    sec = section_properties(od, idia, length, rho)
    f1, _k, _m = first_natural_frequency(sec, length=length, E=E, m_tip=M_TIP)
    # Crash governs strength (50 g >> ~2 g maneuver); evaluate it with SF_crash.
    crash = evaluate_load_case(
        "crash", A_CRASH, SF_CRASH, sec,
        length=length, E=E, sigma_yield=sigma_limit, m_tip=M_TIP,
    )
    return SweepCandidate(
        material=material, length=length, od=od, wall=wall, E=E, rho=rho,
        sigma_limit=sigma_limit, I=sec.I, mast_mass=sec.mast_mass,
        f1=f1, sigma_crash=crash.sigma, sf_crash=crash.sf_yield,
        delta_crash=crash.delta,
    )


def run_design_sweep() -> tuple[list[SweepCandidate], SweepCandidate, SweepCandidate]:
    """Sweep L, OD, wall, and material; return (all, baseline, recommended).

    Recommendation policy: among aluminum candidates that PASS both f1>=200 Hz
    and the crash SF, pick the one closest to (but at/above) the comfortable
    F1_TARGET_HZ that uses standard stock sizing and the smallest geometry
    change from baseline — i.e. prefer keeping the stock 1.5 mm wall and the
    shortest length / smallest OD that still clears the target with margin.
    Aluminum is preferred over CFRP because its yield is well-defined; CFRP is
    reported as the lighter alternative.
    """
    lengths = [0.12, 0.11, 0.10, 0.09, 0.08]
    ods_mm = [16.0, 18.0, 20.0, 22.0, 25.0]
    walls_mm = [1.0, 1.5, 2.0]

    candidates: list[SweepCandidate] = []
    for L_i in lengths:
        for od_mm in ods_mm:
            for t_mm in walls_mm:
                od_i = od_mm * 1e-3
                t_i = t_mm * 1e-3
                if od_i - 2.0 * t_i <= 0.0:          # physical wall guard
                    continue
                # Aluminum
                candidates.append(evaluate_candidate(
                    "6061-T6", L_i, od_i, t_i, E, RHO, SIGMA_YIELD))
                # CFRP (same geometry, screened against conservative allowable)
                candidates.append(evaluate_candidate(
                    "CFRP", L_i, od_i, t_i, E_CFRP, RHO_CFRP, SIGMA_ALLOW_CFRP))

    # Baseline candidate (the failing reference), aluminum at nominal geometry.
    baseline = evaluate_candidate("6061-T6", L, OD, WALL_T, E, RHO, SIGMA_YIELD)

    # --- Recommendation policy -------------------------------------------
    # Use BOTH stiffness levers (shorter L AND larger OD) for a robust,
    # comfortable-margin design rather than shortening alone to barely clear
    # the band. Practical manufacturability / integration constraints:
    #   * Aluminum (well-defined yield) and stock 1.5 mm wall.
    #   * L >= 0.10 m: do NOT shorten below 100 mm — the optical-center height
    #     is needed for the LiDAR sightline over the compute stack (dropping
    #     the full 40 mm to 80 mm would compromise sensor clearance), so we
    #     spend most of the stiffness budget on OD, only trimming L by 20 mm.
    #   * OD <= 22 mm: keep a slim, common stock size.
    # Among candidates meeting those constraints AND clearing the comfortable
    # F1_TARGET, pick the smallest OD / longest L that still clears it (least
    # material, smallest integration change) -> a sensible, defensible part.
    al_pass = [
        c for c in candidates
        if c.material == "6061-T6" and c.f1_pass and c.strength_pass
        and c.f1 >= F1_TARGET_HZ
        and abs(c.wall - WALL_T) < 1e-9      # stock 1.5 mm wall
        and c.length >= 0.10 - 1e-9          # preserve LiDAR sightline
        and c.od <= 0.022 + 1e-9             # slim, common stock OD
        and c.od > OD + 1e-9                 # actually use the OD lever
    ]
    if not al_pass:  # graceful fallback: any passing Al if constraints too tight
        al_pass = [
            c for c in candidates
            if c.material == "6061-T6" and c.f1_pass and c.strength_pass
        ]

    def rec_key(c: SweepCandidate) -> tuple:
        # Prefer smallest OD, then longest L, among those clearing the target;
        # tie-break toward the configuration closest above the target.
        return (
            round(c.od, 4),                       # least diameter (least material)
            -round(c.length, 4),                  # longest length (best sightline)
            round(abs(c.f1 - F1_TARGET_HZ), 1),   # closest above target
        )

    recommended = min(al_pass, key=rec_key)
    return candidates, baseline, recommended


def _fmt_sweep_lines(
    candidates: list[SweepCandidate],
    baseline: SweepCandidate,
    recommended: SweepCandidate,
) -> list[str]:
    """Human-readable design-sweep report (comparison table + reasoning)."""
    out: list[str] = []
    a = out.append

    def row(c: SweepCandidate, tag: str = "") -> str:
        fv = "PASS" if c.f1_pass else "FAIL"
        sv = "PASS" if c.strength_pass else "FAIL"
        return (f"  {tag:<12}{c.material:<9}{c.length*1e3:>6.0f}{c.od*1e3:>6.0f}"
                f"{c.wall*1e3:>6.1f}{c.f1:>9.1f} {fv:<5}{c.sf_crash:>8.2f} {sv:<5}"
                f"{c.sigma_crash/1e6:>9.1f}{c.mast_mass*1e3:>8.1f}")

    a("=" * 88)
    a("DESIGN SWEEP — FREQUENCY FIX (raise f1 >= 200 Hz, keep strength SF >= 1.5)")
    a("=" * 88)
    a("")
    a("Goal: the baseline PASSES strength but FAILS the modal guard band")
    a(f"      (f1 = {baseline.f1:.1f} Hz < {F1_MIN_HZ:.0f} Hz). Find a stiffer mast.")
    a("")
    a("Levers (tip mass dominates m_eff, so f1 ~ sqrt(3 E I / L^3)):")
    a("  * Shorten L : k ∝ L^-3  -> f1 ∝ L^-1.5  (big gain, ~no mass cost)")
    a("  * Grow OD   : I ∝ OD^3·t -> stiffness rises far faster than m_eff")
    a("  Both raise k_eff much faster than m_eff, so f1 climbs.")
    a("")
    a("CFRP alternative (ASSUMED): E = {:.0f} GPa, rho = {:.0f} kg/m^3, conservative".format(
        E_CFRP / 1e9, RHO_CFRP))
    a("  bending allowable {:.0f} MPa (anisotropic, NO single yield -> screening only).".format(
        SIGMA_ALLOW_CFRP / 1e6))
    a("")
    hdr = (f"  {'tag':<12}{'matl':<9}{'L_mm':>6}{'OD':>6}{'t':>6}"
           f"{'f1[Hz]':>9} {'f1?':<5}{'SFcr':>8} {'str?':<5}{'sig[MPa]':>9}{'mast[g]':>8}")
    a(hdr)
    a("  " + "-" * (len(hdr) - 2))
    a(row(baseline, "BASELINE"))
    a(row(recommended, "RECOMMEND"))
    a("")
    a("  Stock-wall (1.5 mm) aluminum candidates that clear the comfortable")
    a(f"  target (f1 >= {F1_TARGET_HZ:.0f} Hz) AND pass strength, sorted small->large OD")
    a("  then long->short L (the recommendation policy: least material / best sightline):")
    al_pass = sorted(
        [c for c in candidates
         if c.material == "6061-T6" and c.f1_pass and c.strength_pass
         and c.f1 >= F1_TARGET_HZ and abs(c.wall - WALL_T) < 1e-9],
        key=lambda c: (round(c.od, 4), -round(c.length, 4)),
    )[:8]
    for c in al_pass:
        tag = "  <== REC" if (c.length == recommended.length and c.od == recommended.od
                              and c.wall == recommended.wall) else ""
        a(row(c) + tag)
    a("")
    a("RECOMMENDATION")
    a("-" * 88)
    dod = (recommended.od - OD) * 1e3
    dL = (recommended.length - L) * 1e3
    a(f"  Revised mast: 6061-T6 aluminum, L = {recommended.length*1e3:.0f} mm "
      f"(from {L*1e3:.0f}), OD = {recommended.od*1e3:.0f} mm (from {OD*1e3:.0f}), "
      f"wall t = {recommended.wall*1e3:.1f} mm (stock).")
    a(f"    Change vs baseline: L {dL:+.0f} mm, OD {dod:+.0f} mm, same wall, same material.")
    a(f"  -> f1 = {recommended.f1:.1f} Hz  (>= {F1_MIN_HZ:.0f} Hz guard; "
      f"{recommended.f1/F1_MIN_HZ:.2f}x the guard, {recommended.f1/CONTROL_RATE_HZ:.1f}x "
      f"the 100 Hz control rate)  PASS")
    a(f"  -> crash-case strength SF = {recommended.sf_crash:.2f} "
      f"(>= {SF_CRASH:.1f})  PASS   (sigma_crash = {recommended.sigma_crash/1e6:.1f} MPa, "
      f"delta = {recommended.delta_crash*1e3:.3f} mm)")
    a(f"  -> mast self-mass {recommended.mast_mass*1e3:.1f} g "
      f"(baseline {baseline.mast_mass*1e3:.1f} g): a {(recommended.mast_mass-baseline.mast_mass)*1e3:+.1f} g penalty.")
    a("")
    a("  WHY it works: shortening L from 120 to {:.0f} mm raises k by ({:.0f}/{:.0f})^3 = {:.2f}x,".format(
        recommended.length * 1e3, L * 1e3, recommended.length * 1e3,
        (L / recommended.length) ** 3))
    a("  and growing OD from {:.0f} to {:.0f} mm raises I by {:.2f}x; m_eff barely moves".format(
        OD * 1e3, recommended.od * 1e3, recommended.I / baseline.I))
    a("  (tip mass dominates), so f1 jumps {:.1f} -> {:.1f} Hz. Strength improves too".format(
        baseline.f1, recommended.f1))
    a("  (more I lowers bending stress), so the fix is monotonic in both checks.")
    a("")
    a("  CFRP note: the same {:.0f} mm / {:.0f} mm tube in CFRP would reach".format(
        recommended.length * 1e3, recommended.od * 1e3))
    cfrp = next((c for c in candidates if c.material == "CFRP"
                 and c.length == recommended.length and c.od == recommended.od
                 and c.wall == recommended.wall), None)
    if cfrp is not None:
        a(f"  f1 = {cfrp.f1:.1f} Hz at {cfrp.mast_mass*1e3:.1f} g "
          f"({(cfrp.mast_mass-recommended.mast_mass)*1e3:+.1f} g vs the Al rec) — lighter and")
        a("  stiffer, but anisotropic with no single yield, so aluminum is the recommended")
        a("  baseline. CFRP is the upgrade path if mast mass ever becomes binding.")
    a("=" * 88)
    return out


def _hand_sanity_check_recommended(rec: SweepCandidate) -> list[str]:
    """Independent by-hand recomputation of the recommended f1 (catch slips)."""
    out: list[str] = []
    a = out.append
    od, idia, Lr = rec.od, rec.od - 2.0 * rec.wall, rec.length
    I = math.pi / 64.0 * (od**4 - idia**4)
    A = math.pi / 4.0 * (od**2 - idia**2)
    m_mast = rec.rho * A * Lr
    k = 3.0 * rec.E * I / Lr**3
    m_eff = M_TIP + 0.23 * m_mast
    f1 = 1.0 / (2.0 * math.pi) * math.sqrt(k / m_eff)
    a("SANITY CHECK (recommended geometry, recomputed by hand)")
    a("-" * 88)
    a(f"  I     = pi/64*(OD^4-ID^4) = {I*1e12:.1f} mm^4")
    a(f"  k     = 3*E*I/L^3         = {k:.3e} N/m")
    a(f"  m_eff = m_tip + 0.23*m_mast = {m_eff*1e3:.1f} g "
      f"(m_tip 200 g + 0.23*{m_mast*1e3:.1f} g)")
    a(f"  f1    = (1/2pi)*sqrt(k/m_eff) = {f1:.1f} Hz")
    a(f"  cross-check vs sweep value {rec.f1:.1f} Hz: delta = {abs(f1-rec.f1):.3f} Hz "
      f"({'OK' if abs(f1-rec.f1) < 0.5 else 'MISMATCH'})")
    a("=" * 88)
    return out


def _fmt_lines(sec: SectionProps, cases: list[CantileverResult], f1: float, k_eff: float, m_eff: float) -> list[str]:
    """Build the human-readable report as a list of lines."""
    L_mm = L * 1e3
    out: list[str] = []
    a = out.append

    a("=" * 72)
    a("LiDAR MAST — HAND CALCULATION (analytical baseline for item-16 FEA)")
    a("=" * 72)
    a("")
    a("ASSUMPTIONS (all values labelled ASSUMED; LiDAR item 15 not yet locked)")
    a("-" * 72)
    a(f"  Geometry   : L = {L_mm:.1f} mm (= moment arm), OD = {OD*1e3:.1f} mm, "
      f"wall t = {WALL_T*1e3:.2f} mm, ID = {ID*1e3:.2f} mm   [ASSUMED]")
    a(f"  Material   : 6061-T6 Al, E = {E/1e9:.1f} GPa, "
      f"sigma_yield = {SIGMA_YIELD/1e6:.0f} MPa, rho = {RHO:.0f} kg/m^3   [ASSUMED]")
    a(f"  Tip mass   : m_tip = {M_TIP:.3f} kg (RPLIDAR-class 2D + bracket)   [ASSUMED]")
    a(f"  Maneuver a : a_lat_peak = {A_LAT_PEAK:.1f} m/s^2 (~{A_LAT_PEAK/G:.2f} g)   "
      f"[MEASURED, clean lap]")
    a(f"  Crash a    : {A_CRASH_G:.0f} g = {A_CRASH:.0f} m/s^2 (stated shock level)   [ASSUMED]")
    a(f"  Safety fac : SF_maneuver = {SF_MANEUVER:.1f}, SF_crash = {SF_CRASH:.1f}   [ASSUMED]")
    a("")
    a("SECTION PROPERTIES (derived)")
    a("-" * 72)
    a(f"  A           = {sec.area*1e6:10.3f} mm^2")
    a(f"  I           = {sec.I*1e12:10.3f} mm^4   ( {sec.I:.4e} m^4 )")
    a(f"  c = OD/2    = {sec.c*1e3:10.3f} mm")
    a(f"  mass/length = {sec.mass_per_len*1e3:10.3f} g/m")
    a(f"  mast mass   = {sec.mast_mass*1e3:10.3f} g")
    a("")
    a("LOAD CASES (cantilever, tip point load, fixed root)")
    a("-" * 72)
    header = (f"  {'case':<12}{'F [N]':>10}{'M [N.m]':>12}"
              f"{'sigma[MPa]':>12}{'delta[mm]':>12}{'SF_yield':>10}{'verdict':>10}")
    a(header)
    a("  " + "-" * (len(header) - 2))
    for r in cases:
        verdict = "PASS" if r.sf_yield >= r.sf else "FAIL"
        a(f"  {r.label:<12}{r.force:>10.2f}{r.moment:>12.3f}"
          f"{r.sigma/1e6:>12.2f}{r.delta*1e3:>12.4f}{r.sf_yield:>10.2f}{verdict:>10}")
    a("")
    a("  Notes per case:")
    for r in cases:
        flag = "" if r.sf_yield >= r.sf else "  <-- BELOW TARGET SF, redesign"
        a(f"    {r.label:<10}: applied SF = {r.sf:.1f}, realized yield margin "
          f"= {r.sf_yield:.2f}{flag}")
    a("")
    a("FIRST NATURAL FREQUENCY (Rayleigh tip-mass model; load-independent)")
    a("-" * 72)
    a(f"  k_eff = 3 E I / L^3        = {k_eff:.3e} N/m")
    a(f"  m_eff = m_tip + 0.23*m_mast= {m_eff*1e3:.3f} g  "
      f"(m_tip={M_TIP*1e3:.0f} g + 0.23*{sec.mast_mass*1e3:.1f} g)")
    a(f"  f1    = (1/2pi) sqrt(k/m)  = {f1:.1f} Hz")
    a("")
    a("  Acceptance: f1 must clear the 100 Hz control rate AND the low-hundreds")
    a(f"  -Hz motor/drivetrain band by >=2x => f1 >= {F1_MIN_HZ:.0f} Hz.")
    if f1 >= F1_MIN_HZ:
        a(f"  RESULT: f1 = {f1:.1f} Hz >= {F1_MIN_HZ:.0f} Hz  -> PASS "
          f"(margin {f1/CONTROL_RATE_HZ:.1f}x over 100 Hz control rate).")
    else:
        a(f"  RESULT: f1 = {f1:.1f} Hz <  {F1_MIN_HZ:.0f} Hz  -> FAIL "
          f"-> stiffer/shorter mast or larger section required.")
    a("")
    a("MATERIAL ALTERNATIVE")
    a("-" * 72)
    a("  Carbon-fiber tube (roughly E ~ 70-130 GPa axial, rho ~ 1600 kg/m^3)")
    a("  would raise f1 and cut mass, but is anisotropic with no single yield")
    a("  point; aluminum is used here as the conservative, well-defined baseline.")
    a("")
    a("This hand calc is the ground truth the item-16 static FEA must match")
    a("within ~10-15% (away from stress concentrations) before the")
    a("detailed-geometry FEA is trusted.")
    a("=" * 72)
    return out


def main() -> None:
    sec = section_properties(OD, ID, L, RHO)

    maneuver = evaluate_load_case(
        "maneuver", A_LAT_PEAK, SF_MANEUVER, sec,
        length=L, E=E, sigma_yield=SIGMA_YIELD, m_tip=M_TIP,
    )
    crash = evaluate_load_case(
        "crash", A_CRASH, SF_CRASH, sec,
        length=L, E=E, sigma_yield=SIGMA_YIELD, m_tip=M_TIP,
    )
    f1, k_eff, m_eff = first_natural_frequency(sec, length=L, E=E, m_tip=M_TIP)

    # --- internal sanity checks (cheap asserts; catch unit slips) ---
    # 0.20 kg at ~2 g without SF is ~3.9 N; with SF=2 it is ~7.9 N.
    assert abs(M_TIP * A_LAT_PEAK - 3.88) < 0.1, "maneuver base force off (unit slip?)"
    assert 1e-10 < sec.I < 1e-7, f"I out of physical range for a ~16 mm tube: {sec.I}"
    assert 100.0 < f1 < 5000.0, f"f1 physically implausible for a short Al mast: {f1}"
    assert maneuver.sigma < SIGMA_YIELD, "maneuver stress exceeds yield — check inputs"

    lines = _fmt_lines(sec, [maneuver, crash], f1, k_eff, m_eff)
    report = "\n".join(lines)
    print(report)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "summary.txt").write_text(report + "\n")
    print(f"\n[written] {RUN_DIR / 'summary.txt'}")

    # --- DESIGN SWEEP (frequency fix) ---------------------------------------
    candidates, baseline_c, recommended = run_design_sweep()

    # The recommended design must clear BOTH the modal guard and the crash SF.
    assert recommended.f1 >= F1_MIN_HZ, (
        f"recommended f1 {recommended.f1:.1f} Hz below {F1_MIN_HZ:.0f} Hz guard")
    assert recommended.sf_crash >= SF_CRASH, (
        f"recommended crash SF {recommended.sf_crash:.2f} below {SF_CRASH:.1f}")
    # Baseline must reproduce the known failing f1 (guards against drift).
    assert abs(baseline_c.f1 - 163.8) < 0.5, (
        f"baseline f1 drifted from the documented 163.8 Hz: {baseline_c.f1:.1f}")

    sweep_lines = _fmt_sweep_lines(candidates, baseline_c, recommended)
    sweep_lines += [""] + _hand_sanity_check_recommended(recommended)
    sweep_report = "\n".join(sweep_lines)
    print("\n" + sweep_report)

    (RUN_DIR / "design_sweep.txt").write_text(sweep_report + "\n")
    print(f"\n[written] {RUN_DIR / 'design_sweep.txt'}")


if __name__ == "__main__":
    main()
