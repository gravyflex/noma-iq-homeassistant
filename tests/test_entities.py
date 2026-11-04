"""End-to-end: config entry setup -> entity names and unique ids."""

import pytest
from unittest.mock import patch
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.noma_iq.const import DOMAIN

pytestmark = pytest.mark.asyncio


class FakeDevice:
    serial_number = "AC000W1"
    oem_model_number = "dehum"
    device_model_number = "NOMA-DEHUM"
    eu_ads_url = ads_url = "https://ads.example"
    europe = False

    def __init__(self):
        self.properties_full = {
            "power": {"value": 1, "base_type": "boolean", "read_only": False, "name": "power"},
            "display_on": {"value": 1, "base_type": "boolean", "read_only": False, "name": "display_on"},
            "ionizer": {"value": 0, "base_type": "boolean", "read_only": False, "name": "ionizer"},
            "auto_defrost": {"value": 0, "base_type": "boolean", "read_only": False, "name": "auto_defrost"},
            "timer_remaining": {"value": 0, "base_type": "boolean", "read_only": False, "name": "timer_remaining"},
            "water_bucket_full": {"value": 0, "base_type": "boolean", "read_only": True, "name": "water_bucket_full"},
            "filter_clean_alarm": {"value": 0, "base_type": "boolean", "read_only": True, "name": "filter_clean_alarm"},
            "humidity_sensor_fault": {"value": 0, "base_type": "boolean", "read_only": True, "name": "humidity_sensor_fault"},
            "current_humidity": {"value": 45, "base_type": "integer", "read_only": True, "name": "current_humidity"},
            "target_humidity": {"value": 50, "base_type": "integer", "read_only": False, "name": "target_humidity"},
            "mode": {"value": "Normal", "base_type": "string", "read_only": False, "name": "mode"},
            "fan_speed": {"value": "Low", "base_type": "string", "read_only": False, "name": "fan_speed"},
        }

    def get_property_value(self, name):
        return self.properties_full[name]["value"]

    async def async_update(self, *args, **kwargs):
        return None


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.device = FakeDevice()

    async def async_get_device(self, dsn):
        return self.device

    def find_property(self, device, aliases):
        for alias in aliases:
            if alias in device.properties_full:
                return alias
        return None

    def get_property_value(self, device, name):
        if not name:
            return None
        return device.properties_full.get(name, {}).get("value")


ENTRY_DATA = {
    "username": "user@example.com",
    "password": "pw",
    "dsn": "AC000W1",
    "device_name": "Water Bucket",
    "oem_model": "dehum",
    "product_name": "Dehumidifier",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def test_entity_names(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="AC000W1")
    entry.add_to_hass(hass)
    with patch("custom_components.noma_iq.coordinator.NomaIqClient", FakeClient):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    names = {}
    for state in hass.states.async_all():
        names.setdefault(state.name, []).append(state.entity_id)

    print("\nENTITY NAMES:")
    for name in sorted(names):
        print(f"  {name!r} -> {names[name]}")

    expected = [
        "Water Bucket Bucket Full",
        "Water Bucket Filter Clean Alarm",
        "Water Bucket Current Humidity",
        "Water Bucket Target Humidity",
        "Water Bucket Mode",
        "Water Bucket Fan Speed",
        "Water Bucket Power",
        "Water Bucket Display On",
        "Water Bucket Ionizer",
        "Water Bucket Auto Defrost",
        "Water Bucket Timer Remaining",
        "Water Bucket Dehumidifier",
        "Water Bucket Bucket Status",
        "Water Bucket Humidity Sensor Fault",
        "Water Bucket Dehumidifier",
        "Water Bucket Controls",
    ]
    missing = [name for name in expected if name not in names]
    assert not missing, f"missing entity names: {missing}\nall: {sorted(names)}"

    assert names["Water Bucket Controls"] == ["climate.water_bucket_controls"]

    duplicates = [name for name, ids in names.items() if len(ids) > 1]
    assert not duplicates, f"duplicate entity names: {duplicates}"
