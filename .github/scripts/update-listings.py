#!/usr/bin/env python3
"""Regenerate everything generated on notes.rr2.dev from the entry pages.

Entries live in research/<slug>/, learning/<slug>/ and worklog/<slug>/. Each is
a self-contained index.html with a <title>, <meta name="date"> and
<meta name="description">. This script:

1. Wraps every entry in the shared design, between markers it owns:
     <!-- nr:head:start/end -->    theme CSS, favicon, font preload (before </head>)
     <!-- nr:top:start/end -->     site header + the note's title block (after <body>)
     <!-- nr:bottom:start/end -->  "Recently on notes", the guide, footer, scripts (before </body>)
   The note's own content sits between top and bottom, untouched.
2. Writes the section pages (research/, learning/, worklog/ index.html) whole.
3. Refreshes the homepage (index.html) between its markers: nr:head, nr:top,
   nr:home (Recent posts carousel + month-by-month archive), nr:bottom.
   The intro paragraph between nr:top and nr:home is hand-written; it is kept.
4. Refreshes 404.html between nr:head / nr:top / nr:bottom.

The design lives in .github/scripts/theme/ (theme.css, core.js, home.js,
guide.js, avatar.webp). It is minified and inlined into every page, so each page
is still one file that opens on its own. Fonts are shared files in assets/fonts/.

Migration: a page that has no nr markers yet is taken to be in the old style.
Its leading <h1> (if it matches the title), the date line under it and the <hr>
after that are removed, because the generated title block replaces them.

The script is idempotent: running it twice leaves the tree unchanged.
unlisted/<slug>/ is deliberately not in KINDS: nothing here reads or rewrites it.

Usage: update-listings.py [repo-root]  (defaults to cwd)
"""
import base64
import html
import math
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
THEME = ROOT / ".github" / "scripts" / "theme"

# Section folder -> (menu name, page heading, page description, word for one entry)
KINDS = {
    "worklog": ("Worklog", "Worklog", "Dated notes on what Rahul built and changed, as it happened.", "entry"),
    "learning": ("Learning", "Learning", "Guides written while learning something new.", "guide"),
    "research": ("Research", "Research", "Longer research reports.", "report"),
}
RECENT_COUNT = 5   # homepage carousel
MORE_COUNT = 4     # "Recently on notes" at the end of each entry
WORDS_PER_MIN = 220

_cname = ROOT / "CNAME"
SITE = _cname.read_text(encoding="utf-8").strip() if _cname.is_file() else "notes.rr2.dev"
SUFFIX_RE = re.compile(rf"\s*[—–\-|]\s*{re.escape(SITE)}\s*$", re.IGNORECASE)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
META_RE = lambda name: re.compile(  # noqa: E731
    rf'<meta\s+name=["\']{name}["\']\s+content=(?:"([^"]*)"|\'([^\']*)\')', re.IGNORECASE)
DATE_RE, DESC_RE = META_RE("date"), META_RE("description")

