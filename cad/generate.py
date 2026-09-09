#!/usr/bin/env python3
"""Regenerate the RoboRacer mast tube family from the registered parameter file.

usage: python cad/generate.py --parameters cad/roboracer/parameters.csv --output <dir>

Reads ONLY parameters registered in parameters.csv. Fails closed if a required parameter
is missing, empty (pending), non-numeric, has the wrong unit, or is geometrically invalid.
Writes:
  <dir>/mast_tube.step   neutral STEP export
  <dir>/geometry.json   metrics measured on the CadQuery solid, the same metrics re-measured
                        after STEP re-import, and the analytic expectation
The reviewed contract CI checks these against is cad/contract.json. Screenshots are not
acceptance; the numbers are. Evidence states are carried through from the register: a
design_choice or vendor_nominal input does not become measured by being modelled.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from pathlib import Path

REQUIRED = {"mast_length": "mm", "mast_outer_diameter": "mm", "mast_wall_thickness": "mm", "density": "kg/m^3"}
FAMILY = "mast_tube"
NOT_GENERATED = {}

class GeometryInputError(ValueError):
    """Raised when the registered inputs cannot produce valid geometry. Fail closed."""

def load_parameters(path: Path) -> dict:
    if not path.is_file():
        raise GeometryInputError(f"parameter file not found: {path}")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    have = {}
    for row in rows:
        name = row["parameter"]
        if name in have:
            raise GeometryInputError(f"duplicate parameter in register: {name}")
        have[name] = row
    out = {}
    for name, unit in REQUIRED.items():
        if name not in have:
            raise GeometryInputError(f"required parameter missing from register: {name}")
        r = have[name]
        if r.get("value", "").strip() == "":
            raise GeometryInputError(f"required parameter has no value (evidence_state={r.get('evidence_state')}): {name}")
        if r.get("evidence_state", "").strip() in {"", "pending"}:
            raise GeometryInputError(f"required parameter has unresolved evidence state: {name}")
        if r.get("unit", "").strip() != unit:
            raise GeometryInputError(f"unit mismatch for {name}: register says {r.get('unit')!r}, generator expects {unit!r}")
        try:
            out[name] = float(r["value"])
        except ValueError:
            raise GeometryInputError(f"non-numeric value for {name}: {r['value']!r}")
        if not math.isfinite(out[name]):
            raise GeometryInputError(f"required parameter must be finite: {name}")
        out[f"{name}__evidence_state"] = r.get("evidence_state", "")
    out["__pending_in_register"] = sorted(n for n, r in have.items() if r.get("value", "").strip() == "")
    return out

def validate(p: dict) -> None:
    L, D, t = p["mast_length"], p["mast_outer_diameter"], p["mast_wall_thickness"]
    if L <= 0 or D <= 0 or t <= 0:
        raise GeometryInputError(f"non-positive dimension: L={L} D={D} t={t}")
    if 2 * t >= D:
        raise GeometryInputError(f"wall {t} mm leaves no bore in a {D} mm tube (need 2t < D)")
    if p["density"] <= 0:
        raise GeometryInputError("density must be positive")

def analytic(p: dict) -> dict:
    L, D, t = p["mast_length"], p["mast_outer_diameter"], p["mast_wall_thickness"]
    d = D - 2 * t
    vol = math.pi / 4 * (D**2 - d**2) * L
    return {"volume_mm3": vol, "mass_kg": vol * 1e-9 * p["density"], "bbox_mm": [D, D, L], "inner_diameter_mm": d}

def build(p: dict):
    import cadquery as cq
    L, D, t = p["mast_length"], p["mast_outer_diameter"], p["mast_wall_thickness"]
    return cq.Workplane("XY").circle(D / 2).circle(D / 2 - t).extrude(L)

def measure(solid) -> dict:
    v = solid.val(); bb = v.BoundingBox()
    return {"volume_mm3": float(v.Volume()), "bbox_mm": [float(bb.xlen), float(bb.ylen), float(bb.zlen)],
            "n_solids": len(solid.solids().vals())}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def versions() -> dict:
    import platform, importlib.metadata as md
    v = {"python": platform.python_version()}
    for k in ("cadquery", "cadquery-ocp", "numpy", "pytest"):
        try: v[k] = md.version(k)
        except md.PackageNotFoundError: pass
    try:
        import OCP; v["OCP"] = getattr(OCP, "__version__", "unknown")
        v["ocp"] = v["OCP"]  # conda-forge package name; pip uses cadquery-ocp
        # Conda-forge may provide OCP without Python distribution metadata.
        v.setdefault("cadquery-ocp", v["OCP"])
    except Exception: pass
    return v

def generate(parameters: Path, output: Path) -> dict:
    import cadquery as cq
    p = load_parameters(parameters); validate(p)
    output.mkdir(parents=True, exist_ok=True)
    solid = build(p)
    step = output / f"{FAMILY}.step"
    cq.exporters.export(solid, str(step))
    reimported = cq.importers.importStep(str(step))
    direct, roundtrip = measure(solid), measure(reimported)
    for m in (direct, roundtrip):
        m["mass_kg"] = m["volume_mm3"] * 1e-9 * p["density"] if "density" in p else None
    result = {
        "family": FAMILY, "parameters_file": str(parameters), "parameters_sha256": sha256(parameters),
        "inputs": {k: v for k, v in p.items() if not k.startswith("__")},
        "analytic": analytic(p), "measured_direct": direct, "measured_after_step_reimport": roundtrip,
        "step_file": step.name, "step_sha256": sha256(step), "versions": versions(),
        "not_generated_pending_owner_inputs": {k: v for k, v in NOT_GENERATED.items()},
        "pending_parameters_in_register": p["__pending_in_register"],
    }
    (output / "geometry.json").write_text(json.dumps(result, indent=1) + "\n")
    return result

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parameters", required=True, type=Path); ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    try:
        r = generate(a.parameters, a.output)
    except GeometryInputError as e:
        print(f"REFUSED: {e}", file=sys.stderr); return 2
    m = r["measured_direct"]
    mass = f"  mass {m['mass_kg']*1000:.3f} g" if m.get("mass_kg") is not None else ""
    print(f"{FAMILY}: volume {m['volume_mm3']:.3f} mm^3{mass}  bbox {[round(x, 3) for x in m['bbox_mm']]}  -> {a.output}")
    if r["not_generated_pending_owner_inputs"]:
        print("not generated (pending owner inputs): " + ", ".join(r["not_generated_pending_owner_inputs"]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
