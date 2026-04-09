"""ChromaDB knowledge/RAG plugin."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb

from core.base import BaseKnowledge

logger = logging.getLogger(__name__)


class ChromaDBKnowledge(BaseKnowledge):

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
    ):
        self._host = host or os.getenv("CHROMA_HOST", "")
        self._port = int(port or os.getenv("CHROMA_PORT", "8000"))
        self._collection_name = collection_name or os.getenv(
            "CHROMA_COLLECTION", "synapse_knowledge"
        )
        self._persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIR", "./data/chroma"
        )

        self._client = self._connect()
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB knowledge plugin initialized: collection='{self._collection_name}', "
            f"documents={self._collection.count()}"
        )

    def _connect(self) -> chromadb.ClientAPI:
        if self._host:
            logger.info(f"Connecting to ChromaDB server at {self._host}:{self._port}")
            return chromadb.HttpClient(host=self._host, port=self._port)
        else:
            logger.info(f"Using local ChromaDB at {self._persist_directory}")
            Path(self._persist_directory).mkdir(parents=True, exist_ok=True)
            return chromadb.PersistentClient(path=self._persist_directory)

    @property
    def name(self) -> str:
        return "chromadb"

    def search(
        self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            where_filter = filters if filters else None
            results = self._collection.query(
                query_texts=[query],
                n_results=min(limit, self._collection.count() or 1),
                where=where_filter,
            )

            items = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = (
                        results["metadatas"][0][i]
                        if results["metadatas"] and results["metadatas"][0]
                        else {}
                    )
                    distance = (
                        results["distances"][0][i]
                        if results["distances"] and results["distances"][0]
                        else 1.0
                    )
                    doc_id = (
                        results["ids"][0][i]
                        if results["ids"] and results["ids"][0]
                        else f"doc-{i}"
                    )

                    items.append(
                        {
                            "id": doc_id,
                            "title": metadata.get("title", "Untitled"),
                            "content": doc,
                            "source": metadata.get("source", "unknown"),
                            "category": metadata.get("category", "general"),
                            "relevance_score": round(1.0 - distance, 4),
                        }
                    )

            return items
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {str(e)}", exc_info=True)
            return []

    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self._collection.get(ids=[item_id])
            if result and result["documents"] and result["documents"][0]:
                metadata = result["metadatas"][0] if result["metadatas"] else {}
                return {
                    "id": item_id,
                    "title": metadata.get("title", "Untitled"),
                    "content": result["documents"][0],
                    "source": metadata.get("source", "unknown"),
                    "category": metadata.get("category", "general"),
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving document {item_id}: {str(e)}")
            return None

    def add_document(
        self,
        doc_id: str,
        content: str,
        title: str = "Untitled",
        source: str = "manual",
        category: str = "general",
        extra_metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        try:
            metadata = {
                "title": title,
                "source": source,
                "category": category,
            }
            if extra_metadata:
                metadata.update(extra_metadata)

            self._collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[metadata],
            )
            logger.info(f"Added document '{title}' (id={doc_id}) to knowledge base")
            return True
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}", exc_info=True)
            return False

    def add_documents_bulk(self, documents: List[Dict[str, Any]]) -> int:
        try:
            ids = [d["id"] for d in documents]
            contents = [d["content"] for d in documents]
            metadatas = [
                {
                    "title": d.get("title", "Untitled"),
                    "source": d.get("source", "manual"),
                    "category": d.get("category", "general"),
                }
                for d in documents
            ]

            self._collection.upsert(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
            )
            logger.info(f"Bulk added {len(ids)} documents to knowledge base")
            return len(ids)
        except Exception as e:
            logger.error(f"Error in bulk add: {str(e)}", exc_info=True)
            return 0

    def health_check(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {str(e)}")
            return False
