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

def deduplicate_portfolio_by_account(portfolio_dict):
    structured_data = {}
    for acc_name, holdings in portfolio_dict.items():
        acc_summary = {}
        for item in holdings:
            sym = item['Symbol']
            if sym not in acc_summary:
                acc_summary[sym] = {"Qty": 0, "AvgPrice": 0, "CMP": item.get('CMP', 0), "Count": 0}
            acc_summary[sym]["Qty"] += item["Qty"]
            acc_summary[sym]["AvgPrice"] += item["Avg Price"]
            acc_summary[sym]["Count"] += 1
        
        for sym in acc_summary:
            acc_summary[sym]["AvgPrice"] /= acc_summary[sym]["Count"]
            del acc_summary[sym]["Count"]
        structured_data[acc_name] = acc_summary
    return structured_data

def ask_ai_question(question, portfolio_dict):
    client = get_ai_client()
    if not client: return "Error: API Key missing."
    
    compact_data = deduplicate_portfolio_by_account(portfolio_dict)
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"]
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""
    DATE: {today_str} (Current/Actual)
    CURRENCY: PKR
    ROLE: Senior Portfolio Manager (Institutional).
    
    DATA (Portfolios by Account):
    {json.dumps(compact_data, indent=2)}
    
    USER QUERY: {question}
    
    STRICT INSTRUCTIONS:
    1. NEVER assume a date. Today is {today_str}.
    2. NEVER assume or invent prices. Use CMP.
    3. NO '$' symbols. All values are in PKR.
    4. Provide analysis for EACH account separately as requested.
    5. DO NOT show tables of individual symbols unless requested. Show Account totals.
    """

    tried_models = []
    for model_name in models:
        avail, _ = is_model_available(model_name)
        if not avail: continue
        tried_models.append(model_name)
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                return f"**Analysis Model:** `{model_name}`\n\n{response.text}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name)
                continue
    return f"RATE_LIMIT: Tried {tried_models}"

def analyze_portfolio_tiered(report_type, portfolio_dict):
    client = get_ai_client()
    if not client: return "Error: API Key missing."

    compact_data = deduplicate_portfolio_by_account(portfolio_dict)
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"]
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""
    DATE: {today_str} (STRICTLY CURRENT)
    CURRENCY: PKR
    TASK: {report_type} Institutional Portfolio Review.
    GOAL: Recovery of each account to net profit.
    
    DATA (Grouped by Account):
    {json.dumps(compact_data, indent=2)}
    
    REPORT REQUIREMENTS:
    1. EXECUTIVE SUMMARY: Consolidated status in PKR.
    2. PERFORMANCE OVERVIEW: Show EACH account (RSL, MMK, SPK, SFEL) separately. 
       - Report ONLY Account Totals (Cost, Value, P&L) in PKR.
       - NEVER show a table with individual Tickers/Symbols here.
    3. RECOVERY STRATEGY: Treat each account as a separate portfolio. 
       - Mention specific tickers only in text to explain the strategy (Buy/Hold/Switch).
    4. No Emojis. Professional Tone. No '$'. No assumed dates.
    """

    tried_models = []
    for model_name in models:
        avail, _ = is_model_available(model_name)
        if not avail: continue
        tried_models.append(model_name)
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                return f"**Strategic Model:** `{model_name}`\n\n{response.text}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name)
                continue
    return f"RATE_LIMIT: Tried {tried_models}"

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
