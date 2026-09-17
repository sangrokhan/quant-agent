# Backtest Report: Apirine On-Balance Volume Modified (OBVM) Signal Crossover

**Strategy file:** `strategies/2026-09-17_obvm_signal_crossover.py`
**Source:** Traders.com Apr 2020 Traders' Tips (Vitali Apirine, "On-Balance
Volume Modified (OBVM)", TASC Apr 2020), TradeStation EasyLanguage code, read
via `browser_exec` this iteration --
`https://traders.com/Documentation/FEEDbk_docs/2020/04/TradersTips.html`.

## Hypothesis

OBVM = EMA(OBV, obvm_length), SignalLine = EMA(OBVM, signal_length) --
structurally "MACD applied to the classic Granville on-balance-volume
indicator instead of price". A bullish crossover (OBVM crosses above its
signal line) should mark a volume-flow momentum shift toward accumulation,
serving as a long entry trigger; exit on the bearish cross or a time stop.
First OBV-signal-line-crossover strategy in this repo (distinct from prior
OBV divergence / z-score / OBV-vs-SMA constructions).

## Grid test (Step 6)

`obvm_length` in [5,7,12] x `signal_length` in [8,10,15] x `max_hold_days`
in [10,20,30], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.333** (108/324)
- by_asset_class: equity 86/162 (0.531), crypto 22/162 (0.136)
- by_vol_regime: low 71/108 (0.657), mid 16/108 (0.148), high 21/108 (0.194)
  -- strongly favors low-vol regimes
- best cell: QQQ, obvm_length=5/signal_length=10/max_hold_days=30, low-vol,
  Sharpe 2.91

Grid signal: robust on equity (both QQQ and SPY have full-vol-regime-passing
cells), weak on crypto.

## Single-config validation (Step 7)

### QQQ, obvm_length=12, signal_length=15, max_hold_days=30 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.559 (threshold 1.0) |
| Max drawdown | **PASS** | 0.094 (threshold 0.25) |
| Transaction cost survival (10bps/trade, 32 trades) | **PASS** | net Sharpe 1.498 (threshold 0.5) |
| Walk-forward (4 manual equal splits -- `check_walk_forward` in validators.py is broken: `vectorbt.utils.splitting` missing in installed version; computed manually) | **PASS** | per-split Sharpe [1.645, 1.094, 1.442, 2.070] -- all 4 splits positive, consistent |
| Parameter sensitivity (obvm_length in [10,12,14]) | **PASS** | relative_std 0.032 (threshold 0.6); Sharpes [1.628, 1.559, 1.506] -- very flat/robust |

**Verdict: ACCEPT for QQQ.** Cleanest result of this trigger's iterations:
all 4 walk-forward splits positive and consistent, very low parameter
sensitivity.

### SPY, obvm_length=7, signal_length=8, max_hold_days=20 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.243 |
| Max drawdown | **PASS** | 0.115 |
| Transaction cost survival (72 trades) | **PASS** | net Sharpe 1.070 |
| Walk-forward (4 manual equal splits) | **PASS (3/4 positive)** | per-split Sharpe [2.072, -0.241, 2.139, 0.896] -- one negative split (likely 2022 rate-hike regime), overall still net positive and headline metrics pass |
| Parameter sensitivity (obvm_length in [5,7,10]) | **PASS** | relative_std 0.204; Sharpes [0.752, 1.243, 0.957] |

**Verdict: ACCEPT for SPY** (per-symbol-tuned config, different from QQQ's),
with the caveat noted in `notes`/here: one of four walk-forward splits was
negative, so this is a slightly less robust accept than QQQ's.

### Crypto (BTC/USDT, ETH/USDT)

Grid pass_fraction for crypto was 0.136 (22/162), weaker than equity.
**Rejected** -- not investigated to a specific single-config this iteration.

## Overall decision

**ACCEPTED, equity only (QQQ + SPY, per-symbol tuned configs)**:
QQQ obvm_length=12/signal_length=15/max_hold_days=30 (strongest, all 4 WF
splits positive); SPY obvm_length=7/signal_length=8/max_hold_days=20
(accepted but with 1 of 4 WF splits negative -- noted as the weaker of the
two accepts). Crypto rejected (grid pass_fraction 0.136).
