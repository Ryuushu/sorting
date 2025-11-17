import base64
import cv2
import numpy as np

def decode_base64_image(image_data):
    if image_data.startswith('data:image'):
        image_base64 = image_data.split(',')[1]
        file_bytes = base64.b64decode(image_base64)
        np_arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    return None
