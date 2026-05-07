import requests
import datetime
from indicators import get_live_price

symbols = ["FFLM", "FFL", "MLCF", "PIBTL", "THCCL", "PSO", "UNITY", "ASC", "WAVES", "SYS"]

print(f"--- Live Price Test ({datetime.datetime.now()}) ---")

for sym in symbols:
    res = get_live_price(sym)
    if res:
        print(f"✅ {sym}: {res['price']} (Time: {res['timestamp']})")
    else:
        print(f"❌ {sym}: FAILED")

# Test the other DPS endpoint as a fallback
def get_live_price_v2(symbol):
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            price_div = soup.find('div', {'class': 'quote__price'})
            if price_div:
                price_text = price_div.text.strip().replace(',', '')
                return float(price_text)
    except Exception as e:
        print(f"Error v2 for {symbol}: {e}")
    return None

print("\n--- Fallback Price Test (V2 - Scraping) ---")
for sym in symbols:
    p = get_live_price_v2(sym)
    if p:
        print(f"✅ {sym}: {p}")
    else:
        print(f"❌ {sym}: FAILED")
