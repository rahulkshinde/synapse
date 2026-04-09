"""Tests for ChromaDB knowledge plugin."""

import pytest

from plugins.knowledge.chromadb_knowledge import ChromaDBKnowledge


@pytest.fixture
def knowledge(tmp_path):
    """ChromaDBKnowledge using a temp directory (no server needed)."""
    return ChromaDBKnowledge(
        host="",
        persist_directory=str(tmp_path / "chroma"),
        collection_name="test_knowledge",
    )


# ── Basic Operations ──────────────────────────────────────────


class TestDocumentOperations:
    def test_add_and_retrieve_document(self, knowledge):
        ok = knowledge.add_document(
            doc_id="rb-001",
            content="When CPU exceeds 85%, scale up replicas immediately.",
            title="High CPU Runbook",
            source="runbooks/high_cpu.md",
            category="runbook",
        )
        assert ok is True

        doc = knowledge.get_by_id("rb-001")
        assert doc is not None
        assert doc["title"] == "High CPU Runbook"
        assert "CPU exceeds 85%" in doc["content"]

    def test_get_nonexistent_document(self, knowledge):
        assert knowledge.get_by_id("does-not-exist") is None

    def test_upsert_overwrites(self, knowledge):
        knowledge.add_document(doc_id="rb-002", content="Version 1", title="Test")
        knowledge.add_document(
            doc_id="rb-002", content="Version 2", title="Test Updated"
        )

        doc = knowledge.get_by_id("rb-002")
        assert doc is not None
        assert "Version 2" in doc["content"]
        assert doc["title"] == "Test Updated"


# ── Search ────────────────────────────────────────────────────


class TestSearch:
    def test_search_returns_relevant_results(self, knowledge):
        knowledge.add_document(
            doc_id="rb-cpu",
            content="High CPU usage runbook: check node_cpu_seconds_total, scale pods, look for goroutine leaks.",
            title="High CPU Runbook",
            category="runbook",
        )
        knowledge.add_document(
            doc_id="rb-disk",
            content="Disk pressure runbook: check df -h, clean unused images, rotate logs.",
            title="Disk Pressure Runbook",
            category="runbook",
        )

        results = knowledge.search("cpu is too high")
        assert len(results) >= 1
        # The CPU runbook should rank higher than the disk runbook
        assert results[0]["title"] == "High CPU Runbook"
        assert results[0]["relevance_score"] > 0

    def test_search_empty_collection(self, knowledge):
        results = knowledge.search("anything")
        assert results == []

    def test_search_with_limit(self, knowledge):
        for i in range(5):
            knowledge.add_document(
                doc_id=f"doc-{i}", content=f"Document {i} about SRE", title=f"Doc {i}"
            )

        results = knowledge.search("SRE", limit=2)
        assert len(results) <= 2


# ── Bulk Operations ───────────────────────────────────────────


class TestBulkOperations:
    def test_bulk_add(self, knowledge):
        docs = [
            {
                "id": "bulk-1",
                "content": "OOM kill recovery steps",
                "title": "OOMKill",
                "category": "runbook",
            },
            {
                "id": "bulk-2",
                "content": "Certificate expiration handling",
                "title": "Cert Expiry",
                "category": "runbook",
            },
            {
                "id": "bulk-3",
                "content": "Kafka consumer lag troubleshooting",
                "title": "Kafka Lag",
                "category": "runbook",
            },
        ]
        count = knowledge.add_documents_bulk(docs)
        assert count == 3

        doc = knowledge.get_by_id("bulk-2")
        assert doc is not None
        assert doc["title"] == "Cert Expiry"


# ── Health Check ──────────────────────────────────────────────


class TestHealthCheck:
    def test_health_check_local(self, knowledge):
        assert knowledge.health_check() is True
