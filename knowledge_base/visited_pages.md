# knowledge_base/visited_pages.jsonl

Append-only log of every web page the Research Agent has fetched during the
research-discovery pipeline (RESEARCH_LOOP.md Steps A-E), one JSON object
per line. This is the access-control record: **before fetching any URL,
check this file first and skip URLs already present** (regardless of which
past iteration/day visited them) so the same page is never re-processed.

## Schema (one JSON object per line)

```json
{
  "url": "string, canonical/normalized URL (strip tracking query params)",
  "visited_at": "ISO8601 UTC timestamp",
  "search_keyword": "the search query that surfaced this URL",
  "page_summary": "1-3 sentence summary of what the page covers",
  "strategy_extracted": true,
  "extracted_hypothesis_ids": ["2026-09-04-003"],
  "notes": "free text: why useful/not useful, quality of the source, anything a future loop should know before deciding whether it's worth re-reading"
}
```

Field notes:
- `url`: normalize before writing/comparing (drop `utm_*`/tracking params,
  trailing slashes) so trivially-different URLs to the same content are
  still recognized as visited.
- `strategy_extracted`: `true` if the page yielded at least one testable
  hypothesis, `false` if it was read but had nothing usable (still worth
  recording so it's never re-fetched).
- `extracted_hypothesis_ids`: cross-reference into
  `knowledge_base/strategies_log.jsonl`'s `id` field (empty list if
  `strategy_extracted` is `false`).
- This file grows unbounded by design — it is the dedupe ledger, not a
  rolling cache. Never rewrite/delete prior lines.

## Sample entry

```json
{"url": "https://example-quant-blog.com/mean-reversion-crypto-funding-rates", "visited_at": "2026-09-04T09:15:00Z", "search_keyword": "crypto funding rate mean reversion strategy backtest", "page_summary": "Blog post proposing a funding-rate-extreme mean reversion strategy for perpetual futures, with suggested entry/exit thresholds and a rough backtest on BTC.", "strategy_extracted": true, "extracted_hypothesis_ids": ["2026-09-04-001"], "notes": "Thresholds in the post are for perp funding rate, need mapping to whatever funding-rate data source is actually available via ccxt before this is directly testable."}
```

Keep entries append-only — never rewrite or delete a prior line.
