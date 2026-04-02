from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE

from .entity import NomaIqEntity


class NomaIqHumiditySensor(NomaIqEntity, SensorEntity):
    _attr_name = "Current Humidity"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.HUMIDITY

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "current_humidity")
        self._property_name = self.find_alias("current_humidity")

    @property
    def available(self) -> bool:
        return super().available and self._property_name is not None

    @property
    def native_value(self):
        value = self._client.get_property_value(self.device, self._property_name)
        return int(value) if value is not None else None


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    entity = NomaIqHumiditySensor(coordinator)
    if entity.available:
        async_add_entities([entity])

