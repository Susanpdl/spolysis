# 3D application implementation

Validation recorded on 2026-10-18.

Every new upload requests 3D analysis.
RTMPose keypoints remain an internal input to monocular 3D reconstruction.

## Repository cleanup

Cleanup on 2026-10-20 removed the unused standalone classifier, its training and clip-library tools, the unused LLM recommendation path, and unsupported model placeholders.
Image observations required by reconstruction, framing checks, and video projection remain in place.
Historical database migrations and callback names remain compatible with existing records and workers.
Future changes to those contracts are open options in [v2.md](../v2.md).
Geometry and pipeline integration tests now use synthetic articulated motion and temporary references instead of requiring an ignored local dataset file.
These tests check implementation behavior and do not establish tennis reconstruction accuracy.

## Implemented

- Expo SDK 57, React Native 0.86.3, React 19, and the New Architecture, including updated native camera, storage, upload, sharing, and navigation integrations.
- Stroke and handedness selection, guided recording, countdown, recording limits, camera lifecycle handling, and video-library import.
- Real local pose validation using Apple Vision on iOS and ML Kit on Android.
- Persistent authentication, repaired authentication buttons, network errors, upload progress, retry without re-upload after confirmation failure, and analysis history navigation.
- Private signed download links returned only after checking job ownership.
- An offline-bundled Three.js viewer with playback, scrubbing, orbit controls, original-pose comparison, and reset.
- Video playback controls and explicit video-file sharing.
- One shared 3D pipeline invoked on Modal through a durable Temporal workflow.
- Strict MotionBERT checkpoint loading with the official architecture, checkpoint key handling, joint-layout conversion, flip augmentation, and overlap blending.
- Angle-based reference alignment, estimated stroke phases, measured difference feedback, and corrections that preserve original limb lengths throughout transitions.
- Retry-safe result callbacks that propagate database failures instead of claiming success.
- A database migration for stroke selection, handedness, and read-only client access policies.
- A Fly deployment definition with separate API and workflow-worker processes.

## Validation

- TypeScript type checking and ESLint pass.
- Python lint passes.
- API lifecycle, ownership checks, duplicate callbacks, storage failure, missing uploads, joint mapping, bone preservation, alignment, rendering, and pipeline contracts are covered by tests.
- The upgraded iOS simulator build succeeds on EAS, including the Apple Vision frame processor and VisionCamera worklets.
- Native iOS tests pass for analysis history, actual result media, 3D playback, stroke selection, handedness selection, video import, native upload, result sharing, account review, and sign-out using an isolated authentication/API fixture.
- The final native suite passes both tests from a fresh installation, including sign-in, system password and photo dialogs, the full imported-video flow, sign-out, and authentication forms.
  The authentication service is a test fixture; production authentication remains blocked by Supabase availability.
- Expo Doctor passes all 21 checks, the dependency tree resolves, and the production Android JavaScript export succeeds.
- The bundled viewer passes Chromium rendering and interaction tests.
- The real pretrained MotionBERT checkpoint loads strictly and produces finite 3D output locally.
- R2 and Temporal connectivity checks pass.
- The corrected Modal GPU pipeline is deployed.
- A real close-up tennis video was rejected by the production quality gate because of blur and unsuitable framing.
- Real THETIS forehand, backhand, serve, and volley clips completed on the deployed GPU pipeline and produced rendered video and 3D skeleton artifacts.
- A real Temporal Cloud workflow completed through Modal and authenticated HTTP callback activities against the local callback fixture.
  This verifies orchestration but does not substitute for a production database write.

## Build evidence

