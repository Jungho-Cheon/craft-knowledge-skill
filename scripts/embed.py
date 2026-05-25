#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "chromadb>=1.0",
#   "sentence-transformers>=3.0",
# ]
# ///
"""
Build or update the vector index for a craft-knowledge vault.

Usage:
  uv run embed.py --vault /path/to/vault           # index entire vault
  uv run embed.py --vault /path/to/vault --check   # show stale files without indexing
  uv run embed.py --vault /path/to/vault --file domains/sentry/concepts/dsn.md
"""
import argparse
import json
import re
import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EXCLUDE_DIRS = {".obsidian", ".chromadb", "_templates", ".git"}
EXCLUDE_FILES = {"MEMORY.md"}
MANIFEST_PATH = ".chromadb/manifest.json"


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            return text[end + 3:].strip()
    return text


def extract_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def should_index(path: Path, vault: Path) -> bool:
    parts = set(path.relative_to(vault).parts)
    if parts & EXCLUDE_DIRS:
        return False
    if path.name in EXCLUDE_FILES:
        return False
    return path.suffix == ".md"


def load_manifest(vault: Path) -> dict:
    p = vault / MANIFEST_PATH
    if p.exists():
        return json.loads(p.read_text())
    return {}


def save_manifest(vault: Path, manifest: dict):
    p = vault / MANIFEST_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2))


def is_stale(md_file: Path, vault: Path, manifest: dict) -> bool:
    relative = str(md_file.relative_to(vault))
    mtime = md_file.stat().st_mtime
    return manifest.get(relative) != mtime


def collect_files(vault: Path) -> list[Path]:
    return sorted(f for f in vault.rglob("*.md") if should_index(f, vault))


def index_file(collection, md_file: Path, vault: Path, manifest: dict):
    try:
        raw = md_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  skip {md_file.name}: {e}", file=sys.stderr)
        return

    body = strip_frontmatter(raw)
    if not body.strip():
        return

    relative = str(md_file.relative_to(vault))
    collection.upsert(
        ids=[relative],
        documents=[body],
        metadatas=[{
            "path": str(md_file),
            "relative_path": relative,
            "title": extract_title(body, md_file.stem),
        }],
    )
    manifest[relative] = md_file.stat().st_mtime
    print(f"  indexed: {relative}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--file", default=None, help="Index a single file (relative to vault)")
    parser.add_argument("--check", action="store_true", help="Show stale files without indexing")
    args = parser.parse_args()

    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"Error: vault not found at {vault}", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(vault)

    # --check mode: report staleness and exit
    if args.check:
        files = collect_files(vault)
        stale = [f for f in files if is_stale(f, vault, manifest)]
        if not stale:
            print(f"Index is up to date. ({len(files)} notes)")
        else:
            print(f"{len(stale)} stale note(s) (run embed.py --vault {vault} to update):")
            for f in stale:
                print(f"  {f.relative_to(vault)}")
        sys.exit(0)

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(vault / ".chromadb"))
    collection = client.get_or_create_collection("notes", embedding_function=ef)

    # --file mode: single file
    if args.file:
        target = vault / args.file
        if not target.exists():
            print(f"Error: file not found: {target}", file=sys.stderr)
            sys.exit(1)
        index_file(collection, target, vault, manifest)
        save_manifest(vault, manifest)
        print(f"Done. Total: {collection.count()}")
        return

    # Full vault: only index stale files
    files = collect_files(vault)
    stale = [f for f in files if is_stale(f, vault, manifest)]

    if not stale:
        print(f"Index is up to date. ({len(files)} notes, nothing to do)")
        sys.exit(0)

    print(f"Indexing {len(stale)}/{len(files)} changed files in {vault}...")
    for f in stale:
        index_file(collection, f, vault, manifest)

    save_manifest(vault, manifest)
    print(f"\nDone. Total documents in index: {collection.count()}")


if __name__ == "__main__":
    main()
