# Backtest Report: PJK Channel "Trade in the Bands" (Kaufman Rule 3)

**Strategy file:** `strategies/2026-09-18_pjk_channel_trade_in_bands.py`
**Date:** 2026-09-18
**Hypothesis:** Per Perry Kaufman's TASC 5/2025 "PJK Channels" article
(EasyLanguage disclosed at
https://traders.com/Documentation/FEEDbk_docs/2025/05/TradersTips.html,
read via browser_exec fallback -- web_extract's DDGS backend cannot
extract page content), Rule 3 of the three disclosed rules trades *within*
a rolling-OLS-regression channel: long entries are gated by a positive
regression slope AND price pulling back to within a `zone` fraction of the
lower band (pullback-in-uptrend, not breakout); exits trigger at a
`zone`-distance price target near the upper band, or immediately if slope
flips non-positive. Distinct from the already-tested/accepted
2026-09-12-188 "Inside Channel" (financial-hacker.com writeup), which has
no slope-direction gate and trades both bands symmetrically regardless of
trend.

## Grid summary (Step 6)

Parameter grid: `period` in {30,40,50}, `zone` in {0.15,0.20,0.30};
symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3
(low/mid/high realized-vol terciles); sample 2016-01-01 to 2026-09-01.

- Total cells: 108, passed: 30, **pass_fraction = 0.278**
- By asset class: equity 25/54 passed; crypto 5/54 passed
- By vol regime: low 16/36, mid 14/36, **high 0/36** (strategy fails
  decisively in high-vol regimes across both asset classes)
- Best cell: equity SPY low-vol, period=50/zone=0.3, Sharpe=2.17
- Worst cell: crypto BTC/USDT mid-vol, period=50/zone=0.3, Sharpe=-1.08
- Averaging equity-only cells by (period, zone): best average was
  **period=50, zone=0.3** (mean Sharpe 1.12 across its 6 equity cells)

## Single-config validation (Step 7): period=50, zone=0.3

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample, 2016-2026) | 0.896 | 0.786 | >= 1.0 | **FAIL both** |
| Max drawdown | 0.224 | 0.179 | <= 0.25 | PASS both |
| Net Sharpe after costs (5bps/trade) | 0.831 | 0.704 | >= 0.5 | PASS both |
| Walk-forward (4-split, manual -- see note) | 3/4 splits positive | 3/4 splits positive | >= 0.75 frac | PASS both |
| Parameter sensitivity (9-combo local sweep, relative std) | 0.156 | 0.162 | <= 0.5 | PASS both |

Note: `validators.check_walk_forward` errors on the installed vectorbt
version (`vbt.utils.splitting.RangeSplitter` no longer exists -- same
break seen in prior iterations, e.g.
`scratch_results/validate_result_cybernetic_osc.json`). Used a manual
4-way contiguous-chunk walk-forward split with the same pass criterion
(>=75% of splits Sharpe>0) as a substitute.

## Decision: REJECT

Full-sample Sharpe (QQQ 0.896, SPY 0.786) misses the 1.0 threshold on both
primary equity symbols despite decent MDD/cost-survival/walk-forward/
parameter-stability. The grid confirms this is a real, if narrower-than-
hoped, effect: strong in low/mid vol regimes (esp. the observed SPY
low-vol Sharpe 2.17 best cell) but the *high-vol tercile fails completely
(0/36 cells)* across both asset classes -- the slope-gated pullback logic
apparently gets whipsawed badly once volatility rises, dragging the
full-sample blended Sharpe below the bar. Crypto is decisively rejected
(5/54 pass). A future iteration could revisit this with an explicit
vol-regime gate (flat during high-vol tercile) as a "fix" attempt, which
is exactly the kind of low-vol-only honest-scope finding this repo's
notes convention is meant to preserve.

Strategy file and this report are kept as a rejected-attempt record.
