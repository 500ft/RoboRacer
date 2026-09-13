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


def _release_grade_register(tmp_path, contract=None):
    """A synthetic register with every row filled at a release-grade state, for tests that need a
    COMPLETE contract. Shared quantities take the synthetic contract's own targets so the two
    representations agree by construction. Nothing in it is a measurement."""
    contract = contract or complete()[0]
    rows = list(_csv.DictReader(module.REGISTER.open(encoding="utf-8", newline="")))
    for r in rows:
        if r["evidence_state"] == "pending":
            shared = contract["dimensions"].get(r["parameter"], {}).get("value")
            r["value"], r["evidence_state"], r["source"] = (str(shared) if shared is not None else "25"), "inspection", "synthetic inspection record"
        elif r["evidence_state"] in ("model_assumption", "design_choice", "reported_vendor_nominal", "committed_simulation"):
            r["evidence_state"], r["source"] = "inspection", "synthetic inspection record"
    p = tmp_path / "parameters.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return p


def _complete_with_register(tmp_path):
    contract, observations = complete()
    reg = _release_grade_register(tmp_path, contract)
    contract["derived_from_register"] = module.build_derived(module.load_register(reg))
    return contract, observations, reg


def test_synthetic_geometry_match_is_explicitly_limited(tmp_path):
    contract, observations, reg = _complete_with_register(tmp_path)
    assert module.complete_contract_blockers(contract, reg) == []
    assert module.compare_geometry(contract, observations, reg) == "MODEL_GEOMETRY_MATCH_ONLY"


def test_geometry_mode_refuses_the_same_incomplete_contract_release_refuses(tmp_path):
    # Review 2026-09-12: release and geometry must use ONE complete-contract schema.
    contract, observations, reg = _complete_with_register(tmp_path)
    contract["indicator_access"]["root_x"] = None
    assert any("indicator_access.root_x" in b for b in module.complete_contract_blockers(contract, reg))
    with pytest.raises(ValueError, match="not complete"):
        module.compare_geometry(contract, observations, reg)


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
    assert sum("derived clause pending" in b for b in blockers) == 5, blockers
    assert any("not release-grade" in b for b in blockers), "design_choice/model_assumption rows must block release"


# ── review 2026-09-12: RELEASABLE was returned on placeholders, missing metrology fields, not_evidence rows ──
def test_placeholder_review_strings_are_blockers(tmp_path):
    contract, _, reg = _complete_with_register(tmp_path)
    contract["reviewed_by"], contract["bolt_source"], contract["datum"] = "TBD", "?", "x"
    b = module.complete_contract_blockers(contract, reg)
    assert sum("placeholder" in x for x in b) == 3, b


def test_missing_indicator_positions_and_bolt_tolerance_are_blockers(tmp_path):
    contract, _, reg = _complete_with_register(tmp_path)
    contract["indicator_access"] = {k: None for k in contract["indicator_access"]}
    contract["bolt_coordinate_tolerance_mm"] = None
    b = module.complete_contract_blockers(contract, reg)
    assert sum("indicator_access." in x for x in b) == 5 and any("bolt_coordinate_tolerance_mm" in x for x in b), b


def test_malformed_targets_are_blockers(tmp_path):
    contract, _, reg = _complete_with_register(tmp_path)
    contract["bolt_coordinates_mm"] = [[0, 0]]                       # x/y only
    contract["dimensions"]["tube_volume"]["value"] = 1.0             # inconsistent with OD/wall/length
    contract["dimensions"]["mast_length"]["tolerance_abs"] = -1
    b = module.complete_contract_blockers(contract, reg)
    assert any("bolt_coordinates_mm malformed" in x for x in b) and any("tube_volume target" in x for x in b) and any("tolerance -1" in x for x in b), b


def test_unsupported_evidence_state_and_missing_source_are_refused(tmp_path):
    def poison(rows):
        for r in rows:
            if r["evidence_state"] == "pending": r["value"], r["evidence_state"], r["source"] = "1", "not_evidence", ""
    with pytest.raises(module.ContractInputError, match="unsupported evidence_state"):
        module.load_register(_write_register(tmp_path, poison))
    def sourceless(rows):
        for r in rows:
            if r["parameter"] == "mast_length": r["source"] = ""
    with pytest.raises(module.ContractInputError, match="no source"):
        module.load_register(_write_register(tmp_path, sourceless))


def test_release_cli_complete_verdict_is_input_review_only(tmp_path):
    contract, _, reg = _complete_with_register(tmp_path)
    cp = tmp_path / "c.json"; cp.write_text(json.dumps(contract))
    p = subprocess.run([sys.executable, str(ROOT / "cad/fixture_contract.py"), "--release", "--contract", str(cp), "--parameters", str(reg)], capture_output=True, text=True)
    assert p.returncode == 0 and "CONTRACT_COMPLETE" in p.stdout and "not claimed" in p.stdout, p.stdout + p.stderr



# ── review 2 (2026-09-12): halves consistent within themselves but not with each other; --geometry ignored --parameters ──
def test_contract_target_must_agree_with_register_value(tmp_path):
    contract, observations, reg = _complete_with_register(tmp_path)
    contract["dimensions"]["mast_length"]["value"] = 1000.0; observations["dimensions"]["mast_length"] = 1000.0
    contract["dimensions"]["tube_volume"]["value"] = math.pi / 4 * (20**2 - 17**2) * 1000; observations["dimensions"]["tube_volume"] = contract["dimensions"]["tube_volume"]["value"]
    b = module.complete_contract_blockers(contract, reg)
    assert any(x.startswith("mast_length: contract target 1000.0 differs from register value 100") for x in b), b
    with pytest.raises(ValueError, match="differs from register"):
        module.compare_geometry(contract, observations, reg)


def test_geometry_cli_honours_parameters_and_accepts_a_valid_custom_register(tmp_path):
    contract, observations, reg = _complete_with_register(tmp_path)
    contract["drawing_revision"] = "A3"; observations["drawing_revision"] = "A3"      # short identifiers are not placeholders
    cp, op = tmp_path / "c.json", tmp_path / "o.json"; cp.write_text(json.dumps(contract)); op.write_text(json.dumps(observations))
    ok = subprocess.run([sys.executable, str(ROOT / "cad/fixture_contract.py"), "--geometry", str(op), "--contract", str(cp), "--parameters", str(reg)], capture_output=True, text=True)
    assert ok.returncode == 0 and "MODEL_GEOMETRY_MATCH_ONLY" in ok.stdout, ok.stdout + ok.stderr
    default = subprocess.run([sys.executable, str(ROOT / "cad/fixture_contract.py"), "--geometry", str(op), "--contract", str(cp)], capture_output=True, text=True)
    assert default.returncode != 0, "with the committed (pending) register the same contract must not pass"


def test_short_revision_identifier_is_not_a_placeholder():
    assert not module._is_placeholder("A3") and not module._is_placeholder("R2")
    assert module._is_placeholder("TBD") and module._is_placeholder("") and module._is_placeholder("?")
