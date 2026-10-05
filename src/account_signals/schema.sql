CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    country TEXT NOT NULL,
    employees INTEGER NOT NULL,
    annual_revenue_usd INTEGER NOT NULL,
    sells_software INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    account_id TEXT NOT NULL REFERENCES accounts (account_id),
    kind TEXT NOT NULL,
    occurred_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts (account_id),
    written_on TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS note_labels (
    note_id TEXT PRIMARY KEY REFERENCES notes (note_id),
    intent TEXT NOT NULL,
    evidence TEXT NOT NULL,
    model TEXT NOT NULL,
    rejected_output INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
    account_id TEXT PRIMARY KEY REFERENCES accounts (account_id),
    fit REAL NOT NULL,
    intent REAL NOT NULL,
    priority REAL NOT NULL,
    tier TEXT NOT NULL,
    reasons TEXT NOT NULL,
    scored_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_calls (
    call_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    purpose TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    cost_usd REAL NOT NULL,
    cached INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    text TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_account ON events (account_id, occurred_on);
CREATE INDEX IF NOT EXISTS idx_notes_account ON notes (account_id, written_on);
