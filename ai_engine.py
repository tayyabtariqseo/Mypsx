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
    """Institutional-grade weighted average calculation for aggregated holdings."""
    structured_data = {}
    for acc_name, holdings in portfolio_dict.items():
        acc_summary = {}
        for item in holdings:
            sym = item['Symbol']
            if sym not in acc_summary:
                acc_summary[sym] = {"Qty": 0, "TotalCost": 0, "CMP": item.get('CMP', 0)}
            acc_summary[sym]["Qty"] += item["Qty"]
            acc_summary[sym]["TotalCost"] += (item["Qty"] * item["Avg Price"])
        
        # Calculate Weighted Average Price
        for sym in acc_summary:
            acc_summary[sym]["AvgPrice"] = round(acc_summary[sym]["TotalCost"] / acc_summary[sym]["Qty"], 2) if acc_summary[sym]["Qty"] > 0 else 0
            del acc_summary[sym]["TotalCost"]
        structured_data[acc_name] = acc_summary
    return structured_data

def ask_ai_question(question, portfolio_dict):
    client = get_ai_client()
    if not client: return "Error: API Key missing."
    
    compact_data = deduplicate_portfolio_by_account(portfolio_dict)
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"]
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""
    DATE: {today_str}. CURRENCY: PKR. ROLE: Senior Portfolio Manager.
    PORTFOLIO DATA: {json.dumps(compact_data, indent=2)}
    INQUIRY: {question}
    STRICT: Use provided CMP. No $ symbols. Professional analysis. Separate accounts.
    """

    tried = []
    for model_name in models:
        avail, _ = is_model_available(model_name)
        if not avail: continue
        tried.append(model_name)
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                return f"**Active Analyst:** `{model_name}`\n\n{response.text}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name, 150) # 150s cooldown
                continue
    return f"RATE_LIMIT: {tried}"

def analyze_portfolio_tiered(report_type, portfolio_dict):
    client = get_ai_client()
    if not client: return "Error: API Key missing."

    compact_data = deduplicate_portfolio_by_account(portfolio_dict)
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest", "gemini-2.0-flash"]
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""
    DATE: {today_str}. CURRENCY: PKR. TASK: {report_type} Institutional Portfolio Review.
    DATA (Grouped by Account): {json.dumps(compact_data, indent=2)}
    REPORT STRUCTURE:
    1. EXECUTIVE SUMMARY: Consolidated status in PKR.
    2. PERFORMANCE OVERVIEW: Show EACH account (RSL, MMK, SPK, SFEL) separately. 
       - Report ONLY Account Totals (Cost, Value, P&L) in PKR.
       - NEVER show individual Ticker tables.
    3. RECOVERY STRATEGY: Separate strategies for each account based on its specific holdings.
    STRICT: No Emojis. No '$'. Use CMP. Professional Tone.
    """

    tried = []
    for model_name in models:
        avail, _ = is_model_available(model_name)
        if not avail: continue
        tried.append(model_name)
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response.text:
                report_content = response.text
                save_cached_report(report_type, report_content)
                return f"**Active Analyst:** `{model_name}`\n\n{report_content}"
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_model_exhausted(model_name, 150)
                continue
    return f"RATE_LIMIT: {tried}"
