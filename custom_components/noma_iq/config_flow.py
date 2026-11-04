from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .ayla import NomaIqAuthError, NomaIqClient, NomaIqConnectionError
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

    async def _async_validate(self, username: str, password: str):
        """Return (devices, errors) for a credential pair."""
        client = NomaIqClient(username, password, async_get_clientsession(self.hass))
        try:
            devices = await client.async_list_devices()
        except NomaIqAuthError:
            return None, {"base": "invalid_auth"}
        except NomaIqConnectionError as err:
            _LOGGER.debug("NOMA iQ connection error: %s", err)
            return None, {"base": "cannot_connect"}
        except Exception:  # noqa: BLE001 - never leak a traceback into the flow
            _LOGGER.exception("Unexpected error talking to NOMA iQ")
            return None, {"base": "unknown"}
        return devices, {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            devices, errors = await self._async_validate(self._username, self._password)
            if devices is not None:
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

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        """Start reauthentication after the coordinator rejected the credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Ask for a new password and reload the entry once it is accepted."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            username = entry.data[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            devices, errors = await self._async_validate(username, password)
            if devices is not None:
                if not any(device.dsn == entry.data[CONF_DSN] for device in devices):
                    errors["base"] = "unknown_device"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_PASSWORD: password},
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_USERNAME: entry.data[CONF_USERNAME]},
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry):
        return NomaIqOptionsFlow()


class NomaIqOptionsFlow(OptionsFlow):
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
