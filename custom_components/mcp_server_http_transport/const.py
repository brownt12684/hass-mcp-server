"""Constants for the MCP Server integration."""

DOMAIN = "mcp_server_http_transport"

# MCP Server configuration
DEFAULT_PORT = 8080
DEFAULT_HOST = "0.0.0.0"

# Config entry keys
CONF_CONNECTION_MODE = "connection_mode"

# Connection modes
MODE_REMOTE_HTTP_OIDC = "remote_http_oidc"
MODE_LOCAL_SSE = "local_sse"

# HTTP endpoints
REMOTE_MCP_PATH = "/api/mcp"
LOCAL_SSE_PATH = "/api/mcp/sse"
LOCAL_SSE_MESSAGE_PATH = "/api/mcp/sse/messages/{session_id}"
