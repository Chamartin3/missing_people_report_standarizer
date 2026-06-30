"""Create the pgvector extension, tables, and the HNSW index. Idempotent.

Run once before the extract/identify scripts:
    docker compose run --rm app python scripts/init_db.py
"""

from facefinder.data import init_db

if __name__ == "__main__":
    init_db()
    print("db initialised: extension + tables + hnsw index")
