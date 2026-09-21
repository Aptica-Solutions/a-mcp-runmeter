"""Apply the explicit AI cost choice in ONBOARDING.md; no engine is copied."""
import argparse
import json
import re
from pathlib import Path

ENGINE = "git+https://github.com/Aptica-Solutions/a-mcp-runmeter.git@9ea1a258b6e19537218ef87bb9edc5041ffa1ac9"
SERVER_NAME = "aptica-runmeter"
SERVER = {"command": "uv", "args": ["run", "--script", "_engineer/ai-cost/launch.py"]}
MODES = {"none", "development", "application", "both"}


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def apply(root):
    root = Path(root).resolve()
    survey = root / "ONBOARDING.md"
    if not survey.exists():
        return "AI cost tracking: pending onboarding; nothing configured."
    text = survey.read_text(encoding="utf-8")
    blocks = re.findall(r"<!-- AI_COST_TRACKING_START -->\s*```json\s*(.*?)\s*```\s*<!-- AI_COST_TRACKING_END -->", text, re.S)
    if not blocks:
        return "AI cost tracking: no explicit choice; existing configuration unchanged."
    if len(blocks) != 1:
        raise ValueError("Exactly one AI cost configuration block is required")
    choice = json.loads(blocks[0])
    if not isinstance(choice, dict) or set(choice) != {"mode", "project_id", "environment"}:
        raise ValueError("AI cost configuration requires only mode, project_id, environment")
    if choice["mode"] not in MODES:
        raise ValueError("Invalid AI cost tracking mode")
    if choice["mode"] != "none":
        for field in ("project_id", "environment"):
            if not isinstance(choice[field], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", choice[field]):
                raise ValueError(f"{field} must be a stable lowercase identifier")
    state_path = root / ".aptica" / "ai-cost.json"
    manifest_path = root / ".mcp.json"
    previous = read_json(state_path, {})
    manifest = read_json(manifest_path, {"mcpServers": {}})
    servers = manifest.setdefault("mcpServers", {})
    existing = servers.get(SERVER_NAME)
    if existing is not None and (not previous.get("managed_server") or existing != previous["managed_server"]):
        raise ValueError("Existing aptica-runmeter registration is not owned by this setup; resolve it explicitly")
    if choice["mode"] == "none":
        servers.pop(SERVER_NAME, None)
    else:
        servers[SERVER_NAME] = SERVER
    config = {"schema_version": 1, **choice, "engine": ENGINE,
              "managed_server": SERVER if choice["mode"] != "none" else None}
    write_json(manifest_path, manifest)
    write_json(state_path, config)
    return f"AI cost tracking configured: {choice['mode']}. Existing telemetry is never deleted."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        print(apply(args.root))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"AI cost configuration failed: {exc}\n")


if __name__ == "__main__":
    main()
