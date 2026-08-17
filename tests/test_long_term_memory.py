"""Comprehensive test suite for Phase 5.3 Long-Term Memory & Persistent Memory Foundation.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import os
import tempfile
import threading

import pytest

from app.memory.db_manager import MemoryDatabaseManager
from app.memory.long_term_models import (
    LongTermMemoryConfig,
    MemoryCandidate,
    MemoryOperation,
    MemoryRequest,
    MemorySource,
    MemoryType,
    UserControlState,
)
from app.memory.long_term_service import LongTermMemoryService
from app.memory.promotion_service import MemoryPromotionService
from app.memory.repository import SQLAlchemyMemoryRepository


@pytest.fixture
def temp_db_manager():
    """Create a temporary SQLite database manager fixture."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

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
def long_term_service(temp_db_manager):
    """Create a LongTermMemoryService instance backed by temporary SQLite DB."""
    repo = SQLAlchemyMemoryRepository(temp_db_manager)
    promo = MemoryPromotionService(repo)
    return LongTermMemoryService(repository=repo, promotion_service=promo)


# --- CATEGORY A: DATABASE INITIALIZATION ---


def test_database_initialization_and_schema(temp_db_manager):
    assert temp_db_manager.is_initialized is True
    assert temp_db_manager.is_healthy() is True


# --- CATEGORY B: CRUD OPERATIONS ---


def test_long_term_memory_crud(long_term_service):
    # 1. Create
    res_c = long_term_service.remember(
        subject="preferred_editor",
        content="VSCode",
        memory_type=MemoryType.PREFERENCE,
    )
    assert res_c.status == "SUCCESS"
    m_id = res_c.memory_id
    assert m_id is not None

    # 2. Read
    mem = long_term_service.get_memory(m_id)
    assert mem is not None
    assert mem.subject == "preferred_editor"
    assert mem.content == "VSCode"

    # 3. Update
    res_u = long_term_service.update_memory(m_id, content="Cursor")
    assert res_u.status == "SUCCESS"
    assert long_term_service.get_memory(m_id).content == "Cursor"

    # 4. Delete / Forget
    res_d = long_term_service.forget(memory_id=m_id)
    assert res_d.status == "SUCCESS"
    assert (
        long_term_service.get_memory(m_id).user_control_state
        == UserControlState.DELETED
    )


# --- CATEGORY C: PERSISTENCE ACROSS RESTARTS ---


def test_long_term_memory_persistence_across_restarts():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

    try:
        # Process A: Write memory & close DB
        db_mgr_a = MemoryDatabaseManager(db_path_override=temp_path)
        db_mgr_a.initialize_database()
        repo_a = SQLAlchemyMemoryRepository(db_mgr_a)
        svc_a = LongTermMemoryService(repository=repo_a)

        svc_a.remember("restart_test_key", "Persisted_Value_99")
        db_mgr_a.close()

        # Process B: Re-open DB & read memory
        db_mgr_b = MemoryDatabaseManager(db_path_override=temp_path)
        db_mgr_b.initialize_database()
        repo_b = SQLAlchemyMemoryRepository(db_mgr_b)
        svc_b = LongTermMemoryService(repository=repo_b)

        val = svc_b.find_preference("restart_test_key")
        assert val == "Persisted_Value_99"
        db_mgr_b.close()
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:  # noqa: BLE001
                pass


# --- CATEGORY D: PROMOTION POLICY ---


def test_memory_promotion_policy(long_term_service):
    candidate = MemoryCandidate(
        memory_type=MemoryType.PREFERENCE,
        subject="communication_style",
        content="concise",
        source=MemorySource.USER_EXPLICIT,
        explicit_request=True,
    )

    res = long_term_service.promote_candidate(candidate)
    assert res.status == "SUCCESS"
    assert long_term_service.find_preference("communication_style") == "concise"


# --- CATEGORY E: DEDUPLICATION ---


