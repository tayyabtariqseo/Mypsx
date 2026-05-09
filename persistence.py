import os
import json
import datetime

# Baseline file to store "Day 0" values
BASELINE_FILE = "analysis/portfolio_baseline.json"

def get_pkt_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))

def get_baseline():
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_baseline(data):
    os.makedirs("analysis", exist_ok=True)
    # Only save if not already exists (preserving Day 0) or if explicitly resetting
    with open(BASELINE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_cached_analysis(symbol):
    path = f"analysis/{symbol}_latest.json"
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except: return None
    return None

def save_analysis(symbol, timeframe, indicator_data, report):
    os.makedirs("analysis", exist_ok=True)
    path = f"analysis/{symbol}_latest.json"
    data = {
        "symbol": symbol,
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "timeframe": timeframe,
        "indicator_data": indicator_data,
        "report": report,
        "timestamp": datetime.datetime.now().isoformat()
    }
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
