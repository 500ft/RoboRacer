"""The consolidated CAD-ledger validator must keep every old semantic rule and reject every old
negative control, including a dependency cycle between two DONE tasks (review 2, 2026-09-12)."""
import copy, subprocess, sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cad import ledger_validator as V


def test_live_ledger_passes():
    assert V.live().startswith("PASS live")


def test_every_negative_control_is_rejected():
    rows, gates, plan = V.load()
    n, accepted = V.negative_controls(rows, gates, plan)
    assert n >= 8 and accepted == [], accepted


def test_cycle_between_two_done_tasks_is_rejected():
    rows, gates, plan = V.load()
    done = [r for r in rows if r["status"] == "done"]
    assert len(done) >= 2
    b = copy.deepcopy(rows); a, c = done[0]["id"], done[1]["id"]
    for r in b:
        if r["id"] == a: r["depends_on"] = c
        if r["id"] == c: r["depends_on"] = a
    with pytest.raises(V.LedgerError, match="cycle"):
        V.validate(b, gates, plan)


def test_a_legitimate_new_row_passes():
    rows, gates, plan = V.load()
    new = dict(rows[0]); new.update(id="ZZ-CAD-99", status="todo", depends_on="", estimate_hours="1", evidence="", blocker="")
    plan2 = plan + "\n### ZZ-CAD-99 — synthetic\n"
    V.validate(rows + [new], gates, plan2)


def test_historical_is_a_report_not_a_gate():
    rep = V.historical(V.HISTORICAL_BASE)
    assert set(rep) == {"base", "sprint_ledger_unchanged_since_base", "note"}
    assert isinstance(rep["sprint_ledger_unchanged_since_base"], bool)


def test_cli_live_exit_codes():
    p = subprocess.run([sys.executable, str(ROOT / "cad/ledger_validator.py"), "live"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
