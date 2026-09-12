# Backtest Report: Apirine Higher High/Lower Low Stochastic (HHLLS) Crossover

**Strategy file:** `strategies/2026-09-12_apirine_hhlls_crossover.py`
**Hypothesis ID:** 2026-09-12-194
**Source:** Vitali Apirine, "Higher Highs & Lower Lows", Stocks & Commodities
V.34:02 (Feb 2016), fully disclosed MetaStock code extracted directly from
PDF (forex-station.com mirror).

## Hypothesis

HHS (Higher High Stochastic) and LLS (Lower Low Stochastic): both 20-day
EMAs of a bounded 0-100 ratio measuring how fresh recent higher-highs
(resp. lower-lows) are relative to their own 20-day range. Source's own
two-stage "emerging trend" rule: (1) HHS crosses above LLS, (2) HHS > 50
AND LLS < 50. Long entry requires both conditions; exit on the mirror
bearish condition.

## Grid test (Step 6): `lookback_window` in {10, 20, 30}, QQQ/SPY equity +
BTC/USDT, ETH/USDT crypto, vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.222** (8/36 cells) -- moderate, better than
  several other iterations this trigger.
- **By asset class:** equity 8/18; crypto 0/18 (decisive fail).
- **By vol regime:** low 6/12, mid 1/12, high 1/12 -- edge concentrated in
  low-vol regime.
- **Best cell:** QQQ, low-vol, `lookback_window=10` (Sharpe 2.92).
- **Worst cell:** QQQ, high-vol, `lookback_window=30` (Sharpe -0.92).
- Best average-Sharpe configs: QQQ `lookback_window=10` avg 1.591; SPY
  `lookback_window=10` avg 1.052 (both averaged across vol terciles on
  the 2019-2026 grid window).

## Single-config validation (Step 7), full 2018-2026 sample

| Symbol | Params | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param-sens rel.std | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | lookback_window=10 | 1.042 (pass) | 0.257 (**FAIL**, narrow, thr 0.25) | 0.980 (pass) | 1.00 (pass) | 0.334 (pass) | 54 |
| SPY | lookback_window=10 | 0.751 (**FAIL**) | 0.168 (pass) | 0.654 (pass) | 0.75 (pass, exact threshold) | 0.078 (pass) | 61 |

Also checked QQQ `lookback_window=20` (Sharpe 0.769, fails) and SPY
`lookback_window=30` (Sharpe 0.838, fails) as alternates with better
grid-window averages -- neither improves on the near-miss QQQ config.

## Decision: **REJECT** (both QQQ near-miss MDD, SPY Sharpe fail; crypto
decisive fail)

QQQ's best config (`lookback_window=10`) passes 4 of 5 validators cleanly
but narrowly misses the max-drawdown threshold (0.257 vs 0.25, a 0.7pp
overshoot) -- closer to acceptance than most rejections this trigger, but
still a fail per the strict threshold. SPY does not find a config that
clears the Sharpe bar across the full sample despite promising grid-window
averages. Crypto rejected decisively at the grid stage (0/18).
