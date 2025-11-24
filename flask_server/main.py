from app import create_app, socketio
from app.mqtt_client import start_mqtt
import os

app = create_app()

if __name__ == '__main__':
    print('='*60)
    print('🚀 AI-IoT Server Starting...')
    print('🎥 Video stream at http://0.0.0.0:5000/video_feed')
    print('🌐 Dashboard at http://0.0.0.0:5000/')
    print('='*60)
    
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("➡️ Flask reloader child — MQTT TIDAK dijalankan")
        start_mqtt()
    else:
        print("➡️ Main process — MQTT dijalankan")
        # start_mqtt()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)