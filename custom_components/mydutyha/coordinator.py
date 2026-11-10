"""Coordinator: fetches MYDUTY data and exposes today's shift."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MyDutyApi, MyDutyError
from .state import build_day_state

_LOGGER = logging.getLogger(__name__)


class MyDutyCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass,
        user_id: str,
        group_id: str | None = None,
        member_id: str | None = None,
    ) -> None:
        self.api = MyDutyApi(user_id, group_id, member_id)
        super().__init__(
            hass,
            _LOGGER,
            name="MyDutyHA Coordinator",
            update_interval=None,  # refreshed at the configured sync times
        )

    async def _async_update_data(self) -> dict:
        delay = 1
        for attempt in range(1, 4):
            try:
                raw = await self.api.async_fetch_data()
                break
            except MyDutyError as err:
                if attempt == 3:
                    raise UpdateFailed(f"Error fetching MYDUTY data: {err}") from err
                _LOGGER.warning(
                    "Attempt %s/3 failed fetching MYDUTY data: %s", attempt, err
                )
                await asyncio.sleep(delay)
                delay *= 2
            except Exception as err:  # noqa: BLE001 - network layer
                raise UpdateFailed(f"Error fetching MYDUTY data: {err}") from err
        else:  # pragma: no cover - loop always breaks or raises
            raise UpdateFailed("Error fetching MYDUTY data")

        entries: list[dict] = []
        for block in raw.get("month_blocks", []):
            entries.extend(block.get("schedules") or [])

        result = build_day_state(raw.get("duty_units", []), entries)
        _LOGGER.debug("MYDUTY update result: %s", result)
        return result
