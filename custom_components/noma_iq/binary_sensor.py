from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import NomaIqEntity

DEVICE_CLASSES: dict[str, BinarySensorDeviceClass] = {
    "water_bucket_full": BinarySensorDeviceClass.PROBLEM,
    "filter_clean_alarm": BinarySensorDeviceClass.PROBLEM,
    "humidity_sensor_fault": BinarySensorDeviceClass.PROBLEM,
}


class NomaIqBinarySensor(NomaIqEntity, BinarySensorEntity):
    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._property_name = self.find_alias(key)
        self._attr_translation_key = key
        self._attr_device_class = DEVICE_CLASSES.get(key)

    @property
    def available(self) -> bool:
        return super().available and self._property_name is not None

    @property
    def is_on(self):
        return self._as_bool(self._client.get_property_value(self.device, self._property_name))


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    entities = []
    for key in ("water_bucket_full", "filter_clean_alarm", "humidity_sensor_fault"):
        entity = NomaIqBinarySensor(coordinator, key)
        if entity.available:
            entities.append(entity)
    async_add_entities(entities)
