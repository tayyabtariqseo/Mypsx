import psxdata

print("--- Help for psxdata.quote ---")
help(psxdata.quote)

print("\n--- Listing first 10 tickers ---")
try:
    ts = psxdata.tickers()
    print(ts[:10])
except Exception as e:
    print(f"Error: {e}")
