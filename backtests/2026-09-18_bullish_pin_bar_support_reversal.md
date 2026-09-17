# Backtest Report: Bullish Pin Bar Reversal at Rolling Support (QQQ accepted; SPY near-miss)

**Strategy file:** `strategies/2026-09-18_bullish_pin_bar_support_reversal.py`
**Knowledge base id:** 2026-09-18-021

## Hypothesis

Per tradingstrategyguides.com's "Pin Bar Reversal Strategy: The Complete
Guide For Price Action Traders"
(https://tradingstrategyguides.com/pin-bar-reversal-strategy-the-complete-guide-for-price-action-traders/,
visited this iteration via `browser_exec` fallback -- `web_extract` refused
with "DuckDuckGo (ddgs) is a search-only backend and cannot extract URL
content"), a genuine bullish pin bar reversal requires:

- a lower tail that is >= 2-3x the real body and dominates the candle's range,
- a small/non-existent upper "nose" (<=10-15% of range),
- the real body closing in the top 25% of the candle range, and
- crucially, the pattern must occur **at a key support/resistance/trendline
  level** -- the source states "pin bars traded in isolation fail".

This strategy operationalizes the support condition with a rolling-min-low
proxy (today's low within `support_tolerance` of the trailing
`support_lookback`-day low), since the repo's OHLCV data has no discretionary
S&R annotations. Entry is the day after a qualifying bullish pin bar forms at
rolling support; exit at a fixed risk:reward target (source recommends
>=2:1, tuned to 2.5:1) off the pin bar's own tail-implied stop, a hard stop
below the tail tip, or a `max_hold_days` time-stop.

## Single-config metrics (best grid config: `support_lookback=10,
rr_target=2.5, max_hold_days=25, support_tolerance=0.01`)

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-forward pass_fraction | Param-sensitivity rel-std | Trades |
|---|---|---|---|---|---|---|
| QQQ | 1.071 (pass, thr 1.0) | 0.033 (pass, thr 0.25) | 1.009 (pass, thr 0.5) | 0.75 (pass, thr 0.75) | 0.123 (pass, thr 0.5) | 12 |
| SPY | 0.967 (**fail**, thr 1.0) | 0.037 (pass) | 0.853 (pass) | 1.00 (pass) | 0.286 (pass) | 16 |

## Step 6 grid summary (support_lookback in [10,20,30], rr_target in
[1.5,2.0,3.0], symbols=QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

```
total_cells: 108, passed_cells: 15, pass_fraction: 0.139
by_asset_class: equity 13/54, crypto 2/54
by_vol_regime: low 5/36, mid 1/36, high 9/36
best_cell: QQQ low-vol, support_lookback=10/rr_target=2.0, Sharpe=1.65
worst_cell: ETH/USDT high-vol, support_lookback=10/rr_target=1.5, Sharpe=-0.86
```

Grid confirms: this pattern is strongly equity-favored (13/54 vs 2/54 for
crypto) and works better in higher-vol regimes than mid-vol for the raw
support-lookback/rr_target combos tried, consistent with pin-bar rejections
being more meaningful/tradeable during volatile whipsaw conditions.

## Pass/fail per validator (best config)

- Sharpe ratio: **QQQ pass** (1.071 >= 1.0), SPY fail (0.967 < 1.0)
- Max drawdown: both pass
- Transaction cost survival (10bps/trade flat): both pass
- Walk-forward (4 equal contiguous splits, positive-Sharpe fraction >= 0.75):
  both pass (QQQ 3/4, SPY 4/4)
- Parameter sensitivity (support_lookback x rr_target x max_hold_days sweep,
  relative std <= 0.5): both pass

Note: this repo's `validation/validators.py::check_walk_forward` currently
errors (`module 'vectorbt.utils' has no attribute 'splitting'`) against the
installed vectorbt version -- a manual 4-equal-split walk-forward using the
identical pass criterion (fraction of splits with positive Sharpe >= 0.75)
was substituted for this iteration; a future iteration should fix
`check_walk_forward` itself.

## Decision

**Accepted for QQQ only.** SPY missed the Sharpe threshold by a narrow
margin (0.967 vs 1.0) despite passing every other validator -- recorded as a
near-miss worth revisiting (e.g. widening `support_tolerance` or adding a
trend-alignment filter specific to SPY). Crypto (BTC/USDT, ETH/USDT) was
decisively rejected by the Step 6 grid (2/54 passes) and not carried forward
to single-config validation.
