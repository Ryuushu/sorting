from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    CORS(app)

    # Init socketio WITH app
    socketio.init_app(app)

    # Import routes
    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app
