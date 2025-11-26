from flask import Blueprint, render_template, request, jsonify, Response
import cv2
import numpy as np
import base64
import time

from .detection import deteksi_roi
from .database import log_detection, init_db,log
from .mqtt_client import mqtt_client,servo
from app.state_cache import servo_state
from app import socketio
from app.controller import capture_ctrl
import json
from .detection import deteksi_roi, segmentasi, crop_rotated, prediksi,deteksi_roi2,matching,rule_grub
import matplotlib.pyplot as plt

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
        processed_frame, detections = deteksi_roi(frame)
        
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
def to_base64(img):
    """Convert numpy image to base64 string."""
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

def debug_subplot(frame, roi_crop, roi_crop_paper, enhanced, thresh, vis_frame):
    fig, axes = plt.subplots(2, 3, figsize=(15,10))

    axes[0,0].imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    axes[0,0].set_title('Original Frame')

    axes[0,1].imshow(cv2.cvtColor(roi_crop, cv2.COLOR_BGR2RGB))
    axes[0,1].set_title('ROI Crop')

    axes[0,2].imshow(cv2.cvtColor(roi_crop_paper, cv2.COLOR_BGR2RGB))
    axes[0,2].set_title('Paper Crop')

    axes[1,0].imshow(enhanced, cmap='gray')
    axes[1,0].set_title('Enhanced (CLAHE)')

    axes[1,1].imshow(thresh, cmap='gray')
    axes[1,1].set_title('Threshold')

    axes[1,2].imshow(cv2.cvtColor(vis_frame, cv2.COLOR_BGR2RGB))
    axes[1,2].set_title('Final Visualization')

    for ax in axes.flatten():
        ax.axis('off')

    plt.tight_layout()
    plt.show()
def tampilkan_chars(chars):
    n = len(chars)
    if n == 0:
        print("Tidak ada karakter untuk ditampilkan")
        return
    
    cols = min(10, n)
    rows = (n // cols) + (1 if n % cols else 0)
    
    fig, axes = plt.subplots(rows, cols, figsize=(cols*1.5, rows*2))
    axes = axes.flatten()  # flatten agar bisa index
    
    for i, char_img in enumerate(chars):
        axes[i].imshow(char_img, cmap='gray')
        axes[i].set_title(f"Char {i+1}")
        axes[i].axis('off')
    
    # Kosongkan subplot sisa
    for j in range(i+1, len(axes)):
        axes[j].axis('off')
    
    plt.tight_layout()
    plt.show()
@bp.route('/upload_web', methods=['POST'])
def upload_web():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON received'}), 400

        image_data = data.get("image")
        if not image_data or not image_data.startswith("data:image"):
            return jsonify({'status': 'error', 'message': 'Invalid image data'}), 400

        # --- Decode image ---
        image_base64 = image_data.split(",")[1]
        file_bytes = base64.b64decode(image_base64)
        np_arr = np.frombuffer(file_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'status': 'error', 'message': 'Failed to decode image'}), 400
        
        roi_crop_b64 = to_base64(frame)

        # --- Tentukan ROI kanan ---
        h, w = frame.shape[:2]
        x1, y1 = int(w/1.9), 200
        x2, y2 = w-100, int(h/1.1)
        roi_box = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
        roi_crop = frame[y1:y2, x1:x2]

        # --- Debug ROI crop ---

        # --- Auto detect paper box ---
        red_box_coord, roi_crop_paper = deteksi_roi2(roi_crop)
        if red_box_coord is None or roi_crop_paper is None:
            return jsonify({'status':'error','message':'Paper box not detected'}), 400

        red_box_coord[:,0] += x1
        red_box_coord[:,1] += y1

        roi_crop_paper_b64 = to_base64(roi_crop_paper)

        # --- Grayscale + CLAHE ---
        gray = cv2.cvtColor(roi_crop_paper, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        thresh = cv2.inRange(enhanced, 0, 170)
        
        chars, boxes, msg = segmentasi(thresh)
        hasil, conf = prediksi(chars)
        txt_match = matching(hasil)
        grub = rule_grub(txt_match)
        
        if grub == 'Utara':
            servo(1, 45)
        elif grub == 'Selatan':
            servo(4, 160)   # biasanya selatan 135° kalau mau berlawanan arah Utara
        elif grub == 'Timur':
            servo(2, 45)
        elif grub == 'Barat':
            servo(5, 160)
        else:
            print("Grup tidak dikenali")
        
        

        # --- Visualisasi final ---
        vis_frame = frame.copy()
        cv2.drawContours(vis_frame, [red_box_coord], -1, (0,255,0), 2)
        cv2.polylines(vis_frame, [roi_box], True, (0,255,255), 2)
        vis_frame_b64 = to_base64(vis_frame)
        debug_subplot(frame, roi_crop, roi_crop_paper, enhanced, thresh, vis_frame)
        tampilkan_chars(chars)
        return jsonify({
            'status': 'ok',
            'roi_crop': roi_crop_b64,
            'roi_crop_paper': roi_crop_paper_b64,
            'final_vis': vis_frame_b64,
            'paper_box': red_box_coord.tolist(),
            'roi_box': roi_box.tolist(),
            'hasil': hasil,
            'confidence': conf
        }), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
@bp.route("/proxy_ipcam")
def proxy_ipcam():
    import requests
    from flask import Response, request

    url = request.args.get("url")
    if not url:
        return "Missing IP Camera URL", 400

    # Auto-add protocol
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    try:
        # Streaming request ke IP Camera
        r = requests.get(url, stream=True, timeout=5)

        # Pastikan responsnya MJPEG
        return Response(
            r.iter_content(chunk_size=1024),
            content_type=r.headers.get(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=--frame",
            )
        )
    except Exception as e:
        print("Proxy error:", e)
        return "Failed to fetch IP Camera stream", 500

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
    return jsonify(log())

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
    angle = request.args.get('angle', 90, type=int)
    
    if servo_id < 1 or servo_id > 6:
        return jsonify({'status': 'error', 'message': 'Invalid servo ID'}), 400

    # Payload sesuai format ESP
    payload = f"servo{servo_id}:{angle}"

    # Topik sesuai ESP
    topic = "servo/control"

    mqtt_client.publish(topic, payload)

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