#!/usr/bin/env python3
"""Mast modal tap test — fail-closed preregistration generator.

usage: python experiments/tap_test_prereg.py            # (re)write docs/specs/mast-modal-tap-test/preregistration.md
       python experiments/tap_test_prereg.py --check    # fail if the committed document is stale
       python experiments/tap_test_prereg.py --release  # exit 2 REFUSED while the band cannot be computed

The document this writes is a preregistration SKELETON: the hypothesis, the prediction sources,
the committed form of the acceptance band and the procedural rules are frozen now; the numeric
band is REFUSED until every row of cad/roboracer/modal-inputs.csv is filled by inspection,
measurement or an owner decision. No pass band is invented from a register that has no
calibrated modal uncertainty (cad/roboracer/fixture-preparation.md). Nominal frequencies are
computed with the repository's own hand-calculation code from the registered geometry and read
from the committed FEA summary; they are current expectations, not the frozen prediction.
"""
from __future__ import annotations
import argparse, csv, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import mast_hand_calc as HC  # noqa: E402  (repo's own f1 = (1/2pi) sqrt(k_eff/m_eff), m_eff = m_tip + 0.23 m_mast)

REGISTER = ROOT / "cad/roboracer/parameters.csv"
MODAL = ROOT / "cad/roboracer/modal-inputs.csv"
FEA_SUMMARY = ROOT / "runs/mast_fea/fea_summary.txt"
BASELINE_DOC = ROOT / "docs/design/16_mechanical_design_analysis.md"
OUTPUT = ROOT / "docs/specs/mast-modal-tap-test/preregistration.md"
PREREG_VERSION = "2026-09-11-skeleton"
GUARD_HZ = 200.0  # design criterion from docs/design/16_mechanical_design_analysis.md; not a modal-test threshold
COVERAGE_K = 2.0  # expanded uncertainty factor committed now


class PreregInputError(ValueError):
    """Inputs cannot support the document as written. Fail closed."""


def _read(path: Path) -> dict:
    rows = {}
    for r in csv.DictReader(path.open(newline="", encoding="utf-8")):
        if r["parameter"] in rows:
            raise PreregInputError(f"duplicate parameter in {path.name}: {r['parameter']}")
        state, raw = r["evidence_state"].strip(), r["value"].strip()
        if state == "pending" and raw:
            raise PreregInputError(f"pending parameter carries a value in {path.name}: {r['parameter']}")
        if state != "pending":
            try:
                raw = float(raw)
            except ValueError:
                raise PreregInputError(f"non-numeric value in {path.name}: {r['parameter']}={raw!r}")
            if not math.isfinite(raw) or raw <= 0:
                raise PreregInputError(f"value must be finite and positive: {r['parameter']}")
        rows[r["parameter"]] = dict(value=None if state == "pending" else raw, unit=r["unit"], state=state,
                                    source=r["source"], release=r["release_requirement"])
    return rows


def nominal_hand_f1(reg: dict) -> dict:
    """Hand-model f1 from the registered geometry via the repository's own function."""
    need = {"mast_length": "mm", "mast_outer_diameter": "mm", "mast_wall_thickness": "mm",
            "youngs_modulus": "N/mm^2", "density": "kg/m^3", "tip_total_mass": "kg"}
    for n, u in need.items():
        if n not in reg or reg[n]["unit"] != u or reg[n]["value"] is None:
            raise PreregInputError(f"register row unusable for the hand model: {n} (need unit {u}, non-pending)")
    L = reg["mast_length"]["value"] * 1e-3; od = reg["mast_outer_diameter"]["value"] * 1e-3
    t = reg["mast_wall_thickness"]["value"] * 1e-3; E = reg["youngs_modulus"]["value"] * 1e6
    sec = HC.section_properties(od, od - 2 * t, L, reg["density"]["value"])
    f1, k_eff, m_eff = HC.first_natural_frequency(sec, length=L, E=E, m_tip=reg["tip_total_mass"]["value"])
    states = sorted({reg[n]["state"] for n in need})
    return dict(f1_hz=f1, k_eff_n_per_m=k_eff, m_eff_kg=m_eff, mast_mass_kg=sec.mast_mass, input_states=states)


