import importlib

import pytest
from fastapi.testclient import TestClient

PRIMARY = "https://knova-rag.vercel.app/api/login/google/callback"
SECONDARY = "https://knova-lac.vercel.app/api/login/google/callback"


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOVA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.sqlite3'}")
    monkeypatch.setenv("KNOVA_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_URL", "https://knova-rag.vercel.app")
    monkeypatch.setenv("CORS_ORIGINS", "https://knova-lac.vercel.app")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_APP_REDIRECT_URI", PRIMARY)
    monkeypatch.setenv("GOOGLE_APP_REDIRECT_URIS", f"{PRIMARY},{SECONDARY}")

    import src.database as database_module
    database_module.Database._instance = None
    import backend.main as main
    main = importlib.reload(main)
    return main, TestClient(main.app)


def _request(main, **headers):
    from starlette.requests import Request

    raw = [(k.lower().replace("_", "-").encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "query_string": b""})


def test_redirect_falls_back_to_primary_without_hints(api):
    main, _ = api
    assert main._login_redirect_uri(_request(main)) == PRIMARY
    assert main._login_redirect_uri(None) == PRIMARY


def test_redirect_matches_browser_origin(api):
    main, _ = api
    assert main._login_redirect_uri(_request(main, referer="https://knova-lac.vercel.app/login?mode=signup")) == SECONDARY
    assert main._login_redirect_uri(_request(main, origin="https://knova-rag.vercel.app")) == PRIMARY
    assert main._login_redirect_uri(_request(main, x_forwarded_host="knova-lac.vercel.app")) == SECONDARY


def test_redirect_ignores_untrusted_origin(api):
    main, _ = api
    assert main._login_redirect_uri(_request(main, referer="https://evil.example.com/login")) == PRIMARY
    assert main._login_redirect_uri(_request(main, x_forwarded_host="evil.example.com")) == PRIMARY


def test_consent_url_uses_browser_origin(api, monkeypatch):
    main, client = api
    captured = {}

    class _FakeFlow:
        code_verifier = "verifier"

        def authorization_url(self, **kwargs):
            return "https://accounts.google.com/o/oauth2/auth?fake=1", "state-123"

    def fake_build(redirect_uri=main.APP_LOGIN_REDIRECT_URI):
        captured["redirect_uri"] = redirect_uri
        return _FakeFlow()

    monkeypatch.setattr(main, "_build_login_flow", fake_build)
    response = client.get("/app-auth/google/url", headers={"Referer": "https://knova-lac.vercel.app/login"})
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://accounts.google.com/")
    assert captured["redirect_uri"] == SECONDARY


def test_callback_returns_to_the_origin_that_started_login(api, monkeypatch):
    main, client = api
    captured = {}

    class _FakeCredentials:
        id_token = "fake-id-token"

    class _FakeFlow:
        code_verifier = None

        def fetch_token(self, code=None):
            return None

        @property
        def credentials(self):
            return _FakeCredentials()

    def fake_build(redirect_uri=main.APP_LOGIN_REDIRECT_URI):
        captured["redirect_uri"] = redirect_uri
        return _FakeFlow()

    monkeypatch.setattr(main, "_build_login_flow", fake_build)
    monkeypatch.setattr(main, "pop_oauth_verifier", lambda state: "verifier")
    monkeypatch.setattr(
        main.id_token,
        "verify_oauth2_token",
        lambda *args, **kwargs: {"sub": "google-user", "email": "google@example.com", "name": "Google User"},
    )
    main._remember_login_redirect("state-xyz", SECONDARY)

    response = client.get("/login/google/callback?code=abc&state=state-xyz", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "https://knova-lac.vercel.app/chat"
    assert captured["redirect_uri"] == SECONDARY
    assert main.SESSION_COOKIE_NAME in response.cookies


def test_callback_uses_frontend_url_for_the_default_local_redirect(api, monkeypatch):
    main, client = api

    class _FakeCredentials:
        id_token = "fake-id-token"

    class _FakeFlow:
        code_verifier = None

        def fetch_token(self, code=None):
            return None

        @property
        def credentials(self):
            return _FakeCredentials()

    monkeypatch.setattr(main, "_build_login_flow", lambda redirect_uri=None: _FakeFlow())
    monkeypatch.setattr(main, "pop_oauth_verifier", lambda state: "verifier")
    monkeypatch.setattr(
        main.id_token,
        "verify_oauth2_token",
        lambda *args, **kwargs: {"sub": "google-user-2", "email": "google2@example.com", "name": "Google User"},
    )

    response = client.get("/login/google/callback?code=abc&state=none", follow_redirects=False)
    assert response.headers["location"] == "https://knova-rag.vercel.app/chat"
