#!/usr/bin/env python3
"""Regenerate every generated part of the site from the slug dirs.

1. research/, learning/, worklog/ index.html listings.
2. Homepage (index.html):
   - "Latest" ticker between <!-- latest:start --> / <!-- latest:end -->
   - expandable section lists between <!-- sections:start --> / <!-- sections:end -->
3. Every entry page: a "Recently on <site>" block injected just before </body>,
   between <!-- notes:more:start --> / <!-- notes:more:end -->. It lists the
   newest entries across all sections, never the page it sits on.

Listing text comes from each entry page's <title>, with the trailing
"— <site>" suffix (site name from CNAME) stripped. Every section in KINDS
sorts by each entry's <meta name="date" content="YYYY-MM-DD"> (newest first).

The script is idempotent: running it twice leaves the tree unchanged.
"NEW" tags (entries <= FRESH_DAYS old) are decided in the visitor's browser by
a few lines of inline JS, so they don't go stale between pushes.

Usage: update-listings.py [repo-root]  (defaults to cwd)

Adding a new top-level section: add a key to KINDS and SECTION_LABELS (date-
sorted listings, homepage and article blocks follow automatically). Also add
<section>/index.html and extend .github/workflows/update-listings.yml
paths/guard/git add.
"""
import html
import re
import sys
from dataclasses import dataclass
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
# Homepage label per section: "/research/ — reports (N)".
SECTION_LABELS = {"research": "reports", "learning": "guides", "worklog": "log"}

TICKER_COUNT = 5   # homepage "Latest" ticker
MORE_COUNT = 4     # "Recently on" block at the end of each entry
FRESH_DAYS = 3     # entries this many days old or newer get a "New" tag

# Site name (from CNAME) is stripped off the end of entry titles for listings,
# e.g. "GoDaddy → Cloudflare — notes.rr2.dev" becomes "GoDaddy → Cloudflare".
_cname = ROOT / "CNAME"
SITE = _cname.read_text(encoding="utf-8").strip() if _cname.is_file() else ""
SUFFIX_RE = (
    re.compile(rf"\s*[—–\-|]\s*{re.escape(SITE)}\s*$", re.IGNORECASE) if SITE else None
)


def marker_re(name: str) -> re.Pattern:
    return re.compile(
        rf"<!-- {re.escape(name)}:start -->.*?<!-- {re.escape(name)}:end -->",
        re.DOTALL,
    )


LATEST_RE = marker_re("latest")
SECTIONS_RE = marker_re("sections")
# The block plus the blank line we put in front of it, so removal is clean.
MORE_RE = re.compile(
    r"\n*<!-- notes:more:start -->.*?<!-- notes:more:end -->\n*", re.DOTALL
)
BODY_END_RE = re.compile(r"\s*</body>", re.IGNORECASE)


# --------------------------------------------------------------------------- data


@dataclass
class Entry:
    section: str
    slug: str
    title: str
    iso: str  # 'YYYY-MM-DD' or ''

    @property
    def path(self) -> Path:
        return ROOT / self.section / self.slug / "index.html"

    @property
    def url(self) -> str:
        return f"/{self.section}/{self.slug}/"


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


def parse_iso(iso: str):
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def fmt_date(iso: str) -> str:
    """Format 'YYYY-MM-DD' like 'Aug 8, 2026', or '' if invalid/empty."""
    d = parse_iso(iso)
    return f"{d:%b} {d.day}, {d:%Y}" if d else ""


def fmt_dmy(iso: str) -> str:
    """'28 Sep 2026' (homepage section lists, article blocks)."""
    d = parse_iso(iso)
    return f"{d.day} {d:%b} {d:%Y}" if d else ""


def fmt_dm(iso: str) -> str:
    """'28 Sep' (ticker)."""
    d = parse_iso(iso)
    return f"{d.day} {d:%b}" if d else ""


def section_entries(name: str) -> list:
    base = ROOT / name
    entries = [
        Entry(name, s, title_of(base / s / "index.html", s), date_iso_of(base / s / "index.html"))
        for s in slug_dirs(base)
    ]
    # Newest first by date; undated entries fall to the end, slug order kept
    # among equal dates (slug_dirs is already sorted and the sort is stable).
    entries.sort(key=lambda e: e.iso, reverse=True)
    return entries


def all_entries() -> list:
    entries = [e for name in KINDS for e in section_entries(name)]
    # Newest first across sections; ties broken by section then slug so the
    # output is stable run to run.
    entries.sort(key=lambda e: (e.section, e.slug))
    entries.sort(key=lambda e: e.iso, reverse=True)
    return entries


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def write_if_changed(path: Path, new: str, old: str, what: str) -> bool:
    if new == old:
        print(f"unchanged {path.relative_to(ROOT)}")
        return False
    path.write_text(new, encoding="utf-8")
    print(f"updated   {path.relative_to(ROOT)} ({what})")
    return True


