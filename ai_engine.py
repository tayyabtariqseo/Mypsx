from google import genai
import os
import datetime
import json
from dotenv import load_dotenv

load_dotenv()

def get_ai_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except: pass
    
    if not api_key:
        api_key = "AIzaSyCHAKoDciqo4WZoXkbmA0nVMRRU6I9J3RA"
    
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except:
        return None

def save_summary(type, date_str, data):
    path = f"analysis/summaries_{type}.json"
    history = {}
    if os.path.exists(path):
        with open(path, 'r') as f: history = json.load(f)
    history[date_str] = data
    with open(path, 'w') as f: json.dump(history, f)

def get_history_context(type, days=7):
    path = f"analysis/summaries_{type}.json"
    if not os.path.exists(path): return ""
    with open(path, 'r') as f: history = json.load(f)
    sorted_dates = sorted(history.keys(), reverse=True)
    context = ""
    for d in sorted_dates[:days]: context += f"\nDate {d}: {history[d]}\n"
    return context

def save_qa_history(question, answer, model_name):
    path = "analysis/qa_history.json"
    history = []
    if os.path.exists(path):
        with open(path, 'r') as f: history = json.load(f)
    history.append({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": f"[Model: {model_name}]\n{answer}"
    })
    if len(history) > 20: history = history[-20:]
    with open(path, 'w') as f: json.dump(history, f)

def get_qa_history():
    path = "analysis/qa_history.json"
    if not os.path.exists(path): return []
    with open(path, 'r') as f: return json.load(f)

def ask_ai_question(question, portfolio_context):
    client = get_ai_client()
    if not client: return "Error: API Key missing or invalid."
    
    # Updated models based on ListModels verification
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash", "gemini-pro-latest"]
    
    prompt = f"Portfolio Context: {portfolio_context}. User Question: {question}. Role: Senior Portfolio Recovery Expert. Focus on recovery."

    for model_name in models:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            answer = response.text
            save_qa_history(question, answer, model_name)
            return f"**Active Model:** `{model_name}`\n\n{answer}"
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                # If last model also fails with 429
                if model_name == models[-1]:
                    return f"AI Quota Exceeded (All Models). Error with `{model_name}`: {err}"
                continue
            if "404" in err or "NOT_FOUND" in err:
                continue
            return f"Error with `{model_name}`: {err}"
            
    return "All AI models are currently unavailable (Quota or Connectivity)."

def analyze_portfolio_tiered(report_type, portfolio_data):
    client = get_ai_client()
    if not client: return "Error: API Key missing or invalid."

    # Updated models based on ListModels verification
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"]
    memory_context = ""
    if report_type == "Weekly":
        memory_context = "CONTEXT (Past Daily): " + get_history_context("daily", 7)
    elif report_type == "Monthly":
        memory_context = "CONTEXT (Past Weekly): " + get_history_context("weekly", 4)

    prompt = f"TASK: {report_type} Analysis for PSX Portfolio. Goal: Recovery to Profit. {memory_context}. DATA: {portfolio_data}"

    for model_name in models:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            report = response.text
            if not report:
                continue # Try next model if response is empty
            
            # Safe summary saving
            summary_data = report[:500] if len(report) > 500 else report
            save_summary(report_type.lower(), datetime.datetime.now().strftime("%Y-%m-%d"), summary_data)
            
            return f"**Active Model:** `{model_name}`\n\n{report}"
        except Exception as e:
            err = str(e)
            if "429" in err or "404" in err: continue
            return f"Analysis Failed with `{model_name}`: {err}"
    return "AI Analysis Quota Exceeded across all supported models. Please retry in 1 minute."
