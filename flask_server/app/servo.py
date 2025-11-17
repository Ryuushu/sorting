import requests
from .config import ESP32_CONTROLLER_IP


def send_servo_command(servo_id):
    try:
        url = f"{ESP32_CONTROLLER_IP}/servo/{servo_id}?action=activate"
        response = requests.get(url, timeout=3)
        return response.status_code == 200
    except:
        return False