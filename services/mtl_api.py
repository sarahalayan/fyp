# mtl_api.py

from flask import Flask, request, jsonify
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import io
import base64

app = Flask(__name__)

# 1. Define your MultitaskModelMobileNetV2 class 
class MultitaskModelMobileNetV2(nn.Module):
    def __init__(self, num_fruit_classes, num_ripeness_classes, num_disease_classes, pretrained=True, freeze_backbone=False):
        super(MultitaskModelMobileNetV2, self).__init__()
        self.mobilenet = models.mobilenet_v2(pretrained=pretrained)
        self.backbone = self.mobilenet.features
        self.backbone_output_size = self.mobilenet.classifier[1].in_features

        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False

        self.fc_fruit = nn.Sequential(
            nn.Linear(self.backbone_output_size, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, num_fruit_classes)
        )

        self.fc_ripeness = nn.Sequential(
            nn.Linear(self.backbone_output_size, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, num_ripeness_classes)
        )

        self.fc_disease = nn.Sequential(
            nn.Linear(self.backbone_output_size, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, num_disease_classes)
        )

    def forward(self, x):
        features = self.backbone(x)
        features = torch.mean(features, [2, 3])
        features = features.view(features.size(0), -1)
        fruit_output = self.fc_fruit(features)
        ripeness_output = self.fc_ripeness(features)
        disease_output = self.fc_disease(features)
        return fruit_output, ripeness_output, disease_output

# 2. Define your class names 
fruit_class_names = ['apple', 'grapes', 'orange', 'strawberry']
disease_class_names = ['Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy', 'Grape___Black_rot', 'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy', 'Orange___Haunglongbing_(Citrus_greening)', 'Strawberry___Leaf_scorch', 'Strawberry___healthy']
ripeness_class_names = ['ripe', 'unripe']

# 3. Instantiate the model with the correct number of classes
num_fruit_classes = len(fruit_class_names)
num_ripeness_classes = len(ripeness_class_names)
num_disease_classes = len(disease_class_names)

# Define the path to the saved model file 
save_path = 'C:/Users/USER/Downloads/fyp project chatbot/models/MultitaskModelMobileNetV2_clean_data.pth'
# Load the model
try:
    mtl_model = MultitaskModelMobileNetV2(
        num_fruit_classes=num_fruit_classes,
        num_ripeness_classes=num_ripeness_classes,
        num_disease_classes=num_disease_classes,
        pretrained=False,
        freeze_backbone=False
    )
    mtl_model.load_state_dict(torch.load(save_path, map_location=torch.device('cpu'))) # Load to CPU first
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mtl_model.to(device)
    mtl_model.eval()
    print(f"MTL Model loaded successfully from {save_path} and moved to {device}!")
except FileNotFoundError:
    print(f"Error: The model file '{save_path}' was not found. Please check the path.")
    mtl_model = None
except Exception as e:
    print(f"An error occurred during model loading: {e}")
    mtl_model = None

# 4. Define the same preprocessing transformations
test_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

@app.route('/predict_image', methods=['POST'])
def predict_image():
    if mtl_model is None:
        return jsonify({"error": "MTL model not loaded. Check server logs."}), 500

    data = request.get_json()
    if not data or 'image_base64' not in data:
        return jsonify({"error": "No image_base64 provided in JSON body."}), 400

    try:
        image_base64 = data['image_base64']
        
        try:
            image_bytes = base64.b64decode(image_base64)
            print(f"DEBUG (mtl_api.py): Successfully decoded base64. Bytes length: {len(image_bytes)}")
        except Exception as e:
            print(f"ERROR (mtl_api.py): Base64 decode failed: {e}")
            return jsonify({"error": f"Invalid base64 encoding: {e}"}), 400
        
        try:
            
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB") 
            print("DEBUG (mtl_api.py): Successfully opened image with PIL.")
        except Exception as e:
            print(f"ERROR (mtl_api.py): PIL Image.open failed: {e}. Raw bytes length: {len(image_bytes)}")
            return jsonify({"error": f"Failed to open image from bytes: {e}"}), 400
        

        # Preprocess the image
        image_tensor = test_transforms(image).unsqueeze(0).to(device)

        # Perform inference
        with torch.no_grad():
            fruit_output, ripeness_output, disease_output = mtl_model(image_tensor)

        # Get predicted labels (indices)
        _, predicted_fruit_idx = torch.max(fruit_output, 1)
        _, predicted_ripeness_idx = torch.max(ripeness_output, 1)
        _, predicted_disease_idx = torch.max(disease_output, 1)

        # Map indices to class names
        predicted_fruit = fruit_class_names[predicted_fruit_idx.item()]
        predicted_ripeness = ripeness_class_names[predicted_ripeness_idx.item()]
        predicted_disease = disease_class_names[predicted_disease_idx.item()]

        return jsonify({
            "fruit": predicted_fruit,
            "ripeness": predicted_ripeness,
            "disease": predicted_disease
        })

    except Exception as e:
        print(f"ERROR (mtl_api.py): An unexpected error occurred during prediction: {e}")
        return jsonify({"error": f"Error processing image: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)