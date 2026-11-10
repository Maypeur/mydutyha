from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


def _entity_key(entry) -> str:
    """Stable key for entity ids; keeps the ids of pre-0.2 share-link entries."""
    return str(
        entry.options.get("id")
        or entry.data.get("id")
        or entry.data.get("share_id")
        or entry.data.get("user_id")
    )


class MyDutyIsWorkedSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entity_key):
        super().__init__(coordinator)
        self._attr_name = f"MyDuty {entity_key} Is Worked"
        self._attr_unique_id = f"myduty_{entity_key}_day_is_worked"

    @property
    def is_on(self):
        return self.coordinator.data.get("day_is_worked")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "start_time": self.coordinator.data.get("day_ha_start"),
            "end_time": self.coordinator.data.get("day_ha_end"),
            "is_night_shift": self.coordinator.data.get("is_night_shift", False),
            "day_code": self.coordinator.data.get("day_code"),
        }

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyIsOffSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entity_key):
        super().__init__(coordinator)
        self._attr_name = f"MyDuty {entity_key} Is Off"
        self._attr_unique_id = f"myduty_{entity_key}_day_is_off"

    @property
    def is_on(self):
        return self.coordinator.data.get("day_is_off")

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyIsNightShiftSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entity_key):
        super().__init__(coordinator)
        self._attr_name = f"MyDuty {entity_key} Is Night Shift"
        self._attr_unique_id = f"myduty_{entity_key}_is_night_shift"

    @property
    def is_on(self):
        return self.coordinator.data.get("is_night_shift")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "start_time": self.coordinator.data.get("day_ha_start"),
            "end_time": self.coordinator.data.get("day_ha_end"),
            "day_code": self.coordinator.data.get("day_code"),
        }

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["mydutyha"][entry.entry_id]
    entity_key = _entity_key(entry)
    entities = [
        MyDutyIsWorkedSensor(coordinator, entity_key),
        MyDutyIsOffSensor(coordinator, entity_key),
        MyDutyIsNightShiftSensor(coordinator, entity_key),
    ]
    async_add_entities(entities, True)