GA = """<script async src="https://www.googletagmanager.com/gtag/js?id=G-2QQWNZ1TJ4"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-2QQWNZ1TJ4');
</script>"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def block_re(name: str) -> re.Pattern:
    return re.compile(rf"<!-- nr:{name}:start -->.*?<!-- nr:{name}:end -->", re.DOTALL)


def wrap(name: str, inner: str) -> str:
    return f"<!-- nr:{name}:start -->\n{inner}\n<!-- nr:{name}:end -->"


# ------------------------------------------------------------------ the entries


@dataclass
class Entry:
    section: str
    slug: str
    title: str
    iso: str
    desc: str
    minutes: int

    @property
    def path(self) -> Path:
        return ROOT / self.section / self.slug / "index.html"

    @property
    def url(self) -> str:
        return f"/{self.section}/{self.slug}/"

    @property
    def day(self):
        try:
            return date.fromisoformat(self.iso)
        except ValueError:
            return None


def strip_generated(text: str) -> str:
    for name in ("head", "top", "bottom"):
        text = block_re(name).sub("", text)
    # the old generator's block, from before this design
    return re.sub(r"\n*<!-- notes:more:start -->.*?<!-- notes:more:end -->\n*", "\n", text, flags=re.DOTALL)


def reading_minutes(page_html: str) -> int:
    body = strip_generated(page_html)
    body = body[body.lower().find("<body"):] if "<body" in body.lower() else body
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.DOTALL | re.IGNORECASE)
    words = len(re.sub(r"<[^>]+>", " ", html.unescape(body)).split())
    return max(1, math.ceil(words / WORDS_PER_MIN))


def read_entry(section: str, slug: str) -> Entry:
    text = (ROOT / section / slug / "index.html").read_text(encoding="utf-8")
    m = TITLE_RE.search(text)
    title = SUFFIX_RE.sub("", " ".join(html.unescape(m.group(1)).split())) if m else slug
    d, ds = DATE_RE.search(text), DESC_RE.search(text)
    if "<!-- nr:top:start -->" not in text:  # count words as they will be after migration
        text = migrate_old_header(strip_generated(text), title)
    pick = lambda m: (m.group(1) if m.group(1) is not None else m.group(2)) if m else ""  # noqa: E731
    return Entry(section, slug, title or slug, pick(d), html.unescape(pick(ds)), reading_minutes(text))


def all_entries() -> list:
    out = []
    for section in KINDS:
        base = ROOT / section
        if base.is_dir():
            out += [read_entry(section, p.name) for p in sorted(base.iterdir())
                    if p.is_dir() and (p / "index.html").is_file()]
    # newest first; ties by section then slug so output is stable run to run
    out.sort(key=lambda e: (e.section, e.slug))
    out.sort(key=lambda e: e.iso, reverse=True)
    return out


def fmt_long(e):  # September 12, 2026
    return f"{e.day:%B} {e.day.day}, {e.day:%Y}" if e.day else ""


def fmt_short(e):  # Sep 12, 2026
    return f"{e.day:%b} {e.day.day}, {e.day:%Y}" if e.day else ""


# ------------------------------------------------------------------ theme assets


def minify_css(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


def minify_js(js: str) -> str:
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    lines = []
    for line in js.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        cut = line.find("  //")  # trailing comments are always set off by two spaces
        lines.append(line[:cut].rstrip() if cut != -1 else line)
    return "\n".join(lines)


def asset(name: str) -> str:
    return (THEME / name).read_text(encoding="utf-8")


CSS = minify_css(asset("theme.css"))
JS = {k: minify_js(asset(f"{k}.js")) for k in ("core", "home", "guide")}
AVATAR = "data:image/webp;base64," + base64.b64encode((THEME / "avatar.webp").read_bytes()).decode()

# Set the saved theme before first paint, so dark mode never flashes white.
INIT_JS = ("(function(){var r=document.documentElement;r.classList.add('js');"
           "try{var t=localStorage.getItem('nr-theme');if(t)r.dataset.theme=t}catch(e){}})();")

MOON = ('<svg class="nr-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>')
SUN = ('<svg class="nr-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
       'aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42'
       'M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>')
CHEVRON_L = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
             'stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>')
CHEVRON_R = CHEVRON_L.replace("M15 18l-6-6 6-6", "M9 18l6-6-6-6")

# The guide. Three poses share one SVG; CSS shows the one in use.
FACE = ('<circle class="hd" cx="{x}" cy="{y}" r="13"/><circle class="eye" cx="{ex1}" cy="{ey}" r="1.6"/>'
        '<circle class="eye" cx="{ex2}" cy="{ey}" r="1.6"/><path class="mouth" d="{mouth}"/>')
GUIDE_SVG = (
    '<svg viewBox="0 0 60 88" aria-hidden="true">'
    '<g class="p-sit"><g class="who">'
    '<path class="ln far" d="M34 59 L25 58"/><path class="ln far shin-f" d="M25 58 L27 83 L23 84"/>'
    '<g class="torso"><path class="ln" d="M35 31 L34 59"/><path class="ln far" d="M35 38 L31 49 L28 58"/>'
    '<path class="ln arm" d="M35 38 L30 49 L26 58"/>'
    + FACE.format(x=35, y=18, ex1=28.5, ex2=35, ey=16.5, mouth="M27.5 22.5 Q31 25.5 34.5 22.5") +
    '</g><path class="ln" d="M34 60 L22 60"/><path class="ln shin-n" d="M22 60 L21 85 L16.5 85.5"/></g></g>'
    '<g class="p-stand"><path class="ln wave-arm" d="M30 41 L22 52 L20 61"/><path class="ln" d="M30 41 L38 52 L40 61"/>'
    '<path class="ln" d="M30 36 L30 63 M30 63 L26 75 L24 86 M30 63 L34 75 L36 86"/>'
    + FACE.format(x=30, y=23, ex1=25.5, ex2=34.5, ey=22, mouth="M25.5 27 Q30 30.5 34.5 27") +
    '</g><g class="p-hang"><path class="ln" d="M30 42 L22 29 L28 3 M30 42 L38 29 L32 3 M30 37 L30 64"/>'
    '<path class="ln hleg-l" d="M30 64 L26 75 L25 86"/><path class="ln hleg-r" d="M30 64 L34 75 L35 86"/>'
    + FACE.format(x=30, y=24, ex1=25.5, ex2=34.5, ey=23, mouth="M25.5 28 Q30 31.5 34.5 28") +
    '</g></svg>')
GUIDE = ('<div class="nr-layer" id="nr-layer"><div class="nr-rope" id="nr-rope"></div><div class="nr-zip" id="nr-zip"></div>'
         '<div class="nr-gw" id="nr-gw"><div class="nr-bubble" id="nr-bubble" role="status" aria-live="polite"><p></p>'
         '<div class="nr-acts"></div></div><button class="nr-buddy" id="nr-buddy" type="button" '
         f'aria-label="Ask the guide for help">{GUIDE_SVG}</button></div></div>')


def head_block() -> str:
    return wrap("head",
                '<link rel="icon" href="/favicon.ico" sizes="any">\n'
                '<link rel="preload" href="/assets/fonts/fraunces.woff2" as="font" type="font/woff2" crossorigin>\n'
                f"<style>{CSS}</style>\n<script>{INIT_JS}</script>")


def top_block(sections: list, current: str = "", extra: str = "") -> str:
    menu = "".join(
        f'<li><a href="/{s}/"{" aria-current=page" if s == current else ""}><span>{KINDS[s][0]}</span></a></li>'
        for s in sections)
    header = (
        '<div class="nr-top"><header class="nr-nav"><div class="nr-logo">'
        f'<a href="https://rr2.dev"><img class="nr-ico" src="{AVATAR}" width="24" height="24" alt="">'
        '<span class="nr-root">rr2.dev</span></a><span class="nr-slash">/</span><a href="/">notes</a></div>'
        f'<ul class="nr-menu">{menu}<li><button class="nr-toggle" id="nr-toggle" type="button" '
        f'aria-label="Switch between light and dark">{MOON}{SUN}</button></li></ul></header></div>\n'
        '<main class="nr-wrap" id="top">')
    return wrap("top", header + ("\n" + extra if extra else ""))


FOOTER = ('<footer class="nr-footer"><p>Part of <a href="https://rr2.dev">rr2.dev</a> · '
          '<a href="/worklog/setting-up-notes-rr2-dev/">Purpose behind this site →</a>'
          '<span hidden> · <button type="button" id="nr-guide-on">Show guide</button></span></p>'
          '<p>Credits to <a href="https://arnav.tech">Arnav Gupta</a> for the original '
          '<a href="https://github.com/championswimmer/sites.arnavg.in">sites.arnavg.in</a> project.</p></footer>')
TOPLINK = ('<a class="nr-toplink" id="nr-toplink" href="#top" aria-label="Back to top">'
           '<svg viewBox="0 0 12 6" fill="currentColor" aria-hidden="true"><path d="M12 6H0l6-6z"/></svg></a>')


def bottom_block(before_main_close: str, scripts: tuple, toplink: bool = True) -> str:
    js = "".join(f"<script>{JS[k]}</script>" for k in scripts)
    return wrap("bottom", f"{before_main_close}\n{GUIDE}\n</main>\n{FOOTER}\n{TOPLINK if toplink else ''}{js}")


# ------------------------------------------------------------------ shared markup


def meta_line(e: Entry, short: bool = True, new: bool = True) -> str:
    d = fmt_short(e) if short else fmt_long(e)
    parts = ['<span class="nr-new">New</span>'] if new else []
    if d:
        parts.append(f'<time datetime="{e.iso}">{esc(d)}</time>')
    parts.append(f"<span>{e.minutes} min read</span>")
    parts.append(f'<span class="nr-tag">{e.section}</span>')
    return "".join(parts)


def card(e: Entry) -> str:
    desc = f"<p>{esc(e.desc)}</p>" if e.desc else ""
    return (f'<article class="nr-card" data-sec="{e.section}" data-fresh="{e.iso}"><h2>{esc(e.title)}</h2>{desc}'
            f'<div class="nr-meta">{meta_line(e)}</div><a class="nr-cover" href="{e.url}" aria-label="{esc(e.title)}"></a></article>')


def months(entries: list) -> str:
    groups = {}
    for e in entries:
        groups.setdefault(f"{e.day:%B %Y}" if e.day else "Undated", []).append(e)
    out = []
    for label, es in groups.items():
        rows = "".join(
            f'<li data-sec="{e.section}"><a href="{e.url}">'
            + (f'<time class="nr-cal" datetime="{e.iso}" aria-label="{esc(fmt_long(e))}"><b>{e.day:%b}</b><span>{e.day.day}</span></time>'
               if e.day else "")
            + f'<span class="nr-body"><span class="nr-t">{esc(e.title)}</span>'
              f'<span class="nr-sub"><span class="nr-tag">{e.section}</span> {e.minutes} min read</span></span></a></li>'
            for e in es)
        n = len(es)
        out.append(f'<section class="nr-month"><h3>{label}<span>{n} note{"s" if n != 1 else ""}</span></h3><ol>{rows}</ol></section>')
    return "".join(out)


def more_cards(picks: list, label: str) -> str:
    """The small post cards that end every entry (and fill the 404 page)."""
    if not picks:
        return ""
    rows = "".join(f'<li data-sec="{o.section}"><a href="{o.url}" data-fresh="{o.iso}"><span class="nr-meta">'
                   f'{meta_line(o)}</span><span>{esc(o.title)}</span></a></li>' for o in picks)
    return (f'<aside class="nr-more" aria-label="{esc(label)}"><div class="nr-more-head"><h2 class="nr-label">'
            f'{esc(label)}</h2><a href="/">All notes →</a></div><ol>{rows}</ol></aside>')


def write_if_changed(path: Path, new: str, what: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    if new == old:
        print(f"unchanged {path.relative_to(ROOT)}")
        return False
    path.write_text(new, encoding="utf-8")
    print(f"updated   {path.relative_to(ROOT)} ({what})")
    return True


def place(text: str, name: str, block: str, anchor_re: str, after: bool) -> str:
    """Replace an existing nr block, or insert it next to anchor_re."""
    rx = block_re(name)
    if rx.search(text):
        return rx.sub(lambda _m: block, text, count=1)
    m = re.search(anchor_re, text, re.IGNORECASE)
    if not m:
        raise SystemExit(f"error: no {anchor_re!r} to anchor nr:{name}")
    i = m.end() if after else m.start()
    return text[:i] + ("\n" if after else "") + block + ("\n" if not after else "") + text[i:]


def migrate_old_header(text: str, title: str) -> str:
    """Drop an old-style page's own <h1>, date line and <hr>; the generated block replaces them."""
    m = re.search(r"<body[^>]*>", text, re.IGNORECASE)
    if not m:
        return text
    head, rest = text[:m.end()], text[m.end():]
    h1 = re.match(r"\s*<h1[^>]*>(.*?)</h1>", rest, re.DOTALL | re.IGNORECASE)
    if not h1 or " ".join(html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).split()) != title:
        return text
    rest = rest[h1.end():]
    rest = re.sub(r"^\s*<p class=\"meta\">.*?</p>", "", rest, count=1, flags=re.DOTALL)
    rest = re.sub(r"^\s*<hr\s*/?>", "", rest, count=1, flags=re.IGNORECASE)
    return head + "\n" + rest.lstrip("\n")


