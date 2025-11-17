from flask import Blueprint, render_template, request, jsonify, Response
import cv2
import numpy as np
import base64
import time
from .detection import process_frame
from .database import log_detection, init_db
from .controller import get_servo_status, send_servo_command
from .mqtt_client import mqtt_client
from app.state_cache import servo_state
import json
bp = Blueprint('routes', __name__)

latest_frame = None

@bp.route('/')
def index():
    """Render main dashboard"""
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
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
@bp.route('/upload_web', methods=['POST'])
def upload_web():
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON received'}), 400
        
        image_data = data.get("image")
        if not image_data or not image_data.startswith("data:image"):
            return jsonify({'status': 'error', 'message': 'Invalid image data'}), 400

        # Decode base64
        image_base64 = image_data.split(",")[1]
        file_bytes = base64.b64decode(image_base64)

        np_arr = np.frombuffer(file_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'status': 'error', 'message': 'Failed to decode image'}), 400

        processed_frame, detections = process_frame(frame)

        _, buffer = cv2.imencode('.jpg', processed_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        socketio.emit('frame_update', {'frame': frame_base64})

        return jsonify({
            'status': 'ok',
            'detections': detections,
            'detections_image': frame_base64
        }), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/video_feed')
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

@bp.route('/stream', methods=['POST'])
def stream_frame():
    """Receive realtime stream frame (tanpa deteksi)"""
    global latest_frame
    try:
        file_bytes = np.frombuffer(request.data, np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'status': 'error', 'message': 'Invalid frame'}), 400
        
        with frame_lock:
            latest_frame = frame.copy()
        
        # Kirim ke websocket biar dashboard update
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        socketio.emit('frame_update', {'frame': frame_base64})
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/logs')
def get_logs():
    """Get detection logs from MySQL"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = mysql.connector.connect(**DB_CONFIG)
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM detections ORDER BY id DESC LIMIT %s", (limit,))
    rows = c.fetchall()
    conn.close()

    return jsonify(rows)

@bp.route('/api/servo_status')
def servo_status():
    """Ask ESP32 for servo status via MQTT"""
    
    # Request status
    mqtt_client.publish("iot/servo/get_status", "1")


    if servo_state is None:
        return jsonify({'status': 'pending', 'message': 'Waiting status...'}), 202
    
    return jsonify(servo_state)

@bp.route('/api/manual_servo/<int:servo_id>')
def manual_servo(servo_id):
    """Manual servo control via MQTT"""
    angle = request.args.get('angle', 180, type=int)
    
    if servo_id < 1 or servo_id > 6:
        return jsonify({'status': 'error', 'message': 'Invalid servo ID'}), 400

    payload = {
        "servo": servo_id,
        "angle": angle
    }

    topic = f"iot/servo/{servo_id}"

    mqtt_client.publish(topic, json.dumps(payload))

    return jsonify({
        "status": "success",
        "message": f"Sent to servo {servo_id}: angle {angle}",
        "topic": topic,
        "payload": payload
    })

@bp.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update text-servo mbping configuration"""
    global TEXT_SERVO_MAPPING
    
    if request.method == 'POST':
        new_mapping = request.json
        TEXT_SERVO_MAPPING.update(new_mapping)
        return jsonify({'status': 'success', 'mapping': TEXT_SERVO_MAPPING})
    else:
        return jsonify(TEXT_SERVO_MAPPING)