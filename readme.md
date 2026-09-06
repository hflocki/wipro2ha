# Thitronik WiPro III - Home Assistant Integration (`wipro2ha`)

Custom Home Assistant Component to integrate the **Thitronik WiPro III** alarm system via Bluetooth Low Energy (BLE) GATT notifications.

**This integration is read-only.** It only subscribes to status notifications from the WiPro III module - it never writes to the device and cannot arm, disarm, or otherwise control the alarm system.

## Features

* **Real-time Armed Status**: Monitors whether the alarm system is armed or disarmed (`binary_sensor.wipro_alarmanlage_scharf`)[cite: 2].
* **Wireless Contact Monitoring**: Detects open magnetic radio window/door contacts (`binary_sensor.wipro_funkkontakt_gesamt`)[cite: 2].
* **Exact Hex-Match Contacts**: Individual sensors (`Kontakt 0` to `Kontakt 7`) mapped via exact hex-patterns to avoid false multi-triggering.
* **Human-Readable Alarm Reason**: Parses Byte 2 to decode and display the exact trigger reason (e.g., *Jammer Detection*, *Break-in Door*, *Radio Cable Loop*)[cite: 1, 6].
* **Live Hex Pattern Diagnostic**: Dedicated text sensor displaying Byte 6 as `0x0B (00001011)` for easy contact identification on your dashboard[cite: 6].
* **Push & Polling Modes**: Supports both persistent connection (Push / Notifications) and configurable Polling intervals[cite: 3, 4].
* **Coordinator-based Updates**: A shared `DataUpdateCoordinator` owns the BLE connection and distributes payloads efficiently[cite: 4].
* **Persistent Connection**: Uses `bleak-retry-connector` with background auto-reconnect loops for high availability[cite: 3, 4].

---

## Reverse-Engineered Status Data Protocol

The WiPro III sends status updates via BLE notifications on characteristic UUID `57695072-6f20-5374-6174-757320202020`[cite: 4].

### 8-Byte Payload Structure

Example payload: `01 8C 25 21 01 05 0B 00`

| Byte Index | Hex Value | Description |
| :--- | :--- | :--- |
| **Byte 0** | `0x01` | Unknown / System Indicator |
| **Byte 1** | `0x8C` | **Alarm Status** (`0x0C` bitmask = Armed, `0x80` = Status flag) |
| **Byte 2** | `0x25` | **Alarm Reason Code** (Decodes why the alarm was triggered; see map below)[cite: 1, 6] |
| **Byte 3** | `0x21` | Reserved / Unknown |
| **Byte 4** | `0x01` | Reserved / Unknown |
| **Byte 5** | `0x05` | Reserved / Unknown |
| **Byte 6** | `0x0B` | **Wireless Contacts** (`0x00` = All Closed, Exact Hex-Pattern for open sensors)[cite: 2, 6] |
| **Byte 7** | `0x00` | Reserved / Unknown |

### Alarm Reason Mapping (Byte 2)

| Code | Description |
| :--- | :--- |
| `0` | No Alarm / Clear[cite: 1] |
| `1 - 31` | Triggered Radio Contact Index (1 to 31)[cite: 1, 6] |
| `32` | Break-in Door (Interior Light)[cite: 1] |
| `33` | Break-in Door (CAN-Bus)[cite: 1] |
| `36` | Gas Detector Triggered[cite: 1] |
| `37` | Jammer Detection (Interference Detected)[cite: 1] |
| `38` | Radio Cable Loop Disconnected[cite: 1] |
| `225` | Panic Alarm (App / Button)[cite: 1] |

---

## Security Considerations

This integration only *reads* status data - it does not expose any way to arm, disarm, or otherwise control the alarm system[cite: 1]. The main thing to be aware of is that BLE status notifications can, in principle, be read by anyone within Bluetooth range (roughly 10-30 m) of the vehicle, not just Home Assistant. Whether that's a meaningful risk in practice depends on the WiPro III module's own BLE security (pairing/bonding, encryption) rather than on this integration.

---

## Installation via HACS (Custom Repository)

1. Open **Home Assistant** and navigate to **HACS** -> **Integrations**.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add repository URL: `https://github.com/hflocki/wipro2ha`
4. Category: **Integration**
5. Click **Add**, search for **Thitronik WiPro III**, and click **Download**.
6. Restart Home Assistant.

---

## Setup & Configuration

1. Go to **Settings** -> **Devices & Services** -> **Add Integration**.
2. Search for **Thitronik WiPro III**[cite: 3, 5].
3. Enter the **Bluetooth MAC Address** of your Thitronik BLE module (e.g., `AA:BB:CC:DD:EE:FF`)[cite: 3, 4].
4. Select Connection Mode (**Push** or **Polling**) and scan interval[cite: 3, 4].
5. Save the configuration[cite: 3]. The integration will validate connection before saving[cite: 3].

---

## Created Entities

All entities are grouped under a single **Thitronik WiPro III** device in Home Assistant[cite: 2, 6].

### Binary Sensors (`binary_sensor`)
* `binary_sensor.wipro_alarmanlage_scharf` (Safety Class: Armed / Disarmed)[cite: 2]
* `binary_sensor.wipro_funkkontakt_gesamt` (Window Class: Any wireless contact open)[cite: 2]
* `binary_sensor.wipro_kontakt_0` to `binary_sensor.wipro_kontakt_7` (Window Class: Individual exact-match contact sensors)[cite: 2]
* `binary_sensor.wipro_raw_data` (Diagnostic: Displays all raw bytes in state attributes)[cite: 2]
* `binary_sensor.wipro_byte_6_diagnose` (Diagnostic: On/Off state for Byte 6)[cite: 2]

### Text Sensors (`sensor`)
* `sensor.wipro_alarmgrund` (Diagnostic: Displays human-readable alarm trigger reasons)[cite: 6]
* `sensor.wipro_byte_6_hex_muster` (Diagnostic: Displays current Byte 6 pattern in Hex & Binary, e.g. `0x0B (00001011)`)[cite: 6]

---

## Debugging & Logging

To enable verbose logging for troubleshooting BLE connection or raw payload issues, add the following snippet to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.wipro2ha: debug
