"""Comprehensive test suite for Phase 5.4 User Profile & Personal Context Management.

Phase 5.4 - User Profile & Personal Context Management
"""

import os
import tempfile
import threading

import pytest

from app.memory.db_manager import MemoryDatabaseManager
from app.memory.long_term_service import LongTermMemoryService
from app.memory.profile_models import (
    PreferenceState,
    ProjectStatus,
    WorkflowStatus,
)
from app.memory.profile_service import UserProfileService
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
def user_profile_service(temp_db_manager):
    """Create a UserProfileService instance backed by temporary SQLite DB via LongTermMemoryService."""
    repo = SQLAlchemyMemoryRepository(temp_db_manager)
    promo = MemoryPromotionService(repo)
    lt_service = LongTermMemoryService(repository=repo, promotion_service=promo)
    return UserProfileService(long_term_service=lt_service)


# --- CATEGORY A: USER IDENTITY ---


def test_user_identity_setting_and_retrieval(user_profile_service):
    res = user_profile_service.set_preferred_name("Alex")
    assert res is True

    identity = user_profile_service.get_identity()
    assert identity.preferred_name == "Alex"
    assert identity.display_name == "Alex"


# --- CATEGORY B: PREFERENCES & SUPERSEDING ---


def test_preference_organization_and_superseding(user_profile_service):
    # Set Chrome
    user_profile_service.set_preference("preferred_browser", "Chrome")
    assert user_profile_service.get_preference("preferred_browser") == "Chrome"

    # Supersede with Edge
    user_profile_service.set_preference("preferred_browser", "Edge")
    assert user_profile_service.get_preference("preferred_browser") == "Edge"

    profile = user_profile_service.build_profile()
    pref_item = profile.preferences.get("preferred_browser")
    assert pref_item is not None
    assert pref_item.value == "Edge"
    assert pref_item.status == PreferenceState.ACTIVE


# --- CATEGORY C: PERSISTENT PROJECTS ---


def test_persistent_project_profile(user_profile_service):
    ok = user_profile_service.add_project(
        name="Friday AI Assistant",
        local_path="D:\\Friday AI",
        description="Local personal voice assistant",
        aliases=["Friday", "Assistant"],
    )
    assert ok is True

    proj = user_profile_service.get_project("Friday AI Assistant")
    assert proj is not None
    assert proj.local_path == "D:\\Friday AI"
    assert proj.status == ProjectStatus.ACTIVE
    assert "Friday" in proj.aliases


# --- CATEGORY D: EXPLICIT CONTACT MEMORY ---


def test_explicit_contact_memory(user_profile_service):
    ok = user_profile_service.add_contact(
        name="Sarah",
        relationship="Project Lead",
        organization="Friday Core",
        notes="Remembers team lead",
    )
    assert ok is True

    c = user_profile_service.get_contact("Sarah")
    assert c is not None
    assert c.relationship == "Project Lead"
    assert c.organization == "Friday Core"


# --- CATEGORY E: WORKFLOW PROFILE ---


def test_workflow_profile_storage(user_profile_service):
    steps = ["Open Browser", "Search AI News", "Summarize Results"]
    ok = user_profile_service.add_workflow(
        name="AI News Routine", steps=steps, description="Daily AI briefing"
    )
    assert ok is True

    wf = user_profile_service.get_workflow("AI News Routine")
    assert wf is not None
    assert wf.steps == steps
    assert wf.status == WorkflowStatus.ACTIVE


# --- CATEGORY F: INTERACTION PATTERNS ---


def test_interaction_patterns_building(user_profile_service):
    user_profile_service.long_term_service.remember(
        subject="preferred_response_length",
        content="concise",
        memory_type="INTERACTION_PATTERN",
    )

    profile = user_profile_service.build_profile()
    pat = profile.interaction_patterns.get("preferred_response_length")
    assert pat is not None
    assert pat.pattern_value == "concise"


# --- CATEGORY G: SNAPSHOT GENERATION ---


def test_user_profile_snapshot_generation(user_profile_service):
    user_profile_service.set_preferred_name("Alex")
    user_profile_service.set_preference("communication_style", "concise")

    snap = user_profile_service.create_snapshot()
    assert snap.preferred_name == "Alex"
    assert snap.preferences_summary.get("communication_style") == "concise"
    assert "Preferred Name: Alex" in snap.formatted_snapshot


# --- CATEGORY H: ZERO DUPLICATE STORAGE ---


def test_zero_duplicate_storage_verification(user_profile_service, temp_db_manager):
    # Verify UserProfileService operates directly on underlying LongTermMemoryService
    user_profile_service.set_preference("theme", "Dark")
    raw_memories = user_profile_service.long_term_service.list_memories()

    assert len(raw_memories) == 1
    assert raw_memories[0].subject == "theme"
    assert raw_memories[0].content == "Dark"


# --- CATEGORY I: PROFILE RESET AND FORGET ---


def test_profile_reset_and_forget(user_profile_service):
    user_profile_service.set_preference("temp_key", "temp_val")
    assert user_profile_service.get_preference("temp_key") == "temp_val"

    removed = user_profile_service.remove_preference("temp_key")
    assert removed is True
    assert user_profile_service.get_preference("temp_key") is None


# --- CATEGORY J: CONCURRENCY ---


def test_user_profile_service_concurrency(user_profile_service):
    threads = []

    def worker(worker_id: int):
        for i in range(10):
            user_profile_service.set_preference(f"conc_key_{worker_id}", f"val_{i}")

    for w in range(5):
        t = threading.Thread(target=worker, args=(w,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    profile = user_profile_service.build_profile()
    assert len(profile.preferences) == 5
