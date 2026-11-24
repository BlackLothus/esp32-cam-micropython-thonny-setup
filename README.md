# ESP32-CAM (AI-Thinker) with MicroPython on Linux: Troubleshooting & Setup Guide

A practical, step-by-step guide to diagnosing, recovering, and setting up an **ESP32-CAM** board with an **ESP32-CAM-MB** carrier board on Linux (Pop!\_OS / Ubuntu) using **MicroPython** and **Thonny IDE**.

## TL;DR

If your ESP32-CAM + ESP32-CAM-MB carrier board is stuck on `Device is busy or does not respond` on Linux and ignores the physical `RST` button, the board is probably not dead. In my case, the lockups were most likely caused by Linux serial tools asserting **DTR/RTS** (holding the board in reset) and unstable PC USB power. The reliable workaround is:

1. Connect once over USB using `pyserial`'s `miniterm` with DTR/RTS forced off (`--dtr 0 --rts 0`) to configure Wi-Fi (`boot.py`) and **WebREPL** (`webrepl_cfg.py`).
2. Move the board to a stable external 5V USB wall charger and develop wirelessly in Thonny over WebREPL.
3. Run scripts from Thonny's shell with `exec(open('server.py').read())` instead of pressing `Run (F5)` to avoid `[Errno 111]`.

## Table of Contents

