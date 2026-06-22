#!/usr/bin/env python
"""Publish, validate, and verify external ROS-bag evidence assets."""

from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "evidence" / "item11" / "bags" / "MANIFEST.yaml"
REQUIRED_FIELDS = {
    "name",
    "source",
    "topics",
    "git_tag",
    "record_command",
    "rosbag_storage",
    "clock_source",
    "use_sim_time",
    "asset_sha256",
    "asset_size_bytes",
    "converter_git_revision",
    "converter_sha256",
    "converter_command",
    "telemetry_path",
    "telemetry_sha256",
    "storage",
    "url",
    "access",
}
VALID_SOURCES = {"enriched-bridge", "upstream-gym_ros", "synthetic-test"}
VALID_STORAGE = {"github-release", "s3", "local"}
MAX_RELEASE_BYTES = 2_000_000_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"bags": []}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("bags"), list):
        raise ValueError("manifest must contain a top-level 'bags' list")
    return payload


def validate_entry(entry: dict[str, Any], repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS.difference(entry))
    if missing:
        errors.append(f"{entry.get('name', '<unnamed>')}: missing fields {missing}")
        return errors
    name = str(entry["name"])
    if entry["source"] not in VALID_SOURCES:
        errors.append(f"{name}: invalid source {entry['source']!r}")
    if entry["storage"] not in VALID_STORAGE:
        errors.append(f"{name}: invalid storage {entry['storage']!r}")
    if entry["rosbag_storage"] != "sqlite3":
        errors.append(f"{name}: item 11 requires sqlite3 bags")
    if entry["clock_source"] != "system" or bool(entry["use_sim_time"]):
        errors.append(f"{name}: item 11 requires system clock and use_sim_time=false")
    digest_fields = ("asset_sha256", "converter_sha256", "telemetry_sha256")
    for field in digest_fields:
        value = str(entry[field])
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            errors.append(f"{name}: {field} must be a lowercase SHA-256")
    if int(entry["asset_size_bytes"]) <= 0:
        errors.append(f"{name}: asset_size_bytes must be positive")
    if not isinstance(entry["topics"], list) or not entry["topics"]:
        errors.append(f"{name}: topics must be a non-empty list")
    if not str(entry["url"]).startswith(("https://", "file://")):
        errors.append(f"{name}: url must be https:// or file://")
    telemetry_path = repo_root / str(entry["telemetry_path"])
    if not telemetry_path.exists():
        errors.append(f"{name}: missing telemetry {entry['telemetry_path']}")
    elif sha256_file(telemetry_path) != entry["telemetry_sha256"]:
        errors.append(f"{name}: telemetry SHA-256 mismatch")
    return errors


def validate_manifest(path: Path, repo_root: Path = REPO_ROOT) -> None:
    payload = load_manifest(path)
    names: set[str] = set()
    errors: list[str] = []
    for raw_entry in payload["bags"]:
        if not isinstance(raw_entry, dict):
            errors.append("every bags entry must be a mapping")
            continue
        name = str(raw_entry.get("name", ""))
        if name in names:
            errors.append(f"duplicate bag name: {name}")
        names.add(name)
        errors.extend(validate_entry(raw_entry, repo_root))
    if errors:
        raise ValueError("; ".join(errors))


