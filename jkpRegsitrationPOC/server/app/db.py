"""PostgreSQL connection and migration runner."""

import logging
import pathlib
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "jkp_reg_poc_rest",
    "user": "postgres",
    "password": "postgres",
}

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "migrations"


def get_connection():
    """Get a new database connection."""
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Run all pending migrations in order."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Ensure migration tracking table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    filename VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            conn.commit()

            # Get already-applied migrations
            cur.execute("SELECT filename FROM _migrations ORDER BY filename;")
            applied = {row[0] for row in cur.fetchall()}

            # Run each .sql file in order
            sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
            for sql_file in sql_files:
                if sql_file.name in applied:
                    continue
                logger.info("Running migration: %s", sql_file.name)
                cur.execute(sql_file.read_text())
                cur.execute(
                    "INSERT INTO _migrations (filename) VALUES (%s);",
                    (sql_file.name,),
                )
                conn.commit()
                logger.info("  ✓ %s applied", sql_file.name)

        logger.info("Database migrations complete (jkp_reg_poc_rest)")
    finally:
        conn.close()
