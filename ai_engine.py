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
        api_key = "AIzaSyDqRH_N12GpkxGoaN2AHXP7l3-KcVfdm9g"
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

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

def save_qa_history(question, answer):
    path = "analysis/qa_history.json"
    history = []
    if os.path.exists(path):
        with open(path, 'r') as f: history = json.load(f)
    history.append({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer
    })
    if len(history) > 20: history = history[-20:]
    with open(path, 'w') as f: json.dump(history, f)

def get_qa_history():
    path = "analysis/qa_history.json"
    if not os.path.exists(path): return []
    with open(path, 'r') as f: return json.load(f)

def ask_ai_question(question, portfolio_context):
    client = get_ai_client()
    if not client: return "Error: API Key missing."
    
    # Priority rotation to avoid 429 on free tier
    models = ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro"]
    
    prompt = f"""
    Portfolio Context: {portfolio_context}
    User Question: {question}
    
    Role: Senior Portfolio Recovery Expert for Pakistan Stock Exchange.
    Instructions: 
    - Focus on loss recovery until accounts are profitable, then shift to growth.
    - Provide actionable, professional advice.
    - If data suggests a stock is weak, suggest recovery paths (averaging, switching, or holding).
    """

    for model_name in models:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            answer = response.text
            save_qa_history(question, answer)
            return answer
        except Exception as e:
            if "429" in str(e): continue
            return f"Query Failed: {str(e)}"
    return "AI is temporarily busy (Quota Limit). Please retry in 1 minute."

def analyze_portfolio_tiered(report_type, portfolio_data):
    client = get_ai_client()
    if not client: return "Error: API Key missing."

    models = ["gemini-1.5-flash", "gemini-1.5-pro"]
    memory_context = ""
    if report_type == "Weekly":
        memory_context = "CONTEXT (Past Daily): " + get_history_context("daily", 7)
    elif report_type == "Monthly":
        memory_context = "CONTEXT (Past Weekly): " + get_history_context("weekly", 4)

    prompt = f"""
    You are a Senior Portfolio Strategist (PSX Expert).
    TASK: {report_type} Analysis focused on 'Loss Recovery to Profit' then 'Portfolio Growth'.
    {memory_context}
    DATA: {portfolio_data}
    REQUIREMENTS:
    1. Status for each account (Recovery or Growth phase).
    2. Recovery actions for losing positions using technical methodology (indicators, EMAs).
    3. Trade recommendations (Buy/Sell/Hold).
    """

    for model_name in models:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            report = response.text
            save_summary(report_type.lower(), datetime.datetime.now().strftime("%Y-%m-%d"), report[:500] + "...")
            return report
        except Exception as e:
            if "429" in str(e): continue
            return f"Analysis Failed: {str(e)}"
    return "AI Analysis is currently unavailable due to quota limits."

def analyze_with_ai_v2(symbol, timeframe, indicator_data):
    # Background analysis for indicators, used by other functions
    client = get_ai_client()
    if not client: return "Error: API Key missing."
    prompt = f"Background Technical Analysis for {symbol} ({timeframe}): {indicator_data}. Focus on recovery strategy."
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text
    except: return "Analysis background task paused (Quota)."
