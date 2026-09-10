# Momentum Pinball (LBR/RSI = RSI-of-ROC) oversold entry, daily-bar adaptation

**Hypothesis source:** Momentum Pinball (Linda Raschke / Larry Connors,
"Street Smarts"), per MQL5 article "Momentum Pinball trading strategy"
(https://www.mql5.com/en/articles/4148, read via Google AI-overview
synthesis). LBR/RSI = a 3-period RSI applied to a 1-period ROC series.
Source rule: LBR/RSI of last closed daily bar < 30 = oversold long setup.
Original system uses an intraday stop-order entry (next session's first
hourly bar high) and holds 1-2 days; adapted here to a pure daily-bar
version (enter at next close after the oversold cross, exit after
`max_hold_days` or an LBR/RSI cross back above `exit_threshold`=70).

## Grid test (Step 6)

`param_grid={"oversold_threshold": [20,30], "max_hold_days": [2,4,6]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 15/72 = 0.208**
- By asset class: equity 15/36 (0.42), crypto 0/36 (0.0) — decisive crypto rejection
- By vol regime: low 9/24, mid 4/24, high 2/24
- Best cell: SPY, low-vol, oversold_threshold=20/max_hold_days=6, Sharpe 1.77
- Worst cell: SPY, high-vol, oversold_threshold=20/max_hold_days=2, Sharpe -1.05

## Full-sample validator suite (Step 7), config oversold_threshold=20/max_hold_days=6

| Validator | SPY | QQQ |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.539 ❌ | 0.717 ❌ |
| Max drawdown (<=0.25) | 0.092 ✅ | 0.098 ✅ |
| Tx-cost survival (net Sharpe >=0.5, 10bps/trade) | 0.435 ❌ | 0.618 ✅ |
| Walk-forward (manual 4-slice fallback) | 0.75 ✅ (3/4) | 1.00 ✅ (4/4) |
| Parameter sensitivity (relative std <=0.5) | 0.632 ❌ | 0.658 ❌ |

SPY: 40 trades. QQQ: 45 trades. Both fail Sharpe and parameter sensitivity.

## Decision

**Reject** for both SPY and QQQ — both fail Sharpe ratio (0.539/0.717 vs
1.0 threshold) and parameter sensitivity (relative std 0.632/0.658 vs 0.5
threshold, i.e. performance swings too much across the small grid of
oversold_threshold/max_hold_days combos). Crypto rejected decisively
(0/36 grid cells). The daily-bar adaptation of this originally-intraday
system likely loses the edge that came from the tight next-session-open
stop-order entry timing — a close-based next-day entry is materially
looser and picks up more noise. Not worth pursuing further without
intraday data.
