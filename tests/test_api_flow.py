"""HTTP lifecycle integration tests with isolated external-service adapters."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.auth import get_current_user
from api.routers import jobs, uploads, internal
from api.config import settings


class Database:
    def __init__(self):
        self.rows = {"jobs": [], "results": []}
        self.fail_results = False

    def table(self, name):
        return Query(self, name)


class Query:
    def __init__(self, db, name):
        self.db = db
        self.name = name
        self.filters = []
        self.action = "select"
        self.payload = None

    def select(self, *a, **k):
        return self

    def eq(self, key, value):
        self.filters.append(lambda r: r.get(key) == value)
        return self

    def in_(self, key, values):
        self.filters.append(lambda r: r.get(key) in values)
        return self

    def order(self, *a, **k):
        return self

    def range(self, *a):
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, **kwargs):
        self.action = "upsert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def execute(self):
        if self.name == "results" and self.db.fail_results:
            raise RuntimeError("database unavailable")
        rows = self.db.rows[self.name]
        selected = [r for r in rows if all(f(r) for f in self.filters)]
        if self.action in {"insert", "upsert"}:
            row = {
                "created_at": "2026-10-17T00:00:00+00:00",
                "updated_at": "2026-10-17T00:00:00+00:00",
                **self.payload,
            }
            if self.action == "upsert":
                rows[:] = [r for r in rows if r["job_id"] != row["job_id"]]
            rows.append(row)
            selected = [row]
        elif self.action == "update":
            for r in selected:
                r.update(self.payload)
        return SimpleNamespace(data=selected, count=len(selected))


@pytest.fixture
def client(monkeypatch):
    db = Database()
    for module in [jobs, uploads, internal]:
        monkeypatch.setattr(module, "service_client", db)
    monkeypatch.setattr(jobs, "cache_job_status", lambda *a: None)
    monkeypatch.setattr(internal, "invalidate_job_cache", lambda *a: None)
    monkeypatch.setattr(
        uploads, "generate_upload_url", lambda *a: "https://storage.example/upload"
    )
    monkeypatch.setattr(uploads, "verify_upload", lambda *a: None)
    monkeypatch.setattr(
        uploads, "start_analysis_workflow", AsyncMock(return_value="workflow-id")
    )
    import api.r2

    monkeypatch.setattr(
        api.r2,
        "generate_download_url",
        lambda key: f"https://private.example/{key}?signed=1",
    )
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "alice",
        "email": "alice@example.test",
    }
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, db
    app.dependency_overrides.clear()


def create(client):
    response = client.post(
        "/uploads/url",
        json={
            "filename": "stroke.mp4",
            "stroke_type": "forehand",
            "handedness": "left",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["job_id"]


def test_3d_http_lifecycle_and_duplicate_completion(client):
    c, db = client
    job = create(c)
    assert db.rows["jobs"][0]["tier"] == "premium"
    assert c.post(f"/uploads/{job}/confirm").status_code == 200
    headers = {"Authorization": f"Bearer {settings.internal_api_secret}"}
    assert (
        c.post(f"/internal/jobs/{job}/processing", headers=headers).status_code == 200
    )
    result = {
        "stroke_type": "forehand",
        "confidence": 0.85,
        "recommendation": "Review your elbow angle.",
        "overlay_video_url": f"results/{job}/overlay.mp4",
        "skeleton_3d_url": f"results/{job}/skeleton_3d.json",
        "delta_summary": {"right_elbow": 25},
        "fault_joints": ["right_elbow"],
    }
    for _ in range(2):
        assert (
            c.post(
                f"/internal/jobs/{job}/complete_premium", json=result, headers=headers
            ).status_code
            == 200
        )
    assert len(db.rows["results"]) == 1
    response = c.get(f"/jobs/{job}/result")
    assert response.status_code == 200, response.text
    assert "?signed=1" in response.json()["overlay_video_url"]
    assert c.get(f"/jobs/{job}").json()["status"] == "completed"


def test_2d_upload_is_rejected(client):
    c, _ = client
    assert (
        c.post(
            "/uploads/url",
            json={"filename": "video.mp4", "tier": "free", "stroke_type": "forehand"},
        ).status_code
        == 422
    )


def test_other_users_cannot_read_or_confirm_jobs(client):
    c, _ = client
    job = create(c)
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "bob",
        "email": "bob@example.test",
    }
    for path in [f"/jobs/{job}", f"/jobs/{job}/result"]:
        assert c.get(path).status_code == 404
    assert c.post(f"/uploads/{job}/confirm").status_code == 404


def test_completion_storage_failure_is_retryable(client):
    c, db = client
    job = create(c)
    db.fail_results = True
    result = {
        "stroke_type": "serve",
        "confidence": 0.9,
        "recommendation": "Review",
        "overlay_video_url": "overlay",
        "skeleton_3d_url": "skeleton",
        "delta_summary": {},
        "fault_joints": [],
    }
    response = c.post(
        f"/internal/jobs/{job}/complete_premium",
        json=result,
        headers={"Authorization": f"Bearer {settings.internal_api_secret}"},
    )
    assert response.status_code == 500
    assert db.rows["jobs"][0]["status"] == "pending"


def test_callback_requires_internal_secret(client):
    c, _ = client
    job = create(c)
    assert (
        c.post(
            f"/internal/jobs/{job}/processing",
            headers={"Authorization": "Bearer invalid"},
        ).status_code
        == 403
    )


def test_missing_upload_never_starts_compute(client, monkeypatch):
    c, _ = client
    job = create(c)

    def reject(*args):
        raise ValueError("missing")

    monkeypatch.setattr(uploads, "verify_upload", reject)
    assert c.post(f"/uploads/{job}/confirm").status_code == 400
    uploads.start_analysis_workflow.assert_not_awaited()
