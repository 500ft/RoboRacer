#!/usr/bin/env python3
"""Static-fixture geometry contract for the RoboRacer mast, derived from the register.

usage: python cad/fixture_contract.py            # (re)write cad/roboracer/fixture-contract.json
       python cad/fixture_contract.py --check    # fail if the committed contract is stale
       python cad/fixture_contract.py --release  # exit 2 REFUSED while any clause is pending

This is the geometry contract that docs/CAD_MEASUREMENT_CONTRACT.md and
cad/roboracer/fixture-preparation.md require BEFORE any fixture model exists. It names every
quantity a fixture model must be compared against, derives the ones the register can support
(specimen stiffness, minimum fixture stiffness, quantization terms) from registered rows only,
and carries every unmeasured interface as a pending clause. It models nothing and measures
nothing: a clause becoming evaluable requires the register row to be filled by inspection or
an owner decision, never by this script. Evidence states are carried through from the register.
"""
from __future__ import annotations
import argparse, csv, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "cad/roboracer/parameters.csv"
OUTPUT = ROOT / "cad/roboracer/fixture-contract.json"
CONTRACT_VERSION = "2026-09-11"
# Register rows the fixture contract consumes, with the unit the formulas assume.
UNITS = {
    "mast_length": "mm", "mast_outer_diameter": "mm", "mast_wall_thickness": "mm",
    "youngs_modulus": "N/mm^2", "density": "kg/m^3", "tip_total_mass": "kg",
    "indicator_resolution_limit": "mm", "fixture_stiffness_ratio_min": "1",
    "force_target_1": "N", "force_target_5": "N",
    "clamp_engagement": "mm", "clamp_bolt_pitch": "mm", "lidar_bracket_bolt_pitch": "mm",
    "optical_center_offset": "mm", "actual_load_height": "mm", "root_rotation_station_spacing": "mm",
}
# Worst-first ordering used to summarise the evidence state of a derived clause.
STATE_RANK = ["pending", "model_assumption", "reported_vendor_nominal", "design_choice",
              "committed_simulation", "protocol"]


class ContractInputError(ValueError):
    """The register cannot support the contract as written. Fail closed."""


def load_register(path: Path = REGISTER) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    have = {}
    for row in rows:
        if row["parameter"] in have:
            raise ContractInputError("duplicate parameter in register: " + row["parameter"])
        have[row["parameter"]] = row
    out = {}
    for name, unit in UNITS.items():
        if name not in have:
            raise ContractInputError("required parameter missing from register: " + name)
        r = have[name]
        if r["unit"].strip() != unit:
            raise ContractInputError(f"unit mismatch for {name}: register {r['unit']!r}, contract expects {unit!r}")
        state = r["evidence_state"].strip()
        raw = r["value"].strip()
        if state == "pending":
            if raw:
                raise ContractInputError("pending parameter carries a value; refuse to treat it as measured: " + name)
            out[name] = dict(value=None, state="pending", source=r["source"], release=r["release_requirement"])
            continue
        try:
            value = float(raw)
        except ValueError:
            raise ContractInputError(f"non-numeric value for {name}: {raw!r}")
        if not math.isfinite(value) or value <= 0:
            raise ContractInputError(f"value must be finite and positive: {name}={raw}")
        out[name] = dict(value=value, state=state, source=r["source"], release=r["release_requirement"])
    return out


def _state(*names, reg):
    states = [reg[n]["state"] for n in names]
    return min(states, key=lambda s: STATE_RANK.index(s) if s in STATE_RANK else len(STATE_RANK))


def _clause(cid, requirement, inputs, reg, *, value=None, unit=None, formula=None,
            verification=None, axes=None, note=None):
    pending = [n for n in inputs if reg[n]["state"] == "pending"]
    c = {"id": cid, "requirement": requirement, "inputs": list(inputs),
         "status": "pending" if pending else "evaluable",
         "evidence_state": _state(*inputs, reg=reg) if inputs else "protocol"}
    if pending:
        c["pending_inputs"] = pending
        c["release_requirement"] = {n: reg[n]["release"] for n in pending}
    if formula: c["formula"] = formula
    if value is not None: c["value"] = value
    if unit: c["unit"] = unit
    if axes: c["axes"] = axes
    if verification: c["verification"] = verification
    if note: c["note"] = note
    return c


