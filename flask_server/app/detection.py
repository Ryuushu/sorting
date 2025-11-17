import cv2
from ultralytics import YOLO
import easyocr
from .controller import send_servo_command

model = YOLO('best.pt')
reader = easyocr.Reader(['en'], gpu=True)

TEXT_SERVO_MAPPING = {
    "A1": 1,
    "A2": 2,
    "A3": 3,
    "A4": 4,
    "A5": 5,
    "A6": 6,
}

def process_frame(frame):
    detections = []
    results = model(frame, conf=0.5)

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            label = model.names[cls]

            roi = frame[y1:y2, x1:x2]
            if roi.size == 0: continue

            ocr_results = reader.readtext(roi)

            for (bbox, text, ocr_conf) in ocr_results:
                text = text.strip().upper()

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label}: {text}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                if text in TEXT_SERVO_MAPPING:
                    servo_id = TEXT_SERVO_MAPPING[text]
                    detections.append({
                        'text': text,
                        'servo': servo_id,
                        'confidence': ocr_conf,
                        'bbox': [x1, y1, x2, y2],
                        'object_label': label
                    })

                    send_servo_command(servo_id)
                    cv2.circle(frame, (x2-20, y1+20), 10, (0, 255, 0), -1)

    return frame, detections
