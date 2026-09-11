"""Fail-closed fixture target/observation comparison; never a hardware release."""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "cad/roboracer/fixture-contract.json"
DIMENSIONS = {
    "tube_volume": "mm^3", "mast_length": "mm", "mast_outer_diameter": "mm",
    "mast_wall_thickness": "mm", "clamp_engagement": "mm", "clamp_bolt_pitch": "mm",
    "lidar_bracket_bolt_pitch": "mm", "optical_center_offset": "mm",
    "actual_load_height": "mm", "root_rotation_station_spacing": "mm",
}
ACCESS = {"tip_x", "tip_y", "root_x", "root_y", "rotation"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, positive=False):
    require(type(value) in (int, float) and math.isfinite(value), "unresolved/nonfinite numerical input")
    require(not positive or value > 0, "numerical input must be positive")
    return value


def filled(value):
    require(isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {"pending", "unknown", "tbd"}, "unresolved identity/source")


def check_draft(contract):
    require(type(contract) is dict and type(contract.get("schema_version")) is int and contract["schema_version"] == 1, "unsupported schema")
    require(contract.get("status") in {"draft_blocked", "reviewed_model_contract"}, "invalid contract status")
    dimensions = contract.get("dimensions")
    require(type(dimensions) is dict and set(dimensions) == set(DIMENSIONS), "missing/extra dimensions")
    for key, unit in DIMENSIONS.items():
        item = dimensions[key]
        require(type(item) is dict and set(item) == {"value", "unit", "tolerance_abs", "source"}, "invalid dimension record")
        require(item["unit"] == unit, "incorrect dimension unit")
        if item["value"] is not None:
            number(item["value"], positive=key != "optical_center_offset")
        if item["tolerance_abs"] is not None:
            number(item["tolerance_abs"], positive=True)
    require(type(contract.get("indicator_access")) is dict and set(contract["indicator_access"]) == ACCESS, "missing indicator access")
    return "DRAFT_BLOCKED" if contract["status"] == "draft_blocked" else "SCHEMA_ONLY"


def coordinates(value):
    require(type(value) is list and len(value) >= 2, "missing bolt coordinates")
    for point in value:
        require(type(point) is list and len(point) == 3, "expected bolt x/y/z")
        for component in point:
            number(component)
    require(len({tuple(p) for p in value}) == len(value), "duplicate bolt coordinates")


def compare_geometry(contract, observations):
    check_draft(contract)
    require(contract["status"] == "reviewed_model_contract", "unresolved: contract is not reviewed")
    for key in ("datum", "drawing_revision", "reviewed_by", "bolt_source"):
        filled(contract.get(key))
    for value in contract["indicator_access"].values():
        filled(value)
    require(type(observations) is dict, "missing geometry observations")
    for key in ("datum", "drawing_revision"):
        require(observations.get(key) == contract[key], "geometry identity/datum mismatch")
    observed = observations.get("dimensions")
    units = observations.get("units")
    require(type(observed) is dict and set(observed) == set(DIMENSIONS), "missing/extra geometry dimensions")
    require(type(units) is dict and units == DIMENSIONS, "geometry units mismatch")
    for key, item in contract["dimensions"].items():
        expected = number(item["value"], positive=key != "optical_center_offset")
        tolerance = number(item["tolerance_abs"], positive=True)
        filled(item["source"])
        actual = number(observed[key], positive=key != "optical_center_offset")
        require(abs(actual - expected) <= tolerance, f"{key} outside tolerance")
    targets = {key: item["value"] for key, item in contract["dimensions"].items()}
    for values in (targets, observed):
        od, wall = values["mast_outer_diameter"], values["mast_wall_thickness"]
        require(2 * wall < od, "invalid tube wall/OD")
        volume = math.pi / 4 * (od**2 - (od - 2 * wall)**2) * values["mast_length"]
        require(abs(values["tube_volume"] - volume) <= contract["dimensions"]["tube_volume"]["tolerance_abs"], "tube reference-segment volume inconsistent with dimensions")
    coordinates(contract.get("bolt_coordinates_mm"))
    coordinates(observations.get("bolt_coordinates_mm"))
    tolerance = number(contract.get("bolt_coordinate_tolerance_mm"), positive=True)
    expected = contract["bolt_coordinates_mm"]
    actual = observations["bolt_coordinates_mm"]
    require(len(actual) == len(expected), "bolt count mismatch")
    for target, point in zip(expected, actual):
        require(all(abs(a - b) <= tolerance for a, b in zip(target, point)), "bolt coordinate outside tolerance")
    return "MODEL_GEOMETRY_MATCH_ONLY"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT)
    parser.add_argument("--geometry", type=Path, help="Reviewed CAD observation JSON; not a screenshot")
    parser.add_argument("--check-draft", action="store_true", help="Schema only; never release readiness")
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text())
        if args.check_draft:
            require(args.geometry is None, "draft check cannot compare geometry")
            print(check_draft(contract))
        else:
            require(args.geometry is not None, "missing --geometry observations")
            print(compare_geometry(contract, json.loads(args.geometry.read_text())))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")


if __name__ == "__main__":
    main()
