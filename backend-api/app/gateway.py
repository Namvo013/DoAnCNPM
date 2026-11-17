import asyncio
import hmac
import logging
from urllib.parse import urlsplit, urlunsplit

import httpx
import websockets
from websockets.legacy.client import connect as websocket_connect
from fastapi import APIRouter, HTTPException, Request, WebSocket
from starlette.responses import Response

from app.config import Settings

logger = logging.getLogger(__name__)
HOP_BY_HOP_HEADERS = {
    b"connection",
    b"content-encoding",
    b"content-length",
    b"keep-alive",
    b"proxy-authenticate",
    b"proxy-authorization",
    b"te",
    b"trailer",
    b"transfer-encoding",
    b"upgrade",
}


def service_for_path(path: str) -> str | None:
    if path == "auth" or path.startswith("auth/"):
        return "auth"
    if path == "admin/admins" or path.startswith("admin/admins/"):
        return "auth"
    if (
        path == "pois"
        or path.startswith("pois/")
        or path == "admin/pois"
        or path.startswith("admin/pois/")
        or path == "admin/images"
        or path.startswith("admin/images/")
        or path == "admin/translations"
        or path.startswith("admin/translations/")
    ):
        return "poi"
    if path == "admin/heatmap" or path.startswith("admin/heatmap/"):
        return "presence"
    return None


def _service_url(settings: Settings, service: str) -> str:
    value = {
        "auth": settings.auth_service_url,
        "poi": settings.poi_service_url,
        "presence": settings.presence_service_url,
    }[service].rstrip("/")
    if "://" in value:
        return value
    scheme = "http" if value.startswith(("localhost:", "127.0.0.1:", "auth-service:", "poi-service:", "presence-service:")) else "https"
    return f"{scheme}://{value}"


def _internal_headers(settings: Settings) -> dict[str, str]:
    if not settings.internal_service_token:
        raise HTTPException(status_code=503, detail="Internal service authentication is not configured")
    return {"X-Internal-Service-Token": settings.internal_service_token}


def _proxy_response(upstream: httpx.Response, service_url: str) -> Response:
    response = Response(content=upstream.content, status_code=upstream.status_code)
    service_origin = urlsplit(service_url)
    forwarded_headers: list[tuple[bytes, bytes]] = []
    for key, value in upstream.headers.raw:
        if key.lower() in HOP_BY_HOP_HEADERS:
            continue
        if key.lower() == b"location":
            location = urlsplit(value.decode("latin-1"))
            if location.netloc == service_origin.netloc and location.scheme:
                value = urlunsplit(("", "", location.path, location.query, location.fragment)).encode("latin-1")
        forwarded_headers.append((key.lower(), value))
    forwarded_headers.append((b"content-length", str(len(upstream.content)).encode("ascii")))
    response.raw_headers = forwarded_headers
    return response


def create_gateway_router(settings: Settings) -> APIRouter:
    gateway = APIRouter()

    @gateway.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def proxy_api(path: str, request: Request) -> Response:
        service = service_for_path(path)
        if service is None:
            raise HTTPException(status_code=404, detail="Not found")
        base_url = _service_url(settings, service)
        url = f"{base_url}/api/{path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"
        headers = [
            (key.decode("latin-1"), value.decode("latin-1"))
            for key, value in request.headers.raw
            if key.lower() not in HOP_BY_HOP_HEADERS
            and key.lower() not in {b"host", b"x-internal-service-token"}
        ]
        headers.extend(_internal_headers(settings).items())
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                upstream = await client.request(
                    request.method,
                    url,
                    headers=headers,
                    content=await request.body(),
                )
        except httpx.HTTPError as error:
            logger.exception("Gateway request to %s service failed", service)
            raise HTTPException(
                status_code=502,
                detail=f"{service.capitalize()} service is unavailable",
            ) from error

        return _proxy_response(upstream, base_url)

    @gateway.api_route("/media/{path:path}", methods=["GET", "HEAD"])
    async def proxy_media(path: str, request: Request) -> Response:
        url = f"{_service_url(settings, 'poi')}/media/{path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"
        headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in request.headers.raw
            if key.lower() not in HOP_BY_HOP_HEADERS
            and key.lower() not in {b"host", b"x-internal-service-token"}
        }
        headers.update(_internal_headers(settings))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                upstream = await client.request(request.method, url, headers=headers)
        except httpx.HTTPError as error:
            logger.exception("Gateway request to POI media service failed")
            raise HTTPException(status_code=502, detail="POI service is unavailable") from error
        return _proxy_response(upstream, _service_url(settings, "poi"))

    @gateway.websocket("/{path:path}")
    async def proxy_websocket(websocket: WebSocket, path: str) -> None:
        if not (path.startswith("ws/") or path.startswith("api/ws/")):
            await websocket.close(code=1008, reason="Unknown WebSocket route")
            return
        token = settings.internal_service_token
        if not token:
            await websocket.close(code=1011, reason="Internal service authentication is not configured")
            return

        upstream_base = _service_url(settings, "presence")
        parsed = urlsplit(upstream_base)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        query = websocket.url.query
        upstream_url = urlunsplit(
            (scheme, parsed.netloc, f"{parsed.path.rstrip('/')}/{path}", query, "")
        )
        headers = [
            (key.decode("latin-1"), value.decode("latin-1"))
            for key, value in websocket.headers.raw
            if key.lower() in {b"cookie", b"origin", b"user-agent", b"authorization"}
        ]
        headers.append(("X-Internal-Service-Token", token))

        try:
            async with websocket_connect(
                upstream_url,
                extra_headers=headers,
                subprotocols=websocket.scope.get("subprotocols") or None,
                open_timeout=10,
                close_timeout=2,
            ) as upstream:
                await websocket.accept(subprotocol=upstream.subprotocol)

                async def client_to_service() -> None:
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            return
                        if message.get("text") is not None:
                            await upstream.send(message["text"])
                        elif message.get("bytes") is not None:
                            await upstream.send(message["bytes"])

                async def service_to_client() -> None:
                    while True:
                        message = await upstream.recv()
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)

                tasks = {
                    asyncio.create_task(client_to_service()),
                    asyncio.create_task(service_to_client()),
                }
                try:
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        exception = task.exception()
                        if exception is not None:
                            raise exception
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.close()
        except (OSError, TimeoutError, websockets.exceptions.WebSocketException) as error:
            logger.exception("Gateway WebSocket connection to Presence service failed")
            if websocket.client_state.name in {"CONNECTING", "CONNECTED"}:
                await websocket.close(code=1013, reason="Presence service is unavailable")

    return gateway


class InternalServiceAccessMiddleware:
    def __init__(self, app, token: str) -> None:
        self.app = app
        self.token = token.encode("utf-8")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/health", "/api/health"}:
            await self.app(scope, receive, send)
            return

        supplied = next(
            (value for key, value in scope.get("headers", []) if key.lower() == b"x-internal-service-token"),
            b"",
        )
        if not hmac.compare_digest(supplied, self.token):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 4403, "reason": "Internal service authentication required"})
            else:
                body = b'{"detail":"Internal service authentication required"}'
                await send(
                    {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
                    }
                )
                await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
