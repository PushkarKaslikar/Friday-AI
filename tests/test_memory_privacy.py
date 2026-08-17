"""Comprehensive test suite for Phase 5.7 Memory Privacy, Security, Governance & User Control.

Phase 5.7 - Memory Privacy, Security, Governance & User Control
"""

import os
import tempfile
import time

import pytest

from app.memory.db_manager import MemoryDatabaseManager
from app.memory.embedding_provider import LocalEmbeddingProvider
from app.memory.long_term_service import LongTermMemoryService
from app.memory.privacy_metrics import MemoryPrivacyMetrics
from app.memory.privacy_models import (
    PrivacyMode,
    PrivacyReasonCode,
    PrivacySensitivity,
)
from app.memory.privacy_policy import MemoryPrivacyPolicy
from app.memory.privacy_service import MemoryPrivacyService
from app.memory.profile_service import UserProfileService
from app.memory.promotion_service import MemoryPromotionService
from app.memory.repository import SQLAlchemyMemoryRepository
from app.memory.retention_service import MemoryRetentionService
from app.memory.semantic_index import FAISSMemoryIndex
from app.memory.semantic_metrics import SemanticMemoryMetrics
from app.memory.semantic_service import SemanticMemoryService
from app.memory.text_builder import MemoryEmbeddingTextBuilder


@pytest.fixture
def temp_db_manager():
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
def privacy_environment(temp_db_manager):
    repo = SQLAlchemyMemoryRepository(temp_db_manager)
    promo = MemoryPromotionService(repo)
    lt_svc = LongTermMemoryService(repository=repo, promotion_service=promo)
    prof_svc = UserProfileService(long_term_service=lt_svc)

    provider = LocalEmbeddingProvider(dimension=384)
    faiss_idx = FAISSMemoryIndex(dimension=384)
    text_builder = MemoryEmbeddingTextBuilder()
    sem_metrics = SemanticMemoryMetrics()

    f_idx = tempfile.NamedTemporaryFile(suffix=".faiss", delete=False)
    index_file = f_idx.name
    f_idx.close()

    sem_svc = SemanticMemoryService(
        long_term_service=lt_svc,
        db_manager=temp_db_manager,
        embedding_provider=provider,
        semantic_index=faiss_idx,
        text_builder=text_builder,
        metrics=sem_metrics,
        index_path_override=index_file,
    )

    policy = MemoryPrivacyPolicy()
    retention_svc = MemoryRetentionService(
        long_term_service=lt_svc,
        user_profile_service=prof_svc,
        semantic_service=sem_svc,
    )
    metrics = MemoryPrivacyMetrics()

    priv_svc = MemoryPrivacyService(
        policy=policy,
        retention_service=retention_svc,
        metrics=metrics,
        long_term_service=lt_svc,
        user_profile_service=prof_svc,
        semantic_service=sem_svc,
    )

    yield {
        "lt_svc": lt_svc,
        "prof_svc": prof_svc,
        "sem_svc": sem_svc,
        "priv_svc": priv_svc,
        "policy": policy,
        "retention_svc": retention_svc,
        "metrics": metrics,
    }

    if os.path.exists(index_file):
        try:
            os.remove(index_file)
        except Exception:  # noqa: BLE001
            pass


# --- CATEGORY A: SENSITIVITY CLASSIFICATION ---


def test_sensitivity_classification(privacy_environment):
    policy = privacy_environment["policy"]

    # 1. Normal
    s_norm = policy.classify_sensitivity("preferred_browser", "Chrome", "PREFERENCE")
    assert s_norm == PrivacySensitivity.NORMAL

    # 2. Personal
    s_pers = policy.classify_sensitivity("Friday Assistant", "D:\\Friday AI", "PROJECT")
    assert s_pers == PrivacySensitivity.PERSONAL

    # 3. Sensitive
    s_sens = policy.classify_sensitivity("therapist_name", "Dr Smith", "CONTACT")
    assert s_sens == PrivacySensitivity.SENSITIVE

    # 4. Restricted Secret
    s_rest = policy.classify_sensitivity("api_key", "sk-proj-123456789", "PREFERENCE")
    assert s_rest == PrivacySensitivity.RESTRICTED


# --- CATEGORY B: WRITE POLICY & RESTRICTED SECRET DEFENSE ---


def test_write_policy_and_secret_rejection(privacy_environment):
    priv_svc = privacy_environment["priv_svc"]

    # Normal write allowed
    d_ok = priv_svc.evaluate_write("preferred_browser", "Chrome", "PREFERENCE")
    assert d_ok.decision is True
    assert d_ok.reason_code == PrivacyReasonCode.ALLOWED

    # Secret write rejected
    d_secret = priv_svc.evaluate_write("api_key", "sk-proj-999999", "PREFERENCE")
    assert d_secret.decision is False
    assert d_secret.reason_code == PrivacyReasonCode.RESTRICTED_DATA


