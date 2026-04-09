#!/usr/bin/env python3
"""Seed ChromaDB with SRE runbooks from /runbooks."""

import argparse
import logging
import os
import sys
from pathlib import Path

import chromadb

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_runbook(filepath: Path) -> dict:
    content = filepath.read_text()
    lines = content.strip().split("\n")

    title = filepath.stem.replace("_", " ").title()
    category = "general"
    severity = "medium"

    for line in lines:
        if line.startswith("# Runbook:"):
            title = line.replace("# Runbook:", "").strip()
        elif line.startswith("## Severity:"):
            severity = line.replace("## Severity:", "").strip().lower()
        elif line.startswith("## Category:"):
            category = line.replace("## Category:", "").strip().lower()

    doc_id = f"runbook-{filepath.stem}"

    return {
        "id": doc_id,
        "content": content,
        "title": title,
        "source": f"runbooks/{filepath.name}",
        "category": "runbook",
        "severity": severity,
        "topic": category,
    }


def seed_knowledge(
    runbooks_dir: str = "./runbooks",
    host: str = "",
    port: int = 8001,
    collection_name: str = "synapse_knowledge",
    persist_dir: str = "./data/chroma",
):
    runbooks_path = Path(runbooks_dir)
    if not runbooks_path.exists():
        logger.error(f"Runbooks directory not found: {runbooks_dir}")
        sys.exit(1)

    md_files = sorted(runbooks_path.glob("*.md"))
    if not md_files:
        logger.error(f"No .md files found in {runbooks_dir}")
        sys.exit(1)

    logger.info(f"Found {len(md_files)} runbooks in {runbooks_dir}")

    if host:
        logger.info(f"Connecting to ChromaDB server at {host}:{port}")
        client = chromadb.HttpClient(host=host, port=port)
    else:
        logger.info(f"Using local ChromaDB at {persist_dir}")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=persist_dir)

    try:
        client.heartbeat()
        logger.info("ChromaDB connection verified")
    except Exception as e:
        logger.error(f"Cannot connect to ChromaDB: {e}")
        sys.exit(1)

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    documents = []
    for md_file in md_files:
        doc = parse_runbook(md_file)
        documents.append(doc)
        logger.info(f"  Parsed: {doc['title']} ({md_file.name})")

    ids = [d["id"] for d in documents]
    contents = [d["content"] for d in documents]
    metadatas = [
        {
            "title": d["title"],
            "source": d["source"],
            "category": d["category"],
        }
        for d in documents
    ]

    collection.upsert(ids=ids, documents=contents, metadatas=metadatas)

    logger.info(
        f"\nSeeded {len(documents)} runbooks into collection '{collection_name}'"
    )
    logger.info(f"Total documents in collection: {collection.count()}")

    logger.info("\nVerification — test search for 'high cpu usage':")
    results = collection.query(query_texts=["high cpu usage"], n_results=3)
    if results and results["documents"] and results["documents"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            title = results["metadatas"][0][i].get("title", "?")
            dist = results["distances"][0][i] if results["distances"] else "?"
            logger.info(
                f"  #{i + 1}: {title} (distance={dist:.4f})"
                if isinstance(dist, float)
                else f"  #{i + 1}: {title}"
            )
    else:
        logger.warning("  No results returned — check ChromaDB embedding model")


def main():
    parser = argparse.ArgumentParser(
        description="Seed Synapse knowledge base with SRE runbooks"
    )
    parser.add_argument(
        "--runbooks-dir", default="./runbooks", help="Path to runbooks directory"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("CHROMA_HOST", ""),
        help="ChromaDB host (empty for local)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CHROMA_PORT", "8001")),
        help="ChromaDB port",
    )
    parser.add_argument(
        "--collection", default="synapse_knowledge", help="ChromaDB collection name"
    )
    parser.add_argument(
        "--persist-dir", default="./data/chroma", help="Local persist directory"
    )
    args = parser.parse_args()

    seed_knowledge(
        runbooks_dir=args.runbooks_dir,
        host=args.host,
        port=args.port,
        collection_name=args.collection,
        persist_dir=args.persist_dir,
    )


if __name__ == "__main__":
    main()
