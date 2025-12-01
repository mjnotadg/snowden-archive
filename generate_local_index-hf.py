#!/usr/bin/env python3
"""
generate_index.py – Local + Hugging Face Dataset support
Usage:
    python generate_index.py          # Scan local folder (original behavior)
    python generate_index.py --hf     # Use remote HF dataset (no local files needed)
    python generate_index.py --hf --fallback-local  # Prefer HF, fallback to local
"""

from pathlib import Path
import urllib.parse
import re
import argparse
import sys

try:
    from huggingface_hub import HfApi, list_repo_files
except ImportError:
    print("Error: huggingface_hub not installed.")
    print("Run: pip install huggingface_hub")
    sys.exit(1)


HF_REPO_ID = "yukioitsuki/snowden_archived"
api = HfApi()


def extract_year_from_path(path_parts):
    """Find the first 19xx or 20xx year in any part of the path"""
    for part in path_parts:
        match = re.search(r"\b(19\d{2}|20\d{2})\b", part)
        if match:
            return int(match.group(0))
    return None


def get_pdf_files_from_hf():
    """Fetch list of all PDF files from the Hugging Face dataset"""
    print(f"Fetching file list from Hugging Face dataset: {HF_REPO_ID}")
    try:
        files = list_repo_files(repo_id=HF_REPO_ID, repo_type="dataset")
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        print(f"Found {len(pdf_files)} PDF files on Hugging Face")
        return pdf_files
    except Exception as e:
        print(f"Failed to fetch from HF: {e}")
        return []


def scan_local_pdfs(root="."):
    """Original local scanning logic"""
    print("Scanning local directory for PDF files (excluding .files folders)...")
    root_path = Path(root)
    pdf_files = []
    excluded = 0

    for p in root_path.rglob("*.pdf"):
        if ".files" in p.parts:
            excluded += 1
            continue
        if not p.is_file():
            continue

        rel = p.relative_to(root_path)
        year = extract_year_from_path(rel.parts)

        pdf_files.append({
            "path": str(rel.as_posix()),
            "name": p.name,
            "year": year
        })

    print(f"Found {len(pdf_files)} local PDF files ({excluded} excluded)")
    return pdf_files


def generate_html(pdf_entries, total_files):
    """Generate HTML content from list of entries"""
    # Group: top-level directory → year (or None) → files
    grouped = {}
    for f in pdf_entries:
        path = f["path"]
        top_dir = path.split("/", 1)[0] if "/" in path else path.split("/", 1)[0]
        year_key = f["year"] if f["year"] else "no-year"
        grouped.setdefault(top_dir, {}).setdefault(year_key, []).append(f)

    content = ""
    for top_dir in sorted(grouped.keys()):
        content += f'<div class="directory collapsed">\n'
        content += f'  <div class="dir-header">{top_dir}<span class="arrow"></span></div>\n'
        content += f'  <div class="content">\n'

        year_map = {}
        for y_key, flist in grouped[top_dir].items():
            display = "No Year Folder" if y_key == "no-year" else str(y_key)
            year_map[display] = sorted(flist, key=lambda x: x["path"].lower())

        sorted_years = sorted(
            (y for y in year_map.keys() if y != "No Year Folder"),
            key=int
        )
        if "No Year Folder" in year_map:
            sorted_years.append("No Year Folder")

        for year_name in sorted_years:
            files = year_map[year_name]
            content += f'    <div class="year collapsed">\n'
            content += f'      <div class="year-header">{year_name} <span class="count">({len(files)} PDFs)</span><span class="arrow"></span></div>\n'
            content += f'      <div class="content">\n'
            content += '        <div class="table-wrapper"><table><thead><tr><th>Document</th><th>Path</th></tr></thead><tbody>\n'
            for f in files:
                safe_name = f["name"].replace("|", "Vertical Bar")
                # Use direct HF URL for download
                hf_url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{f['path']}"
                link = urllib.parse.quote(hf_url, safe=":/")
                content += f'          <tr><td><a href="{link}" target="_blank">{safe_name}</a></td><td><code>{f["path"]}</code></td></tr>\n'
            content += '        </tbody></table></div>\n'
            content += '      </div></div>\n'

        content += '  </div></div>\n'

    # Load template
    template_path = Path("templates.html")
    if not template_path.exists():
        print("Error: templates.html not found!")
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")
    final_html = template.replace("{TOTAL_FILES}", str(total_files)) \
                         .replace("<!-- INJECTED_CONTENT -->", content)

    Path("index_local.html").write_text(final_html, encoding="utf-8")
    print(f"\nSuccess: index_local.html generated with {total_files} PDFs")
    print("   → Links point directly to Hugging Face (no local files needed)")
    print("   → Double-click index_local.html → full offline-capable index!")


def main():
    parser = argparse.ArgumentParser(description="Generate Snowden Archive index")
    parser.add_argument("--hf", action="store_true", help="Use Hugging Face dataset instead of local files")
    parser.add_argument("--fallback-local", action="store_true", help="If HF fails, fall back to local scan")
    args = parser.parse_args()

    pdf_entries = []

    if args.hf:
        hf_files = get_pdf_files_from_hf()
        if hf_files:
            pdf_entries = []
            for path in hf_files:
                name = Path(path).name
                parts = Path(path).parts
                year = extract_year_from_path(parts)
                pdf_entries.append({
                    "path": path,
                    "name": name,
                    "year": year
                })
        else:
            if args.fallback_local:
                print("Falling back to local files...")
                pdf_entries = scan_local_pdfs()
            else:
                print("No files found and no fallback enabled.")
                sys.exit(1)
    else:
        pdf_entries = scan_local_pdfs()

    if not pdf_entries:
        print("No PDF files found.")
        sys.exit(1)

    generate_html(pdf_entries, len(pdf_entries))


if __name__ == "__main__":
    main()
