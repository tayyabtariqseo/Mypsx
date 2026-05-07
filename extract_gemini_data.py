import datetime
import pandas as pd
from indicators import get_psx_data, calculate_indicators, calculate_pivots

def extract_for_gemini():
    symbol = "SYS"
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
    print("Columns:", df.columns.tolist())
    latest = df.iloc[-1]
    
    pivots = calculate_pivots(df)
    trad = pivots['traditional']
    
    print(f"## Data for GEMINI.md - {datetime.date.today()}")
    print(f"CMP: {latest['Close']:.2f}")
    print(f"RSI: {latest['RSI']:.2f}")
    print(f"MACD: {latest['MACD_12_26_9']:.2f}")
    print(f"ADX: {latest['ADX_14']:.2f}")
    print(f"SuperTrend: {latest['SUPERT_20_2']:.2f}")
    
    print("\n## Pivots (Traditional)")
    for k, v in trad.items():
        print(f"{k}: {v:.2f}")
        
    print("\n## EMAs")
    ema_lengths = [9, 25, 44, 88, 100, 200]
    for length in ema_lengths:
        print(f"EMA {length}: {latest[f'EMA_{length}']:.2f}")

if __name__ == "__main__":
    extract_for_gemini()
