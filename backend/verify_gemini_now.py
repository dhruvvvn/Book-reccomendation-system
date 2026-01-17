import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

print(f"Testing API Key: {api_key[:5]}...{api_key[-5:]}")
print(f"Model: {model_name}")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Hello, can you hear me?")
    print("Success! Response:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
