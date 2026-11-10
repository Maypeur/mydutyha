"""MyDutyHA - MYDUTY shift calendar for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN
from .coordinator import MyDutyCoordinator

_LOGGER = logging.getLogger(__name__)

DEFAULT_SYNC_TIMES = ["00:05", "12:00", "17:30"]
PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    user_id = str(entry.options.get("user_id") or entry.data.get("user_id") or "")
    if not user_id:
        raise ConfigEntryNotReady(
            "No MYDUTY user id configured. Open the MyDutyHA options and sign "
            "in with your MYDUTY e-mail and password."
        )

    group_id = (
        entry.options.get("group_id")
        or entry.data.get("group_id")
        or None
    )
    member_id = (
        entry.options.get("member_user_id")
        or entry.data.get("member_user_id")
        or None
    )
    coordinator = MyDutyCoordinator(hass, user_id, group_id, member_id)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def scheduled_update(now):
        await coordinator.async_request_refresh()

    unsubs = []
    for sync_time in entry.options.get("sync_times", DEFAULT_SYNC_TIMES):
        try:
            hour, minute = map(int, sync_time.split(":"))
        except (ValueError, AttributeError):
            continue
        unsubs.append(
            async_track_time_change(
                hass, scheduled_update, hour=hour, minute=minute, second=0
            )
        )

    def remove_time_listeners():
        while unsubs:
            unsubs.pop()()

    entry.async_on_unload(remove_time_listeners)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    async def handle_sync_now(call):
        wanted = call.data.get("user_id")
        wanted = str(wanted) if wanted is not None else None
        for entry_id, coord in list(hass.data.get(DOMAIN, {}).items()):
            if wanted is None:
                await coord.async_request_refresh()
                continue
            user_id = str(
                getattr(coord.api, "user_id", "")
            )
            if user_id == wanted:
                await coord.async_request_refresh()

    hass.services.async_register(DOMAIN, "sync_now", handle_sync_now)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload so new sync times / credentials take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    if unload_ok and not hass.data.get(DOMAIN):
        try:
            hass.services.async_remove(DOMAIN, "sync_now")
        except Exception:  # noqa: BLE001 - service may not be registered
            pass
    return unload_ok
