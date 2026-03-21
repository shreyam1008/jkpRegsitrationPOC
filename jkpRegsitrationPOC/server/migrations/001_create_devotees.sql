-- Migration 001: Create devotees table
CREATE TABLE IF NOT EXISTS devotees (
    id                    SERIAL PRIMARY KEY,
    satsangi_id           VARCHAR(10) NOT NULL UNIQUE,

    -- Personal
    first_name            VARCHAR(100) NOT NULL,
    last_name             VARCHAR(100) NOT NULL,
    phone_number          VARCHAR(20)  NOT NULL,
    email                 VARCHAR(200),
    gender                VARCHAR(10),
    date_of_birth         DATE,
    age                   INTEGER,
    nationality           VARCHAR(50)  NOT NULL DEFAULT 'Indian',
    special_category      VARCHAR(50),
    nick_name             VARCHAR(100),
    pan                   VARCHAR(20),

    -- Government ID
    govt_id_type          VARCHAR(50),
    govt_id_number        VARCHAR(80),
    id_expiry_date        DATE,
    id_issuing_country    VARCHAR(50),

    -- Address
    country               VARCHAR(50)  NOT NULL DEFAULT 'India',
    address               TEXT,
    city                  VARCHAR(100),
    district              VARCHAR(100),
    state                 VARCHAR(100),
    pincode               VARCHAR(10),

    -- Other
    emergency_contact     VARCHAR(20),
    introducer            VARCHAR(200),
    introduced_by         VARCHAR(30),
    ex_center_satsangi_id VARCHAR(20),
    print_on_card         BOOLEAN NOT NULL DEFAULT FALSE,
    has_room_in_ashram    BOOLEAN NOT NULL DEFAULT FALSE,
    banned                BOOLEAN NOT NULL DEFAULT FALSE,
    first_timer           BOOLEAN NOT NULL DEFAULT FALSE,
    date_of_first_visit   DATE,
    notes                 TEXT,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_devotees_satsangi_id ON devotees (satsangi_id);
CREATE INDEX IF NOT EXISTS idx_devotees_name        ON devotees (LOWER(first_name), LOWER(last_name));
CREATE INDEX IF NOT EXISTS idx_devotees_phone       ON devotees (phone_number);
CREATE INDEX IF NOT EXISTS idx_devotees_email       ON devotees (LOWER(email)) WHERE email IS NOT NULL;