# Marks [data-fresh] elements whose date is within FRESH_DAYS of today, in the
# visitor's local calendar. Without JS nothing is marked — the lists still work.
FRESH_JS = (
    "<script>(function(){var d=new Date();d.setHours(0,0,0,0);"
    "var els=document.querySelectorAll('[data-fresh]');"
    "for(var i=0;i<els.length;i++){"
    "var t=new Date(els[i].getAttribute('data-fresh')+'T00:00:00');"
    "var a=Math.round((d-t)/864e5);"
    f"if(a>=0&&a<={FRESH_DAYS})els[i].classList.add('is-new');"
    "}})();</script>"
)


# ----------------------------------------------------------- 1. section listings


def line_for(e: Entry) -> str:
    li = f'<li><a href="{e.url}">{esc(e.title)}</a>'
    d = fmt_date(e.iso)
    if d:
        li += f" — {esc(d)}"
    return f"  {li}</li>"


def update_listing(name: str) -> bool:
    kind = KINDS[name]
    entries = section_entries(name)
    if entries:
        items = "\n".join(line_for(e) for e in entries)
    else:
        items = "  <li><em>Nothing here yet.</em></li>"
    block = (
        "<ul>\n"
        f'  <!-- one <li> per {kind}: '
        f'<li><a href="/{name}/slug/">Title</a> — Mmm D, YYYY</li> -->\n'
        f"{items}\n"
        "</ul>"
    )
    listing = ROOT / name / "index.html"
    text = listing.read_text(encoding="utf-8")
    new, n = UL_RE.subn(block, text, count=1)
    if n == 0:
        print(f"error: no <ul> block in {listing}", file=sys.stderr)
        sys.exit(1)
    return write_if_changed(listing, new, text, f"{len(entries)} entries")


# ------------------------------------------------------------------ 2. homepage


def ticker_items(entries: list, hidden: bool) -> str:
    extra = ' aria-hidden="true" tabindex="-1"' if hidden else ""
    out = []
    for e in entries:
        out.append(
            f'      <a href="{e.url}" data-fresh="{e.iso}"{extra}>'
            f'<span class="tk-new">New</span>'
            f'<span class="tk-date">{esc(fmt_dm(e.iso))}</span>'
            f'<span class="tk-title">{esc(e.title)}</span></a>'
            f'<span class="tk-sep" aria-hidden="true">/</span>'
        )
    return "\n".join(out)


def latest_block(entries: list) -> str:
    top = entries[:TICKER_COUNT]
    if not top:
        # No entries yet: keep a plain rule where the ticker would sit.
        return "<!-- latest:start -->\n<hr>\n<!-- latest:end -->"
    return (
        "<!-- latest:start -->\n"
        '<nav class="ticker" aria-label="Latest entries">\n'
        '  <span class="ticker-label">Latest</span>\n'
        '  <div class="ticker-window">\n'
        '    <div class="ticker-track">\n'
        f"{ticker_items(top, hidden=False)}\n"
        "      <!-- repeated for a seamless loop -->\n"
        f"{ticker_items(top, hidden=True)}\n"
        "    </div>\n"
        "  </div>\n"
        "</nav>\n"
        f"{FRESH_JS}\n"
        "<!-- latest:end -->"
    )


def sections_block() -> str:
    lines = ["<!-- sections:start -->", '<ul class="sections">']
    for name in KINDS:
        entries = section_entries(name)
        summary = (
            f'<a href="/{name}/">/{name}/</a> — {SECTION_LABELS[name]} '
            f'(<span data-count="{name}">{len(entries)}</span>)'
        )
        if not entries:
            lines.append(f'  <li><details class="empty"><summary>{summary}</summary></details></li>')
            continue
        lines.append(f"  <li><details>\n    <summary>{summary}</summary>\n    <ul>")
        for e in entries:
            d = fmt_dmy(e.iso)
            t = f'<time class="date" datetime="{e.iso}">{esc(d)}</time>' if d else '<span class="date"></span>'
            lines.append(f'      <li>{t}<a href="{e.url}">{esc(e.title)}</a></li>')
        lines.append("    </ul>\n  </details></li>")
    lines += ["</ul>", "<!-- sections:end -->"]
    return "\n".join(lines)


