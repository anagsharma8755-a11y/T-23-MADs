"""Emit the current SQLAlchemy metadata as a secure Supabase migration."""
from pathlib import Path
import sys

from sqlalchemy import create_mock_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db import Base  # noqa: E402
from app import models  # noqa: E402,F401


statements: list[str] = []


def capture(sql, *_, **__):
    rendered = str(sql.compile(dialect=engine.dialect)).strip()
    if rendered:
        statements.append(rendered + ";")


engine = create_mock_engine("postgresql+psycopg://", capture)
Base.metadata.create_all(engine)

header = """CREATE SCHEMA IF NOT EXISTS mads AUTHORIZATION postgres;
REVOKE ALL ON SCHEMA mads FROM PUBLIC, anon, authenticated;
SET search_path TO mads, public;
"""
footer = """
REVOKE ALL ON ALL TABLES IN SCHEMA mads FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA mads FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA mads REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA mads REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
"""
print(header + "\n".join(statements) + footer)
