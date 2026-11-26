"""HU-02 · a request without a valid access token is rejected with 401.

Drives the real `get_current_user_id` dependency through a tiny FastAPI app that
registers the project's exception handlers, so the status code is the real one.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.modules.auth.adapters.outbound.crypto.jwt_token_service import JwtTokenService
from src.shared.adapters.inbound.http.dependencies import get_current_user_id
from src.shared.adapters.inbound.http.exception_handlers import register_exception_handlers
from src.shared.adapters.outbound.config.settings import Settings, get_settings

SETTINGS = Settings(jwt_secret="a-test-secret-that-is-long-enough-for-hs256", jwt_algorithm="HS256")


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/me")
    def me(user_id: UUID = Depends(get_current_user_id)) -> dict[str, str]:
        return {"user_id": str(user_id)}

    app.dependency_overrides[get_settings] = lambda: SETTINGS
    return TestClient(app)


def _token(user_id: UUID, *, minutes: int, secret: str = SETTINGS.jwt_secret) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=SETTINGS.jwt_algorithm)


def test_hu02_a_valid_access_token_identifies_the_user(client: TestClient) -> None:
    user_id = uuid4()
    token = JwtTokenService(SETTINGS.jwt_secret, SETTINGS.jwt_algorithm, 15).issue_access_token(
        user_id, "free"
    )

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"user_id": str(user_id)}


def test_hu02_an_expired_access_token_is_rejected_with_401(client: TestClient) -> None:
    token = _token(uuid4(), minutes=-30)

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_hu02_a_token_signed_with_another_secret_is_rejected_with_401(client: TestClient) -> None:
    token = _token(uuid4(), minutes=15, secret="some-other-secret-of-sufficient-length-1")

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_hu02_garbage_instead_of_a_token_is_rejected_with_401(client: TestClient) -> None:
    response = client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


def test_hu02_a_request_without_a_token_is_rejected_with_401(client: TestClient) -> None:
    assert client.get("/me").status_code == 401
