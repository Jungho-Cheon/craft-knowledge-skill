#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "chromadb>=1.0",
#   "sentence-transformers>=3.0",
# ]
# ///
"""
Query the vector index of a craft-knowledge vault.

Usage:
  uv run query.py --vault /path/to/vault "search query"
  uv run query.py --vault /path/to/vault --top 5 "search query"
"""
import argparse
import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EXCERPT_LENGTH = 400


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("query", nargs="+")
    args = parser.parse_args()

    vault = Path(args.vault).resolve()
    db_path = vault / ".chromadb"

    if not db_path.exists():
        print(
            f"No index found. Run first:\n"
            f"  uv run embed.py --vault {vault}",
            file=sys.stderr,
        )
        sys.exit(1)

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(db_path))
    collection = client.get_or_create_collection("notes", embedding_function=ef)

    if collection.count() == 0:
        print("Index is empty. Run embed.py to populate it.", file=sys.stderr)
        sys.exit(1)

    query_text = " ".join(args.query)
    results = collection.query(
        query_texts=[query_text],
        n_results=min(args.top, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]

    print(f'Query: "{query_text}"')
    print(f"Vault: {vault}\n")

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
        relevance = max(0.0, 1.0 - dist)
        excerpt = doc[:EXCERPT_LENGTH].replace("\n", " ").strip()
        if len(doc) > EXCERPT_LENGTH:
            excerpt += "..."

        print(f"[{i}] {meta['relative_path']}")
        print(f"    Title    : {meta.get('title', '(unknown)')}")
        print(f"    Relevance: {relevance:.0%}")
        print(f"    Excerpt  : {excerpt}")
        print()


if __name__ == "__main__":
    main()
