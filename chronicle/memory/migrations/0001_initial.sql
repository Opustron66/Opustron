-- Bi-temporal fact store.
--
-- Valid time: valid_from / valid_to, half-open [valid_from, valid_to). NULL valid_from means
-- "since before we know"; NULL valid_to means "still true".
-- Transaction time: every change to a fact's validity writes a new row version. recorded_at is
-- when Chronicle learned that version, replaced_at when a newer version took over. Rows are
-- never deleted or updated except to set replaced_at.
-- Timestamps are fixed-width UTC ISO strings, so text comparison orders them correctly.

CREATE TABLE facts (
    row_id        INTEGER PRIMARY KEY,
    fact_id       TEXT NOT NULL,
    kind          TEXT NOT NULL,              -- 'claim' (from P1) or 'note' (free text, Hermes)
    subject       TEXT NOT NULL,
    predicate     TEXT NOT NULL,
    object        TEXT NOT NULL,
    subject_key   TEXT NOT NULL,              -- casefolded, whitespace-collapsed
    object_key    TEXT NOT NULL,
    content       TEXT NOT NULL,
    spo_key       TEXT NOT NULL,              -- normalised subject|predicate|object[@event_at]
    event_at      TEXT,                       -- the date a deadline/scheduled_for fact points at
    slot          TEXT,                       -- supersession slot; NULL = never auto-superseded
    value_key     TEXT,                       -- what competes inside the slot
    valid_from    TEXT,
    valid_to      TEXT,
    granularity   TEXT NOT NULL DEFAULT 'day', -- 'day' or 'instant'
    superseded_by TEXT,                       -- fact_id that closed this one, if any
    end_reason    TEXT,                       -- 'stated' | 'superseded' | 'retired' | NULL
    confidence    REAL NOT NULL DEFAULT 1.0,
    recorded_at   TEXT NOT NULL,
    replaced_at   TEXT
);
CREATE INDEX facts_current ON facts (fact_id) WHERE replaced_at IS NULL;
CREATE INDEX facts_slot ON facts (slot) WHERE replaced_at IS NULL;
CREATE INDEX facts_subject ON facts (subject_key) WHERE replaced_at IS NULL;
CREATE INDEX facts_object ON facts (object_key) WHERE replaced_at IS NULL;
CREATE INDEX facts_spo ON facts (spo_key) WHERE replaced_at IS NULL;

-- Every document statement behind a fact: the opening claim, restatements and closing claims.
CREATE TABLE fact_sources (
    source_id   INTEGER PRIMARY KEY,
    fact_id     TEXT NOT NULL,
    claim_hash  TEXT NOT NULL UNIQUE,         -- makes re-ingesting the same claim a no-op
    role        TEXT NOT NULL,                -- 'opened' | 'restated' | 'closed'
    doc_id      TEXT NOT NULL,
    uri         TEXT,
    quote       TEXT NOT NULL,
    observed_at TEXT,
    valid_from  TEXT,                         -- as stated by this source
    valid_to    TEXT,
    confidence  REAL NOT NULL DEFAULT 1.0,
    recorded_at TEXT NOT NULL
);
CREATE INDEX fact_sources_fact ON fact_sources (fact_id);
CREATE INDEX fact_sources_doc ON fact_sources (doc_id);

CREATE TABLE entities (
    entity_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    key         TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL DEFAULT 'unknown',
    first_seen  TEXT,
    recorded_at TEXT NOT NULL
);

CREATE TABLE entity_aliases (
    alias     TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities (entity_id)
);
