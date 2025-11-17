import paho.mqtt.client as mqtt
import ssl
from app.state_cache import servo_state
import json
MQTT_BROKER = "4329d3049b4f4b4d84fb6c681a775ff9.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC_SERVO_CMD = "esp8266/servo/cmd"
MQTT_TOPIC_STATUS = "esp8266/status"
MQTT_USERNAME = "ilham"
MQTT_PASSWORD = "Babibabun3"

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.tls_set(
    tls_version=ssl.PROTOCOL_TLS,
    cert_reqs=ssl.CERT_REQUIRED
)
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC_STATUS)

def on_message(client, userdata, msg):
    global servo_state
    
    topic = msg.topic
    payload = msg.payload
    print(f"MQTT Message received: {topic} -> {payload}")
    
    if msg.topic == "iot/servo/status":
        try:
            data = json.loads(msg.payload.decode())
            servo_state = data
        except:
            pass

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


def start_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()