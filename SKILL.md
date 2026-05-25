---
name: craft-knowledge
description: Build structured domain knowledge bases in Obsidian by synthesizing web sources into atomic, interlinked notes that serve as agent-readable records. Only verified facts are published; unconfirmed claims are tagged inline for lazy resolution. Use when user wants to document a domain, build agent expertise from external sources, or create a knowledge base. Triggers on "/craft-knowledge".
---

# Craft Knowledge

Build a domain knowledge base in Obsidian: research → verify → synthesize → atomize → link.

## Vault Setup

At the start of each session, ask:
```
Which vault should I write to? (provide the absolute path)
Are you starting a new domain, or continuing an existing one?
```

This skill uses **dedicated Knowledge Base vaults**, separate from the personal vault (daily notes, weekly notes, etc.).

A vault is either a **package** (single distributable domain) or a **consumer** (integrates multiple packages).

**Package vault** — one domain, distributable unit:

```
{package-name}/
├── kb.yaml            # Package metadata (name, version, embedding_model, ...)
├── MOC.md             # Map of Content — single domain, lives at root
├── concepts/          # Core ideas, definitions
├── people/            # Key figures, authors (when relevant)
├── tools/             # Products, frameworks, libraries
└── .chromadb/         # Vector index (auto-generated, never edit manually)
```

Agent navigation is handled by the vector index (`query.py`), not a manual index file. The MOC serves as the human-readable domain map and insights hub.

**Consumer vault** — integrates installed packages:

```
{vault-name}/
├── kb.json            # Dependency manifest (name, version per package)
├── domains/
│   └── {package-name}/   # Installed package lives here as a namespace
├── _MOC/              # Cross-package Maps of Content (one per domain)
└── .chromadb/
```

Each note = one concept, 5–10 min read (300–800 words). If a note grows beyond that, extract sub-concepts as child notes and link back.

## Vector Index

Every vault uses a local vector index for O(1) semantic search. The index lives inside the vault as `.chromadb/` — a derived artifact, never edited directly, excluded from git.

**Scripts** (stored in the skill, work for any vault via `--vault` argument):
```
~/.claude/skills/craft-knowledge/scripts/
├── embed.py   # Build / update the index; detects stale notes automatically
└── query.py   # Search: returns top-k relevant note paths + excerpts
```

