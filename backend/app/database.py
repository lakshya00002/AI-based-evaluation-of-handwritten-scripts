from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _sqlite_connect_args() -> dict:
    return {
        "check_same_thread": False,
        "timeout": 30.0,
    }


connect_args = _sqlite_connect_args() if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _sqlite_wal_and_busy_timeout(dbapi_connection, connection_record) -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=60000")
    cursor.close()


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
