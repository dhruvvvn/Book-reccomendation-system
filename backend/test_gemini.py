import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env file.")
    exit(1)

if api_key == "your_gemini_api_key_here":
    print("❌ Error: GEMINI_API_KEY is still the placeholder value.")
    exit(1)

try:
    print(f"Testing Gemini API Key: {api_key[:5]}...{api_key[-5:]}")
    genai.configure(api_key=api_key)
    
    # Try flash first
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello, are you working? Reply with 'Yes, I am working!' if you are.")
        print(f"Gemini (1.5-flash) Responded: {response.text}")
    except Exception as e:
        print(f"Gemini (1.5-flash) failed: {e}")
        print("Trying gemini-pro...")
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hello")
        print(f"Gemini (pro) Responded: {response.text}")
        
    print("API Key seems to be authenticating, but check model availability.")
except Exception as e:
    # Print error without emojis to avoid encoding issues
    print(f"Gemini API Error: {str(e)}")
