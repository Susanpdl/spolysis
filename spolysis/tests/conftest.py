"""Tests never depend on developer credentials or production services."""

import os
import numpy as np
import pytest

for key, value in {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYW5vbiJ9.test",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.test",
    "R2_ACCOUNT_ID": "test",
    "R2_ACCESS_KEY_ID": "test",
    "R2_SECRET_ACCESS_KEY": "test",
    "UPSTASH_REDIS_REST_URL": "https://test.upstash.io",
    "UPSTASH_REDIS_REST_TOKEN": "test",
    "INTERNAL_API_SECRET": "test-internal-secret",
    "SENTRY_DSN": "",
}.items():
    os.environ[key] = value


@pytest.fixture
def motion_sequence():
    """Synthetic articulated motion for geometry tests, not an accuracy benchmark.

    Fixed limb lengths and a smooth swing with a central speed peak make the
    tests reproducible without downloading a dataset or loading model weights.
    """
    pose = np.array(
        [
            [0, 1.7, 0.1],
            [-0.04, 1.74, 0.1],
            [0.04, 1.74, 0.1],
            [-0.09, 1.7, 0],
            [0.09, 1.7, 0],
            [-0.25, 1.4, 0],
            [0.25, 1.4, 0],
            [-0.5, 1.2, 0.1],
            [0.5, 1.2, 0.1],
            [-0.45, 1.0, 0.35],
            [0.55, 1.0, 0.35],
            [-0.18, 0.9, 0],
            [0.18, 0.9, 0],
            [-0.2, 0.45, 0.1],
            [0.2, 0.45, 0.1],
            [-0.22, 0, 0],
            [0.22, 0, 0],
        ],
        dtype=np.float32,
    )
    motion = np.repeat(pose[None], 91, axis=0)
    angles = 1.4 * np.tanh(np.linspace(-3, 3, len(motion)))
    for frame, angle in zip(motion, angles):
        c, s = np.cos(angle), np.sin(angle)
        rotation = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        frame[[8, 10]] = (pose[[8, 10]] - pose[6]) @ rotation.T + pose[6]
    return motion