def update_home(entries: list) -> bool:
    home = ROOT / "index.html"
    text = home.read_text(encoding="utf-8")
    new = text
    for rx, block, label in (
        (LATEST_RE, latest_block(entries), "latest"),
        (SECTIONS_RE, sections_block(), "sections"),
    ):
        new, n = rx.subn(lambda _m, b=block: b, new, count=1)
        if n == 0:
            print(f"error: no <!-- {label}:start/end --> markers in {home}", file=sys.stderr)
            sys.exit(1)
    return write_if_changed(home, new, text, "ticker + sections")


# ------------------------------------------------ 3. "Recently on" in every entry

# Self-contained and scoped under .nr-more so page styles can't clash with it.
MORE_CSS = """<style>
  .nr-more { margin: 3.5rem 0 0; padding-top: 1rem; border-top: 1px solid #111;
             font: 1rem/1.6 Georgia, 'Times New Roman', serif; color: #111; }
  .nr-more, .nr-more * { box-sizing: border-box; }
  .nr-more .nr-head { display: flex; justify-content: space-between; align-items: baseline;
                      gap: 1rem; margin: 0 0 0.6rem; }
  .nr-more .nr-label, .nr-more .nr-all, .nr-more .nr-meta {
    font-family: ui-sans-serif, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
  .nr-more .nr-label { font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
                       letter-spacing: 0.14em; margin: 0; }
  .nr-more .nr-all { flex: none; font-size: 0.78rem; color: #7a6450; text-decoration: none; }
  .nr-more .nr-all:hover, .nr-more .nr-all:focus-visible { text-decoration: underline; }
  .nr-more ol { list-style: none; margin: 0; padding: 0; }
  .nr-more li { margin: 0; padding: 0; border-top: 1px solid #ddd6ca; }
  .nr-more li:first-child { border-top: 0; }
  .nr-more li a { display: block; padding: 0.6rem 0; color: #111; text-decoration: none; }
  .nr-more li a:hover .nr-t, .nr-more li a:focus-visible .nr-t { text-decoration: underline; }
  .nr-more .nr-meta { display: block; font-size: 0.72rem; letter-spacing: 0.02em; color: #7a6450;
                      font-variant-numeric: tabular-nums lining-nums; }
  .nr-more .nr-new { display: none; margin-right: 0.4rem; color: #b06a00; font-weight: 600;
                     font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.1em; }
  .nr-more .is-new .nr-new { display: inline; }
  .nr-more .nr-sec::before { content: "\\00B7"; margin: 0 0.4rem; }
  .nr-more .nr-t { font-size: 1.02rem; }
</style>"""


def more_block(current: Entry, entries: list) -> str:
    others = [e for e in entries if not (e.section == current.section and e.slug == current.slug)]
    picks = others[:MORE_COUNT]
    if not picks:
        return ""
    label = f"Recently on {SITE}" if SITE else "Recently added"
    rows = []
    for e in picks:
        d = fmt_dmy(e.iso)
        rows.append(
            f'    <li><a href="{e.url}" data-fresh="{e.iso}">'
            f'<span class="nr-meta"><span class="nr-new">New</span>{esc(d)}'
            f'<span class="nr-sec">{e.section}</span></span>'
            f'<span class="nr-t">{esc(e.title)}</span></a></li>'
        )
    return (
        "<!-- notes:more:start -->\n"
        "<!-- Generated by .github/scripts/update-listings.py; edits here are overwritten. -->\n"
        f"{MORE_CSS}\n"
        f'<aside class="nr-more" aria-label="{esc(label)}">\n'
        f'  <div class="nr-head"><p class="nr-label">{esc(label)}</p>'
        '<a class="nr-all" href="/">All notes →</a></div>\n'
        "  <ol>\n" + "\n".join(rows) + "\n  </ol>\n"
        "</aside>\n"
        f"{FRESH_JS}\n"
        "<!-- notes:more:end -->"
    )


def update_entry(current: Entry, entries: list) -> bool:
    page = current.path
    text = page.read_text(encoding="utf-8")
    stripped = MORE_RE.sub("\n", text)
    block = more_block(current, entries)
    m = None
    for m in BODY_END_RE.finditer(stripped):
        pass  # last </body>
    if m is None:
        print(f"warning: no </body> in {page.relative_to(ROOT)}; skipped", file=sys.stderr)
        return False
    head, tail = stripped[: m.start()], stripped[m.end():]
    new = head + ("\n\n" + block if block else "") + "\n\n</body>" + tail
    return write_if_changed(page, new, text, "recently block")


# --------------------------------------------------------------------------- main

if __name__ == "__main__":
    entries = all_entries()
    for section in KINDS:
        if (ROOT / section / "index.html").is_file():
            update_listing(section)
    if (ROOT / "index.html").is_file():
        update_home(entries)
    for e in entries:
        update_entry(e, entries)
    sys.exit(0)
