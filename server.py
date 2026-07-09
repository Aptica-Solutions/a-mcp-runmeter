#!/usr/bin/env python3
"""
runmeter -- an MCP server for LLM and agent run telemetry.

Give any agent or LLM workflow cost and reliability observability for free.
Record one row per model call (model, tokens, cost, latency, finish reason,
tags), then query and aggregate that telemetry through MCP tools. Cost is
computed automatically from a built-in, overridable pricing table when you do
not pass an explicit figure.

Storage is a local SQLite database. No external service, no credentials, no
network calls. Point RUNMETER_DB_PATH somewhere durable and the same store
serves every agent on the machine.

Environment variables (all optional):
    RUNMETER_DB_PATH    Path to the SQLite file.
                        Default: ~/.runmeter/runmeter.db
    RUNMETER_PRICING    Path to a JSON file that overrides or extends the
                        built-in per-model pricing table. Shape:
                            { "model-name": {"input": 3.0, "output": 15.0} }
                        Values are USD per 1,000,000 tokens.

Design notes:
    - Tools are prefixed `runmeter_` for discoverability.
    - Read tools carry readOnlyHint; the single delete tool carries
      destructiveHint and requires an explicit confirm flag.
    - Every tool returns both human-readable text and structured content.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

mcp = FastMCP("runmeter")

# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------
# USD per 1,000,000 tokens. Approximate list prices meant as sensible defaults,
# not a billing source of truth. Override or extend via RUNMETER_PRICING.
_DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4":      {"input": 15.0, "output": 75.0},
    "claude-sonnet-4":    {"input": 3.0,  "output": 15.0},
    "claude-haiku-4":     {"input": 0.80, "output": 4.0},
    "gpt-4o":             {"input": 2.50, "output": 10.0},
    "gpt-4o-mini":        {"input": 0.15, "output": 0.60},
    "gpt-4.1":            {"input": 2.0,  "output": 8.0},
    "o3":                 {"input": 2.0,  "output": 8.0},
    "gemini-2.5-pro":     {"input": 1.25, "output": 10.0},
    "gemini-2.5-flash":   {"input": 0.30, "output": 2.50},
}


def _load_pricing() -> dict[str, dict[str, float]]:
    """Built-in pricing merged with the optional RUNMETER_PRICING override file."""
    pricing = {k: dict(v) for k, v in _DEFAULT_PRICING.items()}
    override_path = os.environ.get("RUNMETER_PRICING", "").strip()
    if override_path:
        try:
            data = json.loads(Path(override_path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"RUNMETER_PRICING is set to {override_path!r} but could not be "
                f"read as JSON: {exc}. Expected {{'model': {{'input': n, 'output': n}}}}."
            ) from exc
        for model, rates in data.items():
            pricing[model] = {
                "input": float(rates["input"]),
                "output": float(rates["output"]),
            }
    return pricing


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Return computed USD cost for a run, or None if the model is unpriced."""
    pricing = _load_pricing()
    rates = pricing.get(model)
    if rates is None:
        return None
    cost = (input_tokens / 1_000_000) * rates["input"] + (
        output_tokens / 1_000_000
    ) * rates["output"]
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _db_path() -> Path:
    raw = os.environ.get("RUNMETER_DB_PATH", "").strip()
    path = Path(raw).expanduser() if raw else Path.home() / ".runmeter" / "runmeter.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            TEXT    NOT NULL,
            model         TEXT    NOT NULL,
            agent         TEXT,
            input_tokens  INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd      REAL,
            latency_ms    REAL,
            finish_reason TEXT,
            status        TEXT    NOT NULL DEFAULT 'ok',
            tags          TEXT,
            metadata      TEXT
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_ts ON runs(ts);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_agent ON runs(agent);")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
    d["metadata"] = json.loads(d["metadata"]) if d.get("metadata") else {}
    return d


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_since(since: Optional[str]) -> Optional[str]:
    """
    Accept an ISO-8601 timestamp or a relative window like '24h', '7d', '30m',
    '2w'. Return an ISO cutoff string, or None for no lower bound.
    """
    if not since:
        return None
    since = since.strip().lower()
    units = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    if since and since[-1] in units and since[:-1].isdigit():
        amount = int(since[:-1])
        delta = timedelta(**{units[since[-1]]: amount})
        return (datetime.now(timezone.utc) - delta).isoformat(timespec="seconds")
    # Otherwise treat as an explicit ISO timestamp.
    try:
        datetime.fromisoformat(since)
    except ValueError as exc:
        raise ValueError(
            f"Could not parse since={since!r}. Use an ISO timestamp "
            "(2026-07-01T00:00:00+00:00) or a relative window like 24h, 7d, 2w."
        ) from exc
    return since


# ---------------------------------------------------------------------------
# Tool input models
# ---------------------------------------------------------------------------

