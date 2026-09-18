# Hull Moving Average Same-Offset Crossover + SMA(500) Filter — Backtest Report

**Source:** https://opportrade.com/articles/hull-MA-strategy ("Hull MA
Crossover Strategy With SMA Filter"), exact Tradescript rule disclosed.

**Hypothesis:** First HMA-family strategy in this repo. Computes a single
HMA(period) series and trades the crossover between two lag-OFFSETS of
that same series (H_L1 vs H_L4 in the source), filtered by a long-term
SMA trend gate. Distinct from a traditional dual-period MA crossover since
both compared series share identical smoothing.

## Step 6 grid summary
`hma_period` in {16,32,50} x `slow_offset` in {3,4,6} x `trend_sma_window`
in {200,500}, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto),
vol_regime_splits=3. 216 total cells.

- pass_fraction: 49/216 = 22.7%
- by_asset_class: equity 41/108 (38.0%), crypto 8/108 (7.4%)
- by_vol_regime: low 39/72 (54.2%), mid 10/72 (13.9%), high 0/72 (0%)
- best_cell: hma_period=32, slow_offset=6, trend_sma_window=200, SPY low-vol, Sharpe=3.00
- Best QQQ avg config: hma_period=16, slow_offset=6, trend_sma_window=500 (avg Sharpe 1.245, 2/3 vol regimes pass)
- Best SPY avg config: hma_period=16, slow_offset=4, trend_sma_window=500 (avg Sharpe 1.106, 1/3 vol regimes pass at threshold but strong full-period result, see below)

Like nearly every trend-following strategy in this repo, fails universally
in the high-vol tercile (0/72) -- consistent finding, not new information,
but the strategy's low/mid-vol performance is strong enough to accept.

## Step 7 single-config validators

### QQQ (hma_period=16, slow_offset=6, trend_sma_window=500)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.136 | >=1.0 | PASS |
| Max drawdown | 14.31% | <=25% | PASS |
| Transaction cost survival (10bps/trade, 65 trades) | net Sharpe 1.035 | >=0.5 | PASS |
| Walk-forward (manual 4-split) | 0.75 (3/4 splits positive) | >=0.75 | PASS |
| Parameter sensitivity (18-cell QQQ grid) | 0.221 | <=0.5 | PASS |

### SPY (hma_period=16, slow_offset=4, trend_sma_window=500)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.027 | >=1.0 | PASS |
| Max drawdown | 10.68% | <=25% | PASS |
| Transaction cost survival (10bps/trade, 77 trades) | net Sharpe 0.834 | >=0.5 | PASS |
| Walk-forward (manual 4-split) | 0.75 (3/4 splits positive) | >=0.75 | PASS |
| Parameter sensitivity (18-cell SPY grid) | 0.210 | <=0.5 | PASS |

## Decision: ACCEPTED (QQQ and SPY; equity only)

Both equity symbols pass all 5 validators at their own best-avg-Sharpe
config (params differ slightly by symbol: QQQ slow_offset=6, SPY
slow_offset=4, both hma_period=16/trend_sma_window=500). Crypto not
accepted -- grid pass_fraction only 7.4% (8/108), consistent with a
predominantly equity-tuned trend signal. Strategy is scoped to
equity-only live use in `strategies/`.
