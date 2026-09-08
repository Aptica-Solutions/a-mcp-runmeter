# Continuous local usage collection

`runmeter-collect --config /absolute/private/collector.json` imports measured
usage from explicitly configured Cowork, Claude Code, and Codex transcript roots.
It makes no model calls. Configure it through the host scheduler at an appropriate
interval. Configuration, databases, and snapshots belong outside source control.

The host database is separate from earlier importers. Existing MCP rows are not
changed. Optional project stores receive matching records based on explicit root
mappings; other work remains unattributed. No project is discovered or enrolled
implicitly. Worktrees need their own approved root mapping.

## Configuration

```json
{
  "database": "/private-data/runmeter/host.db",
  "summary": "/private-data/runmeter/summary.json",
  "since": "2026-09-01T00:00:00Z",
  "sources": [{"kind": "codex", "root": "/user/.codex/sessions"}],
  "projects": [],
  "pricing": {}
}
```

Source kinds are `cowork`, `claude-code`, and `codex`. Each optional project has
`root`, `project_id`, `environment`, and an external `database`. The schema is
created by the engine plus the additive `collector_schema.sql` migration. No
previous rows are deleted. Preserve the database and its WAL in host backups.

## Accounting and privacy

- Native Codex per-response usage events take precedence over cumulative mirrors.
  Legacy counters use positive deltas; resets are reported as unsupported rather
  than guessed. Output already includes reasoning tokens.
- Claude messages are deduplicated by hashed provider message ID. Repeated
  streaming blocks use component maxima. Forked copies do not add another row.
- File fingerprints avoid reparsing unchanged transcripts. Transactions couple
  global imports with the scan checkpoint; interrupted project writes safely
  converge on rerun. Do not run legacy importers against this host database.
- Stored metadata is restricted to the source kind and numeric cache counters.
  Prompts, responses, titles, raw IDs, and transcript paths are never persisted.
  The exporter emits only grouped counts, value, window, and coverage.
- Unavailable rates produce null costs. Optional model pricing must explicitly
  specify the used token categories: `uncached_input`, `cache_read`,
  `cache_write_5m`, `cache_write_1h`, and `output_tokens`, in USD per million.
  Unknown cache lifetimes remain unpriced. Estimates are not subscription charges.
- Automation classification is unknown. The exporter reports unclassified rows
  rather than deriving scheduled versus interactive activity from titles.
- Missing or empty sources, malformed records, contradictory cache totals, and
  unsupported events appear in coverage. Active incomplete trailing lines are
  deferred. Nonpersistent sessions and inaccessible transcripts cannot be collected.

The initial integration verified replay, growth, duplicate forks, both Codex event
families, cache pricing, unknown models, additive migration, project isolation,
and metadata privacy with synthetic fixtures. Snapshot consumers must preserve
coverage and unpriced counts alongside the totals.