def deterministic_zip(source_dir: Path, destination: Path) -> None:
    if not (source_dir / "metadata.yaml").exists():
        raise ValueError(f"not a ROS 2 bag directory: {source_dir}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in source_dir.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(str(Path(source_dir.name) / path.relative_to(source_dir)))
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def upsert_entry(manifest_path: Path, entry: dict[str, Any]) -> None:
    payload = load_manifest(manifest_path)
    payload["bags"] = [item for item in payload["bags"] if item.get("name") != entry["name"]]
    payload["bags"].append(entry)
    payload["bags"].sort(key=lambda item: str(item["name"]))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def publish(args: argparse.Namespace) -> None:
    bag_dir = args.bag.resolve()
    telemetry = args.telemetry.resolve()
    converter = args.converter.resolve()
    asset_dir = args.asset_dir.resolve()
    asset_path = asset_dir / f"{args.name}.zip"
    deterministic_zip(bag_dir, asset_path)
    size = asset_path.stat().st_size
    if size > MAX_RELEASE_BYTES:
        raise SystemExit("asset exceeds 2 GB; use versioned S3 storage")
    if args.dry_run:
        storage = "local"
        url = asset_path.as_uri()
    else:
        if shutil.which("gh") is None:
            raise SystemExit("gh is required for GitHub release publication")
        dirty_lines = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True
        ).splitlines()
        try:
            allowed_manifest = str(args.manifest.resolve().relative_to(REPO_ROOT))
        except ValueError:
            allowed_manifest = ""
        disallowed = [
            line
            for line in dirty_lines
            if not allowed_manifest or line[3:] != allowed_manifest
        ]
        if disallowed:
            raise SystemExit(
                "commit the evidence-producing code before publishing raw bags; "
                f"unexpected changes: {disallowed}"
            )
        tag_check = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/tags/{args.git_tag}"],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if tag_check.returncode != 0:
            raise SystemExit(f"create and push tag {args.git_tag!r} before publishing raw bags")
        tagged_revision = subprocess.check_output(
            ["git", "rev-list", "-n", "1", args.git_tag], cwd=REPO_ROOT, text=True
        ).strip()
        if tagged_revision != git_revision():
            raise SystemExit(f"tag {args.git_tag!r} must resolve to the current evidence-producing commit")
        release = subprocess.run(
            ["gh", "release", "view", args.git_tag], cwd=REPO_ROOT, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if release.returncode == 0:
            subprocess.run(
                ["gh", "release", "upload", args.git_tag, str(asset_path), "--clobber"],
                cwd=REPO_ROOT,
                check=True,
            )
        else:
            subprocess.run(
                [
                    "gh",
                    "release",
                    "create",
                    args.git_tag,
                    str(asset_path),
                    "--title",
                    "Item 11 ROS-Bag Validation",
                    "--notes",
                    "Raw ROS 2 evidence bags; verify against evidence/item11/bags/MANIFEST.yaml.",
                ],
                cwd=REPO_ROOT,
                check=True,
            )
        storage = "github-release"
        url = f"https://github.com/500ft/RoboRacer/releases/download/{args.git_tag}/{asset_path.name}"
    entry = {
        "name": args.name,
        "source": args.source,
        "topics": args.topic,
        "git_tag": args.git_tag,
        "upstream_revision": args.upstream_revision,
        "record_command": args.record_command,
        "rosbag_storage": "sqlite3",
        "clock_source": "system",
        "use_sim_time": False,
        "rtf_preflight": args.rtf_preflight,
        "rtf_final": args.rtf_final,
        "asset_sha256": sha256_file(asset_path),
        "asset_size_bytes": size,
        "converter_git_revision": git_revision(),
        "converter_sha256": sha256_file(converter),
        "converter_command": args.converter_command,
        "telemetry_path": str(telemetry.relative_to(REPO_ROOT)),
        "telemetry_sha256": sha256_file(telemetry),
        "storage": storage,
        "url": url,
        "access": "public" if not args.dry_run else "local",
    }
    upsert_entry(args.manifest, entry)
    print(yaml.safe_dump(entry, sort_keys=False).strip())


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def find_entry(manifest: Path, name: str) -> dict[str, Any]:
    for entry in load_manifest(manifest)["bags"]:
        if entry.get("name") == name:
            return entry
    raise ValueError(f"unknown bag evidence entry: {name}")


def verify(args: argparse.Namespace) -> None:
    entry = find_entry(args.manifest, args.name)
    errors = validate_entry(entry)
    if errors:
        raise ValueError("; ".join(errors))
    with tempfile.TemporaryDirectory(prefix="item11-bag-") as temp_text:
        temp = Path(temp_text)
        asset = temp / f"{args.name}.zip"
        download(str(entry["url"]), asset)
        if asset.stat().st_size != int(entry["asset_size_bytes"]):
            raise ValueError("asset byte-size mismatch")
        if sha256_file(asset) != entry["asset_sha256"]:
            raise ValueError("asset SHA-256 mismatch")
        if args.reconvert:
            converter = REPO_ROOT / "experiments" / "rosbag_to_telemetry.py"
            if sha256_file(converter) != entry["converter_sha256"]:
                raise ValueError("current converter does not match manifest converter")
            with zipfile.ZipFile(asset) as archive:
                archive.extractall(temp / "bag")
            bag_candidates = list((temp / "bag").glob("*/metadata.yaml"))
            if len(bag_candidates) != 1:
                raise ValueError("asset must contain exactly one ROS 2 bag")
            values = {
                "bag": str(bag_candidates[0].parent),
                "telemetry": str(temp / "telemetry.csv"),
                "metadata": str(temp / "metadata.json"),
                "quality": str(temp / "quality.csv"),
            }
            command = [part.format(**values) for part in shlex.split(entry["converter_command"])]
            subprocess.run(command, cwd=REPO_ROOT, check=True)
            if sha256_file(Path(values["telemetry"])) != entry["telemetry_sha256"]:
                raise ValueError("reconverted telemetry SHA-256 mismatch")
    print(f"Verified bag evidence: {args.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--bag", type=Path, required=True)
    publish_parser.add_argument("--telemetry", type=Path, required=True)
    publish_parser.add_argument("--converter", type=Path, default=REPO_ROOT / "experiments" / "rosbag_to_telemetry.py")
    publish_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    publish_parser.add_argument("--asset-dir", type=Path, default=REPO_ROOT / "evidence" / "item11" / "assets")
    publish_parser.add_argument("--name", required=True)
    publish_parser.add_argument("--source", choices=sorted(VALID_SOURCES), required=True)
    publish_parser.add_argument("--topic", action="append", required=True)
    publish_parser.add_argument("--git-tag", default="v11-ros-bag")
    publish_parser.add_argument("--upstream-revision", default="")
    publish_parser.add_argument("--record-command", required=True)
    publish_parser.add_argument("--converter-command", required=True)
    publish_parser.add_argument("--rtf-preflight", type=float, default=1.0)
    publish_parser.add_argument("--rtf-final", type=float, default=1.0)
    publish_parser.add_argument("--dry-run", action="store_true")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("name")
    verify_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    verify_parser.add_argument("--reconvert", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "lint":
        validate_manifest(args.manifest)
        print(f"Manifest valid: {args.manifest}")
    elif args.command == "publish":
        publish(args)
    else:
        verify(args)


if __name__ == "__main__":
    main()
