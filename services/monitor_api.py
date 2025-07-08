# monitor_api.py 
import os
import cv2
import time
import requests
import io
import threading
import uuid
from datetime import datetime
from flask import Flask, jsonify, Response, request, send_from_directory
from flask_cors import CORS
from PIL import Image
from werkzeug.utils import secure_filename
import base64

# Import TreeDetector and database manager
from utils.tree_detector import TreeDetector
from utils.database_manager import init_db, insert_detection, get_all_detections, \
                                   get_total_detections, get_detection_counts_by_fruit, \
                                   get_detection_counts_by_disease, get_detections_in_time_range

app = Flask(__name__)
CORS(app)

# --- Configuration ---
YOLO_MODEL_PATH = 'C:/Users/USER/Downloads/fyp project chatbot/models/best.pt' 
MTL_API_URL = 'http://localhost:5001/predict_image'

# --- Global Variables for Video Capture and Threading ---
cap = None
is_monitoring_active = False
detection_thread = None
latest_frame = None
current_video_path = None
video_playback_pos = 0 
total_video_frames = 0 
current_detection_interval = 5 
enable_tree_detection_global = True 

# --- Video Upload Configuration ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ensure database is initialized on startup
init_db()

# --- Initialize Tree Detector ---
tree_detector = None
try:
    tree_detector = TreeDetector(model_path=YOLO_MODEL_PATH)
except FileNotFoundError as e:
    print(f"ERROR: Tree detection model not found at {YOLO_MODEL_PATH}. Monitoring will not work: {e}")
except Exception as e:
    print(f"ERROR: Failed to load Tree Detector: {e}")

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_image_to_mtl_api(pil_image: Image.Image):
    """Sends a PIL Image to the MTL API as a Base64 encoded JSON."""
    try:
        byte_arr = io.BytesIO()
        pil_image.save(byte_arr, format='JPEG')
        image_bytes = byte_arr.getvalue()

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        json_payload = {"image_base64": image_base64}
        
        print("Sending image to MTL API as JSON...")
        response = requests.post(MTL_API_URL, json=json_payload)
        response.raise_for_status()
        
        predictions = response.json()
        print(f"Received MTL predictions: {predictions}")
        return predictions
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to MTL API at {MTL_API_URL}. Is it running?")
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request to MTL API failed: {e}")
        if response is not None:
            print(f"MTL API Response Content: {response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while sending to MTL API: {e}")
        return None

# --- Main Monitoring Logic Thread ---
def monitoring_loop():
    global cap, is_monitoring_active, latest_frame, current_video_path, video_playback_pos, total_video_frames, current_detection_interval, enable_tree_detection_global

    if not current_video_path:
        print("ERROR: No video file has been uploaded to start monitoring.")
        is_monitoring_active = False
        return

    if cap and cap.isOpened():
        cap.release()

    print(f"Attempting to open video file: {current_video_path}")
    cap = cv2.VideoCapture(current_video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open video file {current_video_path}. Please check file path and format.")
        is_monitoring_active = False
        current_video_path = None
        return

    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total video frames: {total_video_frames}")

    video_playback_pos = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, video_playback_pos)

    last_detection_time = time.time()
    print("Monitoring loop started for video file.")
    print(f"Tree detection enabled: {enable_tree_detection_global}")

    while is_monitoring_active:
        ret, frame = cap.read()
        if not ret:
            print("INFO: End of video stream or failed to grab frame. Monitoring loop stopping.")
            is_monitoring_active = False
            break

        latest_frame = frame
        video_playback_pos += 1

        current_time = time.time()
        if current_time - last_detection_time >= current_detection_interval:
            last_detection_time = current_time
            print(f"Processing frame {video_playback_pos} for detection at {datetime.now().strftime('%H:%M:%S')}")

            if enable_tree_detection_global and tree_detector: # Tree detection enabled and detector loaded
                try:
                    cropped_tree_images = tree_detector.detect_trees(frame)

                    if cropped_tree_images:
                        print(f"Detected {len(cropped_tree_images)} trees. Sending to MTL API...")
                        for i, tree_img_pil in enumerate(cropped_tree_images):
                            mtl_results = send_image_to_mtl_api(tree_img_pil)
                            
                            if mtl_results:
                                fruit_type = mtl_results.get('fruit', 'unknown')
                                ripeness = mtl_results.get('ripeness', 'unknown')
                                disease = mtl_results.get('disease', 'unknown')
                                confidence_fruit = mtl_results.get('confidence_fruit', None)
                                confidence_ripeness = mtl_results.get('confidence_ripeness', None)
                                confidence_disease = mtl_results.get('confidence_disease', None)
                                
                                insert_detection(
                                    fruit_type=fruit_type,
                                    ripeness=ripeness,
                                    disease=disease,
                                    confidence_fruit=confidence_fruit,
                                    confidence_ripeness=confidence_ripeness,
                                    confidence_disease=confidence_disease,
                                    notes=f"Detection from video stream: {os.path.basename(current_video_path)} (Frame {video_playback_pos}, Tree {i+1}) - Tree detection ON"
                                )
                                print(f"Stored detection: {fruit_type}, {ripeness}, {disease}")
                            else:
                                print(f"MTL API did not return valid results for tree {i+1}.")
                    else:
                        print(f"No trees detected in frame {video_playback_pos}.")
                except Exception as e:
                    print(f"ERROR: Error during tree detection or MTL processing: {e}")
            elif not enable_tree_detection_global: # Tree detection NOT enabled, send full frame
                print("Tree detection is OFF. Sending full frame to MTL API...")
                if frame is not None:
                    try:
                        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        mtl_results = send_image_to_mtl_api(pil_img)

                        if mtl_results:
                            fruit_type = mtl_results.get('fruit', 'unknown')
                            ripeness = mtl_results.get('ripeness', 'unknown')
                            disease = mtl_results.get('disease', 'unknown')
                            confidence_fruit = mtl_results.get('confidence_fruit', None)
                            confidence_ripeness = mtl_results.get('confidence_ripeness', None)
                            confidence_disease = mtl_results.get('confidence_disease', None)

                            insert_detection(
                                fruit_type=fruit_type,
                                ripeness=ripeness,
                                disease=disease,
                                confidence_fruit=confidence_fruit,
                                confidence_ripeness=confidence_ripeness,
                                confidence_disease=confidence_disease,
                                notes=f"Detection from video stream: {os.path.basename(current_video_path)} (Frame {video_playback_pos}) - Tree detection OFF (Full frame)"
                            )
                            print(f"Stored full frame detection: {fruit_type}, {ripeness}, {disease}")
                        else:
                            print("MTL API did not return valid results for full frame.")
                    except Exception as e:
                        print(f"ERROR: Error converting frame or sending full frame to MTL API: {e}")
                else:
                    print("WARNING: Frame is None, cannot send to MTL API.")
            else: # tree_detector is None
                print("Tree detector not initialized. Skipping detection (even if enabled).")
        
        time.sleep(0.01)

    print("Monitoring loop stopped for video file.")
    if cap:
        cap.release()
        cap = None

