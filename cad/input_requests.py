"""Generate a read-only pending-input request sheet from the canonical register."""
import argparse
import csv
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "cad/roboracer/parameters.csv"
DEFAULT_OUTPUT = ROOT / "cad/roboracer/input-requests.csv"
ROUTES = {
    "lidar_bracket_bolt_pitch": "vendor_drawing",
    "clamp_bolt_pitch": "measurement",
    "optical_center_offset": "measurement",
    "actual_load_height": "measurement",
    "clamp_engagement": "design_then_inspect",
    "root_rotation_station_spacing": "design_then_inspect"
}
FIELDS = ["parameter", "unit", "acquisition", "value", "status", "source", "required_evidence"]


def requests(rows):
    result, seen = [], set()
    for row in rows:
        key = row["parameter"]
        if not key or key in seen:
            raise ValueError("missing or duplicate parameter: " + key)
        seen.add(key)
        if row["evidence_state"] != "pending":
            continue
        if row["value"].strip():
            raise ValueError("pending parameter cannot contain an accepted value: " + key)
        if row["unit"] not in {"mm", "m", "N"}:
            raise ValueError("unreviewed pending unit: " + row["unit"])
        result.append(dict(parameter=key, unit=row["unit"],
                           acquisition=ROUTES.get(key, "unclassified"), value="", status="pending",
                           source=row["source"], required_evidence=row["release_requirement"]))
    return sorted(result, key=lambda r: (r["acquisition"], r["parameter"]))


def render(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if committed derived sheet is stale")
    args = parser.parse_args()
    with REGISTER.open(newline="") as handle:
        text = render(requests(list(csv.DictReader(handle))))
    if args.check:
        if not DEFAULT_OUTPUT.is_file() or DEFAULT_OUTPUT.read_text() != text:
            parser.exit(1, "Input request sheet is missing or stale; run python cad/input_requests.py\n")
    else:
        DEFAULT_OUTPUT.write_text(text, encoding="utf-8")
    print("Input request sheet: consistent; no inputs accepted or measured")


if __name__ == "__main__":
    main()
