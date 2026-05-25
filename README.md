# craft-knowledge

A Claude Code skill for building and navigating domain knowledge bases.  
Write notes in Obsidian. Search them semantically. Let agents find what they need instantly.

---

## What problem does this solve?

### Problem 1 — The more notes you have, the harder it is to find anything

When learning a new domain, taking notes feels productive. At first, it is. But once you have 20, 50 notes, you start asking "where did I write about sampling configuration?" Regular search requires exact keyword matches, so searching "session recording rate" won't find the note that explains `replaysSessionSampleRate`.

### Problem 2 — Agents forget everything when a session ends

When you open a new Claude Code session and ask "help me understand fermentation chemistry," the agent has no memory of what you studied before. To catch up, it has to read through your vault note by note. With 30 notes that's manageable. With 100, the startup cost grows linearly with the vault size.

### The solution

Both problems share the same fix.

- **Semantic search**: A vector search engine attached to your vault understands meaning, not just keywords. Searching "session recording rate" finds the note about `replaysSessionSampleRate`.
- **O(1) navigation**: Instead of reading every file, the agent asks "what notes are relevant to this topic?" once and gets back the top matches — regardless of how many notes exist.

> **What is vector search?** Text is converted into a high-dimensional numerical array (a vector) that captures its meaning. Texts with similar meanings land close together in this space. That's why semantically related notes surface even when the exact words don't match.

---

## Key concepts

A few ideas to understand before diving in.

### Source vs. derived artifact

Notes (markdown files) are the **source**. Humans write them, agents read them, git tracks them.

The vector index (`.chromadb/` folder) is a **derived artifact** — generated automatically from the source. Think of it like `node_modules`: it's produced from `package.json` and can be regenerated at any time, so there's no reason to commit it to git.

```
Markdown notes  →  tracked by git   (permanent source)
.chromadb/      →  gitignored        (regenerate with embed.py)
```

Cloning the repository on a new machine and running `embed.py` once is the equivalent of `npm install`.

### WikiLinks and the graph layer

In Obsidian, `[[note-name]]` syntax creates links between notes — called WikiLinks. In this skill, WikiLinks aren't just navigation shortcuts. They are **intentional relationships** that the agent can follow to traverse related concepts.

Vector search finds *similar* notes. WikiLinks connect *related* notes that might not be similar in wording. Both layers work together.

```
Vector search  →  query "sampling"  →  returns notes ranked by semantic similarity
WikiLinks      →  from that note, follow [[alerting]]  →  arrives at a connected concept
```

### Insights

The difference between a note collection and a knowledge base is **insights**.

For example, `extraction-ratio` and `water-temperature` look unrelated. But read them together and a non-obvious pattern appears: "water that's too hot extracts bitter compounds so quickly that the target ratio is hit before the sweeter notes develop — the ratio looks right but the cup tastes wrong." That connection doesn't exist in either note individually.

These cross-note observations — things you can only see by reading multiple notes together — are captured in the `## Insights` section of each MOC (Map of Content). This is what makes a knowledge base valuable instead of just a reference manual.

---

## The bigger picture

Skills distribute *how* an agent acts. A knowledge base distributes *what* it knows — the connections between concepts that only become visible through experience, not from reading documentation.

As this format matures, it could be distributed as a package: someone publishes a domain KB, others install it to give their agent instant expertise, similar to how pre-trained model weights are shared but for structured domain understanding in markdown.

---

## Architecture

```
{VaultRoot}/
├── _MOC/                    # Map of Content per domain — index + insight hub
│   └── {domain}-moc.md
├── _inbox/                  # Unverified stub notes awaiting research
├── domains/
│   └── {domain}/
│       ├── concepts/        # Core ideas and definitions
│       ├── people/          # Key figures (when relevant)
│       └── tools/           # Tools, frameworks, libraries
├── _templates/              # Note templates
├── .chromadb/               # Vector index — auto-generated, gitignored
├── .gitignore
└── MEMORY.md                # Quick reference index for agents
```