# ------------------------------------------------------------------ 1. entries


def update_entry(e: Entry, entries: list, sections: list) -> bool:
    text = e.path.read_text(encoding="utf-8")
    if "<!-- nr:top:start -->" not in text:
        text = migrate_old_header(strip_generated(text), e.title)
    text = re.sub(r"\n*<!-- notes:more:start -->.*?<!-- notes:more:end -->\n*", "\n", text, flags=re.DOTALL)
    name = KINDS[e.section][0]
    desc = f'<p class="nr-desc">{esc(e.desc)}</p>' if e.desc else ""
    post_head = (
        f'<header class="nr-post-head"><nav class="nr-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>»</span>'
        f'<a href="/{e.section}/" data-sec="{e.section}">{name}</a></nav><h1 class="nr-title">{esc(e.title)}</h1>{desc}'
        f'<div class="nr-meta" data-sec="{e.section}">{meta_line(e, short=False, new=False)}</div></header>'
        f'<div class="nr-perch" id="nr-perch" data-hello="{e.minutes} min read. Tap me if you need anything."></div>'
        '<div class="nr-content">')
    more = more_cards([o for o in entries if o.url != e.url][:MORE_COUNT], "Recently on notes")
    text = place(text, "head", head_block(), r"</head>", after=False)
    text = place(text, "top", top_block(sections, e.section, post_head), r"<body[^>]*>", after=True)
    text = place(text, "bottom", bottom_block("</div>\n" + more, ("core", "guide")), r"</body>", after=False)
    return write_if_changed(e.path, text, "theme + recently block")


