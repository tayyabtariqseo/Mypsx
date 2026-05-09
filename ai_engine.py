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
    """Groups holdings by account and symbol to optimize tokens while preserving account separation."""
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
        
        # Finalize averages for the account
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
    TODAY'S DATE: {today_str}
    CURRENCY: All values are in PKR (Pakistani Rupee).
    ROLE: Senior Institutional Portfolio Manager & PSX Expert.
    
    CONTEXT (Portfolios by Account):
    {json.dumps(compact_data, indent=2)}
    
    USER QUERY: {question}
    
    STRICT INSTRUCTIONS:
    1. Use the EXACT prices (CMP) provided. Never assume or invent "Current Prices".
    2. Deal with each account as a separate portfolio.
    3. Provide professional, data-driven analysis focused on loss recovery.
    4. Do not use '$' symbols. Use 'PKR' or no symbol.
    """

    for model_name in models:
        avail, _ = is_model_available(model_name)
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

def analyze_portfolio_tiered(report_type, portfolio_dict):
    client = get_ai_client()
    if not client: return "Error: API Key missing."

    compact_data = deduplicate_portfolio_by_account(portfolio_dict)
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"]
    
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""
    DATE: {today_str}
    CURRENCY: PKR
    TASK: {report_type} Institutional Portfolio Review.
    GOAL: Loss Recovery (Primary) & Systematic Growth.
    
    DATA (Grouped by Account):
    {json.dumps(compact_data, indent=2)}
    
    REPORT STRUCTURE REQUIREMENTS:
    1. EXECUTIVE SUMMARY: High-level overview of the total {today_str} status in PKR.
    2. PERFORMANCE OVERVIEW (PER ACCOUNT):
       - Create a separate analysis/section for EACH account (e.g., RSL, MMK, SPK, SFEL).
       - Show performance metrics (Cost, Value, P&L) for each account in PKR.
       - Use the EXACT CMP provided in the data. Never say "Assumed Price".
    3. RECOVERY STRATEGY (PER ACCOUNT):
       - Tailor the strategy for each account. Suggest specific recovery paths (Hold/Average/Switch) based on the specific holdings of that account.
    4. TECHNICAL INSIGHTS: Apply background technical analysis (EMA/RSI/Pivots methodology) to justify the recovery moves.
    
    TONE: Senior Portfolio Strategist (Professional, Precise, Actionable).
    STRICT: No '$' symbols. No invented dates. No invented prices.
    """

    for model_name in models:
        avail, _ = is_model_available(model_name)
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
