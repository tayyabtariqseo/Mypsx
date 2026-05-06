import pandas as pd
from indicators import get_psx_data, calculate_indicators, get_live_price, calculate_pivots
import datetime

symbol = "SYS"
print(f"--- Analysis for {symbol} ---")

# 1. Get Live Snapshot
live_data = get_live_price(symbol)
if live_data:
    print(f"Live Price: {live_data['price']:.2f} as of {live_data['timestamp']}")
else:
    print("Live price unavailable.")

# 2. Get Historical Data
start_date = datetime.datetime.now() - datetime.timedelta(days=365)
df = get_psx_data(symbol, start_date=start_date)

if df.empty:
    print("No historical data found.")
else:
    # Split Adjustment (5-for-1 on 2025-06-02)
    split_date = pd.to_datetime("2025-06-02")
    mask = df.index < split_date
    for col in ['Open', 'High', 'Low', 'Close']:
        df.loc[mask, col] = df.loc[mask, col] / 5
    
    print("\n--- First 10 rows of Adjusted Data ---")
    print(df.head(10))
    # 3. Calculate Indicators
    df = calculate_indicators(df)
    
    print("\n--- Indicators for Last 5 Days ---")
    cols_to_show = ['Close', 'RSI', 'MACD_12_26_9', 'ADX_14', 'EMA_9', 'SUPERT_20_2']
    print(df[cols_to_show].tail(5))
    
    latest = df.iloc[-1]
    
    print("\n--- Technical Indicators (Daily) ---")
    print(f"CMP: {latest['Close']:.2f}")
    print(f"RSI (14): {latest['RSI']:.2f}")
    print(f"MACD: {latest['MACD_12_26_9']:.2f}")
    print(f"Chaikin: {latest['Chaikin']:.2e}")
    print(f"ADX (14): {latest['ADX_14']:.2f}")
    print(f"SuperTrend: {latest['SUPERT_20_2']:.2f}")
    
    print("\n--- EMAs ---")
    for length in [9, 25, 44, 88, 100, 200]:
        print(f"EMA {length}: {latest[f'EMA_{length}']:.2f}")
        
    # 4. Pivots
    pivots = calculate_pivots(df)
    if pivots:
        trad = pivots['traditional']
        print("\n--- Support & Resistance (Traditional Pivots) ---")
        print(f"R2: {trad['R2']:.2f}")
        print(f"R1: {trad['R1']:.2f}")
        print(f"Pivot (P): {trad['P']:.2f}")
        print(f"S1: {trad['S1']:.2f}")
        print(f"S2: {trad['S2']:.2f}")

    # Save to a summary file for easy reading
    with open("ANALYSIS_SUMMARY.txt", "w") as f:
        f.write(f"Analysis for {symbol} - {datetime.datetime.now()}\n")
        f.write(f"CMP: {latest['Close']:.2f}\n")
        f.write(f"RSI: {latest['RSI']:.2f}\n")
        f.write(f"MACD: {latest['MACD_12_26_9']:.2f}\n")
        f.write(f"Chaikin: {latest['Chaikin']:.2e}\n")
        f.write(f"ADX: {latest['ADX_14']:.2f}\n")
        f.write(f"SuperTrend: {latest['SUPERT_20_2']:.2f}\n")
        f.write("\nEMAs:\n")
        for length in [9, 25, 44, 88, 100, 200]:
            f.write(f"EMA {length}: {latest[f'EMA_{length}']:.2f}\n")
