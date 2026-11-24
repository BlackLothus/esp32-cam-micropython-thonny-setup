"""Basic ESP32-CAM LED flash test (white flash LED is on GPIO 4; rear red LED is on GPIO 33)."""

from machine import Pin
import time

flash = Pin(4, Pin.OUT)

for _ in range(3):
    flash.value(1)
    time.sleep(0.1)
    flash.value(0)
    time.sleep(0.5)

print("Flash test completed!")
