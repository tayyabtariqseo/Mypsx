import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from indicators import get_psx_data, calculate_indicators, get_live_price, calculate_pivots, get_company_info
from ai_engine import analyze_with_ai_v2
from persistence import load_cached_analysis, save_analysis
import datetime
import re

# 1. THEME & GLOBAL UI STYLING
st.set_page_config(page_title="PSX-AI Portfolio Manager", layout="wide")

# Initialize Session State
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Portfolio"

# Sidebar - Theme Toggle
st.sidebar.header("🎨 Theme Settings")
theme_choice = st.sidebar.radio("Dashboard Mode", options=["Dark", "Light"], index=0)

# Define Colors based on Theme
if theme_choice == "Dark":
    bg_color = "#0e1117"
    text_color = "#E0E0E0"
    card_bg = "#1e1e1e"
    card_text = "#ffffff"
    accent_color = "#26a69a"
    neg_color = "#ef5350"
else:
    bg_color = "#ffffff"
    text_color = "#121212"
    card_bg = "#f9f9f9"
    card_text = "#121212"
    accent_color = "#00c853"
    neg_color = "#ff5252"

# Apply Global CSS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp {{ background-color: {bg_color} !important; color: {text_color} !important; }}
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stTable {{ background-color: {card_bg}; }}
    h1, h2, h3 {{ color: {text_color} !important; font-weight: 700 !important; }}
    </style>
    """, unsafe_allow_html=True)

# 2. HELPER FUNCTIONS
@st.cache_data(ttl=30)
def fetch_live_data(symbol):
    """Fetches live price for a symbol."""
    # Handle futures names for price fetching (strip -MAY etc)
    clean_symbol = symbol.split('-')[0]
    return get_live_price(clean_symbol)

def parse_portfolio_file(file_path):
    """Parses portfolio data from text files."""
    import os
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines:
        # Regex to capture Symbol Qty Price
        match = re.search(r'^([A-Z0-9\-]+)\s+(\d+)\s+([\d.]+)', line.strip())
        if match:
            symbol, qty, avg_p = match.groups()
            qty, avg_p = int(qty), float(avg_p)
            data.append({"Symbol": symbol, "Qty": qty, "Purchase Price": avg_p})
    return data

# 3. MAIN PORTFOLIO LOGIC
st.title("💼 PSX Portfolio Management")

portfolio_files = {
    "RAFI (RSL)": "RSL.txt",
    "MMK": "MMK.txt",
    "SPK": "SPK.txt",
    "SFEL": "SFEL.txt"
}

# Sidebar Account Selection
st.sidebar.divider()
st.sidebar.header("📂 Account Selection")
selected_accounts = st.sidebar.multiselect(
    "Select Accounts to View",
    options=list(portfolio_files.keys()),
    default=list(portfolio_files.keys())
)

if not selected_accounts:
    st.info("👈 Please select one or more accounts from the sidebar to view your portfolio.")
else:
    # 1. Aggregate Data
    all_rows = []
    for acc in selected_accounts:
        file = portfolio_files[acc]
        rows = parse_portfolio_file(file)
        if rows:
            for r in rows:
                r['Account'] = acc
                all_rows.append(r)
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        # 2. Fetch Live Prices (Unique Symbols)
        unique_symbols = df['Symbol'].unique()
        with st.spinner("Fetching Live Market Prices..."):
            price_map = {}
            for sym in unique_symbols:
                live = fetch_live_data(sym)
                price_map[sym] = live['price'] if live else 0.0
        
        # 3. Calculate Metrics
        df['Current Mkt Price'] = df['Symbol'].map(price_map)
        df['Investment Value'] = df['Qty'] * df['Purchase Price']
        df['Current Value'] = df['Qty'] * df['Current Mkt Price']
        df['Profit/Loss'] = df['Current Value'] - df['Investment Value']
        df['P/L %'] = (df['Profit/Loss'] / df['Investment Value']) * 100
        
        # 4. Display Account-wise Tables or Merged View
        grand_total_invested = 0
        grand_total_current = 0
        
        for acc in selected_accounts:
            st.subheader(f"📁 {acc}")
            acc_df = df[df['Account'] == acc].copy()
            
            # Subtotals
            acc_invested = acc_df['Investment Value'].sum()
            acc_current = acc_df['Current Value'].sum()
            acc_pl = acc_current - acc_invested
            acc_pl_pct = (acc_pl / acc_invested * 100) if acc_invested > 0 else 0
            
            grand_total_invested += acc_invested
            grand_total_current += acc_current
            
            # Formatting for display
            display_cols = ["Symbol", "Qty", "Purchase Price", "Investment Value", "Current Mkt Price", "Profit/Loss", "P/L %"]
            acc_display = acc_df[display_cols].copy()
            
            # Styling function
            def style_pl(val):
                color = accent_color if val >= 0 else neg_color
                return f'color: {color}; font-weight: bold'

            st.table(acc_display.style.format({
                "Purchase Price": "{:.2f}",
                "Investment Value": "{:,.2f}",
                "Current Mkt Price": "{:.2f}",
                "Profit/Loss": "{:,.2f}",
                "P/L %": "{:.2f}%"
            }).map(style_pl, subset=['Profit/Loss', 'P/L %']))
            
            # Account Summary Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Invested", f"Rs. {acc_invested:,.2f}")
            c2.metric("Current Value", f"Rs. {acc_current:,.2f}")
            c3.metric("Total P/L", f"Rs. {acc_pl:,.2f}", f"{acc_pl_pct:.2f}%")
            st.divider()
        
        # 5. Grand Total Card
        total_pl = grand_total_current - grand_total_invested
        total_pl_pct = (total_pl / grand_total_invested * 100) if grand_total_invested > 0 else 0
        
        st.markdown(f"## 💰 Grand Total Portfolio Summary")
        
        res_col1, res_col2, res_col3 = st.columns(3)
        
        with res_col1:
            st.markdown(f"<div style='background-color:{card_bg}; padding:20px; border-radius:10px; border-left: 5px solid gray;'> <p style='margin:0; opacity:0.7;'>Total Invested</p> <h2 style='margin:0;'>Rs. {grand_total_invested:,.2f}</h2> </div>", unsafe_allow_html=True)
        with res_col2:
            st.markdown(f"<div style='background-color:{card_bg}; padding:20px; border-radius:10px; border-left: 5px solid {accent_color};'> <p style='margin:0; opacity:0.7;'>Current Market Value</p> <h2 style='margin:0;'>Rs. {grand_total_current:,.2f}</h2> </div>", unsafe_allow_html=True)
        with res_col3:
            pl_color = accent_color if total_pl >= 0 else neg_color
            st.markdown(f"<div style='background-color:{card_bg}; padding:20px; border-radius:10px; border-left: 5px solid {pl_color};'> <p style='margin:0; opacity:0.7;'>Overall Profit/Loss</p> <h2 style='margin:0; color:{pl_color};'>Rs. {total_pl:,.2f} ({total_pl_pct:.2f}%)</h2> </div>", unsafe_allow_html=True)

    else:
        st.warning("No portfolio data found in the selected files.")

# Background Data Mechanism (Hidden from UI but available in code)
# Existing functions like analyze_with_ai_v2 and calculate_indicators remain in memory/persistence.py
# and indicators.py for future background processing or expansion.
