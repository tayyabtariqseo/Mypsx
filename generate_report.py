from ai_engine import analyze_with_ai
import datetime

symbol = "SYS"
timeframe = "1D"

# Data from my latest run_analysis.py run
latest_data = {
    "Close": 145.34,
    "RSI": 47.85,
    "MACD": 3.07,
    "EMA_9": 150.28,
    "EMA_100": 144.99,
    "EMA_200": 139.34,
    "Chaikin": 2.19e+05,
    "ADX": 15.34,
    "SuperTrend": 141.99
}

ai_data_string = f"""
Price: {latest_data['Close']}
RSI: {latest_data['RSI']}
MACD: {latest_data['MACD']}
EMAs: 9:{latest_data['EMA_9']}, 100:{latest_data['EMA_100']}, 200:{latest_data['EMA_200']}
Chaikin: {latest_data['Chaikin']}
DMI/ADX: {latest_data['ADX']}
SuperTrend: {latest_data['SuperTrend']}

Additional Context:
Board Meeting held on May 2, 2026. Approved FY2025 accounts and proposed annual dividend.
A 5-for-1 stock split was recently approved. Current prices are split-adjusted.
Market was closed on May 1 (Labour Day).
CMP dropped from ~152 to 145.34 on April 30.
"""

print("Generating AI Report...")
report = analyze_with_ai(symbol, timeframe, ai_data_string)
print("\n--- AI Analyst Report ---")
print(report)

with open("AI_REPORT.md", "w") as f:
    f.write(f"# AI Analyst Report for {symbol} ({datetime.date.today()})\n\n")
    f.write(report)
