from google import genai
import os
import datetime
import json
from dotenv import load_dotenv

load_dotenv()

def get_ai_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def save_summary(type, date_str, data):
    """Saves daily/weekly summaries for tiered memory."""
    path = f"analysis/summaries_{type}.json"
    history = {}
    if os.path.exists(path):
        with open(path, 'r') as f:
            history = json.load(f)
    
    history[date_str] = data
    with open(path, 'w') as f:
        json.dump(history, f)

def get_history_context(type, days=7):
    """Retrieves recent history for tiered context."""
    path = f"analysis/summaries_{type}.json"
    if not os.path.exists(path):
        return ""
    with open(path, 'r') as f:
        history = json.load(f)
    
    # Sort and get last N entries
    sorted_dates = sorted(history.keys(), reverse=True)
    context = ""
    for d in sorted_dates[:days]:
        context += f"\nDate {d}: {history[d]}\n"
    return context

def analyze_portfolio_tiered(report_type, portfolio_data, strategy="Strength-based Recovery"):
    """
    Tiered Analysis: Daily -> Weekly -> Monthly.
    portfolio_data: dict with account names as keys and lists of holdings as values.
    """
    client = get_ai_client()
    if not client: return "Error: API Key missing."

    model = "gemini-2.0-flash" # Default robust model
    
    # Tiered Memory Logic
    memory_context = ""
    if report_type == "Weekly":
        memory_context = "HISTORICAL CONTEXT (Past 7 Days Daily Summaries):\n" + get_history_context("daily", 7)
    elif report_type == "Monthly":
        memory_context = "HISTORICAL CONTEXT (Past 4 Weeks Weekly Summaries):\n" + get_history_context("weekly", 4)

    prompt = f"""
    You are a Senior Portfolio Strategist specializing in the Pakistan Stock Exchange.
    TASK: Generate a {report_type} Portfolio Analysis for a client focused on '{strategy}'.
    
    {memory_context}
    
    CURRENT PORTFOLIO DATA:
    {portfolio_data}
    
    REQUIREMENTS:
    1. For EACH account (RSL, MMK, SPK, SFEL):
       - Brief Technical Review of major holdings.
       - A concise 'Closing Note' for that account.
       - Specific Trade Ideas: Should the user BUY more (Average Down), HOLD, or SELL (to move funds elsewhere)?
    
    2. CONSOLIDATED SUMMARY (Detailed):
       - Overall performance vs market trend.
       - SUGGESTION FOR LOSS RECOVERY: Based on your analysis of all symbols, identify the top 3 moves to reach 'Profit' as early as possible.
       - Explicitly suggest if a weak symbol should be sold to average down a stronger, high-potential symbol (Strength-based Recovery).
    
    Tone: Professional, aggressive towards recovery, but data-driven.
    Output: Professional Markdown.
    """

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        report = response.text
        
        # Save a condensed summary for next tier memory
        summary_prompt = f"Summarize this portfolio report into 3 bullet points for historical memory: {report}"
        summary_res = client.models.generate_content(model=model, contents=summary_prompt)
        save_summary(report_type.lower(), datetime.datetime.now().strftime("%Y-%m-%d"), summary_res.text)
        
        return report
    except Exception as e:
        return f"Analysis Failed: {str(e)}"

def analyze_with_ai_v2(symbol, timeframe, indicator_data):
    # (Existing single-stock logic kept for specific chart views)
    client = get_ai_client()
    if not client: return "Error: API Key missing."
    
    prompt = f"Analyze {symbol} ({timeframe}): {indicator_data}. Focus on trend strength and immediate buy/sell suggestion for loss recovery."
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"
