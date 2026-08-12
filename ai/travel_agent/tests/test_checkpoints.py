import logging

from app.domain.models import NextAction, UserPreferences
from app.memory.checkpoints import InMemoryCheckpointBackend


def test_in_memory_checkpoint_allows_domain_models(caplog) -> None:
    saver = InMemoryCheckpointBackend().create()
    payload = {
        "next_action": NextAction.ASK_USER,
        "preferences": UserPreferences(liked_tags=["美食"]),
    }

    encoded = saver.serde.dumps_typed(payload)
    with caplog.at_level(logging.WARNING, logger="langgraph.checkpoint.serde.jsonplus"):
        restored = saver.serde.loads_typed(encoded)

    assert restored == payload
    assert "Deserializing unregistered type" not in caplog.text
    assert "Blocked deserialization" not in caplog.text
