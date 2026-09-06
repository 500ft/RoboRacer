#!/usr/bin/env python3
"""Evaluate the preregistered LiDAR-mast static compliance experiment.

The physical test measures displacement per applied force (compliance, mm/N).
It does not measure stress. Raw rows must use this schema:

    axis,cycle,direction,force_n,tip_mm,fixture_mm

``fixture_mm`` is subtracted row-by-row before fitting. The protocol and frozen
thresholds live in ``docs/specs/mast-physical-validation/design.md``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


CRASH_FORCE_N = 128.76
HAND_DEFLECTION_MM = 0.166
FEA_DEFLECTION_MM = 0.176
HAND_COMPLIANCE_MM_PER_N = HAND_DEFLECTION_MM / CRASH_FORCE_N
FEA_COMPLIANCE_MM_PER_N = FEA_DEFLECTION_MM / CRASH_FORCE_N

MIN_R_SQUARED = 0.99
MAX_HYSTERESIS_FRACTION = 0.05
MAX_RELATIVE_U95 = 0.10
MAX_FEA_RELATIVE_ERROR = 0.15
REQUIRED_INDICATOR_COUNTS = 20.0
LOAD_LEVELS_N = (4.0, 8.0, 12.0, 16.0, 20.0)


@dataclass(frozen=True)
class AxisMetrics:
    axis: str
    rows: int
    compliance_mm_per_n: float
    intercept_mm: float
    r_squared: Optional[float]
    hysteresis_fraction: Optional[float]
    fea_relative_error: Optional[float]


@dataclass(frozen=True)
class Verdict:
    classification: str
    reasons: List[str]
    relative_u95: float
    fixture_subtracted: bool
    axes: List[AxisMetrics]
    evidence_kind: str
    reference_identity: Optional[str]


@dataclass(frozen=True)
class Campaign:
    """Validated file provenance, not authentication of a physical experiment."""

    evidence_kind: str
    compliance_mm_per_n: Dict[str, float]
    relative_u95: float
    resolution_mm: float
    reference_identity: str
    rows_identity: str
    manifest_path: Path
    raw_csv_path: Path


def _finite(value: object, name: str, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(name + " must be finite numeric data") from exc
    if isinstance(value, bool) or not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(name + " must be finite" + (" and positive" if positive else ""))
    return result


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " must be non-empty text")
    return value.strip()


def _object(value: object, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(name + " must be a JSON object")
    return value


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rows_identity(rows: Iterable[Dict[str, object]]) -> str:
    # Canonical parsed cells bind the in-process rows to the checked CSV.
    return _sha(json.dumps(list(rows), sort_keys=True, allow_nan=False).encode())


def load_campaign(path: Path, raw_csv: Path) -> Campaign:
    """Load a versioned campaign and verify local artifact/source identities."""

    metadata = _object(json.loads(path.read_text(encoding="utf-8")), "campaign")
    if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
        raise ValueError("campaign schema_version must be 1")
    kind = metadata.get("evidence_kind")
    if kind not in ("physical", "synthetic"):
        raise ValueError("evidence_kind must be physical or synthetic")
    for key in ("specimen_id", "drawing_revision", "operator", "clamp_method"):
        _text(metadata.get(key), key)
    _finite(metadata.get("ambient_temperature_c"), "ambient_temperature_c")
    test_date = date.fromisoformat(_text(metadata.get("test_date"), "test_date"))
    root = path.resolve().parent

    def artifact(key: str) -> Tuple[Path, bytes]:
        record = _object(metadata.get(key), key)
        rel = Path(_text(record.get("path"), key + ".path"))
        resolved = (root / rel).resolve()
        if rel.is_absolute() or not resolved.is_relative_to(root):
            raise ValueError(key + " must stay within the campaign directory")
        digest = _text(record.get("sha256"), key + ".sha256")
        data = resolved.read_bytes()
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or _sha(data) != digest:
            raise ValueError(key + " SHA-256 mismatch")
        if not data.strip():
            raise ValueError(key + " artifact is empty")
        return resolved, data

    csv_path, csv_bytes = artifact("raw_csv")
    if csv_path != raw_csv.resolve() or csv_bytes != raw_csv.read_bytes():
        raise ValueError("campaign raw_csv does not identify the supplied CSV")
    ref_path, ref_bytes = artifact("reference")
    _, inspection_bytes = artifact("inspection")
    _, calibration_bytes = artifact("calibration")
    _, uncertainty_bytes = artifact("uncertainty")
    artifact("zero_checks")
    artifact("setup")
    ref = _object(json.loads(ref_bytes), "reference")
    inspection = _object(json.loads(inspection_bytes), "inspection")
    calibration = _object(json.loads(calibration_bytes), "calibration")
    uncertainty = _object(json.loads(uncertainty_bytes), "uncertainty")
    for record, name in ((ref, "reference"), (inspection, "inspection"),
                         (uncertainty, "uncertainty")):
        if record.get("specimen_id") != metadata["specimen_id"]:
            raise ValueError(name + " specimen_id mismatch")
        if record.get("evidence_kind") != kind:
            raise ValueError(name + " evidence_kind mismatch")
    for record in (ref, inspection):
        if record.get("drawing_revision") != metadata["drawing_revision"]:
            raise ValueError("drawing_revision mismatch")
    if ref.get("reference_kind") != ("as_built" if kind == "physical" else "synthetic"):
        raise ValueError("reference is not the required as-built/synthetic reference")
    if ref.get("inspection_sha256") != _sha(inspection_bytes):
        raise ValueError("reference inspection linkage mismatch")
    _text(ref.get("boundary_conditions"), "reference boundary_conditions")
    _text(ref.get("solver_version"), "reference solver_version")
    _text(ref.get("model_revision"), "reference model_revision")
    source_commit = _text(ref.get("source_commit"), "reference source_commit")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be a full Git SHA")
    repo = Path(__file__).resolve().parents[1]
    check = subprocess.run(["git", "cat-file", "-t", source_commit], cwd=repo,
                           capture_output=True, text=True, check=False)
    if check.returncode or check.stdout.strip() != "commit":
        raise ValueError("reference source_commit does not resolve to a commit")
    if kind == "physical":
        # The prediction must be a reviewed, committed artifact, not a nominal
        # constant or a reference edited after observing the measurements.
        try:
            ref_rel = ref_path.relative_to(repo)
        except ValueError as exc:
            raise ValueError("physical reference must be inside this repository") from exc
        reference_commit = _text(metadata.get("reference_commit"), "reference_commit")
        if not re.fullmatch(r"[0-9a-f]{40}", reference_commit):
            raise ValueError("reference_commit must be a full Git SHA")
        frozen = subprocess.run(["git", "show", reference_commit + ":" + ref_rel.as_posix()],
                                cwd=repo, capture_output=True, check=False)
        if frozen.returncode or frozen.stdout != ref_bytes:
            raise ValueError("as-built reference does not match its committed version")
        frozen_at = subprocess.run(["git", "show", "-s", "--format=%cI", reference_commit],
                                   cwd=repo, capture_output=True, text=True, check=False)
        started_at = datetime.fromisoformat(_text(metadata.get("test_started_at"), "test_started_at"))
        if started_at.tzinfo is None or started_at.date() != test_date:
            raise ValueError("test_started_at requires timezone and must match test_date")
        if frozen_at.returncode or datetime.fromisoformat(frozen_at.stdout.strip()) >= started_at:
            raise ValueError("reference must be committed before the campaign start")
    compliances = _object(ref.get("compliance_mm_per_n"), "compliance_mm_per_n")
    if set(compliances) != {"x", "y"}:
        raise ValueError("reference requires exactly x/y compliances")
    compliances = {axis: _finite(value, axis + " compliance", True)
                   for axis, value in compliances.items()}
    for key in ("length_mm", "od_mm", "wall_mm", "clamp_engagement_mm", "load_height_mm"):
        _finite(inspection.get(key), "inspection " + key, True)
    if 2 * float(inspection["wall_mm"]) >= float(inspection["od_mm"]):
        raise ValueError("inspection tube wall is inconsistent with OD")
    if calibration.get("evidence_kind") != kind:
        raise ValueError("calibration evidence_kind mismatch")
    for key in ("force_instrument_id", "tip_instrument_id", "fixture_instrument_id"):
        _text(calibration.get(key), key)
    calibrated = date.fromisoformat(_text(calibration.get("calibration_date"), "calibration_date"))
    if calibrated > test_date:
        raise ValueError("calibration must precede the campaign")
    resolution = _finite(calibration.get("resolution_mm"), "resolution_mm", True)
    u95 = _finite(uncertainty.get("relative_u95"), "relative_u95", True)
    _text(uncertainty.get("method"), "uncertainty method")
    _text(uncertainty.get("reviewed_by"), "uncertainty reviewed_by")
    components = _object(uncertainty.get("components"), "uncertainty components")
    for key in ("force", "tip", "fixture", "repeatability", "reference"):
        _text(components.get(key), "uncertainty " + key)
    return Campaign(kind, compliances, u95, resolution,
                    (metadata.get("reference_commit", source_commit)) + ":sha256:" + _sha(ref_bytes),
                    _rows_identity(read_csv(raw_csv)), path.resolve(), raw_csv.resolve())


def predicted_deflection_mm(force_n: float, compliance_mm_per_n: float = FEA_COMPLIANCE_MM_PER_N) -> float:
    """Return the linear-elastic predicted deflection at ``force_n``."""

    force_n = _finite(force_n, "force_n")
    compliance_mm_per_n = _finite(compliance_mm_per_n, "compliance", True)
    if force_n < 0:
        raise ValueError("force_n must be non-negative")
    return force_n * compliance_mm_per_n


def indicator_counts_at_load(force_n: float, resolution_mm: float) -> float:
    """Return predicted displacement expressed in indicator resolution counts."""

    resolution_mm = _finite(resolution_mm, "resolution_mm", True)
    return predicted_deflection_mm(force_n) / resolution_mm


def indicator_is_adequate(force_n: float, resolution_mm: float) -> bool:
    """Require at least 20 predicted counts at the maximum planned load."""

    return indicator_counts_at_load(force_n, resolution_mm) >= REQUIRED_INDICATOR_COUNTS


def _linear_fit(points: Sequence[Tuple[float, float]]) -> Tuple[float, float, Optional[float]]:
    if len(points) < 2:
        raise ValueError("at least two points are required for a fit")
    mean_x = sum(p[0] for p in points) / len(points)
    mean_y = sum(p[1] for p in points) / len(points)
    ss_x = sum((x - mean_x) ** 2 for x, _ in points)
    if ss_x <= 0:
        raise ValueError("force values must span more than one level")
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / ss_x
    intercept = mean_y - slope * mean_x
    residual = sum((y - (slope * x + intercept)) ** 2 for x, y in points)
    total = sum((y - mean_y) ** 2 for _, y in points)
    r_squared = None if total == 0 else 1.0 - residual / total
    for value in (slope, intercept, residual, total):
        _finite(value, "derived fit")
    return slope, intercept, r_squared


def _hysteresis_fraction(rows: Sequence[Dict[str, object]], slope: float) -> Optional[float]:
    paired: DefaultDict[Tuple[int, float], Dict[str, List[float]]] = defaultdict(
        lambda: {"load": [], "unload": []}
    )
    corrected = []
    for row in rows:
        value = float(row["tip_mm"]) - float(row["fixture_mm"])
        corrected.append(value)
        level = float(row["load_level_n"])
        key = (int(row["cycle"]), level)
        direction = str(row["direction"]).strip().lower()
        if direction not in ("load", "unload"):
            raise ValueError("direction must be 'load' or 'unload'")
        paired[key][direction].append(value - slope * (float(row["force_n"]) - level))

    full_scale = max(corrected) - min(corrected)
    if full_scale <= 0:
        return None
    differences = []
    for directions in paired.values():
        if directions["load"] and directions["unload"]:
            mean_load = sum(directions["load"]) / len(directions["load"])
            mean_unload = sum(directions["unload"]) / len(directions["unload"])
            differences.append(abs(mean_load - mean_unload))
    if not differences:
        return None
    return max(differences) / full_scale


def evaluate_rows(rows: Iterable[Dict[str, object]], relative_u95: float,
                  campaign: Optional[Campaign] = None) -> Verdict:
    """Fit each axis and apply the frozen quality/agreement classification."""

    relative_u95 = _finite(relative_u95, "relative_u95")
    if relative_u95 < 0:
        raise ValueError("relative_u95 must be non-negative")
    rows = list(rows)
    if campaign is not None:
        if not isinstance(campaign, Campaign):
            raise ValueError("campaign must be loaded by load_campaign")
        # Do not trust a constructed or stale dataclass in the public API.
        # Recheck files at evaluation time, then use only the loaded values.
        campaign = load_campaign(campaign.manifest_path, campaign.raw_csv_path)
        if campaign.relative_u95 != relative_u95:
            raise ValueError("relative_u95 differs from campaign uncertainty record")
        if _rows_identity(rows) != campaign.rows_identity:
            raise ValueError("measurement rows differ from campaign CSV")
    grouped: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)
    fixture_subtracted = True
    for source in rows:
        row = dict(source)
        required = ("axis", "cycle", "direction", "force_n", "tip_mm", "fixture_mm")
        missing = [key for key in required if key not in row or row[key] in (None, "")]
        if missing:
            if "fixture_mm" in missing:
                fixture_subtracted = False
            raise ValueError("missing required values: " + ", ".join(missing))
        axis = str(row["axis"]).strip().lower()
        if axis not in ("x", "y"):
            raise ValueError("axis must be x or y")
        cycle = _finite(row["cycle"], "cycle", True)
        if not cycle.is_integer():
            raise ValueError("cycle must be a positive integer")
        row["cycle"] = int(cycle)
        direction = str(row["direction"]).strip().lower()
        if direction not in ("load", "unload"):
            raise ValueError("direction must be load or unload")
        row["direction"] = direction
        row["force_n"] = _finite(row["force_n"], "force_n", True)
        row["tip_mm"] = _finite(row["tip_mm"], "tip_mm")
        row["fixture_mm"] = _finite(row["fixture_mm"], "fixture_mm")
        level = _finite(row.get("load_level_n", row["force_n"]), "load_level_n", True)
        if level not in LOAD_LEVELS_N or abs(row["force_n"] - level) >= 2.0:
            raise ValueError("load level must be 4/8/12/16/20 N with an unambiguous measured force")
        row["load_level_n"] = level
        grouped[axis].append(row)

    if not grouped:
        raise ValueError("no measurement rows supplied")
    if set(grouped) != {"x", "y"}:
        raise ValueError("both x/y axes are required")
    for axis, axis_rows in grouped.items():
        cycles = {row["cycle"] for row in axis_rows}
        if len(cycles) < 3:
            raise ValueError(axis + " axis requires at least three complete cycles")
        cells = [(row["cycle"], row["direction"], row["load_level_n"]) for row in axis_rows]
        required = {(cycle, direction, level) for cycle in cycles
                    for direction in ("load", "unload") for level in LOAD_LEVELS_N}
        if len(set(cells)) != len(cells) or set(cells) != required:
            raise ValueError(axis + " axis has missing or duplicate cycle/direction/load cells")

    axes = []
    for axis, axis_rows in sorted(grouped.items()):
        points = [
            (float(row["force_n"]), float(row["tip_mm"]) - float(row["fixture_mm"]))
            for row in axis_rows
        ]
        slope, intercept, r_squared = _linear_fit(points)
        hysteresis = _hysteresis_fraction(axis_rows, slope)
        axes.append(
            AxisMetrics(
                axis=axis,
                rows=len(axis_rows),
                compliance_mm_per_n=slope,
                intercept_mm=intercept,
                r_squared=r_squared,
                hysteresis_fraction=hysteresis,
                fea_relative_error=(abs(slope - campaign.compliance_mm_per_n[axis])
                                    / campaign.compliance_mm_per_n[axis]) if campaign else None,
            )
        )

    reasons = []
    if campaign is None:
        reasons.append("traceable campaign and as-built reference not supplied")
    elif campaign.resolution_mm > 0.001 or any(
        20.0 * compliance / campaign.resolution_mm < REQUIRED_INDICATOR_COUNTS
        for compliance in campaign.compliance_mm_per_n.values()
    ):
        reasons.append("indicator resolution or 20-count measurability screen fails")
    if not fixture_subtracted:
        reasons.append("fixture motion was not subtracted")
    if relative_u95 > MAX_RELATIVE_U95:
        reasons.append("relative U95 exceeds 10%")
    for axis in axes:
        if axis.compliance_mm_per_n <= 0:
            reasons.append("{}-axis compliance is not positive".format(axis.axis))
        if axis.r_squared is None or axis.r_squared < MIN_R_SQUARED:
            reasons.append("{}-axis R^2 is undefined or below 0.99".format(axis.axis))
        if axis.hysteresis_fraction is None or axis.hysteresis_fraction > MAX_HYSTERESIS_FRACTION:
            reasons.append("{}-axis hysteresis is undefined or exceeds 5%".format(axis.axis))

    if reasons:
        classification = "INCONCLUSIVE"
    else:
        disagreement = [
            axis for axis in axes if axis.fea_relative_error is not None
            and axis.fea_relative_error > MAX_FEA_RELATIVE_ERROR
        ]
        if disagreement:
            classification = "DISCREPANCY"
            reasons.append("as-built compliance differs from as-built FEA by more than 15%")
        else:
            classification = "VALIDATED"
            reasons.append("all quality gates pass and compliance is within 15% of as-built FEA")
        if campaign.evidence_kind == "synthetic":
            classification = "SIMULATED_DISCREPANCY" if disagreement else "SIMULATED_AGREEMENT"
            reasons = ["synthetic software exercise only; no physical validation"]

    return Verdict(
        classification=classification,
        reasons=reasons,
        relative_u95=relative_u95,
        fixture_subtracted=fixture_subtracted,
        axes=axes,
        evidence_kind=campaign.evidence_kind if campaign else "unverified",
        reference_identity=campaign.reference_identity if campaign else None,
    )


def read_csv(path: Path) -> List[Dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV header is absent or contains duplicate columns")
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError("CSV contains extra cells without headers")
        return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="raw measurement CSV")
    parser.add_argument("--campaign", type=Path, required=True,
                        help="version-1 campaign JSON with checked reference and instrument records")
    parser.add_argument(
        "--relative-u95",
        type=float,
        help="optional compatibility check; must equal the campaign uncertainty record",
    )
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    args = parser.parse_args()

    try:
        campaign = load_campaign(args.campaign, args.csv)
        u95 = campaign.relative_u95 if args.relative_u95 is None else args.relative_u95
        verdict = evaluate_rows(read_csv(args.csv), u95, campaign)
        payload = json.dumps(asdict(verdict), indent=2, sort_keys=True, allow_nan=False)
    except (ValueError, OSError, OverflowError) as exc:
        parser.error(str(exc))
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
