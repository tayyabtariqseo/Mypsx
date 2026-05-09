import time
import os
import json
import datetime

LIMITS_FILE = "analysis/ai_limits.json"
CACHE_DIR = "analysis/reports"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_pkt_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))

def load_limits():
    if os.path.exists(LIMITS_FILE):
        try:
            with open(LIMITS_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_limits(limits):
    os.makedirs("analysis", exist_ok=True)
    with open(LIMITS_FILE, 'w') as f: json.dump(limits, f)

def mark_model_exhausted(model_name, duration_sec=120): # Increased to 120s for safety
    limits = load_limits()
    limits[model_name] = time.time() + duration_sec
    save_limits(limits)

def is_model_available(model_name):
    limits = load_limits()
    if model_name in limits:
        if time.time() < limits[model_name]:
            return False, int(limits[model_name] - time.time())
    return True, 0

def get_baseline():
    if os.path.exists("analysis/portfolio_baseline.json"):
        with open("analysis/portfolio_baseline.json", 'r') as f: return json.load(f)
    return {}

def save_baseline(data):
    os.makedirs("analysis", exist_ok=True)
    with open("analysis/portfolio_baseline.json", 'w') as f: json.dump(data, f, indent=4)

# Report Caching Logic
def get_cached_report(report_type):
    path = os.path.join(CACHE_DIR, f"{report_type.lower()}.json")
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                # Cache valid for 1 hour
                if time.time() - data['timestamp'] < 3600:
                    return data['report']
        except: return None
    return None

def save_cached_report(report_type, content):
    path = os.path.join(CACHE_DIR, f"{report_type.lower()}.json")
    data = {
        "timestamp": time.time(),
        "report": content
    }
    with open(path, 'w') as f: json.dump(data, f)
