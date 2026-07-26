# Spolysis - Tennis Motion Analysis Platform

Spolysis is a mobile application that helps amateur tennis players improve their technique by showing them exactly what their body is doing wrong - and what it should do instead - on their own footage.

A user records themselves playing through a guided in-app camera.
The system compares their motion against a dataset of professional players performing the same strokes, then delivers a precise correction overlaid on their original video.

## What makes this different

Every tennis analysis app on the market today gives you scores, stickmen, or a side-by-side comparison with a professional.
Spolysis gives you your own body, corrected, on your own footage.

The correction is not the pro's motion pasted on - the pro has different limb lengths and that would look wrong.
Instead, the system computes the exact joint-angle deltas between what the user did and what they should have done, then applies those corrections to the user's own skeleton using an IK solver that preserves their bone lengths.
The result is a video of what the user's body specifically should have looked like.

This is only possible with a full 3D reconstruction pipeline.
The free tier uses 2D pose estimation and can catch common faults visible in-plane (low follow-through, late contact, open stance).
The premium tier does a full monocular 3D lift, phase-aligned DTW comparison against professional reference motion, CCD IK correction, and renders the corrected skeleton composited over the user's original footage.

## Tier structure

**Free (2D)**
- Guided in-app recording with live pose validation
- RTMPose-x 2D pose estimation
- ST-GCN stroke classification (forehand / backhand / serve / volley) and fault detection
- Plain-text coaching recommendation (Claude API phrased, rules-based findings)
- Curated reference clip of a professional performing the correct motion

**Premium (3D)**
- Everything in the free tier
- Monocular 3D reconstruction (MotionBERT / PoseMamba)
- Phase detection (preparation, backswing, contact, follow-through)
- Keyframe-anchored DTW alignment against professional reference motion
- Biomechanical delta computation (joint angles and timing per phase)
- CCD IK correction applied only to flawed joints, eased in/out over neighboring frames
- Corrected skeleton rendered over original footage (OpenCV + ffmpeg H.264)
- Interactive 3D viewer (Three.js) - rotate and scrub the correction

## Current state

**Phase 1 is complete (code).**
The full 2D free tier is implemented end-to-end, from guided recording to results screen.
The codebase is ready to run; the remaining steps before the first real analysis comes back are infrastructure provisioning and training data.

Phase 2 (3D reconstruction and DTW comparison) is designed and the pipeline architecture is implemented.
The 3D stages are not yet fine-tuned or validated on tennis data - that requires the training datasets described below.

### What is built

| Layer | Status |
|---|---|
| React Native app (Expo Bare) | Complete - all screens, navigation, camera, upload |
| FastAPI backend (Fly.io) | Complete - auth, uploads, job status, internal callbacks |
| Temporal workflow orchestration | Complete - durable per-job workflow with retries |
| Modal GPU pipeline | Complete - all 8 stages wired end to end |
| 2D pose estimation (RTMPose-x) | Complete - weights auto-download on first run |
| Stroke + fault classifier (ST-GCN) | Architecture complete; heuristic fallback ships now; awaiting training data |
| Coaching text (Claude API) | Complete |
| Supabase auth + database | Schema written; needs provisioning |
| Cloudflare R2 storage | Integrated; needs provisioning |
| RevenueCat subscriptions | Integrated; needs product configuration |

### What is not yet built

- Phase 2 pipeline stages (3D lift, smoothing, DTW, delta computation)
- Phase 3 pipeline stages (IK correction, OpenCV overlay, ffmpeg encode, Three.js viewer)
- ST-GCN trained weights (depends on labeled training data - see below)
- Pro reference motion library for DTW (see below)

## Training data status

The ST-GCN classifier and the 3D reference motion library both require tennis-specific data.
This is the active bottleneck before Phase 1 goes live.

### Datasets identified

| Dataset | What it provides | Access |
|---|---|---|
| **THETIS** | 8,374 clips, 12 stroke classes, 3D Kinect skeleton, 55 subjects | Public - github.com/THETIS-dataset/dataset |
| **CalTennis** | 51 hours, 11M+ frames, multi-view 3D, 40 players | Public - huggingface.co/datasets/demalenk/caltennis |
| **Tennis-MoCap** | BVH motion files, 17 players (5 high-performance) | Public - github.com/jdpulgarin/Tennis-MoCap |
| **Penn Action** | 2,326 clips, forehand + serve labels, 2D keypoints | Public - cis.upenn.edu/~kostas/Penn_Action.tar.gz |
| **SportsPose** | 176K+ validated 3D poses, includes tennis | Access requested from DTU (pending) |
| **3DTennisDS** | 10 professional players, Vicon MoCap, 39 markers | Contact authors (pending) |
| **Tennis Action-GE** | Technique quality annotations by 20 coaches | Contact authors |

**Critical gap:** No public dataset has frame-level fault annotations (arm_only, late_contact, etc.).
The THETIS beginner/expert pair structure can generate weak fault labels via delta computation.
The Tennis Action-GE dataset with coach annotations is the most promising source for direct fault labels.

## Architecture overview

