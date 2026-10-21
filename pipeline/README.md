# 3D pipeline

The active entry point is `spolysis-pipeline/run_full_pipeline` in `pipeline/app.py`.
It invokes `pipeline/runner.py` and accepts a job ID, private R2 upload key, selected stroke, and handedness.

## Execution

1. Download the private upload into an isolated temporary directory.
2. Validate duration, decode at 30 fps, and bound image size.
3. Estimate RTMPose-x body keypoints and reject poor visibility, framing, or blur.
4. Select the strongest swing and nearby context.
5. Lift to 3D using the official full MotionBERT model and strict checkpoint loading.
6. Smooth and normalize motion, mirror left-handed strokes for comparison, and estimate phases.
7. Align diagnostic joint angles against a compatible Tennis-MoCap reference.
8. Compute differences and rotate joint subtrees while preserving limb lengths.
9. Render an H.264 overlay, save original and corrected skeletons, and generate grounded feedback.
10. Persist the completed result under the job ID so activity retries reuse successful work.

Raw image keypoints are an internal reconstruction input.
The app exposes reconstructed motion, a correction overlay, and measured differences.
Coordinates are relative; inferred contact is a wrist-motion proxy rather than detected ball impact.

## Runtime

`pipeline/app.py` is the authoritative GPU image definition.
It pins Torch 2.1.0, CUDA-compatible MMCV 2.1.0, MMPose 1.3.1, and the official MotionBERT source/checkpoint revision.
The official MotionBERT checkpoint is pretrained on Human3.6M and has not been tennis fine-tuned.
Missing or incompatible weights fail explicitly.
SmoothNet is disabled without a validated checkpoint; the default smoothing uses Savitzky-Golay only.

```sh
pip install modal==1.5.3
modal setup
modal deploy pipeline/app.py
```

Deploy from the repository root.
Set the Modal secret `spolysis-secrets` with `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, and `INTERNAL_API_SECRET`.
Reference NPY files in `data/reference_motion` are mounted into the image.
They derive from Tennis-MoCap and retain its CC BY-SA 3.0 attribution.

## Orchestration

Temporal runs one durable workflow per analysis.
A CPU worker invokes the Modal function and reports processing, completion, rejection, or failure through authenticated internal API endpoints.
Only object keys and JSON cross service boundaries; temporary local paths do not.
API callback failures propagate to Temporal for retry.

```sh
pip install -r api/requirements.txt modal==1.5.3
python -m pipeline.temporal.worker
```

The worker needs `TEMPORAL_HOST`, `TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY`, `TEMPORAL_TASK_QUEUE`, `INTERNAL_API_URL`, `INTERNAL_API_SECRET`, and Modal credentials.
It runs separately from the GPU container so it can continuously poll the task queue.
The root Dockerfile and `fly.runtime.toml` package both API and worker processes.

## Artifacts

| Key | Content |
|---|---|
| `raw/<job>/video.mp4` | Original upload, as allocated by the API |
| `artifacts/<job>/keypoints_2d.json` | Internal selected-window image keypoints |
| `results/<job>/overlay.mp4` | Correction composited on selected source frames |
| `results/<job>/skeleton_3d.json` | Versioned original/corrected relative COCO-17 motion |
| `results/<job>/result.json` | Cached result metadata for idempotent GPU retries |

The API verifies job ownership before issuing expiring artifact download links.
Do not enable public access on the bucket that stores these artifacts.

## Validation and research limits

Automated tests cover API contracts, ownership, callback retries, joint layout conversion, reflection, alignment, missing checkpoint failure, bone preservation, blur discrimination, and zero-correction projection.
A real expert THETIS forehand completed on Modal and produced a playable overlay and finite 3D skeletons.
This demonstrates integration, not quantitative tennis accuracy across all strokes and camera conditions.

A subject-held-out tennis benchmark and physical-device recordings remain required for accuracy and robustness validation.
[SportsPose access](https://christianingwersen.github.io/SportsPose/download.html) requires an author request, and commercial use requires permission.
Do not claim tennis fine-tuning has happened or replace missing weights with randomly initialized networks.
Future model and reference improvements are options in [v2.md](../v2.md), pending selection.