def committed_fea_f1(path: Path = FEA_SUMMARY) -> float:
    m = re.search(r"f1 \(1st bending\) \[Hz\]\s+([\d.]+)\s+([\d.]+)", path.read_text())
    if not m:
        raise PreregInputError(f"cannot read f1 from {path}")
    return float(m.group(2))


def rejected_baseline_f1(path: Path = BASELINE_DOC) -> float:
    m = re.search(r"\*\*(\d+\.\d) Hz\*\* \| \*\*(\d+\.\d) Hz\*\*", path.read_text())
    if m:  # table row "| **174.7 Hz** | **330.1 Hz** |" style is not guaranteed; fall back to the labelled cell
        return float(m.group(1))
    m = re.search(r"f1 = \(1/2π\)·√\(k_eff/m_eff\)`? \| \*\*(\d+\.\d) Hz\*\*", path.read_text())
    if not m:
        raise PreregInputError(f"cannot read the rejected baseline f1 from {path}")
    return float(m.group(1))


def band(modal: dict) -> dict:
    """Acceptance band in the committed form; None while any input is pending."""
    pending = [n for n, r in modal.items() if r["state"] == "pending"]
    out = {"pending_inputs": pending, "form": (
        "ACCEPT if |f_meas - f_pred| / f_pred <= delta_model + U95_meas / f_pred, where "
        "f_pred = as_built_f1_prediction, delta_model = model_discrepancy_tolerance_rel, "
        "U95_meas = k * u_f with k = %.0f, and u_f / f = sqrt( 0.25*[(u_k/k)^2 + (u_m/m)^2] + "
        "(1/(T f sqrt(12)))^2 + s_rep^2 ), s_rep = standard deviation of the per-tap f1 over taps_per_axis / sqrt(taps_per_axis). "
        "Each axis is judged separately; the guard f_meas >= %.0f Hz is a design criterion reported alongside, not the test verdict." % (COVERAGE_K, GUARD_HZ))}
    if pending:
        out["band_hz"] = None
        return out
    f = modal["as_built_f1_prediction"]["value"]; d = modal["model_discrepancy_tolerance_rel"]["value"]
    uk, um = modal["stiffness_rel_std_uncertainty"]["value"], modal["modal_mass_rel_std_uncertainty"]["value"]
    T = modal["record_duration"]["value"]
    u_rel_model = 0.5 * math.sqrt(uk**2 + um**2)
    u_rel_res = 1.0 / (T * f * math.sqrt(12))
    u_rel = math.sqrt(u_rel_model**2 + u_rel_res**2)  # s_rep is a campaign output; entered at evaluation time
    half = d + COVERAGE_K * u_rel
    out.update(band_hz=[f * (1 - half), f * (1 + half)], half_width_rel=half,
               components=dict(delta_model=d, u_rel_model=u_rel_model, u_rel_resolution=u_rel_res))
    return out


