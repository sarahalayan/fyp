# chatbot_api_server.py
from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS for cross-origin requests
import os
import sys

# Add the directory containing chatbot_agents.py to the Python path
# This ensures you can import from it easily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from utils.chatbot_agents import run_chatbot, agent_executor

app = Flask(__name__)
CORS(app) # Enable CORS for all routes - important for frontend to talk to backend
# In services/chatbot_api_server.py
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Sets max upload size to 16 MB 

# Define a temporary directory for image uploads from the UI
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/chat', methods=['POST'])
def chat():
    if agent_executor is None:
        return jsonify({"error": "Chatbot is not initialized. Check server logs."}), 500

    user_message = request.form.get('message', '') # Get text message from form data
    image_file = request.files.get('image')      # Get image file from form data

    image_path = None
    if image_file:
        try:
            # Save the uploaded image to a temporary file
            filename = image_file.filename
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(temp_path)
            image_path = temp_path
            print(f"DEBUG: Saved uploaded image to temporary path: {image_path}")
        except Exception as e:
            print(f"ERROR: Failed to save uploaded image: {e}")
            return jsonify({"error": f"Failed to process image upload: {e}"}), 400

    try:
        # Call the run_chatbot function from chatbot_agents.py
        # Pass the image_path directly, as run_chatbot expects it now
        chatbot_response = run_chatbot(user_message, image_path=image_path)
        return jsonify({"response": chatbot_response})
    except Exception as e:
        print(f"ERROR: An error occurred during chatbot interaction: {e}")
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        # Clean up the temporary image file if it was created
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"DEBUG: Cleaned up temporary image file: {image_path}")
            except Exception as e:
                print(f"ERROR: Failed to remove temporary image file {image_path}: {e}")


if __name__ == '__main__':
    print("Starting Chatbot API Server...")
    # Make sure to install Flask-CORS: pip install Flask-Cors
    app.run(host='0.0.0.0', port=5000, debug=True) # Run on a different port than MTL API