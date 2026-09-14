#!/usr/bin/env python3
"""Reusable CAD-ledger validator: the embedded rules from docs/CAD_PLAN_CHECKS.md, verbatim in
meaning, split into two commands (review 2, 2026-09-12).

    python cad/ledger_validator.py live         # semantic rules on the EVOLVING ledger + negative controls
    python cad/ledger_validator.py historical   # byte-preservation evidence vs a named base commit (report)

`live` is what CI gates. It preserves every semantic rule of the old validator -- unique IDs,
complete columns, status/owner vocabularies, a plan heading per row, finite positive hours (with
the documented SSY withholding exception), blockers named, evidence behind done rows, dependencies
known and satisfied, NO DEPENDENCY CYCLES, the project-specific ordering rules, gate consistency,
and markdown link integrity -- and re-runs the old negative controls in memory so a weakened rule
is itself a failure. It does NOT pin any file to a byte snapshot.

`historical` reports whether docs/SPRINT_TASKS.csv still matches a named base commit. It is
evidence about history, not a gate on the live ledger: a legitimate new sprint row changes those
bytes and must not turn the CAD gate red.
"""
from __future__ import annotations
import argparse, copy, csv, json, math, re, subprocess, sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = "id,day,priority,owner,depends_on,task,deliverable,acceptance_criteria,verification,estimate_hours,status,evidence,blocker".split(",")
STATUSES = {"todo", "in_progress", "blocked", "done", "deferred"}
OWNERS = {"Owner", "Agent", "External"}


class LedgerError(AssertionError):
    pass


def _req(cond, msg):
    if not cond:
        raise LedgerError(msg)


