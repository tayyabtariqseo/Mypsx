from google import genai
import os
import datetime
import json
import time
from dotenv import load_dotenv
from persistence import mark_model_exhausted, is_model_available

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
    if not api_key: return None
    try: return genai.Client(api_key=api_key)
    except: return None

def deduplicate_portfolio(portfolio_data):
    """Aggregates holdings by symbol to reduce AI input size and avoid redundant analysis."""
    dedup = {}
    for item in portfolio_data:
        sym = item['Symbol']
        if sym not in dedup:
            dedup[sym] = {"Qty": 0, "AvgPrice": 0, "Count": 0}
        dedup[sym]["Qty"] += item["Qty"]
        dedup[sym]["AvgPrice"] += item["Avg Price"]
        dedup[sym]["Count"] += 1
    
    # Finalize averages
    for sym in dedup:
        dedup[sym]["AvgPrice"] /= dedup[sym]["Count"]
        del dedup[sym]["Count"]
    return dedup

def ask_ai_question(question, portfolio_data):
    client = get_ai_client()
    if not client: return "Error: API Key missing."
    
    compact_data = deduplicate_portfolio(portfolio_data)
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"]
    
    prompt = f"""
    ROLE: Senior Financial Analyst & Portfolio Strategist (PSX Expert).
    CONTEXT: {compact_data}
    USER QUERY: {question}
    INSTRUCTION: Provide a data-driven, professional analysis. Avoid generic filler. Focus on recovery and strategic alpha.
    """

    for model_name in models:
        avail, wait_time = is_model_available(model_name)
        if not avail: continue

        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                return f"**Analysis Model:** `{model_name}`\n\n{response.text}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name)
                continue
    return "RATE_LIMIT"

def analyze_portfolio_tiered(report_type, portfolio_data):
    client = get_ai_client()
    if not client: return "Error: API Key missing."

    compact_data = deduplicate_portfolio(portfolio_data)
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"]
    
    prompt = f"""
    TASK: {report_type} Institutional Portfolio Review.
    GOAL: Loss Recovery & Systematic Growth.
    DATA: {compact_data}
    REQUIREMENTS: Professional markdown, technical methodology (EMA/RSI context), actionable trade logic.
    """

    for model_name in models:
        avail, wait_time = is_model_available(model_name)
        if not avail: continue

        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                return f"**Strategic Model:** `{model_name}`\n\n{response.text}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name)
                continue
    return "RATE_LIMIT"

def get_qa_history():
    path = "analysis/qa_history.json"
    if not os.path.exists(path): return []
    try:
        with open(path, 'r') as f: return json.load(f)
    except: return []

def save_qa_history(question, answer, model_name):
    path = "analysis/qa_history.json"
    history = get_qa_history()
    history.append({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": f"[Model: {model_name}]\n{answer}"
    })
    if len(history) > 15: history = history[-15:]
    with open(path, 'w') as f: json.dump(history, f)
