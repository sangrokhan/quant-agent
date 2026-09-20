# LBR 3/10 Oscillator + low-vol regime gate (rescue attempt for 2026-09-20-120)

**Strategy file:** `strategies/2026-09-20_lbr_3_10_oscillator_lowvol_gate.py`
**Outcome:** REJECTED (rescue attempt failed — gate made results WORSE, not better)

## Hypothesis

Direct rescue attempt for rejected id 2026-09-20-120 (LBR 3/10 Oscillator,
unconditional, full-period Sharpe 0.540 QQQ / 0.618 SPY). That iteration's
grid showed decisive regime-dependence (low-vol pass_fraction 0.594 vs mid
0.25 vs high 0.031), suggesting a vol-regime gate (mirroring the accepted
2026-09-03-001 BB+vol-regime pattern) might rescue it: only take the
golden-cross long signal while realized vol ≤ its own trailing median;
force flat if regime flips to elevated vol mid-position.

## Grid test (Step 6)

`param_grid`: `vol_regime_ratio ∈ {0.8, 1.0, 1.2}`, `signal_window ∈ {9,
16}` (6 combos, fast=3/slow=10 fixed) × `symbols = {equity: [QQQ, SPY],
crypto: [BTC/USDT, ETH/USDT]}` × `vol_regime_splits=3` = 72 cells,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.236** (17/72) — **WORSE** than the ungated
  version's 0.292 (28/96)
- **By asset class:** equity 11/36 (0.306), crypto 6/36 (0.167) — both worse
  than ungated (equity 0.375, crypto 0.208)
- **By vol regime:** low 15/24 (0.625), mid 2/24 (0.083), high 0/24 (0.0)
- **Best per-config pass rate:** ratio=1.2/signal=16 or ratio=1.2/signal=9,
  4/12 each — still worse than ungated's best per-config (4/12 was also the
  ungated ceiling, so no improvement even at the best gate setting)

## Single-config validators (Step 7) — best grid params (ratio=1.2, signal_window=16)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (≥1.0) | 0.360 — **FAIL** (down from 0.540 ungated) | 0.714 — **FAIL** (up from 0.618 ungated but still fails) |
| Max Drawdown (≤0.25) | 0.206 — pass | 0.121 — pass |
| Transaction cost survival (net Sharpe≥0.5) | 0.044 — **FAIL** (down from 0.204) | 0.155 — **FAIL** (down from 0.200) |
| Walk-forward (4-split proxy) | 0.75 — pass | 0.75 — pass |
| Parameter sensitivity (relative_std≤0.5) | 0.925 — **FAIL** (new failure, wasn't failing ungated) | 0.350 — pass |

## Decision

**REJECTED — rescue attempt failed.** The vol-regime gate did not rescue the
strategy; it made both the grid pass_fraction (0.236 vs 0.292) and most
single-config metrics worse (QQQ Sharpe dropped from 0.540 to 0.360, both
symbols' net-of-cost Sharpe dropped further, and QQQ's parameter
sensitivity newly failed at relative_std 0.925). The reduced trade count
(190/206 vs 281/277 ungated) confirms the gate is filtering out
profitable trades along with the intended unprofitable high-vol ones,
netting worse rather than better performance — likely because the gate's
trailing-median-vol condition frequently forces an exit shortly after a
profitable golden-cross entry, cutting winners short rather than avoiding
losers. Same pattern observed this same day for the SZO rescue attempt
(id 2026-09-20-119: trend-filter made SZO worse, not better). Do not
pursue a vol-regime gate on this particular oscillator further; the LBR
3/10 Oscillator family should be considered closed unless a fundamentally
different filter (e.g. trend-direction confirmation on a higher timeframe,
not a volatility gate) is proposed in a future iteration.
