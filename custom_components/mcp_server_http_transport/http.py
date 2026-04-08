"""HTTP transport implementations for the MCP server."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import MutableMapping
from typing import Any
from uuid import uuid4

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from mcp.server import Server

from .completions import complete
from .const import DOMAIN, LOCAL_SSE_MESSAGE_PATH, LOCAL_SSE_PATH, REMOTE_MCP_PATH
from .prompts import get_prompt, get_prompts
from .resources import get_resources, read_resource
from .tools import call_tool, get_tool_schemas

try:
    from custom_components.oidc_provider.token_validator import get_issuer_from_request
except ImportError:  # pragma: no cover - exercised in production, mocked in tests
    get_issuer_from_request = None

_LOGGER = logging.getLogger(__name__)
SSE_KEEPALIVE_SECONDS = 15


def _request_origin(request: web.Request) -> str:
    """Return the request origin, honoring forwarded headers when present."""
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    forwarded_host = request.headers.get("X-Forwarded-Host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.url.origin())


def _get_protected_resource_metadata(base_url: str) -> dict[str, Any]:
    """Generate OAuth 2.0 Protected Resource Metadata (RFC 9728)."""
    return {
        "resource": f"{base_url}{REMOTE_MCP_PATH}",
        "authorization_servers": [f"{base_url}/oidc"],
        "bearer_methods_supported": ["header"],
        "resource_signing_alg_values_supported": ["RS256"],
        "resource_documentation": f"{base_url}{REMOTE_MCP_PATH}",
    }


def _get_sse_session_store(hass: HomeAssistant) -> MutableMapping[str, asyncio.Queue]:
    """Get the in-memory SSE session store."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    return domain_data.setdefault("sse_sessions", {})


class MCPRequestHandler:
    """Shared JSON-RPC request handling for all MCP transports."""

    def __init__(self, hass: HomeAssistant, server: Server) -> None:
        """Initialize the request handler."""
        self.hass = hass
        self.server = server

    async def handle_jsonrpc(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle a JSON-RPC message."""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                    },
                    "serverInfo": {
                        "name": "home-assistant-mcp-server",
                        "version": "0.1.0",
                    },
                },
                "id": msg_id,
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {"tools": get_tool_schemas()},
                "id": msg_id,
            }

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = await call_tool(self.hass, name, arguments)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": msg_id,
            }

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "result": get_resources(),
                "id": msg_id,
            }

        if method == "resources/read":
            uri = params.get("uri", "")
            contents = await read_resource(self.hass, uri)
            return {
                "jsonrpc": "2.0",
                "result": {"contents": contents},
                "id": msg_id,
            }

        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "result": {"prompts": get_prompts()},
                "id": msg_id,
            }

        if method == "prompts/get":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await get_prompt(self.hass, name, arguments)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": msg_id,
            }

        if method == "completion/complete":
            ref = params.get("ref", {})
            argument = params.get("argument", {})
            result = await complete(self.hass, ref, argument)
            return {
                "jsonrpc": "2.0",
                "result": {"completion": result},
                "id": msg_id,
            }

        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": msg_id,
            }

        return None


class MCPProtectedResourceMetadataView(HomeAssistantView):
    """OAuth 2.0 Protected Resource Metadata endpoint (RFC 9728) at root."""

    url = "/.well-known/oauth-protected-resource"
    name = "api:mcp:metadata:root"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return protected resource metadata."""
        base_url = (
            get_issuer_from_request(request) if get_issuer_from_request else _request_origin(request)
        )
        return web.json_response(_get_protected_resource_metadata(base_url))


class MCPSubpathProtectedResourceMetadataView(HomeAssistantView):
    """OAuth 2.0 Protected Resource Metadata endpoint (RFC 9728) with /mcp suffix."""

    url = "/.well-known/oauth-protected-resource/api/mcp"
    name = "api:mcp:metadata:mcp"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return protected resource metadata with /mcp suffix."""
        base_url = (
            get_issuer_from_request(request) if get_issuer_from_request else _request_origin(request)
        )
        return web.json_response(_get_protected_resource_metadata(base_url))


class MCPEndpointView(HomeAssistantView):
    """Authenticated HTTP MCP endpoint."""

    url = REMOTE_MCP_PATH
    name = "api:mcp"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, server: Server) -> None:
        """Initialize the MCP endpoint."""
        self.hass = hass
        self.server = server
        self.handler = MCPRequestHandler(hass, server)

    def _validate_token(self, request: web.Request) -> dict[str, Any] | None:
        """Validate the OAuth bearer token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]

        try:
            from custom_components.oidc_provider.token_validator import (
                get_issuer_from_request as oidc_get_issuer_from_request,
                validate_access_token,
            )

            expected_issuer = oidc_get_issuer_from_request(request)
            return validate_access_token(self.hass, token, expected_issuer)
        except ImportError as err:
            _LOGGER.error("OIDC provider integration not found: %s", err)
            return None

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST requests for authenticated MCP messages."""
        token_payload = self._validate_token(request)
        if not token_payload:
            base_url = (
                get_issuer_from_request(request) if get_issuer_from_request else _request_origin(request)
            )
            resource_metadata_url = f"{base_url}/.well-known/oauth-protected-resource/api/mcp"
            www_authenticate = (
                f'Bearer realm="MCP Server", resource_metadata="{resource_metadata_url}"'
            )
            return web.json_response(
                {"error": "invalid_token", "error_description": "Invalid or missing token"},
                status=401,
                headers={"WWW-Authenticate": www_authenticate},
            )

        return await _handle_post_request(request, self.handler)


class MCPLocalEndpointView(HomeAssistantView):
    """Unauthenticated local Streamable HTTP MCP endpoint."""

    url = REMOTE_MCP_PATH
    name = "api:mcp"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, server: Server) -> None:
        """Initialize the local MCP endpoint."""
        self.hass = hass
        self.server = server
        self.handler = MCPRequestHandler(hass, server)

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST requests for local Streamable HTTP MCP messages."""
        return await _handle_post_request(request, self.handler)


