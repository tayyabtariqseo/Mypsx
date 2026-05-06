import datetime
import pandas as pd
from indicators import get_psx_data, calculate_indicators, get_live_price, get_company_info
from ai_engine import analyze_with_ai_v2
from persistence import save_analysis, load_cached_analysis

def generate_today():
    symbol = "SYS"
    timeframe = "1D"
    
    # Check if already cached
    existing = load_cached_analysis(symbol)
    if existing:
        print(f"Today's report for {symbol} is already cached.")
        print("--- Report ---")
        print(existing['report'])
        return

    full_name = get_company_info(symbol)
    
    # 1. Fetch Latest Data
    print(f"Fetching latest data for {symbol}...")
    start_date = datetime.datetime.now() - datetime.timedelta(days=365)
    df = get_psx_data(symbol, start_date=start_date)
    
    if df.empty:
        print("Error: Could not fetch historical data.")
        return

    # Split Adjustment (5-for-1 on 2025-06-02)
    split_date = pd.to_datetime("2025-06-02")
    mask = df.index < split_date
    for col in ['Open', 'High', 'Low', 'Close']:
        df.loc[mask, col] = df.loc[mask, col] / 5
    
    df = calculate_indicators(df)
    latest = df.iloc[-1]
    
    current_price = latest['Close']
    rsi = latest['RSI']
    macd = latest['MACD_12_26_9']
    ema9 = latest['EMA_9']
    ema100 = latest['EMA_100']
    ema200 = latest['EMA_200']
    
    ai_data_string = f"Co: {full_name}, P: {current_price:.2f}, RSI: {rsi:.2f}, MACD: {macd:.2f}, EMAs: 9:{ema9:.2f}, 100:{ema100:.2f}, 200:{ema200:.2f}"
    
    print(f"Generating AI report for {symbol} using V2 logic...")
    report = analyze_with_ai_v2(symbol, timeframe, ai_data_string)
    
    if "Error" not in report and "Analysis is currently" not in report:
        save_analysis(symbol, timeframe, ai_data_string, report)
        print("Success: Report saved to cache.")
    else:
        print(f"Failure during generation: {report}")
    
    print("\n--- AI Report ---")
    print(report)

if __name__ == "__main__":
    generate_today()
