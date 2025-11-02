from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import requests
from datetime import datetime
import sqlite3
import threading
import base64
import time
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize YOLO model (YOLOv8n for faster inference)
model = YOLO('yolov8n.pt')  # Download automatically on first run

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=True)  # Set gpu=False if no CUDA

# ESP32 Controller IP
ESP32_CONTROLLER_IP = "http://192.168.1.101"  # Update with your ESP32 IP

# Global variable for latest frame
latest_frame = None
frame_lock = threading.Lock()

# Text to Servo mapping configuration
TEXT_SERVO_MAPPING = {
    "A1": 1,
    "A2": 2,
    "A3": 3,
    "A4": 4,
    "A5": 5,
    "A6": 6,
}

# Database initialization
def init_db():
    conn = sqlite3.connect('detection_log.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS detections
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  detected_text TEXT,
                  servo_id INTEGER,
                  confidence REAL,
                  bbox TEXT)''')
    conn.commit()
    conn.close()

init_db()

def log_detection(detected_text, servo_id, confidence, bbox):
    """Log detection to database"""
    conn = sqlite3.connect('detection_log.db')
    c = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    bbox_str = str(bbox)
    c.execute("INSERT INTO detections VALUES (NULL, ?, ?, ?, ?, ?)",
              (timestamp, detected_text, servo_id, confidence, bbox_str))
    conn.commit()
    conn.close()
    
    # Emit to WebSocket for real-time update
    socketio.emit('new_detection', {
        'timestamp': timestamp,
        'text': detected_text,
        'servo': servo_id,
        'confidence': confidence
    })

def send_servo_command(servo_id):
    """Send command to ESP32 to activate servo"""
    try:
        url = f"{ESP32_CONTROLLER_IP}/servo/{servo_id}?action=activate"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            print(f"✓ Servo {servo_id} activated successfully")
            return True
        else:
            print(f"✗ Failed to activate servo {servo_id}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error sending servo command: {e}")
        return False

def process_frame(frame):
    """Process frame with YOLO and OCR"""
    detections = []
    
    # Run YOLO detection
    results = model(frame, conf=0.5)
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Get bounding box coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = model.names[cls]
            
            # Extract ROI for OCR
            roi = frame[y1:y2, x1:x2]
            
            if roi.size > 0:
                # Run OCR on ROI
                ocr_results = reader.readtext(roi)
                
                for (bbox, text, ocr_conf) in ocr_results:
                    text = text.strip().upper()
                    
                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"{label}: {text}", (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # Check if text matches any trigger
                    if text in TEXT_SERVO_MAPPING:
                        servo_id = TEXT_SERVO_MAPPING[text]
                        
                        detections.append({
                            'text': text,
                            'servo': servo_id,
                            'confidence': ocr_conf,
                            'bbox': [x1, y1, x2, y2],
                            'object_label': label
                        })
                        
                        # Send servo command
                        success = send_servo_command(servo_id)
                        
                        if success:
                            # Log to database
                            log_detection(text, servo_id, ocr_conf, [x1, y1, x2, y2])
                            
                            # Draw success indicator
                            cv2.circle(frame, (x2-20, y1+20), 10, (0, 255, 0), -1)
    
    return frame, detections

@app.route('/')
def index():
    """Render main dashboard"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_frame():
    """Receive frame from ESP32-CAM"""
    global latest_frame
    
    try:
        # Get image from request
        file_bytes = np.frombuffer(request.data, np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'status': 'error', 'message': 'Invalid image'}), 400
        
        # Process frame
        processed_frame, detections = process_frame(frame)
        
        # Store latest frame
        with frame_lock:
            latest_frame = processed_frame.copy()
        
        # Emit frame to WebSocket clients
        _, buffer = cv2.imencode('.jpg', processed_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        socketio.emit('frame_update', {'frame': frame_base64})
        
        return jsonify({
            'status': 'success',
            'detections': detections,
            'count': len(detections)
        }), 200
        
    except Exception as e:
        print(f"Error processing frame: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/video_feed')
def video_feed():
    """MJPEG stream for web dashboard"""
    def generate():
        while True:
            with frame_lock:
                if latest_frame is not None:
                    _, buffer = cv2.imencode('.jpg', latest_frame)
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.03)  # ~30 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/logs')
def get_logs():
    """Get detection logs"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = sqlite3.connect('detection_log.db')
    c = conn.cursor()
    c.execute("SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    
    logs = []
    for row in rows:
        logs.append({
            'id': row[0],
            'timestamp': row[1],
            'text': row[2],
            'servo': row[3],
            'confidence': row[4],
            'bbox': row[5]
        })
    
    return jsonify(logs)

@app.route('/api/servo_status')
def servo_status():
    """Get servo status from ESP32"""
    try:
        response = requests.get(f"{ESP32_CONTROLLER_IP}/status", timeout=3)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'status': 'error', 'message': 'Cannot reach ESP32'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/manual_servo/<int:servo_id>')
def manual_servo(servo_id):
    """Manual servo control from dashboard"""
    angle = request.args.get('angle', 180, type=int)
    
    if servo_id < 1 or servo_id > 6:
        return jsonify({'status': 'error', 'message': 'Invalid servo ID'}), 400
    
    try:
        url = f"{ESP32_CONTROLLER_IP}/servo/{servo_id}?angle={angle}"
        response = requests.get(url, timeout=3)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update text-servo mapping configuration"""
    global TEXT_SERVO_MAPPING
    
    if request.method == 'POST':
        new_mapping = request.json
        TEXT_SERVO_MAPPING.update(new_mapping)
        return jsonify({'status': 'success', 'mapping': TEXT_SERVO_MAPPING})
    else:
        return jsonify(TEXT_SERVO_MAPPING)

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI-IoT Server Starting...")
    print("=" * 60)
    print(f"📡 Waiting for ESP32-CAM frames at http://0.0.0.0:5000/upload")
    print(f"🎥 Video stream available at http://0.0.0.0:5000/video_feed")
    print(f"🌐 Dashboard available at http://0.0.0.0:5000/")
    print(f"🤖 ESP32 Controller: {ESP32_CONTROLLER_IP}")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)