# Jump + Volume Confirmation Drift Continuation (PEAD proxy) — SPY/QQQ/BTC/ETH

**Hypothesis source:** https://quantmemo.com/strategies/earnings-drift-pead
(read via browser_exec; web_extract's configured backend is DDG-only and
cannot fetch page content, so it failed and this fell back to the browser
per RESEARCH_LOOP.md Step 2).

## Hypothesis

PEAD's core mechanism (per source): a large one-day informational jump,
confirmed by above-average volume/attention, is followed by continued
drift in the same direction because the market under-reacts. This repo has
no point-in-time earnings-calendar data, so this strategy tests the
OHLCV-only proxy: return-z-score jump + volume confirmation -> fixed
holding-period long.

## Step 6 — Grid summary (216 cells: 3 jump_std_mult x 3 volume_mult x 2
hold_days x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles)

- `pass_fraction`: 0.241 (52/216)
- `by_asset_class`: equity 6/108 (5.6%), crypto 46/108 (42.6%) —
  **opposite of the source's equity-native thesis**; crypto passed far more
  often, likely because crypto's much larger single-day jumps trivially
  clear the Sharpe bar in isolated vol-tercile slices, not because the
  PEAD mechanism (analyst under-reaction) applies to crypto.
- `by_vol_regime`: low 20/72, mid 27/72, high 5/72 — best cell was a
  low-vol-tercile SPY slice (Sharpe 2.25 at jump_std_mult=1.5,
  volume_mult=1.2, hold_days=10); worst cell was a high-vol-tercile SPY
  slice with the shorter hold (Sharpe -1.14).

## Step 7 — Full-sample validators (best grid config: SPY,
jump_std_mult=1.5, volume_mult=1.2, hold_days=10, 2019-01-01..2026-09-01)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | -0.071 | >= 1.0 | **FAIL** |
| Max drawdown | 0.310 | <= 0.25 | **FAIL** |
| Transaction cost survival (10bps/trade, 35 trades) | -0.121 | >= 0.5 | **FAIL** |
| Walk-forward (manual 4-split fallback — `check_walk_forward` broken on installed vectorbt 1.1.0, no `vbt.utils.splitting`) | 0.75 (3/4 splits positive) | >= 0.75 | pass |
| Parameter sensitivity (jump_std_mult in {1.25,1.5,1.75,2.0}) | relative_std 1.167 | <= 0.5 | **FAIL** |

## Verdict: REJECTED

The grid's "best cell" (isolated low-vol tercile, single symbol) does not
generalize: full-sample Sharpe is negative, drawdown exceeds the threshold,
the strategy doesn't survive realistic transaction costs, and Sharpe is
wildly unstable across nearby jump-threshold values (relative std > 1.0).
This is a textbook grid-search overfit — the tercile slice that scored
Sharpe 2.25 is not representative of the strategy's actual full-sample
behavior. Only walk-forward barely passed (3/4 splits positive), which
alone is not sufficient to accept.

The elevated crypto pass-rate in the grid (42.6% vs equity's 5.6%) is noted
for future loops but should NOT be read as "this PEAD proxy works on
crypto" — it's much more likely an artifact of z-scored-jump thresholds
being trivially met during crypto's larger baseline volatility swings
within isolated vol-tercile slices, the same overfitting pattern seen on
the equity side.
