from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE

from .entity import NomaIqEntity


class NomaIqHumiditySensor(NomaIqEntity, SensorEntity):
    _attr_translation_key = "current_humidity"
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


class NomaIqWaterBucketStatusSensor(NomaIqEntity, SensorEntity):
    _attr_translation_key = "water_bucket_status"
    _attr_icon = "mdi:bucket"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "water_bucket_status")
        self._property_name = self.find_alias("water_bucket_full")

    @property
    def available(self) -> bool:
        return super().available and self._property_name is not None

    @property
    def native_value(self):
        value = self._client.get_property_value(self.device, self._property_name)
        state = self._as_bool(value)
        if state is None:
            return None
        return "Full" if state else "OK"


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    entities = []
    for entity in (
        NomaIqHumiditySensor(coordinator),
        NomaIqWaterBucketStatusSensor(coordinator),
    ):
        if entity.available:
            entities.append(entity)
    async_add_entities(entities)
