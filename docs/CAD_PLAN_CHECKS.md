# CAD amendment verification — 2026-09-06

Source base: `cdc60d2bcd9eaed1fae553cbdea633c8b185e48a` (original integrity PR head). Current candidate identity is the CAD PR head. Python 3.11.8. Planning/metadata checks only; no geometry tests or CAD environment are claimed implemented.

## Reproduction

Run from the repository root. This checks task schema, finite estimates, local and cross-ledger dependencies, missing/invalid closure evidence, dependency activation, cycles, public withholding and document links, and rejects the recorded negative mutations. External gate records are unverified until actual owner/source evidence exists; presence cannot authenticate that evidence.

```sh
python cad/ledger_validator.py live          # every rule above; exit 1 on any failure
python cad/ledger_validator.py historical    # SPRINT_TASKS.csv byte comparison vs the base commit, report only
```

The validator that was embedded here as a script was consolidated into [`cad/ledger_validator.py`](../cad/ledger_validator.py) on 2026-09-13 (RR-CAD-10c) with every rule kept; `cad/tests/test_ledger_validator.py` runs it in the `cad-geometry` workflow. The byte comparison needs the base commit present, so the workflow checks out full history; in a shallow clone the report says `null` instead of failing.

Also run `git diff --check cdc60d2bcd9eaed1fae553cbdea633c8b185e48a`; use `git diff --cached --check` after staging new files.

## Current observed results

- Embedded validator (including negative mutations): exit 0. PASS: 8 tasks; prioritized=23 h; parked=5 h; withheld estimates=0; 4 invalid mutations rejected; dependencies/links/sprint preservation PASS
- Existing relevant check: `PYTHONPATH=gym python experiments/test_mast_physical_validation.py -q` — exit 0; 20 targeted mast tests in 1.020 s; full ROS/Docker suite NOT rerun.
- Whitespace check is run separately on the staged amendment before commit. The PR records the committed identity; no CAD geometry/environment or independent hardware validation is claimed.

The earlier tests in the first CAD PR remain historical evidence, not automatically rerun evidence for this amendment. No physical or parametric-geometry validation follows from this planning checker.
