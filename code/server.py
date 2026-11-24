"""Minimal ESP32-CAM HTTP server with MJPEG stream, snapshot, deep sleep, and clean stop.
Run from Thonny WebREPL with: exec(open('server.py').read())
"""

import camera
import socket
import network
import machine
import time
import gc

FLIP = 1       # see phase 10 on README
MIRROR = 1     
CSS_ROTATE = 0 
QUALITY = 25   


def camera_on():
    # Preventive deinit avoids sensor lockups between sessions
    try:
        camera.deinit()
    except Exception:
        pass
    camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
    camera.framesize(camera.FRAME_QVGA)  # 320x240 keeps latency low over Wi-Fi
    camera.quality(QUALITY)
    camera.flip(FLIP)
    camera.mirror(MIRROR)


def camera_off():
    try:
        camera.deinit()
    except Exception:
        pass


def html_page():
    return (
        "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
        "<html>\n"
        "<head>\n"
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>ESP32-CAM Control</title>\n"
        "  <style>\n"
        "    body { font-family: sans-serif; text-align: center; background: #111; color: #eee; }\n"
        "    img { max-width: 90%; border: 2px solid #444; transform: rotate(" + str(CSS_ROTATE) + "deg); margin-top: 20px; }\n"
        "    a { color: #4af; margin: 0 10px; font-size: 1.1em; text-decoration: none; }\n"
        "    a:hover { text-decoration: underline; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h2>ESP32-CAM Control</h2>\n"
        "  <div>\n"
        '    <a href="/stream">Live Stream</a> |\n'
        '    <a href="/photo" onclick="window.stop(); document.getElementById(\'cam\').src=\'\';">Single Photo</a> |\n'
        '    <a href="/sleep" onclick="window.stop(); document.getElementById(\'cam\').src=\'\';">Deep Sleep (30s)</a> |\n'
        '    <a href="/stop" onclick="window.stop(); document.getElementById(\'cam\').src=\'\';">Stop Server</a>\n'
        "  </div>\n"
        '  <img id="cam" src="/stream" />\n'
        "</body>\n"
        "</html>\n"
    )
    
    
def start_server():
    ip = network.WLAN(network.STA_IF).ifconfig()[0]
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print(f"Server ready! Open: http://{ip}")

    try:
        while True:
            cl, remote = s.accept()
            req = cl.recv(1024).decode("utf-8", "ignore")

            if "GET /photo " in req:
                camera_on()
                buf = camera.capture()
                camera_off()
                if buf:
                    cl.send(
                        b"HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: "
                        + str(len(buf)).encode()
                        + b"\r\n\r\n"
                    )
                    cl.sendall(buf)
                cl.close()

            elif "GET /stream " in req:
                camera_on()
                try:
                    cl.send(
                        b"HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n"
                    )
                    while True:
                        buf = camera.capture()
                        if buf:
                            cl.send(
                                b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                + str(len(buf)).encode()
                                + b"\r\n\r\n"
                            )
                            cl.sendall(buf)
                            cl.send(b"\r\n")
                        # Free frame buffer immediately to avoid MemoryError during long streams
                        buf = None
                        gc.collect()
                        time.sleep(0.05)  # ~20 fps cap to limit sensor heating
                except OSError:
                    # Client closed the stream
                    pass
                finally:
                    camera_off()
                    cl.close()

            elif "GET /sleep " in req:
                cl.send(
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n"
                    b"Entering Deep Sleep for 30 seconds...\n"
                    b"(Auto-restarts on wake-up only if saved as main.py)"
                )
                cl.close()
                camera_off()
                s.close()
                time.sleep(0.5)
                machine.deepsleep(30000)

            elif "GET /stop " in req:
                cl.send(
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nServer stopped."
                )
                cl.close()
                break

            else:
                cl.send(html_page().encode())
                cl.close()
    finally:
        camera_off()
        s.close()
        print("Server stopped.")


# Run in foreground; use _thread to keep the REPL free
start_server()
