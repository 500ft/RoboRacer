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
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Sequence, Tuple


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


@dataclass(frozen=True)
class AxisMetrics:
    axis: str
    rows: int
    compliance_mm_per_n: float
    intercept_mm: float
    r_squared: float
    hysteresis_fraction: float
    fea_relative_error: float


@dataclass(frozen=True)
class Verdict:
    classification: str
    reasons: List[str]
    relative_u95: float
    fixture_subtracted: bool
    axes: List[AxisMetrics]


def predicted_deflection_mm(force_n: float, compliance_mm_per_n: float = FEA_COMPLIANCE_MM_PER_N) -> float:
    """Return the linear-elastic predicted deflection at ``force_n``."""

    if force_n < 0:
        raise ValueError("force_n must be non-negative")
    return force_n * compliance_mm_per_n


def indicator_counts_at_load(force_n: float, resolution_mm: float) -> float:
    """Return predicted displacement expressed in indicator resolution counts."""

    if resolution_mm <= 0:
        raise ValueError("resolution_mm must be positive")
    return predicted_deflection_mm(force_n) / resolution_mm


def indicator_is_adequate(force_n: float, resolution_mm: float) -> bool:
    """Require at least 20 predicted counts at the maximum planned load."""

    return indicator_counts_at_load(force_n, resolution_mm) >= REQUIRED_INDICATOR_COUNTS


def _linear_fit(points: Sequence[Tuple[float, float]]) -> Tuple[float, float, float]:
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
    r_squared = 1.0 if total == 0 and residual == 0 else 1.0 - residual / total
    return slope, intercept, r_squared


def _hysteresis_fraction(rows: Sequence[Dict[str, object]]) -> float:
    paired: DefaultDict[Tuple[int, float], Dict[str, List[float]]] = defaultdict(
        lambda: {"load": [], "unload": []}
    )
    corrected = []
    for row in rows:
        value = float(row["tip_mm"]) - float(row["fixture_mm"])
        corrected.append(value)
        key = (int(row["cycle"]), round(float(row["force_n"]), 6))
        direction = str(row["direction"]).strip().lower()
        if direction not in ("load", "unload"):
            raise ValueError("direction must be 'load' or 'unload'")
        paired[key][direction].append(value)

    full_scale = max(corrected) - min(corrected)
    if full_scale <= 0:
        return math.inf
    differences = []
    for directions in paired.values():
        if directions["load"] and directions["unload"]:
            mean_load = sum(directions["load"]) / len(directions["load"])
            mean_unload = sum(directions["unload"]) / len(directions["unload"])
            differences.append(abs(mean_load - mean_unload))
    if not differences:
        return math.inf
    return max(differences) / full_scale


def evaluate_rows(rows: Iterable[Dict[str, object]], relative_u95: float) -> Verdict:
    """Fit each axis and apply the frozen quality/agreement classification."""

    if relative_u95 < 0:
        raise ValueError("relative_u95 must be non-negative")
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
        grouped[str(row["axis"]).strip().lower()].append(row)

    if not grouped:
        raise ValueError("no measurement rows supplied")

    axes = []
    for axis, axis_rows in sorted(grouped.items()):
        points = [
            (float(row["force_n"]), float(row["tip_mm"]) - float(row["fixture_mm"]))
            for row in axis_rows
        ]
        slope, intercept, r_squared = _linear_fit(points)
        hysteresis = _hysteresis_fraction(axis_rows)
        axes.append(
            AxisMetrics(
                axis=axis,
                rows=len(axis_rows),
                compliance_mm_per_n=slope,
                intercept_mm=intercept,
                r_squared=r_squared,
                hysteresis_fraction=hysteresis,
                fea_relative_error=abs(slope - FEA_COMPLIANCE_MM_PER_N)
                / FEA_COMPLIANCE_MM_PER_N,
            )
        )

    reasons = []
    if not fixture_subtracted:
        reasons.append("fixture motion was not subtracted")
    if relative_u95 > MAX_RELATIVE_U95:
        reasons.append("relative U95 exceeds 10%")
    for axis in axes:
        if axis.r_squared < MIN_R_SQUARED:
            reasons.append("{}-axis R^2 is below 0.99".format(axis.axis))
        if axis.hysteresis_fraction > MAX_HYSTERESIS_FRACTION:
            reasons.append("{}-axis hysteresis exceeds 5%".format(axis.axis))

    if reasons:
        classification = "INCONCLUSIVE"
    else:
        disagreement = [
            axis for axis in axes if axis.fea_relative_error > MAX_FEA_RELATIVE_ERROR
        ]
        if disagreement:
            classification = "DISCREPANCY"
            reasons.append("as-built compliance differs from as-built FEA by more than 15%")
        else:
            classification = "VALIDATED"
            reasons.append("all quality gates pass and compliance is within 15% of as-built FEA")

    return Verdict(
        classification=classification,
        reasons=reasons,
        relative_u95=relative_u95,
        fixture_subtracted=fixture_subtracted,
        axes=axes,
    )


def read_csv(path: Path) -> List[Dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="raw measurement CSV")
    parser.add_argument(
        "--relative-u95",
        type=float,
        required=True,
        help="expanded uncertainty divided by measured compliance (for example 0.08)",
    )
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    args = parser.parse_args()

    verdict = evaluate_rows(read_csv(args.csv), args.relative_u95)
    payload = json.dumps(asdict(verdict), indent=2, sort_keys=True)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
