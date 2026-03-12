"""PostgreSQL connection and schema management."""

import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "jkp_reg_poc",
    "user": "postgres",
    "password": "postgres",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS satsangis (
    satsangi_id         VARCHAR(8) PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    phone_number        VARCHAR(20) NOT NULL,
    age                 INTEGER,
    date_of_birth       VARCHAR(20),
    pan                 VARCHAR(20),
    gender              VARCHAR(10),
    special_category    VARCHAR(30),
    nationality         VARCHAR(30) NOT NULL DEFAULT 'Indian',
    govt_id_type        VARCHAR(30),
    govt_id_number      VARCHAR(50),
    id_expiry_date      VARCHAR(20),
    id_issuing_country  VARCHAR(30),
    nick_name           VARCHAR(100),
    print_on_card       BOOLEAN NOT NULL DEFAULT FALSE,
    introducer          VARCHAR(200),
    country             VARCHAR(30) NOT NULL DEFAULT 'India',
    address             TEXT,
    city                VARCHAR(100),
    district            VARCHAR(100),
    state               VARCHAR(100),
    pincode             VARCHAR(10),
    emergency_contact   VARCHAR(20),
    ex_center_satsangi_id VARCHAR(20),
    introduced_by       VARCHAR(30),
    has_room_in_ashram  BOOLEAN NOT NULL DEFAULT FALSE,
    email               VARCHAR(200),
    banned              BOOLEAN NOT NULL DEFAULT FALSE,
    first_timer         BOOLEAN NOT NULL DEFAULT FALSE,
    date_of_first_visit VARCHAR(20),
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_satsangis_name
    ON satsangis (LOWER(first_name), LOWER(last_name));
CREATE INDEX IF NOT EXISTS idx_satsangis_phone
    ON satsangis (phone_number);
CREATE INDEX IF NOT EXISTS idx_satsangis_email
    ON satsangis (LOWER(email)) WHERE email IS NOT NULL;
"""


def get_connection():
    """Get a new database connection."""
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Create the satsangis table if it doesn't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        logger.info("Database schema initialized successfully")
    finally:
        conn.close()