def build(reg: dict) -> dict:
    L, D, t = (reg[k]["value"] for k in ("mast_length", "mast_outer_diameter", "mast_wall_thickness"))
    E = reg["youngs_modulus"]["value"]
    if 2 * t >= D:
        raise ContractInputError(f"wall {t} mm leaves no bore in a {D} mm tube")
    d = D - 2 * t
    I = math.pi * (D**4 - d**4) / 64                       # mm^4
    k = 3 * E * I / L**3                                   # N/mm
    ratio = reg["fixture_stiffness_ratio_min"]["value"]
    res = reg["indicator_resolution_limit"]["value"]       # mm
    q_um = res * 1e3 / math.sqrt(12)                       # uniform quantization std, micrometres
    diff_um = q_um * math.sqrt(2)                          # difference of two independent readings
    f_lo, f_hi = reg["force_target_1"]["value"], reg["force_target_5"]["value"]
    geom = ("mast_length", "mast_outer_diameter", "mast_wall_thickness", "youngs_modulus")
    clauses = [
        _clause("effective_free_length", "Inspected effective free length from clamp datum to load line equals the registered mast_length",
                ["mast_length"], reg, value=L, unit="mm",
                verification=reg["mast_length"]["release"]),
        _clause("specimen_bending_stiffness", "Ideal cantilever stiffness of the registered specimen; the scale every fixture term is compared against",
                geom, reg, value=k, unit="N/mm", formula="k = 3*E*I/L^3, I = pi*(D^4 - (D-2t)^4)/64",
                note="Model quantity (E is a model_assumption). Recompute from the as-built stiffness once inspected; not an as-built value."),
        _clause("fixture_translational_stiffness_min", "Load-point fixture translational stiffness >= fixture_stiffness_ratio_min x specimen stiffness on EACH axis at the actual force line",
                geom + ("fixture_stiffness_ratio_min",), reg, value=ratio * k, unit="N/mm", axes=["x", "y"],
                formula="k_fixture_min = fixture_stiffness_ratio_min * k",
                verification="Physical commissioning at the load point; a rigid CAD solid is not stiffness evidence. Ratio does not bound root rotation."),
        _clause("indicator_resolution", "Independent tip AND root indicator stations, each at or below indicator_resolution_limit, with fixed reference supports and recorded measurement directions",
                ["indicator_resolution_limit"], reg, value=res, unit="mm", axes=["x", "y"],
                verification="Instrument IDs and calibration records in the campaign evidence"),
        _clause("ideal_tip_signal_range", "Ideal-beam tip displacement across the protocol force range, for count-resolution planning only",
                geom + ("force_target_1", "force_target_5"), reg,
                value={"at_force_target_1_um": f_lo / k * 1e3, "at_force_target_5_um": f_hi / k * 1e3}, unit="um",
                formula="delta = F / k", note="Planning scale; the frozen gate is on the fitted slope, not pointwise counts."),
        _clause("root_rotation_observation", "Root rotation is observed with two spatially separated root stations over a measured baseline; a single root translation channel cannot observe rotation",
                ["indicator_resolution_limit", "root_rotation_station_spacing", "actual_load_height"], reg,
                value={"single_station_quantization_std_um": q_um, "differential_quantization_std_um": diff_um,
                       "angular_std_urad": None, "tip_equivalent_um": None},
                formula="angular_std_urad = differential_quantization_std_um / root_rotation_station_spacing_mm * 1e3; tip_equivalent_um = angular_std_urad * actual_load_height_mm * 1e-3",
                note="Quantization-only planning terms assume independent uniform rounding; calibration, hysteresis and drift are still required in the filled error budget."),
        _clause("load_line_height", "Force line height above the clamp datum, measured; equals the lever used in every stiffness and rotation term",
                ["actual_load_height"], reg, unit="mm"),
        _clause("clamp_engagement", "Root clamp engagement length and fastener configuration reproduce the actual mast root restraint",
                ["clamp_engagement"], reg, unit="mm"),
        _clause("clamp_bolt_coordinates", "Deck-side clamp bolt pattern measured on the mating datum; full deck CAD not required",
                ["clamp_bolt_pitch"], reg, unit="mm"),
        _clause("tip_assembly_interface", "Sensor bracket bolt pattern and optical-centre offset from the exact purchased sensor revision and bracket drawing",
                ["lidar_bracket_bolt_pitch", "optical_center_offset"], reg, unit="mm"),
        _clause("tip_moving_mass", "Tip assembly mass used by the reference model equals the weighed body + bracket + moving cable; no heat-sink plate or hardware added silently",
                ["tip_total_mass"], reg, value=reg["tip_total_mass"]["value"], unit="kg",
                verification=reg["tip_total_mass"]["release"],
                note="Register value is a summed allowance (model_assumption), not a weighed assembly."),
    ]
    pending = [c["id"] for c in clauses if c["status"] == "pending"]
    return {
        "family": "mast_static_fixture",
        "contract_version": CONTRACT_VERSION,
        "status": "contract_only; no fixture geometry modelled, fabricated or measured",
        "source_parameters": "cad/roboracer/parameters.csv",
        "governing_documents": ["docs/CAD_MEASUREMENT_CONTRACT.md", "cad/roboracer/fixture-preparation.md",
                                "docs/specs/mast-physical-validation/design.md"],
        "release_gate": "A fixture model is accepted (RR-CAD-05/06) only when every clause is evaluable, each evaluable clause is met by the regenerated geometry within a declared tolerance, and the physical commissioning checks named under verification are recorded. Pending clauses are filled by inspection or owner decision in the register, never here.",
        "clauses": clauses,
        "evaluable_clauses": [c["id"] for c in clauses if c["status"] == "evaluable"],
        "pending_clauses": pending,
        "not_generated_pending_owner_inputs": sorted({n for c in clauses for n in c.get("pending_inputs", [])}),
        "evidence_note": "Derived values are model quantities from design_choice/model_assumption rows; passing a geometry comparison against them means the fixture model matches the intended design, not that an as-built fixture is stiff enough or that the campaign is ready.",
    }


def render(contract: dict) -> str:
    return json.dumps(contract, indent=1) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail if the committed contract is stale")
    mode.add_argument("--release", action="store_true", help="exit 2 REFUSED while any clause is pending")
    parser.add_argument("--parameters", type=Path, default=REGISTER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        contract = build(load_register(args.parameters))
    except ContractInputError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    text = render(contract)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != text:
            print("Fixture contract is missing or stale; run python cad/fixture_contract.py", file=sys.stderr)
            return 1
    elif args.release:
        if contract["pending_clauses"]:
            print("REFUSED: fixture contract has pending clauses: " + ", ".join(contract["pending_clauses"]), file=sys.stderr)
            return 2
    else:
        args.output.write_text(text, encoding="utf-8")
    print(f"Fixture contract {contract['contract_version']}: {len(contract['evaluable_clauses'])} evaluable, "
          f"{len(contract['pending_clauses'])} pending; nothing modelled or measured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
