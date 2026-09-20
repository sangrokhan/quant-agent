# CC/RS Drift-Ratio Trend Breakout — Backtest Report (2026-09-21)

## Hypothesis

Per trendsandbreakouts.com's Rogers-Satchell Volatility article
(https://trendsandbreakouts.com/rogers-satchell-volatility, read via
browser_exec fallback — web_search backend intermittently returning
TLS/connection errors this iteration): Rogers-Satchell (RS) volatility is
drift-independent (built purely from within-bar OHLC relationships) while
close-to-close (CC) realized volatility conflates directional drift with
intrabar scatter. The source's own claim: "Run Rogers-Satchell and
close-to-close vol over the same lookback... that ratio by itself is a
useful trend filter without requiring any moving averages or momentum
oscillators." This strategy operationalizes CC_vol/RS_vol as a standalone
trend-detection gate combined with an N-day-high breakout trigger.

Source URL: https://trendsandbreakouts.com/rogers-satchell-volatility

## Strategy file

`strategies/2026-09-21_cc_rs_drift_ratio_trend_breakout.py`

## Grid test summary (Step 6)

- Grid: `ratio_threshold` ∈ {1.3, 1.5, 1.8}, `breakout_window` ∈ {15, 20, 30}
- Symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- Vol regime splits: 3
- Total cells: 108, passed: 14, **pass_fraction = 0.130**
- By asset class: equity 14/54 passed, crypto **0/54** (decisive fail on
  crypto — the drift-ratio signal fires far too rarely to matter, or the
  breakout confirmation never aligns with a ratio spike on crypto's noisier
  bars)
- By vol regime: low 8/36, mid 5/36, high 1/36 — weak everywhere, not
  concentrated in any one regime
- Best average Sharpe across all 9 param combos on equity: ~0.58 (ratio
  1.5, breakout_window=15) — well below the 1.0 bar
- Best single cell: ratio_threshold=1.3, breakout_window=15, SPY, low-vol,
  Sharpe=1.57; worst: same params, SPY high-vol, Sharpe=-0.92

## Single-config validation (Step 7) — SPY, ratio_threshold=1.3, breakout_window=15, full sample 2018-01-01..2026-09-01

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.320 | ≥1.0 |
| Max drawdown | pass | 0.154 | ≤0.25 |
| Transaction cost survival | **FAIL** | net Sharpe 0.245 (40 trades, 10bps/trade) | ≥0.5 |
| Parameter sensitivity | pass | relative std 0.380 (9 combos, SPY) | ≤0.5 |
| Walk-forward | not run (decisive reject already on 2 of 4 core validators; skipped per `suggested_workload` time-budget) |

## Decision: REJECTED (decisive)

The source's own "ratio as standalone trend filter, no MA/oscillator
needed" claim did not translate into a usable trading edge in this repo's
backtests: the signal is far too sparse and unreliable outside a narrow
low-vol equity slice, decisively fails on crypto (0/54 grid cells passed),
and even the best equity config fails both Sharpe and transaction-cost
survival on the full sample. Unlike the near-miss Z-Score Range Box
Breakout tested earlier this trigger, this is a clean, low-ambiguity
rejection — no regime-gating rescue is obviously indicated since performance
is weak across all three vol regimes, not concentrated in one.
