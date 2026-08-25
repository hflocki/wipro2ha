"""Test scenarios for WiPro III binary sensors."""

import sys
from pathlib import Path

# Add project root directory to sys.path to allow imports from custom_components
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.wipro2ha.binary_sensor import WiProAlarmSensor, WiProSensor


def test_alarm_sensor_armed_state():
    """Test if byte 1 correctly detects armed and disarmed states."""
    # Mock HomeAssistant instance
    hass = None

    sensor = WiProAlarmSensor(
        hass=hass,
        name="Alarmanlage Scharf",
        byte_index=1,
        bitmask=0x0C,
    )

    # Test Armed Payload: Byte 1 contains 0x8C (0x8C & 0x0C == 0x0C -> True)
    armed_payload = bytes.fromhex("018c002101050000")
    sensor.update_from_hex(armed_payload)
    assert sensor.is_on is True

    # Test Disarmed Payload: Byte 1 contains 0x80 (0x80 & 0x0C == 0x00 -> False)
    disarmed_payload = bytes.fromhex("0180002101050000")
    sensor.update_from_hex(disarmed_payload)
    assert sensor.is_on is False


def test_window_contact_bitmask():
    """Test if byte 6 correctly detects open contacts per individual bit."""
    # Mock HomeAssistant instance
    hass = None

    # Initialize sensor listening specifically to Bit 0 (bitmask 0x01)
    bit0_sensor = WiProSensor(
        hass=hass,
        name="Bit 0 Sensor",
        byte_index=6,
        bitmask=0x01,
    )

    # Payload with Byte 6 set to 0x01 (Window/Contact 1 open)
    payload_bit0_open = bytes.fromhex("0180002101050100")
    bit0_sensor.update_from_hex(payload_bit0_open)
    assert bit0_sensor.is_on is True

    # Payload with Byte 6 set to 0x02 (Window/Contact 2 open, Contact 1 closed)
    payload_bit1_open = bytes.fromhex("0180002101050200")
    bit0_sensor.update_from_hex(payload_bit1_open)
    assert bit0_sensor.is_on is False
