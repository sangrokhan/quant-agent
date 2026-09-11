# Backtest Report: EMV Fast/Signal-Line Crossover (QQQ/SPY, REJECTED)

**Strategy file:** `strategies/2026-09-11_emv_signal_line_crossover.py`
**Date:** 2026-09-11
**Outcome:** REJECTED

## Hypothesis

Richard Arms' Ease of Movement (EMV) fast-window SMA crossing above a
slower signal-window SMA of EMV signals building upside momentum on light
volume (MACD-style dual-moving-average cross of the EMV oscillator itself).
Distinct from the already-tested plain EMV zero-line cross
(2026-09-04-115, accepted equity w/ SMA trend filter) and EMV
bullish-divergence variant (2026-09-08-093, rejected).

Source: Google AI-overview synthesis (TradingSim/Investopedia sourced),
retrieved via `browser_exec` fallback after `web_search` DDGS TLS/connection
errors on this query. URL:
`https://www.google.com/search?q=%22Ease+of+Movement%22+EMV+indicator+trading+strategy+rules+signal+line`.
Explicit rule quoted: "enter when the fast EMV line crosses above the
signal moving average"; exit "when fast EMV line crosses below the signal
moving average".

## Step 6 — Grid test summary

Grid: `fast_window` in {5,7,10}, `signal_window` in {14,21}, `max_hold_days`
in {15,20,30}; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto);
vol_regime_splits=3 (low/mid/high terciles). 144 total cells.

- **pass_fraction: 0.243** (35/144)
- **by_asset_class:** equity 35/108 passed; crypto **0/36** (decisive
  rejection on crypto)
- **by_vol_regime:** low 20/36, mid 11/36, high 4/36, n/a 0/36 — edge
  concentrated in low/mid-vol regimes, degrades sharply in high-vol
- **best_cell:** fast_window=10, signal_window=14, max_hold_days=15,
  QQQ, mid-vol regime, Sharpe 1.946
- **worst_cell:** fast_window=7, signal_window=21, max_hold_days=20, QQQ,
  high-vol regime, Sharpe -0.164

## Step 7 — Single-config validation (best config: fast_window=10,
signal_window=14, max_hold_days=15)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **1.100 PASS** | 0.729 **FAIL** | >= 1.0 |
| Max drawdown | 0.364 **FAIL** | 0.202 PASS | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.817 PASS | 0.411 **FAIL** | >= 0.5 |
| Walk-forward (manual 4-split; `vbt.utils.splitting.RangeSplitter` broken in this install, same pre-existing repo-wide workaround as other reports) | 1.0 (4/4) PASS | 0.75 (3/4) PASS | >= 0.75 |
| Parameter sensitivity (relative std across fast_window x signal_window mini-sweep) | 0.327 PASS | 0.286 PASS | <= 0.5 |

## Step 8 — Decision: REJECTED

Neither symbol clears all validators: QQQ fails max drawdown (36.4% vs 25%
threshold — a single elevated-vol regime episode blows through the
drawdown budget despite decent Sharpe); SPY fails both Sharpe (0.729) and
transaction-cost survival (0.411 net Sharpe after 10bps/trade, 206 trades).
Crypto is decisively rejected across the entire grid (0/36 cells).

## Notes for future iterations

- The edge is real but concentrated in low/mid-vol regimes and doesn't
  survive risk controls on either equity symbol at this parameter setting.
  A volatility-regime gate (same construction as
  `2026-09-03_bb_meanrev_qqq_volregime.py`) restricting entries to
  low/mid-vol terciles could plausibly rescue the QQQ MDD failure — worth
  a follow-up iteration.
- SPY's high trade count (206) relative to QQQ (209, similar) at the same
  parameterization drags net-of-cost Sharpe below threshold; a longer
  `signal_window` (reducing trade frequency) is worth testing specifically
  for SPY in a follow-up, similar to the per-symbol tuning pattern used
  in 2026-09-11-017 (Aroon+Chandelier SPY fix).
