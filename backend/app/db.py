from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

class Base(DeclarativeBase): pass

if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    # Supabase's transaction pooler is the correct endpoint for serverless
    # functions. Keep the per-instance pool deliberately small and disable
    # psycopg prepared statements, which are incompatible with transaction
    # pooling.
    engine = create_engine(
        settings.database_url,
        connect_args={
            "prepare_threshold": None,
            # Keep application tables outside Supabase's API-exposed public
            # schema. The bootstrap migration creates this schema first.
            "options": "-c search_path=mads,public",
        },
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        pool_recycle=300,
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

