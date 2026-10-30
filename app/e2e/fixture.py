"""Local UI-test service. Never deploy this unauthenticated fixture server."""

import argparse
import base64
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument("--media-dir", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
base = "http://localhost:8877"
user = {
    "id": "a1111111-1111-4111-8111-111111111111",
    "email": "ui-test@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "app_metadata": {},
    "user_metadata": {},
    "created_at": "2026-10-17T12:00:00Z",
}


def encoded(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")


token = ".".join(
    [
        encoded({"alg": "HS256", "typ": "JWT"}),
        encoded({"sub": user["id"], "exp": int(time.time()) + 86400}),
        "test-signature",
    ]
)
jobs = [
    {
        "id": "b1111111-1111-4111-8111-111111111111",
        "tier": "premium",
        "status": "completed",
        "created_at": "2026-10-17T12:00:00Z",
        "updated_at": "2026-10-17T12:01:00Z",
    }
]
result = json.loads(args.result.read_text())
result.update(
    {
        "overlay_video_url": f"{base}/media/overlay.mp4",
        "skeleton_3d_url": f"{base}/media/skeleton.json",
        "reference_clip_url": None,
        "created_at": jobs[0]["created_at"],
    }
)
failures = {
    "result": False,
    "motion": False,
    "video": False,
    "finishing": False,
    "confirm": False,
    "history": False,
    "history_page": False,
}
counters = {"uploads": 0, "confirmations": 0, "history_pages": 0}
initial_job = dict(jobs[0])


class Handler(BaseHTTPRequestHandler):
    def respond(self, value, status=200):
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/__test/failures":
            failures.update(json.loads(body))
            self.respond(failures)
        elif self.path == "/__test/jobs":
            jobs[:] = json.loads(body)
            self.respond({})
        elif self.path == "/__test/reset":
            jobs[:] = [dict(initial_job)]
            failures.update(dict.fromkeys(failures, False))
            counters.update(dict.fromkeys(counters, 0))
            self.respond({})
        elif self.path.startswith("/auth/v1/token"):
            self.respond(
                {
                    "access_token": token,
                    "refresh_token": "fixture-refresh",
                    "token_type": "bearer",
                    "expires_in": 86400,
                    "user": user,
                }
            )
        elif self.path.startswith("/auth/v1/logout"):
            self.respond({})
        elif self.path.startswith("/internal/jobs/"):
            print("Workflow callback:", self.path.rsplit("/", 1)[-1], flush=True)
            self.respond({"status": "ok"})
        elif self.path == "/uploads/url":
            job = {
                **jobs[0],
                "id": str(uuid4()),
                "status": "pending",
            }
            jobs.insert(0, job)
            self.respond(
                {
                    "job_id": job["id"],
                    "r2_key": "fixture.mp4",
                    "upload_url": f"{base}/upload",
                }
            )
        elif self.path.endswith("/confirm"):
            counters["confirmations"] += 1
            if failures["confirm"]:
                self.respond({"detail": "Temporary confirmation outage"}, 503)
                return
            job_id = self.path.split("/")[2]
            next(job for job in jobs if job["id"] == job_id)["status"] = "completed"
            self.respond({"status": "processing"})
        else:
            self.respond({"detail": "Unknown test endpoint"}, 404)

    def do_PUT(self):
        counters["uploads"] += 1
        remaining = int(self.headers.get("Content-Length", 0))
        while remaining:
            chunk = self.rfile.read(min(remaining, 65536))
            remaining -= len(chunk)
        self.respond({})

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/__test/state":
            self.respond({"jobs": jobs, **counters})
        elif path == "/auth/v1/user":
            self.respond(user)
        elif path == "/jobs":
            page = int(parse_qs(urlsplit(self.path).query).get("page", ["1"])[0])
            if page > 1:
                counters["history_pages"] += 1
            if failures["history"] or (page > 1 and failures["history_page"]):
                self.respond({"detail": "Temporary history outage"}, 503)
                return
            visible_jobs = [
                {**job, "status": "processing"} if failures["finishing"] else job
                for job in jobs
            ]
            self.respond(
                {
                    "jobs": visible_jobs[(page - 1) * 20 : page * 20],
                    "total": len(jobs),
                    "page": page,
                    "page_size": 20,
                }
            )
        elif path.startswith("/jobs/"):
            job_id = path.split("/")[2]
            if path.endswith("/result"):
                if failures["result"]:
                    self.respond({"detail": "Temporary result outage"}, 503)
                    return
                self.respond({**result, "job_id": job_id})
            else:
                self.respond(next(j for j in jobs if j["id"] == job_id))
        elif path in {"/media/overlay.mp4", "/media/skeleton.json"}:
            if failures["video" if path.endswith("mp4") else "motion"]:
                self.respond({"detail": "Temporary media outage"}, 503)
                return
            data = (args.media_dir / path.split("/")[-1]).read_bytes()
            start, end = 0, len(data) - 1
            partial = self.headers.get("Range", "")
            if partial:
                bounds = partial.removeprefix("bytes=").split("-")
                start = int(bounds[0] or 0)
                end = min(int(bounds[1] or end), end)
            self.send_response(206 if partial else 200)
            self.send_header(
                "Content-Type",
                "video/mp4" if path.endswith("mp4") else "application/json",
            )
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            self.end_headers()
            self.wfile.write(data[start : end + 1])
        else:
            self.respond({"detail": "Unknown test endpoint"}, 404)


print("UI fixture listening on localhost:8877", flush=True)
ThreadingHTTPServer(("127.0.0.1", 8877), Handler).serve_forever()
