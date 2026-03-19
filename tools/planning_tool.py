#!/usr/bin/env python3
"""
Small CLI for interacting with `planning.json`.

Supports:
- add: append a new `features[]` entry
- set-status: update only the `status` field for an existing entry

It intentionally does NOT support arbitrary editing or deletion.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PLANNING_PATH = Path(__file__).resolve().parent.parent / "planning.json"


@dataclass(frozen=True)
class Feature:
    id: str


def _load_planning(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"planning file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or "features" not in data:
        raise ValueError("planning.json must be a JSON object with a top-level `features` key")

    if not isinstance(data["features"], list):
        raise ValueError("planning.json `features` must be an array")

    return data


def _find_feature_index(features: list[dict[str, Any]], feature_id: str) -> int:
    for i, feat in enumerate(features):
        if isinstance(feat, dict) and feat.get("id") == feature_id:
            return i
    return -1


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    tmp_dir = path.parent
    fd, tmp_path_str = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(tmp_dir))
    tmp_path = Path(tmp_path_str)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        tmp_path.replace(path)
    finally:
        # If something failed before replace().
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _backup_file(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + ".bak")
    # Keep it simple: overwrite previous backup.
    shutil.copy2(path, backup_path)
    return backup_path


def _parse_components(items: list[str]) -> list[str]:
    # Allow comma-separated values inside each flag.
    out: list[str] = []
    for item in items:
        parts = [p.strip() for p in item.split(",") if p.strip()]
        out.extend(parts)
    return out


def cmd_list(args: argparse.Namespace) -> int:
    path: Path = args.file
    data = _load_planning(path)
    features: list[dict[str, Any]] = data["features"]

    # Minimal readable output.
    for feat in features:
        if not isinstance(feat, dict):
            continue
        fid = feat.get("id", "")
        title = feat.get("title", "")
        status = feat.get("status", "")
        print(f"{fid}\t{status}\t{title}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    path: Path = args.file
    data = _load_planning(path)
    features: list[dict[str, Any]] = data["features"]

    feature_id: str = args.id.strip()
    if not feature_id:
        raise ValueError("`--id` must be non-empty")

    existing_idx = _find_feature_index(features, feature_id)
    if existing_idx != -1:
        raise ValueError(f"feature id already exists: {feature_id}")

    components = _parse_components(args.component or [])

    # Construct the record; do NOT attempt to edit existing records.
    new_feat: dict[str, Any] = {
        "id": feature_id,
        "title": args.title,
        "status": args.status,
        "description": args.description,
        "components": components,
        "added": args.added or date.today().isoformat(),
    }

    features.append(new_feat)

    if args.dry_run:
        print(f"[dry-run] would append feature: {feature_id}")
        return 0

    if not args.no_backup:
        backup_path = _backup_file(path)
        print(f"backup: {backup_path}")

    _atomic_write_json(path, data)
    print(f"added: {feature_id}")
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    path: Path = args.file
    data = _load_planning(path)
    features: list[dict[str, Any]] = data["features"]

    feature_id: str = args.id.strip()
    if not feature_id:
        raise ValueError("`--id` must be non-empty")

    new_status: str = args.status
    if not new_status:
        raise ValueError("`--status` must be non-empty")

    idx = _find_feature_index(features, feature_id)
    if idx == -1:
        raise ValueError(f"feature id not found: {feature_id}")

    feat = features[idx]
    if not isinstance(feat, dict):
        raise ValueError(f"malformed feature entry at index {idx}")

    # Only mutate the `status` field.
    feat["status"] = new_status

    if args.dry_run:
        print(f"[dry-run] would set status for {feature_id} -> {new_status}")
        return 0

    if not args.no_backup:
        backup_path = _backup_file(path)
        print(f"backup: {backup_path}")

    _atomic_write_json(path, data)
    print(f"status updated: {feature_id} -> {new_status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="planning_tool.py",
        description="Interact with planning.json (add features, update status).",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_PLANNING_PATH,
        help=f"path to planning.json (default: {DEFAULT_PLANNING_PATH})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen; do not write.")
    parser.add_argument("--no-backup", action="store_true", help="Do not write a .bak backup before changes.")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List features (id, status, title).")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="Append a new feature entry.")
    p_add.add_argument("--id", required=True, help="Unique feature id (e.g. dns-nexus-subdomains).")
    p_add.add_argument("--title", required=True, help="Human-friendly title.")
    p_add.add_argument("--status", required=True, help="Status string (e.g. concept).")
    p_add.add_argument("--description", required=True, help="Description text.")
    p_add.add_argument(
        "--component",
        action="append",
        default=[],
        help="Component string. Can be provided multiple times; each value may contain commas.",
    )
    p_add.add_argument("--added", default=None, help="YYYY-MM-DD (default: today).")
    p_add.set_defaults(func=cmd_add)

    p_status = sub.add_parser("set-status", help="Update only the `status` field for a feature.")
    p_status.add_argument("--id", required=True, help="Feature id to update.")
    p_status.add_argument("--status", required=True, help="New status string.")
    p_status.set_defaults(func=cmd_set_status)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

