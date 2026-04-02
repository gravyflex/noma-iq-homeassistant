from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .entity import NomaIqEntity


class NomaIqWritableBooleanSwitch(NomaIqEntity, SwitchEntity):
    _attr_name = None

    def __init__(self, coordinator, property_name: str) -> None:
        super().__init__(coordinator, f"switch_{property_name}")
        self._property_name = property_name

    @property
    def name(self):
        return self._property_name.replace("_", " ").title()

    @property
    def is_on(self):
        return self._as_bool(self._client.get_property_value(self.device, self._property_name))

    async def async_turn_on(self, **kwargs):
        await self._client.async_set_property_value(self.device, self._property_name, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._client.async_set_property_value(self.device, self._property_name, False)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    device = coordinator.device
    if device is None:
        return

    excluded = {
        coordinator.client.find_property(device, ["target_humidity"]),
    }
    entities = []
    for property_name, meta in device.properties_full.items():
        if property_name in excluded:
            continue
        if meta.get("read_only"):
            continue
        if meta.get("base_type") != "boolean":
            continue
        entities.append(NomaIqWritableBooleanSwitch(coordinator, property_name))
    async_add_entities(entities)
