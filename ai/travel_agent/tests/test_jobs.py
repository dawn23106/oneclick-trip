from app.jobs import InMemoryAgentJobStore


def _job(run_id: str = "run-1", status: str = "QUEUED") -> dict:
    return {
        "run_id": run_id,
        "conversation_id": "conversation-1",
        "user_id": "1",
        "status": status,
        "result": None,
    }


def test_in_memory_job_store_enforces_one_active_run_per_conversation() -> None:
    store = InMemoryAgentJobStore()
    assert store.create(_job()) is True
    assert store.create(_job("run-2")) is False
    assert store.has_active("conversation-1") is True


def test_terminal_job_remains_queryable_and_releases_conversation() -> None:
    store = InMemoryAgentJobStore()
    job = _job()
    store.create(job)
    job.update(status="COMPLETED", result={"plan_saved": True})
    store.save(job)

    assert store.has_active("conversation-1") is False
    assert store.get("run-1")["result"] == {"plan_saved": True}
    assert store.create(_job("run-2")) is True