def load(root=ROOT):
    with (root / "docs/CAD_TASKS.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        _req(reader.fieldnames == COLUMNS, f"CAD_TASKS.csv columns differ from {COLUMNS}")
        rows = list(reader)
    gates = json.loads((root / "docs/CAD_DEPENDENCIES.json").read_text())
    plan = (root / "docs/CAD_PLAN.md").read_text()
    return rows, gates, plan


def validate(rows, gates, plan, root=ROOT):
    """All semantic rules of the old embedded validator. Raises LedgerError with the rule named."""
    by_id = {r["id"]: r for r in rows}
    _req(rows and len(by_id) == len(rows), "duplicate or missing task ids")
    for key, g in gates.items():
        _req(key not in by_id, f"gate {key} collides with a task id")
        src = (root / g["source"]).resolve()
        _req(src.is_relative_to(root.resolve()) and src.is_file(), f"gate {key} source missing: {g['source']}")
        _req(any(line.startswith(g["heading_prefix"]) for line in src.read_text().splitlines()), f"gate {key} heading not found: {g['heading_prefix']}")
        _req(g["status"] in {"unverified", "satisfied"}, f"gate {key} status invalid")
        if g["status"] == "satisfied":
            _req(g["evidence"] and (root / g["evidence"]).is_file(), f"gate {key} satisfied without evidence")
        else:
            _req(g["evidence"] is None, f"gate {key} unverified but carries evidence")
    for r in rows:
        _req(None not in r and set(r) == set(COLUMNS), f"{r.get('id')}: malformed row")
        _req(all(r[k] for k in COLUMNS if k not in {"depends_on", "estimate_hours", "evidence", "blocker"}), f"{r['id']}: required column empty")
        _req(r["status"] in STATUSES, f"{r['id']}: status {r['status']!r}")
        _req(r["owner"] in OWNERS, f"{r['id']}: owner {r['owner']!r}")
        _req("### " + r["id"] + " — " in plan, f"{r['id']}: no heading in CAD_PLAN.md")
        if not r["estimate_hours"]:
            _req(r["id"] in {"SSY-CAD-08", "SSY-CAD-09"}, f"{r['id']}: estimate_hours empty")
            _req(r["status"] == "deferred" and r["task"] == "Details withheld pending XC-02", f"{r['id']}: withheld row malformed")
        else:
            try:
                h = float(r["estimate_hours"])
            except ValueError:
                raise LedgerError(f"{r['id']}: estimate_hours not numeric")
            _req(math.isfinite(h) and h > 0, f"{r['id']}: estimate_hours must be finite and > 0")
        if r["status"] in {"blocked", "deferred"}:
            _req(r["blocker"], f"{r['id']}: {r['status']} without a blocker")
        if r["status"] == "done":
            _req(r["evidence"] and (root / r["evidence"]).exists(), f"{r['id']}: done without existing evidence")
        for dep in filter(None, r["depends_on"].split(";")):
            _req(dep != r["id"] and (dep in by_id or dep in gates), f"{r['id']}: unknown dependency {dep}")
            if r["status"] in {"todo", "in_progress", "done"}:
                ok = by_id[dep]["status"] == "done" if dep in by_id else gates[dep]["status"] == "satisfied"
                _req(ok, f"{r['id']} is {r['status']} but dependency {dep} is not done/satisfied")

    def walk(key, stack):
        _req(key not in stack, f"dependency cycle through {key}")
        if key in by_id:
            for dep in filter(None, by_id[key]["depends_on"].split(";")):
                walk(dep, stack | {key})
    for key in by_id:
        walk(key, set())

    def ancestors(key):
        result = set()
        for dep in filter(None, by_id[key]["depends_on"].split(";")):
            result.add(dep)
            if dep in by_id:
                result.update(ancestors(dep))
        return result
    if "DR-CAD-06" in by_id:
        vehicle = {"DR-CAD-02V", "DR-CAD-03", "DR-CAD-04", "DR-CAD-05", "DR-CAD-07", "DR-CAD-11"}
        _req(not ancestors("DR-CAD-06") & vehicle, "DR-CAD-06 must not depend on vehicle tasks")
        _req(not ancestors("DR-CAD-08") & vehicle, "DR-CAD-08 must not depend on vehicle tasks")
    if "RR-CAD-04" in by_id:
        for key in ("RR-CAD-04", "RR-CAD-05", "RR-CAD-06", "RR-CAD-07"):
            _req("RR-CAD-03" not in ancestors(key), f"{key} must not depend on RR-CAD-03 (deck demoted below mast/clamp/fixture)")
    if "SSY-CAD-01" in by_id:
        required = {"SSY-01", "SSY-02", "SSY-03", "XC-02"}
        _req(required <= set(by_id["SSY-CAD-01"]["depends_on"].split(";")), "SSY-CAD-01 dependencies incomplete")
        _req(required <= set(by_id["SSY-CAD-02"]["depends_on"].split(";")), "SSY-CAD-02 dependencies incomplete")
        if gates["XC-02"]["status"] != "satisfied":
            for key in ("SSY-CAD-08", "SSY-CAD-09"):
                r = by_id[key]
                _req(r["task"] == "Details withheld pending XC-02" and r["deliverable"] == "Withheld", f"{key} must stay withheld while XC-02 is open")
                _req(r["estimate_hours"] == "" and r["depends_on"] == "XC-02", f"{key} withheld row malformed")
    return by_id


def negative_controls(rows, gates, plan, root=ROOT):
    """The old validator's mutation tests, plus the review's cycle-between-done-tasks case. Every
    mutation must be rejected; a weakened rule therefore fails here."""
    cases = []
    def add(mut_rows=None, mut_gates=None, name=""):
        b = copy.deepcopy(rows); g = copy.deepcopy(gates)
        if mut_rows: mut_rows(b)
        if mut_gates: mut_gates(g)
        cases.append((name, b, g))
    add(lambda b: b[0].update(depends_on="NONEXISTENT"), name="unknown dependency")
    add(lambda b: (b[0].update(depends_on=b[1]["id"]), b[1].update(depends_on=b[0]["id"])), name="two-task cycle")
    done = [r for r in rows if r["status"] == "done"]
    if len(done) >= 2:
        a, c = done[0]["id"], done[1]["id"]
        add(lambda b: ([r.update(depends_on=c) for r in b if r["id"] == a], [r.update(depends_on=a) for r in b if r["id"] == c]), name="cycle between two DONE tasks (review 2)")
    add(lambda b: b[0].update(estimate_hours="NaN"), name="NaN hours")
    add(lambda b: b[0].update(estimate_hours="-1"), name="negative hours")
    add(lambda b: b.append(dict(b[0])), name="duplicate id")
    add(lambda b: [r.update(evidence="evidence/does-not-exist.md") for r in b if r["status"] == "done"][:1], name="done without evidence")
    add(lambda b: [r.update(blocker="") for r in b if r["status"] in {"blocked", "deferred"}][:1], name="blocked without blocker")
    if any(r["id"] == "DR-CAD-06" for r in rows):
        add(lambda b: next(r for r in b if r["id"] == "DR-CAD-06").update(depends_on=next(r for r in b if r["id"] == "DR-CAD-06")["depends_on"] + ";DR-CAD-03"), name="bench depends on vehicle")
    if any(r["id"] == "RR-CAD-05" for r in rows):
        def m(b):
            next(r for r in b if r["id"] == "RR-CAD-03")["depends_on"] = ""
            next(r for r in b if r["id"] == "RR-CAD-05")["depends_on"] += ";RR-CAD-03"
        add(m, name="fixture depends on deck")
    if gates:
        add(lambda b: b[0].update(status="in_progress"), name="in_progress with unsatisfied dependency")
        add(mut_gates=lambda g: g["XC-02"].update(status="satisfied"), name="gate satisfied without evidence")
        add(mut_gates=lambda g: g["SSY-01"].update(heading_prefix="### DOES-NOT-EXIST "), name="gate heading missing")
        if any(r["id"] == "SSY-CAD-08" for r in rows):
            add(lambda b: next(r for r in b if r["id"] == "SSY-CAD-08").update(task="Unapproved details"), name="withheld row published")
    accepted = []
    for name, b, g in cases:
        try:
            validate(b, g, plan, root)
        except LedgerError:
            continue
        accepted.append(name)
    return len(cases), accepted


def link_integrity(root=ROOT):
    """Every relative markdown link in tracked + untracked .md files resolves (old rule, kept)."""
    names = subprocess.check_output(["git", "-C", str(root), "ls-files", "*.md", "**/*.md"], text=True).splitlines()
    names += subprocess.check_output(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "*.md", "**/*.md"], text=True).splitlines()
    broken = []
    for name in sorted(set(names)):
        path = root / name
        if not path.is_file():
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(errors="ignore")):
            if target.startswith(("https:", "http:", "mailto:", "#")):
                continue
            target = unquote(target.split("#", 1)[0])
            if target and not (path.parent / target).exists():
                broken.append((name, target))
    return broken


