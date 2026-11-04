from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession
from ayla_iot_unofficial.ayla_iot_unofficial import AylaApi
from ayla_iot_unofficial.exc import AylaAuthError, AylaAuthExpiringError, AylaNotAuthedError

try:
    from .const import DEHUM_OEM_MODEL, NOMA_APP_ID, NOMA_APP_SECRET
except ImportError:  # standalone CLI import path
    from const import DEHUM_OEM_MODEL, NOMA_APP_ID, NOMA_APP_SECRET

_LOGGER = logging.getLogger(__name__)


class NomaIqError(Exception):
    """Base integration error."""


class NomaIqAuthError(NomaIqError):
    """Authentication was rejected by the cloud."""


class NomaIqConnectionError(NomaIqError):
    """The cloud could not be reached."""


class NomaIqDeviceNotFoundError(NomaIqError):
    """Configured device is not present."""


# Errors raised by the Ayla library when the session is invalid or expired.
AYLA_AUTH_ERRORS = (AylaAuthError, AylaNotAuthedError, AylaAuthExpiringError)

# Errors raised while talking to the cloud that are not credential problems.
AYLA_CONNECTION_ERRORS = (ClientError, asyncio.TimeoutError)


@dataclass(slots=True)
class NomaDeviceSummary:
    dsn: str
    name: str
    oem_model: str
    product_name: str
    model: str | None
    mac: str | None
    lan_ip: str | None


def _normalize_key(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum() or ch == "_")


class NomaIqClient:
    """Thin wrapper around the Ayla API specialized for the NOMA iQ app tenant.

    The Ayla session is established lazily and then reused for every poll. It is
    only re-established when the cloud rejects the bearer token.
    """

    def __init__(self, username: str, password: str, session: ClientSession) -> None:
        self._api = AylaApi(
            username=username,
            password=password,
            app_id=NOMA_APP_ID,
            app_secret=NOMA_APP_SECRET,
            websession=session,
        )
        self._signed_in = False

    @property
    def signed_in(self) -> bool:
        """Return True while the cached Ayla session is usable."""
        return self._signed_in

    def _invalidate(self) -> None:
        self._signed_in = False

    async def async_login(self, *, force: bool = False) -> None:
        """Sign in, unless an unexpired session is already cached."""
        if self._signed_in and not force:
            return
        self._invalidate()
        try:
            await self._api.async_sign_in()
        except AylaAuthError as err:
            raise NomaIqAuthError(str(err)) from err
        except AYLA_CONNECTION_ERRORS as err:
            raise NomaIqConnectionError(str(err)) from err
        except Exception as err:  # noqa: BLE001 - library raises bare KeyError on odd payloads
            raise NomaIqError(str(err)) from err
        self._signed_in = True

    async def _async_with_session(self, call):
        """Run an API call, re-authenticating once if the token was rejected."""
        await self.async_login()
        try:
            return await call()
        except AYLA_AUTH_ERRORS:
            self._invalidate()
        except AYLA_CONNECTION_ERRORS as err:
            raise NomaIqConnectionError(str(err)) from err
        await self.async_login(force=True)
        try:
            return await call()
        except AYLA_AUTH_ERRORS as err:
            self._invalidate()
            raise NomaIqAuthError(str(err)) from err
        except AYLA_CONNECTION_ERRORS as err:
            raise NomaIqConnectionError(str(err)) from err

    async def async_list_devices(self) -> list[NomaDeviceSummary]:
        devices = await self._async_with_session(self._api.async_list_devices)
        return [
            NomaDeviceSummary(
                dsn=device["dsn"],
                name=device.get("product_name") or device["dsn"],
                oem_model=device.get("oem_model") or "",
                product_name=device.get("product_name") or "",
                model=device.get("model"),
                mac=device.get("mac"),
                lan_ip=device.get("lan_ip"),
            )
            for device in devices
        ]

    async def async_get_device(self, dsn: str):
        async def _fetch():
            for device in await self._api.async_get_devices(update=False):
                if device.serial_number == dsn:
                    await device.async_update()
                    return device
            return None

        device = await self._async_with_session(_fetch)
        if device is None:
            raise NomaIqDeviceNotFoundError(dsn)
        return device

    @staticmethod
    def property_name_map(device) -> dict[str, str]:
        return {_normalize_key(name): name for name in device.properties_full.keys()}

    @staticmethod
    def find_property(device, aliases: list[str]) -> str | None:
        names = NomaIqClient.property_name_map(device)
        for alias in aliases:
            key = _normalize_key(alias)
            if key in names:
                return names[key]
        for actual in device.properties_full.keys():
            normalized = _normalize_key(actual)
            for alias in aliases:
                alias_key = _normalize_key(alias)
                if alias_key in normalized or normalized in alias_key:
                    return actual
        return None

    @staticmethod
    def device_supports_dehumidifier(device) -> bool:
        return (getattr(device, "oem_model_number", "") or "").lower() == DEHUM_OEM_MODEL

    @staticmethod
    def get_property_value(device, property_name: str | None) -> Any:
        if not property_name:
            return None
        try:
            return device.get_property_value(property_name)
        except Exception:
            return device.properties_full.get(property_name, {}).get("value")

    @staticmethod
    def _coerce_property_value(device, property_name: str, value: Any) -> Any:
        prop = device.properties_full.get(property_name, {})
        base_type = (prop.get("base_type") or "").lower()
        if base_type == "boolean":
            return 1 if bool(value) else 0
        return value

    async def async_set_property_value(self, device, property_name: str, value: Any) -> None:
        value = self._coerce_property_value(device, property_name, value)
        _LOGGER.debug("Setting NOMA property %s=%r on %s", property_name, value, device.serial_number)

        payload = {
            "batch_datapoints": [
                {
                    "dsn": device.serial_number,
                    "name": device.properties_full.get(property_name, {}).get("name", property_name),
                    "datapoint": {"value": value},
                }
            ]
        }
        endpoint = (
            f"{device.eu_ads_url if getattr(device, 'europe', False) else device.ads_url}"
            "/apiv1/batch_datapoints.json"
        )
        async def _write():
            async with await device.ayla_api.async_request(
                "post",
                endpoint,
                json=payload,
            ) as resp:
                if resp.status == 401:
                    raise AylaAuthError("Write rejected: not authenticated")
                try:
                    return await resp.json()
                except Exception:
                    return None

        resp_data = await self._async_with_session(_write)

        if property_name in device.properties_full:
            device.properties_full[property_name]["value"] = value
        if isinstance(resp_data, list) and resp_data:
            datapoint = resp_data[0].get("datapoint")
            if isinstance(datapoint, dict) and property_name in device.properties_full:
                device.properties_full[property_name].update(datapoint)
        await device.async_update([property_name])
