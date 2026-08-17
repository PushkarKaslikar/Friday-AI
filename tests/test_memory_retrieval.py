"""Comprehensive test suite for Phase 5.6 Memory Retrieval & Relevant Context Engine.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

import os
import tempfile
import time

import pytest

from app.memory.context_builder import MemoryContextBuilder
from app.memory.db_manager import MemoryDatabaseManager
from app.memory.embedding_provider import LocalEmbeddingProvider
from app.memory.long_term_service import LongTermMemoryService
from app.memory.profile_service import UserProfileService
from app.memory.promotion_service import MemoryPromotionService
from app.memory.query_builder import MemoryQueryBuilder
from app.memory.ranking_service import MemoryRankingService
from app.memory.repository import SQLAlchemyMemoryRepository
from app.memory.retrieval_metrics import MemoryRetrievalMetrics
from app.memory.retrieval_models import (
    CandidateMemory,
    MemoryRetrievalConfig,
    MemoryRetrievalRequest,
    RetrievalMode,
    RetrievalStatus,
)
from app.memory.retrieval_policy import MemoryRetrievalPolicy
from app.memory.retrieval_service import MemoryRetrievalService
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
def retrieval_environment(temp_db_manager):
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

    config = MemoryRetrievalConfig(similarity_threshold=0.20, max_results=5)
    policy = MemoryRetrievalPolicy(config=config)
    q_builder = MemoryQueryBuilder()
    ranking_svc = MemoryRankingService(config=config)
    ctx_builder = MemoryContextBuilder(config=config)
    ret_metrics = MemoryRetrievalMetrics()

    ret_svc = MemoryRetrievalService(
        long_term_service=lt_svc,
        user_profile_service=prof_svc,
        session_service=None,
        semantic_service=sem_svc,
        policy=policy,
        query_builder=q_builder,
        ranking_service=ranking_svc,
        context_builder=ctx_builder,
        metrics=ret_metrics,
        config=config,
    )

    yield {
        "lt_svc": lt_svc,
        "prof_svc": prof_svc,
        "sem_svc": sem_svc,
        "ret_svc": ret_svc,
        "policy": policy,
        "q_builder": q_builder,
        "ranking_svc": ranking_svc,
        "ctx_builder": ctx_builder,
    }

    if os.path.exists(index_file):
        try:
            os.remove(index_file)
        except Exception:  # noqa: BLE001
            pass


# --- CATEGORY A: RETRIEVAL POLICY ---


def test_retrieval_policy_triggers_and_skips():
    policy = MemoryRetrievalPolicy()

    # 1. Explicit memory question -> TRIGGER
    req_exp = MemoryRetrievalRequest(
        request_id="r1", user_text="What do you remember about my browser?"
    )
    should_ret, mode, _ = policy.should_retrieve(req_exp)
    assert should_ret is True
    assert mode in (
        RetrievalMode.EXPLICIT,
        RetrievalMode.AUTO,
        RetrievalMode.PROFILE_FIRST,
    )

    # 2. Personal reference -> TRIGGER
    req_pref = MemoryRetrievalRequest(
        request_id="r2", user_text="Open my usual browser"
    )
    should_ret, mode, _ = policy.should_retrieve(req_pref)
    assert should_ret is True

    # 3. Simple action command -> SKIP
    req_skip = MemoryRetrievalRequest(request_id="r3", user_text="Set volume to 50%")
    should_ret, mode, _ = policy.should_retrieve(req_skip)
    assert should_ret is False
    assert mode == RetrievalMode.NONE


# --- CATEGORY B: QUERY BUILDER ---


def test_query_builder_normalization():
    builder = MemoryQueryBuilder()
    text = "Hey Friday, could you please tell me which browser I prefer?"
    q = builder.build_query(text)
    assert "hey friday" not in q
    assert "please" not in q
    assert "browser" in q
    assert "prefer" in q


# --- CATEGORY C & D: HYBRID SEARCH & STRUCTURED FILTERING ---


def test_hybrid_search_and_filtering(retrieval_environment):
    lt_svc = retrieval_environment["lt_svc"]
    sem_svc = retrieval_environment["sem_svc"]
    ret_svc = (
        retrieval_environment["retrieval_environment"]
        if "retrieval_environment" in retrieval_environment
        else retrieval_environment["ret_svc"]
    )

    lt_svc.remember("preferred_browser", "Chrome", memory_type="PREFERENCE")
    lt_svc.remember("contact_person", "Sarah", memory_type="PROFILE")
    sem_svc.sync_index()

    req = MemoryRetrievalRequest(
        request_id="r_flt", user_text="What browser do I prefer?"
    )
    res = ret_svc.retrieve_memory_context(req)

    assert res.retrieval_status == RetrievalStatus.MEMORIES_FOUND
    assert res.selected_count >= 1
    assert "Chrome" in res.context_text or "preferred_browser" in res.context_text


# --- CATEGORY E: RANKING ENGINE ---


def test_ranking_engine_weights():
    ranking_svc = MemoryRankingService()
    now = time.time()

    c_explicit = CandidateMemory(
        memory_id="m1",
        memory_type="PREFERENCE",
        subject="preferred_browser",
        content="Chrome",
        source="USER_EXPLICIT",
        confidence=1.0,
        importance="HIGH",
        created_at=now,
        updated_at=now,
        semantic_similarity=0.85,
    )

    c_derived = CandidateMemory(
        memory_id="m2",
        memory_type="PREFERENCE",
        subject="preferred_browser",
        content="Firefox",
        source="DERIVED",
        confidence=0.5,
        importance="LOW",
        created_at=now - 86400,
        updated_at=now - 86400,
        semantic_similarity=0.40,
    )

    ranked = ranking_svc.rank_candidates(
        [c_derived, c_explicit], relevance_threshold=0.20
    )
    assert len(ranked) == 2
    assert ranked[0].memory_id == "m1"
    assert ranked[0].final_score > ranked[1].final_score


# --- CATEGORY G: CONTEXT BUILDER & SANITIZATION ---


def test_context_builder_budgeting_and_sanitization():
    ctx_builder = MemoryContextBuilder()
    now = time.time()

    secret_mem = CandidateMemory(
        memory_id="m_sec",
        memory_type="PREFERENCE",
        subject="api_key",
        content="my_secret_token_12345",
        source="USER_EXPLICIT",
        confidence=1.0,
        importance="HIGH",
        created_at=now,
        updated_at=now,
    )

    block = ctx_builder.build_context_block([secret_mem], max_chars=500)
    assert "<RELEVANT_MEMORY_CONTEXT>" in block
    assert "my_secret_token_12345" not in block
    assert "********" in block


# --- CATEGORY H: USER PROFILE INTEGRATION ---


def test_profile_preference_retrieval(retrieval_environment):
    prof_svc = retrieval_environment["prof_svc"]
    ret_svc = retrieval_environment["ret_svc"]

    prof_svc.set_preference("preferred_editor", "VS Code", source="USER_EXPLICIT")

    req = MemoryRetrievalRequest(
        request_id="r_prof", user_text="What editor do I prefer?"
    )
    res = ret_svc.retrieve_memory_context(req)

    assert res.retrieval_status == RetrievalStatus.MEMORIES_FOUND
    assert res.selected_count >= 1
    assert "VS Code" in res.context_text or "preferred_editor" in res.context_text


# --- CATEGORY K: DEGRADED MODE FALLBACK ---


def test_degraded_mode_offline_fallback(retrieval_environment):
    ret_svc = retrieval_environment["ret_svc"]
    prof_svc = retrieval_environment["prof_svc"]

    prof_svc.set_preference("theme", "Dark", source="USER_EXPLICIT")

    # Disable semantic service
    ret_svc.semantic_service = None

    req = MemoryRetrievalRequest(request_id="r_deg", user_text="What theme do I use?")
    res = ret_svc.retrieve_memory_context(req)

    assert res.degraded_mode is True
    assert res.retrieval_status in (
        RetrievalStatus.MEMORIES_FOUND,
        RetrievalStatus.DEGRADED,
    )


# --- CATEGORY M: READ-ONLY INVARIANCE ---


def test_retrieval_read_only_invariance(retrieval_environment):
    lt_svc = retrieval_environment["lt_svc"]
    ret_svc = retrieval_environment["ret_svc"]

    lt_svc.remember("project_name", "Friday AI", memory_type="PROJECT")
    count_before = lt_svc.repository.count()

    req = MemoryRetrievalRequest(
        request_id="r_ro", user_text="What project am I working on?"
    )
    ret_svc.retrieve_memory_context(req)

    count_after = lt_svc.repository.count()
    assert count_before == count_after
