# CAD amendment verification — 2026-09-06

Source base: `cdc60d2bcd9eaed1fae553cbdea633c8b185e48a` (original integrity PR head). Current candidate identity is the CAD PR head. Python 3.11.8. Planning/metadata checks only; no geometry tests or CAD environment are claimed implemented.

## Reproduction

Run from the repository root in a clone containing the base commit. This checks task schema, finite estimates, local and cross-ledger dependencies, missing/invalid closure evidence, dependency activation, cycles, public withholding, document links and byte-preservation of the earlier sprint ledger. External gate records are unverified until actual owner/source evidence exists; presence cannot authenticate that evidence.

```sh
python - <<'PY'
BASE = "cdc60d2bcd9eaed1fae553cbdea633c8b185e48a"
import copy, csv, json, math, re, subprocess
from pathlib import Path
from urllib.parse import unquote
root = Path.cwd()
columns = "id,day,priority,owner,depends_on,task,deliverable,acceptance_criteria,verification,estimate_hours,status,evidence,blocker".split(",")
with (root / "docs/CAD_TASKS.csv").open(newline="") as f:
    reader = csv.DictReader(f)
    assert reader.fieldnames == columns
    rows = list(reader)
gates = json.loads((root / "docs/CAD_DEPENDENCIES.json").read_text())
plan = (root / "docs/CAD_PLAN.md").read_text()
def validate(rows, gates):
    by_id = {r["id"]: r for r in rows}
    assert rows and len(by_id) == len(rows)
    for key, g in gates.items():
        assert key not in by_id
        src = (root / g["source"]).resolve()
        assert src.is_relative_to(root.resolve()) and src.is_file()
        assert any(line.startswith(g["heading_prefix"]) for line in src.read_text().splitlines())
        assert g["status"] in {"unverified", "satisfied"}
        if g["status"] == "satisfied":
            assert g["evidence"] and (root / g["evidence"]).is_file()
        else:
            assert g["evidence"] is None
    for r in rows:
        assert None not in r and set(r) == set(columns)
        assert all(r[k] for k in columns if k not in {"depends_on","estimate_hours","evidence","blocker"})
        assert r["status"] in {"todo","in_progress","blocked","done","deferred"}
        assert r["owner"] in {"Owner","Agent","External"}
        assert "### " + r["id"] + " — " in plan
        if not r["estimate_hours"]:
            assert r["id"] in {"SSY-CAD-08","SSY-CAD-09"}
            assert r["status"] == "deferred" and r["task"] == "Details withheld pending XC-02"
        else:
            h = float(r["estimate_hours"])
            assert math.isfinite(h) and h > 0
        if r["status"] in {"blocked","deferred"}:
            assert r["blocker"]
        if r["status"] == "done":
            assert r["evidence"] and (root / r["evidence"]).exists()
        for dep in filter(None, r["depends_on"].split(";")):
            assert dep != r["id"] and (dep in by_id or dep in gates)
            if r["status"] in {"todo","in_progress","done"}:
                assert by_id[dep]["status"] == "done" if dep in by_id else gates[dep]["status"] == "satisfied"
    def walk(key, stack):
        assert key not in stack, "dependency cycle"
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
        vehicle = {"DR-CAD-02V","DR-CAD-03","DR-CAD-04","DR-CAD-05","DR-CAD-07","DR-CAD-11"}
        assert not ancestors("DR-CAD-06") & vehicle
        assert not ancestors("DR-CAD-08") & vehicle
    if "RR-CAD-04" in by_id:
        for key in ("RR-CAD-04","RR-CAD-05","RR-CAD-06","RR-CAD-07"):
            assert "RR-CAD-03" not in ancestors(key)
    if "SSY-CAD-01" in by_id:
        required = {"SSY-01","SSY-02","SSY-03","XC-02"}
        assert required <= set(by_id["SSY-CAD-01"]["depends_on"].split(";"))
        assert required <= set(by_id["SSY-CAD-02"]["depends_on"].split(";"))
        if gates["XC-02"]["status"] != "satisfied":
            for key in ("SSY-CAD-08","SSY-CAD-09"):
                r = by_id[key]
                assert r["task"] == "Details withheld pending XC-02" and r["deliverable"] == "Withheld"
                assert r["estimate_hours"] == "" and r["depends_on"] == "XC-02"
    return by_id
validate(rows, gates)
# Mutation tests: no files or original rows are changed.
negative = []
bad = copy.deepcopy(rows); bad[0]["depends_on"] = "NONEXISTENT"
negative.append((bad, gates))
bad = copy.deepcopy(rows); bad[0]["depends_on"] = bad[1]["id"]; bad[1]["depends_on"] = bad[0]["id"]
negative.append((bad, gates))
bad = copy.deepcopy(rows); bad[0]["estimate_hours"] = "NaN"
negative.append((bad, gates))
if any(r["id"] == "DR-CAD-06" for r in rows):
    bad = copy.deepcopy(rows)
    next(r for r in bad if r["id"] == "DR-CAD-06")["depends_on"] += ";DR-CAD-03"
    negative.append((bad, gates))
if any(r["id"] == "RR-CAD-05" for r in rows):
    bad = copy.deepcopy(rows)
    next(r for r in bad if r["id"] == "RR-CAD-03")["depends_on"] = ""
    next(r for r in bad if r["id"] == "RR-CAD-05")["depends_on"] += ";RR-CAD-03"
    negative.append((bad, gates))
if gates:
    bad = copy.deepcopy(rows); bad[0]["status"] = "in_progress"
    negative.append((bad, gates))
    bad_g = copy.deepcopy(gates); bad_g["XC-02"]["status"] = "satisfied"
    negative.append((rows, bad_g))
    bad_g = copy.deepcopy(gates); bad_g["SSY-01"]["heading_prefix"] = "### DOES-NOT-EXIST "
    negative.append((rows, bad_g))
    bad = copy.deepcopy(rows); next(r for r in bad if r["id"] == "SSY-CAD-08")["task"] = "Unapproved details"
    negative.append((bad, gates))
for bad, bad_g in negative:
    try:
        validate(bad, bad_g)
    except AssertionError:
        pass
    else:
        raise AssertionError("invalid mutation was accepted")
changed = subprocess.check_output(["git","diff","--name-only",BASE], text=True).splitlines()
untracked = subprocess.check_output(["git","ls-files","--others","--exclude-standard"], text=True).splitlines()
for name in sorted(set(changed + untracked)):
    path = root / name
    if path.suffix != ".md" or not path.is_file():
        continue
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
        if target.startswith(("https:","http:","mailto:","#")):
            continue
        target = unquote(target.split("#",1)[0])
        assert (path.parent / target).exists(), (name,target)
assert subprocess.check_output(["git","show",BASE+":docs/SPRINT_TASKS.csv"]) == (root / "docs/SPRINT_TASKS.csv").read_bytes()
active = sum(float(r["estimate_hours"]) for r in rows if r["day"] != "conditional")
parked = sum(float(r["estimate_hours"]) for r in rows if r["day"] == "conditional" and r["estimate_hours"])
unknown = sum(not r["estimate_hours"] for r in rows)
print(f"PASS: {len(rows)} tasks; prioritized={active:g} h; parked={parked:g} h; withheld estimates={unknown}; {len(negative)} invalid mutations rejected; dependencies/links/sprint preservation PASS")
PY
```

Also run `git diff --check cdc60d2bcd9eaed1fae553cbdea633c8b185e48a`; use `git diff --cached --check` after staging new files.

## Current observed results

- Embedded validator (including negative mutations): exit 0. PASS: 8 tasks; prioritized=23 h; parked=5 h; withheld estimates=0; 4 invalid mutations rejected; dependencies/links/sprint preservation PASS
- Existing relevant check: `PYTHONPATH=gym python experiments/test_mast_physical_validation.py -q` — exit 0; 20 targeted mast tests in 1.020 s; full ROS/Docker suite NOT rerun.
- Whitespace check is run separately on the staged amendment before commit. The PR records the committed identity; no CAD geometry/environment or independent hardware validation is claimed.

The earlier tests in the first CAD PR remain historical evidence, not automatically rerun evidence for this amendment. No physical or parametric-geometry validation follows from this planning checker.
