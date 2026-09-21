"""Thin persistent MCP adapter. Call once per provider result, never per retry of telemetry."""
from contextlib import AsyncExitStack
import importlib.util
from pathlib import Path


class Recorder:
    def __init__(self, root=None, scope="application"):
        if scope not in ("application", "development"):
            raise ValueError("scope must be application or development")
        self.root, self.scope = root, scope
        self.session = None

    async def __aenter__(self):
        spec = importlib.util.spec_from_file_location("aptica_runmeter_launcher", Path(__file__).with_name("launch.py"))
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        launch = launcher.settings(self.root, self.scope)
        self.stack = AsyncExitStack()
        if launch is None:
            return self
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        self.config, command, args, env = launch
        try:
            read, write = await self.stack.enter_async_context(stdio_client(StdioServerParameters(command=command, args=args, env=env)))
            self.session = await self.stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
        except BaseException:
            await self.stack.aclose()
            raise
        return self

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)

    async def record(self, *, model, input_tokens, output_tokens, cost_usd=None,
                     latency_ms=None, finish_reason=None, status="ok"):
        if self.session is None:
            return None
        run = {"model": model, "input_tokens": input_tokens, "output_tokens": output_tokens,
               "status": status, "agent": self.config["project_id"],
               "tags": [f"project:{self.config['project_id']}",
                        f"environment:{self.config['environment']}", f"scope:{self.scope}"]}
        for key, value in (("cost_usd", cost_usd), ("latency_ms", latency_ms), ("finish_reason", finish_reason)):
            if value is not None:
                run[key] = value
        result = await self.session.call_tool("runmeter_record", {"run": run})
        if result.isError:
            raise RuntimeError("Runmeter rejected telemetry; inspect collector health")
        return result
