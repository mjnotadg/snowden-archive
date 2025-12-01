#!/usr/bin/env python3
"""
GitHub-ready Markdown inventory with clickable file links.
Groups files by top-level directory → year → table.
All FilePath entries become real clickable links on GitHub.
"""

import argparse
from pathlib import Path
from typing import Dict, List, Set
import re
import urllib.parse


def extract_year(part: str) -> int:
    m = re.search(r"\b(19\d{2}|20\d{2})\b", part)
    return int(m.group(0)) if m else 999999


def group_files(root_dir: Path, extensions: Set[str] | None = None):
    structure: Dict[str, Dict[int | None, List[Path]]] = {}

    for file_path in root_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if extensions and file_path.suffix.lower() not in extensions:
            continue

        rel = file_path.relative_to(root_dir)
        if not rel.parts:
            continue

        top_level = rel.parts[0]

        # Find the first year folder in the path
        year: int | None = None
        for part in rel.parts:
            y = extract_year(part)
            if y != 999999:
                year = y
                break

        structure.setdefault(top_level, {})
        structure[top_level].setdefault(year, []).append(file_path)

    return structure


def github_link(rel_path: Path) -> str:
    """[path/to/file](encoded-path) – works perfectly on GitHub"""
    path_str = rel_path.as_posix()
    encoded = urllib.parse.quote(path_str, safe="/")
    return f"[{path_str}]({encoded})"


def generate_markdown_inventory(
    root_dir: Path,
    extensions: Set[str] | None = None,
    output_file: Path | None = None,
) -> str:
    root_dir = root_dir.resolve()
    lines: List[str] = []

    lines.append("# Snowden Archive – File Inventory\n")
    lines.append("> Auto-generated • All paths are clickable on GitHub\n")
    lines.append("## Directories\n")

    structure = group_files(root_dir, extensions)
    total = 0

    for top_dir in sorted(structure.keys()):
        lines.append(f"### {top_dir}\n")

        year_groups = structure[top_dir]
        years = sorted(y for y in year_groups if y is not None)
        if None in year_groups:
            years.append(None)

        for year in years:
            files = sorted(year_groups[year], key=lambda p: p.relative_to(root_dir))
            total += len(files)
            if not files:
                continue

            header = "No Year Folder" if year is None else str(year)
            lines.append(f"#### {header}\n")

            lines.append("| Filename | FilePath |")
            lines.append("|----------|----------|")

            for fp in files:
                rel = fp.relative_to(root_dir)
                name = fp.name.replace("|", "\\|")
                link = github_link(rel)
                lines.append(f"| {name} | {link} |")

            lines.append("")  # blank line after table

        lines.append("---\n")

    content = "\n".join(lines).rstrip() + "\n"

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")
        print(f"Success: GitHub-ready inventory saved → {output_file}")

    print(f"Success: {total} files in {len(structure)} top-level directories")
    return content


def main():
    parser = argparse.ArgumentParser(
        description="Generate GitHub-ready Markdown inventory with clickable file links."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--ext",
        action="append",
        dest="extensions",          # ← this was missing before!
        help="Filter by extension, e.g. --ext .pdf --ext .md (repeatable)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("INVENTORY.md"),
        help="Output file (default: INVENTORY.md)",
    )
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: Directory not found: {root}")
        return

    extensions_set: Set[str] | None = None
    if args.extensions:
        extensions_set = {
            (ext if ext.lower().startswith(".") else f".{ext}").lower()
            for ext in args.extensions
        }

    print(f"Scanning: {root}")
    if extensions_set:
        print(f"Only including: {', '.join(sorted(extensions_set))}")

    generate_markdown_inventory(root, extensions_set, args.output)

    print(f"\nFinished! Commit '{args.output}' to your repository root.")
    print("Every FilePath will now be a working link on GitHub.")


if __name__ == "__main__":
    main()
