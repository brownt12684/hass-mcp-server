"""Test constants."""


def test_constants():
    """Test constants are defined correctly."""
    from custom_components.mcp_server_http_transport.const import (
        CONF_CONNECTION_MODE,
        DEFAULT_HOST,
        DEFAULT_PORT,
        DOMAIN,
        LOCAL_SSE_MESSAGE_PATH,
        LOCAL_SSE_PATH,
        MODE_LOCAL_SSE,
        MODE_REMOTE_HTTP_OIDC,
        REMOTE_MCP_PATH,
    )

    assert DOMAIN == "mcp_server_http_transport"
    assert DEFAULT_PORT == 8080
    assert DEFAULT_HOST == "0.0.0.0"
    assert CONF_CONNECTION_MODE == "connection_mode"
    assert MODE_REMOTE_HTTP_OIDC == "remote_http_oidc"
    assert MODE_LOCAL_SSE == "local_sse"
    assert REMOTE_MCP_PATH == "/api/mcp"
    assert LOCAL_SSE_PATH == "/api/mcp/sse"
    assert LOCAL_SSE_MESSAGE_PATH == "/api/mcp/sse/messages/{session_id}"
