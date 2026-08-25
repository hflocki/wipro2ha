# Documentation: Reverse-Engineering WiPro III BLE Data via nRF Connect

This guide explains how to use Nordic Semiconductor's **nRF Connect for Mobile** app to capture, monitor, and map raw Bluetooth Low Energy (BLE) payloads from the Thitronik WiPro III alarm system.

---

## Prerequisites

1. **nRF Connect for Mobile** installed on your smartphone:
   * [Android (Google Play Store)](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp)
   * [iOS (Apple App Store)](https://apps.apple.com/app/nrf-connect-for-mobile/id1054362403)
2. Access to your vehicle equipped with the Thitronik WiPro III BLE module.

---

## 1. Connect to the WiPro III BLE Module

1. Open **nRF Connect** and grant Bluetooth permissions.
2. Tap **Scan** in the upper-right corner.
3. Look for your Thitronik module (often named `WiPro III`, `Thitronik`, or showing your device MAC address).
4. Tap **Connect** next to the device.

---

## 2. Locate the Status Characteristic

1. Once connected, expand the **Unknown Service** (UUID: `57695072-6f20-5374-6174-757320202020` or similar).
2. Locate the **Characteristic** with UUID:
   `57695072-6f20-5374-6174-757320202020`
3. Tap the **Triple-Down-Arrow icon** (or "Enable Notifications") next to the characteristic to subscribe to live updates.

---

## 3. Map Wireless Contacts (Byte 6 Mapping)

The status payload consists of 8 bytes in Hex format (e.g., `01 8C 00 21 01 05 00 00`). 
**Byte index 6** (the 7th byte pair) represents the wireless contact bitmask.

### Testing Procedure:

1. Keep all doors, windows, and hatches **closed**.
   * Expected payload: `... 00 00` (Byte 6 is `0x00`).
2. Open **one specific window/contact at a time** and observe the changes in Byte 6:

| Action / Opened Contact | Observed Hex Payload | Byte 6 Value | Bitmask | Bit Index |
| :--- | :--- | :--- | :--- | :--- |
| **All Closed** | `01 80 00 21 01 05 00 00` | `0x00` | `00000000` | None |
| **Driver Door** | `01 80 00 21 01 05 01 00` | `0x01` | `00000001` | **Bit 0** |
| **Passenger Door** | `01 80 00 21 01 05 02 00` | `0x02` | `00000010` | **Bit 1** |
| **Side Window Left** | `01 80 00 21 01 05 04 00` | `0x04` | `00000100` | **Bit 2** |
| **Rear Garage Door** | `01 80 00 21 01 05 08 00` | `0x08` | `00001000` | **Bit 3** |
| **Skylight / Hatch** | `01 80 00 21 01 05 10 00` | `0x10` | `00010000` | **Bit 4** |

---

## 4. Multi-Contact Bitwise Operations

When multiple contacts are open at the same time, the WiPro III combines them using a bitwise **OR** operation:

* **Example:** Driver Door (`0x01`) + Passenger Door (`0x02`) open simultaneously:
  * Byte 6 value: `0x01 | 0x02 = 0x03`
  * Payload: `01 80 00 21 01 05 03 00`

---

## 5. Integrating mapped values into `binary_sensor.py`

Once mapped, rename the bit sensors in your integration to reflect the real vehicle names:

```python
# Example mapping in binary_sensor.py
WIPRO_SENSORS = [
    WiProSensorConfig(name="Fahrerhaustür", byte_index=6, bitmask=0x01),
    WiProSensorConfig(name="Beifahrertür", byte_index=6, bitmask=0x02),
    WiProSensorConfig(name="Fenster Heck", byte_index=6, bitmask=0x04),
]

[![AI Generated](https://img.shields.io/badge/AI_Generated-Gemini-8E44AD?style=for-the-badge&logo=google-gemini&logoColor=white)](https://github.com/hflocki/wipro2ha)
