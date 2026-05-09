from google import genai
import os
import datetime
import json
import time
from dotenv import load_dotenv
from persistence import mark_model_exhausted, is_model_available, get_cached_report, save_cached_report

load_dotenv()

def get_ai_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except: pass
    if not api_key: api_key = "AIzaSyCHAKoDciqo4WZoXkbmA0nVMRRU6I9J3RA"
    if not api_key: return None
    try: return genai.Client(api_key=api_key)
    except: return None

def deduplicate_portfolio_by_account(portfolio_dict):
    structured_data = {}
    for acc_name, holdings in portfolio_dict.items():
        acc_summary = {}
        for item in holdings:
            sym = item['Symbol']
            if sym not in acc_summary:
                acc_summary[sym] = {"Qty": 0, "AvgPrice": 0, "CMP": item.get('CMP', 0)}
            acc_summary[sym]["Qty"] += item["Qty"]
            acc_summary[sym]["AvgPrice"] = (acc_summary[sym]["AvgPrice"] + item["Avg Price"]) / 2 if acc_summary[sym]["AvgPrice"] > 0 else item["Avg Price"]
        structured_data[acc_name] = acc_summary
    return structured_data

def ask_ai_question(question, portfolio_dict):
    client = get_ai_client()
    if not client: return "Error: API Key missing."
    
    compact_data = deduplicate_portfolio_by_account(portfolio_dict)
    # Comprehensive Model Pool
    models = [
        "gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest", 
        "gemini-pro-latest", "gemini-2.0-flash-lite-001", "gemini-1.5-flash", "gemini-1.5-pro"
    ]
    
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    prompt = f"""
    DATE: {today_str}. CURRENCY: PKR. ROLE: Senior Institutional Analyst.
    DATA: {json.dumps(compact_data, indent=2)}
    QUERY: {question}
    STRICT: No '$'. No assumed dates. No tables of individual tickers. Use CMP.
    """

    tried_models = []
    for model_name in models:
        avail, wait = is_model_available(model_name)
        if not avail: continue
        
        tried_models.append(model_name)
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                return f"**Active Analyst:** `{model_name}`\n\n{response.text}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name)
                continue
    return f"RATE_LIMIT: {tried_models}"

def analyze_portfolio_tiered(report_type, portfolio_dict):
    # Check Cache First
    cached = get_cached_report(report_type)
    if cached:
        return f"**System Note:** Displaying cached report (updated within last hour).\n\n{cached}"

    client = get_ai_client()
    if not client: return "Error: API Key missing."

    compact_data = deduplicate_portfolio_by_account(portfolio_dict)
    models = [
        "gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest", 
        "gemini-2.0-flash", "gemini-2.0-flash-lite-001"
    ]
    
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    prompt = f"""
    DATE: {today_str}. CURRENCY: PKR. TASK: {report_type} Review.
    DATA: {json.dumps(compact_data, indent=2)}
    STRUCTURE: Executive Summary (PKR), Performance Overview (Per Account Totals), Recovery Strategy (Per Account).
    STRICT: Professional. No Emojis. No '$'. No ticker tables. Treat each account as a separate institutional portfolio.
    """

    tried_models = []
    for model_name in models:
        avail, wait = is_model_available(model_name)
        if not avail: continue

        tried_models.append(model_name)
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                report_content = response.text
                save_cached_report(report_type, report_content)
                return f"**Active Analyst:** `{model_name}`\n\n{report_content}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name)
                continue
    return f"RATE_LIMIT: {tried_models}"

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
    if len(history) > 10: history = history[-10:]
    with open(path, 'w') as f: json.dump(history, f)