def render(reg: dict, modal: dict) -> str:
    hand = nominal_hand_f1(reg); fea = committed_fea_f1(); base = rejected_baseline_f1(); b = band(modal)
    n_pend = len(b["pending_inputs"])
    status = (f"**SKELETON — acceptance band REFUSED: {n_pend} of {len(modal)} modal inputs pending.** "
              "No tap has been recorded; no fixture or accelerometer exists in the register.") if n_pend else \
             f"**FROZEN — band {b['band_hz'][0]:.1f}–{b['band_hz'][1]:.1f} Hz (half-width {100*b['half_width_rel']:.1f} %).**"
    rows = "\n".join(f"| `{n}` | {r['unit']} | {r['state']} | {'' if r['value'] is None else r['value']} | {r['release']} |"
                     for n, r in modal.items())
    return f"""# Mast modal tap test — preregistration ({PREREG_VERSION})

{status}

Regenerated by `python experiments/tap_test_prereg.py`; `--check` fails when this file is stale and
`--release` exits 2 while the band is REFUSED. A numeric band appearing here while
[modal-inputs.csv](../../../cad/roboracer/modal-inputs.csv) still has pending rows is a defect, not a result.

## Sequence and scope

Static compliance ([frozen protocol](../mast-physical-validation/design.md)) is finished first; the tap test is a
separate prospective protocol ([decision](../../../cad/roboracer/fixture-preparation.md)). The static protocol's
±15 % agreement and U95 ≤ 10 % are not modal thresholds. The {GUARD_HZ:.0f} Hz guard is a design criterion and is
reported alongside the verdict, never substituted for it.

## Hypothesis

The as-built mast's first bending frequency on each axis agrees with the committed as-built prediction
within the band defined below. The test can fail: a measured f1 outside the band on either axis is a
recorded discrepancy against the model, reported as such.

## Prediction sources — current expectations, not the frozen prediction

| Source | f1 | Basis | Evidence state |
| --- | --- | --- | --- |
| Hand model on the registered geometry | {hand['f1_hz']:.1f} Hz | `experiments/mast_hand_calc.first_natural_frequency`: k_eff = {hand['k_eff_n_per_m']:.1f} N/m, m_eff = {hand['m_eff_kg']:.4f} kg (m_tip {reg['tip_total_mass']['value']} kg + 0.23 × {hand['mast_mass_kg']*1e3:.2f} g) | {', '.join(hand['input_states'])} |
| Committed nominal FEA | {fea:.1f} Hz | `runs/mast_fea/fea_summary.txt`, root ENCASTRE, nominal geometry | committed_simulation |
| Rejected §3.1 baseline (L = 120 mm, OD 16 mm) | {base:.1f} Hz | `docs/design/16_mechanical_design_analysis.md` | rejected design — **not** the test target |

The frozen prediction is `as_built_f1_prediction`: an as-built modal model on inspected geometry with
installed sensor/bracket/cable mass and the root restraint measured in the static campaign, committed
(source and value) before any tap record exists. Neither nominal value above is an as-built observation,
and the hand-vs-FEA gap ({100*abs(hand['f1_hz']-fea)/hand['f1_hz']:.1f} % of the hand value, as `fea_summary.txt` reports) is information for choosing
`model_discrepancy_tolerance_rel`, not a substitute for it.

## Acceptance band — form committed now, numbers refused until inputs exist

{b['form']}

Band: {'REFUSED — pending: ' + ', '.join(f'`{p}`' for p in b['pending_inputs']) if b['band_hz'] is None else f"{b['band_hz'][0]:.2f}–{b['band_hz'][1]:.2f} Hz"}

Model discrepancy tolerance and measurement uncertainty are kept as separate terms so that widening
one cannot be disguised as the other. Coverage factor k = {COVERAGE_K:.0f} is committed here.

## Modal input register

| parameter | unit | evidence_state | value | release requirement |
| --- | --- | --- | --- | --- |
{rows}

## Procedural rules frozen now

- Excite bending away from the root node; observe near the tip; both axes; `taps_per_axis` repeats fixed before acquisition.
- Record the actual DAQ rate, anti-aliasing filter, record duration and installed accelerometer/cable mass; mass loading is quantified, never assumed negligible.
- Every raw record is kept; exclusions keep the source rows and a written reason.
- The as-built prediction commit and this document's frozen revision both precede the first tap; their hashes are recorded in the campaign evidence.
- Outcome reporting: per-axis measured f1 with U95, the band, ACCEPT/REJECT per axis, and the guard comparison — including a REJECT.
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--release", action="store_true")
    parser.add_argument("--modal", type=Path, default=MODAL)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        reg, modal = _read(REGISTER), _read(args.modal)
        text = render(reg, modal)
        b = band(modal)
    except PreregInputError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != text:
            print("Preregistration document is missing or stale; run python experiments/tap_test_prereg.py", file=sys.stderr)
            return 1
    elif args.release:
        if b["band_hz"] is None:
            print("REFUSED: acceptance band not computable; pending modal inputs: " + ", ".join(b["pending_inputs"]), file=sys.stderr)
            return 2
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(f"Tap-test preregistration {PREREG_VERSION}: band "
          f"{'REFUSED (%d pending inputs)' % len(b['pending_inputs']) if b['band_hz'] is None else 'computed'}; no measurement exists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
