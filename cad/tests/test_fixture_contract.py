"""Fixture geometry contract: derived from the register, fail-closed, no measurement supplied."""
import csv, importlib.util, json, math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("fixture_contract", ROOT / "cad/fixture_contract.py")
FC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FC)

MEASUREMENT_CONTRACT = ROOT / "docs/CAD_MEASUREMENT_CONTRACT.md"


def _rows():
    return list(csv.DictReader(FC.REGISTER.open(newline="")))


def _write(rows, path):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return path


def test_committed_contract_is_current():
    assert FC.main(["--check"]) == 0


def test_derived_terms_match_measurement_contract_arithmetic():
    c = FC.build(FC.load_register())
    by = {cl["id"]: cl for cl in c["clauses"]}
    # Same numbers docs/CAD_MEASUREMENT_CONTRACT.md reproduces by hand.
    assert by["specimen_bending_stiffness"]["value"] == pytest.approx(775.9836594264038, rel=1e-12)
    assert by["fixture_translational_stiffness_min"]["value"] == pytest.approx(7759.836594264038, rel=1e-12)
    assert by["fixture_translational_stiffness_min"]["axes"] == ["x", "y"]
    assert by["ideal_tip_signal_range"]["value"]["at_force_target_1_um"] == pytest.approx(5.15474772104962, rel=1e-12)
    rot = by["root_rotation_observation"]["value"]
    assert rot["single_station_quantization_std_um"] == pytest.approx(1 / math.sqrt(12), rel=1e-12)
    assert rot["differential_quantization_std_um"] == pytest.approx(math.sqrt(2) / math.sqrt(12), rel=1e-12)
    assert rot["angular_std_urad"] is None and rot["tip_equivalent_um"] is None
    text = MEASUREMENT_CONTRACT.read_text()
    assert "775.984" in text and "7,759.84" in text and "0.408" in text


def test_pending_clauses_cover_exactly_the_pending_register_rows():
    pending_rows = {r["parameter"] for r in _rows() if r["evidence_state"] == "pending"}
    c = FC.build(FC.load_register())
    assert set(c["not_generated_pending_owner_inputs"]) == pending_rows
    assert c["pending_clauses"], "contract must stay fail-closed while the register has pending rows"
    for cl in c["clauses"]:
        if cl["status"] == "pending":
            assert cl.get("value") is None or None in cl["value"].values()
            assert set(cl["pending_inputs"]) <= pending_rows
        else:
            assert cl["evidence_state"] != "pending"


def test_release_gate_refuses_while_pending(capsys):
    assert FC.main(["--release"]) == 2
    assert "REFUSED" in capsys.readouterr().err


def test_filling_a_pending_row_makes_its_clause_evaluable_positive_control(tmp_path):
    rows = _rows()
    for r in rows:
        if r["parameter"] == "actual_load_height":
            r["value"], r["evidence_state"] = "100", "design_choice"   # synthetic, test-only
    c = FC.build(FC.load_register(_write(rows, tmp_path / "p.csv")))
    by = {cl["id"]: cl for cl in c["clauses"]}
    assert by["load_line_height"]["status"] == "evaluable"
    assert by["root_rotation_observation"]["status"] == "pending"      # spacing still pending
    assert "actual_load_height" not in c["not_generated_pending_owner_inputs"]


def test_pending_row_carrying_a_value_is_refused(tmp_path):
    rows = _rows()
    for r in rows:
        if r["parameter"] == "clamp_engagement":
            r["value"] = "25"   # pending state must not smuggle a number in
    with pytest.raises(FC.ContractInputError, match="pending parameter carries a value"):
        FC.load_register(_write(rows, tmp_path / "p.csv"))


def test_unit_mismatch_and_missing_row_are_refused(tmp_path):
    rows = _rows()
    for r in rows:
        if r["parameter"] == "youngs_modulus":
            r["unit"] = "GPa"
    with pytest.raises(FC.ContractInputError, match="unit mismatch"):
        FC.load_register(_write(rows, tmp_path / "u.csv"))
    rows = [r for r in _rows() if r["parameter"] != "indicator_resolution_limit"]
    with pytest.raises(FC.ContractInputError, match="missing from register"):
        FC.load_register(_write(rows, tmp_path / "m.csv"))


def test_stale_committed_contract_is_detected(tmp_path):
    stale = tmp_path / "fixture-contract.json"
    doc = json.loads((ROOT / "cad/roboracer/fixture-contract.json").read_text())
    doc["clauses"][1]["value"] = 1.0
    stale.write_text(json.dumps(doc, indent=1) + "\n")
    assert FC.main(["--check", "--output", str(stale)]) == 1
