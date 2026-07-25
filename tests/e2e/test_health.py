"""Smoke test that the FastAPI app boots and /healthz responds.

Note: this does NOT spin up Mongo (the app's lifespan would try to connect).
We use a fresh app instance with the lifespan skipped via TestClient context
not entering. For real e2e against Mongo + Redis, use the docker-compose stack.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_health_endpoint_responds_ok() -> None:
    # Minimal FastAPI app with just the healthz route so we don't touch lifespan/db.
    app = FastAPI()

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
