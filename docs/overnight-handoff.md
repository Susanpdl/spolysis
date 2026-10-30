# Overnight handoff

## Current phase

Iteration 3 implements trustworthy history failure and pagination recovery.
Consolidated native validation, screenshot review, and cleanup are complete for this batch.
Work stays in `overnight/prepared`; no worker commits, pushes, deployment, production mutations, or additional agents.
GNHF owns `notes.md`; checkpoint status goes in ignored iteration sidecars.

## Completed work

- Phase 1: completed-result retry, refreshed signed-link recovery for video and motion, bounded and cancellable motion download, and repaired native test interactions.
- Phase 2: progress routes identify each job or clip, result routes identify each job, and offscreen completion waits for focus before navigating.
- Pending jobs reopened from history can retry confirmation using the existing ownership-checked endpoint without uploading again.
- Confirmation failure explains that the video transfer finished and offers Start analysis again.
- Progress content scrolls when vertical space is limited.
- Background history polls no longer activate the native pull-to-refresh animation; manual refresh keeps its own loading state.
- Native tests cover distinct-job navigation, rejection guidance, pending-job restart, and confirmation retry with transfer counters.
- Recovery test setup resets fixture state before every test, because assertion aborts can bypass Swift defer cleanup.
- Sign-in waits for the delayed native password-save prompt before opening history.
- Phase 3: loaded history remains visible with a stale-status warning and retry when refresh fails; unavailable initial history no longer claims zero analyses.
- Failed pagination stops automatic requests after the normal retry budget and offers explicit retry for older analyses.
- Native history checks cover initial outage, a genuinely empty account, failed processing-job polling, and second-page recovery with bounded request counts.

## Native setup

The installed `com.spolysis.app` is a compatible development shell without an embedded JavaScript bundle.
Use Metro from this checkout; no native rebuild was required.
Simulator: iPhone 17 Pro, iOS 26.5, UDID `858FB450-9823-4060-AADB-CDB3CBB58445`.
The system Ruby has `xcodeproj` 1.28.1; CocoaPods is unnecessary for this installed shell.
Every command below runs from the repository root.

```sh
xcrun simctl boot 858FB450-9823-4060-AADB-CDB3CBB58445
xcrun simctl bootstatus 858FB450-9823-4060-AADB-CDB3CBB58445 -b
ruby app/e2e/create-project.rb /tmp/SpolysisOvernightUITests.xcodeproj
```

Start the fixture and Metro in separate terminals:

```sh
.venv-test/bin/python app/e2e/fixture.py --media-dir .gnhf/media --result .gnhf/media/result.json
```

```sh
EXPO_PUBLIC_SUPABASE_URL=http://localhost:8877 EXPO_PUBLIC_SUPABASE_ANON_KEY=fixture-anon EXPO_PUBLIC_API_URL=http://localhost:8877 npm --prefix app start -- --clear --port 8081
```

Actual pipeline media is in ignored `.gnhf/media/overlay.mp4`, `.gnhf/media/skeleton.json`, and `.gnhf/media/result.json`.
Phase 1 downloaded it read-only from `results/34406f21-3fa4-425e-918f-7f7efad187e3/` using main-checkout ignored configuration in memory.
No credentials were copied into this worktree or printed.
The simulator library already contains the overlay used for import; it exercises transfer behavior, not reconstruction accuracy on raw footage.
If the library is reset, use `xcrun simctl addmedia 858FB450-9823-4060-AADB-CDB3CBB58445 .gnhf/media/overlay.mp4`.
Fixture credentials must never enter a distribution build.

## Verification and evidence

Phase 3 uses the consolidated command below, with its own result bundle and log.
The fixture now supports real 20-row pagination and independent history and page-failure switches.
The initial pagination baseline reproduces repeated failed-page requests and no retry control.
Its first refresh test did not initiate a request, so the corrected refresh baseline uses the existing five-second processing-job poll.
That baseline verifies failed history responses and no stale-data warning.
The baseline bundles are `/tmp/spolysis-overnight-phase3-before.xcresult` and `/tmp/spolysis-overnight-phase3-refresh-before.xcresult`.
Their exported attachments are `.gnhf/evidence/phase3-before` and `.gnhf/evidence/phase3-refresh-before`.

```sh
xcodebuild clean test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase3-final.xcresult CODE_SIGNING_ALLOWED=NO
```

Final native result: all 11 tests pass with zero failures in 210.171 seconds.
This is one uninterrupted consolidated pass on the final product and native-test source.
All nine recovery tests, the signed-in imported-video journey with sign-out, and the authentication screens pass.
The new pagination assertion records three failed requests, then one successful explicit retry; the final older row becomes accessible.
All six new history screenshots were inspected at 1206 x 2622.
The three failure-state screenshots are preserved under `docs/screenshots/history-*.png`; all recovered states are in `.gnhf/evidence/phase3-final`.
The final journey ends signed out on the sign-in screen.
Log: `/tmp/spolysis-overnight-phase3-final.log`.
Fixture and Metro logs: `/tmp/spolysis-overnight-phase3-fixture.log` and `/tmp/spolysis-overnight-phase3-metro.log`.
TypeScript, ESLint, Prettier for HomeScreen, Python lint, fixture formatting, and diff whitespace checks pass.
The viewer build passed during Metro startup.
No API or pipeline implementation changed; the Python regression suite was not repeated.
Service outages use isolated HTTP 503 responses, not device airplane mode or production services.

