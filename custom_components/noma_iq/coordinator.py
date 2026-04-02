from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientSession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ayla import NomaIqClient, NomaIqDeviceNotFoundError
from .const import CONF_DSN, CONF_PASSWORD, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class NomaIqDataUpdateCoordinator(DataUpdateCoordinator[Any]):
    def __init__(self, hass, entry, session: ClientSession) -> None:
        self.entry = entry
        self.client = NomaIqClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=session,
        )
        self.device = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_DSN]}",
            update_interval=timedelta(
                seconds=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self):
        try:
            self.device = await self.client.async_get_device(self.entry.data[CONF_DSN])
            return self.device
        except NomaIqDeviceNotFoundError as err:
            raise UpdateFailed(f"Configured NOMA device not found: {err}") from err
        except Exception as err:
            raise UpdateFailed(str(err)) from err

