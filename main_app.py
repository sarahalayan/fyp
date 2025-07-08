# Create a dummy image for testing
dummy_image_path = "C:/Users/USER/Downloads/fyp project chatbot/246.jpg"
dummy_image = Image.new('RGB', (224, 224), color = 'red')
dummy_image.save(dummy_image_path, format='JPEG')
print(f"Created dummy image: {dummy_image_path}")

with open(dummy_image_path, "rb") as f:

    image_bytes_for_test = f.read()

user_query_image = "Hello chatbot, give me predictions for my image of a plant ripeness please."
