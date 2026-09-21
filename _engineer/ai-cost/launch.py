# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Launch the pinned standalone engine with a project-isolated external store."""
import json
import os
from pathlib import Path
import shutil
import sys


def settings(root=None, scope="development"):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    config = json.loads((root / ".aptica" / "ai-cost.json").read_text(encoding="utf-8"))
    mode = config["mode"]
    if mode == "none" or mode not in (scope, "both"):
        return None
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("Install uv before enabling AI cost tracking")
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    directory = base / "Aptica" / "runmeter" / config["project_id"] / config["environment"]
    database = Path(os.environ.get("RUNMETER_DB_PATH", directory / f"{scope}.db")).expanduser().resolve()
    if database.is_relative_to(root.resolve()):
        raise ValueError("Telemetry storage must be outside the source checkout")
    database.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(database.parent, 0o700)
    env = dict(os.environ, RUNMETER_DB_PATH=str(database))
    return config, uv, ["tool", "run", "--from", config["engine"], "runmeter-mcp"], env


def main():
    config_path = Path(__file__).resolve().parents[2] / ".aptica" / "ai-cost.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    scope = "application" if config["mode"] == "application" else "development"
    launch = settings(scope=scope)
    if launch is None:
        raise SystemExit("AI cost tracking is disabled")
    _, executable, args, env = launch
    os.execve(executable, [executable, *args], env)


if __name__ == "__main__":
    main()
