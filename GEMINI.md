# Systems Ltd. (SYS) Technical Analysis
**Live Dashboard:** [mttpsx.streamlit.app](https://mttpsx.streamlit.app/)

Persistent tracking of technical indicators and trade data for Systems Ltd. (SYS) on the Pakistan Stock Exchange (PSX).

## Trade Summary
- **Purchase Price:** 160.00
- **Quantity:** 1000
- **Current Market Price (CMP):** 154.10 (as of May 8, 2026)
- **Status:** Strong uptrend; price is holding above all key EMAs with rising momentum.

## Technical Indicators (Daily) - Updated May 8, 2026

| Indicator | Value | Interpretation |
| :--- | :--- | :--- |
| **Technical Score** | 80/100 | Strongly Bullish (Robust uptrend across all timeframes). |
| **RSI (14)** | 58.53 | Bullish; healthy momentum with room to grow. |
| **MACD (12, 26, 9)** | 2.77 | Bullish; momentum is increasing. |
| **ADX (14)** | 14.19 | Weak Trend; consolidation phase ending, trend strengthening. |
| **Super Trend** | 144.01 | Price is above the trend line (Support). |

## Support & Resistance (Pivots)
- **R1:** 156.61 (Immediate Resistance)
- **Pivot (P):** 154.80 (Immediate Support)
- **S1:** 153.61
- **S2:** 151.80
- **S3:** 140.45 (EMA 200 - Critical Support)

## Exponential Moving Averages (EMA)
The price is well above all key EMAs:
- **EMA 9:** 151.84 (Immediate Support)
- **EMA 25:** 148.82
- **EMA 44:** 146.48
- **EMA 88:** 145.85
- **EMA 100:** 145.62
- **EMA 200:** 140.45

## Market Timings (PKT - UTC+5)
- **Monday - Thursday:** 09:15 AM - 03:30 PM
- **Friday:** 09:00 AM - 04:30 PM
- **Weekend:** Closed

## Project Guidelines
- **Live Data:** Only fetch live price during market hours to minimize API hits.
- **Offline Mode:** Show "Mkt is Close" with the last closing price in yellow outside hours.

## AI Agent Guidelines
- **Persistent Progress:** Update `SESSION_STATE.md` and `FULL_WORK_LOG.md` every 15 minutes or after significant milestones to ensure no work is lost.
- **Quota Management:** Monitor token usage and stop operations when the session quota reaches **90%**.
- **Session Handover:** When the quota limit is reached, perform a final save of all session data, state, and pending tasks for the next resumption.
