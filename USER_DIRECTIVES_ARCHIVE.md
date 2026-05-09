# PSX Portfolio Recovery Engine - User Directives Archive

## 1. Core Architectural Requirements
- **Strategy Lifecycle:** Focus exclusively on "Loss Recovery" until each account is in net profit. Once profitable, shift focus to "Systematic Growth."
- **Account Separation:** Treat each of the 4 accounts (RSL, MMK, SPK, SFEL) as separate institutional portfolios. Analysis and recovery strategies must be tailored per account.
- **Day 0 Baseline:** Established May 9, 2026, as the starting point (Day 0). Day 1+ must show growth/loss as a percentage (e.g., +5.6%).
- **Market Compliance:** Adhere strictly to PSX timings (Mon-Thu 9:15-3:30, Fri 9:00-4:30 PKT). No live data fetching during off-hours or weekends; use last saved closing prices.

## 2. UI & Professional Standards
- **Institutional Persona:** The app must look professional, not like a "kid's project."
- **Emoji Removal:** Remove all decorative/non-essential emojis from navigation and headers.
- **Currency:** Strictly use PKR (Pakistani Rupee). Remove all '$' symbols and USD references.
- **Clean Metrics:** The CMP (Current Market Price) column must show only the latest price (numerical), no timestamps or "locked" dates.
- **Privacy:** Hide absolute Baseline and Current values from the main dashboard Growth Tracker unless logged in with PIN (786). Show only consolidated % growth publicly.
- **Navigation:** Professional sidebar with clear sections: Recovery Dashboard, Growth Tracker, Editor, AI Strategy.

## 3. AI & Data Integrity
- **No Data Fabrication:** AI must never assume dates (today is May 9, 2026) or invent "assumed prices." It must use provided CMP.
- **Quota Management:** 
    - Implement model rotation (Gemini 2.5 Flash -> Flash Latest -> Pro Latest) to bypass 429/404 errors.
    - Show a real-time countdown timer if rate limits are hit.
    - Persist the "report task" so it auto-resumes after the timer hits zero.
- **Deduplication:** Aggregate holdings by symbol *internally* to optimize AI tokens, but present the final analysis *per account*.
- **Report Caching:** Cache successful AI reports for 1 hour to prevent redundant API hits and quota waste.
- **Transparency:** AI responses must tag the active model used (e.g., `Active Analyst: gemini-pro-latest`).

## 4. Key Metrics & Totals
- **Recovery Dashboard:** Show individual totals for each account (Invested, Value, P/L in PKR) and a final consolidated grand total at the bottom.
- **Growth Tracker:** Show Consolidated Growth % as the primary metric.

## 5. Explicit Instruction History (Consolidated)
- "Deal each account as separate portfolio."
- "Aggregate and consolidate portfolio just for sending AI, to optimize token request... this is your background working not for data show."
- "No need to show symbol... show me total of each account and at the end show consolidated total."
- "Dont locked the date in current price colum, it must be latest data."
- "Use highest gemini version first and when quota exceed show message which version you are using."
- "Act smart and visualize data as expert analyst not a kid."
- "No need to stock analysis, calls tracking... just loss recovery mechanism."
