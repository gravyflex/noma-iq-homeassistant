from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientSession
from ayla_iot_unofficial.ayla_iot_unofficial import AylaApi

try:
    from .const import DEHUM_OEM_MODEL, NOMA_APP_ID, NOMA_APP_SECRET
except ImportError:  # standalone CLI import path
    from const import DEHUM_OEM_MODEL, NOMA_APP_ID, NOMA_APP_SECRET

_LOGGER = logging.getLogger(__name__)


class NomaIqError(Exception):
    """Base integration error."""


class NomaIqAuthError(NomaIqError):
    """Authentication failed."""


class NomaIqDeviceNotFoundError(NomaIqError):
    """Configured device is not present."""


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
    """Thin wrapper around the Ayla API specialized for the NOMA iQ app tenant."""

    def __init__(self, username: str, password: str, session: ClientSession) -> None:
        self._api = AylaApi(
            username=username,
            password=password,
            app_id=NOMA_APP_ID,
            app_secret=NOMA_APP_SECRET,
            websession=session,
        )

    async def async_login(self) -> None:
        try:
            await self._api.async_sign_in()
        except Exception as err:  # library-specific exceptions are not stable
            raise NomaIqAuthError(str(err)) from err

    async def async_list_devices(self) -> list[NomaDeviceSummary]:
        await self.async_login()
        devices = await self._api.async_list_devices()
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
        await self.async_login()
        devices = await self._api.async_get_devices(update=False)
        for device in devices:
            if device.serial_number == dsn:
                await device.async_update()
                return device
        raise NomaIqDeviceNotFoundError(dsn)

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

    @staticmethod
    async def async_set_property_value(device, property_name: str, value: Any) -> None:
        value = NomaIqClient._coerce_property_value(device, property_name, value)
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
        async with await device.ayla_api.async_request(
            "post",
            endpoint,
            json=payload,
        ) as resp:
            try:
                resp_data = await resp.json()
            except Exception:
                resp_data = None

        if property_name in device.properties_full:
            device.properties_full[property_name]["value"] = value
        if isinstance(resp_data, list) and resp_data:
            datapoint = resp_data[0].get("datapoint")
            if isinstance(datapoint, dict) and property_name in device.properties_full:
                device.properties_full[property_name].update(datapoint)
        await device.async_update([property_name])
