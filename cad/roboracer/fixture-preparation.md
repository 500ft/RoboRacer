# Mast fixture and metrology preparation — 2026-09-09

Status: proposed fixture decisions, no fabrication or physical validation. [Input requests](input-requests.csv) mirror every pending row in [parameters.csv](parameters.csv). Run `python cad/input_requests.py --check` to detect stale requests.

## Decisions made now

- Use the already selected 6061-T6 tube, 100 mm effective free length, 20 mm OD and 1.5 mm wall; cut/deburr stock and inspect it. Keep a machined metal split-clamp route as the proposed fixture, not a printed polymer primary clamp. This preserves the material/model basis and avoids an additional creep-dependent boundary. Clamp engagement and bolt coordinates must be calculated and inspected before release, not guessed.
- Prioritize tube/clamp/load fixture over full deck packaging. The fixture must reproduce the actual mast root restraint, load height and tip assembly. A complete vehicle model is not needed to test that observable.
- Investigate the manufacturer UST-10LX mounting drawing, not a generic sensor footprint. [Hokuyo specification C-42-04077, 2015-03-02](https://www.hokuyo-aut.jp/dl/UST-10LX_Specification.pdf), inspected 2026-09-09, confirms 130 g excluding cable and 50×50×70 mm body. This supports the reported body mass only; bracket and moving cable allowances remain assumptions.
- The same manufacturer specification recommends a 200×200×2 mm aluminum heat-sink plate. Do **not** silently add it to the moving assembly: with the model density, that plate alone would be 0.216 kg, exceeding the current 0.175 kg tip allowance. Verify the actual thermal/mounting arrangement and recompute mass/FEA if it changes. No powered-sensor thermal adequacy is claimed.

## Correct target and separate verdicts

[The rejected baseline](../../docs/design/16_mechanical_design_analysis.md) has a hand-model frequency of **174.7 Hz**, below the project's 200 Hz guard. [The selected nominal FEA](../../runs/mast_fea/fea_summary.txt) reports **285.5 Hz**, and the selected hand estimate is 330.1 Hz. Neither is an as-built observation.

The [frozen physical protocol](../../docs/specs/mast-physical-validation/design.md) tests **static compliance only** at 4/8/12/16/20 N, both axes, at least three load/unload cycles. Its ±15% agreement and U95 ≤10% are not automatically modal-test thresholds. The 200 Hz guard is a design criterion, not proof of real motor excitation separation.

Decision: finish static compliance first; keep tap testing as a separate prospective protocol. Before that protocol is frozen, identify accelerometer/DAQ bandwidth and anti-aliasing, installed sensor/cable mass, excitation/response locations on both axes, record duration/frequency resolution, repeatability and an as-built modal model. Excite bending away from the root node and observe near the tip; quantify mass loading rather than assuming a sensor is negligible. No pass band is invented from a register that has no calibrated modal uncertainty.

For the first-mode approximation, f ∝ √(k/m), so uncorrelated relative standard uncertainties propagate as u_f/f ≈ 0.5√[(u_k/k)²+(u_m/m)²]. Installed root flexibility, mode identification and timing uncertainty also matter; they are not supplied by nominal CAD. An acceptance band must distinguish model discrepancy tolerance from measurement uncertainty and be committed before acquiring modal results.

## Static fixture geometry contract before CAD

Apply [the existing measurement contract](../../docs/CAD_MEASUREMENT_CONTRACT.md), including ≥10× specimen translational stiffness **in each axis**, independent tip/root stations ≤0.001 mm resolution, independent root-rotation observation, filled uncertainty and pre-load as-built reference freeze.

Proposed initial layout: two spatially separated root observations with a 100 mm baseline where fixture access permits; actual spacing remains pending until measured. With independent 1 micrometre quantization, differential standard uncertainty is 0.408 micrometres; over 100 mm this is 4.08 microradians, producing another 0.408 micrometres at a 100 mm load height. This is only a planning calculation, not a complete or accepted error budget. Shorter baselines worsen angular sensitivity. A single root indicator does not measure rotation.

Next CAD acceptance: regenerate from reviewed parameters, export STEP and compare tube volume, effective free length, clamp engagement, bolt coordinates, force-line height, root-station baseline and indicator access against the contract. Separate geometry interference from structural stiffness and physical commissioning. Reject missing tolerances or unknown mating datums; retain screenshots only as supplementary evidence.

After fabrication, commit and push inspection-linked, axis-specific as-built predictions **before any campaign load**. Freeze model source and reference commits separately. Do not use the nominal 0.176 mm/128.76 N reference to award physical validation.

## One remaining measurement sitting

Use the generated sheet to identify the actual bracket pattern/optical-center datum, root clamp bolts/engagement, installed load height and root observation spacing. Add weighed body/bracket/moving cable masses and calibrated force/displacement records to the campaign evidence. The model's 50g crash load is not a bench loading instruction. The manufacturer sensor shock specification is not proof that the complete assembly tolerates that assumed crash.

These measurements and installed hardware identities cannot be looked up for an unknown physical assembly. RR-CAD-02 and the physical campaign remain blocked; the fabrication route and observability design are now explicit.

## Completion correction — 2026-09-11

The preparation above did not deliver the executable fixture geometry contract
or a standalone modal preregistration draft. RR-CAD-09 and RR-S11 now track
those omitted software/document deliverables in the existing task ledgers.
The [fixture contract](fixture-contract.json) exists with null targets and
tolerances; it does **not** mean fixture CAD, inspection or metrology is done.
The [modal preregistration](../../docs/specs/mast-physical-validation/modal-preregistration.md)
exists as DRAFT/BLOCKED, not the previously deferred frozen protocol.

```sh
python cad/fixture_contract.py --check-draft
python cad/fixture_contract.py --geometry path/to/cad-observations.json
python cad/fixture_contract.py --check      # derived_from_register matches parameters.csv
python cad/fixture_contract.py --release    # exit 2 REFUSED while any target or register row is pending
```

Draft schema checking prints `DRAFT_BLOCKED`; exit 0 does not release geometry.
Default comparison exits 2 while inputs are unresolved. Before comparison,
the owner/reviewer must supply datum definition, drawing revision, reviewed
targets with absolute tolerances and sources, ordered bolt x/y/z coordinates
in that datum, and independent tip/root/rotation access review. All six pending
register interfaces are represented; no unknown interface has been guessed.
`tube_volume` means the ideal exposed tube reference segment with length
`mast_length` (effective free length), not the entire clamped stock or assembly.
Finite wall/OD and analytic tube volume consistency are checked.

Geometry observation JSON carries `drawing_revision`, the identical `datum`,
`dimensions` (same keys with finite numbers), `units` (same keys with exact
contract units), and `bolt_coordinates_mm` in the same bolt order. Extract
these from regenerated/reimported CAD and review the extraction; this helper
does not itself parse STEP. A successful comparison says only
`MODEL_GEOMETRY_MATCH_ONLY`, not fixture structural acceptance, interference
clearance, as-built evidence or hardware readiness. The existing tube-only
STEP tests remain separate. RR-CAD-02/04/05/06/07 and physical testing remain
blocked as previously recorded.