class RecordInput(BaseModel):
    model: str = Field(..., description="Model identifier, e.g. 'claude-sonnet-4'.")
    input_tokens: int = Field(0, ge=0, description="Prompt/input token count.")
    output_tokens: int = Field(0, ge=0, description="Completion/output token count.")
    cost_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Explicit run cost in USD. If omitted, computed from the "
        "pricing table when the model is known.",
    )
    latency_ms: Optional[float] = Field(
        None, ge=0, description="End-to-end latency in milliseconds."
    )
    finish_reason: Optional[str] = Field(
        None, description="e.g. 'stop', 'length', 'tool_use', 'error'."
    )
    agent: Optional[str] = Field(
        None, description="Logical agent or workflow name that made the call."
    )
    status: str = Field("ok", description="'ok' or 'error'.")
    tags: list[str] = Field(
        default_factory=list, description="Free-form labels for later grouping."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary JSON-serializable extra fields."
    )

    @field_validator("status")
    @classmethod
    def _status_ok(cls, v: str) -> str:
        v = (v or "ok").strip().lower()
        if v not in {"ok", "error"}:
            raise ValueError("status must be 'ok' or 'error'.")
        return v


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    annotations={
        "title": "Record a model run",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
def runmeter_record(run: RecordInput) -> dict[str, Any]:
    """
    Record a single LLM/agent run and return the stored row.

    Cost is taken from `cost_usd` when provided; otherwise it is computed from
    the built-in pricing table (USD per 1M tokens) when the model is known. If
    the model is unpriced and no cost is given, cost is stored as null and the
    response notes that the model is unpriced so you can extend the table.
    """
    cost = run.cost_usd
    priced = True
    if cost is None:
        cost = _compute_cost(run.model, run.input_tokens, run.output_tokens)
        priced = cost is not None

    ts = _now_iso()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO runs
                (ts, model, agent, input_tokens, output_tokens, cost_usd,
                 latency_ms, finish_reason, status, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                run.model,
                run.agent,
                run.input_tokens,
                run.output_tokens,
                cost,
                run.latency_ms,
                run.finish_reason,
                run.status,
                json.dumps(run.tags) if run.tags else None,
                json.dumps(run.metadata) if run.metadata else None,
            ),
        )
        run_id = cur.lastrowid
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()

    record = _row_to_dict(row)
    note = (
        f"Recorded run #{run_id} for {run.model}: "
        f"{run.input_tokens} in / {run.output_tokens} out tokens, "
        f"cost {'$' + format(cost, '.6f') if cost is not None else 'unpriced'}."
    )
    if not priced:
        note += (
            f" Model {run.model!r} is not in the pricing table; pass cost_usd or "
            "set RUNMETER_PRICING to price it."
        )
    return {"note": note, "run": record}


