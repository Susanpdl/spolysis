"""HTTP lifecycle integration tests with isolated external-service adapters."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi.testclient import TestClient
from botocore.exceptions import ClientError, EndpointConnectionError
from api import r2
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
    for path, body in [
        ("processing", {}),
        ("fail", {"error_message": "Late failure"}),
        ("reject", {"rejection_reason": "Late rejection"}),
    ]:
        assert (
            c.post(
                f"/internal/jobs/{job}/{path}", json=body, headers=headers
            ).status_code
            == 200
        )
        assert c.get(f"/jobs/{job}").json()["status"] == "completed"
    assert c.get(f"/jobs/{job}/result").status_code == 200


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
        raise r2.InvalidUploadError("missing")

    monkeypatch.setattr(uploads, "verify_upload", reject)
    assert c.post(f"/uploads/{job}/confirm").status_code == 400
    uploads.start_analysis_workflow.assert_not_awaited()


@pytest.mark.parametrize("code", ["404", "NoSuchKey", "NotFound"])
def test_missing_storage_object_needs_new_upload(client, monkeypatch, code):
    c, db = client
    job = create(c)
    storage = Mock()
    storage.head_object.side_effect = ClientError(
        {"Error": {"Code": code}}, "HeadObject"
    )
    monkeypatch.setattr(r2, "get_r2_client", lambda: storage)
    monkeypatch.setattr(uploads, "verify_upload", r2.verify_upload)
    assert c.post(f"/uploads/{job}/confirm").status_code == 400
    assert db.rows["jobs"][0]["status"] == "pending"
    uploads.start_analysis_workflow.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [
        ClientError({"Error": {"Code": "InternalError"}}, "HeadObject"),
        ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject"),
        EndpointConnectionError(endpoint_url="https://storage.example"),
    ],
)
def test_storage_outage_retries_start_without_new_upload(client, monkeypatch, error):
    c, db = client
    job = create(c)
    storage = Mock()
    storage.head_object.side_effect = error
    monkeypatch.setattr(r2, "get_r2_client", lambda: storage)
    monkeypatch.setattr(uploads, "verify_upload", r2.verify_upload)
    response = c.post(f"/uploads/{job}/confirm")
    assert response.status_code == 503
    assert "Retry starting" in response.json()["detail"]
    assert db.rows["jobs"][0]["status"] == "pending"
    uploads.start_analysis_workflow.assert_not_awaited()
    storage.head_object.side_effect = None
    storage.head_object.return_value = {
        "ContentLength": 1024,
        "ContentType": "video/mp4",
    }
    assert c.post(f"/uploads/{job}/confirm").status_code == 200
    uploads.start_analysis_workflow.assert_awaited_once()
    assert len(db.rows["jobs"]) == 1


@pytest.mark.parametrize(
    "metadata",
    [
        {"ContentLength": 0, "ContentType": "video/mp4"},
        {"ContentLength": 500 * 1024 * 1024 + 1, "ContentType": "video/mp4"},
        {"ContentLength": 1024, "ContentType": "image/jpeg"},
    ],
)
def test_invalid_storage_object_never_starts_compute(client, monkeypatch, metadata):
    c, _ = client
    job = create(c)
    storage = Mock()
    storage.head_object.return_value = metadata
    monkeypatch.setattr(r2, "get_r2_client", lambda: storage)
    monkeypatch.setattr(uploads, "verify_upload", r2.verify_upload)
    assert c.post(f"/uploads/{job}/confirm").status_code == 400
    uploads.start_analysis_workflow.assert_not_awaited()


@pytest.mark.parametrize(
    "failure", [500, 502, 503, 504, 429, "timeout", "connect", "malformed"]
)
def test_auth_outage_is_retryable_without_creating_jobs(client, monkeypatch, failure):
    """Exercise app requests through real token validation and the GoTrue SDK."""
    import httpx
    from gotrue import SyncGoTrueClient
    from api import auth

    c, db = client
    app.dependency_overrides.pop(get_current_user)
    unavailable = True

    def respond(request):
        assert request.headers["Authorization"] == "Bearer athlete-token"
        if unavailable:
            if failure == "timeout":
                raise httpx.ReadTimeout("private upstream detail", request=request)
            if failure == "connect":
                raise httpx.ConnectError("private upstream detail", request=request)
            if failure == "malformed":
                return httpx.Response(200, text="not JSON")
            return httpx.Response(failure, json={"msg": "private upstream detail"})
        return httpx.Response(
            200,
            json={
                "id": "alice",
                "aud": "authenticated",
                "role": "authenticated",
                "email": "alice@example.test",
                "app_metadata": {},
                "user_metadata": {},
                "created_at": "2026-10-17T00:00:00Z",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as upstream:
        sdk = SyncGoTrueClient(
            http_client=upstream, auto_refresh_token=False, persist_session=False
        )
        monkeypatch.setattr(auth, "_auth_client", SimpleNamespace(auth=sdk))
        headers = {"Authorization": "Bearer athlete-token"}
        for response in [
            c.get("/jobs", headers=headers),
            c.post(
                "/uploads/url",
                headers=headers,
                json={"filename": "stroke.mp4", "stroke_type": "forehand"},
            ),
        ]:
            assert response.status_code == 503, response.text
            assert "try again" in response.json()["detail"]
            assert "private upstream detail" not in response.text
        assert db.rows["jobs"] == []
        uploads.start_analysis_workflow.assert_not_awaited()
        unavailable = False
        assert c.get("/jobs", headers=headers).status_code == 200
        assert (
            c.post(
                "/uploads/url",
                headers=headers,
                json={"filename": "stroke.mp4", "stroke_type": "forehand"},
            ).status_code
            == 201
        )
        assert db.rows["jobs"][0]["user_id"] == "alice"


@pytest.mark.parametrize("status_code", [401, 403])
def test_rejected_auth_token_remains_unauthorized(client, monkeypatch, status_code):
    import httpx
    from gotrue import SyncGoTrueClient
    from api import auth

    c, db = client
    app.dependency_overrides.pop(get_current_user)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, json={"msg": "token rejected"})
        )
    ) as upstream:
        sdk = SyncGoTrueClient(
            http_client=upstream, auto_refresh_token=False, persist_session=False
        )
        monkeypatch.setattr(auth, "_auth_client", SimpleNamespace(auth=sdk))
        response = c.get("/jobs", headers={"Authorization": "Bearer rejected-token"})
        assert response.status_code == 401
        assert db.rows["jobs"] == []


@pytest.mark.parametrize(
    ("terminal", "body"),
    [
        ("fail", {"error_message": "Analysis could not finish."}),
        ("reject", {"rejection_reason": "Keep your full body in view."}),
    ],
)
def test_completion_cannot_overwrite_concurrent_terminal_callback(
    client, monkeypatch, terminal, body
):
    c, db = client
    job = create(c)
    assert c.post(f"/uploads/{job}/confirm").status_code == 200
    headers = {"Authorization": f"Bearer {settings.internal_api_secret}"}
    assert (
        c.post(f"/internal/jobs/{job}/processing", headers=headers).status_code == 200
    )
    execute = Query.execute

    def interleaved_execute(query):
        result = execute(query)
        if query.name == "results" and query.action == "upsert":
            # A second worker callback lands after the initial status read.
            response = c.post(
                f"/internal/jobs/{job}/{terminal}", json=body, headers=headers
            )
            assert response.status_code == 200
        return result

    monkeypatch.setattr(Query, "execute", interleaved_execute)
    response = c.post(
        f"/internal/jobs/{job}/complete_premium",
        headers=headers,
        json={
            "stroke_type": "forehand",
            "confidence": 0.85,
            "recommendation": "Review your elbow angle.",
            "overlay_video_url": f"results/{job}/overlay.mp4",
            "skeleton_3d_url": f"results/{job}/skeleton_3d.json",
            "delta_summary": {},
            "fault_joints": [],
        },
    )
    assert response.status_code == 409, response.text
    status = c.get(f"/jobs/{job}").json()
    assert status["status"] == {"fail": "failed", "reject": "rejected"}[terminal]
    for field, value in body.items():
        assert status[field] == value
    assert c.get(f"/jobs/{job}/result").status_code == 400
