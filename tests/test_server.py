"""
Tests for the runmeter MCP server.

Each test points RUNMETER_DB_PATH at a fresh temp file so the suite never
touches a real store. Tools are exercised through their plain function bodies
(FastMCP leaves the wrapped callables importable), which keeps the tests fast
and free of any transport or client dependency.
"""

import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def srv(tmp_path, monkeypatch):
    """Import server with an isolated DB and pricing override per test."""
    monkeypatch.setenv("RUNMETER_DB_PATH", str(tmp_path / "runmeter.db"))
    monkeypatch.delenv("RUNMETER_PRICING", raising=False)
    module = importlib.import_module("server")
    importlib.reload(module)
    return module


def _record(srv, **kwargs):
    return srv.runmeter_record(srv.RecordInput(**kwargs))


def test_record_computes_cost_from_pricing(srv):
    out = _record(srv, model="claude-sonnet-4", input_tokens=1_000_000, output_tokens=1_000_000)
    # $3/M in + $15/M out = $18 for 1M each.
    assert out["run"]["cost_usd"] == pytest.approx(18.0)
    assert out["run"]["id"] == 1


def test_explicit_cost_wins_over_table(srv):
    out = _record(srv, model="claude-sonnet-4", input_tokens=10, output_tokens=10, cost_usd=0.42)
    assert out["run"]["cost_usd"] == pytest.approx(0.42)


def test_unpriced_model_is_null_and_flagged(srv):
    out = _record(srv, model="mystery-model-x", input_tokens=100, output_tokens=100)
    assert out["run"]["cost_usd"] is None
    assert "not in the pricing table" in out["note"]


def test_pricing_override_file(tmp_path, monkeypatch):
    pricing = tmp_path / "pricing.json"
    pricing.write_text(json.dumps({"mystery-model-x": {"input": 1.0, "output": 2.0}}))
    monkeypatch.setenv("RUNMETER_DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("RUNMETER_PRICING", str(pricing))
    import server
    importlib.reload(server)
    out = server.runmeter_record(
        server.RecordInput(model="mystery-model-x", input_tokens=1_000_000, output_tokens=1_000_000)
    )
    # $1/M in + $2/M out = $3.
    assert out["run"]["cost_usd"] == pytest.approx(3.0)


def test_list_filters_and_paging(srv):
    _record(srv, model="gpt-4o", agent="triage", tags=["prod"])
    _record(srv, model="gpt-4o", agent="triage", tags=["dev"])
    _record(srv, model="claude-haiku-4", agent="summarize", tags=["prod"])

    all_runs = srv.runmeter_list()
    assert all_runs["total"] == 3

    by_model = srv.runmeter_list(model="gpt-4o")
    assert by_model["total"] == 2

    by_tag = srv.runmeter_list(tag="prod")
    assert by_tag["total"] == 2

    paged = srv.runmeter_list(limit=1)
    assert paged["count"] == 1 and paged["total"] == 3


def test_status_validation(srv):
    with pytest.raises(ValueError):
        srv.RecordInput(model="gpt-4o", status="maybe")


def test_summary_groups_by_model_with_error_rate(srv):
    _record(srv, model="gpt-4o", input_tokens=1_000_000, output_tokens=0, status="ok")
    _record(srv, model="gpt-4o", input_tokens=1_000_000, output_tokens=0, status="error")
    _record(srv, model="claude-haiku-4", input_tokens=1_000_000, output_tokens=1_000_000)

    summ = srv.runmeter_summary(group_by="model")
    groups = {g["group"]: g for g in summ["groups"]}
    assert groups["gpt-4o"]["runs"] == 2
    assert groups["gpt-4o"]["error_rate"] == pytest.approx(0.5)
    # Groups sorted by cost desc; totals present.
    assert summ["totals"]["runs"] == 3


def test_summary_group_by_tag_counts_multi_tag_rows(srv):
    _record(srv, model="gpt-4o", tags=["prod", "east"])
    _record(srv, model="gpt-4o", tags=["prod"])
    summ = srv.runmeter_summary(group_by="tag")
    groups = {g["group"]: g for g in summ["groups"]}
    assert groups["prod"]["runs"] == 2
    assert groups["east"]["runs"] == 1


def test_summary_rejects_bad_group_by(srv):
    with pytest.raises(ValueError):
        srv.runmeter_summary(group_by="planet")


def test_get_missing_run(srv):
    out = srv.runmeter_get(999)
    assert out["run"] is None


def test_export_csv_has_header_and_rows(srv):
    _record(srv, model="gpt-4o", input_tokens=5, output_tokens=5)
    out = srv.runmeter_export(fmt="csv")
    lines = out["content"].splitlines()
    assert lines[0].startswith("id,ts,model")
    assert out["count"] == 1


def test_delete_requires_confirm(srv):
    _record(srv, model="gpt-4o")
    guard = srv.runmeter_delete(1, confirm=False)
    assert guard["deleted"] is False
    assert srv.runmeter_list()["total"] == 1

    done = srv.runmeter_delete(1, confirm=True)
    assert done["deleted"] is True
    assert srv.runmeter_list()["total"] == 0


def test_since_relative_window(srv):
    _record(srv, model="gpt-4o")
    # A 24h window includes the just-recorded run; a 0-length parse is rejected.
    assert srv.runmeter_list(since="24h")["total"] == 1
    with pytest.raises(ValueError):
        srv.runmeter_list(since="not-a-window")
