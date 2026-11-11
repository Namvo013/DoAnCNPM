from collections.abc import AsyncIterator
from typing import Any

from fastapi import HTTPException, Request, WebSocket, status


async def get_database(request: Request) -> Any:
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable")
    return database


async def get_redis(request: Request) -> AsyncIterator[Any]:
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis is unavailable")
    yield redis_client


async def get_websocket_database(websocket: WebSocket) -> Any:
    database = getattr(websocket.app.state, "database", None)
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable")
    return database


async def get_websocket_redis(websocket: WebSocket) -> AsyncIterator[Any]:
    redis_client = getattr(websocket.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis is unavailable")
    yield redis_client
