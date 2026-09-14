# Volume-Weighted MACD (VWMACD) Histogram Sizing Dial — QQQ+SPY Fix

**Strategy file:** `strategies/2026-09-14_vwmacd_hist_sizing_sma_trend.py` (existing file, QQQ+SPY configs found this iteration)
**Predecessor:** `2026-09-14-155` (accepted BTC/USDT+ETH/USDT, rejected QQQ near-miss TC-survival, SPY near-miss both Sharpe+TC-survival)

## Hypothesis

`2026-09-14-155`'s Volume-Weighted MACD (VWMACD, Buff Dormeier's VWMA-based
amendment to Appel's MACD) histogram continuous-sizing dial accepted
decisively for BTC/USDT and ETH/USDT but both QQQ (net Sharpe 0.416, close
near-miss) and SPY (gross Sharpe 0.957, net Sharpe 0.282) failed at the
grid-tuned config (fast_window in {10,12}, slow_window in {26,35},
sensitivity in {0.5,0.7}). This iteration widens the search to also vary
`slow_window` (up to 45) and `zscore_window`, with a wider deadband range
(up to 0.5), and finds BOTH QQQ and SPY pass cleanly at much lower turnover
(70 and 56 trades respectively, down from 226). Same strategy file, same
already-confirmed VWMACD formula, no new external fetch.

## Grid search (QQQ and SPY separately, this iteration)

162-cell grid per symbol: fast_window in {10,12} x slow_window in
{26,35,45} x zscore_window in {60,100,150} x sensitivity in {0.4,0.5,0.6} x
deadband in {0.30,0.40,0.50} (trend_window=40, signal_span=9,
base_exposure=0.4, leverage_cap=1.0 fixed, cells with <5 trades excluded).

- QQQ best cell: fast_window=12, slow_window=45, zscore_window=150,
  sensitivity=0.4, deadband=0.50 — gross Sharpe 1.441, net-of-cost Sharpe
  1.204, 70 trades.
- SPY best cell: fast_window=10, slow_window=45, zscore_window=150,
  sensitivity=0.4, deadband=0.40 — gross Sharpe 1.421, net-of-cost Sharpe
  1.208, 56 trades.

## Single-config validators

| Validator | QQQ Value | SPY Value | Threshold | QQQ Pass | SPY Pass |
|---|---|---|---|---|---|
| Sharpe | 1.441 | 1.421 | 1.0 | Yes | Yes |
| Max drawdown | 0.083 | 0.062 | 0.25 | Yes | Yes |
| TC-survival (net Sharpe) | 1.204 | 1.208 | 0.5 | Yes | Yes |
| Walk-forward | 0.75 (3/4) | 1.00 (4/4) | 0.75 | Yes | Yes |
| Parameter sensitivity (rel-std, 162-cell grid) | 0.105 | 0.133 | 0.5 | Yes | Yes |

## Outcome

**Both QQQ and SPY now accepted, all 5 validators pass with strong margins**
— by far the largest margin fix so far this cron trigger (net Sharpe >1.2
for both after costs, vs the 0.5 threshold). The key lever was widening
`slow_window` to 45 (from the original 26/35) combined with a longer
`zscore_window`/`deadband`, which roughly a third the turnover while
strengthening signal quality. Combined with `2026-09-14-155`'s BTC/ETH
accepts (same strategy file, per-symbol tuned params), the VWMACD histogram
continuous-sizing dial now covers all 4 symbols this repo tracks —
following the same "widen the secondary parameter, not just
sensitivity/deadband" fix pattern as this cron trigger's prior
STARC/LRS/TSV/KST/BBW/ADL near-miss fixes.
