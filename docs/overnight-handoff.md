# Overnight handoff

## Current phase

Iteration 1 is complete: the native test path is restored and three confirmed result recovery defects are repaired.
Next, continue the ranked capture and upload interruption audit.
Work is confined to the `overnight/prepared` worktree.
No commits, pushes, deployments, or production mutations are performed by this worker.
GNHF maintains its own `notes.md`; this worker does not edit it.

## Native setup

- Simulator: `858FB450-9823-4060-AADB-CDB3CBB58445`, iPhone 17 Pro, iOS 26.5.
- Installed app: `com.spolysis.app`, compatible development shell with no embedded JavaScript bundle.
- Start Metro from this worktree before launching the app; no native rebuild was needed.
- `ruby app/e2e/create-project.rb /tmp/SpolysisOvernightUITests.xcodeproj` works with the system Ruby and installed `xcodeproj` 1.28.1 gem.
- CocoaPods is absent at the previously suggested locations, but is unnecessary for reusing this installed shell.
- Derived data: `/tmp/spolysis-overnight-ui`.
- Ignored actual pipeline media: `.gnhf/media/overlay.mp4`, `.gnhf/media/skeleton.json`, `.gnhf/media/result.json`.
- Source artifacts were downloaded read-only from `results/34406f21-3fa4-425e-918f-7f7efad187e3/` using main-checkout ignored configuration in memory.
- No credentials were copied to this worktree or printed.

## Commands and evidence

Start the existing isolated fixture from the repository root:

```sh
.venv-test/bin/python app/e2e/fixture.py --media-dir .gnhf/media --result .gnhf/media/result.json
```

Start Metro in another terminal:

```sh
EXPO_PUBLIC_SUPABASE_URL=http://localhost:8877 EXPO_PUBLIC_SUPABASE_ANON_KEY=fixture-anon EXPO_PUBLIC_API_URL=http://localhost:8877 npm --prefix app start -- --clear --port 8081
```

Add the test video to the simulator library if needed:

```sh
xcrun simctl addmedia 858FB450-9823-4060-AADB-CDB3CBB58445 .gnhf/media/overlay.mp4
```

Run the native tests with a fresh result-bundle path:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests/SignedInTests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-audit-tap.xcresult CODE_SIGNING_ALLOWED=NO
```

The ordinary-tap signed-in audit passed one test with zero failures in 57.470 seconds.
The earlier long-press smoke and signed-in audits failed navigation before making result requests.
Their result bundles are `/tmp/spolysis-overnight-audit-smoke.xcresult` and `/tmp/spolysis-overnight-audit-signedin.xcresult`.
Screenshots and exported attachments are under ignored `.gnhf/evidence`.

## Remaining work and decisions

See [Athlete review](athlete-review.md) for the ranked backlog and claim boundaries.
Production Supabase DNS remains unavailable as checked on 2026-10-30.
No large architecture decision is currently required for this first slice.
Fixture credentials must remain confined to local Metro sessions and must never be distributed.
Stop worker-started services and the test app before concluding each iteration.

## Phase 1 implementation and validation

Completed analyses now distinguish result-download failure from reconstruction and offer retry without another upload.
Video and 3D failures provide direct recovery controls that refresh signed links.
Motion download cancels on navigation and times out after 30 seconds.
An unsuccessful link refresh preserves a retryable failure state.
Buttons expose disabled and busy accessibility states.
The existing fixture can simulate result, motion, video, and finishing-job states without production access.

The final consolidated native pass uses this command:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase1-final.xcresult CODE_SIGNING_ALLOWED=NO
```

Its log is `/tmp/spolysis-overnight-phase1-final.log`.
The consolidated pass succeeded: five tests, zero failures, 115.025 seconds of test execution on 2026-10-30.
This covers three recovery tests, the signed-in import/upload/review/share/sign-out journey, and welcome/sign-up/sign-in navigation.
The motion recovery test also verifies a failed metadata refresh before successful recovery.
Final attachments are exported under `.gnhf/evidence/phase1-final`; three recovery screenshots are included under `docs/screenshots`.
Screenshot review confirms visible retry actions, readable text, and actual recovered video at 1206 x 2622 resolution.
Real signed-link expiry, interrupted transfer resumption, session expiry, offline history, Dynamic Type, and small-screen behavior are not yet validated.
The separate completed-result baseline is `/tmp/spolysis-overnight-completion-before.xcresult`.
Its first attempt in the earlier recovery bundle was obstructed by a native password dialog; the separate rerun dismissed that dialog and reproduced the reconstruction spinner.
The baseline media failures are captured in `/tmp/spolysis-overnight-recovery-before.xcresult` and exported under `.gnhf/evidence/recovery-before`.

The following checks pass for the completed application changes:

```sh
npm --prefix app run typecheck
npm --prefix app run lint
npm --prefix app run build:viewer
.venv-test/bin/python -m ruff check api pipeline tests app/e2e/fixture.py
npx --prefix app prettier --check app/src/hooks/useJob.ts app/src/screens/UploadProgressScreen.tsx app/src/screens/ResultScreen.tsx app/src/components/VideoPlayer.tsx app/src/components/Button.tsx
```

No API or pipeline implementation changed, so the Python regression suite was not rerun in this phase.
The first type check found the removed React Native `absoluteFillObject` API; replacing it with `absoluteFill` resolved that compatibility error.
The ignored checkpoint is `.gnhf/checkpoints/iteration-1-result-recovery.patch`.
Its status is recorded in the ignored run sidecar `.gnhf/runs/objective-act-as-a-d-19111c/iteration-1-checkpoints.md`, preserving orchestrator-owned notes.

## Cleanup and next iteration

Metro on port 8081, the fixture on port 8877, and the test app were stopped after verification.
Stopping the Simulator GUI also shut down the simulator device; its installation and data are preserved.
Boot it before the next native session:

```sh
xcrun simctl boot 858FB450-9823-4060-AADB-CDB3CBB58445
xcrun simctl bootstatus 858FB450-9823-4060-AADB-CDB3CBB58445 -b
```
No worker-started server or test runner remains active.
The app ended signed out after the full journey, then the authentication smoke test opened the sign-in form.
Restart the fixture and Metro using the commands above for the next batch.
The next smallest cohesive batch is native capture/upload interruption and rejection recovery, with fixture controls extended only for concrete failure cases.
