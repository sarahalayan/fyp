import requests
import base64
from PIL import Image
import io
import os

# Base URL of your Flask API
API_URL = "http://localhost:5001/predict_image"

# --- 1. Create a dummy image for testing ---
def create_dummy_image(path="dummy_image.jpg"): # Changed extension to .jpg
    try:
        # Create a simple red square image
        img = Image.new('RGB', (224, 224), color = 'red')
        img.save(path, format='JPEG') # Specify format as 'JPEG' for .jpg files
        print(f"Dummy image saved to {path}")
        return path
    except Exception as e:
        print(f"Error creating dummy image: {e}")
        return None

# --- 2. Function to load and encode an image ---
def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return None
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

# --- Main test logic ---
if __name__ == "__main__":
    print("Starting MTL API test...")

    # Create a dummy image or specify a path to an existing one
    test_image_path = "C:/Users/USER/Downloads/fyp project chatbot/246.jpg" # Ensure this matches the function default
    if not os.path.exists(test_image_path):
        test_image_path = create_dummy_image(test_image_path)
        if test_image_path is None:
            print("Could not create/find test image. Exiting.")
            exit()

    # Encode the image
    image_base64 = encode_image_to_base64(test_image_path)

    if image_base64:
        # Prepare the data payload
        data = {'image_base64': image_base64}

        try:
            print(f"Sending POST request to {API_URL}...")
            response = requests.post(API_URL, json=data) # Send as JSON
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

            predictions = response.json()
            print("\n--- API Response (Predictions) ---")
            print(predictions)

            # Basic validation of the response structure
            if isinstance(predictions, dict) and all(key in predictions for key in ['fruit', 'ripeness', 'disease']):
                print("\nTest SUCCESS: Received predictions for all tasks.")
                print(f"Fruit: {predictions['fruit']}")
                print(f"Ripeness: {predictions['ripeness']}")
                print(f"Disease: {predictions['disease']}")
            else:
                print("\nTest WARNING: Response structure might not be as expected.")
                print(f"Raw response: {predictions}")

        except requests.exceptions.ConnectionError:
            print("\nTest FAILED: Could not connect to the Flask API.")
            print("Please ensure 'mtl_api.py' is running in another terminal.")
        except requests.exceptions.RequestException as e:
            print(f"\nTest FAILED: An HTTP request error occurred: {e}")
            print(f"Response status code: {response.status_code if 'response' in locals() else 'N/A'}")
            print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
        except Exception as e:
            print(f"\nTest FAILED: An unexpected error occurred: {e}")
    else:
        print("Image encoding failed, cannot proceed with API test.")

    # Clean up dummy image if created
    if os.path.exists(test_image_path) and test_image_path == "dummy_image.jpg": # Changed extension to .jpg
        os.remove(test_image_path)
        print(f"Cleaned up {test_image_path}")