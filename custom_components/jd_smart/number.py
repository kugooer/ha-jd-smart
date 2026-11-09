"""Number platform for JD Smart."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEVICE_TYPE_WATER_HEATER
from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity


@dataclass(frozen=True, kw_only=True)
class JdSmartNumberDescription(NumberEntityDescription):
    """JD Smart number description."""

    stream_id: str
    # The device reports some settings in coarser units than the app shows
    # them: the insulation duration is stored in 10 minute steps, while the
    # app edits it in half hours.
    scale: float = 1


# Ranges mirror the sliders in the JD Smart app for this device family.
NUMBERS: tuple[JdSmartNumberDescription, ...] = (
    JdSmartNumberDescription(
        key="cruise_time",
        stream_id="CruiseTime",
        translation_key="circulation_duration",
        native_min_value=1,
        native_max_value=15,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    JdSmartNumberDescription(
        key="insulation_difference",
        stream_id="TemDifference",
        translation_key="insulation_difference",
        native_min_value=3,
        native_max_value=15,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    JdSmartNumberDescription(
        key="insulation_time",
        stream_id="InsulationTimeSet",
        translation_key="insulation_duration",
        native_min_value=0,
        native_max_value=12,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.SLIDER,
        scale=6,
        entity_category=EntityCategory.CONFIG,
    ),
)

NUMBERS_BY_DEVICE_TYPE = {
    DEVICE_TYPE_WATER_HEATER: NUMBERS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart numbers."""
    async_add_entities(
        JdSmartNumber(coordinator, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in NUMBERS_BY_DEVICE_TYPE.get(coordinator.device_type, ())
        if (
            coordinator.data is None
            or description.stream_id in coordinator.data.streams
        )
    )


class JdSmartNumber(JdSmartEntity, NumberEntity):
    """JD Smart stream number setting."""

    entity_description: JdSmartNumberDescription

    def __init__(self, coordinator, description: JdSmartNumberDescription) -> None:
        """Initialize number."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    @property
    def native_value(self) -> float | None:
        """Return the current setting."""
        value = self.streams.get(self.entity_description.stream_id)
        if value in (None, ""):
            return None
        try:
            return round(float(value) / self.entity_description.scale, 2)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write a new setting to the device."""
        raw = int(round(value * self.entity_description.scale))
        try:
            await self.coordinator.async_control_streams(
                {self.entity_description.stream_id: raw}
            )
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err
