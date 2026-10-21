# Spolysis project context

## Product scope

Spolysis helps tennis players review reconstructed motion and suggested corrections on their own footage.
Every new analysis follows the same 3D pipeline.
The user chooses the stroke and handedness, records or imports a clip, then reviews the overlay, joint-angle differences, and interactive motion viewer.

The authoritative implementation overview is [README.md](README.md).
Recorded validation evidence and external release requirements are in [Implementation status](docs/IMPLEMENTATION_STATUS.md).
Future proposals belong in [v2.md](v2.md) and require the user's choice before implementation.
Recommendations in that document are not approved product decisions.

## Active implementation

| Area | Current implementation |
|---|---|
| App | React Native with Expo and native camera modules |
| Live framing | Apple Vision on iOS and ML Kit on Android |
| Auth and database | Supabase |
| API | FastAPI on Fly |
| Storage | Private R2 objects and signed URLs |
| Orchestration | Temporal with a separate CPU worker |
| Analysis | Shared `pipeline.runner.run_analysis`, invoked on Modal |
| Image observations | RTMPose-x keypoints used internally for reconstruction, quality checks, swing selection, and projection |
| Reconstruction | Pretrained MotionBERT with strict checkpoint loading |
| Smoothing | Savitzky-Golay; optional SmoothNet requires a validated checkpoint |
| Comparison | Phase-anchored joint-angle alignment against Tennis-MoCap |
| Correction | Joint rotations that preserve the user's limb lengths |
| Output | H.264 overlay, original/corrected skeleton data, deterministic coaching text |
| Viewer | Bundled Three.js with playback, scrubbing, rotation, and original-motion comparison |

The current analysis selects the strongest swing with nearby context.
Image keypoints are a required intermediate representation, not an independent analysis product.
Motion coordinates and joint angles are estimates; do not claim calibrated millimetres, true ball-contact detection, tennis fine-tuning, or clinical validation.
The inferred contact phase is based on wrist motion.
Do not substitute randomly initialized models when weights are missing.

## Compatibility and data

The database's `tier` field and the `complete_premium` callback name remain for compatibility with existing records and workers.
They do not select a separate analysis implementation or imply active billing.
Historical results remain readable.
Do not edit previously applied database migrations to rename these contracts.
A coordinated schema/API migration is an explicit option in `v2.md`.

Reference motion derives from Tennis-MoCap and must retain attribution and its CC BY-SA 3.0 license.
Its reference players are regional high-performance athletes; do not describe the dataset as an ATP/WTA benchmark.
The THETIS videos recorded in validation evidence demonstrate integration, not quantitative reconstruction accuracy.
Dataset access, permissions, and model evaluation must be established before adopting additional training data.

## Engineering expectations

Keep analysis logic in `pipeline/runner.py` so deployed execution and integration tests exercise the same stages.
Only durable object keys and JSON cross service boundaries; local temporary paths must stay within their process.
API callbacks must propagate failures so Temporal can retry them.
Preserve job ownership checks, private storage, signed downloads, and bone lengths through correction transitions.
Never commit credentials or put server secrets in the app environment.
Do not manually edit generated artifacts or changelog files.
Preserve authored native modules under `app/modules`; generated platform projects and dependency caches are not source.

Run the checks documented in README after relevant changes.
Use physical devices for live camera validation and test fixtures for isolated UI flows.
Do not describe a fixture-backed test as production authentication or database validation.
The last recorded production blockers are documented in the implementation status; verify them before any release claim.
