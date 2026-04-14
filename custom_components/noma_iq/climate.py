from __future__ import annotations

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVAC_MODE_AUTO, HVAC_MODE_DRY, HVAC_MODE_OFF

from .entity import NomaIqEntity


class NomaIqClimateEntity(NomaIqEntity, ClimateEntity):
    _attr_supported_features = ClimateEntityFeature.TARGET_HUMIDITY | ClimateEntityFeature.FAN_MODE
    _attr_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_DRY, HVAC_MODE_AUTO]
    _attr_target_humidity_step = 1

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "climate")
        self._power = self.find_alias("power")
        self._target = self.find_alias("target_humidity")
        self._current = self.find_alias("current_humidity")
        self._mode_property = self._find_property("mode")
        self._fan_property = self._find_property("fan_speed")

    @staticmethod
    def _normalize_options(values: list | None) -> list[str]:
        if not values:
            return []
        options: list[str] = []
        for raw in values:
            if raw is None:
                continue
            if isinstance(raw, dict):
                label = raw.get("label") or raw.get("name") or raw.get("value")
                if label is not None:
                    options.append(str(label))
                continue
            options.append(str(raw))
        return list(dict.fromkeys(options))

    def _find_property(self, name: str) -> str | None:
        device = self.device
        if device is None:
            return None
        return self._client.find_property(device, [name])

    def _property_options(self, property_name: str | None) -> list[str]:
        device = self.device
        if device is None or not property_name:
            return []
        prop = device.properties_full.get(property_name, {})
        values = prop.get("values") or prop.get("choices") or prop.get("options")
        if isinstance(values, dict):
            values = list(values.values())
        if isinstance(values, str):
            return [values]
        if isinstance(values, list):
            return self._normalize_options(values)
        return []

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.device is not None
            and self._power is not None
            and self._target is not None
        )

    @property
    def is_on(self) -> bool:
        return self._as_bool(self._client.get_property_value(self.device, self._power))

    @property
    def hvac_mode(self) -> str:
        if not self.is_on:
            return HVAC_MODE_OFF
        if not self._mode_property:
            return HVAC_MODE_DRY
        mode = self._client.get_property_value(self.device, self._mode_property)
        if isinstance(mode, str) and mode.lower() == "auto":
            return HVAC_MODE_AUTO
        return HVAC_MODE_DRY

    @property
    def hvac_action(self) -> str:
        return self.hvac_mode

    @property
    def target_humidity(self) -> int | None:
        value = self._client.get_property_value(self.device, self._target)
        return int(value) if value is not None else None

    @property
    def current_humidity(self) -> int | None:
        value = self._client.get_property_value(self.device, self._current)
        return int(value) if value is not None else None

    @property
    def fan_modes(self) -> list[str]:
        return self._property_options(self._fan_property)

    @property
    def fan_mode(self) -> str | None:
        value = self._client.get_property_value(self.device, self._fan_property)
        return str(value) if value is not None else None

    async def _set_power(self, state: bool) -> None:
        await self._client.async_set_property_value(self.device, self._power, state)
        await self.coordinator.async_request_refresh()

    async def _set_mode(self, mode: str | None) -> None:
        if not self._mode_property or mode is None:
            return
        await self._client.async_set_property_value(self.device, self._mode_property, mode)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode == HVAC_MODE_OFF:
            await self._set_power(False)
            return
        await self._set_power(True)
        if hvac_mode == HVAC_MODE_AUTO:
            await self._set_mode("Auto")
        else:
            modes = self._property_options(self._mode_property)
            if modes:
                await self._set_mode(modes[0])

    async def async_set_target_humidity(self, humidity: float) -> None:
        if not self._target:
            return
        await self._client.async_set_property_value(self.device, self._target, int(humidity))
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if self._fan_property is None:
            return
        await self._client.async_set_property_value(self.device, self._fan_property, fan_mode)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data["noma_iq"][entry.entry_id]
    entity = NomaIqClimateEntity(coordinator)
    if entity.device is not None and entity._power is not None:
        async_add_entities([entity])
