# Backtest report: SFP (Swing Failure Pattern) bullish liquidity-sweep reversal

**Strategy file:** `strategies/2026-09-09_sfp_liquidity_sweep_reversal.py`
**KB id:** 2026-09-09-087

## Hypothesis

Per https://www.quantvps.com/blog/swing-failure-pattern-strategy (accessed via
browser_exec fallback — web_search's DDGS backend errored with a TLS
connection error), a bullish SFP: price wicks below a prior N-bar swing low
(sweeping stops) but closes back above it same bar (rejection). Enter long
the next bar; stop below the sweep wick; target at a fixed risk:reward
multiple (source suggests 1:2/1:3) or a max-hold time-stop. First
liquidity-sweep/stop-hunt strategy in this repo requiring the sweep-and-reject
within the SAME bar (distinct from Turtle Soup 2026-09-04-076's next-day
close-back-above, and from IBS-based Adjusted Failed Bounce 2026-09-05-019).

## Grid test (Step 6)

`param_grid`: `swing_lookback=[5,10,15]`, `risk_reward=[1.5,2.0]`,
`max_hold_days=[10,20]`; `symbols`: equity `[QQQ, SPY]`, crypto
`[BTC/USDT, ETH/USDT]`; `vol_regime_splits=3`; period 2019-01-01..2026-09-01.

- **pass_fraction:** 0.125 (18/144)
- **by_asset_class:** equity 18/72, crypto 0/72 (crypto rejected decisively)
- **by_vol_regime:** low 17/48, mid 1/48, high 0/48 — the pattern only shows
  edge in low-vol grind regimes; it degrades sharply once volatility rises
  (consistent with a liquidity-sweep pattern that gets noisier/less reliable
  as whipsaw increases).
- **best_cell:** swing_lookback=10, risk_reward=2.0, max_hold_days=10, SPY,
  low-vol regime, Sharpe 2.50 (regime-sliced, not full-sample).
- **worst_cell:** swing_lookback=15, risk_reward=2.0, max_hold_days=10, SPY,
  mid-vol regime, Sharpe -0.92.

## Single-config validation (Step 7) — best full-period config (swing_lookback=10, risk_reward=2.0, max_hold_days=10)

vectorbt's `check_walk_forward` is broken repo-wide
(`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`),
consistent with prior iterations' notes — substituted a manual 4-equal-split
walk-forward check (Sharpe>0 per split) as documented in
`backtests/2026-09-09_ibd_relative_strength_line_breakout.md`.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.308 — **FAIL** | 0.398 — **FAIL** |
| Max drawdown (<=0.25) | 0.247 — pass | 0.227 — pass |
| TC survival (net Sharpe >=0.5, 10bps/trade, ~160 trades) | 0.098 — **FAIL** | 0.093 — **FAIL** |
| Walk-forward (manual 4-split, >=75% positive) | 2/4 (0.5) — **FAIL** | 3/4 (0.75) — pass |
| Parameter sensitivity (relative std <=0.5) | 0.918 — **FAIL** | 0.264 — pass |

Full-sample Sharpe (0.31/0.40) is far below the grid's best regime-sliced
cell (2.50) — the pattern's edge is concentrated almost entirely in low-vol
regimes and full-period trading, which is unfiltered by vol regime, dilutes
it into a loss on Sharpe/TC/param-sensitivity grounds for both symbols.

## Decision

**Rejected** (both QQQ and SPY) — Sharpe, transaction-cost survival, and (for
QQQ) walk-forward and parameter sensitivity all fail on the full,
un-regime-filtered sample. Crypto rejected decisively (0/72 grid cells).

**Worth revisiting:** the grid's low-vol-regime pass rate (17/48, by far the
best slice) suggests this same signal gated to trade ONLY during low
realized-vol regimes (similar filter to the accepted
`2026-09-03_bb_meanrev_qqq_volregime.py`) could clear the bar — a future
iteration could re-test with an explicit vol-regime gate added to
`generate_signals` rather than trading the raw pattern unconditionally.
