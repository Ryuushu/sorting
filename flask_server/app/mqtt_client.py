import paho.mqtt.client as mqtt

MQTT_BROKER = "192.168.21.50"
MQTT_PORT = 1883
MQTT_TOPIC_FRAME = "esp8266/camera/frame"
MQTT_TOPIC_SERVO_CMD = "esp8266/servo/cmd"
MQTT_TOPIC_STATUS = "esp8266/status"

mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC_FRAME)
    client.subscribe(MQTT_TOPIC_STATUS)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload
    print(f"MQTT Message received: {topic} -> {payload}")
    # Bisa tambahkan handler sesuai topik

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


def start_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()