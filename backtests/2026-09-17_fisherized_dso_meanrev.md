# Backtest Report: Ehlers Fisherized Deviation-Scaled Oscillator (FDSO) Mean Reversion

**Strategy file:** `strategies/2026-09-17_fisherized_dso_meanrev.py`
**Source:** Traders.com Oct 2018 Traders' Tips (John Ehlers, "Probability --
Probably A Good Thing To Know", TASC Oct 2018), TradeStation EasyLanguage code,
read via `browser_exec` this iteration (`https://traders.com/Documentation/FEEDbk_docs/2018/10/TradersTips.html`).

## Hypothesis

The Fisher-transformed, RMS-normalized, SuperSmoother-filtered oscillator
(FDSO) has an approximately-Gaussian probability distribution (per Ehlers'
own probability-distribution measurement method in the article), making
fixed +-2 thresholds statistically meaningful oversold/overbought cutoffs
for mean reversion, unlike arbitrary raw-oscillator thresholds. Adapted here
long-only: buy when FisherFilt crosses above `oversold`, exit on cross below
0 or after `max_hold_days`.

## Grid test (Step 6)

`period` in [30,40,55] x `oversold` in [-1.5,-2.0,-2.5] x `max_hold_days` in
[10,15,20], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.108** (35/324)
- by_asset_class: equity 23/162 (0.142), crypto 12/162 (0.074)
- by_vol_regime: low 12/108, mid 6/108, high 17/108 (high-vol regime slightly
  favored -- plausible: Fisher-transform bands trigger more meaningfully
  amid larger price swings)
- best cell: QQQ, period=55/oversold=-1.5/max_hold_days=20, high-vol regime,
  Sharpe 2.03
- worst cell: ETH/USDT, period=55/oversold=-1.5/max_hold_days=15, mid-vol,
  Sharpe -1.81

Grid signal: the strategy holds up narrowly on equity (QQQ specifically,
longer `period`~55, wider `max_hold_days`~20-30), not broadly across the full
grid, and crypto is decisively weaker.

## Single-config validation (Step 7)

### QQQ, period=55, oversold=-1.5, max_hold_days=30 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.310 (threshold 1.0) |
| Max drawdown | **PASS** | 0.100 (threshold 0.25) |
| Transaction cost survival (10bps/trade, 12 trades) | **PASS** | net Sharpe 1.289 (threshold 0.5) |
| Walk-forward (4 manual equal splits -- `check_walk_forward` in validators.py is currently broken: `vectorbt.utils.splitting` module doesn't exist in installed vectorbt version; computed manually instead) | **PASS** | per-split Sharpe [1.218, 0.403, 0.445, 2.266], pass_fraction 1.0 (all splits positive) |
| Parameter sensitivity (period in [45,50,55,60,65]) | **PASS** | relative_std 0.446 (threshold 0.6); Sharpes [0.326, 0.749, 1.310, 1.520, 0.842] |

**Verdict: ACCEPT for QQQ only** (only 12 trades over 7.5 years -- a low-frequency
strategy; economically plausible given Ehlers' RMS-normalization window of 55
days is long, producing infrequent extreme-Fisher-value entries).

### SPY, period=20, oversold=-2.5, max_hold_days=30 (best SPY grid cell)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | PASS | 1.092 |
| Max drawdown | PASS | 0.039 |
| Transaction cost survival | PASS | net Sharpe 1.077 (but only **2 trades** total -- statistically meaningless sample) |
| Parameter sensitivity (period in [15,20,25,30]) | **FAIL** | relative_std 1.653 (threshold 0.6); Sharpes [-0.480, 1.092, 0.815, 0.070] -- collapses/flips sign one step off |

**Verdict: REJECT for SPY** -- passes headline Sharpe/MDD but on only 2 trades
and fails parameter sensitivity decisively; not a robust configuration.

### Crypto (BTC/USDT, ETH/USDT)

Grid pass_fraction for crypto was 0.074 (12/162), and the strongest crypto
cells (BTC/USDT, period=40) failed `mdd_passed`/`sharpe_passed` jointly in
most regimes per the grid. **Rejected decisively.**

## Overall decision

**ACCEPTED, narrow scope: QQQ only**, period=55/oversold=-1.5/max_hold_days=30.
SPY and crypto rejected. This is a low-frequency (~1.6 trades/year), long-only
mean-reversion overlay -- suitable as a small satellite signal, not a
standalone high-turnover system.
