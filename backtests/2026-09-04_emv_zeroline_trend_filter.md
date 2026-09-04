# Ease of Movement (EMV) Zero-Line Cross + SMA Trend Filter — Backtest Report (2026-09-04)

## Hypothesis
Ease of Movement (EMV, Richard Arms) is a volume-based oscillator
(Distance Moved / Box Ratio, smoothed by an n-period SMA, default 14) that
measures how "easily" price moves per unit of volume. Source explicitly
states EMV is rarely reliable standalone and should be combined with a
moving-average trend filter. Long entry when EMV(emv_period) crosses above
zero while close > SMA(trend_window=200); exit on EMV crossing back below
zero or a max_hold_days time-stop.

Sources:
- https://www.google.com/search?q=Ease+of+Movement+indicator+trading+strategy+rules+quantifiedstrategies
  (AI overview + SERP snippets: zero-line cross rule, 14-period default,
  recommends MA trend filter)
- https://www.quantifiedstrategies.com/ease-of-movement/ (formula detail,
  pros/cons, explicit recommendation to pair with a moving-average trend
  filter + RSI; full coded backtest rules are membership-gated but the
  core zero-line + trend-filter logic is stated free)
(web_search failed for both queries -- DDGS/RequestError -- fell back to
browser_exec: Google search page read directly, then quantifiedstrategies.com
article read directly via rendered DOM text.)

## Grid summary (Step 6)
`param_grid={emv_period:[10,14,21], max_hold_days:[10,15]}`, symbols
`{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=72, passed_cells=17, **pass_fraction=0.236**
- by_asset_class: equity 17/36, crypto **0/36**
- by_vol_regime: low 10/24, mid 2/24, high 5/24
- best_cell: emv_period=10, max_hold_days=10, SPY, low-vol, Sharpe=2.79
- worst_cell: emv_period=14, max_hold_days=10, SPY, mid-vol, Sharpe=-0.79

## Single-config validation (Step 7)
Config: emv_period=10, trend_window=200, max_hold_days=10. Full sample
2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.268 (pass) | 1.194 (pass) |
| Max drawdown (<=0.25) | 0.144 (pass) | 0.109 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 1.048 (pass) | 0.911 (pass) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 0.75, 3/4 splits positive (pass) | 0.75, 3/4 splits positive (pass) |
| Parameter sensitivity (emv_period in {10,14,21}, rel std <=0.5) | 0.372 (pass) | 0.256 (pass) |
| num_trades | 84 | 70 |

Note: `validators.check_walk_forward`'s `vbt.utils.splitting.RangeSplitter`
is broken in this vectorbt install (same known issue noted in prior
iterations, e.g. 2026-09-04 Williams %R report) -- used a manual 4-equal-slice
fallback computing per-slice Sharpe > 0 via the same vectorbt returns
accessor, consistent with the prior workaround.

## Decision (Step 8)
**Accept for QQQ and SPY** — all 5 standard validators pass on BOTH major
equity index ETFs at the same config (emv_period=10, trend_window=200,
max_hold_days=10), which is broader than most accepted strategies in this
log (typically QQQ-only with SPY as a near-miss).
**Reject for crypto** — 0/36 grid cells pass; the volume/box-ratio EMV
formula (tuned on equity OHLCV) does not transfer to 24/7 crypto data,
consistent with nearly every other volume/price-oscillator strategy tested
in this repo.
