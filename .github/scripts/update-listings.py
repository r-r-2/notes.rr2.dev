#!/usr/bin/env python3
"""Regenerate research/, learning/, and worklog/ index.html listings from slug dirs,
and refresh the per-section item counts on the homepage.

Listing text comes from each entry page's <title>, with the trailing
"— <site>" suffix (site name from CNAME) stripped. Sections in DATED also
show each entry's <meta name="date" content="YYYY-MM-DD">, appended after
the link.

Usage: update-listings.py [repo-root]  (defaults to cwd)
"""
import html
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
UL_RE = re.compile(r"<ul>.*?</ul>", re.DOTALL)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
DATE_RE = re.compile(
    r'<meta\s+name=["\']date["\']\s+content=["\'](\d{4}-\d{2}-\d{2})["\']',
    re.IGNORECASE,
)
KINDS = {"research": "report", "learning": "guide", "worklog": "entry"}
DATED = {"worklog"}  # sections whose listings show each entry's date

# Site name (from CNAME) is stripped off the end of entry titles for listings,
# e.g. "GoDaddy → Cloudflare — notes.rr2.dev" becomes "GoDaddy → Cloudflare".
_cname = ROOT / "CNAME"
SITE = _cname.read_text(encoding="utf-8").strip() if _cname.is_file() else ""
SUFFIX_RE = (
    re.compile(rf"\s*[—–\-|]\s*{re.escape(SITE)}\s*$", re.IGNORECASE) if SITE else None
)


def slug_dirs(base: Path) -> list:
    if not base.is_dir():
        return []
    return sorted(
        p.name for p in base.iterdir() if p.is_dir() and (p / "index.html").is_file()
    )


def title_of(page: Path, slug: str) -> str:
    m = TITLE_RE.search(page.read_text(encoding="utf-8"))
    if not m:
        return slug
    title = " ".join(html.unescape(m.group(1)).split())
    if SUFFIX_RE:
        title = SUFFIX_RE.sub("", title)
    return title or slug


def date_iso_of(page: Path) -> str:
    """Raw 'YYYY-MM-DD' date from the entry's <meta name="date">, or '' if absent."""
    m = DATE_RE.search(page.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def fmt_date(iso: str) -> str:
    """Format 'YYYY-MM-DD' like 'Aug 8, 2026', or '' if invalid/empty."""
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return ""
    return f"{d:%b} {d.day}, {d:%Y}"


def line_for(name: str, slug: str, dated: bool) -> str:
    page = ROOT / name / slug / "index.html"
    li = f'<li><a href="/{name}/{slug}/">{html.escape(title_of(page, slug))}</a>'
    if dated:
        d = fmt_date(date_iso_of(page))
        if d:
            li += f" — {html.escape(d)}"
    return f"  {li}</li>"


def update(name: str) -> bool:
    base = ROOT / name
    kind = KINDS[name]
    dated = name in DATED
    slugs = slug_dirs(base)
    if dated:
        # Newest first by date; undated entries fall to the end, slug order kept
        # among equal dates (slug_dirs is already sorted and the sort is stable).
        slugs.sort(key=lambda s: date_iso_of(base / s / "index.html"), reverse=True)
    if slugs:
        items = "\n".join(line_for(name, s, dated) for s in slugs)
    else:
        items = "  <li><em>Nothing here yet.</em></li>"
    block = (
        "<ul>\n"
        f'  <!-- one <li> per {kind}: <li><a href="/{name}/slug/">Title</a></li> -->\n'
        f"{items}\n"
        "</ul>"
    )
    listing = base / "index.html"
    text = listing.read_text(encoding="utf-8")
    new, n = UL_RE.subn(block, text, count=1)
    if n == 0:
        print(f"error: no <ul> block in {listing}", file=sys.stderr)
        sys.exit(1)
    if new == text:
        print(f"unchanged {listing.relative_to(ROOT)}")
        return False
    listing.write_text(new, encoding="utf-8")
    print(f"updated   {listing.relative_to(ROOT)} ({len(slugs)} entries)")
    return True


def update_home(home: Path) -> bool:
    text = home.read_text(encoding="utf-8")
    new = text
    for name in KINDS:
        n = len(slug_dirs(ROOT / name))
        new = re.sub(
            rf'(<span data-count="{name}">)\d+(</span>)',
            rf"\g<1>{n}\g<2>",
            new,
        )
    if new == text:
        print(f"unchanged {home.relative_to(ROOT)}")
        return False
    home.write_text(new, encoding="utf-8")
    print(f"updated   {home.relative_to(ROOT)} (counts)")
    return True


if __name__ == "__main__":
    for section in KINDS:
        if (ROOT / section / "index.html").is_file():
            update(section)
    home = ROOT / "index.html"
    if home.is_file():
        update_home(home)
    sys.exit(0)
