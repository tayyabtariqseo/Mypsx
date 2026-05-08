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
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Sidebar - Login Section
st.sidebar.header("🔒 Privacy & Admin")
if not st.session_state.logged_in:
    pin = st.sidebar.text_input("Enter PIN to unlock", type="password")
    if pin == "786": # User can change this PIN
        st.session_state.logged_in = True
        st.rerun()
else:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

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

# Apply Global CSS for Mobile Optimization
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {{ 
        background-color: {bg_color} !important; 
        color: {text_color} !important; 
    }}
    
    html, body, [class*="css"] {{ 
        font-family: 'Inter', sans-serif; 
    }}
    
    /* Optimize Tables for Mobile */
    .stTable {{ 
        background-color: {card_bg}; 
        font-size: 0.85rem !important; 
    }}
    
    /* Reduce padding for mobile density */
    .block-container {{
        padding-top: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}

    /* Compact Metrics */
    [data-testid="stMetricValue"] {{
        font-size: 1.2rem !important;
    }}
    
    h1 {{ font-size: 1.8rem !important; }}
    h2 {{ font-size: 1.4rem !important; }}
    h3 {{ font-size: 1.1rem !important; }}

    /* Hide Sidebar on very small screens if needed, or keep it compact */
    </style>
    """, unsafe_allow_html=True)

# 2. HELPER FUNCTIONS
def get_pkt_time():
    """Returns current time in Pakistan Time (PKT)."""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))

def update_github_file(file_path, content, token):
    # ... (rest of update_github_file logic)
    import requests
    import base64
    repo = "tayyabtariqseo/Mypsx"
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = r.json().get('sha') if r.status_code == 200 else None
    payload = {"message": f"Update {file_path} via Dashboard", "content": base64.b64encode(content.encode()).decode()}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

@st.cache_data(ttl=300) # Increased TTL for performance
def fetch_live_data(symbol):
    """Fetches live price for a symbol."""
    clean_symbol = symbol.split('-')[0].strip()
    return get_live_price(clean_symbol)

def get_cached_prices():
    """Retrieves prices from the latest analysis JSON files to speed up initial load."""
    import os, json
    prices = {}
    analysis_dir = "analysis"
    if os.path.exists(analysis_dir):
        files = sorted([f for f in os.listdir(analysis_dir) if f.endswith('.json')], reverse=True)
        if files:
            try:
                with open(os.path.join(analysis_dir, files[0]), 'r') as f:
                    data = json.load(f)
                    # This assumes analysis files store price, if not we fallback
                    if 'price' in data: prices[data.get('symbol', 'SYS')] = data['price']
            except: pass
    return prices

def parse_portfolio_file(file_path):
    # ... (existing parse_portfolio_file logic)
    import os
    if not os.path.exists(file_path): return None
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                symbol = parts[0].strip()
                qty = int(parts[1].replace(',', ''))
                avg_p = float(parts[2].replace(',', ''))
                if symbol.lower() not in ["symbol", "qty", "avg", "total"]:
                    data.append({"Symbol": symbol, "Qty": qty, "Avg Price": avg_p})
            except ValueError: continue
    return data

# 3. MAIN PORTFOLIO LOGIC
if st.session_state.logged_in:
    tab_view, tab_edit, tab_ai = st.tabs(["📊 Portfolio View", "✍️ Portfolio Editor", "🤖 AI Strategy"])
else:
    tab_view = st.container()

# Global DF for AI
portfolio_df_for_ai = None

with tab_view:
    st.header("📈 Dashboard")
    
    # Debug/Status Indicator in PKT
    with st.sidebar:
        st.divider()
        st.info(f"📊 Last Refresh: {get_pkt_time().strftime('%H:%M:%S')} PKT")

    portfolio_files = {"RAFI (RSL)": "RSL.txt", "MMK": "MMK.txt", "SPK": "SPK.txt", "SFEL": "SFEL.txt"}

    # Sidebar Account Selection
    st.sidebar.header("📂 Accounts")
    selected_accounts = st.sidebar.multiselect("Select Accounts", options=list(portfolio_files.keys()), default=list(portfolio_files.keys()))

    if not selected_accounts:
        st.info("👈 Select accounts in sidebar.")
    else:
        # 1. Aggregate Data
        all_rows = []
        for acc in selected_accounts:
            rows = parse_portfolio_file(portfolio_files[acc])
            if rows:
                for r in rows:
                    r['Account'] = acc
                    all_rows.append(r)
        
        if all_rows:
            df = pd.DataFrame(all_rows)
            
            # 2. Fast Cache Load + Live Fetch
            unique_symbols = df['Symbol'].unique()
            price_map = {}
            time_map = {}
            
            # Step A: Load from memory/cache first for instant UI
            cached = get_cached_prices()
            for sym in unique_symbols:
                price_map[sym] = cached.get(sym, 0.0)
                time_map[sym] = "Cached"

            # Step B: Fetch Live in background (Simulated by st.spinner + restricted refresh)
            with st.spinner("Updating Live Prices..."):
                for sym in unique_symbols:
                    live = fetch_live_data(sym)
                    if live and live['price'] > 0:
                        price_map[sym] = live['price']
                        time_map[sym] = live['timestamp'].astimezone(datetime.timezone(datetime.timedelta(hours=5))).strftime('%H:%M') if hasattr(live['timestamp'], 'astimezone') else "Live"
            
            # 3. Calculate Metrics
            df['CMP'] = df['Symbol'].map(price_map)
            df['CMP_Time'] = df['Symbol'].map(time_map)
            df['CMP'] = pd.to_numeric(df['CMP'], errors='coerce').fillna(0.0)
            df['Invested'] = df['Qty'] * df['Avg Price']
            df['Current'] = df['Qty'] * df['CMP']
            df['P/L'] = df['Current'] - df['Invested']
            df['P/L%'] = df.apply(lambda x: (x['P/L'] / x['Invested'] * 100) if x['Invested'] > 0 else 0, axis=1)
            
            # 4. Display per Account
            grand_total_invested = 0
            grand_total_current = 0
            
            for acc in selected_accounts:
                st.subheader(f"📁 {acc}")
                acc_df = df[df['Account'] == acc].copy()
                
                acc_invested = acc_df['Invested'].sum()
                acc_current = acc_df['Current'].sum()
                acc_pl = acc_current - acc_invested
                acc_pl_pct = (acc_pl / acc_invested * 100) if acc_invested > 0 else 0
                
                grand_total_invested += acc_invested
                grand_total_current += acc_current
                
                # Combine CMP and Time for cleaner view
                acc_df['CMP (PKT)'] = acc_df.apply(lambda x: f"{x['CMP']:.2f} ({x['CMP_Time']})", axis=1)
                
                display_cols = ["Symbol", "Qty", "Avg Price", "Invested", "CMP (PKT)", "P/L", "P/L%"]
                acc_display = acc_df[display_cols].copy()
                
                # Privacy Masking (Qty, Invested, P/L use *** | P/L% remains visible)
                if not st.session_state.logged_in:
                    for col in ["Qty", "Invested", "P/L"]:
                        acc_display[col] = "***"
                
                def style_pl(val):
                    if val == "***": return ""
                    try:
                        v = float(str(val).replace('%','').replace(',',''))
                        color = accent_color if v >= 0 else neg_color
                        return f'color: {color}; font-weight: bold'
                    except: return ""

                if st.session_state.logged_in:
                    st.table(acc_display.style.format({
                        "Avg Price": "{:.2f}",
                        "Invested": "{:,.0f}",
                        "P/L": "{:,.0f}",
                        "P/L%": "{:.1f}%"
                    }).map(style_pl, subset=['P/L', 'P/L%']))
                    
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Invest", f"{acc_invested:,.0f}")
                    mc2.metric("Value", f"{acc_current:,.0f}")
                    mc3.metric("P/L", f"{acc_pl:,.0f}", f"{acc_pl_pct:.1f}%")
                else:
                    # Masked View - P/L% remains visible and styled
                    st.table(acc_display.style.format({
                        "Avg Price": "{:.2f}",
                        "P/L%": "{:.1f}%"
                    }).map(style_pl, subset=['P/L%']))
                    
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Invest", "***")
                    mc2.metric("Value", "***")
                    mc3.metric("P/L", "***", f"{acc_pl_pct:.1f}%")
                st.divider()
            
            # 5. Grand Summary
            total_pl = grand_total_current - grand_total_invested
            total_pl_pct = (total_pl / grand_total_invested * 100) if grand_total_invested > 0 else 0
            
            st.markdown(f"### 💰 Total Summary")
            sc1, sc2, sc3 = st.columns(3)
            if st.session_state.logged_in:
                sc1.metric("Total Invest", f"{grand_total_invested:,.0f}")
                sc2.metric("Total Value", f"{grand_total_current:,.0f}")
                sc3.metric("Total P/L", f"{total_pl:,.0f}", f"{total_pl_pct:.1f}%")
            else:
                sc1.metric("Total Invest", "***")
                sc2.metric("Total Value", "***")
                sc3.metric("Total P/L", "***", f"{total_pl_pct:.1f}%")

        else:
            st.warning("No portfolio data found in the selected files.")

if st.session_state.logged_in:
    with tab_edit:
        st.header("✍️ Portfolio Editor")
        st.info("Edit your holdings here. Format: SYMBOL QTY PRICE (One per line)")
        
        selected_file_label = st.selectbox("Select Account to Edit", options=list(portfolio_files.keys()))
        file_path = portfolio_files[selected_file_label]
        
        import os
        current_content = ""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
        
        new_content = st.text_area(f"Data for {selected_file_label}", value=current_content, height=300)
        
        st.divider()
        st.subheader("🚀 Cloud Sync (GitHub)")
        gh_token = st.text_input("Enter GitHub Personal Access Token (PAT) for Auto-Sync", type="password", help="Required to save changes permanently to GitHub.")
        
        if st.button(f"Save & Sync {selected_file_label}"):
            # ... (existing save logic)
            st.rerun()

if st.session_state.logged_in:
    with tab_ai:
        st.header("🤖 Tiered AI Strategy")
        st.markdown("### Loss Recovery Engine (Strength-Based)")
        
        # Determine which report is due
        now = get_pkt_time()
        is_saturday = (now.weekday() == 5 and now.hour >= 9)
        is_first_of_month = (now.day == 1 and now.hour >= 1)
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            if st.button("Run Daily Analysis", help="Executes daily portfolio review"):
                st.session_state.ai_report_type = "Daily"
        with col_r2:
            btn_label = "Run Weekly Analysis" + (" (DUE)" if is_saturday else "")
            if st.button(btn_label, help="Aggregates past 7 days of daily summaries"):
                st.session_state.ai_report_type = "Weekly"
        with col_r3:
            btn_label = "Run Monthly Analysis" + (" (DUE)" if is_first_of_month else "")
            if st.button(btn_label, help="Aggregates past 4 weeks of weekly summaries"):
                st.session_state.ai_report_type = "Monthly"

        if 'ai_report_type' in st.session_state:
            with st.spinner(f"Generating {st.session_state.ai_report_type} AI Strategy..."):
                # Use data from the session (if it was loaded in Portfolio tab)
                # Note: We access the 'df' from tab_view indirectly by ensuring it's available
                # In Streamlit, local variables like 'df' inside 'with tab_view' aren't always global
                # but since we are in the same script, we'll re-fetch if needed.
                
                # Fetching again to be safe and clean
                all_rows = []
                # ... (Logic to rebuild ai_payload)
                for acc, file in {"RSL": "RSL.txt", "MMK": "MMK.txt", "SPK": "SPK.txt", "SFEL": "SFEL.txt"}.items():
                    rows = parse_portfolio_file(file)
                    if rows: [all_rows.append(r) for r in rows]
                
                if all_rows:
                    ai_payload = pd.DataFrame(all_rows).to_dict('records')
                    report = analyze_portfolio_tiered(st.session_state.ai_report_type, ai_payload)
                    st.divider()
                    st.markdown(report)
                else:
                    st.warning("No portfolio data found to analyze.")

# Background Data Mechanism (Hidden from UI but available in code)
# Existing functions like analyze_with_ai_v2 and calculate_indicators remain in memory/persistence.py
# and indicators.py for future background processing or expansion.
