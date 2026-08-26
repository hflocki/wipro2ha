"""Test scenarios for the WiPro III config flow's connection validation.

These tests mock out the BLE layer (async_ble_device_from_address,
establish_connection) rather than talking to real hardware or a full
Home Assistant test harness - they only exercise _async_can_connect(),
which is the piece of logic that decides whether setup succeeds.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.wipro2ha.config_flow import ThitronikConfigFlow


def _make_flow():
    flow = ThitronikConfigFlow()
    flow.hass = MagicMock()
    return flow


@pytest.mark.asyncio
async def test_can_connect_returns_false_when_device_not_found():
    """No BLE device discovered -> validation fails without attempting a connection."""
    flow = _make_flow()

    with patch(
        "custom_components.wipro2ha.config_flow.async_ble_device_from_address",
        return_value=None,
    ), patch(
        "custom_components.wipro2ha.config_flow.establish_connection",
        new_callable=AsyncMock,
    ) as mock_connect:
        result = await flow._async_can_connect("AA:BB:CC:DD:EE:FF")

    assert result is False
    mock_connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_can_connect_returns_true_and_disconnects_on_success():
    """A reachable device connects successfully and is disconnected again afterwards."""
    flow = _make_flow()
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()

    with patch(
        "custom_components.wipro2ha.config_flow.async_ble_device_from_address",
        return_value=MagicMock(),
    ), patch(
        "custom_components.wipro2ha.config_flow.establish_connection",
        new_callable=AsyncMock,
        return_value=mock_client,
    ):
        result = await flow._async_can_connect("AA:BB:CC:DD:EE:FF")

    assert result is True
    mock_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_can_connect_returns_false_on_connection_error():
    """A connection error (e.g. device out of range) is treated as unreachable."""
    flow = _make_flow()

    with patch(
        "custom_components.wipro2ha.config_flow.async_ble_device_from_address",
        return_value=MagicMock(),
    ), patch(
        "custom_components.wipro2ha.config_flow.establish_connection",
        new_callable=AsyncMock,
        side_effect=TimeoutError("no route to device"),
    ):
        result = await flow._async_can_connect("AA:BB:CC:DD:EE:FF")

    assert result is False
