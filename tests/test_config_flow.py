"""Setup-flow + reauth + entity naming smoke against a real HA instance."""

import pytest
from unittest.mock import patch
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.noma_iq.ayla import (
    NomaDeviceSummary, NomaIqAuthError, NomaIqConnectionError,
)
from custom_components.noma_iq.const import DOMAIN

pytestmark = pytest.mark.asyncio

DEV = NomaDeviceSummary(
    dsn="AC000W1", name="Water Bucket", oem_model="dehum",
    product_name="Dehumidifier", model="NOMA1", mac=None, lan_ip=None,
)
ENTRY_DATA = {
    "username": "user@example.com", "password": "old",
    CONF_USERNAME: "user@example.com", CONF_PASSWORD: "old",
    "dsn": "AC000W1", "device_name": "Water Bucket", "oem_model": "dehum",
    "product_name": "Dehumidifier",
}


class FakeClient:
    result = None
    def __init__(self, *args, **kwargs):
        pass
    async def async_list_devices(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def test_setup_flow_success(hass):
    FakeClient.result = [DEV]
    with patch("custom_components.noma_iq.config_flow.NomaIqClient", FakeClient):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "pw"},
        )
        assert result["step_id"] == "select_device"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"dsn": "AC000W1"}
        )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["dsn"] == "AC000W1"


async def test_setup_flow_auth_error(hass):
    FakeClient.result = NomaIqAuthError("bad password")
    with patch("custom_components.noma_iq.config_flow.NomaIqClient", FakeClient):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "pw"},
        )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_setup_flow_connection_error(hass):
    FakeClient.result = NomaIqConnectionError("down")
    with patch("custom_components.noma_iq.config_flow.NomaIqClient", FakeClient):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "pw"},
        )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_updates_password(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="AC000W1")
    entry.add_to_hass(hass)
    FakeClient.result = [DEV]
    with patch("custom_components.noma_iq.config_flow.NomaIqClient", FakeClient):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
            data=entry.data,
        )
        assert result["step_id"] == "reauth_confirm"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new-password"}
        )
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-password"


async def test_reauth_rejects_bad_password(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="AC000W1")
    entry.add_to_hass(hass)
    FakeClient.result = NomaIqAuthError("nope")
    with patch("custom_components.noma_iq.config_flow.NomaIqClient", FakeClient):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
            data=entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "still-wrong"}
        )
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data[CONF_PASSWORD] == "old"
