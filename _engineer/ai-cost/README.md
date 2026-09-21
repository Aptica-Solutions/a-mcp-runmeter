# Optional AI cost tracking

The onboarding survey is the configuration source. After confirming it, run
`python _engineer/ai-cost/configure.py` from the project root. The standard
tooling initializer also applies an existing survey choice. This generates
`.aptica/ai-cost.json` and manages only the `aptica-runmeter` entry in `.mcp.json`.
It preserves all other MCP servers and refuses to overwrite a user-modified
entry. Re-running is idempotent. Choosing `none` removes the owned registration,
does not start a process, and never deletes existing telemetry.

## Architecture

Runmeter is consumed from its public standalone repository at a full commit
hash. The template distributes configuration, a launcher, and a small MCP
adapter; it does not copy the engine. Update the pinned commit deliberately in
`configure.py`, validate it, and reapply configuration through the existing
template release process. No new repository synchronization service is used.

Install `uv` on the host and make it available to the MCP client's process.
Clients that read `.mcp.json` can start the generated registration after their
normal trust step. Other clients should register the same launcher using their
native project/server settings. Configuration never edits global client state.

The store defaults to the operating system's user data directory, under
`Aptica/runmeter/<project_id>/<environment>/<scope>.db`, outside source control.
Use `RUNMETER_DB_PATH` to select another approved external store and
`RUNMETER_PRICING` for a pricing file outside source. Separate projects and
environments by default; share only when their access and retention rules allow
it. Retention is an operator policy; this setup never silently deletes records.

## Collection is separate from enablement

`development` configures the assistant-side MCP collector. An assistant does
not necessarily receive authoritative token usage for its own calls. Do not
invent usage or ask it to estimate its own bill. Use an approved assistant
transcript/provider collector to supply actual counts. Registering MCP alone
does not intercept every assistant call.

`application` enables a thin integration for calls made by the delivered app.
Use `Recorder` from `recorder.py` in a persistent async context, call the model
provider, then pass that response's actual `model`, `input_tokens`, and
`output_tokens` to `await recorder.record(...)`. Import this adapter with the
application's normal module loader and include `mcp>=1.0,<2` in that app's
dependency lock only when this integration is selected. No dependency is added
to disabled applications. Non-Python apps can use the same MCP tool contract
with their existing MCP SDK.

The adapter sets project, environment, and scope labels deterministically.
It accepts no prompts, response bodies, user identifiers, or arbitrary metadata.
For `both`, runtime calls and development calls use distinct stores by default.
Treat costs computed from configured rates as API-equivalent estimates, not
subscription charges. Supply explicit provider cost only when known. Providers
with cache-token pricing require the caller to calculate an explicit correct
cost or provide a supported pricing collector; do not count cached tokens as
ordinary input and claim billing accuracy.

The recorder raises on collection failure so the application can apply its
documented telemetry-failure policy. Runmeter recording is not idempotent.
Do not blindly retry an uncertain write; a retry can double-count a model call.
The setup does not claim application instrumentation is complete until an
integration test demonstrates a real provider response being recorded once.

## Validation

Run `python -m unittest discover -s _engineer/ai-cost/tests` in the template.
The tests use synthetic surveys, temporary source/data directories, and a fake
MCP session. A separate opt-in smoke check can launch the pinned public package
against a temporary database; it must not use a production telemetry store.
