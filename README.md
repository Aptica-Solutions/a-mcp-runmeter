# runmeter

[![CI](https://github.com/Aptica-Solutions/a-mcp-runmeter/actions/workflows/ci.yml/badge.svg)](https://github.com/Aptica-Solutions/a-mcp-runmeter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

An MCP server that gives any LLM or agent workflow cost and reliability observability for free.

Record one row per model call (model, tokens, cost, latency, finish reason, tags), then query and aggregate that telemetry through MCP tools. Cost is computed automatically from a built-in, overridable pricing table when you do not pass an explicit figure. Storage is a local SQLite file. No external service, no credentials, no network calls.

Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk). Works with any MCP client (Claude Code, Claude Desktop, or your own agent) over stdio.

Companion project: [a-agentic-delivery-pipeline](https://github.com/Aptica-Solutions/a-agentic-delivery-pipeline) is an AI-native, skills-driven delivery pipeline that emits its per-stage telemetry to runmeter.

## Why

Most agent stacks can tell you what an agent did, but not what it cost or how often it failed. Teams end up bolting on a spreadsheet or a bespoke logging table per project. runmeter makes per-run cost and reliability a first-class, queryable signal that every agent on the machine writes to the same way. It is the "cost-per-task economics" and "evaluation and performance" discipline that production agent work needs, packaged as a drop-in MCP server.

## Tools

| Tool | Purpose | Hint |
|------|---------|------|
| `runmeter_record` | Record one model/agent run; auto-computes cost when the model is priced | write |
| `runmeter_get` | Fetch a single run by id | read-only |
| `runmeter_list` | List runs newest-first with filters (model, agent, tag, status, since) and paging | read-only |
| `runmeter_summary` | Roll up cost, tokens, avg latency, and error rate grouped by model / agent / finish_reason / day / tag | read-only |
| `runmeter_export` | Export raw runs as JSON or CSV for external analysis | read-only |
| `runmeter_delete` | Delete one run by id; requires `confirm=true` | destructive |

Every tool returns both a human-readable `note` and structured content.

## Install

```bash
git clone https://github.com/Aptica-Solutions/a-mcp-runmeter.git
cd a-mcp-runmeter
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 server.py
```

### Connect from an MCP client

Point your client at `server.py` over stdio. Example (`claude_mcp_config.json`):

```json
{
  "mcpServers": {
    "runmeter": {
      "command": "python3",
      "args": ["/absolute/path/to/a-mcp-runmeter/server.py"],
      "env": { "RUNMETER_DB_PATH": "~/.runmeter/runmeter.db" }
    }
  }
}
```

## Configuration

All optional. runmeter runs with zero configuration.

| Variable | Default | Purpose |
|----------|---------|---------|
| `RUNMETER_DB_PATH` | `~/.runmeter/runmeter.db` | SQLite telemetry store location |
| `RUNMETER_PRICING` | built-in table | JSON file overriding/extending per-model pricing |

Pricing override file shape (USD per 1,000,000 tokens):

```json
{
  "my-fine-tuned-model": { "input": 3.0, "output": 15.0 }
}
```

The built-in table ships sensible list-price defaults for common Claude, GPT, and Gemini models. They are convenience defaults, not a billing source of truth; override them for anything you meter seriously.

## Example flow

An agent records each call as it goes:

```jsonc
// runmeter_record
{ "run": { "model": "claude-sonnet-4", "input_tokens": 8200, "output_tokens": 640,
           "latency_ms": 1830, "finish_reason": "stop", "agent": "discharge-summarizer",
           "tags": ["prod", "east"] } }
// -> cost auto-computed at $3/M in + $15/M out = $0.034200
```

Then you ask for a rollup:

```jsonc
// runmeter_summary  { "group_by": "model", "since": "7d" }
// -> per-model run count, tokens, total cost, avg latency, and error rate,
//    sorted by cost descending, with grand totals.
```

`since` accepts an ISO timestamp or a relative window: `30m`, `24h`, `7d`, `2w`.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

The test suite points `RUNMETER_DB_PATH` at a throwaway file per test, so it never touches a real store.

## Design notes

- Tools use consistent `runmeter_` prefixes for discoverability.
- Read tools carry `readOnlyHint`; the single delete tool carries `destructiveHint` and refuses to run without an explicit `confirm`, so it cannot wipe the store by accident.
- Aggregation runs in Python so multi-tag rows and per-day buckets are handled uniformly, keeping the SQL simple and portable.
- No ORM and one dependency beyond the MCP SDK and Pydantic, by design: low total cost of ownership and easy to audit.

## License

MIT. See [LICENSE](LICENSE).

---

Built by [Aptica Solutions](https://github.com/Aptica-Solutions).
