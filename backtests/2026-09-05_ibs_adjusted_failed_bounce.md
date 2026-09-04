# IBS "Adjusted Failed Bounce" dip-buy (Rob Hanna, adapted)

**Hypothesis:** Per CoinGecko's summary of Rob Hanna's "Adjusted Failed
Bounce" strategy (IBS = (Close-Low)/(High-Low)), a dead-cat-bounce pattern
in an established short-term downtrend is a mean-reversion long entry. Rule:
(1) yesterday's IBS >= ibs_threshold (0.6), (2) yesterday's low < lowest low
of the `lookback` days before yesterday, (3) today's close < yesterday's
close (bounce fails), (4) exit when close > highest high of the `lookback`
days before entry, or a max_hold_days time-stop backstop.

Source: https://www.coingecko.com/learn/internal-bar-strength-ibs

Novelty: distinct from all prior IBS-family strategies in this repo
(2026-09-04-089/158/159/164, all simple IBS threshold-cross or averaged-IBS
entries) — this is a structurally different 4-condition failed-bounce
pattern.

## Step 6 — Grid summary

Grid: `ibs_threshold in {0.5,0.6,0.7}`, `lookback in {3,5,7}`,
`max_hold_days in {10,15}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 144 total cells.

- pass_fraction: 0.0625 (9/144) -- weak from the start
- by_asset_class: equity 9/108 passed; crypto 0/36 (ccxt loader tz-aware
  Timestamp error, known issue)
- by_vol_regime: low 7/36, mid 0/36, high 2/36
- best_cell: ibs_threshold=0.6, lookback=3, max_hold_days=15, SPY, low-vol,
  Sharpe 1.59

## Step 7 — Single-config validation (ibs_threshold=0.6, lookback=3, max_hold_days=15)

| Metric | SPY | QQQ |
|---|---|---|
| Sharpe (>=1.0) | 0.198 FAIL | 0.205 FAIL |
| Max drawdown (<=0.25) | 0.356 FAIL | 0.352 FAIL |
| Net-of-cost Sharpe (>=0.5, 10bps/trade) | 0.136 FAIL | 0.152 FAIL |
| Param sensitivity relative_std (<=0.5, lookback in {3,5,7}) | 0.705 FAIL | 0.313 PASS |
| num_trades | 52 | 56 |
| Walk-forward | not run — same vectorbt limitation as prior entries this run. |

## Step 8 — Decision

**Rejected, decisively.** Full-sample Sharpe near-zero on both symbols
(0.198/0.205), MDD breaches the 0.25 threshold on both (0.356/0.352 —
worse than most other strategies tested this run), net-of-cost Sharpe fails
badly, and SPY additionally fails parameter sensitivity (relative_std
0.705). Unlike most rejections this run (which fail full-sample Sharpe
despite a stable/isolated grid signal), this pattern also fails MDD
outright and shows real parameter instability on SPY — a genuinely weak,
overfitting-prone setup, not just a diluted-by-full-sample-averaging edge.
Crypto rejected due to the known ccxt loader tz-aware Timestamp bug (0
usable cells).
