"""
Dependency injection para FastAPI.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import get_session


def get_db() -> Generator[Session, None, None]:
    """Provee una session de DB y la cierra al terminar."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
