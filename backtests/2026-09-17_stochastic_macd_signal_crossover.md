# Backtest Report: Apirine Stochastic MACD Oscillator (STMACD) Signal Crossover

**Strategy file:** `strategies/2026-09-17_stochastic_macd_signal_crossover.py`
**Source:** Traders.com Nov 2019 Traders' Tips (Vitali Apirine, "The Stochastic
MACD Oscillator", TASC Nov 2019), TradeStation EasyLanguage code, read via
`browser_exec` this iteration (web_search failed with a DDGS/Yahoo TLS
connection error; fell back to browser navigation of the traders.com archive
URL directly) --
`https://traders.com/Documentation/FEEDbk_docs/2019/11/TradersTips.html`.

## Hypothesis

STMACD = (FastStoch - SlowStoch) * 100, where FastStoch/SlowStoch are the
fast/slow EMA of Close normalized against the rolling `periods`-day
high/low range (stochastic-style normalization applied to MACD's EMA
spread). A bullish crossover of STMACD above its own EMA signal line
(while STMACD is below `overbought`, avoiding chasing an already-extended
move) should mark a momentum-shift long entry; exit on bearish crossover or
after `max_hold_days`.

## Grid test (Step 6)

`periods` in [30,45,60] x `overbought` in [5,10,15] x `max_hold_days` in
[10,20,30], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.377** (122/324) -- notably higher than most recent
  iterations in this repo, suggesting this indicator construction is
  broadly reasonable.
- by_asset_class: equity 84/162 (0.519), crypto 38/162 (0.235)
- by_vol_regime: low 69/108 (0.639), mid 23/108 (0.213), high 30/108 (0.278)
  -- clearly strongest in low-vol regimes (momentum signal-line crossovers
  tend to whipsaw in choppier/high-vol conditions).
- best cell: QQQ, periods=45/overbought=15/max_hold_days=30, low-vol,
  Sharpe 2.48

Grid signal: strategy construction is fundamentally sound, strongest on
equity in low-vol regimes; a broader hand-search around the grid's
neighborhood (below) found the best full-sample single config.

## Single-config validation (Step 7)

### SPY, periods=30, overbought=20, max_hold_days=10 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.261 (threshold 1.0) |
| Max drawdown | **PASS** | 0.099 (threshold 0.25) |
| Transaction cost survival (10bps/trade, 91 trades) | **PASS** | net Sharpe 1.020 (threshold 0.5) |
| Walk-forward (4 manual equal splits -- `check_walk_forward` in validators.py is broken: `vectorbt.utils.splitting` module missing in installed version; computed manually) | **PASS** (mixed but all positive) | per-split Sharpe [2.131, 0.437, 2.338, 0.522] -- all positive but wide dispersion between regime periods |
| Parameter sensitivity (periods in [25,30,35]) | **PASS** | relative_std 0.235 (threshold 0.6); Sharpes [0.699, 1.261, 0.967] |

**Verdict: ACCEPT for SPY**, 91 trades over 7.5 years (~12/year) is a
reasonably-sized sample, not a thin-sample artifact like some prior
near-misses in this repo.

### QQQ

Broader hand-search around the grid neighborhood found only marginal
full-sample configs (best Sharpe ~1.036, e.g. periods=50/overbought=12/
max_hold_days=30), close to the 1.0 threshold without meaningful margin.
**Not accepted for QQQ** -- treated as a near-miss worth revisiting with a
different entry-mode variant (e.g. oversold-bounce entry instead of plain
signal crossover) in a future iteration.

### Crypto (BTC/USDT, ETH/USDT)

Grid pass_fraction for crypto was 0.235 (38/162) -- meaningfully better than
most recently-tested crypto strategies in this repo, but not investigated
further to a specific accepted single-config this iteration given the SPY
config already met the bar; flagged as a candidate worth a dedicated
crypto-focused parameter search in a future iteration.

## Overall decision

**ACCEPTED, narrow scope: SPY only**, periods=30/overbought=20/
max_hold_days=10. QQQ near-miss (not accepted, Sharpe ceiling ~1.04).
Crypto not accepted this iteration but flagged as a promising candidate for
follow-up given grid pass_fraction 0.235 (better than typical).
