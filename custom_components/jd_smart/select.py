"""Select platform for JD Smart."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .const import DEVICE_TYPE_AIR_CONDITIONER, DEVICE_TYPE_WATER_HEATER
from .entity import JdSmartEntity


@dataclass(frozen=True, kw_only=True)
class JdSmartSelectDescription(SelectEntityDescription):
    """JD Smart select description."""

    stream_id: str
    option_to_value: dict[str, str]


SELECTS: tuple[JdSmartSelectDescription, ...] = (
    JdSmartSelectDescription(
        key="hordir",
        stream_id="hordir",
        translation_key="horizontal_direction",
        options=["swing", "direct"],
        option_to_value={"swing": "0", "direct": "1"},
    ),
)


# Gas water heaters expose the app's 模式设置 as the Mode stream. Captured
# values: 13 = 增容 (capacity boost, the default), 8 = 舒适浴 (comfort bath),
# 9 = 随温感 (ambient tracking). Switching the mode also restores that mode's
# own target temperature on the device.
WATER_HEATER_SELECTS: tuple[JdSmartSelectDescription, ...] = (
    JdSmartSelectDescription(
        key="mode",
        stream_id="Mode",
        translation_key="water_heater_mode",
        options=["capacity_boost", "comfort_bath", "ambient_tracking"],
        option_to_value={
            "capacity_boost": "13",
            "comfort_bath": "8",
            "ambient_tracking": "9",
        },
    ),
)

SELECTS_BY_DEVICE_TYPE = {
    DEVICE_TYPE_AIR_CONDITIONER: SELECTS,
    DEVICE_TYPE_WATER_HEATER: WATER_HEATER_SELECTS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart selects."""
    async_add_entities(
        JdSmartSelect(coordinator, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in SELECTS_BY_DEVICE_TYPE.get(coordinator.device_type, ())
        if (
            coordinator.data is None
            or description.stream_id in coordinator.data.streams
        )
    )


class JdSmartSelect(JdSmartEntity, SelectEntity):
    """JD Smart stream select."""

    entity_description: JdSmartSelectDescription

    def __init__(
        self,
        coordinator,
        description: JdSmartSelectDescription,
    ) -> None:
        """Initialize select."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._value_to_option = {
            value: option for option, value in description.option_to_value.items()
        }

    @property
    def current_option(self) -> str | None:
        """Return selected option."""
        return self._value_to_option.get(
            self.streams.get(self.entity_description.stream_id, "")
        )

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        try:
            await self.coordinator.async_control_streams(
                {
                    self.entity_description.stream_id: int(
                        self.entity_description.option_to_value[option]
                    )
                }
            )
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err