# ------------------------------------------------------------------ 2. section pages


def update_section(section: str, entries: list, sections: list) -> bool:
    name, heading, desc, _ = KINDS[section]
    mine = [e for e in entries if e.section == section]
    n = len(mine)
    body = months(mine) if mine else f'<p class="nr-empty">Nothing here yet. {heading} notes will show up here.</p>'
    hello = f"{n} note{'s' if n != 1 else ''} in here. Tap me if you need anything." if n else "Nothing here yet. Tap me for the other notes."
    intro = (f'<header class="nr-post-head"><nav class="nr-crumbs" aria-label="Breadcrumb"><a href="/">Home</a></nav>'
             f'<h1 class="nr-title">{heading}</h1><p class="nr-desc">{esc(desc)}</p></header>'
             f'<div class="nr-perch" id="nr-perch" data-hello="{esc(hello)}"></div>')
    page = (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n{GA}\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{heading} — {SITE}</title>\n<meta name=\"description\" content=\"{esc(desc)}\">\n"
            "<!-- Generated by .github/scripts/update-listings.py; edits here are overwritten. -->\n"
            f"{head_block()}\n</head>\n<body>\n{top_block(sections, section, intro)}\n{body}\n"
            f"{bottom_block('', ('core', 'guide'))}\n</body>\n</html>\n")
    path = ROOT / section / "index.html"
    path.parent.mkdir(exist_ok=True)
    return write_if_changed(path, page, f"{n} entries")


