"""Pure mapping from MYDUTY duty schedules to today's shift (no HA imports)."""

from __future__ import annotations

from datetime import date, datetime, timedelta


def _fmt(value) -> str | None:
    """'0700' -> '07:00'."""
    if not value:
        return None
    text = str(value).zfill(4)
    return f"{text[0:2]}:{text[2:4]}"


def _minutes(value: str | None) -> int:
    if not value:
        return 0
    hours, mins = value.split(":")
    return int(hours) * 60 + int(mins)


def build_day_state(
    duty_units: list[dict],
    entries: list[dict],
    now: datetime | None = None,
) -> dict:
    """Return the day/start/end/off/night-shift state for ``now``."""
    now = now or datetime.now()
    duty_map = {str(unit.get("dutyUnitId")): unit for unit in duty_units}

    def find_entry(target: date) -> dict | None:
        for entry in entries:
            if (
                str(entry.get("year")) == str(target.year)
                and str(entry.get("month")).zfill(2) == f"{target.month:02d}"
                and str(entry.get("day")).zfill(2) == f"{target.day:02d}"
            ):
                return entry
        return None

    result = {
        "day_code": None,
        "day_ha_start": None,
        "day_ha_end": None,
        "day_is_worked": False,
        "day_is_off": False,
        "is_night_shift": False,
    }

    # A night shift that started yesterday and runs into today.
    yesterday_entry = find_entry((now - timedelta(days=1)).date())
    if yesterday_entry:
        unit = duty_map.get(str(yesterday_entry.get("dutyUnitId")))
        if unit:
            start = _fmt(unit.get("startTime"))
            end = _fmt(unit.get("endTime"))
            if start and end and _minutes(end) < _minutes(start):
                if not (unit.get("isOffDay") or unit.get("isVacation")):
                    result.update(
                        day_code=unit.get("title"),
                        day_ha_start=start,
                        day_ha_end=end,
                        day_is_worked=True,
                        day_is_off=False,
                        is_night_shift=True,
                    )
                    return result

    today_entry = find_entry(now.date())
    if today_entry:
        unit = duty_map.get(str(today_entry.get("dutyUnitId")))
        if unit:
            start = _fmt(unit.get("startTime"))
            end = _fmt(unit.get("endTime"))
            is_off = bool(unit.get("isOffDay")) or bool(unit.get("isVacation"))
            result.update(
                day_code=unit.get("title"),
                day_ha_start=start,
                day_ha_end=end,
                day_is_off=is_off,
                day_is_worked=not is_off,
            )
            if start and end and _minutes(end) < _minutes(start):
                result["is_night_shift"] = True

    return result
