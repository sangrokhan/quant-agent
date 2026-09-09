# 2026-09-10 — Ehlers 2-Pole SuperSmoother Trend Crossover

## Hypothesis

John Ehlers' 2-pole SuperSmoother filter (*Cybernetic Analysis for Stocks and
Futures*, 2004, Eq. 3-3) is a recursive Butterworth-style low-pass filter
with much less lag than a comparable SMA/EMA. Per
https://stonehillforex.com/2-pole-super-smoother-filter-as-a-baseline-indicator/,
it can be used directly as a trend "baseline": price crossing above the
SuperSmoother line, confirmed by the line's own upward slope, signals a
long entry; the opposite crossover or a slope flip signals exit. Exact
filter coefficients corroborated against
https://gist.github.com/flare9x/089be64732079134faa0a50332e4437b (Julia
port of Ehlers' book code).

This is distinct from every other Ehlers strategy already tested in this
repo (Roofing Filter, Trendflex, Even Better Sinewave, Cyber Cycle, MESA
Stochastic, Instantaneous Trendline) — those all use the SuperSmoother (or a
highpass/SuperSmoother combination) as a denoising stage feeding a
cycle/oscillator construction, not as the crossover signal line itself.

Strategy file: `strategies/2026-09-10_supersmoother_trend_crossover.py`

## Single-config validator results (n=30, slope_lookback=3, max_hold_days=20)

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-forward pass fraction | Trades |
|---|---|---|---|---|---|
| QQQ | 1.019 (pass, thr 1.0) | 0.086 (pass, thr 0.25) | 0.856 (pass, thr 0.5) | 0.75 (pass, thr 0.75; 3/4 splits) | 68 |
| SPY | 1.064 (pass, thr 1.0) | 0.062 (pass, thr 0.25) | 0.825 (pass, thr 0.5) | 1.00 (pass, thr 0.75; 4/4 splits) | 69 |

Parameter sensitivity (12-cell low-vol-tercile Sharpe grid across
n∈{10,20,30} × slope_lookback∈{3,5}, QQQ+SPY): relative std = 0.270,
threshold 0.5 → **pass**.

Note: `check_walk_forward` in `validation/validators.py` currently raises
(`vectorbt.utils` has no `splitting` attribute on the installed vectorbt
1.1.0) — a pre-existing library/version mismatch unrelated to this
strategy. Walk-forward was computed with an equivalent manual 4-way
`np.array_split` range-split + per-split Sharpe>0 check (same
pass-fraction/threshold semantics as the intended validator) as a
substitute; recorded here for a future loop to fix `validators.py` itself.

## Step 6 grid summary (n×slope_lookback × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- 72 cells total, 14 passed (pass_fraction 0.194).
- By asset class: equity 14/36 passed, crypto 0/36 passed — **works on
  equities only, fails outright on crypto** (BTC/USDT, ETH/USDT never
  passed a single cell).
- By vol regime: low 10/24, mid 4/24, high 0/24 — edge is concentrated in
  low/mid realized-vol regimes; strategy loses money in high-vol regimes
  (best not to trade this style of trend baseline through high-vol
  chop/crash periods, consistent with prior Bollinger/HalfTrend findings in
  this repo).
- Best cell: n=30, slope_lookback=5, SPY, low-vol, Sharpe 1.957.
- Worst cell: n=10, slope_lookback=5, SPY, mid-vol, Sharpe -1.019.

## Decision: ACCEPT (equity only — QQQ, SPY)

All validators pass for both QQQ and SPY on the primary n=30 config over the
full 2018-2026 sample. Crypto (BTC/USDT, ETH/USDT) is explicitly rejected —
zero grid cells passed in any vol regime, so this strategy's live scope is
equity trend-following only, not crypto.
