from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .entity import NomaIqEntity


class NomaIqPropertySelect(NomaIqEntity, SelectEntity):
    _attr_name = None

    def __init__(
        self,
        coordinator,
        property_name: str,
        options: list[str],
        *,
        read_map: dict[str, str] | None = None,
        write_map: dict[str, str] | None = None,
    ) -> None:
        super().__init__(coordinator, f"select_{property_name}")
        self._property_name = property_name
        self._options = options
        self._read_map = read_map or {}
        self._write_map = write_map or {}

    @property
    def name(self):
        return self._property_name.replace("_", " ").title()

    @property
    def current_option(self):
        value = self._client.get_property_value(self.device, self._property_name)
        if value is None:
            return None
        return self._read_map.get(str(value), str(value))

    @property
    def options(self):
        current = self.current_option
        values = list(self._options)
        if current and current not in values:
            values.append(current)
        return values

    async def async_select_option(self, option: str) -> None:
        await self._client.async_set_property_value(
            self.device,
            self._property_name,
            self._write_map.get(option, option),
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["noma_iq"][entry.entry_id]
    device = coordinator.device
    if device is None:
        return

    entities = []
    if "mode" in device.properties_full and not device.properties_full["mode"].get("read_only"):
        entities.append(
            NomaIqPropertySelect(
                coordinator,
                "mode",
                ["Auto", "Continuous", "Manual"],
                read_map={"Normal": "Manual"},
                write_map={"Manual": "Normal"},
            )
        )
    if "fan_speed" in device.properties_full and not device.properties_full["fan_speed"].get("read_only"):
        entities.append(
            NomaIqPropertySelect(
                coordinator,
                "fan_speed",
                ["Low", "High"],
            )
        )

    async_add_entities(entities)