def test_memory_deduplication(long_term_service):
    res1 = long_term_service.remember("dedup_browser", "Chrome")
    assert res1.status == "SUCCESS"

    res2 = long_term_service.remember("dedup_browser", "Chrome")
    assert res2.status == "SUCCESS"
    assert "Duplicate" in res2.message

    memories = long_term_service.list_memories(subject="dedup_browser")
    assert len(memories) == 1


# --- CATEGORY F: CONFLICT RESOLUTION ---


def test_memory_conflict_resolution(long_term_service):
    long_term_service.remember("conflict_theme", "Dark")
    assert long_term_service.find_preference("conflict_theme") == "Dark"

    long_term_service.remember("conflict_theme", "Light")
    assert long_term_service.find_preference("conflict_theme") == "Light"

    memories = long_term_service.list_memories(subject="conflict_theme")
    assert len(memories) == 1


# --- CATEGORY G: FORGET & CLEAR ---


def test_memory_forget_and_clear(long_term_service):
    long_term_service.remember("key_1", "Val 1")
    long_term_service.remember("key_2", "Val 2")

    res_f = long_term_service.forget(subject="key_1")
    assert res_f.status == "SUCCESS"
    assert (
        long_term_service.repository.find_by_type_subject("PREFERENCE", "key_1") is None
    )

    res_c = long_term_service.clear_all()
    assert res_c.status == "SUCCESS"
    assert long_term_service.repository.count() == 0


# --- CATEGORY H: BOUNDS & SIZE LIMITS ---


def test_memory_limits_and_bounding(temp_db_manager):
    repo = SQLAlchemyMemoryRepository(temp_db_manager)
    cfg = LongTermMemoryConfig(max_total_memories=2)
    svc = LongTermMemoryService(repository=repo, config=cfg)

    res1 = svc.remember("k1", "v1")
    res2 = svc.remember("k2", "v2")
    assert res1.status == "SUCCESS"
    assert res2.status == "SUCCESS"

    res3 = svc.remember("k3", "v3")
    assert res3.status == "REJECTED"
    assert "limit reached" in res3.message


# --- CATEGORY I: SECURITY & CREDENTIAL REJECTION ---


def test_security_credential_rejection(long_term_service):
    res_pass = long_term_service.remember("user_password", "super_secret_123")
    assert res_pass.status == "REJECTED"
    assert "credentials" in res_pass.message.lower()

    res_key = long_term_service.remember("api_key", "sk-proj-123456789")
    assert res_key.status == "REJECTED"


# --- CATEGORY J: CONCURRENCY & THREAD SAFETY ---


def test_database_concurrency_thread_safety(long_term_service):
    threads = []

    def worker(worker_id: int):
        for i in range(10):
            long_term_service.remember(f"thread_key_{worker_id}", f"value_{i}")

    for w in range(5):
        t = threading.Thread(target=worker, args=(w,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    count = long_term_service.repository.count()
    assert count == 5


# --- CATEGORY K: FAILURE RECOVERY & DEGRADATION ---


def test_database_failure_recovery_and_degradation():
    db_mgr = MemoryDatabaseManager(db_path_override="Z:\\invalid_path\\test.db")
    healthy = db_mgr.is_healthy()
    assert healthy is False


# --- CATEGORY L: STRUCTURED REQUEST HANDLING ---


def test_structured_memory_request_handling(long_term_service):
    req_rem = MemoryRequest(
        operation=MemoryOperation.REMEMBER,
        memory_type=MemoryType.PREFERENCE,
        subject="preferred_language",
        content="Python",
    )

    res_rem = long_term_service.handle_memory_request(req_rem)
    assert res_rem.status == "SUCCESS"
    assert long_term_service.find_preference("preferred_language") == "Python"

    req_forget = MemoryRequest(
        operation=MemoryOperation.FORGET,
        memory_type=MemoryType.PREFERENCE,
        subject="preferred_language",
    )
    res_forget = long_term_service.handle_memory_request(req_forget)
    assert res_forget.status == "SUCCESS"
    assert long_term_service.find_preference("preferred_language") is None
