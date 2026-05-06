import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from indicators import get_psx_data, calculate_indicators, get_live_price, calculate_pivots, get_company_info
from ai_engine import analyze_with_ai_v2
from persistence import load_cached_analysis, save_analysis
import datetime
import re

# 1. THEME & GLOBAL UI STYLING
st.set_page_config(page_title="PSX-AI Analyzer by Tayyab", layout="wide")

# Initialize Session State
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'show_report' not in st.session_state:
    st.session_state.show_report = False
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Analysis" # "Analysis", "Calls", or "Portfolio"

# Sidebar - Theme Toggle
st.sidebar.header("🎨 Theme Settings")
theme_choice = st.sidebar.radio("Dashboard Mode", options=["Dark", "Light"], index=0)

# Define Colors based on Theme
if theme_choice == "Dark":
    chart_template = "plotly_dark"
    bg_color = "#0e1117"
    text_color = "#E0E0E0"
    card_bg = "#1e1e1e"
    card_text = "#ffffff"
    grid_color = "#2d2d2d"
    candle_up = "#26a69a"
    candle_down = "#ef5350"
else:
    chart_template = "plotly_white"
    bg_color = "#ffffff"
    text_color = "#121212"
    card_bg = "#f9f9f9"
    card_text = "#121212"
    grid_color = "#f0f0f0"
    candle_up = "#00c853"
    candle_down = "#ff5252"

# Apply Global CSS for Full Background and Typography
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    
    /* Full Page Background */
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}
    
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}
    
    .stMetric {{
        background-color: {card_bg};
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }}
    
    h1, h2, h3, h4 {{
        color: {text_color} !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }}
    
    p, li, span {{
        color: {text_color} !important;
        letter-spacing: 0.01em;
        line-height: 1.6;
    }}

    .stTable {{
        background-color: {card_bg};
    }}
    </style>
    """, unsafe_allow_html=True)

# 2. HELPER FUNCTIONS
def is_market_open():
    """Checks if the Pakistan Stock Exchange is currently open (UTC+5)."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_pkt = now_utc.astimezone(datetime.timezone(datetime.timedelta(hours=5)))
    weekday = now_pkt.weekday() # 0=Mon, 4=Fri, 5=Sat, 6=Sun
    time_pkt = now_pkt.time()
    
    if weekday >= 5: # Weekend
        return False
    if weekday == 4: # Friday: 9:00 AM - 4:30 PM
        return datetime.time(9, 0) <= time_pkt <= datetime.time(16, 30)
    else: # Mon-Thu: 9:15 AM - 3:30 PM
        return datetime.time(9, 15) <= time_pkt <= datetime.time(15, 30)

