# tree_detector.py

import os
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image # For converting NumPy arrays to PIL Images if needed

class TreeDetector:
    def __init__(self, model_path: str):
        """
        Initializes the TreeDetector by loading the YOLOv9 model.

        Args:
            model_path (str): The path to the trained YOLOv9 model weights (e.g., 'path/to/best.pt').
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"YOLOv9 model not found at: {model_path}")
        
        self.model = YOLO(model_path)
        print(f"Tree detection model loaded successfully from: {model_path}")
        

    def detect_trees(self, image_np: np.ndarray, confidence_threshold: float = 0.5) -> list[Image.Image]:
        """
        Detects trees in a given image (NumPy array) and returns cropped PIL Images
        of the detected trees.

        Args:
            image_np (np.ndarray): The input image as a NumPy array (H, W, C - BGR format from OpenCV).
            confidence_threshold (float): Minimum confidence score for a detection to be considered.

        Returns:
            list[PIL.Image.Image]: A list of PIL Image objects, where each image is a cropped
                                   region of a detected tree. Returns an empty list if no trees
                                   are detected or if the image is invalid.
        """
        if not isinstance(image_np, np.ndarray) or image_np.ndim != 3:
            print("Warning: Input image_np must be a 3-dimensional NumPy array.")
            return []

        image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)

        # Run inference
        # The 'verbose=False' prevents excessive logging during detection for cleaner output
        results = self.model(image_rgb, verbose=False) 
        
        cropped_tree_images = []

        # Iterate over results (one result object per image passed to model)
        for r in results:
            # Check if any detections (boxes) are present
            if r.boxes is not None:
                for box in r.boxes:
                    confidence = box.conf.item() # Get confidence score as a standard float
                    
                    if confidence >= confidence_threshold:
                        # Get bounding box coordinates in xyxy format
                        # Ultralytics boxes return xyxy coordinates by default
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                        # Ensure coordinates are within image bounds
                        h, w, _ = image_np.shape
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)

                        # Crop the detected region from the original NumPy array (BGR)
                        cropped_np = image_np[y1:y2, x1:x2]

                        # Convert cropped NumPy array (BGR) to PIL Image (RGB) for MTL agent compatibility
                        # MTL agent likely expects an image format it can decode, a PIL image is good.
                        if cropped_np.size > 0: # Ensure crop is not empty
                            cropped_pil = Image.fromarray(cv2.cvtColor(cropped_np, cv2.COLOR_BGR2RGB))
                            cropped_tree_images.append(cropped_pil)
                            # print(f"DEBUG: Detected tree with confidence {confidence:.2f}, cropped size {cropped_pil.size}")

        return cropped_tree_images

# --- Example Usage (for testing this module) ---
if __name__ == "__main__":

    
    # Placeholder for your actual model path:
    YOUR_ACTUAL_YOLO_MODEL_PATH = 'C:/Users/USER/Downloads/fyp project chatbot/best.pt'
    
    dummy_model_dir = 'temp_models'
    os.makedirs(dummy_model_dir, exist_ok=True)
    dummy_model_path = os.path.join(dummy_model_dir, 'best.pt')
    if not os.path.exists(dummy_model_path):
        
        with open(dummy_model_path, 'w') as f:
            f.write('')
        print(f"Created a dummy model file at {dummy_model_path}. "
              "Please REPLACE 'YOUR_ACTUAL_YOLO_MODEL_PATH' "
              "with the correct path to your actual trained YOLOv9 model.")
 
    dummy_image_path="C:/Users/USER/Downloads/fyp project chatbot/istockphoto-1490263061-612x612_jpg.rf.b83ac7b7b76ecd0416d5738253ceb820.jpg"
    if not os.path.exists(dummy_image_path):
        dummy_image_np = np.zeros((640, 640, 3), dtype=np.uint8) # Create a black image
        cv2.imwrite(dummy_image_path, dummy_image_np)
        print(f"Created a dummy image at {dummy_image_path}. ")
    
    # --- Actual Test Run ---
    print("\n--- Testing TreeDetector ---")
    try:
        detector = TreeDetector(model_path=YOUR_ACTUAL_YOLO_MODEL_PATH)
        
        # Load a test image (replace with your actual test image if desired)
        test_image_np = cv2.imread(dummy_image_path) # Read as BGR
        if test_image_np is None:
            print(f"Error: Could not load test image at {dummy_image_path}")
        else:
            print(f"Test image loaded with shape: {test_image_np.shape}")
            cropped_trees = detector.detect_trees(test_image_np)

            if cropped_trees:
                print(f"Detected {len(cropped_trees)} potential trees.")
                # Save and display the first detected tree for verification
                for i, tree_img in enumerate(cropped_trees):
                    output_path = f"detected_tree_{i}.jpg"
                    tree_img.save(output_path)
                    print(f"Saved detected tree {i+1} to {output_path}")
            else:
                print("No trees detected in the test image (or dummy image).")

    except FileNotFoundError as e:
        print(f"Failed to initialize TreeDetector: {e}")
        print("Please ensure 'YOUR_ACTUAL_YOLO_MODEL_PATH' points to your valid 'best.pt' file.")
    except Exception as e:
        print(f"An error occurred during TreeDetector test: {e}")

    # Clean up dummy files if they were created
    if os.path.exists(dummy_model_path):
        os.remove(dummy_model_path)
        os.rmdir(dummy_model_dir)
    if os.path.exists(dummy_image_path):
        os.remove(dummy_image_path)