The native iOS development build is [169329d0-3c0c-4cd5-82ab-7c3df38241dc](https://expo.dev/accounts/susshann/projects/spolysis/builds/169329d0-3c0c-4cd5-82ab-7c3df38241dc).
The standalone iOS simulator build is [3bbe4587-f257-4389-95b4-12d05366feda](https://expo.dev/accounts/susshann/projects/spolysis/builds/3bbe4587-f257-4389-95b4-12d05366feda).
It launches successfully without Metro or the local test service.
The standalone build also passes the native welcome, sign-up, and sign-in screen smoke test with those services stopped.
Its embedded bundle contains the configured production URLs, no fixture URL or fixture credentials, and no checked server-secret values.
The Android release APK build [49b2bf4b-ffde-49e2-b2d3-d485c14eb3fd](https://expo.dev/accounts/susshann/projects/spolysis/builds/49b2bf4b-ffde-49e2-b2d3-d485c14eb3fd) succeeds, including the ML Kit pose module and VisionCamera frame processors.
The pose module explicitly declares CameraX because VisionCamera's private implementation dependency does not expose `ImageProxy` to downstream modules.
The downloaded APK passes archive integrity checks and contains the production service URLs without fixture values or checked server-secret values in its JavaScript bundle.

- [Download Android APK](https://expo.dev/artifacts/eas/ki8nsZ6nMmFucu9iq9JyFQpDuhq6LMsb1-n4cJaEozM.apk)
- [Download standalone iOS simulator app](https://expo.dev/artifacts/eas/FrM6kL4LwOJS8BqNf1M-W7Sr-bVGYWOOgF8yVX5Qw1M.tar.gz)

## Dependency security

The backend now uses FastAPI 0.146 and Starlette 1.9.
Unused OpenTelemetry exporter packages were removed, eliminating an obsolete protobuf constraint.
The backend requirements audit reports no known vulnerabilities, and installation in a clean Python environment passes `pip check` and all six API tests.
The complete API and motion suite also passes all 15 tests after this update.

The platform upgrade removes the obsolete Expo 51 dependency graph and uses the supported SDK 57 platform.
The audit is not clean: the latest recorded npm audit reports 40 high-severity dependency entries caused by two remaining upstream advisories in the Expo/Metro/build-signing dependency graph.
These are [braces stack exhaustion](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) and [node-forge signature verification](https://github.com/advisories/GHSA-86w9-cpqp-85rv).
Neither had a patched upstream release available during verification.
The 40 entries include affected parent packages, rather than 40 independent vulnerabilities.
Recheck `npm audit` and update the platform tooling when upstream fixes become available.

## Screenshots

The native simulator screenshots show actual pipeline result media served by the isolated UI-test service.
Authentication and job completion in these screenshots use the local fixture, not the unavailable production Supabase project.

- [3D viewer](screenshots/3d-viewer.png)
- [Recording and import setup](screenshots/recording-setup.png)
- [Imported video result](screenshots/imported-result.png)
- [Video sharing](screenshots/share-video.png)
- [Account](screenshots/account.png)
- [Standalone welcome screen](screenshots/welcome.png)

## External requirements and limits

The configured Supabase project hostname does not resolve from both the development machine and the deployed Fly backend.
The Supabase account must be restored or connected before real authentication, database migration, and a production signed-in device test can be finished.
The Supabase integration was located, but account authorization remains a user action.

The API and worker deployment depends on migration `api/migrations/003_3d_analysis.sql` and valid Supabase settings.
The worker also needs Modal credentials in Fly secrets.
Deploy from the repository root with `fly deploy --config fly.runtime.toml` after those prerequisites are satisfied.
The existing generated `api/fly.toml` is retained without manual modification.

A real phone is required to validate live camera framing, recording orientation, and on-device WebGL performance.
Android builds successfully but still requires physical-device runtime validation.
App Store distribution requires the owner's Apple signing and store configuration.
A non-interactive production iOS build was attempted and stopped because distribution signing credentials are not configured in EAS.

This build uses pretrained MotionBERT, not a claimed tennis-fine-tuned or clinically validated model.
Coordinates are relative and angle estimates should not be represented as measured millimetres.
SportsPose fine-tuning, a held-out quantitative tennis benchmark, and independent biomechanical validation remain necessary before making accuracy claims.
The reference set contains regional high-performance players and must retain Tennis-MoCap attribution.

Monetization is not enabled in the new 3D-only flow.
Subscription products, pay-per-analysis credits, and server-side entitlement enforcement require a separate completed billing setup before charging users.

The R2 bucket must have public access disabled for raw videos and result artifacts.
Signed links in the API do not override a publicly accessible R2 bucket configuration.