def live(root=ROOT):
    rows, gates, plan = load(root)
    validate(rows, gates, plan, root)
    n, accepted = negative_controls(rows, gates, plan, root)
    _req(not accepted, "invalid mutations were ACCEPTED: " + "; ".join(accepted))
    broken = link_integrity(root)
    _req(not broken, f"broken markdown links: {broken[:5]}")
    active = sum(float(r["estimate_hours"]) for r in rows if r["day"] != "conditional" and r["estimate_hours"])
    parked = sum(float(r["estimate_hours"]) for r in rows if r["day"] == "conditional" and r["estimate_hours"])
    return f"PASS live: {len(rows)} tasks; prioritized={active:g} h; parked={parked:g} h; {n} invalid mutations rejected; links OK"


def historical(base, root=ROOT):
    """Report (never a live gate): does docs/SPRINT_TASKS.csv still equal its bytes at `base`?"""
    then = subprocess.run(["git", "-C", str(root), "show", base + ":docs/SPRINT_TASKS.csv"], capture_output=True).stdout
    now = (root / "docs/SPRINT_TASKS.csv").read_bytes()
    return dict(base=base, sprint_ledger_unchanged_since_base=(then == now) if then else None,
                note="Historical preservation evidence. Divergence means the sprint ledger evolved after the base commit; it is not a defect of the CAD ledger. None means the base commit is not in this clone (shallow checkout).")


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["live", "historical"]); ap.add_argument("--base", default=None)
    a = ap.parse_args(argv)
    if a.mode == "live":
        try:
            print(live()); return 0
        except LedgerError as e:
            print("FAIL live:", e, file=sys.stderr); return 1
    base = a.base or HISTORICAL_BASE
    print(json.dumps(historical(base), indent=1)); return 0


HISTORICAL_BASE = "cdc60d2bcd9eaed1fae553cbdea633c8b185e48a"

if __name__ == "__main__":
    sys.exit(main())
