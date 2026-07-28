"""Covers US-03 acceptance criteria: signup, verification, login, session
timeout token shape, and account lockout after 5 consecutive failures.
"""


def test_signup_creates_account_and_triggers_verification(client):
    resp = client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@iiml.ac.in"
    assert body["is_verified"] is False
    assert body["verification_token"]


def test_signup_rejects_duplicate_email(client):
    client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    resp = client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "anotherpass1"})
    assert resp.status_code == 400


def test_signup_rejects_short_password(client):
    resp = client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "short"})
    assert resp.status_code == 422


def test_verify_with_token_marks_account_verified(client):
    signup = client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "supersecret1"}).json()
    resp = client.post("/auth/verify", json={"token": signup["verification_token"]})
    assert resp.status_code == 200

    login = client.post("/auth/login", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_verified"] is True


def test_login_wrong_password_fails(client):
    client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    resp = client.post("/auth/login", json={"email": "a@iiml.ac.in", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_success_returns_access_and_refresh_tokens(client):
    client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    resp = client.post("/auth/login", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] == 30 * 60


def test_account_locks_after_five_consecutive_failed_logins(client):
    client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "supersecret1"})

    for _ in range(5):
        resp = client.post("/auth/login", json={"email": "a@iiml.ac.in", "password": "wrongpass"})
        assert resp.status_code == 401

    locked_resp = client.post("/auth/login", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    assert locked_resp.status_code == 423


def test_refresh_token_issues_new_access_token(client):
    client.post("/auth/signup", json={"email": "a@iiml.ac.in", "password": "supersecret1"})
    login = client.post("/auth/login", json={"email": "a@iiml.ac.in", "password": "supersecret1"}).json()

    resp = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_me_requires_bearer_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
