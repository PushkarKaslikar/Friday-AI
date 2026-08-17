"""Comprehensive test suite for Phase 5.5 Semantic Memory & Local Vector Index Foundation.

Phase 5.5 - Semantic Memory & Local Vector Index Foundation
"""

import os
import tempfile
import threading

import pytest

from app.memory.db_manager import MemoryDatabaseManager
from app.memory.embedding_provider import LocalEmbeddingProvider
from app.memory.long_term_models import LongTermMemoryEntry
from app.memory.long_term_service import LongTermMemoryService
from app.memory.promotion_service import MemoryPromotionService
from app.memory.repository import SQLAlchemyMemoryRepository
from app.memory.semantic_index import FAISSMemoryIndex
from app.memory.semantic_metrics import SemanticMemoryMetrics
from app.memory.semantic_service import SemanticMemoryService
from app.memory.text_builder import MemoryEmbeddingTextBuilder


@pytest.fixture
def temp_db_manager():
    """Create a temporary SQLite database manager fixture."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_path = f.name
    f.close()

    db_mgr = MemoryDatabaseManager(db_path_override=temp_path)
    db_mgr.initialize_database()
    yield db_mgr
    db_mgr.close()
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:  # noqa: BLE001
            pass


@pytest.fixture
def semantic_service(temp_db_manager):
    """Create a SemanticMemoryService backed by temporary SQLite DB and FAISS index."""
    repo = SQLAlchemyMemoryRepository(temp_db_manager)
    promo = MemoryPromotionService(repo)
    lt_service = LongTermMemoryService(repository=repo, promotion_service=promo)

    provider = LocalEmbeddingProvider(dimension=384)
    faiss_idx = FAISSMemoryIndex(dimension=384)
    text_builder = MemoryEmbeddingTextBuilder()
    metrics = SemanticMemoryMetrics()

    f_idx = tempfile.NamedTemporaryFile(suffix=".faiss", delete=False)
    index_file = f_idx.name
    f_idx.close()

    service = SemanticMemoryService(
        long_term_service=lt_service,
        db_manager=temp_db_manager,
        embedding_provider=provider,
        semantic_index=faiss_idx,
        text_builder=text_builder,
        metrics=metrics,
        index_path_override=index_file,
    )
    yield service
    if os.path.exists(index_file):
        try:
            os.remove(index_file)
        except Exception:  # noqa: BLE001
            pass


# --- CATEGORY A: EMBEDDING PROVIDER ---


def test_embedding_provider_lifecycle():
    provider = LocalEmbeddingProvider(model_name="test-model", dimension=384)
    assert provider.dimensions == 384
    assert provider.model_name == "test-model"

    ok = provider.load()
    assert ok is True
    assert provider.is_healthy() is True

    res = provider.embed_text("Test embedding text")
    assert len(res.vector) == 384
    assert res.dimension == 384
    assert abs(res.norm - 1.0) < 0.05

    provider.unload()
    assert provider.is_healthy() is False


# --- CATEGORY B: TEXT BUILDER & SANITIZATION ---


def test_text_builder_formatting_and_sanitization():
    builder = MemoryEmbeddingTextBuilder(max_chars=100)
    entry = LongTermMemoryEntry(
        memory_id="m1",
        memory_type="PREFERENCE",
        subject="preferred_browser",
        content="Chrome",
    )

    text = builder.build_embedding_text(entry)
    assert "Chrome" in text
    assert "preferred_browser" in text

    # Secret credential sanitization
    secret_entry = LongTermMemoryEntry(
        memory_id="m2",
        memory_type="PREFERENCE",
        subject="my_password",
        content="super_secret_password_123",
    )
    secret_text = builder.build_embedding_text(secret_entry)
    assert "super_secret_password_123" not in secret_text
    assert "[REDACTED SECRET]" in secret_text


# --- CATEGORY C: FAISS INDEX OPERATIONS ---


def test_faiss_index_add_search_clear():
    idx = FAISSMemoryIndex(dimension=4)
    vec1 = [0.5, 0.5, 0.5, 0.5]
    vec2 = [0.0, 1.0, 0.0, 0.0]

    vid1 = idx.add_vector(vec1)
    vid2 = idx.add_vector(vec2)
    assert idx.vector_count == 2

    hits = idx.search_vectors(vec2, top_k=1)
    assert len(hits) == 1
    assert hits[0][0] == vid2

    idx.clear()
    assert idx.vector_count == 0


# --- CATEGORY D & E: INCREMENTAL INDEXING ---


def test_incremental_indexing_create_update_delete(semantic_service):
    lt_svc = semantic_service.long_term_service

    # 1. Create memory
    res = lt_svc.remember("preferred_editor", "VS Code", memory_type="PREFERENCE")
    assert res.status == "SUCCESS"

    semantic_service.sync_index()
    assert semantic_service.semantic_index.vector_count == 1

    # 2. Search
    hits = semantic_service.semantic_search("Which code editor do I like?", top_k=1)
    assert len(hits) == 1
    assert hits[0].memory_id == res.memory_id

    # 3. Update memory
    lt_svc.remember("preferred_editor", "Cursor", memory_type="PREFERENCE")
    semantic_service.sync_index()
    assert semantic_service.semantic_index.vector_count == 1

    # 4. Delete memory
    lt_svc.forget(subject="preferred_editor")
    semantic_service.sync_index()
    assert semantic_service.semantic_index.vector_count == 0


# --- CATEGORY F & G: CONSISTENCY VALIDATION ---


def test_consistency_validation(semantic_service):
    lt_svc = semantic_service.long_term_service
    lt_svc.remember("project_name", "Friday AI", memory_type="PROJECT")
    semantic_service.sync_index()

    report = semantic_service.validate_index_consistency()
    assert report.is_consistent is True
    assert report.vector_count == 1
    assert report.sqlite_memory_count == 1
    assert len(report.orphan_vector_ids) == 0
    assert len(report.missing_memory_ids) == 0


# --- CATEGORY H: SECURITY ---


def test_sensitive_credential_embedding_rejection(semantic_service):
    lt_svc = semantic_service.long_term_service

    # Secret credential attempt
    res = lt_svc.remember("api_key", "sk-proj-9999999999999")
    semantic_service.sync_index()

    # Verify no raw secret is stored in vector index
    hits = semantic_service.semantic_search("sk-proj-9999999999999", top_k=5)
    for h in hits:
        assert "sk-proj" not in str(h.metadata)


# --- CATEGORY I: ATOMIC REBUILD ---


def test_atomic_index_rebuild(semantic_service):
    lt_svc = semantic_service.long_term_service
    lt_svc.remember("theme", "Dark", memory_type="PREFERENCE")
    lt_svc.remember("language", "Python", memory_type="PREFERENCE")

    ok = semantic_service.rebuild_index()
    assert ok is True
    assert semantic_service.semantic_index.vector_count == 2

    report = semantic_service.validate_index_consistency()
    assert report.is_consistent is True


# --- CATEGORY J: SEARCH PRIMITIVE ---


def test_low_level_semantic_search_primitive(semantic_service):
    lt_svc = semantic_service.long_term_service
    lt_svc.remember("browser", "Chrome", memory_type="PREFERENCE")
    semantic_service.sync_index()

    hits = semantic_service.semantic_search("browser recommendation", top_k=5)
    assert len(hits) == 1
    assert hits[0].similarity > 0.0


# --- CATEGORY K: CONCURRENCY ---


def test_semantic_service_concurrency(semantic_service):
    lt_svc = semantic_service.long_term_service
    threads = []

    def worker(worker_id: int):
        for i in range(5):
            lt_svc.remember(
                f"conc_key_{worker_id}_{i}", f"val_{i}", memory_type="PREFERENCE"
            )
            semantic_service.sync_index()

    for w in range(3):
        t = threading.Thread(target=worker, args=(w,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    report = semantic_service.validate_index_consistency()
    assert report.sqlite_memory_count == 15
