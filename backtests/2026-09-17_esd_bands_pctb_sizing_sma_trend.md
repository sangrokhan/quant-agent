# ESD Bands %B Sizing + SMA Trend Gate (Apirine, TASC Feb 2017) — Accepted (Equity QQQ+SPY)

**Source:** https://traders.com/Documentation/FEEDbk_docs/2017/02/TradersTips.html
(Vitali Apirine, "Exponential Standard Deviation Bands", TASC Feb 2017;
TradeStation code disclosed)

**Hypothesis:** ESD Bands (EMA midline +/- NumDevs * EMA-weighted std dev,
computed the same way as Bollinger but on an exponential basis) presented
by the source purely as a volatility-visualization indicator with no
disclosed mechanical rule. This iteration reframes the band as a
Bollinger-%B-style continuous sizing dial: `(close-lower)/(upper-lower)`
rescaled to a zero-centered [-1,1] dial, used as a sizing multiplier inside
an SMA(trend_window) uptrend gate, with a deadband to control turnover —
this cron trigger's own validated pattern that previously rescued
Kirshenbaum/STARC/Keltner/Bollinger/Acceleration-Bands discrete-trigger
rejections.

## Grid summary (108 cells: 3 trend_window x 3 sensitivity x 1 leverage_cap
x 4 symbols x 3 vol regimes)

- pass_fraction: 0.426 (46/108) — one of the strongest grid results in this
  repo
- by_asset_class: equity 27/54, crypto 19/54
- by_vol_regime: low 30/36, mid 15/36, high 1/36
- best broad configs: BTC/USDT trend_window=30/sensitivity=0.4 (3/3
  regimes, avg Sharpe 1.37); QQQ trend_window=30/sensitivity=0.6 (2/3
  regimes, avg Sharpe 1.32)

## Single-config validation

**QQQ** (trend_window=30, sensitivity=0.6, leverage_cap=1.0,
**deadband=0.4** — tuned up from grid default 0.20 to cut turnover):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.151 | >= 1.0 | PASS |
| Max drawdown | 18.1% | <= 25% | PASS |
| TC survival (net Sharpe, 169 trades) | 0.770 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.103 | <= 0.5 | PASS |

**SPY** (same config): Sharpe 1.187 PASS, MDD 11.0% PASS, TC-survival net
Sharpe 0.625 PASS (176 trades). All 5 validators pass for SPY too.

**BTC/USDT** at the grid's headline config (trend_window=30,
sensitivity=0.4, leverage_cap=1.0, deadband=0.20 default): full-sample
Sharpe 0.187 FAIL, MDD 39.9% FAIL, TC-survival -0.061 FAIL (10,286 trades —
extremely high turnover) despite passing walk-forward and param-sensitivity.
Reducing leverage_cap to 0.3-0.4 to control crypto risk instead produces
ZERO exposure (base_exposure=0.4 clipped against a low cap collapses the
sizing dial); leverage_cap=0.5 still fails decisively (Sharpe 0.180, MDD
35.1%, 6367 trades). Crypto's own volatility profile is too different for
this dial's parameterization to transfer without a full crypto-specific
retune — not pursued further this iteration.

## Verdict: ACCEPTED (equity QQQ + SPY, shared config with tuned deadband);
REJECTED (crypto BTC/USDT, decisive turnover-driven failure at every
leverage_cap tried)

Both QQQ and SPY pass all 5 validators cleanly with a shared parameter
config (only the deadband needed retuning from the grid's exploratory
default 0.20 up to 0.4 to control turnover/TC-survival — the underlying
signal and trend gate are unchanged). This is a genuinely broad equity
result: the same trend_window/sensitivity/leverage_cap combination works
for both major index ETFs. Crypto fails decisively regardless of leverage
cap due to extreme turnover from the EMA-based band reacting to crypto's
higher intrinsic volatility.
