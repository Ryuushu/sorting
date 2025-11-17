import mysql.connector
from datetime import datetime
from .config import DB_CONFIG

def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME,
            detected_text VARCHAR(255),
            servo_id INT,
            confidence FLOAT,
            bbox TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_detection(detected_text, servo_id, confidence, bbox):
    conn = mysql.connector.connect(**DB_CONFIG)
    c = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = "INSERT INTO detections (timestamp, detected_text, servo_id, confidence, bbox) VALUES (%s, %s, %s, %s, %s)"
    values = (timestamp, detected_text, servo_id, confidence, str(bbox))
    c.execute(query, values)
    conn.commit()
    conn.close()
    return timestamp
