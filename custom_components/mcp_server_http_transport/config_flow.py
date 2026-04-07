"""Config flow for MCP Server."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_CONNECTION_MODE, DOMAIN, MODE_LOCAL_SSE, MODE_REMOTE_HTTP_OIDC

_LOGGER = logging.getLogger(__name__)


class MCPServerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MCP Server."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            connection_mode = user_input[CONF_CONNECTION_MODE]
            if (
                connection_mode == MODE_REMOTE_HTTP_OIDC
                and "oidc_provider" not in self.hass.config_entries.async_domains()
            ):
                return self.async_abort(
                    reason="oidc_provider_required",
                    description_placeholders={
                        "oidc_provider_url": "https://github.com/ganhammar/hass-oidc-provider"
                    },
                )
            return self.async_create_entry(title="MCP Server", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CONNECTION_MODE, default=MODE_REMOTE_HTTP_OIDC
                    ): vol.In(
                        {
                            MODE_REMOTE_HTTP_OIDC: "Remote HTTP + OIDC (Claude/Web)",
                            MODE_LOCAL_SSE: "Local SSE (LM Studio/Desktop MCP clients)",
                        }
                    )
                }
            ),
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
