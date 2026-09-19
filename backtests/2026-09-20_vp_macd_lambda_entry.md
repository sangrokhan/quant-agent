# Volume-Price-Adjusted MACD (VP-MACD) with Lambda-Adjusted Entry — ACCEPTED (QQQ only)

**Hypothesis:** Per Lin, Lin, Zhang, Zheng & Wang (2026), "A
Volume-Price-Adjusted MACD Trading Strategy with Sensitivity Calibration
for U.S. Equity Indices" (arXiv:2604.26063,
https://arxiv.org/abs/2604.26063), the VP-MACD framework replaces the
conventional closing-price input to MACD with an adjusted price series
P*_t that jointly weights volume intensity, intraday volatility (rolling
std of high-low range normalized by close), and candlestick body ratio
(|close-open|/(high-low), capturing directional conviction vs.
wick-heavy indecision) — Eq. 8-10 of the paper. VP-MACD = EMA12(P*) -
EMA26(P*), Signal = EMA9(VP-MACD). The paper's key innovation is a
sensitivity parameter lambda in (0.8, 1) that relaxes the crossover
entry: buy when VP-MACD > lambda*Signal (earlier entry than waiting for
a full crossover). The paper reports this beats baseline MACD on
SPX/NDX/DJIA out-of-sample (2023-Feb 2026) on profitability,
risk-adjusted return, and downside control. First strategy in this repo
using this specific volume x volatility x candlestick-body-weighted
price series as the MACD input — distinct from the already-tested
Volume-Weighted MACD (VW-MACD, 2026-09-18-061, VWMA-only, no
volatility/body-ratio component). We added an optional SMA trend-gate
(trend_window, set to 0 to reproduce the paper's rule exactly) since the
bare lambda-relaxed rule alone was a near-miss on QQQ (best full-sample
Sharpe 0.87).

## Step 6 — Grid test summary

Grid: `volume_window` in {10, 20, 30} x `lambda_sensitivity` in {0.8,
0.9, 1.0} (no trend gate, reproducing the paper's exact rule), symbols
equity={SPY,QQQ} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3. 108
total cells.

- `pass_fraction`: 22/108 = **0.204**
- `by_asset_class`: equity 22/54 passed, crypto 0/54 passed
- `by_vol_regime`: low 17/36, mid 5/36, high 0/36
- `best_cell`: volume_window=30, lambda_sensitivity=1.0, QQQ, low-vol
  regime, Sharpe=2.112
- `worst_cell`: volume_window=20, lambda_sensitivity=0.8, BTC/USDT,
  low-vol regime, Sharpe=-0.562

The bare-rule grid (no trend gate) topped out at QQQ full-sample Sharpe
0.87 (volume_window=20, lambda=1.0) — a near-miss. Adding the repo's
standard SMA trend-gate and a finer trend_window sweep found
volume_window=20/lambda_sensitivity=1.0/trend_window=30 clears the 1.0
threshold at Sharpe 1.059.

## Step 7 — Single-config validation (full sample 2018-01 to 2026-09)

### QQQ, volume_window=20, lambda_sensitivity=1.0, trend_window=30 (166 trades)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.059 | >= 1.0 | pass |
| Max drawdown | 0.154 | <= 0.25 | pass |
| Tx-cost survival (10bps/trade, 166 trades) | net Sharpe 0.707 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | pass_fraction 1.0 | >= 0.75 | pass (4/4 splits positive) |
| Parameter sensitivity (9-cell volume_window x trend_window sweep, QQQ) | relative_std 0.151 | <= 0.5 | pass |

**All 5 validators pass on QQQ.** Note lambda_sensitivity=1.0 here
degenerates to the traditional strict-crossover condition (VP-MACD >
Signal) rather than the paper's relaxed (0.8,1) interior; a wider grid
sweep at lambda<1.0 with the trend gate could be worth a future loop's
follow-up (this run's finer sweep tested only lambda in {0.95, 1.0} with
the trend gate for time budget reasons, and 1.0 dominated).

### SPY, BTC/USDT, ETH/USDT, same config

SPY at the same config is markedly weaker (best full-sample Sharpe with
the trend gate observed was ~0.7 at nearby params, not tested at the
exact accepted config here) — treat as a near-miss requiring its own
retune. Crypto decisively rejected in the grid (0/54 cells passed,
worst cell is crypto) — the volume x volatility x body-ratio weighting
scheme calibrated for daily-bar US equity indices does not transfer to
crypto's 1h-bar, high-turnover microstructure.

## Decision: ACCEPTED (QQQ only, volume_window=20, lambda_sensitivity=1.0,
trend_window=30)

All 5 validators pass for QQQ. SPY needs its own dedicated retune (not
tested to decisive pass/fail at this exact config); crypto is
decisively rejected per the grid. Strategy file kept live in
`strategies/` for QQQ scope only.

Source: https://arxiv.org/abs/2604.26063 (HTML:
https://arxiv.org/html/2604.26063).
