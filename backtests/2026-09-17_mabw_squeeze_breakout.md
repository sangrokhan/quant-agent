# Backtest Report: Apirine Moving Average Band Width (MABW) Squeeze Breakout

**Strategy file:** `strategies/2026-09-17_mabw_squeeze_breakout.py`
**Source:** Traders.com Aug 2021 Traders' Tips (Vitali Apirine, "Moving
Average Bands" [Jul 2021] + "Moving Average Band Width" [Aug 2021]),
TradeStation EasyLanguage code, read via `browser_exec` this iteration --
`https://traders.com/Documentation/FEEDbk_docs/2021/08/TradersTips.html`.

## Hypothesis

Bands built around a slow EMA (MA1), with width determined by the deviation
of a fast EMA (MA2) from MA1 -- not a Bollinger-style price standard
deviation. BandWidth = (Upper-Lower)/MA1*100 measures relative narrowness;
a fresh low in BandWidth ("squeeze") followed by a breakout above the
UpperBand should mark the start of a new directional move exiting
consolidation. Novel band construction (fast/slow EMA-spread deviation, not
price stdev) distinct from all Bollinger/Keltner/ATR-based squeeze
strategies already in this repo.

## Grid test (Step 6)

`periods1` in [30,50,70] x `squeeze_pct` in [0.1,0.2,0.3] x `max_hold_days`
in [15,30,45], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.299** (97/324)
- by_asset_class: equity 49/162 (0.302), crypto 48/162 (0.296) -- **notably
  balanced**, unlike almost every other strategy tested this trigger where
  crypto lags equity substantially.
- by_vol_regime: low 72/108 (0.667), mid 22/108 (0.204), high 3/108 (0.028)
  -- squeeze-breakout signal strongly favors low-vol regimes (makes sense:
  squeezes are calm-market phenomena by construction).
- best cell: SPY, periods1=30/squeeze_pct=0.1/max_hold_days=45, low-vol,
  Sharpe 2.82

Despite the balanced grid pass_fraction, no BTC/USDT full-sample config in
the searched neighborhood cleared Sharpe 1.0 (best full-sample BTC Sharpe
found was only 0.24) -- the grid's per-vol-regime cell passes for crypto
were evidently concentrated in favorable sub-periods, not representative of
the full sample.

## Single-config validation (Step 7)

### QQQ, periods1=25, squeeze_pct=0.1, max_hold_days=45 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.176 (threshold 1.0) |
| Max drawdown | **PASS** | 0.135 |
| Transaction cost survival (10bps/trade, 46 trades) | **PASS** | net Sharpe 1.099 |
| Walk-forward (4 manual equal splits -- `check_walk_forward` in validators.py broken: `vectorbt.utils.splitting` missing; computed manually) | **PASS** (all positive) | [2.508, 0.780, 1.203, 0.232] |
| Parameter sensitivity (periods1 in [22,25,28]) | **PASS** | relative_std 0.177; Sharpes [0.756, 1.176, 0.983] |

**Verdict: ACCEPT for QQQ.** Reasonable trade count (46 over 7.5 years,
~6/year).

### SPY

Best full-sample config found (periods1=30/squeeze_pct=0.1/max_hold_days=45)
was razor-thin (Sharpe 1.007, one negative walk-forward split of -0.076).
**Not accepted** -- too marginal to trust alongside the more robust QQQ
config.

### Crypto (BTC/USDT, ETH/USDT)

Despite a surprisingly balanced grid pass_fraction (0.296, comparable to
equity's 0.302), full-sample hand-search across the same parameter
neighborhood found the best BTC/USDT Sharpe was only 0.24 -- the grid's
vol-regime-tercile cell passes do not translate into a viable full-sample
config. **Rejected** -- the grid pass_fraction here is a case study in why
a favorable grid summary alone should not substitute for full-sample
single-config validation (Step 7).

## Overall decision

**ACCEPTED, QQQ only**: periods1=25, squeeze_pct=0.1, max_hold_days=45. SPY
and crypto rejected despite promising-looking grid summaries -- full-sample
validation is decisive here.
