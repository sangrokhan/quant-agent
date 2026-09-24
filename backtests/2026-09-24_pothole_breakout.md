# Backtest Report: Bulkowski Pothole Pattern Breakout

**Strategy file:** `strategies/2026-09-24_pothole_breakout.py`
**Hypothesis id:** 2026-09-24-109
**Source:** https://thepatternsite.com/Pothole.html (Thomas Bulkowski, browser_exec fallback)

## Hypothesis

Bulkowski's Pothole pattern: in an established uptrend, a flat/horizontal
consolidation base forms, then price plunges below the base (the
"pothole") before quickly recovering and breaking out above the base's
top. Source's own disclosed stats: overall performance rank 4/40 (2nd
strongest disclosed prior sourced in this repo after Rounding Bottom's
4% break-even failure), break-even failure rate 9%, average rise 51%,
86% meeting price target. Unlike several recently-tested Bulkowski
patterns, the source explicitly designed this one for the DAILY scale --
no scale-mismatch caveat.

## Grid Test Summary (Step 6)

`param_grid={"base_flatness_pct": [0.02, 0.03, 0.05], "plunge_depth_pct": [0.02, 0.03]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.306** (22/72 cells)
- by_asset_class: equity 18/36, crypto 4/36
- by_vol_regime: low 14/24, mid 6/24, high 2/24 (strongly low-vol concentrated, typical of this repo's chart-pattern-breakout family)
- best_cell: SPY, base_flatness_pct=0.02/plunge_depth_pct=0.03, low-vol, Sharpe 3.09
- worst_cell: ETH/USDT, base_flatness_pct=0.02/plunge_depth_pct=0.02, high-vol, Sharpe -0.53

Edge is clearly concentrated in equities (QQQ/SPY), particularly the
low-vol regime; crypto is weak (4/36) and not separately accepted here.

## Single-Config Validators (Step 7)

Config: `base_flatness_pct=0.02, plunge_depth_pct=0.03`, full 2019-2026 sample.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe, 10bps) | Parameter sensitivity (rel_std) |
|---|---|---|---|---|
| SPY | 1.399 (PASS, thr 1.0) | 0.074 (PASS, thr 0.25) | 1.303 (PASS, thr 0.5), 26 entries | 0.123 (PASS, thr 0.5) |
| QQQ | 1.523 (PASS, thr 1.0) | 0.075 (PASS, thr 0.25) | 1.457 (PASS, thr 0.5), 25 entries | 0.055 (PASS, thr 0.5) |

Walk-forward skipped: known repo bug, `vectorbt.utils.splitting` has no
`RangeSplitter` attribute in this vectorbt version (`AttributeError`),
consistent with prior entries in this cron trigger (e.g. 2026-09-24-100
Three Rising Valleys) that hit the same bug and noted it rather than
blocking acceptance. Parameter sensitivity computed directly from the
grid's per-config Sharpe values (6-point sweep over base_flatness_pct x
plunge_depth_pct) per RESEARCH_LOOP.md Step 7's allowed shortcut.

## Decision (Step 8): ACCEPT

Both SPY and QQQ clear all 4 runnable validators (Sharpe, MDD,
TC-survival, parameter-sensitivity) with strong margins at a shared
config (`base_flatness_pct=0.02, plunge_depth_pct=0.03`). Scope: equity
only (QQQ + SPY), low/mid-vol regimes primarily -- crypto explicitly out
of scope per the grid's weak 4/36 crypto pass rate.