# --- Flask API Endpoints ---

@app.route('/upload_video', methods=['POST'])
def upload_video():
    global current_video_path, is_monitoring_active, detection_thread, current_detection_interval, enable_tree_detection_global

    if 'video' not in request.files:
        return jsonify({"error": "No video file part in the request"}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No selected video file"}), 400
    
    detection_interval_str = request.form.get('detectionInterval', '5')
    try:
        current_detection_interval = int(detection_interval_str)
        if current_detection_interval <= 0:
            current_detection_interval = 5
    except ValueError:
        current_detection_interval = 5

    enable_tree_detection_global = request.form.get('enableTreeDetection') == 'true'

    print(f"Received detection interval: {current_detection_interval} seconds. Tree detection enabled: {enable_tree_detection_global}.")

    if file and allowed_file(file.filename):
        filename = secure_filename(str(uuid.uuid4()) + os.path.splitext(file.filename)[1])
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        current_video_path = filepath
        
        if is_monitoring_active:
            is_monitoring_active = False
            if detection_thread and detection_thread.is_alive():
                detection_thread.join(timeout=2)
                print("Old monitoring thread stopped.")

        is_monitoring_active = True
        detection_thread = threading.Thread(target=monitoring_loop)
        detection_thread.daemon = True
        detection_thread.start()
        
        return jsonify({"status": f"Video '{file.filename}' uploaded and monitoring started with {current_detection_interval}s interval. Tree detection: {'ON' if enable_tree_detection_global else 'OFF'}."}), 200
    else:
        return jsonify({"error": "Invalid file type. Allowed types are: " + ', '.join(ALLOWED_EXTENSIONS)}), 400

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    global is_monitoring_active, detection_thread
    if not current_video_path:
        return jsonify({"error": "No video uploaded. Please upload a video first."}), 400

    if not is_monitoring_active:
        is_monitoring_active = True
        detection_thread = threading.Thread(target=monitoring_loop)
        detection_thread.daemon = True
        detection_thread.start()
        return jsonify({"status": "Monitoring started for uploaded video."})
    return jsonify({"status": "Monitoring already active."})

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global is_monitoring_active
    if is_monitoring_active:
        is_monitoring_active = False
        if detection_thread and detection_thread.is_alive():
            detection_thread.join(timeout=5)
            if detection_thread.is_alive():
                print("Warning: Monitoring thread did not terminate gracefully.")
        if cap and cap.isOpened():
            cap.release()
            print("Video capture released by stop command.")
        return jsonify({"status": "Monitoring stopped."})
    return jsonify({"status": "Monitoring not active."})

@app.route('/video_feed')
def video_feed():
    """Streams the live video feed (from uploaded video) as MJPEG."""
    def generate_frames():
        global latest_frame
        while True:
            if latest_frame is not None:
                ret, buffer = cv2.imencode('.jpg', latest_frame)
                if not ret:
                    continue
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.03)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/monitoring/status', methods=['GET'])
def get_monitoring_status():
    """Returns the current status of the video monitoring."""
    global is_monitoring_active, current_video_path
    status_message = "active" if is_monitoring_active else "inactive"
    video_filename = os.path.basename(current_video_path) if current_video_path else "No video loaded"
    
    return jsonify({
        "monitoring_status": status_message,
        "current_video_file": video_filename,
        "is_active": is_monitoring_active
    })

