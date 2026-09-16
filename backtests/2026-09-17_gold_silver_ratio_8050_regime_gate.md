# Backtest report: Gold-Silver Ratio 80/50 rule regime gate

**Strategy file:** `strategies/2026-09-17_gold_silver_ratio_8050_regime_gate.py`

## Hypothesis

Per the widely-cited "80/50 rule" for gold-silver ratio trading (confirmed
via Google SERP synthesis this iteration -- CBS News/SprottMoney/JM
Bullion/GoldSilver/AuAg Funds/ICICI Direct all independently describe the
same numeric rule: ratio > 80 = gold overvalued vs silver, rotate back at
ratio near 50), apply the ratio as a risk-on/risk-off regime gate (flat
above 80, re-enabled at/below 50, hysteresis in between) on a primary
asset's SMA trend-following signal.

## CRITICAL METHODOLOGICAL FINDING (invalidates the intended test)

The implementation computed `ratio = GLD.close / SLV.close` (ETF **share
prices**), NOT the true gold:silver **ounce** price ratio the 80/50 rule
actually refers to. GLD/SLV share prices embed fractional-ounce structuring
(GLD ~1/10 oz gold per share; SLV's per-share silver backing differs from
1oz), so the ETF price ratio trades in an entirely different numeric range
(historically **4.68 to 12.55**, mean 8.28, over 2019-2026) than the true
ounce ratio the source's 80/50 levels apply to (which trades in the 50-100+
range). Consequence: `high_thresh=80` / `low_thresh=50` (and every other
threshold value tested in [70,75,80,85] x [45,50,55]) **never fires** across
the entire 2019-2026 sample -- the risk-on state never flips false. The
"regime gate" is a permanent no-op, and every grid cell above is actually
just measuring a bare `SMA(trend_window)` trend-following baseline with the
gold/silver machinery contributing nothing.

## Grid test summary (Step 6) -- results are for the degenerate (gate-inert) baseline

`param_grid={"trend_window": [20,40,60], "high_thresh": [75,80,85]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 36, pass_fraction: 33.3% (equity 27/54,
  crypto 9/54) -- but since `high_thresh` never actually varies the signal,
  this 3x3 grid is really only a 1x3 (trend_window-only) grid measured 3x
  redundantly.
- Manual threshold sweep confirmed: varying trend_window in [30,50,70,100]
  and high/low_thresh in [70..85]/[45..55] shows Sharpe is IDENTICAL across
  every threshold combination for a fixed trend_window -- direct proof the
  gate never fires.
- Best config trend_window=30 reaches QQQ Sharpe 1.215, SPY Sharpe 1.032
  (still passes since it's really just a tight-window SMA trend strategy,
  a construction already extensively tested/accepted in this repo under
  many names).

## Decision: REJECTED

Rejected on methodological grounds, not performance grounds: the actual
gold-silver-ratio-regime-gate hypothesis was never genuinely tested because
the threshold levels were calibrated to the wrong price scale (ETF share
price ratio vs. true ounce ratio). What was measured is a bare SMA
trend-following baseline already covered many times over in this repo's
knowledge base (not a novel finding). Logging this as a rejection with the
scale-mismatch root cause documented so a future iteration attempting this
angle again knows to either (a) rescale thresholds to the ETF price ratio's
own historical percentile distribution (e.g. use the ratio's own trailing
90th/10th percentile as calibration, not the literal 80/50 spot-ounce
numbers), or (b) source true XAU/XAG spot-ounce price data instead of
GLD/SLV ETF shares if available via this repo's loaders (currently it is
not -- data/loaders.py only supports yfinance equity/ETF tickers and ccxt
crypto pairs, no direct commodities spot feed).