def parse_calls_file(file_path):
    """Parses trade signals from the text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newline or date markers
    blocks = re.split(r'\n(?=📅|\d{1,2}-[A-Za-z]+-\d{2})', content.strip())
    calls = []
    
    for block in blocks:
        if not block.strip(): continue
        
        call = {}
        # Date
        date_match = re.search(r'(?:📅\s*)?(\d{1,2}-[A-Za-z]+-\d{2})', block)
        call['date'] = date_match.group(1) if date_match else "N/A"
        
        # Symbol
        symbol_match = re.search(r'📌\s*([A-Z]+)', block)
        call['symbol'] = symbol_match.group(1) if symbol_match else "N/A"
        
        # Buy1
        b1_match = re.search(r'Buy1:\s*([\d.]+)', block)
        call['buy1'] = float(b1_match.group(1)) if b1_match else 0.0
        
        # Buy2
        b2_match = re.search(r'Buy2:\s*([\d.]+)', block)
        call['buy2'] = float(b2_match.group(1)) if b2_match else 0.0
        
        # Targets
        t_match = re.search(r'Target:\s*([\d.]+)\s*\(S\)', block)
        call['tp1'] = float(t_match.group(1)) if t_match else 0.0
        
        tm_match = re.search(r'([\d.]+)\s*\(M\)', block)
        call['tp2m'] = float(tm_match.group(1)) if tm_match else 0.0
        
        call['target_l'] = "" # Placeholder as not in data
        
        # Stoploss
        sl_match = re.search(r'Stoploss:\s*([\d.]+)', block)
        call['sl'] = float(sl_match.group(1)) if sl_match else 0.0
        
        if call['symbol'] != "N/A":
            calls.append(call)
            
    return calls

def get_call_status(row):
    """Calculates status and hits based on current price with 5% tolerance."""
    cp = row['current_price']
    if cp == 0: return "N/A", "Unknown"
    
    tol = 0.05
    
    # Targets/SL (Call Closed)
    if abs(cp - row['tp1']) / row['tp1'] <= tol:
        return "TP1 Hit", "Call Closed"
    if row['tp2m'] > 0 and abs(cp - row['tp2m']) / row['tp2m'] <= tol:
        return "TP2 Hit", "Call Closed"
    if row['sl'] > 0 and abs(cp - row['sl']) / row['sl'] <= tol:
        return "SL Hit", "Call Closed"
        
    # Buy Zones (Call Open)
    if abs(cp - row['buy1']) / row['buy1'] <= tol:
        return "Near to Buy 1", "Call is again open"
    if row['buy2'] > 0 and abs(cp - row['buy2']) / row['buy2'] <= tol:
        return "Near to Buy 2", "Call is again open"
        
    return "", "In Progress"

def parse_portfolio_file(file_path):
    """Parses portfolio data from text files."""
    import os
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines:
        match = re.search(r'^([A-Z0-9\-]+)\s+(\d+)\s+([\d.]+)', line.strip())
        if match:
            symbol, qty, avg_p = match.groups()
            qty, avg_p = int(qty), float(avg_p)
            data.append({"Symbol": symbol, "Qty": qty, "Avg Price": avg_p, "Invested": qty * avg_p})
    return pd.DataFrame(data) if data else None

# 3. APP HEADER
st.title("📊 PSX-AI Analyzer by Tayyab")

# Sidebar - Stock Inputs
st.sidebar.divider()
st.sidebar.header("📉 Stock Analysis")
symbol = st.sidebar.text_input("Enter Ticker (e.g. SYS, PSO, FFL)", value="SYS").upper()
timeframe = st.sidebar.selectbox("Timeframe", options=["1D", "1W", "1M"], index=0)

# Cached fetching
@st.cache_data(ttl=3600)
def fetch_historical_data(symbol, start_date):
    return get_psx_data(symbol, start_date=start_date)

@st.cache_data(ttl=30) # Rapid refresh for live price
def fetch_live_data(symbol):
    return get_live_price(symbol)

@st.cache_data(ttl=86400)
def fetch_company_info(symbol):
    return get_company_info(symbol)

@st.cache_data(ttl=600)
def get_ai_analysis_v3(symbol, timeframe, ai_data_string):
    cached_data = load_cached_analysis(symbol)
    if cached_data and cached_data.get('timeframe') == timeframe:
        return cached_data['report']
    report = analyze_with_ai_v2(symbol, timeframe, ai_data_string)
    if "Error" not in report and "Analysis is currently" not in report:
        save_analysis(symbol, timeframe, ai_data_string, report)
    return report

# Sidebar Buttons
col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    if st.button("Analyze Stock", width="stretch"):
        st.session_state.view_mode = "Analysis"
        with st.spinner(f"Accessing Live Exchange Data for {symbol}..."):
            market_status = is_market_open()
            full_name = fetch_company_info(symbol)
            live_json = fetch_live_data(symbol) if market_status else None
            start_date = datetime.datetime.now() - datetime.timedelta(days=365)
            df = fetch_historical_data(symbol, start_date)
            if df is not None and not df.empty:
                if symbol == "SYS":
                    split_date = pd.to_datetime("2025-06-02")
                    mask = df.index < split_date
                    for col in ['Open', 'High', 'Low', 'Close']:
                        df.loc[mask, col] = df.loc[mask, col] / 5
                df = calculate_indicators(df)
                latest_hist = df.iloc[-1]
                pivots = calculate_pivots(df, lookback=2)
                current_price = live_json['price'] if live_json else latest_hist['Close']
                st.session_state.analysis_data = {
                    "symbol": symbol, "full_name": full_name, "live_json": live_json,
                    "market_status": market_status, "df": df, "latest_hist": latest_hist,
                    "pivots": pivots, "current_price": current_price, "timeframe": timeframe
                }
                st.session_state.show_report = False
            else:
                st.error(f"No data found for {symbol}.")

with col_b2:
    if st.button("Calls", width="stretch"):
        st.session_state.view_mode = "Calls"

col_b3, col_b4 = st.sidebar.columns(2)
with col_b3:
    if st.button("AI Report", width="stretch"):
        if st.session_state.analysis_data:
            st.session_state.show_report = True
            st.session_state.view_mode = "Analysis"
        else:
            st.sidebar.warning("Please Analyze Stock first!")
with col_b4:
    if st.button("Portfolio", width="stretch"):
        st.session_state.view_mode = "Portfolio"

# 4. MAIN DISPLAY LOGIC
if st.session_state.view_mode == "Analysis" and st.session_state.analysis_data:
    data = st.session_state.analysis_data
    h_col1, h_col2 = st.columns([1, 12])
    with h_col1:
        st.image("https://dps.psx.com.pk/static/images/logo.png", width=80)
    with h_col2:
        st.markdown(f"<h1 style='margin:0;'>{data['full_name']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:gray !important; font-size: 1.1rem; margin-top:-5px;'>{data['symbol']} | Live from PSX Data Portal</p>", unsafe_allow_html=True)

    # Market Status Banner
    market_open = data.get('market_status', False)
    if market_open:
        st.success(f"🟢 **Official PSX Current Price:** {data['current_price']:.2f} | **Updated:** {data['live_json']['timestamp'].strftime('%H:%M:%S')}")
    else:
        st.warning(f"🟡 **Mkt is Close** | **Last Closing:** {data['current_price']:.2f}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", f"{data['current_price']:.2f}")
    m2.metric("RSI (14)", f"{data['latest_hist']['RSI']:.2f}")
    m3.metric("MACD", f"{data['latest_hist']['MACD_12_26_9']:.2f}")
    m4.metric("ADX (14)", f"{data['latest_hist']['ADX_14']:.2f}")

    # Chart logic
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=("Price Action", "Volume", "RSI (14)", "MACD (12, 26, 9)"), row_heights=[0.5, 0.1, 0.2, 0.2])
    df = data['df']
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price", increasing_line_color=candle_up, decreasing_line_color=candle_down), row=1, col=1)
    ema_map = {'EMA_9': '#1e88e5', 'EMA_25': '#ffb300', 'EMA_44': '#8e24aa', 'EMA_100': '#fb8c00', 'EMA_200': '#f44336'}
    for ema_col, color in ema_map.items():
        fig.add_trace(go.Scatter(x=df.index, y=df[ema_col], mode='lines', name=ema_col.replace('_', ' '), line=dict(width=1.2, color=color)), row=1, col=1)
    if 'SUPERT_20_2' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_20_2'], mode='lines', name='SuperTrend', line=dict(dash='dash', color='#4caf50', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='#607d8b'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='#3f51b5', width=2)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#f44336", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#4caf50", row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], name="MACD", line=dict(color='#2196f3')), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], name="Signal", line=dict(color='#ff9800')), row=4, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="Histogram", marker_color='#9e9e9e'), row=4, col=1)
    fig.update_layout(height=1100, template=chart_template, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=60, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_xaxes(gridcolor=grid_color, zeroline=False)
    fig.update_yaxes(gridcolor=grid_color, zeroline=False)
    st.plotly_chart(fig, use_container_width=True)

    if st.session_state.show_report:
        st.divider()
        st.subheader("🤖 Gemini AI Technical Report")
        with st.spinner("Generating Professional AI Report..."):
            latest_hist = data['latest_hist']
            ai_data_string = f"Co: {data['full_name']}, P: {data['current_price']}, RSI: {latest_hist['RSI']}, MACD: {latest_hist['MACD_12_26_9']}, EMAs: 9:{latest_hist['EMA_9']}, 100:{latest_hist['EMA_100']}, 200:{latest_hist['EMA_200']}"
            report = get_ai_analysis_v3(data['symbol'], data['timeframe'], ai_data_string)
            st.markdown(f"<div style='background-color:{card_bg}; color:{card_text}; padding:25px; border-radius:12px; border: 1px solid rgba(128,128,128,0.2); font-size: 1.1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>{report}</div>", unsafe_allow_html=True)

    st.divider()
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.subheader("📍 Pivot Points")
        pivots = data['pivots']
        if pivots:
            tab1, tab2 = st.tabs(["Traditional", "Fibonacci"])
            with tab1: st.table(pd.DataFrame({"Level": ["R3","R2","R1","P","S1","S2","S3"], "Price": [f"{pivots['traditional'][k]:.2f}" for k in ["R3","R2","R1","P","S1","S2","S3"]]}))
            with tab2: st.table(pd.DataFrame({"Level": ["R3","R2","R1","P","S1","S2","S3"], "Price": [f"{pivots['fibonacci'][k]:.2f}" for k in ["R3","R2","R1","P","S1","S2","S3"]]}))
    with t_col2:
        st.subheader("📈 Indicator Summary")
        latest_hist = data['latest_hist']
        ind_list = ["EMA_9", "EMA_25", "EMA_44", "EMA_88", "EMA_100", "EMA_200", "RSI", "MACD_12_26_9", "ADX_14", "Chaikin"]
        st.table(pd.DataFrame({"Indicator": [i.replace('_', ' ') for i in ind_list], "Value": [f"{latest_hist[i]:.2f}" if i != "Chaikin" else f"{latest_hist[i]:.2e}" for i in ind_list]}))

elif st.session_state.view_mode == "Calls":
    st.subheader("🎯 Active Trading Calls")
    with st.spinner("Fetching Live Prices for Calls..."):
        raw_calls = parse_calls_file("calls.txt")
        processed_calls = []
        for call in raw_calls:
            live = fetch_live_data(call['symbol'])
            call['current_price'] = live['price'] if live else 0.0
            hit, status = get_call_status(call)
            call['tp_sl_hit'] = hit
            call['status'] = status
            processed_calls.append(call)
        
        if processed_calls:
            df_calls = pd.DataFrame(processed_calls)
            # Reorder and Rename Columns
            col_order = ['date', 'symbol', 'buy1', 'buy2', 'tp1', 'tp2m', 'target_l', 'sl', 'current_price', 'tp_sl_hit', 'status']
            df_calls = df_calls[col_order]
            df_calls.columns = ["Date", "Symbol", "Buy1 (b1)", "Buy2 (b2)", "Target S (TP1)", "Target M (TP2M)", "Target L", "Stop Loss (SL)", "Current Price", "TP/SL Hit", "Status"]
            
            # Styling
            def color_status(val):
                color = 'transparent'
                if val == 'Call Closed': color = '#ef5350'
                if val == 'Call is again open': color = '#26a69a'
                return f'background-color: {color}'

            # Format prices to 2 decimal places
            price_cols = ["Buy1 (b1)", "Buy2 (b2)", "Target S (TP1)", "Target M (TP2M)", "Stop Loss (SL)", "Current Price"]
            format_dict = {col: "{:.2f}" for col in price_cols}
            
            st.table(df_calls.style.format(format_dict).map(color_status, subset=['Status']))
        else:
            st.info("No active calls found in calls.txt.")

elif st.session_state.view_mode == "Portfolio":
    st.subheader("💼 PSX Portfolio Management")
    
    portfolio_files = {
        "RAFI (RSL)": "RSL.txt",
        "MMK": "MMK.txt",
        "SPK": "SPK.txt",
        "SFEL": "SFEL.txt"
    }
    
    grand_total = 0
    
    for name, file in portfolio_files.items():
        st.markdown(f"### 📁 {name}")
        df_p = parse_portfolio_file(file)
        if df_p is not None:
            # Display Table
            st.table(df_p.style.format({"Avg Price": "{:.2f}", "Invested": "{:,.2f}"}))
            
            # Subtotal
            subtotal = df_p['Invested'].sum()
            st.markdown(f"**Total Invested in {name}:** <span style='font-size:1.2rem; color:#26a69a;'>Rs. {subtotal:,.2f}</span>", unsafe_allow_html=True)
            grand_total += subtotal
            st.divider()
        else:
            st.warning(f"Could not load portfolio data for {name} ({file}).")
    
    # Grand Total
    st.markdown(f"## 💰 Grand Total Portfolio Value")
    st.markdown(f"<div style='background-color:{card_bg}; padding:30px; border-radius:15px; border: 2px solid #26a69a; text-align:center;'> <h1 style='margin:0; color:#26a69a;'>Rs. {grand_total:,.2f}</h1> <p style='margin:0; opacity:0.8;'>Total Amount Invested Across All Accounts</p> </div>", unsafe_allow_html=True)

else:
    st.info("👈 Enter a ticker and click Analyze to begin, or view active Calls/Portfolio.")
