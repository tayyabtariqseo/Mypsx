import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from indicators import get_live_price, get_psx_data, calculate_indicators, get_company_info
from ai_engine import analyze_portfolio_tiered, ask_ai_question, get_qa_history, save_qa_history
from persistence import get_baseline, save_baseline, get_pkt_time, load_limits, get_cached_report
import datetime
import os
import json
import time
import concurrent.futures

# 1. THEME & GLOBAL UI STYLING
st.set_page_config(page_title="Portfolio Management System", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'ai_report' not in st.session_state: st.session_state.ai_report = ""
if 'report_task' not in st.session_state: st.session_state.report_task = None
if 'price_cache' not in st.session_state: st.session_state.price_cache = {}

# Sidebar - Administration
st.sidebar.title("Management Console")
if not st.session_state.logged_in:
    pin = st.sidebar.text_input("PIN", type="password")
    if pin == "786":
        st.session_state.logged_in = True
        st.rerun()
else:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

st.sidebar.header("Navigation")
page = st.sidebar.radio("View", ["Recovery Dashboard", "Growth Tracker", "Portfolio Editor", "AI Strategy"])

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
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
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

def sync_all_prices(symbols, force=False):
    """Optimized sync using session_state to avoid duplicate API hits."""
    if not force and st.session_state.price_cache:
        # Check if all symbols are in cache
        if all(s in st.session_state.price_cache for s in symbols):
            return st.session_state.price_cache

    mkt_open = is_market_open()
    stored_prices = get_persistent_prices()
    price_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_price_logic, s, mkt_open, stored_prices): s for s in symbols}
        for f in concurrent.futures.as_completed(futures):
            s, res = f.result()
            if res: price_map[s] = res['price']
    
    if mkt_open: save_persistent_prices(price_map)
    st.session_state.price_cache = price_map
    return price_map

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
    st.header("Portfolio Recovery Dashboard")
    mkt_open = is_market_open()
    st.sidebar.info(f"Market Status: {'OPEN' if mkt_open else 'CLOSED'}\nPKT: {get_pkt_time().strftime('%H:%M')}")
    
    if st.sidebar.button("Refresh Live Prices"):
        st.session_state.price_cache = {}
        st.rerun()

    selected_accounts = st.sidebar.multiselect("Select Accounts", options=list(portfolio_files.keys()), default=list(portfolio_files.keys()))
    
    if not selected_accounts:
        st.info("Select accounts in the sidebar.")
    else:
        all_rows = []
        for acc in selected_accounts:
            rows = parse_portfolio_file(portfolio_files[acc])
            for r in rows: r['Account'] = acc; all_rows.append(r)
        
        if all_rows:
            df_port = pd.DataFrame(all_rows)
            unique_symbols = df_port['Symbol'].unique()
            price_map = sync_all_prices(unique_symbols)
            
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
                
                status = "PROFIT" if (c - i) >= 0 else "RECOVERY"
                st.subheader(f"Account: {acc} ({status})")
                
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
                
                t1, t2, t3 = st.columns(3)
                if st.session_state.logged_in:
                    t1.metric("Acc Invested (PKR)", f"{i:,.0f}")
                    t2.metric("Acc Value (PKR)", f"{c:,.0f}")
                    t3.metric("Acc P/L (PKR)", f"{c-i:,.0f}", f"{(c-i)/i*100 if i>0 else 0:.1f}%")
                else:
                    t3.metric("Acc P/L%", f"{(c-i)/i*100 if i>0 else 0:.1f}%")
            
            st.divider()
            st.markdown("### Consolidated Portfolio Summary")
            ti, tc = grand_total_invested, grand_total_current
            s1, s2, s3 = st.columns(3)
            if st.session_state.logged_in:
                s1.metric("Grand Total Invested (PKR)", f"{ti:,.0f}")
                s2.metric("Grand Market Value (PKR)", f"{tc:,.0f}")
                s3.metric("Grand Portfolio P/L (PKR)", f"{tc-ti:,.0f}", f"{(tc-ti)/ti*100 if ti>0 else 0:.1f}%")
            else:
                s3.metric("Total Portfolio P/L%", f"{(tc-ti)/ti*100 if ti>0 else 0:.1f}%")

