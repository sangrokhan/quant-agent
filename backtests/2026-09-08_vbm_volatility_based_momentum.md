# VBM (Volatility-Based Momentum) Threshold Trend — Backtest Report (2026-09-08)

## Hypothesis
Per Steve Roehling's "A Volatility Based Momentum Indicator for Traders"
(Medium): VBM(n,v) = (Close - Close[n periods ago]) / ATR(v periods) --
raw price difference divided by ATR, expressing momentum in "multiples of
volatility" (MoV) rather than percentage terms. Long entry when
VBM(momentum_window=44, atr_window=65) >= entry_threshold; exit on VBM
falling below exit_threshold or a max_hold_days time-stop.

Distinct from 2026-09-08-065 (rejected: return/realized-vol-of-returns
ratio, a Sharpe-like normalization) -- VBM instead divides a raw price
LEVEL difference by ATR, a range-based volatility proxy.

Source: https://medium.com/@sroehling/a-volatility-based-momentum-indicator-for-traders-250957de978d

## Grid test summary (momentum_window=[14,22,44] x entry_threshold=
[0.5,1.0,1.5] x exit_threshold=[0.0,-0.5], QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 2018-2026)

- total_cells=216, passed=56, pass_fraction=0.259
- by_asset_class: equity 56/108, crypto 0/108 (decisive crypto rejection)
- by_vol_regime: low 36/72, mid 18/72, high 2/72 (edge concentrated in
  low/mid-vol, thin but present in high-vol)
- best_cell: QQQ low-vol, momentum_window=44/entry_threshold=0.5/
  exit_threshold=0.0, Sharpe 2.84
- worst_cell: QQQ high-vol, Sharpe -1.08

## Single-config validators (momentum_window=44, entry_threshold=0.5,
exit_threshold=0.0)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full-sample) | 1.167 PASS | 0.793 FAIL | >= 1.0 |
| Max drawdown | 0.209 PASS | 0.212 PASS | <= 0.25 |
| TC survival (5bps/trade, net Sharpe) | 1.124 PASS (80 trades) | 0.733 PASS (82 trades) | >= 0.5 |
| Walk-forward (4-split manual contiguous) | 4/4 PASS | 4/4 PASS | >= 0.75 |
| Parameter sensitivity (relative std, 4-point sweep) | 0.072 PASS | 0.169 PASS | <= 0.5 |

Crypto (BTC/USDT, ETH/USDT): rejected decisively, 0/108 grid cells passed.

## Decision: ACCEPT (QQQ only)

QQQ passes all five validators comfortably (best clean Sharpe pass this
strategy family). SPY fails full-sample Sharpe (0.793) despite passing
MDD/TC/WF/param-sensitivity -- keep this strategy live for QQQ only.
Crypto is decisively out of scope (0/108 grid cells).
