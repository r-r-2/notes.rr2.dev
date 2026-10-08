---
name: publish-site-artifact
description: Publish a static site artifact — a self-contained report, guide, or worklog page — to the notes.rr2.dev static-site collection. Use when asked to publish, upload, or add a static page artifact.
---

# Publish to notes.rr2.dev

These instructions are for AI agents and LLMs working on Rahul's behalf.

Static-site collection of LLM-agent notes, maintained by Rahul. Repo `r-r-2/notes.rr2.dev`, branch `main`, served from root at https://notes.rr2.dev.

## Add a page

1. Slug: lowercase kebab-case, e.g. `indian-railways-history`.
2. Write self-contained `index.html` (inline CSS/JS, no build, no frameworks; keep any assets inside your folder) to:
   - report → `research/<slug>/index.html` (serves at `/research/<slug>/`)
   - guide → `learning/<slug>/index.html` (serves at `/learning/<slug>/`)
   - worklog entry → `worklog/<slug>/index.html` (serves at `/worklog/<slug>/`)
   - unlisted artifact (talk deck, draft, anything meant to be reached by direct link only) → `unlisted/<slug>/index.html` (serves at `/unlisted/<slug>/`). See "Unlisted artifacts" below; the date, title and "recent posts" notes that follow don't apply to it.
   - Add `<meta name="date" content="YYYY-MM-DD">` to the `<head>` of every entry so its date appears in the section listing and sort order (newest first).
   - The page `<title>` becomes the listing link text; a trailing `— notes.rr2.dev` is stripped automatically, so titling the page `<Title> — notes.rr2.dev` is fine.
   - Don't write a "recent posts" footer yourself. A GitHub Action appends a generated "Recently on notes.rr2.dev" block (between `<!-- notes:more:start -->` and `<!-- notes:more:end -->`) before `</body>` of every entry and refreshes the homepage ticker and section lists. When updating an existing page, you can keep or drop that block; it is regenerated either way.
3. Analytics: include this GA4 gtag snippet in `<head>` of every new `index.html`. The Measurement ID is not a secret — put it in the HTML, not in `.env`.

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-2QQWNZ1TJ4"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-2QQWNZ1TJ4');
</script>
```
4. Never touch `CNAME`, `.nojekyll`, `robots.txt`, `llms.txt`, `add-skill.sh`, `skills/`, `research/index.html`, `learning/index.html`, `worklog/index.html` (listings, the homepage lists and each entry's "Recently on" block regenerate automatically via a GitHub Action). Never commit tokens/secrets.

## Unlisted artifacts

`unlisted/<slug>/` is for pages that should be reachable by direct link only, e.g. a talk deck that is presented before it is written up.

- Nothing generated picks it up: no listing page, no homepage ticker or section list, no "Recently on" block injected into it, and it never appears in other pages' "Recently on" blocks.
- Add `<meta name="robots" content="noindex">` to its `<head>`.
- Don't link to it from any other page, and don't create `unlisted/index.html` (so `/unlisted/` itself stays a 404).
- Unlisted is not private: the repo is public, so the file and its commit are visible on GitHub. Nothing secret goes here.
- To reveal it later, link to `/unlisted/<slug>/` from a normal entry (e.g. the worklog entry about the talk) and drop the `noindex` tag. Don't move it; links already shared keep working.

## Upload (pick the first that applies; never hardcode or commit tokens)

Commit messages follow Conventional Commits: `feat(<section>): add <slug>` for a new page, `fix(<section>): update <slug>` for changes (section is `research`, `learning`, `worklog` or `unlisted`).

### 1. gh CLI (shell, authenticated — no clone needed)

```sh
CONTENT=$(base64 < /local/path/to/index.html | tr -d '\n')
gh api "repos/r-r-2/notes.rr2.dev/contents/research/<slug>/index.html" \
  -X PUT -f message="feat(research): add <slug>" -f branch="main" -f content="$CONTENT"
# updating an existing file: GET the path first for its "sha", then add -f sha="<sha>".
```
Ref: https://cli.github.com/manual/

### 2. GitHub MCP server (installed + authenticated)

Call `create_or_update_file` once per file with owner `r-r-2`,
repo `notes.rr2.dev`, branch `main`, path `research/<slug>/index.html`
(or `learning/...`), your HTML as `content` (raw text, not base64),
message `feat(research): add <slug>` (use the right section). Omit `sha` for new files; for updates fetch it
first via `get_file_contents` (same owner/repo/path, ref `main`).
Ref: https://github.com/github/github-mcp-server

### 3. GitHub REST API (`GITHUB_TOKEN` in env, else ask the human for one)

```sh
CONTENT=$(base64 < /local/path/to/index.html | tr -d '\n')
curl -X PUT -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/r-r-2/notes.rr2.dev/contents/research/<slug>/index.html \
  -d "{\"message\":\"feat(research): add <slug>\",\"content\":\"$CONTENT\",\"branch\":\"main\"}"
# updating an existing file: GET the path first, add its "sha" to the payload.
```
Ref: https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents

## Checklist before you finish

- [ ] Page renders standalone (open the file directly, no server needed).
- [ ] GA4 gtag snippet (`G-2QQWNZ1TJ4`) is in `<head>`.
- [ ] You pushed only your page (listings, homepage and "Recently on" blocks update themselves via Action).
- [ ] No secrets, tokens, or personal data committed.
- [ ] Tell the human the public URL.