**Prerequisite**: [`uv`](https://docs.astral.sh/uv/) must be installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`). All Python dependencies (`chromadb`, `sentence-transformers`) are declared inline in the scripts and installed automatically by `uv` on first run — no manual `pip install` needed.

**Embedding model**: `paraphrase-multilingual-MiniLM-L12-v2` — 50+ languages including Korean, runs locally via ONNX, no API key required. Model weights are cached in `~/.cache/` after the first run.

### Session Start (continuing an existing vault)

Before reading any notes, query the index to find what's relevant to the current task:

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/query.py \
  --vault {vault_path} "task description or topic"
```

Read only the returned note paths. Do **not** enumerate all files — that defeats the purpose.

If `.chromadb/` does not exist yet (first time, or cloned on a new machine), build it:
```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault {vault_path}
```

Check index freshness without modifying anything:
```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault {vault_path} --check
```

### After Writing or Editing Notes

Run embed without any extra flags — it automatically detects and re-indexes only changed files:
```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault {vault_path}
```

To update a single file immediately after editing:
```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py \
  --vault {vault_path} --file concepts/note-name.md
```

### .gitignore

`.chromadb/` must be in the vault's `.gitignore`. It is a derived artifact: rebuild it anytime with `embed.py`.

## Vault Merge

Use when two separate vaults should be combined (e.g., merging a domain-specific vault into a larger multi-domain vault).

### Merge Workflow

1. **Inventory both vaults** — list all notes and MOCs in source and target
2. **Detect conflicts** — notes with identical filenames or overlapping concepts
3. **Resolve conflicts** (for each conflict):
   - If content is complementary → merge into one note, consolidate sources
   - If content is duplicate → keep the more complete version, discard the other
   - If domain classification differs → spawn a sub-agent to reclassify (see Classify step)
4. **Rewrite internal links** — update all `[[WikiLinks]]` to reflect new paths in target vault
5. **Merge MOCs** — combine domain MOC entries; remove duplicates
6. **Move notes** — copy resolved notes into `{TargetVault}/domains/{package-name}/`
7. **Verify graph integrity** — ensure no broken links remain (search for `[[` targets that don't exist)
8. **Report** — list merged notes, resolved conflicts, and any remaining `status: stub` notes

## Note Frontmatter

```yaml
---
domain: {domain}
status: published | stub
sources:
  - url: "https://..."
    accessed: {YYYY-MM-DD}
tags: []
refresh_after: {YYYY-MM-DD}   # optional — for time-sensitive topics
---
```

- `published` — all claims in this note are verified from ≥2 independent sources
- `stub` — placeholder; content to be filled once verified

**Unverified claims inside a note** are not written as prose. Instead, use an inline tag block:

```md
> [!question]- Needs verification #needs-verification
> {claim or question that couldn't be confirmed}
> Sources checked: {list}
```

This keeps unverified content visible to agents (greppable via `#needs-verification`) without polluting the main body.

## Workflow

### 1. Scope
- Confirm domain name and depth (intro / intermediate / deep-dive)
- Confirm vault type: package (single domain) or consumer (multi-domain)
- Check if `MOC.md` exists at the vault root; if not, create one

### 2. Research & Verify
- Web-search the topic; read ≥2 independent primary sources before writing
- Never guess — keep searching until the claim is confirmed
- If a claim cannot be verified after reasonable search: capture it as a `[!question]` callout, not as prose
- Log every source URL in frontmatter

### 3. Synthesize (copyright-safe)
- Rewrite entirely in your own words; no direct copy-paste of source text
- Distill to: key ideas, mechanisms, trade-offs, concrete examples
- Unverifiable claims → `[!question]` callout + `#needs-verification` tag

### 4. Atomize
- One concept per note
- Target 300–800 words; split overflows into child notes

### 5. Link
- Add `[[WikiLinks]]` to related notes (stubs count)
- Update the domain MOC with the new note
- Bidirectional links — link back from referenced notes too

### 6. Classify (ambiguous domain)
- If a note could belong to 2+ domains, spawn a sub-agent in a **fresh session**:
  ```
  "Given these domain options: {A}, {B}. Classify this note based only on its content.
   Return: primary domain, reason (≤2 sentences), confidence 1–5."
  ```
- Accept if confidence ≥ 4; otherwise save with `status: stub` and `#needs-verification` tag in the most likely folder

### 7. Lazy refresh
- On each skill invocation, search for notes tagged `#needs-verification` and `status: stub`
- Attempt verification; if confirmed, rewrite as prose and remove the callout
- Update `refresh_after` dates for time-sensitive notes

## MOC Template

```md
# {Domain} — Map of Content

## Core Concepts
- [[concept-a]]
- [[concept-b]]

## Key People
- [[person-x]]

## Tools & Frameworks
- [[tool-y]]

## Open Questions
- [[stub-note-title]] — #needs-verification
```

## Insight Layer

A knowledge base that only accumulates facts is a reference manual, not an intelligence asset. Every note should help a reader (human or agent) understand **why it matters** and **how it combines** with other notes to produce understanding that no single note can provide alone.

### Insight obligations per note

Every published note must include at minimum one of:

- **"함께 고려할 것" (Consider together)** — explicitly name 2–3 other notes whose meaning changes when read alongside this one
- **"잘못 이해하거나 설정하면 (When this goes wrong)"** — what breaks if this concept is misconfigured or misunderstood, traced to its downstream effect
- **"결정 기준 (Decision criteria)"** — when to use this vs. a common alternative

### MOC Insights section

The MOC is not just an index. It must contain a dedicated `## Insights` section with cross-cutting observations that emerge only from reading multiple notes together. Each insight follows the form:

```md
> **[Insight title]**: {observation}. See [[note-a]], [[note-b]].
```

Aim for 3–7 insights per domain. These are the highest-value outputs of the knowledge base.

### Existing files are signals

When an existing file is found in the vault (even empty), **never delete it**. It was placed there deliberately — investigate and fill it. An empty file in a knowledge vault is a claim that this topic matters; the obligation is to research and complete it, not to remove it.

### Insight discovery triggers

After writing each new note, ask:
1. Does this note *change the meaning* of any other note I've written?
2. Is there a trade-off, failure mode, or combination effect that only becomes visible by reading this note and another together?
3. If an agent used only this note without the others, what would it get wrong?

If yes to any — write that insight into the MOC and link both notes.

## Rules

- **Verified facts only in prose** — if you can't confirm it, use a `[!question]` callout.
- **Secondary creation** — reframe, summarize, compare; never reproduce source text verbatim.
- **Never hallucinate** — search before writing; no guessing.
- **Always update the MOC** after adding notes.
- Long-form reference → child note linked from parent.
- **Never delete existing vault files** — investigate and fill them instead.
- **Insights are first-class outputs** — a domain with no MOC insights section is incomplete.
