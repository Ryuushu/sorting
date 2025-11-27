import mysql.connector
from datetime import datetime
from .config import DB_CONFIG
from flask import request


def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME,
            detected_text VARCHAR(255),
            servo_id INT,
            img VARCHAR(255)
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(detected_text, servo_id, img_path):
    conn = mysql.connector.connect(**DB_CONFIG)
    c = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = "INSERT INTO detections (timestamp, detected_text, servo_id, img) VALUES (%s, %s, %s, %s)"
    values = (timestamp, detected_text, servo_id, img_path)
    c.execute(query, values)
    conn.commit()
    conn.close()
    return timestamp

def log():
    """Get detection logs from MySQL"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = mysql.connector.connect(**DB_CONFIG)
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM detections ORDER BY id DESC LIMIT %s", (limit,))
    rows = c.fetchall()
    conn.close()

    return rows
