from __future__ import annotations

from redis import Redis
from redis.sentinel import Sentinel


def create_redis_client(
    redis_url: str,
    *,
    sentinel_hosts: tuple[tuple[str, int], ...] = (),
    sentinel_master: str = "oneclick-trip-master",
    sentinel_password: str | None = None,
    decode_responses: bool = False,
) -> Redis:
    """Create a direct Redis client locally or a Sentinel-discovered master client."""
    if not sentinel_hosts:
        return Redis.from_url(redis_url, decode_responses=decode_responses)

    direct = Redis.from_url(redis_url)
    connection = direct.connection_pool.connection_kwargs
    password = connection.get("password")
    db = int(connection.get("db", 0))
    direct.close()
    sentinel = Sentinel(
        list(sentinel_hosts),
        socket_connect_timeout=2,
        socket_timeout=2,
        sentinel_kwargs={"password": sentinel_password} if sentinel_password else None,
    )
    return sentinel.master_for(
        sentinel_master,
        password=password,
        db=db,
        decode_responses=decode_responses,
        socket_connect_timeout=2,
        socket_timeout=5,
        retry_on_timeout=True,
    )


def parse_sentinel_hosts(raw: str | None) -> tuple[tuple[str, int], ...]:
    if not raw:
        return ()
    endpoints: list[tuple[str, int]] = []
    for item in raw.split(","):
        host, separator, port = item.strip().rpartition(":")
        if not separator or not host:
            raise ValueError(f"Invalid Redis Sentinel endpoint: {item!r}")
        endpoints.append((host, int(port)))
    return tuple(endpoints)
