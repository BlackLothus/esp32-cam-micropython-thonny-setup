"""Initialize the OV2640 sensor and save a single JPEG snapshot as 'test.jpg'."""

import camera

# Preventive deinit to avoid 'OSError: Camera Init Failed' after soft reboots
try:
    camera.deinit()
except Exception:
    pass

ok = camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
print("Camera initialized:", ok)

if ok:
    buf = camera.capture()
    camera.deinit()
    if buf:
        with open("test.jpg", "wb") as f:
            f.write(buf)
        print("Image saved as 'test.jpg'! Size:", len(buf), "bytes")
    else:
        print("Error: camera.capture() returned an empty buffer.")
else:
    print("Error: failed to initialize camera. Try a physical RST press.")
