import yfinance as yf
import pandas as pd
import datetime

symbol = "SYS.PSX" # Standard format for PSX on yfinance
print(f"--- Fetching {symbol} via yfinance ---")

# Try SYS.PSX and SYS.KA (Karachi)
for s in ["SYS.PSX", "SYS.KA"]:
    print(f"\nTrying {s}...")
    try:
        ticker = yf.Ticker(s)
        df = ticker.history(period="1mo")
        if not df.empty:
            print(f"Success with {s}!")
            print(df[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10))
        else:
            print(f"No data for {s}")
    except Exception as e:
        print(f"Error with {s}: {e}")
