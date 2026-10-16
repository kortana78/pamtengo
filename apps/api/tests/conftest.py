import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_pamtengo.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.rate_limit import reset_rate_limiter
from app.db.session import Base, get_db
from app.main import create_app
from app.services import email_mock

TEST_URL = "sqlite:///./test_pamtengo.db"
engine = create_engine(TEST_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _clean_db():
    from app import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    email_mock.reset_mock()
    reset_rate_limiter()
    yield
    email_mock.reset_mock()


@pytest.fixture()
def db():
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(db):
    def override():
        try:
            yield db
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


AUTH = {"X-User-Email": "admin@pamtengo.demo"}


def make_company(client, **kw):
    payload = {
        "name": "Acme Demo Ltd",
        "country": "Malawi",
        "industry": "agriculture",
        "employee_range": "51-200",
        **kw,
    }
    r = client.post("/api/v1/companies", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def make_lead(client, company_id=None, **kw):
    payload = {
        "company_id": company_id,
        "full_name": "Test Lead",
        "job_title": "Operations Director",
        "email": "lead@example.com",
        **kw,
    }
    if company_id is None:
        payload.pop("company_id")
        payload.setdefault("company_name", "Acme Demo Ltd")
        payload.setdefault("company_country", "Malawi")
        payload.setdefault("company_industry", "agriculture")
    r = client.post("/api/v1/leads", json=payload)
    assert r.status_code == 201, r.text
    return r.json()
