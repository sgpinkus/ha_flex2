"""Sensor platform — exposes r_opt ∈ [0, 1] with full curve as attributes."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FlexCoordinator, SIGNAL_UPDATE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FlexCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FlexOutputSensor(coordinator, entry)])


class FlexOutputSensor(SensorEntity):
    """
    Exposes r* ∈ [0, 1] as the sensor state.
    Full curve data (curve_xs, curve_cost, curve_total, regime, …)
    is available as extra state attributes for the Lovelace card.
    """

    _attr_icon = "mdi:brightness-6"
    _attr_native_unit_of_measurement = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, coordinator: FlexCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_r_opt"
        self._attr_name = "Flex2 r_opt"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE, self._handle_update
            )
        )

    @callback
    def _handle_update(self, entry_id: str) -> None:
        if entry_id == self._coordinator.entry.entry_id:
            self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        if not self._coordinator.data:
            return None
        return self._coordinator.data.get("r_opt")

    @property
    def extra_state_attributes(self) -> dict:
        return self._coordinator.data or {}