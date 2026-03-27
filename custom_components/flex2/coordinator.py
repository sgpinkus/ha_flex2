"""FlexCoordinator — subscribes to price signal, runs solver, signals sensor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, CONF_P_L, CONF_P_H, CONF_PRICE_ENTITY, DEFAULT_P_L, DEFAULT_P_H
from .cost import HLQuadraticCost, solve

_LOGGER = logging.getLogger(__name__)

SIGNAL_UPDATE = f"{DOMAIN}_update"


class FlexCoordinator:

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.data: dict[str, Any] = {}
        self._unsub = None

        p_l = entry.options.get(CONF_P_L, entry.data.get(CONF_P_L, DEFAULT_P_L))
        p_h = entry.options.get(CONF_P_H, entry.data.get(CONF_P_H, DEFAULT_P_H))
        self._cost_fn = HLQuadraticCost(p_l=float(p_l), p_h=float(p_h))
        self._price_entity: str = entry.data[CONF_PRICE_ENTITY]

    async def async_setup(self) -> None:
        self._unsub = async_track_state_change_event(
            self.hass, [self._price_entity], self._on_price_change
        )
        await self._solve()

    @callback
    def async_teardown(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    def _current_lambda(self) -> float | None:
        state = self.hass.states.get(self._price_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except ValueError:
            _LOGGER.warning("flex2: cannot parse λ from %s: %s",
                            self._price_entity, state.state)
            return None

    async def _solve(self) -> None:
        lam = self._current_lambda()
        if lam is None:
            return
        self.data = solve(lam, self._cost_fn)
        _LOGGER.debug("flex2: λ=%.4f  regime=%s  r*=%.3f",
                      lam, self.data["regime"], self.data["r_opt"])
        async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)

    @callback
    def _on_price_change(self, event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unknown", "unavailable"):
            return
        self.hass.async_create_task(self._solve())