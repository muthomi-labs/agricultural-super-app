# tests/conftest.py
#
# Shared fixtures for the whole suite. Fixture design notes, since the
# *why* behind these choices matters more than the code itself:
#
# - `app` is session-scoped: creating a Flask app and pushing its context
#   is real work we don't want to repeat for every single test function.
#   We push the application context once and keep it alive for the
#   entire test session.
#
# - `db` is function-scoped and autouse=True: every test gets a
#   completely empty, freshly-created set of tables, and they're dropped
#   again afterward. This is what gives us test ISOLATION -- one test's
#   data can never leak into or affect another test. The cost is a
#   create_all()/drop_all() pair per test, which is cheap against
#   in-memory SQLite (milliseconds) but would be a real bottleneck
#   against a real Postgres instance -- a tradeoff worth knowing you're
#   making, not just inheriting by accident.
#
# - Fixtures that need to build data (`create_user`, `register_user`)
#   are written as FACTORIES: the fixture itself returns a function,
#   which each test then calls with whatever arguments it needs. Plain
#   fixtures give you one fixed object; factory fixtures let a single
#   fixture serve every test that needs "a user, but with different
#   attributes" without duplicating setup code in every test.

import pytest

from app import create_app
from app.auth.jwt import encode_token
from app.extensions import db as _db
from app.models import User
from app.services.ai_service import clear_ask_assistant_cache
from app.services.channel_rate_limiter import reset_rate_limits


@pytest.fixture(scope="session")
def app():
    flask_app = create_app("testing")
    ctx = flask_app.app_context()
    ctx.push()
    yield flask_app
    ctx.pop()


@pytest.fixture(autouse=True)
def db(app):
    _db.create_all()
    yield _db
    _db.session.remove()
    _db.drop_all()


@pytest.fixture(autouse=True)
def _reset_ask_assistant_cache():
    """ask_assistant()'s cache is module-level state (see ai_service.py)
    -- without this, a reply cached by one test could be served, wrong,
    to a different test that happens to ask the same question."""
    clear_ask_assistant_cache()
    yield
    clear_ask_assistant_cache()


@pytest.fixture(autouse=True)
def _reset_channel_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_user(db):
    """
    Factory for creating a User directly via the ORM (bypassing the API
    and its schema-level `role` restriction) -- unit tests for the
    service layer need to set up state, including states the public API
    can never produce itself, like an "admin" user or an inactive
    account.
    """

    def _create_user(
        username="testuser",
        email=None,
        password="testpassword123",
        role="farmer",
        is_active=True,
        language="en",
    ):
        email = email or f"{username}@example.com"
        user = User(username=username, email=email, role=role, is_active=is_active, language=language)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _create_user


@pytest.fixture
def register_user(client):
    """
    Factory for registering a user through the real HTTP API -- what
    integration tests (and any unit test that specifically wants a
    ready-made auth token) should use, since it exercises the actual
    registration flow instead of a shortcut.

    Returns a dict: {"user": <dict>, "token": <str>, "headers": <dict>}.
    """

    def _register_user(username="testuser", email=None, password="TestPassword123!", role="farmer", language=None):
        email = email or f"{username}@example.com"
        body = {"username": username, "email": email, "password": password, "role": role}
        if language is not None:
            body["language"] = language
        response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, response.get_json()
        body = response.get_json()
        return {
            "user": body["user"],
            "token": body["token"],
            "headers": {"Authorization": f"Bearer {body['token']}"},
        }

    return _register_user


@pytest.fixture
def amina(register_user):
    """A ready-made registered user, for tests that just need 'a user'."""
    return register_user(username="amina")


@pytest.fixture
def brian(register_user):
    """A second registered user, for ownership/authorization tests."""
    return register_user(username="brian")


@pytest.fixture
def admin_user(create_user):
    """
    A ready-made admin, for admin-route tests. Built via create_user
    (direct ORM), not register_user -- registering as "admin" through the
    public API is deliberately rejected (see user_schema.py), so a real
    admin account can only ever come from a path like this one: seeded
    directly, exactly as it would need to be in a real deployment.

    Returns a dict shaped like register_user's, for a consistent
    {"user", "headers"} interface across fixtures.
    """
    user = create_user(username="admin1", email="admin1@example.com", role="admin")
    token = encode_token(user.id)
    return {"user": user, "headers": {"Authorization": f"Bearer {token}"}}
