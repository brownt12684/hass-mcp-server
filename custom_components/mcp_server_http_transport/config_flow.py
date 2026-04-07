"""Config flow for MCP Server."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_CONNECTION_MODE, DOMAIN, MODE_LOCAL_SSE, MODE_REMOTE_HTTP_OIDC


class MCPServerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MCP Server."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Choose the connection mode."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["remote_http_oidc", "local_sse"],
        )

    async def async_step_remote_http_oidc(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Configure the remote HTTP + OIDC mode."""
        if "oidc_provider" not in self.hass.config_entries.async_domains():
            return self.async_abort(
                reason="oidc_provider_required",
                description_placeholders={
                    "oidc_provider_url": "https://github.com/ganhammar/hass-oidc-provider"
                },
            )

        if user_input is not None:
            return self.async_create_entry(
                title="MCP Server",
                data={CONF_CONNECTION_MODE: MODE_REMOTE_HTTP_OIDC},
            )

        return self.async_show_form(
            step_id="remote_http_oidc",
            data_schema=vol.Schema({}),
        )

    async def async_step_local_sse(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Configure the local SSE mode."""
        if user_input is not None:
            return self.async_create_entry(
                title="MCP Server",
                data={CONF_CONNECTION_MODE: MODE_LOCAL_SSE},
            )

        return self.async_show_form(
            step_id="local_sse",
            data_schema=vol.Schema({}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return MCPServerOptionsFlowHandler()


class MCPServerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle MCP Server options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
