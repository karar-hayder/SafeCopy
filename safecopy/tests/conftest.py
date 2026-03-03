from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from safecopy.db.base import Base


@pytest.fixture(scope="session")
def test_engine():
    # Use an in-memory SQLite database for tests
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine):
    # Setup session maker for the test engine
    TestSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=test_engine
    )

    # Clear all data before each test for isolation

    with test_engine.begin() as conn:
        # For SQLite, we can just delete from each table.
        # Check Base.metadata for existing tables.
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

    # Patch the real SessionLocal and the get_session context manager's SessionLocal usage
    with patch("safecopy.db.session.SessionLocal", TestSessionLocal):
        session = TestSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@pytest.fixture(autouse=True)
def setup_db(db_session):
    # This ensures each test has a clean session and the db is patched
    pass
