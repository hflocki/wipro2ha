"""Test scenarios for WiPro III binary sensors."""

import sys
from pathlib import Path

# Add project root directory to sys.path to allow imports from custom_components
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.wipro2ha.binary_sensor import (
    WiProAlarmSensor,
    WiProRawSensor,
    WiProSensor,
)

# coordinator/entry are only needed for the coordinator-driven update path
# and for building unique_id/device_info - the sensors' update_from_hex()
# logic is tested directly here without either, so both are None.


def test_alarm_sensor_armed_state():
    """Test if byte 1 correctly detects armed and disarmed states."""
    sensor = WiProAlarmSensor(
        coordinator=None,
        entry=None,
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
    # Initialize sensor listening specifically to Bit 0 (bitmask 0x01)
    bit0_sensor = WiProSensor(
        coordinator=None,
        entry=None,
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


def test_raw_sensor_exposes_all_bytes():
    """Test that WiProRawSensor splits the payload into per-byte hex attributes."""
    sensor = WiProRawSensor(coordinator=None, entry=None, name="Raw Data")

    payload = bytes.fromhex("018c00210105ab00")
    sensor.update_from_hex(payload)

    assert sensor.is_on is True
    attrs = sensor.extra_state_attributes
    assert attrs["raw_hex"] == "018c00210105ab00"
    assert attrs["byte_0"] == "0x01"
    assert attrs["byte_1"] == "0x8C"
    assert attrs["byte_6"] == "0xAB"
    assert attrs["byte_7"] == "0x00"


def test_raw_sensor_handles_short_payload():
    """Test that WiProRawSensor doesn't crash on a payload shorter than 8 bytes."""
    sensor = WiProRawSensor(coordinator=None, entry=None, name="Raw Data")

    short_payload = bytes.fromhex("0180")
    sensor.update_from_hex(short_payload)

    attrs = sensor.extra_state_attributes
    assert attrs["byte_0"] == "0x01"
    assert attrs["byte_1"] == "0x80"
    assert attrs["byte_2"] is None
    assert attrs["byte_7"] is None


def test_unique_id_and_device_info_set_when_entry_present():
    """Test that unique_id/device_info are derived from the config entry when given."""

    class FakeEntry:
        entry_id = "abc123"
        title = "Thitronik (AA:BB:CC:DD:EE:FF)"

    sensor = WiProAlarmSensor(
        coordinator=None,
        entry=FakeEntry(),
        name="Alarmanlage Scharf",
        byte_index=1,
        bitmask=0x0C,
    )

    assert sensor.unique_id == "abc123_byte1_eq0c"
    assert sensor.device_info["identifiers"] == {("wipro2ha", "abc123")}
