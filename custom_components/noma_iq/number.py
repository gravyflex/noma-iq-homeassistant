from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE

from .entity import NomaIqEntity


class NomaIqTargetHumidityNumber(NomaIqEntity, NumberEntity):
    _attr_name = "Target Humidity"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 35
    _attr_native_max_value = 85
    _attr_native_step = 1
    _attr_mode = "slider"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "target_humidity")
        self._property_name = self.find_alias("target_humidity")

    @property
    def available(self) -> bool:
        return super().available and self.device is not None and self._property_name is not None

    @property
    def native_value(self):
        value = self._client.get_property_value(self.device, self._property_name)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self._client.async_set_property_value(self.device, self._property_name, int(value))
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    entity = NomaIqTargetHumidityNumber(coordinator)
    if entity.device is not None and entity._property_name is not None:
        async_add_entities([entity])
