# notes.rr2.dev

A collection of LLM-agent-generated notes, maintained by Rahul. Served via
GitHub Pages at <https://notes.rr2.dev>. Adapted from
[championswimmer/sites.arnavg.in](https://github.com/championswimmer/sites.arnavg.in)
by Arnav Gupta.

## Layout

- `/index.html` — apex page. Spartan. Keep it that way.
- `/research/<report-name>/index.html` — reports.
- `/learning/<guide-name>/index.html` — guides.
- `/worklog/<entry-name>/index.html` — worklog entries.
- `/unlisted/<slug>/index.html` — unlisted artifacts (talk decks, drafts). Reachable by direct link only: no listing page, not on the homepage, skipped by the generator. Unlisted, not private — the repo is public.
- `/llms.txt` — instructions for LLMs uploading to this repo. Read it before adding anything.

## Rules

- Every page is self-contained HTML with inline CSS/JS. No build step, no frameworks, no external dependencies unless unavoidable.
- Slugs are lowercase kebab-case.
- Adding a page? Follow `/llms.txt`.

## Generated content

`.github/scripts/update-listings.py` (run by the `update-listings` Action on every push that touches an entry) rewrites:

- `research/`, `learning/`, `worklog/` listing pages,
- the homepage "Latest" ticker and section lists (between `<!-- latest:… -->` and `<!-- sections:… -->` markers in `index.html`),
- the "Recently on notes.rr2.dev" block at the end of every entry (between `<!-- notes:more:… -->` markers).

Don't hand-edit inside those markers. To regenerate locally: `python3 .github/scripts/update-listings.py`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, lowercase, imperative, no trailing period.

- Scope is the section or area: `research`, `learning`, `worklog`, `unlisted`, `home`, `listings`, `ci`, `llms`.
- New page → `feat(<section>): add <slug>`. Change to an existing page → `fix(<section>): …` for corrections, `docs(<section>): …` for rewording.
- Site features → `feat(home): …`; workflows → `ci: …`; generated output and housekeeping → `chore(…): …`.
