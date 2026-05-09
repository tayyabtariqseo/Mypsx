from google import genai
import os

def list_models():
    key = "AIzaSyCHAKoDciqo4WZoXkbmA0nVMRRU6I9J3RA"
    client = genai.Client(api_key=key)
    
    print("Listing available models...")
    try:
        # The list_models method in the new SDK
        for model in client.models.list():
            print(f"Name: {model.name}, Supported Actions: {model.supported_actions}")
    except Exception as e:
        print(f"ERROR listing models: {e}")

if __name__ == "__main__":
    list_models()