### Earlier verification

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase2-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Use a new result-bundle path on each run.
The consolidated pass before the final history-refresh change passed seven of eight tests; the affected flows passed after repair as recorded below.
Its log is `/tmp/spolysis-overnight-phase2-verified.log` and fixture log is `/tmp/spolysis-overnight-phase2-fixture.log`.
The first consolidated attempt, `/tmp/spolysis-overnight-phase2-final.xcresult`, passed seven of eight tests.
Its completed-result check used leftover jobs from a failed baseline; per-test fixture reset fixes that setup failure.
The next consolidated pass, `/tmp/spolysis-overnight-phase2-verified.xcresult`, passed seven of eight tests in 183.346 seconds.
The pending test's history tap coincided with a background poll, made no detail request, and left the history visible.
The app had been activating the native refresh control for all background refetches.
Only manual refresh now activates it.
Affected history flows run twice with this command:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests/ResultRecoveryTests/testPendingUploadCanResumeFromHistory -only-testing:SpolysisUITests/ResultRecoveryTests/testSwitchingPendingAnalysesShowsSelectedJob -only-testing:SpolysisUITests/SignedInTests -test-iterations 2 -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase2-history-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Affected-flow result: six executions, zero failures in 165.658 seconds.
Pending-job recovery, distinct-job selection, and the full signed-in journey each passed twice after the final history-refresh fix.
The phase 2 full-suite run also passed completed-result recovery, video recovery, motion and signed-link recovery, confirmation retry, and authentication smoke before that Home-only change.
The confirmation test recorded one upload and two start attempts; the pending-history test recorded no upload and one start attempt.
Phase 2 did not produce one uninterrupted eight-test pass on that iteration's final source; the phase 3 consolidated pass now covers those flows together.
Final affected-flow attachments are `.gnhf/evidence/phase2-history-verified`.
The pending and rejected screenshots under `docs/screenshots` come from the final repeated pass.
The confirmation screenshot comes from the earlier successful confirmation flow; its progress-screen implementation is unchanged.
Its log is `/tmp/spolysis-overnight-phase2-history-verified.log`.
Native baseline bundles are `/tmp/spolysis-overnight-phase2-before.xcresult` and `/tmp/spolysis-overnight-phase2-history-before.xcresult`.
The first switching baseline hit the delayed password-save dialog; the signed-in rerun reproduced the actual wrong-job defect.
Baseline attachments are under `.gnhf/evidence/phase2-before` and `.gnhf/evidence/phase2-history-before`.
The first consolidated attachments are under `.gnhf/evidence/phase2-final`.

Phase 1 passed five native tests with zero failures in 115.025 seconds.
Its bundle is `/tmp/spolysis-overnight-phase1-final.xcresult`, log is `/tmp/spolysis-overnight-phase1-final.log`, and attachments are `.gnhf/evidence/phase1-final`.
Together these journeys exercise isolated authentication, history, real pipeline overlay and motion playback, 3D controls, stroke/hand selection, library import, native upload, sharing, profile, sign-out, and recovery.
Production authentication and database writes are separate unverified claims.

The following static checks pass in phase 3:

```sh
npm --prefix app run typecheck
npm --prefix app run lint
npm --prefix app run build:viewer
.venv-test/bin/python -m ruff check api pipeline tests app/e2e/fixture.py
.venv-test/bin/python -m ruff format --check app/e2e/fixture.py
app/node_modules/.bin/prettier --check app/src/screens/HomeScreen.tsx
git diff --check
```

The viewer build ran during Metro startup.
No API or pipeline implementation changed, so the Python regression suite was not repeated in either phase.

## Remaining ranked work and deferred decisions

1. Transfer interruption, missing-upload recovery, failed jobs, recording guidance, and app termination during transfer.
2. Session expiry/recovery, privacy expectations, account boundaries, and actual device-offline behavior across screens.
   History service-failure and pagination recovery are implemented in phase 3.
3. Actionable coaching and comparison interpretation, including the mismatch between highlighted joint and coaching priority in the inspected volley result.
4. Dynamic Type, smaller screens, accessibility, and remaining empty/loading/error states.
5. Consolidated native validation and honest handoff after those phases.

See [Athlete review](athlete-review.md) for issue evidence and claim limits.
Production Supabase DNS was unavailable when checked on 2026-10-30 in phase 1.
Physical camera behavior, Android runtime, distribution signing, external account access, and model accuracy remain separate requirements.

Durable upload queues and abandoned-job cleanup require a coordinated lifecycle and retention decision.
Recommendation for morning review: define explicit uploading, ready-to-start, and abandoned states with authenticated retry and retention before adding background transfers.
Phase 2 recovers confirmation using the existing contract and does not implement that larger change.

## Checkpoint and cleanup

Phase 1 checkpoint: `.gnhf/checkpoints/iteration-1-result-recovery.patch`.
Phase 2 checkpoint: `.gnhf/checkpoints/iteration-2-upload-recovery.patch`.
Phase 3 checkpoint: `.gnhf/checkpoints/iteration-3-history-recovery.patch`.
Each has an ignored status sidecar in `.gnhf/runs/objective-act-as-a-d-19111c/`.
Phase 3 Metro on 8081 and the fixture on 8877 are stopped.
The test app was terminated and this worker-booted simulator was shut down, preserving its installation and data.
The consolidated journey ends signed out.
All worker-started long-running processes are stopped.
No useful-work exhaustion or production-release claim is made; continue the ranked backlog next iteration.
