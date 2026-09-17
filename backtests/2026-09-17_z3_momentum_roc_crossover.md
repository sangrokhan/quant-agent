# Backtest Report: Ehlers Z3 Double-Differenced Momentum ROC Crossover

**Strategy file:** `strategies/2026-09-17_z3_momentum_roc_crossover.py`
**Source:** easylanguagemastery.com's replication (Jeff Swanson, "Testing the
FM Demodulator Filter") of John Ehlers' TASC Jun 2021 article "Creating More
Robust Trading Strategies With The FM Demodulator" -- specifically the
article's disclosed BASELINE strategy (before the FM-demodulator filter is
applied), read via `browser_exec` this iteration --
`https://easylanguagemastery.com/indicators/testing-the-fm-demodulator-filter/`.
(The Traders.com May 2021 Traders' Tips page for the companion "A Technical
Description Of Market Data For Traders" article only exposed the wrapper
call, not the actual FM Demodulator function body -- web_search failed with
a DDGS/Yahoo TLS error, browser fallback to Google search found this source
instead.)

## Hypothesis

Deriv = Close - Close[2] (2-bar derivative); Z3 = sum of the last 4 Deriv
values -- per Ehlers, this construction places zeros at the Nyquist and
2*Nyquist frequencies, effectively integrating the derivative while
suppressing certain noise components. Z3 is smoothed (Signal = SMA(Z3,
sig_period)) and the rate of change of Signal crossing zero triggers
entries. This Z3 construction (sum of 4 consecutive 2-bar derivatives) is a
distinct momentum-smoothing mechanic from standard ROC/MACD/TRIX already in
this repo.

## Grid test (Step 6)

`sig_period` in [6,8,12] x `roc_period` in [1,2,3] x `max_hold_days` in
[10,20,30], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.216** (70/324)
- by_asset_class: equity 66/162 (0.407), crypto 4/162 (0.025)
- by_vol_regime: low 51/108 (0.472), mid 19/108 (0.176), **high 0/108
  (0.0)** -- universal failure in high-vol regime, the momentum-ROC-crossover
  mechanic apparently whipsaws badly during volatile periods.
- best cell: SPY, sig_period=12/roc_period=2/max_hold_days=30, low-vol,
  Sharpe 2.41

## Single-config validation (Step 7)

### QQQ, sig_period=12, roc_period=3, max_hold_days=20 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.272 (threshold 1.0) |
| Max drawdown | **PASS** | 0.206 (threshold 0.25) |
| Transaction cost survival (10bps/trade, 81 trades) | **PASS** | net Sharpe 1.184 |
| Walk-forward (4 manual equal splits -- `check_walk_forward` in validators.py broken: `vectorbt.utils.splitting` missing; computed manually) | **PASS** (all positive) | [1.737, 0.590, 2.260, 0.927] |
| Parameter sensitivity (sig_period in [10,12,14]) | **PASS** | relative_std 0.150; Sharpes [0.983, 1.272, 1.425] |

**Verdict: ACCEPT for QQQ.** Reasonable trade frequency (81 trades over 7.5
years, ~11/year) for what amounts to a fairly high-frequency momentum
crossover.

### SPY

No SPY full-sample config in the searched neighborhood cleared Sharpe 1.0
with an adequate trade count alongside acceptable MDD. **Not accepted.**

### Crypto (BTC/USDT, ETH/USDT)

Grid pass_fraction for crypto was 0.025 (4/162). **Rejected decisively.**

## Overall decision

**ACCEPTED, QQQ only**: sig_period=12/roc_period=3/max_hold_days=20. SPY and
crypto rejected. Notable decisive weakness: this strategy fails universally
in the high-vol regime tercile (0/108 grid cells) -- a future loop
combining this Z3-ROC signal with a volatility-regime exit filter (similar
to other strategies in this repo's `strategies/` directory that gate out
high-vol periods) could plausibly rescue a broader accept.
