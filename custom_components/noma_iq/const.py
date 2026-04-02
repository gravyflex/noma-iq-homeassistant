from datetime import timedelta

DOMAIN = "noma_iq"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DSN = "dsn"
CONF_DEVICE_NAME = "device_name"
CONF_OEM_MODEL = "oem_model"
CONF_PRODUCT_NAME = "product_name"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30
PLATFORMS = ["humidifier", "binary_sensor", "sensor", "switch"]

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

NOMA_APP_ID = "ctc-noma-Bg-id"
NOMA_APP_SECRET = "ctc-noma-WNHWBmAGLoaMl8xq8lx9XxGmiTQ"

DEHUM_OEM_MODEL = "dehum"

PROP_ALIASES = {
    "power": ["power", "on", "enabled", "running", "status"],
    "target_humidity": [
        "target_humidity",
        "dehumid_target_humidity",
        "set_humidity",
        "humidity",
        "targethumidity",
        "humidity_setpoint",
    ],
    "current_humidity": [
        "current_humidity",
        "indoor_humidity",
        "dehumid_room_humidity",
        "room_humidity",
    ],
    "water_bucket_full": [
        "water_bucket_full",
        "water_bucket_full_status",
        "bucket_full",
        "water_full",
    ],
    "filter_clean_alarm": [
        "filter_clean_alarm",
        "change_filter",
        "filter_alarm",
        "clean_filter_alarm",
    ],
}
