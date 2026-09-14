# Day-4 bounded work — 2026-09-14

Base: `c693225` (main after PR #21; all three workflows green). Every Agent row in [CAD_TASKS.csv](CAD_TASKS.csv) and [SPRINT_TASKS.csv](SPRINT_TASKS.csv) is done. Nothing below is built until the Owner section is filled and this PR is merged; the Agent section is what gets built from it, in order, the same day.

How to use this file: edit the `Owner` blanks directly in this PR (a value, a source path, or `defer`), merge, and the Agent builds every row whose inputs are present. A blank left blank stays blocked; nothing is assumed.

## Owner section — decisions and inputs

### O1. RR-S11 open question — tap-test generator

Should PR #16's `experiments/tap_test_prereg.py` regenerate the modal preregistration document, or stay closed?

Decision: `____` (regenerate | closed)

### O2. RR-CAD-02 — fixture inputs (unblocks RR-CAD-04 → 07)

The register `cad/roboracer/parameters.csv` has six pending rows and the contract refuses release on them. Fill value + source; the source must be a drawing, inspection, calibration record, protocol, or an owner decision recorded in `cad/roboracer/owner-inputs.md` (new file, Agent writes it from this table).

| parameter | value (mm) | source |
|---|---|---|
| clamp_engagement | `____` | `____` |
| clamp_bolt_pitch | `____` | `____` |
| lidar_bracket_bolt_pitch | `____` | `____` |
| optical_center_offset | `____` | `____` |
| actual_load_height | `____` | `____` |
| root_rotation_station_spacing | `____` | `____` |

Contract fields `--release` also requires (see `python cad/fixture_contract.py --release`):

| field | value |
|---|---|
| bolt_coordinates_mm (x/y/z per bolt) | `____` |
| bolt_coordinate_tolerance_mm | `____` |
| indicator_access tip_x / tip_y / root_x / root_y / rotation | `____` |
| reviewed target + tolerance for each row above | `____` |

Interfaces and route (RR-CAD-02 acceptance criteria):

| item | value or reference |
|---|---|
| stock (tube spec, supplier, lot) | `____` |
| root clamp + fastener interface drawing | `____` |
| deck-side clamp mating datum | `____` |
| fabrication / inspection route | `____` |
| calibrated force instrument (model, cal record) | `____` |
| tip and root indicators (resolution ≤ 0.001 mm, cal records) | `____` |
| bench access (where, when) | `____` |
| lead-time quote | `____` |

Register rows at `design_choice` / `model_assumption` (mast length, OD, wall, density, E, tip mass) also block release. Decision: promote by inspection later (`____`) or accept as owner decision for the nominal build (`____`).

### O3. RR-S12 — modal freeze

| input | value |
|---|---|
| as-built modal reference (inspection-linked) | `____` |
| calibration uncertainty | `____` |
| approved numerical band | `____` |

### O4. RR-S02 / RR-S09 — readiness and reviewer

| input | value |
|---|---|
| hardware calibration records | `____` |
| independent reviewer (name, authorized to share) | `____` |

### O5. Housekeeping (no Agent work; one minute)

- Delete merged branches: `audit/fixture-contract-repair2-20260913`, `audit/fixture-contract-repair-20260912`, `audit/fixture-contract-reconcile-20260912` (`gh api -X DELETE repos/500ft/autonomous-racing-systems/git/refs/heads/<b>`).
- Repo settings → enable "Automatically delete head branches".

## Agent section — built after merge, in this order

| # | needs | builds | done when |
|---|---|---|---|
| A1 | O1 | if `regenerate`: port the generator onto #17's modal doc without deleting `modal-freeze.json`; if `closed`: one line in [CAD_REVIEW_DISPOSITION.md](CAD_REVIEW_DISPOSITION.md) closing RR-S11's open item | `python cad/modal_freeze.py --check-draft` exit 0; RR-S11 note updated |
| A2 | O2 table 1 | `cad/roboracer/owner-inputs.md`; fill the six register rows; `fixture_contract.py --refresh` | `--check` current; RR-CAD-02 → done with evidence |
| A3 | O2 tables 2–3 | fill contract review fields and targets | `--release` prints `CONTRACT_COMPLETE` (or names only the rows you left blank) |
| A4 | A2, A3 | RR-CAD-04: mast + root clamp + LiDAR bracket in `cad/roboracer/mast/` from the register; STEP export/reimport; wall/section/volume/mass/load-height asserted in `cad/tests` | `cad-geometry` green; RR-CAD-04 → done |
| A5 | A4 | RR-CAD-05: two-axis loading + metrology fixture in `cad/roboracer/fixture/`; stiffness ≥ 10× specimen per axis checked numerically against [CAD_MEASUREMENT_CONTRACT.md](CAD_MEASUREMENT_CONTRACT.md) | budget arithmetic reproduced in a test; RR-CAD-05 → done |
| A6 | O3 | RR-S12 freeze: populate `modal-freeze.json`, run strict check | `python cad/modal_freeze.py` exit 0; RR-S12 → done |

RR-CAD-06 and 07 follow A4–A5 and stay out of today's scope. A2–A5 will not run on a partial table: a blank row keeps `--release` refusing and the ledger row blocked, by design.

## Optional Agent work that needs no hardware

Only if you pick one:

- `____` RoboRacer CAD/FEA design package and report (the remaining item outside this ledger). Scope: nominal mast/clamp package from the current register, clearly labelled design-choice, no as-built claims.
- `____` `/ponytail-audit` of `experiments/` and `cad/` for dead code and reinvented stdlib; one PR of deletions, no behavior change.

## Boundary

No spending, outreach, fabrication, powered hardware, or fabricated approval is authorized by this plan. A filled blank is an owner statement; the Agent records it as such and does not upgrade it to an inspection. Status lives only in the ledgers; this file is a work order, not evidence.
