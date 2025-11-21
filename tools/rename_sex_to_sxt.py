#!/usr/bin/env python3
"""
Rename aspect files and IDs from *_SEX_* to *_SXT_* and update kb/index.json accordingly.

- Renames files in kb/aspects containing "_SEX_" to use "_SXT_" instead
- Updates the 'id' inside each JSON file accordingly
- Updates kb/index.json items: both 'id' and 'path' fields

Usage (from repo root):
  python tools/rename_sex_to_sxt.py

Optional args:
  --root <path>     # specify project root (defaults to script's two-level parent)
  --dry-run         # show changes without writing
  --verbose         # print each file processed
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Tuple

REPLACE_FROM = "_SEX_"
REPLACE_TO = "_SXT_"


def find_root(default_depth_up: int = 2) -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    root = here
    for _ in range(default_depth_up):
        root = os.path.dirname(root)
    return root


def rewrite_aspect_file(old_path: str, new_path: str, dry_run: bool, verbose: bool) -> Tuple[bool, str]:
    """Return (changed, message). Updates id inside JSON and writes to new_path."""
    try:
        with open(old_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        changed = False
        if isinstance(data, dict) and isinstance(data.get("id"), str) and REPLACE_FROM in data["id"]:
            data["id"] = data["id"].replace(REPLACE_FROM, REPLACE_TO)
            changed = True
        if dry_run:
            return True, f"[dry-run] would write JSON -> {new_path} (id updated: {changed})"
        # ensure parent
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f"Wrote {new_path}")
        return True, "ok"
    except Exception as e:
        # Fallback: rename only, do not modify content
        if dry_run:
            return True, f"[dry-run] would rename only (failed JSON parse: {e}) -> {new_path}"
        # rename by copy
        with open(old_path, "r", encoding="utf-8") as f:
            txt = f.read()
        # DO NOT do global replacement to avoid changing 'Sextile' text
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(txt)
        if verbose:
            print(f"Wrote (raw) {new_path}")
        return True, f"raw copy (json error: {e})"


def update_index_json(index_path: str, dry_run: bool, verbose: bool) -> int:
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            idx = json.load(f)
    except Exception as e:
        print(f"[warn] Could not parse index.json: {e}")
        return 0

    changed = 0
    items = idx.get("items", []) if isinstance(idx, dict) else []
    for it in items:
        if not isinstance(it, dict):
            continue
        if isinstance(it.get("id"), str) and REPLACE_FROM in it["id"]:
            it["id"] = it["id"].replace(REPLACE_FROM, REPLACE_TO)
            changed += 1
        if isinstance(it.get("path"), str) and REPLACE_FROM in it["path"]:
            it["path"] = it["path"].replace(REPLACE_FROM, REPLACE_TO)
            changed += 1
    if changed and not dry_run:
        # backup
        bak = index_path + ".bak"
        try:
            if os.path.exists(bak):
                os.remove(bak)
            os.replace(index_path, bak)
            if verbose:
                print(f"Backed up index.json -> {bak}")
        except Exception:
            # best effort
            pass
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f"Updated {index_path}")
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=find_root(), help="Project root (contains kb/)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    aspects_dir = os.path.join(root, "kb", "aspects")
    index_path = os.path.join(root, "kb", "index.json")

    if not os.path.isdir(aspects_dir):
        print(f"[error] aspects dir not found: {aspects_dir}")
        sys.exit(1)

    # Pass 1: rename files and update their internal id
    renamed = 0
    for name in os.listdir(aspects_dir):
        if name.endswith(".json") and REPLACE_FROM in name:
            old_path = os.path.join(aspects_dir, name)
            new_name = name.replace(REPLACE_FROM, REPLACE_TO)
            new_path = os.path.join(aspects_dir, new_name)

            if args.dry_run:
                print(f"[dry-run] would rename {name} -> {new_name}")
                # simulate writing JSON
                _ = rewrite_aspect_file(old_path, new_path, dry_run=True, verbose=args.verbose)
            else:
                ok, msg = rewrite_aspect_file(old_path, new_path, dry_run=False, verbose=args.verbose)
                if ok:
                    # remove old after writing new
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"[warn] Could not remove old file {old_path}: {e}")
                    renamed += 1
                else:
                    print(f"[warn] Failed to process {old_path}: {msg}")

    # Pass 2: update index.json
    idx_changes = 0
    if os.path.isfile(index_path):
        idx_changes = update_index_json(index_path, dry_run=args.dry_run, verbose=args.verbose)
    else:
        print(f"[warn] index.json not found at {index_path}")

    print("Summary:")
    print(f"  Files renamed: {renamed}")
    print(f"  index.json entries changed: {idx_changes}")
    if args.dry_run:
        print("(dry-run, nothing written)")


if __name__ == "__main__":
    main()
