-- Migration 002: Create visits table (one-to-many with devotees)
CREATE TABLE IF NOT EXISTS visits (
    id              SERIAL PRIMARY KEY,
    devotee_id      INTEGER NOT NULL REFERENCES devotees(id) ON DELETE CASCADE,

    location        VARCHAR(200),
    arrival_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    departure_date  DATE,
    purpose         VARCHAR(200),
    notes           TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visits_devotee_id ON visits (devotee_id);
CREATE INDEX IF NOT EXISTS idx_visits_arrival    ON visits (arrival_date DESC);
