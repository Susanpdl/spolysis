# Pipeline setup

All ML stages run as Modal serverless functions.
The Temporal worker runs locally or on a small Fly.io VM.

## Prerequisites

- Python 3.11+
- A Modal account: `pip install modal && modal setup`
- A Temporal Cloud account (or local dev server: `temporal server start-dev`)
- Credentials from `.env.example` filled in as Modal secrets

## 1. Install dependencies

```bash
cd pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Download model weights

RTMPose-x weights are downloaded automatically on first run via MMPoseInferencer.
Run the helper to pre-cache them:

```bash
python -m pipeline.scripts.download_models
```

Weights land in `~/.cache/mim/`.
They are **not committed to git**.

## 3. Create Modal secrets

```bash
modal secret create spolysis-secrets \
  R2_ACCOUNT_ID=your-account-id \
  R2_ACCESS_KEY_ID=your-access-key \
  R2_SECRET_ACCESS_KEY=your-secret \
  R2_BUCKET=spolysis \
  R2_PUBLIC_URL=https://your-bucket.r2.dev \
  ANTHROPIC_API_KEY=sk-ant-... \
  INTERNAL_API_URL=https://your-app.fly.dev \
  INTERNAL_API_SECRET=your-internal-secret \
  SENTRY_DSN_PIPELINE=https://your-key@sentry.io/project-id
```

## 4. Deploy to Modal

```bash
modal deploy pipeline/app.py
```

The deployed function is `spolysis-pipeline/run_analysis`.
The API triggers it via the Temporal workflow.

## 5. Start the Temporal worker

The Temporal worker runs the workflow and enqueues Modal tasks.

```bash
# Against Temporal Cloud:
TEMPORAL_HOST=your-ns.tmprl.cloud:7233 \
TEMPORAL_NAMESPACE=your-namespace \
python -m pipeline.temporal.worker

# Against local dev server:
python -m pipeline.temporal.worker
```

## 6. Run a single stage manually (debugging)

Every stage has a CLI entry point:

```bash
# Pose estimation
python -m pipeline.stages.pose2d --input sample.mp4 --output /tmp/keypoints.json

# Quality gate
python -m pipeline.stages.quality --input /tmp/keypoints.json

# Classification
python -m pipeline.stages.classify \
  --keypoints /tmp/keypoints.json \
  --model-path pipeline/models/checkpoints/stgcn_best.pth \
  --output /tmp/result.json
```

## 7. Train the ST-GCN classifier

Requires labeled JSONL files in `data/labels/` matching the schema in `data/labels/schema.json`.

```bash
python -m pipeline.scripts.train_stgcn \
  --labels-dir data/labels \
  --checkpoint-out pipeline/models/checkpoints/stgcn_best.pth \
  --epochs 80 \
  --batch-size 16
```

Upload the checkpoint to R2 after training so Modal workers can fetch it at cold start:

```bash
aws s3 cp pipeline/models/checkpoints/stgcn_best.pth \
  s3://spolysis/models/stgcn_best.pth \
  --endpoint-url https://<account-id>.r2.cloudflarestorage.com
```

## Stage input/output contracts

| Stage | Input | Output |
|---|---|---|
| `extract.py` | R2 video key | list of frame paths in `/tmp` |
| `pose2d.py` | frame paths | `keypoints.json` (17-kp COCO per frame) |
| `quality.py` | keypoints | pass/fail + rejection_reason |
| `features.py` | keypoints | joint angles, velocities, normalized positions |
| `segment.py` | features | segment window (start_frame, end_frame, peak_frame) |
| `classify.py` | segment features | stroke_type, fault_label, confidence |
| `lookup.py` | stroke_type, fault_label | reference_clip_url |
| `recommend.py` | stroke_type, fault_label, deltas | coaching_text |

All intermediate artifacts are stored in R2 under `jobs/<job_id>/` so any stage can be rerun without recomputing earlier ones.

## Reference clip library

Curated clips live in `data/clips/catalog.json`.
Actual video files are stored in R2 under `clips/`.
To add a new clip:

1. Upload the .mp4 to R2: `clips/<name>.mp4`
2. Add an entry to `catalog.json` with the `r2_key`
3. Link it under the appropriate `stroke_type` or `fault_clips` key
