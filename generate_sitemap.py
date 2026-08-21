#!/usr/bin/env python3
"""Generate sitemap.xml from the canonical tags of the site's index.html pages.

Run from the repo root after adding or regenerating pages:

    python3 generate_sitemap.py

A page is included when its <link rel="canonical"> points at the page's own
URL (self-canonical). Redirect stubs, templates, and legacy pages without a
canonical are skipped automatically.
"""

import re
import sys
from pathlib import Path

SITE = "https://decodepolitics.org"

SKIP_DIRS = {".git", "node_modules", "_deprecated", "__pycache__",
             "archive", "docs", "_scratch", "Monica Design Templates"}

# Self-canonical pages deliberately kept out of the sitemap.
EXCLUDE = {
    "/coming-soon/",  # pre-launch teaser, duplicates the homepage
}

CANONICAL_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"')
REDIRECT_RE = re.compile(r'http-equiv="refresh"', re.IGNORECASE)


def index_files(root: Path) -> list[Path]:
    found = []
    for path in root.rglob("index.html"):
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        found.append(path)
    return sorted(found)


def page_url(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    if rel == "index.html":
        return SITE + "/"
    return SITE + "/" + rel[: -len("index.html")]


def main() -> int:
    root = Path(__file__).resolve().parent
    entries = []
    skipped = []

    for path in index_files(root):
        html = path.read_text(encoding="utf-8", errors="replace")
        m = CANONICAL_RE.search(html)
        url = page_url(root, path)
        if not m or m.group(1) != url or REDIRECT_RE.search(html):
            skipped.append(url)
            continue
        if url[len(SITE):] in EXCLUDE:
            skipped.append(url)
            continue
        entries.append(url)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in entries:
        lines.append(f"  <url><loc>{url}</loc></url>")
    lines.append("</urlset>")

    (root / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml written: {len(entries)} URLs ({len(skipped)} pages skipped)")
    for url in skipped:
        print(f"  skipped: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
