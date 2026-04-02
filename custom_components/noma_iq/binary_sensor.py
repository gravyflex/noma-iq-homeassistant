from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import NomaIqEntity


class NomaIqBinarySensor(NomaIqEntity, BinarySensorEntity):
    _attr_name = None

    def __init__(self, coordinator, key: str, sensor_name: str) -> None:
        super().__init__(coordinator, key)
        self._property_name = self.find_alias(key)
        self._attr_translation_key = key
        self._sensor_name = sensor_name

    @property
    def available(self) -> bool:
        return super().available and self._property_name is not None

    @property
    def is_on(self):
        return self._as_bool(self._client.get_property_value(self.device, self._property_name))


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    entities = []
    for key, label in [
        ("water_bucket_full", "Water Bucket Full"),
        ("filter_clean_alarm", "Filter Clean Alarm"),
    ]:
        entity = NomaIqBinarySensor(coordinator, key, label)
        if entity.available:
            entities.append(entity)
    async_add_entities(entities)

