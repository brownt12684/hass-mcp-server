"""Test config flow for MCP Server integration."""

from unittest.mock import Mock, patch

from homeassistant import data_entry_flow

from custom_components.mcp_server_http_transport.config_flow import (
    MCPServerConfigFlow,
    MCPServerOptionsFlowHandler,
)
from custom_components.mcp_server_http_transport.const import (
    CONF_CONNECTION_MODE,
    MODE_LOCAL_SSE,
    MODE_LOCAL_STREAMABLE_HTTP,
    MODE_REMOTE_HTTP_OIDC,
)


class TestMCPServerConfigFlow:
    """Test the MCP Server config flow."""

    async def test_user_flow_shows_menu(self):
        """Test user flow shows an explicit mode-selection menu."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=["oidc_provider"])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == data_entry_flow.FlowResultType.MENU
        assert result["step_id"] == "user"
        assert "remote_http_oidc" in result["menu_options"]
        assert "local_sse" in result["menu_options"]
        assert "local_streamable_http" in result["menu_options"]

    async def test_remote_http_oidc_flow_creates_entry(self):
        """Test remote OIDC flow creates the correct entry."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=["oidc_provider"])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_remote_http_oidc(user_input={})

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "MCP Server"
        assert result["data"] == {CONF_CONNECTION_MODE: MODE_REMOTE_HTTP_OIDC}

    async def test_remote_http_oidc_flow_shows_form_when_no_input(self):
        """Test remote OIDC flow shows a confirmation form."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=["oidc_provider"])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_remote_http_oidc(user_input=None)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "remote_http_oidc"
        assert result["data_schema"] is not None

    async def test_remote_http_oidc_flow_aborts_when_oidc_provider_missing(self):
        """Test remote OIDC flow aborts when OIDC provider is not installed."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=[])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_remote_http_oidc(user_input=None)

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "oidc_provider_required"

    async def test_local_sse_flow_creates_entry_without_oidc(self):
        """Test local SSE mode does not require the OIDC provider."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=[])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_local_sse(user_input={})

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_CONNECTION_MODE: MODE_LOCAL_SSE}

    async def test_local_sse_flow_shows_form(self):
        """Test local SSE mode shows a confirmation form."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=[])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_local_sse(user_input=None)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "local_sse"
        assert result["data_schema"].schema == {}

    async def test_local_streamable_http_flow_creates_entry_without_oidc(self):
        """Test local Streamable HTTP mode does not require the OIDC provider."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=[])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_local_streamable_http(user_input={})

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_CONNECTION_MODE: MODE_LOCAL_STREAMABLE_HTTP}

    async def test_local_streamable_http_flow_shows_form(self):
        """Test local Streamable HTTP mode shows a confirmation form."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=[])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_local_streamable_http(user_input=None)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "local_streamable_http"
        assert result["data_schema"].schema == {}

    async def test_version_is_set(self):
        """Test config flow version is set."""
        flow = MCPServerConfigFlow()
        assert flow.VERSION == 1

    def test_async_get_options_flow_returns_options_flow(self):
        """Test async_get_options_flow returns options flow instance."""
        with patch.object(MCPServerOptionsFlowHandler, "__init__", return_value=None):
            mock_config_entry = Mock()
            options_flow = MCPServerConfigFlow.async_get_options_flow(mock_config_entry)

            assert isinstance(options_flow, MCPServerOptionsFlowHandler)

    async def test_remote_http_oidc_form_has_empty_schema(self):
        """Test remote OIDC form has empty data schema."""
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_domains = Mock(return_value=["oidc_provider"])

        flow = MCPServerConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_remote_http_oidc(user_input=None)

        assert result["data_schema"].schema == {}


class TestMCPServerOptionsFlow:
    """Test the MCP Server options flow."""

    async def test_init_step_shows_form(self):
        """Test init step shows form."""
        mock_config_entry = Mock()

        flow = MCPServerOptionsFlowHandler.__new__(MCPServerOptionsFlowHandler)
        flow._config_entry = mock_config_entry

        result = await flow.async_step_init(user_input=None)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_init_step_with_user_input_creates_entry(self):
        """Test init step with user input creates entry."""
        mock_config_entry = Mock()

        flow = MCPServerOptionsFlowHandler.__new__(MCPServerOptionsFlowHandler)
        flow._config_entry = mock_config_entry

        result = await flow.async_step_init(user_input={})

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == ""
        assert result["data"] == {}

    async def test_init_step_form_has_empty_schema(self):
        """Test init step form has empty data schema."""
        mock_config_entry = Mock()

        flow = MCPServerOptionsFlowHandler.__new__(MCPServerOptionsFlowHandler)
        flow._config_entry = mock_config_entry

        result = await flow.async_step_init(user_input=None)

        # Verify the schema is empty (no user input required)
        assert result["data_schema"].schema == {}

    def test_options_flow_stores_config_entry(self):
        """Test options flow stores config entry."""
        mock_config_entry = Mock()

        # Use internal attribute to avoid deprecated setter
        flow = MCPServerOptionsFlowHandler.__new__(MCPServerOptionsFlowHandler)
        flow._config_entry = mock_config_entry

        assert flow.config_entry == mock_config_entry
