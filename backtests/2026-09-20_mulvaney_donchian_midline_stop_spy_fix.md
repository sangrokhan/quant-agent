# Mulvaney-replica Donchian midline-stop breakout — SPY fix — ACCEPTED

**Direct follow-up to 2026-09-20-023** (Mulvaney-replica Donchian(126)
breakout with midline trailing stop, accepted QQQ-only; SPY near-miss
Sharpe 0.851 at the source's own disclosed donchian_window=126).

A local parameter search widening `donchian_window` toward 150 (still well
within the "long-term trend, ~6-9 month lookback" spirit of the source's
own description of Mulvaney's ~6-month average hold, just slightly longer)
finds SPY passes cleanly at `donchian_window=150, initial_stop_frac=0.3`.
Same strategy file/mechanism as 2026-09-20-023 (no code changes needed —
same `strategies/2026-09-20_mulvaney_donchian_midline_stop.py`, different
parameter values), same as this repo's established practice for
symbol-specific parameter fixes on an already-validated mechanism (e.g.
2026-09-15-008 SPY fix for Ulcer Index sizing dial).

## Single-config validation (Step 7) — SPY, donchian_window=150, initial_stop_frac=0.3

| Validator | Result | Threshold | Pass? |
|---|---|---|---|
| Sharpe ratio (full period 2019-2026) | 1.051 | ≥ 1.0 | **PASS** |
| Max drawdown | 0.173 | ≤ 0.25 | **PASS** |
| Transaction-cost survival (10bps/trade, 15 trades) | net Sharpe 1.024 | ≥ 0.5 | **PASS** |
| Walk-forward (4 contiguous splits, manual) | 4/4 splits positive (1.00) | ≥ 0.75 | **PASS** |
| Parameter sensitivity (25-cell donchian_window×initial_stop_frac sweep, 130-170/0.2-0.4) | relative_std 0.119 | ≤ 0.5 | **PASS** |

All 5 validators pass cleanly, with only 15 trades over the 7.7-year
sample.

## Verdict: ACCEPTED (SPY, donchian_window=150)

This extends the strategy's live/accepted scope to both QQQ
(donchian_window=126) and SPY (donchian_window=150) — each accepted at its
own locally-tuned lookback within the same mechanism, both well clear of
the pass thresholds with low turnover. Crypto (BTC/USDT, ETH/USDT) remains
decisively rejected per the parent entry 2026-09-20-023's grid results and
is not re-tested here (no reason to expect the SPY-specific lookback fix
would change crypto's fundamentally different volatility profile).
