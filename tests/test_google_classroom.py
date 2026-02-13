import pytest

PASSWORD = "Password123!"


def _login(client, email):
    resp = client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(client, email):
    return {"Authorization": f"Bearer {_login(client, email)}"}


@pytest.fixture()
def gc_user(db_session):
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole

    email = "gc_user@test.com"
    user = db_session.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email, full_name="GC User", role=UserRole.TEACHER,
        hashed_password=get_password_hash(PASSWORD),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Status endpoint ───────────────────────────────────────────

class TestGoogleStatus:
    def test_not_connected_by_default(self, client, gc_user):
        headers = _auth(client, gc_user.email)
        resp = client.get("/api/google/status", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["connected"] is False

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/google/status")
        assert resp.status_code == 401


# ── Disconnect endpoint ──────────────────────────────────────

class TestGoogleDisconnect:
    def test_disconnect_clears_tokens(self, client, gc_user, db_session):
        # Simulate connected state
        gc_user.google_id = "google123"
        gc_user.google_access_token = "fake-access-token"
        gc_user.google_refresh_token = "fake-refresh-token"
        db_session.commit()

        headers = _auth(client, gc_user.email)
        resp = client.delete("/api/google/disconnect", headers=headers)
        assert resp.status_code == 200
        assert "disconnected" in resp.json()["message"].lower()

        # Verify status is now disconnected
        status_resp = client.get("/api/google/status", headers=headers)
        assert status_resp.json()["connected"] is False


# ── Courses without connection ────────────────────────────────

class TestGoogleCoursesNoConnection:
    def test_courses_without_connection_returns_400(self, client, gc_user):
        headers = _auth(client, gc_user.email)
        resp = client.get("/api/google/courses", headers=headers)
        assert resp.status_code == 400
        assert "not connected" in resp.json()["detail"].lower()

    def test_sync_without_connection_returns_400(self, client, gc_user):
        headers = _auth(client, gc_user.email)
        resp = client.post("/api/google/courses/sync", headers=headers)
        assert resp.status_code == 400
        assert "not connected" in resp.json()["detail"].lower()


# ── Auth endpoint ─────────────────────────────────────────────

class TestGoogleAuth:
    def test_auth_returns_authorization_url(self, client):
        resp = client.get("/api/google/auth")
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_url" in data
        assert "state" in data
