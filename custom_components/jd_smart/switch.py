"""Switch platform for JD Smart."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .const import DEVICE_TYPE_AIR_CONDITIONER, DEVICE_TYPE_WATER_HEATER
from .entity import JdSmartEntity


@dataclass(frozen=True, kw_only=True)
class JdSmartSwitchDescription(SwitchEntityDescription):
    """JD Smart switch description."""

    stream_id: str


SWITCHES: tuple[JdSmartSwitchDescription, ...] = (
    JdSmartSwitchDescription(
        key="bglight", stream_id="bglight", translation_key="backlight"
    ),
    JdSmartSwitchDescription(
        key="scrdispaly", stream_id="scrdispaly", translation_key="display"
    ),
    JdSmartSwitchDescription(
        key="ecomode", stream_id="ecomode", translation_key="powerful"
    ),
)

# Gas water heaters expose these 0/1 streams as on/off toggles in the app:
# one-shot circulation, turbo boost, tap-to-start circulation, all-day
# circulation and disinfection.
WATER_HEATER_SWITCHES: tuple[JdSmartSwitchDescription, ...] = (
    # CruiseMode is the app's "单次" (single circulation) action: writing 1
    # starts one preheat cycle (pump on, water flows, heater works) and
    # writing 0 cancels it. The device clears it on its own when the cycle
    # ends, so the switch follows the reported state.
    JdSmartSwitchDescription(
        key="single_circulation",
        stream_id="CruiseMode",
        translation_key="single_circulation",
        entity_category=EntityCategory.CONFIG,
    ),
    JdSmartSwitchDescription(
        key="turbo_power",
        stream_id="TurboPower",
        translation_key="turbo_boost",
        entity_category=EntityCategory.CONFIG,
    ),
    JdSmartSwitchDescription(
        key="instant_heat",
        stream_id="ActiononOff",
        translation_key="instant_heat",
        entity_category=EntityCategory.CONFIG,
    ),
    JdSmartSwitchDescription(
        key="all_day_power",
        stream_id="AllDayPower",
        translation_key="all_day_circulation",
        entity_category=EntityCategory.CONFIG,
    ),
    JdSmartSwitchDescription(
        key="disinfect",
        stream_id="Disinfect",
        translation_key="cruise_disinfection",
        entity_category=EntityCategory.CONFIG,
    ),
)

SWITCHES_BY_DEVICE_TYPE = {
    DEVICE_TYPE_AIR_CONDITIONER: SWITCHES,
    DEVICE_TYPE_WATER_HEATER: WATER_HEATER_SWITCHES,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart switches."""
    async_add_entities(
        JdSmartSwitch(coordinator, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in SWITCHES_BY_DEVICE_TYPE.get(coordinator.device_type, ())
        if (
            coordinator.data is None
            or description.stream_id in coordinator.data.streams
        )
    )


class JdSmartSwitch(JdSmartEntity, SwitchEntity):
    """JD Smart stream switch."""

    entity_description: JdSmartSwitchDescription

    def __init__(
        self,
        coordinator,
        description: JdSmartSwitchDescription,
    ) -> None:
        """Initialize switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    @property
    def is_on(self) -> bool | None:
        """Return switch state."""
        value = self.streams.get(self.entity_description.stream_id)
        if value == "":
            return None
        return value == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on."""
        await self._control(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off."""
        await self._control(0)

    async def _control(self, value: int) -> None:
        """Control helper."""
        try:
            await self.coordinator.async_control_streams(
                {self.entity_description.stream_id: value}
            )
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err
