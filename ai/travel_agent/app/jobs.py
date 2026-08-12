from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Protocol

import redis
from fastapi.encoders import jsonable_encoder


TERMINAL_JOB_STATUSES = {"COMPLETED", "FAILED"}


class AgentJobStore(Protocol):
    """异步 Agent 作业存储契约，并负责同一会话的执行互斥。"""
    def create(self, job: dict[str, Any]) -> bool: ...

    def get(self, run_id: str) -> dict[str, Any] | None: ...

    def save(self, job: dict[str, Any]) -> None: ...

    def has_active(self, conversation_id: str) -> bool: ...

    def recover_interrupted(self) -> int: ...

    def close(self) -> None: ...


class InMemoryAgentJobStore:
    """开发模式使用的进程内作业存储，服务重启后数据不保留。"""
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._active: dict[str, str] = {}

    def create(self, job: dict[str, Any]) -> bool:
        conversation_id = str(job["conversation_id"])
        if self.has_active(conversation_id):
            return False
        run_id = str(job["run_id"])
        self._jobs[run_id] = deepcopy(job)
        self._active[conversation_id] = run_id
        return True

    def get(self, run_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(run_id)
        return deepcopy(job) if job is not None else None

    def save(self, job: dict[str, Any]) -> None:
        run_id = str(job["run_id"])
        copied = deepcopy(jsonable_encoder(job))
        self._jobs[run_id] = copied
        if str(copied.get("status")) in TERMINAL_JOB_STATUSES:
            conversation_id = str(copied["conversation_id"])
            if self._active.get(conversation_id) == run_id:
                self._active.pop(conversation_id, None)

    def has_active(self, conversation_id: str) -> bool:
        run_id = self._active.get(conversation_id)
        if not run_id:
            return False
        job = self._jobs.get(run_id)
        if job and str(job.get("status")) not in TERMINAL_JOB_STATUSES:
            return True
        self._active.pop(conversation_id, None)
        return False

    def close(self) -> None:
        return None

    def recover_interrupted(self) -> int:
        return 0


class RedisAgentJobStore:
    """生产模式作业存储，通过 Redis NX 锁保证单会话只有一个活跃任务。"""
    def __init__(self, redis_url: str, *, ttl_minutes: int = 1440) -> None:
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = max(ttl_minutes, 1) * 60
        self._prefix = "oneclick-trip:agent-job"

    def ping(self) -> None:
        self._redis.ping()

    def create(self, job: dict[str, Any]) -> bool:
        conversation_id = str(job["conversation_id"])
        run_id = str(job["run_id"])
        active_key = self._active_key(conversation_id)
        if not self._redis.set(active_key, run_id, ex=self._ttl_seconds, nx=True):
            if self.has_active(conversation_id):
                return False
            if not self._redis.set(active_key, run_id, ex=self._ttl_seconds, nx=True):
                return False
        self._redis.setex(self._job_key(run_id), self._ttl_seconds, self._encode(job))
        return True

    def get(self, run_id: str) -> dict[str, Any] | None:
        payload = self._redis.get(self._job_key(run_id))
        if payload is None:
            return None
        return dict(json.loads(payload))

    def save(self, job: dict[str, Any]) -> None:
        run_id = str(job["run_id"])
        conversation_id = str(job["conversation_id"])
        pipeline = self._redis.pipeline()
        pipeline.setex(self._job_key(run_id), self._ttl_seconds, self._encode(job))
        if str(job.get("status")) in TERMINAL_JOB_STATUSES:
            current = self._redis.get(self._active_key(conversation_id))
            if current == run_id:
                pipeline.delete(self._active_key(conversation_id))
        else:
            pipeline.setex(self._active_key(conversation_id), self._ttl_seconds, run_id)
        pipeline.execute()

    def has_active(self, conversation_id: str) -> bool:
        active_key = self._active_key(conversation_id)
        run_id = self._redis.get(active_key)
        if not run_id:
            return False
        job = self.get(run_id)
        if job and str(job.get("status")) not in TERMINAL_JOB_STATUSES:
            self._redis.expire(active_key, self._ttl_seconds)
            return True
        self._redis.delete(active_key)
        return False

    def close(self) -> None:
        self._redis.close()

    def recover_interrupted(self) -> int:
        """服务启动时将遗留的非终态任务标记为失败并释放会话锁。"""
        recovered = 0
        for key in self._redis.scan_iter(match=f"{self._prefix}:run:*"):
            payload = self._redis.get(key)
            if payload is None:
                continue
            job = dict(json.loads(payload))
            if str(job.get("status")) in TERMINAL_JOB_STATUSES:
                continue
            job.update(
                status="FAILED",
                stage="interrupted",
                detail="服务重启中断了本次执行，请重新发起",
                completed_at=None,
                error="Agent service restarted before this run completed",
            )
            self.save(job)
            recovered += 1
        return recovered

    def _job_key(self, run_id: str) -> str:
        return f"{self._prefix}:run:{run_id}"

    def _active_key(self, conversation_id: str) -> str:
        return f"{self._prefix}:active:{conversation_id}"

    @staticmethod
    def _encode(job: dict[str, Any]) -> str:
        return json.dumps(jsonable_encoder(job), ensure_ascii=False, separators=(",", ":"))
