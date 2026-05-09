# PSX Portfolio Recovery & Growth Dashboard
**Live Dashboard:** [mttpsx.streamlit.app](https://mttpsx.streamlit.app/)

Specialized system for tracking account recovery from loss to profit, followed by long-term growth monitoring for Pakistan Stock Exchange (PSX) portfolios.

## System Focus
1. **Recovery Phase:** Prioritizes strategies to bring each account into net profit.
2. **Growth Phase:** Transitions to tracking percentage growth once baseline profitability is achieved.
3. **Day 0 Tracking:** Baseline set on May 9, 2026, to monitor future performance.

## Key Performance Indicators (May 9, 2026)
- **Account Status:** Recovery Mode (Main focus).
- **Consolidated P/L:** Tracking towards zero-loss baseline.
- **Growth Benchmark:** Day 0 values established.

## Project Guidelines
- **Live Data:** Only fetched during PSX market hours (Mon-Thu: 9:15-3:30, Fri: 9:00-4:30 PKT).
- **Offline Integrity:** Outside market hours, use the last saved closing prices from `analysis/last_prices.json`.
- **AI Methodology:** Technical analysis (RSI, EMA, MACD) is performed in the background to drive AI recovery suggestions.

## AI Agent Guidelines (Quota Management)
- **Model Rotation:** Use `gemini-1.5-flash` primarily, rotating to `gemini-2.0-flash-exp` if 429 errors occur.
- **Strict Caching:** Persistent background analysis must be cached to avoid redundant API calls.
- **Recovery Focus:** AI prompts must prioritize "Loss Recovery" strategies (averaging, switching) until accounts are in profit.
