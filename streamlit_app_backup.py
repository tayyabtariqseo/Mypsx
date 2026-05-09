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

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'gh_token' not in st.session_state: st.session_state.gh_token = ""
if 'ai_report' not in st.session_state: st.session_state.ai_report = ""

st.sidebar.header("🔒 Privacy & Admin")
if not st.session_state.logged_in:
    pin = st.sidebar.text_input("Enter PIN", type="password")
    if pin == "786":
        st.session_state.logged_in = True
        st.rerun()
else:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

st.sidebar.header("🎨 Theme Settings")
theme_choice = st.sidebar.radio("Mode", options=["Dark", "Light"], index=0)
if theme_choice == "Dark":
    bg, txt, card, acc, neg = "#0e1117", "#E0E0E0", "#1e1e1e", "#26a69a", "#ef5350"
else:
    bg, txt, card, acc, neg = "#ffffff", "#121212", "#f9f9f9", "#00c853", "#ff5252"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg} !important; color: {txt} !important; }}
    .stTable {{ background-color: {card}; font-size: 0.85rem !important; }}
    .block-container {{ padding: 2rem 1rem !important; }}
    </style>
    """, unsafe_allow_html=True)

# 2. HELPERS
def get_pkt_time(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))

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
    try: return symbol, get_live_price(symbol.split('-')[0].strip())
    except: return symbol, None

def get_persistent_prices():
    try:
        with open("analysis/last_prices.json", 'r') as f: return json.load(f)
    except: return {}

def save_persistent_prices(data):
    os.makedirs("analysis", exist_ok=True)
    with open("analysis/last_prices.json", 'w') as f: json.dump(data, f)

@st.cache_data(ttl=600)
def parse_portfolio_file_cached(file_path):
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

# 3. MAIN
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
    selected_accounts = st.sidebar.multiselect("Accounts", options=list(portfolio_files.keys()), default=list(portfolio_files.keys()))
    
    if not selected_accounts:
        st.info("Select accounts.")
    else:
        all_rows = []
        for acc in selected_accounts:
            rows = parse_portfolio_file_cached(portfolio_files[acc])
            for r in rows: r['Account'] = acc; all_rows.append(r)
        
        if all_rows:
            df = pd.DataFrame(all_rows)
            unique_symbols = df['Symbol'].unique()
            price_map = get_persistent_prices()
            time_map = {s: "Stored" for s in unique_symbols}
            
            with st.spinner("Prices..."):
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
                    futures = {ex.submit(fetch_single_price, s): s for s in unique_symbols}
                    for f in concurrent.futures.as_completed(futures):
                        s, data = f.result()
                        if data:
                            price_map[s] = data['price']
                            time_map[s] = data['timestamp'].strftime('%H:%M') if isinstance(data['timestamp'], datetime.datetime) else "Live"
            save_persistent_prices(price_map)
            
            df['CMP'] = df['Symbol'].map(price_map).fillna(0.0)
            df['CMP_Time'] = df['Symbol'].map(time_map)
            df['Invested'] = df['Qty'] * df['Avg Price']
            df['Current'] = df['Qty'] * df['CMP']
            df['P/L'] = df['Current'] - df['Invested']
            df['P/L%'] = df.apply(lambda x: (x['P/L'] / x['Invested'] * 100) if x['Invested'] > 0 else 0, axis=1)
            
            grand_total_invested = grand_total_current = 0
            for acc in selected_accounts:
                st.subheader(f"📁 {acc}")
                acc_df = df[df['Account'] == acc].copy()
                i, c = acc_df['Invested'].sum(), acc_df['Current'].sum()
                grand_total_invested += i; grand_total_current += c
                
                acc_df['CMP (PKT)'] = acc_df.apply(lambda x: f"{x['CMP']:.2f} ({x['CMP_Time']})", axis=1)
                cols = ["Symbol", "Qty", "Avg Price", "Invested", "CMP (PKT)", "P/L", "P/L%"]
                disp = acc_df[cols].copy()
                if not st.session_state.logged_in:
                    for col in ["Qty", "Invested", "P/L"]: disp[col] = "***"
                
                def s_pl(v):
                    if v == "***": return ""
                    try: return f'color: {acc if float(str(v).replace("%","").replace(",","")) >= 0 else neg}; font-weight: bold'
                    except: return ""

                fmt = {"Avg Price": "{:.2f}", "Invested": "{:,.0f}", "P/L": "{:,.0f}", "P/L%": "{:.1f}%"}
                if not st.session_state.logged_in: del fmt["Invested"], fmt["P/L"]
                
                st.table(disp.style.format(fmt).map(s_pl, subset=['P/L', 'P/L%'] if st.session_state.logged_in else ['P/L%']))
                
                m1, m2, m3 = st.columns(3)
                if st.session_state.logged_in:
                    m1.metric("Invest", f"{i:,.0f}")
                    m2.metric("Value", f"{c:,.0f}")
                    m3.metric("P/L", f"{c-i:,.0f}", f"{(c-i)/i*100 if i>0 else 0:.1f}%")
                else:
                    m1.metric("Invest", "***")
                    m2.metric("Value", "***")
                    m3.metric("P/L", "***", f"{(c-i)/i*100 if i>0 else 0:.1f}%")
            
            st.markdown("### 💰 Summary")
            ti, tc = grand_total_invested, grand_total_current
            s1, s2, s3 = st.columns(3)
            if st.session_state.logged_in:
                s1.metric("Total Invest", f"{ti:,.0f}")
                s2.metric("Total Value", f"{tc:,.0f}")
                s3.metric("Total P/L", f"{tc-ti:,.0f}", f"{(tc-ti)/ti*100 if ti>0 else 0:.1f}%")
            else:
                s1.metric("Total Invest", "***")
                s2.metric("Total Value", "***")
                s3.metric("Total P/L", "***", f"{(tc-ti)/ti*100 if ti>0 else 0:.1f}%")
        else: st.warning("No data.")

if st.session_state.logged_in:
    with tab_edit:
        st.header("✍️ Portfolio Editor")
        acc_label = st.selectbox("Account to Edit", options=list(portfolio_files.keys()))
        f_path = portfolio_files[acc_label]
        
        # Force reload from disk to prevent stale data
        with open(f_path, 'r', encoding='utf-8') as f: 
            raw_content = f.read()
        
        # Use a dynamic key based on account to force UI refresh
        edit_content = st.text_area(f"Data for {acc_label}", value=raw_content, height=300, key=f"editor_{acc_label}")
        
        token = st.text_input("GitHub Token", value=st.session_state.gh_token, type="password")
        if st.button(f"Save & Sync {acc_label}"):
            st.session_state.gh_token = token
            with open(f_path, 'w', encoding='utf-8') as f: f.write(edit_content)
            
            # CLEAR CACHE to ensure View tab updates
            st.cache_data.clear()
            
            if token:
                if update_github_file(f_path, edit_content, token):
                    st.success(f"✅ Saved & Synced {acc_label} to GitHub!")
                else:
                    st.error("❌ GitHub Sync Failed. Saved locally only.")
            else:
                st.success(f"✅ Saved locally to {acc_label}!")
            
            st.info("Refresh page to see updates in Portfolio View.")

    with tab_ai:
        st.header("🤖 AI Strategy")
        now = get_pkt_time()
        c1, c2, c3 = st.columns(3)
        if c1.button("Daily"): 
            st.session_state.ai_report = analyze_portfolio_tiered("Daily", df.to_dict('records'))
        if c2.button("Weekly"):
            st.session_state.ai_report = analyze_portfolio_tiered("Weekly", df.to_dict('records'))
        if c3.button("Monthly"):
            st.session_state.ai_report = analyze_portfolio_tiered("Monthly", df.to_dict('records'))
        
        if st.session_state.ai_report:
            st.markdown(st.session_state.ai_report)

        st.divider()
        st.subheader("❓ AI Deep Dive")
        query = st.text_input("Ask question...")
        if st.button("Ask AI"):
            if query:
                with st.spinner("Thinking..."):
                    st.markdown(ask_ai_question(query, df.to_dict('records')))
        
        history = get_qa_history()
        if history:
            with st.expander("📜 History"):
                for item in reversed(history):
                    st.markdown(f"**Q:** {item['question']}\n**A:** {item['answer']}")
                    st.divider()
