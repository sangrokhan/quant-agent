# Backtest Report: TII Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_tii_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-103

## Hypothesis

Trend Intensity Index (M.H. Pee, 2002): TII = 100*SDPOS/(SDPOS+SDNEG),
RSI-style ratio of positive/negative SMA-deviation sums, bounded [0,100].
Confirmed via DuckDuckGo HTML SERP (tradingpedia.com, stockmaniacs.net,
pineify.app).

Repo has 4+ prior TII entries, all binary midline/extreme-threshold
crossovers, all rejected. This iteration reframes TII as a CONTINUOUS
SIZING dial within an SMA(trend_window) uptrend gate, following the
ADX/CHOP/VHF/PFE pattern.

## Grid test summary (Step 6)

`param_grid={tii_sensitivity: [0.4,0.6,0.8], deadband: [0.15,0.20,0.25]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=41, pass_fraction=0.380
- by_asset_class: equity 22/54 (0.41), crypto 19/54 (0.35)
- by_vol_regime: low 36/36 (1.00), mid 5/36 (0.14), high 0/36 (0.00)
- per-symbol: QQQ 13/27, SPY 9/27, BTC/USDT 10/27 (best in HIGH-vol
  regime, unusual), ETH/USDT 9/27

## Single-config validator results (Step 7)

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Verdict |
|---|---|---|---|---|---|
| QQQ | sens=0.4, db=0.15 | 0.630 (**FAIL**) | 21.10% (pass) | 0.311 (**FAIL**) | **REJECT** |
| SPY | sens=0.8, db=0.20 | 0.655 (**FAIL**) | 17.10% (pass) | 0.356 (**FAIL**) | **REJECT** |
| BTC/USDT | sens=0.8, db=0.25 | 1.254 (pass) | 45.23% (**FAIL**, decisive) | 1.183 (pass) | **REJECT** (MDD) |

## Decision

**Reject across all symbols.** Unlike the prior sizing-dial family
(ADX/CHOP/VHF/PFE/TSI/etc.) which all cleared 1+ symbols cleanly, TII's
best-grid-cell equity Sharpe (0.63-0.65) is well below the 1.0 threshold at
the grid's own best-cell config -- not a cost-drag or deadband-tunable
near-miss like BOP/PFE were, but a genuinely weak gross return profile.
Crypto's MDD (45.2%) is the worst of any strategy this cron trigger, far
beyond what widening the deadband typically fixes (per BOP/PFE experience,
worth ~5-10pp of MDD reduction at most, not the ~20pp needed here). This is
the first clean rejection in the continuous-sizing-dial reframing campaign
this cron trigger (VZO/ADX/DMI-diff/CHOP/Vortex/TSI/RMI/SMI/BOP/IMI/VHF/PFE
all accepted at least one symbol) -- useful negative evidence that not every
previously-rejected binary-threshold indicator becomes viable once
reframed as a continuous dial; TII's SMA-deviation-sum construction appears
to carry genuinely weaker signal than the range/path-length or
double-smoothed-momentum constructions that worked elsewhere this trigger.
