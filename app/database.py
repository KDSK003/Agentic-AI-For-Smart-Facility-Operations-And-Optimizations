"""
Database connection setup for the Agentic FacilityOps AI Platform.
Uses SQLite for local development (zero-config, matches the schema in section 9 of the spec).
Swap SQLALCHEMY_DATABASE_URL for a Postgres URL later without touching models.py.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./facilityops.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
