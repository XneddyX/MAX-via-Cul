"""Switch entities for MAX! integration control."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from . import CulMaxConfigEntry
from .const import DOMAIN
from .coordinator import CulMaxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CulMaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities for MAX! integration."""
    coordinator: CulMaxCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = [CulMaxPairingSwitch(coordinator)]

    async_add_entities(entities)


class CulMaxPairingSwitch(SwitchEntity):
    """Switch to start and stop MAX! pairing mode."""

    _attr_has_entity_name = True
    _attr_name = "Pairing Mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:link-variant-plus"

    def __init__(self, coordinator: CulMaxCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = (
            f"{DOMAIN}_pairing_switch_{coordinator.host.replace('.', '_')}_{coordinator.port}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"controller_{coordinator.host}:{coordinator.port}")},
            name=f"MAX! CUL ({coordinator.host}:{coordinator.port})",
            manufacturer="eQ-3 / CULFW",
            model="MAX! via CUL",
        )
        self._refresh_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.add_pairing_state_listener(self._on_pairing_state_update)
        )
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._on_timer,
                timedelta(seconds=1),
            )
        )

    def _refresh_state(self) -> None:
        self._attr_is_on = self._coordinator.is_pairing_mode

    @callback
    def _on_pairing_state_update(self) -> None:
        self._refresh_state()
        self.async_write_ha_state()

    @callback
    def _on_timer(self, now) -> None:
        if not self._coordinator.is_pairing_mode:
            return
        self._refresh_state()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start pairing mode."""
        await self._coordinator.async_start_pairing()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop pairing mode."""
        await self._coordinator.async_stop_pairing()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pairing_until = self._coordinator.pairing_until
        return {
            "pairing_until": pairing_until.isoformat() if pairing_until else None,
            "remaining_seconds": self._coordinator.get_pairing_remaining_seconds(),
            "host": self._coordinator.host,
            "port": self._coordinator.port,
        }
