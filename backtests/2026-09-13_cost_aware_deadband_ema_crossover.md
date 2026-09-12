# Cost-aware deadband EMA-crossover momentum

**Strategy file:** `strategies/2026-09-13_cost_aware_deadband_ema_crossover.py`
**Hypothesis id:** 2026-09-13-040

## Source

Bysik & Slepaczuk, "Machine Learning-Based Bitcoin Trading Under
Transaction Costs: Evidence From Walk-Forward Forecasting" (arXiv:2606.00060,
May 2026), read this iteration via browser_exec. The paper's ML forecasting
pipeline (XGBoost/LSTM/iTransformer) is out of scope for one iteration, but
its key generalizable finding is extracted and tested here: "naive
sign-based strategies fail once transaction costs of ten basis points are
imposed. A cost-aware execution filter, which prevents trades only when
the forecast magnitude exceeds a transaction-cost-based threshold, sharply
reduces turnover and restores profitability."

Applied to a plain EMA fast/slow crossover (isolating the deadband
mechanism as the only new variable): a crossover flip is only ACTED ON
when the normalized crossover margin `|ema_fast - ema_slow| / close`
clears `deadband_threshold`; otherwise the previous position is held.

## Grid test (Step 6)

`deadband_threshold` in [0.0, 0.005, 0.015] x `ema_slow` in [26, 50],
equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3 -> 72
cells.

- pass_fraction: 0.292 (21/72)
- by_asset_class: equity 18/36, crypto **3/36** (notably nonzero -- unusual
  for a plain crossover-family strategy in this repo)
- by_vol_regime: low 15/24, mid 6/24, high 0/24

## Single-config validation (Step 7)

Per-symbol fine parameter search (ema_fast x ema_slow x deadband_threshold):

**QQQ** (ema_fast=12, ema_slow=100, deadband_threshold=0.0 -- i.e. the
deadband itself ends up NOT binding at the best config, but the search
included deadband values):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.304 | >=1.0 | Yes |
| Max drawdown | 0.183 | <=0.25 | Yes |
| TC survival (net Sharpe, 10bps/trade, 9 trades) | 1.295 | >=0.5 | Yes |
| Walk-forward (4 splits) | 1.0 (4/4) | >=0.75 | Yes |
| Parameter sensitivity (rel std, 5-combo local sweep) | 0.070 | <=0.5 | Yes |

**SPY** (ema_fast=8, ema_slow=26, deadband_threshold=0.0):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.211 | >=1.0 | Yes |
| Max drawdown | 0.129 | <=0.25 | Yes |
| TC survival (net Sharpe, 10bps/trade, 31 trades) | 1.161 | >=0.5 | Yes |
| Walk-forward (4 splits) | 1.0 (4/4) | >=0.75 | Yes |
| Parameter sensitivity (rel std, 5-combo local sweep) | 0.038 | <=0.5 | Yes |

Note: BTC/USDT and ETH/USDT full-sample sweeps found high raw Sharpe (up
to 1.23) at deadband_threshold=0.005, but max drawdown fails decisively
(BTC: 0.598 vs 0.25 cap) -- the crypto candidates from the grid's 3/36
"passing cells" are narrow per-vol-regime slices, not full-sample passes.

## Outcome

**Accepted for QQQ and SPY** (per-symbol tuned EMA-crossover parameters;
deadband_threshold=0.0 at the best full-sample configs for both symbols,
meaning the deadband concept itself did not turn out to be the binding
improvement here -- the accepted edge is standard EMA-crossover momentum).
Crypto (BTC/USDT, ETH/USDT) rejected on full-sample MDD despite promising
grid-level Sharpe in some vol-regime slices.
