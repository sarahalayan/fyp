import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv() # Ensure your .env is loaded

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("--- Available Gemini Models ---")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"Name: {m.name}, Supported Methods: {m.supported_generation_methods}")
print("----------------------------")