```
Mobile app (React Native + Expo Bare)
  │
  ├── ML Kit Pose Detection (live, on-device) - framing gate before recording
  ├── Guided recording screen with body outline overlay
  └── Upload to Cloudflare R2 via signed URL

FastAPI backend (Fly.io)
  ├── Supabase auth (JWT)
  ├── Job creation + R2 presigned URLs
  ├── Temporal workflow trigger
  └── Internal callback endpoints (pipeline → API)

Temporal workflow (durable orchestration)
  └── Chains pipeline stages with automatic retries

Modal GPU pipeline (serverless, A10G, per-second billing)
  ├── Frame extraction (ffmpeg, 30fps)
  ├── Player detection + crop
  ├── Quality gate (blur, framing, occlusion)
  ├── RTMPose-x 2D keypoints per frame
  ├── Feature extraction (joint angles, velocities)
  ├── Stroke segmentation (wrist velocity peak detection)
  ├── ST-GCN classification (stroke type + fault label)
  ├── Reference clip lookup
  └── Claude API coaching text

Cloudflare R2 + CDN
  └── Raw uploads, result videos, reference clips, intermediate artifacts
```

## Technology choices and rationale

**2D pose: RTMPose-x via MMPose** - maximum accuracy variant with permissive license.
YOLO pose (AGPL) and BlazePose server-side (degrades on fast tennis motion) are explicitly excluded.

**Stroke classification: ST-GCN** - exploits the skeleton graph structure; transfers well from NTU RGB+D pretrained weights; outperforms temporal CNNs on skeleton-based action recognition.

**3D lift: MotionBERT and PoseMamba** - both are regression-based (fast inference, no iterative optimization).
Both will be fine-tuned on tennis data; the one with better accuracy on tennis motion deploys to production.
Iterative optimization (SMPLify-style) is explicitly excluded from the user-facing inference path due to latency (1-5s per frame).

**Temporal smoothing: Savitzky-Golay + SmoothNet** - SG removes gross noise first; SmoothNet understands human motion structure and produces the best overlay quality.

**DTW alignment: keyframe-anchored DTW** - anchor at wrist velocity peak / contact point; constrained DTW on each side with Sakoe-Chiba band.
This handles the timing variation between amateur and professional strokes reliably.

**IK correction: CCD with joint limits** - rotation-based deltas map directly to CCD; fast CPU execution in milliseconds; applied only to flawed joints in the flawed window; eased in/out over neighboring frames to avoid puppet artifacts.

**Rendering: OpenCV skeleton projection + ffmpeg H.264** - corrected skeleton composited over original frames; visually distinct color and transparency.

**Orchestration: Temporal** - durable workflow per pipeline run; every stage is an activity with retries and timeouts; full state visibility.

**GPU compute: Modal (serverless)** - zero idle cost, per-second billing.
Target unit economics: $0.15-$0.50 per 5-minute premium analysis.

**Coaching text: Claude API (Haiku)** - LLM only rephrases findings; it never originates them.
Rules-based thresholds select findings from computed deltas; Claude puts them in natural coaching language.

## Repository structure

```
/app        React Native app (Expo Bare)
/api        FastAPI backend
/pipeline   ML pipeline - all stages, models, Temporal workflow - deployed to Modal
/data       Dataset curation scripts, clip library catalog, label schema
/docs       Architecture decisions, dataset notes
```

## Running the project

See `/pipeline/README.md` for the full setup guide including:
- Python environment and dependency installation
- RTMPose-x weight download
- Modal secret configuration and deployment
- Temporal worker startup
- Per-stage CLI entry points for debugging
- ST-GCN training instructions

## Build phases

**Phase 1 (current) - 2D free tier end to end**
Done when: a real phone-recorded video goes in and a stroke verdict, text recommendation, and reference clip come back on a real device.
Status: code complete; blocked on infrastructure provisioning and ST-GCN training data.

**Phase 2 - 3D reconstruction and comparison, no rendering**
Done when: for a test video the system outputs a numerically validated delta table (e.g. hip rotation at contact: user 34°, pro reference 52°) confirmed as plausible.
Status: architecture designed; pipeline stages not yet implemented; blocked on training datasets.

**Phase 3 - Correction, overlay, and interactive viewer**
Done when: a user video comes back with a visibly correct corrected skeleton overlaid at the flawed moment, no jitter, no puppet artifacts, and the 3D viewer rotates and scrubs correctly.
Status: not started.

**Phase 4 - Hardening and growth**
Full observability rollout, fault-specific reference clips, production benchmark between MotionBERT and PoseMamba, interactive viewer performance tuning.
Status: not started.

## Competitive landscape

| Competitor | What they ship | Gap |
|---|---|---|
| Tennis AI 2.0 | On-device MediaPipe; 107 metrics; side-by-side pro skeleton; 1.8 stars Android | 2D only; no IK-corrected overlay; unreliable |
| sevensix | Cloud CV; stickman + pro curve overlay; iOS only; 4.2 stars | 2D / curve only; no 3D lift or IK |
| OffCourtz | Parameter scoring; "how you should have performed" overlay | Closest language but 2D; no bone-length-preserving IK |
| SwingVision | ~500K users, ~$4M ARR; ball tracking, stats, highlights | Adjacent product (stats, not form correction); proves people pay |

No public competitor ships the full path: monocular 3D lift → phase-aligned DTW → CCD IK correction on user's own bone lengths → overlay on original footage.
