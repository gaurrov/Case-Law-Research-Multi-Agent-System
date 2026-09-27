"""Shared fixtures for pytest."""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from db.models import Base, CaseCorpus, CaseEmbedding

TEST_DB_URL = "sqlite:///test_case_law.db"


@pytest.fixture(scope="session")
def test_engine():
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    import os
    try:
        os.remove("test_case_law.db")
    except OSError:
        pass


@pytest.fixture
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def seed_cases(db_session):
    """Insert a small set of test cases."""
    existing = db_session.query(CaseCorpus).count()
    if existing > 0:
        return db_session.query(CaseCorpus).all()

    cases = [
        CaseCorpus(
            case_name="Test v. Privacy Corp",
            citation="100 F.3d 100 (Test 2020)",
            court="Test Circuit",
            date="2020-01-01",
            full_text="This case discusses employee privacy rights in digital communications. "
                      "The court held that warrantless monitoring of personal devices violates "
                      "the Fourth Amendment when no consent was given.",
            summary="Employee privacy in digital communications.",
        ),
        CaseCorpus(
            case_name="Example v. Search Inc",
            citation="200 F.3d 200 (Test 2021)",
            court="Test Circuit",
            date="2021-06-15",
            full_text="The central issue is whether a warrantless search of a cell phone "
                      "incident to arrest is constitutional. The court suppressed the evidence.",
            summary="Warrantless cell phone search during arrest.",
        ),
        CaseCorpus(
            case_name="Demo v. Contract LLC",
            citation="300 F.3d 300 (Test 2019)",
            court="Test Circuit",
            date="2019-03-10",
            full_text="This contract dispute involves breach of a software licensing agreement. "
                      "The court awarded damages for lost profits.",
            summary="Software license breach of contract.",
        ),
    ]
    for c in cases:
        db_session.add(c)
    db_session.commit()
    return cases
