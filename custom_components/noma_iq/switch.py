from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .entity import NomaIqEntity

# Properties with an entry under "entity.switch" in strings.json/translations.
TRANSLATED_SWITCH_KEYS = {"power", "display_on", "ionizer", "auto_defrost"}


class NomaIqWritableBooleanSwitch(NomaIqEntity, SwitchEntity):
    def __init__(self, coordinator, property_name: str) -> None:
        super().__init__(coordinator, f"switch_{property_name}")
        self._property_name = property_name
        if property_name in TRANSLATED_SWITCH_KEYS:
            self._attr_translation_key = property_name
        else:
            # No translation entry: derive a readable name so the entity is not
            # named after the device and does not collide with its siblings.
            self._attr_name = property_name.replace("_", " ").strip().title()

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