# ------------------------------------------------------------------ 3. homepage


def update_home(entries: list, sections: list) -> bool:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    recent = entries[:RECENT_COUNT]
    chips = "".join(
        f'<li><a href="/{s}/" data-f="{s}" data-sec="{s}">{KINDS[s][0]} <span class="nr-n">'
        f'{sum(1 for e in entries if e.section == s)}</span></a></li>' for s in sections)
    dots = "".join(f'<button type="button" aria-label="Post {i + 1}"></button>' for i in range(len(recent)))
    home = (
        '<h2 class="nr-label nr-recent-label">Recent posts</h2>'
        '<section class="nr-recent" id="nr-recent" aria-roledescription="carousel" aria-label="Recent posts">'
        f'<div class="nr-track">{"".join(card(e) for e in recent)}</div>'
        f'<div class="nr-rfoot"><div class="nr-dots" role="group" aria-label="Choose a post">{dots}</div>'
        f'<div class="nr-ctrl"><button class="nr-btn" id="nr-prev" type="button" aria-label="Previous post">{CHEVRON_L}</button>'
        f'<span class="nr-count" id="nr-count" aria-live="polite">1 / {len(recent)}</span>'
        f'<button class="nr-btn" id="nr-next" type="button" aria-label="Next post">{CHEVRON_R}</button></div></div>'
        '<div class="nr-bar" aria-hidden="true"><i></i></div></section>'
        '<h2 class="nr-label nr-all">All notes</h2>'
        f'<ul class="nr-chips" aria-label="Show one section"><li><a href="/" data-f="all" aria-current="true">All '
        f'<span class="nr-n">{len(entries)}</span></a></li>{chips}</ul>{months(entries)}')
    new = place(text, "head", head_block(), r"</head>", after=False)
    new = place(new, "top", top_block(sections), r"<body[^>]*>", after=True)
    new = place(new, "home", wrap("home", home), r"<!-- nr:bottom:start -->|</body>", after=False)
    new = place(new, "bottom", bottom_block("", ("core", "home", "guide"), toplink=True), r"</body>", after=False)
    return write_if_changed(path, new, "carousel + archive")


def update_plain(path: Path, sections: list, entries: list) -> bool:
    """A hand-written page (404): the shared header, guide and footer, plus the newest notes to go to instead."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    new = place(text, "head", head_block(), r"</head>", after=False)
    new = place(new, "top", top_block(sections), r"<body[^>]*>", after=True)
    more = more_cards(entries[:MORE_COUNT], "Newest notes")
    new = place(new, "bottom", bottom_block(more, ("core", "guide"), toplink=False), r"</body>", after=False)
    return write_if_changed(path, new, "theme + newest notes")


# ------------------------------------------------------------------ main

if __name__ == "__main__":
    entries = all_entries()
    # Menu and chips only show sections that have something in them.
    sections = [s for s in KINDS if any(e.section == s for e in entries)]
    for e in entries:
        update_entry(e, entries, sections)
    for s in KINDS:
        if (ROOT / s).is_dir():
            update_section(s, entries, sections)
    if (ROOT / "index.html").is_file():
        update_home(entries, sections)
    update_plain(ROOT / "404.html", sections, entries)
    sys.exit(0)
