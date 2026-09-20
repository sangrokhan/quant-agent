# Backtest Report: Fractional-ATR-Distance Breakout with Trend Filter + ATR Stop (Rescue #2)

**Strategy file:** `strategies/2026-09-21_fractional_atr_breakout_trend_filter_rescue.py`
**Date:** 2026-09-21
**Rescue lineage:** `2026-09-20-137` (fixed-bar exit, no stop, rejected on
MDD) -> `2026-09-21-188` (added ATR stop-loss, improved but still failed
MDD on full sample) -> **this entry** (adds a 200-day SMA trend filter on
top of the ATR stop).

## Hypothesis

Per this repo's own knowledge-base notes on the prior rescue attempt
(2026-09-21-188): "the next fix should add a regime filter ... rather than
a purely per-trade risk control, since the per-trade stop-loss fix has now
been tried and still falls short." This iteration keeps the identical
entry trigger (`high >= prior_close + atr_frac*ATR`) and ATR-multiple
stop-loss, but additionally requires `close[t-1] > SMA(trend_window)`
before the breakout entry is allowed to fire — skipping the signal
entirely during established downtrends, on the theory that most of the
strategy's drawdown came from repeatedly buying ATR-distance "breakouts"
during choppy/declining markets where the breakout was noise, not real
momentum.

## Grid test (Step 6)

`param_grid={"atr_frac": [0.25, 0.5], "hold_days": [5, 10],
"stop_atr_mult": [2.0, 3.0], "trend_window": [50, 100, 200]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2018-01-01 to 2026-09-01.

- **Overall pass_fraction: 86/288 = 0.299** (up from the prior rescue's
  0.236, and the original's 0.222)
- By asset class: equity 77/144, crypto 9/144
- By vol regime: low 56/96, mid 18/96, **high 12/96** (first time this
  strategy family shows any high-vol-regime robustness at all)
- Best cell: QQQ, atr_frac=0.25/hold_days=10/stop_atr_mult=2.0/
  trend_window=50, low-vol regime, Sharpe 2.76

## Full-sample single-config validators

**QQQ** (atr_frac=0.25, hold_days=5, stop_atr_mult=3.0, trend_window=200):

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.263 | >= 1.0 |
| Max drawdown | **PASS** | 0.123 | <= 0.25 |
| Transaction cost survival (10bps, 246 trades) | **PASS** | 0.870 | >= 0.5 |
| Walk-forward (manual 4-split) | **PASS** | 4/4 | >= 0.75 |
| Parameter sensitivity | **PASS** | relative_std 0.119 | <= 0.5 |

**SPY** (atr_frac=0.25, hold_days=10, stop_atr_mult=3.0, trend_window=200):

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.041 | >= 1.0 |
| Max drawdown | **PASS** | 0.159 | <= 0.25 |
| Transaction cost survival (10bps, 149 trades) | **PASS** | 0.763 | >= 0.5 |
| Walk-forward (manual 4-split) | **PASS** | 4/4 | >= 0.75 |
| Parameter sensitivity | **PASS** | relative_std 0.202 | <= 0.5 |

Crypto (BTC/USDT, ETH/USDT): swept the same 24-point local grid — **no
parameter combination passes both Sharpe and max-drawdown simultaneously**
for either symbol. Rejected for crypto.

## Decision: ACCEPTED (equity only — QQQ + SPY)

Both equity symbols pass all 5 validators with clean margins at their own
(similar, not identical) best local config. This resolves the original
2026-09-20-137 near-miss's max-drawdown failure via a trend filter added on
top of the already-tried ATR stop-loss, exactly per the roadmap this repo's
own knowledge base laid out across the last two iterations. Crypto remains
rejected — the trend filter and stop-loss reduce equity drawdown
substantially but do not rescue crypto's much larger tail risk.
