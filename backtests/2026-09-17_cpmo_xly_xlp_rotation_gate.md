# Backtest Report: Apirine Compare Price Momentum Oscillator (CPMO) Rotation Gate

**Strategy file:** `strategies/2026-09-17_cpmo_xly_xlp_rotation_gate.py`
**Source:** Traders.com Aug 2020 Traders' Tips (Vitali Apirine, "The Compare
Price Momentum Oscillator (CPMO)", TASC Aug 2020), Wealth-Lab reference
strategy code, read via `browser_exec` this iteration --
`https://traders.com/Documentation/FEEDbk_docs/2020/08/TradersTips.html`.

## Hypothesis

The DecisionPoint Price Momentum Oscillator (PMO, a double-EMA-smoothed
1-period rate-of-change oscillator) is already saturated in this repo as a
single-asset signal-vs-own-line strategy. The CPMO article's novel angle is
applying PMO in an INTERMARKET context: compute PMO independently for two
sector/asset proxies and trade the crossover of one PMO series above/below
the other. The source's reference example compares consumer discretionary
(IXY) vs consumer staples (IXR) PMO as a market-wide risk-on/risk-off
rotation signal. Adapted here with modern liquid sector ETF proxies
(XLY vs XLP) to gate a long position in the traded asset (QQQ/SPY/crypto).
This is a genuinely novel mechanic (cross-asset PMO comparison) despite the
underlying PMO formula itself being saturated.

## Grid test (Step 6)

`period1` in [25,35,45] x `period2` in [15,20,25] x `max_hold_days` in
[20,30,40], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.259** (84/324)
- by_asset_class: equity 72/162 (0.444), crypto 12/162 (0.074)
- by_vol_regime: low 50/108 (0.463), mid 22/108 (0.204), high 12/108 (0.111)
  -- risk-on/risk-off rotation signal is noisier in high-vol regimes.
- best cell: SPY, period1=35/period2=15/max_hold_days=40, low-vol, Sharpe 2.51
- No single cell passed all 3 vol-regime terciles cleanly in this grid; the
  closest, QQQ period1=25/period2=20/max_hold_days=20, failed only the
  mid-vol tercile (Sharpe 0.99, just under the 1.0 min_sharpe grid threshold).

## Single-config validation (Step 7)

### period1=35, period2=15, max_hold_days=20 (full sample 2019-2026, same config both symbols)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | **PASS** 1.231 | **PASS** 1.187 |
| Max drawdown | **PASS** 0.132 | **PASS** 0.124 |
| TC survival (10bps, 26 trades each) | **PASS** net Sharpe 1.178 | **PASS** net Sharpe 1.113 |
| Walk-forward (4 manual splits -- `check_walk_forward` in validators.py broken: `vectorbt.utils.splitting` missing; computed manually) | **PASS** [1.521, 0.069, 1.601, 1.293] -- all positive, one weak split | **PASS** [0.936, 0.827, 1.739, 1.171] -- all positive |
| Parameter sensitivity (period1 in [30,35,40]) | **PASS** relative_std 0.140 | **PASS** relative_std 0.131 |

**Verdict: ACCEPT for both QQQ and SPY**, same config (period1=35/period2=15/
max_hold_days=20) works cleanly on both -- unusual in this repo where most
recent accepts needed per-symbol tuning. Sample size is thin (26 trades over
7.5 years each, ~3.5/year) since the rotation signal itself is
infrequent -- flagged as a lower-frequency signal, consistent with an
intermarket regime-rotation mechanic rather than a tactical timing signal.

### Crypto (BTC/USDT, ETH/USDT)

Grid pass_fraction for crypto was 0.074 (12/162). **Rejected decisively.**

## Overall decision

**ACCEPTED, equity only (QQQ + SPY, SAME config, unusual for this repo)**:
period1=35/period2=15/max_hold_days=20, XLY-vs-XLP rotation gate. Low trade
frequency (~3.5 trades/year) is a known limitation -- noted for future
loops considering whether to combine this rotation gate with a
higher-frequency entry trigger (as several prior "gate" strategies in this
repo have done). Crypto rejected decisively.
