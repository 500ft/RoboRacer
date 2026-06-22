#!/usr/bin/env python
"""Offline tests for item 11 evidence-chain tooling."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "experiments"))

from bag_evidence import deterministic_zip, sha256_file, validate_manifest
from generate_synthetic_rosbag import create_bag
from rosbag_to_telemetry import convert_bag


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="item11-evidence-test-") as temp_text:
        temp = Path(temp_text)
        bag = temp / "bag"
        telemetry = temp / "repo" / "telemetry.csv"
        metadata = temp / "metadata.json"
        quality = temp / "quality.csv"
        manifest = temp / "MANIFEST.yaml"
        asset_a = temp / "a.zip"
        asset_b = temp / "b.zip"
        create_bag(bag, include_internal_state=True, force=True)
        convert_bag(bag, telemetry, metadata, quality)
        deterministic_zip(bag, asset_a)
        deterministic_zip(bag, asset_b)
        if sha256_file(asset_a) != sha256_file(asset_b):
            raise AssertionError("bag ZIP output is not deterministic")

        converter = REPO_ROOT / "experiments" / "rosbag_to_telemetry.py"
        entry = {
            "name": "synthetic",
            "source": "synthetic-test",
            "topics": ["/ego_racecar/odom", "/drive", "/f1tenth/internal_state"],
            "git_tag": "test",
            "upstream_revision": "",
            "record_command": "generated fixture",
            "rosbag_storage": "sqlite3",
            "clock_source": "system",
            "use_sim_time": False,
            "asset_sha256": sha256_file(asset_a),
            "asset_size_bytes": asset_a.stat().st_size,
            "converter_git_revision": "test",
            "converter_sha256": sha256_file(converter),
            "converter_command": f"{sys.executable} experiments/rosbag_to_telemetry.py --bag {{bag}} --output {{telemetry}} --metadata {{metadata}} --quality {{quality}}",
            "telemetry_path": str(telemetry),
            "telemetry_sha256": sha256_file(telemetry),
            "storage": "local",
            "url": asset_a.as_uri(),
            "access": "local",
        }
        manifest.write_text(yaml.safe_dump({"bags": [entry]}, sort_keys=False), encoding="utf-8")
        validate_manifest(manifest, repo_root=temp / "repo")
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "experiments" / "bag_evidence.py"), "verify", "synthetic", "--manifest", str(manifest), "--reconvert"],
            cwd=REPO_ROOT,
            check=True,
        )
        payload = json.loads(metadata.read_text())
        if payload["steer_rad_source"] != "internal_state":
            raise AssertionError("fixture did not exercise enriched conversion")
    print("bag evidence tests passed")


if __name__ == "__main__":
    main()
