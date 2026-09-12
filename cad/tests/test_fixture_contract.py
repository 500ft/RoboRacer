"""Synthetic contract controls are not measured fixture or geometry evidence."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("fixture_contract", ROOT / "cad/fixture_contract.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def complete():
    contract = json.loads(module.DEFAULT.read_text())
    contract["status"] = "reviewed_model_contract"
    contract["datum"] = "SYNTHETIC root origin; z free axis; x/y transverse"
    contract["reviewed_by"] = "SYNTHETIC ONLY"
    contract["drawing_revision"] = "synthetic-1"
    for item in contract["dimensions"].values():
        item.update(value=10.0, tolerance_abs=0.1, source="synthetic drawing")
    for key, value in {"mast_outer_diameter": 20.0, "mast_wall_thickness": 1.5,
                       "mast_length": 100.0, "tube_volume": math.pi / 4 * (20**2 - 17**2) * 100}.items():
        contract["dimensions"][key]["value"] = value
    contract["bolt_coordinates_mm"] = [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]]
    contract["bolt_coordinate_tolerance_mm"] = 0.1
    contract["bolt_source"] = "synthetic drawing"
    contract["indicator_access"] = {key: "synthetic reviewed access" for key in ("tip_x", "tip_y", "root_x", "root_y", "rotation")}
    observations = dict(drawing_revision="synthetic-1", datum=contract["datum"],
                        dimensions={k: v["value"] for k, v in contract["dimensions"].items()},
                        units={k: v["unit"] for k, v in contract["dimensions"].items()},
                        bolt_coordinates_mm=copy.deepcopy(contract["bolt_coordinates_mm"]))
    return contract, observations


def test_committed_draft_is_not_geometry_acceptance():
    contract = json.loads(module.DEFAULT.read_text())
    assert module.check_draft(contract) == "DRAFT_BLOCKED"
    with pytest.raises(ValueError, match="unresolved|reviewed"):
        module.compare_geometry(contract, {})


def test_synthetic_geometry_match_is_explicitly_limited():
    contract, observations = complete()
    assert module.compare_geometry(contract, observations) == "MODEL_GEOMETRY_MATCH_ONLY"


@pytest.mark.parametrize("change", ["wall", "volume"])
def test_impossible_tube_targets_are_not_reviewable(change):
    contract, observations = complete()
    key, value = ("mast_wall_thickness", 11.0) if change == "wall" else ("tube_volume", 100.0)
    contract["dimensions"][key]["value"] = value
    observations["dimensions"][key] = value
    with pytest.raises(ValueError): module.compare_geometry(contract, observations)


@pytest.mark.parametrize("change", ["missing", "pending", "nan", "bool", "tolerance", "datum", "bolts", "access", "unit", "source"])
def test_incomplete_or_invalid_contract_rejected(change):
    contract, observations = complete()
    item = contract["dimensions"]["clamp_engagement"]
    if change == "missing": del contract["dimensions"]["clamp_engagement"]
    if change == "pending": item["value"] = None
    if change == "nan": item["value"] = float("nan")
    if change == "bool": item["value"] = True
    if change == "tolerance": item["tolerance_abs"] = 0
    if change == "datum": contract["datum"] = None
    if change == "bolts": contract["bolt_coordinates_mm"] = []
    if change == "access": del contract["indicator_access"]["rotation"]
    if change == "unit": item["unit"] = "m"
    if change == "source": item["source"] = None
    with pytest.raises(ValueError): module.compare_geometry(contract, observations)


@pytest.mark.parametrize("change", ["outside", "missing", "nan", "unit", "datum", "bolts", "bolt_count", "revision"])
def test_bad_geometry_rejected(change):
    contract, observations = complete()
    if change == "outside": observations["dimensions"]["clamp_engagement"] = 10.2
    if change == "missing": del observations["dimensions"]["clamp_engagement"]
    if change == "nan": observations["dimensions"]["clamp_engagement"] = float("inf")
    if change == "unit": observations["units"]["clamp_engagement"] = "m"
    if change == "datum": observations["datum"] = "different origin"
    if change == "bolts": observations["bolt_coordinates_mm"][0][1] = 0.2
    if change == "bolt_count": observations["bolt_coordinates_mm"].pop()
    if change == "revision": observations["drawing_revision"] = "stale"
    with pytest.raises(ValueError): module.compare_geometry(contract, observations)


def test_cli_fails_closed_without_geometry():
    result = subprocess.run([sys.executable, str(ROOT / "cad/fixture_contract.py")], capture_output=True, text=True)
    assert result.returncode == 2
    assert "BLOCKED" in result.stderr
