"""User Profile service for building, refreshing, and managing user domain context over LongTermMemoryService.

Phase 5.4 - User Profile & Personal Context Management
"""

import threading
import time

from app.memory.long_term_models import (
    MemorySource,
    MemoryType,
)
from app.memory.long_term_service import LongTermMemoryService
from app.memory.profile_models import (
    PreferenceState,
    ProfilePreferenceItem,
    ProjectStatus,
    UserContactItem,
    UserIdentity,
    UserInteractionPatternItem,
    UserProfile,
    UserProfileConfig,
    UserProfileSnapshot,
    UserProjectItem,
    UserWorkflowItem,
    WorkflowStatus,
)


class UserProfileService:
    """Thread-safe domain manager organizing persistent long-term memories into a structured UserProfile."""

    def __init__(
        self,
        long_term_service: LongTermMemoryService,
        config: UserProfileConfig | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self.long_term_service = long_term_service
        self.config = config or UserProfileConfig()

    def build_profile(self) -> UserProfile:
        """Build and return a strongly typed UserProfile by aggregating active persistent memories."""
        with self._lock:
            active_memories = self.long_term_service.list_memories()

            identity = UserIdentity()
            preferences: dict[str, ProfilePreferenceItem] = {}
            projects: dict[str, UserProjectItem] = {}
            contacts: dict[str, UserContactItem] = {}
            workflows: dict[str, UserWorkflowItem] = {}
            patterns: dict[str, UserInteractionPatternItem] = {}

            for mem in active_memories:
                m_type = (
                    mem.memory_type.value
                    if hasattr(mem.memory_type, "value")
                    else str(mem.memory_type)
                )
                subject = mem.subject.strip()

                # Identity check
                if subject in ("preferred_name", "user_name", "display_name"):
                    identity.preferred_name = mem.content
                    identity.display_name = mem.content
                    identity.profile_updated_at = mem.updated_at
                    continue

                # Preferences
                if m_type in (
                    MemoryType.PREFERENCE.value,
                    MemoryType.USER_PREFERENCE.value,
                    MemoryType.COMMUNICATION_PREFERENCE.value,
                ):
                    preferences[subject] = ProfilePreferenceItem(
                        key=subject,
                        value=mem.content,
                        category=m_type,
                        status=PreferenceState.ACTIVE,
                        source=(
                            mem.source.value
                            if hasattr(mem.source, "value")
                            else str(mem.source)
                        ),
                        confidence=mem.confidence,
                        source_memory_ids=[mem.memory_id],
                        updated_at=mem.updated_at,
                    )
                # Projects
                elif m_type == MemoryType.PROJECT.value:
                    meta = mem.metadata or {}
                    projects[subject] = UserProjectItem(
                        project_id=mem.memory_id,
                        name=subject,
                        description=meta.get("description", ""),
                        local_path=mem.content,
                        status=ProjectStatus.ACTIVE,
                        aliases=meta.get("aliases", []),
                        related_applications=meta.get("related_applications", []),
                        created_at=mem.created_at,
                        updated_at=mem.updated_at,
                        source_memory_ids=[mem.memory_id],
                    )
                # Contacts
                elif m_type == MemoryType.CONTACT.value:
                    meta = mem.metadata or {}
                    contacts[subject] = UserContactItem(
                        contact_id=mem.memory_id,
                        name=subject,
                        aliases=meta.get("aliases", []),
                        relationship=mem.content,
                        organization=meta.get("organization", ""),
                        notes=meta.get("notes", ""),
                        created_at=mem.created_at,
                        updated_at=mem.updated_at,
                        source_memory_ids=[mem.memory_id],
                    )
                # Workflows
                elif m_type == MemoryType.WORKFLOW.value:
                    meta = mem.metadata or {}
                    steps_list = meta.get("steps")
                    if not steps_list and mem.content:
                        steps_list = [
                            s.strip() for s in mem.content.split(";") if s.strip()
                        ]

                    workflows[subject] = UserWorkflowItem(
                        workflow_id=mem.memory_id,
                        name=subject,
                        description=meta.get("description", ""),
                        steps=steps_list or [],
                        status=WorkflowStatus.ACTIVE,
                        created_at=mem.created_at,
                        updated_at=mem.updated_at,
                        source_memory_ids=[mem.memory_id],
                    )
                # Interaction Patterns
                elif m_type.upper() in (
                    "INTERACTION_PATTERN",
                    "PATTERN",
                    "INTERACTION",
                ):
                    patterns[subject] = UserInteractionPatternItem(
                        pattern_key=subject,
                        pattern_value=mem.content,
                        confidence=mem.confidence,
                        source_memory_ids=[mem.memory_id],
                        updated_at=mem.updated_at,
                    )

            return UserProfile(
                identity=identity,
                preferences=preferences,
                projects=projects,
                contacts=contacts,
                workflows=workflows,
                interaction_patterns=patterns,
                last_updated_at=time.time(),
            )

    def create_snapshot(self) -> UserProfileSnapshot:
        """Build a read-only, token-budgeted prompt snapshot of user context."""
        profile = self.build_profile()

        pref_summary = {k: v.value for k, v in profile.preferences.items()}
        proj_list = [
            f"{p.name} ({p.local_path})" if p.local_path else p.name
            for p in profile.projects.values()
        ]
        contact_list = [
            f"{c.name} ({c.relationship})" if c.relationship else c.name
            for c in profile.contacts.values()
        ]
        workflow_list = list(profile.workflows.keys())
        comm_style = pref_summary.get("communication_style", "concise")

        lines = ["=== USER PROFILE SNAPSHOT ==="]
        if profile.identity.preferred_name:
            lines.append(f"Preferred Name: {profile.identity.preferred_name}")

        if pref_summary:
            lines.append("Preferences:")
            for k, v in pref_summary.items():
                lines.append(f"  - {k}: {v}")

        if proj_list:
            lines.append("Active Projects:")
            for p in proj_list:
                lines.append(f"  - {p}")

        if profile.contacts:
            lines.append("Known Contacts:")
            for c in profile.contacts.values():
                lines.append(f"  - {c.name}: {c.relationship}")

        if workflow_list:
            lines.append("Workflows:")
            for w in workflow_list:
                lines.append(f"  - {w}")

        formatted = "\n".join(lines)
        if len(formatted) > self.config.max_snapshot_chars:
            formatted = formatted[: self.config.max_snapshot_chars] + "... [TRUNCATED]"

        return UserProfileSnapshot(
            preferred_name=profile.identity.preferred_name,
            preferences_summary=pref_summary,
            active_projects=proj_list,
            known_contacts=[c.name for c in profile.contacts.values()],
            active_workflows=workflow_list,
            interaction_style=comm_style,
            formatted_snapshot=formatted,
            timestamp=time.time(),
        )

    # --- PREFERENCES ---

    def set_preference(
        self, key: str, value: str, source: str = "USER_EXPLICIT"
    ) -> bool:
        """Store or update a structured user preference."""
        res = self.long_term_service.remember(
            subject=key,
            content=value,
            memory_type=MemoryType.PREFERENCE,
            source=(
                MemorySource.USER_EXPLICIT
                if source == "USER_EXPLICIT"
                else MemorySource.DERIVED
            ),
        )
        return res.status == "SUCCESS"

    def get_preference(self, key: str) -> str | None:
        """Retrieve current value of active preference."""
        return self.long_term_service.find_preference(key.strip().lower())

    def remove_preference(self, key: str) -> bool:
        """Deactivate preference from persistent memory."""
        res = self.long_term_service.forget(subject=key.strip().lower())
        return res.status == "SUCCESS"

    # --- PROJECTS ---

    def add_project(
        self,
        name: str,
        local_path: str = "",
        description: str = "",
        aliases: list[str] | None = None,
    ) -> bool:
        """Persist a user project profile record."""
        meta = {"description": description, "aliases": aliases or []}
        res = self.long_term_service.remember(
            subject=name,
            content=local_path,
            memory_type=MemoryType.PROJECT,
            metadata=meta,
        )
        return res.status == "SUCCESS"

    def get_project(self, name: str) -> UserProjectItem | None:
        """Fetch project profile by name (case-insensitive)."""
        profile = self.build_profile()
        target = name.strip().lower()
        for k, v in profile.projects.items():
            if k.lower() == target:
                return v
        return None

    def list_projects(self) -> list[UserProjectItem]:
        """List all active persistent project profiles."""
        profile = self.build_profile()
        return list(profile.projects.values())

    # --- CONTACTS ---

    def add_contact(
        self,
        name: str,
        relationship: str = "",
        organization: str = "",
        notes: str = "",
    ) -> bool:
        """Persist an explicitly remembered contact record."""
        meta = {"organization": organization, "notes": notes}
        res = self.long_term_service.remember(
            subject=name,
            content=relationship,
            memory_type=MemoryType.CONTACT,
            metadata=meta,
        )
        return res.status == "SUCCESS"

    def get_contact(self, name: str) -> UserContactItem | None:
        """Fetch contact profile by name (case-insensitive)."""
        profile = self.build_profile()
        target = name.strip().lower()
        for k, v in profile.contacts.items():
            if k.lower() == target:
                return v
        return None

    def list_contacts(self) -> list[UserContactItem]:
        """List all explicitly remembered contact profiles."""
        profile = self.build_profile()
        return list(profile.contacts.values())

    # --- WORKFLOWS ---

    def add_workflow(self, name: str, steps: list[str], description: str = "") -> bool:
        """Persist a recurring workflow definition."""
        content_str = "; ".join(steps)
        meta = {"description": description, "steps": steps}
        res = self.long_term_service.remember(
            subject=name,
            content=content_str,
            memory_type=MemoryType.WORKFLOW,
            metadata=meta,
        )
        return res.status == "SUCCESS"

    def get_workflow(self, name: str) -> UserWorkflowItem | None:
        """Fetch workflow profile by name (case-insensitive)."""
        profile = self.build_profile()
        target = name.strip().lower()
        for k, v in profile.workflows.items():
            if k.lower() == target:
                return v
        return None

    def list_workflows(self) -> list[UserWorkflowItem]:
        """List all active persistent workflow profiles."""
        profile = self.build_profile()
        return list(profile.workflows.values())

    # --- IDENTITY ---

    def set_preferred_name(self, name: str) -> bool:
        """Set user's preferred name."""
        res = self.long_term_service.remember(
            subject="preferred_name",
            content=name,
            memory_type=MemoryType.USER_PREFERENCE,
        )
        return res.status == "SUCCESS"

    def get_identity(self) -> UserIdentity:
        """Return user identity dataclass."""
        profile = self.build_profile()
        return profile.identity