class MCPLocalSSEView(HomeAssistantView):
    """Unauthenticated local SSE endpoint for MCP clients."""

    url = LOCAL_SSE_PATH
    name = "api:mcp:sse"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, server: Server) -> None:
        """Initialize the local SSE view."""
        self.hass = hass
        self.server = server

    async def get(self, request: web.Request) -> web.StreamResponse:
        """Open an SSE stream and send the message endpoint URI."""
        session_id = uuid4().hex
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        sessions = _get_sse_session_store(self.hass)
        sessions[session_id] = queue

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await response.prepare(request)

        endpoint_uri = f"{_request_origin(request)}{LOCAL_SSE_MESSAGE_PATH.format(session_id=session_id)}"
        await _write_sse_event(response, "endpoint", endpoint_uri)

        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=SSE_KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    await response.write(b": keepalive\n\n")
                    continue

                if message is None:
                    break

                await _write_sse_event(response, "message", json.dumps(message))
        except (ConnectionResetError, asyncio.CancelledError, RuntimeError):
            pass
        finally:
            sessions.pop(session_id, None)
            with contextlib.suppress(RuntimeError, ConnectionResetError):
                await response.write_eof()

        return response


class MCPLocalMessageEndpointView(HomeAssistantView):
    """Per-session message POST endpoint for the local SSE transport."""

    url = LOCAL_SSE_MESSAGE_PATH
    name = "api:mcp:sse:messages"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, server: Server) -> None:
        """Initialize the local message endpoint."""
        self.hass = hass
        self.server = server
        self.handler = MCPRequestHandler(hass, server)

    async def post(self, request: web.Request) -> web.Response:
        """Handle local SSE transport POST messages."""
        session_id = request.match_info["session_id"]
        sessions = _get_sse_session_store(self.hass)
        queue = sessions.get(session_id)
        if queue is None:
            return web.json_response(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32001, "message": "Unknown or expired SSE session"},
                    "id": None,
                },
                status=404,
            )

        try:
            body = await request.json()
            _LOGGER.debug("Received local SSE MCP request: %s", body)
            response_data = await self.handler.handle_jsonrpc(body)
            if response_data is not None:
                await queue.put(response_data)
            return web.Response(status=202)
        except Exception as err:
            _LOGGER.error("Error handling local SSE MCP request: %s", err, exc_info=True)
            error_body = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(err)}"},
                "id": body.get("id") if isinstance(body, dict) else None,
            }
            await queue.put(error_body)
            return web.Response(status=202)


async def _handle_post_request(request: web.Request, handler: MCPRequestHandler) -> web.Response:
    """Handle a standard JSON POST MCP request."""
    body: dict[str, Any] | None = None
    try:
        body = await request.json()
        _LOGGER.debug("Received MCP request: %s", body)
        response_data = await handler.handle_jsonrpc(body)
        if response_data is None:
            return web.Response(status=202)
        return web.json_response(response_data)
    except Exception as err:
        _LOGGER.error("Error handling MCP request: %s", err, exc_info=True)
        return web.json_response(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(err)}"},
                "id": body.get("id") if isinstance(body, dict) else None,
            },
            status=500,
        )


async def _write_sse_event(response: web.StreamResponse, event: str, data: str) -> None:
    """Write one SSE event to the client."""
    payload = f"event: {event}\ndata: {data}\n\n".encode("utf-8")
    await response.write(payload)
