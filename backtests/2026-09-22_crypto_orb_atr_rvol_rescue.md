# Crypto ORB v2 — ATR-range + RVOL filter rescue attempt (REJECTED)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_crypto_orb_atr_rvol_rescue.py`
**Source:** https://tradersentiments.com/trading-strategies/opening-range-breakout (accessed 2026-09-22)

## Hypothesis
Rescue attempt on prior KB entry `2026-09-04-148` (crypto first-hour-UTC ORB,
rejected: 71%/53% max drawdown, deeply negative net Sharpe after costs from
churning ~8700-8800 unfiltered trades over 6.7yr). That entry's own `notes`
suggested adding a volume/VWAP confirmation filter and widening the opening
range. This iteration implements two concrete numeric filters from the
source article's "Essential Indicator Confirmation Stack": (1) an ATR-based
range-size filter (only trade if opening-range height is 25%-60% of a
rolling ATR) and (2) an RVOL >= 1.5 volume-confirmation filter, on top of a
wider opening range (1h or 4h) and an EMA(9) trailing-stop exit.

## Result: catastrophic under-trading, not over-trading
The AND-combination of the ATR-range filter and RVOL filter is far too
restrictive on hourly BTC/ETH bars over 2019-2026:

| symbol | range_hours | rvol_threshold | # trades (7.6yr) | full-sample Sharpe |
|---|---|---|---|---|
| BTC/USDT | 1 | 1.0 | 58 | 0.055 |
| BTC/USDT | 1 | 1.5 | 16 | 0.129 |
| BTC/USDT | 4 | 1.0 | 0 | n/a |
| BTC/USDT | 4 | 1.5 | 0 | n/a |
| ETH/USDT | 1 | 1.0 | 12 | 0.091 |
| ETH/USDT | 1 | 1.5 | 0 | n/a |
| ETH/USDT | 4 | * | 0 | n/a |

Grid test (`run_grid_crypto_orb_atr_rvol_rescue.py`, 24 cells, crypto only,
3 vol-regime terciles): **0/24 cells passed**, most cells have null/NaN
Sharpe because there are too few trades per vol-regime split to compute a
meaningful ratio (many regimes have 0-2 trades).

## Decision: REJECT
The double-filter (ATR range + RVOL) essentially never fires jointly on
crypto 1h bars, especially with a 4h opening range (0 trades in every
4h-range configuration tested). Where it does fire (1h range), sample size
is too small (12-58 trades over 7.6 years) to draw any statistical
conclusion, and even so the Sharpe that does show up is close to zero, not
negative -- unlike the original over-trading rejection, this is an
under-trading / feasibility failure, not a "false edge disproven" failure.

## Notes for future revisit
This is a genuinely different failure mode from the original rejection
(over-trading -> catastrophic drawdown) — now it's under-trading -> no
statistical signal. A future loop could try: (a) loosening the RVOL
threshold well below 1.0 (e.g. 0.7-0.9) since RVOL >= 1.5 turns out
extremely rare on crypto's already-high baseline volume, (b) widening the
ATR range band (e.g. 0.15-0.80 instead of 0.25-0.60), or (c) abandoning the
RVOL filter entirely and keeping only the ATR range-size filter as a single,
less-restrictive gate on top of the original (rejected) unfiltered ORB.
