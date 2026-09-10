# Chop Zone (34-EMA angle) trend-continuation + ADX filter

**Hypothesis source:** https://pineify.app/pine-script/indicators/chop-zone
(Pineify engineering team, published 2024). Full formula disclosed:
`span = 25 / (highestHigh - lowestLow) * lowestLow`,
`dy = (EMA34[t-1] - EMA34[t]) / hlc3 * span`,
`angle = arccos(1/sqrt(1+dy^2)) * 180/pi` (sign flipped here so positive
angle = accelerating uptrend, matching source's "turquoise = bullish"
color semantics). Source's own "Strategy 1 — Trend Continuation with ADX
Filter": long when ADX(14) > 25 AND the EMA angle is >= a "strong" threshold
(turquoise/dark-green colors) for 2+ consecutive bars; exit when the angle
decelerates back toward the "yellow" neutral zone.

## Grid test (Step 6)

`param_grid={"adx_threshold": [20,25,30], "angle_strong_threshold": [3,5]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 17/72 = 0.236**
- By asset class: equity 17/36 (0.47), crypto 0/36 (0.0) — decisive crypto rejection
- By vol regime: low 12/24, mid 5/24, high 0/24 — strategy only works in calmer regimes
- Best cell: SPY, low-vol, adx_threshold=20/angle_strong_threshold=3, Sharpe 2.73
- Worst cell: QQQ, high-vol, adx_threshold=30/angle_strong_threshold=3, Sharpe -1.73

## Full-sample validator suite (Step 7), config adx_threshold=20/angle_strong_threshold=3

| Validator | SPY | QQQ |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.60 ❌ | 1.41 ✅ |
| Max drawdown (<=0.25) | 0.267 ❌ | 0.155 ✅ |
| Tx-cost survival (net Sharpe >=0.5, 10bps/trade) | 0.47 ❌ | 1.31 ✅ |
| Walk-forward (manual 4-slice fallback; `vbt.utils.splitting.RangeSplitter` broken in this install, pre-existing repo-wide gap) | 0.75 ✅ (3/4) | 1.00 ✅ (4/4) |
| Parameter sensitivity (relative std <=0.5, 6-cell adx_threshold x angle_strong_threshold sweep) | 0.399 ✅ | 0.479 ✅ |

SPY: 62 trades over 7.7yr. QQQ: 58 trades over 7.7yr, all 5 validators pass.

## Decision

**Accept for QQQ only.** SPY fails 3 of 5 validators (Sharpe, MDD,
transaction-cost survival) at the shared config — the Chop Zone angle +
ADX filter combination works on QQQ's higher-beta trend character but not
SPY's calmer index behavior. Crypto (BTC/USDT, ETH/USDT) rejected
decisively across the entire grid (0/36 cells) — likely because crypto's
24/7 continuous trading and different volatility character breaks the
30-bar highest-high/lowest-low normalization calibrated (per source) for
traditional market hours/sessions.
