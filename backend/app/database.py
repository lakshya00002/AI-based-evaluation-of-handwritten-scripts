from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_startup_migrations() -> None:
    inspector = inspect(engine)
    if "assignments" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("assignments")}
    with engine.begin() as connection:
        if "due_date" not in columns:
            connection.execute(text("ALTER TABLE assignments ADD COLUMN due_date DATETIME"))
        if "allow_multiple_submissions" not in columns:
            connection.execute(
                text("ALTER TABLE assignments ADD COLUMN allow_multiple_submissions BOOLEAN NOT NULL DEFAULT 0")
            )
