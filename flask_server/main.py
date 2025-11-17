from app import create_app, socketio
from app.mqtt_client import start_mqtt

app = create_app()

if __name__ == '__main__':
    print('='*60)
    print('🚀 AI-IoT Server Starting...')
    print('🎥 Video stream at http://0.0.0.0:5000/video_feed')
    print('🌐 Dashboard at http://0.0.0.0:5000/')
    print('='*60)
    
    start_mqtt()  # start MQTT loop
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)