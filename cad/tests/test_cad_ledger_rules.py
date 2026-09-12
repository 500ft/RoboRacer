"""Row-level rules for the evolving CAD ledger, without pinning any file to a byte snapshot.

Review 2026-09-12: the embedded validator in docs/CAD_PLAN_CHECKS.md pins docs/SPRINT_TASKS.csv
to its bytes at one commit, so every legitimate ledger edit turns it red and re-pinning would keep
the appearance of a gate without its purpose. These tests keep the rules that protect the ledger's
meaning -- unique IDs, known dependencies, evidence behind every done row, a plan heading per row,
blocked rows naming their blocker -- and leave historical preservation to git.
"""
import csv, json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
COLUMNS = "id,day,priority,owner,depends_on,task,deliverable,acceptance_criteria,verification,estimate_hours,status,evidence,blocker".split(",")


def _rows():
    with (ROOT / "docs/CAD_TASKS.csv").open(newline="") as f:
        r = csv.DictReader(f); assert r.fieldnames == COLUMNS; return list(r)


def test_ids_unique_and_columns_complete():
    rows = _rows(); ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})
    for r in rows:
        assert r["status"] in {"todo", "in_progress", "blocked", "done", "deferred"}, r["id"]
        assert r["owner"] in {"Owner", "Agent", "External"}, r["id"]


def test_dependencies_exist_and_done_rows_have_done_dependencies():
    rows = _rows(); by = {r["id"]: r for r in rows}
    gates = json.loads((ROOT / "docs/CAD_DEPENDENCIES.json").read_text())
    for r in rows:
        for dep in filter(None, r["depends_on"].split(";")):
            assert dep != r["id"] and (dep in by or dep in gates), (r["id"], dep)
            if r["status"] in {"todo", "in_progress", "done"}:
                ok = by[dep]["status"] == "done" if dep in by else gates[dep]["status"] == "satisfied"
                assert ok, f"{r['id']} is {r['status']} but depends on {dep} which is not done/satisfied"


def test_done_rows_have_existing_evidence_and_blocked_rows_name_a_blocker():
    for r in _rows():
        if r["status"] == "done":
            assert r["evidence"] and (ROOT / r["evidence"]).exists(), r["id"]
        if r["status"] in {"blocked", "deferred"}:
            assert r["blocker"], r["id"]


def test_every_row_has_a_plan_heading():
    plan = (ROOT / "docs/CAD_PLAN.md").read_text()
    missing = [r["id"] for r in _rows() if "### " + r["id"] + " — " not in plan]
    assert missing == [], missing


def test_sprint_ledger_ids_are_unique_too():
    ids = [r["id"] for r in csv.DictReader((ROOT / "docs/SPRINT_TASKS.csv").open())]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})