@mcp.tool(
    annotations={
        "title": "Get one run",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def runmeter_get(run_id: int) -> dict[str, Any]:
    """Return the full stored row for a single run id."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return {
            "note": f"No run found with id {run_id}. Use runmeter_list to browse ids.",
            "run": None,
        }
    return {"note": f"Run #{run_id}.", "run": _row_to_dict(row)}


@mcp.tool(
    annotations={
        "title": "List runs",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def runmeter_list(
    model: Optional[str] = None,
    agent: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List runs newest-first with optional filters.

    Filters: model, agent, status ('ok'/'error'), tag (matches any run carrying
    that tag), and since (ISO timestamp or relative window like '24h', '7d').
    Use limit/offset to page. Returns up to `limit` rows plus the total count
    matching the filters so you know whether to page further.
    """
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    cutoff = _parse_since(since)

    where: list[str] = []
    params: list[Any] = []
    if model:
        where.append("model = ?")
        params.append(model)
    if agent:
        where.append("agent = ?")
        params.append(agent)
    if status:
        where.append("status = ?")
        params.append(status.strip().lower())
    if cutoff:
        where.append("ts >= ?")
        params.append(cutoff)
    if tag:
        where.append("tags LIKE ?")
        params.append(f'%"{tag}"%')
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    with _connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM runs {clause}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"SELECT * FROM runs {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()

    runs = [_row_to_dict(r) for r in rows]
    return {
        "note": f"{len(runs)} of {total} matching run(s) shown (offset {offset}).",
        "total": total,
        "count": len(runs),
        "offset": offset,
        "runs": runs,
    }


@mcp.tool(
    annotations={
        "title": "Summarize cost and reliability",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def runmeter_summary(
    group_by: str = "model",
    since: Optional[str] = None,
) -> dict[str, Any]:
    """
    Aggregate telemetry into cost and reliability rollups.

    group_by is one of: 'model', 'agent', 'finish_reason', 'day', or 'tag'.
    Optional `since` limits the window (ISO timestamp or relative like '30d').
    Each group reports run count, total input/output tokens, total cost,
    average latency, and error rate. Groups are sorted by total cost descending.
    """
    valid = {"model", "agent", "finish_reason", "day", "tag"}
    group_by = group_by.strip().lower()
    if group_by not in valid:
        raise ValueError(f"group_by must be one of {sorted(valid)}, got {group_by!r}.")
    cutoff = _parse_since(since)

    where = "WHERE ts >= ?" if cutoff else ""
    params: list[Any] = [cutoff] if cutoff else []

    with _connect() as conn:
        rows = [_row_to_dict(r) for r in conn.execute(
            f"SELECT * FROM runs {where}", params
        ).fetchall()]

    # Aggregate in Python so 'tag' (many-per-row) and 'day' are handled uniformly.
    buckets: dict[str, dict[str, Any]] = {}

    def bucket(key: str) -> dict[str, Any]:
        return buckets.setdefault(
            key,
            {
                "group": key,
                "runs": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "errors": 0,
                "_latency_sum": 0.0,
                "_latency_n": 0,
            },
        )

    for r in rows:
        if group_by == "tag":
            keys = r["tags"] or ["(untagged)"]
        elif group_by == "day":
            keys = [r["ts"][:10]]
        else:
            keys = [r.get(group_by) or "(none)"]
        for key in keys:
            b = bucket(str(key))
            b["runs"] += 1
            b["input_tokens"] += r["input_tokens"] or 0
            b["output_tokens"] += r["output_tokens"] or 0
            b["cost_usd"] += r["cost_usd"] or 0.0
            if r["status"] == "error":
                b["errors"] += 1
            if r["latency_ms"] is not None:
                b["_latency_sum"] += r["latency_ms"]
                b["_latency_n"] += 1

    groups = []
    for b in buckets.values():
        n_lat = b.pop("_latency_n")
        lat_sum = b.pop("_latency_sum")
        b["cost_usd"] = round(b["cost_usd"], 6)
        b["avg_latency_ms"] = round(lat_sum / n_lat, 2) if n_lat else None
        b["error_rate"] = round(b["errors"] / b["runs"], 4) if b["runs"] else 0.0
        groups.append(b)
    groups.sort(key=lambda g: g["cost_usd"], reverse=True)

    totals = {
        "runs": sum(g["runs"] for g in groups),
        "cost_usd": round(sum(g["cost_usd"] for g in groups), 6),
        "input_tokens": sum(g["input_tokens"] for g in groups),
        "output_tokens": sum(g["output_tokens"] for g in groups),
        "errors": sum(g["errors"] for g in groups),
    }
    note = (
        f"{totals['runs']} run(s) grouped by {group_by}: "
        f"${totals['cost_usd']:.4f} total, {totals['errors']} error(s)."
    )
    return {"note": note, "group_by": group_by, "totals": totals, "groups": groups}


@mcp.tool(
    annotations={
        "title": "Export runs",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def runmeter_export(
    fmt: str = "json",
    since: Optional[str] = None,
    limit: int = 1000,
) -> dict[str, Any]:
    """
    Export raw runs as a JSON array or CSV string for external analysis.

    fmt is 'json' or 'csv'. Optional `since` limits the window. Newest-first,
    capped at `limit` rows (max 10000).
    """
    fmt = fmt.strip().lower()
    if fmt not in {"json", "csv"}:
        raise ValueError("fmt must be 'json' or 'csv'.")
    limit = max(1, min(limit, 10_000))
    cutoff = _parse_since(since)

    where = "WHERE ts >= ?" if cutoff else ""
    params: list[Any] = [cutoff] if cutoff else []
    with _connect() as conn:
        rows = [_row_to_dict(r) for r in conn.execute(
            f"SELECT * FROM runs {where} ORDER BY id DESC LIMIT ?",
            [*params, limit],
        ).fetchall()]

    if fmt == "json":
        payload = json.dumps(rows, indent=2)
    else:
        cols = [
            "id", "ts", "model", "agent", "input_tokens", "output_tokens",
            "cost_usd", "latency_ms", "finish_reason", "status",
        ]
        lines = [",".join(cols)]
        for r in rows:
            lines.append(
                ",".join("" if r.get(c) is None else str(r.get(c)) for c in cols)
            )
        payload = "\n".join(lines)

    return {
        "note": f"Exported {len(rows)} run(s) as {fmt}.",
        "format": fmt,
        "count": len(rows),
        "content": payload,
    }


@mcp.tool(
    annotations={
        "title": "Delete a run",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
    }
)
def runmeter_delete(run_id: int, confirm: bool = False) -> dict[str, Any]:
    """
    Delete a single run by id. Requires confirm=true to actually remove it.

    This is the only destructive tool. It scopes to one id and refuses to run
    without an explicit confirm, so it cannot wipe the store by accident.
    """
    if not confirm:
        return {
            "note": f"Refusing to delete run #{run_id} without confirm=true. "
            "Re-issue with confirm=true to proceed.",
            "deleted": False,
        }
    with _connect() as conn:
        cur = conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        removed = cur.rowcount
    if removed == 0:
        return {"note": f"No run #{run_id} to delete.", "deleted": False}
    return {"note": f"Deleted run #{run_id}.", "deleted": True}


if __name__ == "__main__":
    mcp.run()
