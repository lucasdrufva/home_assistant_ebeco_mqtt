# Home Assistant Ebeco MQTT

Control your [Ebeco](https://www.ebeco.com/) thermostats from Home Assistant locally using MQTT.  
This custom integration allows you to bypass the cloud by communicating directly with the EB-Connect WiFi module.

---

## Features

This integration provides:
- Floor temperature sensor
- A thermostat entity for setting the target temperature

**Note:** For advanced configuration (schedules, sensor settings, etc.), you must use the Ebeco mobile app or adjust settings physically via the thermostat.

---

## Installation

To use this integration, your EB-Connect WiFi module must be modified to connect to your own MQTT broker instead of the default Azure IoT Hub.

The module trusts DigiCert Global Root G2. If your MQTT broker already uses a certificate signed by this CA, you can skip steps 7–10.

> ⚠️ **Warning**: This process involves modifying firmware on the device and may void warranties or cause bricking if done incorrectly. Proceed at your own risk.

### Required Tools

- ESP32-compatible programmer (e.g., USB-to-Serial adapter)
- Python tools: `esptool`, `esp32knife.py`, `parttool.py`, `otatool.py`, `nvs_partition_gen.py`
- Root certificate bundle that has signed your MQTT broker (`ca.pem`)

---

### Step-by-Step: Modify EB-Connect WiFi Module

1. **Connect Programmer to ESP32**
   - Attach your USB-to-Serial adapter to the EB-Connect module’s UART pins.

2. **Dump the flash:**
   ```bash
   esptool.py -p [SERIAL_PORT] -b 1156200 read_flash 0 0x400000 flash.bin
   ```

3. **Analyze flash contents:**

   ```bash
   esp32knife.py --chip=esp32 load_from_file ./flash.bin
   ```

4. **Modify MQTT connection string:**

   ```bash
   cp parsed/part.0.nvs.cvs nvs.csv
   # Edit `nvs.csv` in a text editor and replace the hostname in `connstring` with your own MQTT broker's hostname.
   ```

5. **Regenerate the NVS partition:**

   ```bash
   nvs_partition_gen.py nvs.csv nvs_patched.bin 16384
   ```

   > ⚠️ `16384` is the NVS partition size — verify this in the partition table output from `esp32knife`.

6. **Write the patched NVS partition to flash:**

   ```bash
   parttool.py --port [SERIAL_PORT] write_partition --partition-name=nvs --input nvs_patched.bin
   ```

7. **Patch root certificates:**

   ```bash
   ./patch_cert_bundle.py --input parsed/part.3.ota_0 --certs ca.pem --output ota_0_patched.bin --index 0,1
   ```

8. **Fix image headers:**

    Using a custom fork of [esptool](https://github.com/lucasdrufva/esptool)

   ```bash
   esptool.py --chip esp32 image_repair ota_0_patched.bin
   ```

9. **Write patched OTA image:**

   ```bash
   otatool.py --port [SERIAL_PORT] --slot 0 --input ota_0_patched.bin
   ```

10. **Activate the new OTA partition:**

    ```bash
    otatool.py --port [SERIAL_PORT] switch_ota_partition --slot 0
    ```

---

## Configuration in Home Assistant

Once your EB-Connect module connects to your MQTT broker, copy the files to the custom_components folder in Home Assistant config. Then restart Home Assistant and add this integration

---

## Attribution

This project includes portions of code originally derived from
[home\_assistant\_ebeco](https://github.com/joggs/home_assistant_ebeco) by [joggs],
used under the terms of the MIT License.

The code has been modified to suit the needs of this custom MQTT-based integration.

