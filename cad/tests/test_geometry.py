"""Geometry CI for the RoboRacer mast_tube family (RR-CAD-08).

Fail-closed checks named in the task's acceptance criteria: regenerate from the registered
parameters and match the reviewed contract; prove failure on an altered parameter, invalid
dimensions, missing inputs, an empty pending value, a unit mismatch, and a bad STEP file.
"""
import csv, json, subprocess, sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "cad"))
import generate as G  # noqa: E402

PARAMS = REPO / "cad/roboracer/parameters.csv"
CONTRACT = json.loads((REPO / "cad" / "contract.json").read_text())
ALTER = "mast_wall_thickness"; ALTER_TO = "2.0"
INVALID = "mast_wall_thickness"; INVALID_TO = "10.0"
DROP = "mast_outer_diameter"; BLANK = "mast_length"

def _rewrite(src, dst, edit):
    rows = edit(list(csv.DictReader(src.open())))
    with dst.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return dst

def _set(name, **kv):
    def f(rows):
        for r in rows:
            if r["parameter"] == name: r.update(kv)
        return rows
    return f

def _check_contract(m, e, tol):
    assert abs(m["volume_mm3"] - e["volume_mm3"]) <= tol["volume_mm3_rel"] * e["volume_mm3"]
    if e.get("mass_kg") is not None:
        assert abs(m["mass_kg"] - e["mass_kg"]) <= tol["mass_kg_rel"] * e["mass_kg"]
    for a, b in zip(sorted(m["bbox_mm"]), sorted(e["bbox_mm"])):
        assert abs(a - b) <= tol["bbox_mm_abs"]
    assert m["n_solids"] == e["n_solids"]

def test_regenerates_and_matches_contract(tmp_path):
    r = G.generate(PARAMS, tmp_path)
    _check_contract(r["measured_direct"], CONTRACT["expected"], CONTRACT["tolerances"])
    assert (tmp_path / f"{G.FAMILY}.step").is_file() and (tmp_path / "geometry.json").is_file()

def test_step_roundtrip_preserves_volume(tmp_path):
    r = G.generate(PARAMS, tmp_path)
    a, b = r["measured_direct"]["volume_mm3"], r["measured_after_step_reimport"]["volume_mm3"]
    assert abs(a - b) <= CONTRACT["tolerances"]["step_roundtrip_volume_rel"] * a

def test_analytic_matches_measured(tmp_path):
    r = G.generate(PARAMS, tmp_path)
    assert abs(r["analytic"]["volume_mm3"] - r["measured_direct"]["volume_mm3"]) <= 1e-6 * r["analytic"]["volume_mm3"]

def test_altered_parameter_fails_contract(tmp_path):
    r = G.generate(_rewrite(PARAMS, tmp_path / "p.csv", _set(ALTER, value=ALTER_TO)), tmp_path / "o")
    with pytest.raises(AssertionError):
        _check_contract(r["measured_direct"], CONTRACT["expected"], CONTRACT["tolerances"])

def test_invalid_dimensions_refused(tmp_path):
    with pytest.raises(G.GeometryInputError):
        G.generate(_rewrite(PARAMS, tmp_path / "p.csv", _set(INVALID, value=INVALID_TO)), tmp_path / "o")

def test_missing_input_refused(tmp_path):
    with pytest.raises(G.GeometryInputError, match="missing from register"):
        G.generate(_rewrite(PARAMS, tmp_path / "p.csv", lambda rows: [r for r in rows if r["parameter"] != DROP]), tmp_path / "o")

def test_empty_pending_value_refused(tmp_path):
    with pytest.raises(G.GeometryInputError, match="no value"):
        G.generate(_rewrite(PARAMS, tmp_path / "p.csv", _set(BLANK, value="", evidence_state="pending")), tmp_path / "o")

def test_unit_mismatch_refused(tmp_path):
    with pytest.raises(G.GeometryInputError, match="unit mismatch"):
        G.generate(_rewrite(PARAMS, tmp_path / "p.csv", _set(BLANK, unit="in")), tmp_path / "o")

def test_bad_step_is_detected(tmp_path):
    import cadquery as cq
    G.generate(PARAMS, tmp_path)
    step = tmp_path / f"{G.FAMILY}.step"
    data = step.read_bytes(); step.write_bytes(data[: len(data) // 2])
    with pytest.raises(Exception):
        s = cq.importers.importStep(str(step))
        assert len(s.solids().vals()) == CONTRACT["expected"]["n_solids"]
        assert abs(s.val().Volume() - CONTRACT["expected"]["volume_mm3"]) <= 1e-6 * CONTRACT["expected"]["volume_mm3"]

def test_cli_refuses_with_exit_2(tmp_path):
    p = _rewrite(PARAMS, tmp_path / "p.csv", lambda rows: [r for r in rows if r["parameter"] != DROP])
    proc = subprocess.run([sys.executable, str(REPO / "cad" / "generate.py"), "--parameters", str(p), "--output", str(tmp_path / "o")],
                          capture_output=True, text=True)
    assert proc.returncode == 2 and "REFUSED" in proc.stderr

def test_installed_versions_match_lock():
    lock = dict(l.split("#")[0].strip().split("==") for l in (REPO / "cad" / "requirements.lock").read_text().splitlines() if "==" in l.split("#")[0])
    v = G.versions()
    for k in ("cadquery", "python"):
        assert v.get(k) == lock.get(k), f"{k}: installed {v.get(k)} != locked {lock.get(k)}"
