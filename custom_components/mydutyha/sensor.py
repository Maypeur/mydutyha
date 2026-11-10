from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


def _entity_key(entry) -> str:
    """Stable key for entity ids; keeps the ids of pre-0.2 share-link entries."""
    return str(
        entry.options.get("id")
        or entry.data.get("id")
        or entry.data.get("share_id")
        or entry.data.get("user_id")
    )


def _create_base_attrs(entity_key, suffix):
    return {
        "name": f"MyDuty {entity_key} {suffix}",
        "unique_id": f"myduty_{entity_key}_{suffix.lower().replace(' ', '_')}"
    }


class MyDutyDayCodeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entity_key):
        super().__init__(coordinator)
        attrs = _create_base_attrs(entity_key, "Day Code")
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

    @property
    def state(self):
        return self.coordinator.data.get("day_code")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "is_night_shift": self.coordinator.data.get("is_night_shift", False),
            "is_worked": self.coordinator.data.get("day_is_worked", False),
            "is_off": self.coordinator.data.get("day_is_off", False),
        }

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyDayStartSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entity_key):
        super().__init__(coordinator)
        attrs = _create_base_attrs(entity_key, "Day Start")
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

    @property
    def state(self):
        return self.coordinator.data.get("day_ha_start")

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


class MyDutyDayEndSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entity_key):
        super().__init__(coordinator)
        attrs = _create_base_attrs(entity_key, "Day End")
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

    @property
    def state(self):
        return self.coordinator.data.get("day_ha_end")

    @property
    def available(self) -> bool:
        return bool(self.coordinator and getattr(self.coordinator, "last_update_success", True))


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["mydutyha"][entry.entry_id]
    entity_key = _entity_key(entry)
    entities = [
        MyDutyDayCodeSensor(coordinator, entity_key),
        MyDutyDayStartSensor(coordinator, entity_key),
        MyDutyDayEndSensor(coordinator, entity_key),
    ]
    async_add_entities(entities, True)
