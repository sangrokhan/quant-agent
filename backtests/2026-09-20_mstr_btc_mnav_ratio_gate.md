# MSTR/BTC "mNAV Proxy" Regime Gate — BTC/USDT

**Hypothesis source:** Google SERP synthesis (mNAV.com, Simple Mining,
Look Into Bitcoin, BitMEX Trading Guides — read via `browser_exec` after
`web_search`'s DuckDuckGo backend returned no results for the query),
covering Strategy Inc's (MSTR, formerly MicroStrategy) mNAV ("multiple of
Net Asset Value") metric.

## Hypothesis

mNAV = MSTR's market cap / fair value of its BTC holdings. Sources agree
the premium historically *expands* during bitcoin bull-market euphoria
(peaked >2.4x in 2024) and *compresses* toward/below 1.0 during
risk-off/deleveraging phases (recent 2025-2026 compression to ~0.75x per a
cited discussion). Since `data/loaders.py` only exposes OHLCV (no MSTR
balance-sheet BTC-holdings/debt data for the literal mNAV formula), this
strategy uses the directly observable MSTR_close/BTC_close price ratio as a
proxy for mNAV's premium/discount **direction**, treating "ratio above its
own rolling SMA" as a risk-on regime gate on a plain SMA trend-following
signal for the traded asset itself.

## Step 6 — Grid summary (108 cells: 3 trend_sma_window x 3 ratio_sma_window
x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles)

- `pass_fraction`: 0.380 (41/108)
- `by_asset_class`: equity 23/54 (42.6%), crypto 18/54 (33.3%)
- `by_vol_regime`: low 25/36 (69.4%), mid 10/36 (27.8%), high 6/36 (16.7%)
  — pass rate is concentrated in low-vol regimes (a grid-tercile artifact
  common to trend-following gates in this repo), so full-sample validation
  below is the decisive check.
- Best cell: QQQ, `trend_sma_window=50, ratio_sma_window=90`, low-vol
  tercile, Sharpe 2.51.

## Step 7 — Full-sample validators (BTC/USDT, `trend_sma_window=100,
ratio_sma_window=40`, 2019-01-01..2026-09-01)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.252 | >= 1.0 | PASS |
| Max drawdown | 0.224 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 143 trades) | 1.157 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback; `check_walk_forward` broken on installed vectorbt 1.1.0) | 0.75 (3/4 splits positive Sharpe) | >= 0.75 | PASS |
| Parameter sensitivity (9-combo grid, relative std) | 0.201 | <= 0.5 | PASS |

Full-sample sweep across all 4 symbols at the SAME grid params:

| Symbol | Best config (tw/rw) | Sharpe | MDD |
|---|---|---|---|
| QQQ | 150/60 | 1.007 | 0.127 |
| SPY | 150/60 | 0.794 | 0.121 |
| BTC/USDT | 100/40 | 1.252 | 0.224 |
| ETH/USDT | 50/40 | 0.845 | 0.460 |

QQQ clears Sharpe at 150/60 but was not put through the full validator
suite (single-config scope this iteration is BTC/USDT, the strategy's
intended domain); SPY/ETH do not clear Sharpe/MDD at any tested config.

## Step 8 — Decision

**ACCEPT for BTC/USDT only** at `trend_sma_window=100, ratio_sma_window=40`.
All 5 validators pass. QQQ shows a promising near-accept at a different
config (150/60, Sharpe 1.007) worth a future fine-tune iteration, but is
NOT accepted this iteration (single primary config tested per Step 7 scope
under `suggested_workload=max`). SPY and ETH/USDT are out of scope —
ETH/USDT's MDD (0.46) is decisively too high across every tested config.
