import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from indicators import get_live_price, get_psx_data, calculate_indicators, get_company_info
from ai_engine import analyze_portfolio_tiered, ask_ai_question, get_qa_history
from persistence import get_baseline, save_baseline, get_pkt_time
import datetime
import os
import json
import concurrent.futures

# 1. THEME & GLOBAL UI STYLING
st.set_page_config(page_title="PSX Portfolio Recovery Engine", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'gh_token' not in st.session_state: st.session_state.gh_token = ""
if 'ai_report' not in st.session_state: st.session_state.ai_report = ""

# Sidebar - Admin
st.sidebar.title("🛡️ Portfolio Recovery")
if not st.session_state.logged_in:
    pin = st.sidebar.text_input("Enter PIN", type="password")
    if pin == "786":
        st.session_state.logged_in = True
        st.rerun()
else:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

st.sidebar.header("📍 Navigation")
page = st.sidebar.radio("Go to", ["Recovery Dashboard", "Growth Tracker", "Portfolio Editor", "AI Recovery Strategy"])

theme_choice = st.sidebar.radio("Appearance", options=["Dark", "Light"], index=0)
if theme_choice == "Dark":
    bg, txt, card, acc, neg = "#0e1117", "#E0E0E0", "#1e1e1e", "#26a69a", "#ef5350"
else:
    bg, txt, card, acc, neg = "#ffffff", "#121212", "#f9f9f9", "#00c853", "#ff5252"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg} !important; color: {txt} !important; }}
    .stTable {{ background-color: {card}; font-size: 0.85rem !important; }}
    .stMetric {{ background-color: {card}; padding: 15px; border-radius: 10px; border: 1px solid rgba(128,128,128,0.1); }}
    </style>
    """, unsafe_allow_html=True)

# 2. HELPERS
def is_market_open():
    now_pkt = get_pkt_time()
    weekday = now_pkt.weekday()
    time_pkt = now_pkt.time()
    if weekday >= 5: return False
    if weekday == 4: return datetime.time(9, 0) <= time_pkt <= datetime.time(16, 30)
    else: return datetime.time(9, 15) <= time_pkt <= datetime.time(15, 30)

def get_persistent_prices():
    try:
        with open("analysis/last_prices.json", 'r') as f: return json.load(f)
    except: return {}

def save_persistent_prices(data):
    os.makedirs("analysis", exist_ok=True)
    with open("analysis/last_prices.json", 'w') as f: json.dump(data, f)

def fetch_price_logic(symbol, mkt_open, stored_prices):
    if mkt_open:
        res = get_live_price(symbol.split('-')[0].strip())
        if res: return symbol, res
    if symbol in stored_prices:
        return symbol, {"price": stored_prices[symbol], "timestamp": "Offline", "source": "cache"}
    return symbol, None

@st.cache_data(ttl=600)
def parse_portfolio_file(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    data = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                symbol, qty, avg_p = parts[0].strip(), int(parts[1].replace(',', '')), float(parts[2].replace(',', ''))
                if symbol.lower() not in ["symbol", "qty", "avg", "total"]: data.append({"Symbol": symbol, "Qty": qty, "Avg Price": avg_p})
            except: continue
    return data

# 3. PAGE LOGIC
portfolio_files = {"RAFI (RSL)": "RSL.txt", "MMK": "MMK.txt", "SPK": "SPK.txt", "SFEL": "SFEL.txt"}

if page == "Recovery Dashboard":
    st.header("📈 Portfolio Recovery Dashboard")
    mkt_open = is_market_open()
    st.sidebar.info(f"Market: {'🟢 OPEN' if mkt_open else '🔴 CLOSED'}\n\nPKT: {get_pkt_time().strftime('%H:%M')}")
    
    selected_accounts = st.sidebar.multiselect("Accounts", options=list(portfolio_files.keys()), default=list(portfolio_files.keys()))
    
    if not selected_accounts:
        st.info("Select accounts to monitor recovery.")
    else:
        all_rows = []
        for acc in selected_accounts:
            rows = parse_portfolio_file(portfolio_files[acc])
            for r in rows: r['Account'] = acc; all_rows.append(r)
        
        if all_rows:
            df_port = pd.DataFrame(all_rows)
            unique_symbols = df_port['Symbol'].unique()
            stored_prices = get_persistent_prices()
            price_map = {}
            
            with st.spinner("Updating Market Data..."):
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
                    futures = {ex.submit(fetch_price_logic, s, mkt_open, stored_prices): s for s in unique_symbols}
                    for f in concurrent.futures.as_completed(futures):
                        s, res = f.result()
                        if res: price_map[s] = res['price']
            
            if mkt_open: save_persistent_prices(price_map)
            
            df_port['CMP'] = df_port['Symbol'].map(price_map).fillna(0.0)
            df_port['Invested'] = df_port['Qty'] * df_port['Avg Price']
            df_port['Current'] = df_port['Qty'] * df_port['CMP']
            df_port['P/L'] = df_port['Current'] - df_port['Invested']
            df_port['P/L%'] = df_port.apply(lambda x: (x['P/L'] / x['Invested'] * 100) if x['Invested'] > 0 else 0, axis=1)
            
            grand_total_invested = grand_total_current = 0
            for acc in selected_accounts:
                acc_df = df_port[df_port['Account'] == acc].copy()
                i, c = acc_df['Invested'].sum(), acc_df['Current'].sum()
                grand_total_invested += i; grand_total_current += c
                
                status = "🟢 PROFIT" if (c - i) >= 0 else "🔴 RECOVERY"
                st.subheader(f"📁 {acc} - {status}")
                
                cols = ["Symbol", "Qty", "Avg Price", "Invested", "CMP", "P/L", "P/L%"]
                disp = acc_df[cols].copy()
                if not st.session_state.logged_in:
                    for col in ["Qty", "Invested", "P/L"]: disp[col] = "***"
                
                def s_pl(v):
                    if v == "***": return ""
                    try: return f'color: {acc if float(str(v).replace("%","").replace(",","")) >= 0 else neg}; font-weight: bold'
                    except: return ""

                fmt = {"Avg Price": "{:.2f}", "Invested": "{:,.0f}", "CMP": "{:.2f}", "P/L": "{:,.0f}", "P/L%": "{:.1f}%"}
                if not st.session_state.logged_in: del fmt["Invested"], fmt["P/L"]
                
                st.table(disp.style.format(fmt).map(s_pl, subset=['P/L', 'P/L%'] if st.session_state.logged_in else ['P/L%']))
            
            st.divider()
            st.markdown("### 💰 Consolidated Strategy View")
            ti, tc = grand_total_invested, grand_total_current
            s1, s2, s3 = st.columns(3)
            if st.session_state.logged_in:
                s1.metric("Total Invested", f"{ti:,.0f}")
                s2.metric("Market Value", f"{tc:,.0f}")
                s3.metric("Unrealized P/L", f"{tc-ti:,.0f}", f"{(tc-ti)/ti*100 if ti>0 else 0:.1f}%")
            else:
                s3.metric("Total Portfolio P/L%", f"{(tc-ti)/ti*100 if ti>0 else 0:.1f}%")

elif page == "Growth Tracker":
    st.header("📈 Growth Tracker (Post Day 0)")
    baseline = get_baseline()
    
    # Implementation of Growth Tracking vs Day 0
    st.info("Tracking growth from May 9, 2026 (Day 0). Each account shows growth relative to the baseline value.")
    
    all_data = []
    for acc, f in portfolio_files.items():
        rows = parse_portfolio_file(f)
        for r in rows: r['Account'] = acc; all_data.append(r)
    
    if all_data:
        df_all = pd.DataFrame(all_data)
        prices = get_persistent_prices()
        df_all['CMP'] = df_all['Symbol'].map(prices).fillna(0.0)
        df_all['Current'] = df_all['Qty'] * df_all['CMP']
        
        acc_growth = df_all.groupby('Account')['Current'].sum().to_dict()
        
        if st.sidebar.button("Set Day 0 Baseline"):
            save_baseline(acc_growth)
            st.rerun()
        
        if not baseline:
            st.warning("No Baseline set. Click 'Set Day 0 Baseline' to start tracking.")
        else:
            rows = []
            for acc in portfolio_files.keys():
                b_val = baseline.get(acc, 0)
                c_val = acc_growth.get(acc, 0)
                diff = c_val - b_val
                perc = (diff / b_val * 100) if b_val > 0 else 0
                rows.append({"Account": acc, "Baseline (Day 0)": b_val, "Current Value": c_val, "Growth (%)": perc})
            
            df_growth = pd.DataFrame(rows)
            st.table(df_growth.style.format({"Baseline (Day 0)": "{:,.0f}", "Current Value": "{:,.0f}", "Growth (%)": "{:+.2f}%"}))
            
            # Summary Metric
            total_b = sum(baseline.values())
            total_c = sum(acc_growth.values())
            total_perc = ((total_c - total_b) / total_b * 100) if total_b > 0 else 0
            st.metric("Consolidated Growth Since Day 0", f"{total_c:,.0f}", f"{total_perc:+.2f}%")

elif page == "Portfolio Editor":
    st.header("✍️ Editor")
    if not st.session_state.logged_in:
        st.warning("Login required.")
    else:
        acc_label = st.selectbox("Account", options=list(portfolio_files.keys()))
        f_path = portfolio_files[acc_label]
        with open(f_path, 'r', encoding='utf-8') as f: raw = f.read()
        edit_content = st.text_area("Raw Data", value=raw, height=300)
        if st.button("Save locally"):
            with open(f_path, 'w', encoding='utf-8') as f: f.write(edit_content)
            st.cache_data.clear()
            st.success("Saved.")

elif page == "AI Recovery Strategy":
    st.header("🤖 AI Portfolio Strategy")
    if not st.session_state.logged_in:
        st.warning("Login required.")
    else:
        all_data = []
        for f in portfolio_files.values(): all_data.extend(parse_portfolio_file(f))
        
        c1, c2 = st.columns(2)
        if c1.button("Analyze Portfolio"): 
            st.session_state.ai_report = analyze_portfolio_tiered("Daily", all_data)
        if c2.button("Weekly Recovery Plan"):
            st.session_state.ai_report = analyze_portfolio_tiered("Weekly", all_data)
        
        if st.session_state.ai_report:
            st.markdown(st.session_state.ai_report)

        st.divider()
        q = st.text_input("Ask about Recovery/Growth...")
        if st.button("Ask AI"):
            if q:
                with st.spinner("Thinking..."):
                    st.markdown(ask_ai_question(q, all_data))
        
        hist = get_qa_history()
        if hist:
            with st.expander("📜 History"):
                for item in reversed(hist):
                    st.markdown(f"**Q:** {item['question']}\n**A:** {item['answer']}")
                    st.divider()
