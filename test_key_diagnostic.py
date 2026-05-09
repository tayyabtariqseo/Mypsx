from google import genai
import os

def test_key():
    key = "AIzaSyCHAKoDciqo4WZoXkbmA0nVMRRU6I9J3RA"
    client = genai.Client(api_key=key)
    models = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
    
    print(f"Testing key: {key[:10]}...")
    for m in models:
        print(f"--- Testing {m} ---")
        try:
            response = client.models.generate_content(model=m, contents="Hello")
            print(f"SUCCESS: {response.text[:50]}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_key()
