# quant-agent

Autonomous quant research system built as a **2-agent architecture** running
on top of Hermes cronjobs.

## Architecture

```
                     ┌──────────────────────────────┐
   every hour        │  Hermes cronjob (hourly)      │
   ───────────────►  │                                │
                     │  1. run gatekeeper/check_gate.py
                     │     (pure rule script, no LLM)│
                     └───────────────┬────────────────┘
                                     │
                     approved == false│  approved == true
                     ───────────────►│  ───────────────►
                     (stop, do        │  (start Research Agent
                      nothing this    │   LLM turn, following
                      run)            │   RESEARCH_LOOP.md)
                                     ▼
                     ┌──────────────────────────────┐
                     │  Research Agent               │
                     │  (the cronjob's LLM turn      │
                     │   itself — not a separate      │
                     │   process/codepath)            │
                     │                                │
                     │  knowledge_base/  → read       │
                     │  data/loaders.py  → fetch      │
                     │  strategies/      → write code │
                     │  validation/      → validate   │
                     │  backtests/       → write report│
                     │  knowledge_base/  → append log │
                     └──────────────────────────────┘
```

- **Gatekeeper** (`gatekeeper/check_gate.py`): a pure, deterministic,
  LLM-free Python script. It answers exactly one question — "may the
  research loop run right now, and how ambitiously?" — based on day of
  week, time of day (KST), and Claude 5-hour rolling usage. It is meant to
  run first, every hour, before any LLM turn starts. See
  [gatekeeper section](#gatekeeper) below for the full policy and I/O
  contract.

- **Research Agent**: **not a separate process or codebase.** The "agent" is
  the Hermes cronjob's own LLM turn — when the gatekeeper approves a run,
  that LLM turn follows the procedure in [`RESEARCH_LOOP.md`](RESEARCH_LOOP.md)
  step by step: read the knowledge base, check novelty, form a hypothesis,
  write strategy code, backtest/validate it with `validation/validators.py`,
  and log the outcome back to the knowledge base. There is no
  `research_agent.py` to run — the procedure doc *is* the implementation.

## Repository layout

```
quant-agent/
  README.md              — this file
  RESEARCH_LOOP.md        — step-by-step procedure the Research Agent LLM turn follows
  SAFETY.md               — hard safety boundary: why/how live trading is blocked
  requirements.txt        — pinned-ish deps for the scaffold pieces (yfinance, ccxt, vectorbt, ...)
  gatekeeper/
    check_gate.py          — rule-based go/no-go script (see below)
    usage_state.json        — MOCK usage state example (see schema below)
  data/
    loaders.py              — thin wrappers over src/quant_agent/data (yfinance/ccxt + parquet cache)
    cache/                  — local parquet cache (gitignored, .gitkeep tracked)
  src/quant_agent/data/     — the actual MarketDataService/ParquetCache/providers (pre-existing)
  strategies/               — validated strategy code lands here (see naming convention below)
  backtests/                — backtest reports (metrics + charts) land here (see naming convention below)
  knowledge_base/
    strategies_log.md        — schema doc + sample entries
    strategies_log.jsonl      — the actual append-only log
  validation/
    validators.py             — Sharpe/MDD/cost/walk-forward/param-sensitivity checks (vectorbt-backed)
  paper_trading/
    simulator.py               — pure local fill simulator, no broker connectivity
```

## Gatekeeper

`gatekeeper/check_gate.py` takes no stdin/argv. Run it directly:

```bash
python gatekeeper/check_gate.py
```

It prints one JSON line to stdout:

```json
{"approved": true, "reason": "...", "suggested_workload": "normal"}
```

and exits `0` if `approved` is `true`, `1` otherwise — so a caller can branch
on exit code alone without parsing JSON if it prefers.

### Policy

- **Weekdays (Mon–Fri) 10:00–18:00 KST**: treated as cost-sensitive hours.
  Approved only while the Claude 5-hour rolling usage is **≤ 75%** (i.e. at
  least 25% headroom is always kept free for interactive/human use during
  business hours). If the usage state can't be read during this window, the
  gate **fails closed** (not approved).
- **All other times** (weekday evenings/nights, and all of Sat/Sun):
  approved as long as usage hasn't hit the hard 100% limit. Once at the hard
  limit, stays blocked until the usage state reports the rolling window has
  reset. If the usage state can't be read outside business hours, the gate
  **fails open** at `"light"` workload (low risk, avoids stalling the loop
  entirely on a missing mock file).
- `suggested_workload` (`light|normal|max`) is advisory: a hint for how
  ambitious a single research loop iteration should be (e.g. skip a long
  walk-forward parameter sweep under `"light"`).

### Usage data source — now LIVE (real Anthropic API)

`check_gate.py` reads the **actual** Claude 5-hour rolling usage percentage
from Anthropic's official (undocumented) OAuth usage endpoint
(`https://api.anthropic.com/api/oauth/usage`, `five_hour.utilization`), via
Hermes' built-in `agent.account_usage.fetch_account_usage("anthropic")`
helper (`~/.hermes/hermes-agent`). This is the same 5-hour rolling window
Claude Code / Claude Pro-Max itself enforces — not an estimate.

Verified manually:
```bash
$ python3 gatekeeper/check_gate.py
{"approved": true, "reason": "weekday business hours (KST 17:53); usage 30.0% within 75% headroom budget", "suggested_workload": "normal"}
```

If the live fetch fails (Hermes package not importable, network error, not
logged in via OAuth), `check_gate.py` falls back to reading
`usage_state.json` below — this mock file exists purely as that fallback /
for local testing without network access, not as the primary source.

### `usage_state.json` schema (fallback only)

```json
{
  "updated_at": "2026-09-03T08:00:00Z",
  "rolling_window_hours": 5,
  "window_start": "2026-09-03T03:00:00Z",
  "window_reset_at": "2026-09-03T13:00:00Z",
  "usage_pct": 42.0,
  "limit_reached": false
}
```

Fields:
- `usage_pct` (required): current 5h rolling window usage, 0–100+.
- `limit_reached` (optional, inferred as `usage_pct >= 100` if omitted):
  explicit hard-limit flag in case the real usage source can signal "blocked"
  independent of the raw percentage.
- `window_reset_at` (optional): informational, surfaced in the `reason`
  string when blocked.

The mock example above ships as `gatekeeper/usage_state.json`. It is only
consulted when the live Anthropic usage-API fetch fails — see
`.gitignore` notes below for how a real, frequently-updated state file
would be handled if you want to override the fallback path.

## How to run things

```bash
# from repo root, using the existing uv-managed venv
uv sync                      # or: pip install -r requirements.txt

# 1. Gatekeeper check (what a cronjob runs first, every hour)
python gatekeeper/check_gate.py

# 2. Research loop: not a script — see RESEARCH_LOOP.md.
#    That document is what the Hermes cronjob's LLM turn follows once
#    the gatekeeper approves.
```

`src/quant_agent/` already has a working `MarketDataService` with tests
(`uv run pytest`), independent of this scaffold — `data/loaders.py` just
exposes two convenience one-liners (`load_equity`, `load_crypto`) on top of
it for strategy scripts.

## Naming conventions

- `strategies/<YYYY-MM-DD>_<short_slug>.py` — one file per accepted strategy
  hypothesis, dated by the loop iteration that produced it. `short_slug`
  should roughly match the `id`/`hypothesis` in the knowledge base entry.
- `backtests/<YYYY-MM-DD>_<short_slug>.md` — one report per strategy file,
  same slug, containing at minimum the metrics table validators produced and
  any chart(s) vectorbt generated (embed as a saved image path or an ASCII
  summary if no image tooling is available in that loop).

## Safety

See [`SAFETY.md`](SAFETY.md). Short version: **no function in this
repository ever places a real order.** Paper trading only.