```
~/.claude/skills/craft-knowledge/
├── skill.md          # Agent workflow specification
├── README.md         # This document
└── scripts/
    ├── embed.py      # Build and update the vector index
    └── query.py      # Semantic note search
```

---

## Setup

### 1. Install uv (once per machine)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`uv` is a Python package manager that works like `npx`. When you run a script, it automatically installs the required libraries (`chromadb`, `sentence-transformers`) into an isolated environment. No manual `pip install` needed.

### 2. Build the index for a vault

After creating an Obsidian vault and writing some notes:

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault /path/to/vault
```

**What happens on the first run**:
1. `uv` installs required packages automatically (~200MB, cached afterward)
2. The embedding model is downloaded (~500MB, saved to `~/.cache/` for reuse)
3. Every `.md` file in the vault is converted into a vector and stored in `.chromadb/`

Subsequent runs only process files that have changed since the last index.

### 3. Add .gitignore

If the vault is under version control, make sure `.chromadb/` is excluded:

```
.chromadb/
```

---

## Usage

### Starting a new domain KB

In Claude Code:

```
/craft-knowledge Build a knowledge base about {domain}. Reference {URL}.
```

The agent will ask for the vault path and depth (intro / intermediate / deep-dive).

### Resuming work in a new session

The agent searches first, then reads only what's relevant:

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/query.py \
  --vault /path/to/vault "topic or question"

# Example output
[1] domains/sentry/tools/alerting.md              Relevance: 29%
[2] domains/sentry/concepts/events-and-issues.md  Relevance: 18%
[3] domains/sentry/concepts/environments.md       Relevance: 17%
```

Read only those notes, then follow `[[WikiLinks]]` within them to explore connected concepts.

### After writing or editing notes

```bash
# Auto-detects changed files and updates only those
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault /path/to/vault

# Update a single file immediately
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py \
  --vault /path/to/vault --file domains/sentry/tools/alerting.md
```

### Check if the index is fresh

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault /path/to/vault --check

# Up to date
Index is up to date. (15 notes)

# Needs updating
2 stale note(s):
  domains/sentry/tools/alerting.md
  domains/sentry/concepts/dsn.md
