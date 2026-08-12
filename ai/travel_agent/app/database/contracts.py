from __future__ import annotations

from typing import Protocol

from app.domain.models import PersistedPlanState, UserPreferences


class UserPreferenceRepository(Protocol):
    """长期旅行偏好的读取与保存契约。"""
    async def get_by_user_id(self, user_id: str) -> UserPreferences:
        """Load long-term travel preferences from MySQL."""

    async def save(self, user_id: str, preferences: UserPreferences) -> None:
        """Persist a reviewed long-term preference update."""


class PlanRepository(Protocol):
    """已校验行程的当前版本读取与不可变版本追加契约。"""
    async def get_current(
        self,
        user_id: str,
        conversation_id: str,
    ) -> PersistedPlanState | None:
        """Load the latest valid plan for the conversation."""

    async def save_new_version(
        self,
        user_id: str,
        conversation_id: str,
        plan_state: PersistedPlanState,
    ) -> PersistedPlanState:
        """Atomically persist a validated immutable plan version."""
