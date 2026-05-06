import os
import json
import datetime

CACHE_DIR = "analysis"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(symbol):
    """Generates the file path for today's cache for a given symbol."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    return os.path.join(CACHE_DIR, f"{symbol}_{today}.json")

def load_cached_analysis(symbol):
    """Loads today's analysis from the file cache if it exists."""
    path = get_cache_path(symbol)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache for {symbol}: {e}")
            return None
    return None

def save_analysis(symbol, timeframe, indicator_data, report):
    """Saves the AI report and indicator data to a file-based cache."""
    path = get_cache_path(symbol)
    data = {
        "symbol": symbol,
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "timeframe": timeframe,
        "indicator_data": indicator_data,
        "report": report,
        "timestamp": datetime.datetime.now().isoformat()
    }
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving cache for {symbol}: {e}")
        return False
