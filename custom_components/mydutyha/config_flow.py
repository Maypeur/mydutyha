"""Config and options flow for MyDutyHA (MYDUTY app login, no share links)."""

from __future__ import annotations

import logging
import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .api import MyDutyApi, MyDutyAuthError, MyDutyError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_SYNC_TIMES = ["00:05", "12:00", "17:30"]
TIME_RE = re.compile(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")


def _entity_key(entry: config_entries.ConfigEntry) -> str:
    """Stable key used for entity ids; keeps ids of pre-0.2 entries."""
    return str(
        entry.options.get("id")
        or entry.data.get("id")
        or entry.data.get("share_id")
        or entry.data.get("user_id")
    )


def _schema(include_creds: bool, defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    fields: dict = {
        vol.Required("name", default=defaults.get("name", "")): str,
        vol.Optional(
            "user_id", default=defaults.get("user_id", "")
        ): str,
    }
    if include_creds:
        fields[vol.Optional("email", default=defaults.get("email", ""))] = str
        fields[vol.Optional("password", default="")] = str
    return vol.Schema(fields)


async def _resolve_user_id(user_id: str, email: str, password: str) -> tuple[str | None, str | None]:
    """Return (user_id, error_key)."""
    if user_id:
        if not user_id.isdigit():
            return None, "invalid_user_id"
        api = MyDutyApi(user_id)
        await api.async_bootstrap()
        try:
            await api.async_user()
        except MyDutyError:
            return None, "unknown_user"
        return user_id, None

    if email and password:
        api = MyDutyApi()
        await api.async_bootstrap()
        try:
            user = await api.async_login(email, password)
        except MyDutyAuthError:
            return None, "invalid_auth"
        except MyDutyError as err:
            _LOGGER.debug("MYDUTY login failed: %s", err)
            return None, "cannot_connect"
        return str(user["userId"]), None

    return None, "credentials_required"


class MyDutyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            name = (user_input.get("name") or "").strip()
            user_id = (user_input.get("user_id") or "").strip()
            email = (user_input.get("email") or "").strip()
            password = user_input.get("password") or ""
            if not name:
                errors["name"] = "required"
            else:
                resolved, error = await _resolve_user_id(user_id, email, password)
                if error:
                    errors["base" if error != "invalid_user_id" else "user_id"] = error
                else:
                    await self.async_set_unique_id(resolved)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=name,
                        data={"name": name, "id": resolved, "user_id": resolved},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(include_creds=True),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MyDutyOptionsFlowHandler()


class MyDutyOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        entry = self.config_entry
        options = entry.options

        if user_input is not None:
            times: list[str] = []
            for i in range(1, 4):
                value = (user_input.get(f"sync_time_{i}") or "").strip()
                if not value:
                    continue
                if not TIME_RE.match(value):
                    errors[f"sync_time_{i}"] = "invalid_format"
                else:
                    times.append(value)
            if not times and not errors:
                errors["base"] = "at_least_one_time"

            current = str(options.get("user_id") or entry.data.get("user_id") or "")
            user_id = (user_input.get("user_id") or "").strip()
            email = (user_input.get("email") or "").strip()
            password = user_input.get("password") or ""

            new_user_id = current
            if user_id or (email and password):
                new_user_id, error = await _resolve_user_id(user_id, email, password)
                if error:
                    errors["base" if error != "invalid_user_id" else "user_id"] = error
                    new_user_id = current

            if not errors and not new_user_id:
                errors["base"] = "credentials_required"

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        "sync_times": times,
                        "user_id": new_user_id,
                        # keep the entity key of pre-0.2 entries
                        "id": _entity_key(entry),
                    },
                )

        sync_times = list(options.get("sync_times", DEFAULT_SYNC_TIMES))
        while len(sync_times) < 3:
            sync_times.append("")

        schema = vol.Schema(
            {
                vol.Optional(
                    "user_id",
                    default=str(options.get("user_id") or entry.data.get("user_id") or ""),
                ): str,
                vol.Optional("email", default=""): str,
                vol.Optional("password", default=""): str,
                vol.Optional("sync_time_1", default=sync_times[0]): str,
                vol.Optional("sync_time_2", default=sync_times[1]): str,
                vol.Optional("sync_time_3", default=sync_times[2]): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
