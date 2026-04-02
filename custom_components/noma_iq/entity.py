from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .ayla import NomaIqClient
from .const import CONF_DEVICE_NAME, CONF_DSN, PROP_ALIASES


class NomaIqEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, suffix: str) -> None:
        super().__init__(coordinator)
        self._client = coordinator.client
        self._device_name = coordinator.entry.data[CONF_DEVICE_NAME]
        self._suffix = suffix
        self._attr_unique_id = f"{coordinator.entry.data[CONF_DSN]}_{suffix}"
        self._attr_device_info = {
            "identifiers": {("noma_iq", coordinator.entry.data[CONF_DSN])},
            "name": self._device_name,
            "manufacturer": "Canadian Tire / NOMA iQ",
            "model": getattr(coordinator.device, "device_model_number", None),
            "serial_number": coordinator.entry.data[CONF_DSN],
        }

    @property
    def device(self):
        return self.coordinator.device

    def find_alias(self, key: str) -> str | None:
        return self._client.find_property(self.device, PROP_ALIASES[key])

    @staticmethod
    def _as_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "on", "yes", "open", "full"}
        return None

