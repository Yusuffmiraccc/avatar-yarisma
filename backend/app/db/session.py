from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import AppError

settings = get_settings()
is_sqlite = "sqlite" in settings.database_url
engine_kwargs = {"future": True}
if is_sqlite:
    engine_kwargs.update({"connect_args": {"check_same_thread": False, "timeout": 30}})
else:
    engine_kwargs.update({"pool_pre_ping": True, "pool_recycle": 1800, "isolation_level": "READ COMMITTED"})

engine = create_engine(settings.database_url, **engine_kwargs)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """İstek başına tek transaction: başarıda commit, hatada rollback."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_unique_violation(exc):
            raise AppError(409, "CONFLICT", "Benzersiz kayıt çakışması.") from exc
        raise
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def _is_unique_violation(exc: IntegrityError) -> bool:
    orig = exc.orig
    code = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if code == "23505":
        return True
    args = getattr(orig, "args", ())
    if args and args[0] == 1062:  # MySQL duplicate entry
        return True
    message = str(orig).lower()
    return "unique constraint failed" in message or "duplicate key" in message