# --- CATEGORY C: RETENTION & EXPIRATION CLEANUP ---


def test_retention_expiration_cleanup(privacy_environment):
    lt_svc = privacy_environment["lt_svc"]
    retention_svc = privacy_environment["retention_svc"]

    # Create temporary memory and simulate overdue expiration
    res = lt_svc.remember("temp_note", "val_123", memory_type="PREFERENCE")
    m = lt_svc.get_memory(res.memory_id)
    assert m is not None
    m.expires_at = time.time() - 3600
    lt_svc.repository.update_memory(m)

    cleaned = retention_svc.run_expiration_cleanup()
    assert cleaned == 1
    assert len(lt_svc.list_memories()) == 0


# --- CATEGORY D: RETRIEVAL PRIVACY ---


def test_retrieval_privacy_blocking(privacy_environment):
    priv_svc = privacy_environment["priv_svc"]

    d_norm = priv_svc.evaluate_read("preferred_browser", "Chrome", "PREFERENCE")
    assert d_norm.retrieval_allowed is True

    d_secret = priv_svc.evaluate_read("password", "secret123", "PREFERENCE")
    assert d_secret.retrieval_allowed is False
    assert d_secret.reason_code == PrivacyReasonCode.RESTRICTED_DATA


# --- CATEGORY E: INDEX PRIVACY ---


def test_index_privacy_blocking(privacy_environment):
    priv_svc = privacy_environment["priv_svc"]

    d_norm = priv_svc.evaluate_index("preferred_browser", "Chrome", "PREFERENCE")
    assert d_norm.index_allowed is True

    d_secret = priv_svc.evaluate_index("private_key", "0x12345", "PREFERENCE")
    assert d_secret.index_allowed is False
    assert d_secret.reason_code == PrivacyReasonCode.RESTRICTED_DATA


# --- CATEGORY F: PROFILE PRIVACY ---


def test_profile_privacy_blocking(privacy_environment):
    priv_svc = privacy_environment["priv_svc"]

    d_norm = priv_svc.evaluate_profile("preferred_browser", "Chrome", "PREFERENCE")
    assert d_norm.profile_allowed is True

    d_secret = priv_svc.evaluate_profile("bearer_token", "xyz789", "PREFERENCE")
    assert d_secret.profile_allowed is False


# --- CATEGORY H: DELETION PROPAGATION ---


def test_deletion_propagation_end_to_end(privacy_environment):
    lt_svc = privacy_environment["lt_svc"]
    sem_svc = privacy_environment["sem_svc"]
    priv_svc = privacy_environment["priv_svc"]

    res = lt_svc.remember("preferred_browser", "Chrome", memory_type="PREFERENCE")
    m_id = res.memory_id
    sem_svc.sync_index()

    assert len(lt_svc.list_memories()) == 1
    assert sem_svc.semantic_index.vector_count == 1

    ok = priv_svc.forget_memory(
        subject="preferred_browser", memory_type="PREFERENCE", memory_id=m_id
    )
    assert ok is True
    assert len(lt_svc.list_memories()) == 0
    assert sem_svc.semantic_index.vector_count == 0


# --- CATEGORY NO_PERSISTENCE & STRICT MODES ---


def test_privacy_modes(privacy_environment):
    priv_svc = privacy_environment["priv_svc"]

    # NO_PERSISTENCE mode
    priv_svc.config.mode = PrivacyMode.NO_PERSISTENCE
    d_no_p = priv_svc.evaluate_write("preferred_editor", "VS Code", "PREFERENCE")
    assert d_no_p.decision is False
    assert d_no_p.reason_code == PrivacyReasonCode.POLICY_DISABLED

    # STRICT mode
    priv_svc.config.mode = PrivacyMode.STRICT
    d_strict = priv_svc.evaluate_write("doctor", "Dr Smith", "CONTACT")
    assert d_strict.requires_confirmation is True

    priv_svc.config.mode = PrivacyMode.NORMAL


# --- CATEGORY COMPLETE WIPE ---


def test_clear_all_memory_wipe(privacy_environment):
    lt_svc = privacy_environment["lt_svc"]
    sem_svc = privacy_environment["sem_svc"]
    priv_svc = privacy_environment["priv_svc"]

    lt_svc.remember("preferred_browser", "Chrome", memory_type="PREFERENCE")
    sem_svc.sync_index()

    ok = priv_svc.clear_all_memory(confirmation=True)
    assert ok is True
    assert len(lt_svc.list_memories()) == 0
    assert sem_svc.semantic_index.vector_count == 0
