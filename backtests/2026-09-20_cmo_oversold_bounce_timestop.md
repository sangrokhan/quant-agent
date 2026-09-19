# Chande Momentum Oscillator (CMO) Oversold-Bounce Time-Stop — QQQ/SPY

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_cmo_oversold_bounce_timestop.py`
**Source:** https://www.quantifiedstrategies.com/chande-momentum-oscillator-trading-strategy/

## Hypothesis

CMO(9) crosses below -50/-40/-60 (extreme oversold) triggers a long entry,
held for a short max_hold_days (3/5/8) or exited early if CMO recovers above
0, per the source's own disclosed finding that short holding periods
(5-day) outperformed longer ones (10/15/30-day) monotonically in its own
SPY backtest.

## Grid test (Step 6)

`param_grid={"oversold_threshold": [-40, -50, -60], "max_hold_days": [3, 5, 8]}`,
equity QQQ/SPY + crypto BTC/USDT/ETH/USDT, vol_regime_splits=3, 2019-2026.

- Overall pass fraction: 0.222 (24/108)
- By asset class: equity 22/54 (0.407), crypto 2/54 (0.037)
- By vol regime: low 10/36, mid 9/36, high 5/36 — no regime clearly dominant
- Best cell: oversold_threshold=-40, max_hold_days=3, QQQ, **low-vol regime only**, Sharpe 1.93

The best cell is a narrow low-vol-regime slice, not representative of the
full sample.

## Single-config validation (Step 7) — oversold_threshold=-40, max_hold_days=3

| Symbol | Sharpe | MDD | Net-of-cost Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.138 (FAIL, <1.0) | 0.211 (pass) | 0.019 (FAIL, <0.5) | 0.75 (pass) | 0.635 (FAIL, >0.5) |
| SPY | -0.120 (FAIL) | 0.241 (pass) | -0.221 (FAIL) | 0.25 (FAIL) | 0.790 (FAIL) |

Full-sample performance is dramatically weaker than the grid's cherry-picked
best cell (low-vol QQQ slice) — the strategy does not generalize across the
full sample or across a range of parameter perturbations.

## Decision: **REJECTED** (both QQQ and SPY fail Sharpe, tx-cost-survival, and parameter-sensitivity decisively; SPY additionally fails walk-forward)

Crypto grid pass_fraction is even worse (0.037/54), not investigated further.

Note for future loops: the source's article disclosed a 5-day-hold
methodology finding but the exact numeric entry rule was paywalled; this
independently-constructed oversold-crossing rule with a short time-stop does
not reproduce a tradeable edge on this repo's QQQ/SPY/crypto universe. Do
not re-attempt the same construction without a materially different
entry/exit design (e.g. combining with a trend filter or divergence
detection instead of a bare threshold-cross).
