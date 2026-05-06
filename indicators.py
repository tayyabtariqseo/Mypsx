import pandas as pd
import pandas_ta as ta
from psxdata import stocks
import requests
import datetime

def get_live_price(symbol):
    """
    Fetches the absolute latest price from the PSX Data Portal (DPS).
    """
    url = f"https://dps.psx.com.pk/timeseries/int/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            data_points = data.get('data', [])
            if data_points:
                # The PSX DPS feed is sorted Newest-to-Oldest. 
                # data[0] is the current live price.
                latest = data_points[0]
                
                # Convert UTC timestamp to PKT (UTC+5)
                utc_dt = datetime.datetime.fromtimestamp(latest[0], tz=datetime.timezone.utc)
                pkt_dt = utc_dt.astimezone(datetime.timezone(datetime.timedelta(hours=5)))
                
                return {
                    "price": float(latest[1]),
                    "timestamp": pkt_dt,
                    "volume": latest[2]
                }
        return None
    except:
        return None

def get_psx_data(symbol, start_date=None, end_date=None):
    """
    Fetches data for a PSX symbol using psxdata library.
    Normalizes the format to match yfinance output (DatetimeIndex, Capitalized Columns).
    """
    try:
        # psxdata returns data for the symbol
        df = stocks(symbol)
        if df is None or df.empty:
            return pd.DataFrame()

        # Normalize format
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df = df.set_index('date')
        
        # Rename columns to Title Case (Open, High, Low, Close, Volume)
        rename_map = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        df = df.rename(columns=rename_map)
        
        # Keep only the OHLCV columns
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Filter by date range
        if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]
            
        return df
    except Exception as e:
        print(f"Error fetching data with psxdata: {e}")
        return pd.DataFrame()

def calculate_pivots(df, lookback=2):
    """
    Calculates Traditional and Fibonacci Pivot Points.
    Uses OHLC from 'lookback' bars ago.
    """
    if len(df) < lookback:
        return None
    
    prev = df.iloc[-lookback]
    h, l, c = prev['High'], prev['Low'], prev['Close']
    range_hl = h - l
    
    # Traditional (Floor)
    p = (h + l + c) / 3
    trad = {
        "P": p,
        "R1": (2 * p) - l,
        "S1": (2 * p) - h,
        "R2": p + range_hl,
        "S2": p - range_hl,
        "R3": h + 2 * (p - l),
        "S3": l - 2 * (h - p)
    }
    
    # Fibonacci
    fib = {
        "P": p,
        "R1": p + 0.382 * range_hl,
        "S1": p - 0.382 * range_hl,
        "R2": p + 0.618 * range_hl,
        "S2": p - 0.618 * range_hl,
        "R3": p + 1.000 * range_hl,
        "S3": p - 1.000 * range_hl
    }
    
    return {"traditional": trad, "fibonacci": fib}

def get_company_info(symbol):
    """
    Fetches the full company name from the PSX Data Portal.
    """
    # Try the company profile page which is more reliable for the name
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for the name in the header
            name_div = soup.find('div', {'class': 'quote__name'})
            if name_div:
                return name_div.text.strip()
    except:
        pass
    
    # Fallback to Ticker
    return symbol

def calculate_indicators(df):
    """
    Calculates all user-specified indicators.
    """
    if df.empty:
        return df

    # RSI (14)
    df['RSI'] = ta.rsi(df['Close'], length=14)

    # MACD (12, 26, 9)
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df = pd.concat([df, macd], axis=1)

    # EMAs (9, 25, 44, 88, 100, 200)
    ema_lengths = [9, 25, 44, 88, 100, 200]
    for length in ema_lengths:
        df[f'EMA_{length}'] = ta.ema(df['Close'], length=length)

    # Chaikin Oscillator (3/10) - uses 'adosc' in pandas-ta
    df['Chaikin'] = ta.adosc(df['High'], df['Low'], df['Close'], df['Volume'], fast=3, slow=10)

    # DMI (14/14) - Returns ADX, +DI, -DI
    dmi = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, dmi], axis=1)

    # SuperTrend (20, 2)
    st = ta.supertrend(df['High'], df['Low'], df['Close'], length=20, multiplier=2)
    df = pd.concat([df, st], axis=1)

    return df
