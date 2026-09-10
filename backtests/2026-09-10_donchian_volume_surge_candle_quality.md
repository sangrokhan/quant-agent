# Donchian Channel Breakout + Volume Surge + Candle-Quality Filter (QQQ)

**Hypothesis source:** Google AI-overview synthesis (LuxAlgo/JournalPlus/TrendSpider/avatrade.co.za),
via browser_exec Google SERP fallback (web_search's DDGS backend TLS/connection error on this
query: `https://www.google.com/search?q=Donchian%20channel%20breakout%20volume%20surge%20confirmation%20strategy%20rules`).

**Hypothesis:** A close breaking cleanly above the N-day upper Donchian band is a
stronger, less-fakeout-prone long entry when (1) the breakout bar's volume is
>= 1.5-2x its own N-day average volume ("proving institutional participation"),
AND (2) the breakout candle's body comprises >=60% of its own high-low range
(filters weak doji/pin-bar edge closes). Exit near the Donchian channel
midline, buffered by an ATR multiple.

Strategy file: `strategies/2026-09-10_donchian_volume_surge_candle_quality.py`

## Step 6 grid summary (144 cells: donchian_window x vol_surge_mult x min_body_ratio x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol terciles)

- `pass_fraction`: 12/144 = 0.083
- `by_asset_class`: equity 12/72 passed; **crypto 0/72 passed** (decisive fail)
- `by_vol_regime`: low 12/48 passed; mid 0/48; high 0/48 (only survives in
  low-vol regime, and only on equity)
- best cell: donchian_window=15, vol_surge_mult=1.5, min_body_ratio=0.5, QQQ,
  low-vol regime, Sharpe 1.797
- worst cell: donchian_window=25, vol_surge_mult=1.5, min_body_ratio=0.5, QQQ,
  high-vol regime, Sharpe -0.912

## Step 7 single-config validation (QQQ, donchian_window=15, vol_surge_mult=1.5,
min_body_ratio=0.5 -- grid's best cell, full 2019-01-01..2026-09-01 sample, not
just the low-vol slice)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.388 | 1.0 |
| Max drawdown | pass | 0.080 | 0.25 |
| Transaction cost survival (10bps/trade, 8 trades) | **FAIL** | 0.341 | 0.5 |
| Walk-forward (4 splits, manual since vbt.utils.splitting unavailable) | pass | 0.75 (3/4 splits positive) | 0.75 |
| Parameter sensitivity (12-cell full-sample sweep) | **FAIL** | NaN (mean returns ~0, relative_std undefined/Infinity) | 0.5 |

## Outcome: **rejected**

Sharpe and transaction-cost-survival fail decisively on the full sample --
the grid's best cell (Sharpe 1.797) is a low-vol-regime-only slice, not
representative of the full-sample behavior once the strategy runs through
mid/high-vol regimes. Only 8 trades over 2019-2026 on QQQ (breakout+volume-
surge+candle-quality triple filter is very restrictive), so parameter
sensitivity is degenerate (near-zero mean Sharpe across the parameter grid).
Crypto rejected decisively (0/72 grid cells) -- the volume-surge/candle-
quality filters appear to select too few, too noisy signals on BTC/ETH.

Worth a future revisit with: a looser volume/body threshold to generate more
trades, or restricting entries explicitly to low-vol regimes only (per the
grid's own by_vol_regime finding) rather than trading unconditionally.
