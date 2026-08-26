# Testing wipro2ha

This project uses `pytest` to test the sensor logic and config flow without needing real Thitronik WiPro III hardware. All BLE communication is mocked - the tests only exercise the integration's own parsing and decision logic.

## Setup

1. Create and activate a virtual environment in the **repository root** (not inside `tests/`):

   ```bash
   cd wipro2ha-main
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
   ```

2. Install the test dependencies:

   ```bash
   pip install -r requirements-test.txt
   ```

   This pulls in `pytest`, `pytest-asyncio`, a lightweight Home Assistant test environment (`pytest-homeassistant-custom-component`), and the integration's own runtime dependencies (`bleak`, `bleak-retry-connector`, `voluptuous`, `pyserial`).

   > `pyserial` is required because `homeassistant.components.bluetooth` transitively imports `homeassistant.components.usb`, which needs it - even though this integration never touches a serial port directly.

3. Run the tests from the `tests/` folder:

   ```bash
   cd tests
   pytest
   ```

   Each test file adds the repository root to `sys.path` itself (`sys.path.insert(0, Path(__file__).resolve().parent.parent)`), so this works regardless of which directory you run `pytest` from.

Expected result: `8 passed`.

## What the tests cover

### `test_binary_sensor.py`

These tests call `update_from_hex()` directly with hand-crafted byte payloads - no BLE connection, no coordinator, no Home Assistant runtime involved. They verify the pure parsing logic:

| Test | What it checks |
| :--- | :--- |
| `test_alarm_sensor_armed_state` | Byte 1 with `0x8C` is read as "armed"; `0x80` as "disarmed" (`WiProAlarmSensor` exact-bitmask matching) |
| `test_window_contact_bitmask` | Byte 6 bit-level detection: a single bit set is detected as "open", a different bit set is correctly read as "closed" for the sensor watching bit 0 |
| `test_raw_sensor_exposes_all_bytes` | `WiProRawSensor` splits an 8-byte payload into individual `byte_0` ... `byte_7` hex attributes |
| `test_raw_sensor_handles_short_payload` | `WiProRawSensor` doesn't crash on a payload shorter than 8 bytes; missing bytes become `None` |
| `test_unique_id_and_device_info_set_when_entry_present` | `unique_id` and `device_info` are correctly derived from a (fake) config entry |

`coordinator` and `entry` are passed as `None` in these tests - the sensor classes are built to work standalone for exactly this reason, so the parsing logic can be tested in isolation from the BLE/coordinator machinery.

### `test_config_flow.py`

These tests mock out the BLE layer (`async_ble_device_from_address`, `establish_connection`) with `unittest.mock`, so no real Bluetooth traffic happens. They verify `ThitronikConfigFlow._async_can_connect()` - the setup-time reachability check:

| Test | What it checks |
| :--- | :--- |
| `test_can_connect_returns_false_when_device_not_found` | No BLE device discovered -> returns `False` without even attempting a connection |
| `test_can_connect_returns_true_and_disconnects_on_success` | Device found, connection succeeds -> returns `True`, and the client is disconnected again afterwards |
| `test_can_connect_returns_false_on_connection_error` | Connection attempt raises an error (e.g. device out of range) -> returns `False` instead of crashing |

## What is *not* covered (yet)

- `coordinator.py`'s actual connect/reconnect loop (`_connect_and_subscribe`) - this involves real background tasks and long-running `while` loops, which would need a more involved async test setup (e.g. `pytest-asyncio` with controlled time via `pytest_freezer`, already available as a dependency).
- `__init__.py`'s `async_setup_entry` / `async_unload_entry` - these mostly wire other already-tested pieces together.
- Bits 5-7 of the contact bitmask, since they aren't mapped to real-world contacts yet (see `docs/nrf_connect_guide.md`).

## Adding a new test

If you map a new contact bit or add a new sensor, add a case following the existing pattern in `test_binary_sensor.py`: construct the sensor with `coordinator=None, entry=None`, call `update_from_hex()` with a payload, and assert on `.is_on` or `.extra_state_attributes`.
