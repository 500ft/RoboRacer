# Day-4 bounded work — revised 2026-09-15

Outcome: turn available owner inputs into the next reviewable engineering deliverable,
with a separate, explicit path to physical mast validation.

Replaces [PR #22](https://github.com/500ft/autonomous-racing-systems/pull/22),
reviewed at `021c2054db8280310beb4e906a5282d810cae751`. Base:
`c6932253b6e2ab705066c4ae8ca37fc3819f5cd2` (main after PR #21).
This PR adds this plan only; it changes no task status, parameter, protocol,
threshold, or repository setting. A1–A9 below are future work orders.

## Verified starting point and critique of PR #22

The status authorities remain [CAD_TASKS.csv](CAD_TASKS.csv) and
[SPRINT_TASKS.csv](SPRINT_TASKS.csv). At the base revision:

| Ledger | Done | Blocked | Deferred |
| --- | --- | --- | --- |
| CAD | RR-CAD-01/08/09/10 | RR-CAD-02/04/05/06/07 | RR-CAD-03 |
| Sprint | RR-S01/03/04/05/06/07/08/10, RR-D03, RR-S11 | RR-S02/09/12/13 | None |

There is no ready Agent implementation row, but several Agent rows are blocked;
they are not done. The six pending register values, unreviewed fixture contract,
and draft modal freeze remain unresolved. PR #21 repairs the historical-ledger
check in shallow clones; the September 13 CAD CI failure is not a new Day-4 task.

| Problem in #22 | Correction in this work order |
| --- | --- |
| Six dimensions were enough to mark RR-CAD-02 done. | Accept the complete interface, manufacture/metrology route and availability record; partial intake can still be delivered. |
| Owner was asked to supply every design detail. | Owner identifies actual hardware, available records and decisions; Agent extracts sourced dimensions and proposes missing design choices for review. |
| Contract checklist omitted identity fields and four target dimensions. | Cover the live schema, all ten dimensions, sources, tolerances and evidence states. |
| A stiffness arithmetic test was enough to close RR-CAD-05. | Require the actual fixture model, both axes, root-rotation observability and a reviewed fitted-compliance uncertainty budget. |
| Modal checker exit 0 was enough to close RR-S12. | Respect its `READY_FOR_HUMAN_FREEZE_REVIEW_ONLY` result, actual review and the RR-CAD-06 dependency. Freeze analysis code before acquisition too. |
| A1–A6 were promised the same day and tied to one complete form. | Execute only ready work, allow independent branches and partial intake, and use effort estimates rather than a hardware deadline. |
| Optional nominal CAD could imply an unspecified clamp; an audit promised deletions before findings. | Bound nominal work to supported inputs; audit first and justify any later removal against callers and evidence lineage. |

## How to use this plan

Fill only the inputs available now. Each `____` accepts a value with units and a
source, a source path/reference for extraction, or `defer` with the missing item
and the event that could resolve it. A document reference need not be retyped
into every numerical field. The Agent returns a normalized intake and remaining
blockers. Blank or deferred fields remain unresolved; neither means approval.

Merging this plan does not complete an owner gate. Subsequent work follows the
recorded choices and accepted dependencies. Existing explicit authorizations
remain valid; do not ask for them again. No Owner decision below is filled by
this replacement PR. A1, optional work and mechanical intake can proceed
independently when selected; missing modal data does not block static work.

Use source revision/page, specimen or instrument identity, units, and evidence
kind when available. Distinguish drawing tolerance from measurement uncertainty.
An owner-approved nominal value remains a design decision, not an inspection.
Do not relabel all assumptions merely to make a checker green. An inaccessible,
inconsistent or ambiguous source remains pending until resolved.

## Owner section — decisions and inputs

### O1. RR-S11 follow-up — tap-test generator

Decision: `____` (`closed` | `regenerate` | `defer`).

Recommendation: `closed` unless deterministic regeneration has a concrete use;
the [draft procedure](specs/mast-physical-validation/modal-preregistration.md),
[freeze fields](specs/mast-physical-validation/modal-freeze.json) and checker
already exist. This closes only the leftover generator question from
[PR #16](https://github.com/500ft/autonomous-racing-systems/pull/16), not RR-S12.
If `regenerate`, desired generated content/source of truth: `____`.

### O2. RR-CAD-02 — identify the assembly and supply available records

Smallest useful input: actual sensor/bracket and clamp identities, available
drawings or measurements, and whether fabrication/metrology access exists.
The Agent can derive proposed clamp engagement or observation spacing; the
Owner need not invent these dimensions before engineering work starts.

| Interface in [parameters.csv](../cad/roboracer/parameters.csv) | Value in mm or source/defer | Source kind, revision/datum and uncertainty if measured |
| --- | --- | --- |
| `clamp_engagement` | `____` | `____` |
| `clamp_bolt_pitch` | `____` | `____` |
| `lidar_bracket_bolt_pitch` | `____` | `____` |
| `optical_center_offset` | `____` | `____` |
| `actual_load_height` | `____` | `____` |
| `root_rotation_station_spacing` | `____` | `____` |

| Route / availability needed for RR-CAD-02 | Record or defer |
| --- | --- |
| Specimen/stock specification, supplier and lot identity if acquired; material basis | `____` |
| Exact sensor/bracket revision, root clamp and fasteners; source drawings | `____` |
| Deck-side mating datum, coordinate axes and force-line definition | `____` |
| Fabrication and inspection route; available tools and CAD access if needed | `____` |
| Force instrument ID, range and applicable calibration record | `____` |
| Tip/root instrument IDs, resolution at most 0.001 mm and calibration records | `____` |
| Independent root-rotation observation method and reference supports | `____` |
| Bench access, operator/availability and actual lead-time quote | `____` |
| Installed body/bracket/moving-cable mass and thermal mounting arrangement | `____` |
| Owner acceptance of the assembled RR-CAD-02 record, revision and date | `____` |

Link the same calibration record from O4; do not maintain two versions. Record
nominal availability separately from possession or calibration. The documented
heat-sink/moving-mass issue in [fixture preparation](../cad/roboracer/fixture-preparation.md)
must be resolved before the installed assembly is represented by the model.
The complete vehicle deck is deferred and is not an RR-CAD-02 prerequisite.

### O2a. Reviewed model contract — Agent prepares, Owner/reviewer accepts

The schema is [fixture-contract.json](../cad/roboracer/fixture-contract.json),
enforced by [fixture_contract.py](../cad/fixture_contract.py). Supply an existing
drawing/target schedule if available: `____`. Otherwise A2/A3 prepare a proposal
from the accepted interfaces; proposed values do not become approved by being
written down.

| Review information | Value/source or defer |
| --- | --- |
| `datum`, `drawing_revision`, `reviewed_by`, dated review record | `____` |
| `bolt_source`, ordered `bolt_coordinates_mm` in that datum, positive `bolt_coordinate_tolerance_mm` | `____` |
| `indicator_access.tip_x` and `indicator_access.tip_y`: positions, directions, reference supports and access | `____` |
| `indicator_access.root_x` and `indicator_access.root_y`: positions, directions, reference supports and access | `____` |
| `indicator_access.rotation`: independent observations, baseline and sensitivity | `____` |
| Reviewed target/tolerance/source schedule for all ten dimensions below | `____` |
| Per-row disposition of nominal material, geometry and mass values, with intended use and supporting record | `____` |

All ten dimensions need `value`, `unit`, positive `tolerance_abs`, and `source`:
the six O2 interfaces plus `mast_length`, `mast_outer_diameter`,
`mast_wall_thickness` and `tube_volume`. Volume is in mm³; lengths are in mm.
`tube_volume` is the exposed ideal tube segment, not the clamped stock or full
assembly. Derive its expected value independently from reviewed dimensions and
justify its tolerance before comparing a candidate export.

The current strict checker also rejects the evidence states of `mast_length`,
`mast_outer_diameter`, `mast_wall_thickness`, `youngs_modulus`, `density` and
`tip_total_mass`. Resolve each with its actual basis and intended use. An
explicit `owner_decision` can support a nominal design contract under the
current schema; it cannot satisfy an as-built measurement requirement. Keep
body/bracket/cable components consistent with total mass. A legitimate physical
value that conflicts with the schema needs a separately reviewed correction,
not a fabricated nonzero value or widened tolerance.

### O3. RR-S12 — later modal review, after inspection-linked references exist

Current disposition: `____` (`defer` | supply records for review).
Use the [modal preregistration](specs/mast-physical-validation/modal-preregistration.md)
and [complete freeze schema](specs/mast-physical-validation/modal-freeze.json).
Three filled cells are insufficient. The Agent can extract the following from
a supplied record; the Owner/reviewer approves the resulting numerical protocol.

| Required group | Record or defer |
| --- | --- |
| As-built x/y frequencies, specimen/drawing, inspected geometry and installed mass; separate model-source and reference commits | `____` |
| Instrument IDs, calibration/bandwidth, timing and anti-alias characterization; instrumented impulse or response-only acquisition choice | `____` |
| Excitation/response coordinates for both axes, clamp/cable configuration and sensor-loading correction | `____` |
| Sample rate, duration, true frequency resolution, analysis band, anti-alias passband/stopband/attenuation and repeats per axis | `____` |
| Estimator/window/damping and mode pairing; coherence or prospectively reviewed alternative, repeatability and mass-loading limits | `____` |
| Numerical uncertainty budget, maximum relative U95, separate model-discrepancy band, boundary decision rule, exclusions/retest rules and reviewer rationale | `____` |
| Owner/reviewer approval record tied to the final protocol revision | `____` |

Populate every existing settings/records key, not just the examples above.
Response-only decay requires a prospective protocol/checker change; it cannot
provide force-response coherence. Neither the static ±15% band nor nominal
285.5 Hz is a physical modal acceptance rule. Keep the separate 200 Hz design
screen and the rejected 174.7 Hz baseline distinct.

### O4. RR-S02 and RR-S09 — physical readiness and independent review

| Input | Record or defer |
| --- | --- |
| [Campaign-readiness checklist](specs/mast-physical-validation/campaign-readiness.md): actual apparatus, inspection, as-built FEA, calibrations, uncertainty, zero checks and setup records | `____` |
| Owner's apparatus/operator readiness and data-use approval, tied to records | `____` |
| Independent reviewer name and review scope | `____` |
| Existing or new sharing authorization: recipient, channel and permitted artifacts | `____` |
| Actual written feedback and disposition, when received | `____` |

A name does not complete RR-S09; actual feedback does. A file-presence check
does not complete RR-S02; the full checklist and substantive human review do.
Preparing a review packet can proceed before a reviewer is available. Sending
it requires the recorded authorization; do not repeat an already granted one.

### O5. Optional repository housekeeping — independent of engineering

Branch cleanup decision: `____` (`defer` | review candidates).
Auto-delete merged PR branches: `____` (`leave unchanged` | `enable`).

The candidates from #22 are `audit/fixture-contract-repair2-20260913`,
`audit/fixture-contract-repair-20260912`, and
`audit/fixture-contract-reconcile-20260912`. Before proposing deletion, fetch,
verify the associated PR merged, confirm no unique unmerged commits, and check
open PR/worktree/dependent-branch use. Report the exact candidates; execute only
the approved cleanup. Do not include closed-but-unmerged #16 or active plan
branches automatically. This planning PR changes neither branches nor settings.

## Agent section — dependency-driven work orders

Start each implementation batch from current main, refresh both ledgers and
checks, and select the smallest ready deliverable. A missing field blocks its
dependent acceptance gate, not unrelated extraction, design proposals or review
preparation. Estimates below are focused engineering effort, not dates; resolve
external lead times separately. Each completed batch supplies its diff, exact
checks and exits, source/output identity, and remaining named inputs in a PR.

| Work | Needs and deliverable | Acceptance / ledger effect |
| --- | --- | --- |
| A1 — generator disposition | O1 only. `closed`: record the decision in [CAD_REVIEW_DISPOSITION.md](CAD_REVIEW_DISPOSITION.md). `regenerate`: inspect #16 and port only the useful generator onto the current modal document/schema. | Preserve `modal-freeze.json`, authored review fields and current thresholds. For regeneration, test deterministic output, unresolved inputs staying blocked and preservation of reviewed content; a draft-schema check alone is insufficient. RR-S11's completed draft stays done; record the follow-up without closing RR-S12. Estimate after choosing the branch. |
| A2 — source intake and interface proposals | Any available O2 records. Create `cad/roboracer/owner-inputs.md` with row-to-source mapping, unresolved items and explicit design proposals; extract rather than re-request data already supplied. | Partial record is a valid deliverable. Fill only supported register values with truthful states; regenerate both derived files using the commands below. RR-CAD-02 remains blocked until all its route/interface criteria and actual owner acceptance are evidenced. Allow about 1–2 h for an initial source packet, then re-estimate. |
| A3 — reviewed targets and contract comparison | O2a and consistent accepted register entries. Prepare all target/tolerance/source and identity/access fields; freeze reviewed targets before judging an export. | `--check` current and `--release` returns `CONTRACT_COMPLETE` only when complete. This is input-review completeness. Separately extract observations from regenerated/reimported CAD and run `--geometry` to obtain `MODEL_GEOMETRY_MATCH_ONLY`. Record the extractor and source/export identity; neither string proves fixture stiffness or physical readiness. May iterate with A4/A5; record results under their existing tasks. |
| A4 — RR-CAD-04 mast/clamp/bracket | Accepted RR-CAD-02 and completed RR-CAD-08; approved interface targets. Deliver native source, STEP and joint details in `cad/roboracer/mast/`. Exploratory proposals can precede acceptance; final geometry cannot. | Fresh-process STEP reimport; independent wall/section/volume/mass/load-height checks; documented clamp engagement, bolt fits, optical offset, clearance and joint assumptions. Include bad units, missing dimensions, invalid walls and out-of-tolerance controls. Relevant reviewed contracts and hosted geometry checks pass before task closure. Existing estimate: 5 h. |
| A5 — RR-CAD-05 two-axis fixture | Accepted RR-CAD-02 and completed RR-CAD-04. Deliver fixture source/STEP, setup drawing and an actual load-path model in `cad/roboracer/fixture/`. | Prove modeled load-point translational stiffness at least 10× specimen stiffness on each axis; resolve independent root/tip observations and root rotation. Supply a filled reviewed fitted-compliance budget with calibrated inputs and all sources. Arithmetic tests supplement these deliverables. Missing calibration or budget terms keep closure blocked; physical blank-fixture commissioning remains a separate RR-S02 gate. Existing estimate: 5 h. |
| A6 — RR-CAD-06/07 handoff and release sequence | Completed RR-CAD-04/05, geometry/reference mapping and review. Prepare `cad/roboracer/analysis-export/` and subsequently `cad/roboracer/release/` with drawings, BOM, inspection sheets and boundary maps. | Resolve the staging ambiguity described below before promising ledger closure. Reopen exports, verify dimensions/datums and have a second reviewer reproduce the pack. After actual fabrication/inspection, generate and review separate axis-specific as-built references before loading. Existing estimates: 3 h each; external work is additional. |
| A7 — RR-S02/S09 evidence packet | O4 plus the applicable A4–A6 artifacts. Assemble readiness and review packets; obtain authorized feedback and record dispositions. | Packet preparation is separate from actual approval/feedback. RR-S02 closes only on its full physical-readiness evidence; RR-S09 only on actual independent written review. Neither blocks A1 or partial A2. This row does not execute a physical campaign. |
| A8 — RR-S12 numerical modal freeze | Completed RR-S11, accepted RR-CAD-02 and completed RR-CAD-06, as required by the sprint ledger; all O3 records and the readiness review required by the modal protocol. | Populate the existing schema, obtain `READY_FOR_HUMAN_FREEZE_REVIEW_ONLY`, then inspect sources/calibration, justify the budget/rule and record actual Owner/reviewer approval. Commit and push the reviewed protocol and separate as-built model/reference; verify hashes and remote commit identity. Only then close RR-S12. Existing Owner estimate: 2 h of review, not acquisition or reference generation. |
| A9 — RR-S13 modal analysis | Completed RR-S12 with frozen observable, schema and rule. Implement the analyzer and negative controls against that specification. | Predeclared synthetic boundary cases cover agreement, discrepancy, invalid/poor-quality data and exclusions without adjusting the approved band. Freeze reviewed analysis code before tapping. A rule change reopens prospective review; no physical result is produced by synthetic tests. Estimate after the approved schema exists. |

Critical physical path: RR-CAD-02 → RR-CAD-04 → RR-CAD-05 → staged
RR-CAD-06/07 and actual fabrication/inspection → reviewed as-built reference →
RR-S02 readiness → static campaign under its separate authorization. Modal
work adds RR-S12 → RR-S13 and the prospective acquisition review. Static work
does not wait for the optional generator or the modal campaign.

### Resolve the handoff/release ambiguity before implementation reaches A6

RR-CAD-06's wording mixes preparation of an inspection/FEA handoff with a later
post-inspection reference freeze, while RR-CAD-07 depends on RR-CAD-06 to release
the fabrication pack. Reading both as one completion gate can require a built
specimen before issuing its fabrication pack.

Before those rows activate, propose a narrow ledger/contract amendment for
review: retain RR-CAD-06 for the verified geometry/inspection handoff and keep
the actual post-inspection as-built freeze as an explicit prerequisite under
RR-S02/RR-S12 (with a distinct tracked deliverable if needed). RR-CAD-07 can then
release a reviewed fabrication pack without claiming the specimen exists.
Preserve the freeze-before-loading requirement and all evidence criteria.
This plan identifies that staging repair but does not change or bypass the
current ledger. Until reconciled, deliver a draft handoff and leave closure open.

### First fixture feasibility check and stop criteria

Hypothesis: the proposed fixture can distinguish specimen compliance from
fixture translation/rotation within the existing uncertainty gate on both axes.
Use reviewed tube/material/load-line inputs, proposed fixture geometry and actual
instrument records where available. Vary fixture dimensions and observation
spacing; hold the approved specimen and trial matrix fixed. Calculate load-point
stiffness and propagate force, tip, root translation, root rotation, repeatability
and reference uncertainty through the actual fitted-compliance estimator.

The [measurement contract](CAD_MEASUREMENT_CONTRACT.md) gives the nominal scale:
775.984 N/mm specimen stiffness, approximately 7,759.84 N/mm minimum fixture
stiffness per axis, and only 5.155 µm specimen motion at 4 N. A 50 µrad root
rotation at a 100 mm lever contributes 5 µm; a rigid-looking CAD model is not
an adequate check. Recompute these quantities for accepted inputs.

Within A5's initial 5 h allowance, produce a feasibility result or a named
missing-input/design-change list before finishing presentation drawings. Pass
requires both stiffness ratios ≥10, tip/root resolution ≤0.001 mm, ≥20 predicted
counts at full scale, and fitted-compliance relative expanded U95 ≤10% with a
reviewed complete budget. Missing terms mean unresolved, not zero. If the
layout fails, change restraint, metrology or geometry and re-review affected
targets; do not relax the frozen gates or close the task on illustrative math.
Any correction that changes the measured observable needs a prospective
protocol amendment before campaign loads.

## Optional work without hardware

Selection: `____` (`nominal package` | `audit` | `both` | `neither`).
If both, preferred first deliverable: `____`.

- **Nominal CAD/FEA package:** first reconcile existing tube STEP, parameter
  hashes, hand model and committed FEA into a reproducible design package and
  report. Reuse existing results with their limitations; rerun a model only
  for a stated change or reproduction need. Current inputs support the nominal
  tube, not an unspecified real clamp/bracket. Missing interfaces permit only
  explicitly scoped design proposals with assumptions, never a released
  assembly. Define proposed outputs and acceptance checks in a small work order
  before implementation; completion does not close RR-CAD-02/04/05 or any
  physical gate. Prefer this option when the objective is an engineering
  deliverable and hardware records remain unavailable.
- **Ponytail audit:** inspect `experiments/` and `cad/` and produce a ranked
  keep/delete/simplify list with caller, CLI, CI, documentation and artifact-
  lineage evidence. These experiment scripts can be standalone entry points;
  absence of imports is not proof of dead code. Any deletion PR follows the
  findings and relevant behavioral/reproduction checks. Zero justified
  deletions is an acceptable audit outcome. This plan does not execute the audit.

## Verification and handoff

For this plan-only PR, run from the repository root:

```sh
python3 cad/ledger_validator.py live
python3 cad/input_requests.py --check
python3 cad/fixture_contract.py --check
python3 cad/fixture_contract.py --check-draft
python3 cad/modal_freeze.py --check-draft
git diff --check
git diff --exit-code origin/main -- docs/CAD_TASKS.csv docs/SPRINT_TASKS.csv
```

Expect all exits 0; the two draft checks still print `DRAFT_BLOCKED`.
Run each strict command separately and record its expected exit 2:

```sh
python3 cad/fixture_contract.py --release
python3 cad/modal_freeze.py
```

The live ledger validator also checks local Markdown links and rejects its nine
invalid dependency/status mutations; it cannot judge scientific readiness.
Record these results and exact candidate identity in the PR. Observe hosted CI
and Docker checks; the path-filtered CAD workflow need not run on a docs-only
change. Do not describe an untriggered workflow as newly passed.

During A2 register updates, regenerate **both** derived artifacts, then check:

```sh
python cad/input_requests.py
python cad/fixture_contract.py --refresh
python cad/input_requests.py --check
python cad/fixture_contract.py --check
```

For executable changes, use the corresponding separate environment from
[START_HERE.md](START_HERE.md): portable Python 3.10 evidence checks, pinned
CadQuery tests for CAD changes, and legacy Gym only when simulation changes.
Every changed generator keeps source, generated artifact and tests consistent.
Record expected refusals as such; never use shell success alone as an engineering
verdict. Future status updates belong in the existing ledgers with verified
dependencies and evidence, not in a competing checklist here.

## Boundary and resume

This PR supplies the critique and replacement work order. No Owner measurements,
choices or approvals are invented. It does not authorize spending, fabrication,
powered hardware, acquisition, outreach, or repository housekeeping. Preserve
existing static thresholds and distinguish software checks, nominal design,
as-built predictions and physical results.

Next implementation session: read this file and both ledgers, check current main,
normalize supplied inputs through A2, and run the smallest selected ready branch.
If no inputs or optional selection arrive, report the exact unresolved records;
do not turn the placeholder form into evidence or claim the whole project done.
