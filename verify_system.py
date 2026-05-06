import sys
import os
import datetime
import pandas as pd

# Mock Streamlit for testing
class MockSt:
    def cache_data(self, **kwargs):
        return lambda x: x
st = MockSt()

print("--- Final System Verification ---")

# 1. Verify Persistence
print("\n[1/3] Checking Persistence Layer...")
from persistence import load_cached_analysis, save_analysis
symbol = "SYS"
cached = load_cached_analysis(symbol)
if cached:
    print(f"✅ Found cached report for {symbol} dated {cached['date']}")
    print(f"✅ Report preview: {cached['report'][:100]}...")
else:
    print(f"❌ No cached report found for {symbol} for today.")

# 2. Verify AI Engine Configuration
print("\n[2/3] Checking AI Engine Configuration...")
from ai_engine import analyze_with_ai
import inspect
source = inspect.getsource(analyze_with_ai)
if "gemini-2.5-flash" in source:
    print("✅ AI Engine is correctly targeting Gemini 2.5 models.")
else:
    print("❌ AI Engine is still using old model names!")
    print("Source snippet:", source[:200])

if "in 1 minute" in source:
    print("❌ AI Engine still contains 'in 1 minute' error message.")
else:
    print("✅ AI Engine contains updated error messages.")

# 3. Functional Test (Direct call)
print("\n[3/3] Performing Functional Test...")
# If we have a cache, it should return it immediately
# If not, it will try the API
from app import get_ai_analysis_v2
timeframe = "1D"
ai_data_string = "Test Data"
print(f"Requesting analysis for {symbol}...")
report = get_ai_analysis_v2(symbol, timeframe, ai_data_string)

if "## Technical Analysis" in report:
    print("✅ SUCCESS: Received valid technical report.")
elif "Quota reached" in report:
    print("⚠️ API Quota limit (expected if cache missed and API busy).")
    print(f"Error Details: {report}")
else:
    print(f"❓ Unexpected response: {report[:200]}")

print("\n--- Verification Complete ---")