@app.route('/api/monitoring/detections', methods=['GET'])
def get_monitoring_detections():
    """
    Fetches detections from the database, with an optional limit.
    GET /api/monitoring/detections?limit=X
    """
    limit_str = request.args.get('limit')
    limit = None
    if limit_str and limit_str.lower() != 'all':
        try:
            limit = int(limit_str)
            if limit <= 0:
                limit = None
        except ValueError:
            limit = None
    
    try:
        detections = get_all_detections(limit=limit) 
        
        column_names = ['id', 'timestamp', 'fruit_type', 'ripeness', 'disease', 
                        'confidence_fruit', 'confidence_ripeness', 'confidence_disease', 
                        'image_capture_path', 'notes'] 
        
        detections_dicts = []
        for row in detections:
            detection_dict = dict(zip(column_names, row))
            for key in ['confidence_fruit', 'confidence_ripeness', 'confidence_disease']:
                if detection_dict[key] is not None:
                    try:
                        detection_dict[key] = float(detection_dict[key])
                    except ValueError:
                        detection_dict[key] = None
            detections_dicts.append(detection_dict)
        
        return jsonify(detections_dicts)
    except Exception as e:
        print(f"Error fetching detections for chatbot: {e}")
        return jsonify({"error": "Failed to fetch monitoring detections"}), 500

@app.route('/api/monitoring/detections_in_range', methods=['GET'])
def get_monitoring_detections_in_range():
    """
    Fetches detections from the database within a specified time range.
    Requires 'start_time' and 'end_time' query parameters in ISO 8601 format.
    GET /api/monitoring/detections_in_range?start_time=YYYY-MM-DDTHH:MM:SS&end_time=YYYY-MM-DDTHH:MM:SS
    """
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')

    if not start_time_str or not end_time_str:
        return jsonify({"error": "Both 'start_time' and 'end_time' query parameters are required."}), 400

    try:
        detections = get_detections_in_time_range(start_time_str, end_time_str)
        
        column_names = ['id', 'timestamp', 'fruit_type', 'ripeness', 'disease', 
                        'confidence_fruit', 'confidence_ripeness', 'confidence_disease', 
                        'image_capture_path', 'notes'] 
        
        detections_dicts = []
        for row in detections:
            detection_dict = dict(zip(column_names, row))
            for key in ['confidence_fruit', 'confidence_ripeness', 'confidence_disease']:
                if detection_dict[key] is not None:
                    try:
                        detection_dict[key] = float(detection_dict[key])
                    except ValueError:
                        detection_dict[key] = None
            detections_dicts.append(detection_dict)
        
        return jsonify(detections_dicts)
    except Exception as e:
        print(f"Error fetching detections in time range: {e}")
        return jsonify({"error": f"Failed to fetch detections in time range: {e}"}), 500

@app.route('/api/monitoring/total_detections', methods=['GET'])
def get_total_detections_endpoint():
    """Returns the total number of detections."""
    try:
        total_count = get_total_detections()
        return jsonify({"total_detections": total_count})
    except Exception as e:
        print(f"Error fetching total detections: {e}")
        return jsonify({"error": "Failed to fetch total detections"}), 500

@app.route('/api/monitoring/detections_by_fruit', methods=['GET'])
def get_detections_by_fruit_endpoint():
    """Returns detection counts grouped by fruit type."""
    try:
        fruit_counts = get_detection_counts_by_fruit()
        result = [{'fruit_type': row[0], 'count': row[1]} for row in fruit_counts]
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching detections by fruit: {e}")
        return jsonify({"error": "Failed to fetch detections by fruit"}), 500

@app.route('/api/monitoring/detections_by_disease', methods=['GET'])
def get_detections_by_disease_endpoint():
    """Returns detection counts grouped by disease type."""
    try:
        disease_counts = get_detection_counts_by_disease()
        result = [{'disease': row[0], 'count': row[1]} for row in disease_counts]
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching detections by disease: {e}")
        return jsonify({"error": "Failed to fetch detections by disease"}), 500


@app.route('/api/monitoring/progress', methods=['GET'])
def get_monitoring_progress():
    global video_playback_pos, total_video_frames, is_monitoring_active, current_video_path
    
    if not current_video_path or not cap or not cap.isOpened():
        video_playback_pos = 0
        total_video_frames = 0
        is_monitoring_active_status = False
    else:
        is_monitoring_active_status = is_monitoring_active
        
    return jsonify({
        "processed_frames": video_playback_pos,
        "total_frames": total_video_frames,
        "is_monitoring_active": is_monitoring_active_status
    })


if __name__ == '__main__':
    print("Starting Monitoring API Server...")
    print(f"YOLO Model Path set to: {YOLO_MODEL_PATH}")
    print(f"MTL API URL set to: {MTL_API_URL}")
    print(f"Detection Interval: {current_detection_interval} seconds (Actual configured)")
    print(f"Video Uploads Folder: {UPLOAD_FOLDER}")
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)
