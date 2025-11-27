# app/mqtt_capture.py
import cv2
import time
import base64
import json
import numpy as np
import paho.mqtt.client as mqtt
from app.controller import capture_ctrl
from app import socketio
from threading import Lock
from datetime import datetime
# --------------------------
# MQTT CONFIG
# --------------------------
BROKER = "4329d3049b4f4b4d84fb6c681a775ff9.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "ilham"
PASSWORD = "Babibabun3"
TOPIC_DISTANCE = "esp8266/ultrasonic"

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.tls_set()

# --------------------------
# COOLDOWN CONFIG
# --------------------------
capture_ctrl.COOLDOWN_TIME = 3  # detik

# --------------------------
# Save Frame to Disk
# --------------------------
def save_frame_to_disk():
    if capture_ctrl.latest_frame is None:
        print("⚠️ latest_frame NULL, belum ada gambar dari browser!")
        return

    timestamp = int(time.time())
    filename = f"capture_{timestamp}.jpg"
    path = f"static/captures/{filename}"
    cv2.imwrite(path, capture_ctrl.latest_frame)
    print(f"📸 Saved: {path}")

    _, buf = cv2.imencode(".jpg", capture_ctrl.latest_frame)
    img64 = base64.b64encode(buf).decode()

    # Kirim ke frontend
    socketio.emit("capture_done", {"file": filename, "image": img64})
    print("✅ Capture dikirim ke frontend")

    # Aktifkan cooldown
    with capture_ctrl.lock:
        capture_ctrl.cooldown_active = True
        print("⛔ Cooldown aktif (anti spam capture)")

    # Mulai timer cooldown
    socketio.start_background_task(cooldown_timer)

# --------------------------
# Cooldown Timer
# --------------------------
def cooldown_timer():
    time.sleep(capture_ctrl.COOLDOWN_TIME)
    with capture_ctrl.lock:
        capture_ctrl.cooldown_active = False
        capture_ctrl.capture_requested = False
        print("✅ Cooldown selesai, capture boleh lagi")

# --------------------------
# MQTT on_message
# --------------------------
def emit_ultrasonic(data):
    socketio.emit("trigger_ultrasonic", data, namespace="/")
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except:
        print("❌ Bad JSON:", msg.payload)
        return

    # Ambil distance
    if isinstance(payload, (float, int)):
        distance = float(payload)
    elif isinstance(payload, dict):
        distance = float(payload.get("distance", 999))
    else:
        print("❌ Unsupported payload:", payload)
        return

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{timestamp} | 📏 Distance: {distance} | cooldown: {capture_ctrl.cooldown_active} | requested: {capture_ctrl.capture_requested}")
    data = { "distance": distance, "timestamp": timestamp}
    socketio.start_background_task(emit_ultrasonic, data)
    if 60 <= distance <= 65:
        mqtt_client.publish("esp8266/servo_reset", payload="reset", qos=0)
    if 35 <= distance <= 35:
        mqtt_client.publish("esp8266/servo_reset", payload="reset", qos=0)
    if distance > 20:
        if capture_ctrl.capture_requested:
            with capture_ctrl.lock:
                capture_ctrl.capture_requested = False
            print("🔄 Reset capture_requested karena objek menjauh")
    # Trigger capture jika jarak sesuai
    if 15 <= distance <= 17:
        with capture_ctrl.lock:
            if not capture_ctrl.cooldown_active and not capture_ctrl.capture_requested:
                capture_ctrl.capture_requested = True
                print("⚡ Trigger capture sent ke frontend")
                socketio.start_background_task(
                    lambda: socketio.emit("trigger_capture", namespace="/")
                )
                # socketio.start_background_task(save_frame_to_disk)
            else:
                print("⛔ Capture diblokir, cooldown atau sudah requested")         


def servo(servo_id, angle):
    payload = f"servo{servo_id}:{angle}"
    mqtt_client.publish("servo/control", payload)
    
# --------------------------
# Start MQTT
# --------------------------
def start_mqtt():
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_client.subscribe(TOPIC_DISTANCE)
    mqtt_client.loop_start()
    print("📡 MQTT Connected & Listening")
