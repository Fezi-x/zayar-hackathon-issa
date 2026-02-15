import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env file
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

# Fix for SQLAlchemy 1.4+ requiring 'postgresql://' instead of 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Enforce SSL for Neon/Postgres
if "sslmode" not in DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
    DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"

print(f"DEBUG: Using DATABASE_URL starting with {DATABASE_URL.split(':')[0]}")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
