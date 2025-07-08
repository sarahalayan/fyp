# database_manager.py
import sqlite3
from datetime import datetime, timedelta 
import time 

DATABASE_NAME = 'plant_monitor.db'

def connect_db():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_NAME)

def init_db():
    """Initializes the database schema if tables don't exist."""
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                fruit_type TEXT,
                ripeness TEXT,
                disease TEXT,
                confidence_fruit REAL,
                confidence_ripeness REAL,
                confidence_disease REAL,
                image_capture_path TEXT,
                notes TEXT
            )
        ''')
        conn.commit()
    print(f"Database '{DATABASE_NAME}' initialized.")

def insert_detection(fruit_type, ripeness, disease, 
                     confidence_fruit=None, confidence_ripeness=None, confidence_disease=None,
                     image_capture_path=None, notes=None):
    """
    Inserts a new detection record into the database.
    Timestamp is automatically generated.
    """
    timestamp = datetime.now().isoformat()
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO detections (timestamp, fruit_type, ripeness, disease, 
                                     confidence_fruit, confidence_ripeness, confidence_disease, 
                                     image_capture_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, fruit_type, ripeness, disease, 
              confidence_fruit, confidence_ripeness, confidence_disease, 
              image_capture_path, notes))
        conn.commit()
        print(f"Inserted detection: {fruit_type}, {ripeness}, {disease} at {timestamp}")
        return cursor.lastrowid

def get_all_detections(limit: int = None):
    """Fetches all detection records from the database, optionally limited."""
    with connect_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM detections ORDER BY timestamp DESC"
        params = []
        if limit is not None and isinstance(limit, int) and limit > 0:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        detections = cursor.fetchall()
    return detections

def get_detections_in_time_range(start_timestamp: str, end_timestamp: str):
    """
    Fetches detection records within a specified time range (ISO 8601 format).
    Args:
        start_timestamp (str): Start of the time range (e.g., '2023-01-01T00:00:00.000000')
        end_timestamp (str): End of the time range (e.g., '2023-01-01T23:59:59.999999')
    Returns:
        list: A list of detection records.
    """
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM detections
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
        ''', (start_timestamp, end_timestamp))
        detections = cursor.fetchall()
    return detections

def get_detection_counts_by_fruit():
    """Counts detections by fruit type."""
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT fruit_type, COUNT(*) FROM detections GROUP BY fruit_type')
        return cursor.fetchall()

def get_detection_counts_by_disease():
    """Counts detections by disease type."""
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT disease, COUNT(*) FROM detections GROUP BY disease')
        return cursor.fetchall()

def get_latest_detection_by_disease(disease_name):
    """Gets the timestamp of the latest detection for a specific disease."""
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp FROM detections WHERE disease = ? ORDER BY timestamp DESC LIMIT 1', (disease_name,))
        result = cursor.fetchone()
        return result[0] if result else None

def get_total_detections():
    """Gets the total number of detections."""
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM detections')
        return cursor.fetchone()[0]

# Example Usage (for testing)
if __name__ == "__main__":
    init_db()

    # Inserting some dummy data for testing time range
    print("\nInserting dummy data for time range testing...")
    insert_detection("apple", "ripe", "Apple___healthy", notes="Today's first apple", confidence_fruit=0.9, confidence_ripeness=0.95, confidence_disease=0.1)
    time.sleep(0.1) # Small delay to ensure different timestamps
    insert_detection("grapes", "unripe", "Grape___Black_rot", notes="Today's grape disease", confidence_fruit=0.8, confidence_ripeness=0.2, confidence_disease=0.7)
    time.sleep(0.1)
    # Simulate a detection from a previous day
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO detections (timestamp, fruit_type, ripeness, disease, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (yesterday, "banana", "ripe", "Banana___healthy", "Yesterday's banana"))
    conn.commit()
    conn.close()

    start_of_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_today = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    
    print(f"\nDetections for today ({start_of_today} to {end_of_today}):")
    today_detections = get_detections_in_time_range(start_of_today, end_of_today)
    for row in today_detections:
        print(row)

    print("\nAll Detections (to confirm):")
    for row in get_all_detections():
        print(row)