elif page == "Growth Tracker":
    st.header("Growth Tracker (Post Day 0)")
    baseline = get_baseline()
    st.info("Tracking growth from May 9, 2026 (Day 0).")
    
    all_data_flat = []
    all_syms = set()
    for acc, f in portfolio_files.items():
        rows = parse_portfolio_file(f)
        for r in rows: 
            r['Account'] = acc; all_data_flat.append(r)
            all_syms.add(r['Symbol'])
    
    if all_data_flat:
        df_all = pd.DataFrame(all_data_flat)
        price_map = sync_all_prices(list(all_syms))
        df_all['CMP'] = df_all['Symbol'].map(price_map).fillna(0.0)
        df_all['Current'] = df_all['Qty'] * df_all['CMP']
        
        acc_growth = df_all.groupby('Account')['Current'].sum().to_dict()
        
        if st.session_state.logged_in:
            if st.sidebar.button("Set Day 0 Baseline"):
                save_baseline(acc_growth)
                st.rerun()
        
        if not baseline:
            st.warning("No Baseline set. Administrator must login to set Day 0 Baseline.")
        else:
            rows = []
            for acc in portfolio_files.keys():
                b_val = baseline.get(acc, 0)
                c_val = acc_growth.get(acc, 0)
                diff = c_val - b_val
                perc = (diff / b_val * 100) if b_val > 0 else 0
                if st.session_state.logged_in:
                    rows.append({"Account": acc, "Baseline (PKR)": b_val, "Current Value (PKR)": c_val, "Growth (%)": perc})
                else:
                    rows.append({"Account": acc, "Baseline": "***", "Current": "***", "Growth (%)": perc})

            df_growth = pd.DataFrame(rows)
            fmt_g = {"Growth (%)": "{:+.2f}%"}
            if st.session_state.logged_in: fmt_g.update({"Baseline (PKR)": "{:,.0f}", "Current Value (PKR)": "{:,.0f}"})
            st.table(df_growth.style.format(fmt_g))
            
            total_b = sum(baseline.values())
            total_c = sum(acc_growth.values())
            total_perc = ((total_c - total_b) / total_b * 100) if total_b > 0 else 0
            
            st.divider()
            if st.session_state.logged_in: st.metric("Consolidated Portfolio Growth (PKR)", f"{total_c:,.0f}", f"{total_perc:+.2f}%")
            else: st.metric("Consolidated Portfolio Growth (%)", f"{total_perc:+.2f}%")

elif page == "Portfolio Editor":
    st.header("Portfolio Editor")
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
            st.success("Saved locally.")

elif page == "AI Strategy":
    st.header("Institutional AI Strategy")
    if not st.session_state.logged_in:
        st.warning("Login required.")
    else:
        limits = load_limits()
        max_wait = 0
        for m, t in limits.items():
            if time.time() < t: max_wait = max(max_wait, int(t - time.time()))
        
        if max_wait > 0:
            st.warning(f"AI Cooldown: Retrying in {max_wait} seconds. All models currently reporting quota exhaustion.")
            time.sleep(1)
            st.rerun()

        # Gather grouped data for AI (using the FRESH price_cache from Dashboard)
        price_map = st.session_state.get('price_cache', get_persistent_prices())
        grouped_portfolio = {}
        for label, file in portfolio_files.items():
            rows = parse_portfolio_file(file)
            for r in rows: r['CMP'] = price_map.get(r['Symbol'], 0)
            grouped_portfolio[label] = rows

        c1, c2 = st.columns(2)
        if c1.button("Daily Recovery Report"): 
            st.session_state.report_task = "Daily"
            st.session_state.ai_report = ""
        if c2.button("Weekly Recovery Plan"): 
            st.session_state.report_task = "Weekly"
            st.session_state.ai_report = ""

        if st.session_state.report_task:
            task = st.session_state.report_task
            cached = get_cached_report(task)
            if cached:
                st.session_state.ai_report = f"**System Note:** Displaying cached analysis (Updated within last hour).\n\n{cached}"
                st.session_state.report_task = None
            else:
                with st.spinner(f"Generating {task} Institutional Analysis..."):
                    res = analyze_portfolio_tiered(task, grouped_portfolio)
                    if res.startswith("RATE_LIMIT"):
                        st.error(f"Quota exceeded. System is blacklisting exhausted models. Retrying in background...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.ai_report = res
                        st.session_state.report_task = None
        
        if st.session_state.ai_report:
            st.markdown(st.session_state.ai_report)

        st.divider()
        q = st.text_input("Institutional Inquiry (Account Recovery focus)")
        if st.button("Query AI"):
            if q:
                with st.spinner("Senior Analyst Analysis..."):
                    res = ask_ai_question(q, grouped_portfolio)
                    if res.startswith("RATE_LIMIT"):
                        st.error("Quota exceeded. Initiating cooldown...")
                        time.sleep(1)
                        st.rerun()
                    else: 
                        st.markdown(res)
                        model_name = res.split('`')[1] if '`' in res else 'Unknown'
                        save_qa_history(q, res.split('\n\n')[1] if '\n\n' in res else res, model_name)
        
        hist = get_qa_history()
        if hist:
            with st.expander("Strategic Inquiry History"):
                for item in reversed(hist):
                    st.markdown(f"**Q:** {item['question']}\n**A:** {item['answer']}")
                    st.divider()
