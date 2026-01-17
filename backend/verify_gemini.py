import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"DEBUG: Loaded API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")

if not api_key or api_key == "your_gemini_api_key_here":
    print("❌ ERROR: API Key is missing or default placeholder.")
    exit(1)

genai.configure(api_key=api_key)

models_to_try = [
    "gemini-2.0-flash-lite-preview-02-05",
    "gemini-flash-latest",
    "gemini-pro-latest",
    "gemini-2.0-flash-lite-001"
]

print("\n--- Testing Models ---")
for model_name in models_to_try:
    print(f"\nTesting {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Reply with 'OK'")
        print(f"SUCCESS: {model_name} responded: {response.text.strip()}")
    except Exception as e:
        print(f"FAILED: {model_name} error: {e}")

print("\n--- Done ---")
