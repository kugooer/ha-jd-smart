"""Water heater platform for JD Smart."""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DEVICE_TYPE_WATER_HEATER,
    WATER_HEATER_MAX_TEMP,
    WATER_HEATER_MIN_TEMP,
    WATER_HEATER_REQUIRED_STREAMS,
)
from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity

WATER_HEATER_SUPPORTED_FEATURES = (
    WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.ON_OFF
)

POWER_STREAM = "Power"
TARGET_TEMP_STREAM = "TemperatureSet"
CURRENT_TEMP_STREAM = "CurrentTemperature"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart water heaters."""
    async_add_entities(
        JdSmartWaterHeater(coordinator)
        for coordinator in entry.runtime_data.coordinators.values()
        if coordinator.device_type == DEVICE_TYPE_WATER_HEATER
        if (
            coordinator.data is None
            or WATER_HEATER_REQUIRED_STREAMS <= coordinator.data.streams.keys()
        )
    )


class JdSmartWaterHeater(JdSmartEntity, WaterHeaterEntity):
    """JD Smart gas water heater entity."""

    _attr_name = None
    _attr_supported_features = WATER_HEATER_SUPPORTED_FEATURES
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    # The DL1S panel and app allow 32-60 degrees Celsius; the device clamps
    # anything outside of that range.
    _attr_min_temp = WATER_HEATER_MIN_TEMP
    _attr_max_temp = WATER_HEATER_MAX_TEMP
    _attr_target_temperature_step = 1
    _attr_translation_key = "water_heater"

    def __init__(self, coordinator) -> None:
        """Initialize water heater."""
        super().__init__(coordinator, "water_heater")

    @property
    def current_temperature(self) -> float | None:
        """Return current water temperature."""
        return _float_or_none(self.streams.get(CURRENT_TEMP_STREAM))

    @property
    def target_temperature(self) -> float | None:
        """Return target water temperature."""
        return _float_or_none(self.streams.get(TARGET_TEMP_STREAM))

    @property
    def is_on(self) -> bool | None:
        """Return whether the water heater is powered on."""
        value = self.streams.get(POWER_STREAM)
        if value is None:
            return None
        return value == "1"

    @property
    def current_operation(self) -> str | None:
        """Return the current operation state."""
        is_on = self.is_on
        if is_on is None:
            return None
        return STATE_ON if is_on else STATE_OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target water temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._control({TARGET_TEMP_STREAM: int(temperature)})

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the water heater on."""
        await self._control({POWER_STREAM: 1})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the water heater off."""
        await self._control({POWER_STREAM: 0})

    async def _control(self, commands: dict[str, object]) -> None:
        """Control helper."""
        try:
            await self.coordinator.async_control_streams(commands)
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err


def _float_or_none(value: str | None) -> float | None:
    """Convert a value to float."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None
