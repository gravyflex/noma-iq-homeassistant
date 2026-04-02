from __future__ import annotations

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)

from .entity import NomaIqEntity


class NomaIqDehumidifierEntity(NomaIqEntity, HumidifierEntity):
    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER
    _attr_name = None
    _attr_supported_features = HumidifierEntityFeature(0)
    _attr_min_humidity = 35
    _attr_max_humidity = 85
    _attr_target_humidity_step = 1

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "dehumidifier")
        self._power = self.find_alias("power")
        self._target = self.find_alias("target_humidity")
        self._current = self.find_alias("current_humidity")

    @property
    def available(self) -> bool:
        return super().available and self.device is not None and self._power is not None

    @property
    def is_on(self):
        return self._as_bool(self._client.get_property_value(self.device, self._power))

    @property
    def current_humidity(self):
        value = self._client.get_property_value(self.device, self._current)
        return int(value) if value is not None else None

    @property
    def target_humidity(self):
        value = self._client.get_property_value(self.device, self._target)
        return int(value) if value is not None else None

    async def async_turn_on(self, **kwargs):
        await self._client.async_set_property_value(self.device, self._power, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._client.async_set_property_value(self.device, self._power, False)
        await self.coordinator.async_request_refresh()

    async def async_set_humidity(self, humidity: int):
        if not self._target:
            return
        await self._client.async_set_property_value(self.device, self._target, int(humidity))
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    entity = NomaIqDehumidifierEntity(coordinator)
    if entity.device is not None and entity._power is not None:
        async_add_entities([entity])
