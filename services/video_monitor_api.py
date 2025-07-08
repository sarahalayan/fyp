# monitor_api.py
import os
import cv2
import time
import requests
import io
import threading
import uuid # For unique filenames
from datetime import datetime
from flask import Flask, jsonify, Response, request, send_from_directory
from flask_cors import CORS
from PIL import Image
from werkzeug.utils import secure_filename # For securing filenames
import base64 

# Import your TreeDetector and database manager
from utils.tree_detector import TreeDetector
from utils.database_manager import init_db, insert_detection

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

# --- Configuration ---
# IMPORTANT: Update this path to your actual trained YOLOv9 model (best.pt)
YOLO_MODEL_PATH = 'C:/Users/USER/Downloads/fyp project chatbot/models/best.pt' # Adjust this path!

MTL_API_URL = 'http://localhost:5001/predict_image' # Your MTL API endpoint
# Interval (in seconds) for processing frames for tree detection
DETECTION_INTERVAL_SECONDS = 5 # Process a frame for detection every 5 seconds

# --- Video Upload Configuration ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Ensure upload directory exists

# --- Global Variables for Video Capture and Threading ---
cap = None # OpenCV VideoCapture object (can be for live camera or video file)
is_monitoring_active = False
detection_thread = None
latest_frame = None # To store the latest frame for MJPEG streaming
current_video_path = None # Path to the currently playing video file
video_playback_pos = 0 # Current frame number for video playback

# Ensure database is initialized on startup
init_db()

# --- Initialize Tree Detector (will be loaded once on app start) ---
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
        # Convert PIL Image to bytes in JPEG format
        byte_arr = io.BytesIO()
        pil_image.save(byte_arr, format='JPEG')
        image_bytes = byte_arr.getvalue()

        # Base64 encode the image bytes
        image_base64 = base64.b64encode(image_bytes).decode('utf-8') # Decode to string for JSON

        # Prepare the JSON payload
        json_payload = {"image_base64": image_base64}
        
        print("Sending image to MTL API as JSON...")
        # Send the JSON payload using the 'json' parameter in requests.post
        response = requests.post(MTL_API_URL, json=json_payload)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        predictions = response.json()
        print(f"Received MTL predictions: {predictions}")
        return predictions
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to MTL API at {MTL_API_URL}. Is it running?")
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request to MTL API failed: {e}")
        # Print the response content for more details if it's a 4xx/5xx error
        if response is not None:
            print(f"MTL API Response Content: {response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while sending to MTL API: {e}")
        return None


# --- Main Monitoring Logic Thread ---
def monitoring_loop():
    global cap, is_monitoring_active, latest_frame, current_video_path, video_playback_pos

    if not current_video_path:
        print("ERROR: No video file has been uploaded to start monitoring.")
        is_monitoring_active = False
        return

    # If already playing, ensure we release the old one and start fresh for a new loop
    if cap and cap.isOpened():
        cap.release()

    print(f"Attempting to open video file: {current_video_path}")
    cap = cv2.VideoCapture(current_video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open video file {current_video_path}. Please check file path and format.")
        is_monitoring_active = False
        current_video_path = None
        return

    # Reset playback position for a new loop
    video_playback_pos = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, video_playback_pos)

    last_detection_time = time.time()
    print("Monitoring loop started for video file.")

    while is_monitoring_active:
        ret, frame = cap.read() # Read a frame from the video file
        if not ret:
            print("INFO: End of video stream or failed to grab frame. Monitoring loop stopping.")
            is_monitoring_active = False # Stop the loop
            break # Exit the while loop

        latest_frame = frame # Store the latest frame for the /video_feed endpoint
        video_playback_pos += 1 # Increment frame position

        current_time = time.time()
        if current_time - last_detection_time >= DETECTION_INTERVAL_SECONDS:
            last_detection_time = current_time
            print(f"Processing frame {video_playback_pos} for tree detection at {datetime.now().strftime('%H:%M:%S')}")

            if tree_detector:
                try:
                    cropped_tree_images = tree_detector.detect_trees(frame)

                    if cropped_tree_images:
                        print(f"Detected {len(cropped_tree_images)} trees. Sending to MTL API...")
                        for i, tree_img_pil in enumerate(cropped_tree_images):
                            mtl_results = send_image_to_mtl_api(tree_img_pil)
                            
                            if mtl_results:
                                # Store results in the database
                                fruit_type = mtl_results.get('fruit_type', 'unknown')
                                ripeness = mtl_results.get('ripeness', 'unknown')
                                disease = mtl_results.get('disease', 'unknown')
                                confidence_fruit = mtl_results.get('confidence_fruit')
                                confidence_ripeness = mtl_results.get('confidence_ripeness')
                                confidence_disease = mtl_results.get('confidence_disease')
                                
                                insert_detection(
                                    fruit_type=fruit_type,
                                    ripeness=ripeness,
                                    disease=disease,
                                    confidence_fruit=confidence_fruit,
                                    confidence_ripeness=confidence_ripeness,
                                    confidence_disease=confidence_disease,
                                    notes=f"Detection from video stream: {os.path.basename(current_video_path)} (Frame {video_playback_pos}, Tree {i+1})"
                                )
                                print(f"Stored detection: {fruit_type}, {ripeness}, {disease}")
                            else:
                                print(f"MTL API did not return valid results for tree {i+1}.")
                    else:
                        print(f"No trees detected in frame {video_playback_pos}.")
                except Exception as e:
                    print(f"ERROR: Error during tree detection or MTL processing: {e}")
            else:
                print("Tree detector not initialized. Skipping detection.")
        
        # Small delay to control playback speed and prevent burning CPU
        # Adjust as needed. A value like 0.033 would be roughly 30 FPS playback.
        time.sleep(0.01)

    print("Monitoring loop stopped for video file.")
    if cap:
        cap.release() # Release the video file
        cap = None
    # current_video_path is NOT reset here, so the same video can be replayed
    # if you want to automatically clear it, uncomment: current_video_path = None 


