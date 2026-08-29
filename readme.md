# Thitronik WiPro III - Home Assistant Integration (`wipro2ha`)

Custom Home Assistant Component to integrate the **Thitronik WiPro III** alarm system via Bluetooth Low Energy (BLE) GATT notifications.

**This integration is read-only.** It only subscribes to status notifications from the WiPro III module - it never writes to the device and cannot arm, disarm, or otherwise control the alarm system.

## Features

* **Real-time Armed Status**: Monitors whether the alarm system is armed or disarmed (`binary_sensor.wipro_alarmanlage_scharf`).
* **Wireless Contact Monitoring**: Detects open magnetic radio window/door contacts (`binary_sensor.wipro_funkkontakt_gesamt`).
* **Named Contact Sensors**: Exposes individual sensors for each mapped wireless contact (e.g. driver door, passenger door, skylight - see [Created Entities](#created-entities)).
* **Coordinator-based Updates**: A shared `DataUpdateCoordinator` owns the BLE connection and distributes the latest status to all entities, so parsing only happens once per notification.
* **Persistent Connection**: Uses `bleak-retry-connector` with background auto-reconnect loops for high availability.
* **Setup Validation**: When adding the integration, a short connection attempt confirms the module is actually reachable before the config entry is created.
* **Raw Hex Diagnostics**: Raw state entity for debugging and decoding BLE status payloads.

---

## Reverse-Engineered Status Data Protocol

The WiPro III sends status updates via BLE notifications on characteristic UUID `57695072-6f20-5374-6174-757320202020`.

### 8-Byte Payload Structure

Example payload: `01 8C 00 21 01 05 00 00`

| Byte Index | Hex Value | Description |
| :--- | :--- | :--- |
| **Byte 0** | `0x01` | Unknown / System Indicator |
| **Byte 1** | `0x8C` | **Alarm Status** (`0x0C` bitmask = Armed, `0x80` = Status flag) |
| **Byte 2** | `0x00` | Vehicle Status |
| **Byte 3** | `0x21` | Reserved / Unknown |
| **Byte 4** | `0x01` | Reserved / Unknown |
| **Byte 5** | `0x05` | Reserved / Unknown |
| **Byte 6** | `0x00` | **Wireless Contacts** (`0x00` = All Closed, Bitmask for open sensors) |
| **Byte 7** | `0x00` | Reserved / Unknown |

Full bit-level contact mapping for Byte 6 is documented in [`docs/nrf_connect_guide.md`](docs/nrf_connect_guide.md).

---

## Security Considerations

This integration only *reads* status data - it does not expose any way to arm, disarm, or otherwise control the alarm system. The main thing to be aware of is that BLE status notifications can, in principle, be read by anyone within Bluetooth range (roughly 10-30 m) of the vehicle, not just Home Assistant. Whether that's a meaningful risk in practice depends on the WiPro III module's own BLE security (pairing/bonding, encryption) rather than on this integration.

If you're evaluating whether to expose this project publicly:

* Check whether your module requires pairing/bonding before it will send notifications. If it does, casual eavesdropping is significantly harder.
* If you find that status data (or, worse, a writable/control characteristic) is accessible without any authentication, please report that to Thitronik directly rather than publishing exploit details - that would be a weakness in the device's own firmware, not in this integration.
* This project intentionally does not implement any write/control functionality, and contributions adding one should be considered carefully.

---

## Installation via HACS (Custom Repository)

1. Open **Home Assistant** and navigate to **HACS** -> **Integrations**.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add repository URL: `https://github.com/hflocki/wipro2ha`
4. Category: **Integration**
5. Click **Add**, search for **Thitronik WiPro III**, and click **Download**.
6. Restart Home Assistant.

*Note: For private repository usage, make sure your GitHub Personal Access Token (PAT) with `repo` scope is configured in the HACS integration settings.*

---

## Setup & Configuration

1. Go to **Settings** -> **Devices & Services** -> **Add Integration**.
2. Search for **Thitronik WiPro III**.
3. Enter the **Bluetooth MAC Address** of your Thitronik BLE module (e.g., `AA:BB:CC:DD:EE:FF`).
4. Save the configuration. The integration will attempt a short connection to confirm the module is reachable before creating the entry - if it fails, double-check the MAC address and that the module is powered on and in range.

---

## Created Entities

All entities are grouped under a single **Thitronik WiPro III** device in Home Assistant.

* `binary_sensor.wipro_alarmanlage_scharf` (Safety Class: Armed / Disarmed)
* `binary_sensor.wipro_funkkontakt_gesamt` (Window Class: Any wireless contact open)
* Individual named contact sensors (Window Class), one per mapped bit in Byte 6:
  * Fahrerhaustür, Beifahrertür, Fenster, Heckgarage, Dachluke
  * (Bits 5-7 are not yet mapped - see [`docs/nrf_connect_guide.md`](docs/nrf_connect_guide.md) to contribute a mapping)
* `binary_sensor.wipro_raw_data` (Diagnostic: Displays all 8 raw bytes in state attributes)

---

## License

MIT License


---

## References

* BLE protocol and central locking mechanism research by Matthias Harzheim at [Camperflower Blog](https://camperflower.de/smart-camper-zentralverriegelung-und-thitronik-alarmanlage/).


---

### 💬 Danksagung / Credits

Thanks to [@to0b](https://github.com/to0b)


<a href="https://www.buymeacoffee.com/hflocki" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="60" width="217">
</a>
