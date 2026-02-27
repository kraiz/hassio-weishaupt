"""The Weishaupt WEM integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import async_get as async_get_dev_reg

from .api import WeishauptApiClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import WeishauptDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weishaupt WEM from a config entry."""
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    session = async_get_clientsession(hass)
    client = WeishauptApiClient(
        host=host,
        username=username,
        password=password,
        session=session,
    )

    coordinator = WeishauptDataUpdateCoordinator(
        hass=hass,
        client=client,
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Ensure a parent device exists so child devices can reference it via `via_device`.
    dev_reg = async_get_dev_reg(hass)
    device_name = f"Weishaupt {entry.title}" if entry.title else "Weishaupt Systemgerät"
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Weishaupt",
        name=device_name,
        model="WEM-Systemgerät",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