# --- Flask API Endpoints ---

@app.route('/upload_video', methods=['POST'])
def upload_video():
    global current_video_path, is_monitoring_active, detection_thread

    # Check if the post request has the file part
    if 'video' not in request.files:
        return jsonify({"error": "No video file part in the request"}), 400
    
    file = request.files['video']
    # If the user does not select a file, the browser submits an empty file without a filename.
    if file.filename == '':
        return jsonify({"error": "No selected video file"}), 400
    
    if file and allowed_file(file.filename):
        # Generate a unique filename to prevent conflicts
        filename = secure_filename(str(uuid.uuid4()) + os.path.splitext(file.filename)[1])
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Set the current video path and attempt to start monitoring
        current_video_path = filepath
        
        if not is_monitoring_active:
            is_monitoring_active = True
            # Re-initialize thread to ensure it starts fresh with new video
            detection_thread = threading.Thread(target=monitoring_loop)
            detection_thread.daemon = True
            detection_thread.start()
            return jsonify({"status": f"Video '{file.filename}' uploaded and monitoring started."}), 200
        else:
            return jsonify({"status": f"Video '{file.filename}' uploaded. Monitoring already active, it will finish current processing or you can stop and restart."}), 200
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
            detection_thread.join(timeout=5) # Wait for thread to finish gracefully
            if detection_thread.is_alive():
                print("Warning: Monitoring thread did not terminate gracefully.")
        # Ensure cap is released if it was opened
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
            time.sleep(0.03) # Adjust frame rate for streaming (~30 FPS)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_latest_detections', methods=['GET'])
def get_latest_detections():
    """Fetches the latest detections from the database for display in UI."""
    from utils.database_manager import get_all_detections # Import here to avoid circular dependency on Flask startup
    try:
        detections = get_all_detections()
        column_names = ['id', 'timestamp', 'fruit_type', 'ripeness', 'disease', 
                        'confidence_fruit', 'confidence_ripeness', 'confidence_disease', 
                        'image_capture_path', 'notes'] # Match your DB schema
        
        detections_dicts = [dict(zip(column_names, row)) for row in detections]
        
        return jsonify(detections_dicts)
    except Exception as e:
        print(f"Error fetching latest detections: {e}")
        return jsonify({"error": "Failed to fetch detections"}), 500

if __name__ == '__main__':
    print("Starting Monitoring API Server...")
    print(f"YOLO Model Path set to: {YOLO_MODEL_PATH}")
    print(f"MTL API URL set to: {MTL_API_URL}")
    print(f"Detection Interval: {DETECTION_INTERVAL_SECONDS} seconds")
    print(f"Video Uploads Folder: {UPLOAD_FOLDER}")
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)