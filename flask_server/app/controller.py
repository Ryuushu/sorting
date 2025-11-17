import requests

ESP32_CONTROLLER_IP = "http://192.168.21.111"

def send_servo_command(servo_id, action='activate'):
    try:
        url = f"{ESP32_CONTROLLER_IP}/servo/{servo_id}?action={action}"
        response = requests.get(url, timeout=3)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending servo command: {e}")
        return False

def get_servo_status():
    try:
        url = f"{ESP32_CONTROLLER_IP}/status"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.json()
        else:
            return {'status': 'error', 'message': 'Cannot reach ESP32'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
