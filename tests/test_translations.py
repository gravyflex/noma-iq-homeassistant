"""Regression tests: every _attr_translation_key must have a matching strings.json entry.

Prevents the issue-#1 class of bug where an entity with _attr_translation_key
set (and _attr_has_entity_name=True / _attr_name=None) had no matching entry
in strings.json, causing HA to fall back to a generic entity name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENT_DIR = REPO_ROOT / "custom_components" / "noma_iq"
STRINGS_JSON = COMPONENT_DIR / "strings.json"

# Entity modules and their HA domain mapping
ENTITY_MODULES: dict[str, str] = {
    "binary_sensor.py": "binary_sensor",
    "sensor.py": "sensor",
    "select.py": "select",
    "switch.py": "switch",
    "number.py": "number",
    "humidifier.py": "humidifier",
}

# Dynamic translation keys that are set at runtime in __init__.
# These must be kept in sync with the entity module source.
DYNAMIC_TRANSLATION_KEYS: dict[str, dict[str, list[str]]] = {
    # binary_sensor.py: _attr_translation_key = key  (key arg in async_setup_entry loop)
    "binary_sensor.py": {
        "binary_sensor": ["water_bucket_full", "filter_clean_alarm"],
    },
    # select.py: _attr_translation_key = property_name
    "select.py": {
        "select": ["mode", "fan_speed"],
    },
    # switch.py: _attr_translation_key = property_name  (discovered dynamically)
    "switch.py": {
        "switch": ["power", "display_on", "ionizer", "auto_defrost"],
    },
}


def load_strings_json() -> dict:
    """Load and return strings.json, asserting it is valid JSON."""
    assert STRINGS_JSON.exists(), f"strings.json not found at {STRINGS_JSON}"
    text = STRINGS_JSON.read_text(encoding="utf-8")
    data = json.loads(text)  # raises if invalid JSON
    assert isinstance(data, dict), "strings.json root must be a JSON object"
    return data


def find_static_translation_keys(module_path: Path) -> list[str]:
    """Extract static _attr_translation_key = "..." assignments from a Python file."""
    content = module_path.read_text(encoding="utf-8")
    # Match: _attr_translation_key = "some_key"
    pattern = r'''_attr_translation_key\s*=\s*["'](\w+)["']'''
    return re.findall(pattern, content)


def test_strings_json_is_valid_json() -> None:
    """strings.json must parse as valid JSON."""
    load_strings_json()  # will raise on parse failure


def test_strings_json_has_entity_section() -> None:
    """strings.json must contain an 'entity' top-level key."""
    data = load_strings_json()
    assert "entity" in data, "strings.json missing top-level 'entity' key"


def test_static_translation_keys_have_strings_entries() -> None:
    """Every static _attr_translation_key must have entity.<domain>.<key> in strings.json."""
    data = load_strings_json()
    entity_section = data.get("entity", {})
    missing: list[str] = []

    for module_file, domain in ENTITY_MODULES.items():
        module_path = COMPONENT_DIR / module_file
        if not module_path.exists():
            continue
        keys = find_static_translation_keys(module_path)
        for key in keys:
            domain_section = entity_section.get(domain, {})
            if key not in domain_section:
                missing.append(f"entity.{domain}.{key} (from {module_file})")

    assert not missing, (
        "Missing strings.json entries for static translation keys:\n"
        + "\n".join(missing)
    )


def test_dynamic_translation_keys_have_strings_entries() -> None:
    """Every dynamic _attr_translation_key (set in __init__) must have entity.<domain>.<key> in strings.json."""
    data = load_strings_json()
    entity_section = data.get("entity", {})
    missing: list[str] = []

    for module_file, domain_keys in DYNAMIC_TRANSLATION_KEYS.items():
        for domain, keys in domain_keys.items():
            domain_section = entity_section.get(domain, {})
            for key in keys:
                if key not in domain_section:
                    missing.append(f"entity.{domain}.{key} (dynamic, from {module_file})")

    assert not missing, (
        "Missing strings.json entries for dynamic translation keys:\n"
        + "\n".join(missing)
    )


def test_entity_name_present_in_strings() -> None:
    """Each entity.<domain>.<key> entry must have a 'name' field."""
    data = load_strings_json()
    entity_section = data.get("entity", {})
    missing_name: list[str] = []

    # Check all static keys
    for module_file, domain in ENTITY_MODULES.items():
        module_path = COMPONENT_DIR / module_file
        if not module_path.exists():
            continue
        keys = find_static_translation_keys(module_path)
        for key in keys:
            domain_section = entity_section.get(domain, {})
            entry = domain_section.get(key, {})
            if "name" not in entry:
                missing_name.append(f"entity.{domain}.{key}.name (from {module_file})")

    # Check all dynamic keys
    for module_file, domain_keys in DYNAMIC_TRANSLATION_KEYS.items():
        for domain, keys in domain_keys.items():
            domain_section = entity_section.get(domain, {})
            for key in keys:
                entry = domain_section.get(key, {})
                if "name" not in entry:
                    missing_name.append(f"entity.{domain}.{key}.name (dynamic, from {module_file})")

    assert not missing_name, (
        "Missing 'name' field in strings.json entries:\n"
        + "\n".join(missing_name)
    )


def test_select_entities_have_state_translations() -> None:
    """Select entities should have 'state' translations in strings.json."""
    data = load_strings_json()
    entity_section = data.get("entity", {})
    select_section = entity_section.get("select", {})
    missing_state: list[str] = []

    for key in DYNAMIC_TRANSLATION_KEYS.get("select.py", {}).get("select", []):
        entry = select_section.get(key, {})
        if "state" not in entry:
            missing_state.append(f"entity.select.{key}.state")

    assert not missing_state, (
        "Missing 'state' translations for select entities:\n"
        + "\n".join(missing_state)
    )