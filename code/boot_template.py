"""Wi-Fi auto-connect and WebREPL startup template. Rename to 'boot.py' on the board."""

import network
import time
import webrepl

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

w = network.WLAN(network.STA_IF)
w.active(True)

# Optional static IP: (static_ip, subnet_mask, gateway_ip, dns_ip)
# w.ifconfig(('192.168.1.150', '255.255.255.0', '192.168.1.1', '192.168.1.1'))

w.connect(WIFI_SSID, WIFI_PASSWORD)

for _ in range(20):
    if w.isconnected():
        break
    time.sleep(0.5)

if w.isconnected():
    print("IP:", w.ifconfig()[0])
    webrepl.start()
else:
    print("Wi-Fi connection failed. Check credentials and 2.4 GHz band.")
