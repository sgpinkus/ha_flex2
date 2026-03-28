"""flex2 — demand-response integration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.components.lovelace import LovelaceData
from homeassistant.components.lovelace.resources import ResourceStorageCollection

from .const import DOMAIN, INTEGRATION_VERSION
from .coordinator import FlexCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]
_WWW_DIR  = Path(__file__).parent / "www"
_URL_BASE = "/flex2"
_CARD_URL = f"{_URL_BASE}/flex2-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static path and schedule Lovelace resource registration.
    Add/update the card JS as a Lovelace resource (storage mode only)."""
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_URL_BASE, str(_WWW_DIR), cache_headers=False)]
        )
    except RuntimeError:
        pass  # already registered on reload
    try:
        lovelace: LovelaceData | None = hass.data.get("lovelace")
        if lovelace is None:
            raise Exception('LovelaceData instance not found')
        if lovelace.resource_mode != "storage":
            raise Exception('Lovelace not in storage mode')
        if not isinstance(lovelace.resources, ResourceStorageCollection): # Should be redundant.
            raise Exception('Lovelace not in storage mode')

        resources: ResourceStorageCollection = lovelace.resources
        await resources.async_get_info() # Forces loading.

        versioned_url = f"{_CARD_URL}?v={INTEGRATION_VERSION}"
        existing = [
            r for r in resources.async_items()
            if r["url"].startswith(_CARD_URL)
        ]

        if not existing:
            await resources.async_create_item(
                {"res_type": "module", "url": versioned_url}
            )
            _LOGGER.info("flex2: registered Lovelace resource %s", versioned_url)
        else:
            # Update URL if version changed
            resource = existing[0]
            if resource["url"] != versioned_url:
                await resources.async_update_item(
                    resource["id"],
                    {"res_type": "module", "url": versioned_url},
                )
                _LOGGER.info("flex2: updated Lovelace resource to %s", versioned_url)

    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning(
            "flex2: could not auto-register Lovelace resource (%s). "
            "Add manually: URL=%s  Type=JavaScript module", exc, _CARD_URL
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = FlexCoordinator(hass, entry)
    await coordinator.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: FlexCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_teardown()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
