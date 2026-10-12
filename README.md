# notes.rr2.dev

A collection of LLM-agent-generated notes, maintained by Rahul. Served via
GitHub Pages at <https://notes.rr2.dev>. Adapted from
[championswimmer/sites.arnavg.in](https://github.com/championswimmer/sites.arnavg.in)
by Arnav Gupta.

## Layout

- `/index.html` — homepage. The intro paragraph is hand-written; everything between `<!-- nr:… -->` markers is generated.
- `/assets/fonts/` — the two web fonts (Fraunces for headings, Caveat for the guide's speech), subset to Latin.
- `/favicon.ico` — same icon as rr2.dev.
- `/research/<report-name>/index.html` — reports.
- `/learning/<guide-name>/index.html` — guides.
- `/worklog/<entry-name>/index.html` — worklog entries.
- `/unlisted/<slug>/index.html` — unlisted artifacts (talk decks, drafts). Reachable by direct link only: no listing page, not on the homepage, skipped by the generator. Unlisted, not private — the repo is public.
- `/llms.txt` — instructions for LLMs uploading to this repo. Read it before adding anything.

## Rules

- Every page is self-contained HTML with inline CSS/JS. No build step, no frameworks, no external dependencies unless unavoidable.
- The site design (colours, fonts, header, footer, the stick-figure guide) lives in `.github/scripts/theme/`. The generator minifies it and inlines it into every page, so pages stay self-contained. Edit the design there, never in a page.
- Slugs are lowercase kebab-case.
- Adding a page? Follow `/llms.txt`.

## Generated content

`.github/scripts/update-listings.py` (run by the `update-listings` Action on every push that touches an entry or the design) rewrites:

- every entry page, between its `<!-- nr:head:… -->`, `<!-- nr:top:… -->` and `<!-- nr:bottom:… -->` markers: the inlined design, the site header, the title block (title, description, date, reading time, section), the "Recently on notes" cards, the guide and the footer. The entry's own content between the markers is never touched;
- the `research/`, `learning/` and `worklog/` section pages, whole;
- the homepage's Recent posts carousel and month-by-month archive (between `<!-- nr:home:… -->`), plus its head, header and footer;
- the header and footer of `404.html`.

Don't hand-edit inside those markers. To regenerate locally: `python3 .github/scripts/update-listings.py`. Running it twice changes nothing.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, lowercase, imperative, no trailing period.

- Scope is the section or area: `research`, `learning`, `worklog`, `unlisted`, `home`, `listings`, `ci`, `llms`.
- New page → `feat(<section>): add <slug>`. Change to an existing page → `fix(<section>): …` for corrections, `docs(<section>): …` for rewording.
- Site features → `feat(home): …`; workflows → `ci: …`; generated output and housekeeping → `chore(…): …`.
