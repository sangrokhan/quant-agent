# Backtest Report: Bollinger %B Mean Reversion (Larry Connors), SPY

**Strategy file:** `strategies/2026-09-04_bb_pctb_meanrev_connors.py`
**Hypothesis ID:** 2026-09-04-107
**Source:** https://www.quantifiedstrategies.com/2-simple-mean-reversion-trading-strategies/

## Hypothesis

Larry Connors' %B strategy: in an uptrend (close > 200d SMA), a close where
Bollinger %B drops below 0 (price pierces below the lower band) signals a
short-term overextension worth a mean-reversion long, exit on a quick
recovery. Source's own SPY backtest (1993-present): 63 trades, 89% win
rate, profit factor 3, only 4% time invested, MDD -8%.

## Single-config validators (primary config: bb_std=2.0, exit_pct_b=0.8, SPY, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.59 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.287 | ≤ 0.25 | **FAIL** |
| Transaction cost survival (10bps/trade, 21 trades) | net Sharpe 0.57 | ≥ 0.5 | PASS |

## Step 6 grid summary (bb_std∈{1.5,2.0} × exit_pct_b∈{0.5,0.8}, SPY+QQQ+BTC/USDT+ETH/USDT, vol_regime_splits=3)

- Total cells: 48, passed: 3, **pass_fraction = 0.0625** (very weak)
- By asset class: equity 3/24, crypto 0/24.
- By vol regime: low 1/16, mid 2/16, high 0/16.
- Best cell: bb_std=2.0, exit_pct_b=0.8, SPY, mid-vol, Sharpe 1.23.

## Decision: REJECTED

Grid pass_fraction is very weak (6.25%) and the full-sample Sharpe (0.59)
and MDD (0.287) both clearly fail on the best config. On this repo's
2019-2026 sample (vs. the source's much longer 1993-present sample), the
%B<0 entry trigger doesn't fire often/cleanly enough to reproduce the
source's reported edge — consistent with several other Connors/QuantifiedStrategies
mean-reversion variants already tested in this repo underperforming on the
shorter, more recent sample window (e.g. RSI2 -005). No walk-forward/param-sensitivity
run given the weak headline result (light-workload judgment call, not needed
to confirm rejection).
