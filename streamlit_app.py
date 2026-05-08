import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from indicators import get_psx_data, calculate_indicators, get_live_price, calculate_pivots, get_company_info
from ai_engine import analyze_with_ai_v2, analyze_portfolio_tiered, ask_ai_question, get_qa_history
from persistence import load_cached_analysis, save_analysis
import datetime
import re
import os
import json
import concurrent.futures

# 1. THEME & GLOBAL UI STYLING
st.set_page_config(page_title="PSX-AI Portfolio Manager", layout="wide")

# Initialize Session State
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Portfolio"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'gh_token' not in st.session_state:
    st.session_state.gh_token = ""

# Sidebar - Login Section
st.sidebar.header("🔒 Privacy & Admin")
if not st.session_state.logged_in:
    pin = st.sidebar.text_input("Enter PIN to unlock", type="password", key="login_pin")
    if pin == "786":
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
    bg_color, text_color, card_bg, accent_color, neg_color = "#0e1117", "#E0E0E0", "#1e1e1e", "#26a69a", "#ef5350"
else:
    bg_color, text_color, card_bg, accent_color, neg_color = "#ffffff", "#121212", "#f9f9f9", "#00c853", "#ff5252"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp {{ background-color: {bg_color} !important; color: {text_color} !important; font-family: 'Inter', sans-serif; }}
    .stTable {{ background-color: {card_bg}; font-size: 0.85rem !important; }}
    .block-container {{ padding: 2rem 1rem !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.2rem !important; }}
    h1 {{ font-size: 1.8rem !important; }}
    h2 {{ font-size: 1.4rem !important; }}
    h3 {{ font-size: 1.1rem !important; }}
    </style>
    """, unsafe_allow_html=True)

# 2. HELPER FUNCTIONS
def get_pkt_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))

def update_github_file(file_path, content, token):
    import requests, base64
    repo = "tayyabtariqseo/Mypsx"
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = r.json().get('sha') if r.status_code == 200 else None
    payload = {"message": f"Update {file_path}", "content": base64.b64encode(content.encode()).decode()}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

def fetch_single_price(symbol):
    """Wrapper for parallel fetching."""
    try:
        clean_symbol = symbol.split('-')[0].strip()
        data = get_live_price(clean_symbol)
        return symbol, data
    except:
        return symbol, None

def get_persistent_prices():
    """Loads prices from a dedicated JSON cache for instant boot."""
    path = "analysis/last_prices.json"
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def save_persistent_prices(price_data):
    """Saves prices to a dedicated JSON cache."""
    path = "analysis/last_prices.json"
    os.makedirs("analysis", exist_ok=True)
    with open(path, 'w') as f:
        json.dump(price_data, f)

@st.cache_data(ttl=600)
def parse_portfolio_file_cached(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                symbol, qty, avg_p = parts[0].strip(), int(parts[1].replace(',', '')), float(parts[2].replace(',', ''))
                if symbol.lower() not in ["symbol", "qty", "avg", "total"]:
                    data.append({"Symbol": symbol, "Qty": qty, "Avg Price": avg_p})
            except: continue
    return data

# 3. MAIN PORTFOLIO LOGIC
if st.session_state.logged_in:
    tab_view, tab_edit, tab_ai = st.tabs(["📊 Portfolio View", "✍️ Portfolio Editor", "🤖 AI Strategy"])
else:
    tab_view = st.container()

with tab_view:
    st.header("📈 Dashboard")
    with st.sidebar:
        st.divider()
        st.info(f"📊 Last Sync: {get_pkt_time().strftime('%H:%M:%S')} PKT")

    portfolio_files = {"RAFI (RSL)": "RSL.txt", "MMK": "MMK.txt", "SPK": "SPK.txt", "SFEL": "SFEL.txt"}
    st.sidebar.header("📂 Accounts")
    selected_accounts = st.sidebar.multiselect("Select Accounts", options=list(portfolio_files.keys()), default=list(portfolio_files.keys()))

    if not selected_accounts:
        st.info("👈 Select accounts in sidebar.")
    else:
        # A. LOAD DATA
        all_rows = []
        for acc in selected_accounts:
            rows = parse_portfolio_file_cached(portfolio_files[acc])
            for r in rows:
                r['Account'] = acc
                all_rows.append(r)
        
        if all_rows:
            df = pd.DataFrame(all_rows)
            unique_symbols = df['Symbol'].unique()
            
            # B. FAST PRICE LOAD (Cache)
            price_map = get_persistent_prices()
            time_map = {s: "Stored" for s in unique_symbols}
            
            # C. PARALLEL LIVE FETCH
            with st.spinner("Fetching Live Prices..."):
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_price = {executor.submit(fetch_single_price, sym): sym for sym in unique_symbols}
                    for future in concurrent.futures.as_completed(future_to_price):
                        sym, data = future.result()
                        if data:
                            price_map[sym] = data['price']
                            time_map[sym] = data['timestamp'].strftime('%H:%M') if isinstance(data['timestamp'], datetime.datetime) else "Live"
            
            save_persistent_prices(price_map)
            
            # D. CALCULATE & DISPLAY
            df['CMP'] = df['Symbol'].map(price_map).fillna(0.0)
            df['CMP_Time'] = df['Symbol'].map(time_map)
            df['Invested'] = df['Qty'] * df['Avg Price']
            df['Current'] = df['Qty'] * df['CMP']
            df['P/L'] = df['Current'] - df['Invested']
            df['P/L%'] = df.apply(lambda x: (x['P/L'] / x['Invested'] * 100) if x['Invested'] > 0 else 0, axis=1)
            
            grand_total_invested = 0
            grand_total_current = 0
            
            for acc in selected_accounts:
                st.subheader(f"📁 {acc}")
                acc_df = df[df['Account'] == acc].copy()
                acc_invested, acc_current = acc_df['Invested'].sum(), acc_df['Current'].sum()
                acc_pl = acc_current - acc_invested
                acc_pl_pct = (acc_pl / acc_invested * 100) if acc_invested > 0 else 0
                grand_total_invested += acc_invested
                grand_total_current += acc_current
                
                acc_df['CMP (PKT)'] = acc_df.apply(lambda x: f"{x['CMP']:.2f} ({x['CMP_Time']})", axis=1)
                display_cols = ["Symbol", "Qty", "Avg Price", "Invested", "CMP (PKT)", "P/L", "P/L%"]
                acc_display = acc_df[display_cols].copy()
                
                if not st.session_state.logged_in:
                    for col in ["Qty", "Invested", "P/L"]: acc_display[col] = "***"
                
                def style_pl(val):
                    if val == "***": return ""
                    try:
                        v = float(str(val).replace('%','').replace(',',''))
                        return f'color: {accent_color if v >= 0 else neg_color}; font-weight: bold'
                    except: return ""

                format_dict = {"Avg Price": "{:.2f}", "Invested": "{:,.0f}", "P/L": "{:,.0f}", "P/L%": "{:.1f}%"}
                if not st.session_state.logged_in: 
                    del format_dict["Invested"], format_dict["P/L"]
                
                st.table(acc_display.style.format(format_dict).map(style_pl, subset=['P/L', 'P/L%'] if st.session_state.logged_in else ['P/L%']))
                
                mc1, mc2, mc3 = st.columns(3)
                if st.session_state.logged_in:
                    mc1.metric("Invest", f"{acc_invested:,.0f}")
                    mc2.metric("Value", f"{acc_current:,.0f}")
                    mc3.metric("P/L", f"{acc_pl:,.0f}", f"{acc_pl_pct:.1f}%")
                else:
                    mc1.metric("Invest", "***")
                    mc2.metric("Value", "***")
                    mc3.metric("P/L", "***", f"{acc_pl_pct:.1f}%")
                st.divider()
            
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
            st.warning("No portfolio data found.")

if st.session_state.logged_in:
    with tab_edit:
        st.header("✍️ Portfolio Editor")
        selected_file_label = st.selectbox("Select Account to Edit", options=list(portfolio_files.keys()))
        file_path = portfolio_files[selected_file_label]
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
        new_content = st.text_area(f"Data for {selected_file_label}", value=content, height=300)
        gh_token = st.text_input("GitHub Token (PAT)", value=st.session_state.gh_token, type="password")
        if st.button(f"Save & Sync {selected_file_label}"):
            st.session_state.gh_token = gh_token
            with open(file_path, 'w', encoding='utf-8') as f: f.write(new_content)
            if gh_token:
                if update_github_file(file_path, new_content, gh_token): st.success("✅ Synced to GitHub!")
                else: st.error("❌ Sync Failed.")
            else: st.success("✅ Saved locally.")
            st.cache_data.clear()

    with tab_ai:
        st.header("🤖 Tiered AI Strategy")
        now = get_pkt_time()
        c1, c2, c3 = st.columns(3)
        if c1.button("Daily"): st.session_state.ai_report_type = "Daily"
        if c2.button("Weekly" + (" (DUE)" if now.weekday()==5 and now.hour>=9 else "")): st.session_state.ai_report_type = "Weekly"
        if c3.button("Monthly" + (" (DUE)" if now.day==1 and now.hour>=1 else "")): st.session_state.ai_report_type = "Monthly"

        if 'ai_report_type' in st.session_state:
            with st.spinner("AI Analysis..."):
                all_rows = []
                for f in ["RSL.txt", "MMK.txt", "SPK.txt", "SFEL.txt"]: 
                    all_rows.extend(parse_portfolio_file_cached(f))
                if all_rows:
                    report = analyze_portfolio_tiered(st.session_state.ai_report_type, pd.DataFrame(all_rows).to_dict('records'))
                    st.markdown(report)
                else: st.warning("No data.")

        st.divider()
        st.subheader("❓ AI Deep Dive")
        user_query = st.text_input("Ask a question...")
        if st.button("Ask AI"):
            if user_query:
                all_rows = []
                for f in ["RSL.txt", "MMK.txt", "SPK.txt", "SFEL.txt"]: all_rows.extend(parse_portfolio_file_cached(f))
                with st.spinner("Thinking..."):
                    st.markdown(ask_ai_question(user_query, pd.DataFrame(all_rows).to_dict('records')))
        
        qa_history = get_qa_history()
        if qa_history:
            with st.expander("📜 History"):
                if st.button("Clear"):
                    if os.path.exists("analysis/qa_history.json"): os.remove("analysis/qa_history.json"); st.rerun()
                for item in reversed(qa_history):
                    st.markdown(f"**Q:** {item['question']}\n**A:** {item['answer']}")
                    st.divider()
