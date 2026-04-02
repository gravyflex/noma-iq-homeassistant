from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .ayla import NomaIqClient, NomaIqAuthError
from .const import (
    CONF_DEVICE_NAME,
    CONF_DSN,
    CONF_OEM_MODEL,
    CONF_PASSWORD,
    CONF_PRODUCT_NAME,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NomaIqConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._username: str | None = None
        self._password: str | None = None
        self._devices: dict[str, dict[str, Any]] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            session = async_create_clientsession(self.hass)
            client = NomaIqClient(self._username, self._password, session)
            try:
                devices = await client.async_list_devices()
            except NomaIqAuthError:
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("NOMA iQ login/device listing failed")
                errors["base"] = "cannot_connect"
                _LOGGER.debug("NOMA iQ error: %s", err)
            else:
                self._devices = {
                    device.dsn: {
                        CONF_DEVICE_NAME: device.name,
                        CONF_DSN: device.dsn,
                        CONF_OEM_MODEL: device.oem_model,
                        CONF_PRODUCT_NAME: device.product_name,
                    }
                    for device in devices
                }
                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_device(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            dsn = user_input[CONF_DSN]
            await self.async_set_unique_id(dsn)
            self._abort_if_unique_id_configured()
            selected = self._devices[dsn]
            return self.async_create_entry(
                title=selected[CONF_DEVICE_NAME],
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_DSN: selected[CONF_DSN],
                    CONF_DEVICE_NAME: selected[CONF_DEVICE_NAME],
                    CONF_OEM_MODEL: selected[CONF_OEM_MODEL],
                    CONF_PRODUCT_NAME: selected[CONF_PRODUCT_NAME],
                },
            )

        labels = {
            dsn: f"{meta[CONF_DEVICE_NAME]} ({meta[CONF_OEM_MODEL] or meta[CONF_PRODUCT_NAME] or 'unknown'})"
            for dsn, meta in self._devices.items()
        }
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DSN): vol.In(labels)}
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry):
        return NomaIqOptionsFlow(config_entry)


class NomaIqOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): int
                }
            ),
        )

