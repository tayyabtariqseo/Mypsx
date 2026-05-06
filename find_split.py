import pandas as pd
from indicators import get_psx_data
import datetime

symbol = "SYS"
start_date = datetime.datetime.now() - datetime.timedelta(days=365)
df = get_psx_data(symbol, start_date=start_date)

if not df.empty:
    df['pct_change'] = df['Close'].pct_change()
    # Find the row where price dropped by ~80% (1/5th)
    split_row = df[df['pct_change'] < -0.7]
    if not split_row.empty:
        print("Potential split detected:")
        print(split_row)
    else:
        print("No split detected in the last year based on price drop.")
else:
    print("No data found.")
