# CAD planning amendment — verification

Prepared 2026-09-06. Source base: `cdc60d2bcd9eaed1fae553cbdea633c8b185e48a`. Candidate identity is the CAD PR head; no circular self-hash is embedded here. Runtime: Python 3.11.8. Scope: task documents only, not CAD artifact acceptance.

## Reproduce the planning checks

From the repository root, run the following. It checks CSV structure, unique IDs, dependency closure/cycles, task-to-plan coverage, local Markdown file targets in the amendment, and byte preservation of the original sprint ledger. It does not inspect dimensions or validate hardware.

```sh
python - <<'PY'
BASE = "cdc60d2bcd9eaed1fae553cbdea633c8b185e48a"
import csv, re, subprocess
from pathlib import Path
from urllib.parse import unquote
root = Path.cwd()
with (root / "docs/CAD_TASKS.csv").open(newline="") as f:
    reader = csv.DictReader(f)
    expected = "id,day,priority,owner,depends_on,task,deliverable,acceptance_criteria,verification,estimate_hours,status,evidence,blocker".split(",")
    assert reader.fieldnames == expected
    rows = list(reader)
ids = [row["id"] for row in rows]
assert len(ids) == len(set(ids)) and rows
plan = (root / "docs/CAD_PLAN.md").read_text()
lookup = {row["id"]: row for row in rows}
for row in rows:
    assert None not in row and all(row[k] for k in expected if k not in {"depends_on", "evidence", "blocker"})
    assert row["status"] in {"todo", "blocked", "deferred", "in_progress", "done"}
    assert row["owner"] in {"Agent", "Owner", "External"}
    assert float(row["estimate_hours"]) > 0
    assert "### " + row["id"] + " — " in plan
    if row["status"] in {"blocked", "deferred"}:
        assert row["blocker"]
    if row["status"] == "done":
        assert row["evidence"]
    for dep in filter(None, row["depends_on"].split(";")):
        assert dep in lookup and dep != row["id"]
def walk(key, stack):
    assert key not in stack, "Dependency cycle: " + key
    for dep in filter(None, lookup[key]["depends_on"].split(";")):
        walk(dep, stack | {key})
for key in ids:
    walk(key, set())
changed = subprocess.check_output(["git", "diff", "--name-only", BASE], text=True).splitlines()
untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], text=True).splitlines()
for name in sorted(set(changed + untracked)):
    path = root / name
    if path.suffix != ".md" or not path.is_file():
        continue
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
        if target.startswith(("https:", "http:", "mailto:", "#")):
            continue
        target = unquote(target.split("#", 1)[0])
        assert (path.parent / target).exists(), (name, target)
assert subprocess.check_output(["git", "show", BASE + ":docs/SPRINT_TASKS.csv"]) == (root / "docs/SPRINT_TASKS.csv").read_bytes()
core = sum(float(r["estimate_hours"]) for r in rows if r["day"] != "conditional")
later = sum(float(r["estimate_hours"]) for r in rows if r["day"] == "conditional")
print(f"PASS: {len(rows)} tasks; core={core:g} h; conditional={later:g} h; IDs/dependencies/links valid; original sprint ledger unchanged")
PY
```

Also run `git diff --check cdc60d2bcd9eaed1fae553cbdea633c8b185e48a`. For staged new files before commit, additionally run `git diff --cached --check`.

## Observed outcomes

- Final staged whitespace check: `git diff --cached --check` — exit 0; no whitespace errors.

- Planning validator: exit 0; 7 tasks; 24 initial-phase hours and 0 conditional hours; unique IDs, acyclic dependencies, local links and original sprint-ledger preservation passed.
- Existing check command: `PYTHONPATH=gym python experiments/test_mast_physical_validation.py` — exit 0. 20 mast-validation tests passed in 1.109 seconds; this was a targeted test, not the full ROS/Docker suite.
- These results check documentation/software consistency only; they do not establish model fit, CAD geometry quality, calibration or physical safety.
