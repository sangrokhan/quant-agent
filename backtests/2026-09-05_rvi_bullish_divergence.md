# RVI bullish divergence (rejected)

**Hypothesis:** Per Google's AI-overview synthesis of Investopedia/Avatrade/
Forexopher RVI divergence rules: bullish divergence = price forms a LOWER
LOW while the RVI oscillator forms a HIGHER LOW over the same window; entry
trigger = RVI crosses above its signal line OR rises above zero; stop below
recent swing low. Adapted to a long-only daily-bar backtest: exit on RVI
crossing back below its signal line, or a max_hold_days time-stop.

Source: Google AI-overview search result (quantifiedstrategies.com's own
RVI divergence page 404'd; used the AI-overview's citation of Investopedia/
Avatrade/Forexopher instead — `web_search` still failing this session,
`browser_exec` Google search used throughout).

Novelty: first RVI-DIVERGENCE strategy in this repo — prior RVI entries
(signal-line-cross/midline-cross variants) never compared price swing lows
against RVI swing lows; divergence detection is a materially different,
more selective condition.

## Step 6 — Grid summary

Grid: `rvi_window in {8,10,14}`, `swing_lookback in {15,20,30}`,
`max_hold_days in {15,25}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 216 total cells.

- pass_fraction: 0.0 (0/216) -- **decisive rejection**, every cell in
  every asset class / vol regime failed.
- by_asset_class: equity 0/108; crypto 0/108
- by_vol_regime: low 0/72, mid 0/72, high 0/72
- best_cell: rvi_window=10, swing_lookback=15, max_hold_days=15, QQQ,
  high-vol, Sharpe 0.84 (still below the 1.0 grid threshold)

## Step 7 — Single-config check (best grid params: rvi_window=10, swing_lookback=15, max_hold_days=15)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (QQQ, full-period) | ❌ | 0.48 | ≥ 1.0 |
| Sharpe ratio (SPY, full-period) | ❌ | 0.21 | ≥ 1.0 |
| Max drawdown (QQQ) | ✅ | 8.1% | ≤ 25% |
| Max drawdown (SPY) | ✅ | 5.7% | ≤ 25% |

Decisive across the entire 216-cell grid — no cell reached the 1.0 Sharpe
bar. The divergence condition (price lower-low + RVI higher-low + RVI
cross) is too rare/low-conviction as implemented to produce a tradeable
edge on daily bars for either asset class. Skipped walk-forward/parameter
sensitivity given the fully decisive grid result.

## Decision: **REJECT** (0/216 grid cells passed; decisive across both asset classes and all vol regimes)
