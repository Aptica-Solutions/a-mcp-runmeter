-- Additive collector migration. Existing MCP and imported records remain intact.
CREATE TABLE IF NOT EXISTS collector_keys (
    key TEXT PRIMARY KEY,
    run_id INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS collector_run_id ON collector_keys(run_id);
CREATE TABLE IF NOT EXISTS collector_files (
    key TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    health TEXT NOT NULL
);
