import os
import json
import datetime
from persistence import load_cached_analysis, save_analysis

def test_cache():
    symbol = "TEST_SYM"
    timeframe = "1D"
    indicator_data = "RSI: 50, Price: 100"
    report = "This is a test AI report."
    
    # Clean up any existing test cache
    today = datetime.date.today().strftime("%Y-%m-%d")
    cache_file = os.path.join("analysis", f"{symbol}_{today}.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print(f"Removed old test cache: {cache_file}")

    # 1. Test saving
    print("Saving analysis...")
    success = save_analysis(symbol, timeframe, indicator_data, report)
    if success:
        print("Save successful.")
    else:
        print("Save failed.")
        return

    # 2. Test existence
    if os.path.exists(cache_file):
        print(f"Cache file found: {cache_file}")
    else:
        print("Cache file NOT found!")
        return

    # 3. Test loading
    print("Loading analysis...")
    loaded = load_cached_analysis(symbol)
    if loaded:
        print("Load successful.")
        print(f"Symbol: {loaded['symbol']}")
        print(f"Report: {loaded['report']}")
        if loaded['report'] == report:
            print("Report matches!")
        else:
            print("Report mismatch!")
    else:
        print("Load failed.")

if __name__ == "__main__":
    test_cache()