1. [The Problem (and Why This Guide Exists)](#the-problem-and-why-this-guide-exists)
2. [Hardware, Software, and Repository Structure](#hardware-software-and-repository-structure)
3. [Phase 0: Hardware Check of the Bottom Board (CH340)](#phase-0-hardware-check-of-the-bottom-board-ch340)
4. [Phase 1: Isolated Test of the Top Board (ESP32-CAM)](#phase-1-isolated-test-of-the-top-board-esp32-cam)
5. [Phase 2: Flashing MicroPython Firmware with Camera Driver](#phase-2-flashing-micropython-firmware-with-camera-driver)
6. [Phase 3: Testing the OV2640 Sensor and Capturing a Photo](#phase-3-testing-the-ov2640-sensor-and-capturing-a-photo)
7. [Phase 4: Testing the Bottom Board (ESP32-CAM-MB) on Linux](#phase-4-testing-the-bottom-board-esp32-cam-mb-on-linux)
8. [Phase 5: Verifying the DTR/RTS Hypothesis with Python (`pyserial`) and `miniterm`](#phase-5-verifying-the-dtrrts-hypothesis-with-python-pyserial-and-miniterm)
9. [Phase 6: Choosing a Workflow (Path A vs Path B)](#phase-6-choosing-a-workflow-path-a-vs-path-b)
10. [Phase 7: Implementing Path A (WebREPL + Camera Server)](#phase-7-implementing-path-a-webrepl--camera-server)
11. [Phase 8: Quick Maintenance Guide](#phase-8-quick-maintenance-guide)
12. [Phase 9: Thonny's `[Errno 111]` Bug on WebREPL and Shell Management](#phase-9-thonnys-errno-111-bug-on-webrepl-and-shell-management)
13. [Phase 10: Camera Parameters and Final Script (`server.py`)](#phase-10-camera-parameters-and-final-script-serverpy)
14. [Phase 11: Known Limitations, Signal Diagnostics, and Security](#phase-11-known-limitations-signal-diagnostics-and-security)

## The Problem (and Why This Guide Exists)

It all started on a Saturday afternoon while trying to test an ESP32-CAM for a university project. After several failed attempts, it seemed almost certain that the board was fried or dead on arrival. With some patience, isolated hardware testing, and persistence, I finally found a reliable workflow.

Since I am still a student, this document is not meant to be an infallible academic manual; it is simply an honest account of my own experience. My only goal is to **save hours of troubleshooting** for other beginners (or anyone rusty with MicroPython on the ESP32-CAM) and, above all, to **save perfectly working boards from ending up in the trash**.

As soon as I plugged the ESP32-CAM into Thonny on Linux, no matter what I tried, I kept getting this error:

```text
Device is busy or does not respond. Your options:
- wait until it completes current work;
- use Ctrl+C to interrupt current work;
- reset the device and try again;
- check connection properties;
- make sure the device has suitable MicroPython / CircuitPython / firmware;
- make sure the device is not in bootloader mode.

Could not interrupt current process. Please wait, try again or select Stop/Restart!
```

None of the reset buttons (neither on the ESP32-CAM nor on the bottom carrier board) responded, and Thonny's Stop/Restart button did nothing.

*Note: English is not my first language, so I used AI to help with the translation. All troubleshooting, wiring, and tests were done on my own hardware.*

## Hardware, Software, and Repository Structure

**Hardware tested:**

- **Top board:** ESP32-CAM (AI-Thinker) with **OV2640** camera sensor and PSRAM.
- **Bottom board:** **ESP32-CAM-MB** programmer carrier board (CH340 USB-to-Serial chip).
- **Test tools:** A second ESP32 (classic **ESP32-WROOM**) used as a USB-to-Serial bridge + External 5V Power Supply + External 5V USB wall charger.

**Software environment:**

- Linux (Pop!\_OS / Ubuntu), Thonny IDE, MicroPython, `pyserial` (`miniterm`).

**Final outcome:**  
Both the ESP32-CAM (including the OV2640 sensor) and the ESP32-CAM-MB carrier board were **completely functional**. In my case, the freezes were most likely caused by PC USB power delivery issues and how Linux tools (Thonny, `screen`, `mpremote`) handle the serial **DTR/RTS** signals on this carrier board. The final working setup uses **external power + WebREPL on Thonny over Wi-Fi**.

### Repository Structure

```text
.
|-- README.md                  # This complete guide
|-- .gitignore                 # Protects local credentials (boot.py, webrepl_cfg.py, secrets.py)
|-- code/
    |-- 01_test_flash.py       # Basic onboard Flash LED test on GPIO 4
    |-- 02_test_camera.py      # OV2640 initialization and test.jpg capture
    |-- boot_template.py       # Clean template for auto Wi-Fi + WebREPL
    |-- server.py              # Final HTTP server (Streaming, Photo, Deep Sleep, Stop)
```

## Phase 0: Hardware Check of the Bottom Board (CH340)

Before testing the camera itself, I wanted to rule out a dead or factory-defective bottom board.

- **Check performed:** Connected *only* the **ESP32-CAM-MB** carrier board (without the ESP32-CAM mounted on top) to the PC and ran:

  ```bash
  lsusb
  ```

- **Output:**

  ```text
  Bus 001 Device 025: ID 1a86:7523 QinHeng Electronics CH340 serial converter
  ```

- **Conclusion:** Seeing `QinHeng Electronics CH340 serial converter` (`ID 1a86:7523`) confirmed that the USB-to-Serial chip was electrically intact and recognized by Linux. The issue wasn't a dead carrier board, but rather communication or power between the two boards.

## Phase 1: Isolated Test of the Top Board (ESP32-CAM)

To rule out interference from the bottom board, the top ESP32-CAM board was tested on its own using a classic **ESP32-WROOM** as a USB-to-Serial bridge and a dedicated external 5V power supply.

> ### Warning: Can I use an ESP32-S3 as a serial bridge?
>
> **Not when using the native USB port of an ESP32-S3.** When trying to use an ESP32-S3's native USB port as a serial bridge (connecting its `EN` pin to `GND` to disable its CPU), the serial port completely disappears from the system (`ls /dev/ttyACM* /dev/ttyUSB*` returns `No such file or directory`).
>
> **Technical reason:**
> - **ESP32-S3 (native USB port):** Has its USB controller integrated **natively inside the main processor**. Pulling `EN` to `GND` to keep the CPU asleep also shuts down the USB controller, making `/dev/ttyACM0` vanish. *(Note: many dual-USB ESP32-S3 devkits also include a second "UART" USB port wired to an external USB-to-Serial chip, which can work as a bridge; this limitation only applies to the native USB port.)*
> - **ESP32-WROOM (classic):** Uses an **external, separate** USB-to-Serial converter chip. Even when holding the main microcontroller in reset (`EN -> GND`), the USB chip stays powered and visible as `/dev/ttyUSB0`.

### Wiring (ESP32-WROOM Bridge + External Power Supply)

> **Safety Note:** **Never** connect the `5V` pin of the bridge ESP32 and the external power supply together. Also, avoid powering the ESP32-CAM from the bridge ESP32's 5V pin, use an external power supply dedicated to the ESP32-CAM. However, you **must** share a common `GND` across all three components (power supply, bridge ESP32, and ESP32-CAM).

| Source | Destination | Function / Notes |
| --- | --- | --- |
| **Bridge ESP32 (`EN` / `RST`)** | **Bridge ESP32 (`GND`)** | **Crucial:** disables the bridge CPU so you only use its USB-to-Serial chip. |
| **Power Supply (`+5V`)** | **ESP32-CAM (`5V`)** | Dedicated power (at least 1A) to prevent *brownout* reboots. |
| **Power Supply (`GND`)** | **ESP32-CAM (`GND`)** + **Bridge ESP32 (`GND`)** | Common ground required for serial communication. |
| **Bridge ESP32 (`TX0`)** | **ESP32-CAM (`U0T`)** | Straight connection (see note below). |
| **Bridge ESP32 (`RX0`)** | **ESP32-CAM (`U0R`)** | Straight connection (see note below). |
| **ESP32-CAM (`IO0`)** | **ESP32-CAM (`GND`)** | **Only during firmware flashing** (disconnect for normal operation). |

> **Why straight `TX -> TX` and `RX -> RX`?** Normally UART connections are crossed, so this might look like a typo. However, with `EN` tied to `GND`, the bridge devkit's CPU is disabled and its `TX0`/`RX0` header pins are already wired internally to the RX/TX lines of its onboard USB-to-Serial chip, so you connect `TX0` directly to `U0T` and `RX0` directly to `U0R`.

### Common Issue in This Phase

- **Symptom:** Thonny runs code even when the external power supply is off, or turning on the CAM outputs garbled characters followed by `Device is busy or does not respond`.
- **Solution:** Double-check that **`EN -> GND`** is firmly connected on the bridge ESP32, that you are using only the top board of the ESP32-CAM, and that **`IO0` is NOT connected to `GND`** yet (that is only needed in Phase 2).

### Basic ESP32 Test (Flash LED on GPIO 4)

Ready-to-use file: [`code/01_test_flash.py`](code/01_test_flash.py)

*(Note: the small red status LED on `GPIO 33` is an SMD LED on the back of the board; the bright white square Flash LED on the camera side is on `GPIO 4`.)*

```python
from machine import Pin
import time

flash = Pin(4, Pin.OUT)

for i in range(3):
    flash.value(1)
    time.sleep(0.1)
    flash.value(0)
    time.sleep(0.5)

print("Flash test complete!")
```

- **Outcome:** The Flash LED blinks three times. The ESP32 board itself works.
- **Note:** If your ESP32-CAM does not have MicroPython installed yet, you can either flash a generic ESP32 firmware directly via Thonny (following the steps in Phase 2 without downloading an external file) or jump straight to Phase 2 to flash the camera-enabled firmware.

## Phase 2: Flashing MicroPython Firmware with Camera Driver

Standard MicroPython firmware does not include the `camera` module required for the OV2640 sensor.

- **Firmware used:** GitHub repository [`lemariva/micropython-camera-driver`](https://github.com/lemariva/micropython-camera-driver) (`firmware` folder), file installed: `micropython_v1.21.0_camera_no_ble.bin`.

### Flashing Procedure via Thonny

1. Connect the jumper **`IO0 -> GND`** on the ESP32-CAM and press the **`RST`** button on the back of the board once.
2. In Thonny, go to **`Run > Configure interpreter...`** -> select **`MicroPython (ESP32)`** -> click **`Install or update MicroPython (esptool)`**.
3. Select the serial port (`/dev/ttyUSB0`), click the menu icon (three horizontal lines) -> **`Select local MicroPython image`** -> pick the downloaded `.bin` file, keeping *Erase flash* checked.
4. Once finished (`Done!`), **disconnect the `IO0 -> GND` jumper**, press **`RST`** on the CAM, and click **Stop/Restart** in Thonny.

## Phase 3: Testing the OV2640 Sensor and Capturing a Photo

### 1. Initialization and RAM Capture Test

```python
import camera

ok = camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
print("Camera initialized:", ok)

if ok:
    buf = camera.capture()
    if buf:
        print("Capture succeeded! Image size:", len(buf), "bytes")
    else:
        print("Error: capture() returned empty")
    camera.deinit()
```

- **Expected output:** `Camera initialized: True` - `Capture succeeded! Image size: ~12000 bytes`.

### 2. `OSError: Camera Init Failed`

- **Likely cause:** Thonny's *soft reboot* does not physically reset the OV2640 sensor, which can likely remain in a locked state between consecutive runs.
- **Solution:** Perform a physical **hard reset** (press `RST` on the board) and always include a preventive `camera.deinit()` at the beginning of your script.

### 3. Saving and Viewing a Photo (`test.jpg`)

Ready-to-use file: [`code/02_test_camera.py`](code/02_test_camera.py)

```python
import camera

try:
    camera.deinit()
except Exception:
    pass

camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
buf = camera.capture()
camera.deinit()

with open("test.jpg", "wb") as f:
    f.write(buf)

print("Image saved! Size:", len(buf), "bytes")
```

- **How to view the photo in Thonny:** Go to **`View > Files`**, right-click `test.jpg` under **MicroPython device** -> **`Download to...`**. *(Remember to peel off the protective plastic film from the lens ^.^)*

## Phase 4: Testing the Bottom Board (ESP32-CAM-MB) on Linux

Once the top board was confirmed working, mounting it back onto the **ESP32-CAM-MB** carrier board (microSD slot aligned with the micro-USB port, camera facing up) brought the exact same freezes back:

- **In Thonny (`/dev/ttyUSB0`):** `Device is busy or does not respond`, even after pressing `RST`.
- **Carrier board + CAM via `screen /dev/ttyUSB0 115200`:** Output was either completely blank from the start or cut off mid-line (in my case: `"0x1 (POWERON_RESET),boot:0x13 (S"`), and the physical `RST` button became completely unresponsive.

### Likely Diagnosis (The DTR/RTS Behavior on Linux)

On the **ESP32-CAM-MB** carrier board, the auto-reset circuit wired to the CH340 chip relies on the serial **DTR** and **RTS** lines. In my case, the issue was most likely caused by `screen`, Thonny, and `mpremote` asserting DTR/RTS by default when opening `/dev/ttyUSB0` on Linux, which pulls the ESP32 reset pin (`EN`) low and keeps the board frozen—making even the physical `RST` button ineffective. While other driver or hardware quirks can exist depending on the setup, forcing DTR and RTS to `0` immediately resolved the lockup on my machine.

## Phase 5: Verifying the DTR/RTS Hypothesis with Python (`pyserial`) and `miniterm`

To test this hypothesis, we need to open the serial port while explicitly forcing **DTR and RTS off (`0`)**.

> **Linux Permissions Note:** If you get a `Permission denied` error on `/dev/ttyUSB0`, add your user to the `dialout` group and log out/back in:
>
> ```bash
> sudo usermod -aG dialout $USER
> ```

1. **Install `pyserial` on Pop!\_OS / Ubuntu:**  
   On recent Debian/Ubuntu-based distros, `pip install pyserial` is blocked by PEP 668 (`externally-managed-environment`). Install it via `apt`:

   ```bash
   sudo apt update && sudo apt install -y python3-serial
   ```

2. **Serial read test with DTR/RTS disabled:**

   ```bash
   python3 -c "import serial, time; s=serial.Serial('/dev/ttyUSB0', 115200); s.dtr=False; s.rts=False; print('Press RST on the carrier board...'); [print(s.read(s.in_waiting or 1).decode(errors='ignore'), end='', flush=True) for _ in iter(int, 1)]"
   ```

   - **Outcome:** Pressing `RST` on the carrier board finally prints the full boot log all the way to the MicroPython `>>>` prompt.

   > **Troubleshooting `[Errno 16] Device or resource busy`:**  
   > On Linux, usually only one program can access `/dev/ttyUSB0` at a time. If you get this error, another process (usually Thonny, a background `screen` session, or `miniterm`) is still holding the port open.
   >
   > 1. Check which process is using the port:
   >
   >    ```bash
   >    lsof /dev/ttyUSB0
   >    ```
   >
   > 2. Close the process:
   >    - **Thonny:** close it or switch the interpreter to *Local Python 3* / *WebREPL*.
   >    - **`screen`:** run `killall screen`.
   >    - **Any other process:** stop it with `kill <PID>` (using the PID from step 1).
   > 3. Run `lsof /dev/ttyUSB0` again to confirm the output is empty, then retry the `python3 -c` command.

3. **Tools tested that did NOT bypass the lockup on my setup:**
   - Switching Thonny's interpreter to `MicroPython (generic) • USB Serial @ /dev/ttyUSB0`: still `Device is busy`.
   - `mpremote` (`pipx install mpremote` -> `mpremote connect /dev/ttyUSB0 repl`): hangs on `Connected to MicroPython at /dev/ttyUSB0` with no response.

4. **Working interactive shell (`miniterm`):**

   ```bash
   python3 -m serial.tools.miniterm /dev/ttyUSB0 115200 --dtr 0 --rts 0
   ```

   - **Outcome:** Pressing `RST` brings up `>>>`. Typing `print("hello")` returns `hello`. *(To exit `miniterm`: press **`Ctrl+]`** — if **`]`** needs AltGr on your keyboard layout, `Ctrl+5` usually sends the same key.)*

## Phase 6: Choosing a Workflow (Path A vs Path B)

With all hardware confirmed healthy, there are two main ways to program the board on Linux:

- **Path A (WebREPL in Thonny over Wi-Fi — Recommended):** One-time setup via `miniterm`, then use the carrier board strictly for power (via an external wall charger) and develop over Wi-Fi in Thonny.
- **Path B (USB-only with ESP32 Bridge + `miniterm`):** Use the carrier board only to read logs, and wire up the ESP32 bridge whenever you need to upload files.

| Criteria | Path A (Wi-Fi WebREPL) | Path B (USB + ESP32 Bridge) |
| --- | --- | --- |
| **Pros** | No programming cables, bypasses the DTR/RTS lockup, can be powered by an external wall charger (more stable), easy to place the camera anywhere. | Does not depend on Wi-Fi or a router; supports full firmware flashing (`.bin`). |
| **Cons** | Requires being on the same Wi-Fi network and knowing the IP; Thonny's `Run` button needs a workaround (see Phase 9). | Clunky (many jumper wires), prone to loose connections, tethered to the PC and requires a spare ESP32. |

### SWOT Analysis (Path A)

- **Strengths:** Eliminates both the Linux DTR/RTS issue and laptop USB power drops in one stroke.
- **Weaknesses:** If you switch Wi-Fi networks, you need to briefly reconnect via USB + `miniterm` to update `boot.py`.
- **Opportunities:** Lets you develop and test the camera directly in its final physical location powered by a standard phone charger.
- **Threats:** Router changing the IP via DHCP, or *AP Isolation* enabled on public/new networks.

## Phase 7: Implementing Path A (WebREPL + Camera Server)

Reference template: [`code/boot_template.py`](code/boot_template.py)

1. **Open `miniterm` over USB:**

   ```bash
   python3 -m serial.tools.miniterm /dev/ttyUSB0 115200 --dtr 0 --rts 0
   ```

   Press **RST** on the carrier board until `>>>` appears.

2. **Set the WebREPL password (`webrepl_cfg.py`):**  
   Instead of using the interactive `import webrepl_setup` menu (which handles `Backspace`/`Delete` poorly inside `miniterm`), write the config file directly in one line using a 4–9 character password (do not reuse your Wi-Fi password):

   ```python
   with open("webrepl_cfg.py", "w") as f: f.write("PASS = 'YOUR_WEBREPL_PASS'\n")
   ```

   *(Remember this password, you will need it in step 5 to connect Thonny.)*  
   *After pressing Enter, `"..."` will appear as output; you must press Enter again.*

3. **Create `boot.py` for automatic Wi-Fi + WebREPL:**  
   Instead of *paste mode* (`Ctrl+E` / `Ctrl+D`), writing `boot.py` with a single one-line command is much more reliable in `miniterm` *since you only need to copy it, update the credentials, and paste* (replace `YOUR_WIFI` and `YOUR_PASSWORD` with your 2.4 GHz network credentials):

   ```python
   with open("boot.py", "w") as f: f.write('import network, time, webrepl\nw = network.WLAN(network.STA_IF)\nw.active(True)\nw.connect("YOUR_WIFI", "YOUR_PASSWORD")\nfor _ in range(20):\n    if w.isconnected(): break\n    time.sleep(0.5)\nprint("IP:", w.ifconfig()[0])\nwebrepl.start()\n')
   ```

   - **Expected output:** An integer (e.g. `234`, representing bytes written) followed by `>>>`.
   - Press **RST** on the carrier board and wait 5 seconds: it will print the router-assigned IP and `WebREPL daemon started on ws://192.168.x.y:8266`.

4. **Switch to external power:**  
   Close `miniterm` (`Ctrl+]`), unplug the carrier board from your PC, and plug it into a **5V USB wall charger** (e.g., a phone charger or the USB-A port of a multiport charger). In my case, this eliminated freezes that were most likely caused by Linux USB autosuspend or PC USB power drops (which had resulted in `[Errno 113] Connect call failed`).

5. **Verify connectivity and connect Thonny:**
   - From your PC terminal, verify the board is reachable:

     ```bash
     ping -c 4 192.168.x.y
     ```

     *(If you get `Destination Host Unreachable`, press the `RST` button on the bottom carrier board for one second and try again after 5 seconds.)*
   - In Thonny, go to **`Run > Configure interpreter...`** -> **`MicroPython (ESP32)`** -> **`WebREPL`**.
   - Enter `ws://192.168.x.y:8266` and the password set in **step 2** (`webrepl_cfg.py`) -> click **OK**.
   - The shell should display `WebREPL connected` followed by `>>>`.

6. **Run the camera server (`server.py`):**  
   Save [`code/server.py`](code/server.py) onto the board via **`File > Save as... > MicroPython device`** as `server.py`, then start it from Thonny's shell with:

   ```python
   exec(open('server.py').read())
   ```

   Open the printed URL in your browser (e.g., `http://192.168.x.y`) to access the live stream and camera controls.

## Phase 8: Quick Maintenance Guide

> **Golden Rule (Terminal vs. Thonny Conflict):** A serial port (`/dev/ttyUSB0`) should only be used by one program at a time. If you get port-busy errors:
> - Exit `miniterm` with **`Ctrl+]`**.
> - Exit `screen` with **`Ctrl+A`**, then **`K`**, then **`Y`** (or run `killall screen`).
> - In Thonny, switch the interpreter to `Local Python 3` / `WebREPL`, or close the IDE.

### 1. How to change the Wi-Fi network

- **If you are still connected via WebREPL in Thonny:** open `boot.py` from the *Files* panel (*MicroPython device*), update SSID and password in `w.connect("NEW_WIFI", "NEW_PASS")`, save (`Ctrl+S`), and power-cycle the board.
- **If you already moved to a new network/router (board unreachable over Wi-Fi):**
  1. Plug the carrier board into your PC via USB and launch `miniterm`:

     ```bash
     python3 -m serial.tools.miniterm /dev/ttyUSB0 115200 --dtr 0 --rts 0
     ```

  2. Press **RST** on the carrier board until `>>>` appears.
  3. Run the one-liner with your new credentials:

     ```python
     with open("boot.py", "w") as f: f.write('import network, time, webrepl\nw = network.WLAN(network.STA_IF)\nw.active(True)\nw.connect("NEW_WIFI", "NEW_PASS")\nfor _ in range(20):\n    if w.isconnected(): break\n    time.sleep(0.5)\nprint("IP:", w.ifconfig()[0])\nwebrepl.start()\n')
     ```

     *(press Enter twice)*
  4. **Expected output:** An integer followed by `>>>`.
  5. Press **RST** and wait 5 seconds: note the new `ws://192.168.x.y:8266` address, exit `miniterm` (`Ctrl+]`), move the board back to the external charger, and update the IP in Thonny.

### 2. How to change the WebREPL password

  - **From Thonny:** edit `webrepl_cfg.py` (`PASS = 'newpass'`, 4–9 chars), save, and reboot the board.
  - **From `miniterm` (USB):**

  ```python
  with open("webrepl_cfg.py", "w") as f: f.write("PASS = 'newpass'\n")
  ```

  *(Wait for the byte count to print, then press **RST**.)*

### 3. How to find or fix the board's IP address

  The IP is automatically assigned by your router's **DHCP server** within your local subnet (e.g., `192.168.1.X`).

  - **Find it via USB (foolproof):**  
  Plug into your PC, launch `miniterm` (`--dtr 0 --rts 0`), and press **RST** to read the `IP: 192.168.x.y` line.
  - **Find it over the network (without unplugging the charger):**
  - Check connected devices in your router's admin panel (look for `espressif` or `esp32`).
  - Or scan port `8266` from a Linux terminal (requires `sudo apt install nmap`):

    ```bash
    sudo nmap -p 8266 --open 192.168.1.0/24
    ```

    ***Note**: `sudo` is needed so `nmap` can use ARP discovery on the local network; without it, the ESP32 is often skipped.*
  - **Set a Static IP (optional):**
  - **Via router (Recommended):** Set up a *DHCP Reservation* binding the ESP32-CAM's MAC address to a fixed IP. This keeps your code portable across different networks.
  - **In `boot.py`:** Add this line before `w.connect(...)` using a free IP in your subnet:

    ```python
    # (Chosen_IP, Subnet_Mask, Gateway/Router, DNS)
    w.ifconfig(('192.168.1.150', '255.255.255.0', '192.168.1.1', '192.168.1.1'))
    ```

## Phase 9: Thonny's `[Errno 111]` Bug on WebREPL and Shell Management

### Why pressing `Run (F5)` throws `ConnectionRefusedError: [Errno 111]`

It seems that Thonny's green **Run (`F5`)** button sends a *soft reboot* before running the script, which likely closes WebREPL's port `8266` briefly on the ESP32, causing Thonny to receive `[Errno 111]` when it tries to reconnect immediately.

### Reliable Ways to Run Scripts

1. **During development - `exec()` (Recommended):**  
   Save your file onto the board (`Ctrl+S`) and run it from Thonny's shell:

   ```python
   exec(open('server.py').read())
   ```

   Unlike `import server` (which caches the module in `sys.modules` and ignores subsequent edits until reboot), `exec(...)` always reads and runs **the latest saved version** without dropping WebREPL.

2. **In production (auto-start on boot) — `main.py`:**  
   Once your script is ready to run autonomously on power-up, save it as **`main.py`**: MicroPython automatically executes `boot.py` followed immediately by `main.py`.

### Why the shell stays busy (and how to stop the server)

An HTTP server runs inside an infinite loop (`while True:`) waiting on `s.accept()`, so the `>>>` prompt won't return while the server is running. Furthermore, over WebREPL, `Ctrl+C` is often ignored while blocked on `s.accept()`.

- **Clean shutdown (built into `server.py`):** Open **`http://<IP>/stop`** in your browser (or click the Stop Server link on the web page). The server exits the loop, deinitializes the camera, closes the socket, and immediately returns `>>>` in Thonny.
- **Background execution (optional):** To keep the shell free while the server runs, replace `start_server()` at the bottom of `server.py` with:

  ```python
  import _thread
  _thread.start_new_thread(start_server, ())
  ```

## Phase 10: Camera Parameters and Final Script (`server.py`)

### OV2640 Hardware Parameters (and CSS Rotation)

The OV2640 sensor handles flipping, mirroring, and JPEG compression directly in hardware with zero CPU overhead:

| Function | MicroPython Command | Values / Notes |
| --- | --- | --- |
| **Vertical flip** | `camera.flip(1)` | `1` = flipped, `0` = normal |
| **Horizontal mirror** | `camera.mirror(1)` | `1` = mirrored, `0` = normal *(combine `flip(1)` + `mirror(1)` for a 180-degree rotation)* |
| **Resolution** | `camera.framesize(...)` | `FRAME_QVGA` (320x240, smooth), `FRAME_CIF` (400x296), `FRAME_VGA` (640x480), `FRAME_SVGA` (800x600), `FRAME_HD` (1280x720) |
| **JPEG compression** | `camera.quality(25)` | From `10` (highest quality, larger file) to `63` (lightweight, lower latency) |
| **Brightness / Contrast** | `camera.brightness(0)` | From `-2` to `2` (also applies to `camera.contrast()` and `camera.saturation()`) |
| **90 / 270 deg rotation** | `CSS_ROTATE = 90` | Not supported in OV2640 hardware: handled via CSS (`transform: rotate(...)`) in the HTML page |

### Features of [`code/server.py`](code/server.py)

The complete script in the `code/` folder includes:

- **Live MJPEG Streaming (`/stream`)** and **Single Photo Capture (`/photo`)**.
- **Active power saving:** the OV2640 sensor stays powered off while idle (`camera.deinit()`) and only initializes during active requests, preventing overheating.
- **Deep Sleep (`/sleep`):** puts the board into deep sleep for 30 seconds (`machine.deepsleep(30000)`). **Note:** after `machine.deepsleep()`, the ESP32 performs a full reboot and automatically runs only `boot.py` and `main.py`, therefore, the server will only restart on its own after waking up if you have saved it as `main.py`.
- **Clean stop (`/stop`):** gracefully shuts down the server and frees the WebREPL shell.
- **RAM & browser handling:** runs `gc.collect()` on every frame and uses client-side `window.stop()` to immediately release the stream when switching pages.

## Phase 11: Known Limitations, Signal Diagnostics, and Security

### 1. Real-World Limitations

- **Single client at a time (`s.listen(1)`):** While one browser is watching `/stream`, any other device trying to connect will wait until the first client closes the stream.
- **Latency & *TCP buffering*:** If the stream builds up a 1–2 second delay and then jumps forward to live, the JPEG frames are too heavy for the current Wi-Fi link. Lower the resolution (`FRAME_QVGA` / `FRAME_CIF`) or raise `QUALITY` (e.g., `25`–`30`).
- **Wi-Fi signal quality check (RSSI):** From Thonny's shell (while the server is stopped), run:

  ```python
  import network
  network.WLAN(network.STA_IF).status('rssi')
  ```

  *Reference:* `-50` / `-60` dBm is great, `-70` dBm is fair, below `-75` / `-80` dBm is weak (keep the board away from metal surfaces/PCs and orient the PCB antenna toward the router).
- **External antenna (IPEX connector):** On the AI-Thinker board, simply plugging in an external antenna is not enough; you must desolder and reposition a 0-Ohm SMD resistor to disconnect the onboard PCB antenna.
- **Overheating & RAM:** Continuous streaming heats up the OV2640 significantly; capping the frame rate (`time.sleep(0.05)`) and avoiding resolutions above `FRAME_VGA` for continuous streaming helps prevent thermal lockups and `MemoryError`.

### 2. Security & `.gitignore`

**Network Security Notice:**

- The HTTP server in `server.py` has **no authentication**, and **WebREPL** uses a short password transmitted in cleartext (`ws://`) over Wi-Fi.
- Anyone connected to the same local network can view your camera stream or trigger `/stop` and `/sleep`.
- **Use this setup only on trusted local networks**, **never expose port `80` or `8266` to the Internet** (no router port forwarding), and **do not reuse your Wi-Fi password** for WebREPL.

**Credentials (`.gitignore`):**  
If you clone or fork this repository, **never commit your real credentials** (Wi-Fi SSID/password or WebREPL password). Always use template files with placeholders and make sure your `.gitignore` includes:

```gitignore
boot.py
webrepl_cfg.py
secrets.py
```