"""MCP Server for Home Assistant."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from mcp.server import Server

from .const import CONF_CONNECTION_MODE, DOMAIN, MODE_LOCAL_SSE, MODE_REMOTE_HTTP_OIDC
from .http import (
    MCPLocalMessageEndpointView,
    MCPLocalSSEView,
    MCPEndpointView,
    MCPProtectedResourceMetadataView,
    MCPSubpathProtectedResourceMetadataView,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MCP Server component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MCP Server from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    server = Server("home-assistant-mcp-server")
    hass.data[DOMAIN]["server"] = server
    hass.data[DOMAIN].setdefault("sse_sessions", {})

    connection_mode = entry.data.get(CONF_CONNECTION_MODE, MODE_REMOTE_HTTP_OIDC)
    if connection_mode == MODE_LOCAL_SSE:
        hass.http.register_view(MCPLocalSSEView(hass, server))
        hass.http.register_view(MCPLocalMessageEndpointView(hass, server))
        _LOGGER.info("MCP Server initialized in local SSE mode at /api/mcp/sse")
    else:
        hass.http.register_view(MCPProtectedResourceMetadataView())
        hass.http.register_view(MCPSubpathProtectedResourceMetadataView())
        hass.http.register_view(MCPEndpointView(hass, server))
        _LOGGER.info("MCP Server initialized in remote HTTP/OIDC mode at /api/mcp")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].clear()
    return True