```

### On a freshly cloned repository

```bash
git clone {kb-repo}
cd {kb-dir}
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault .
```

---

## Note quality standards

### Conditions for `status: published`

- Every factual claim is verified against **≥2 independent sources**
- Source URLs and access dates are recorded in frontmatter
- Unverified claims are isolated in a callout block, not mixed into prose:

```markdown
> [!question]- Needs verification #needs-verification
> {claim that couldn't be confirmed}
> Sources checked: {list}
```

This keeps unverified content greppable via `#needs-verification` without polluting the note body.

### Insight obligations

Every published note must include at least one of:

**Consider together** — "What would a reader miss by only reading this note?" Name 2–3 other notes that, when read alongside this one, complete the picture. Explain why the combination matters.

**When this goes wrong** — Trace the downstream symptoms of misunderstanding or misconfiguring this concept. "If you do X, then Y happens in Z" — concrete, causal chains.

**Decision criteria** — When similar alternatives exist, describe when to choose this one vs. the other. Remove ambiguity for the reader.

### MOC Insights section

The MOC is not just a table of contents. It must contain a `## Insights` section with cross-cutting observations that only become visible when reading multiple notes together:

```markdown
## Insights

> **[Insight title]**: {observation not visible from any single note}. See [[note-a]], [[note-b]].
```

Aim for 3–7 insights per domain. An empty Insights section means the knowledge base is incomplete.

---

## Current limitations and improvement directions

An honest assessment of what this structure doesn't yet solve.

### 1. Content goes stale

**Now**: Technical KBs degrade quickly. When a library releases a new major version or best practices shift, existing notes can become actively misleading. The `refresh_after` frontmatter field exists but is not automatically checked or acted upon — manual review is required.

**Directions**:
- Add `check-sources.py` to periodically re-fetch source URLs and detect content changes
- Auto-tag notes past their `refresh_after` date with `#needs-refresh` so agents prioritize them on the next session
- Introduce semver versioning for KB packages so consumers can pin to a known-good version

### 2. The index must be rebuilt on each new machine

**Now**: Because `.chromadb/` is gitignored, anyone receiving the KB must run `embed.py` themselves. The first run takes several minutes (model download + indexing).

**Directions**:
- Define a KB package metadata standard (`kb.yaml`):
  ```yaml
  name: sentry-react
  version: 1.0.0
  embedding_model: paraphrase-multilingual-MiniLM-L12-v2
  notes: 15
  insights: 5
  ```
- A `craft-knowledge install {kb-name}` command that handles download and indexing in one step
- Pre-built index distribution is technically possible via a shared embedding service, but conflicts with the current design principle of running everything locally

### 3. No objective quality measurement

**Now**: Note count doesn't indicate quality. A 15-note KB with rich cross-note insights can be more valuable than a 100-note KB of isolated facts. Currently this requires human judgment.

**Directions**:
- `audit.py` script that automatically reports:
  - Percentage of notes with Insights sections
  - Average WikiLink count per note
  - Ratio of `#needs-verification` notes
  - Count of expired `refresh_after` dates
- Use these metrics as quality badges in a marketplace context: `verified: 93%`, `insights: 5`, `freshness: 2026-05`

### 4. WikiLink traversal is manual

**Now**: After `query.py` returns entry-point notes, following their WikiLinks to discover connected concepts is something the agent must do manually — it isn't automated.

**Directions**:
- Add `--expand` flag to `query.py`: parse WikiLinks from returned notes and automatically include the linked notes in the results
- This would combine vector search (similarity-based) and graph traversal (relationship-based) into a single command

### 5. KB building depends on a single author

**Now**: Creating and maintaining a KB depends on one person (or one agent session). There's no structure for teams to collaboratively build domain knowledge, or for communities to maintain shared KBs.

**Directions**:
- Add `author` field to note frontmatter for per-note ownership
- Since markdown is the source, standard git PR workflows apply naturally — multiple contributors write notes in their area of expertise and merge via PR
- In a marketplace context, this maps directly to npm's package ownership + community PR model

---

## Command reference

### embed.py

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault {path} [options]
```

| Option | Description |
|--------|-------------|
| `--vault PATH` | Vault root path (required) |
| `--file RELPATH` | Index a single file. Path relative to vault root |
| `--check` | Report stale files without modifying anything |

Without options, detects changed files automatically and re-indexes only those.

### query.py

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/query.py --vault {path} "query"
```

| Option | Description |
|--------|-------------|
| `--vault PATH` | Vault root path (required) |
| `--top N` | Number of results to return (default: 3) |
| `query` | Search query. Korean and English both supported |

**Embedding model**: `paraphrase-multilingual-MiniLM-L12-v2`  
Supports 50+ languages. Runs locally via ONNX. No API key required.  
Model weights are downloaded on first run to `~/.cache/chroma/onnx_models/` and reused.

---

## Design decision log

| Decision | Alternative considered | Reason |
|----------|----------------------|--------|
| `.chromadb/` gitignored | Commit the index | Binary files produce meaningless diffs and bloat the repo. Reproducible from source |
| `uv run` for dependencies | Global `pip install` | No system Python pollution. Reproducible across machines. Zero manual install steps |
| Multilingual embedding model | English-only model | English-only model returned 0–3% relevance on Korean queries. Multilingual model: 29–53% |
| Vector search + WikiLinks dual layer | Vector search alone | Vectors find similar notes. Insights come from connecting dissimilar notes. WikiLinks fill that gap |
| No `_status.md` summary file | Session state summary file | Maintenance cost grows linearly with note count. Becomes stale. Solved by vector search instead |
| mtime-based staleness detection | Full re-index every run | Only processes changed files, keeping update time constant regardless of vault size |
