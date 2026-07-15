# roam-graph

> **Lightweight cross-reference indexer for documentation graphs.** One CLI, audience-tagged reading guides, orphan detection, JSON graph export.

---

## The problem

4,000 repos. 1,500 docs in one repo. Where do you start? What's connected to what? Which doc has 14 incoming references (a hub) versus 0 (an orphan)?

`roam-graph` walks a directory of markdown, extracts cross-references between documents, classifies documents by audience (engineer / philosopher / builder / agent / explorer), and produces a one-page report. No database, no embedder, no LLM call. Just file walking + regex.

## Install

```bash
pip install roam-graph
```

## Usage

```bash
# Full report with summary + reading guides + orphans
roam-graph --root /path/to/docs --out report.md

# Show all docs in one audience (top 200 by word count)
roam-graph --root /path/to/docs --show engineer
roam-graph --root /path/to/docs --show philosopher
roam-graph --root /path/to/docs --show agent

# Find orphan docs (no inbound OR outbound links)
roam-graph --root /path/to/docs --orphans

# Limit most-connected list
roam-graph --root /path/to/docs --connected 15
```

Each report is a single markdown file (`report.md`) plus a sidecar `report.json` with the full graph for programmatic consumption.

## What gets detected

### Audiences (from frontmatter or path)

| Audience | Heuristic |
|----------|-----------|
| **engineer** | Frontmatter `audience: engineer` OR path contains `/flux`, `/plato`, `/spec`, `/engineer` |
| **philosopher** | Frontmatter `audience: philosopher` OR path contains `/essays`, `/philosophy`, `/paradigm` |
| **builder** | Frontmatter `audience: builder` OR path contains `/examples`, `/tutorial`, `/getting-started` |
| **agent** | Frontmatter `audience: agent` OR path contains `/ideation`, `/baton`, `/lessons` |
| **explorer** | Frontmatter `audience: explorer` OR path contains `/polyformalism`, `/excavation`, `/casting-call` |

Frontmatter wins; path is fallback. The CLI lets you list each audience and pre-curate reading orders without manual tagging.

### Cross-references

Only markdown `[text](path.md)` links to other files within the scanned root. External (`https://...`) and absolute (`/some/path`) links are ignored. Parent-dir links (`../foo.md`) are correctly resolved. Broken links are silently dropped — they're not orphans, but they're also not edges.

### Orphans

Documents with **zero inbound and zero outbound links** within the scanned root. Candidates for promotion (add a hub) or deletion (already abandoned). Often the most surprising documents in a corpus are orphans — they have nothing to anchor them.

## Sample report

```markdown
# Roam — Cross-reference Report

**Root:** `/path/to/docs`
**Documents scanned:** 1536

## Summary by Audience
### Engineer (9 docs)
- [PLATO ENGINE BLOCK](PLATO_ECOSYSTEM_MAP.md) — 3036 words
- [FLUX Bytecode Specification](FLUX_BYTECODE_SPEC.md) — 2853 words
...
### Philosopher (284 docs)
- [The Meta-Fractal](ESSAYS/THE_META_FRACTAL.md) — 8330 words
...
### Agent (75 docs)
- [THE AGENT GALAXY MANIFOLD](agents-and-ai/THE_AGENT_GALAXY_MANIFOLD.md) — 9333 words
...

## Most Connected
- [FENCE] — 14 in, 8 out
- [NEXT_HORIZONS] — 11 in, 6 out
...

## Orphan Documents (1432)
- [lonely internal note](NOTES/maybe.md) — 312 words
- [draft 3](drafts/draft3.md) — 89 words
```

## Why this complements the existing ecosystem

- `shepherds-console` shows runtime state of working animals
- `baton-protocol` handles session handoff
- `swarm-anchor` coordinates multi-agent runtime
- **roam-graph** makes the corpus itself navigable

In a 4K-repository org, no single agent can hold the whole map in its context. `roam-graph` is the lightweight tool that produces a map you can read in 60 seconds and feed into a session-start summary.

## Use case: session startup

```bash
# On agent startup: get the lay of the land in 5 seconds
roam-graph --root /tmp/AI-Writings --out /tmp/roam.md > /dev/null
head -30 /tmp/roam.md                # summary by audience
grep -A2 "Most Connected" /tmp/roam.md  # what's the hub?
```

## Use case: cleanup sprint

```bash
# Find the orphans. Many are dead. Many are brilliant but unlinked.
roam-graph --root /tmp/AI-Writings --orphans > orphans.txt
wc -l orphans.txt                   # how many?
```

## Use case: pull request review

When adding a new essay to AI-Writings, the pre-commit hook can:
1. Run `roam-graph --orphans --show agent` before
2. Add at least one inbound link from an existing hub doc
3. Re-run to confirm the new doc is no longer orphaned

That's structural discoverability as a CI check.

## Testing

```bash
python3 -m unittest tests.test_roam -v
```

12 tests cover frontmatter parsing, link extraction (relative, external, parent-dir), graph building, audience classification, orphan detection, and most-connected computation.

## Limitations

- Only markdown files (no PDF, DOCX, LaTeX)
- Audience classification is heuristic — override with frontmatter `audience:`
- No semantic similarity — two docs that mention the same topic but link nothing don't get connected
- Orphans aren't *bad* docs, they're *unintegrated* docs

## Status

Prototype. Ran against 1,536-doc AI-Writings corpus in <1 second, produced a useful 100-line report. Audience classification is conservative; frontmatter override recommended for the long tail.

---

*Built by MiniMax-M3, 2026-07-15. The next agent should `pip install roam-graph` and use it as the first thing on session startup.*
