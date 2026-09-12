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



# ── register-derived clauses and release gate (ported from PR #16, adapted to the merged schema) ──
import csv as _csv


def _committed():
    return json.loads(module.DEFAULT.read_text())


def _write_register(tmp_path, mutate):
    rows = list(_csv.DictReader(module.REGISTER.open(encoding="utf-8", newline="")))
    mutate(rows)
    p = tmp_path / "parameters.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return p


def test_committed_derived_section_is_current():
    assert module.derived_is_current(_committed()), "run: python cad/fixture_contract.py --refresh"


def test_derived_terms_match_measurement_contract_arithmetic():
    reg = module.load_register()
    d = module.build_derived(reg)
    by = {c["id"]: c for c in d["clauses"]}
    D, t, L, E = 20.0, 1.5, 100.0, 68900.0
    I = math.pi * (D**4 - (D - 2 * t)**4) / 64
    assert math.isclose(by["specimen_bending_stiffness"]["value"], 3 * E * I / L**3, rel_tol=1e-12)
    assert math.isclose(by["fixture_translational_stiffness_min"]["value"], 10 * 3 * E * I / L**3, rel_tol=1e-12)
    assert math.isclose(by["root_rotation_observation"]["value"]["single_station_quantization_std_um"], 1.0 / math.sqrt(12), rel_tol=1e-12)


def test_pending_clauses_cover_exactly_the_pending_register_rows():
    reg = module.load_register()
    d = module.build_derived(reg)
    pending_rows = {n for n, v in reg.items() if v["state"] == "pending"}
    assert set(d["not_generated_pending_owner_inputs"]) == pending_rows
    assert len(d["pending_clauses"]) == 5 and len(d["evaluable_clauses"]) == 6


def test_release_gate_refuses_the_committed_draft():
    blockers = module.release_blockers(_committed())
    assert any("reviewed_model_contract" in b for b in blockers)
    assert sum("derived clause pending" in b for b in blockers) == 5


def test_release_cli_exit_code_is_2_and_names_pending_clauses():
    p = subprocess.run([sys.executable, str(ROOT / "cad/fixture_contract.py"), "--release"], capture_output=True, text=True)
    assert p.returncode == 2 and "REFUSED" in p.stderr and "clamp_engagement" in p.stderr


def test_filling_a_pending_row_makes_its_clause_evaluable_positive_control(tmp_path):
    def fill(rows):
        for r in rows:
            if r["parameter"] == "clamp_engagement":
                r["value"], r["evidence_state"], r["source"] = "25", "inspection", "synthetic inspection record"
    reg = module.load_register(_write_register(tmp_path, fill))
    d = module.build_derived(reg)
    assert "clamp_engagement" in d["evaluable_clauses"] and len(d["pending_clauses"]) == 4


def test_pending_row_carrying_a_value_is_refused(tmp_path):
    def poison(rows):
        for r in rows:
            if r["parameter"] == "actual_load_height":
                r["value"] = "80"      # evidence_state stays pending
    with pytest.raises(module.ContractInputError, match="pending parameter carries a value"):
        module.load_register(_write_register(tmp_path, poison))


def test_unit_mismatch_and_missing_row_are_refused(tmp_path):
    def bad_unit(rows):
        for r in rows:
            if r["parameter"] == "mast_length": r["unit"] = "m"
    with pytest.raises(module.ContractInputError, match="unit mismatch"):
        module.load_register(_write_register(tmp_path, bad_unit))
    def drop(rows):
        rows[:] = [r for r in rows if r["parameter"] != "youngs_modulus"]
    with pytest.raises(module.ContractInputError, match="missing from register"):
        module.load_register(_write_register(tmp_path, drop))


def test_stale_derived_section_is_detected_against_a_changed_register(tmp_path):
    def bump(rows):
        for r in rows:
            if r["parameter"] == "mast_length": r["value"] = "120"
    assert not module.derived_is_current(_committed(), _write_register(tmp_path, bump))


def test_release_still_refuses_when_only_the_review_fields_are_filled():
    contract, _ = complete()          # #17's synthetic reviewed contract: targets filled, register untouched
    contract["derived_from_register"] = _committed()["derived_from_register"]
    blockers = module.release_blockers(contract)
    assert all("derived clause pending" in b for b in blockers) and len(blockers) == 5, blockers
